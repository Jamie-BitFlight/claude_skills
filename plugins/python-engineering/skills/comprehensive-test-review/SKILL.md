---
name: comprehensive-test-review
description: Review pytest test effectiveness against authoritative contracts, relevant faults, behavior-preserving refactors, realistic boundaries, isolation, and diagnostics. Use for test-quality audits, coverage-gap reviews, regression-test changes, or mocking reviews; preserve existing project gates rather than inventing coverage targets.
argument-hint: <test_file_or_directory>
user-invocable: true
---

# Comprehensive Test Review

Review whether the specified tests distinguish required behavior from relevant faults. Establish
the product purpose, supported environments, and governing contracts before judging coverage or
style. Treat each expectation as a claim, not as authority merely because it is already a test.

Load [Python Development Standards](../standards-for-python-development/SKILL.md) for applicable
shared rules. Preserve coherent existing framework/mock usage and the supported Python floor.

## Effectiveness checks

For each material claim, record the contract authority, failure excluded, observation, and evidence.

| Property | Review question and evidence |
| --- | --- |
| Oracle validity | Does the expected answer follow from an authoritative requirement/interface, independently of the implementation under test? Identify stale or contradictory requirements rather than silently selecting a convenient answer. |
| Fault sensitivity | Does the test fail on the original defect or a relevant deliberately seeded fault? Confirm it reaches the intended assertion: collection, import, setup, or unrelated errors do not demonstrate detection. |
| Refactor tolerance | Does a behavior-preserving change leave the expectation valid? Avoid incidental helper names, ordering, serialization, or call counts unless those details are contractual. |
| Boundary fidelity | Does the test exercise the entry point, handoff, state transition, or external contract carrying the guarantee? Check what a mock, fake, fixture, or bypassed adapter removes from observation. |
| Isolation | Are time, randomness, environment, shared state, ordering, concurrency, and cleanup controlled where relevant? Record what isolated/full-suite or serial/parallel comparisons actually establish. |
| Diagnostic value | Does failure identify the violated property and relevant input/state difference, without replacing useful evidence with a generic pass/fail? |

Do not require executing mutations for every test. For a changed regression test or an important
untested guarantee, choose the cheapest relevant negative control. When execution is unavailable,
record a proposed control and mark fault sensitivity unvalidated; do not infer it from source or
coverage. Keep destructive or external effects in a safe, authorized test environment.

## Review procedure

1. **Read the target and contract.** Read the complete relevant tests, fixtures, product entry
   points, and authoritative requirements. Locate the test in the product-to-consumer path and
   identify the first boundary its observation can actually see.
2. **Capture a baseline.** Discover the repository's real test command and selection from its
   testing guidance/configuration/CI. Preserve strict configuration, warning policy, configured
   plugins, and supported runtimes. Record revision, command, collected/selected cases, outcomes,
   skips/xfails, and unavailable environments. Do not claim a subset represents the whole suite.
3. **Challenge meaningful faults.** Use the effectiveness checks above. For changed regression
   protection, compare original defect and corrected behavior under comparable conditions. Check
   that a harmless implementation variation remains accepted where practical. Inspect both the
   final assertion and the execution that reached it.
4. **Inspect risk coverage and maintainability.** Apply the supporting checks below. Prioritize
   missing or misleading guarantees over cosmetic consistency. Group related findings by
   demonstrated mechanism, while accounting for each affected claim.
5. **Propose or apply only authorized corrections.** Name product, interface/architecture, oracle,
   or harness defects separately; several may coexist. For a material change, predeclare the
   expected improvement, preserved invariants, unacceptable regressions, and baseline. Explain
   why an architectural correction is necessary instead of prescribing layers by default.
6. **Validate the delta.** Run affected positive, negative, boundary, and integration cases.
   Preserve meaningful guarantees when replacing or removing tests. Record before/after evidence
   and remaining uncertainty; use independent and additional unseen cases for substantial
   redesign where practical. Revalidate evidence invalidated by subsequent edits.

## Supporting checks

**Coverage:** Respect an established project gate, but do not invent universal line/branch
percentages or require a test per symbol. Inspect changed branches, public contracts, critical
paths, boundary cases, and meaningful failure/recovery behavior for uncovered risk. Coverage
shows execution, not whether a wrong result would be rejected. A percentage cannot compensate
for a missed required guarantee.

**Structure:** Keep Arrange-Act-Assert legible, use behavior-oriented names, and give each test a
coherent claim. Multiple assertions are appropriate when they establish that claim, including
absence of forbidden side effects. Prefer useful diagnostics over assertion-count rules.

**Doubles:** Follow the project's framework and scope fixtures/mocks appropriately. Preserve
valid fakes and dependency injection at meaningful seams. Do not mock away the boundary whose
contract is being assessed. Interaction assertions remain appropriate when ordering, a prohibited
write, authorization, or another interaction is itself the guarantee.

**Maintainability:** Follow applicable type-hint, naming, and fixture conventions. Identify slow
or flaky patterns and measure relevant runtime before proposing optimization. Verify cleanup of
resources and worker/thread/process activity where used. Do not introduce a dependency merely
to replace a coherent existing test idiom.

## Generated artifacts and agent skills

Keep these claims separate:

- Inventory or generated-artifact freshness: compare the preserved checked-in state with the
  declared inputs. Report missing, extra, and changed semantic identities; keep a separate
  canonical-byte check when deterministic serialization is part of the contract.
- Generator correctness: use independent, deliberately constructed fixtures and meaningful
  invalid/boundary cases. Comparing a generator with its own output is not an independent oracle.
- Consumer or agent behavior: execute the real consumer or representative tasks and inspect
  consequential routing, handoffs, side effects, and completion evidence.

Do not regenerate immediately before a freshness assertion and treat the result as evidence the
original state was current. A valid file, an instruction phrase, or a mapped but unexecuted task
does not prove behavior. For nondeterministic agents, predeclare acceptable outcomes and critical
invariants, preserve traces, and report repeated-run uncertainty rather than a universal pass claim.

## Result contract

Return scope/revision, authoritative contracts, and prioritized findings. For every material finding
include the violated claim, location, counterexample or missing evidence, correction category,
recommended change, and required validation. Keep observed defects separate from proposed probes.

Report claim -> validator -> observed result -> evidence boundary. Distinguish passed, failed,
blocked, and unvalidated claims; list omitted suites, skips, and residual risks. Report coverage
and cost separately from correctness. Do not turn source review or authored eval fixtures into
passing behavioral evidence.

## Related skills and implementation

Use [Test Failure Mindset](../test-failure-mindset/SKILL.md) when a failing expectation needs
adjudication, [Test Design](../python3-test-design/SKILL.md) for test architecture, and
[Testing Patterns](../python3-testing/SKILL.md) for pytest implementation. When available, delegate
implementation to `python-engineering:python-pytest-architect` and review its execution evidence.
The review protocol above does not require DH or Process Siren to be installed.
