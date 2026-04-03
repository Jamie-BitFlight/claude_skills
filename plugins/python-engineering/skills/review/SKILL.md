---
name: review
description: Use when reviewing Python changes for design quality, typed-boundary compliance, testing adequacy, and maintainability. Invoke for code review, PR review, or quality assessment.
disable-model-invocation: true
argument-hint: '[path or scope]'
---

# Review

Review the requested Python scope with these priorities.

## Input

Scope: $ARGUMENTS

## Review Dimensions

1. **Correctness and boundary safety** — external data validated at boundaries; no raw payloads in typed core
2. **Design clarity and maintainability** — clear module responsibilities; SOLID applied
3. **Test quality and debugging ergonomics** — behavioral names; AAA pattern; edge cases covered
4. **Type health and escape hatches** — no unjustified `Any`; boundary modules only for raw data
5. **Operational clarity** — clear failures; explicit configuration; debuggable behavior

## Checklist

```text
TYPE SAFETY
- [ ] All functions have complete type hints
- [ ] No Any outside boundary modules
- [ ] No legacy typing imports (List, Dict, Optional, Union)

ERROR HANDLING
- [ ] No bare except clauses
- [ ] No swallowed exceptions
- [ ] Exceptions have context (add_note or from)

SECURITY
- [ ] No SQL injection vulnerabilities
- [ ] No command injection (shell=True with user input)
- [ ] No hardcoded secrets
- [ ] Input validation present at boundaries

DESIGN
- [ ] Functions under 50 lines
- [ ] No deep nesting (>3 levels)
- [ ] No circular imports
- [ ] __all__ defined in public modules
- [ ] SOLID principles followed

TESTING
- [ ] Tests exist for changed code
- [ ] Edge cases covered
- [ ] pytest-mock (not unittest.mock)

BOUNDARY
- [ ] Raw data validated before crossing into typed core
- [ ] Boundary modules use approved naming (parse_*, validate_*, etc.)
- [ ] Typed return values from boundary code
```

## Report Format

For each finding:

```text
[SEVERITY] [Category]: Brief Description
Location: file.py:123 in function_name
Issue: Detailed explanation
Fix: Suggested fix with code
```

End with:

```text
## Review Summary

Files Reviewed: N
Total Findings: N

| Severity | Count |
|----------|-------|
| Critical | X     |
| High     | X     |
| Medium   | X     |
| Low      | X     |

Recommendation: APPROVE / REQUEST CHANGES / BLOCK
```
