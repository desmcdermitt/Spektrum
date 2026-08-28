> Items 1.x and 2.x are already implemented and committed on the working branch for this
> change; they are checked off so the remaining work is visible at a glance. Everything
> unchecked is still to do.

## 1. Initialise OpenSpec

- [x] 1.1 Add `openspec/config.yaml` declaring the `spec-driven` schema
- [x] 1.2 Add `openspec/project.md` covering the PR procedure, the red-then-green rule,
      scope discipline, and the reporter compatibility contract
- [x] 1.3 Confirm `openspec status` and `openspec validate` run clean against the repo
- [x] 1.4 Back-fill the specs for the live-view work that shipped in v1.3.0: bring the four
      completed changes over from the `spektrum-live` branch, archive them so their
      requirements are promoted into `openspec/specs/`, and write a real Purpose for each
      capability. Without this the repo declares `schema: spec-driven` over an empty spec
      baseline while the behaviour is already released

## 2. Agent-facing documentation

- [x] 2.1 Add root `AGENTS.md`: architecture summary, file map, commands
- [x] 2.2 Explain in `AGENTS.md` why `tests/` is pytest rather than Spektrum specs, and
      that `Expectation` built directly does not register with a spec
- [x] 2.3 Symlink `CLAUDE.md` to `AGENTS.md` (do not create a second copy)
- [x] 2.4 Add `.claude/conventions.md`, scoped in its own text to new and modified code
- [x] 2.5 Cross-check the file map against the tree and correct any drift
      - Drift found and corrected: `tests/reporting/` was listed but does not exist on
        this branch, and `docs/` — the whole Sphinx tree — was missing from the map.
        `transport.py` is `RetryTransport` for outbound reporter HTTP, not part of the
        live view, and is now annotated as such
- [x] 2.6 Correct the claim that `tests/` is pytest-only. `tests/live/` is 22 cases across
      7 `Spec` classes, run by the CLI (`python -m spektrum -s tests/live/`); pytest
      collects none of them, so a green `pytest tests` says nothing about them. AGENTS.md
      documents both suites, and `openspec/project.md` and `.claude/conventions.md` were
      corrected to match
- [x] 2.7 Remove the invented `can_*` case-naming convention from AGENTS.md. `case_filter`
      in `spektrum/spec.py` takes every public non-lifecycle method; `grep -rn 'def can_'`
      over the tree returns nothing, so the prefix never existed
- [x] 2.8 Stop presenting bare `tox` as a way to run the suite. `envlist` is
      py36–py39 + pypy3 while CI tests only 3.12, so `tox` fails on absent interpreters
      instead of running tests. AGENTS.md now points at `tox -e py312` / `tox -e flake8`
- [x] 2.9 Correct `--coverage` in README.rst: it starts, stops and saves a coverage
      session but never calls `report()`, so it writes `.coverage` and prints nothing

- [x] 2.10 Document how to select what runs in README.rst. The README covered `-s`,
      `--show-all-expects`, `-c`, `--xunit-results`, `--coverage` and the reporters, but
      not `-p`, `-t` or `-m` -- the flags real usage reaches for first. Verified against a
      throwaway spec tree by executing every command in the section, and recorded the two
      non-obvious semantics: `-p "re:..."` is anchored at the end only
      (`re.search(f'{pattern}$', ...)` in `runner.py`), while `-t "re:..."` is anchored at
      both ends (`re.compile(f'^{name}$')` in `utils.py`) and is also matched against the
      spaced form of the case name

## 3. Public-repository audit

- [x] 3.1 Grep every added document for internal product names, tracker URLs, hostnames
      and infrastructure detail; the repository is public and rules borrowed from a
      downstream project must be generalised, not copied
      - The back-filled live specs named an internal downstream harness. Its requirement
        was dropped from `openspec/specs/live-server-linger/spec.md` — a consumer's
        obligation is not Spektrum's to specify — and the remaining mentions in the
        archived proposal, design, tasks and delta were generalised
- [x] 3.2 Apply the same grep to the commit messages on the branch, not only the files
- [ ] 3.3 Read each document once as an outside contributor with no downstream context,
      and cut anything that only makes sense from the inside

## 4. Open questions to settle before finishing

- [x] 4.1 Decide whether `CONTRIBUTING.md` is wanted, or whether `openspec/project.md`
      already covers that ground (see design.md — Open Questions)
      - Wanted. `openspec/project.md` is written for someone already inside the workflow
        and is not a document a first-time outside contributor will find. CONTRIBUTING.md
        is the conventional entry point on a public repo; it links to project.md for the
        detail rather than restating it
- [x] 4.2 Decide whether to add `.github/pull_request_template.md`
      - Yes. The red-then-green rule only works if the PR form asks for both counts, and
        the two-suite checklist is the one thing a contributor cannot guess
- [x] 4.3 If either is wanted, write it and re-run the audit in section 3
      - Both written; the section 3 grep was re-run over them and over the revised
        README.rst and AGENTS.md

## 5. Verification

- [x] 5.1 Confirm no file under `spektrum/` or `tests/` was modified — this change is
      documentation and tooling only
- [x] 5.2 Run both suites and confirm the counts are unchanged from master: pytest
      `1 passed`, and `python -m spektrum -s tests/live/` 22 passed / 121 expectations.
      The branch touches no code, so both are unchanged by construction
- [x] 5.3 Run `tox -e flake8` and confirm clean (`python -m flake8 spektrum tests`, exit 0)
- [x] 5.4 Confirm no version bump and no release-note entry are included; this change
      ships nothing to users of the library

## 6. Review

- [ ] 6.1 Rebase onto current `master` and resolve any drift in the file map
- [ ] 6.2 Squash to a single commit, folding the verification counts and the reasoning
      from the intermediate messages into the body. Note the two oldest commits on this
      branch are already on `origin/MQ-3301`, so this rewrites published history and needs
      a force-push — confirm nobody has built on the branch first
- [ ] 6.3 Open the PR against `liquidweb/Spektrum`, base `master`, describing it as
      docs-and-tooling-only with no behaviour change
- [ ] 6.4 Archive this change once merged (`openspec archive`)
