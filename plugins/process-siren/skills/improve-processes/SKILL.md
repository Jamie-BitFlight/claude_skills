---
name: improve-processes
description: Process quality methodology for the process-siren agent — use before or during Mermaid conversion when the source process shows ambiguity, missing decisions, undefined actors, vague conditions, or structural weakness. Provides triage sequence, excellence criteria, and an improvement framework drawn from Lean, Six Sigma, BPR, Design Thinking, Systems Thinking, and Theory of Constraints. Activates when source content is poorly structured enough that converting it as-is would encode wrong behavior for AI readers.
---

# Improve Processes

Process-siren's job is semantic fidelity. Faithful conversion of a flawed process encodes the flaws with false precision. Use this skill when the source process needs improvement before — or alongside — Mermaid conversion.

## When to Apply

Apply before converting when the source shows ANY of:

- Abstract verbs with no concrete action ("handle", "manage", "ensure")
- Conditions that cannot be evaluated by an AI agent ("when appropriate", "if needed")
- Missing entry or exit conditions
- Undefined actors ("we", "the system", "someone")
- Steps that do not change state (pure description, no action)
- No feedback loop or error path

## Frameworks (Reference Only)

These frameworks share one principle — a process must make its permitted behavior explicit, auditable, and actor-owned. Do not confuse explicit behavior with determinism: concurrent or distributed processes may intentionally permit multiple valid next states.

**Lean** (Ohno) — eliminate steps that produce no state change; apply 5 Whys to trace ambiguity to its root

**Six Sigma** / DMAIC (Smith) — Define outcome, Measure current state, Analyze gap, Improve, Control recurrence

**BPR** (Hammer) — radical question: "If we started from scratch, what would this look like?"

**Design Thinking** (IDEO/Brown) — Empathize with the agent executing the process; design for their decision points

**Systems Thinking** (Senge) — identify feedback loops and side effects before encoding structure

**Theory of Constraints** (Goldratt) — find the bottleneck step; simplify around it before adding branches

**Antifragility** (Taleb) — prefer processes that improve under stress over processes that merely tolerate it

## Excellence Checklist

Before converting, verify the source process satisfies:

- [ ] Clarity — no interpretive gaps; every term has one meaning
- [ ] Explicit behavior — permitted outcomes and transitions are defined; require determinism only where the process contract requires one outcome
- [ ] Minimal cognitive load — relies on structure, not memory
- [ ] Explicit feedback loops — error paths and retry conditions stated
- [ ] Measurable outcomes — each terminal state has an observable signal
- [ ] Visible constraints — blockers and preconditions named, not implied
- [ ] Ownership — every step names the actor
- [ ] Edge case coverage — at least one failure scenario is handled
- [ ] Teachable in 5 minutes — a novice can follow it cold
- [ ] Auditable — execution can be traced and verified after the fact

## Pre-Conversion Completeness Gate

After reading the process-under-review and all linked or referencing files, evaluate this gate before any Mermaid conversion begins.

**Question:** Are all branches, conditions, and terminal states derivable from what has been read — with no unbound unknowns?

```mermaid
flowchart TD
    Read["Read process-under-review<br>and all linked/referencing files"] --> Inventory["Inventory all steps, conditions,<br>branches, and terminal states<br>found in the source material"]
    Inventory --> Gate{"Are all branches, conditions,<br>and terminal states derivable<br>from the source — with no<br>unbound unknowns?"}
    Gate -->|"Yes — all structure is derivable"| Triage["Proceed to Triage Protocol<br>then Mermaid conversion"]
    Gate -->|"No — unknowns remain"| Coach["Enter coach-mode<br>Stop conversion entirely"]
    Coach --> Report["Produce BLOCKED report<br>(see Coach-Mode Report Format below)"]
    Report --> Done(["Return report to process author<br>Await answers before any conversion"])
```

### Why This Gate Exists

Converting an incomplete process produces a diagram that looks authoritative but encodes ambiguity as if it were resolved. An AI agent reading that diagram will follow the false structure and behave incorrectly. Coach-mode surfaces the incompleteness instead of hiding it.

### Coach-Mode Report Format

When the gate returns NO, produce this report — do not produce any Mermaid:

```text
CONVERSION ASSESSMENT

Goal:
- [One sentence stating what the process is intended to accomplish]

Source material read:
- [List each file or section examined, with path or reference]

What is known (derivable from source):
- [Fact 1 — cite the source section]
- [Fact 2 — cite the source section]
- ...

What is unknown or unbound:
- [Missing branch] | Gap: [what is undefined] | Source: [which file/section is silent on this]
- [Ambiguous condition] | Gap: [what observable fact is missing] | Source: [which file/section]
- [Undefined terminal state] | Gap: [what success/failure looks like] | Source: [absent from all files]
- [Step referencing undefined thing] | Gap: [the undefined reference] | Source: [where the reference appears]

Questions the process author must answer before conversion can proceed:

[Category — e.g., Branching Conditions]:
- [Question 1] (needed because: [why this blocks a specific diagram node or edge])
- [Question 2] (needed because: ...)

[Category — e.g., Terminal States]:
- [Question] (needed because: ...)

Decision:
- BLOCKED

Conversion will proceed once all questions above are answered.
```

**Report field rules:**

- "What is known" — list only facts directly readable or unambiguously derivable from the source files; cite the source for each
- "What is unknown or unbound" — list only genuine gaps; do not list things that are merely implicit if the implication is unambiguous
- "Questions" — one question per gap; ask only what is missing; do not ask about things already answered in the source
- "BLOCKED" is the only valid verdict when the gate returns NO; there is no partial conversion

## Triage Protocol

```mermaid
flowchart TD
    Start(["Source process received"]) --> O{"Is the intended outcome<br>stated in one measurable sentence?"}
    O -->|"No"| FixO["Rewrite outcome statement<br>before proceeding"]
    O -->|"Yes"| A{"Is the actor named<br>for every step?"}
    FixO --> A
    A -->|"No — actor undefined"| FixA["Name actor per step;<br>ask user if ambiguous"]
    A -->|"Yes"| B{"Do all steps change observable state?"}
    FixA --> B
    B -->|"No — some steps are pure description"| FixB["Remove or rewrite no-op steps<br>as concrete actions"]
    B -->|"Yes"| C{"Are all decision conditions<br>evaluable without interpretation?"}
    FixB --> C
    C -->|"No — vague conditions remain"| FixC["Replace with observable facts:<br>exit code, file existence, string match"]
    C -->|"Yes"| D{"Are entry and exit<br>conditions explicit?"}
    FixC --> D
    D -->|"No"| FixD["Add entry precondition<br>and exit terminal state"]
    D -->|"Yes"| Convert(["Process is ready for Mermaid conversion"])
    FixD --> Convert
```

## Validation Model Selection

After completeness and triage establish what the process means, identify the important correctness claims before choosing how to validate them. Classify claims independently: one process may need more than one validation model.

For each important claim, ask in order:

1. **What failure must be excluded?** State the prohibited behavior or required property in observable terms.
2. **At what resolution does the claim exist?** Distinguish workflow/system behavior from component, algorithm, or transformation behavior.
3. **What is the least-formal model capable of falsifying or proving it?** Do not add formalism that buys no additional confidence.

Route the claim as follows:

- **Executable checks/tests** — use when representative executions or property-based tests provide sufficient evidence.
- **Mermaid structural validation** — use when the claim is that actors, steps, guards, branches, and terminal states are explicit and traversable. Mermaid specifies execution structure; it does not prove behavioral correctness.
- **TLA+ candidate** — use when correctness depends on multiple possible executions: concurrency, interleavings, message/order variation, retries, crashes, shared mutable state, resource ownership, atomicity, fairness, deadlock freedom, safety invariants, or liveness requirements. Extract state variables, initial conditions, actions/transitions, guards, safety invariants, liveness properties, and environmental/fairness assumptions. Prefer model checking when finite state-space exploration can expose a counterexample.
- **Lean candidate** — use when correctness requires a universal proposition over values, transformations, or formally defined states, such as invariant preservation, semantic equivalence, termination, or "for every valid input" guarantees. Prefer a cheaper validation method when representative execution or state-space exploration is sufficient.

Do not route an entire document to TLA+ or Lean merely because one claim qualifies. Route individual claims and retain Mermaid for the executable process representation when useful.

### Formal-Validation Signals

When reviewing a process, explicitly inventory these signals if present:

- shared mutable state or exclusive resources
- concurrent or independently scheduled actors
- ordering assumptions or asynchronous messages
- retries, crashes, recovery, rollback, or partial failure
- atomic operations or transactions
- fairness or eventual-progress assumptions
- safety requirements — something prohibited must never occur
- liveness requirements — something required must eventually occur
- universal transformation or preservation claims
- equivalence or termination claims

A TLA+ or Lean classification is a recommendation to create or invoke an appropriate formal model; do not invent a proof or claim verification from the process diagram alone.

### Validation Gate

Before declaring an improved process ready, record:

- the important correctness claims identified
- the failure mode each claim excludes
- the resolution at which each claim exists
- the selected validation model and why it is sufficient
- assumptions required by that validation
- the success criterion: observable check, counterexample absence within a stated model, or machine-checked proof

A process may be structurally ready for Mermaid conversion while still carrying correctness claims that require separate validation. Do not describe Mermaid syntax validation or semantic-fidelity checking as proof that those claims hold.

## Practical Improvement Framework

Apply in sequence when rebuilding a weak process:

```mermaid
flowchart TD
    S1["1. Rewrite outcome as one measurable sentence"] --> S2
    S2["2. Replace abstract verbs with concrete actions"] --> S3
    S3["3. Add decision gates — If X, then Y"] --> S4
    S4["4. Define inputs and outputs for each step"] --> S5
    S5["5. Remove steps that do not change state"] --> S6
    S6["6. Add at least one correct execution example"] --> S7
    S7["7. Add at least one failure example"] --> S8
    S8["8. Stress-test: what happens at each edge case?"] --> S9
    S9["9. Time the walkthrough — can a novice follow in 5 minutes?"] --> S10
    S10["10. Confirm auditable — can execution be traced after the fact?"] --> Done(["Improved process ready"])
```
