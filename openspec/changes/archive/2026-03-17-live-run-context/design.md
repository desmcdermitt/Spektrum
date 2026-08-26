## Context

`SpektrumRunner.run()` starts the live server (`live_server.start()`) before calling `PikeManager` for discovery. However, nothing is written to the event queue until `run_all()` executes — which happens after all discovery, instantiation, metadata filtering, and `before_all` setup. A connecting browser receives only an empty snapshot.

The `search_paths` and `module_name` arguments to `run()` are exactly the user-supplied values that describe what is being run. They are available the moment the server starts.

## Goals / Non-Goals

**Goals:**
- Display search path and module filter in the browser as soon as a client connects, before any spec is discovered.
- Keep the change minimal: one new event type, one new state field, one header UI update.

**Non-Goals:**
- Displaying metadata filters, concurrency, or other run parameters.
- Changing when specs are discovered or when `before_all` runs.
- Persisting run context across server restarts.

## Decisions

### Decision 1: Use a new `run-started` event emitted synchronously after server start

A `run-started` event is placed on the queue immediately after `live_server.start()` returns, before entering `PikeManager`. The event carries `{ search_path, module_name }`.

**Why:** The queue already handles ordering — `_consume_events` processes events in arrival order. Placing `run-started` first guarantees it is in the server's state before any `spec-discovered` event arrives. No new coordination mechanism is needed.

**Alternatives considered:**
- Passing run context directly to `LiveServer.__init__` — avoids the queue but couples the server constructor to runner arguments.
- Sending run context as part of the snapshot only — works, but then the server needs the info at construction time, which has the same coupling problem.

### Decision 2: Store run context in `LiveServer._run_context` and include it in every snapshot

`_consume_events` stores the `run-started` payload in `self._run_context`. `_build_snapshot` includes it as a `run_context` field in the snapshot dict.

New clients always receive a snapshot as their first event, so they will always see the run context immediately regardless of when they connect (before or after discovery).

### Decision 3: Render run context in the HTML header subtitle

The existing header has space for a subtitle below the "Spektrum Live" title. When `snapshot.run_context` is present the JS sets a subtitle element to the search path (and appends the module filter if set). No new SSE event type is needed on the browser side — the snapshot already carries the info.

## Risks / Trade-offs

- **`put_nowait` before consumer starts**: The consumer task (`_consume_events`) is started by `live_server.start()`. There is a small window where `put_nowait` is called before the consumer coroutine picks up the event. Because `asyncio.Queue` is unbounded, this is safe — the event waits in the queue until consumed.
  → No mitigation needed.

- **Minimal UI real estate**: The header already has a connection-status element on the right. The subtitle goes on the left below the title, keeping the existing layout intact.

## Migration Plan

No migration required. The change is purely additive:
- Non-live runs are unaffected.
- Existing clients that do not parse `run_context` in the snapshot will ignore the new field.
