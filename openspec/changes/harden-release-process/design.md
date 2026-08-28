## Context

Releasing Spektrum is one mechanical act with a long gap in the middle. The version bump
and the release notes go through code review; the tag that actually publishes can only be
created after that review merges. Every failure this change addresses lives in that gap.

`bumpversion` is configured `commit = True, tag = True`, so it produces both in one step,
on whatever commit it is run on. Run on a branch — which is the only place it can be run,
since the bump needs review — it tags a commit that the merge will rewrite. The tag is
then correct about nothing: not the version's content, not its history, not its
reachability. `git log` shows the bump landing on `master` under a new SHA while the tag
stays behind on the old one, which is why this reads as working until someone checks PyPI
months later.

The current state, measured:

| | |
|---|---|
| PyPI latest | 1.2.1, 2025-06-11, Travis build #68 |
| `master` | 1.3.0 + 3 merged PRs, `b7c2850` |
| Tags never pushed anywhere | `v1.2.2` → `87916dc`, `v1.3.0` → `3bb7e89` |
| Local tags disagreeing with the canonical repo | `v1.2.0`, `v1.2.1` |

## Goals / Non-Goals

**Goals**

- A maintainer who knows nothing about the history can release correctly by running two
  commands, and cannot produce a dangling tag by following them.
- Every refusal names the fix. A check that prints only "failed" returns the reader to the
  process that just misled them.
- The drift that hid two lost releases is visible on demand, before the next release
  rather than after it.

**Non-Goals**

- Migrating CI. Travis works — #68 published 1.2.1, and #81–83 are green on `master`.
  Replacing it is a larger change with its own risk, and it is not what broke.
- Enforcement inside CI. Worth doing, deferred deliberately; see proposal.md.
- Retroactively publishing 1.2.2 or 1.3.0. PyPI goes 1.2.1 → 1.3.1 and the notes carry
  the 1.3.0 entry so nothing is undocumented.
- Fixing `tools/run_tests.sh`, which calls `nosetests`. Pre-existing, unrelated.

## Decisions

**Two subcommands, not one.** A release is two events separated by a review, and a single
command would have to guess which side of the merge it is on. `prepare` and `publish` name
the phase, and each states what the other does next.

**Resolve the remote by URL, never by name.** `origin` is a personal fork for both
maintainers, and pushing the tag to the fork is half of what lost both releases. The script
scans `git remote -v` for the canonical slug and refuses when zero or more than one remote
matches, rather than defaulting to `upstream` — a name that is a local convention, not a
guarantee.

**`--allow-dirty --no-commit --no-tag`, always.** `bumpversion` still writes the three
version files, so the tool stays authoritative for the bump, but it never creates the
artefact it gets wrong. `--allow-dirty` is required because the release notes are edited
before the bump, by design: a version with no notes is not releasable.

**`publish` reads the canonical `master`, not the working tree.** Version, notes and
consistency are all read through `git show <remote>/master:<path>`. What gets tagged is
what is on the canonical master, whatever state the local clone is in.

**Notes before version.** `prepare` refuses until `docs/release_notes/index.rst` has a
section for the new version, and prints the heading to paste plus the commits merged since
the last release. This inverts the old order, in which the notes were a step someone could
skip and nothing noticed — the release notes stopped at 1.0.0 while `setup.py` said 1.3.0.

**Type the version to confirm.** A y/n prompt is answered reflexively. PyPI versions cannot
be reused, replaced or deleted-and-reuploaded, so the last gate before an irreversible
action asks for something that cannot be typed by accident.

**Wait for PyPI rather than trusting the push.** A pushed tag is not a release; it is a
request for one. The script polls for the version and, on timeout, points at the build —
which is where a revoked `PYPI_TOKEN` would show up.

**Fetch the branch, not `--tags`.** `git fetch --tags` exits non-zero on "would clobber
existing tag", which is precisely the state a clone is left in by a failed release. Under
`set -e` that killed the script on its first command, for a condition `status` exists to
report. Found by running `status` against this repository, where local `v1.2.1` disagrees
with the canonical one.

## Risks / Trade-offs

- **A tag pushed by hand still bypasses everything.** The script cannot prevent
  `git push upstream v9.9.9`. Only a CI-side guard closes this, and that is deferred. The
  mitigation meanwhile is that `status` reports the damage.
- **`bash` and `awk` dependency.** Avoided `declare -A` so the script runs on bash 3.2
  (macOS) as well as 4+. Not tested on macOS; both maintainers are on Linux.
- **The 15-minute PyPI poll can outlive a slow build.** Timing out is not a failure — the
  tag is pushed and the release is in flight. The message says so, rather than implying
  the release was lost.
- **`status` costs two network calls** (PyPI, `git ls-remote`). It is read-only and cheap
  enough to run habitually, which is the point.

## Migration Plan

No migration. The script is additive and the documents it corrects have no consumers other
than maintainers. The stale local tags (`v1.2.2`, `v1.3.0`, and the divergent `v1.2.0` /
`v1.2.1`) are each maintainer's own clone to clean up; `status` names them and
`git tag -d` removes them. Nothing on the canonical repository changes.

The first real exercise is the outstanding 1.3.1 release, which reaches `publish` with the
prepare PR already written by hand.

## Open Questions

- Is `PYPI_TOKEN` still valid? Unused since 2025-06-11. A repo admin can read and rotate
  it in Travis repository settings, so this is a check to run rather than access to
  obtain — but it stays unverified until a tag build actually deploys.
- Who holds maintainer rights on the Spektrum project on PyPI? Minting a replacement token
  requires it, and nothing in the repository records it.
- Should `v1.2.2` and `v1.3.0` be published retroactively from their dangling commits
  rather than skipped? Assumed no — the content is already in `master` and reaches users
  in 1.3.1 — but it is the maintainer's call, not the script's.
