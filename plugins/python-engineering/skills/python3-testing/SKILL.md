---
name: python3-testing
description: Pytest testing patterns for Python — fixtures (session/module/function/factory), AAA structure, behavioral naming, coverage targets by code type, property-based testing with Hypothesis, and mutation testing with mutmut. Use when writing tests, designing fixtures, configuring coverage, or applying parametrize, async testing, or property-based strategies.
user-invocable: false
---

# Testing Patterns

Consult `python3-core` for standing defaults (coverage, test naming, AAA).

## Test Failure Mindset

Tests are specifications. When a test fails, investigate both possibilities:

| Hypothesis A | Hypothesis B |
|---|---|
| Test expectations are wrong | Implementation has a bug |
| Test is outdated | Test caught a regression |
| Test has wrong assumptions | Test found an edge case |

**Red flags**: Never immediately change tests to match implementation. Never assume implementation is always correct. Never bulk-update tests without individual analysis.

For the full investigation protocol, red flags, and example responses, load `/python-engineering:test-failure-mindset`.

## Fixture Design

- Session fixtures for expensive resources (DB, servers)
- Module fixtures for shared test data
- Function fixtures for isolated per-test data
- Factory pattern for complex test objects

```python
from pathlib import Path
from string import Template

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_binary(tmp_path: Path) -> Path:
    template_path = FIXTURES_DIR / "binaries" / "mock_binary_template.sh"
    template = Template(template_path.read_text())
    content = template.substitute(binary_name="tool", version="1.0.0")
    binary = tmp_path / "tool"
    binary.write_text(content)
    binary.chmod(0o755)
    return binary
```

## Coverage Targets

| Code Type | Minimum |
|---|---|
| Business logic | 90% |
| Standard code | 80% |
| Scripts/utilities | 70% |
| Critical paths | 95% + mutation testing |

```toml
# pyproject.toml
[tool.coverage.run]
branch = true
source = ["src"]
omit = ["**/tests/**"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

## Property-Based Testing

When Hypothesis is available:

- Round-trip tests for parsers/serializers
- Invariant tests for state machines
- Boundary validation with `@given(st.from_type(T))`

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers()))
def test_sort_maintains_length(data: list[int]) -> None:
    """Sorting preserves all elements."""
    result = sorted(data)
    assert len(result) == len(data)
```

## Mutation Testing

For critical code (payments, auth, data validation):

```bash
uv run mutmut run --paths-to-mutate=packages/module/
uv run mutmut results
```

Target: >90% mutation score for critical code paths.

## Fixture Composition

Depend on a fixture from another fixture rather than repeating its setup. Each layer cleans up
what it created.

```python
@pytest.fixture
def database_connection() -> Generator[Connection, None, None]:
    conn = connect_to_db()
    yield conn
    conn.close()


@pytest.fixture
def database_with_users(database_connection: Connection) -> Generator[Connection, None, None]:
    create_users(database_connection)
    yield database_connection
    delete_users(database_connection)
```

## Exception Handling in Tests

- **Default to fail-fast**: let exceptions propagate. A test that raises is a test that failed,
  which is the signal you want.
- **Use `pytest.raises` only to test error handling**, and match the message:
  `with pytest.raises(ValueError, match="Invalid email format"):`
- **Keep test helpers narrow**: a bare `except:` or `except Exception:` in a helper swallows the
  bug the suite exists to catch.

## Patterns by Scenario

| Code under test | What the tests must do |
|---|---|
| Critical business logic (payments, auth, validation) | 95%+ coverage, mutation testing, every boundary and invalid input, every error path asserted |
| Async code | `@pytest.mark.asyncio`; `AsyncClient` for HTTP; `asyncio.gather()` for concurrency; cover timeouts and retries |
| CLI applications | `CliRunner` from `typer.testing`; capture Rich output; run with and without `NO_COLOR`. See `typer-rich-testing-patterns.md` in the `python-engineering:python3-cli` skill |
| Database operations | Isolated test database (`tmp_path` or `pytest-postgresql`); assert commit on success and rollback on error; test migrations against a real engine |

## Performance Tests

Profile before optimizing — `cProfile` for CPU, `pytest-memray` for memory. Guard against
regression with `pytest-benchmark`, which fails the test when timing regresses:

```python
def test_operation_performance(benchmark) -> None:
    """Benchmark operation performance against its SLA."""
    result = benchmark(expensive_operation, arg1, arg2)
    assert result.success
```

## Migrating unittest.mock to pytest-mock

- Replace `unittest.mock` imports with `pytest_mock.MockerFixture`.
- Turn `@patch` decorators into `mocker.patch()` calls inside the test.
- Turn `Mock()` into `mocker.Mock()`.
- Drop the `with` context managers; call `mocker` directly.

## Test Directory Structure

```text
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
├── integration/             # Tests with external dependencies
├── e2e/                     # End-to-end workflows
└── fixtures/                # Test data files
```

## References

- `references/testing-standards.md` — full testing standards
- `references/agent-prompts.md` — agent test prompts
- `references/plan-templates.md` — test plan templates
