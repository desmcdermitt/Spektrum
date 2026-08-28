## Why

The repository is about to gain a spec-driven workflow that nothing enforces and that the
tooling no longer reads. `openspec/project.md` — the file this project treats as its
working agreement — is classified as **legacy structure** by OpenSpec 1.9.0: preserved on
disk, never fed to an agent. Nothing in `/opsx:apply` or the `openspec` CLI surfaces the
repo's conventions, so the workflow can be followed to the letter and still produce code
that ignores the house rules. Meanwhile the published Sphinx documentation describes a
version of Spektrum that no longer exists.

The gap is measurable rather than theoretical. `docs/` documents eight command-line flags
that were removed (`--parallel`, `--num-processes`, `--tags`, `--no-color`, `--no-art`,
`--ascii-only`, `--json-results`) and omits thirteen that exist (the whole `--tr-*` set,
`--live`/`--live-port`/`--live-linger`, `--concurrency`, `--dry-run`,
`--exclude-by-metadata`). `docs/parallel/index.rst` explains a multi-process architecture
that asyncio and semaphores replaced. `docs/release_notes/index.rst` stops at 1.0.0 while
`setup.py` says 1.3.0 — three releases with no notes. And the spec baseline covers only
the live view: roughly 4,000 lines of runner, expectation and reporting code have no spec
at all, so "spec-driven" currently describes one feature rather than the library.

## What Changes

- **Enforce the workflow in CI.** Add a check that fails when `spektrum/` changes without a
  corresponding change under `openspec/`, and that runs `openspec validate --all`. A rule
  no build enforces is a suggestion.
- **Make the conventions reachable by the agent that writes the code.** `/opsx:apply` is
  the one command that edits source, and it reads only the change's own artifacts. Route
  `.claude/conventions.md` and the PR procedure into it, and resolve `project.md`'s legacy
  status so the rules live somewhere the tooling actually loads.
- **Correct the published documentation.** Remove or rewrite the flags and the parallel
  chapter that no longer describe the code, document the thirteen undocumented flags, and
  bring the release notes up to 1.3.0.
- **Inventory the spec gap.** Produce a list of the library's unspecified capabilities,
  ranked, so back-filling them becomes scheduled work rather than an open-ended intention.
  Writing those specs is deliberately *not* in this change — see Impact.
- **Verify the audit claims hold.** Every drift figure above was measured; the same checks
  become a repeatable script so the next audit is a command rather than an afternoon.

## Capabilities

### New Capabilities

_(none — see below)_

### Modified Capabilities

_(none — see below)_

This change sets `skip_specs: true`. It alters no Spektrum behaviour: every deliverable is
documentation, repository tooling, or CI configuration. The library's public surface, its
CLI flags and its reporters behave identically before and after. Specs describe behaviour,
so inventing a requirement here to satisfy validation would put a false entry in the
baseline this change exists to make trustworthy.

## Impact

- `docs/using/`, `docs/parallel/`, `docs/reporting/`, `docs/release_notes/` — the stale
  chapters. `docs/parallel/index.rst` may warrant deletion rather than revision.
- `.github/workflows/` — new; the repository currently has no Actions workflow, only the
  PR template. `.travis.yml` is the existing CI and stays authoritative for tests and lint.
- `.claude/` — a repo-level `opsx:apply` override, so the conventions load regardless of
  which session or subagent runs it.
- `openspec/project.md` and `AGENTS.md` — whichever becomes the authority, exactly one of
  them must be it.
- `tools/` — the audit script lands here; note `tools/run_tests.sh` is already stale
  (`nosetests`) and is a candidate for removal in passing.
- **Not touched:** `spektrum/` and `tests/`. Three known code defects are deliberately out
  of scope, because each changes behaviour and so needs its own change with a real spec: the
  `--tr-endpoint` default pointing at a private TestRail tenant, `spec_filter` raising
  `AttributeError` on a nested non-`Spec` class, and `-p`/`-t`'s help text never mentioning
  the `re:` prefix that makes the feature discoverable.
