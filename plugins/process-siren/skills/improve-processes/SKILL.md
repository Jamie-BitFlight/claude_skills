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

When a process is large, growing complex, or appears to restate behavior agents may already infer reliably, optionally measure baseline behavior before retaining that instruction load. This is a refinement method, not a mandatory gate or prescribed tool. Adapt execution to whatever isolated-agent, shell, harness, SDK, or API capability exists in the environment.

The experiment asks **what an otherwise capable agent naturally does**, not whether it can reproduce the process being evaluated. Scenario design therefore matters as much as sample size.

##### Scenario design

Create several realistic situations that exercise the same underlying capability under different incidental details. Each prompt should contain only information the agent would naturally have at that point in real execution:

- state the situation, available evidence/resources, constraints that genuinely exist, and desired outcome;
- ask what steps/actions the agent would take next;
- vary names, ordering, surrounding context, and non-essential details so repeated wording does not manufacture consensus;
- include ordinary cases plus relevant boundary/failure cases when those are part of the capability;
- keep the desired outcome constant enough that returned approaches remain comparable;
- make each query independent and single-response where practical so previous samples cannot anchor later ones.

Do **not** expose the target process, its step names, preferred ordering, expected safeguards, implementation-specific vocabulary, or the hypothesis being tested unless that information would genuinely exist in the real scenario. Avoid leading constructions such as "make sure to", "safely", "correctly", "without losing data", "following best practices", named techniques, or questions that enumerate candidate actions. Such wording can cue the behavior whose spontaneous presence is being measured.

Prefer neutral prompts such as:

```text
You are in <concrete situation>. You have <resources/evidence actually available>.
Your desired outcome is <observable outcome>.
What steps would you take?
```

rather than:

```text
How would you safely perform <task> while ensuring you verify X, preserve Y,
and recover if Z fails?
```

The second prompt has already supplied much of the process and cannot measure whether agents infer those steps independently.

##### Sampling and interpretation

1. Run at least 10 isolated responses across available models/harnesses where practical. Prefer model and harness diversity over repeated samples from one configuration when the question is what agents generally infer.
2. Preserve raw responses before interpretation. Normalize them into comparable semantic steps without forcing differently expressed actions into the same category.
3. Identify high-consensus behavior, variable decisions, common omissions, ordering differences, and unsafe variants. Look across scenarios as well as models: behavior that appears only under one wording may be prompt-sensitive rather than common knowledge.
4. Compare observations with the ProcessModel's required contracts and invariants. Consensus measures likely inference, not correctness or safety.
5. Treat absence carefully. A step omitted from a concise answer may be implicit rather than behavior the agent would omit during execution. When that distinction materially affects compression, use a scenario that makes the decision observable rather than asking a leading follow-up.
6. Compress high-consensus behavior only when it satisfies required invariants and the consequence of inference failure is acceptable. A short confirmation may remain useful for sequencing or contract boundaries.
7. Specify exact/preferred behavior for high-variance decisions. For consequential high-variance nodes, locally expand and validate the child procedure.
8. Record scenarios, prompt wording, model/harness diversity, sample count, normalization decisions, observed consensus/variance, unsafe variants, and the resulting instruction decision. Do not claim universality from the sample.

##### Compression validation

Baseline sampling discovers candidate prior knowledge; it does not by itself justify deleting instructions. Before examining sample results, record the contract-relevant invariants, unacceptable outcomes, and material decision points that compression must preserve so success criteria cannot drift toward outputs that merely look plausible.

When compression is material, optionally validate the candidate instruction set against the fuller version:

1. Run the same representative scenarios with the full and compressed instructions under comparable tools/environment.
2. Include held-out scenarios that were not used to decide what to compress; do not tune only to the discovery scenarios.
3. Repeat selected scenario/model combinations when practical. Separate within-model stochastic variation, consistent cross-model disagreement, and sensitivity to scenario wording — each is a different reason behavior may need explicit instruction.
4. Where practical, compare outputs or execution traces without telling the evaluator which instruction variant produced them. Judge against the pre-recorded contract rather than preference for brevity or the newer version.
5. If the harness exposes execution traces, inspect actions, navigation, tool use, omissions, and recovery behavior as well as the final answer. A model mentioning a safeguard is weaker evidence than observing it perform the safeguard when required.
6. Observe the benefit of compression where available: instruction/context reduction, task success, unsafe or contract-violating behavior, execution time, and unnecessary tool/work expansion. No fixed metric or tooling is required.
7. Restore or specify behavior when compression causes a contract-relevant regression. Retain compression when behavior remains within the contract across the evidence collected.

Cross-model evidence should reflect the models the process is expected to support. Behavior consistently inferred by stronger models but missed by a supported weaker model is not safely redundant for that deployment context.

##### Bias checks

Before using the sample, ask:

- Would a respondent know the preferred process merely from vocabulary or facts included in the prompt?
- Does the prompt imply that a particular safeguard, ordering, tool, or failure mode should be considered?
- Are scenarios diverse enough that consensus is not an artifact of one framing?
- Did normalization erase meaningful differences between responses?
- Are we mistaking common model training patterns for requirements of this specific system?
- Would removing the instruction still be acceptable if a future capable model chose a different but contract-compatible path?

If these checks fail, redesign the scenarios rather than treating the resulting consensus as evidence for compression.

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
