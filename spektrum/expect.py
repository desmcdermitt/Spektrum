import asyncio
import ast
import copy
import inspect
from contextvars import ContextVar


from spektrum import (
    logger,
    utils,
)
from spektrum.spec import Spec
from spektrum.exceptions import FailedRequireException
from ast_decompiler import decompile

# Holds { 'queue': asyncio.Queue, 'spec_id': str, 'case_name': str } when a
# live run is active; None otherwise.  Set/reset by execute_test_case().
_LIVE_CTX: ContextVar = ContextVar('_LIVE_CTX', default=None)

log = logger.get(__name__)


class Expectation(object):
    def __init__(self, target, required=False, caller_args=None, caller_kwargs=None,
                 src_params=None):
        self.prefix = 'expect'
        self.success = False
        self.used_negative = False
        self.target = target
        self.required = required
        self.expected = None
        self.actions = [target]
        self.caller_args = caller_args
        self.caller_kwargs = caller_kwargs
        self.custom_msg = None
        self.custom_report_vars = {}
        self.src_params = src_params

    def _verify_condition(self, condition):
        self.success = condition if not self.used_negative else not condition
        self._emit_live_assertion()
        if self.required and not self.success:
            raise FailedRequireException()

        return self.success

    def _emit_live_assertion(self) -> None:
        ctx = _LIVE_CTX.get()
        if ctx is None:
            return
        try:
            ctx['queue'].put_nowait({
                'type': 'assertion-added',
                'spec_id': ctx['spec_id'],
                'case_name': ctx['case_name'],
                'assertion': {
                    'evaluation': str(self),
                    'success': self.success,
                    'required': self.required,
                },
            })
        except (asyncio.QueueFull, RuntimeError):
            pass

    def _compare(self, action_name, expected, condition):
        self.expected = expected
        self.actions.extend([action_name, expected])
        self._verify_condition(condition=condition)

    def __str__(self):
        action_list = copy.copy(self.actions)
        src = self.target_src_param
        # f-string source shows unevaluated placeholders and unicode escapes;
        # use the already-evaluated value instead.
        if src and src.lstrip().startswith(('f"', "f'", 'f"""', "f'''")):
            src = None
        action_list[0] = src or str(self.target)
        action_list[-1] = self.expected_src_param or str(self.expected)

        return ' '.join([str(action) for action in action_list])

    @property
    def target_src_param(self):
        if self.src_params and self.src_params.expect_arg:
            return self.src_params.expect_arg

    @property
    def expected_src_param(self):
        if self.src_params and self.src_params.cmp_arg:
            return self.src_params.cmp_arg

    @property
    def not_to(self):
        self.actions.append('not')
        self.used_negative = not self.used_negative
        return self.to

    @property
    def to(self):
        self.actions.append('to')
        return self

    def equal(self, expected):
        self._compare(
            action_name='equal',
            expected=expected,
            condition=self.target == expected
        )

    def almost_equal(self, expected, places=7):
        if not isinstance(places, int):
            raise TypeError('Places must be an integer')

        self._compare(
            action_name='almost equal',
            expected=expected,
            condition=round(abs(self.target - expected), places) == 0
        )

    def be_greater_than(self, expected):
        self._compare(
            action_name='be greater than',
            expected=expected,
            condition=self.target > expected
        )

    def be_less_than(self, expected):
        self._compare(
            action_name='be less than',
            expected=expected,
            condition=self.target < expected
        )

    def be_none(self):
        self._compare(
            action_name='be',
            expected=None,
            condition=self.target is None
        )

    def be_true(self):
        self._compare(
            action_name='be',
            expected=True,
            condition=self.target
        )

    def be_false(self):
        self._compare(
            action_name='be',
            expected=False,
            condition=not self.target
        )

    def contain(self, expected):
        self._compare(
            action_name='contain',
            expected=expected,
            condition=expected in self.target
        )

    def be_in(self, expected):
        self._compare(
            action_name='be in',
            expected=expected,
            condition=self.target in expected
        )

    def be_a(self, expected):
        self._compare(
            action_name='be a',
            expected=expected,
            condition=type(self.target) is expected
        )

    def be_an_instance_of(self, expected):
        self._compare(
            action_name='be an instance of',
            expected=expected,
            condition=isinstance(self.target, expected)
        )

    def be_a_subset_of(self, expected):
        try:
            iter(expected)
            iter(self.target)
        except TypeError:
            raise TypeError('Expected must be ')

        self._compare(
            action_name='be a subset of',
            expected=expected,
            condition=set(self.target).issubset(set(expected))
        )

    def be_a_superset_of(self, expected):
        try:
            iter(expected)
            iter(self.target)
        except TypeError:
            raise TypeError('Must specify iterables')

        self._compare(
            action_name='be a superset of',
            expected=expected,
            condition=set(self.target).issuperset(set(expected))
        )

    def raise_a(self, exception):
        self.expected = exception
        self.actions.extend(['raise', exception])
        condition = False
        raised_exc = 'nothing'

        try:
            self.target(*self.caller_args, **self.caller_kwargs)
        except Exception as e:
            condition = type(e) is exception
            raised_exc = e

        # We didn't raise anything
        if self.used_negative and not isinstance(raised_exc, Exception):
            self.success = True

        # Raised, but it didn't match
        elif self.used_negative and type(raised_exc) is not exception:
            self.success = False

        elif self.used_negative:
            self.success = not condition

        else:
            self.success = condition

        if not self.success:
            was = 'wasn\'t' if self.used_negative else 'was'

            # Make sure we have a name to use
            if getattr(self.expected, '__name__'):
                name = self.expected.__name__
            else:
                name = type(self.expected).__name__

            self.custom_msg = f'function {was} expected to raise "{name}".'
            # self.custom_report_vars['Raised Exception'] = (
            #     type(raised_exc).__name__
            # )


class Requirement(Expectation):
    def __init__(self, target, required=True, caller_args=None, caller_kwargs=None,
                 src_params=None):
        super().__init__(
            target=target,
            required=required,
            caller_args=caller_args,
            caller_kwargs=caller_kwargs,
            src_params=src_params,
        )
        self.prefix = 'require'


def _find_last_spec():
    for frame, *_ in inspect.stack():
        obj = frame.f_locals.get('self')
        if obj and isinstance(obj, Spec):
            return obj, frame


def _add_expect_to_spec(instance):
    '''Walks the stack back until it gets to a Spec and adds the expectation'''
    try:
        spec, frame = _find_last_spec()

        # HACK(jmvrbanac): Oooo this is nasty!
        max_depth = 50
        depth = 0
        stack_frame = frame.f_back
        while stack_frame and depth < max_depth:
            has_name = stack_frame.f_code.co_name == 'execute_method'
            is_right_file = 'runner.py' in stack_frame.f_code.co_filename

            if has_name and is_right_file:
                func = stack_frame.f_locals['method'].__func__
                spec.__expects__[func].append(instance)
                break

            stack_frame = stack_frame.f_back
            depth += 1

    except (AttributeError, TypeError, KeyError, IndexError) as error:
        raise RuntimeError(
            f'Error attempting to add expect to parent Spec: {error}'
        ) from error


def _get_closest_expression(line, tree):
    def distance(node):
        return abs(node.lineno - line)

    # Walk the tree until we get the expression we need
    expect_exp = None
    closest_exp = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr):
            if node.lineno == line:
                expect_exp = node
                break

            if (closest_exp is None
                    or distance(node) < distance(closest_exp)):
                closest_exp = node

    return expect_exp or closest_exp


def get_expect_params():
    stack = inspect.stack()
    expect_stack_info = stack[2]
    expect_frame = expect_stack_info.frame
    try:
        spec, _ = _find_last_spec()

        source_filename = expect_frame.f_code.co_filename
        source, node = utils.load_source_and_ast(source_filename)

        expr_node = _get_closest_expression(expect_frame.f_lineno, node)
        return ExpectParams(expr_node)
    except (AttributeError, TypeError, IndexError, ValueError):
        log.debug('Failed to get expect params... suppressing')


def expect(obj, caller_args=None, **kwargs):
    '''Primary method for test assertions in Spektrum

    :param obj: The evaluated target object
    :param caller_args: Is only used when using expecting a raised Exception
    :param **kwargs: Kwargs passed through to the function.
    '''
    src_params = get_expect_params()
    obj = Expectation(
        obj,
        caller_args=caller_args or [],
        caller_kwargs=kwargs,
        src_params=src_params,
    )

    try:
        _add_expect_to_spec(obj)
    except (AttributeError, TypeError, RuntimeError):
        log.debug('Failed to to add expect to spec... suppressing')

    return obj


def require(obj, caller_args=None, **kwargs):
    '''Primary method for test assertions in Spektrum

    :param obj: The evaluated target object
    :param caller_args: Is only used when using expecting a raised Exception
    :param **kwargs: Kwargs passed through to the function.
    '''
    src_params = get_expect_params()
    obj = Requirement(
        obj,
        caller_args=caller_args or [],
        caller_kwargs=kwargs,
        src_params=src_params,
    )

    try:
        _add_expect_to_spec(obj)
    except (AttributeError, TypeError, RuntimeError):
        log.debug('Failed to to add require to spec... suppressing')

    return obj


class ExpectParams(object):
    types_with_args = [
        'equal',
        'almost_equal',
        'be_greater_than',
        'be_less_than',
        'be_almost_equal',
        'be_a',
        'be_an_instance_of',
        'be_in',
        'contain',
        'raise_a',
        'be_a_subset_of',
        'be_a_superset_of',
    ]

    def __init__(self, expr):
        self.expect_exp = expr

    @property
    def cmp_call(self):
        # `_get_closest_expression` falls back to the nearest expression statement
        # whenever the calling line holds none of its own, so this can be any
        # expression at all -- a bare `await`, a plain `helper()` call, a
        # docstring. Only a call can be an `expect(X).to.matcher(Y)` chain, and
        # everything below walks this node, so reject anything else up front.
        if self.expect_exp and isinstance(self.expect_exp.value, ast.Call):
            return self.expect_exp.value

    @property
    def expect_call(self):
        # Verify the whole `expect(X).to.matcher(Y)` shape rather than trusting
        # it. A bare `helper()` is a call whose func is a Name, and `self.a.b()`
        # is a call whose func chain bottoms out somewhere other than a call.
        cmp_call = self.cmp_call
        if cmp_call is None or not isinstance(cmp_call.func, ast.Attribute):
            return None

        matcher_owner = cmp_call.func.value
        if not isinstance(matcher_owner, ast.Attribute):
            return None

        expect_call = matcher_owner.value

        return expect_call if isinstance(expect_call, ast.Call) else None

    @property
    def cmp_type(self):
        cmp_call = self.cmp_call
        if cmp_call is not None and isinstance(cmp_call.func, ast.Attribute):
            return cmp_call.func.attr

    @property
    def cmp_arg(self):
        arg = None
        # A matcher may still be written without its argument, so the argument
        # list is not guaranteed to be populated just because the type matches.
        if self.cmp_type in self.types_with_args and self.cmp_call.args:
            arg = decompile(self.cmp_call.args[0])
        return arg

    @property
    def expect_type(self):
        expect_call = self.expect_call
        if expect_call is not None and isinstance(expect_call.func, ast.Name):
            return expect_call.func.id

    @property
    def expect_arg(self):
        expect_call = self.expect_call
        if expect_call is not None and expect_call.args:
            return decompile(expect_call.args[0])
