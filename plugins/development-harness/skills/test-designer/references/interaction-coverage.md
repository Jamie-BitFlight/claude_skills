# Interaction coverage

Read this reference when several independent factors can jointly affect a protected behavior. The
goal is economical interaction coverage, not a particular generator or pairwise testing by default.

## Model the interaction

1. Name only factors that can affect the admitted obligation: inputs, prior state, configuration,
   environment, capability, or execution mode.
2. Partition each factor into behaviorally distinct values. Include boundaries when behavior can
   change at the boundary.
3. Classify combinations:
   - **feasible**: the system can reach the combination;
   - **reachable rejection**: a caller can request it and correct behavior is rejection or another
     forbidden-effect guarantee;
   - **impossible**: the environment cannot meaningfully realize it.
4. Constrain only impossible combinations. Reachable rejection cases remain in the model.
5. Seed known regressions and high-consequence combinations explicitly.

Complete when every factor/value and exclusion has a behavioral reason.

## Select strength

Choose the cheapest selection strategy that still matches the plausible failure mechanism:

- explicit examples for a few known interactions;
- pairwise coverage when two-factor interactions are the supported risk model;
- higher-order coverage when evidence or consequence makes three or more factors material;
- exhaustive coverage when the feasible space is already small enough;
- stateful/sequence design when order, retry, interruption, race, or recovery is causal.

A covering array is a selection mechanism. It does not establish the oracle, execution reach, or
temporal behavior.

Complete when the selected strength has a reason tied to failure risk rather than tool availability.

## Generate and verify

Use any available combinatorial generator when it reduces manual selection cost. Record the model,
constraints, strength, tool/version, and seed/options that affect reproducibility.

Verify the resulting rows against the claimed feasible t-way combinations. A model file, successful
generator invocation, or row count is not coverage evidence. Earlier rejection can mask later
behavior, so confirm each retained case can reach the observation it is meant to protect.

Credit existing tests before adding rows. Treat the selected rows as one protection family: after
removing or consolidating cases, recompute any coverage claim for the surviving family.

If generation or verification is unavailable, return the model and intended strength as proposed
evidence and name coverage as unvalidated.

Complete when the coverage claim is mechanically supported or explicitly marked unvalidated.

## Hand back

Report only what changes the test design:

- factors and behaviorally distinct values;
- feasibility constraints and their reasons;
- selected strength and why;
- explicit regression/high-consequence seeds;
- existing tests credited;
- generated/verified status and uncovered interactions;
- oracle/boundary caveats that combination coverage cannot establish.
