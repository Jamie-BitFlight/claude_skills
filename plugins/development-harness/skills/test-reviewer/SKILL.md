---
name: test-reviewer
description: Review existing tests against the software and contracts they actually exercise. Use to assess whether a test has a justified purpose, detects important faults, tolerates valid refactors, or deserves strengthening, replacement, consolidation, or removal consideration. Reviews are read-only and evidence-backed, including TDD and regression tests.
---

# Test Reviewer

Read [Testing principles](../../docs/testing-principles.md) before review; it defines the shared
criteria, compact test card, safe execution boundary, and evidence required for each disposition.

## Scope

Review without editing or deleting the target's tests, product, requirements, or generated state.
A request to review is not permission to execute destructive probes or update snapshots. Use safe
isolated execution when authorized and available; otherwise report the proposed check as unvalidated.
Prefer a reviewer independent of the test author where available; disclose when that is not possible.

## Procedure

1. **Resolve the review boundary.** Inventory the scoped tests, parameter families, fixtures,
   helpers, production entry points, relevant callers, contracts, and CI selection. Read each
   material dependency, or mark the coverage gap. Establish product purpose and supported
   environments. Reuse existing investigation evidence instead of starting the same inquiry again.
2. **Trace each material test.** Map setup -> production path -> observation -> assertion.
   Identify its intended claim and authority, the failure consequence, what it actually observes,
   and what can remain broken while it passes. Separate characterization from approved intent.
   Do not infer importance from names, test counts, or covered lines.
3. **Challenge effectiveness.** Apply the shared oracle, fault-sensitivity, refactor-tolerance,
   fidelity, isolation, and diagnostic criteria. Select the cheapest relevant positive/negative
   controls for important or changed guarantees. Confirm the original defect or seeded fault
   reaches the intended assertion, not a collection/setup error. Do not require mutation execution
   for every test or call static inspection an observed fault-detection result.
4. **Assess suite value.** Identify missing high-consequence protection, misleading passes,
   redundant cases, and costly/flaky checks. Compare claim, input variants, boundary, failure
   mechanism, and diagnostics before treating overlap as duplication. Apply project conventions
   and established coverage gates. Keep correctness, qualitative value, and runtime cost separate.
5. **Recommend a disposition.** Use KEEP, STRENGTHEN, REPLACE, CONSOLIDATE, REMOVAL-CANDIDATE,
   or UNRESOLVED with the evidence defined in the shared guide. Do not use missing documentation
   or unmeasured sensitivity as proof of uselessness. For any material replacement/removal,
   account for the original guarantees, their surviving carriers, and unacceptable regressions.
6. **Specify the next validation.** Distinguish product, requirement, oracle, boundary/interface,
   and test/CI-harness defects. For a proposed change, define success and protected behavior before
   its implementation; compare baseline and candidate under equivalent relevant conditions, adding
   independent/unseen scenarios for substantial redesign where practical. No corrections are
   applied by this review. Carry unresolved authority or evidence into the handoff.

## Report

Return scope/revision, sources read, and uncovered scope before the findings. For each test or
explicitly bounded equivalent family, use a row containing:

```text
Test/location | intended claim + authority | actual observation/boundary
Importance/failure excluded | effectiveness + evidence | disposition
Correction category | surviving protection / gap | next discriminating validation
```

Distinguish observed defects, inferred risks, and proposed probes. Report claim -> validator ->
observed result -> evidence boundary. Include the exact command/selection when run, outcomes,
skips/xfails, omitted suites, and unavailable environments. Authored evals and source inspection
are not passing runtime evidence.

Conclude with `REVIEW COMPLETE` when the declared scope was assessed, or `REVIEW PARTIAL` with
unread dependencies or missing evidence; separately state whether required behavior is supported,
failed, or unvalidated. Report `No material test findings in the assessed scope` when applicable.
Completion of a review never means every test passed, and a removal candidate never authorizes deletion.

For findings needing causal investigation, read
[Test Failure Mindset](../test-failure-mindset/SKILL.md) or
[Root-Cause Tracing Process](../root-cause-tracing-process/SKILL.md); carry the contract and evidence
forward. For new/replacement test planning use [Test Designer](../test-designer/SKILL.md).
When project commands are unknown, [DH Meta Docs](../dh-meta-docs/SKILL.md) routes quality-gate
discovery. Preserve the caller's existing SAM verdict, artifact registration, and status contract.
