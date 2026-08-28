## Why

When the live view server starts, the browser shows a blank page until spec discovery completes — there is no indication of what is being run or that anything is happening. For large suites, discovery and instantiation can take several seconds, leaving the user staring at an empty screen with no context.

## What Changes

- A `run-started` event is emitted to the event queue immediately after the live server starts, carrying the search path and optional module filter that were passed to the runner.
- The live server stores this run context and includes it in every snapshot sent to new clients.
- The live view HTML displays the search path (and module filter if set) in the header area as soon as the browser connects, before any specs are discovered.

## Capabilities

### New Capabilities

- `live-run-context`: Capture and display the run's search path and module filter in the live view header from the moment the server starts.

### Modified Capabilities

_(none)_

## Impact

- `spektrum/runner.py`: Emit a `run-started` event immediately after `live_server.start()`.
- `spektrum/reporting/live.py`: Handle `run-started` — store run context in server state; include it in snapshot payloads.
- `spektrum/reporting/live.py` (HTML): Render search path and module filter in the page header when present.
