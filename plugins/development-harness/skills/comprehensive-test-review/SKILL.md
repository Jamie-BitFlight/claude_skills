---
name: comprehensive-test-review
description: Use when reviewing test suites for coverage, isolation, mock usage, naming conventions, or completeness. Activates on "review test coverage", "audit test quality", or "check tests for completeness" requests. Performs thorough checklist-driven review covering test isolation, mock correctness, AAA pattern adherence, and naming standards.
argument-hint: <test_file_or_directory>
user-invocable: true
---

# Comprehensive Test Review

Perform test review for the specified test files or directories.

## Test Review Process

### Standard Checklist

**Coverage Requirements:**

- [ ] Minimum 80% line and branch coverage
- [ ] Critical paths have 95%+ coverage
- [ ] All public functions have at least one test
- [ ] Edge cases are explicitly tested

**Test Quality:**

- [ ] Tests follow AAA (Arrange-Act-Assert) pattern
- [ ] Test names describe behavior, not implementation
- [ ] Each test verifies one logical unit
- [ ] Tests are isolated and independent

**Mocking Standards:**

- [ ] Uses the project's mocking framework appropriately
- [ ] Mocks are scoped appropriately
- [ ] No over-mocking of implementation details
- [ ] External dependencies are properly stubbed

**Type Safety:**

- [ ] All fixtures have complete type hints
- [ ] Test functions have explicit return types
- [ ] Using modern language features for type annotations

### Additional Examination Points

Beyond the standard checklist:

- **Execution Time**: Identifying slow tests for optimization
- **Flaky Patterns**: Tests dependent on timing, order, or external state

## Analysis Process

1. **Gather test files** in specified path
2. **Run coverage analysis** with `{test command from language manifest}`
3. **Check each test** against the standard checklist
4. **Identify gaps** in coverage and quality
5. **Generate recommendations** prioritized by impact

## Output Format

Provide findings in this structure:

```markdown
## Test Review Summary

### Coverage Analysis
- Overall: X%
- Critical modules: Y%
- Gaps identified: [list]

### Quality Issues
**HIGH Priority:**
- [Issue with location and fix]

**MEDIUM Priority:**
- [Issue with recommendation]

**LOW Priority:**
- [Minor improvements]

### Recommendations
1. [Prioritized action items]
```

## Related Skills

- **analyze-test-failures**: Detailed analysis of specific test failures
- **test-failure-mindset**: Set investigative approach for session
