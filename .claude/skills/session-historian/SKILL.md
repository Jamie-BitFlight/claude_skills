---
name: session-historian
description: Look up prior Claude Code sessions when context is lost or forgotten. Use when asked what was done before, what happened in the last session, or any request to recall past conversation history, prior decisions, experiments, or outcomes. Indexes and searches raw JSONL transcripts from ~/.claude/projects/ via DuckDB. Returns verbatim user messages, summarizes AI actions and sub-agent outcomes, detects tool errors and user frustration signals, and reports tool usage statistics. Summaries cached at ~/.claude/kaizen/session-summaries/.
---

# Session Historian

Look up what happened in prior Claude Code sessions. Index and search raw JSONL transcripts. Cache session summaries.

## Script

```text
.claude/skills/session-historian/scripts/session_query.py
```

Run directly (shebang + PEP 723, no manual `uv run` prefix needed):

```bash
.claude/skills/session-historian/scripts/session_query.py list
.claude/skills/session-historian/scripts/session_query.py messages <session-id>
.claude/skills/session-historian/scripts/session_query.py search "experiment worktree"
.claude/skills/session-historian/scripts/session_query.py show <session-id>
.claude/skills/session-historian/scripts/session_query.py index
```

## Workflow: "I forgot what happened"

1. **List recent sessions** to find the relevant one:

   ```bash
   .claude/skills/session-historian/scripts/session_query.py list --limit 10
   ```

2. **Read verbatim user messages** (fastest way to reconstruct context):

   ```bash
   .claude/skills/session-historian/scripts/session_query.py messages <session-id-prefix>
   ```

3. **Search for specific topics** across all raw files:

   ```bash
   .claude/skills/session-historian/scripts/session_query.py search "experiment" --limit 10
   ```

4. **Generate and cache a session summary** (when detail is needed):
   - Run `show <session-id>` to get session metadata and file path
   - Read the raw JSONL file
   - Produce a structured summary following the template below
   - Write to `~/.claude/kaizen/session-summaries/<session-id>.md`
   - Run `mark-summarized <session-id>` to flag in the index

## Summary Template

When generating a session summary, write to `~/.claude/kaizen/session-summaries/<session-id>.md`:

```markdown
---
source_type: claude-session
source_path: <file_path>
session_id: <session_id>
project: <project_name>
date_range: <first_ts> → <last_ts>
user_message_count: <N>
assistant_turns: <N>
confidence: high|medium|low
generated_at: <ISO timestamp>
---

## Summary

[BLUF: 2-3 sentences on what this session accomplished]

## User Messages (verbatim)

[Numbered list of every user message, exactly as written, with timestamp]

1. [2026-02-21T15:40] "First ensure that .claude/worktrees is gitignored..."
2. [2026-02-21T16:51] "Ah. Do you not remember the experiment..."

## Actions Taken

[Bullet list of what the AI did — file edits, commands run, commits made]

- Created .claude/worktrees directory and added to .gitignore
- Spawned sub-agent a0263e5 to read workflow docs → produced project_workflow.draft.md
- ...

## Sub-Agent Tasks and Outcomes

| Agent ID | Task | Outcome |
|----------|------|---------|
| a0263e5  | Read docs, produce workflow draft | Produced project_workflow.draft.md |
| a5d97a8  | Execute work-backlog-item workflow | Partial — blocked at AskUserQuestion node |

## Key Findings / Decisions

[Important decisions made, things discovered, conclusions reached]

## What Was NOT Completed

[Work started but not finished, blocked items]

## Sources

File: <file_path>
Indexed: <DB_PATH>
```

## Fidelity Rules (from summarizer skill)

- **Read before summarizing**: Read the actual JSONL file, do not guess from metadata.
- **Verbatim user messages**: Copy exactly — never paraphrase.
- **Preserve counts**: "3 sub-agents spawned, 2 succeeded, 1 blocked" not "most sub-agents succeeded."
- **Distinguish absence**: "Not mentioned in transcript" not "didn't happen."
- **Search raw files**: `search` command reads raw JSONL, not summaries. Never search summaries for facts.

## Index Location

```text
~/.claude/kaizen/session-index.duckdb    ← DuckDB index (sessions + user_messages tables)
~/.claude/kaizen/session-summaries/      ← Cached AI-generated summaries
```

The index is built on first `list` or explicitly with `index`. It is NOT automatically kept current — re-run `index` or pass `--rebuild` to pick up new sessions.

## Command Reference

### errors

List tool errors from a session with timestamps and tool names.

Performs a two-pass scan: first builds a map of tool-use IDs to tool names from assistant records, then extracts `tool_result` blocks where `is_error` is `True` from user records and resolves the tool name for each.

```bash
# Rich formatted output (default)
.claude/skills/session-historian/scripts/session_query.py errors
.claude/skills/session-historian/scripts/session_query.py errors <session-id-prefix>

# Tab-separated plain text: timestamp TAB tool_name TAB error_content
.claude/skills/session-historian/scripts/session_query.py errors --raw
```

Arguments and options:

- `session_id` — session ID prefix or `"last"` (default) for the most recent session
- `--raw` — output tab-separated lines: `timestamp\ttool_name\terror_content_single_line`

Exit codes: 1 if session not found; 0 if session found but no errors exist.

### tools

List all tools used in a session with call counts and success/failure breakdown.

Performs a two-pass scan: collects `tool_use` blocks from assistant records, then correlates `tool_result` blocks from user records to classify each call. Calls with no matching result are counted as unmatched (session interrupted before the tool returned).

```bash
# Rich table output (default) — sorted by total calls descending
.claude/skills/session-historian/scripts/session_query.py tools
.claude/skills/session-historian/scripts/session_query.py tools <session-id-prefix>

# Tab-separated plain text with header row
.claude/skills/session-historian/scripts/session_query.py tools --raw
```

Arguments and options:

- `session_id` — session ID prefix or `"last"` (default) for the most recent session
- `--raw` — outputs header `tool\ttotal\tsuccesses\tfailures\tunmatched` then one row per tool

Table columns: Tool Name, Total Calls, Successes, Failures, Unmatched.

Exit codes: 1 if session not found; 0 if session found but no tool calls recorded.

### irritation

Detect user frustration signals in a session. Reports two signal types:

1. **Correction phrases** — user messages containing phrases such as `"wrong"`, `"stop"`, `"undo"`, `"revert"`, `"no,"` etc., matched case-insensitively.
2. **Stuck tool loops** — sequences of 3 or more consecutive identical tool calls (same tool name and input hash) in assistant records.

```bash
# Rich formatted output — two sections: Correction Phrases + Stuck Tool Loops
.claude/skills/session-historian/scripts/session_query.py irritation
.claude/skills/session-historian/scripts/session_query.py irritation <session-id-prefix>

# Type-prefixed tab-separated lines
.claude/skills/session-historian/scripts/session_query.py irritation --raw
```

Arguments and options:

- `session_id` — session ID prefix or `"last"` (default) for the most recent session
- `--raw` — type-prefixed tab-separated lines:
  - Correction phrase match: `phrase\t<ts>\t<phrase>\t<excerpt>`
  - Stuck loop signal: `loop\t<ts>\t<tool>\t<count>\t<hash>`

Exit codes: 1 if session not found; 0 if session found but no signals detected.

### current-path

Print the JSONL file path for the current live session. Reads `CLAUDE_SESSION_ID` from the environment and resolves the path using the encoded current working directory. Does not use DuckDB — pure filesystem check.

Default output is a single raw line (machine-readable), suitable for agent pipelines. Use `--rich` for human display.

```bash
# Raw output (default) — one absolute path, no markup, agent-safe
.claude/skills/session-historian/scripts/session_query.py current-path

# Rich Panel display
.claude/skills/session-historian/scripts/session_query.py current-path --rich
```

Arguments and options:

- No `session_id` argument — reads `CLAUDE_SESSION_ID` from the environment
- `--rich` — renders the path inside a Rich Panel with a green border (default: raw path only)

Exit codes: 1 if `CLAUDE_SESSION_ID` is not set, or if the expected JSONL file does not exist (prints diagnostics to stderr including session ID, expected path, and projects directory).

## JSONL Schema Reference

Records in `~/.claude/projects/<project-slug>/<session-id>.jsonl`:

```json
{"type": "user", "sessionId": "uuid", "timestamp": "ISO8601",
 "message": {"content": "string or [{type,text}]"}}
{"type": "assistant", "sessionId": "uuid", "timestamp": "ISO8601",
 "message": {"content": [{...}]}}
```

Records with `toolUseResult` key are tool results — skip for user message extraction.
Tool use blocks have `type: "tool_use"` inside `message.content` array.
