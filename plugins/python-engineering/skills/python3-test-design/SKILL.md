---
name: python3-test-design
description: Guides pytest test architecture for Python 3.11+ using behavioral contracts, risk, and maintenance-adjusted value. Use when choosing unit/integration/property/e2e boundaries, fixture strategy, coverage measurement, or mutation testing. Preserves existing project gates but does not invent test-pyramid ratios, coverage percentages, mutation-score targets, or tests for implementation detail.
---

# Python Test Design Skill

Design Python tests under the shared rules in
`/python-engineering:standards-for-python-development`. Repository requirements and established
project gates take precedence. This skill adds Python/pytest-specific boundary and fixture guidance;
it does not create a second testing philosophy.

## Decision order

1. Establish the supported behavior, contract, callers/consumers, existing protection, and relevant
   failure consequence before deciding what test to retain.
2. Separate direct validation of the current change from permanent regression protection.
3. Prefer the highest stable contract boundary that still discriminates the consequential failure
   with acceptable cost and diagnostics.
4. Keep unit tests TDD-sized: one small behavioral slice that survives behavior-preserving refactors.
5. Do not mirror private helpers, branches, constants, incidental call counts, or decomposition unless
   those details are themselves authoritative contracts.
6. Preserve an existing repository coverage/mutation gate. When none exists, do not invent one.

## Boundary selection

### Unit / function

Use when a small boundary is itself stable, drives the next TDD behavior, or uniquely distinguishes
an important fault more cheaply than broader evidence. Pure functions and algorithms often fit here,
but their implementation branches do not automatically become permanent test obligations.

### Integration / contract / lifecycle

Use when the guarantee depends on component composition: databases, filesystems, protocols,
serialization consumers, packaging/startup, transactions, persistence, authorization, retries,
recovery, or multi-step state transitions. Prefer this boundary over duplicated white-box unit tests
when it protects the same externally meaningful failure and remains diagnosable.

### Property-based / stateful

Use Hypothesis when a justified invariant spans many inputs or action sequences and examples would
poorly represent the state space. Justify the invariant independently; round trips alone can preserve
paired bugs.

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers()))
def test_sort_preserves_elements(data: list[int]) -> None:
    assert sorted(sorted(data)) == sorted(data)
```

### BDD / acceptance

Use when user-visible workflow requirements benefit from scenario language or stakeholder-readable
acceptance evidence. Do not add a BDD layer merely to duplicate an existing contract test.

## Fixtures and doubles

Use the smallest fixture structure that keeps scenario, action, observation, and cleanup legible.
Prefer factories/builders when they reduce genuine repeated setup; do not build a parallel fixture
framework that reproduces production complexity.

Use fakes/mocks at real seams. State what a double removes from observation and do not mock away the
mechanism the test is intended to challenge. For important integration assumptions, validate the
double against the real dependency where practical.

## Coverage

Coverage is measurement, not a universal quality score.

- Respect a repository's existing `fail_under` or equivalent gate when one is configured.
- When no gate exists, enable useful branch/missing-line reporting without inventing a percentage.
- Inspect uncovered changed behavior for risk; do not create tests solely to raise the number.
- Do not infer suite value from test counts or unit/integration/e2e ratios.

Example measurement configuration without a new threshold:

```toml
[tool.coverage.run]
branch = true
source = ["src"]
omit = ["**/tests/**", "**/__pycache__/**"]

[tool.coverage.report]
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

## Mutation testing

Use mutation testing only when it materially strengthens confidence in important logic and the
mutations reach the intended behavioral observation. Preserve a project mutation gate if one exists;
otherwise do not invent a mutation-score target.

```bash
uv run mutmut run --paths-to-mutate=packages/auth/
uv run mutmut results
```

A mutant killed by import/collection/setup failure does not prove that the intended test detects the
relevant defect.

## Test organization

Follow the existing project's layout. For a new pytest project, separate boundaries only when the
distinction improves execution or ownership, for example:

```text
tests/
├── conftest.py
├── unit/
├── integration/
└── e2e/
```

Do not create directories or test categories merely to satisfy a pyramid shape.

## Related resources

- **Agent**: `python-engineering:python-pytest-architect` for implementation
- **Skill**: `python-engineering:standards-for-python-development` for shared Python rules
- **Skill**: `python-engineering:python3-testing` for pytest implementation patterns
