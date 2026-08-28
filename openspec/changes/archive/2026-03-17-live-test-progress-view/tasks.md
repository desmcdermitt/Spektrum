## 1. CLI and Configuration

- [x] 1.1 Add `--live` boolean flag to the docopt CLI in `spektrum/__main__.py`
- [x] 1.2 Add `--live-port` flag (default 7777) to the docopt CLI in `spektrum/__main__.py`
- [x] 1.3 Pass the live flag and port through to `SpektrumRunner` instantiation

## 2. Runner Lifecycle Events

- [x] 2.1 Add an optional `event_queue: asyncio.Queue` parameter to `SpektrumRunner.__init__`
- [x] 2.2 Emit a `spec-discovered` event for each spec with full case list after discovery, before execution begins
- [x] 2.3 Emit a `case-started` event at the start of each test case execution
- [x] 2.4 Emit a `case-finished` event at the end of each test case with status, duration, and result details
- [x] 2.5 Emit a `run-complete` event after all specs finish with pass/fail/skip totals
- [x] 2.6 Verify that when no queue is provided, runner behavior is unchanged

## 3. Live Progress Server

- [x] 3.1 Create `spektrum/reporting/live.py` with `LiveServer` class using asyncio
- [x] 3.2 Implement root `GET /` handler returning the embedded progress page HTML
- [x] 3.3 Implement `GET /events` SSE handler with proper `text/event-stream` headers and keep-alive
- [x] 3.4 Implement SSE client registry — track connected clients and broadcast events to all of them
- [x] 3.5 Implement snapshot logic: on new SSE client connection, emit current accumulated state as a `snapshot` event
- [x] 3.6 Implement the event consumer loop that reads from the runner's `asyncio.Queue` and broadcasts to SSE clients
- [x] 3.7 Implement port-conflict detection with a clear error message and non-zero exit
- [x] 3.8 Implement graceful shutdown: push `run-complete` to connected clients, then close server within 5 seconds

## 4. Progress Page UI (HTML/JS)

- [x] 4.1 Design the inline HTML structure — spec sections, case rows, status badges
- [x] 4.2 Implement CSS: pending/running/passed/failed/skipped badge colors, collapsible dropdown styles
- [x] 4.3 Implement JavaScript `EventSource` connection to `/events` with automatic reconnect
- [x] 4.4 Handle `snapshot` event: render the full spec/case tree from initial state
- [x] 4.5 Handle `case-update` event: update the specific case row's status badge in-place
- [x] 4.6 Implement collapsible dropdown per case: hidden by default, toggled on click
- [x] 4.7 Populate dropdown content: failure message + traceback for failed; skip reason for skipped; expect results for passed
- [x] 4.8 Handle `run-complete` event: display summary banner with pass/fail/skip counts and update page title
- [x] 4.9 Embed the final HTML/CSS/JS as a string constant in `live.py`

## 5. Integration

- [x] 5.1 Wire `LiveServer` startup into `SpektrumRunner.run()` when `event_queue` is set — start server before first test
- [x] 5.2 Wire `LiveServer` shutdown into runner teardown after all tests finish
- [x] 5.3 Print the live URL to stdout when the server starts (e.g., `Live view: http://localhost:7777`)
- [x] 5.4 Ensure the live server runs as an asyncio task in the same event loop as the runner without blocking test execution

## 6. Tests

- [x] 6.1 Add unit tests for runner event emission (mock queue, assert events published)
- [x] 6.2 Add unit tests for `LiveServer` SSE broadcast logic (connect client, emit event, assert received)
- [x] 6.3 Add integration test: run a sample spec with `--live`, connect to `/events`, assert snapshot and case-update events arrive
- [x] 6.4 Add test for port-conflict error path
