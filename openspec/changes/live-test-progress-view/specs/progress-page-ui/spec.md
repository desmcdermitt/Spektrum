## ADDED Requirements

### Requirement: Page displays the full spec/case hierarchy
The progress page SHALL render all discovered specs and their cases in a tree structure that mirrors the final pretty-print output, grouped by spec class name.

#### Scenario: Hierarchy shown on page load
- **WHEN** the page is loaded and a snapshot event has been received
- **THEN** each spec SHALL be shown as a top-level section with its cases listed beneath it

#### Scenario: Nested specs shown at correct depth
- **WHEN** a spec contains nested child specs
- **THEN** child specs SHALL be indented under their parent spec

### Requirement: Running cases show a "running" status indicator
Any test case currently executing SHALL be visually marked with a "running" status badge.

#### Scenario: Case transitions to running
- **WHEN** a `case-update` event with status `running` is received for a case
- **THEN** that case SHALL display a "running" badge (e.g., spinner or distinct color) within one render cycle

### Requirement: Pending cases show a "pending" status indicator
Any test case that has not yet started SHALL be visually marked as "pending".

#### Scenario: Initial page render shows pending cases
- **WHEN** the page first renders cases from the snapshot
- **THEN** all cases that have not yet started SHALL display a "pending" badge

#### Scenario: Case remains pending until it starts
- **WHEN** other cases in the same spec are running or complete
- **THEN** cases that have not yet started SHALL continue to show "pending"

### Requirement: Completed cases show result in a collapsible dropdown
Each completed case (passed, failed, or skipped) SHALL display its result status and offer a collapsible section containing result details.

#### Scenario: Passed case shows pass badge
- **WHEN** a `case-update` event with status `passed` is received
- **THEN** that case SHALL display a "passed" badge (e.g., green)

#### Scenario: Failed case shows fail badge and expandable details
- **WHEN** a `case-update` event with status `failed` is received
- **THEN** that case SHALL display a "failed" badge (e.g., red) and a collapsed dropdown
- **THEN** expanding the dropdown SHALL reveal the failure message and traceback

#### Scenario: Skipped case shows skip badge
- **WHEN** a `case-update` event with status `skipped` is received
- **THEN** that case SHALL display a "skipped" badge and the skip reason in the collapsed dropdown

#### Scenario: Passed case dropdown shows expect results
- **WHEN** a passed case's dropdown is expanded
- **THEN** it SHALL show the list of `expect()` assertion results for that case

### Requirement: Page reconnects automatically if the SSE stream drops
If the SSE connection to the server is lost, the page SHALL attempt to reconnect automatically.

#### Scenario: Reconnection after disconnect
- **WHEN** the SSE connection is lost (network hiccup or server restart)
- **THEN** the browser SHALL attempt to reconnect within 3 seconds using the browser's built-in EventSource retry

### Requirement: Page shows a completion banner when all tests finish
When a `run-complete` event is received, the page SHALL display a summary banner with total pass/fail/skip counts.

#### Scenario: Run complete banner appears
- **WHEN** a `run-complete` SSE event is received
- **THEN** the page SHALL display a banner with the counts of passed, failed, and skipped cases
- **THEN** the page title SHALL update to reflect the final result (e.g., "✓ All passed" or "✗ 3 failed")
