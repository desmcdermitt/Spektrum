# Contributing

Spektrum is a Python testing framework inspired by RSpec and Jasmine. Contributions are
welcome — this file covers how to get one reviewed.

## Development setup

```shell
pip install -r dev-requirements.txt
```

Build, test and lint commands are listed in [AGENTS.md](AGENTS.md#commands) and not
repeated here.

## Spektrum is a library

A defect here does not fail one test. It changes what every suite built on Spektrum
reports, and every consumer picks it up at once. [openspec/project.md](openspec/project.md)
is the full working agreement — the red-then-green rule, scope discipline, and the
reporter compatibility contract. Read it before opening a PR.

The short version:

- **Prove the change.** A behavioural change needs a test that fails without it and passes
  with it. Put both counts in the PR.
- **Run both suites.** `tests/` has a pytest suite *and* a suite of Spektrum specs that
  pytest does not collect. See [AGENTS.md](AGENTS.md#two-suites-and-neither-runs-the-other).
- **Keep the diff to the change.** Pre-existing problems in a file you touched are worth
  reporting, not worth widening the diff for. Don't reformat existing code.

## Opening a PR

Use the PR template — link the issue it addresses and describe how you verified the change.
Base branch is `master`.

## Before you open a PR

- [ ] `python -m pytest tests -q` passes — record the count
- [ ] `python -m spektrum -s tests/live/` passes — record the count. A failing case does
      exit 1, but a **nonexistent search path** exits 0 under `python -m` (the `spektrum`
      console script exits 1 there), so a typo'd path looks like success
- [ ] `tox -e flake8` is clean (max line length 100)
- [ ] A test proves the change: observed failing before, passing after
- [ ] Docs (`README.rst`, `AGENTS.md`, `docs/`) updated if this changes how the project is
      built, run, or used
- [ ] Squashed to a single commit, with the evidence above folded into the message body.
      Work in as many commits as you like locally; a PR is one commit
