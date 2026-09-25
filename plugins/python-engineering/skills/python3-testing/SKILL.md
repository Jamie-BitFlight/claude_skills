---
name: python3-testing
description: Pytest testing patterns for Python — fixtures, behavioral naming, behavior/risk-driven coverage, property-based testing with Hypothesis when useful, and mutation testing when justified. Use when writing tests, designing fixtures, configuring coverage, or applying parametrize, async testing, or property-based strategies.
user-invocable: false
---

# Testing Patterns

Consult `standards-for-python-development` for the shared rules (coverage, test naming, AAA).

## Test Failure Mindset

Tests encode claims about expected behavior; validate them against authoritative intent.
Neither a test nor its implementation is automatically correct. Investigate both possibilities:

| Hypothesis A | Hypothesis B |
|---|---|
| Test expectations are wrong | Implementation has a bug |
| Test is outdated | Test caught a regression |
| Test has wrong assumptions | Test found an edge case |

**Red flags**: Never immediately change tests to match implementation. Never assume implementation is always correct. Never bulk-update tests without individual analysis.

Also investigate producer/consumer contracts, fixtures, mocks, observation, and CI conditions;
several defects can coexist. For the evidence, correction, and validation protocol, load
[the test-failure mindset](../test-failure-mindset/SKILL.md).

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

## Coverage

Coverage is evidence about exercised behavior, not a universal percentage target.

- Cover changed behavior, contracts, boundaries, regressions, and meaningful failure paths.
- Respect an existing repository coverage gate; do not introduce one when the project has none.
- Inspect uncovered changed branches and decide whether they represent meaningful risk.
- Do not add low-value tests solely to raise a percentage.

A project that already configures `fail_under` keeps that value. New configuration may enable branch measurement and missing-line reporting without inventing a threshold.

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

Use mutation testing for critical logic when it materially strengthens confidence. Do not invent a universal mutation-score target.

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
| Critical business logic (payments, auth, validation) | Exercise security/correctness boundaries, invalid inputs, and meaningful error paths directly; consider mutation testing where it strengthens evidence |
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

## Mocking

For new pytest suites, prefer `pytest-mock` when a mock is the clearest seam. Preserve coherent existing `unittest.mock` usage rather than introducing a dependency solely to migrate syntax. Prefer fakes, dependency injection, or `monkeypatch` when they make the behavior clearer.

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
