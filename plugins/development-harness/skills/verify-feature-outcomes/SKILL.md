---
name: verify-feature-outcomes
description: Verify after implementation that a feature achieved its required user/system outcomes. Use for goal-backward post-implementation verification that tests observable behavior rather than merely checking code existence.
---
# Verify Feature Outcomes

Start from the required outcomes, not the implementation.

1. Resolve the feature goal, acceptance criteria, constraints, and relevant environment.
2. For each required outcome, identify an observation that would distinguish success from implementation-shaped activity.
3. Exercise the feature at the highest practical level that observes the promised behavior; use lower-level inspection only where direct execution is unavailable or insufficient.
4. Verify integration paths and negative/error behavior when they are material to the contract.
5. Compare observed results with acceptance criteria and record evidence.
6. Separate VERIFIED outcomes, GAPS_FOUND, and UNVERIFIED outcomes. Never convert unavailable evidence into success.
7. Report the smallest concrete gap and the evidence needed to close it.

Do not award success because files, functions, tests, or tasks exist. They are evidence only when they demonstrate the required outcome.
