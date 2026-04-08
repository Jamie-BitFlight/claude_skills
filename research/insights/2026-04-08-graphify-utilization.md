# Utilization Proposals: graphify

**Research entry**: ./research/skill-generation-tools/graphify.md
**Generated**: 2026-04-08
**Integration surfaces found**: 3 (CLI | SDK | MCP server)
**Proposals written**: 2
**Skipped**: 5 — existing tools redundant or incompatible scope

---

## Utilization 1: context-gathering → graphify

**Research entry**: ./research/skill-generation-tools/graphify.md
**Caller**: .claude/agents/context-gathering.md
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Automates multimodal codebase analysis during context manifest creation; replaces manual `Grep` + `Glob` traversal with structured knowledge graph
**Setup cost**: Medium (pip install graphifyy, one-time graph build per repo)
**Integration surface**: `graphify . --no-viz` or `/graphify . --json` (CLI command)

### Why this caller

The context-gathering agent currently traces codebases manually by reading implementation files, call paths, and data access patterns sequentially (per the agent file, lines 26-40). For large codebases, this manual approach is token-expensive and misses cross-domain connections. graphify extracts structural relationships via AST + LLM-assisted semantic analysis in a single run, producing `GRAPH_REPORT.md` (god nodes, surprising connections) and `graph.json` (queryable offline). When context-gathering invokes graphify first, it gains pre-computed codebase topology, allowing it to write substantially richer context manifests with 71.5x fewer tokens (per graphify research, line 18). The agent can then read `GRAPH_REPORT.md` as the narrative foundation, then use `graph.json` queries for specific path traversal if needed.

### Integration sketch

```bash
# Inside context-gathering flow, after reading task file:
graphify . --no-viz --json
# Produces: graphify-out/GRAPH_REPORT.md and graphify-out/graph.json

# Read god nodes and community structure:
cat graphify-out/GRAPH_REPORT.md

# For specific path queries (offline, no LLM cost):
graphify query "what connects component A to component B" --budget 1500

# Write context manifest using structured topology from graph instead of manual traversal
```

---

## Utilization 2: doc-drift-auditor → graphify

**Research entry**: ./research/skill-generation-tools/graphify.md
**Caller**: .claude/agents/doc-drift-auditor.md
**Integration mechanism**: CLI subprocess + graph.json queries
**Replaces or adds**: Enhances documentation audit by adding architectural topology awareness; auditor can identify drift not just in documented-vs-implemented features but also in relationship structures
**Setup cost**: Medium (pip install graphifyy, graph build)
**Integration surface**: `graphify . --no-viz` (CLI) or `graphify query` with `--dfs` flag (offline path query)

### Why this caller

The doc-drift-auditor currently performs git timeline analysis and implementation discovery by parsing source files to extract classes, functions, and CLI arguments (lines 38-45). While this finds feature-level drift (documented feature missing from code), it cannot detect architectural drift — when the relationship structure itself changes without touching individual features. graphify's relationship classification (`EXTRACTED` vs `INFERRED` vs `AMBIGUOUS`) reveals both code dependencies and semantic relationships, tagged with confidence. By building a graph before and after documentation edits, the auditor gains visibility into whether docs describe an old architecture vs the current one. The `graph.json` format is offline-queryable, so the auditor can ask "were these components related in the previous version?" without re-extraction.

### Integration sketch

```bash
# Baseline extraction at start of audit:
graphify . --no-viz
cp -r graphify-out baseline-graph-out/

# After identifying potential drift in Git timeline:
# Query the graph for relationship evidence:
graphify query "what calls DatabaseLayer" --dfs

# Identify surprising connections marked INFERRED + confidence scores:
# These reveal design decisions that may not appear in source code

# Compare GRAPH_REPORT.md across versions to see architecture shifts:
diff baseline-graph-out/GRAPH_REPORT.md graphify-out/GRAPH_REPORT.md
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| .claude/agents/research-context-agent.md | **Incompatible scope** — research-context-agent appends Integration Opportunities sections to research entries; graphify is a target tool, not a framework for discovery. The agent doesn't need to call graphify. |
| .claude/agents/research-utilization-assessor.md | **Functional conflict** — This agent IS the utilization assessor. It should not depend on graphify for its own operation. |
| .claude/agents/research-insight-extractor.md | **No integration surface** — Agent creates backlog items from research findings. No codebase analysis dependency. |
| .claude/skills/knowledge-explorer/SKILL.md | **Scope mismatch** — Manages `research/` KB entries (metadata, versioning, category tracking). Does not analyze target codebases. graphify targets user codebases, not the skills repository itself. |
| .claude/skills/external-pattern-integrator/SKILL.md | **Different workflow stage** — Integrates external patterns into local skills (phase 2-3: enhancement + validation). graphify provides topology discovery (phase 0: orientation), which is upstream but not part of the integrator's responsibility. Could be used by orchestrators invoking the integrator, but not a direct caller. |

---

## Integration Opportunity: Always-On Graph Summary in Claude Code

**Note**: The research entry documents a PreToolUse hook for Claude Code (line 60) that surfaces `GRAPH_REPORT.md` before every Glob/Grep. This is setup by `graphify claude install`, which is **user-initiated**, not an automatic skill enhancement. No skill modification is needed; users run the install command explicitly.

However, if the `/gh` skill or `/knowledge-explorer` skill wanted to auto-run graphify on known repositories as part of their initialization, that would be a valid enhancement point (out of scope for this assessment, deferred to operational setup).

