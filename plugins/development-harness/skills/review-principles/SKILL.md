---
name: review-principles
description: Assess review findings against the target's governing contract, evidence, and consequence without imposing a lens-specific verdict, schema, or gate. Use when classifying a candidate concern in a code or change review.
---

# Review principles

Use this procedure before universal or specialist checks. The caller keeps its review scope,
verdict, findings, persistence, artifact destination, and terminal response contract.

## Establish authority and applicability

Establish supported behavior and environment from requirements, interfaces, callers,
configuration, and active checks. Apply constraints in this order:

1. Explicit user requirements and applicable safety/security constraints.
2. Supported versions, public contracts, architecture, dependency policy, active CI/lint/type-check
   gates, and established conventions.
3. Relevant runtime, framework, library, or host specification.
4. Specialist defaults and design preferences.

Resolve conflicts against the governing source and name material conflicts. A project preference
cannot change a runtime or host capability; report an unsupported configuration as a compatibility
conflict. Existing code and tests establish observed behavior, not approved intent. Do not require a
migration, dependency,
abstraction, file split, or permanent test only to satisfy a default; require a demonstrated
limitation, incompatible contract, maintenance problem, or active project gate. Determine
applicability from changed source and relevant execution/configuration paths, not a filename or
manifest alone.

## Establish evidence and consequence

Treat a checklist pattern as a candidate to investigate. Before making it blocking:

1. Locate the affected code and applicable obligation, including the source of a required gate.
2. Identify the supported input, state, operation, or consumer for which it matters.
3. Inspect the relevant guard, caller, recovery path, or documented exception that could refute it.
4. State the concrete consequence and supporting evidence, or what remains unvalidated.

A static source trace, incompatible schema, or failed applicable deterministic gate can establish a
defect without a runtime reproduction. State that boundary. Before recommending error handling,
identify the recovery owner and whether a signal or forbidden effect crosses the boundary.

Make a finding blocking only for a violated required contract, active project gate, or material
correctness/security property. Keep optional improvements distinct and derive urgency from
consequence and exposure, not a syntax match, topology metric, arbitrary score, or reviewer count.
Preserve material uncertainty and the cheapest discriminating next check through the caller's
existing reporting route.

## Admit further work

Before a candidate can make the caller's verdict blocking or create a fix task, follow-up, repeated
review, test harness, discovery check, or environment, record in the caller's existing reporting
route:

1. The original outcome, acceptance criterion, invariant, or applicable
   correctness/security/data-loss contract.
2. Observed evidence and concrete impact.
3. The smallest correction and a concrete direct verification method.

After a correction, record the observed result of that method through the caller's existing
validation and reporting contract.

When that relation or impact is missing, retain the candidate as advisory pending attribution or
disposition. It cannot create a blocker or another work branch. An explicitly named skill or
command selects a route; require automatic-discovery proof only when an applicable routing contract
requires autonomous selection.

Before repeating a review or probe, identify changed source, evidence, conditions, or hypothesis
that can distinguish the admitted claim. Stop a branch that only rechecks a harness created by an
earlier review. This admission rule does not waive configured mandatory gates, existing task
classifications, migration-fidelity procedures, or caller-owned delegation/retry terminal limits.
Do not introduce or override a fixed review retry count: continue only while new distinguishing
information exists and the caller's applicable limits permit it. The caller retains ordinary
authority to implement an admitted correction.

## Keep review in scope

Read material source independently. Treat supplied context and evidence as pointers to verify, not
conclusions to inherit. Distinguish change-induced defects, existing defects exposed by the change,
and unrelated existing issues using the declared scope.

Keep the review read-only for target code, tests, documentation, and generated state. Do not run an
autofix or destructive probe. Use safe authorized checks, record unavailable evidence, and treat a
separately authorized disposable experiment as its own boundary.

Use the caller's existing status, finding, artifact, and persistence contracts. This skill does not
define a shared severity scale, verdict schema, gate, tracking system, or report format. When a
specialized procedure is needed, invoke it under the caller's protocol and return relevant findings
through that protocol.
