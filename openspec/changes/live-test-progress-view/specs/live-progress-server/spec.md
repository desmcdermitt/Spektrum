## ADDED Requirements

### Requirement: Server starts when --live flag is provided
When the `--live` CLI flag is passed, Spektrum SHALL start an HTTP server on the configured port (default 7777) before test execution begins and shut it down after all tests complete.

#### Scenario: Server starts on default port
- **WHEN** `spektrum --live -s tests/` is invoked
- **THEN** an HTTP server SHALL be listening on port 7777 before any test runs

#### Scenario: Server starts on custom port
- **WHEN** `spektrum --live --live-port 9090 -s tests/` is invoked
- **THEN** an HTTP server SHALL be listening on port 9090

#### Scenario: Port conflict produces a clear error
- **WHEN** `--live` is specified and the target port is already in use
- **THEN** Spektrum SHALL print an error message naming the port and exit with a non-zero status code before running any tests

### Requirement: Server serves the live progress page
The HTTP server SHALL serve a self-contained HTML progress page at the root path (`/`).

#### Scenario: Browser requests root path
- **WHEN** a browser sends `GET /`
- **THEN** the server SHALL respond with `200 OK`, `Content-Type: text/html`, and the full progress page HTML

### Requirement: Server provides an SSE event stream
The HTTP server SHALL expose a Server-Sent Events endpoint at `/events` that pushes test state changes to connected browsers.

#### Scenario: Client connects to SSE endpoint
- **WHEN** a browser sends `GET /events` with `Accept: text/event-stream`
- **THEN** the server SHALL respond with `200 OK`, `Content-Type: text/event-stream`, and keep the connection open

#### Scenario: Full state snapshot on connect
- **WHEN** a client connects to `/events` after some tests have already run
- **THEN** the server SHALL immediately emit a `snapshot` event containing the current state of all specs and cases

#### Scenario: Live events pushed as cases change state
- **WHEN** a test case transitions to running, passed, failed, or skipped
- **THEN** the server SHALL push a `case-update` SSE event to all connected clients within 100ms of the transition

### Requirement: Server shuts down cleanly after test run
After all tests complete, the HTTP server SHALL remain available for a short grace period and then shut down, or shut down immediately if no clients are connected.

#### Scenario: Graceful shutdown with no clients
- **WHEN** all tests complete and no SSE clients are connected
- **THEN** the server SHALL shut down immediately and Spektrum SHALL exit normally

#### Scenario: Graceful shutdown with active clients
- **WHEN** all tests complete and one or more SSE clients are connected
- **THEN** the server SHALL push a `run-complete` event and then shut down within 5 seconds
