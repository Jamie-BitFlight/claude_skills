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
