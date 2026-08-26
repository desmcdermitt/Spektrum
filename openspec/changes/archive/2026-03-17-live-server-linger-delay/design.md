## Context

The live progress server (`LiveServer` in `spektrum/reporting/live.py`) currently shuts down immediately after the `run-complete` event is broadcast to SSE clients. For fast test suites (under a few seconds), the server may be gone before a developer can open a browser and navigate to `http://localhost:7777`. The linger delay solves this by holding the server open for a configurable number of seconds after `run-complete`.

## Goals / Non-Goals

**Goals:**
- Add a `--live-linger` integer flag (seconds, default 5) to the Spektrum CLI
- `LiveServer.shutdown()` sleeps for the linger duration before closing the TCP server
- Print a notice to stdout indicating how long the server will remain up
- Downstream harnesses forward `--live-linger` into the Spektrum argv (their own change)

**Non-Goals:**
- Dynamic linger (e.g., "wait until a client connects") — keep it simple and time-based
- Per-client session management or reconnect detection

## Decisions

**Where the delay lives — `LiveServer.shutdown()` vs. `runner.run()`**

The delay belongs inside `LiveServer.shutdown()`. The runner already `await`s `live_server.shutdown()` inside its `run_all()` coroutine, so a `asyncio.sleep()` there naturally holds the event loop open without any structural changes to the runner. Putting the delay in the runner would couple the runner to a concern that belongs to the server.

**Default linger: 5 seconds**

Five seconds is enough time to open a browser tab and type a localhost URL. It's not so long that it feels like the process is hanging. Users who need longer can override with `--live-linger 30`.

**`--live-linger 0` disables linger entirely**

Zero is the natural "no delay" value and backward-compatible. Current behavior (immediate shutdown) is preserved when `--live-linger 0` is passed or when `--live` is not used at all.

**Countdown message vs. single notice**

A single stdout message ("Live view staying up for N seconds...") is sufficient. A per-second countdown adds noise and requires a separate task; the user can see the browser loaded or not.

## Risks / Trade-offs

- [If the event loop exits before linger completes] → The `asyncio.sleep` in `shutdown()` is awaited within `run_all()`, which is itself inside `loop.run_until_complete()`, so the loop stays alive for the full duration.
- [Linger adds wall-clock time to CI runs where `--live` is used] → Acceptable; `--live` is inherently a developer-facing flag, not typically used in CI. If CI does use it, passing `--live-linger 0` restores immediate shutdown.
