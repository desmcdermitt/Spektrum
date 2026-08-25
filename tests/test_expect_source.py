'''Regression coverage for the expect-source reporting defect.

`get_expect_params` records the source expression behind every assertion so the
reporter can print `foo to equal bar` rather than raw values. It locates that
expression with `_get_closest_expression`, which falls back to the *nearest*
expression statement whenever the calling line holds no expression statement of
its own. An assignment is enough to trigger the fallback, because
`outcome = expect(1).to.equal(2)` is an `ast.Assign`, not an `ast.Expr`.

`ExpectParams` then assumes the statement it was handed is an
`expect(X).to.matcher(Y)` call and walks `cmp_call.func.value.value` blindly. Any
other statement shape raises. The reporter touches these properties only while
rendering, so a run that has already finished every test loses its whole report:

    pretty.py:146    f'{arrow} {mark} {expect.evaluation}'
      -> expect.py    __str__ -> target_src_param -> expect_arg -> expect_call
    AttributeError: 'Await' object has no attribute 'func'

The `Await` node in that traceback is only the shape that happened to be caught.
A bare `helper()` or `self.api.get()` next to an assertion poisons the same
properties and is far more common in test code, so these checks sweep statement
shapes rather than pinning the single reported one. Two further traps sit behind
it:

- Guarding `expect_call` alone is not enough. `__str__` also reads
  `expected_src_param` -> `cmp_arg` -> `cmp_type`, which walks `cmp_call.func` by
  a separate route.
- The failure is not one exception type. An empty argument list reaches
  `decompile(call.args[0])` and raises IndexError instead.

These checks build `Expectation` objects directly rather than calling `expect()`,
so a poisoned assertion is never registered with a live spec.
'''
import ast

import pytest

from spektrum.expect import (
    Expectation,
    ExpectParams,
    _get_closest_expression,
)
from spektrum.reporting.data import ExpectFormatData


# Ordinary lines of test code that may sit next to an assertion, and that
# `_get_closest_expression` can therefore hand to `ExpectParams`.
STATEMENT_SHAPES = [
    ('bare-await', 'async def sample():\n    await helper()\n'),
    ('awaited-chain', 'async def sample():\n    await self.api.get()\n'),
    ('bare-call', 'def sample():\n    helper()\n'),
    ('method-call', 'def sample():\n    self.helper()\n'),
    ('chained-call', 'def sample():\n    self.api.get()\n'),
    ('deep-chained-call', 'def sample():\n    self.a.b.c()\n'),
    ('subscript-call', 'def sample():\n    items[0]()\n'),
    ('lambda-call', 'def sample():\n    (lambda: 1)()\n'),
    ('call-of-call', 'def sample():\n    factory()()\n'),
    ('docstring', 'def sample():\n    "a docstring"\n'),
    ('bare-name', 'def sample():\n    value\n'),
    ('bare-attribute', 'def sample():\n    self.value\n'),
    ('f-string', 'def sample():\n    f"{value}"\n'),
    ('comparison', 'def sample():\n    left == right\n'),
    ('boolean-op', 'def sample():\n    left and right\n'),
    ('unary-op', 'def sample():\n    not value\n'),
    ('ternary', 'def sample():\n    a if b else c\n'),
    ('list-literal', 'def sample():\n    [1, 2]\n'),
    ('dict-literal', 'def sample():\n    {1: 2}\n'),
    ('list-comprehension', 'def sample():\n    [each for each in items]\n'),
    ('generator', 'def sample():\n    (each for each in items)\n'),
    ('slice', 'def sample():\n    items[1:2]\n'),
    ('yield', 'def sample():\n    yield value\n'),
    ('ellipsis', 'def sample():\n    ...\n'),
    ('awaited-expect', 'async def sample():\n    await expect(v).to.equal(1)\n'),
    ('single-attribute-matcher', 'def sample():\n    expect(v).to_be_thing()\n'),
    ('expect-without-arguments', 'def sample():\n    expect().to.equal(2)\n'),
    ('matcher-without-arguments', 'def sample():\n    expect(v).to.equal()\n'),
]

SOURCE_PROPERTIES = [
    'expect_call',
    'cmp_type',
    'cmp_arg',
    'expect_arg',
]

# Real assertions must keep rendering their own source text. Without these a fix
# that simply returned None everywhere would satisfy the sweep above while
# silently reducing every report to bare values.
RENDERED_ASSERTIONS = [
    ('expect(value).to.equal(2)', 'value to equal 2'),
    (
        'expect(php[\'account_version\']).to.equal(self.versions[0])',
        'php[\'account_version\'] to equal self.versions[0]',
    ),
    (
        'expect(service.package.id).to.equal(upgrade_package.id)',
        'service.package.id to equal upgrade_package.id',
    ),
]

ASSIGNED_EXPECT_SOURCE = '''
async def sample():
    await helper()
    outcome = expect(1).to.equal(2)
    return outcome
'''

# The `outcome = ...` line above. It is an assignment, so no expression statement
# shares its line and `_get_closest_expression` falls back to the bare `await`.
ASSIGNED_EXPECT_LINE = 4

SHAPE_IDS = [label for label, _ in STATEMENT_SHAPES]
SHAPE_SOURCES = [source for _, source in STATEMENT_SHAPES]


def statement_for(source):
    '''The first statement inside the sample function in this source.'''
    return ast.parse(source).body[0].body[0]


@pytest.mark.parametrize('prop', SOURCE_PROPERTIES)
@pytest.mark.parametrize('source', SHAPE_SOURCES, ids=SHAPE_IDS)
def test_source_property_resolves_for_any_statement(source, prop):
    '''No statement shape may make a source property raise.'''
    getattr(ExpectParams(statement_for(source)), prop)


@pytest.mark.parametrize('source', SHAPE_SOURCES, ids=SHAPE_IDS)
def test_rendering_succeeds_for_any_statement(source):
    '''The reporter renders every assertion through `str()`; it must not raise.'''
    str(Expectation(1, src_params=ExpectParams(statement_for(source))))


def test_expression_chosen_for_an_assigned_expect_is_usable():
    '''The real selection path must not hand back an unusable statement.'''
    chosen = _get_closest_expression(
        ASSIGNED_EXPECT_LINE,
        ast.parse(ASSIGNED_EXPECT_SOURCE),
    )

    for prop in SOURCE_PROPERTIES:
        getattr(ExpectParams(chosen), prop)


@pytest.mark.parametrize('source, wanted', RENDERED_ASSERTIONS)
def test_real_assertions_keep_rendering_their_source(source, wanted):
    '''A guard against a fix that resolves the crash by resolving nothing.'''
    expectation = Expectation('actual', src_params=ExpectParams(ast.parse(source).body[0]))
    expectation.to.equal('actual')

    assert str(expectation) == wanted


@pytest.mark.parametrize('source', SHAPE_SOURCES, ids=SHAPE_IDS)
def test_reporter_labels_fall_back_to_the_value(source):
    '''An unresolved source expression must not be reported as the name `None`.

    The reporter prints `f'| {expect.target_name}: {expect.target}'`, so a
    `target_name` of None renders the label `None:` next to the value.

    Shapes that really are `expect(X).to.matcher(Y)` calls still resolve their
    own source text, so this asserts only that a label is always produced.
    '''
    expectation = Expectation('the-target', src_params=ExpectParams(statement_for(source)))
    expectation.to.equal('the-expected')
    reported = ExpectFormatData(expectation)

    assert reported.target_name is not None
    assert reported.expected_name is not None
