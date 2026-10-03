# Improvement Proposals: GitHub Agentic Workflows (gh-aw)

**Research entry**: ./research/developer-tools/gh-aw.md
**Generated**: 2026-10-02
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 2

No proposal reached high confidence, so this file holds no numbered improvements. The entry's
Relevance section records each change as "already covered", "out of scope" or "none", so no
concrete mechanism whose absence can be observed in a local file remains.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| MCP safe-inputs validation, tool mapping, server lifecycle (Relevance > Integration Opportunities; Key Features > MCP Server Integration: "Safe-inputs framework validates tool inputs before agent use") | low | The entry describes safe-inputs in one sentence and does not say what is validated, against what schema, or where the check runs. Its Integration Opportunities item maps to `.mcp.json`, whose "Today" quote is "`mcpServers` configuration with environment variable indirection for API keys", and its Change field says "out of scope" because the entry does not say what safe-inputs validates. `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` covers per-tool auth (`require_scopes`, line 94). FastMCP derives input schemas from type annotations, so a gap can't be stated without the gh-aw safe-inputs specification. To raise confidence, fetch the gh-aw safe-inputs docs and list the checks that FastMCP's annotation-derived schema validation lacks. |
| Safe-outputs: the agent emits structured JSON and a separately permissioned job validates it against declared permissions before writing (Key Features > Security & Sandboxing; Technical Architecture > Safe-Outputs Framework) | low | The Relevance section does not name this pattern. I inferred it from Key Features myself, so it is not grounded in a Relevance passage. The nearest local analog is the dh backlog MCP server (`plugins/development-harness/backlog_core/`), the only path agents use to write to the backlog. I did not examine whether it splits proposal from validated execution. To raise confidence, have the research entry name a concrete local target, and read the backlog write path to check whether a validate-then-execute split is absent. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-engine registry with validation before compile (Relevance > Applications, mapped to `./.claude/skills/README.md`) | Already covered. `scripts/generate_harness_compatibility.py` keeps a `HARNESSES` registry and rejects unknown harness and plugin names with an explicit error (lines 124-131). `plugins/agent-orchestration/README.md` line 14 sets up per-harness notes under `delegate/references/harness-notes/`. The entry's "Change" field now records the same conclusion ("already covered"). |
| Markdown + YAML frontmatter declarative definitions (Relevance > Applications, mapped to `./.claude/agents/backlog-mcp-validator.md`) | The entry's own Change field says "none". The entry's "Today" quote for the mapped file is "The `backlog` server is configured in this agent's `mcpServers` frontmatter." Local agents and skills already use YAML frontmatter, and skilllint validates it on commit. |
