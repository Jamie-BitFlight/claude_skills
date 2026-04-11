# Improvement Proposals: Tabularis

**Research entry**: ./research/developer-tools/tabularis.md
**Generated**: 2026-04-11
**Patterns assessed**: 3
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Database MCP server real-world pattern for fastmcp-creator

**Source pattern**: "The MCP server enables agents to: Query schema dynamically from live databases, Execute exploratory queries to understand relationships, Generate and test SQL without manual round-trips, Validate database changes during development" (Section: Relevance to Claude Code Development > 1. Database Integration for Agents)
**Local system**: plugins/fastmcp-creator/skills/fastmcp-creator/references/real-world-patterns.md
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: the fastmcp-creator is intentionally generic; adding domain-specific templates may not align with the skill's scope, and the local system might rely on users composing their own domain servers from the generic patterns provided

### Current state

`references/real-world-patterns.md` contains a trivial `DatabaseServer` stub example (line 23-34) that mounts a `query_users` tool returning an empty list `[]`. No real-world database MCP server pattern demonstrates schema introspection tools (`list_tables`, `describe_table`, `run_query`) or connection management. An agent building a database MCP server from the current examples would need to invent the tool structure from scratch.

### Target state

`references/real-world-patterns.md` includes a "Database Schema Introspection Server" section with a pattern showing: (1) a `list_tables` tool that returns table names from a connection, (2) a `describe_table` tool returning columns/indexes/foreign keys, (3) a `run_query` tool executing parameterized SQL and returning results, and (4) connection management via FastMCP's lifespan/context pattern. The pattern uses SQLite as the example backend for zero-setup reproducibility.

### Measurable signal

`references/real-world-patterns.md` contains a section titled "Database Schema Introspection Server" with at least 3 tool definitions (`list_tables`, `describe_table`, `run_query`) and a lifespan function managing the database connection. Searchable via: `grep -c "describe_table" references/real-world-patterns.md` returns >= 1.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Database MCP server real-world pattern | Medium | The fastmcp-creator skill is intentionally generic. Would need to verify with skill maintainer whether domain-specific templates are in scope. The local system already provides all building blocks (tools, lifespan, composition) -- the gap is a composed example, not a missing capability. To raise confidence: check if other real-world patterns in the file are domain-specific templates or only FastMCP feature demonstrations. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Extensibility via Plugins (JSON-RPC 2.0 over stdio, no restart, capability declaration) | Already covered -- MCP IS JSON-RPC 2.0 over stdio. The `plugin-creator/skills/mcp-integration/SKILL.md` covers stdio transport configuration, dynamic tool discovery, and capability exposure. The `plugin-creator/skills/skill-creator/SKILL.md` covers auto-discovery of skills without restart. Tabularis's plugin pattern is architecturally equivalent to what MCP already provides in the local system. |
| AI-Assisted Development Model (user-facing AI features alongside agent integration) | Too abstract -- the research entry describes a development methodology ("exploring how far intelligent agents could accelerate building a fully functional tool from scratch") without naming a concrete mechanism. No observable before/after state can be defined. This is a philosophy, not a pattern. |
