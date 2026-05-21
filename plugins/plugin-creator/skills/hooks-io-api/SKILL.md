---
name: hooks-io-api
description: Hook JSON input/output API reference — what data hooks receive via stdin and what JSON they can return to control Claude Code behavior. Use when writing hook scripts, checking exit code behavior, building JSON output for PreToolUse permissions, or understanding event-specific input schemas.
user-invocable: true
---

# Claude Code Hooks — I/O API Reference (May 2026)

JSON schemas for hook stdin input and stdout output per event. For hook system fundamentals, activate `Skill(skill: "plugin-creator:hooks-core-reference")`. For working examples, activate `Skill(skill: "plugin-creator:hooks-patterns")`.

---

## Hook Input (JSON via stdin)

### Common Fields (All Events)

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse"
}
```

**`permission_mode` values**: `"default"`, `"plan"`, `"acceptEdits"`, `"auto"`, `"dontAsk"`, `"bypassPermissions"`

**When running with `--agent` or inside a subagent**, two additional fields are included:

| Field | Description |
| --- | --- |
| `agent_id` | Unique identifier for the subagent. Present only when the hook fires inside a subagent call |
| `agent_type` | Agent name (e.g. `"Explore"` or `"security-reviewer"`). For custom subagents, this is the `name` field from the agent's frontmatter, not the filename |

### PreToolUse Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "psql -c 'SELECT * FROM users'",
    "description": "Query the users table",
    "timeout": 120000
  },
  "tool_use_id": "toolu_01ABC123"
}
```

**Tool-specific `tool_input` fields:**

| Tool | Fields |
| --- | --- |
| `Bash` | `command`, `description`, `timeout`, `run_in_background` |
| `Write` | `file_path`, `content` |
| `Edit` | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Read` | `file_path`, `offset`, `limit` |
| `Glob` | `pattern`, `path` |
| `Grep` | `pattern`, `path`, `glob`, `output_mode`, `-i`, `multiline` |
| `WebFetch` | `url`, `prompt` |
| `WebSearch` | `query`, `allowed_domains`, `blocked_domains` |
| `Agent` | `prompt`, `description`, `subagent_type`, `model` |

### PostToolUse Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  },
  "tool_response": {
    "filePath": "/path/to/file.txt",
    "success": true
  },
  "tool_use_id": "toolu_01ABC123",
  "duration_ms": 12
}
```

`duration_ms`: tool execution time in milliseconds, excluding permission prompts and PreToolUse hooks.

### PostToolUseFailure Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PostToolUseFailure",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "toolu_01ABC123",
  "error": "Command exited with non-zero status code 1",
  "is_interrupt": false,
  "duration_ms": 4187
}
```

### PostToolBatch Input

Fires once after every tool call in a parallel batch resolves, before the next model call. No matcher support.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PostToolBatch",
  "tool_calls": [
    {
      "tool_name": "Read",
      "tool_input": { "file_path": "/path/to/file.py" },
      "tool_use_id": "toolu_01...",
      "tool_response": "     1\tfile contents..."
    }
  ]
}
```

Note: `tool_response` in PostToolBatch is the serialized `tool_result` content the model sees — different from PostToolUse's structured `Output` object.

### PermissionRequest Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PermissionRequest",
  "tool_name": "Bash",
  "tool_input": {
    "command": "rm -rf node_modules"
  },
  "permission_suggestions": [
    {
      "type": "addRules",
      "rules": [{ "toolName": "Bash", "ruleContent": "rm -rf node_modules" }],
      "behavior": "allow",
      "destination": "localSettings"
    }
  ]
}
```

### PermissionDenied Input

Fires when the auto mode classifier denies a tool call. Does not fire on manual denials or PreToolUse blocks.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "auto",
  "hook_event_name": "PermissionDenied",
  "tool_name": "Bash",
  "tool_input": { "command": "rm -rf /tmp/build" },
  "tool_use_id": "toolu_01ABC123",
  "reason": "Auto mode denied: command targets a path outside the project"
}
```

### Notification Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "Notification",
  "message": "Claude needs your permission to use Bash",
  "title": "Permission needed",
  "notification_type": "permission_prompt"
}
```

**`notification_type` values**: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_complete`, `elicitation_response`

### UserPromptSubmit Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Write a function to calculate factorial"
}
```

### UserPromptExpansion Input

Fires when a user-typed slash command expands into a prompt, before it reaches Claude.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "UserPromptExpansion",
  "expansion_type": "slash_command",
  "command_name": "example-skill",
  "command_args": "arg1 arg2",
  "command_source": "plugin",
  "prompt": "/example-skill arg1 arg2"
}
```

Matcher filters on `command_name`. `expansion_type` is `slash_command` for skills/commands or `mcp_prompt` for MCP server prompts.

### Stop Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "stop_hook_active": true,
  "last_assistant_message": "I've completed the refactoring. Here's a summary...",
  "background_tasks": [
    {
      "id": "task-001",
      "type": "shell",
      "status": "running",
      "description": "tail logs",
      "command": "tail -f /var/log/syslog"
    }
  ],
  "session_crons": [
    {
      "id": "cron-001",
      "schedule": "0 9 * * 1-5",
      "recurring": true,
      "prompt": "check the build"
    }
  ]
}
```

- `stop_hook_active`: `true` when Claude is already continuing due to a stop hook — check to prevent infinite loops. Claude Code overrides after 8 consecutive blocks.
- `last_assistant_message`: text content of Claude's final response (no transcript parsing needed)
- `background_tasks`: in-flight background tasks (v2.1.145+). Each entry: `id`, `type` (`shell`/`subagent`/`monitor`/`workflow`/`teammate`/etc.), `status`, `description`, plus type-specific fields (`command`, `agent_type`, `server`, `tool`, `name`)
- `session_crons`: scheduled session wakeups (v2.1.145+). Each entry: `id`, `schedule`, `recurring`, `prompt`

### StopFailure Input

Fires instead of Stop when the turn ends due to an API error. Output and exit code are ignored.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "StopFailure",
  "error": "rate_limit",
  "error_details": "429 Too Many Requests",
  "last_assistant_message": "API Error: Rate limit reached"
}
```

**`error` values**: `rate_limit`, `authentication_failed`, `oauth_org_not_allowed`, `billing_error`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `unknown`

### SubagentStart Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "SubagentStart",
  "agent_id": "agent-abc123",
  "agent_type": "Explore"
}
```

- `agent_type`: built-in agent names (`"general-purpose"`, `"Explore"`, `"Plan"`) or, for custom agents, the `name` field from the agent's frontmatter (not the filename). Matcher filters on this value.

### SubagentStop Input

```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../abc123.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "SubagentStop",
  "stop_hook_active": false,
  "agent_id": "def456",
  "agent_type": "rewrite-room-auditor",
  "agent_transcript_path": "~/.claude/projects/.../abc123/subagents/agent-def456.jsonl",
  "last_assistant_message": "Analysis complete. Found 3 potential issues...",
  "background_tasks": [],
  "session_crons": []
}
```

- `agent_type`: the `name` field from the agent's frontmatter (not the filename). **Matcher filters on this value** — same matcher values as SubagentStart.
- `agent_transcript_path`: path to the subagent's own transcript in nested `subagents/` folder
- `last_assistant_message`: text content of the subagent's final response (no transcript parsing needed)
- `background_tasks`, `session_crons`: scoped to the **parent** session, not the subagent (v2.1.145+)

### TaskCreated Input

Fires when a task is being created via `TaskCreate`. No matcher support.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "TaskCreated",
  "task_id": "task-001",
  "task_subject": "Implement user authentication",
  "task_description": "Add login and signup endpoints",
  "teammate_name": "implementer",
  "team_name": "my-project"
}
```

### TaskCompleted Input

Fires when a task is being marked as completed. No matcher support.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "TaskCompleted",
  "task_id": "task-001",
  "task_subject": "Implement user authentication",
  "task_description": "Add login and signup endpoints",
  "teammate_name": "implementer",
  "team_name": "my-project"
}
```

### TeammateIdle Input

Fires when an agent team teammate is about to go idle. No matcher support.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "TeammateIdle",
  "teammate_name": "researcher",
  "team_name": "my-project"
}
```

### ConfigChange Input

Fires when a configuration file changes during a session. Matcher filters on `source`.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "ConfigChange",
  "source": "project_settings",
  "file_path": "/path/to/.claude/settings.json"
}
```

**`source` / matcher values**: `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`

### CwdChanged Input

Fires when working directory changes. No matcher support. Has access to `CLAUDE_ENV_FILE`.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/new/dir",
  "hook_event_name": "CwdChanged",
  "old_cwd": "/path/to/project",
  "new_cwd": "/path/to/project/src"
}
```

### FileChanged Input

Fires when a watched file changes. Matcher serves dual role: builds the watch list (literal filenames split on `|`) AND filters which hooks run.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "FileChanged",
  "file_path": "/path/to/project/.envrc",
  "event": "change"
}
```

**`event` values**: `change` (modified), `add` (created), `unlink` (deleted)

### WorktreeCreate Input

Fires when a worktree is being created. Replaces default `git worktree` behavior when configured.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "WorktreeCreate",
  "name": "feature-auth"
}
```

### WorktreeRemove Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "WorktreeRemove",
  "worktree_path": "/path/to/.claude/worktrees/feature-auth"
}
```

### PreCompact Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "PreCompact",
  "trigger": "manual",
  "custom_instructions": ""
}
```

**`trigger` / matcher values**: `manual`, `auto`

### PostCompact Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "PostCompact",
  "trigger": "manual",
  "compact_summary": "Summary of the compacted conversation..."
}
```

### InstructionsLoaded Input

Fires when a CLAUDE.md or `.claude/rules/*.md` file is loaded. Matcher filters on `load_reason`.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "InstructionsLoaded",
  "file_path": "/path/to/project/CLAUDE.md",
  "memory_type": "Project",
  "load_reason": "session_start"
}
```

**`load_reason` / matcher values**: `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`

### Elicitation Input

Fires when an MCP server requests user input. Matcher filters on MCP server name.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "Elicitation",
  "mcp_server_name": "my-mcp-server",
  "message": "Please provide your credentials",
  "mode": "form",
  "requested_schema": {
    "type": "object",
    "properties": {
      "username": { "type": "string", "title": "Username" }
    }
  }
}
```

### ElicitationResult Input

Fires after a user responds to an MCP elicitation. Matcher filters on MCP server name.

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "ElicitationResult",
  "mcp_server_name": "my-mcp-server",
  "action": "accept",
  "content": { "username": "alice" },
  "mode": "form",
  "elicitation_id": "elicit-123"
}
```

### Setup Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "Setup",
  "trigger": "init"
}
```

- `trigger`: `"init"` (from `--init` or `--init-only`) or `"maintenance"` (from `--maintenance`)
- Has access to `CLAUDE_ENV_FILE` for persisting environment variables

### SessionStart Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "SessionStart",
  "source": "startup",
  "model": "claude-sonnet-4-6"
}
```

- `source` / matcher values: `startup`, `resume`, `clear`, `compact`
- `model`: model identifier
- `agent_type`: present when Claude Code started with `claude --agent <name>`
- Has access to `CLAUDE_ENV_FILE` for persisting environment variables

### SessionEnd Input

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "SessionEnd",
  "reason": "other"
}
```

**`reason` / matcher values**: `clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`

---

## Hook Output

### Exit Codes

| Code | Behavior |
| --- | --- |
| 0 | Success. stdout processed (JSON or plain text) |
| 2 | Blocking error. stderr fed back to Claude (or shown to user, event-dependent) |
| Other | Non-blocking error. stderr shown in verbose mode (Ctrl+O). Execution continues |

**Important**: JSON output is only processed on exit 0. Exit code 2 uses stderr only.

**Note**: Exit code 1 is non-blocking for most events — execution continues. Only exit code 2 blocks. Exception: `WorktreeCreate` — any non-zero exit code fails worktree creation.

### Exit Code 2 Behavior Per Event

| Event | Can Block? | Exit Code 2 Effect |
| --- | --- | --- |
| `PreToolUse` | Yes | Blocks tool call, shows stderr to Claude |
| `PermissionRequest` | Yes | Denies permission, shows stderr to Claude |
| `UserPromptSubmit` | Yes | Blocks prompt, erases it, shows stderr to user |
| `UserPromptExpansion` | Yes | Blocks the expansion |
| `Stop` | Yes | Blocks stoppage, shows stderr to Claude |
| `SubagentStop` | Yes | Blocks stoppage, shows stderr to Claude subagent |
| `TeammateIdle` | Yes | Prevents teammate going idle, shows stderr as feedback |
| `TaskCreated` | Yes | Rolls back task creation, shows stderr as feedback |
| `TaskCompleted` | Yes | Prevents task completion, shows stderr as feedback |
| `ConfigChange` | Yes | Blocks config change (except `policy_settings`) |
| `PreCompact` | Yes | Blocks compaction |
| `PostToolBatch` | Yes | Stops agentic loop before next model call |
| `Elicitation` | Yes | Denies the elicitation |
| `ElicitationResult` | Yes | Blocks the response (action becomes decline) |
| `WorktreeCreate` | Yes | Any non-zero exit fails worktree creation |
| `PostToolUse` | No | Shows stderr to Claude (tool already ran) |
| `PostToolUseFailure` | No | Shows stderr to Claude (tool already failed) |
| `PermissionDenied` | No | Exit code ignored. Use JSON `hookSpecificOutput.retry: true` to allow retry |
| `Notification` | No | Shows stderr to user only |
| `SubagentStart` | No | Shows stderr to user only |
| `StopFailure` | No | Output and exit code ignored |
| `PreCompact` | Yes | Blocks compaction, stderr shown to user |
| `PostCompact` | No | Shows stderr to user only |
| `Setup` | No | Shows stderr to user only |
| `SessionStart` | No | Shows stderr to user only |
| `SessionEnd` | No | Shows stderr to user only |
| `CwdChanged` | No | Shows stderr to user only |
| `FileChanged` | No | Shows stderr to user only |
| `WorktreeRemove` | No | Failures logged in debug mode only |
| `InstructionsLoaded` | No | Exit code ignored |

---

## JSON Output Control

**Important**: JSON output only processed with exit code 0. Exit code 2 uses stderr only.

### Common JSON Fields (All Events)

```json
{
  "continue": true,
  "stopReason": "Message shown when continue is false",
  "suppressOutput": false,
  "systemMessage": "Optional warning message shown to user",
  "terminalSequence": "]777;notify;Claude Code;Needs attention"
}
```

| Field | Type | Effect |
| --- | --- | --- |
| `continue` | boolean | `false` stops Claude entirely (takes precedence over all other fields) |
| `stopReason` | string | Shown to user when `continue` is false |
| `suppressOutput` | boolean | Hide stdout from transcript mode |
| `systemMessage` | string | Warning message shown to user |
| `terminalSequence` | string | Terminal escape sequence emitted by Claude Code on your behalf. Restricted to OSC `0`/`1`/`2`/`9`/`99`/`777` and BEL. Use instead of writing to `/dev/tty` (hooks run without a controlling terminal) |

### PreToolUse JSON Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Auto-approved documentation file",
    "updatedInput": {
      "field_to_modify": "new value"
    },
    "additionalContext": "Current environment: production. Proceed with caution."
  }
}
```

| Field | Values | Effect |
| --- | --- | --- |
| `permissionDecision` | `allow`, `deny`, `ask`, `defer` | Controls tool execution. `defer` only valid in non-interactive `-p` mode — pauses for resume |
| `permissionDecisionReason` | string | Shown to user (allow/ask) or Claude (deny). Ignored for `defer` |
| `updatedInput` | object | Modifies tool input before execution. Include all fields, not just changed ones |
| `additionalContext` | string | Added to Claude's context alongside the tool result |

**Precedence when multiple hooks return different decisions**: `deny` > `defer` > `ask` > `allow`

**Note**: Top-level `decision` and `reason` fields are deprecated for PreToolUse. Use `hookSpecificOutput.permissionDecision` and `hookSpecificOutput.permissionDecisionReason`. Deprecated `"approve"` maps to `"allow"`, `"block"` maps to `"deny"`.

### PermissionRequest JSON Output

Allow with modified input:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow",
      "updatedInput": { "command": "npm run lint" }
    }
  }
}
```

Deny with message:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "deny",
      "message": "Command not allowed by policy",
      "interrupt": true
    }
  }
}
```

### PermissionDenied JSON Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionDenied",
    "retry": true
  }
}
```

`retry: true` tells the model it may retry the denied tool call. Only command hooks can return this — prompt/agent hook output is discarded for this event.

### PostToolUse JSON Output

```json
{
  "decision": "block",
  "reason": "Explanation for decision",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Additional information for Claude",
    "updatedToolOutput": {
      "stdout": "[redacted]",
      "stderr": "",
      "interrupted": false,
      "isImage": false
    }
  }
}
```

- `decision: "block"` adds `reason` next to the tool result as feedback to Claude
- `updatedToolOutput`: replaces what Claude sees (tool has already run — files written, commands executed are not reversed). Value must match the tool's output shape exactly. For Bash: `{ stdout, stderr, interrupted, isImage }`
- `updatedMCPToolOutput`: same as `updatedToolOutput` but for MCP tools only

### UserPromptSubmit JSON Output

```json
{
  "decision": "block",
  "reason": "Prompt contains sensitive data",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "My additional context here",
    "sessionTitle": "My session title"
  }
}
```

- `decision: "block"` prevents prompt processing, erases prompt from context
- `reason` shown to user but not added to context
- `sessionTitle`: sets the session title automatically based on prompt content
- Plain text stdout also adds context (no JSON needed for simple use cases)

### UserPromptExpansion JSON Output

```json
{
  "decision": "block",
  "reason": "This slash command is not available",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptExpansion",
    "additionalContext": "Additional context for this expansion"
  }
}
```

### Stop / SubagentStop JSON Output

```json
{
  "decision": "block",
  "reason": "Must be provided when Claude is blocked from stopping"
}
```

- `decision: "block"` prevents stopping. `reason` is required and becomes Claude's next instruction
- SubagentStop does not support `additionalContext`. To inject context into the parent session after a subagent returns, use a `PostToolUse` hook on the `Agent` tool instead

### TeammateIdle / TaskCreated / TaskCompleted JSON Output

Two control options:

- **Exit code 2**: feeds stderr back to the model as feedback; action is blocked
- **JSON `{"continue": false, "stopReason": "..."}`**: stops the teammate entirely

### PostToolBatch JSON Output

```json
{
  "decision": "block",
  "reason": "Reason to stop before next model call",
  "hookSpecificOutput": {
    "hookEventName": "PostToolBatch",
    "additionalContext": "Context injected once before the next model call"
  }
}
```

### ConfigChange JSON Output

```json
{
  "decision": "block",
  "reason": "Configuration changes require admin approval"
}
```

`policy_settings` changes cannot be blocked — hooks fire but blocking decisions are ignored.

### WorktreeCreate JSON Output

Hook replaces default `git worktree` behavior. Must return the absolute path to the created worktree directory:

- **Command hooks**: print path on stdout
- **HTTP hooks**: return `{ "hookSpecificOutput": { "hookEventName": "WorktreeCreate", "worktreePath": "/absolute/path" } }`

### Elicitation JSON Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "Elicitation",
    "action": "accept",
    "content": { "username": "alice" }
  }
}
```

**`action` values**: `accept`, `decline`, `cancel`

### ElicitationResult JSON Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "ElicitationResult",
    "action": "decline",
    "content": {}
  }
}
```

### PreCompact JSON Output

```json
{
  "decision": "block",
  "reason": "Cannot compact — CI check in progress"
}
```

### Setup / SessionStart JSON Output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Project context loaded successfully",
    "initialUserMessage": "Check the build status",
    "watchPaths": ["/path/to/watch"]
  }
}
```

- `additionalContext`: added to Claude's context at the start of the conversation
- `initialUserMessage`: SessionStart only — used as the first user message in non-interactive (`-p`) mode
- `watchPaths`: SessionStart only — array of absolute paths to watch for `FileChanged` events
- Multiple hooks' `additionalContext` values are concatenated

---

## Events With No Decision Control

These events support side-effects only — logging, notifications, cleanup. No blocking or decision output is processed:

`StopFailure`, `PostCompact`, `Notification`, `WorktreeRemove`, `SessionEnd`, `InstructionsLoaded`, `CwdChanged`, `FileChanged`

---

## Sources

- [Hooks Reference](https://docs.anthropic.com/en/docs/claude-code/hooks.md) (accessed 2026-05-21)
- [Hooks Guide](https://docs.anthropic.com/en/docs/claude-code/hooks-guide.md)
- [Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings.md)
- [Plugin Components Reference](https://docs.anthropic.com/en/docs/claude-code/plugins-reference.md#hooks)
