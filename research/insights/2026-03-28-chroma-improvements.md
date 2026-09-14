---
title: "Improvement Proposals: Chroma"
---

<!-- removed-call-citations -->
> **Removed-call citation:** the `TeamCreate` call cited below no longer exists in Claude Code. Since v2.1.178, naming a teammate on an `Agent` call under `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` spawns it directly, with no separate setup step (`plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md` § "Agent teams"). This file stands as the dated record of what was analysed and is not rewritten; re-verify any conclusion below that rests on `TeamCreate` — "already covered", "already implemented", or a proposed dispatch — against the current tree before acting on it.

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| AI Agent Memory and RAG | Describes using Chroma as a tool (utilization opportunity), not a mechanism to adopt in local skills/workflows. No architectural pattern transferable to skill system. |
| Embedding Function Integration | Describes Chroma's embedding API as a consumption target. No local system gap -- our skills do not perform embedding and adopting this pattern would require replacing, not extending, local architecture. |
| Metadata-Based Filtering for context control | Too abstract to map to a concrete local system gap. Local context management uses file-based rules (CLAUDE.md, rules/). The research entry does not describe a specific filtering mechanism replicable in our file-based system. |
| Hybrid Search Patterns | Describes Chroma's hybrid search capability. No equivalent problem domain exists in local skills -- agents do not perform vector+metadata search internally. |
| Async Support | Describes Chroma's AsyncClient API. Local agent orchestration already uses Claude Code's built-in async tool dispatch (Agent tool, TeamCreate). No gap identified. |
| Authentication for multi-tenant agents | Describes Chroma's token-based auth feature. Local skills operate in a single-tenant CLI environment. Pattern is incompatible with local architecture. |
| OpenTelemetry observability | Research entry describes this as a feature of Chroma to consume, not a mechanism to replicate in skill/agent infrastructure. Adding OpenTelemetry to Claude Code skills would require infrastructure changes outside scope of skill extension. |
| Deployment Flexibility | Describes Chroma's deployment modes (in-memory, server, K8s, cloud). Not a pattern applicable to Claude Code skill architecture which operates as CLI plugins. |
