> **Most of this landed in MQ-3307.** The `Next Release` section, `tools/release.sh`
> (interactive mode, `release`, `publish`, `status`), the Claude skill and the
> documentation shipped with the release-process commit, because the release could not be
> run without them. What remains below is the **CI notes gate** (group 3) and the
> contributor-facing wording that pairs with it, plus the hand-over steps.
>
> Until the gate exists, `Next Release` is enforced at release time only: `release.sh`
> refuses when the section is empty. That catches the omission, but late — at the moment
> nobody remembers what the change was for, which is the problem the gate exists to fix.

## 1. Sequence the prerequisites

- [x] 1.1 MQ-3307 carries the script, the docs and the 1.3.1 bump. Landed as one commit.
- [ ] 1.2 Ship 1.3.1 with `./tools/release.sh publish` once MQ-3307 is on `master`, and
      confirm it on PyPI. Its notes were written by hand; from 1.3.2 onward they come from
      `Next Release`.
- [ ] 1.3 Re-measure the claim in proposal.md — Why after a cycle with the gate off: of the
      PRs merged, how many added a `Next Release` entry unprompted. It was 0 of 5 for
      gh-#13 through gh-#17. That number is the argument for group 3.

## 2. Add the Next Release section

- [x] 2.1 Add a `Next Release` section at the top of `docs/release_notes/index.rst`, above
      the newest `Release:` entry, using the same heading underline style.
- [x] 2.2 Give it a `*Nothing yet.*` placeholder so Sphinx renders no bare heading and the
      empty state is readable.
- [x] 2.3 Confirm the file still renders through `docutils` with no warnings.

## 3. Build the gate

- [ ] 3.1 `tools/check_release_notes.py`: extract the `Next Release` body from a given
      revision of the notes and count `#.` entries.
- [ ] 3.2 Resolve the base revision — `TRAVIS_BRANCH` under Travis, otherwise the
      merge-base with the canonical remote's `master`, resolved by URL as `release.sh`
      does; `--base <ref>` overrides. Fetch the base first, because Travis clones shallow.
- [ ] 3.3 Fail when the base-to-head diff touches `spektrum/` (excluding
      `spektrum/vendor/`) and the head does not have strictly more entries than the base.
      Exempt every other path.
- [ ] 3.4 Honour a `No-release-note: <reason>` trailer in the head commit as an explicit,
      reviewable exemption.
- [ ] 3.5 Report a failure that names the file, the missing entry and the format to add —
      not just that a check failed.
- [ ] 3.6 Error, rather than pass, when the base commit cannot be resolved. A gate that
      passes vacuously is worse than no gate.
- [ ] 3.7 Unit tests under `tests/` covering: `spektrum/` touched with no new entry
      (fails); with a new entry (passes); docs-only diff (exempt); `spektrum/vendor/` only
      (exempt); `No-release-note:` trailer present (passes); base unresolvable (errors).
- [ ] 3.8 Add a `notes` environment to `tox.ini` running the script, so the local command
      and the CI command are the same one.
- [ ] 3.9 Add `TOXENV=notes` to the `.travis.yml` matrix. Do not touch the deploy block.

## 4. Replace `prepare` with `release`

- [x] 4.1 Add `release <major|minor|patch>` to `tools/release.sh`, carrying over every
      guard from `prepare`: canonical remote resolved by URL, clean tree, tag and PyPI
      collision checks, `bumpversion --allow-dirty --no-commit --no-tag`, both suites and
      flake8.
- [x] 4.2 Refuse when `Next Release` holds no entries — that is the signal there is
      nothing to release, and it should read as such rather than as an error.
- [x] 4.3 Rename `Next Release` to `Release: <new version>`, dropping the placeholder, and
      open a fresh empty `Next Release` above it.
- [x] 4.4 Commit one commit on a branch named `v<old>-to-v<new>`, subject `v<old> -> v<new>`.
- [x] 4.5 Push to the fork — the remaining remote once the canonical one is identified —
      with `--fork <remote>` to disambiguate.
- [x] 4.6 Open the PR with `gh pr create` against the canonical repository, base `master`.
      Refuse and print the exact command if `gh` is missing or unauthenticated; never
      leave a pushed branch that looks like a finished release.
- [x] 4.7 Print the `publish` command and stop. Do not tag: the commit to tag does not
      exist until the PR merges.
- [x] 4.8 Remove `prepare`, and make the removed name print a pointer to `release` rather
      than an unknown-command error.
- [x] 4.9 Extend `status` to report how many entries are sitting under `Next Release`, so
      it answers whether a release is due.

- [x] 4.10 Bare `tools/release.sh`, no arguments: detect which of the five states in
      design.md the repository is in and dispatch. The subcommands stay for scripting.
- [x] 4.11 Nothing merged since the released tag: print the current version and exit 0
      saying there is nothing to release. Not an error.
- [x] 4.12 Changes waiting: list them, show `<current> -> <each candidate>` and prompt for
      major, minor or patch, then run the `release` path.
- [x] 4.13 After the PR is opened, prompt whether it has merged. Yes routes into `publish`,
      whose own checks re-read `<remote>/master` — a wrong answer must cost a refusal, not
      a bad tag. No prints the `./tools/release.sh publish` command and exits 0.
- [x] 4.14 Merged-but-never-tagged: detect it on entry and go straight to the tag step.
      Verify against the current tree, which is in exactly this state — 1.3.0 on master,
      1.2.1 on PyPI.
- [x] 4.15 Notes-missing: refuse and name the merged PRs that added no entry, rather than
      offering a release with nothing to say about it.
- [x] 4.16 Non-interactive safety: with no tty, refuse rather than assuming a default.

## 5. Write it down where people look

- [x] 5.1 `README.rst`: a Releases section — where published versions live, the one-to-two
      week cadence, that a release happens only if something merged, and the one-line
      contributor expectation. Fill the empty `Continuous Integration` heading while there.
- [x] 5.2 `docs/maintenance/index.rst`: `prepare` becomes `release`; document the cadence
      and update the by-hand fallback to include the section rename.
- [ ] 5.3 `CONTRIBUTING.md` and `.github/pull_request_template.md`: add the note
      requirement to the pre-PR checklist and the template, including the
      `No-release-note:` trailer.
- [x] 5.4 `AGENTS.md`: its release paragraph names `prepare`.

## 6. Make it reachable from a Claude session

- [x] 6.1 `.claude/skills/cut-a-release/SKILL.md`, with a description that matches
      "cut a release", "ship a version", "is there anything to release" and the like, so
      it fires from ordinary conversation as well as from `/cut-a-release`.
- [x] 6.2 The skill runs `./tools/release.sh status` first and reports what is waiting —
      including the case where `Next Release` is empty and the answer is "nothing to
      release today".
- [x] 6.3 It reads the accumulated `Next Release` entries and proposes `patch`, `minor` or
      `major` with its reasoning, then asks before running. This is the judgement the
      script deliberately does not make.
- [x] 6.4 It runs `./tools/release.sh release <part>` and surfaces the PR link. It must
      not reimplement any step, and must not work around a refusal — a refusal is reported
      to the user as-is.
- [x] 6.5 It knows the second half: after the PR merges, `./tools/release.sh publish`, and
      that a tag on an unmerged commit is the failure the whole process exists to prevent.
- [x] 6.6 `AGENTS.md`: point at the skill from the release section, and add
      `.claude/skills/` to the file map.
- [ ] 6.7 Verify in a real session that "let's cut a new release" reaches the skill, and
      that a refusal from the script is reported rather than routed around.

## 7. Verify

- [x] 7.1 `python -m pytest tests -q` and `python -m spektrum -s tests/live/` both pass;
      record counts. Red-then-green for the gate's own tests.
- [ ] 7.2 `tox -e flake8` clean; `tox -e notes` runs locally and reaches the same verdict
      as CI on the same diff.
- [ ] 7.3 Exercise the gate on real PRs from this repository's history: gh-#15 (touches
      `spektrum/`, no note — must fail) and gh-#16 (docs only — must pass).
- [x] 7.4 Exercise `release` end to end against a bare repository named to match the
      canonical slug, as `harden-release-process` did: section renamed, one commit, branch
      and subject correct, no tag created.
- [x] 7.5 Confirm `docutils` renders both changed `.rst` files with no warnings, and
      `openspec validate --all` passes.

## 8. Hand over

- [ ] 8.1 Both maintainers run `gh auth login` once so `release` can open the PR.
- [ ] 8.2 Run the first real `release` at the end of the first one-to-two week window.
- [ ] 8.3 Revisit the two open questions in design.md once the cadence has been tried:
      whether `tools/` changes should require a note, and whether a scheduled nudge earns
      its noise.
