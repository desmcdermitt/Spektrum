# Project rules — Spektrum

Spektrum is a **library**: a test framework other projects depend on. That single fact
drives every rule below. A defect here does not fail one test — it silently changes what
every suite built on it reports, and a breaking change lands in every consumer at once.

## Before opening a PR — MANDATORY

### 1. Prove the change with a red-then-green run

Every behavioural change needs a test that **fails without the change and passes with
it**, and the PR must show both numbers. A test written after the fix, never observed
failing, proves only that it agrees with the code as written.

The mechanical way to get both, without disturbing anything else in the tree:

```shell
git stash push -- <the source files you changed>
python -m pytest tests -q          # RED — record the count
git stash pop
python -m pytest tests -q          # GREEN — record the count
```

Substitute `python -m spektrum -s tests/live/` for the pytest line when the change is
covered by the spec suite instead — see the next section.

Paste both counts into the PR. Collection-only checks are not verification; only an
executed suite is.

### 2. Run **both** suites, not just your file

```shell
python -m pytest tests -q
python -m spektrum -s tests/live/
```

`tests/` holds two suites with different runners, and neither runs the other. `pytest`
does not collect `tests/live/` — those are `Spec` subclasses, so pytest silently
reports success while leaving them untouched. Running one suite and calling the tree green
is the easiest way to ship a regression here.

A reporting change can pass its own tests and still break the runner, because the
reporters are reached through `SpektrumRunner`, not directly. Both suites together are
cheap — there is no excuse for scoping it down.

### 3. Lint

```shell
tox -e flake8      # or: python -m flake8 spektrum tests
```

Max line length is 100; `H301,H405,H702,W503` are ignored. `spektrum/vendor/*` is
excluded and must stay that way — never reformat vendored code.

### 4. Any failure means no PR

A red suite is not a discussion. Fix it, or explain to the maintainer why the failure is
expected and let **them** decide — never rule a failure acceptable on your own.

### 5. Squash to a single commit

A PR is **one commit**. Work in as many commits as you like while the branch is local —
they are the record of how you got there — then collapse them before review:

```shell
git reset --soft $(git merge-base master HEAD)
git commit          # one subject, and a body that keeps the evidence
```

The body is where the intermediate messages go, not the bin. Fold in the counts from the
red-then-green run, anything a reviewer would otherwise have to reconstruct, and the
reasoning behind decisions that are not obvious from the diff.

Two cases where this needs care:

- **Commits already pushed.** Squashing rewrites published history and needs a
  force-push. Confirm nobody has built on the branch first, and never force-push a branch
  someone else is working from.
- **A change that is genuinely two changes.** If the diff cannot be described in one
  subject line without an "and", that is the signal to open two PRs, not to keep two
  commits in one.

### 6. Green → open the PR

Target `liquidweb/Spektrum`, base `master`. Paste every run into the PR body.

## Scope discipline

- **Fix only what the branch is for.** A checker or reviewer surfacing pre-existing
  problems in a file you touched is not a licence to widen the diff. Report them; open a
  separate issue.
- **Do not reformat.** This repo predates several conventions applied to newer code
  (`except Exception:` in `raise_a`, mixed quote styles). Leaving them is deliberate:
  churn buries the real change in review.
- **Never stage broadly.** `git add -A` can sweep up unrelated in-progress work. Stage
  explicit paths and check `git status` before committing.

## Compatibility

`ExpectParams`, `ExpectFormatData` and the reporters form the contract that downstream
output is rendered from. Before changing what a property returns, check the consumers:

- `spektrum/reporting/pretty.py` — the default console reporter.
- `spektrum/reporting/testrail.py` — reached **per-case during a run**, so a failure here
  can lose results already collected, mid-run, rather than merely at the end.
- `spektrum/reporting/xunit.py`, `live.py` — CI and live-view output.

Prefer widening a guard over changing a return type. Returning `None` where a caller
expects a string moves a crash into a downstream label rather than removing it.

## Git

- **Branch:** named for the issue or ticket being worked.
- **Commit subject:** `<id>: <description>`, imperative mood.
- **One commit per PR.** Squash before review — see *Before opening a PR*, step 5.
- **Base:** `master` on `liquidweb/Spektrum`. `origin` is normally a personal fork, so
  anything resolving `origin/HEAD` is looking at the wrong baseline.
- **Do not commit or push unless asked.**
