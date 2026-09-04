---
name: dh-glossary
description: One-line definitions of development-harness (dh) plugin terminology — RT-ICA, ARL, SAM, the S1-S7 pipeline stage names, Impact Radius — each with a pointer to its canonical source file. Use when a dh skill, agent, or workflow step references a term without defining it, before guessing what the term means from its observed outputs, or when asked what a dh concept or acronym stands for.
user-invocable: true
---

# dh Glossary

A mandate that names a dh concept states only the name, not the method — the orchestrator sees the
outcome (a verdict, a gate, a report) and can misinfer the mechanism from watching what it does.
Load this skill instead of inferring; each entry states the method, not just the outcome, and
points to the file that is authoritative if this entry ever drifts from it.

## Terms

**RT-ICA** (Reverse Thinking - Information Completeness Assessment) — works backward from the
stated goal through its prerequisite chain: what must exist to reach the goal, then what each of
those things requires, recursively back to the current state. Classifies each prerequisite as
AVAILABLE, DERIVABLE, or MISSING. `dh:rt-ica` blocks planning on any MISSING condition (S2
implementation gate); `dh:planner-rt-ica` is the non-blocking sister used during grooming, which
localizes a MISSING condition to the affected task instead of halting. Canonical:
[`skills/rt-ica/SKILL.md`](../rt-ica/SKILL.md).

**ARL** (Autonomous Refinement Loop) — research into the prerequisites for autonomous agent
execution without synchronous human blocking gates: failure categories, and the conditions under
which a machine-verifiable check can replace human judgment. dh's human-touchpoint model is
ARL-derived — see the S1-S7 entry below. Canonical:
`plugins/plugin-creator/skills/arl/SKILL.md`.

**SAM** (Stateless Agent Methodology) — the 7-stage development pipeline this harness implements
(S1-S7, below). "Stateless" means each stage's state lives in a provider-owned artifact, never in
conversation history — a stage reads its input from the prior stage's registered artifact, not
from what an agent remembers saying earlier. Canonical: `plugins/development-harness/AGENTS.md`
("SAM 7-Stage Pipeline").

**S1-S7** — the SAM pipeline stage names, in order: **S1 Discovery** (understand the feature,
codebase, constraints) → **S2 Planning + RT-ICA** (generate a plan, gated by `dh:rt-ica`) → **S3
Context Integration** (validate the plan against actual codebase state) → **S4 Task
Decomposition** (break the plan into executable tasks) → **S5 Execution** (implement tasks via
language-specific specialists) → **S6 Forensic Review** (verify each task against its acceptance
criteria) → **S7 Final Verification** (certify the feature meets the original requirements). Not
every stage requires human review — ARL-derived constraint analysis decides when to escalate, not
a fixed checkpoint per stage. Canonical: `plugins/development-harness/AGENTS.md` ("How It Works").

**Impact Radius** — the backlog-item section listing every system a proposed change affects
(code, docs, configuration, CI, tests, agent instructions), written by `@dh:impact-analyst` before
planning. The feasibility gate and grooming staleness checks read this section to size a change's
blast radius; an item using an older grooming template may have this content under a `Resources`
section instead — readers of the primary key fall back to it. Canonical:
`plugins/development-harness/agents/impact-analyst.md`.
