## Why

Writing release notes is currently something a maintainer does from memory, months late,
by reading `git log` — and it does not happen. Of the five PRs merged since 1.2.1
(gh-#13 through gh-#17), **none** touched `docs/release_notes/index.rst`. The notes stopped
at 1.0.0 while `setup.py` reached 1.3.0, and reconstructing the 1.3.0 entry afterwards
required reading the diff of `0abb373` to discover that it had reverted most of 1.2.2.
The person who knew what a change meant had moved on by the time anyone wrote it down.

`harden-release-process` made the release mechanism safe: a tag can no longer land on an
unmerged commit or reach a personal fork. It did not make releasing *routine*. It still
begins with a maintainer deciding it is time, then authoring notes for eleven commits in
one sitting, and there is nothing anywhere that tells a contributor a note is expected of
them or a reader when the next release is due.

## What Changes

- **A persistent `Next Release` section** at the top of `docs/release_notes/index.rst`.
  Contributors add their entry in the PR that makes the change, while they still know why
  they made it. The section is the accumulating draft of the next release.
- **A CI gate on that section.** A Travis `pull_request` build fails when the diff touches
  `spektrum/` but adds no entry under `Next Release`. Docs-only, test-only and
  tooling-only PRs are exempt. Travis already runs `pull_request` builds, so this needs a
  `tox` environment, not new infrastructure.
- **`tools/release.sh release <part>`,** a new subcommand between the existing `prepare`
  and `publish`. It refuses when `Next Release` is empty, renames the section to
  `Release: <version>`, opens a fresh empty `Next Release` above it, bumps the version,
  runs both suites and lint, commits **one** commit on a branch named `v<old>-to-<new>`,
  and opens the PR. `prepare` is replaced by it.
- **`tools/release.sh` with no arguments is an interactive release.** It works out which
  of five states the repository is in and does the next right thing: nothing merged, exit
  saying so; changes waiting, show them and ask major/minor/patch; a release PR open, say
  what to merge; **a release merged but never tagged, go straight to tagging** — the state
  this repository has been in twice, and the one nothing currently detects. The
  subcommands stay for scripting.
- **A release-shaped commit subject.** The single commit and its PR are titled
  `v1.3.0 -> v1.3.1`, so `git log --oneline` shows at a glance where each published
  version begins and ends. Today a release is indistinguishable from any other merge.
- **Tagging stays a separate step.** `release` prints the `publish` command and stops.
  A tag can only ever be created on a commit that is already on `master` — the property
  `harden-release-process` exists to protect, and the reason this is two commands rather
  than one.
- **A Claude entry point.** `.claude/skills/cut-a-release/SKILL.md`, so "let's cut a new
  release" in a session does the right thing instead of the agent reconstructing the
  procedure from `git log`. Skills are also invocable by name, so `/cut-a-release` works
  for anyone who would rather type the command. The skill drives `tools/release.sh` — it
  does not reimplement the steps, and it cannot talk its way past the script's refusals.
- **A documented cadence.** Every one to two weeks *if* anything has merged, never on a
  schedule for its own sake. `release.sh status` already answers "is there anything to
  release"; the cadence gives it a reason to be run.
- **Release information in `README.rst`.** Where published versions live, how to read the
  notes, the cadence, and the one-line expectation for contributors: your PR carries its
  own note. The README currently has an empty `Continuous Integration` heading and a
  `Release Notes` section that is a single link.

## Capabilities

### New Capabilities

_(none — see below)_

### Modified Capabilities

_(none — see below)_

This change sets `skip_specs: true`, consistent with `add-agent-docs`,
`enforce-sdd-and-audit-docs` and `harden-release-process`. No file under `spektrum/` or
`tests/` is touched; the library's public surface, CLI flags and reporters behave
identically before and after. `openspec/specs/` is the baseline for *library* behaviour,
and adding repository tooling to it would dilute exactly the baseline
`enforce-sdd-and-audit-docs` exists to make trustworthy.

## Impact

- `tools/release.sh` — `release` added, `prepare` removed. Depends on MQ-3307, which
  introduces the script; this change reshapes it rather than creating it.
- `tools/check_release_notes.py` — new. The gate, written in Python so it is testable and
  runnable locally rather than only inside CI.
- `.travis.yml` — one `TOXENV=notes` matrix entry. The deploy block is untouched.
- `tox.ini` — a `notes` environment so the gate runs identically locally and in CI.
- `docs/release_notes/index.rst` — gains the `Next Release` section.
- `docs/maintenance/index.rst` — `prepare` becomes `release`; the by-hand fallback and the
  cadence follow it.
- `README.rst`, `CONTRIBUTING.md`, `.github/pull_request_template.md` — the contributor
  half of the rule, stated where a contributor is already looking.
- `.claude/skills/cut-a-release/SKILL.md` — new. `.claude/` currently holds only
  `conventions.md`; this is the first skill in the repo.
- `AGENTS.md` — its release paragraph names `prepare`, and its file map lists `.claude/`.

## Deferred

- **Deriving the entry from the commit rather than asking for it.** Tempting, and wrong:
  a commit subject says what was done, a release note says what a consumer will notice.
  The MQ-3300 entry ("a completed run lost its entire report") is not recoverable from
  "stop expect source lookup from crashing the reporter".
- **The CI-side tag guard** already deferred by `harden-release-process`.
- **Anything that requires a GitHub token in Travis.** Auto-tagging on merge was
  considered and rejected: storing push credentials for the canonical repository in CI
  widens what a compromised build can reach, for a step a maintainer runs in seconds.
