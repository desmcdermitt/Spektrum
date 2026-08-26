## Context

See proposal.md — Why. Three constraints shape the approach:

**The `openspec` CLI is a Node package.** `.travis.yml` is a Python-only matrix
(`TOXENV=py312`, `TOXENV=flake8`) that also owns the PyPI deploy on tags. Any check that
invokes `openspec` needs a Node toolchain the current CI does not have.

**`openspec/project.md` is legacy.** OpenSpec 1.9.0's `legacy-cleanup` module lists
"AGENTS.md and project.md" as legacy structure files and preserves `project.md` for manual
migration. `openspec instructions <artifact> --json` returns no `context` field for this
repo, so nothing the CLI hands an agent mentions the project's rules.

**`/opsx:apply` is the only command that writes source, and it is user-level.** It lives in
`~/.claude/commands/opsx/apply.md`, outside this repository, and its context comes from
`openspec instructions apply --json`, whose `contextFiles` are the change's own artifacts.
The repo cannot edit that file, only shadow it.

What *does* load reliably is `CLAUDE.md`, symlinked to `AGENTS.md`: the harness reads it for
the working directory at session start. That is the one hook the repository controls.

## Goals / Non-Goals

**Goals:**

- A merge-blocking check that a behaviour change arrives with a spec or change document.
- The conventions reach the agent writing the code, in a session or a subagent.
- The published documentation describes the code that exists.
- Drift is measured by a command, so the next audit is repeatable.

**Non-Goals:**

- Writing specs for the unspecified library surface. This change inventories the gap; each
  capability needs authored requirements and review, which would swamp one change.
- Replacing Travis. The test matrix and the tag-triggered PyPI deploy stay where they are.
- Fixing the three known code defects (proposal.md — Impact, tasks.md 1.3). Each changes
  behaviour and so earns its own change.

## Decisions

**A GitHub Actions workflow for the SDD gate, not a Travis job.** Travis would need Node
added to a Python matrix, slowing every build and coupling the test lane to a tool it does
not otherwise use — for a check that has nothing to do with running tests. A separate
workflow keeps one job per concern: Travis proves the code works, Actions proves the
process was followed. *Alternative considered:* a pure-Python path check inside Travis,
needing no Node. Rejected because it can compare changed paths but cannot run
`openspec validate --all`, which is the half that catches a malformed spec.

**The gate is path-based with a labelled escape hatch.** It fails when the diff touches
`spektrum/` but nothing under `openspec/`, and passes when a `no-spec` label is present.
Attempting to distinguish a "real" behaviour change from a docstring fix by parsing the diff
is a heuristic that will be wrong in both directions; a human applying a label is honest
about who made the judgment. *Alternative considered:* warn instead of fail. Rejected —
proposal.md's premise is that an unenforced rule is a suggestion.

**`project.md` stays the authority; the repo shadows `/opsx:apply` to load it.** Moving the
working agreement into `AGENTS.md` would push that file well past the length at which it
stops being read, and OpenSpec preserves `project.md` precisely so it can keep serving this
purpose. The fix for the tooling gap is a repo-level `.claude/commands/opsx/apply.md` that
adds reading `openspec/project.md` and `.claude/conventions.md` as its first step, before
any file is edited. `AGENTS.md` gains one line recording that the CLI does *not* read
`project.md`, so nobody mistakes preservation for enforcement. *Alternative considered:*
`openspec init --tools claude` to regenerate current-format integration. Rejected: it
writes tool integrations into the repo that would duplicate the user-level `opsx` commands
already installed, and the duplication resolves unpredictably.

**Delete `docs/parallel/index.rst` rather than revise it.** It describes distributing tests
across Python processes with `--parallel` and `--num-processes`; the runner is asyncio with
semaphores bounded by `--concurrency`, and the chapter's framing — separate processes,
different reporting — is wrong at the premise, not in its details. Concurrency gets a
section in `docs/using/`. Git keeps the old page for anyone who wants it.

**The audit is a Python script in `tools/`, replacing the shell relic there.** It reports
flags documented but absent from `setup_argparse()`, flags present but undocumented,
`setup.py`'s version against the newest release-note entry, and capabilities under
`spektrum/` with no spec. Python because the repo is Python and the script can import the
CLI's own parser rather than grepping for flags. It exits non-zero on drift so it can be
wired into the gate later, but this change does not wire it in — a drift check that fails
on day one blocks every unrelated PR.

## Risks / Trade-offs

- **The path gate fires on legitimate non-behavioural edits** (a typo in a docstring, a
  lint fix) → the `no-spec` label clears it in one click, and the PR template's blast-radius
  field already asks the author to think about scope.
- **Two CI systems drift apart, or a contributor cannot tell which failure matters** →
  the workflow is named for what it checks, and `CONTRIBUTING.md` states which system owns
  tests and which owns process.
- **Deleting a docs chapter loses information if some consumer still runs a version with
  `--parallel`** → the release notes, once brought current, are where a reader on an old
  version looks; the chapter as written misleads every reader on 1.3.0.
- **The `opsx:apply` override diverges from the user-level command it shadows** as that
  command is updated upstream → the override adds a step and delegates the rest rather than
  copying the file, so it inherits changes instead of freezing them.
- **`skip_specs: true` on a change about enforcing specs reads as a contradiction** →
  proposal.md — Capabilities states the reasoning; the alternative is a fabricated
  requirement in the baseline this change exists to make trustworthy.

## Migration Plan

No deployment and no rollback: nothing ships to users of the library. The one ordering
constraint is that the Actions workflow lands *after* the docs corrections, so the first
run of the gate is not the PR that introduces it failing against itself.

## Open Questions

- ~~**Is Travis still running for this repository?**~~ **Resolved: yes.** Confirmed by the
  maintainer against a build on an open MQ-3300 PR, which ran and passed. Travis therefore
  keeps tests, lint and the tag-triggered PyPI deploy, and the new workflow is the SDD gate
  and nothing else — the smaller of the two shapes this change could have taken. The badge
  in `docs/index.rst` still points at `travis-ci.org`, which shut down for open-source
  builds, so the image is broken even though the builds are not; that is a docs fix, not a
  CI one.
- **Should the docs be published anywhere?** `docs/` is a complete Sphinx tree with no
  configured host and no URL in `setup.py`. Correcting docs nobody can read is worth less
  than correcting them and publishing them, but choosing a host is a decision for the
  maintainer.
