---
name: lint
description: Use when running or guiding deterministic Python quality checks, including linting, typing, test, and policy validation workflows. Invoke for ruff, ty, or pre-commit checks.
disable-model-invocation: true
argument-hint: '[path or scope]'
---

# Lint

Deterministic quality check workflow.

## Input

Scope: $ARGUMENTS

## Steps

1. Detect the repo's configured checkers from `.pre-commit-config.yaml` and CI config
2. Run deterministic checks that already exist in the project
3. Run plugin policy checks when appropriate
4. Report failures grouped by category
5. Fix only when the user asked for fixing; otherwise review and explain

## Commands to Run

```bash
# Formatting
uv run ruff format --check $ARGUMENTS

# Linting
uv run ruff check $ARGUMENTS

# Type check — detect from hooks/CI
uv run ty check $ARGUMENTS
# If project runs mypy: uv run mypy $ARGUMENTS

# Tests (if scope includes test files)
uv run pytest $ARGUMENTS -v --tb=short
```

## Policy Checks

```bash
# Typing boundary policy (Any outside boundary modules)
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-typing-boundaries.sh $ARGUMENTS
```

## Output

Group results by category:

```text
## Lint Results

### Formatting
✅ Pass / ❌ Fail (N issues)

### Linting
✅ Pass / ❌ Fail (N issues: list rule IDs)

### Type Checking
✅ Pass / ❌ Fail (N issues)

### Policy
✅ Pass / ❌ Fail (Any usage outside boundary modules: list files)
```
