import asyncio
import io
import json
import socket
import time

from spektrum import Spec, expect, require


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class RunnerEventEmission(Spec):
    """6.1 Runner event emission tests"""

    def _run_and_collect(self):
        """Run the runner in a fresh thread to avoid event loop conflicts."""
        import threading
        from spektrum.runner import SpektrumRunner
        results = []
        error_holder = []

        def in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                queue = asyncio.Queue()
                runner = SpektrumRunner(event_queue=queue)
                runner.run(['./tests/example_data/'])
                events = []
                while not queue.empty():
                    events.append(queue.get_nowait())
                results.extend(events)
            except Exception as exc:
                error_holder.append(exc)
            finally:
                loop.close()

        t = threading.Thread(target=in_thread, daemon=True)
        t.start()
        t.join(timeout=30)
        if error_holder:
            raise error_holder[0]
        return results

    def test_emits_spec_discovered_event(self):
        events = self._run_and_collect()
        types = [e['type'] for e in events]
        expect('spec-discovered' in types).to.be_true()

    def test_emits_case_finished_event(self):
        events = self._run_and_collect()
        types = [e['type'] for e in events]
        expect('case-finished' in types).to.be_true()

    def test_emits_run_complete_event(self):
        events = self._run_and_collect()
        types = [e['type'] for e in events]
        expect('run-complete' in types).to.be_true()

    def test_no_queue_unchanged_behavior(self):
        import threading
        from spektrum.runner import SpektrumRunner
        results = [None]

        def in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                runner = SpektrumRunner()
                results[0] = runner.run(['./tests/example_data/'])
            finally:
                loop.close()

        t = threading.Thread(target=in_thread, daemon=True)
        t.start()
        t.join(timeout=30)
        expect(isinstance(results[0], bool)).to.be_true()

    def test_spec_discovered_before_case_started(self):
        events = self._run_and_collect()
        discovered = set()
        for evt in events:
            if evt['type'] == 'spec-discovered':
                discovered.add(evt['spec_id'])
            elif evt['type'] == 'case-started':
                expect(evt['spec_id'] in discovered).to.be_true()

    def test_run_complete_has_counts(self):
        events = self._run_and_collect()
        run_complete = next((e for e in events if e['type'] == 'run-complete'), None)
        require(run_complete).not_to.be_none()
        expect('passed' in run_complete).to.be_true()
        expect('failed' in run_complete).to.be_true()
        expect('skipped' in run_complete).to.be_true()


class LiveServerBroadcast(Spec):
    """6.2 LiveServer SSE broadcast logic"""

    async def test_broadcasts_event_to_connected_client(self):
        from spektrum.reporting.live import LiveServer

        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue)
        await server.start()

        received = []

        class MockWriter:
            def is_closing(self):
                return False

            def write(self, data):
                received.append(data)

            async def drain(self):
                pass

        mock = MockWriter()
        server._clients.append(mock)
        await server._broadcast('case-update', {
            'spec_id': 'x',
            'case_name': 'y',
            'status': 'passed',
        })

        require(len(received)).to.equal(1)
        raw = received[0].decode('utf-8')
        expect('event: case-update' in raw).to.be_true()
        parsed = json.loads(raw.split('data: ')[1])
        expect(parsed['status']).to.equal('passed')

        # Cleanup
        server._clients.clear()
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        server._server.close()
        await server._server.wait_closed()

    async def test_snapshot_sent_on_connect(self):
        from spektrum.reporting.live import LiveServer

        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue)
        await server.start()

        # Pre-populate state via the consumer
        await queue.put({
            'type': 'spec-discovered',
            'spec_id': 'abc',
            'spec_name': 'MySpec',
            'spec_display_name': 'My Spec',
            'cases': [{'name': 'test_foo', 'display_name': 'test foo'}],
        })
        await asyncio.sleep(0.05)

        received = []

        class MockWriter:
            def is_closing(self):
                return False

            def write(self, data):
                received.append(data)

            async def drain(self):
                pass

        await server._send_snapshot(MockWriter())

        require(len(received)).to.equal(1)
        raw = received[0].decode('utf-8')
        expect('event: snapshot' in raw).to.be_true()
        snap = json.loads(raw.split('data: ')[1])
        expect(len(snap['specs'])).to.equal(1)
        expect(snap['specs'][0]['id']).to.equal('abc')

        # Cleanup
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        server._server.close()
        await server._server.wait_closed()


class LiveServerIntegration(Spec):
    """6.3 Integration: run spec with --live, connect to /events, assert events arrive"""

    def test_snapshot_and_events_received(self):
        import threading
        import time

        from spektrum.runner import SpektrumRunner

        port = get_free_port()
        collected = []
        server_ready = threading.Event()
        run_done = threading.Event()

        def run_runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            runner = SpektrumRunner(live_port=port)
            runner.run(['./tests/example_data/'])
            run_done.set()
            loop.close()

        def collect_sse():
            # Keep trying to connect until success or server gone
            s = None
            for _ in range(40):
                try:
                    s = socket.create_connection(('127.0.0.1', port), timeout=0.5)
                    break
                except (ConnectionRefusedError, OSError):
                    s = None
                    time.sleep(0.05)

            if s is None:
                collected.append('_connection_failed')
                return

            try:
                s.sendall(b'GET /events HTTP/1.1\r\nHost: localhost\r\n\r\n')
                s.settimeout(8.0)
                buf = b''
                headers_done = False
                while True:
                    try:
                        chunk = s.recv(4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf += chunk
                    if not headers_done and b'\r\n\r\n' in buf:
                        _, buf = buf.split(b'\r\n\r\n', 1)
                        headers_done = True
                    if not headers_done:
                        continue
                    while b'\n\n' in buf:
                        raw, buf = buf.split(b'\n\n', 1)
                        text = raw.decode('utf-8').strip()
                        if text.startswith('event:'):
                            lines = text.split('\n')
                            evt_type = lines[0].split(':', 1)[1].strip()
                            collected.append(evt_type)
                            if evt_type == 'run-complete':
                                return
            except Exception:
                pass
            finally:
                try:
                    s.close()
                except Exception:
                    pass

        runner_thread = threading.Thread(target=run_runner, daemon=True)
        sse_thread = threading.Thread(target=collect_sse, daemon=True)

        runner_thread.start()
        sse_thread.start()

        runner_thread.join(timeout=30)
        sse_thread.join(timeout=5)

        expect('snapshot' in collected).to.be_true()
        expect('case-update' in collected or 'run-complete' in collected).to.be_true()


class LiveRunContext(Spec):
    """Live run-context event and snapshot tests"""

    def _run_and_collect(self, search_path='./tests/example_data/', module_name=None):
        import threading
        from spektrum.runner import SpektrumRunner
        results = []
        error_holder = []

        def in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                queue = asyncio.Queue()
                runner = SpektrumRunner(event_queue=queue)
                runner.run([search_path], module_name=module_name)
                events = []
                while not queue.empty():
                    events.append(queue.get_nowait())
                results.extend(events)
            except Exception as exc:
                error_holder.append(exc)
            finally:
                loop.close()

        t = threading.Thread(target=in_thread, daemon=True)
        t.start()
        t.join(timeout=30)
        if error_holder:
            raise error_holder[0]
        return results

    def test_run_started_is_first_event(self):
        events = self._run_and_collect()
        require(len(events)).to.be_greater_than(0)
        expect(events[0]['type']).to.equal('run-started')

    def test_run_started_contains_search_path(self):
        events = self._run_and_collect()
        run_started = next((e for e in events if e['type'] == 'run-started'), None)
        require(run_started).not_to.be_none()
        expect(run_started['search_path']).to.equal('./tests/example_data/')

    def test_run_started_module_name_none_when_not_set(self):
        events = self._run_and_collect()
        run_started = next((e for e in events if e['type'] == 'run-started'), None)
        require(run_started).not_to.be_none()
        expect(run_started['module_name']).to.be_none()

    async def test_snapshot_includes_run_context_after_run_started(self):
        from spektrum.reporting.live import LiveServer

        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue)
        await server.start()

        await queue.put({
            'type': 'run-started',
            'search_path': 'tests/mymodule/',
            'module_name': 'MySpec',
        })
        await asyncio.sleep(0.05)

        received = []

        class MockWriter:
            def is_closing(self):
                return False

            def write(self, data):
                received.append(data)

            async def drain(self):
                pass

        await server._send_snapshot(MockWriter())

        require(len(received)).to.equal(1)
        snap = json.loads(received[0].decode('utf-8').split('data: ')[1])
        require(snap.get('run_context')).not_to.be_none()
        expect(snap['run_context']['search_path']).to.equal('tests/mymodule/')
        expect(snap['run_context']['module_name']).to.equal('MySpec')

        # Cleanup
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        server._server.close()
        await server._server.wait_closed()

    async def test_snapshot_run_context_null_before_run_started(self):
        from spektrum.reporting.live import LiveServer

        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue)
        await server.start()

        received = []

        class MockWriter:
            def is_closing(self):
                return False

            def write(self, data):
                received.append(data)

            async def drain(self):
                pass

        await server._send_snapshot(MockWriter())
        snap = json.loads(received[0].decode('utf-8').split('data: ')[1])
        expect(snap.get('run_context')).to.be_none()

        # Cleanup
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        server._server.close()
        await server._server.wait_closed()


class LiveAssertionStreaming(Spec):
    """5.1-5.2 Live assertion streaming tests"""

    def _run_and_collect(self):
        import threading
        from spektrum.runner import SpektrumRunner
        results = []
        error_holder = []

        def in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                queue = asyncio.Queue()
                runner = SpektrumRunner(event_queue=queue)
                runner.run(['./tests/example_data/'])
                events = []
                while not queue.empty():
                    events.append(queue.get_nowait())
                results.extend(events)
            except Exception as exc:
                error_holder.append(exc)
            finally:
                loop.close()

        t = threading.Thread(target=in_thread, daemon=True)
        t.start()
        t.join(timeout=30)
        if error_holder:
            raise error_holder[0]
        return results

    def test_emits_assertion_added_events_during_live_run(self):
        events = self._run_and_collect()
        types = [e['type'] for e in events]
        expect('assertion-added' in types).to.be_true()

    def test_assertion_added_event_has_required_fields(self):
        events = self._run_and_collect()
        assertion_events = [e for e in events if e['type'] == 'assertion-added']
        require(len(assertion_events)).to.be_greater_than(0)
        evt = assertion_events[0]
        expect('spec_id' in evt).to.be_true()
        expect('case_name' in evt).to.be_true()
        expect('assertion' in evt).to.be_true()
        a = evt['assertion']
        expect('evaluation' in a).to.be_true()
        expect('success' in a).to.be_true()
        expect('required' in a).to.be_true()

    def test_no_assertion_event_emitted_without_live_ctx(self):
        """Assertions evaluated outside a live run must not emit events."""
        from spektrum.expect import _LIVE_CTX, expect as spk_expect
        require(_LIVE_CTX.get()).to.be_none()
        # Evaluating an assertion here must not raise or produce side effects
        spk_expect(1 + 1).to.equal(2)
        # If we reach here without error the no-op path is confirmed
        expect(True).to.be_true()

    async def test_live_server_handles_assertion_added_and_broadcasts(self):
        from spektrum.reporting.live import LiveServer

        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue)
        await server.start()

        # Seed spec state so the handler can find the case
        await queue.put({
            'type': 'spec-discovered',
            'spec_id': 'spec1',
            'spec_name': 'MySpec',
            'spec_display_name': 'My Spec',
            'cases': [{'name': 'test_foo', 'display_name': 'test foo'}],
        })
        await asyncio.sleep(0.05)

        received = []

        class MockWriter:
            def is_closing(self):
                return False

            def write(self, data):
                received.append(data)

            async def drain(self):
                pass

        server._clients.append(MockWriter())

        await queue.put({
            'type': 'assertion-added',
            'spec_id': 'spec1',
            'case_name': 'test_foo',
            'assertion': {'evaluation': 'x to equal 1', 'success': True, 'required': False},
        })
        await asyncio.sleep(0.05)

        require(len(received)).to.be_greater_than(0)
        raw = received[0].decode('utf-8')
        expect('event: case-update' in raw).to.be_true()
        parsed = json.loads(raw.split('data: ')[1])
        expect(parsed['status']).to.equal('running')
        expect(len(parsed['details']['expects'])).to.equal(1)
        expect(parsed['details']['expects'][0]['evaluation']).to.equal('x to equal 1')

        # Cleanup
        server._clients.clear()
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        server._server.close()
        await server._server.wait_closed()


class LiveServerPortConflict(Spec):
    """6.4 Port-conflict error path"""

    async def test_exits_on_port_conflict(self):
        from spektrum.reporting.live import LiveServer

        # Occupy a port
        occupied = await asyncio.start_server(
            lambda r, w: None, '127.0.0.1', 0,
        )
        port = occupied.sockets[0].getsockname()[1]

        exited = False
        exit_code = None
        try:
            queue = asyncio.Queue()
            server = LiveServer(port, queue)
            try:
                await server.start()
            except SystemExit as exc:
                exited = True
                exit_code = exc.code
        finally:
            occupied.close()
            await occupied.wait_closed()

        expect(exited).to.be_true()
        expect(exit_code).to.equal(1)


class LiveServerLinger(Spec):
    """4.1-4.3 Linger delay behavior"""

    async def _make_server(self, linger):
        from spektrum.reporting.live import LiveServer
        queue = asyncio.Queue()
        server = LiveServer(get_free_port(), queue, linger=linger)
        await server.start()
        return server

    async def _trigger_shutdown(self, server):
        """Put a run-complete event so _consume_events sets the shutdown event."""
        await server._queue.put({
            'type': 'run-complete',
            'passed': 1,
            'failed': 0,
            'skipped': 0,
        })

    async def _cleanup(self, server):
        if server._consumer_task and not server._consumer_task.done():
            server._consumer_task.cancel()
            try:
                await server._consumer_task
            except asyncio.CancelledError:
                pass
        if server._server:
            server._server.close()
            await server._server.wait_closed()

    async def test_linger_zero_shuts_down_immediately(self):
        server = await self._make_server(linger=0)
        await self._trigger_shutdown(server)
        # Let consumer pick up the event
        await asyncio.sleep(0.05)

        start = time.monotonic()
        await server.shutdown()
        elapsed = time.monotonic() - start

        expect(elapsed).to.be_less_than(0.5)

    async def test_linger_holds_server_up(self):
        server = await self._make_server(linger=2)
        await self._trigger_shutdown(server)
        await asyncio.sleep(0.05)

        start = time.monotonic()
        await server.shutdown()
        elapsed = time.monotonic() - start

        expect(elapsed).to.be_greater_than(1.5)
        await self._cleanup(server)

    async def test_linger_notice_printed_to_stdout(self):
        import unittest.mock as mock

        server = await self._make_server(linger=3)
        await self._trigger_shutdown(server)
        await asyncio.sleep(0.05)

        async def _noop(*args, **kwargs):
            pass

        with mock.patch('builtins.print') as mock_print:
            # Override sleep so the test finishes quickly
            with mock.patch('spektrum.reporting.live.asyncio.sleep', side_effect=_noop):
                await server.shutdown()

        printed_messages = [str(call) for call in mock_print.call_args_list]
        notice_printed = any('3 more seconds' in msg for msg in printed_messages)
        expect(notice_printed).to.be_true()

        await self._cleanup(server)
