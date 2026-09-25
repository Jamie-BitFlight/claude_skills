---
name: validate-implementation-plan
description: Validate whether an implementation plan can achieve its stated outcome before execution. Use to check requirement coverage, task contracts, dependencies, data/artifact flow, testability, ownership, impact coverage, and executable ordering without checking whether implementation already exists.
---
# Validate an Implementation Plan

Validate plans goal-backward. Plan completeness is not goal achievement.

1. Establish the intended outcome, requirements, constraints, and authoritative impact set.
2. Map each requirement to task outcomes and acceptance evidence. Flag uncovered or only partially covered requirements.
3. Check each task has a resolvable purpose, required inputs, produced outputs, completion evidence, and owner/capability where assignment matters.
4. Build the dependency graph from real input/output or resource dependencies. Reject missing references, cycles, impossible readiness, and unsafe concurrent ownership. Do not reject a forward textual reference merely because its task number is later.
5. Trace produced artifacts/data into consumers. Flag components created without a planned integration path when integration is required by the outcome.
6. Check acceptance criteria are observable and capable of falsifying failure.
7. Check scope against context/risk rather than fixed task/file-count thresholds. Recommend decomposition only when a task cannot preserve necessary context, ownership, or verification quality.
8. Check architectural boundaries: plans specify required contracts/outcomes while leaving implementation choices to the executor unless the choice is itself a requirement.
9. Compare the plan with the established impact set and unresolved frontier. Every required impact needs implementation, verification, or an explicit justified exclusion.
10. Return READY only when no unresolved issue prevents safe execution; otherwise BLOCKED with specific gaps. Preserve non-blocking warnings separately.

For an explicitly unfinished/drafting plan, validate only invariants that are meaningful before completion and label deferred checks rather than treating incompleteness as failure.
