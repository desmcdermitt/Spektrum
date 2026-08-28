## 1. Establish what is actually broken

- [x] 1.1 Confirm the publish trigger. `.travis.yml` has `deploy.on.tags: true` with
      `provider: pypi`, `username: __token__`, `password: $PYPI_TOKEN`,
      `skip_existing: true`. **A pushed tag is the only thing that publishes.**
- [x] 1.2 Confirm Travis is still active. Repository is `active: true`; builds #81–83 on
      `master` passed on 2026-08-28. Build #68 is the last tag build, `v1.2.1`,
      2025-06-11, which matches PyPI's upload timestamp for 1.2.1.
- [x] 1.3 Confirm the lost releases. `v1.2.2` → `87916dc` and `v1.3.0` → `3bb7e89`; neither
      is an ancestor of `upstream/master`, and neither exists on `liquidweb/Spektrum` or on
      the fork. PyPI's latest is 1.2.1.
- [x] 1.4 Confirm the documented process reproduces the failure.
      `docs/maintenance/index.rst` says `git push origin prep_for_release --tags`, with the
      tag created by `bumpversion` on the branch. Both defects, in one step.

## 2. Build the driver

- [x] 2.1 `tools/release.sh` with `status`, `prepare <part>` and `publish`.
- [x] 2.2 Resolve the canonical remote by URL; refuse on zero or multiple matches.
- [x] 2.3 `prepare`: refuse until the notes for the new version exist, printing the
      heading to paste and the commits merged since the last release.
- [x] 2.4 `prepare`: bump via `bumpversion --allow-dirty --no-commit --no-tag`, then run
      both suites and flake8. Do not commit.
- [x] 2.5 `prepare`: re-runnable. The first run stops at the notes check, and the second
      must not discard the notes just written.
- [x] 2.6 `publish`: read version, notes and consistency from `<remote>/master`, not the
      working tree.
- [x] 2.7 `publish`: refuse on an existing tag (local-but-different, or on the remote), on
      a version already on PyPI, and on version files that disagree.
- [x] 2.8 `publish`: require the version typed to confirm; refuse in a non-tty without
      `--yes`.
- [x] 2.9 `publish`: tag the canonical `master` commit, push the tag to the canonical
      remote, then poll PyPI and report the build URL on timeout.
- [x] 2.10 `status`: classify every local tag against the canonical repository —
      never pushed, or disagreeing — and resolve the "merged since" range from the
      remote's tag rather than the local one.

## 3. Verify the driver against reality

- [x] 3.1 `status` against this repository. Names `v1.2.2`, `v1.3.0` and `v1.2.0` as never
      pushed and `v1.2.1` as disagreeing; reports 1.3.0 on master against 1.2.1 on PyPI.
- [x] 3.2 Refusals, each observed: bad `<part>`; `prep_for_release` existing but not
      checked out; dirty tree at branch creation; missing notes; notes missing on
      `<remote>/master` at publish time; non-tty confirmation.
- [x] 3.3 Full `prepare` path in a scratch clone: branch cut, notes refusal, notes written,
      re-run bumps all three files to 1.3.1, 175 pytest + 22 spec cases + flake8 clean.
- [x] 3.4 Full `publish` path against a bare repository named to match the canonical slug.
      Annotated `v1.3.1` created on the canonical master's exact SHA and pushed; re-running
      refuses because the remote now has the tag.
- [x] 3.5 Regression found by 3.1 and fixed: `git fetch --tags` aborts the script on
      "would clobber existing tag". Fetch the branch only.
- [x] 3.6 Regression found by 3.1 and fixed: local branches named `v1.2.0` / `v1.2.1`
      shadow the tags of the same name. Use `refs/tags/` everywhere.

## 4. Correct the documents

- [x] 4.1 Rewrite `docs/maintenance/index.rst`: lead with the publish trigger, both
      phases, what each check refuses, and a by-hand fallback. Fix the short title
      underline that `docutils` warns on.
- [x] 4.2 Correct `AGENTS.md`'s "Versions and releasing". It currently warns that a bump
      in an ordinary PR "ships a release by accident" — the opposite of the truth.
- [x] 4.3 Confirm `docs/maintenance/index.rst` renders through `docutils` with no
      warnings.

## 5. Hand over

- [ ] 5.1 Both maintainers run `./tools/release.sh status` on their own clone and clear
      the stale tags it names.
- [ ] 5.2 Use `publish` for the outstanding 1.3.1 release — the first real exercise.
- [ ] 5.3 Confirm `PYPI_TOKEN` is still valid before a release depends on it — unused
      since 2025-06-11. Travis repository settings, reachable by anyone with admin on
      `liquidweb/Spektrum`. Separately, record who holds maintainer rights on the Spektrum
      project on PyPI, since that is what minting a replacement requires.
- [ ] 5.4 Open the deferred change for a CI-side tag guard.
