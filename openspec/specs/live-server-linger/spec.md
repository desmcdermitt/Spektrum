# live-server-linger Specification

## Purpose
Keep the live server accepting connections for a bounded period after a run finishes,
so the results page is still reachable once the run itself would have exited.

## Requirements

### Requirement: Live server stays up after run completes
The live progress server SHALL remain available for a configurable number of seconds after the `run-complete` event is broadcast, allowing developers time to load the results page in a browser.

#### Scenario: Server stays up for linger duration
- **WHEN** all tests complete and `--live-linger N` is set (N > 0)
- **THEN** the live server continues accepting HTTP connections for at least N seconds before shutting down

#### Scenario: Linger message printed to stdout
- **WHEN** the live server enters its linger period
- **THEN** a message is printed to stdout indicating how long the server will remain up (e.g., `Live view available for 5 more seconds...`)

#### Scenario: Zero linger disables delay
- **WHEN** `--live-linger 0` is passed
- **THEN** the server shuts down immediately after broadcasting `run-complete`, matching pre-linger behavior

### Requirement: CLI exposes linger flag
The Spektrum CLI SHALL accept a `--live-linger` integer flag that specifies the post-run delay in seconds with a default of 5.

#### Scenario: Default linger applied when flag omitted
- **WHEN** `--live` is passed without `--live-linger`
- **THEN** the server lingers for 5 seconds after the run completes

#### Scenario: Custom linger value respected
- **WHEN** `--live --live-linger 30` is passed
- **THEN** the server lingers for 30 seconds after the run completes

#### Scenario: Linger flag ignored without --live
- **WHEN** `--live-linger N` is passed without `--live`
- **THEN** no live server is started and the flag has no effect
