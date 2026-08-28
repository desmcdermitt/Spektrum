## Context

See proposal.md — Why. Three constraints shape the approach.

MQ-3307 is a prerequisite: it introduces `tools/release.sh`, the corrected release
documentation and the 1.3.1 bump, and this change reshapes that script rather than
creating it. Its central property — a tag exists only
on a commit already on `master` — is load-bearing here, and is why `release` and `publish`
stay separate commands rather than collapsing into the one the request describes.

Travis already builds `pull_request` events (builds #74–#80), so the gate needs a `tox`
environment and one matrix entry, not new infrastructure. Its deploy block holds
`PYPI_TOKEN` and nothing else, and this change adds no credential to it: storing push
rights for the canonical repository in CI widens what a compromised build can reach, for
a step a maintainer runs in seconds.

`docs/release_notes/index.rst` is Sphinx source, reached from `README.rst` and
`docs/index.rst`. Whatever the gate reads has to keep rendering.

## Goals / Non-Goals

**Goals:**

- A contributor learns a note is expected at the moment they can still write a good one,
  from the build rather than from a reviewer's memory.
- A reader of `git log --oneline` can see where each published version starts.
- The gate runs identically on a laptop and in CI — a check only reproducible in CI is a
  check people cannot fix before pushing.
- The release becomes clerical. Nothing in it should require remembering what a change
  three weeks ago was for.

**Non-Goals:**

- Blocking a release on the cadence. One to two weeks is a habit, not a rule; a fortnight
  with nothing merged should produce no release and no noise.
- Guaranteeing note *quality*. The gate can prove a line exists. Only review can say it
  describes what a consumer will notice.
- Any second source of truth. No `CHANGELOG.md` — the Sphinx notes are what the README
  links to and what gets published.

## Decisions

**`Next Release` lives at the top of `docs/release_notes/index.rst`, not in a new file.**
A `CHANGELOG.md` would be the third place a version is written down, after `setup.py` and
`docs/conf.py`, and the one nothing renders. Keeping the draft in the same file as the
history means `release` is a rename rather than a migration, and the notes a contributor
writes are the notes that publish.

When empty the section carries a `*Nothing yet.*` placeholder, so Sphinx does not render a
bare heading and so "is there anything to release" is answerable by reading the file.

**The gate is Python (`tools/check_release_notes.py`), not shell.** It parses RST
structure and diffs two revisions of it; that is beyond what is comfortable in `awk`, and
unlike `release.sh` it wants unit tests of its own. Running it through a `tox -e notes`
environment gives contributors the identical command CI runs.

**The gate compares entry counts, not file modification.** It extracts the `Next Release`
body from the base and from the head and requires strictly more `#.` items in the head.
Alternatives rejected: *requiring the file to be touched* passes on a whitespace edit;
*requiring the entry to name the PR number* is unwritable, since the number does not exist
until the PR is opened.

**The gate fires only on `spektrum/`, excluding `spektrum/vendor/`.** Tests, docs,
`openspec/`, `tools/` and CI config are exempt. A rule that fires on documentation PRs
teaches people to route around it, and `spektrum/vendor/*` is excluded from flake8 for the
same reason it is excluded here — it is not ours to describe.

**There is a deliberate escape hatch: a `No-release-note: <reason>` trailer** in the head
commit. Some `spektrum/` changes genuinely have no consumer-visible effect. A hard gate
with no exit gets switched off the first time it is wrong, and a trailer is visible in
review, which a CI override flag is not.

**The base revision is resolved, never assumed.** On Travis, `TRAVIS_BRANCH` is the base
branch of a PR build and the clone is shallow, so the script fetches the base explicitly
before diffing. Locally it defaults to the merge-base with the canonical remote's `master`,
resolved by URL exactly as `release.sh` does. `--base <ref>` overrides both.

**Bare `tools/release.sh` detects state rather than running a fixed sequence.** A linear
wizard assumes you are at the start; the interesting failures happen when you are not.
Five states, distinguished from the canonical `master`, PyPI and the notes:

| State | Signal | What it does |
|---|---|---|
| Nothing to release | no commits since the released tag | exits saying so |
| Changes waiting | commits merged, `Next Release` non-empty | shows them, asks the part |
| Notes missing | commits merged, `Next Release` empty | refuses; names the PRs owing a note |
| Release PR open | a `v*-to-v*` branch exists, master unchanged | says what to merge |
| **Merged, never tagged** | master's version > PyPI's, notes cover it | goes straight to tagging |

The last row is the whole point. It is the state that lost 1.2.2 and 1.3.0, it is the
state the repository is in today at 1.3.0-on-master against 1.2.1-on-PyPI, and nothing
currently notices it. A wizard that only ever starts from the beginning would walk past it.

**The "has the PR been merged?" answer is not trusted.** Answering yes routes into the
existing `publish` path, which re-reads the version, notes and consistency from
`<remote>/master` and refuses if the bump is not actually there. So a wrong answer costs a
refusal, not a tag on the wrong commit. This is deliberate: asking a human to confirm a
git state and then acting on the answer is how the original failure worked.

**`release` replaces `prepare` rather than joining it.** Two commands that both bump a
version, one of which writes notes from scratch and one of which renames an accumulated
section, is the situation that produces the wrong one being run. `prepare`'s guards — the
canonical-remote resolution, the clean-tree check, `--no-commit --no-tag`, both suites and
lint — carry over unchanged.

**The branch is `v1.3.0-to-v1.3.1`; the commit subject is `v1.3.0 -> v1.3.1`.** The
requested `->` cannot appear in a git ref, so the branch spells it out and the subject —
which has no such restriction — uses the arrow. The subject is what shows up in
`git log --oneline`, which is where it was wanted.

**The PR is opened with `gh`, and its absence is a refusal, not a fallback.** Silently
skipping the PR would leave a pushed branch that looks like a finished release. The script
refuses and prints the exact `gh pr create` command to run by hand.

**The Claude entry point is a skill, not a slash command or a prose section.** The
request is "let's cut a new release" in ordinary conversation, which is what a skill's
description matches on; a slash command only fires when someone types it. A skill file
also gets both — skills are invocable by name, so `/cut-a-release` works from the same
file. Prose in `AGENTS.md` was the third option and is the weakest: it is loaded as
background, not as a procedure to follow, which is how an agent ends up reconstructing
release steps from `git log`.

**The skill drives the script; it does not restate it.** Any procedure written twice
drifts, and the copy an agent reads would be the one nobody runs. The skill's job is
judgement the script cannot make — reading the accumulated `Next Release` entries to
propose `patch` vs `minor`, and surfacing the PR link — and then getting out of the way.
Every gate stays in `release.sh`, where a session cannot argue with it: the script refuses,
and the skill reports the refusal rather than working around it.

**The release branch is pushed to the fork, not to the canonical remote.** `release.sh`
already resolves the canonical remote by URL; the fork is then the sole remaining remote,
and `--fork <remote>` disambiguates when there is more than one.

## Risks / Trade-offs

- **Two PRs both appending to `Next Release` conflict.** → Real and frequent, since every
  PR touches the same few lines. Entries append at the end of the section, one line each,
  so the conflict is textual and trivial; this is the cost of a single accumulating draft
  and is cheaper than reconstructing the notes months later.
- **Travis's shallow clone may not contain the base commit.** → The script fetches the
  base before diffing and reports a clear error rather than passing vacuously. A gate that
  silently passes when it cannot find the base is worse than no gate.
- **The `No-release-note:` trailer can be used to route around the gate.** → Accepted. It
  is recorded in the commit and visible in review, which makes it a decision someone made
  rather than a step nobody took.
- **A note written at PR time may not match what finally merges.** → Review already covers
  the diff; the note is part of the diff.
- **An agent could be asked to release something that should not ship.** → The skill adds
  no authority. `release.sh` still refuses on an empty `Next Release`, a dirty tree, a
  failing suite or a taken version, and the tag still requires a merged PR and a separate
  `publish` run. The session can be wrong about *whether* to release; it cannot produce a
  broken one.
- **`gh` needs authentication in each maintainer's clone.** → One-time `gh auth login`,
  and the refusal says so.

## Migration Plan

Ordering matters, because the outstanding 1.3.1 release already has its notes written by
hand and carried in MQ-3307:

1. Merge MQ-3307, which carries the script, the corrected docs and the 1.3.1 bump.
2. Ship 1.3.1 with `release.sh publish`. This is the last release run the old way.
3. Merge this change, adding an empty `Next Release` above the `Release: 1.3.1` entry and
   turning the gate on. From here every PR carries its own note.
4. The first `release.sh release <part>` run is whatever accumulates over the following
   week or two.

Rollback is dropping the `TOXENV=notes` matrix entry; nothing else in the release path
depends on the gate.

## Open Questions

- Should `tools/` changes require a note? They can change how maintainers release without
  changing what consumers see. Left exempt for now; revisit if it bites.
- Is a scheduled nudge worth it — something that notices `Next Release` has been non-empty
  for a fortnight? `status` already answers the question on demand, and a notification
  nobody owns becomes noise. Deferred until the cadence has been tried by hand.
