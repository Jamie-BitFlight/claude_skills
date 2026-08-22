# Autonomous Refinement Loop (ARL) — Knowledge Reference

**Autonomous Refinement Loop (ARL)** is pattern research into what an AI assistant needs — in information, tools, verification mechanisms, access to external resources, and knowledge of past failures — to produce outcomes that match the user's vision without requiring the human to be a synchronous blocking gate during execution.

The foundational question:

> What determines whether an AI can produce a satisfactory outcome for a given piece of work, and how do we ensure those prerequisites are met before and during execution?

ARL is not a process to run. It is a body of research that informs how processes (like SAM) should be designed, and what conditions enable autonomous execution.

**SOURCE:** [Autonomous Refinement Loop](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md)

## What This Reference Covers

This document provides:

- **Core concept (HOOTL):** What "human out of the loop" means and what it requires
- **Three-layer architecture:** Research body, execution model, observation layer
- **The gates (R1-R10):** Machine-verifiable conditions that replace human judgment at key points in iterative refinement
- **Universal principles:** Patterns that apply to any autonomous development system
- **Framework coverage:** Which gates exist in current frameworks and which must be built from scratch
- **Decision tree:** When can a human gate actually be replaced by machine verification?

When working on improvements, refinement, or autonomous execution tasks, consult this reference to understand what prerequisites must be in place, what could fail without them, and how the gates work together.

## HOOTL: Human Out Of The Loop

**DESIGN GOAL** — The concept describes the desired outcome of ARL research.

HOOTL means achieving human-in-the-loop outcome quality with human-out-of-the-loop execution.

Breaking this down:

- **Human out of the loop** = removed as a synchronous blocking gate during execution. The AI does not pause waiting for approval at every decision point.
- **Human out of the loop ≠ human not needed** — the human still defines intent, answers questions only they can answer, provides vision and priorities. The human is absolutely in the process.
- **Human still in the process** — but asynchronously, on their schedule, responding to contextualized action items rather than approving each step. The human is no longer a rate limiter on loop iteration.

The quality bar is HOOTL success: the artifact meets the same acceptance criteria as if a human reviewed every intermediate step, but the human did not have to be present synchronously to approve that work.

**SOURCE:** [HOOTL: Human Out Of The Loop](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#hootl-human-out-of-the-loop)

## Three Layers of ARL

**DESIGN GOAL** — This architecture describes how HOOTL execution is designed. The research body is observed and evidence-backed. The execution model and observation layer are design goals being researched.

### Layer 1: Research Body

The empirical findings from cross-framework analysis:

- **Failure categories (R1-R10)** — machine-verifiable conditions that replace human judgment gates at specific points in an iterative refinement loop; what goes wrong when each condition is insufficient
- **Structural principles** — patterns that ensure prerequisites are met, applicable to any autonomous development system (see Universal Principles below)
- **Decision tree for gate replacement** — conditions that ALL must hold for a human gate to be replaced by machine verification
- **Scope-feasibility matrix** — which work can run HOOTL (bounded constraints, enumerable data, binary success) and which cannot (unbounded goals, semantic knowledge required)
- **Eliminable/front-loadable/irreducible taxonomy** — classifying each human touchpoint and what it takes to remove the human from it

### Layer 2: Execution Model

How HOOTL execution works in practice:

- **Pre-discovery decomposition** — before execution begins, decompose work into bounded components (where HOOTL is feasible) and unbounded components (where human input is required). Capture clear, measurable goals for bounded work; identify decision points where humans must answer questions only they can answer.
- **Asynchronous feedback queue** — when the AI discovers gaps during execution, they enter a managed queue rather than blocking execution. Each queue item shows DAG visibility: what does this question block and unblock? Stale items are pruned automatically as they become moot.
- **AI user representatives** — a team of agents that triages inbound questions before they reach the human. They ask: why is this being asked? Is there precedent in the user's other projects? Can this be resolved from available tools, external resources, or documented conventions? Questions only reach the human when the AI genuinely cannot resolve them.
- **Question-to-action-item conversion** — the AI exhausts every available resource before surfacing anything to the human. When it does surface something, it is **completed work plus an async action item**, not a blocking question. The human acts on their schedule.

### Layer 3: Observation

Passive agents monitoring execution in real-time:

- Catching mistakes in progress (platform-specific errors, syntax issues, naming conflicts)
- Detecting silent compromises (worker changed the desired outcome instead of escalating)
- Identifying overlooked requirements (acceptance criteria not being addressed)
- Spotting systemic issues (file conflicts, broken cross-references, pattern violations)
- Feeding observations back into both the immediate workflow (live correction) and the research body (new failure categories, refined gate conditions)

**agentskill-kaizen** is the current implementation of this layer in post-hoc mode (mining historical transcripts after sessions complete). The ARL vision extends it to real-time observation during execution.

**SOURCE:** [Three Layers of ARL](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#three-layers-of-arl)

## Relationship Triangle: ARL, SAM, and agentskill-kaizen

- **ARL** produces the theory — failure categories, prerequisites, conditions, principles. "What are the prerequisites for autonomous execution?"
- **SAM** applies the theory — methodology with touchpoints informed by ARL research. "How do we apply these prerequisites in a development process?"
- **agentskill-kaizen** produces the evidence — mining real sessions to validate or challenge ARL's categories. "Do these prerequisites actually predict success?"

The three together form a research cycle: ARL hypothesizes, SAM applies, agentskill-kaizen validates.

**SOURCE:** [Relationship Triangle](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#relationship-triangle-arl-sam-and-agentskill-kaizen)

## Interaction Spectrum

ARL researches what it takes to move AI-human interactions from blocking, high-friction to asynchronous, low-friction. The spectrum, from worst to best:

1. **Question with no context** — "Should I add PyPI publishing?" (blocks, requires human to think)
2. **Question with context** — "Your other projects have this, should I add it?" (blocks, easier to answer)
3. **Statement requesting confirmation** — "I'm going to add this based on your other projects, confirm or stop me" (lower friction, still blocks)
4. **Completed work with async follow-up** — "I did it, here's what you need to do on your end when ready" (doesn't block, human acts on their schedule)

The goal is moving as many interactions as possible to level 4. Level 4 is HOOTL: the human gets quality outcomes without being a synchronous blocking gate.

**SOURCE:** [Interaction Spectrum](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#interaction-spectrum)

## The Gates (R1-R10)

These gates formalize the machine-verifiable conditions that replace human judgment at key points in an iterative refinement loop.

| Gate | What It Checks | When It Fires | What Failure Looks Like |
|------|----------------|---------------|------------------------|
| **R1: Information Completeness** | Sufficient context to operate loop without escalation | Loop entry, re-entry after escalation | Loop proceeds with gaps, agent hallucinate-fills missing information, produces fluent but wrong artifacts |
| **R2: Loop Detection** | Oscillating, stalling, or exceeding resource bounds | Start of each iteration before assessment | Loop runs indefinitely without converging, fix A breaks B repeatedly, same findings recurring |
| **R3: Validity Filtering** | Findings have verifiable evidence (file:line citations) | After assessment, before planning | False positives consume iteration budget, regressions introduced, phantom issues trigger changes |
| **R4: Plan Quality** | Plan internally consistent, addresses actual findings | After planning, before implementation | Inconsistent plan proceeds, addresses wrong findings, changes must be reverted |
| **R5: Purpose Anchor** | Artifact still serves original stated purpose | Captured at iteration 0, checked each iteration | After N iterations, artifact optimized for assessment metrics but no longer serves original use case |
| **R6: Content-Loss Detection** | All semantic units preserved after changes | After implementation, before next iteration | Refactoring removes sections deemed "redundant", no gate catches removal, human discovers loss later |
| **R7: Convergence Tracking** | Findings decreasing, stable, or alternating across iterations | Each iteration boundary after assessment | Loop cannot determine progress, fixes trivial issues indefinitely, or oscillates without converging |
| **R8: Proportionality Check** | Proposed fix proportional to finding severity | During plan quality gate (R4) | Low-severity finding triggers high-scope change that introduces risk without proportional benefit |
| **R9: Downstream Impact** | All references still resolve after changes | After implementation, alongside R6 | Refactoring renames a file, breaks three other components linking to old path, not detected until runtime |
| **R10: Split Justification** | New component independently viable, not just parent-dependent | When plan proposes splitting content into separate artifacts | Component split into three pieces, two only used from parent, adds navigation complexity without value |

**SOURCE:** [The 10 Gates](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#the-10-gates)

## Gate Coverage Across Existing Frameworks

| Coverage Level | R-Requirements | What Exists Today |
|---|---|---|
| **Import directly** | R1, R3, R4 | RT-ICA (SAM), GAN-inspired validation (Octocode/BMAD), 7-dimension plan checking (GSD) |
| **Partial coverage** | R2, R5, R9 | Bounded iteration count (GSD), objective injection (Ralph), downstream impact analysis (Octocode) |
| **Build from scratch** | R6, R7, R8, R10 | No framework provides content-loss detection, convergence tracking, proportionality checks, or split justification |

The build-from-scratch requirements all emerge specifically from iterative refinement — they are invisible to single-pass pipeline designs.

**SOURCE:** [Gate Coverage Across Existing Frameworks](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#gate-coverage-across-existing-frameworks)

## Decision Tree: When Can a Human Gate Be Replaced?

A human gate can potentially be replaced by machine-verifiable conditions when ALL of the following hold:

1. **The check has an external truth source** — something outside the AI's own output to verify against (git state, test results, file existence, structural inventory)
2. **The check operates on a single dimension** — one aspect of quality, not holistic judgment
3. **Success and failure are distinguishable without domain knowledge** — pass/fail determinable from structural properties, not semantic understanding
4. **The scope is bounded** — the check operates on a defined artifact with known boundaries

When ANY of these conditions fails, the gate requires either human judgment or a more sophisticated verification mechanism (adversarial review, cross-examination between independent agents, or escalation).

**Evidence status:** These conditions were synthesized from cross-framework evidence. They correlate with gates classified as eliminable, but have not been tested as a predictive model.

**SOURCE:** [Decision Tree](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#decision-tree-when-can-a-human-gate-be-replaced)

## Universal Principles

Patterns discovered across the frameworks studied that apply to any autonomous development system:

1. **Structure Over Instruction** — Pipeline forces checks rather than asking agents to check themselves. Telling an AI "please do X" is unreliable; structuring the pipeline so X is the only possible path is reliable.
2. **Front-Loading Reduces Runtime Gates** — More context captured upfront = fewer human interventions during execution. Every point of ambiguity in the goal is a point where the loop will either guess or stall.
3. **AI Cannot Reliably Self-Evaluate** — Independent verification structurally separates producer from evaluator. An agent evaluating its own work shares the same blind spots that produced the work.
4. **Compression Is Architectural** — Information compression works when architecture forces it (limited context budget, fixed output format), not when instructed ("please summarize").
5. **Iteration-Aware State Required** — Loop control needs state persisting across iterations. Single-pass frameworks cannot control iterative loops because convergence, oscillation, and drift require cross-iteration tracking.
6. **Parallelism Enables Independent Verification** — Multiple agents checking different dimensions simultaneously reduces shared blind spots and latency. But coordination complexity is a real cost.
7. **Failure Paths Need More Compression** — All frameworks compress success paths well. Failure paths — when the human most needs compressed context — are less compressed.

**SOURCE:** [Universal Principles](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#universal-principles)

## Scope-Feasibility Matrix

The same type of human judgment can be eliminable in one context and irreducible in another. The determining factors are:

| Scope Clarity | Goal Measurability | Data Enumeration | Human Gates Eliminable? |
|---|---|---|---|
| **High** (specific tool, platform, use case) | **High** (binary pass/fail, checklist) | **High** (official docs, known examples) | **Yes** — Autonomous loop feasible |
| **Medium** (domain-specific best practices) | **Medium** (scoring with weights) | **Medium** (reference examples, community patterns) | **Partial** — Autonomous with periodic human checkpoints |
| **Low** (general improvement, meta-goals) | **Low** (subjective, emergent criteria) | **Low** (unknown what "complete" means) | **No** — Requires human at each decision point |

This means ARL cannot be applied uniformly. A scope-classification step must precede any attempt at autonomous operation.

**SOURCE:** [Key Findings](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md#key-findings)

## References

Complete detail on each gate, framework patterns, and prerequisites:

- [Autonomous Refinement Loop — Full Research](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/README.md) — Canonical source for all ARL documentation
- [Synthesis: ARL-Applicable](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/references/synthesis-arl-applicable.md) — R1-R10 mapped to framework mechanisms, loop structure
- [Synthesis: General Theory](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/references/synthesis-general-theory.md) — 7 universal principles for autonomous development systems
- [Expert Panel Q&A](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/references/qa-expert-panel.md) — Full Phase 1-4 expert panel record (6 experts, 5 question groups, 10 R-requirements)
- [Autonomous Loop Principles](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/autonomous-loop-principles.md) — SAM extension analysis (cross-reference)
- [Expert Panel Methodology](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/docs/guides/expert-panel-methodology.md) — Multi-agent cross-examination process
