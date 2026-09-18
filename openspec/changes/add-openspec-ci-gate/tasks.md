## 1. Confirm the ground the gate stands on

- [ ] 1.1 Re-run `openspec validate --all --strict` on current `master` and record the item
      count and exit code. It must be 0 — the whole ordering argument in design.md — Migration
      Plan is that the gate debuts green, and if it does not, fix the artifacts before adding
      the workflow.
- [ ] 1.2 Confirm `.github/` tracks no workflow (`git ls-files .github`), so this one is
      genuinely the first and is not duplicating or shadowing an existing check. Note that
      COS-29 removes the pull request template, so `.github/` may be empty.
- [ ] 1.3 Confirm Travis still builds pull requests, by finding a recent build on a merged PR.
      `enforce-sdd-and-audit-docs` task 1.1 recorded a maintainer verifying this against
      MQ-3300; re-verify rather than inherit the claim, because the whole
      one-job-per-concern split assumes Travis is still the lane that runs tests.
- [ ] 1.4 Verify `@fission-ai/openspec@^1.12.0` resolves and that the unscoped `openspec`
      package is a different project: `npm view @fission-ai/openspec version` and
      `npm view openspec name repository`. Record both, so the package choice in
      design.md is evidenced rather than asserted.
- [ ] 1.5 Re-read the org requirement as leadership stated it and confirm the implemented rule
      is that rule and nothing more: a spec file in the diff, or an `sdd-exception: (.+)` line
      in the PR description. Any local addition — a path list, a second marker, a severity
      tier — is out of contract and has to be justified or dropped.

## 2. Job 1 — artifact validation

- [ ] 2.1 Add `.github/workflows/` with a `pull_request`-triggered workflow named for the
      process concern it checks, `permissions: contents: read`, and a job whose name identifies
      it as the artifact-validation check. Verify the file parses as a workflow —
      `actionlint`, or push the branch and confirm Actions lists the workflow rather than
      reporting an invalid file.
- [ ] 2.2 Install the CLI as `@fission-ai/openspec@^1.12.0` and run
      `openspec validate --all --strict`. Verify by reading the job log: the installed version
      is 1.12.x and the command's exit code is the job's result.
- [ ] 2.3 Prove the job fails on a malformed artifact. On a scratch branch, break one
      requirement (delete a spec's only scenario), push, and confirm the job goes red; revert
      and confirm it goes green. Record both run URLs — this is the red-then-green evidence
      `openspec/project.md` asks for, applied to CI rather than to a test.
- [ ] 2.4 Prove `--strict` is doing work: confirm the artifact from 2.3 that fails under
      `--strict` is one that bare `--all` accepts, so the flag is justified by observation
      rather than by preference.
- [ ] 2.5 Prove an exception line does not waive validation: open a pull request that carries
      both a valid `sdd-exception:` line and the malformed artifact from 2.3, and confirm job 1
      is still red while job 2 is green. This is the one interaction between the two jobs that
      the spec pins down, so it needs a run URL rather than an argument.

## 3. Job 2 — the spec-file-or-exception gate

- [ ] 3.1 Add the second job with `fetch-depth: 0`, taking the diff from
      `github.event.pull_request.base.sha` and `github.event.pull_request.head.sha` via
      `git diff --name-only`. Verify by printing the resolved SHAs and the file list in the log
      and checking them against the pull request's own Files-changed tab.
- [ ] 3.2 Implement condition 1 as the spec-file test: a path matching
      `openspec/changes/*/specs/**/spec.md` or `openspec/specs/**/spec.md`, added or modified.
      Verify a `proposal.md`, `design.md`, `tasks.md` or `.openspec.yaml` does not match, and
      that no other path under `openspec/` does either — the narrowed definition is the point
      of the rule, so an accidentally broad glob defeats it.
- [ ] 3.3 Implement condition 2 as the exception test: match `sdd-exception: (.+)` against
      `github.event.pull_request.body`, line-anchored, and require the captured text to be
      non-empty after trimming whitespace. Verify a bare `sdd-exception:` and
      `sdd-exception:` followed by spaces both fail to match. Pass the body through the
      environment rather than interpolating it into the script — it is author-controlled text.
- [ ] 3.4 Echo the captured reason into the job's output when condition 2 carries the verdict,
      and make the job's summary say which condition passed. Verify from a real run's log that
      the reason is legible there and not only in the pull request's description.
- [ ] 3.5 Implement the verdict: pass if either condition holds; otherwise fail with a non-zero
      exit — no `::warning`, no `exit 0` fallback anywhere in the step. There is no path
      exemption list and no path allowance of any kind; verify by grepping the finished workflow
      for path literals and confirming the only ones are the two spec-file globs.
- [ ] 3.6 Make the failure message state both ways to satisfy the rule — add or modify a
      `spec.md` under `openspec/changes/<change>/specs/`, or add an `sdd-exception: <reason>`
      line to the description — and tell the author to re-run the check after editing the
      description, because a body edit does not re-trigger the workflow. Verify against a real
      failing run's log, not by reading the script.
- [ ] 3.7 Extract the logic into a shell script under `tools/` if it exceeds what is readable
      inline, so it can be run locally against two SHAs and a description file. Verify by
      running it on this branch and on one of the merge commits in recent history and comparing
      the verdicts with what the workflow reports.

## 4. Prove the contract, scenario by scenario

- [ ] 4.1 Walk the `sdd-ci-gate` spec and build a table of its 29 scenarios against how each is
      verified: an executed run, a local run of the 3.7 script, or a reasoned argument. Any
      scenario with no entry is either untested or unspecifiable, and both need an answer
      before the PR opens.
- [ ] 4.2 Exercise condition 1 as real pull requests against a scratch branch, one per case:
      a `spec.md` under `openspec/changes/<change>/specs/` alone passes; a `spec.md` under
      `openspec/specs/` (the archive shape) passes; `spektrum/` plus a spec delta passes;
      `spektrum/` with no spec file and no exception fails; `setup.py` alone fails; a file in a
      brand-new top-level directory fails. Record the run URL for each.
- [ ] 4.3 Prove the exception path passes: open a pull request that touches only `spektrum/`,
      put `sdd-exception: dependency bump, no behaviour change` in its description, and confirm
      job 2 is green **and** the log contains the captured reason. This is the half of the rule
      that has never been exercised in this repository, so it gets its own run URL.
- [ ] 4.4 Prove an empty exception fails: the same pull request with the description reduced to
      a bare `sdd-exception:`, and again with `sdd-exception:` followed only by whitespace.
      Both must be red. Then add a reason and re-run, and confirm it goes green — red-then-green
      on the exception path itself.
- [ ] 4.5 Prove a label is not an exception: apply any label to a failing pull request from 4.2
      and confirm the verdict does not change. The gate reads the description only, and the
      superseded `no-spec` label plan makes this the case most likely to be assumed to work.
- [ ] 4.6 Prove the proposal-stage case: a pull request adding only `proposal.md`, `design.md`
      and `tasks.md` for a new change must fail; the same pull request with
      `sdd-exception: proposal stage, spec deltas follow` must pass with that reason in the log.
      Record both runs — this is the case the narrowed spec-file definition newly catches, and
      the pair is the evidence it is a recorded stage rather than an obstacle.
- [ ] 4.7 Prove the `base..head` rule with a two-commit pull request — the spec delta in the
      first commit, the `spektrum/` edit in the second — and confirm it passes. Then squash it
      to one commit and confirm the verdict is unchanged. This is the scenario a per-commit rule
      would fail, so it is the one that most needs a run URL.
- [ ] 4.8 Prove the deletion case: a pull request touching `spektrum/` whose only spec-file
      change deletes an existing `spec.md`, with no exception line, must fail.
- [ ] 4.9 Prove the staleness caveat is honest: on a failing pull request, add the exception
      line to the description without pushing, and confirm the check stays red until it is
      re-run. Check the failure message from 3.6 actually told the author this.
- [ ] 4.10 Prove the fork path. Open one of the above pull requests from the personal fork and
- [ ] 4.11 Prove that editing the description alone flips the verdict with no push, and that the "Re-run" button does NOT: a re-run replays the original `pull_request` payload, so `github.event.pull_request.body` still holds the body the run was triggered with. Verified by editing a description, re-running, and watching the gate fail with the pre-edit body
- [ ] 4.12 Keep `types: [opened, synchronize, reopened, edited]` on the trigger for that reason; verify two runs exist for one head SHA after a description-only edit
      confirm both jobs run to a verdict with a read-only token and no secrets available,
      including reading the description from the event payload. If any step needs a credential,
      that step is wrong — design.md rules that out.

## 5. Keep the gate non-blocking, and say so

- [ ] 5.1 Confirm neither job is a required status check: read the branch-protection settings
      for `master` on `liquidweb/Spektrum` before and after, and confirm they are byte-identical.
      Verify a red run is still mergeable using one of the deliberately failing pull requests
      from 4.2 — without merging it.
- [ ] 5.2 Add a paragraph to `CONTRIBUTING.md`: Travis owns tests, lint and the tagged deploy;
      this workflow owns process; a spec file or an `sdd-exception: <reason>` line satisfies it;
      a red process check does not block a merge and whoever merges over it owns that call.
      Include the exception line verbatim so it can be copied. Verify by reading it as a
      first-time contributor and checking it answers "which red build matters" and "what do I
      write if I have no spec" without following a link.
- [ ] 5.3 Do NOT add the exception line to a pull request template — COS-29 removes the
      template guild-wide, and a template shipping a pre-written `sdd-exception:` line would
      satisfy the gate on every pull request automatically, which is the same as having no
      gate. Instead verify `CONTRIBUTING.md` and the gate's failure message each teach the
      line on their own, so an author meets it either before or at the point of failing.
- [ ] 5.4 Leave a comment at the top of the workflow recording two things the next person will
      otherwise undo: the rule is org-level and is exactly two conditions, so adding a path
      exemption list puts this repository out of contract; and "spec file" deliberately excludes
      `proposal.md`. Point at this change rather than restating design.md.

## 6. Retire the superseded plan and the prior art

- [ ] 6.1 Strike tasks 5.1–5.4 from `openspec/changes/enforce-sdd-and-audit-docs/tasks.md` and
      note in its design.md that `add-openspec-ci-gate` owns the gate. Be precise about what is
      superseded: the `^spektrum/` watched path, the missing `--strict`, and describing the
      check as merge-blocking. Its escape hatch is **not** superseded — wanting a way for an
      author to declare "no spec, and here is why" was correct and matches the org rule; only
      the mechanism is refined, from a `no-spec` label that records no reason to an
      `sdd-exception: (.+)` line that captures one and is echoed into the log. Verify
      `openspec validate enforce-sdd-and-audit-docs --strict` still passes after the edit.
- [ ] 6.2 Delete the uncommitted `.github/workflows/spec-driven-development.yml` from whatever
      working tree still holds it, or overwrite it with the version this change lands. Verify
      nothing installs the unscoped `openspec` package anywhere in the repository:
      `git grep -n 'install.*openspec'` shows only the scoped name.
- [ ] 6.3 Check the other in-flight changes for CI claims this change falsifies —
      `enforce-release-notes-and-cadence` puts its release-notes gate on Travis, which stays
      true and should stay stated that way. Do not widen this change to move it.

## 7. Verification

- [ ] 7.1 `openspec validate add-openspec-ci-gate --strict` passes.
- [ ] 7.2 `openspec validate --all --strict` passes, and the item count is the pre-change count
      plus one.
- [ ] 7.3 Confirm no file under `spektrum/` or `tests/` was modified: `git diff --stat` against
      the merge base lists only `.github/`, `openspec/`, `CONTRIBUTING.md` and anything added
      under `tools/`.
- [ ] 7.4 Confirm `.travis.yml` and `tox.ini` are untouched, so the test and deploy lanes are
      demonstrably unchanged.
- [ ] 7.5 `python -m pytest tests -q` and `python -m spektrum -s tests/live/` — record both
      counts and confirm they match the counts before the change. Required by
      `openspec/project.md` regardless of the change being CI-only, and cheap.
- [ ] 7.6 Public-repository audit: grep every added file for internal product names, private
      hostnames, tracker URLs and tokens, and apply the same grep to this branch's commit
      messages. The workflow file will be read by anyone browsing a public repository. Include
      the exception text from the test runs in this sweep — it is prose written into a public
      build log.

## 8. Review and land

- [ ] 8.1 Read the workflow once as a maintainer of a sibling repository and ask whether it
      ports with no edits at all. The two-condition rule contains no repository-specific data,
      so anything Spektrum-specific that leaked into the logic is a defect, not a setting.
- [ ] 8.2 Rebase onto current `master` and re-run task 1.1, in case an artifact landed
      meanwhile that fails strict validation.
- [ ] 8.3 Squash to a single commit, keeping in the body: the run URLs from 2.3, 2.5 and
      4.2–4.10, the package-identity evidence from 1.4, and the decision that the gate is not a
      required check.
- [ ] 8.4 Open the PR against `liquidweb/Spektrum`, base `master`, describing it as CI and
      process only with no library behaviour change, and stating plainly that the new check does
      not block merges. It needs no `sdd-exception:` line — it adds a spec delta and satisfies
      condition 1 on its own.
- [ ] 8.5 Archive this change once merged (`openspec archive add-openspec-ci-gate`), which
      promotes `sdd-ci-gate` into `openspec/specs/` — and which, by the baseline half of the
      spec-file definition, satisfies the gate by construction.
