---
name: python3-tdd
description: Test-driven development workflow for Python. Activates on "TDD", "write tests first", "red-green-refactor", or tasks requiring test-first implementation with pytest. Guides design-first interfaces, failing tests, and implementation to pass.
argument-hint: '<feature-description>'
user-invocable: true
---

# TDD Workflow

Consult `python3-core` for standing defaults. Load `python3-testing` for detailed test patterns.

## Input

Task: $ARGUMENTS

## Phases

### 1. Design Interface

- Define function signatures with full type annotations
- Create Protocol classes for dependencies
- Write docstrings before implementation
- Load `python3-typing` when boundary types or models are involved

### 2. Write Failing Tests

- Load `python3-testing` for fixture patterns and test structure
- Tests must fail initially (RED)
- AAA pattern; behavioral naming
- Run `uv run pytest -v` — confirm failures

### 3. Implement to Pass

- Minimal code to make tests pass (GREEN)
- Run `uv run pytest -v` after each change
- Refactor only while tests stay green

### 4. Verify

```bash
# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check — detect from hooks/CI (see python3-tools)
uv run ty check src/ tests/
# If project runs mypy: uv run mypy src/ tests/

# Tests with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### 5. Quality Gate

- [ ] All tests pass
- [ ] No lint errors
- [ ] No type errors
- [ ] Coverage ≥80%
- [ ] Shebang validated on scripts
