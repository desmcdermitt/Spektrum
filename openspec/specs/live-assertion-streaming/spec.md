# live-assertion-streaming Specification

## Purpose
Stream each assertion result to the live view as it is evaluated, so a long-running
case shows its progress instead of an empty panel until it finishes.

## Requirements

### Requirement: Assertions stream to the live view as they are evaluated
While a test case is running, the live view SHALL display each assertion result as soon as it is evaluated, without waiting for the case to finish.

#### Scenario: Assertion appears while case is running
- **WHEN** a running test case evaluates `expect(x).to.equal(y)`
- **THEN** the live view SHALL show that assertion (with pass/fail state) in the case's detail panel before the case finishes

#### Scenario: Multiple assertions stream incrementally
- **WHEN** a running test case evaluates several assertions in sequence
- **THEN** the live view SHALL display each assertion in the order it was evaluated, appending to the list as they arrive

#### Scenario: Failed assertion streams immediately
- **WHEN** a running test case evaluates an assertion that fails
- **THEN** the live view SHALL show the failed assertion (red) immediately, while the case badge still shows `running`

#### Scenario: Require assertion streams before halting
- **WHEN** a running test case evaluates `require(x).to.be_true()` and the condition is false
- **THEN** the live view SHALL display the failed require assertion before the case transitions to `failed`

### Requirement: Live streaming is inactive when the live server is not running
When Spektrum is run without `--live`, assertion evaluation SHALL NOT attempt to emit streaming events.

#### Scenario: No event queue present
- **WHEN** a test is run without `--live`
- **THEN** assertion evaluation SHALL complete normally with no side effects from the streaming code path

### Requirement: Browser shows in-progress assertions for a running case
The live view HTML page SHALL update the assertions list for a case that is currently in `running` state when new assertion data arrives.

#### Scenario: Assertions panel updates live
- **WHEN** the browser receives a `case-update` SSE event for a `running` case that includes assertion data
- **THEN** the assertions section in the case detail panel SHALL be re-rendered with the latest assertion list

#### Scenario: Final case-update replaces running assertions
- **WHEN** the browser receives a `case-update` SSE event with a terminal status (`passed`, `failed`, `skipped`)
- **THEN** the full assertions list and final status SHALL replace the in-progress view
