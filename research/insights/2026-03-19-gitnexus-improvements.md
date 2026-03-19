# Improvement Proposals: GitNexus

**Research entry**: ./research/mcp-ecosystem/gitnexus.md
**Generated**: 2026-03-19
**Patterns assessed**: 4
**Backlog items created**: 0 (none)
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 4

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| MCP Integration (impact/context/detect_changes tools) | GitNexus provides codebase intelligence via a knowledge graph (tree-sitter AST parsing, LadybugDB graph database, Leiden clustering). The local repo has no equivalent graph infrastructure. The research entry describes using GitNexus as an external MCP server -- this is a utilization opportunity (covered in `2026-03-19-gitnexus-utilization.md`), not a transferable pattern that can extend local skills/agents. Reimplementing the graph pipeline would require replacing, not extending, local systems. |
| Agent Skills (auto-generated community-based skills) | GitNexus auto-generates `.claude/skills/generated/` files from Leiden community detection over a knowledge graph. The local `plugin-creator:skill-creator` creates skills manually from human intent. Adopting auto-generation would require the full GitNexus indexing pipeline (tree-sitter + graph DB + clustering). The pattern is product-specific, not a portable mechanism. |
| Claude Code Hooks (PreToolUse enrichment, PostToolUse auto-reindex) | The local system already uses PostToolUse hooks (`task_status_hook.py` updates LastActivity timestamps on Write/Edit/Bash). PreToolUse hooks for enriching search queries with graph context require an indexed knowledge graph to query -- this is GitNexus's value proposition, not a transferable hook pattern. The hook *mechanism* is already used locally; the hook *content* (graph queries) requires GitNexus infrastructure. |
| Edge Case Prevention (precomputed context for smaller models) | The concept of precomputing structured context at index time to reduce LLM reasoning burden is addressed locally by SAM task file context manifests (populated by `context-gathering` agent) and plan artifacts (architecture spec, feature context). The specific mechanism (knowledge graph clustering + execution flow tracing + process grouping) is GitNexus's product. The local system's approach (human-directed context manifests + agent-gathered file references) serves the same goal through a different architecture that does not benefit from GitNexus's specific technique without adopting the full graph pipeline. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | -- | All patterns were skipped as non-transferable rather than deferred for low confidence |
