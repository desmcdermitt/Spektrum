## Context

Spektrum is an async Python BDD test runner. Test execution flows through `SpektrumRunner.run()` → `execute_spec()` → individual test method invocations. Results are collected by `ReportManager` and rendered after all tests complete. There is no mechanism to observe test state mid-run.

The live progress view adds an optional HTTP server that runs alongside the test runner, receiving events as cases start and finish, and broadcasting them to a browser client over SSE. The browser renders the full spec/case tree with live status updates.

## Goals / Non-Goals

**Goals:**
- Opt-in live view with zero impact on existing test execution when not enabled
- Real-time push of case state changes (started, passed, failed, skipped) to the browser
- Mirror the final pretty-print hierarchy: spec → case, collapsible per case
- No external runtime dependencies beyond what Spektrum already uses

**Non-Goals:**
- Replacing the existing pretty/xunit/testrail reporters
- Persistent storage of test run history
- Authentication or multi-user access to the live page
- Mobile-optimized layout

## Decisions

### 1. SSE over WebSocket

**Decision:** Use Server-Sent Events (SSE) rather than WebSockets for pushing updates to the browser.

**Rationale:** The data flow is strictly one-directional: server → browser. SSE is simpler to implement (plain HTTP), works through proxies without special handling, and requires no client-side library. The `httpx` library already present as a dependency handles HTTP; a minimal `http.server` or `asyncio`-based server suffices.

**Alternative considered:** WebSockets — adds bidirectional complexity with no benefit here.

### 2. Embedded asyncio HTTP server (`aiohttp`-free)

**Decision:** Implement the server using Python's `asyncio` streams or `http.server` in a background thread, avoiding new external dependencies.

**Rationale:** Spektrum is a lightweight framework. Adding `aiohttp` or `fastapi` would bloat the install. A minimal asyncio TCP server serving SSE and static HTML is ~100 lines and has no new install requirements.

**Alternative considered:** `aiohttp` — clean API but adds a heavy dependency; `flask` in thread — simpler but blocks GIL.

### 3. Event bus via asyncio.Queue

**Decision:** `SpektrumRunner` publishes events to an `asyncio.Queue`; `LiveServer` reads from the queue and broadcasts to connected SSE clients.

**Rationale:** Decouples the runner from the server — the runner just puts events on a queue without knowing whether any clients are connected. This keeps the runner changes minimal and testable in isolation.

### 4. Inline HTML/JS static asset

**Decision:** The progress page HTML/CSS/JS is a single inline string embedded in `live.py`, not a file in a `static/` directory.

**Rationale:** Keeps the package installable as a pure Python wheel without needing `package_data` configuration. The page is small enough to inline (~200 lines of HTML+JS).

**Alternative considered:** `static/` directory with `package_data` — cleaner separation but adds packaging complexity.

### 5. CLI flag `--live` with optional port

**Decision:** Add `--live` flag (boolean) and `--live-port` (default 7777) to the docopt CLI.

**Rationale:** Opt-in with a sensible default port. Separating the two flags avoids overloading `--live 7777` syntax.

## Risks / Trade-offs

- **Port conflict** → Mitigation: Graceful error message if port is in use; suggest `--live-port` to override.
- **SSE client falls behind on very large/fast test runs** → Mitigation: Queue is unbounded; late-joining browser clients receive a full state snapshot on connection so they catch up immediately.
- **Asyncio event loop sharing** → The live server runs in the same event loop as the test runner. Care needed to not block the loop. All server I/O must be non-blocking async. Mitigation: tested with `asyncio.sleep(0)` yield points.
- **Browser JS complexity** → The tree rendering and collapsible dropdowns are plain vanilla JS with no framework. This is sufficient for a utility tool but limits future extensibility.

## Migration Plan

- No migration needed — feature is entirely additive behind the `--live` flag.
- Existing users see no change unless they pass `--live`.
- Rollback: remove the flag; `live.py` is isolated with no imports from it in the existing code path.
