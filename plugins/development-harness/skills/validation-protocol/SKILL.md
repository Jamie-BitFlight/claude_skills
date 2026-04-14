---
name: validation-protocol
description: Scientific validation protocol for verifying fixes work through observation, not assumption. Use when claiming a bug fix, code change, refactoring, or implementation is complete — enforces reproduce-broken-state then define-success-criteria then apply-fix then verify-outcome. Success means observing intended behavior, not absence of errors.
---

# Fix Validation Protocol

## Overview

Before claiming any fix works, follow this scientific validation protocol. Success means observing the intended behavior, not merely the absence of errors.

## When to Use This Skill

- Claiming a bug fix is complete
- Verifying a code change works as intended
- Validating an implementation meets requirements
- Confirming a refactoring preserves functionality
- Testing that a feature behaves correctly

## Core Principle

**Success = Observing the intended behavior, not absence of errors.**

A fix that "runs without failing" is not validated. A fix that demonstrates the specific expected outcome is validated.

## The Protocol

### Step 1: Reproduce the Failing State

**Objective**: Establish the broken baseline before attempting any fix.

**Actions**:

- Explicitly create or verify the broken condition exists
- Document the observable symptoms:
  - Exact error messages
  - Wrong values or outputs
  - Unexpected behavior
  - System state issues
- Confirm you can observe the failure consistently

**Why**: Without reproducing the failure, you cannot verify the fix addresses the actual problem. You may fix a different issue or introduce new problems.

**Example**:

```bash
# Create the broken state by running the relevant command or test
{test command from language manifest} -k test_broken_function

# Observe the failure
# Expected: Error or incorrect output
# Observed: Error or incorrect output confirmed
```

### Step 2: Define Success Criteria

**Objective**: State what specific observable output indicates the fix worked.

**Actions**:

- Identify the specific behavior that proves success
- Define measurable, observable outcomes
- Distinguish success from non-success indicators:
  - Success = The fix's intended behavior is demonstrated
  - Success != Absence of errors
  - Success != Absence of warnings
  - Success != "It ran without failing"

**Why**: Clear success criteria prevent false positives where code runs but doesn't actually work correctly.

**Example**:

```text
Success Criteria:
- Function returns expected value: {"status": "processed", "count": 42}
- No exceptions raised
- Output matches test assertion exactly
- Performance within acceptable range (<100ms)
```

### Step 3: Apply the Fix and Observe

**Objective**: Implement the fix and capture what actually happens.

**Actions**:

- Run the code with the fix applied
- Look for the specific success indicators defined in Step 2
- Document what actually happened (verbatim output, return values, behavior)
- Compare observed outcome against success criteria

**Why**: The fix may run without errors but still not produce the intended behavior. Observation reveals the truth.

**Example**:

```bash
# Run the fixed code
{test command from language manifest} -k test_fixed_function

# Observe the output
# Expected: All assertions pass with correct values
# Observed: All assertions pass with correct values
```

### Step 4: Verify the Result

**Objective**: Confirm the broken state is now fixed and success criteria are met.

**Actions**:

- Check that the broken state no longer exists
  - Run the same reproduction steps from Step 1
  - Verify the failure no longer occurs
- Confirm the success criteria from Step 2 are satisfied
  - Each criterion must be met with evidence
  - Partial success is not success
- Document the verification evidence

**Why**: Verification ensures the fix actually solved the problem and didn't just change the symptoms.

**Example**:

```text
Verification Results:

Step 1 Recheck:
- Reproduction steps no longer trigger failure
- Error message no longer appears

Step 2 Criteria Check:
- Function returns {"status": "processed", "count": 42}
- No exceptions raised
- Output matches test assertion
- Performance: 45ms (within <100ms requirement)

Conclusion: Fix verified. All success criteria met with evidence.
```

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: Claiming Success Without Reproducing Failure

```text
"I fixed the bug. The code runs now."
```

**Problem**: Without reproducing the failure, you don't know if the fix addresses the actual issue.

**Correct Approach**:

```text
Step 1: Reproduced failure - function raised ValueError("Invalid input")
Step 2: Success = function returns valid output without error
Step 3: Applied fix - added input validation
Step 4: Verified - function now returns {"result": "valid"}, no ValueError
```

### Anti-Pattern 2: Confusing "No Errors" with Success

```text
"The tests pass now, so the fix works."
```

**Problem**: Tests passing means no exceptions, not necessarily correct behavior.

**Correct Approach**:

```text
Step 2: Success = function processes 1000 records and returns count=1000
Step 3: Observed output: {"processed": 1000, "failed": 0}
Step 4: Verified count matches expected value exactly
```

### Anti-Pattern 3: Skipping Verification

```text
"I made the change. It should work now."
```

**Problem**: "Should work" is speculation, not verification.

**Correct Approach**:

```text
Step 3: Applied fix
Step 4: Ran test suite - all 45 tests pass
Step 4: Manually tested edge case - correct behavior observed
Step 4: Checked logs - no error messages, expected INFO logs present
```

### Anti-Pattern 4: Partial Verification

```text
"The main case works, so the fix is complete."
```

**Problem**: Edge cases and boundary conditions may still be broken.

**Correct Approach**:

```text
Step 2: Success criteria:
  - Normal input: returns expected output
  - Empty input: raises ValueError
  - Large input (10k records): completes within 5s
  - Invalid input: raises TypeError

Step 4: All criteria verified with evidence
```

## Integration with Testing

This validation protocol complements but does not replace automated testing:

**Automated Tests**: Prevent regressions, verify expected behavior systematically

**Validation Protocol**: Ensures the specific fix addresses the specific problem observed

**Use both**:

1. Follow validation protocol to verify the fix
2. Add automated test to prevent regression
3. Run full test suite to ensure no new issues

## Example: Complete Validation Workflow

```text
Bug Report: "User authentication fails with 500 error"

Step 1: Reproduce Failing State
- Attempt login with valid credentials
- Observe: HTTP 500, server logs show "KeyError: 'user_id'"
- Confirmed: Failure reproduces consistently

Step 2: Define Success Criteria
- Login with valid credentials returns HTTP 200
- Response contains {"status": "authenticated", "user_id": <id>}
- No KeyError in server logs
- Session cookie is set

Step 3: Apply Fix and Observe
- Fixed: Added user_id field validation in auth handler
- Tested: Login with valid credentials
- Observed: HTTP 200 response
- Observed: {"status": "authenticated", "user_id": 42}
- Observed: No errors in logs
- Observed: Session cookie present

Step 4: Verify Result
- Reproduction steps no longer trigger 500 error
- HTTP 200 received (not 500)
- Response contains correct user_id
- No KeyError in logs
- Session cookie set correctly

Conclusion: Fix verified. All success criteria met with evidence.

Additional Verification:
- Added regression test for user_id validation
- Full test suite passes (156 tests)
- Deployed to staging, manual verification successful
```

## Summary

This protocol ensures fixes are verified through observation rather than assumption:

1. **Reproduce**: Establish the broken baseline
2. **Define**: State what success looks like
3. **Apply**: Implement the fix
4. **Verify**: Confirm success criteria are met with evidence

**Remember**: Success = Observing the intended behavior, not absence of errors.
