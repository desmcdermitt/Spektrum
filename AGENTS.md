# Spektrum

An async Python test framework: spec classes, fluent assertions, and pluggable reporters,
driven by the `spektrum` CLI.

This file is the entry point for any agent working in the repo. `CLAUDE.md` is a symlink
to it.

## MANDATORY — read before changing anything

- **Any change** → [openspec/project.md](openspec/project.md) — the PR procedure, the
  red-then-green rule, one-commit-per-PR, scope discipline, and the reporter
  compatibility contract.
- **Any Python change** → [.claude/conventions.md](.claude/conventions.md).

Spektrum is a library. A defect does not fail one test; it changes what every suite built
on it reports, and every consumer picks it up at once. Treat the blast radius as the
default assumption, not the exception.

## Architecture in a paragraph

`spektrum.__main__` parses arguments and hands a search path to `SpektrumRunner`
(`runner.py`), which uses `pike` to discover `Spec` subclasses under that path. Specs form
a tree — a spec's nested `Spec` subclasses become child specs — and the runner walks it
asynchronously, running the lifecycle hooks around each case with concurrency bounded by
semaphores. Each `expect()` / `require()` call builds an `Expectation` (`expect.py`),
registers it against the running spec, and records the **source expression** behind it by
inspecting the caller's frame and AST, so the reporter can print `value to equal 2` rather
than `1 to equal 2`. When the run finishes, the runner builds a report of
`SpecFormatData` / `CaseFormatData` / `ExpectFormatData` wrappers (`reporting/data.py`)
and hands that list to the console renderer, plus the xunit renderer when
`--xunit-results` is set. Two reporters never see it: TestRail is
driven per-case *during* the run, and the live view is fed from an event queue from before
discovery starts.

## What counts as a case

Not derivable at a glance, and easy to get wrong:

- Every **public instance method** that is not a lifecycle hook (`before_all`,
  `before_each`, `after_each`, `after_all`) is a case. There is no naming prefix to opt
  in, and no decorator to opt out — `@skip`, `@incomplete` and `@metadata` all leave the
  method a case.
- `_`-prefixed methods are skipped, as is anything that isn't a plain function on the
  class: `@classmethod`, `@staticmethod` and `@property` members are never cases.
- A `DATASET` on the class replaces each case with one per dataset key, so the original
  case name never runs.
- Nested `Spec` subclasses become child specs; `@fixture`-decorated ones are skipped.

## File map

```
.
├── spektrum/
│   ├── __init__.py        # public surface: Spec, DataSpec, expect, require, fixture,
│   │                      #   skip, skip_if, incomplete, metadata, depends_on, concurrency
│   ├── __main__.py        # the CLI (console_scripts: spektrum)
│   ├── runner.py          # SpektrumRunner + the async spec/case execution tree
│   ├── spec.py            # Spec, DataSpec, the decorators, case/spec filtering
│   ├── expect.py          # Expectation/Requirement, the matchers, and the AST-based
│   │                      #   source-expression lookup (ExpectParams)
│   ├── reporting/
│   │   ├── core.py        # ReportManager — fans out to the enabled reporters
│   │   ├── data.py        # the *FormatData wrappers every reporter renders from
│   │   ├── pretty.py      # default console output
│   │   ├── testrail.py    # TestRail — reached PER-CASE DURING a run
│   │   ├── xunit.py       # xunit XML for CI
│   │   ├── live.py        # LiveServer: the --live HTTP server, its SSE stream, and the
│   │   │                  #   page it serves
│   │   └── transport.py   # RetryTransport — an httpx transport with retries, used for
│   │                      #   outbound reporter HTTP, NOT part of the live view
│   ├── exceptions.py, logger.py, utils.py
│   └── vendor/            # vendored ast_decompiler — never reformat, excluded from lint
├── tests/
│   ├── test_runner.py     # pytest: drives SpektrumRunner over tests/example_data
│   ├── example_data/      # sample Spec classes used as runner fixtures
│   └── live/              # Spektrum specs, run by the CLI — see "Two suites" below
├── docs/                  # Sphinx source for the published user documentation
│   ├── index.rst          # toctree root
│   ├── using/, writing_tests/, parallel/, reporting/, release_notes/, maintenance/
│   └── conf.py            # carries the version too — .bumpversion.cfg updates both
├── openspec/              # spec-driven-development artifacts
│   ├── project.md         # the rules — read this first
│   ├── config.yaml        # schema: spec-driven
│   ├── specs/             # capability baseline (the six live-view capabilities)
│   └── changes/           # in-flight proposals, plus archive/ of completed ones
├── tools/run_tests.sh     # stale — calls nosetests; use the commands below instead
├── .claude/
│   ├── conventions.md     # Python standards
│   └── skills/cut-a-release/  # "let's cut a new release" -> tools/release.sh
├── tox.ini                # pytest+coverage envs, the flake8 env, and the flake8 config
└── setup.py               # version lives here and in .bumpversion.cfg
```

## Two suites, and neither runs the other

`tests/` holds two suites with different runners. Running one and calling it green is the
most common way to break this repo.

| Suite | Runner | What it covers |
|---|---|---|
| `tests/test_runner.py` | **pytest** | unit-level: constructs runner/report objects directly |
| `tests/live/` | **the `spektrum` CLI** | the live view end-to-end, as `Spec` classes |

`pytest tests` does not collect `tests/live/` at all — those are `Spec` subclasses, and
pytest has no idea what to do with them. Run both:

```shell
python -m pytest tests -q          # the pytest suite
python -m spektrum -s tests/live/  # the spec suite
```

The split is deliberate. Unit-level work belongs in pytest, because the framework cannot
be its own harness when the code under test is what renders the result — a bug in
reporting would corrupt the report that tells you about the bug. The live view is the
exception: what it emits *is* observable only from a real run, so those tests drive the
real CLI and assert on what a real run produces. `tests/example_data/` holds spec classes
too, but those are *fixtures the runner executes*, not assertions.

Test the units directly. `ExpectParams`, `Expectation` and the `*FormatData` wrappers can
all be constructed by hand. Note `Expectation(...)` built directly does **not** register
with a spec — `_add_expect_to_spec()` is called only by the `expect()` and `require()`
factories — which is what lets a test exercise a pathological assertion without poisoning
the live report.

## Commands

```shell
pip install -r dev-requirements.txt

python -m pytest tests -q            # pytest suite
python -m spektrum -s tests/live/    # spec suite (see above — pytest skips these)
tox -e flake8                        # lint (max line length 100)

spektrum -s <path>                   # run specs at a path
spektrum -s <path> --show-all-expects   # + one line per assertion
```

Useful CLI flags: `-p/--select-module`, `-t/--select-tests`, `-m/--select-by-metadata` /
`--exclude-by-metadata`, `-c/--concurrency`, `--dry-run`, `--coverage`,
`--xunit-results`, `--live` / `--live-port` / `--live-linger`, and the `--tr-*` TestRail
options.

`tox`'s `envlist` is `py{36,37,38,39},pypy3,flake8` — stale, so a bare `tox` fails on
every interpreter that isn't installed and reports red even though `flake8` passed. CI
runs `tox -e py312` and `tox -e flake8` (`.travis.yml`); use those, or call `pytest`
directly. `tox -e py312` works despite py312 being absent from `envlist`.

> `--show-all-expects` matters more than it looks. Consumers that wrap the CLI may enable
> it unconditionally, so the per-assertion rendering path can be live on every run for
> those users. A defect reachable only under that flag is not an edge case downstream.

## Specs

`openspec/specs/` is the capability baseline — currently the six capabilities behind the
live view (`--live`), all of them released. Behaviour described there is a contract that
shipped, so read the relevant spec before changing `reporting/live.py`, `transport.py`, or
the runner's live-event emission. Completed proposals live in
`openspec/changes/archive/`; anything in flight sits directly under `openspec/changes/`.

```shell
openspec list                # in-flight changes and their task progress
openspec validate --all      # every spec and change
```

## Known sharp edges

- A nested class that is **not** a `Spec` subclass crashes discovery:
  `spec_filter` in `spec.py` reads `is_fixture` off the class before checking
  `issubclass(other, Spec)`, so a plain helper class inside a spec raises
  `AttributeError`. Put helpers at module level.
- `python -m spektrum` exits 0 on a nonexistent search path — `__main__` discards
  `main()`'s return value, while the `spektrum` console script (`sys.exit(main())`) exits
  1. A failing case exits 1 either way. Check the reported count, not just the exit code.

## Versions and releasing

The repo disagrees with itself about supported Python: `setup.py` says
`python_requires='>=3.5'` with a lone 3.7 classifier, `tox.ini`'s `envlist` says
py36–py39 + pypy3, and CI tests only 3.12. Treat **3.12 as the supported version** — it is
the only one actually exercised — and don't take the other two as constraints without
asking.

**Pushing a tag to `liquidweb/Spektrum` is the release.** Travis builds every tag and
uploads to PyPI (`deploy.on.tags: true` in `.travis.yml`). Nothing else publishes — not
merging to `master`, not running `bumpversion`. The inverse worry is the one to drop: a
version bump merged in an ordinary PR ships nothing at all, which is exactly how 1.2.2 and
1.3.0 came to sit on `master` having never reached PyPI.

Use `tools/release.sh`. Run it with no arguments and it detects the state and does the
next right thing; `status`, `release <part>` and `publish` are there when you already know
it. In a session, "let's cut a new release" reaches it through
[.claude/skills/cut-a-release/](.claude/skills/cut-a-release/SKILL.md) — drive the script,
never reproduce its steps. It refuses rather than warns.

Every PR adds its own entry under `Next Release` in `docs/release_notes/index.rst`. The
release renames that section to the version it becomes; an empty one is refused.

The two traps the script exists to close: `bumpversion` tags the commit it runs on, which
on a branch is the pre-merge commit the merge then rewrites; and `git push origin --tags`
sends the tag to a personal fork that CI does not watch. Full process:
[docs/maintenance/index.rst](docs/maintenance/index.rst).

## See also

- [README.rst](README.rst) — user-facing intro.
- [docs/](docs/) — Sphinx source for the published documentation.
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to get a change reviewed.
- [openspec/project.md](openspec/project.md) — PR procedure and compatibility contract.
