---
name: python3-tdd
description: Use when a Python task explicitly requires test-driven development, tests-first implementation, or a red-green-refactor workflow.
argument-hint: '<feature-description>'
user-invocable: true
---

# TDD Workflow

Consult `standards-for-python-development` for the shared rules. Load `python3-testing` for detailed test patterns.

## Input

Task: $ARGUMENTS

## Phases

### 1. Design Interface

- Define only the interface needed to express the behavior under test
- Preserve the project's existing architecture and typing conventions
- Load `python3-typing` when boundary types or models are involved

### 2. Write Failing Tests

- Load `python3-testing` for fixture patterns and test structure
- Tests must fail initially (RED)
- AAA pattern; behavioral naming
- Run the smallest relevant pytest target and confirm RED
- Record the expected failure reason before running it; RED is valid only when the observed failure demonstrates the missing behavior. A syntax/import/fixture failure or a test that already passes does not establish the requirement.

### 3. Implement to Pass

- Minimal code to make tests pass (GREEN)
- Run the smallest relevant pytest target after each change and compare the observed result with the expected GREEN result
- Refactor only while tests stay green

### 4. Verify

```bash
# Linting, formatting, and type checking
uv run prek run --files src/ tests/
# Fallback when no .pre-commit-config.yaml:
# uv run ruff check src/ tests/
# uv run ruff format --check src/ tests/

# Tests with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### 5. Quality Gate

- [ ] All tests pass
- [ ] No lint errors
- [ ] No type errors
- [ ] Changed behavior, boundaries, and regressions have appropriate tests
- [ ] Existing project coverage gate is respected, if configured
- [ ] Shebang validated on scripts
