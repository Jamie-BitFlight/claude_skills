---
name: improve-processes
description: Process quality methodology for the process-siren agent — use before or during Mermaid conversion when the source process shows ambiguity, missing decisions, undefined actors, vague conditions, or structural weakness. Provides triage sequence, excellence criteria, and an improvement framework drawn from Lean, Six Sigma, BPR, Design Thinking, Systems Thinking, and Theory of Constraints. Activates when source content is poorly structured enough that converting it as-is would encode wrong behavior for AI readers.
---

# Improve Processes

Process-siren's job is semantic fidelity. Faithful conversion of a flawed process encodes the flaws with false precision. Use this skill when the source process needs improvement before — or alongside — Mermaid conversion.

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

### Five Phases

1. **UNDERSTAND** — establish purpose, scope, evidence, desired outcomes, constraints, and current resolution.
2. **MODEL** — extract actors, state, actions, inputs, outputs, decisions, resources, assumptions, goals, invariants, failure paths, and terminal states.
3. **CHALLENGE** — identify ambiguity, contradictions, missing transitions, undefined ownership, unreachable states, hidden assumptions, missing failure handling, and unverifiable claims. Ask what observation would falsify each important claim.
4. **IMPROVE** — correct gaps derivable from established intent. Escalate only changes that create or alter policy, goals, or other intent.
5. **VALIDATE** — select the cheapest sufficient validator per claim, gather evidence, and feed counterexamples or failures back into CHALLENGE. Stop when required claims are supported or remaining uncertainty requires an explicit human decision.

### Authoritative Loop

```mermaid
flowchart TD
    Start(["Process or system received"]) --> Scope["Discover relevant source material, constraints, existing behavior, and surrounding system"]
    Scope --> Purpose{"Purpose and desired outcomes sufficiently explicit?"}
    Purpose -->|"No"| PurposeGap["Identify missing purpose, goals, or success criteria"]
    PurposeGap --> ResolvePurpose{"Can available evidence resolve the gap without inventing intent?"}
    ResolvePurpose -->|"Yes"| DerivePurpose["Derive candidate purpose and record evidence"]
    DerivePurpose --> Purpose
    ResolvePurpose -->|"No"| AskPurpose["Explain gap and ask only questions required to continue"]
    AskPurpose --> Blocked(["Blocked pending information"])
    Purpose -->|"Yes"| Model["Build semantic model at current resolution"]
    Model --> Inventory["Inventory actors, states, actions, inputs, outputs, decisions, resources, constraints, failures, and terminal states"]
    Inventory --> Claims["Extract goals, invariants, assumptions, guarantees, safety, liveness, and other correctness claims"]
    Claims --> Gaps["Detect ambiguity, contradictions, missing transitions, undefined ownership, unreachable states, hidden assumptions, and unverifiable claims"]
    Gaps --> ResolveGap{"Can gaps be resolved from established intent and evidence?"}
    ResolveGap -->|"No"| Explain["Report known facts, gaps, consequences, and minimal questions"]
    Explain --> Blocked
    ResolveGap -->|"Yes"| Improve["Produce candidate improvement preserving established intent"]
    Improve --> Reclaims["Re-extract claims from candidate"]
    Reclaims --> Validate["Select cheapest sufficient validator for each important claim"]
    Validate --> Kind{"Claim type?"}
    Kind -->|"Observable execution"| Tests["Examples, executable checks, simulation, or property-based tests"]
    Kind -->|"Structural or routing"| Mermaid["Mermaid plus semantic-fidelity checks"]
    Kind -->|"State-space or concurrency"| TLA["TLA+ model plus TLC when tooling is available"]
    Kind -->|"Universal proposition"| LeanProof["Lean specification plus proof when tooling is available"]
    Kind -->|"Human or environmental"| Evidence["Inspection, measurement, experiment, or explicit user acceptance"]
    Tests --> Result
    Mermaid --> Result
    TLA --> Result
    LeanProof --> Result
    Evidence --> Result
    Result{"Claim supported at required confidence?"}
    Result -->|"No"| Diagnose["Turn failure or counterexample into diagnostic evidence"]
    Diagnose --> Root["Identify violated assumption, missing behavior, bad requirement, model defect, or implementation defect"]
    Root --> Intent{"Would correction create or change established intent?"}
    Intent -->|"No"| Improve
    Intent -->|"Yes or uncertain"| Explain
    Result -->|"Yes"| More{"Important unvalidated claims remain?"}
    More -->|"Yes"| Validate
    More -->|"No"| Resolution{"Would finer resolution materially expose new failure modes?"}
    Resolution -->|"Yes"| Decompose["Decompose relevant subsystem; inherit parent goals, constraints, and invariants"]
    Decompose --> Model
    Resolution -->|"No"| Final["Record validated model, evidence, assumptions, residual risks, and validation boundaries"]
    Final --> Done(["Ready for use"])
```

### Purpose at Any Resolution

Every process or subsystem must have enough purpose to judge improvement. Do not require a fully formal goal hierarchy before useful work begins. Establish the smallest defensible purpose at the current resolution, then refine only where additional resolution can change a correctness decision.

Child processes inherit applicable parent goals, constraints, and invariants. They may strengthen them but must not silently contradict them.

### Uncertainty Classification

Do not treat every unknown as blocking. Classify uncertainty:

- **KNOWN + VALID** — evidence supports the claim.
- **KNOWN + INVALID** — evidence or a counterexample contradicts it.
- **UNKNOWN + RESOLVABLE** — investigate available source, repository, runtime, or other evidence before asking the user.
- **UNKNOWN + INTENT-DEPENDENT** — only the process owner can choose; explain the consequence and ask the minimum question.
- **ASSUMED** — continuation requires an assumption; state it explicitly and do not present it as verified.
- **OUT OF SCOPE** — deliberately excluded; record the boundary.

Only UNKNOWN + INTENT-DEPENDENT gaps block autonomous improvement. UNKNOWN + RESOLVABLE gaps require investigation first; they are not grounds to stop and ask the user.

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

### Counterexamples Drive Improvement

Treat validation failures as first-class evidence. Translate a failing execution, model-checker trace, test failure, or proof failure back into process vocabulary:

1. state the violated claim;
2. show the smallest relevant execution or counterexample;
3. identify the violated assumption or missing/incorrect behavior;
4. distinguish process defect, requirement defect, model defect, validator mismatch, and implementation defect;
5. propose a correction only when established intent determines it;
6. re-enter IMPROVE, re-extract claims, and rerun affected validation.

Do not modify a process merely to satisfy a bad model. Diagnose the source of the mismatch first.

### System Boundary Pass

For every material boundary inspect who calls it, what it calls, state crossing the boundary, caller assumptions, callee guarantees, partial-failure behavior, and recovery ownership. Cross-boundary contradictions are gaps even when each local process is internally coherent.

### Change-Impact Validation

After improvement, map changed actors, states, actions, transitions, resources, assumptions, and contracts to dependent claims. Revalidate affected claims/interfaces. Do not rerun unrelated validation without reason or assume prior evidence applies to a changed dependency.

### Authority Boundary

Improve directly only when the correction follows from established purpose, goals, invariants, constraints, or other evidence. If multiple legitimate behaviors remain and choosing among them would create policy or alter intent, explain the alternatives and consequences and ask the user.

### Completion Record

An improved process/system is ready only when its required claims have sufficient evidence or unresolved uncertainty is explicitly surfaced. Record:

- purpose and scope at the validated resolution;
- semantic model: actors, states, actions, decisions, resources, constraints, and failure paths;
- correctness model: claims, invariants, safety/liveness properties, and assumptions;
- claim → validator → evidence mapping;
- counterexamples addressed;
- residual uncertainty and unvalidated claims;
- environmental dependencies and validation boundaries;
- useful representations such as Mermaid, tests, TLA+, Lean, or explanatory documentation.

Mermaid is one projection of this semantic model, not the semantic model itself.

## Improvement Techniques

Use these inside CHALLENGE/IMPROVE, not as a second workflow: rewrite outcomes measurably; replace abstract verbs with concrete actions; make guards observable; define inputs/outputs; remove or rewrite no-op work; exercise success and failure examples; stress edge cases; minimize cognitive load; ensure execution is auditable. The authoritative workflow remains UNDERSTAND → MODEL → CHALLENGE → IMPROVE → VALIDATE.
