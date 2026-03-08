# Research Findings: agentskill-kaizen Plugin Patterns

Research conducted 2026-03-08 to inform the design of the `frustration-analyzer` plugin.

SOURCE: All findings from direct reading of `/home/user/claude_skills/plugins/agentskill-kaizen/` source files.

---

## 1. DuckDB Usage Pattern

### How DuckDB Is Used

Kaizen uses DuckDB in **two distinct modes**:

1. **Direct SQL on JSONL files (no database required)** — via the MotherDuck MCP server's `execute_query` tool. DuckDB reads JSONL natively through `read_ndjson_auto()`. No ETL step, no schema definition, no persistent storage needed for querying. The agent writes SQL that reads raw JSONL files directly from disk.

2. **Persistent DuckDB file for scored data** — the `sentiment-score.py` CLI script writes VADER sentiment scores into a persistent DuckDB file at `~/.claude/kaizen/kaizen.duckdb`. This uses the Python `duckdb` library directly (not MCP), with `CREATE TABLE IF NOT EXISTS` and upsert (`INSERT ... ON CONFLICT DO UPDATE`) semantics.

### MCP Server Configuration (MotherDuck)

The plugin registers a MotherDuck MCP server in two places with different configurations:

**In `plugin.json` (installed plugin context):**

```json
"kaizen-duckdb": {
  "command": "uvx",
  "args": ["mcp-server-motherduck", "--db-path", "${CLAUDE_PLUGIN_ROOT}/data/kaizen.duckdb", "--read-only"],
  "env": { "HOME": "$USERPROFILE" }
}
```

- Points to a persistent `.duckdb` file inside the plugin's data directory
- Read-only mode — the MCP server cannot modify the database
- Uses `${CLAUDE_PLUGIN_ROOT}` for portable path resolution

**In `.mcp.json` (development/local context):**

```json
"kaizen-duckdb": {
  "command": "uvx",
  "args": ["mcp-server-motherduck", "--db-path", ":memory:", "--read-write"]
}
```

- In-memory database — no persistent storage
- Read-write mode — allows creating temporary tables during analysis

### DuckDB Query Patterns

All queries are documented in `skills/transcript-analysis/references/duckdb-queries.md`. Key patterns:

| Query Category | What It Queries | DuckDB Features Used |
|---|---|---|
| Session inventory | Session IDs, date ranges, record counts | `GROUP BY`, `MIN/MAX` on timestamps |
| Record type distribution | Event type frequencies | `GROUP BY`, `ORDER BY frequency` |
| Tool misuse detection | Bash commands that should use built-in tools | `LATERAL unnest`, `from_json`, `regexp_matches`, `CASE WHEN` |
| Tool misuse rate | Per-session misuse percentage | `COUNT(*) FILTER (WHERE ...)`, window functions |
| Error pattern detection | Tool errors by type (edit-before-read, stale edit, etc.) | `LIKE` pattern matching, `LATERAL` subquery |
| User frustration detection | Interrupts, corrections, denials | `regexp_matches` on user message content |
| Subagent delegation analysis | Agent types, models, delegation frequency | JSON path extraction on `Task` tool_use blocks |
| Context waste detection | Orchestrator reads file then delegates mentioning same file | Self-JOIN with `ROW_NUMBER()`, string containment |
| Session timing | Turn durations, averages, maximums | `AVG`, `MAX` on `durationMs` |

**Critical DuckDB techniques:**

- `read_ndjson_auto('/path/to/*.jsonl', columns={line: 'JSON'})` — raw JSON access when auto-detection fails
- `LATERAL unnest(from_json(json_extract(line, '$.message.content'), '["json"]'))` — unpacking JSON arrays for tool call extraction
- `json_extract_string(line, '$.type')` — field extraction from nested JSON
- `regexp_matches(command, '^\s*ls\b')` — regex matching for pattern detection
- `COUNT(*) FILTER (WHERE condition)` — conditional aggregation

### How DuckDB Is Invoked

| Invocation Path | Technology | Use Case |
|---|---|---|
| Agent via MCP `execute_query` tool | MotherDuck MCP server (`mcp-server-motherduck`) | Interactive SQL queries during analysis sessions |
| CLI script (`sentiment-score.py`) | Python `duckdb` library directly | Batch scoring with persistent storage |
| Skill instructions (SKILL.md) | Documents SQL patterns for the agent to use | Reference material — agent copies/adapts queries |

---

## 2. MCP Server Pattern

### FastMCP Version and Configuration

```python
# PEP 723 inline script metadata
# dependencies = ["fastmcp>=3.0.0rc1,<4", ...]
```

- **FastMCP 3.x** (release candidate or newer, below 4.0)
- Server instantiated as: `mcp = FastMCP("kaizen-analysis", mask_error_details=False)`
- `mask_error_details=False` — exposes full error messages to the client (useful for debugging)

### Tool Structure

Six analysis tools plus one dashboard tool, all following this pattern:

```python
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def tool_name(glob_path: str, ..., *, context: Context) -> ReturnType:
    """Docstring serves as tool description for MCP clients."""
    # 1. Resolve input (glob -> file list, or use pre-extracted sequences)
    # 2. Run CPU-bound work via asyncio.to_thread()
    # 3. Return structured data (dict or list[dict])
```

**Key patterns:**

- All analysis tools are `async` and use `asyncio.to_thread()` for CPU-bound operations
- Tools accept either a `glob_path` (raw JSONL files) or pre-extracted `sequences` (dict) to avoid re-reading
- Context parameter used for progress reporting: `await context.info("Building event log...")`
- Private `_impl` functions separate tool registration from business logic
- Error handling via `ToolError` from `fastmcp.exceptions`

### Annotations

Two annotation sets defined as module-level constants:

```python
_READONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_DASHBOARD_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}
```

### Tools Inventory

| Tool | Purpose | Input | Output |
|---|---|---|---|
| `extract_tool_sequences` | Parse JSONL into ordered tool-call arrays per session | `glob_path` | `dict[str, list[str]]` |
| `discover_process_model` | PM4Py Heuristic Miner process discovery | `glob_path` or `sequences` | `str` (heuristic net repr) |
| `check_conformance` | Token-based replay conformance checking | target + reference glob/sequences | `list[dict]` (per-trace fitness) |
| `find_frequent_patterns` | PrefixSpan sequential pattern mining | `glob_path` or `sequences`, `min_support` | `list[dict]` (pattern + support) |
| `detect_frustration_signals` | Regex-based frustration signal extraction | `glob_path` | `list[dict]` (session, timestamp, signal_type, text) |
| `cluster_sessions` | KMeans clustering on tool-call profiles | `glob_path` or `sequences`, `n_clusters` | `dict` (clusters + profiles) |
| `open_dashboard` | Return Panel/Bokeh dashboard URL | none | `dict` (url, message) |

### Dependencies

Heavy scientific stack via PEP 723 inline metadata:

- `fastmcp>=3.0.0rc1,<4` — MCP framework
- `pm4py>=2.7.0` — process mining
- `pandas>=2.0.0` — data manipulation
- `prefixspan>=0.5.2` — sequential pattern mining
- `scikit-learn>=1.0` — KMeans clustering
- `panel>=1.3.0`, `hvplot>=0.9.0`, `holoviews>=1.18.0`, `bokeh>=3.3.0` — dashboard

### Server Registration in plugin.json

```json
"kaizen-analysis": {
  "command": "uv",
  "args": ["run", "--script", "${CLAUDE_PLUGIN_ROOT}/mcp/server.py"]
}
```

- Uses `uv run --script` which reads PEP 723 metadata and auto-installs dependencies
- `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's cache directory at runtime

---

## 3. Plugin Structure

### Directory Layout

```text
agentskill-kaizen/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json                          # Dev MCP config (differs from plugin.json)
├── .gitignore
├── README.md
├── agents/
│   ├── improvement-generator.md       # Generates improvement recommendations
│   └── transcript-analyst.md          # Deep-dive SQL/process mining analysis
├── assets/
│   └── hero.png
├── commands/
│   ├── analyze.md                     # /analyze command
│   ├── explore.md                     # /explore command
│   ├── generate-hooks.md              # /generate-hooks command
│   └── report.md                      # /report command
├── docs/
│   ├── cross-platform-notes.md
│   └── plans/
│       └── 2026-02-20-duckdb-lock-scope-flag.md
├── mcp/
│   ├── server.py                      # FastMCP kaizen-analysis server
│   └── dashboard.py                   # Panel/Bokeh dashboard
├── scripts/
│   └── sentiment-score.py             # VADER sentiment CLI tool
├── skills/
│   ├── kaizen-improvement/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── hook-patterns.md
│   │       └── improvement-templates.md
│   ├── meta-inspector/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── extraction-patterns.md
│   └── transcript-analysis/
│       ├── SKILL.md
│       └── references/
│           ├── duckdb-queries.md
│           └── jsonl-schema.md
├── tests/
│   ├── conftest.py
│   ├── test_dashboard.py
│   └── test_server.py
```

### plugin.json Fields Used

| Field | Value | Notes |
|---|---|---|
| `name` | `agentskill-kaizen` | kebab-case |
| `version` | `0.6.82` | Pre-1.0, high patch count indicates active development |
| `description` | Long, keyword-rich | Includes trigger terms: "anti-patterns", "frustration signals", "continuous improvement" |
| `author` | `{name, url}` | No email |
| `license` | `MIT` | |
| `keywords` | 6 items | "kaizen", "transcript-analysis", "process-mining", etc. |
| `agents` | Array of 2 file paths | Correct format (array, not directory string) |
| `mcpServers` | Inline object (2 servers) | Both MotherDuck and custom FastMCP |

### How Agents Reference MCP

The `transcript-analyst` agent references MCP tools by name in its system prompt:

```markdown
## Tools Available
- **DuckDB MCP** (`execute_query`) — SQL queries against JSONL files
- **Kaizen MCP** — process mining tools (`discover_process_model`, ...)
```

The agent's frontmatter loads the `transcript-analysis` skill for schema/query reference:

```yaml
skills: transcript-analysis
```

The agent does NOT declare `allowed-tools` — it inherits all tools from the parent context, including both MCP servers.

---

## 4. Sentiment Scoring Pattern (sentiment-score.py)

### Architecture

- Standalone CLI tool using Typer with Rich progress bars
- PEP 723 inline script metadata for dependency declaration
- VADER sentiment analysis (`vaderSentiment` library) — lexicon-based, no ML model needed
- Dual output: CSV file + DuckDB persistent database

### Data Model

```python
@dataclass(slots=True)
class ScoredMessage:
    session_id: str
    timestamp: str
    message_index: int
    compound: float      # -1.0 to 1.0 overall sentiment
    positive: float      # 0.0 to 1.0
    negative: float      # 0.0 to 1.0
    neutral: float       # 0.0 to 1.0
    message_length: int
    message_preview: str
    project_path: str
    project_name: str
```

### DuckDB Persistence

- Table: `sentiment` with primary key `(session_id, message_index)`
- Upsert semantics: `INSERT ... ON CONFLICT DO UPDATE` — safe for re-runs
- Default path: `~/.claude/kaizen/kaizen.duckdb`
- Optional — gracefully skips if `duckdb` not installed

### Noise Filtering

Filters out system-generated content before scoring:

- XML tag prefixes: `<local-command-caveat>`, `<bash-stdout>`, `<tool_use_error>`, etc.
- Skill injection content: "Base directory for this skill"
- Tool use results (records with `toolUseResult` field)

---

## 5. Frustration Detection in Kaizen (Current State)

### What Kaizen Detects

**In the MCP server (`detect_frustration_signals`):**

Four regex-based signal categories:

| Signal Type | Patterns Matched |
|---|---|
| `correction` | `no,`, `don't`, `wrong`, `incorrect`, `stop`, `undo`, `revert` |
| `denial` | `that's not`, `i didn't`, `never`, `absolutely not` |
| `interrupt` | `wait`, `hold on`, `cancel`, `abort`, `forget it`, `nevermind` |
| `frustration` | `why did you`, `you keep`, `again?`, `still wrong`, `broken` |

**In DuckDB queries (user frustration detection):**

- `[Request interrupted by user]` — Ctrl+C events
- `[Request interrupted by user for tool use]` — tool denial
- Direct corrections starting with: "No,", "Don't", "Stop", "Why did you", "Why would"
- Content containing: "wrong", "incorrect", "that's not", "you should not"

**In VADER sentiment scoring:**

- Compound scores from -1.0 to 1.0 per user message
- Summary statistics: mean, median, min, max across sessions
- No threshold-based alerting or categorization

### Output Format

Frustration signals return flat records:

```python
{
    "session_id": "abc123",
    "timestamp": "2026-02-18T...",
    "signal_type": "correction",
    "message_text": "No, that's wrong. Use the Read tool instead."
}
```

One signal per message (first match wins via `break`).

---

## 6. Gaps: What Kaizen Does NOT Do (frustration-analyzer Opportunities)

### Explicit Insult Detection

Kaizen detects **soft frustration signals** (corrections, denials, interrupts). It does NOT detect:

- Direct insults or profanity directed at the agent
- Creative verbal abuse (sarcasm, metaphors, analogies)
- Escalating hostility patterns (mild correction -> strong language -> insults)
- Humor-based frustration (jokes at the agent's expense)

The regex patterns are conservative — they catch "wrong" and "don't" but miss colorful language.

### Scenario Extraction (Context Window)

Kaizen extracts individual frustration signals as isolated records. It does NOT:

- Extract the N messages **before** the frustration event (the buildup)
- Reconstruct the scenario that led to frustration (what the agent did wrong)
- Link the frustration signal back to the specific agent action that caused it
- Provide a narrative view: "Agent did X, then Y, user said Z"

The `context_waste_detection` DuckDB query does a limited version (Read then Task within 5 turns), but there is no general "extract conversation window around event" capability.

### Insult Rating/Scoring

Kaizen has no rating system for frustration intensity beyond:

- VADER compound score (-1.0 to 1.0) — general sentiment, not insult-specific
- Binary signal type classification (correction/denial/interrupt/frustration)
- No creativity, humor, severity, or accuracy dimensions
- No leaderboard or ranking of "best" insults

### DuckDB Persistence of Analysis Findings

Kaizen persists only sentiment scores to DuckDB. It does NOT persist:

- Frustration signal detections (these are returned as in-memory MCP tool results)
- Analysis findings or anti-pattern detections
- Historical trends across analysis runs
- Aggregated statistics over time

The analysis output goes to markdown files in `.planning/kaizen/`, not to a queryable database.

### Missing for frustration-analyzer

| Capability | Kaizen Has | frustration-analyzer Needs |
|---|---|---|
| Soft frustration detection (corrections, denials) | Yes (regex) | Inherit and extend |
| Explicit insult/profanity detection | No | Yes — lexicon + pattern matching |
| Scenario extraction (N messages before event) | No | Yes — sliding window on JSONL |
| Multi-dimensional rating (creativity, humor, severity, accuracy) | No | Yes — scoring rubric per insult |
| Persistent findings database | No (markdown only) | Yes — DuckDB tables for findings |
| Historical trend tracking | No | Yes — queryable history of incidents |
| Escalation pattern detection | No | Yes — detect mild->severe progressions |
| Leaderboard/rankings | No | Yes — "hall of fame" for creative insults |

---

## 7. Design Recommendations for frustration-analyzer

### Reusable Patterns from Kaizen

1. **MCP server as `uv run --script`** with PEP 723 inline deps — proven pattern, auto-installs dependencies
2. **FastMCP 3.x with annotations** — `_READONLY_ANNOTATIONS` dict pattern for tool metadata
3. **`asyncio.to_thread()` for CPU-bound work** — keeps MCP server responsive
4. **MotherDuck MCP for ad-hoc SQL** + custom FastMCP for domain logic — clean separation
5. **`${CLAUDE_PLUGIN_ROOT}`** for portable path resolution in plugin.json
6. **Dual MCP config** — `.mcp.json` for dev (`:memory:`, read-write) vs `plugin.json` for installed (file-based, read-only)
7. **Agent with `skills:` preloading** — agent loads domain skill for schema reference
8. **DuckDB upsert pattern** — `INSERT ... ON CONFLICT DO UPDATE` for idempotent writes

### New Patterns Needed

1. **Sliding window extractor** — given an event index in a JSONL file, extract N records before and after
2. **Multi-dimensional scorer** — not just VADER compound, but creativity/humor/severity/accuracy as separate floats
3. **Persistent findings table** — DuckDB table for insult records with all dimensions, queryable over time
4. **Escalation detector** — track frustration intensity over consecutive user messages within a session
5. **Insult lexicon** — curated word/phrase list beyond VADER's general sentiment vocabulary

---

## Sources

- `plugins/agentskill-kaizen/.claude-plugin/plugin.json` — plugin manifest
- `plugins/agentskill-kaizen/.mcp.json` — development MCP config
- `plugins/agentskill-kaizen/mcp/server.py` — FastMCP kaizen-analysis server (614 lines)
- `plugins/agentskill-kaizen/scripts/sentiment-score.py` — VADER sentiment CLI (665 lines)
- `plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md` — transcript analysis skill
- `plugins/agentskill-kaizen/skills/transcript-analysis/references/duckdb-queries.md` — SQL query patterns
- `plugins/agentskill-kaizen/agents/transcript-analyst.md` — transcript analyst agent
