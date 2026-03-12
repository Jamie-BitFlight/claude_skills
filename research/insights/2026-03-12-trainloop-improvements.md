# Improvement Proposals: TrainLoop

**Research entry**: ./research/ml-infrastructure/trainloop.md
**Generated**: 2026-03-12
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 6

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Lightweight integration ("3-line SDK" principle) | Incompatible architecture. TrainLoop's SDK is embedded in third-party applications for data collection. The local system is a plugin marketplace and skill orchestration framework for Claude Code -- not an SDK consumed by external apps. The "minimal friction" principle is already applied locally through scaffolding scripts (`create_plugin.py`) and the `/skill-creator` workflow. |
| Production signal collection | Already tracked in backlog as #109 (SAM: Audit Trail / Observability) and #317 (Structured session work logs with pre-compact and session-start hooks). Both address the gap of collecting agent execution signals for quality improvement. |
| Separated concerns (data collection, training, inference) | Already covered. The local SAM workflow implements clear three-phase separation: planning (`/add-new-feature`), execution (`/implement-feature`), and quality gates (`/complete-implementation`). The architecture in `.claude/rules/local-workflow.md` documents this separation explicitly. |
| Agent feedback loops (reward models for fine-tuning) | Incompatible architecture. TrainLoop fine-tunes the underlying LLM using reinforcement learning reward models. This repository orchestrates Claude Code agents but does not train or fine-tune the models themselves. Model training is outside the repo's scope -- the repo consumes model capabilities via the Claude API. |
| Skill performance optimization (RL techniques for skill selection) | Incompatible architecture. Applying RL to skill selection requires model-level fine-tuning infrastructure. The local system selects skills via frontmatter `description` fields, explicit routing in SKILL.md flowcharts, and user invocation -- deterministic mechanisms, not learned preferences. Introducing RL-based selection would require replacing the local system rather than extending it. |
| Code generation reliability (preference-based fine-tuning) | Incompatible architecture. Preference-based fine-tuning operates at the model training layer. The local system improves code generation reliability through quality gates (code-reviewer, feature-verifier, integration-checker agents in `/complete-implementation`) and structured task decomposition -- orchestration-layer patterns, not model-training patterns. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | -- | All patterns were either incompatible with local architecture or already tracked |
