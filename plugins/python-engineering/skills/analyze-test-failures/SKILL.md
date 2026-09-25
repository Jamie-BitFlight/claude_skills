---
name: analyze-test-failures
description: Analyze specific pytest failures using authoritative contracts and a cited product/test evidence chain. Use for failing test names or pytest output, distinguishing product, interface, oracle, and harness defects without automatically changing expectations or forcing an architectural redesign.
argument-hint: <test_file_or_test_name>
user-invocable: true
---

# Analyze Test Failures

Read and follow [Test Failure Mindset](../test-failure-mindset/SKILL.md), including its Python
standards route. It owns the investigation protocol; this skill applies it to each supplied
failure. Reuse an existing evidence record instead of restarting completed investigation.

## Per-failure application

Read the complete relevant test, fixtures, setup/cleanup, stack trace, and product path. Preserve
the failed revision and conditions; reproduce safely when permitted. Trace the product and test
observation to their earliest demonstrated contract divergence.

For each candidate explanation, identify a discriminating observation and separate observed facts
from unverified inference. Verify which requirement governs the expected behavior. A familiar
mathematical, library, or API convention alone does not establish this product's contract.

Classify supported defects separately as product implementation, interface/architecture, test
oracle, or harness/CI; several may coexist. For missing authority, report the intent decision.
For missing execution, report unvalidated behavior rather than silently choosing a side.

Example: `divide(10, 0)` returning a sentinel versus raising an exception cannot be adjudicated
from the operation's name. A current approved sentinel contract makes a raising implementation
incorrect; an approved error contract makes a sentinel expectation incorrect. Without that
authority, report the ambiguity and the evidence or decision required.

## Output

```text
TEST / REVISION / FAILURE:
CONTRACT / AUTHORITY / INVARIANTS:
EXPECTED / OBSERVED / REPRODUCTION LIMITS:
EVIDENCE CHAIN / FIRST DIVERGENCE:
SUPPORTED CAUSE / UNVERIFIED HYPOTHESES:
CORRECTION CATEGORY / RATIONALE:
PROPOSED CHANGE / PRESERVED BEHAVIOR:
VALIDATION: original fault -> intended failure; corrected behavior -> success
REMAINING UNCERTAINTY / NEXT OBSERVATION OR INTENT DECISION:
```

Do not manufacture cause from an assertion mismatch. Keep correction proposals distinct from
work actually performed. When changing a test, explain the authoritative reason and show its
relevant fault sensitivity; a collection or setup error does not establish regression protection.
Use [Comprehensive Test Review](../comprehensive-test-review/SKILL.md) for the broader assessment.
