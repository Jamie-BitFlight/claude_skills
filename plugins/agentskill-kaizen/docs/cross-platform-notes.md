# Kaizen `kaizen-duckdb` MCP — paths

**Plugin purpose:** analyze Claude Code **session JSONL** for anti-patterns, friction, and improvement ideas (`transcript-analysis` and related skills). DuckDB here is **only** the SQL engine behind the **`kaizen-duckdb` MCP** so agents can query JSONL with `read_ndjson_auto` — not a database you administer separately.

**This page:** path gotchas for that MCP (absolute paths, no shell expansion). Nothing else.

The `kaizen-duckdb` server (see `plugins/agentskill-kaizen/.mcp.json`) runs **`mcp-server-motherduck`** with **`--db-path :memory:`**. Session data stays in JSONL on disk; see `skills/transcript-analysis/references/duckdb-queries.md` for SQL patterns.

---

## Why paths break

MCP hosts pass `args` to the subprocess **without a shell**. Tilde and env vars in `args` are **not** expanded (`~`, `$HOME`, `%USERPROFILE%`, etc.).

The same applies to **path strings inside SQL** passed to `execute_query`: the server does not expand `~` there either. Use **absolute** paths to your `~/.claude/projects/.../*.jsonl` files.

---

## Reference config

`plugins/agentskill-kaizen/.mcp.json`:

```json
"kaizen-duckdb": {
  "command": "uvx",
  "args": ["mcp-server-motherduck", "--db-path", ":memory:", "--read-write"]
}
```

`--read-write` is required with `:memory:` (MotherDuck CLI).

---

## Do not rely on

| Approach | Why it fails |
|---|---|
| `~` or `$HOME` in MCP `args` | No shell expansion |
| `~` inside SQL path strings | Server does not expand tilde |
| `%USERPROFILE%` in JSON `args` | Not interpolated |
