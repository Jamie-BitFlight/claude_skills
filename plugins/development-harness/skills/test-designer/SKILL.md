---
name: test-designer
description: Decide whether a new test is justified, then design contract-driven tests before writing them, including each TDD increment. Use when planning acceptance or regression tests, selecting test boundaries and oracles, or deciding what evidence a software change needs. Produces a risk-proportionate test plan or an explicit no-new-test decision, not production code or a passing-test claim.
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

1. **Admit or reject a new test.** State the meaningful contract or failure the proposed test would
   independently protect and whether existing tests already catch it. A changed file, line, keyword,
   heading, or implementation detail is not sufficient. Prefer deterministic lint/schema/static
   validation for machine-readable form and behavioral evaluation for agent-instruction semantics.
   Reject phrase/prose-presence tests unless exact text is itself a machine-consumed contract. If no
   additional useful protection is justified, return `NO NEW TEST JUSTIFIED` and stop test design.
2. **Establish intent.** Read the scoped requirement, architecture/interface contract, relevant
   callers, existing tests/fixtures, and test configuration. Use implementation evidence to locate
   the real seams, not to invent expected behavior. Mark observed, derived, assumed, and proposed
   interpretations where authority differs. Resolve only consequential missing decisions with the
   owner; carry other evidence gaps explicitly.
3. **Select obligations.** Identify changed and protected behavior, realistic failure mechanisms,
   and their consequence. Reuse adequate existing tests. Add success, rejection, boundary,
   transition, and forbidden-effect cases where the claim requires them, not by a universal quota.
4. **Choose evidence.** For each material test/family, write or reuse a compact test card. Justify
   its oracle independently; select the smallest boundary that retains the failure mechanism.
   State what doubles omit, what must be real, and which plausible fault should reach which failing
   observation when that control materially increases confidence. Include a behavior-preserving
   variation the test should accept when implementation coupling is a risk.
5. **Plan execution.** Discover the actual project command and CI lane. Record isolation,
   prerequisites, cleanup, diagnostics, and negative controls where justified. Follow the shared
   safety rules; propose rather than execute unavailable or unsafe checks. Keep product expectations
   separate from generated-artifact freshness and consumer/agent execution evidence.
6. **Check the plan before authoring.** Confirm that every proposed test has a point, each
   important scoped obligation has protection or an explicit gap, and no oracle merely repeats
   production logic or mutable prose. Check existing project gates without replacing them with
   invented ones. For TDD, design only the next useful increment, state its intended red, and hand
   the design back before writing the test; missing API/setup is not yet behavioral sensitivity
   evidence.

## Result

Return a concise test plan in the current response or caller's existing authorized plan/handoff:

- scope, revision, authoritative behavior, and unresolved intent;
- test cards or a compact matrix, with existing coverage reused and each new case's purpose;
- highest-consequence missing guarantees, justified boundary choices, and execution order;
- expected red for TDD and any risk-justified fault/negative control, positive behavior, and protected refactor behavior;
- proposed versus executed checks, commands/results when observed, and evidence limitations.

Use `NO NEW TEST JUSTIFIED` when the admission gate finds no additional maintained test worth its
lifecycle cost; state the existing protection or more appropriate validation that supports the
choice. Use `DESIGN READY` only for a plan whose material decisions are resolved; it does not mean
tests have run or passed. Use `DESIGN PARTIAL` when useful independent work remains with named gaps,
or `DESIGN BLOCKED` when missing intent/evidence prevents a meaningful next test.

Within SAM, carry the design in existing acceptance/verification sections; do not invent a new
artifact type or task-schema field. After tests exist, use
[Test Reviewer](../test-reviewer/SKILL.md) to challenge their actual protection.
