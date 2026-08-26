## Context

The Spektrum live view (`--live`) runs an HTTP server that streams Server-Sent Events (SSE) to a browser. Currently the event flow is:

1. `spec-discovered` — all cases registered as "pending" at startup
2. `case-started` — case turns "running"
3. `case-finished` — case turns passed/failed/skipped, assertions shown

This means the assertions panel is always empty until the case completes. For long-running tests this can be many seconds with no visible progress.

The `expect()` / `require()` functions in `expect.py` evaluate assertions synchronously during test execution. After each comparison, the result (pass/fail, label) is fully known and could be streamed immediately. The barrier is that `expect.py` has no reference to the event queue — it lives in `runner.py`.

## Goals / Non-Goals

**Goals:**
- Stream each assertion result to the live view as it is evaluated, while the case is still `running`.
- Keep changes minimal and contained to `expect.py`, `runner.py`, and `live.py` (+ HTML).
- No changes to the public API (`expect`, `require`, `Spec`, CLI flags).

**Non-Goals:**
- Live streaming for non-live runs (pretty/xunit reporters are unaffected).
- Streaming `before_each` / `after_each` assertions (only test-method assertions are in scope).
- Persisting assertion history across browser refreshes beyond the existing snapshot mechanism.

## Decisions

### Decision 1: Use `contextvars.ContextVar` to pass the event queue into the expect layer

**Rationale:** `expect.py` already walks the call stack to find the parent `Spec`. Extending that technique to also find the event queue works, but is fragile — it depends on specific frame names (`execute_test_case`). A `ContextVar` is the idiomatic Python mechanism for passing context through an async call chain without threading it explicitly through every function signature.

`runner.py` sets the var in `execute_test_case` (using `token = _LIVE_CTX.set(...)`) before calling `execute_method`, and resets it after (`_LIVE_CTX.reset(token)`). The var carries `{ queue, spec_id, case_name }`.

**Alternatives considered:**
- Attaching `_live_event_queue` to the `Spec` instance — works, but pollutes the Spec with runner internals and can persist beyond a single test case.
- Threading the queue through every function signature — invasive, touches many call sites.

### Decision 2: Emit events from `Expectation._verify_condition`

`_verify_condition` is the single point where `self.success` is set after a comparison. Emitting from here guarantees the event is sent exactly once per assertion, immediately after the result is known, regardless of which comparison method was called (`.equal`, `.be_true`, `.contain`, etc.).

Emission uses `queue.put_nowait(...)` which is safe to call from synchronous code within an async event loop.

**Alternatives considered:**
- Emitting from each comparison method — requires touching every method, easy to miss new ones.
- Emitting from `_add_expect_to_spec` — fires before the comparison result is known (`success` is still `False` at that point).

### Decision 3: Live server converts `assertion-added` into a `case-update` SSE broadcast

Rather than adding a new SSE event type for the browser to handle, the server translates `assertion-added` internal events into the existing `case-update` SSE format (same as `case-finished` but with `status: "running"` and partial `details`). This reuses all existing browser rendering logic with no HTML/JS changes except updating the existing assertions list in-place.

## Risks / Trade-offs

- **High-frequency tests**: A test with hundreds of assertions in a tight loop will put one event per assertion on the queue. The queue and SSE broadcast are both non-blocking (`put_nowait` + `asyncio` writes), so this is unlikely to be a bottleneck in practice, but could produce noisy diffs for fast tests.
  → Mitigation: Acceptable for the initial implementation. A debounce/batch strategy can be added later if needed.

- **`put_nowait` in a sync context**: `_verify_condition` is sync. `put_nowait` raises `QueueFull` if the queue has a `maxsize`. The existing queue is created without a size limit (`asyncio.Queue()`), so this is safe.
  → Mitigation: Document the assumption; ensure the event queue stays unbounded.

- **ContextVar and asyncio task isolation**: Each test case runs as a separate asyncio task via `asyncio.gather`. `ContextVar` values are inherited from the parent context at task creation time but mutations within a task are task-local. Setting and resetting within `execute_test_case` (which runs in the task) is safe.

## Migration Plan

All changes are additive and backward-compatible:
1. Run is unchanged when `--live` is not used (`_LIVE_CTX` will be unset; `_verify_condition` no-ops the event path).
2. No new CLI flags required.
3. No database, schema, or file-format migrations.

## Open Questions

_(none)_
