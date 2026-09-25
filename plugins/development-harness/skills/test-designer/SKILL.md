---
name: test-designer
description: Design contract-driven tests before writing them, including each TDD increment. Use when planning acceptance or regression tests, selecting test boundaries and oracles, or deciding what evidence a software change needs. Produces a risk-proportionate test plan, not production code or a passing-test claim.
---

# Test Designer

Read [Testing principles](../../docs/testing-principles.md) before designing tests; it defines the
shared quality criteria, compact test card, TDD discipline, and safe execution boundary.

## Scope

Plan tests without modifying production code, tests, or their expectations. Return the design to
the caller; an enclosing implementation task may then write tests within its existing authorization.
This is language-independent methodology, not the language specialist agent named by a SAM task.
Do not require a SAM plan, a specific framework, or another plugin for standalone use.

## Procedure

1. **Establish intent.** Read the scoped requirement, architecture/interface contract, relevant
   callers, existing tests/fixtures, and test configuration. Use implementation evidence to locate
   the real seams, not to invent expected behavior. Mark observed, derived, assumed, and proposed
   interpretations where authority differs. Resolve only consequential missing decisions with the
   owner; carry other evidence gaps explicitly.
2. **Select obligations.** Identify changed and protected behavior, realistic failure mechanisms,
   and their consequence. Reuse adequate existing tests. Add success, rejection, boundary,
   transition, and forbidden-effect cases where the claim requires them, not by a universal quota.
3. **Choose evidence.** For each material test/family, write or reuse a compact test card. Justify
   its oracle independently; select the smallest boundary that retains the failure mechanism.
   State what doubles omit, what must be real, and which plausible fault should reach which
   failing observation. Include a behavior-preserving variation the test should accept when
   implementation coupling is a risk.
4. **Plan execution.** Discover the actual project command and CI lane. Record isolation,
   prerequisites, cleanup, diagnostics, and negative controls. Follow the shared safety rules;
   propose rather than execute unavailable or unsafe checks. Keep product expectations separate
   from generated-artifact freshness and consumer/agent execution evidence.
5. **Check the plan before authoring.** Confirm that every proposed test has a point, each
   important scoped obligation has protection or an explicit gap, and no oracle merely repeats
   production logic. Check existing project gates without replacing them with invented ones.
   For TDD, design only the next useful increment, state its intended red, and hand the design
   back before writing the test; missing API/setup is not yet behavioral sensitivity evidence.

## Result

Return a concise test plan in the current response or caller's existing authorized plan/handoff:

- scope, revision, authoritative behavior, and unresolved intent;
- test cards or a compact matrix, with existing coverage reused and each new case's purpose;
- highest-consequence missing guarantees, justified boundary choices, and execution order;
- expected red/negative control, positive behavior, and protected refactor behavior;
- proposed versus executed checks, commands/results when observed, and evidence limitations.

Use `DESIGN READY` only for a plan whose material decisions are resolved; it does not mean tests
have run or passed. Use `DESIGN PARTIAL` when useful independent work remains with named gaps,
or `DESIGN BLOCKED` when missing intent/evidence prevents a meaningful next test.

Within SAM, carry the design in existing acceptance/verification sections; do not invent a new
artifact type or task-schema field. After tests exist, use
[Test Reviewer](../test-reviewer/SKILL.md) to challenge their actual protection.
