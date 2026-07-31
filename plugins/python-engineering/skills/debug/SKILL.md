---
name: debug
description: Structured 6-phase Python debugging workflow covering problem intake, scoping, hypothesis formation, systematic investigation, root-cause analysis, and fix implementation. Use when diagnosing tracebacks, test failures, AttributeError, TypeError, intermittent failures, async/await issues, or any unexpected Python behavior. Applies a dual-hypothesis approach (implementation bug vs test bug), minimal reproduction isolation, data-flow tracing, and produces a structured Bug Investigation Report with confirmed root cause and regression test.
disable-model-invocation: true
argument-hint: '[symptom, error, or path]'
---

# Debug

Structured debugging flow for functional bugs using specifications, logs, and observed behavior.

## Input

Symptom: $ARGUMENTS

## Investigation Steps

1. **Restate the observed symptom** — exact error message, stack trace, or unexpected behavior
2. **Identify the smallest reproducible scope** — minimal code that triggers the failure
3. **Isolate assumptions** — environment, input, state, concurrency
4. **Inspect boundaries early** — check validation and conversion points where external data enters
5. **Distinguish implementation bugs from test bugs** — dual-hypothesis approach
6. **Verify the fix** — rerun deterministic checks after fixing

---

## Phase 1: Problem Intake

Ask for these if not provided:

```text
SPECIFICATION
- [ ] What should the feature do? (spec, user story, acceptance criteria)
- [ ] What behavior is expected?

OBSERVED BEHAVIOR
- [ ] What actually happens?
- [ ] Error messages (exact text)
- [ ] Logs (relevant sections)

REPRODUCTION
- [ ] Steps to reproduce
- [ ] Input data that triggers the bug
- [ ] Environment (Python version, OS, dependencies)

CONTEXT
- [ ] When did it last work? (if ever)
- [ ] What changed recently?
- [ ] Is it intermittent or consistent?
```

Intake template:

```text
## Bug Report

**Expected Behavior**: [What should happen according to spec]
**Actual Behavior**: [What is happening]
**Error/Logs**: [Paste exact error messages or relevant log output]
**Reproduction Steps**:
1. [First step]
2. [Step where failure occurs]
**Environment**: Python [version], OS [os], packages [list]
**Recent Changes**: [What changed before this started happening]
```

---

## Phase 2: Problem Scoping

### Define Boundaries

```text
WORKING
- [ ] [Feature X works correctly]
NOT WORKING
- [ ] [Feature Z fails with error]
UNKNOWN
- [ ] [Feature V not tested yet]
```

Narrow the scope:

```text
1. Is this a regression or never worked?
2. Does it fail for all inputs or specific ones?
3. Does it fail in all environments or specific ones?
4. Is the failure consistent or intermittent?
5. What's the smallest reproduction case?
```

Minimal reproduction:

```python
def test_reproduction():
    """Minimal reproduction of the bug."""
    input_data = {"key": "value"}  # Specific input that triggers bug
    result = buggy_function(input_data)
    assert result == expected, f"Got {result}, expected {expected}"
```

---

## Phase 3: Hypothesis Formation

```text
## Hypothesis List

H1: [Description of potential cause]
    Evidence for: [what supports this]
    Evidence against: [what contradicts this]
    Test: [how to verify]

H2: [Description of potential cause]
    Evidence for: [what supports this]
    Evidence against: [what contradicts this]
    Test: [how to verify]
```

## Common Bug Categories

| Category | Symptoms | Investigation |
|---|---|---|
| Type Error | AttributeError, TypeError | Check types at boundary |
| State Mutation | Intermittent, order-dependent | Look for shared mutable state |
| Race Condition | Intermittent, timing-dependent | Check async/threading code |
| Edge Case | Specific inputs fail | Test boundary conditions |
| Integration | Works in isolation, fails together | Check interface contracts |
| Configuration | Environment-dependent | Compare working vs failing env |

---

## Phase 4: Systematic Investigation

Trace the data flow:

```text
1. INPUT: What data enters the function? Log: input values, types, shapes
2. PROCESSING: What transformations occur? Add debug logging at each step
3. OUTPUT: What comes out? Compare actual vs expected output
4. SIDE EFFECTS: Database writes, file system changes, external API calls
```

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

Hypothesis test pattern:

```python
def test_hypothesis_1():
    """Test H1: [hypothesis description]"""
    # Setup to isolate this hypothesis
    # Action that should reveal if H1 is correct
    # Assertion that confirms or refutes H1
```

---

## Phase 5: Root Cause Analysis

```text
## Root Cause Evidence

**Confirmed Root Cause**: [description]

**Evidence**:
1. [File:line] - [what this shows]
2. [Log entry] - [what this shows]
3. [Test result] - [what this shows]

**Why This Causes the Bug**: [causal chain from root cause to symptom]

**Eliminated Hypotheses**:
- H2: Ruled out because [evidence]
```

Fix requirements before implementing:

```text
## Fix Specification

**Root Cause**: [concise description]
**Location**: [file:line range]
**Fix Approach**: [what needs to change]
**Risks**: [potential side effects]
**Test Coverage**:
- [ ] Test for original bug (regression test)
- [ ] Test for edge cases
```

---

## Phase 6: Fix Implementation

```text
BEFORE FIX
- [ ] Root cause identified with evidence
- [ ] Minimal reproduction exists

DURING FIX
- [ ] Fix addresses root cause (not symptoms)
- [ ] Fix is minimal (no scope creep)
- [ ] Regression test written first

AFTER FIX
- [ ] Regression test passes
- [ ] Existing tests still pass
- [ ] Edge case tests added
```

Regression test pattern:

```python
def test_bug_description():
    """Regression test for bug.

    Bug: [brief description]
    Root cause: [what was wrong]
    Fix: [what was changed]
    """
    input_data = create_problematic_input()
    result = fixed_function(input_data)
    assert result == expected_output
```

---

## Output Format

```text
## Bug Investigation Report

**Status**: [Investigating | Root Cause Found | Fixed | Cannot Reproduce]

### Problem Statement
**Expected**: [spec behavior]
**Actual**: [observed behavior]
**Impact**: [who/what is affected]

### Hypotheses

| # | Hypothesis | Status | Evidence |
|---|------------|--------|----------|
| H1 | [description] | Confirmed/Refuted | [evidence] |

### Root Cause
**Location**: file:line
**Description**: what's wrong and why
**Evidence**: how we know

### Fix
**Approach**: what was changed
**Regression Test**: test for the original bug
**Verification**: all checks pass after fix
```

---

## Common Python Bug Patterns

### NoneType Errors

```python
# Bug: AttributeError: 'NoneType' has no attribute 'x'
# Cause: Function returns None unexpectedly

# Fix: Add proper None handling
if (result := get_something()) is None:
    raise ValueError("Expected result but got None")
return result.x
```

### Mutable Default Arguments

```python
# Bug: List accumulates across calls
def buggy(items=[]):  # WRONG: mutable default
    items.append(1)
    return items


# Fix
def fixed(items: list | None = None) -> list:
    if items is None:
        items = []
    items.append(1)
    return items
```

### Async/Await Issues

```python
# Bug: Coroutine never executed
async def fetch_data():
    return await api_call()


# WRONG: Missing await
result = fetch_data()  # Returns coroutine, not result

# Fix
result = await fetch_data()
```

### Import Errors

```python
# Bug: ImportError or circular import
# Fix: Use local imports for circular dependencies
def function_that_needs_other_module():
    from .other_module import OtherClass  # Local import

    return OtherClass()
```

---

## Checks After Fix

```bash
uv run prek run --files <modified_files>
# Fallback when no .pre-commit-config.yaml:
# uv run ruff check
uv run pytest -v
```
