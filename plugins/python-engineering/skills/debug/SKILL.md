---
name: debug
description: Use when debugging Python failures using a structured investigation workflow focused on reproduction, boundary assumptions, and root-cause isolation. Activate for tracebacks, test failures, or unexpected behavior.
disable-model-invocation: true
argument-hint: '[symptom, error, or path]'
---

# Debug

Structured debugging flow.

## Input

Symptom: $ARGUMENTS

## Investigation Steps

1. **Restate the observed symptom** — exact error message, stack trace, or unexpected behavior
2. **Identify the smallest reproducible scope** — minimal code that triggers the failure
3. **Isolate assumptions** — environment, input, state, concurrency
4. **Inspect boundaries early** — check validation and conversion points where external data enters
5. **Distinguish implementation bugs from test bugs** — dual-hypothesis approach
6. **Verify the fix** — rerun deterministic checks after fixing

## Common Bug Categories

| Category | Symptoms | Investigation |
|---|---|---|
| Type Error | AttributeError, TypeError | Check types at boundary |
| State Mutation | Intermittent, order-dependent | Look for shared mutable state |
| Race Condition | Intermittent, timing-dependent | Check async/threading code |
| Edge Case | Specific inputs fail | Test boundary conditions |
| Integration | Works in isolation, fails together | Check interface contracts |
| Configuration | Environment-dependent | Compare working vs failing env |

## Debug Logging Pattern

```python
import logging
logger = logging.getLogger(__name__)

def investigate(data: InputType) -> OutputType:
    logger.debug(f"INPUT: {data!r}, type={type(data)}")
    intermediate = step1(data)
    logger.debug(f"STEP1: {intermediate!r}")
    result = step2(intermediate)
    logger.debug(f"OUTPUT: {result!r}, type={type(result)}")
    return result
```

## Output Format

```text
## Bug Investigation Report

**Status**: [Investigating | Root Cause Found | Fixed | Cannot Reproduce]

### Root Cause
**Location**: file:line
**Description**: what's wrong and why
**Evidence**: how we know

### Fix
**Approach**: what was changed
**Regression Test**: test for the original bug
**Verification**: all checks pass after fix
```

## Checks After Fix

```bash
uv run ruff check
uv run pytest -v
uv run ty check  # or project checker
```
