# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Spektrum Testing Framework

Python BDD testing framework inspired by RSpec/Jasmine. Created by LiquidWeb Quality Engineering.

## Development Commands

### Running Tests (the framework's own tests)
```bash
# Run all tests
spektrum -s tests/          # or: python -m spektrum -s tests/

# Run specific module or class
spektrum -p test_runner.TestClass

# Run specific test methods
spektrum -t "test_name1,test_name2"

# Run with concurrency
spektrum -c 4 -s tests/

# Dry run (discover without executing)
spektrum --dry-run -s tests/

# Run with coverage
spektrum --coverage -s tests/
```

### Quality and Packaging
```bash
flake8                           # Lint (100 char line limit, see tox.ini for ignore rules)
tox                              # Full test matrix (Python 3.6-3.9, PyPy3, flake8)
tox -e py39                      # Specific tox environment
pip install -e .                 # Install in development mode
bumpversion patch|minor|major    # Version bump
```

### Output Formats
```bash
spektrum --xunit-results results.xml
spektrum -m key=value            # Filter by metadata
spektrum --exclude-by-metadata key=value
spektrum --show-all-expects
```

### TestRail Integration
```bash
spektrum --tr-endpoint https://madqe.testrail.io \
         --tr-username <username> \
         --tr-apikey <api_key> \
         --tr-project 1 \
         --tr-suite 4 \
         --tr-run <run_id>
```

## Core Architecture

### Execution Flow
1. `SpektrumRunner.run()` (`runner.py`) uses `PikeManager` to discover all `Spec` subclasses in the search path
2. Specs are filtered by module name, metadata, or test name patterns
3. All discovered specs are instantiated and passed to `ReportManager.track_top_level()`
4. Tests execute asynchronously via `asyncio.gather()` with semaphore-controlled concurrency
5. Each test result flows through `ReportManager` → renderers (Pretty, XUnit, TestRail)

### Key Classes
- **`Spec`** (`spec.py`): Base class for all tests. Test methods prefixed with `test_`. Lifecycle: `before_all()` → `before_each()` → test → `after_each()` → `after_all()`. All lifecycle hooks and test methods support `async`.
- **`DataSpec`** (`spec.py`): Subclass of `Spec` for data-driven tests via `DATASET` dict — generates one test per dataset entry per test method.
- **`SpektrumRunner`** (`runner.py`): Orchestrates discovery, filtering, execution. Uses Pike for class discovery; supports regex module name filtering and nested class selection (`module.Parent.Child`).
- **`ReportManager`** (`reporting/core.py`): Collects results and delegates to enabled reporters (TestRail, XUnit, Pretty).
- **`CaseFormatData` / `SpecFormatData`** (`reporting/data.py`): Data objects that wrap spec/case state for renderers.
- **`TestRailRenderer`** (`reporting/testrail.py`): Reconciles spec hierarchy with TestRail sections/cases, creates runs and reports results via `TestRailClient`.

### Test Discovery
- Pike (`PikeManager`) scans search paths for all `Spec` subclasses
- `@fixture` decorator marks a class as a non-executable fixture (excluded from discovery)
- Nested `Spec` classes become children of their enclosing spec
- Classes decorated with `@fixture` and subclasses of `Spec` are tracked but not run as top-level specs

### Subclass Filtering (Advanced)
Set these class attributes to control nested execution:
- `__SPEKTRUM_FILTER_CHILD__`: Run only the specified child subclass; parent runs `before_all()` only
- `__SPEKTRUM_SKIP_PARENT_TESTS__`: Skip parent test methods when executing a specific subclass

### TestRail Section Hierarchy
Sections mirror class hierarchy using `__qualname__`. `reconcile_spec_and_section()` creates or reuses sections at each level; cases are created at setup time with `add_case()`.

## Code Patterns

### Basic Spec
```python
from spektrum import Spec, expect, require, skip

class ExampleSpec(Spec):
    async def before_all(self):
        self.resource = await setup()

    def test_something(self):
        expect(2 + 2).to.equal(4)

    async def test_async(self):
        result = await some_async_function()
        require(result).to.be_true()

    @skip('Not yet implemented')
    def test_future(self):
        pass

    async def after_all(self):
        await teardown(self.resource)
```

### Data-Driven Tests
```python
class DataSpec(Spec):
    DATASET = {
        'case_a': {'x': 1, 'y': 2, 'expected': 3},
        'case_b': {
            'args': {'x': -1, 'y': 1, 'expected': 0},
            'meta': {'category': 'edge_case'},
        },
    }

    def test_addition(self, x, y, expected):
        expect(x + y).to.equal(expected)
```

### Nested Specs
```python
class ParentSpec(Spec):
    async def before_all(self):
        self.shared = setup_resource()

    class ChildSpec(Spec):
        def test_child(self):
            expect(self.parent.shared).not_to.be_none()
```

### Decorators
- `@skip(reason)` / `@skip_if(condition, reason)`: Skip tests
- `@incomplete`: Mark as work-in-progress
- `@metadata(**kv_pairs)`: Attach metadata for filtering
- `@depends_on(test)`: Define execution ordering
- `@fixture`: Mark class as non-executable fixture
- `@concurrency(case=N, spec=N)`: Override concurrency limits

## Project Structure
```
spektrum/
├── __init__.py           # Public exports: Spec, DataSpec, expect, require, decorators
├── __main__.py           # CLI entry point (docopt-based)
├── spec.py               # Spec, DataSpec, decorators, case_filter, spec_filter
├── expect.py             # Expectation class, expect(), require()
├── runner.py             # SpektrumRunner, execute_spec()
├── utils.py              # camelcase_to_spaces, snakecase_to_spaces, filter_cases_by_data
├── logger.py             # Logging setup
├── exceptions.py         # FailedRequireException
├── reporting/
│   ├── core.py           # ReportManager (delegates to reporters)
│   ├── data.py           # CaseFormatData, SpecFormatData, ExpectFormatData
│   ├── pretty.py         # Console renderer
│   ├── xunit.py          # JUnit XML renderer
│   ├── testrail.py       # TestRail API integration + TestRailClient
│   └── transport.py      # RetryTransport (httpx retry logic for TestRail)
├── vendor/
│   └── ast_decompiler.py # Vendored AST decompiler for better error messages
tests/
├── test_runner.py        # Framework's own pytest-based tests
└── example_data/         # Example spec classes used by test_runner.py
```

## Dependencies
- **Runtime**: `colored`, `docopt`, `pike>=0.1.0`, `coverage`, `httpx>=0.23.0`, `python-dateutil>=2.8.2`, `pyyaml`, `ast-decompiler`
- **Dev**: `tox`, `twine`, `bumpversion`, `pytest`, `flake8`
- **Python**: 3.5+ (primary development on 3.12)
