**Issue:** <!-- Link the issue this addresses, or say why there isn't one. -->

## Why

<!-- What problem does this solve? One sentence is enough if the issue has the detail. -->

## What

<!-- What changed? Bullet points of the approach taken. -->

### Blast radius

<!-- Spektrum is a library: which consumers see this? e.g. reporters only / the runner /
the public API in spektrum/__init__.py / a CLI flag's behaviour. -->

## Reading guide

<!-- Optional for a small change. For anything touching more than one file, map it for
reviewers before they read the diff. -->

| File | What to look at | Why |
|---|---|---|
| `` | … | … |

## Test plan

**Red-then-green** (required for a behavioural change — see
[openspec/project.md](../openspec/project.md)):

- Failing without the change: <!-- paste the count -->
- Passing with the change: <!-- paste the count -->

**Automated tests added/updated:**
- [ ] …

**Manual verification steps:**
1. …

## Checklist

- [ ] `python -m pytest tests -q` — paste the count
- [ ] `python -m spektrum -s tests/live/` — paste the count (pytest does not collect
      these, and under `python -m` a nonexistent search path exits 0, so the count is the
      only proof the suite ran)
- [ ] `tox -e flake8` clean
- [ ] Docs updated (`README.rst` / `AGENTS.md` / `docs/`) if this changes how the project
      is built, run, or used
- [ ] Squashed to a single commit (see
      [openspec/project.md](../openspec/project.md) — Before opening a PR, step 5)
- [ ] No version bump unless this PR is the release
- [ ] No secrets, tokens, or real customer data included
