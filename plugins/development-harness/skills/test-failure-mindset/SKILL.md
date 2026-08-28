---
name: test-failure-mindset
description: Use when encountering failing tests, diagnosing test errors, or establishing a systematic approach to test failure investigation. Activates on "test failure analysis", "debugging tests", or "why tests fail" requests. Establishes the mindset that treats test failures as valuable diagnostic signals requiring root-cause investigation — not automatic code fixes or test dismissal.
user-invocable: true
---

# Test Failure Analysis Mindset

Establish a balanced investigative approach for all test failures encountered in this session.

## Core Principle

Tests are specifications - they define expected behavior.

## Dual Hypothesis Approach

Always consider both possibilities when a test fails:

| Hypothesis A                    | Hypothesis B             |
| ------------------------------- | ------------------------ |
| Test expectations are incorrect | Implementation has a bug |
| Test is outdated                | Test caught a regression |
| Test has wrong assumptions      | Test found an edge case  |

## Investigation Protocol

For EVERY test failure:

### 1. Pause and Read

- Understand what the test is trying to verify
- Read its name, comments, and assertions
- Check the test's history (git blame) for context

### 2. Trace the Implementation

- Follow the code path that leads to the failure
- Understand actual behavior vs. expected behavior
- Check if recent changes affected this code path

### 3. Consider the Context

- Is this testing a documented requirement?
- Would current behavior surprise a user?
- What would be the impact of each possible fix?

### 4. Make a Reasoned Decision

| Situation               | Action                             |
| ----------------------- | ---------------------------------- |
| Implementation is wrong | Fix the bug                        |
| Test is wrong           | Fix test AND document why          |
| Unclear                 | Seek clarification before changing |

### 5. Learn from the Failure

- What can this teach about the system?
- Should additional tests cover related cases?
- Is there a pattern being missed?

## Red Flags (Dangerous Patterns)

- Immediately changing tests to match implementation
- Assuming implementation is always correct
- Bulk-updating tests without individual analysis
- Removing "inconvenient" test cases
- Adding mock/stub workarounds instead of fixing root causes

## Good Practices

- Treat each test failure as a potential bug discovery
- Document analysis in comments when fixing tests
- Write clear test names that explain intent
- Consider adding more tests when finding ambiguity

## Related Skills

- **analyze-test-failures**: Detailed analysis of specific test failures
- **comprehensive-test-review**: Full test suite review
