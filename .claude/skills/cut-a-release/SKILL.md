---
name: cut-a-release
description: Cut, prepare or publish a Spektrum release to PyPI. Use when asked to "cut a release", "ship a version", "do a release", "release 1.4.0", "bump the version", "is there anything to release", or "publish to PyPI". Drives tools/release.sh; never reproduces the release steps by hand.
---

# Cutting a Spektrum release

`tools/release.sh` is the release process. **Drive it. Do not reimplement it, and do not
work around anything it refuses.**

Publishing is one act: pushing a tag to `liquidweb/Spektrum` makes Travis upload to PyPI.
Merging does not publish. Running `bumpversion` does not publish. Two versions — 1.2.2 and
1.3.0 — reached `master` and never reached PyPI because their tags were created on a
pre-merge commit and pushed to a personal fork. Every guard in that script exists because
of one of those two mistakes.

## What to do

Run it and read what it says:

```shell
./tools/release.sh
```

With no arguments it works out which state the repository is in and does the next right
thing — nothing to release, changes waiting, a release PR already open, or a release that
merged but was never tagged. It is interactive; it will ask before it changes anything.

The subcommands exist for when you already know the state:

| Command | What it does |
|---|---|
| `./tools/release.sh status` | read-only: what is published, what has drifted |
| `./tools/release.sh release <major\|minor\|patch>` | notes + bump + one commit + PR |
| `./tools/release.sh publish` | tags the merged master and pushes — **this publishes** |

## Your job, and the parts that are not your job

**Yours:** proposing the version part. Read the entries under `Next Release` in
`docs/release_notes/index.rst` and say whether they look like a patch, a minor or a major,
*with your reasoning*, then let the user decide. Bug fixes are a patch; a new flag or
capability is a minor; a change that breaks a consumer's suite is a major. The script
deliberately does not guess this.

**Also yours:** reporting what happened. Surface the PR link. If the script refuses, show
the refusal — it names the fix.

**Not yours:** anything the script does. Do not edit version files, do not create tags, do
not hand-write the release notes rename, do not push a tag because the script would not.
A refusal is an answer, not an obstacle.

## Two commands, not one, and why

`release` opens a PR and stops. `publish` tags the merge commit afterwards. They are
separate because the commit worth tagging does not exist until the PR merges — tagging
before that is the exact failure that lost both previous releases.

So a release spans a review. Expect to do this in two sittings, and say so rather than
waiting or inventing a way around it.

When the user answers "yes, it merged", `publish` re-reads the version, the notes and the
version files from the canonical `master` and refuses if the bump is not actually there.
A wrong answer costs a refusal, not a bad tag. Do not try to verify the merge yourself
first — that check is already in the script and is the authoritative one.

## Before the release

Every merged PR is supposed to add its own entry under `Next Release`. If that section is
empty, `release` refuses, and the fix is a normal PR adding the entries — not editing the
notes as part of the release. Say that rather than filling them in yourself: whoever made
the change knows what it meant.

## When PyPI does not update

The tag is pushed and the release is in flight; nothing is lost. The build is at
https://app.travis-ci.com/github/liquidweb/Spektrum/builds and a dead credential shows
there as a failing deploy step on an otherwise green build. `PYPI_TOKEN` is a Travis
repository secret, rotatable by anyone with admin on the repo. See
[docs/maintenance/index.rst](../../../docs/maintenance/index.rst).
