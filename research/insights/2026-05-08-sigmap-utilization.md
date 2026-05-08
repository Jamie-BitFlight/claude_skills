# Utilization Proposals: SigMap

**Research entry**: ./research/developer-tools/sigmap.md
**Generated**: 2026-05-08
**Integration surfaces found**: 3 (CLI | MCP | Adapters)
**Proposals written**: 2
**Skipped**: 3 — existing context retrieval patterns sufficient, hook complexity not justified

---

## Utilization 1: context-gathering agent → SigMap MCP server

**Research entry**: ./research/developer-tools/sigmap.md
**Caller**: .claude/agents/context-gathering.md
**Integration mechanism**: MCP tools (on-demand retrieval)
**Replaces or adds**: Replaces manual file discovery with deterministic TF-IDF ranking for faster, more accurate context manifest generation
**Setup cost**: Medium (MCP server startup, environment setup, cache initialization)
**Integration surface**: `sigmap --mcp` exposes 9 on-demand tools: ask, validate, judge, plan, weights, health, map, impact, dependencies

### Why this caller

The context-gathering agent currently reads files manually and traces dependencies to build a comprehensive context manifest for task execution (per .claude/agents/context-gathering.md). Its "Step 2: Research Everything" phase involves hunting down features, services, components, and error handling patterns — a process that relies on file discovery and pattern matching rather than semantic ranking.

SigMap's TF-IDF ranking and 2-hop dependency graph traversal directly address this discovery burden. Rather than manually tracing call paths and dependencies, the agent could:

1. Use `sigmap ask "<task description>"` to get ranked files relevant to the task
2. Use `sigmap plan "<goal>"` to identify change impact and affected files before reading
3. Use `sigmap dependencies <file>` to understand file relationships for the context manifest's "What Needs to Connect" section
4. Use `sigmap judge --response <manifest> --context <files>` to validate the manifest is grounded in actual codebase structure

This collapses the manual dependency-tracing phase into deterministic, ranked retrieval — improving both speed and accuracy of the manifest.

### Integration sketch

The agent loads the SigMap MCP server in its `mcpServers` frontmatter:

```yaml
mcpServers:
  sigmap:
    command: npx
    args: ["sigmap", "--mcp"]
```

In Step 2 (Research Everything), instead of:

```text
Hunt down:
- Every feature/service/module that will be touched
- Every component that communicates with those components
- [manual tracing]
```

The agent calls SigMap tools:

```python
# Use sigmap ask to get ranked files for the task goal
ranked_files = call_mcp_tool("sigmap_ask", query=task.description)

# For impact analysis, use sigmap plan
impact = call_mcp_tool("sigmap_plan", goal=task.goal)

# Get dependency relationships
for file in important_files:
    deps = call_mcp_tool("sigmap_dependencies", file=file)
    # Include in context manifest under "Component Relationships"
```

The resulting manifest includes a "Ranked File List" section derived from `sigmap ask` with confidence scores, plus dependency graph visualization from `sigmap map`.

---

## Utilization 2: SAM task plan generation → SigMap impact analysis

**Research entry**: ./research/developer-tools/sigmap.md
**Caller**: SAM (Structured Agent-Managed) task planning system via @dh:implementation-manager or /dh:implement-feature
**Integration mechanism**: CLI subprocess (`npx sigmap plan`)
**Replaces or adds**: Adds capability to predict file change impact before task decomposition, improving task prioritization and dependency ordering
**Setup cost**: Low (CLI invocation only, no MCP server setup required)
**Integration surface**: `sigmap plan "<goal>"` — analyzes change impact, ranks files by confidence level, identifies affected tests

### Why this caller

The SAM feature implementation workflow decomposes tasks based on explicit dependencies and impact estimates (per .claude/rules/local-workflow.md and /dh:implement-feature skill). Currently, impact analysis relies on agent reasoning about dependencies and file relationships — a process that is:

1. Non-deterministic (different agents may estimate different impact radii)
2. Manual (requires reading dependency graphs and inferring change cascades)
3. Subjective (agents may miss transitive dependencies or underestimate breadth)

SigMap's `plan` command provides deterministic, reproducible impact analysis that the orchestrator can invoke before spawning task agents. For a goal like "Add rate limiting to auth flow", `sigmap plan` outputs:

1. Files affected (ranked by confidence: direct changes, indirect dependencies, tests)
2. Impact radius (dependency graph showing 1-hop and 2-hop relationships)
3. Test files to run (affected test suites)

This information flows into task decomposition: agents can be informed upfront which files they'll likely touch, reducing re-planning mid-task.

### Integration sketch

When `/dh:implement-feature` is invoked with a feature goal, before delegating to task agents:

```bash
# Run SigMap to predict impact
npx sigmap plan "Add rate limiting to auth flow"

# Output example:
# Files with direct changes (confidence: high):
# - src/middleware/auth.ts (confidence: 0.95)
# - src/config/rate-limit.ts (confidence: 0.92)
#
# Files with indirect impact (1-hop):
# - src/services/auth-service.ts (confidence: 0.87)
# - src/routes/auth-routes.ts (confidence: 0.84)
#
# Affected tests:
# - tests/middleware/auth.test.ts
# - tests/integration/rate-limit.test.ts
```

The impact output is parsed and passed to task creation logic, which orders tasks by dependency (direct changes → indirect impacts) and includes file predictions in task acceptance criteria.

Task agents receive this upfront: "You will touch auth.ts (high confidence) and auth-service.ts (indirect dependency). Tests in rate-limit.test.ts will validate your work."

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| knowledge-explorer skill | Manages research KB entries, not live codebase. SigMap targets active source code; different scope. Would require KB indexing separate from SigMap's codebase-focused ranking. |
| Hooks (file-watch patterns) | `sigmap --watch` could trigger on file changes to regenerate `.context/` files. However, context generation is already deferred to agent execution time. Auto-watch adds I/O overhead without clear value for on-demand retrieval pattern (agents call sigmap when needed, not always-on). Skip for now; revisit if context staleness becomes a problem. |
| contextual-ai-documentation-optimizer agent | Optimizes documentation and prompts, not codebase retrieval. SigMap's signature extraction and ranking are not applicable to documentation quality. Skip scope overlap check. |

---

## Summary

SigMap provides two concrete utilization opportunities for this codebase:

1. **context-gathering agent** — Replace manual file discovery with deterministic ranked retrieval via MCP tools
2. **SAM task planning** — Add impact analysis upfront to improve task decomposition and dependency ordering

Both integrate at natural attachment points (agent MCP server startup, CLI invocation before task spawning) and solve existing pain points (manual discovery, subjective impact estimation).

The remaining systems were evaluated and either lack scope overlap (knowledge-explorer on KB vs. SigMap on code) or introduce overhead without clear benefit (watch hooks for always-on regeneration).
