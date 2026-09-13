# ARL Meta-Layer: Observation Layer (Improvement Meta-Process)

**HOOTL** (Human Out Of The Loop) = human not a synchronous blocking gate during *execution*. That is the desired outcome of ARL research.

**ARL's Observation Layer** is the meta-process that sits above the three SDLC layers. Implemented by agentskill-kaizen (post-hoc) and session-historian (transcript data).

---

## Phase Mapping

| Phase | Skills/Agents |
|-------|---------------|
| **Observe** | agentskill-kaizen, session-historian, logging |
| **Identify** | hallucination-detector, fact-check, doc-drift-auditor, code-review |
| **Accumulate** | knowledge-explorer, refresh-research, research-curator, context-refinement |
| **Improve** | kaizen-improvement, optimize-claude-md, work-backlog-item close, topic-specialist |

---

## ARL Flow

1. **Observe** — session-historian indexes transcripts; agentskill-kaizen analyzes for patterns
2. **Identify** — hallucination-detector (Stop hook), fact-check (VERIFIED/REFUTED), doc-drift-auditor, agentskill-kaizen maps to R1-R10
3. **Probe** — (To be designed.) Triggers: transcript-analysis Dimension 3 (User Frustration), Dimension 9 (Missing Hooks)
4. **Accumulate** — research/ KB, context manifest, Integration Opportunities. Staleness tracking required.
5. **Improve** — Update SAM process, layer docs, skill instructions

---

## The Knowledge Gap

- **Human**: Expectations, known issues, assumptions often unarticulated
- **AI**: Massive domain knowledge, holes in specificity/reliability
- **Goal**: Build knowledge of invisible practices; probe human for specifics

---

## Human-Probing Flow

Design: [arl-human-probing-design.md](./arl-human-probing-design.md) — triggers, probe questions, project-local domain knowledge format, integration with groom-backlog-item and work-backlog-item.

---

## Experiments & Learnings

Flow experiments run in [sam-flow-experiments](https://github.com/Jamie-BitFlight/sam-flow-experiments). Learnings from experiments feed back into ARL improvements, skill instructions, and layer docs.

---

## Canonical Provenance

[PROVENANCE.md](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/research/arl/PROVENANCE.md) — HOOTL, ARL, agentskill-kaizen; relationship triangle; author design intent.
