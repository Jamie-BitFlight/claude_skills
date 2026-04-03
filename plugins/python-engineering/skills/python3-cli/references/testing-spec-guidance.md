# Testing Architecture Guidance for Architecture Specs

Reference for the `python-cli-design-spec` agent. Specifies what testing architecture to
include in `architect-{slug}.md`. Implementation details belong to the `python-pytest-architect`
agent — this file defines WHAT to specify, not HOW to implement.

---

## Required Testing Stack

Include these in every architecture spec's technology stack:

```text
pytest>=8.0.0              # test execution
pytest-cov>=6.0.0          # coverage (80% minimum, 95%+ critical code)
pytest-mock>=3.14.0        # mocking (never unittest.mock directly)
pytest-asyncio>=0.24.0     # async support
typer.testing.CliRunner    # CLI integration testing
hypothesis>=6.100.0        # property-based testing (validation functions)
mutmut>=2.4.0              # mutation testing (payments, auth, security)
```

---

## Coverage Requirements to Specify

- **Overall**: 80% line and branch coverage (enforced in pyproject.toml `fail_under=80`)
- **Critical code** (payment, auth, security, compliance): 95%+ coverage
- **Mutation testing**: 90%+ kill rate for critical code paths

---

## Test Architecture Patterns to Specify in Specs

### CLI Integration Testing

- Typer `CliRunner` with `mix_stderr=False` for stderr/stdout separation
- `env={"NO_COLOR": "1"}` to disable color codes for assertion simplicity
- Test all commands: success path, invalid inputs, help output (`--help`), exit codes
- Mark with `@pytest.mark.cli`

### Business Logic Unit Testing

- Mock all external dependencies via pytest-mock `MockerFixture`
- Protocol types for dependency contracts (enables spec validation on mocks)
- Factory pattern for test instance creation
- Mark with `@pytest.mark.unit` (implied by default)

### Async Service Testing

- `@pytest.mark.asyncio` or module-level `pytestmark`
- `AsyncGenerator[YieldType, None]` type hints for async fixtures
- Verify concurrency limits explicitly

### Rich Output Testing

- `StringIO`-based console capture
- Assert content presence, not exact text (structural validation)
- Verify width calculations

### Property-Based Testing

- `@given` with `hypothesis` strategies
- 500+ examples for critical paths (`@settings(max_examples=500)`)
- Required for all validation functions and parsers

---

## Test Directory Structure to Specify

```text
tests/
├── conftest.py              # shared fixtures and pytest config
├── fixtures/                # external test data files
│   ├── sample_config.toml
│   └── mock_responses/
├── test_cli.py              # CLI integration tests
├── test_core/
│   ├── conftest.py
│   └── test_*.py
└── test_services/
    ├── conftest.py
    └── test_*.py
```

---

## pytest Configuration Block (include in spec)

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=packages/{package_name}",
    "--cov-report=term-missing",
    "-v",
]
testpaths = ["tests"]
pythonpath = [".", "packages/"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "cli: marks tests as CLI integration tests",
    "critical: marks tests requiring mutation testing",
]

[tool.coverage.run]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 80
```

---

## BDD (pytest-bdd) — When to Specify

Include BDD in the architecture spec when:

- Stakeholders need requirements traceability
- Formal acceptance criteria are defined in Gherkin format
- Non-technical reviewers must validate test scenarios

Do NOT specify BDD for pure unit tests or simple utility functions.

Feature files go in `features/`, step definitions in `tests/step_defs/`.
