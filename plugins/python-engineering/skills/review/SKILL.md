---
name: review
description: Reviews Python code across 9 dimensions — type safety, error handling, security, performance, modern patterns, design clarity, typed-boundary compliance, test quality, and documentation. Use when performing code review, PR review, pre-merge quality checks, or assessing Python for security vulnerabilities, bare except clauses, Any usage outside boundaries, or missing input validation at system boundaries.
disable-model-invocation: true
argument-hint: '[path or scope]'
---

# Review

Review the requested Python scope with these priorities.

## Input

Scope: $ARGUMENTS

## Instructions

1. Read target files from arguments
2. Check each dimension listed below
3. Report findings with severity and location
4. Suggest fixes with code examples

---

## Review Dimensions

### 1. Type Safety

**Check for:**

- Missing type hints on function parameters and return types
- Use of `Any` without justification — no `Any` outside boundary modules
- Legacy typing imports (`List`, `Dict`, `Optional`, `Union`)
- Missing Protocol definitions for duck typing
- Incorrect use of TypeVar, Generic, or ParamSpec

**Severity**: High (type errors cause runtime failures)

```python
# Bad - missing types
def process(data):
    return data.get("value")


# Good - complete types
def process(data: dict[str, int]) -> int | None:
    return data.get("value")
```

### 2. Error Handling

**Check for:**

- Bare `except:` or `except Exception:`
- Swallowed exceptions (catch and ignore)
- Missing context in re-raised exceptions
- Exceptions that should use `add_note()`

**Severity**: High (silent failures cause data corruption)

```python
# Bad - swallowed exception
try:
    result = risky_call()
except Exception:
    pass  # Silent failure

# Good - specific handling with context
try:
    result = risky_call()
except ConnectionError as e:
    e.add_note(f"Failed connecting to {host}")
    raise
```

### 3. Security

**Check for:**

- SQL queries with string formatting (injection risk)
- `subprocess.run(..., shell=True)` with user input
- Hardcoded credentials or API keys
- `eval()` or `exec()` with external input
- Pickle with untrusted data
- Path traversal vulnerabilities
- Missing input validation at boundaries

**Severity**: Critical (security vulnerabilities)

```python
# Bad - SQL injection risk
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good - parameterized query
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### 4. Performance

**Check for:**

- List membership checks instead of sets (`in list` vs `in set`)
- String concatenation in loops
- Repeated function calls that could be cached
- N+1 query patterns
- Synchronous I/O in async contexts
- Missing `__slots__` for data classes with many instances

**Severity**: Medium (degraded performance)

```python
# Bad - O(n) lookup on each iteration
valid_codes = [200, 201, 204]
for code in codes:
    if code in valid_codes:  # O(n) each time
        process(code)

# Good - O(1) lookup
VALID_CODES = {200, 201, 204}
for code in codes:
    if code in VALID_CODES:  # O(1) each time
        process(code)
```

### 5. Modern Patterns

**Check for:**

- Legacy typing imports when builtin generics available
- Missing walrus operator opportunities
- If/elif chains that should be match-case
- `unittest.mock` in pytest tests (use `pytest-mock` instead)
- Manual implementations duplicating stdlib

**Severity**: Low (technical debt)

```python
# Bad - legacy pattern
from typing import Optional

result = expensive_call()
if result:
    process(result)

# Good - modern pattern
if result := expensive_call():
    process(result)
```

### 6. Design Clarity and Maintainability

**Check for:**

- Functions longer than 50 lines
- Classes with too many responsibilities (violates SRP)
- Deep nesting (more than 3 levels)
- Circular imports
- Missing `__all__` in public modules
- Dead code (unreachable or unused)
- SOLID principles not followed

**Severity**: Medium (maintainability)

### 7. Correctness and Boundary Safety

**Check for:**

- External data (JSON, env vars, CLI args) not validated at system boundaries
- Raw payloads passed into typed core functions
- Boundary modules not using approved naming (`parse_*`, `validate_*`)
- Typed return values missing from boundary code

**Severity**: High (correctness)

```python
# Bad - raw dict passed into typed core
def handle_request(payload: dict) -> None:
    user = create_user(payload["name"], payload["email"])


# Good - validated at boundary
def handle_request(payload: dict) -> None:
    user_input = UserInput.model_validate(payload)  # validates at boundary
    user = create_user(user_input.name, user_input.email)
```

### 8. Test Quality and Debugging Ergonomics

**Check for:**

- Missing tests for changed code
- Tests without behavioral names (should describe behavior, not implementation)
- Tests not following AAA pattern (Arrange, Act, Assert)
- Missing edge case and error path coverage
- `unittest.mock` instead of `pytest-mock`
- Missing Hypothesis property-based tests for functions matching any of:
  - Parsers, serializers, codecs (round-trip identity: `decode(encode(x)) == x`)
  - Validators and boundary parsers (holds for all valid-domain inputs)
  - Mathematical and algorithmic functions (sorting, searching, arithmetic properties)
  - String transformation functions (normalization, escaping, formatting invariants)
  - CLI argument conversion paths

**Severity**: Medium (test quality)

### 9. Documentation

**Check for:**

- Public functions without docstrings
- Outdated docstrings (don't match signature)
- Missing type information in docstrings when types unclear
- Complex logic without explanatory comments

**Severity**: Low (maintainability)

---

## Checklist

```text
TYPE SAFETY
- [ ] All functions have complete type hints
- [ ] No Any outside boundary modules
- [ ] No legacy typing imports (List, Dict, Optional, Union)
- [ ] TypeVar/Protocol used appropriately

ERROR HANDLING
- [ ] No bare except clauses
- [ ] No swallowed exceptions
- [ ] Exceptions have context (add_note or from)
- [ ] Specific exception types used

SECURITY
- [ ] No SQL injection vulnerabilities
- [ ] No command injection (shell=True with user input)
- [ ] No hardcoded secrets
- [ ] Input validation present at boundaries

PERFORMANCE
- [ ] Sets used for membership testing
- [ ] No string concatenation in loops
- [ ] Appropriate caching used
- [ ] Async patterns correct

MODERN PATTERNS
- [ ] Builtin generics used (list, dict, not List, Dict)
- [ ] Walrus operator where beneficial
- [ ] Match-case for dispatch
- [ ] pytest-mock instead of unittest.mock

DESIGN
- [ ] Functions under 50 lines
- [ ] No deep nesting (>3 levels)
- [ ] No circular imports
- [ ] __all__ defined in public modules
- [ ] SOLID principles followed

BOUNDARY
- [ ] Raw data validated before crossing into typed core
- [ ] Boundary modules use approved naming (parse_*, validate_*, etc.)
- [ ] Typed return values from boundary code

TESTING
- [ ] Tests exist for changed code
- [ ] Edge cases covered
- [ ] pytest-mock (not unittest.mock)
- [ ] Behavioral test names
- [ ] Hypothesis @given tests for parsers, validators, math, round-trips

DOCUMENTATION
- [ ] Public functions have docstrings
- [ ] Docstrings match signatures
- [ ] Complex logic commented
```

---

## Report Format

For each finding:

```text
[SEVERITY] [Category]: Brief Description
Location: file.py:123 in function_name
Issue: Detailed explanation
Fix: Suggested fix with code
Impact: Why this matters (security, performance, reliability)
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
