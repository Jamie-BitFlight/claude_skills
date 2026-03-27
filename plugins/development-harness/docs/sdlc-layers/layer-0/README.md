# Layer 0: SDLC-Agnostic (Framework/Process)

**Scope**: Applies to all software development regardless of language, framework, or product goal.

---

## What Belongs Here

- SAM 7-stage pipeline definition and artifact flow
- Human touchpoint model (escalation triggers, constraint analysis)
- Artifact conventions (token pattern, naming, storage)
- RT-ICA prerequisite gate
- Verification protocol (producer vs evaluator, verdicts)
- Task file format
- Subagent contract, delegation patterns
- Evidence discipline (fact-check, find-cause, scientific-thinking)
- Orchestrator discipline (anti-patterns)
- Context-fit complexity model (decomposition, constraint economics, progressive disclosure)

---

## What Does NOT Belong Here

- Language-specific quality gate commands (→ Layer 1)
- Stack-specific architecture patterns (→ Layer 2)
- ARL Observation Layer flow (→ arl-meta-layer.md)

---

## Documents in This Directory

| Document | Purpose |
|----------|---------|
| [sam-pipeline.md](./sam-pipeline.md) | Canonical 7-stage flow |
| [arl-touchpoints.md](./arl-touchpoints.md) | Human touchpoint model summary |
| [artifact-conventions.md](./artifact-conventions.md) | Token pattern, naming, storage |
| [rt-ica-gate.md](./rt-ica-gate.md) | Prerequisite assessment, BLOCK conditions |
| [verification-protocol.md](./verification-protocol.md) | Producer/evaluator separation, verdicts |
| [task-file-format.md](./task-file-format.md) | Link to TASK_FILE_FORMAT |
| [evidence-discipline.md](./evidence-discipline.md) | fact-check, find-cause, scientific-thinking triggers |
| [orchestrator-discipline.md](./orchestrator-discipline.md) | Delegation anti-patterns, read constraints |
| [context-fit-complexity.md](./context-fit-complexity.md) | Task complexity as context sufficiency, decomposition principles |
