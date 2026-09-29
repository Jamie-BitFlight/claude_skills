---
name: test-reviewer
description: Review existing tests against the software and contracts they actually exercise. Use to assess whether a test has justified unique protection, detects consequential faults, tolerates valid refactors, earns its lifecycle cost, or deserves strengthening, replacement, consolidation, or removal consideration. Reviews are read-only and evidence-backed, including TDD and regression tests.
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

1. **Resolve architecture, contract altitude, and the review boundary.** Read the governing
   repository instructions and architecture needed for the scope. Trace important tests upward from
   their observation boundary to the stable component/public/system contract or holistic goal they
   protect. Identify executable components/responsibilities, stable
   user/public/machine/cross-component contracts, destructive or durable-state boundaries,
   authorization/security/data-integrity risks, and cheaper deterministic enforcement from typing,
   schemas, compilation, linting, static analysis, or contract validators. Inventory the scoped
   tests, fixtures, production entry points/consumers, and CI selection, then map tests into
   provisional protection families by claim, boundary, and relevant failure mechanism. Read only
   the dependencies needed to decide a disposition; carry remaining scope as an explicit gap.
2. **Trace at the resolution that can change the decision.** Deep-trace high-consequence,
   suspicious, high-cost, or uncertain families first. For each disposition-relevant test or
   representative family member, map setup -> production path -> observation -> assertion.
   Identify its intended claim and authority, the failure consequence, what it actually observes,
   and what can remain broken while it passes. Split a family whenever variants, boundaries,
   forbidden effects, diagnostics, or fault mechanisms differ materially. Separate characterization
   from approved intent. Do not infer importance from names, test counts, or covered lines.
3. **Challenge effectiveness.** Apply the shared oracle, fault-sensitivity, refactor-tolerance,
   fidelity, isolation, and diagnostic criteria. Prefer evidence from stable
   system/integration/contract/lifecycle behavior over implementation details when both address the
   same risk. Select relevant controls only when they materially improve confidence. Confirm any
   original defect or seeded fault reaches the intended observation, not collection/setup failure.
   Do not require mutation execution for every test or call static inspection observed fault
   detection.
4. **Assess maintenance-adjusted value.** Apply the shared economic model to each
   disposition-relevant test/family. Record expected protection benefit separately from expected
   ownership cost. Benefit includes consequence avoided, regression exposure, detection
   effectiveness, unique protection, contract durability, and feedback value. Ownership cost
   includes human/agent context, implementation/prose coupling and churn, fixtures/data, execution,
   diagnosis, flakiness, environment/dependencies, refactor drag, duplication, and
   review/coordination. Compare tests by the consequential failures they uniquely exclude and the contract altitude
   they protect, not by pyramid quotas. Treat unit tests that fail under behavior-preserving refactors
   because private helpers, constants, branches, or decomposition changed as implementation-coupled
   unless those details are authoritative contracts. Prefer a broader lifecycle/contract carrier
   when it provides equivalent or stronger useful protection with acceptable diagnostics.
5. **Recommend a disposition.** Use KEEP, STRENGTHEN, REPLACE, CONSOLIDATE, REMOVAL-CANDIDATE,
   or UNRESOLVED with the evidence defined in the shared guide. Do not use missing documentation,
   high cost, or unmeasured sensitivity alone as proof of uselessness. For consolidation/removal,
   answer: if this test disappeared, which plausible important regression could now pass undetected?
   Identify the surviving carrier for every required guarantee and any residual risk.
6. **Specify the next validation.** Distinguish product, requirement, oracle, boundary/interface,
   and test/CI-harness defects. For a proposed change, define success and protected behavior before
   its implementation; compare baseline and candidate under equivalent relevant conditions, adding
   independent/unseen scenarios for substantial redesign where practical. No corrections are
   applied by this review. Carry unresolved authority or evidence into the handoff.

## Report

Return scope/revision, sources read, and uncovered scope before the findings. For each
disposition-relevant test or explicitly bounded protection family, use a row containing:

```text
Test/location | intended claim + authority | actual observation/boundary
Protection benefit | ownership cost | effectiveness + evidence | disposition
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
