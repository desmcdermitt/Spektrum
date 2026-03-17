## 1. Context Variable Infrastructure

- [x] 1.1 Add a `ContextVar` named `_LIVE_CTX` to `spektrum/expect.py` that holds `{ queue, spec_id, case_name }` or `None`

## 2. Runner — Set Context Before Test Execution

- [x] 2.1 In `execute_test_case` (`runner.py`), set `_LIVE_CTX` to `{ queue: event_queue, spec_id: spec._id, case_name: case.__name__ }` before calling `execute_method` for the test, and reset it after

## 3. Expect — Emit Assertion Events

- [x] 3.1 In `Expectation._verify_condition` (`expect.py`), after `self.success` is set, read `_LIVE_CTX`; if present, call `queue.put_nowait` with a new `assertion-added` event containing `spec_id`, `case_name`, and the assertion's `as_dict` payload

## 4. Live Server — Handle `assertion-added` Events

- [x] 4.1 In `LiveServer._consume_events` (`reporting/live.py`), add a handler for `assertion-added` that appends the assertion to the in-memory case state under `details.expects`
- [x] 4.2 After updating state, broadcast a `case-update` SSE event with `status: "running"` and the current `details` payload (reusing the existing `_broadcast` helper)

## 5. Tests

- [x] 5.1 Add a test in `tests/live/` (or extend existing live tests) that verifies an `assertion-added` event is emitted to the queue when an assertion is evaluated during a live run
- [x] 5.2 Add a test verifying that no event is emitted when `_LIVE_CTX` is not set (non-live run)
