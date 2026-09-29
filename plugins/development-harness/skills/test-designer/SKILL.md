---
name: test-designer
description: Separate required change validation from permanent test retention, then design maintenance-adjusted contract tests before writing them, including each TDD increment. Use when planning acceptance or regression evidence, selecting system/integration/unit boundaries and oracles, or deciding what evidence a software change needs. Produces a direct validation plan plus a risk-proportionate retained-test plan or explicit no-new-test decision, not production code or a passing-test claim.
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
   callers, existing tests/fixtures, and test configuration before deciding what evidence is worth
   retaining. Use implementation evidence to locate the real seams, not to invent expected behavior.
   Mark observed, derived, assumed, and proposed interpretations where authority differs. Resolve only
   consequential missing decisions with the owner; carry other evidence gaps explicitly.
2. **Select obligations by consequence.** Identify the stable behavior, system goal, supported
   contract, realistic failure mechanisms, and consequence if each obligation regresses. Prioritize
   destructive or durable state transitions, authorization/security/data-integrity boundaries,
   cross-component invariants, recovery/fail-closed behavior, and evidenced high-impact regressions.
   Reuse adequate existing protection. Do not invent obligations from implementation shape.
3. **Define close validation separately from retention.** For a fix or other claimed behavior
   change, identify the direct observation that will show the targeted outcome changed as intended.
   Prefer the same discriminating observation before and after the change when practical. This
   evidence may be a one-time probe, command, scenario, existing contract/system test, or
   deterministic validator; it does not have to become a permanent test. If the original failure
   cannot be reproduced, state that evidence limit rather than substituting an unrelated green suite.
4. **Admit or reject retained protection economically.** Apply the shared test-economics model to
   the obligations established above. State expected protection benefit, recurring ownership cost,
   and whether existing evidence catches the same important failure more cheaply. A changed file,
   line, keyword, heading, constant, helper, or branch is not sufficient justification. For text,
   ask what consequential behavior the assertion discriminates. Text can be a valid oracle when its
   observed value proves a meaningful path/outcome, but do not retain assertions whose only claim is
   that prose, instructions, headings, examples, or phrases still exist. For instruction text,
   require evidence that changing/removing it adversely affects the desired agent behavior before
   treating presence as regression protection. If added protection does not materially exceed
   recurring ownership cost, return `NO NEW TEST JUSTIFIED` for retention while preserving the
   required close-validation plan.
5. **Choose contract altitude and boundary.** Prefer the highest stable contract altitude that still
   discriminates the consequential failure with acceptable cost and diagnostics. Trace retained
   lower-level tests upward to the system goal or supported contract they help protect. Keep unit
   tests TDD-sized: one small behavioral slice, refactor-tolerant, and not a mirror of private
   helpers, constants, branches, or decomposition. Use a unit/function boundary when it is itself a
   stable contract or gives unique important fault discrimination more cheaply. For each material
   test/family, justify its oracle independently, state what doubles omit and what must be real, and
   include a behavior-preserving variation when implementation coupling is a risk.
6. **Plan execution.** Discover the actual project command and CI lane. Record isolation,
   prerequisites, cleanup, diagnostics, and negative controls where justified. Follow the shared
   safety rules; propose rather than execute unavailable or unsafe checks. Keep product expectations
   separate from generated-artifact freshness and consumer/agent execution evidence.
7. **Check the plan before authoring.** Confirm that every proposed test has a point, each important
   scoped obligation has protection or an explicit gap, and no oracle merely repeats production logic
   or mutable source. Ask: what undesirable behavior could occur if this assertion disappeared while
   all other tests remained green? If the answer is only that implementation/prose could change, the
   test has no demonstrated regression protection. Check existing project gates without replacing
   them with invented ones. For TDD, design only the next useful increment, state its intended red,
   and hand the design back before writing the test; missing API/setup is not yet behavioral
   sensitivity evidence.

## Result

Return a concise test plan in the current response or caller's existing authorized plan/handoff:

- scope, revision, authoritative behavior, and unresolved intent;
- direct close validation for the claimed change, explicitly separate from retained regression protection;
- test cards or a compact matrix, with each retained case's protection benefit, ownership cost, and unique purpose;
- highest-consequence missing guarantees, justified boundary choices, and execution order;
- expected red for TDD and any risk-justified fault/negative control, positive behavior, and protected refactor behavior;
- proposed versus executed checks, commands/results when observed, and evidence limitations.

Use `NO NEW TEST JUSTIFIED` only for the retention decision when the admission gate finds no
additional maintained test worth its lifecycle cost; it never waives direct validation of a claimed
fix/change. State the close evidence plus existing protection or more appropriate validation that
supports the choice. Use `DESIGN READY` only for a plan whose material decisions are resolved; it does not mean
tests have run or passed. Use `DESIGN PARTIAL` when useful independent work remains with named gaps,
or `DESIGN BLOCKED` when missing intent/evidence prevents a meaningful next test.

Within SAM, carry the design in existing acceptance/verification sections; do not invent a new
artifact type or task-schema field. After tests exist, use
[Test Reviewer](../test-reviewer/SKILL.md) to challenge their actual protection.
