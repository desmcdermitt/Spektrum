## Why

Spektrum carries no agent-facing documentation and a half-finished OpenSpec setup, so a
coding agent — or a new human contributor — arrives with no statement of how the project
is laid out, how it is tested, or what a change is expected to prove before it is opened
for review. `openspec/` holds empty `specs/` and `changes/` trees but no `project.md` or
`config.yaml`, so the tooling cannot actually be used against this repo.

This matters more here than in an application. Spektrum is a library: a defect does not
fail one test, it changes what every suite built on it reports, and it reaches every
consumer at once. That risk profile needs to be written down, not rediscovered.

## What Changes

- Initialise OpenSpec properly: add `openspec/project.md` (the working rules) and
  `openspec/config.yaml` (the schema declaration), so `openspec` commands operate on this
  repo.
- Add a root `AGENTS.md`, with `CLAUDE.md` symlinked to it: architecture summary, file
  map, commands, and the reasoning behind non-obvious choices — chiefly that `tests/` is
  pytest rather than Spektrum specs, because the framework cannot be its own harness when
  the code under test is what renders the result.
- Add `.claude/conventions.md`: the Python standards, scoped explicitly to new and
  modified code so they do not read as a mandate to reformat the existing tree.
- Record the reporter compatibility contract — `ExpectParams`, `ExpectFormatData` and the
  reporters are what downstream output is rendered from, and `testrail.py` in particular
  is reached per-case *during* a run, so a failure there can lose results already
  collected rather than merely spoiling the final summary.
- Establish the red-then-green rule: a behavioural change must show a test failing without
  it and passing with it, and both counts belong in the PR.
- Consider adding `CONTRIBUTING.md` and a PR template, which the repo currently lacks.

No behaviour changes. No source file under `spektrum/` is touched.

## Capabilities

### New Capabilities

None. This change adds documentation and project tooling only; it introduces no runtime
behaviour and therefore no capability spec. `.openspec.yaml` sets `skip_specs: true`
accordingly, rather than inventing a requirement to satisfy validation.

### Modified Capabilities

None.

## Impact

- **Added**: `openspec/project.md`, `openspec/config.yaml`, `AGENTS.md`, `CLAUDE.md`
  (symlink), `.claude/conventions.md`. Possibly `CONTRIBUTING.md` and
  `.github/pull_request_template.md`.
- **Unchanged**: everything under `spektrum/` and `tests/`. No API, dependency, or
  packaging change; no version bump.
- **Audience**: contributors and coding agents. Nothing ships to users of the library.
- **Constraint**: this repository is public. Every document must stay vendor-neutral — no
  internal product names, tracker URLs, hostnames, or infrastructure detail. Rules
  borrowed from a downstream project must be generalised, not copied, since much of what
  such a project enforces is specific to its own environment and meaningless here.
