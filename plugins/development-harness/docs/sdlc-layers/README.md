# SDLC Layer Separation Architecture

Three-layer architecture separating SDLC-agnostic framework/process from language-specific steps and stack/goal-specific implementations. Each layer builds on the previous layer's best practices, reference documentation, and examples.

---

## Layer Model

| Layer | Scope | Contents |
|-------|-------|----------|
| **Layer 0** | SDLC-Agnostic | SAM pipeline, human touchpoints, artifact conventions, RT-ICA, verification protocol, task format, subagent contract, evidence discipline |
| **Layer 1** | Language-Specific | Language manifest, abstract roles, quality gates, project detection, language standards |
| **Layer 2** | Stack/Goal-Specific | Architecture patterns, toolchain config, reference examples, stack research |
| **ARL Meta-Layer** | Observation (Improvement) | Observe → Identify → Probe → Accumulate → Improve |

---

## Directory Structure

```text
.claude/docs/sdlc-layers/
├── README.md           # This file — overview
├── layer-0/            # SDLC-agnostic reference docs
│   ├── README.md
│   ├── sam-pipeline.md
│   ├── arl-touchpoints.md
│   ├── artifact-conventions.md
│   ├── rt-ica-gate.md
│   ├── verification-protocol.md
│   ├── evidence-discipline.md
│   └── orchestrator-discipline.md
├── layer-1/            # Language-specific overview
│   ├── README.md
│   ├── layer-1-overview.md
│   ├── language-manifest-template.md
│   ├── linting-discovery-protocol.md
│   ├── workflow-pattern-taxonomy.md
│   └── harness-role-mapping.md
├── layer-2/            # Stack profiles (see plugins/development-harness/docs/layer-2/)
├── arl-meta-layer.md   # ARL Observation Layer flow
└── arl-human-probing-design.md  # Human-probing flow design (to be implemented)
```

---

## Principles

1. **Layer 0 is the single source of truth** for process, gates, and conventions. Layer 1 and 2 docs reference it; they do not duplicate.
2. **Harness owns process**; language plugins own specialists. The development-harness is the canonical Layer 0 implementation.
3. **Stack profiles are optional**. A project can use Layer 0 + Layer 1 only.

---

## Evaluation

Use the `evaluate-sdlc-layers` skill to validate and iterate on this implementation: `/evaluate-sdlc-layers [--dry-run | --fix]`

---

## Experiments & Learnings

Flow experiments run in [sam-flow-experiments](https://github.com/Jamie-BitFlight/sam-flow-experiments). Clone via SSH: `git clone git@github.com:Jamie-BitFlight/sam-flow-experiments.git`. Each experiment tests orchestrations, prompts, and task handoffs against concept fixtures from stateless-agent-methodology. Findings feed back into layer docs, skills, and the ARL Observation Layer.

---

## References

- [SAM definition](../../skills/work-backlog-item/references/sam-definition.md)
- [Development harness](../../../plugins/development-harness/CLAUDE.md)
- [ARL PROVENANCE](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/PROVENANCE.md) (external repo)
