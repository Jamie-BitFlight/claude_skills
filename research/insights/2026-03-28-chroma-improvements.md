# Improvement Proposals: Chroma

**Research entry**: ./research/data-infrastructure/chroma.md
**Generated**: 2026-03-28
**Patterns assessed**: 8
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 8

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| AI Agent Memory and RAG | Describes using Chroma as a tool (utilization opportunity), not a mechanism to adopt in local skills/workflows. No architectural pattern transferable to skill system. |
| Embedding Function Integration | Describes Chroma's embedding API as a consumption target. No local system gap -- our skills do not perform embedding and adopting this pattern would require replacing, not extending, local architecture. |
| Metadata-Based Filtering for context control | Too abstract to map to a concrete local system gap. Local context management uses file-based rules (CLAUDE.md, .claude/rules/). The research entry does not describe a specific filtering mechanism replicable in our file-based system. |
| Hybrid Search Patterns | Describes Chroma's hybrid search capability. No equivalent problem domain exists in local skills -- agents do not perform vector+metadata search internally. |
| Async Support | Describes Chroma's AsyncClient API. Local agent orchestration already uses Claude Code's built-in async tool dispatch (Agent tool, TeamCreate). No gap identified. |
| Authentication for multi-tenant agents | Describes Chroma's token-based auth feature. Local skills operate in a single-tenant CLI environment. Pattern is incompatible with local architecture. |
| OpenTelemetry observability | Research entry describes this as a feature of Chroma to consume, not a mechanism to replicate in skill/agent infrastructure. Adding OpenTelemetry to Claude Code skills would require infrastructure changes outside scope of skill extension. |
| Deployment Flexibility | Describes Chroma's deployment modes (in-memory, server, K8s, cloud). Not a pattern applicable to Claude Code skill architecture which operates as CLI plugins. |
