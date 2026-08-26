# Coding Conventions — Spektrum

Python standards for this repo. There is no automated checker wired up here, so these
apply by review and by judgement.

**Spektrum is older than several of these rules.** Existing code violates some of them —
`except Exception:` in `Expectation.raise_a`, mixed quote delimiters, missing type hints.
That is deliberate and is **not** a backlog to burn down inside an unrelated change. Apply
these to code you add or modify; leave the rest alone. See "Scope discipline" in
[openspec/project.md](../openspec/project.md).

## Mechanical

Lint with `tox -e flake8`. Max line length **100**. `H301,H405,H702,W503` ignored;
`spektrum/vendor/*` excluded and never reformatted.

- **Quotes** — single quotes as the delimiter, `'''` for docstrings. Only the *outer*
  delimiter matters; an inner `"` is fine.
- **Trailing commas** — required on every multi-line construct: parenthesised imports,
  dict/list/tuple literals. Single-line collections do not need one.
- **Exceptions** — no bare `except:`, no base `except Exception:`. Catch specific types.
  Catch *every* type the guarded call can raise: an AST walk that raises `AttributeError`
  on one shape may raise `IndexError` on another.
- **No `print()` for diagnostics** — use `spektrum.logger`. Reporters under `reporting/`
  are the exception: writing to stdout is what they are for.
- **`await` only inside `async def`.**
- **Naming** — PascalCase classes, snake_case functions and variables. Dunders and
  ALL_CAPS constants exempt. No `Common` in a class name.
- **Pythonic** — `is None` not `== None`; truthiness not `len(x) == 0`; direct iteration
  not `range(len(...))`.
- **Imports** — a multi-item `from x import a, b` uses the parenthesised multi-line form
  with a trailing comma.
- **Every package folder needs `__init__.py`** (may be empty).

## Type hints

Newer modules (`runner.py`, parts of `reporting/`) are annotated; older ones are not.
Annotate what you add.

- Parameters get annotations; a function returning non-None annotates its return.
  `-> None` is never required.
- `Optional[T]`, `List[T]`, `Dict[K, V]` — not bare `list` / `dict`, not `Union[T, None]`.
- `**kwargs` may be left untyped.

## Design

- **KISS** — no indirection that earns nothing: alias-only properties, a variable assigned
  only to be returned, a wrapper used once.
- **YAGNI** — no speculative parameters or abstractions for a single implementation.
- **SRP** — one responsibility per unit.
- **Composition over inheritance** — do not subclass merely to borrow a method.
- **DRY** — lift genuinely duplicated logic; do not over-abstract two lines that merely
  look alike.

## Library-specific rules

These matter more here than they would in an application.

- **Guard defensively at the boundary, then trust inward.** `expect.py` reads AST nodes
  produced by arbitrary user source. Validate the shape you require before walking it,
  rather than walking it and catching the fallout.
- **A reporter must never be able to kill a run.** Everything under `reporting/` executes
  after — or, for TestRail and the live view, *during* — tests that have already produced
  results. An exception there destroys work that was already complete and unrecoverable.
  Rendering code should degrade to a less informative line, never raise.
- **Do not change what a public property returns without checking its consumers.**
  Returning `None` where a caller expects a string relocates a crash rather than fixing
  it; give the caller a sensible fallback in the same change.
- **Every behavioural change needs a red-then-green test.** See
  [openspec/project.md](../openspec/project.md).

## Test conventions

`tests/` holds two suites: `tests/test_runner.py` is pytest, and `tests/live/` is
Spektrum specs run by the CLI. Neither runner sees the other's tests — see
[AGENTS.md](../AGENTS.md). New unit-level work goes in the pytest suite.

- `pytest.mark.parametrize` with explicit `ids` for shape sweeps; a failing id should name
  the case without opening the file.
- Prefer constructing units directly (`ExpectParams`, `Expectation`, `ExpectFormatData`)
  over driving the whole runner, so a failure localises.
- A "does not raise" test needs no assertion body — the call raising *is* the failure.
- When a fix could be satisfied by returning nothing, add a control test asserting the
  healthy path still produces real output.
