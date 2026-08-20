---
name: cleanup
description: Runs structured Python cleanup and modernization — static analysis via prek/ruff, smell investigation to root cause, typed-boundary hardening by inventorying Any usage, and modernization within the project's requires-python lane. Use when refactoring Python code, removing dead code, hardening type boundaries, or running a modernization pass on a file or scope.
argument-hint: '[path or scope]'
---

# Cleanup

Structured cleanup and modernization workflow.

## Input

Scope: $ARGUMENTS

## Goals

- Remove duplication and ambiguous ownership
- Investigate code smells instead of suppressing them
- Improve typed boundaries and reduce escape hatches
- Modernize only within the project's compatibility lane
- Preserve behavior unless explicitly changing it

## Steps

### 1. Static Analysis

```bash
uv run prek run --files $ARGUMENTS
# Fallback when no .pre-commit-config.yaml:
# uv run ruff format $ARGUMENTS
# uv run ruff check --fix $ARGUMENTS
# uv run ruff check --fix --unsafe-fixes $ARGUMENTS
```

### 2. Smell Investigation

For each smell found:

- Identify the root cause (not just the symptom)
- Determine if it's a design smell or a quick fix
- Document the investigation and decision

### 3. Type Boundary Hardening

- Inventory all `Any` usage
- Move boundary code to dedicated modules
- Add typed wrappers where raw data crosses boundaries
- Run typing policy checks

### 4. Modernization (within project lane)

- Modernize typing imports only if Python floor supports it
- Apply match-case where it reduces complexity
- Use walrus operator where it improves readability
- Only within the project's `requires-python` constraint

### 5. Verification

```bash
uv run prek run --files $ARGUMENTS
# Fallback when no .pre-commit-config.yaml:
# uv run ruff check $ARGUMENTS
# uv run ruff format --check $ARGUMENTS
uv run pytest $ARGUMENTS -v
```

## Load Specialists

- Load `python3-typing` for boundary refactoring
- Load `python3-testing` if test gaps are found
- Load `python3-tools` for toolchain changes
