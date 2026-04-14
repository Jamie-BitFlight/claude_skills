---
name: code-review-python
description: Provides Python-specific code review rules for the dh code-reviewer agent. Activates on pyproject.toml or *.py file detection — enforces uv, ruff, ty, pytest, type annotation, error handling, and Python 3.11+ idioms including pathlib, match statements, and modern union syntax.
user-invocable: false
---

# Python Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `pyproject.toml` or `*.py` files are detected.

## Type Annotations

- All public function boundaries must have type annotations — parameters and return type
- `Any` is only acceptable with an inline comment explaining why a specific type cannot be used
- `TypedDict` is required for dicts that cross module boundaries; plain `dict[str, ...]` is only acceptable within a single function
- `Optional[X]` is legacy — use `X | None` (Python 3.10+ union syntax)
- `Union[X, Y]` is legacy — use `X | Y`
- Return type `None` must be explicit on functions that have no return value but have side effects
- Protocol classes are preferred over ABC for structural typing

## Ruff Compliance

- Bare `except:` is a blocking finding — must be `except ExceptionType:`
- `print()` in library code (non-CLI, non-script) is a blocking finding (T201) — use `logging` instead
- Magic numbers in comparisons are a blocking finding (PLR2004) — extract to named constants
- Unused imports must be removed, not commented out
- f-strings are required for string interpolation — `%` and `.format()` are legacy
- `__all__` must be defined in modules that have public API surface

## ty Type Safety

- Unresolved imports indicate a missing `uv add` — fix the import, not the type checker
- `# ty: ignore` suppressions are prohibited — fix the code to satisfy ty
- `ty extra-paths` in `pyproject.toml` must stay in sync with `pytest` `pythonpath`
- TypedDict nominal incompatibility across modules means the TypedDict should be defined in a shared location, not duplicated

## pytest Patterns

- Test names follow behavioral naming: `test_<what>_when_<condition>_returns_<result>` or `test_<what>_when_<condition>_raises_<exception>`
- Tests assert on observable behavior, not on implementation details (internal state, private methods)
- Integration tests hit real dependencies — mocking the thing under test is not a test
- Fixtures are preferred over test-class instance state
- `assert result is not None` is not a meaningful assertion — assert the actual expected value
- Tests are isolated — no shared mutable state between test functions
- Parametrize repetitive test cases with `@pytest.mark.parametrize`
- Each test file mirrors the module it tests: `src/foo/bar.py` → `tests/foo/test_bar.py`

## uv Usage

- All Python execution uses `uv run` — bare `python` invocations are only acceptable in CI where the venv is pre-activated
- New dependencies are added with `uv add` — manual edits to `pyproject.toml` dependencies without running `uv add` leave the lockfile stale
- Scripts with external dependencies declare PEP 723 inline metadata (`# /// script`) and also add those deps via `uv add --dev` for IDE tooling
- `uv run --script` is used for standalone scripts with PEP 723 metadata

## Error Handling

- `except Exception:` is a blocking finding unless immediately followed by a re-raise or very specific logging
- Empty `except` blocks are a blocking finding — they swallow all errors silently
- Exception messages must include enough context to diagnose without reading the source: `raise ValueError(f"Expected positive int, got {value!r}")` not `raise ValueError("invalid input")`
- Sentinel return values (returning `None` or `-1` on error without raising) require a documented contract — silence must be intentional and documented

## Modern Python 3.11+ Idioms

- `match` statements are preferred for multi-branch dispatch on type or value (over long `if/elif` chains)
- `pathlib.Path` is required for all file path operations — `os.path` is legacy
- `tomllib` (stdlib in 3.11+) is used for reading TOML — do not add `tomli` as a dependency
- `datetime.UTC` is used instead of `datetime.timezone.utc` (Python 3.11+)
- `ExceptionGroup` and `except*` are used for concurrent exception handling where appropriate
- `str.removeprefix()` and `str.removesuffix()` replace manual slicing for prefix/suffix removal

## Anti-Patterns

```python
# WRONG: bare except
try:
    do_thing()
except:
    pass

# RIGHT: narrow except with action
try:
    do_thing()
except ConnectionError as e:
    logger.warning("Connection failed: %s", e)
    raise

# WRONG: magic number
if status == 429:
    ...

# RIGHT: named constant
HTTP_TOO_MANY_REQUESTS = 429
if status == HTTP_TOO_MANY_REQUESTS:
    ...

# WRONG: os.path
import os
path = os.path.join(base, "config.toml")

# RIGHT: pathlib
from pathlib import Path
path = Path(base) / "config.toml"
```
