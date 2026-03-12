---
name: Enhance session-historian script with Agent SDK navigation and current session path reporting
description: <div><sub>2026-03-11T15:47:18Z</sub>
metadata:
  topic: enhance-session-historian-script-with-agent-sdk-navigation-a
  source: User request — session 2026-03-11
  added: '2026-03-11'
  priority: P1
  type: Feature
  status: in-progress
  issue: '#599'
  last_synced: '2026-03-12T12:47:32Z'
  groomed: '2026-03-11'
  plan: plan/tasks-6-session-historian-enhance.md
---

## Fact-Check

<div><sub>2026-03-11T15:47:18Z</sub>

Date: 2026-03-11
Claims checked: 3

VERIFIED: Agent SDK has list_sessions() / get_session_messages() utilities; session JSONL stored at ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
  Source: https://platform.claude.com/docs/en/agent-sdk/sessions.md (accessed 2026-03-11)

VERIFIED: Session JSONL paths are accessible to agents — Claude Code hooks provide transcript_path field with concrete filesystem paths
  Source: https://code.claude.com/docs/en/hooks.md (accessed 2026-03-11)

REFUTED: "Agent SDK is the correct tool for navigating Claude Code session history"
  Finding: Agent SDK is a general-purpose client library for building agents. Claude Code scripts have direct filesystem access to session JSONL via hooks and standard path resolution. The correct approach is direct Python file I/O using the known path pattern, optionally using Agent SDK utility functions as a library — not as the primary mechanism.
  Source: https://code.claude.com/docs/en/sub-agents.md (accessed 2026-03-11)

Summary: 2 VERIFIED | 1 REFUTED | 0 INCONCLUSIVE
</div>

## RT-ICA

<div><sub>2026-03-11T15:47:27Z</sub>

Goal: Extend session_query.py with richer query capabilities (errors, tools used, user irritation signals) and current-session JSONL path resolution.

Conditions:
1. Session JSONL format is known and parseable | AVAILABLE | ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl, format documented
2. Current session path can be derived programmatically | AVAILABLE | Hooks expose transcript_path; resolvable via CLAUDE_SESSION_ID env var + path pattern
3. Agent SDK as primary parsing mechanism | MISSING (REFUTED) | Use direct Python file I/O; Agent SDK is optional client library only
4. Error/tool/irritation signal schema in JSONL | DERIVABLE | Readable from existing session_query.py + live JSONL inspection
5. Existing session_query.py is the correct base | AVAILABLE | Confirmed at .claude/skills/session-historian/scripts/session_query.py

Decision: APPROVED
Correction: Replace "enhance via Agent SDK" with "enhance via direct JSONL parsing; optionally use Agent SDK list_sessions()/get_session_messages() as utility functions"
</div>

## Groomed (2026-03-11)

### Issue Classification

<div><sub>2026-03-11T15:47:34Z</sub>

Type: procedural
Scenario-target: Feature enhancement — extend existing script with new query modes and path resolution
Analysis method: none (no defect, no recurring pattern)
Rationale: Clean feature addition to session_query.py with well-defined inputs (JSONL files), outputs (query results), and scope boundaries
</div>

### Prior Work

<div><sub>2026-03-11T15:50:14Z</sub>

session_query.py at `.claude/skills/session-historian/scripts/session_query.py` already provides:

- `list` — recent sessions with metadata (session_id, project, timestamps, msg counts, KB, summary flag) via DuckDB index
- `messages <session-id>` — verbatim user messages from DuckDB index, supports `last` alias
- `search <query>` — raw JSONL grep across all files, returns matching user messages with context window
- `show <session-id>` — session metadata from index, prints cached summary if present
- `index` — builds/rebuilds DuckDB session index (tables: sessions, user_messages)
- `mark-summarized <session-id>` — flags a session as having a cached summary

DuckDB schema already present:
- `sessions` table: session_id, file_path, project_slug, project_name, first_ts, last_ts, total_records, user_msg_count, assistant_turns, file_size_kb, has_summary, indexed_at
- `user_messages` table: session_id, file_path, msg_index, timestamp, content, word_count

Records with `toolUseResult` key are already filtered out of user message extraction. Noise prefixes (system-reminder, task-notification, etc.) are already filtered.

What is NOT yet indexed or queryable:
- Tool use blocks (names, inputs, counts) — not in DB schema
- Tool errors (is_error=true tool_result records) — not captured
- Tool use repetition patterns (repeated same tool with same args = stuck) — no detection
- User correction/irritation language in messages — not detected
- Current session JSONL path — not resolvable from within the script
- Subagent vs. main-session distinction — not surfaced

</div>

### JSONL Schema Research

<div><sub>2026-03-11T15:50:38Z</sub>

Verified by reading `/home/ubuntulinuxqa2/.claude/projects/-home-ubuntulinuxqa2-repos-claude-skills/824cd038-8761-4069-820f-fca8bd31a315/subagents/agent-a05e9fe.jsonl` directly (2026-03-11).

Top-level record fields:
- `type`: "user" | "assistant"
- `sessionId`: UUID string (matches parent session, not subagent)
- `agentId`: short hex string (e.g. "a05e9fe") — present in subagent files
- `isSidechain`: boolean — true for subagent files
- `timestamp`: ISO 8601 with milliseconds (e.g. "2026-01-09T15:08:25.035Z")
- `uuid`: UUID of this record
- `parentUuid`: UUID of prior record (null for first)
- `cwd`: working directory string
- `version`: Claude Code version string
- `gitBranch`: current branch

User record with toolUseResult:
- `toolUseResult`: string — present when this is a tool result record
- `sourceToolAssistantUUID`: UUID of the assistant turn that issued the tool call
- `message.role`: "user"
- `message.content`: array with one `{"type": "tool_result", "content": "...", "is_error": true|false, "tool_use_id": "toolu_..."}`

Assistant record with tool call:
- `message.role`: "assistant"
- `message.content`: array containing blocks:
  - `{"type": "text", "text": "..."}` — text output
  - `{"type": "tool_use", "id": "toolu_...", "name": "Bash"|"Read"|"Write"|..., "input": {...}}` — tool call

Error signal location:
- `is_error: true` inside a `tool_result` content block within a user record that has `toolUseResult` set
- `<tool_use_error>` prefix appears in user message content (noise prefix already in _NOISE_PREFIXES)

Irritation signal locations:
- User message content containing correction phrases: "no,", "wrong", "that's not", "you're not", "stop", "again", "already told you", "I said", "didn't I say"
- Repeated identical tool_use (same tool name + same input hash) within one session = stuck loop indicator
- Multiple consecutive user messages with short word count after a long assistant turn = frustration pattern

Storage path findings:
- Subagent JSONL: `~/.claude/projects/<encoded-cwd>/<session-uuid>/subagents/agent-<id>.jsonl`
- Main session JSONL: NOT found at expected `~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl` in the claude-skills project. The session UUID directories contain only subagents/ and tool-results/ subdirectories. The main session transcript may be stored elsewhere or may not be persisted as a standalone JSONL in this installation version (Claude Code 2.1.x).

CLAUDE_SESSION_ID environment variable: available in hooks via `transcript_path`; resolvable at runtime by agents using `os.environ.get("CLAUDE_SESSION_ID")`. The path pattern `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` should be verified against actual filesystem at implementation time — the grooming search found no top-level JSONL files matching this pattern.

</div>

### Expected Behavior

<div><sub>2026-03-11T15:50:49Z</sub>

The enhanced script exposes four new query modes:

1. `errors <session-id>` — lists all tool errors in a session: timestamp, tool name, error message excerpt, and preceding user message for context. Output sortable by recency.

2. `tools <session-id>` — lists all tool calls in a session with name, call count, and any error count per tool. Supports `--errors-only` flag to show only tools that errored.

3. `irritation <session-id>` — scans for user irritation signals: correction phrases in user messages, repeated identical tool calls (stuck loop), and rapid short user messages after long assistant turns. Returns timestamped findings with severity classification.

4. `current-path` — prints the JSONL file path for the current session, resolved from `CLAUDE_SESSION_ID` environment variable and known path patterns. Exits with code 1 and an informative message if CLAUDE_SESSION_ID is not set or no matching file is found.

All new commands work against raw JSONL (no index required) so they work on sessions not yet indexed. The `errors` and `tools` commands also accept `last` as session ID shorthand (same as existing `messages` command).

</div>

### Acceptance Criteria

<div><sub>2026-03-11T15:51:03Z</sub>

1. Running `session_query.py errors <session-id>` against a session JSONL that contains `is_error: true` tool_result records returns at least one row with tool name and error message excerpt. Running it against a session with no errors exits cleanly with "No errors found" message.

2. Running `session_query.py tools <session-id>` returns a list of all distinct tool names used in the session with per-tool call count. Running with `--errors-only` returns only tools that had at least one error.

3. Running `session_query.py irritation <session-id>` against a session where the same tool was called 3+ times with identical input reports a "stuck loop" finding. Running against a session with user messages containing "no," or "that's wrong" reports a "correction phrase" finding.

4. Running `session_query.py current-path` inside a Claude Code session (CLAUDE_SESSION_ID set) prints a filesystem path. If the path is a file that exists, it is a valid JSONL file. If CLAUDE_SESSION_ID is not set, the command exits with code 1 and prints an error to stderr.

5. Running `session_query.py errors last` and `session_query.py tools last` resolves to the most recently indexed session, consistent with how `messages last` behaves.

6. All four new commands pass `uv run prek run --files session_query.py` (ruff format + ruff check + type checker) with no new violations.

7. Running `session_query.py --help` lists all new commands in the help text.

</div>

### Files

<div><sub>2026-03-11T15:51:12Z</sub>

Modify only:
- `.claude/skills/session-historian/scripts/session_query.py` — add four new Typer commands: `errors`, `tools`, `irritation`, `current-path`

No new files required. No new Python dependencies required — duckdb and typer are already declared in PEP 723 inline metadata.

The DuckDB schema does NOT need to change for the initial implementation. The new commands read raw JSONL directly (no index). If caching tool/error data in the index is desired in a follow-up, a schema migration would be needed — that is out of scope for this item.

</div>

### Desired Structure

<div><sub>2026-03-11T15:51:22Z</sub>

session_query.py exposes these commands after the change:

```text
list              — unchanged
messages          — unchanged
search            — unchanged
show              — unchanged
index             — unchanged
mark-summarized   — unchanged
errors            — NEW: tool errors in a session
tools             — NEW: tool usage summary for a session
irritation        — NEW: user irritation signal scan
current-path      — NEW: print current session JSONL path
```

The four new commands parse raw JSONL records directly without requiring the index. They share the existing `_iter_records()` and `_extract_text()` helpers. They follow the same CLI conventions as existing commands: Rich output by default, `--raw` flag for plain text where useful, `last` alias for most-recent session.

Irritation signal detection uses a fixed vocabulary of correction phrases (configurable as a module-level constant) and a configurable repeat-threshold for stuck-loop detection (default: 3 identical calls).

</div>

### Resources

<div><sub>2026-03-11T15:51:34Z</sub>

| Type | Item |
|------|------|
| Prior work | `.claude/skills/session-historian/scripts/session_query.py` — base script with JSONL parsing, DuckDB indexing, existing commands |
| Prior work | `.claude/skills/session-historian/SKILL.md` — skill documentation with JSONL schema reference |
| Prior work | `/home/ubuntulinuxqa2/.claude/projects/-home-ubuntulinuxqa2-repos-claude-skills/824cd038-8761-4069-820f-fca8bd31a315/subagents/agent-a05e9fe.jsonl` — representative JSONL file with verified schema (user, assistant, tool_use, tool_result, error records) |
| Agent | @python3-development:python-cli-architect — Typer/Rich CLI implementation with PEP 723, ruff, type checking |
| Agent | @python3-development:python-pytest-architect — test coverage for new commands |
| Agent | @python3-development:python-code-reviewer — post-implementation review |

</div>

### Dependencies

<div><sub>2026-03-11T15:51:40Z</sub>

- Depends on: None — self-contained enhancement to an existing script
- Blocks: None identified in backlog

</div>

### Blockers

<div><sub>2026-03-11T15:51:50Z</sub>

One open question for implementation: the main session JSONL path (not subagent) was not found at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` on this installation. The project directories contain only subagents/ and tool-results/ subdirectories. The `current-path` command implementor must verify the actual storage location at implementation time by checking `CLAUDE_SESSION_ID` at runtime and searching the filesystem. The command should report clearly when the file is not found rather than silently returning a nonexistent path.

</div>

### Effort

<div><sub>2026-03-11T15:51:58Z</sub>

Medium — four new Typer commands on an established codebase with shared JSONL parsing infrastructure already in place. The irritation detection heuristics require careful threshold tuning. The `current-path` command needs filesystem path resolution that may require trial-and-error against the actual Claude Code installation.

</div>

### Priority

<div><sub>2026-03-11T15:52:05Z</sub>

7/10 — enables automated irritation/error pattern analysis of past sessions, which directly supports session debriefs and kaizen workflows. Not blocking active work but meaningfully improves session retrospective tooling.

</div>
