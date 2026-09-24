---
name: analyze-change-impact
description: Analyze the causal system-wide impact of a proposed change across behavior, interfaces, state/data, runtime dependencies, tests, documentation, controls, people/processes, and model/prompt/context behavior. Use before planning when lexical reference search is insufficient to establish blast radius and verification obligations.
---
# Analyze Change Impact

Find what the proposed change can cause across the real system. Text search discovers candidates; it does not establish impact.

1. Establish the current baseline, proposed delta, intended outcome, non-goals, time horizon, and rollback/transition boundary.
2. Seed an impact set from changed interfaces, state, data, dependencies, controls, actors, and externally visible behavior.
3. Follow causal propagation paths through callers/consumers, schemas/state transitions, runtime/deployment dependencies, tests, documentation, operational controls, people/process handoffs, and model/prompt/context behavior where applicable.
4. For each candidate, require a causal path from the change to a changed state, decision, outcome, obligation, or risk. Exclude lexical-only matches with no causal path.
5. Record direct evidence separately from derived impact. Keep unknown frontier items when evidence cannot close a plausible path.
6. For each included impact identify owner/consumer, transition or compatibility risk, and a verification obligation capable of detecting the predicted effect.
7. Check removed controls and delayed/second-order effects explicitly when the change can suppress detection or move failure downstream.
8. Return the estimated impact set, propagation paths, exclusions with rationale, unknown frontier, transition risks, and verification obligations.

Do not design the implementation. Do not claim zero impact from zero text matches. Do not convert impact count into severity without considering consequence and propagation.
