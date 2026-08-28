# test-runner-lifecycle Specification

## Purpose
How `SpektrumRunner` reports its own progress to the live event queue — accepting the
queue, announcing each discovered spec before execution, and signalling completion.

## Requirements

### Requirement: Runner accepts a live-event queue
When a live event queue is provided to `SpektrumRunner`, the runner SHALL publish lifecycle events to it without affecting normal execution behavior.

#### Scenario: No queue provided — no change in behavior
- **WHEN** `SpektrumRunner` is used without `--live`
- **THEN** no events SHALL be published and test execution SHALL behave identically to before

#### Scenario: Queue provided — case-started event emitted
- **WHEN** a live queue is configured and a test case begins execution
- **THEN** the runner SHALL put a `case-started` event on the queue containing the spec name, case name, and timestamp

#### Scenario: Queue provided — case-finished event emitted
- **WHEN** a live queue is configured and a test case finishes execution
- **THEN** the runner SHALL put a `case-finished` event on the queue containing spec name, case name, status (passed/failed/skipped), duration, and result details (failure message + traceback if failed; skip reason if skipped; expect results if passed)

### Requirement: Runner emits a spec-discovered event for each spec before execution
When a live queue is provided, the runner SHALL publish a `spec-discovered` event for every spec and case at discovery time, before any test runs.

#### Scenario: All specs and cases announced before first test
- **WHEN** a live queue is configured and discovery completes
- **THEN** the runner SHALL emit one `spec-discovered` event per spec containing the spec's full case list, before any `case-started` event is emitted

### Requirement: Runner emits a run-complete event after all tests finish
When a live queue is provided, the runner SHALL publish a `run-complete` event after all specs and cases have finished executing.

#### Scenario: Run-complete event contains summary counts
- **WHEN** all tests finish
- **THEN** the runner SHALL emit a `run-complete` event with totals: passed count, failed count, skipped count, and total duration
