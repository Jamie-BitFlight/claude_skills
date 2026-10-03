# Improvement Proposals: GitHub Agentic Workflows (gh-aw)

**Research entry**: ./research/developer-tools/gh-aw.md
**Generated**: 2026-10-02
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered, out of scope or tracked)**: 3

No proposal reached high confidence, so this file holds no numbered improvements. The entry's
Relevance section records each change as "out of scope" or "none", so no concrete mechanism
whose absence can be observed in a local file remains. Revised 2026-10-03 against gh-aw v0.89.21:
the `safe-inputs` row is retired (upstream renamed it to `mcp-scripts`) and the multi-engine row
is reclassified from "already covered" to "out of scope".

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Safe-outputs: the agent emits structured JSON and a separately permissioned job validates it against declared permissions before writing (Key Features > Security & Sandboxing; Technical Architecture > Safe-Outputs Framework) | low | The Relevance section does not name this pattern. I inferred it from Key Features myself, so it is not grounded in a Relevance passage. The nearest local analog is the dh backlog MCP server (`plugins/development-harness/backlog_core/`), the only path agents use to write to the backlog. I did not examine whether it splits proposal from validated execution. To raise confidence, have the research entry name a concrete local target, and read the backlog write path to check whether a validate-then-execute split is absent. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Per-workflow AI-engine selection (Relevance > Applications, mapped to `./plugins/agent-orchestration/README.md`) | Out of scope. gh-aw's `engine:` frontmatter field selects Copilot, Claude, Codex, Gemini or Pi per workflow run (AI Engines reference, v0.89.21). `scripts/generate_harness_compatibility.py` line 36 `HARNESSES` lists this repository's four plugin host compatibility targets, and `load_verification_source()` (lines 111-133) only rejects verification evidence that names an unknown plugin or harness; it does not choose an engine for any run. `plugins/agent-orchestration/README.md` line 14 lists only `harness-notes/claude-code.md` ("Add siblings per harness"), and a case-insensitive search for `engine` over the script and the plugin directory finds no matching file. An earlier revision called this "already covered"; that was not supported by the cited code. |
| gh-aw `mcp-scripts` inline typed tools (Relevance > Integration Opportunities, mapped to `.mcp.json`; replaces the retired `safe-inputs` deferred row) | Out of scope. The earlier deferred row was stale: upstream renamed `safe-inputs` to `mcp-scripts`, and the v0.89.21 reference documents typed inputs (`type`, `required`, `default`, `enum`), per-tool `env:` and `timeout:`, execution on the Actions runner outside the agent container, large-output handling and a read-only warning. FastMCP already provides typed-input tools in this repository's ecosystem (`plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` line 114 `@mcp.tool` on a typed function; `references/server-core.md` line 114 "Generates an input schema from type annotations"), while `.mcp.json` only registers external servers. This repository has no gh-aw workflow that would host inline tools, so no gap can be stated. |
| Markdown + YAML frontmatter declarative definitions (Relevance > Applications, mapped to `./.claude/agents/backlog-mcp-validator.md`) | The entry's own Change field says "none". The entry's "Today" quote for the mapped file is "The `backlog` server is configured in this agent's `mcpServers` frontmatter." Local agents and skills already use YAML frontmatter, and skilllint validates it on commit. |
