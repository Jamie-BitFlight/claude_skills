---
name: test-designer
description: Design validation and maintained regression protection before test authoring. Use for TDD increments, acceptance or regression evidence, test boundary/oracle decisions, and multi-factor interaction coverage.
---

# Test Designer

Design the smallest evidence set that can distinguish the consequential failure while remaining stable
through valid redesign. Plan only; return the design to the caller.

Use [Testing principles](../../docs/testing-principles.md) as shared reference. For retention, read
**Test admission gate** and **Test economics**. For boundary/oracle decisions, read **Contract
altitude** and principles 2-5. For TDD, read **TDD contract**. Before execution planning, read
**Evidence execution boundary**.

## Procedure

1. **Resolve the claim.** Identify the required behavior, realistic failure, consequence, and
   evidence authority. Label material intent as authoritative, observed, derived, assumed, or proposed;
   implementation locates seams but does not define expected behavior. Inspect callers, existing
   protection, configuration, and implementation only far enough to locate the real boundary. Resolve
   only ambiguity that can change the design and carry the rest as explicit gaps. Complete when every
   material claim has an authoritative basis or a consequential unresolved decision.
2. **Design close evidence.** Choose the direct observation that would distinguish the claimed change,
   preferably the same observation before and after a fix. Complete when the change has a discriminating
   validation path or a named evidence limitation.
3. **Choose retained protection.** Apply the testing-principles admission gate and economics. Reuse
   existing protection where it catches the same important failure. Complete when every proposed
   maintained test has unique protection worth its ownership cost, or return `NO NEW TEST JUSTIFIED`.
4. **Place the observation.** Choose the highest stable contract altitude that still exposes the
   failure with acceptable cost and diagnostics. Justify the oracle independently and identify what
   must remain real at the boundary. For TDD, design only the next useful behavioral increment and
   state its intended red. Complete when a valid redesign can preserve the protected behavior without
   preserving incidental implementation.
5. **Cover interactions when they can cause the failure.** If several independent inputs, states,
   configurations, environments, or capabilities can jointly affect an admitted obligation, read
   [Interaction coverage](references/interaction-coverage.md) and apply it. Otherwise continue without
   an interaction model. Complete when consequential interactions are either covered or named as gaps.
6. **Make execution reproducible.** Discover the project command and CI lane; record prerequisites,
   isolation, cleanup, diagnostics, selected cases, and proposed versus observed evidence. Complete
   when an implementer can run the design without inventing missing test semantics.
7. **Conserve the plan.** Account for every scoped obligation, remove duplicate or implementation-only
   protection, and preserve direct validation separately from retention. Complete when every retained
   case has a purpose and every important uncovered obligation is explicit.

## Result

Return only the resolution the caller needs:

- authoritative claim and unresolved intent;
- direct close validation;
- retained test cards or `NO NEW TEST JUSTIFIED`;
- boundary, independent oracle, realistic fault, and execution evidence;
- interaction model/coverage only when step 5 fired;
- evidence status: `DESIGN READY` when material design decisions are resolved, `DESIGN PARTIAL` when useful independent design remains with named gaps, or `DESIGN BLOCKED` when missing intent/evidence prevents a meaningful next test. These are design states, never passing-test claims.

`NO NEW TEST JUSTIFIED` applies only to permanent retention; direct validation of a claimed behavior change still requires evidence.

Within SAM, carry this in the caller's existing acceptance/verification fields. After tests exist,
use [Test Reviewer](../test-reviewer/SKILL.md) to challenge their actual protection.
