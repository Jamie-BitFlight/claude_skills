---
name: improve-processes
description: Analyze and improve processes or systems using an explicit semantic model, adaptive instruction resolution, evidence-driven change, and claim-level validation. Use when reviewing process quality, resolving ambiguity or gaps, deciding how much procedural detail is necessary, or validating consequential process behavior.
---

# Improve Processes

## Operating Principle

Use this skill whenever a process/system must be analyzed or improved, or when faithful representation would otherwise encode ambiguity as authoritative behavior. Establish purpose at the current useful resolution, model only what evidence supports, investigate resolvable uncertainty, and ask the user only when continuing would create or alter intent or policy.

### Model Quality Checks

During MODEL and CHALLENGE, verify the relevant ProcessModel has:

- observable desired outcomes and terminal states;
- explicit actors/ownership, inputs, outputs, state, transitions, resources, and constraints where applicable;
- evaluable guards and explicitly permitted behavior, including intentional nondeterminism;
- failure, retry, recovery, rollback, and feedback behavior where applicable;
- assumptions and boundaries distinguished from verified facts;
- enough auditability to reconstruct materially important execution;
- important correctness claims expressed so they can be falsified or otherwise validated.

Do not require irrelevant fields merely to complete a checklist.

## Canonical Process Model

Use one lightweight semantic model as the handoff between understanding, improvement, validation, and representation. Populate only fields relevant at the current resolution.

```text
ProcessModel
  purpose; scope; resolution; parent_constraints[]
  actors[]; states[]; actions[]; transitions[]
    action/node may include { purpose; requires[]; guarantees[]; resolution { altitude; consequence; behavioral_variance; rationale }; expansion_ref?; validation[] }
  inputs[]; outputs[]; resources[]
  goals[]; invariants[]; assumptions[]; failure_modes[]
  claims[] { claim; failure_excluded; resolution; assumptions[]; falsifier; validation_method; status; evidence[] }
  uncertainties[] { classification; evidence; consequence }
  boundaries[] { caller_assumptions[]; callee_guarantees[]; state_crossing_boundary[]; partial_failure_behavior; recovery_owner }
  residual_risks[]
```

Mermaid, tests, TLA+, Lean, and prose consume or project this model; do not build parallel interpretations for each representation.

### Result Contract

Return one overall status plus per-claim status:

- **READY** — usable at requested resolution; required claims have sufficient evidence.
- **IMPROVED** — authorized corrections applied; affected claims revalidated sufficiently.
- **BLOCKED_INTENT** — progress requires a decision that creates/alters intent or policy.
- **UNVALIDATED** — usable model, but required claims lack necessary tooling/evidence.
- **INVALID** — evidence shows a required claim fails and no intent-preserving correction has resolved it.

Every result records evidence, assumptions, residual uncertainty, and validation boundaries.

## Process and System Improvement Loop

Treat process improvement as recursive systems engineering, not diagram cleanup. At each useful resolution: establish purpose, model behavior, extract falsifiable claims, challenge them, improve defects that can be resolved without inventing intent, validate with the least-formal sufficient method, and feed failures back into improvement.

### Recursion Safety

Recursive analysis must descend in **system resolution**, not recursively reinvoke Process Siren on the same unchanged scope. Each descent must name a strictly narrower subsystem, boundary, claim, or unresolved dependency and inherit applicable parent goals/constraints. Track visited analysis targets by `(scope, resolution, claim/boundary)`; do not revisit an unchanged target unless new evidence or a process change invalidated prior results. Stop descending when finer resolution cannot materially change a correctness decision, when required evidence/tooling is unavailable, or when an intent-dependent decision is reached. Validation feedback returns to the nearest affected model level rather than restarting the whole analysis.

### Five Phases

1. **UNDERSTAND** — establish purpose, scope, evidence, desired outcomes, constraints, and current resolution.
2. **MODEL** — extract actors, state, actions, inputs, outputs, decisions, resources, assumptions, goals, invariants, failure paths, and terminal states.
3. **CHALLENGE** — identify ambiguity, contradictions, missing transitions, undefined ownership, unreachable states, hidden assumptions, missing failure handling, and unverifiable claims. Ask what observation would falsify each important claim.
4. **IMPROVE** — before material change, declare the change contract and preserve the smallest useful baseline; then correct gaps derivable from established intent. Escalate only changes that create or alter policy, goals, or other intent.
5. **VALIDATE** — test the candidate against the predeclared contract, compare relevant before/after evidence, select the cheapest sufficient validator per claim, and feed counterexamples or regressions back into CHALLENGE. Stop when required claims are supported or remaining uncertainty requires an explicit human decision.

### Purpose at Any Resolution

Every process or subsystem must have enough purpose to judge improvement. Do not require a fully formal goal hierarchy before useful work begins. Establish the smallest defensible purpose at the current resolution, then refine only where additional resolution can change a correctness decision.

Child processes inherit applicable parent goals, constraints, and invariants. They may strengthen them but must not silently contradict them.

### Evidence Provenance and Authority

Keep requirement authority separate from interpretation. Label material process claims when authority matters:

- **OBSERVED** — directly supported by the source process, authoritative dependency, runtime/repository evidence, or explicit user evidence;
- **DERIVED** — reasoned from named observations; retain the basis;
- **ASSUMED** — necessary interpretation not established by available evidence;
- **PROPOSED** — candidate purpose, requirement, policy, or correction not yet established as intent.

A derived or proposed statement does not become established intent merely because it makes the process more coherent. Only apply a correction when authoritative evidence determines it; otherwise preserve the uncertainty or request the consequential decision.

### Uncertainty Classification

Do not treat every unknown as blocking. Classify uncertainty:

- **KNOWN + VALID** — evidence supports the claim.
- **KNOWN + INVALID** — evidence or a counterexample contradicts it.
- **UNKNOWN + RESOLVABLE** — investigate available source, repository, runtime, or other evidence before asking the user.
- **UNKNOWN + INTENT-DEPENDENT** — only the process owner can choose; explain the consequence and ask the minimum question.
- **ASSUMED** — continuation requires an assumption; state it explicitly and do not present it as verified.
- **OUT OF SCOPE** — deliberately excluded; record the boundary.

Only UNKNOWN + INTENT-DEPENDENT gaps block autonomous improvement. UNKNOWN + RESOLVABLE gaps require investigation first; they are not grounds to stop and ask the user.

### Evidence-Driven Improvement

Scale improvement evidence with consequence and uncertainty; do not impose a benchmark on trivial, reversible edits.

Before a **material behavior change**, record a small change contract before examining the candidate result:

- targeted claim/property and current failure or evidence;
- expected improvement;
- invariants/contracts that must remain true;
- observable success criterion;
- unacceptable regressions;
- smallest useful baseline of current behavior, cost, friction, or counterexample.

Then improve and validate the **delta**, not merely whether the candidate appears reasonable. Reuse comparable scenarios/evidence against before and after states where practical. For substantial redesigns, include representative success, failure, boundary, and some held-out scenarios that did not drive the change.

When subjective judgment remains, independent evaluation is preferred where practical: use a fresh agent/context, and hide old/new identity during comparison when knowing which is the candidate could bias judgment. This is an optional strengthening technique, not a required harness architecture.

If execution traces are available, inspect actual navigation, actions, tool use, backtracking, handoffs, omissions, and recovery — not only final prose. Measure only dimensions relevant to the improvement claim, such as correctness, elapsed work, steps, tool calls, human decisions, resource use, recovery quality, interruptions, or context/instruction load.

Classify a failed or disappointing change before editing again. Useful diagnostic classes include:

- **requirement** — the desired behavior/constraint is wrong, contradictory, or incomplete;
- **knowledge/evidence** — required facts are unavailable or unsupported;
- **decision/judgment** — the process leaves a consequential choice under-specified;
- **process/transition** — sequencing, state transition, guard, or terminal behavior is defective;
- **interface/contract** — caller/callee assumptions or guarantees conflict;
- **reliability/recovery** — retries, rollback, partial failure, or recovery are inadequate;
- **observability** — success, failure, or state cannot be determined reliably;
- **representation** — the underlying process is sound but its instructions/diagram communicate it incorrectly;
- **validation/model** — the validator, scenario, assumptions, or formal model do not faithfully test the intended claim.

Use the diagnosis to choose the next correction; do not add generic rules in response to an unidentified failure.

Rigor is proportional:

- routine/reversible change → direct improvement plus proportionate check;
- material behavior change → predeclared change contract + baseline + before/after comparison;
- consequential, irreversible, destructive, interruptive, or security-sensitive change → higher local resolution plus appropriate independent/adversarial and claim-level validation where practical.

### Altitude and Resolution Review

Completeness means sufficient detail for the process contract and risk at the current resolution; it does not mean equal detail everywhere. Prefer the lowest resolution that makes each decision safe and unambiguous. Review materially important nodes during CHALLENGE before treating missing detail as a gap.

For each node ask:

1. What contract must it satisfy — purpose, preconditions, guarantees, and relevant invariants?
2. What altitude/resolution is it currently expressed at?
3. What is the consequence of incorrect inference or execution?
4. How variable is the behavior a competent agent is likely to infer without more instruction?
5. Should the node be compressed, retained, or locally expanded and validated?

Use consequence and behavioral variance independently:

- **Low consequence + low variance** — compress aggressively; a short confirmation of the common path may be enough.
- **Low consequence + high variance** — state the preferred behavior where variance matters.
- **High consequence + low variance** — state the contract, critical safeguards, and verification even when the procedure is familiar.
- **High consequence + high variance** — locally expand into a precise child procedure and validate it.

Treat destructive, irreversible, interruptive, security/trust-boundary, externally visible, difficult-to-recover, concurrent/resource-sensitive, credential/money-sensitive, or partial-failure-prone actions as signals that higher local resolution may be required.

Expansion is local. Do not raise the resolution of surrounding routine nodes merely because one node needs detail. Parent nodes state contracts; child expansions state the higher-resolution procedure. A child inherits applicable parent goals, constraints, invariants, preconditions, and guarantees and must not silently weaken them.

High risk does not mean "write more." It means choose the required resolution, make the critical behavior explicit, and validate it at that resolution. Conversely, trim detail that consumes attention without changing safe execution.

#### Optional Baseline Agent Behavior Sampling

When instruction-heavy or complex processes may restate behavior capable agents already infer reliably, optionally measure that baseline before retaining the instruction load. Use neutral representative scenarios and isolated responses across supported models/harnesses; consensus measures likely inference, never correctness. Compress only behavior compatible with required invariants whose inference-failure consequence is acceptable, then validate material compression against the fuller instructions using comparable and held-out scenarios. Keep the method environment-independent; adapt it to available agent, shell, SDK, or API capabilities.

Load [baseline-agent-behavior-eval.md](./references/baseline-agent-behavior-eval.md) when this optional refinement is selected. It defines neutral scenario design, sampling/normalization, bias checks, repeated/cross-model variance interpretation, blind comparison, trace inspection, and compression validation.

### Claims Are the Unit of Validation

Do not select one validator for an entire document or process. Extract important correctness claims and validate them independently.

For each claim record:

1. the claim in falsifiable terms;
2. the failure it excludes;
3. the resolution at which it exists;
4. assumptions it depends on;
5. what observation would falsify it;
6. the cheapest sufficient validator;
7. the evidence produced and validation boundary.

### Validation Model Selection

Escalate validation only as far as needed:

- **Static inspection / observable checks** — direct structural or environmental facts.
- **Example execution / executable tests** — representative behavior is sufficient.
- **Generated or property-based tests / simulation** — broad execution sampling can challenge the claim.
- **Mermaid structural validation** — actors, actions, guards, branches, and terminal states must be explicit and traversable. Mermaid describes execution structure; it does not prove behavioral correctness.
- **TLA+ / model checking candidate** — correctness depends on multiple possible executions: concurrency, interleavings, ordering, asynchronous messages, retries, crashes, shared mutable state, resource ownership, atomicity, fairness, deadlock freedom, safety, or liveness.
- **Lean theorem-proving candidate** — correctness requires a universal proposition such as invariant preservation, semantic equivalence, termination, or a guarantee over every valid input.

Prefer the least-formal method that provides the required confidence. TLA+ and Lean are not mandatory escalation stages.

When TLA+ applies, extract state variables, initial conditions, actions/transitions, guards, safety invariants, liveness properties, and fairness/environmental assumptions. When Lean applies, extract definitions, assumptions, proposition, and proof obligations.

If formal tooling is unavailable, produce a validation handoff containing those artifacts and mark the claim UNVALIDATED. Never imply that recommending TLA+ or Lean constitutes verification.

Sources for these capability distinctions: TLA+ is a formal specification language for modeling concurrent/distributed system behaviors and TLC explores reachable states for invariant/temporal-property violations [1]. Lean is an interactive theorem prover/programming language whose kernel checks proof terms [2].

### Counterexamples and Failed Validation

Treat failures as evidence. State the violated claim and smallest relevant counterexample, diagnose it using the Evidence-Driven Improvement categories, correct only when established intent determines the change, then rerun affected validation. Do not modify a process merely to satisfy a bad model or validator.

### System Boundary Pass

For every material boundary inspect who calls it, what it calls, state crossing the boundary, caller assumptions, callee guarantees, partial-failure behavior, and recovery ownership. Cross-boundary contradictions are gaps even when each local process is internally coherent.

### Semantic Conservation for Material Rewrites

Goal attainment does not prove that every valuable original behavior survived. Before a material rewrite, inventory independently meaningful original actions/orderings, decision rules, constraints, reasoning principles, routing behavior, validation/completion conditions, and domain or maintenance invariants that could be affected.

After the candidate exists, account for each changed or removed meaning as:

- **PRESERVED** — equivalent behavior remains;
- **RELOCATED** — equivalent behavior remains at another reachable appropriate location;
- **AUTOMATED** — deterministic machinery now carries it;
- **PROVEN-REDUNDANT** — evidence shows removal does not change required execution/maintenance;
- **UNCERTAIN** — equivalence or safe removal lacks evidence;
- **LOST** — no valid carrier or redundancy evidence remains.

Reject a material improvement with a required `LOST` meaning. A behavior-affecting `UNCERTAIN` removal remains unresolved rather than being justified by high-level goal alignment.

### Evidence Trade-offs

Keep hard correctness/contract evidence, qualitative judgments, and efficiency telemetry separate. Do not average unlike evidence into one quality score. Lower cost, fewer instructions, or better readability cannot compensate for violation of a required invariant; report mixed trade-offs directly.

### Change-Impact Validation

After improvement, map changed actors, states, actions, transitions, resources, assumptions, and contracts to dependent claims. Revalidate affected claims/interfaces. Do not rerun unrelated validation without reason or assume prior evidence applies to a changed dependency.

### Authority Boundary

Improve directly only when the correction follows from established purpose, goals, invariants, constraints, or other evidence. If multiple legitimate behaviors remain and choosing among them would create policy or alter intent, explain the alternatives and consequences and ask the user.

### Completion Record

Finish only when required claims have sufficient evidence or remaining uncertainty is explicit. Return the Result Contract status plus purpose/scope, material ProcessModel elements, claim → validator → evidence mapping, addressed counterexamples, assumptions, residual risks, validation boundaries, and any useful representations. Mermaid is a projection of the model, not the model itself.

## References

[1] [TLA+ Documentation](https://lamport.azurewebsites.net/tla/tla.html) (accessed 2026-09-24)

[2] [Lean Documentation](https://lean-lang.org/documentation/) (accessed 2026-09-24)
