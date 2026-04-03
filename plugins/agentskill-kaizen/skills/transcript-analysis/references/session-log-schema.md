# Claude Code Session Log Schema Reference

<!-- Monorepo sync: primary edit path is `plugins/plugin-creator/skills/hooks-guide/references/claude-session-log-schema-reference.md`. Copy here when that file changes so the kaizen MCP resource/tool ships a self-contained reference. -->

All claims in this file are sourced from direct inspection of actual session JSONL files
and verified against the LM Assist TypeScript source at `.claude/worktrees/lmassist/`.
No fields are inferred or assumed.

SOURCE: Record schema verified 2026-03-24 by direct inspection of session JSONL files under
`~/.claude/projects/`. Directory structure and project-key encoding corrected 2026-03-24
against LM Assist source ([`core/src/utils/path-utils.ts`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/utils/path-utils.ts),
[`core/src/session-reader.ts`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-reader.ts),
[`core/src/agent-session-store.ts`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts),
[`core/src/agent-teams-service.ts`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-teams-service.ts),
[`core/src/tasks-service.ts`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/tasks-service.ts)).
Size statistics from 500-file scan across `~/.claude/projects/**/*.jsonl`.

---

## `~/.claude/` Directory Structure

```text
~/.claude/
├── projects/
│   └── <project-key>/                    ← dash-encoded project path (see encoding below)
│       ├── <session-id>.jsonl            ← main session transcript
│       ├── agent-<agent-id>.jsonl        ← top-level subagent transcript
│       └── <session-id>/
│           └── subagents/
│               └── agent-<agent-id>.jsonl ← nested subagent transcript
├── tasks/
│   └── <task-list-id>/                   ← one directory per task list (often a session-id)
│       ├── <task-id>.json                ← individual task file
│       └── ...
├── plans/
│   └── <plan-name>.md                    ← plan markdown files
└── teams/
    └── <team-name>/
        └── config.json                   ← team configuration file
```

**Project key encoding**: Claude Code encodes the project path using dash-replacement (not
URL-encoding). All directory separators (`/`, `\`) and colons (`:`) are replaced with `-`.

```text
Linux:   /home/user/repos/myproject   →  -home-user-repos-myproject
macOS:   /Users/admin/project         →  -Users-admin-project
Windows: C:\home\project              →  C--home-project
```

SOURCE: [`core/src/utils/path-utils.ts` lines 17–19](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/utils/path-utils.ts#L17-L19):

```typescript
export function legacyEncodeProjectPath(projectPath: string): string {
  return projectPath.replace(/[:\\/]/g, '-');
}
```

**Session files**: The main session transcript is `{sessionId}.jsonl` directly inside the
project-key directory. Subagent files are named `agent-{agentId}.jsonl`. Nested subagents live
in `{sessionId}/subagents/agent-{agentId}.jsonl`.

SOURCE: [`core/src/agent-session-store.ts` lines 2418–2438](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L2418-L2438); [`core/src/session-reader.ts` lines 169–191](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-reader.ts#L169-L191).

**Listing sessions**: The `SessionReader.listSessions()` method skips files starting with
`agent-` — these are subagent transcripts, not main sessions.

SOURCE: [`core/src/session-reader.ts` lines 190–191](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-reader.ts#L190-L191):

```typescript
if (!file.endsWith('.jsonl') || file.startsWith('agent-')) {
  continue;
}
```

XDG alternative path (from ccusage): `~/.config/claude/projects/`

Glob pattern for all session transcripts: `~/.claude/projects/**/*.jsonl`

Each `.jsonl` file is newline-delimited JSON — one JSON object per line.

---

## Message Types

`type` is the discriminator field on every JSONL record. Full set:

```typescript
type ClaudeSessionMessageType =
  | 'system'                // System messages (init, turn_duration, stop_hook_summary, compact_boundary)
  | 'user'                  // User prompts and tool results
  | 'assistant'             // Assistant responses
  | 'result'                // Execution result (final record in completed sessions)
  | 'progress'              // Progress updates during execution
  | 'summary'               // Context compaction summaries
  | 'file-history-snapshot' // File state snapshots
```

SOURCE: [`core/src/agent-session-store.ts` lines 362–369](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L362-L369).

System messages additionally have a `subtype` field:

```typescript
type ClaudeSystemSubtype =
  | 'init'              // Session initialization (first record)
  | 'turn_duration'     // Duration of a turn
  | 'stop_hook_summary' // Stop hook execution summary
  | 'compact_boundary'; // Context compaction boundary marker
```

SOURCE: [`core/src/agent-session-store.ts` lines 373–378](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L373-L378).

---

## Top-Level Record Fields

Every record in a session JSONL file has these fields:

```json
{
  "parentUuid": "string — UUID of parent message",
  "isSidechain": false,
  "userType": "string",
  "cwd": "/absolute/working/directory",
  "sessionId": "string — session identifier",
  "version": "string",
  "gitBranch": "string",
  "agentId": "string — present in subagent logs",
  "slug": "string",
  "type": "user | assistant | system | result | progress | summary | file-history-snapshot",
  "message": {},
  "uuid": "string — this record's UUID",
  "timestamp": "ISO 8601 string",
  "requestId": "string — present on assistant records",
  "sourceToolAssistantUUID": "string — present on user records that are tool results"
}
```

---

## `type: "system"` Records — Session Init

The first record in every session file is `type: "system"`, `subtype: "init"`. It contains
session metadata set when Claude Code starts:

```typescript
interface ClaudeSystemInit {
  type: 'system';
  subtype: 'init';
  cwd: string;
  session_id: string;
  tools: string[];
  mcp_servers: Array<{ name: string; status: string }>;
  model: string;
  permissionMode: string;
  slash_commands: string[];
  claude_code_version: string;
  output_style: string;
  agents?: unknown[];
  plugins?: unknown[];
}
```

SOURCE: [`core/src/agent-session-store.ts` lines 389–403](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L389-L403).

---

## `type: "result"` Records — Execution Result

The last record in a completed session is `type: "result"`. It records the final outcome:

```typescript
interface ClaudeResultMessage {
  type: 'result';
  subtype: 'success' | 'error' | 'cancelled' | 'timeout';
  session_id: string;
  result?: string;
  errors?: string[];
  is_error: boolean;
  duration_ms: number;
  duration_api_ms: number;
  num_turns: number;
  total_cost_usd: number;
  usage: {
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens: number;
    cache_read_input_tokens: number;
  };
}
```

SOURCE: [`core/src/agent-session-store.ts` lines 430–447](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L430-L447).

The `SessionReader.listSessionsWithDetails()` method reads the last line of each file and
extracts `num_turns`, `total_cost_usd`, `duration_ms`, and `is_error` from this record.

SOURCE: [`core/src/session-reader.ts` lines 243–254](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-reader.ts#L243-L254).

---

## `type: "assistant"` Records

The `message` object on assistant records:

```typescript
interface ClaudeAssistantMessage {
  type: 'assistant';
  message: {
    id: string;
    model: string;
    content: Array<{
      type: 'text' | 'tool_use' | 'thinking';
      text?: string;       // present when type === 'text'
      id?: string;         // present when type === 'tool_use'
      name?: string;       // present when type === 'tool_use'
      input?: unknown;     // present when type === 'tool_use'
      thinking?: string;   // present when type === 'thinking' (extended thinking)
    }>;
    usage?: {
      input_tokens: number;
      output_tokens: number;
      cache_creation_input_tokens: number;
      cache_read_input_tokens: number;
    };
    stop_reason?: string;
  };
}
```

SOURCE: [`core/src/agent-session-store.ts` lines 406–427](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L406-L427).

The `thinking` content type is an extended thinking block. LM Assist extracts these separately
into `thinkingBlocks` in the session cache.

The raw JSON structure using the wire format (as it appears in the JSONL):

```json
{
  "model": "claude-sonnet-4-6",
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [],
  "stop_reason": "tool_use | end_turn",
  "stop_sequence": null,
  "usage": {}
}
```

### usage Object

Token costs are recorded **per assistant turn**, not per individual tool call.

```json
{
  "input_tokens": 2,
  "output_tokens": 1,
  "cache_creation_input_tokens": 34915,
  "cache_read_input_tokens": 0,
  "cache_creation": {
    "ephemeral_5m_input_tokens": 34915,
    "ephemeral_1h_input_tokens": 0
  },
  "service_tier": "standard"
}
```

**Important**: `input_tokens` reflects the total context sent to the API for that turn, including
all accumulated tool results. There is no per-tool-call token count in native logs.

---

## `type: "user"` Records

The `message` object on user records:

```json
{
  "role": "user",
  "content": []
}
```

User records include: human messages, tool results returned to the model, and system messages.

### User Message Classification (PromptType)

Not all `type: "user"` records with text content are real human prompts. LM Assist classifies
them by examining the XML tag prefix of the text:

```typescript
type PromptType = 'user' | 'command' | 'command_output' | 'system_caveat' | 'hook_result';

function classifyUserPrompt(text: string, isMeta?: boolean): PromptType {
  if (isMeta || text.trimStart().startsWith('<local-command-caveat>')) return 'system_caveat';
  if (text.trimStart().startsWith('<command-name>') ||
      text.trimStart().startsWith('<command-message>'))           return 'command';
  if (text.trimStart().startsWith('<local-command-stdout>'))      return 'command_output';
  if (text.trimStart().startsWith('<user-prompt-submit-hook>'))   return 'hook_result';
  return 'user';
}
```

SOURCE: [`core/src/session-cache.ts` lines 33–56](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-cache.ts#L33-L56).

A prompt is a "real" user prompt if `promptType` is `undefined`, `'user'`, or `'command'`.

SOURCE: [`core/src/session-cache.ts` lines 61–63](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-cache.ts#L61-L63):

```typescript
export function isRealUserPrompt(prompt: CachedUserPrompt): boolean {
  return !prompt.promptType || prompt.promptType === 'user' || prompt.promptType === 'command';
}
```

---

## Content Item Types

`message.content` is a list. Each item has a `type` field.

### `text`

```json
{
  "type": "text",
  "text": "string content"
}
```

### `thinking`

Appears in **assistant** records when extended thinking is active. Contains the model's
internal reasoning before its response.

```json
{
  "type": "thinking",
  "thinking": "string — the model's reasoning"
}
```

SOURCE: [`core/src/agent-session-store.ts` lines 411–416](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L411-L416).

### `tool_use`

Appears in **assistant** records. Records a tool call made by the model.

```json
{
  "type": "tool_use",
  "id": "toolu_01ABC...",
  "name": "ToolName",
  "input": {}
}
```

`name` is the tool name — e.g., `Bash`, `Read`, `mcp__plugin_dh_sam__sam_ready`.

### `tool_result`

Appears in **user** records. Contains the response returned to the model.

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01ABC...",
  "is_error": null,
  "content": "string or list"
}
```

`content` is a string for most tools. For some MCP tools it is a list of objects.

---

## Pairing tool_use with tool_result

`tool_use.id` matches `tool_result.tool_use_id`. They appear in consecutive records:
- `tool_use` in an assistant record
- `tool_result` in the next user record

```python
# Extract all tool call / result pairs
pending = {}
for rec in records:
    msg = rec.get("message", {})
    content = msg.get("content", []) if isinstance(msg, dict) else []
    for item in content if isinstance(content, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_use":
            pending[item["id"]] = item["name"]
        elif item.get("type") == "tool_result" and item.get("tool_use_id") in pending:
            name = pending.pop(item["tool_use_id"])
            rc = item.get("content", "")
            size = len(rc) if isinstance(rc, str) else len(json.dumps(rc))
            yield name, size
```

---

## Computing Response Size

```python
content = tool_result_item.get("content", "")
size_chars = len(content) if isinstance(content, str) else len(json.dumps(content))
tokens_estimated = size_chars // 4  # rough 4-chars-per-token approximation
```

---

## Observed Response Sizes

From 500-file scan, `plugin_dh` MCP tools only (20 result records found):

| Tool | Calls | Avg chars | Max chars | Avg est. tokens |
|---|---|---|---|---|
| `mcp__plugin_dh_backlog__backlog_view` | 3 | 7,403 | 18,632 | 1,851 |
| `mcp__plugin_dh_backlog__backlog_list` | 1 | 13,355 | 13,355 | 3,339 |
| `mcp__plugin_dh_backlog__backlog_groom` | 15 | 247 | 247 | 62 |
| `mcp__plugin_dh_backlog__backlog_list_merged_prs` | 1 | 70 | 70 | 18 |

Other MCP tools observed in separate files:

| Tool | Result size |
|---|---|
| `mcp__context7__query-docs` | 5,685 chars (~1,421 tokens) |
| `mcp__context7__resolve-library-id` | 933 chars (~233 tokens) |

Note: SAM tools (`mcp__plugin_dh_sam__*`) appear in 823 files but were not sampled in this
initial scan. Sizes are expected to be large based on `sam_ready` returning full Task objects
(25+ fields). See backlog #1041 for progressive disclosure improvement plan.

---

## Team Sessions: Two Inspection Views

In a team session, both views are available in the logs:

**Team lead perspective** — the orchestrator's `.jsonl` contains:
- A `tool_use` record for each teammate spawn (via the `Task` tool)
- A `tool_result` record containing what that teammate returned

**Teammate perspective** — each teammate's `.jsonl` contains:
- Their full execution: thinking, tool calls, tool results, and final output

This means you can audit what prompt each teammate received and what it returned,
as well as what the teammate actually did to produce that result — independently.

### Task Spawn Record (in team-lead session)

```json
{
  "type": "tool_use",
  "id": "toolu_spawn_01",
  "name": "Task",
  "input": {
    "subagent_type": "Explore",
    "description": "Find all authentication middleware",
    "prompt": "Search for all middleware that validates JWT tokens..."
  }
}
```

### Teammate Result Record (in team-lead session)

The `tool_result` for a teammate spawn uses a `toolUseResult` wrapper — different from
the flat `content` field used by regular tool results:

```json
{
  "type": "tool_result",
  "toolUseResult": {
    "tool_use_id": "toolu_spawn_01",
    "content": "Found 3 middleware files: src/middleware/auth.ts (line 24)..."
  }
}
```

Regular tool results (Bash, Read, MCP tools) use flat `tool_use_id` and `content` fields.
Teammate results wrap these inside `toolUseResult`.

---

## Teams Configuration

Team configuration is stored in `~/.claude/teams/<team-name>/config.json` — a subdirectory
per team, not a flat JSON file.

```typescript
interface TeamMember {
  name: string;
  agentId: string;
  agentType?: string;
  role?: string;
  status?: string;
}

interface TeamConfig {
  name: string;
  members: TeamMember[];
  createdAt?: string;
}
```

SOURCE: [`core/src/agent-teams-service.ts` lines 11–23](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-teams-service.ts#L11-L23), [`lines 38–45`](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-teams-service.ts#L38-L45).

**Correction**: The previous version of this document stated the path as
`~/.claude/teams/<team-name>.json` (flat file). The actual path is
`~/.claude/teams/<team-name>/config.json` (directory + config.json). Verified against
`AgentTeamsService.getTeam()` which reads `path.join(this.teamsDir, teamName, 'config.json')`.

SOURCE: [`core/src/agent-teams-service.ts` line 39](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-teams-service.ts#L39).

---

## Plans — `~/.claude/plans/*.md`

When Claude enters plan mode (via the `EnterPlanMode`/`ExitPlanMode` tool calls), the plan is
written as a standalone markdown file. Files are named by plan title.

```text
~/.claude/plans/
├── implement-auth-middleware.md
├── refactor-session-cache.md
└── add-webhook-endpoints.md
```

Plans are plain markdown containing goals, steps, approach, and constraints. LM Assist renders
them with a visual plan view that links each step back to the session that created it.

---

## Tasks — `~/.claude/tasks/{list-id}/{task-id}.json`

Tasks are stored as individual JSON files, one per task, organized into directories by task
list ID (typically a session ID). Each task file contains:

```typescript
interface Task {
  id: string;
  subject: string;
  description: string;
  activeForm?: string;                                        // active display form of the task
  status: 'pending' | 'in_progress' | 'completed' | 'deleted';
  blocks: string[];                                           // task IDs this task blocks
  blockedBy: string[];                                        // task IDs that block this task
  owner?: string;                                             // agent or user who owns the task
  metadata?: Record<string, unknown>;
}
```

SOURCE: [`core/src/tasks-service.ts` lines 17–27](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/tasks-service.ts#L17-L27).

**Added fields vs prior documentation**: `activeForm` and `owner` were missing from the
previous version of this document. Verified against `TasksService.Task` interface.

`status` values: `pending`, `in_progress`, `completed`, `deleted`

`blocks` and `blockedBy` arrays create a dependency graph across tasks within a list.

LM Assist reads all task directories, aggregates across sessions and projects, and renders the
full set as a unified Kanban board showing what every Claude agent is currently working on
across the entire machine.

---

## LM Assist: Session Inspection UI

Raw JSONL files are not readable at scale — a team session with 8 agents, 400 messages, and
50 tool calls requires tooling to inspect. LM Assist is a web UI that reads all session files,
plans, tasks, and team configurations and renders:

- Per-agent execution timelines with tool calls expanded
- Team lead view: spawn calls with prompts sent to each teammate and results returned
- Teammate view: full execution trace for each specialist
- Kanban board: all tasks across all sessions and projects, with dependency graph
- Plan viewer: structured plan steps linked back to the creating session

**Data sources LM Assist reads:**

| Path | Content |
|---|---|
| `~/.claude/projects/**/*.jsonl` | Session transcripts (all agents) |
| `~/.claude/tasks/**/*.json` | Task state across all sessions |
| `~/.claude/plans/*.md` | Plan files from plan mode |
| `~/.claude/teams/*/config.json` | Team configurations (one subdirectory per team) |

SOURCE: [`core/src/agent-teams-service.ts` line 39](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-teams-service.ts#L39); [`core/src/tasks-service.ts` line 99](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/tasks-service.ts#L99);
[`core/src/session-cache.ts` line 408](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/session-cache.ts#L408).

---

## Subagent File Location

Subagent (Task tool spawned) sessions follow a naming convention separate from main sessions:

```text
# Top-level subagent (no parent session context):
~/.claude/projects/<project-key>/agent-<agent-id>.jsonl

# Nested subagent (spawned within a known parent session):
~/.claude/projects/<project-key>/<parent-session-id>/subagents/agent-<agent-id>.jsonl
```

The `agent-id` is a short hash, e.g., `a9afc2c`. The parent session stores a `SubagentInvocation`
record linking `toolUseId` → `agentId`.

SOURCE: [`core/src/agent-session-store.ts` lines 2424–2438](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L2424-L2438).

---

## Session Status Values

LM Assist computes a `status` field from session file state. These values do **not** appear
in the JSONL file; they are derived by LM Assist at parse time:

```typescript
type ClaudeSessionStatus =
  | 'running'    // File modified < 60 seconds ago
  | 'completed'  // Has a result record with success=true
  | 'error'      // Has a result record with errors
  | 'interrupted'// Session ended mid-conversation
  | 'idle'       // 1–10 minutes since last activity, no result
  | 'stale';     // > 10 minutes since last activity, no result
```

SOURCE: [`core/src/agent-session-store.ts` lines 87–107](https://github.com/langmartai/lm-assist/blob/104c96f89c8d51ed9d94d7de927142b28ff7df7c/core/src/agent-session-store.ts#L87-L107).

---

## What Is NOT in the Logs

- Per-tool-call token costs — usage is at turn level only
- Streaming events — logs contain completed messages, not stream chunks
- Hook execution records — hooks are not logged in session JSONL
- Tool execution timing — no duration field per tool call

---

## Using This Schema in Hooks

Hooks receive tool call data via stdin **before** it is written to the session log.
The `PostToolUse` hook `tool_response` field contains the same data that becomes
`tool_result.content` in the session log.

If you need to measure response sizes in a hook:

```javascript
const input = JSON.parse(process.stdin.read() || '{}');
const toolName = input.tool_name;           // same as tool_use.name in session log
const response = input.tool_response;       // same content as tool_result.content
const responseJson = JSON.stringify(response);
const bytes = Buffer.byteLength(responseJson, 'utf8');
```

However, if you only need historical analysis (not real-time reaction), reading the session
logs directly is simpler and requires no hook — the data is already there.
