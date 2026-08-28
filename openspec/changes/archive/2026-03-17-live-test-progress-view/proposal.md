## Why

Spektrum currently only shows test results after all tests complete, giving no visibility into what's happening during a long test run. A live progress view would allow developers to monitor test execution in real-time, see which tests are running, which are pending, and review results as they come in — without waiting for the full suite to finish.

## What Changes

- Add a new HTTP server that serves a live progress page during test execution
- Add a real-time WebSocket (or SSE) feed that pushes test state updates to the browser
- Render the full spec/case hierarchy mirroring the final pretty output, with dynamic status badges
- Each running case shows a "running" indicator; pending cases show "pending"; completed cases show pass/fail in a collapsible dropdown with result details
- New CLI flag `--live` (or `--live-port <port>`) to opt into the live view server

## Capabilities

### New Capabilities
- `live-progress-server`: HTTP server that launches alongside the test runner and serves a live test progress page with real-time updates via SSE or WebSocket
- `progress-page-ui`: Browser-based UI that renders the full spec/case hierarchy with running/pending/complete status and collapsible result dropdowns

### Modified Capabilities
- `test-runner-lifecycle`: Runner emits progress events at case start, case end, and spec completion so the live server can consume and broadcast them

## Impact

- `spektrum/runner.py`: Emit lifecycle events (case started, case finished, spec finished)
- `spektrum/reporting/core.py`: Hook into ReportManager or add a new parallel event bus for live updates
- New module `spektrum/reporting/live.py`: HTTP + SSE/WebSocket server and event broadcaster
- New static assets: HTML/CSS/JS for the progress page (embedded or served from a `static/` directory)
- `spektrum/__main__.py`: New `--live` / `--live-port` CLI flag
- No breaking changes to existing CLI flags or reporter interfaces
