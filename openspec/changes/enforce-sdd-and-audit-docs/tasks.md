## 1. Establish the ground before building on it

- [x] 1.1 Confirm whether Travis still builds this repository. **It does** — verified by
      the maintainer against a build on an open MQ-3300 PR, which ran and passed. So
      `.travis.yml` stays authoritative for tests, lint and the tag-triggered PyPI deploy,
      and section 5's workflow is scoped to the SDD gate alone. No CI-migration proposal is
      needed.
- [ ] 1.2 Re-measure the drift figures in proposal.md — Why against the current tree, so the
      work starts from numbers rather than from a claim made earlier.
- [ ] 1.3 Confirm the three deferred code defects are still present and still out of scope:
      the `--tr-endpoint` default pointing at a private TestRail tenant, `spec_filter`
      raising `AttributeError` on a nested non-`Spec` class, and `-p`/`-t`'s help text not
      mentioning the `re:` prefix at all (`-p` reads only "Selects a module path to run.
      Ex: sample.TestClass"), which makes the feature undiscoverable outside the source.
      Each gets its own change.

## 2. Correct the published documentation

- [ ] 2.1 `docs/using/index.rst`: remove the flags that no longer exist (`--no-color`,
      `--no-art`, `--ascii-only`, `--json-results`, `--tags`) and correct `--search` usage
      to match `setup_argparse()`.
- [ ] 2.2 Document the thirteen flags that exist and are undocumented: `--concurrency`,
      `--dry-run`, `--exclude-by-metadata`, `--live`, `--live-port`, `--live-linger`, and
      the seven `--tr-*` options. Group them by what a reader is trying to do, not
      alphabetically.
- [ ] 2.3 Delete `docs/parallel/index.rst` and its `toctree` entry. It documents
      `--parallel` / `--num-processes` distributing tests across processes; the runner is
      asyncio with semaphores. Add a concurrency section to `docs/using/index.rst` covering
      `--concurrency` instead.
- [ ] 2.4 `docs/release_notes/index.rst`: add entries for 1.1.x, 1.2.x and 1.3.0. Derive
      them from the git log between the release tags, not from memory.
- [ ] 2.5 `docs/index.rst`: the CI badge and its link point at
      `https://travis-ci.org/liquidweb/Spektrum`, which shut down for open-source builds —
      the image is broken although the builds still run. Repoint both at the host actually
      serving them, or drop the badge if it cannot be pointed anywhere useful.
- [ ] 2.6 `docs/reporting/index.rst`: replace the sample `class_path` value
      (`spec.rift.clients.ssh.SSHCredentials.KeyBased`) with a neutral example. It names an
      internal project in a public repository.
- [ ] 2.7 Document the `re:` prefix and its anchoring in `docs/using/index.rst`, matching
      the README section: `-p` anchors at the end only, `-t` at both ends and also against
      the spaced form of the case name. `--exclude-by-metadata` appears in no doc file at
      all today.
- [ ] 2.8 Re-read `docs/index.rst`, `docs/writing_tests/`, `docs/maintenance/` for the same
      class of drift the flag diff cannot catch — removed concepts described in prose.
- [ ] 2.9 Build the docs (`cd docs && make html`) and confirm no Sphinx warnings are
      introduced by the edits.

## 3. Make drift measurable

- [ ] 3.1 Add `tools/audit_docs.py`: import `setup_argparse()` and diff its flags against
      those mentioned under `docs/`, compare `setup.py`'s version with the newest
      release-note entry, and list modules under `spektrum/` with no corresponding spec.
      Import the parser rather than grepping for flags.
- [ ] 3.2 Exit non-zero on drift, and document in `AGENTS.md` — Commands how to run it.
      Do **not** wire it into CI in this change: a drift check that fails on day one blocks
      every unrelated PR.
- [ ] 3.3 Delete `tools/run_tests.sh`. It calls `nosetests`, which cannot run on 3.12, and
      `AGENTS.md` already flags it as stale.

## 4. Route the conventions to the agent that writes the code

- [ ] 4.1 Add `.claude/commands/opsx/apply.md` shadowing the user-level command: read
      `openspec/project.md` and `.claude/conventions.md` as step one, before any file is
      edited, then delegate the rest. Add the step; do not copy the upstream file, so it
      inherits future changes.
- [ ] 4.2 Add one line to `AGENTS.md` recording that OpenSpec 1.9.0 treats
      `openspec/project.md` as legacy structure — preserved, never fed to an agent — so
      nobody mistakes preservation for enforcement.
- [ ] 4.3 Verify the override actually loads: run `/opsx:apply` against a trivial task and
      confirm the conventions were read before the edit.

## 5. Enforce the workflow in CI

- [ ] 5.1 Add `.github/workflows/` with a job that fails when the diff touches `spektrum/`
      and nothing under `openspec/`. Honour a `no-spec` label as the escape hatch.
- [ ] 5.2 Add `openspec validate --all` to that workflow, on Node, so a malformed spec or
      change is caught rather than merely a missing one.
- [ ] 5.3 Name the workflow for what it checks, and state in `CONTRIBUTING.md` which CI
      system owns tests and lint versus which owns process, so a contributor can tell which
      red build matters.
- [ ] 5.4 Land this group **after** section 2, so the gate's first run is not the PR that
      introduces it failing against itself.

## 6. Inventory the spec gap

- [ ] 6.1 List every capability under `spektrum/` with no spec — the runner's execution
      tree, expectation construction and source lookup, case and spec selection, the
      console/xunit/TestRail reporters, the CLI surface — ranked by blast radius.
- [ ] 6.2 Record the inventory where the next person will find it, and state plainly that
      the current baseline covers the live view only. Writing those specs is **not** part of
      this change; each capability becomes its own proposal.

## 7. Verification

- [ ] 7.1 Confirm no file under `spektrum/` or `tests/` was modified: this change is docs,
      tooling and CI only.
- [ ] 7.2 `python -m pytest tests -q` — record the count. It must match the count before
      the change.
- [ ] 7.3 `python -m spektrum -s tests/live/` — record the count (pytest does not collect
      these, and under `python -m` a nonexistent search path exits 0).
- [ ] 7.4 `tox -e flake8` clean, including `tools/audit_docs.py`.
- [ ] 7.5 `openspec validate --all` passes.
- [ ] 7.6 `tools/audit_docs.py` reports no drift, which is the real proof section 2 worked.
- [ ] 7.7 Public-repository audit: grep every added and edited file for internal product
      names, private hostnames and tracker URLs, and apply the same grep to this branch's
      commit messages.

## 8. Review

- [ ] 8.1 Read each edited doc once as an outside contributor with no context, and cut
      anything that only makes sense from the inside.
- [ ] 8.2 Rebase onto current `master` and resolve drift in the flag lists and the file map.
- [ ] 8.3 Squash to a single commit, keeping the measured drift figures and the CI
      decision from task 1.1 in the message body.
- [ ] 8.4 Open the PR against `liquidweb/Spektrum`, base `master`, describing it as
      docs-tooling-and-CI only with no behaviour change.
- [ ] 8.5 Archive this change once merged (`openspec archive enforce-sdd-and-audit-docs`).
