# Utilization Proposals: SoulForge

**Research entry**: ./research/coding-agents/soulforge.md
**Generated**: 2026-04-05
**Integration surfaces found**: 2 (CLI | SDK)
**Proposals written**: 2
**Skipped**: 3 — typescript-pro (SoulForge is competitor agent, not library), orchestrating-swarms (skill documentation, not callable system), javascript-pro (code implementation agent, no context synthesis need)

---

## Utilization 1: context-gathering → SoulForge repo map

**Research entry**: ./research/coding-agents/soulforge.md
**Caller**: .claude/agents/context-gathering.md
**Integration mechanism**: CLI subprocess (headless mode)
**Replaces or adds**: Replaces manual, file-by-file context collection with intelligent, graph-backed codebase analysis. Adds PageRank-based importance ranking, git co-change coupling detection, and semantic symbol summaries.
**Setup cost**: Medium (install Bun, install SoulForge, configure API key for model provider)
**Integration surface**: `soulforge --headless "analyze repo structure for: {task description}" --json --mode architect`

### Why this caller

The `context-gathering` agent builds comprehensive context manifests for new tasks by reading files, understanding architecture, and tracing code paths. Currently this is a manual process requiring exhaustive file reads and pattern discovery. SoulForge's Live Soul Map (documented in soulforge.md lines 44-51) addresses this exactly: "SQLite-backed index of every file, symbol, import, and export. PageRank ranking blends structural importance with conversational relevance." The agent's current approach reads files sequentially; SoulForge's approach builds a persistent codebase graph on startup with real-time updates, blast radius scoring, clone detection, and semantic summaries (lines 49-50). This directly replaces the weaker, generic context collection approach with intelligent codebase awareness that understands which files matter most for the task.

### Integration sketch

```bash
# In context-gathering agent workflow:
# 1. Receive task file path
# 2. Extract task description and key terms
# 3. Invoke SoulForge in architect (read-only) mode for analysis

soulforge --headless \
  "Build context manifest for task: ${TASK_DESCRIPTION}\n\
   Focus areas: ${FOCUS_KEYWORDS}" \
  --json \
  --mode architect \
  --model ${PREFERRED_MODEL} | jq '.context' > /tmp/soul_context.json

# 4. Parse SoulForge's JSON output
# 5. Augment context-gathering's manifest with:
#    - SoulForge's identified key files (PageRank > threshold)
#    - Blast radius annotations ([R:N] tags from soulforge.md line 49)
#    - Co-change partners (implicit coupling, from soulforge.md line 165)
#    - Semantic summaries of top symbols (soulforge.md line 167)

# 6. Write enriched manifest to task file
```

---

## Utilization 2: code-review → SoulForge headless analysis

**Research entry**: ./research/coding-agents/soulforge.md
**Caller**: .claude/agents/code-review.md
**Integration mechanism**: CLI subprocess (headless mode with JSON output)
**Replaces or adds**: Adds capability to perform whole-codebase impact analysis during code review. Enhances local review with SoulForge's blast radius scoring and clone detection.
**Setup cost**: Medium (install Bun, install SoulForge, configure API key)
**Integration surface**: `soulforge --headless "review changes in: {file list}" --json --mode architect`

### Why this caller

The `code-review` agent (soulforge.md research entry shows agents that do code review) identifies bugs, security issues, and pattern violations in recent code changes. Its current scope is isolated to modified files and local patterns. SoulForge's Intelligence Router (lines 59-65, documented in soulforge.md) provides cross-file impact analysis: "Blast radius scoring: [R:N] tags on each file show how many files import it, revealing impact of edits before they're made" (line 49). Additionally, SoulForge's clone detection (line 50: "AST shape hash + MinHash to identify duplicated code patterns") catches duplicate patterns that static review might miss. Integrating SoulForge's headless mode would let code-review automatically detect which files are affected by a change and whether the change duplicates patterns elsewhere in the codebase — capabilities the agent currently lacks.

### Integration sketch

```bash
# In code-review agent workflow after receiving modified files:
# 1. Collect list of modified file paths from git diff

MODIFIED_FILES=$(git diff --name-only HEAD~1)

# 2. Invoke SoulForge in read-only (architect) mode
# Documented in soulforge.md lines 93-98 (Operational Modes)
# and lines 235-243 (Headless Usage Examples)

soulforge --headless \
  "Analyze impact of changes to these files: ${MODIFIED_FILES}\n\
   Identify: blast radius, duplicate patterns, affected importers" \
  --json \
  --mode architect | jq '.blastRadius, .clones, .importers' > /tmp/impact.json

# 3. Parse JSON output:
# - blastRadius: list of files importing modified files
# - clones: duplicate patterns detected (AST shape matches)
# - importers: count [R:N] for each modified file

# 4. Augment code review findings:
#    - Flag if change impacts more files than developer realizes
#    - Flag if pattern duplicates elsewhere (suggests refactoring)
#    - Document full dependency graph affected by change

# 5. Return enhanced review including blast radius warnings
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| .claude/agents/typescript-pro.md | SoulForge is a complete AI agent for coding, not a library or tool that a specialist agent would call. Using SoulForge would replace typescript-pro's work entirely, not augment it. No integration surface as caller. |
| .claude/skills/orchestrating-swarms/SKILL.md | Skill documentation about swarm patterns in Claude Code. SoulForge's AgentBus architecture (line 56) is relevant as a pattern study reference, but the skill is not a callable system — it teaches patterns to humans/agents. No integration mechanism. |
| .claude/agents/javascript-pro.md | Like typescript-pro, this is a specialist code implementation agent. SoulForge is a competitor agent, not a library or tool. No integration as a caller; SoulForge would replace, not augment. |

---

## Notes

**MCP Server Integration (Future)**

SoulForge's roadmap (line 294) includes `@soulforge/mcp` as MCP servers for Claude Code. Once available, this would create a third integration mechanism (MCP tool definition) on top of the current CLI and SDK approaches. Recommend revisiting this utilization assessment once the MCP server is released.

**Model Routing Relevance**

SoulForge's task router (lines 57, 259-264) with per-model assignment (Opus for planning, Sonnet for coding, Haiku for cleanup) is architecturally relevant to Claude Code's model selection rules documented in `.claude/rules/model-selection.md`. This is a pattern adoption opportunity (not utilization), recommended for research-insight-extractor to surface separately.

---
