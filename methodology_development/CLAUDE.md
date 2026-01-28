# Methodology Development - AI-Facing Instructions

This directory contains documentation for the **Stateless Agent Methodology (SAM)**, a constraint-driven development framework designed to compensate for LLM limitations through architectural structure rather than behavioral instructions.

---

## Core Insight

**Claude is a stateless computation engine, not a knowledge worker.**

Treat Claude like a pure function:

- **Input**: Complete context (task file with all answers)
- **Output**: Verified result
- **No side effects**: Fresh context each time
- **No memory**: Everything externalized to artifact files

---

## Directory Contents

| File                                                                                         | Purpose                                                                              |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [stateless-agent-methodology.md](./stateless-agent-methodology.md)                           | Core methodology - problem analysis, architectural solution, pipeline specifications |
| [stateless-software-engineering-framework.md](./stateless-software-engineering-framework.md) | Expanded framework with agent specs and implementation roadmap                       |
| `stateless-agent-methodology-vs-*.md`                                                        | Comparison documents against other frameworks                                        |

---

## When to Consult This Directory

The model MUST consult SAM documentation when:

1. **Designing multi-agent workflows** - Apply stateless agent principles
2. **Creating task decomposition** - Follow atomic task patterns with embedded context
3. **Implementing verification gates** - Use RT-ICA and forensic review patterns
4. **Debugging agent failures** - Reference failure mode elimination strategies
5. **Comparing methodologies** - Check comparison documents for integration guidance

---

## Key SAM Principles

| Principle                      | Implementation                                    | Rationale                                          |
| ------------------------------ | ------------------------------------------------- | -------------------------------------------------- |
| **Stateless agents**           | Fresh context per agent                           | Eliminates context pressure and accumulated errors |
| **Externalized memory**        | All state in artifact files                       | Survives session resets, enables verification      |
| **Single responsibility**      | Each agent does one thing                         | Reduces complexity, enables specialization         |
| **Message passing**            | Agents communicate via artifacts                  | Decouples stages, creates audit trail              |
| **Verification at boundaries** | Every stage validates previous output             | Catches errors before propagation                  |
| **Deterministic backpressure** | Run tests/linters, treat failures as ground truth | Counters cargo-cult priors with objective feedback |
| **Embedded methodology**       | Process IS the prompt                             | Cannot skip what structures the task               |
| **No recall required**         | Task files contain all needed answers             | Reduces reliance on unverified recall              |

---

## SAM Pipeline Stages

```text
STAGE 1: DISCOVERY        → Gather complete information via structured discussion
STAGE 2: PLANNING (RT-ICA) → Verify prerequisites, design solution, BLOCK if missing
STAGE 3: CONTEXT INTEGRATION → Map plan to codebase, resolve conflicts
STAGE 4: TASK DECOMPOSITION → Create atomic tasks with ALL context embedded
STAGE 5: EXECUTION        → Implement single task (FRESH SESSION)
STAGE 6: FORENSIC REVIEW  → Independent verification (COMPLETE or NEEDS_WORK)
STAGE 7: FINAL VERIFICATION → Verify feature achieves original goals
```

---

## Comparison Documents

| Document                                                                     | Compares To            | Focus                                               |
| ---------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------- |
| [vs Task Master](./stateless-agent-methodology-vs-taskmaster.md)             | Task Master (npm tool) | Cognitive framework vs task tooling                 |
| [vs Get Shit Done](./stateless-agent-methodology-vs-get-shit-done.md)        | GSD workflow           | Theory vs practice; shared architecture             |
| [vs Ralph Loop](./stateless-agent-methodology-vs-ralph-loop-orchestrator.md) | Ralph orchestrator     | Phase decomposition vs emergent gates               |
| [vs Gas Town](./stateless-agent-methodology-vs-gastown.md)                   | Gas Town pipeline      | Message passing patterns                            |
| [vs OctoCode](./stateless-agent-methodology-vs-octocode.md)                  | Octocode RDD           | Workflow reliability vs research-driven development |
| [vs V-Model](./stateless-agent-methodology-vs-v-model.md)                    | SDLC V-Model           | Mapping to traditional verification                 |
| [vs SuperClaude](./stateless-agent-methodology-vs-superclaude.md)            | SuperClaude            | Constraint-driven vs capability-driven              |
| [vs cc-sessions](./stateless-agent-methodology-vs-cc-sessions.md)            | cc-sessions framework  | Stateless execution vs session awareness            |

---

## Anti-Patterns to Avoid

| Anti-Pattern              | Why It Fails                      | SAM Approach                  |
| ------------------------- | --------------------------------- | ----------------------------- |
| One agent does everything | Context pressure, no verification | Pipeline with specialists     |
| Trust Claude's memory     | Memory is unreliable              | Externalize to artifact files |
| Behavioral instructions   | Claude rationalizes out           | Structural enforcement        |
| Self-verification only    | Confirmation bias                 | Independent forensic review   |
| Skip prerequisites        | Garbage in, garbage out           | RT-ICA gate blocks            |
| Large context tasks       | Long-context degradation          | Small, focused tasks          |
| Assume training data      | Stale, wrong, hallucinated        | Provide all context in task   |

---

## Integration with Repository

SAM principles are implemented throughout this repository:

- **Root CLAUDE.md** implements verification at boundaries, structured methodology enforcement
- **rt-ica skill** (`.claude/skills/rt-ica/`) provides RT-ICA checkpoint tooling
- **delegate skill** (`.claude/skills/delegate/`) applies stateless agent delegation patterns
- **Workflow diagrams** (`.claude/knowledge/workflow-diagrams/`) visualize SAM-aligned processes

---

## Document Status

| Component              | Maturity |
| ---------------------- | -------- |
| Core Concepts          | Stable   |
| Pipeline Architecture  | Stable   |
| Stage Specifications   | Refined  |
| Formal Mappings        | Stable   |
| Implementation Details | Evolving |
| Comparison Analysis    | Growing  |

---

## Related Resources

- [Research Directory](../research/) - External tools and patterns
- [Workflow Diagrams](../.claude/knowledge/workflow-diagrams/) - Process flow visualizations
- [RT-ICA Skill](../.claude/skills/rt-ica/) - Prerequisite verification implementation
