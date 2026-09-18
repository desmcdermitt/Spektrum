## Context

See proposal.md — Why for the motivation, and for the org requirement this gate implements
verbatim: a spec file in the diff, or an `sdd-exception: (.+)` line in the PR description. Four
constraints shape the approach.

**The CLI is a Node package and the only committed CI is Python-only.** `.travis.yml` is a
two-entry matrix (`TOXENV=py312`, `TOXENV=flake8`) on Python 3.12 that also owns the
tag-triggered PyPI deploy. Running `openspec` from there means installing a Node toolchain in a
build that otherwise has no use for one, on every push, including the tag builds that publish.

**The repository has no Actions workflow to extend.** `.github/` tracked exactly one file, a
pull request template, and COS-29 removes that guild-wide. Whatever this change adds is the
first workflow, so there is no existing job to hang a step off and no established conventions
to match.

**Pull requests come from personal forks.** `openspec/project.md` — Git records that `origin` is
a personal fork for both maintainers and that the canonical repository is `liquidweb/Spektrum`;
the recent history is a run of merges from `desmcdermitt/MQ-*`. On a fork-originated
`pull_request` event the automatically provided token is read-only and secrets do not resolve.
Any design that needs to write a label, post a review or read a secret is unavailable on the
majority of this repository's pull requests. The description, by contrast, arrives in the event
payload as `github.event.pull_request.body` and needs no API call at all.

**Prior art exists and is uncommitted.** A `.github/workflows/spec-driven-development.yml`
sits in a working tree and has never been committed. It is useful as a sketch and wrong in four
ways this change fixes: it runs `npm install -g openspec` (the unscoped package, a different
project entirely); its change-document job emits `::warning` and exits 0 by design; it triggers
the change-document logic on `grep -q '^spektrum/'`, a watched-path rule; and it calls
`openspec validate --all` without `--strict`. Because it was never committed, none of it has
ever run on a pull request — there is no operational history to reason from, only the sketch.

## Goals / Non-Goals

**Goals:**

- One workflow whose failures are all process failures, so a red check is self-explaining.
- The rule leadership stated, implemented literally, with no local additions: a spec file, or a
  reason. A sibling repository adopts it unchanged, because it names no source path.
- No dependency on any credential a fork-originated pull request cannot obtain.
- A first run that is green, so the gate's debut is not its own failure.

**Non-Goals:**

- Replacing or touching Travis. Tests, lint and the deploy stay where they are.
- Deciding *when* a spec is substantive. The gate checks presence of a `spec.md` and non-empty
  exception text. Whether the requirements are any good is a review question, and a heuristic
  that tried to judge it would be wrong in both directions.
- Judging whether a stated exception is a *good* reason. The gate requires that one exists and
  puts it in the log; a reviewer decides whether to accept it.
- Enforcing anything through branch protection. See the decision below.
- Back-filling the missing specs for the unspecified library surface. The gate makes the gap
  visible on new work; closing the existing gap is separate, scheduled work.

## Decisions

**A dedicated GitHub Actions workflow rather than a `tox` environment on Travis.**
`enforce-release-notes-and-cadence` chose Travis for its release-notes gate on the reasonable
grounds that Travis already runs `pull_request` builds, so a check there needs a `tox` env
rather than new infrastructure. That argument does not carry here, because that gate is pure
Python and this one has to execute a Node CLI. Adding Node to the Travis matrix slows every
build, including the tag build that publishes to PyPI, for a check with no bearing on whether
the code works. *Alternative considered:* a pure-Python path check inside Travis, needing no
Node. It could implement the two-condition rule but not `openspec validate --all --strict`,
which is the half that catches the malformed artifact — and splitting one gate across two CI
systems is worse than either placement.

**Two jobs, not one with two steps.** The verdicts are independent and so are their
prerequisites: validation needs Node and the CLI and does not need history; the change-document
rule needs full history, `git`, and the description from the event payload. As separate jobs
they run concurrently, and a failure names itself — "artifacts are valid" versus "a spec file
or a stated exception" — rather than pointing at a step inside a check called
`spec-driven-development`. A single job would also let the first failure mask the second, so an
author fixing a malformed spec would not learn until the next push that the spec file was
missing too.

**Two conditions and no exemption list.** This is the decision the whole contract turns on, and
it is leadership's, not ours: a pull request passes if its diff adds or modifies a spec file, or
its description carries `sdd-exception: (.+)` with text. Nothing else enters the verdict, and
there are no path carve-outs. An earlier draft of this change proposed an exemption list —
`openspec/`, `*.md`, `*.rst`, `docs/`, `README*`, `.claude/` — reasoning that a watched-path
rule fails open while an exemption list fails closed. The premise was right and the conclusion
is now unnecessary: the exception line fails closed too, and it does what no exemption list can,
which is record *why* this particular pull request has no spec. An exemption list also has to be
guessed in advance, maintained per repository, and looked up by every author wondering whether
`.coveragerc` is on it; the two-condition rule has nothing to look up and nothing to maintain.
*Alternative considered:* the `^spektrum/` watched path from the uncommitted sketch, which
`enforce-sdd-and-audit-docs` also specified. Rejected on the failure mode: this repository
already contains `tools/`, `setup.py` and `tox.ini`, none of which that pattern covers, and a
second package directory is a plausible future.

**A spec file means a `spec.md`, not any file under `openspec/`.** Condition 1 is satisfied by a
`spec.md` under `openspec/changes/<change>/specs/` or under `openspec/specs/`, and by nothing
else — a `proposal.md`, `design.md`, `tasks.md` or `.openspec.yaml` on its own does not count.
This reads leadership's "a spec file" literally, and the literal reading is the correct one: a
proposal states motivation, a spec states the contract. Accepting a proposal alone would let a
pull request present as spec-first while shipping no requirement, which is the precise gap the
gate exists to close. Including the baseline path matters too — `openspec archive` writes
`openspec/specs/`, so an archive pull request carries a spec file by construction and never
needs a waiver. *The case this newly catches* is a genuine one: work that opens with a proposal
before its deltas exist. That is a feature rather than an obstacle. The author writes
`sdd-exception: proposal stage, spec deltas follow`, the log records which stage the work is at,
and the alternative — counting `proposal.md` — would have let the same pull request pass while
saying nothing.

**The exception lives in the description and must carry a reason; the job echoes it.**
`enforce-sdd-and-audit-docs` paired its gate with a `no-spec` label and argued that a human
applying a label is honest about who made the judgment. **That instinct was right**, and it is
the same instinct leadership's rule encodes: there must be a way for an author to say "no spec
here" without lying or being blocked, and a person, not a heuristic, decides. What changes is
the mechanism, not the intent. A label is one click, it records no reason, and it is invisible
in the repository's history; the `sdd-exception: (.+)` line forces prose, is rendered where a
reviewer is already reading, and can be echoed into the job's output so the justification
survives in the build log rather than only in an editable field. A label is also unavailable in
practice — writing or reading one reliably from a fork-originated run is more privilege than
this event grants, while the description is already in the payload. So the rule requires
non-empty captured text: a bare `sdd-exception:` fails, which is deliberate, because a marker
with no reason is the label again in text form. *Alternative considered:* keeping the sketch's
advisory `::warning` + `exit 0`. Rejected: contributors calibrate on outcomes, and a check that
has never once failed is indistinguishable from no check.

**Red, visible, and not required.** Making the job a required status check would block merges,
which sounds like the stronger choice and is the wrong one for this repository at this moment.
Branch protection is repository configuration: it is not in the diff, so it cannot be reviewed,
cannot be reverted by a revert, and is invisible to anyone reading the tree. A gate that has
never run should not be handed the ability to stop all work on its first day, and the
maintainer count here means a wrongly-red gate would have nobody to appeal to. What remains is
the useful part — the check is on the pull request, the failure is legible, and merging past it
is a deliberate act by a named person. This is also deliberately the weak half of the pair:
because an author can always state an exception, a red gate means they neither wrote a spec nor
were willing to say why, which is worth seeing and still not worth blocking on. Promotion to
required is a later decision, informed by how often the gate is right; see Open Questions.

**`base..head` with `fetch-depth: 0`, using `git diff` and the event payload.** The diff is
taken between `github.event.pull_request.base.sha` and `github.event.pull_request.head.sha`,
which requires unshallowing the checkout. Per-commit evaluation is specifically excluded:
`openspec/project.md` — Before opening a PR, step 5 tells contributors to work in as many local
commits as they like and squash before review, and the recommended shape of that work is a spec
commit followed by an implementation commit. A per-commit rule would fail the exact workflow the
project asks for. *Alternative considered:* a marketplace changed-files action. Rejected on two
counts: it adds a third-party dependency with repository read access to a public repository for
work that two lines of `git` accomplish, and its fork-event behaviour is an extra thing to
verify. `git diff --name-only` against the two SHAs from the payload has no such questions.

**The description is read as of the run, and the failure message says so.** `pull_request`
fires on `opened`, `synchronize` and `reopened`, so editing the body after a red run does not
re-evaluate anything: the verdict stands until the check is re-run. This staleness is the one
sharp edge of reading the description, and the mitigation is in the failure text — it states
both ways to satisfy the rule *and* tells the author to re-run the check after editing the
description, because the most likely next action is exactly that edit. *Alternative considered:*
adding `types: [edited]` so a body edit re-triggers the workflow. Rejected for now: it re-runs
the whole workflow on every title and description touch, including ones that cannot change the
verdict, and the instruction in the failure message costs nothing. Worth revisiting if authors
are observed to be confused by it rather than merely inconvenienced.

**`@fission-ai/openspec@^1.12.0`, installed per run, not vendored.** The scoped name is the
package that provides this CLI; the unscoped `openspec` on npm is unrelated, and the sketch
installs it. The caret pin takes 1.x fixes without a configuration change and requires a
deliberate edit for 2.x, which matters because `--strict` semantics are exactly the kind of
thing a major version revises. 1.12.0 is the version the specs in this repository were authored
and validated against. *Alternative considered:* an exact pin. Rejected as needless churn for a
non-blocking check; a 1.x regression costs a red check, not a blocked repository.

## Risks / Trade-offs

- **Every docs-only, typo-fix and dependency-bump pull request now needs an exception line, so
  the gate fires more often than a path-based rule would** → accepted, and it is the point. The
  cost is one line of prose per waived pull request; the return is that the reason exists at
  all. The old exemption list would have absorbed these silently and told nobody anything.
  This is also the false-positive rate that gets gates switched off, so it is the number to
  watch first: see Open Questions.
- **`sdd-exception:` becomes a rubber stamp — the same phrase pasted every time** → partly
  mitigated, not solved. Non-empty text is mechanically checkable; sincerity is not. The
  mitigations are that the text is rendered in the description where a reviewer reads it and
  echoed into the build log where it is permanent, so a pattern of thoughtless waivers is
  visible rather than hidden. If it happens, the answer is a review conversation, not a
  cleverer regex.
- **The narrowed spec-file definition fails proposal-stage pull requests that the broader rule
  would have passed** → intended. Those pull requests state the stage in the exception line,
  which is strictly more information than a silent pass. The risk worth naming is the opposite
  one: if proposal-only pull requests are the common case here, the exception rate will look
  alarming for a reason that is procedural rather than a process failure, so the log needs
  reading before the number is interpreted.
- **A body edit after a red run does not re-run the check, and an author reads the stale red as
  a bug** → the failure message tells them to re-run, and `types: [edited]` remains available if
  the instruction proves insufficient.
- **`--all --strict` covers the whole tree, so a pre-existing artifact defect fails a pull
  request that did not cause it** → this is intended and specified, and it is affordable
  precisely because the tree is clean today: validation exits 0 across all 10 items. The
  alternative, validating only changed artifacts, lets a defect on `master` sit indefinitely.
- **The npm registry or a 1.x CLI regression turns the gate red for reasons unrelated to the
  pull request** → non-blocking absorbs it. On a required check this would be an outage.
- **The GitHub workflow and the GitLab template in COS-30 drift apart** → the requirements in
  `sdd-ci-gate` are the shared artifact, not either platform's configuration, and the two-
  condition rule has no per-repository data to diverge on. What legitimately differs is
  host-specific: `github.event.pull_request.body` versus the merge request's description.
- **A contributor cannot tell which red build matters** → the two jobs are named for the
  process concern they check, and `CONTRIBUTING.md` gains a paragraph stating that Travis owns
  tests, lint and the deploy while this workflow owns process and does not block a merge.
- **Nothing prevents a contributor from satisfying the gate with an empty `spec.md`** → an empty
  or requirement-less `spec.md` fails `--strict` in job 1, which closes the cheapest version of
  this. A well-formed but vacuous requirement still passes both jobs, and that is out of scope
  by design: presence is mechanically checkable, substance is a review judgment.

## Migration Plan

Nothing ships to users of the library and there is no deployment step. Ordering has one
constraint and one courtesy:

1. Land the workflow while `openspec validate --all --strict` still exits 0, so the first run
   is green. The pull request that introduces the gate adds
   `openspec/changes/add-openspec-ci-gate/specs/sdd-ci-gate/spec.md`, so it satisfies its own
   change-document job under the narrowed definition, with no exception line needed.
2. Strike tasks 5.1–5.4 from `enforce-sdd-and-audit-docs` in the same pull request or the next
   one, so the superseded plan does not get built a second time by someone working that change
   later. Record what is superseded and what is not: the `^spektrum/` watched path, the missing
   `--strict` and the merge-blocking framing are replaced; its escape hatch is kept, refined
   from a label to an `sdd-exception:` line that carries a reason.

Rollback is deleting one file. Neither job writes anything, so there is no state to unwind.

## Open Questions

- **Should the gate become a required check later, and on what evidence?** Deferrable: it
  changes no specification and no task here, and the answer needs run data the repository does
  not have yet. A reasonable trigger is a month of pull requests in which every red gate was
  correct.
- **What exception rate is too high?** The number is the gate's main health signal, and it has
  no baseline yet. Answerable after the first month across the repositories that adopt the step:
  if nearly every pull request is waived, the rule is landing on work it was not written for; if
  none is, the exception path may be too obscure to find.
- **Should `types: [edited]` be added so a description edit re-triggers the check?** Left out
  deliberately, with the instruction in the failure message as the mitigation. Revisit if
  authors are observed re-pushing empty commits to clear a stale red.
