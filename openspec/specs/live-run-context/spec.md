# live-run-context Specification

## Purpose
Tell a connecting client what is being run — search path and module filter — from the
first frame, by emitting run context before discovery begins and carrying it in every
snapshot.

## Requirements

### Requirement: Runner emits run context immediately after server start
After the live server starts, the runner SHALL emit a `run-started` event to the event queue containing the search path and optional module filter before any discovery or spec instantiation begins.

#### Scenario: run-started event emitted with search path
- **WHEN** the runner starts with `--live` and a search path
- **THEN** a `run-started` event with `search_path` set SHALL be the first event in the queue

#### Scenario: run-started event includes module filter when set
- **WHEN** the runner starts with `--live` and a `-p module_name` filter
- **THEN** the `run-started` event SHALL include `module_name` set to that filter value

#### Scenario: run-started event emitted before spec-discovered
- **WHEN** the runner starts with `--live`
- **THEN** the `run-started` event SHALL appear in the queue before any `spec-discovered` event

### Requirement: Live server stores run context and includes it in snapshots
The live server SHALL store the run context from the `run-started` event and include it in every snapshot sent to connecting clients.

#### Scenario: Snapshot includes run context after run-started received
- **WHEN** a client connects after the `run-started` event has been processed
- **THEN** the snapshot payload SHALL contain a `run_context` field with `search_path` and `module_name`

#### Scenario: Snapshot run_context is null before run-started received
- **WHEN** a client connects before the `run-started` event has been processed
- **THEN** the snapshot payload SHALL contain `run_context: null`

### Requirement: Live view displays run context in the header immediately on connect
The live view HTML page SHALL display the search path (and module filter if present) in the header as soon as the snapshot is received, before any spec rows are rendered.

#### Scenario: Search path shown in header
- **WHEN** the browser receives a snapshot with `run_context.search_path` set
- **THEN** the header SHALL display the search path value

#### Scenario: Module filter shown alongside search path when present
- **WHEN** the browser receives a snapshot with both `run_context.search_path` and `run_context.module_name` set
- **THEN** the header SHALL display both the search path and the module filter

#### Scenario: Header unchanged when run context absent
- **WHEN** the browser receives a snapshot with `run_context: null`
- **THEN** the header subtitle element SHALL remain empty
