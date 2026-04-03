# DuckDB Query Patterns for Transcript Analysis

SQL patterns for querying Claude Code JSONL transcripts via the MotherDuck MCP server (`execute_query` tool). All queries use DuckDB dialect.

**Storage model:** Session data lives in **JSONL files on disk**. DuckDB here is only the **query engine** (`read_ndjson_auto`, aggregates, etc.). The MCP server uses `:memory:`; SQL must use **absolute** paths to JSONL (see `docs/cross-platform-notes.md` for tilde/`args` pitfalls).

**Path substitution:** Replace `/path/to/*.jsonl` in all queries below with the **absolute** transcript glob path from the Data Location section of the parent skill. Do not rely on `~` inside SQL strings — the MotherDuck server does not expand it.

## Verified Schema Access Patterns (2026-03-29)

The following findings were verified against live session JSONL at `~/.claude/projects/-home-ubuntulinuxqa2-repos-claude-skills/*.jsonl`.

### Two read modes — pick the right one

`read_ndjson_auto()` has two distinct modes:

**Mode A — Auto-parse (default, no `columns` arg)**

DuckDB infers the schema and returns native typed columns. `type`, `timestamp`, `sessionId`, `gitBranch`, `message`, etc. are direct column names accessed with dot notation.

```sql
SELECT type, sessionId, gitBranch
FROM read_ndjson_auto('/path/to/*.jsonl')
LIMIT 5;
```

**Mode B — Raw JSON (`columns={line: 'JSON'}`)**

Every record is a single opaque JSON string in the `line` column. Access requires `json_extract_string(line, '$.field')` for every field.

```sql
SELECT json_extract_string(line, '$.type') AS type
FROM read_ndjson_auto('/path/to/*.jsonl', columns={line: 'JSON'})
LIMIT 5;
```

**CRITICAL**: In testing against this project's session files, Mode B returned **all nulls** for `json_extract_string(line, '$.type')`. Mode A returned correct values. **Always verify with a `SELECT * ... LIMIT 2` before writing extraction queries** — do not assume Mode B works.

### message.usage — struct dot access

`message.usage` is a STRUCT column. Access fields with dot notation, not JSON extraction:

```sql
-- Correct
SELECT
  message.usage.input_tokens,
  message.usage.cache_read_input_tokens,
  message.usage.output_tokens
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'assistant'
  AND message.usage.input_tokens IS NOT NULL;

-- Wrong — returns empty/null
SELECT message->>'$.usage.input_tokens' FROM ...
```

### message.content — JSON column, unnest for tool extraction

`message.content` is a JSON column (array of objects). Extracting individual tool calls requires `unnest(from_json(...))`:

```sql
SELECT
  sessionId,
  json_extract_string(tool_item, '$.name') AS tool_name,
  json_extract_string(tool_item, '$.type') AS item_type
FROM read_ndjson_auto('/path/to/*.jsonl'),
  LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
WHERE type = 'assistant'
  AND json_extract_string(tool_item, '$.type') = 'tool_use'
LIMIT 20;
```

### No `result` type in main session files

The schema document describes a `result` type record as the final session record. This record **does not appear** in `~/.claude/projects/*/` session JSONL for this project. Session-level token totals must be computed by summing `assistant` records:

```sql
SELECT sessionId,
  SUM(message.usage.input_tokens) AS total_input,
  SUM(message.usage.cache_read_input_tokens) AS total_cache_read,
  SUM(message.usage.output_tokens) AS total_output
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'assistant'
  AND message.usage.input_tokens IS NOT NULL
GROUP BY sessionId;
```

### Session labeling — gitBranch + MIN(timestamp)

Sessions do not have explicit condition labels. Correlate sessions to instruction changes via `gitBranch` and the session start timestamp:

```sql
SELECT
  sessionId,
  gitBranch,
  MIN(timestamp) AS session_start,
  COUNT(*) AS record_count
FROM read_ndjson_auto('/path/to/*.jsonl')
GROUP BY sessionId, gitBranch
ORDER BY session_start DESC;
```

Use `git log --format="%H %ai" -- CLAUDE.md` to find the commit timestamp of an instruction change. Sessions with `session_start` before that timestamp are pre-change; sessions after are post-change.

### User corrections — `::VARCHAR LIKE` confirmed working

```sql
SELECT sessionId, timestamp,
  CASE
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user for tool use%' THEN 'tool_denial'
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user%' THEN 'interrupt'
    WHEN message.content::VARCHAR LIKE '%User denied%' THEN 'denied'
  END AS signal_type
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'user'
  AND message.content IS NOT NULL
  AND (
    message.content::VARCHAR LIKE '%Request interrupted by user%'
    OR message.content::VARCHAR LIKE '%User denied%'
  );
```

SOURCE: Verified against live JSONL at `~/.claude/projects/-home-ubuntulinuxqa2-repos-claude-skills/` (2026-03-29).

---

## Arbitrary queries (not limited to this cookbook)

1. Load the field reference: **`kaizen-analysis` MCP** — tool `get_transcript_jsonl_schema`, or **`resources/read`** URI `kaizen://session-log/schema` (same markdown), or **Read** [jsonl-schema.md](./jsonl-schema.md) / [session-log-schema.md](./session-log-schema.md) from the plugin.
2. Compose **any** DuckDB SQL against `read_ndjson_auto('ABSOLUTE/GLOB/*.jsonl')` (Mode A — auto-parse). Use direct column names (`type`, `sessionId`, `timestamp`, `message`, etc.) and dot notation for structs (`message.usage.input_tokens`). For `message.content` array extraction use `LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)`. **Do not use** `columns={line: 'JSON'}` (Mode B) — verified to return all nulls on claude-skills session files (2026-03-29).
3. Run SQL via **`kaizen-duckdb` MCP** `execute_query`.

The sections below are **examples** (tool misuse, frustration, etc.), not an exhaustive list of what you may select or filter.

## Loading JSONL Data

DuckDB reads JSONL natively via `read_ndjson_auto()`. Always use Mode A (auto-parse) — do not pass `columns={line: 'JSON'}`:

```sql
-- Single session
SELECT * FROM read_ndjson_auto('/path/to/session.jsonl');

-- All sessions in a project
SELECT * FROM read_ndjson_auto('/path/to/project/*.jsonl');

-- Schema discovery — run this first before writing extraction queries
SELECT * FROM read_ndjson_auto('/path/to/*.jsonl') LIMIT 2;

-- Direct column access (all these work in Mode A)
SELECT type, sessionId, timestamp, gitBranch
FROM read_ndjson_auto('/path/to/*.jsonl')
LIMIT 5;
```

## Corpus Overview Queries

### Session inventory

```sql
SELECT
  sessionId,
  MIN(timestamp) as first_event,
  MAX(timestamp) as last_event,
  COUNT(*) as record_count
FROM read_ndjson_auto('/path/to/*.jsonl')
GROUP BY sessionId
ORDER BY first_event DESC;
```

### Record type distribution

```sql
SELECT type, COUNT(*) as frequency
FROM read_ndjson_auto('/path/to/*.jsonl')
GROUP BY type
ORDER BY frequency DESC;
```

## Tool Misuse Detection

### Bash commands that should use built-in tools

```sql
WITH bash_calls AS (
  SELECT
    sessionId,
    timestamp as ts,
    json_extract_string(tool_item, '$.input.command') as command,
    json_extract_string(tool_item, '$.input.description') as description
  FROM read_ndjson_auto('/path/to/*.jsonl'),
    LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
  WHERE type = 'assistant'
    AND json_extract_string(tool_item, '$.name') = 'Bash'
    AND json_extract_string(tool_item, '$.type') = 'tool_use'
)
SELECT
  sessionId,
  command,
  CASE
    WHEN regexp_matches(command, '^\s*ls\b') THEN 'should_use_glob'
    WHEN regexp_matches(command, '\bgrep\b') AND NOT regexp_matches(command, '\|.*grep') THEN 'should_use_grep'
    WHEN regexp_matches(command, '\bfind\b\s+\S+\s+-name\b') THEN 'should_use_glob'
    WHEN regexp_matches(command, '\bcat\b\s+\S+\.\w+') THEN 'should_use_read'
    WHEN regexp_matches(command, '\bhead\b\s+-\d+') THEN 'should_use_read'
    WHEN regexp_matches(command, '\btail\b\s+-\d+') THEN 'should_use_read'
    WHEN regexp_matches(command, '\bsed\b') THEN 'should_use_edit'
    WHEN regexp_matches(command, '\bawk\b') THEN 'should_use_edit'
  END as violation_type
FROM bash_calls
WHERE violation_type IS NOT NULL
ORDER BY sessionId, ts;
```

### Tool misuse rate per session

```sql
WITH tool_calls AS (
  SELECT
    sessionId,
    json_extract_string(tool_item, '$.name') as tool_name,
    json_extract_string(tool_item, '$.input.command') as command
  FROM read_ndjson_auto('/path/to/*.jsonl'),
    LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
  WHERE type = 'assistant'
    AND json_extract_string(tool_item, '$.type') = 'tool_use'
)
SELECT
  sessionId,
  COUNT(*) FILTER (WHERE tool_name = 'Bash'
    AND (regexp_matches(command, '^\s*ls\b')
      OR regexp_matches(command, '\bgrep\b')
      OR regexp_matches(command, '\bcat\b\s+\S+\.\w+')
      OR regexp_matches(command, '\bfind\b.*-name')))
    as misuse_count,
  COUNT(*) FILTER (WHERE tool_name = 'Bash') as total_bash,
  COUNT(*) as total_tools,
  ROUND(100.0 * misuse_count / NULLIF(total_bash, 0), 1) as misuse_pct
FROM tool_calls
GROUP BY sessionId
HAVING misuse_count > 0
ORDER BY misuse_count DESC;
```

## Error Pattern Detection

### Tool errors by type

```sql
SELECT
  sessionId,
  CASE
    WHEN message.content::VARCHAR LIKE '%File has not been read yet%' THEN 'edit_before_read'
    WHEN message.content::VARCHAR LIKE '%String to replace not found%' THEN 'stale_edit'
    WHEN message.content::VARCHAR LIKE '%User denied tool use%' THEN 'user_denied'
    WHEN message.content::VARCHAR LIKE '%Exit code%' THEN 'command_failure'
    WHEN message.content::VARCHAR LIKE '%not found%' THEN 'missing_binary'
    WHEN message.content::VARCHAR LIKE '%does not exist%' THEN 'file_not_found'
    ELSE 'other'
  END as error_type,
  COUNT(*) as occurrences
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'user'
  AND json_extract_string(message.content::VARCHAR, '$[0].is_error') = 'true'
GROUP BY sessionId, error_type
ORDER BY occurrences DESC;
```

## User Frustration Detection

### Interrupts and corrections

```sql
SELECT
  sessionId,
  timestamp as ts,
  CASE
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user for tool use%' THEN 'tool_denial'
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user%' THEN 'interrupt'
    WHEN message.content::VARCHAR LIKE '%User denied%' THEN 'denied'
    WHEN message.content::VARCHAR ~ '^(No,|Don''t|Stop |Why did you|Why would)' THEN 'correction'
    WHEN message.content::VARCHAR ~ '(wrong|incorrect|that''s not|you should not)' THEN 'correction'
  END as signal_type
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'user'
  AND toolUseResult IS NULL
  AND (
    message.content::VARCHAR LIKE '%Request interrupted by user%'
    OR message.content::VARCHAR LIKE '%User denied%'
    OR message.content::VARCHAR ~ '^(No,|Don''t|Stop |Why did you|Why would)'
    OR message.content::VARCHAR ~ '(wrong|incorrect|that''s not|you should not)'
  )
ORDER BY sessionId, ts;
```

## Subagent Delegation Analysis

### Agent types used

```sql
SELECT
  json_extract_string(tool_item, '$.input.subagent_type') as agent_type,
  json_extract_string(tool_item, '$.input.description') as task_description,
  json_extract_string(tool_item, '$.input.model') as model,
  COUNT(*) as usage_count
FROM read_ndjson_auto('/path/to/*.jsonl'),
  LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
WHERE type = 'assistant'
  AND json_extract_string(tool_item, '$.name') = 'Task'
  AND json_extract_string(tool_item, '$.type') = 'tool_use'
GROUP BY agent_type, task_description, model
ORDER BY usage_count DESC;
```

## Context Waste Detection

### Orchestrator reads file then delegates task mentioning same file

```sql
WITH ordered_tools AS (
  SELECT
    sessionId,
    timestamp as ts,
    json_extract_string(tool_item, '$.name') as tool_name,
    json_extract_string(tool_item, '$.input.file_path') as read_path,
    json_extract_string(tool_item, '$.input.prompt') as task_prompt,
    ROW_NUMBER() OVER (PARTITION BY sessionId ORDER BY timestamp) as turn_num
  FROM read_ndjson_auto('/path/to/*.jsonl'),
    LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
  WHERE type = 'assistant'
    AND json_extract_string(tool_item, '$.type') = 'tool_use'
    AND json_extract_string(tool_item, '$.name') IN ('Read', 'Task')
)
SELECT
  r.sessionId,
  r.read_path,
  t.task_prompt
FROM ordered_tools r
JOIN ordered_tools t
  ON r.sessionId = t.sessionId
  AND t.tool_name = 'Task'
  AND t.turn_num > r.turn_num
  AND t.turn_num <= r.turn_num + 5
  AND r.tool_name = 'Read'
  AND t.task_prompt LIKE '%' || r.read_path || '%';
```

## Session Timing Analysis

### Turn durations

```sql
SELECT
  sessionId,
  AVG(durationMs) as avg_turn_ms,
  MAX(durationMs) as max_turn_ms,
  COUNT(*) as turn_count
FROM read_ndjson_auto('/path/to/*.jsonl')
WHERE type = 'system'
  AND subtype = 'turn_duration'
GROUP BY sessionId
ORDER BY avg_turn_ms DESC;
```

## Notes

- DuckDB JSONL parsing is schema-flexible — fields not present in a record return NULL
- `columns={line: 'JSON'}` (Mode B) returned all nulls in testing against claude-skills session files — use auto-parse (Mode A) by default, verify with `SELECT * ... LIMIT 2` before writing extraction queries
- `message.usage.*` fields are STRUCT — use dot notation (`message.usage.input_tokens`), not JSON extraction
- `message.content` is a JSON column — use `unnest(from_json(message.content, '["json"]'))` for tool extraction
- No `result` type records in main session JSONL — sum `assistant` records for session token totals
- `LATERAL unnest` with `from_json` unpacks JSON arrays for tool call extraction
- Adjust glob paths to match your project transcript location

SOURCE: DuckDB documentation (duckdb.org/docs), MotherDuck MCP server README (github.com/motherduckdb/mcp-server-motherduck), empirical testing against claude-skills transcripts (2026-02-18). All examples updated to Mode A (auto-parse) after Mode B verified non-functional (2026-03-29).
