## Why

Publishing Spektrum is a single mechanical act — push a tag to
`liquidweb/Spektrum` and Travis uploads to PyPI — and the repository documents it
wrongly. `docs/maintenance/index.rst` is the only release document, and following it
exactly produces a release that never happens:

```
#. Push up branch and tag
     git push origin prep_for_release --tags
```

Two defects in three lines. The tag is created by `bumpversion` on the branch, so it
points at the pre-merge commit that the merge then rewrites; and it is pushed to
`origin`, which is a personal fork for both maintainers, while Travis watches
`liquidweb/Spektrum`. The document then closes with a manual `twine upload dist/*`,
which duplicates the CI deploy and requires PyPI credentials neither maintainer holds.

This is not hypothetical. Two versions have been lost to exactly this:

| Version | On PyPI | Tag                  | Reachable from `master` |
|---------|---------|----------------------|-------------------------|
| 1.2.2   | no      | local only, `87916dc` | no                     |
| 1.3.0   | no      | local only, `3bb7e89` | no                     |

PyPI's latest is 1.2.1, published 2025-06-11 by Travis build #68 — the last tag build
this repository has had. `master` has since reached 1.3.0 plus three more merged PRs.
Neither maintainer could state the release procedure from memory, which is the expected
outcome when the written procedure is wrong: there is nothing correct to remember.

## What Changes

- **Add `tools/release.sh`,** a two-phase driver that refuses rather than warns. It
  resolves the canonical remote by URL instead of trusting a remote name, insists the
  release notes exist before it will bump a version, bumps with `--no-commit --no-tag`
  so no tag can land on a pre-merge commit, and tags the canonical `master` directly in
  a separate phase run after the PR merges.
- **Add a `status` subcommand.** Read-only drift report: what PyPI has, what `master`
  claims, whether the notes are written, and every local tag that disagrees with the
  canonical repository. Run against the current tree it names all four bad tags. Had it
  existed, 1.2.2 would have been caught before 1.3.0 repeated it.
- **Rewrite `docs/maintenance/index.rst`** to the process that actually publishes,
  leading with the one fact that matters — pushing a tag to the canonical repository is
  the release — and keeping a by-hand fallback for when the script cannot run.
- **Correct `AGENTS.md`.** Its release paragraph inverts the risk, warning that "a
  version bump in an ordinary PR ships a release by accident". A bump in a PR ships
  nothing; only a pushed tag does. The stated danger is the opposite of the real one.

## Capabilities

### New Capabilities

_(none — see below)_

### Modified Capabilities

_(none — see below)_

This change sets `skip_specs: true`. It alters no Spektrum behaviour: every deliverable
is repository tooling or documentation. No file under `spektrum/` or `tests/` is touched,
and the library's public surface, CLI flags and reporters are identical before and after.
Specs describe behaviour, so inventing a requirement here would put a false entry in the
baseline.

## Impact

- `tools/release.sh` — new. `tools/` currently holds only `run_tests.sh`, which invokes
  `nosetests` and has not worked since before the pytest migration; out of scope here.
- `docs/maintenance/index.rst` — rewritten. Also fixes a short title underline that
  `docutils` warns on today.
- `AGENTS.md` — the "Versions and releasing" section. `CLAUDE.md` is a symlink to it and
  needs no separate edit.
- `.travis.yml` — unchanged. Travis is active and green (builds #81–83 on `master`), and
  build #68 proves the tag-triggered deploy works. The publish step stays where it is.

## Deferred

- **CI-side enforcement.** A guard rejecting a tag build whose commit is not an ancestor
  of `master`, or whose tag disagrees with `setup.py`, would close the hole for a tag
  pushed by hand rather than through the script. It belongs in `.travis.yml` and is its
  own change.
- **Confirming `PYPI_TOKEN` still works.** It has not been exercised since 2025-06-11.
  It is a Travis *repository*-level secret and Travis mirrors GitHub repository
  permissions, so a repo admin can read and rotate it — a check to perform, not an access
  problem to escalate. What is genuinely unrecorded is who holds maintainer rights on the
  Spektrum project on PyPI, which is what minting a replacement token requires. The
  script surfaces the symptom by reporting the build URL when PyPI does not update.
