## Why

When tests run quickly, developers may not have enough time to open the live progress page before the server shuts down after `run-complete`. This makes the live view feature unusable for fast test suites. A configurable post-run delay keeps the server alive long enough for developers to load and review the results.

## What Changes

- Add a `--live-linger` CLI flag (default: 5 seconds) that controls how long the live server stays up after all tests complete
- `LiveServer.shutdown()` waits the configured linger duration before closing, printing a countdown or notice to stdout
- Downstream harnesses that shell out to Spektrum gain the corresponding flag and pass it
  through (out of scope for this repository)

## Capabilities

### New Capabilities

- `live-server-linger`: Post-run delay that holds the live progress server open for a configurable number of seconds after the test run completes, so developers can load and inspect the results page

### Modified Capabilities

<!-- none -->

## Impact

- `spektrum/__main__.py`: new `--live-linger` flag
- `spektrum/runner.py`: passes linger value to `LiveServer`
- `spektrum/reporting/live.py`: `LiveServer.__init__` and `shutdown()` updated to accept and apply linger delay
- Downstream harness CLI (separate repository): new `--live-linger` flag passed through to
  the Spektrum argv
- `tests/live/test_live.py`: tests for linger behavior (server stays up, then closes)
