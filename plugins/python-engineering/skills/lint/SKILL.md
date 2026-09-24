---
name: lint
description: Runs deterministic Python quality checks against a path or scope — formatting, linting, type checking, and typing-boundary policy. Use when checking or fixing code quality via prek, ruff, ty, pytest, or the check-typing-boundaries policy script. Reports results grouped by category; fixes only when explicitly requested.
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
5. Fix only when the user asked for fixing; check-only mode MUST NOT run hooks or commands that can rewrite files

## Commands to Run

```bash
# Check-only path: never invoke mutating hooks.
uv run ruff format --check $ARGUMENTS
uv run ruff check $ARGUMENTS
# Run the type checker selected by hooks/CI (ty shown as the default).
uv run ty check $ARGUMENTS

# Tests (if scope includes test files)
uv run pytest $ARGUMENTS -v --tb=short
```

## Policy Checks

```bash
# Typing boundary policy (Any outside boundary modules)
uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/check-typing-boundaries.py $ARGUMENTS
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
