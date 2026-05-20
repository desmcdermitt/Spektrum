import asyncio
import inspect
import os
import queue
import time
import re
from typing import (
    List,
    Optional,
    Tuple,
)

from pike.manager import PikeManager

from spektrum import (
    logger,
    utils,
)

from spektrum.exceptions import FailedRequireException
from spektrum.expect import _LIVE_CTX
from spektrum.spec import (
    get_case_data,
    Spec,
    spec_filter,
    find_children,
)
from spektrum.reporting.core import ReportManager
from spektrum.reporting.data import CaseFormatData
from spektrum.reporting.pretty import PrettyRenderer
from spektrum.reporting.xunit import XUnitRenderer

logger.setup()
log = logger.get(__name__)


class SpektrumRunner(object):
    def __init__(
        self,
        reporting_options=None,
        concurrency: int = 1,
        event_queue=None,
        live_port: Optional[int] = None,
        live_linger: int = 5,
    ) -> None:
        self.spec_semaphore = asyncio.Semaphore(concurrency)
        self.test_semaphore = asyncio.Semaphore(concurrency)
        self.reporting = ReportManager(reporting_options)
        self.renderer = PrettyRenderer(reporting_options)
        self.xunit_renderer = XUnitRenderer(reporting_options)
        self.event_queue = event_queue
        self.live_port = live_port
        self.live_linger = live_linger

    def run(self, search_paths, module_name=None, metadata=None, test_names=None, exclude=None,
            dry_run=False):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self._async_run(loop, search_paths, module_name, metadata, test_names, exclude, dry_run)
        )

    async def _async_run(
        self,
        loop: asyncio.AbstractEventLoop,
        search_paths: List[str],
        module_name: Optional[str] = None,
        metadata=None,
        test_names=None,
        exclude=None,
        dry_run: bool = False,
    ) -> bool:
        # Start live server first so it stays alive for the entire run under one
        # event loop iteration — no gap between server start and test execution.
        live_server = None
        if self.live_port:
            if not self.event_queue:
                self.event_queue = queue.Queue()
            from spektrum.reporting.live import LiveServer
            live_server = LiveServer(self.live_port, self.event_queue, linger=self.live_linger)
            live_server.start_in_thread()
            print(f'Live view: http://localhost:{self.live_port}', flush=True)

        # Emit run context as the first queue event whenever a queue is active.
        if self.event_queue:
            self.event_queue.put({
                'type': 'run-started',
                'search_path': search_paths[0],
                'module_name': module_name,
            })

        # Run module discovery in a thread executor so the event loop stays
        # alive (accepting HTTP connections, serving snapshots) during the
        # otherwise-blocking import phase.
        all_inherited, instantiated = await loop.run_in_executor(
            None, self._discover, search_paths, module_name,
        )

        self.reporting.track_top_level(
            instantiated,
            all_inherited,
            metadata,
            test_names,
            exclude
        )

        self.reporting.start_reporting(dry_run)

        # Emit spec-discovered for all top-level specs (and their children)
        if self.event_queue:
            for spec in instantiated:
                _emit_spec_discovered(spec, self.event_queue)

        await asyncio.gather(*[
            execute_spec(
                spec,
                self.spec_semaphore,
                self.test_semaphore,
                self.reporting,
                metadata,
                test_names,
                exclude,
                dry_run=dry_run,
                event_queue=self.event_queue,
            )
            for spec in instantiated
        ])

        # Emit run-complete event
        if self.event_queue:
            passed, failed, skipped = _count_results(self.reporting.specs)
            self.event_queue.put({
                'type': 'run-complete',
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
            })

        print('\n', flush=True)

        report = self.reporting.build_report()
        self.renderer.render(report)

        if self.xunit_renderer.filename:
            self.xunit_renderer.render(report)

        if live_server:
            live_server.shutdown()

        return self.reporting.success

    def _discover(self, search_paths: List[str], module_name: Optional[str]) -> Tuple[list, list]:
        '''Synchronous discovery run in an executor so the event loop is free.'''
        with PikeManager(search_paths) as mgr:
            all_inherited = mgr.get_all_inherited_classes(Spec)
            # Only top-level classes are eligible to be instantiated as top-level
            # specs. Nested Spec classes (qualname contains a dot) are picked up
            # automatically as children via find_children() when the enclosing
            # spec is instantiated — listing them here would cause them to run
            # twice (once as a child, once as a top-level entry).
            #
            # Pike can also load the same source file under two different module
            # names (e.g. bare `security_cloudvps_ubuntu` from the search path
            # and `runners.spektrum.liquidweb.api.security_cloudvps_ubuntu` from
            # a fully-qualified import elsewhere). Those produce distinct class
            # objects with identical qualnames — dedupe by source file so each
            # logical class is queued at most once.
            seen = {}
            selected_modules = []
            for cls in all_inherited:
                if not (spec_filter(Spec, cls) and '.' not in cls.__qualname__):
                    continue
                try:
                    source = os.path.realpath(inspect.getfile(cls))
                except (TypeError, OSError):
                    source = cls.__module__
                key = (source, cls.__qualname__)
                if key in seen:
                    continue
                seen[key] = cls
                selected_modules.append(cls)

        if module_name:
            resolved = self._resolve_module_name(selected_modules, module_name)
            instantiated = [
                self._instantiate_with_ancestors(cls, ancestors)
                for cls, ancestors in resolved
            ]
        else:
            instantiated = [cls() for cls in selected_modules]

        return all_inherited, instantiated

    def _map_classes(self, classes, parent):
        class_dict = {}
        for cls in classes:
            cur_node = f'{parent}.{(cls.__name__)}'
            class_dict[cur_node] = cls
            children = find_children(cls)
            if children:
                class_dict.update(self._map_classes(children, cur_node))
        return class_dict

    def _parent_exists(self, name, class_map):
        for cls_name in class_map.keys():
            if cls_name in name:
                return True
        return False

    def _ancestors(self, key: str, class_dict: dict) -> list:
        '''Return ancestor classes for a dotted key, ordered immediate-parent first.'''
        parts = key.split('.')
        chain = []
        # Stop before reducing to just the module segment (need at least module.ClassName).
        while len(parts) > 2:
            parts.pop()
            ancestor_key = '.'.join(parts)
            if ancestor_key in class_dict:
                chain.append(class_dict[ancestor_key])
        return chain

    def _instantiate_with_ancestors(self, cls: type, ancestors: list):
        '''Instantiate `cls` and wrap with display-only Spec instances for each ancestor.
        Ancestor wrappers carry the ancestor's name so nested rendering shows the full
        path, but they have no test cases or lifecycle hooks of their own.'''
        instance = cls()
        cur = instance
        for ancestor_cls in ancestors:
            wrapper_cls = type(
                ancestor_cls.__name__,
                (Spec,),
                {'__module__': ancestor_cls.__module__},
            )
            wrapper = wrapper_cls()
            wrapper.children = [cur]
            cur.parent = wrapper
            cur = wrapper
        return cur

    def _resolve_module_name(self, classes: list, name: str) -> list:
        '''Resolve `name` to a list of (cls, ancestors) pairs.

        Supports three forms:
          - bare module name: `select_module`
          - dotted class path: `select_module.ChildTest.DepthOne.DepthTwo`
          - regex prefixed with `re:`: `re:select_module\\..*Fixture`
        '''
        matched = [
            (cls, [])
            for cls in classes
            if name == (cls.__module__.split('.') or cls.__module__)[-1]
        ]
        if matched:
            return matched

        is_regex = name.startswith(utils.REGEX_TOKEN)
        bare = name[len(utils.REGEX_TOKEN):] if is_regex else name
        sep = '\\.' if is_regex else '.'
        module_part = bare.split(sep, 1)[0]

        module_classes = [
            cls
            for cls in classes
            if module_part == (cls.__module__.split('.') or cls.__module__)[-1]
        ]
        if not module_classes:
            return []

        class_dict = self._map_classes(module_classes, module_part)

        if is_regex:
            pattern = name[len(utils.REGEX_TOKEN):]
            found_keys = {}
            for cls_name, cls in class_dict.items():
                if re.search(f'{pattern}$', cls_name):
                    if not self._parent_exists(cls_name, found_keys):
                        found_keys[cls_name] = cls
            return [
                (cls, self._ancestors(key, class_dict))
                for key, cls in found_keys.items()
            ]

        if name in class_dict:
            return [(class_dict[name], self._ancestors(name, class_dict))]

        return []


def _count_results(specs: dict) -> Tuple[int, int, int]:
    passed = 0
    failed = 0
    skipped = 0
    for spec in specs.values():
        for case in spec.__test_cases__:
            data = CaseFormatData(spec, case)
            if data.skipped or data.incomplete:
                skipped += 1
            elif data.successful:
                passed += 1
            else:
                failed += 1
    return passed, failed, skipped


def _emit_spec_cases_updated(spec, event_queue: queue.Queue) -> None:
    event_queue.put({
        'type': 'spec-cases-updated',
        'spec_id': spec._id,
        'cases': [
            {
                'name': case.__name__,
                'display_name': utils.snakecase_to_spaces(case.__name__),
            }
            for case in spec.__test_cases__
        ],
    })


def _emit_lifecycle_failure(spec, case, event_queue: queue.Queue) -> None:
    case_data = CaseFormatData(spec, case)
    event_queue.put({
        'type': 'case-finished',
        'spec_id': spec._id,
        'spec_name': type(spec).__name__,
        'case_name': case.__name__,
        'status': 'failed',
        'duration': case_data.elapsed_time,
        'details': {
            'expects': [e.as_dict for e in case_data.expects],
            'errors': case_data.errors,
            'skip_reason': None,
        },
    })


def _emit_spec_discovered(spec, event_queue: queue.Queue, parent_id: Optional[str] = None) -> None:
    cases = [
        {
            'name': case.__name__,
            'display_name': utils.snakecase_to_spaces(case.__name__),
        }
        for case in spec.__test_cases__
    ]
    event_queue.put({
        'type': 'spec-discovered',
        'spec_id': spec._id,
        'spec_name': type(spec).__name__,
        'spec_display_name': utils.camelcase_to_spaces(type(spec).__name__),
        'parent_id': parent_id,
        'cases': cases,
    })
    for child in spec.children:
        _emit_spec_discovered(child, event_queue, parent_id=spec._id)


async def execute_nested_spec(spec, semaphore, reporting, metadata=None, test_names=None,
                              exclude=None, dry_run=False):
    parents = []
    cls = spec.__parent_cls__
    last = None

    while cls:
        parent = cls(parent=last)
        last = parent

        parents.append(parent)
        cls = parent.__parent_cls__

    # Walk up the tree to setup specs
    parents.reverse()
    last = None
    for parent in parents:
        successful = await setup_spec(parent, semaphore, reporting, dry_run)
        if successful is False:
            reporting.case_finished(spec, None)
            return
        last = parent

    # Execute the nested spec
    spec.parent = last
    await execute_spec(
        spec,
        semaphore,
        reporting,
        metadata=metadata,
        test_names=test_names,
        exclude=exclude,
        dry_run=dry_run,
    )

    # Walk down the tree to setup specs
    parents.reverse()
    for parent in parents:
        successful = await teardown_spec(parent, semaphore, dry_run)
        if successful is False:
            reporting.case_finished(spec, None)
            return


async def execute_spec(
    spec,
    spec_semaphore,
    test_semaphore,
    reporting,
    metadata=None,
    test_names=None,
    exclude=None,
    dry_run: bool = False,
    event_queue=None,
) -> None:
    if spec.__CASE_CONCURRENCY__:
        test_semaphore = spec.__CASE_CONCURRENCY__
    if spec.__SPEC_CONCURRENCY__:
        spec_semaphore = spec.__SPEC_CONCURRENCY__

    if not spec.parent:
        utils.filter_cases_by_data(spec, metadata, test_names, exclude)

    # Limit spec setups to max concurrency level
    async with spec_semaphore:
        successful = await setup_spec(spec, test_semaphore, reporting, dry_run=dry_run)
        if successful is False:
            setup_case = spec._get_case('before_all')
            spec._add_test_case(setup_case)
            reporting.case_finished(spec, setup_case)
            if event_queue:
                _emit_lifecycle_failure(spec, setup_case, event_queue)
            return

        if event_queue:
            _emit_spec_cases_updated(spec, event_queue)

        test_futures = [
            execute_test_case(spec, func, test_semaphore, reporting, dry_run=dry_run,
                              event_queue=event_queue)
            for func in spec.__test_cases__
        ]
        await asyncio.gather(*test_futures)

    spec_futures = [
        execute_spec(
            child,
            spec_semaphore,
            test_semaphore,
            reporting,
            metadata,
            test_names,
            exclude,
            dry_run=dry_run,
            event_queue=event_queue,
        )
        for child in spec.children
    ]
    await asyncio.gather(*spec_futures)

    async with spec_semaphore:
        successful = await teardown_spec(spec, test_semaphore, dry_run=dry_run)
        if successful is False:
            teardown_case = spec._get_case('after_all')
            spec._add_test_case(teardown_case)
            reporting.case_finished(spec, teardown_case)
            if event_queue:
                _emit_lifecycle_failure(spec, teardown_case, event_queue)

    reporting.spec_finished(spec)


async def setup_spec(spec, semaphore, reporting, dry_run=False):
    log.debug('Setting up Spec: %s', utils.get_fullname(spec))

    reporting.track_spec(spec)
    if spec.has_dependencies:
        return await execute_method(spec.before_all, semaphore, dry_run)


async def teardown_spec(spec, semaphore, dry_run=False):
    log.debug('Tearing down Spec: %s', utils.get_fullname(spec))
    if spec.has_dependencies:
        return await execute_method(spec.after_all, semaphore, dry_run)


async def execute_method(method, semaphore, dry_run, *args, **kwargs):
    # If it has the inherited tag, it's from the base class and don't execute
    if getattr(method, '__inherited_from_spec__', None):
        return

    async with semaphore:
        try:
            log.debug('Executing: %s', method.__func__.__qualname__)
            ret = None

            if not dry_run:
                if asyncio.iscoroutinefunction(method):
                    ret = await method(*args, **kwargs)
                else:
                    ret = method(*args, **kwargs)

            log.debug('Finished: %s', method.__func__.__qualname__)
            return ret

        except FailedRequireException:
            pass

        except Exception as exc:
            # Get the tracebacks and attach them to the test case for
            # reporting later.
            tracebacks = utils.get_tracebacks(exc)
            method.__func__.__tracebacks__ = tracebacks

            return False

    return True


async def execute_test_case(spec, case, semaphore, reporting, dry_run: bool, *args,
                            event_queue=None, **kwargs) -> None:
    spec.has_run = True
    data = get_case_data(case)
    if data.incomplete:
        reporting.case_finished(spec, case)
        return

    # If we're executing a data-driven case we need to override the kwargs
    if data.type == 'data-driven':
        kwargs = data.data_kwargs

    if not (data.skip or data.incomplete):
        successful = await execute_method(spec.before_each, semaphore, dry_run)
        if successful is False:
            data.before_traces.extend(spec.before_each.__tracebacks__)
            reporting.case_finished(spec, case)
            return

    # Emit case-started event for non-skipped cases
    if event_queue and not data.skip:
        event_queue.put({
            'type': 'case-started',
            'spec_id': spec._id,
            'spec_name': type(spec).__name__,
            'case_name': case.__name__,
            'timestamp': time.time(),
        })

    data.start_time = time.time()
    live_token = None
    if event_queue and not data.skip:
        live_token = _LIVE_CTX.set({
            'queue': event_queue,
            'spec_id': spec._id,
            'case_name': case.__name__,
        })
    try:
        await execute_method(getattr(spec, case.__name__), semaphore, dry_run, *args, **kwargs)
    finally:
        if live_token is not None:
            _LIVE_CTX.reset(live_token)
    data.end_time = time.time()

    if not (data.skip or data.incomplete):
        successful = await execute_method(spec.after_each, semaphore, dry_run)
        if successful is False:
            data.after_traces.extend(spec.after_each.__tracebacks__)

    reporting.case_finished(spec, case)

    # Emit case-finished event
    if event_queue:
        case_data = CaseFormatData(spec, case)
        if case_data.skipped or case_data.incomplete:
            status = 'skipped'
        elif case_data.successful:
            status = 'passed'
        else:
            status = 'failed'

        event_queue.put({
            'type': 'case-finished',
            'spec_id': spec._id,
            'spec_name': type(spec).__name__,
            'case_name': case.__name__,
            'status': status,
            'duration': case_data.elapsed_time,
            'details': {
                'expects': [e.as_dict for e in case_data.expects],
                'errors': case_data.errors,
                'skip_reason': case_data.skip_reason,
            },
        })
