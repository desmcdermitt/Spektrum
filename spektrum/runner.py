import asyncio
import time
import re

from pike.manager import PikeManager

from spektrum import logger, utils

from spektrum.exceptions import FailedRequireException
from spektrum.expect import _LIVE_CTX
from spektrum.spec import get_case_data, Spec, spec_filter, find_children
from spektrum.reporting.core import ReportManager
from spektrum.reporting.data import CaseFormatData
from spektrum.reporting.pretty import PrettyRenderer
from spektrum.reporting.xunit import XUnitRenderer

logger.setup()
log = logger.get(__name__)


class SpektrumRunner(object):
    def __init__(self, reporting_options=None, concurrency=1, event_queue=None, live_port=None, live_linger=5):
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

    async def _async_run(self, loop, search_paths, module_name=None, metadata=None,
                         test_names=None, exclude=None, dry_run=False):
        # Start live server first so it stays alive for the entire run under one
        # event loop iteration — no gap between server start and test execution.
        live_server = None
        if self.live_port:
            if not self.event_queue:
                self.event_queue = asyncio.Queue()
            from spektrum.reporting.live import LiveServer
            live_server = LiveServer(self.live_port, self.event_queue, linger=self.live_linger)
            await live_server.start()
            print(f'Live view: http://localhost:{self.live_port}', flush=True)

        # Emit run context as the first queue event whenever a queue is active
        if self.event_queue:
            self.event_queue.put_nowait({
                'type': 'run-started',
                'search_path': search_paths[0],
                'module_name': module_name,
            })
            # Yield so the consumer task processes run-started and any waiting
            # HTTP connections are accepted before synchronous discovery begins.
            await asyncio.sleep(0)

        with PikeManager(search_paths) as mgr:
            all_inherited = mgr.get_all_inherited_classes(Spec)
            selected_modules = [
                cls
                for cls in all_inherited
                if spec_filter(Spec, cls)
            ]

            if module_name:
                selected_modules = self.filter_by_module_name(
                    selected_modules,
                    module_name
                )

            instantiated = [cls() for cls in selected_modules]
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
                    await _emit_spec_discovered(spec, self.event_queue)

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
                await self.event_queue.put({
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
            await live_server.shutdown()

        return self.reporting.success

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

    def filter_by_module_name(self, classes, name):
        found_classes = {
            name: cls
            for cls in classes
            if name == (cls.__module__.split('.') or cls.__module__)[-1]
        }
        found = list(found_classes.values())

        if not found:
            found = []
            module = next(
                cls
                for cls in classes
                if cls.__module__ in name
            )
            class_dict = self._map_classes([module], module.__module__)

            if name.startswith(utils.REGEX_TOKEN):
                name = name[len(utils.REGEX_TOKEN):]
                found_classes = {}
                for cls_name, cls in class_dict.items():
                    if re.search(f'{name}$', cls_name):
                        if not self._parent_exists(cls_name, found_classes):
                            found_classes[cls_name] = cls
                found = [cls for cls in found_classes.values()]
            elif name in class_dict.keys():
                found = [class_dict[name]]

        return found


def _count_results(specs):
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


async def _emit_spec_discovered(spec, queue):
    cases = [
        {
            'name': case.__name__,
            'display_name': utils.snakecase_to_spaces(case.__name__),
        }
        for case in spec.__test_cases__
    ]
    await queue.put({
        'type': 'spec-discovered',
        'spec_id': spec._id,
        'spec_name': type(spec).__name__,
        'spec_display_name': utils.camelcase_to_spaces(type(spec).__name__),
        'cases': cases,
    })
    for child in spec.children:
        await _emit_spec_discovered(child, queue)


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


async def execute_spec(spec, spec_semaphore, test_semaphore, reporting,
                       metadata=None, test_names=None, exclude=None, dry_run=False,
                       event_queue=None):
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
            return

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


async def execute_test_case(spec, case, semaphore, reporting, dry_run, *args,
                            event_queue=None, **kwargs):
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
        await event_queue.put({
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

        await event_queue.put({
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
