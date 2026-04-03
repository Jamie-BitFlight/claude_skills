# JSONL Schema — Kaizen

**Canonical reference:** [session-log-schema.md](./session-log-schema.md) (Claude Code session log schema, LM Assist–verified field paths, directory layout, record types).

**MCP exposure:** same markdown is returned by **`kaizen-analysis`** tool `get_transcript_jsonl_schema` and resource **`kaizen://session-log/schema`**.

Use that document to build **any** DuckDB `json_extract` path or filter on `type` / nested fields. The file below is retained only as a short orientation; do not duplicate long schema blocks here.

## Record types (summary)

| `type` | Role |
|--------|------|
| `assistant` | Model turns; `message.content[]` holds `text`, `tool_use`, `thinking` |
| `user` | User text and `tool_result` blocks |
| `system` | `subtype`: `init`, `turn_duration`, `stop_hook_summary`, `compact_boundary`, … |
| `result` | Session outcome (last line in completed sessions) |
| `progress` | Hooks / subagent streaming |
| `summary` | Compaction summaries |
| `file-history-snapshot` | Tracked file backups |

For full JSON shapes, tool pairing, subagent paths, and token accounting, read [session-log-schema.md](./session-log-schema.md).
