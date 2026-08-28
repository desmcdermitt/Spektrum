## Why

Currently, the live view only shows assertions when a test case finishes — the assertions panel stays empty while a test is running, even if assertions have already been evaluated. This makes the live view less useful for long-running tests where you want to see progress in real time.

## What Changes

- Assertions are streamed to the live view as each one completes, not just after the test case finishes.
- The live view updates the assertions list incrementally while a case is in `running` state.
- No breaking changes to the existing public API (`expect`, `require`, `Spec`, CLI).

## Capabilities

### New Capabilities

- `live-assertion-streaming`: Push each assertion result to the live server's event queue as it is evaluated, so the browser receives and displays assertion results while the test case is still running.

### Modified Capabilities

_(none — no existing spec-level requirements are changing)_

## Impact

- `spektrum/expect.py`: `Expectation._verify_condition` (or a hook after each comparison) must emit an event to the live event queue when one is active.
- `spektrum/runner.py`: Before executing a test case, expose the event queue, `spec_id`, and `case_name` to the expect layer (via `contextvars`).
- `spektrum/reporting/live.py`: Handle a new `assertion-added` internal event type; update in-memory case state and broadcast a `case-update` SSE event with the current assertions payload while the case is still `running`.
- No changes to the CLI, reporters, or external integrations.
