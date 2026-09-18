## Purpose
Make spec-driven development observable on every pull request: define the two ways a pull
request can satisfy the spec-first rule, what counts as a spec file, which conditions turn the
process check red, over which diff the verdict is taken, and why a red gate reports rather
than blocks.

## ADDED Requirements

### Requirement: Invalid OpenSpec artifacts fail the build
The process check SHALL run `openspec validate --all --strict` on every pull request and SHALL
fail when that command exits non-zero. A malformed spec or change document is a broken
artifact, not an untidy one: it is invisible to `openspec list`, it cannot be archived, and it
silently stops describing the behaviour it claims to describe. This failure SHALL have no
exemptions and SHALL NOT be waived by an exception line — a declared exception excuses the
absence of a spec, never a corrupt one.

#### Scenario: Every artifact valid
- **WHEN** a pull request is opened and `openspec validate --all --strict` exits 0
- **THEN** the validation job SHALL pass

#### Scenario: A malformed artifact in the diff
- **WHEN** a pull request adds or edits a file under `openspec/` such that
  `openspec validate --all --strict` exits non-zero
- **THEN** the validation job SHALL fail
- **AND** the failure SHALL name the offending spec or change

#### Scenario: An exception line does not waive validation
- **WHEN** a pull request declares an `sdd-exception:` line and also contains an artifact that
  fails strict validation
- **THEN** the validation job SHALL still fail

#### Scenario: A pre-existing artifact defect on a diff that does not touch openspec/
- **WHEN** an artifact already on the base branch fails strict validation and the pull request
  changes no file under `openspec/`
- **THEN** the validation job SHALL still fail, because validation is evaluated over the whole
  tree rather than over the diff

#### Scenario: Strict mode is not relaxed
- **WHEN** the validation job is configured
- **THEN** it SHALL pass `--strict`, so that a requirement with no scenario or a purpose too
  brief to be useful fails rather than passing silently

### Requirement: Every pull request either carries a spec file or declares an exception
A pull request SHALL satisfy the spec-first rule in exactly one of two ways:

1. its `base..head` diff adds or modifies at least one **spec file**, or
2. its description contains a line matching `sdd-exception: (.+)`, whose captured text is a
   stated reason.

A spec file SHALL mean a `spec.md` under `openspec/changes/<change>/specs/` (a requirement
delta) or under `openspec/specs/` (the agreed baseline). A `proposal.md`, `design.md`,
`tasks.md` or `.openspec.yaml` on its own SHALL NOT satisfy condition 1: a proposal states
motivation and a spec states the contract, and accepting the former would let a pull request
present as spec-first while shipping no requirement at all — which is the gap this gate exists
to close.

If neither condition holds, the change-document job SHALL fail. There SHALL be no path-based
exemption list: the obligation applies to every pull request regardless of what it touches,
because the exception line already provides the relief an exemption list was reaching for, and
does so with a reason attached. A rule with no carve-outs is also a rule nobody has to look up,
and it is the same rule in every repository that adopts it, whatever that repository's source
layout happens to be.

Including the baseline path in the definition means an archive lands cleanly: `openspec
archive` writes `openspec/specs/`, so such a pull request carries a spec file by construction
rather than needing to be waived.

#### Scenario: The diff carries a requirement delta
- **WHEN** a pull request adds or modifies a `spec.md` under `openspec/changes/<change>/specs/`
- **THEN** the change-document job SHALL pass without needing an exception

#### Scenario: The diff archives a change into the baseline
- **WHEN** a pull request adds or modifies a `spec.md` under `openspec/specs/`
- **THEN** the change-document job SHALL pass without needing an exception

#### Scenario: Source change with a requirement delta
- **WHEN** a pull request modifies a file under `spektrum/` and adds a `spec.md` under
  `openspec/changes/<change>/specs/`
- **THEN** the change-document job SHALL pass

#### Scenario: A proposal arrives before its spec deltas
- **WHEN** a pull request adds only `proposal.md`, `design.md` or `tasks.md` and no spec file
- **THEN** the change-document job SHALL require an exception line naming the stage, such as
  `sdd-exception: proposal stage, spec deltas follow`
- **AND** the record SHALL therefore state which stage the work is at rather than passing
  silently

#### Scenario: Neither condition is met
- **WHEN** a pull request's diff contains no spec file
- **AND** its description contains no `sdd-exception:` line
- **THEN** the change-document job SHALL fail
- **AND** its output SHALL state both ways to satisfy the rule, and how to re-run the check
  after editing the description

#### Scenario: A documentation-only pull request
- **WHEN** a pull request changes only `README.rst`, `AGENTS.md` and files under `docs/`, and
  contains no spec file
- **THEN** the change-document job SHALL require an exception line, the same as any other
  pull request

#### Scenario: Build and packaging files carry the same obligation
- **WHEN** a pull request changes `setup.py`, `tox.ini` or a requirements file, contains no
  spec file and declares no exception
- **THEN** the change-document job SHALL fail

#### Scenario: A path nobody anticipated
- **WHEN** a pull request adds a file in a top-level directory that did not exist when this
  rule was written
- **THEN** the rule SHALL apply unchanged, because it is not expressed in terms of paths

#### Scenario: A deleted spec file does not satisfy the rule
- **WHEN** a pull request's only change to a spec file is the deletion of an existing one, and
  it declares no exception
- **THEN** the change-document job SHALL fail, because removing a spec is not supplying one

### Requirement: A declared exception captures a reason and is echoed into the job log
The exception SHALL be recognised only as a line matching `sdd-exception: (.+)` in the pull
request's description, read from `github.event.pull_request.body`, and the captured text SHALL
be non-empty. A bare marker, a label or an empty value SHALL NOT satisfy it.

The description is the right home for it rather than a label or a commit trailer: applying a
label is one click and carries no reason, while captured text forces the author to write the
justification in prose, rendered where a reviewer is already reading. **The job SHALL echo the
captured reason into its own output**, so that a waived pull request says why in its build log
and not only in a field that can be edited afterwards.

#### Scenario: An exception with a stated reason
- **WHEN** the description contains `sdd-exception: dependency bump, no behaviour change`
- **THEN** the change-document job SHALL pass
- **AND** the job output SHALL record the captured reason

#### Scenario: An exception with no reason
- **WHEN** the description contains `sdd-exception:` followed by nothing or only whitespace
- **THEN** the change-document job SHALL fail, because the rule requires a stated reason rather
  than a marker

#### Scenario: A label is not an exception
- **WHEN** a pull request carries a label intended to excuse the missing spec, and its
  description contains no `sdd-exception:` line
- **THEN** the change-document job SHALL fail, because a label records no reason

#### Scenario: The description is edited after the run
- **WHEN** an author adds the exception line after the change-document job has already failed
- **THEN** the verdict SHALL be unchanged until the check is re-run
- **AND** the original failure message SHALL already have told them to re-run it

### Requirement: The verdict is taken over the pull request's base..head diff
Both jobs SHALL evaluate the pull request as a single unit, comparing the base of the pull
request against its head. Neither job SHALL evaluate commits individually. A per-commit rule
would fail any branch that separates its spec commit from its implementation commit, which is
the sequence `openspec/project.md` asks for, and would be defeated by the squash that happens
before review.

#### Scenario: Spec commit and implementation commit in one pull request
- **WHEN** a pull request contains one commit that adds a spec file and a later commit that
  modifies `spektrum/`
- **THEN** the change-document job SHALL pass, because the requirement is satisfied by the
  combined diff

#### Scenario: A single squashed commit
- **WHEN** a pull request contains one commit touching both a spec file and `spektrum/`
- **THEN** the change-document job SHALL pass, giving the same verdict as the multi-commit form
  of the same content

#### Scenario: Full history is available to the check
- **WHEN** the repository is checked out for either job
- **THEN** the checkout SHALL use `fetch-depth: 0`, so the base and head commits of the pull
  request can be diffed directly rather than from a shallow clone that cannot reach the base

### Requirement: The gate reports failure without blocking the merge
A failing process check SHALL be visible on the pull request and SHALL NOT prevent it from
being merged. This change SHALL NOT register either job as a required status check and SHALL
NOT alter any branch-protection setting. Responsibility for merging over a red gate rests with
whoever merges, and the failed run is the record of that decision.

This is deliberately weaker than the exception mechanism is strong: because a pull request can
always state an exception, a red gate means the author neither wrote a spec nor was willing to
say why — which is worth seeing, and still not worth blocking on.

#### Scenario: Merging over a red gate
- **WHEN** the change-document job has failed on a pull request
- **THEN** the pull request SHALL remain mergeable, and the failed run SHALL remain visible on
  it as the record of the decision

#### Scenario: No branch-protection change accompanies the gate
- **WHEN** this capability is implemented
- **THEN** no required-status-check or branch-protection setting on the repository SHALL be
  added or modified

#### Scenario: A red process check is distinguishable from a red test run
- **WHEN** a contributor looks at the checks on a pull request
- **THEN** the process check's name SHALL identify it as a spec-driven-development check, so it
  is not mistaken for the lane that runs tests, lint and the release deploy

### Requirement: The OpenSpec CLI is installed from the scoped package
The process check SHALL install the CLI as `@fission-ai/openspec` pinned to `^1.12.0`. The
unscoped `openspec` package on npm is a different package by a different author and SHALL NOT
be used; installing it produces a CLI that does not implement this contract.

#### Scenario: The scoped package is installed
- **WHEN** the validation job installs its dependency
- **THEN** it SHALL install `@fission-ai/openspec@^1.12.0`

#### Scenario: The unscoped package is rejected
- **WHEN** a pull request changes the process check to install the unscoped `openspec` package
- **THEN** that configuration SHALL be treated as incorrect in review, because it does not
  install this CLI

#### Scenario: The pin permits patch and minor upgrades only
- **WHEN** a new 1.x release of the CLI is published
- **THEN** the check SHALL pick it up without a configuration change, while a 2.x release SHALL
  require the pin to be raised deliberately

### Requirement: The gate runs on pull requests from forks with no privileged access
Both jobs SHALL complete using only a read-only token and no repository secrets, so that a pull
request opened from a personal fork is checked identically to one opened from a branch on the
canonical repository.

#### Scenario: Pull request from a personal fork
- **WHEN** a pull request is opened from a fork, where the automatically provided token is
  read-only and secrets are unavailable
- **THEN** both jobs SHALL run and produce the same verdict they would for a branch on the
  canonical repository

#### Scenario: No privileged operation is attempted
- **WHEN** either job runs
- **THEN** it SHALL require nothing beyond checking out the repository, `npm install` of the
  CLI from the public registry, `git diff`, and the description already present in the event
  payload — no secret, no write to the repository, and no API call requiring elevated
  permission
