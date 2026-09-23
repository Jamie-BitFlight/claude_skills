---
title: "Improvement Proposals: GLM-5:exacto via OpenRouter"
---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Provider Variance Awareness — monitor inference provider behavior and adapt routing | Not applicable to local architecture. This repo delegates to Claude models via the Agent tool, which routes to Anthropic's API directly. There is no multi-provider layer where provider variance monitoring would apply. The pattern addresses infrastructure concerns (OpenRouter's Exacto routing across hosting providers) that are outside the scope of skill/workflow definitions in this repository. |
| Streaming Reasoning Output — make intermediate agent reasoning visible via `<think>` tags | Already covered by Claude Code's native behavior. Sub-agents stream their output in the terminal during execution. The `<think>` tag is a model-level capability (GLM-5 architecture), not a skill or workflow feature that can be adopted by changing local files. Claude Code does not suppress intermediate reasoning from sub-agents. |
| Sparse Expert Routing — activate only relevant tools/skills per task | Already implemented in `plugins/development-harness/skills/implement-feature/SKILL.md` (task-level `skills` list, line 113). `.claude/rules/local-workflow.md`, originally cited here — whose Phase 2 "Execution Loop" step 3 stated exactly this ("For each ready task: … If the task's `skills` list (from ready JSON) is non-empty, include skill-loading instructions in the delegation prompt") — was deleted 2026-03-29 (commit `18f93b5c6`). The `skills` field in task YAML metadata specifies which skills each task needs; the orchestrator includes skill-loading instructions in the delegation prompt. This is functionally equivalent to MoE sparse activation — only relevant skills are loaded per task. |

---

## Notes

The research entry's "Integration Opportunities" section proposes using GLM-5 as an alternative or fallback model for coding tasks. This concept is already tracked as backlog item **#108 SAM: Multi-Model Strategy** (P2). No new backlog item is warranted.

The remaining integration opportunities (self-hosted enterprise deployment, multi-model evaluation framework) are infrastructure concerns that do not map to any skill, agent, or workflow file in this repository.
