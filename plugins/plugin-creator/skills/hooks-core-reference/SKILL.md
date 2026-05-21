---
name: hooks-core-reference
description: Hook system fundamentals — all events, configuration structure, matchers per event type, environment variables, execution behavior, security, and debugging. Use when creating hooks, understanding hook events, matchers, configuration locations, environment variables, or troubleshooting hook issues.
user-invocable: true
---

# Claude Code Hooks — Core Reference (May 2026)

Hooks execute custom commands, HTTP calls, MCP tool calls, LLM prompts, or agent verifiers in response to Claude Code events. Use for automation, validation, formatting, and security.

For JSON input/output schemas, activate `Skill(skill: "plugin-creator:hooks-io-api")`.
For working examples and patterns, activate `Skill(skill: "plugin-creator:hooks-patterns")`.

---

## All Hook Events

| Event | When Fired | Matcher Field | Common Uses |
| --- | --- | --- | --- |
| `PreToolUse` | Before tool execution | tool name | Validation, blocking |
| `PermissionRequest` | When user shown permission dialog | tool name | Auto-approval policies |
| `PermissionDenied` | Auto mode classifier denies a tool call | tool name | Log denials, allow retry |
| `PostToolUse` | After successful tool execution | tool name | Formatting, linting |
| `PostToolUseFailure` | After tool fails | tool name | Error handling |
| `PostToolBatch` | After all tools in a parallel batch resolve, before next model call | no matcher | Batch-level context injection |
| `Notification` | When Claude wants attention | notification type | Custom notifications |
| `UserPromptSubmit` | User submits prompt | no matcher | Input validation |
| `UserPromptExpansion` | Slash command expands into a prompt | command name | Block expansions, inject context |
| `Stop` | Claude finishes a turn | no matcher | Cleanup, final checks |
| `StopFailure` | Turn ends due to API error | error type | Logging, alerts |
| `SubagentStart` | When spawning a subagent | agent type name | Subagent initialization |
| `SubagentStop` | Subagent (Agent tool) completes — fires in parent session | agent type name | Result validation |
| `TeammateIdle` | Agent team teammate about to go idle | no matcher | Quality gates |
| `TaskCreated` | Task being created via TaskCreate | no matcher | Naming enforcement |
| `TaskCompleted` | Task being marked as completed | no matcher | Completion enforcement |
| `InstructionsLoaded` | CLAUDE.md or rules file loaded | load reason | Observability |
| `ConfigChange` | Configuration file changes during session | config source | Settings auditing |
| `WorktreeCreate` | Worktree being created | no matcher | Custom VCS integration |
| `WorktreeRemove` | Worktree being removed | no matcher | Custom VCS cleanup |
| `PreCompact` | Before context compaction | `manual` or `auto` | State backup |
| `PostCompact` | After context compaction completes | `manual` or `auto` | React to new state |
| `Elicitation` | MCP server requests user input mid-task | MCP server name | Programmatic responses |
| `ElicitationResult` | User responds to MCP elicitation | MCP server name | Observe/modify response |
| `Setup` | Repository setup/maintenance flags | `init` or `maintenance` | One-time operations |
| `CwdChanged` | Working directory changes during session | no matcher | Reload env, activate toolchains |
| `FileChanged` | Watched file changes on disk | literal filename pattern | Monitor .env, direnv integration |
| `SessionStart` | Session begins or resumes | `startup`, `resume`, `clear`, `compact` | Environment setup |
| `SessionEnd` | Session ends | exit reason | Cleanup, persistence |

### Stop vs SubagentStop — scope distinction

**`Stop`** fires in **every session** — the main orchestrator session and inside embedded subagents (Agent-tool spawned). When firing inside a subagent, the input includes `agent_id` and `agent_type` fields. Use these to guard hooks that should only run in the main session:

```javascript
// Only run in the main orchestrator, not inside embedded subagents
if (data.agent_id || data.agent_type) {
    process.stdout.write(JSON.stringify({}));
    process.exit(0);
}
```

**`SubagentStop`** fires only in the **parent session** when an Agent-tool call completes.

**Frontmatter exception**: `Stop` hooks defined in skill/agent frontmatter are automatically converted to `SubagentStop` for that component's lifecycle. This only applies to frontmatter-defined hooks, not plugin or settings hooks.

---

## Configuration

### Configuration Locations

| Location | Scope | Shareable |
| --- | --- | --- |
| `~/.claude/settings.json` | All your projects | No |
| `.claude/settings.json` | Single project | Yes, via git |
| `.claude/settings.local.json` | Single project | No, gitignored |
| Managed policy settings | Organization-wide | Yes, admin-controlled |
| Plugin `hooks/hooks.json` | When plugin is enabled | Yes, bundled with plugin |
| Skill or agent frontmatter | While component is active | Yes, in component file |

Enterprise administrators can use `allowManagedHooksOnly` to block user, project, and plugin hooks. Hooks from plugins force-enabled in managed `enabledPlugins` are exempt.

### Structure

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Hook Handler Fields

**Common fields** (all hook types):

| Field | Required | Description |
| --- | --- | --- |
| `type` | yes | `"command"`, `"http"`, `"mcp_tool"`, `"prompt"`, or `"agent"` |
| `if` | no | Permission rule syntax to filter when this handler spawns (e.g. `"Bash(git *)"`, `"Edit(*.ts)"`). Only evaluated on tool events. |
| `timeout` | no | **Seconds** before canceling. Defaults: 600 for `command`/`http`/`mcp_tool`; 30 for `prompt`; 60 for `agent`. `UserPromptSubmit` lowers command/http/mcp_tool default to 30. |
| `statusMessage` | no | Custom spinner message displayed while hook runs |
| `once` | no | If `true`, runs once per session then removed. Only honored in skill frontmatter. |

**Command hook fields** (in addition to common):

| Field | Description |
| --- | --- |
| `command` | Shell command string (shell form) or executable path (exec form when `args` is set) |
| `args` | Argument list. When present, `command` is the executable; spawned directly with no shell |
| `async` | If `true`, runs in background without blocking Claude |
| `asyncRewake` | If `true`, runs in background and wakes Claude when it exits with code 2 |
| `shell` | Shell to use: `"bash"` (default) or `"powershell"` (Windows only) |

**HTTP hook fields**:

| Field | Description |
| --- | --- |
| `url` | URL to POST event data to |
| `headers` | Key-value pairs. Values support `$VAR_NAME` interpolation |
| `allowedEnvVars` | Which env vars may be interpolated into headers |

**Prompt/agent hook fields**:

| Field | Description |
| --- | --- |
| `prompt` | Prompt text. Use `$ARGUMENTS` as placeholder for hook input JSON |
| `model` | Model override. Defaults to a fast model |

---

## Event-Specific Matchers

### PreToolUse / PermissionRequest / PostToolUse / PostToolUseFailure / PermissionDenied

Matched against `tool_name`. Matcher rules:

- Plain name: `Write` matches only Write tool
- Pipe list: `Edit|Write` matches either
- Regex (contains non-alphanumeric chars): `^Notebook` or `mcp__memory__.*`
- `mcp__<server>__.*` matches all tools from a server (`.*` required — bare `mcp__server` is exact match, finds nothing)

| Matcher | Description |
| --- | --- |
| `Agent` | Subagent operations |
| `Bash` | Shell commands |
| `Glob` | File pattern matching |
| `Grep` | Content search |
| `Read` | File reading |
| `Edit` | File editing |
| `Write` | File writing |
| `WebFetch` | Web fetching |
| `WebSearch` | Web search |
| `mcp__<server>__.*` | All tools from MCP server |

### SubagentStart / SubagentStop

Matched against `agent_type`. For custom subagents, `agent_type` is the **`name` field from the agent's frontmatter**, not the filename.

| Matcher value | Fires for |
| --- | --- |
| `general-purpose` | Built-in general-purpose agent |
| `Explore` | Built-in Explore agent |
| `Plan` | Built-in Plan agent |
| `^my-agent-name$` | Custom agent with `name: my-agent-name` in frontmatter |
| (regex supported) | `^rewrite-room-` matches all agents starting with that prefix |

### SessionStart

| Matcher | When |
| --- | --- |
| `startup` | New session started |
| `resume` | `--resume`, `--continue`, or `/resume` |
| `clear` | `/clear` command |
| `compact` | Auto or manual compact |

### SessionEnd

| Matcher | When |
| --- | --- |
| `clear` | Session cleared with `/clear` |
| `resume` | Session switched via interactive `/resume` |
| `logout` | User logged out |
| `prompt_input_exit` | User exited while prompt input was visible |
| `bypass_permissions_disabled` | Bypass permissions mode was disabled |
| `other` | Other exit reasons |

### Notification

| Matcher | Fires when |
| --- | --- |
| `permission_prompt` | Permission requests from Claude |
| `idle_prompt` | Claude waiting for input |
| `auth_success` | Authentication success |
| `elicitation_dialog` | MCP tool elicitation dialog |
| `elicitation_complete` | MCP elicitation submitted or dismissed |
| `elicitation_response` | MCP elicitation response sent to server |

### InstructionsLoaded

| Matcher | Fires when |
| --- | --- |
| `session_start` | File loaded at session start |
| `nested_traversal` | File loaded when Claude accesses a subdirectory |
| `path_glob_match` | File loaded via `paths:` frontmatter match |
| `include` | File loaded via `include` directive |
| `compact` | File re-loaded after compaction |

### ConfigChange

| Matcher | When |
| --- | --- |
| `user_settings` | `~/.claude/settings.json` changes |
| `project_settings` | `.claude/settings.json` changes |
| `local_settings` | `.claude/settings.local.json` changes |
| `policy_settings` | Managed policy settings (non-blockable) |
| `skills` | Skill file changes |

### PreCompact / PostCompact

| Matcher | Trigger |
| --- | --- |
| `manual` | `/compact` command |
| `auto` | Auto-compact when context window fills |

### Setup

| Matcher | Trigger |
| --- | --- |
| `init` | `--init` or `--init-only` flags |
| `maintenance` | `--maintenance` flag |

### StopFailure

| Matcher | Error type |
| --- | --- |
| `rate_limit` | Rate limit |
| `authentication_failed` | Auth failure |
| `billing_error` | Billing error |
| `server_error` | API server error |
| `max_output_tokens` | Output token limit |
| `unknown` | Unknown error |

### Elicitation / ElicitationResult

Matched against the MCP server name.

### UserPromptExpansion

Matched against `command_name` (the slash command name).

### FileChanged

Matcher value is split on `|` and registered as literal filenames to watch (e.g. `.envrc|.env`). Same value also filters which hook groups run when a file changes.

### No-matcher events

`UserPromptSubmit`, `PostToolBatch`, `Stop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `CwdChanged` — matchers are silently ignored on these events. They always fire on every occurrence.

---

## Path Placeholders

Use in `command` and `args` fields to reference scripts at stable paths:

| Placeholder | Value |
| --- | --- |
| `${CLAUDE_PROJECT_DIR}` | Project root (where Claude Code was started) |
| `${CLAUDE_PLUGIN_ROOT}` | Plugin installation directory. Changes on plugin update |
| `${CLAUDE_PLUGIN_DATA}` | Plugin persistent data directory (`~/.claude/plugins/data/{id}/`). Survives plugin updates |

**Exec form** (when `args` is set): Claude Code spawns the executable directly. Each `args` element is one argument with no shell tokenization. Use for paths that may contain spaces.

**Shell form** (when `args` is absent): command string passed to `sh -c`. Wrap placeholders in double-quotes.

```json
{
  "type": "command",
  "command": "node",
  "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/my-hook.cjs"]
}
```

---

## Environment Variables

| Variable | Description | Available In |
| --- | --- | --- |
| `CLAUDE_PROJECT_DIR` | Project root (absolute path) | All hooks |
| `CLAUDE_CODE_REMOTE` | `"true"` if remote web, absent if local CLI | All hooks |
| `CLAUDE_ENV_FILE` | Path for persisting env vars into Bash commands | SessionStart, Setup, CwdChanged, FileChanged |
| `CLAUDE_PLUGIN_ROOT` | Plugin directory (absolute) | Plugin hooks |
| `CLAUDE_PLUGIN_DATA` | Plugin persistent data directory | Plugin hooks |
| `CLAUDE_EFFORT` | Active effort level (`low`/`medium`/`high`/`xhigh`/`max`) | Tool-use context events |

### CLAUDE_ENV_FILE — Persisting Environment Variables

Variables written to `CLAUDE_ENV_FILE` are sourced before each Bash command. Append (`>>`) to preserve variables set by other hooks.

```bash
#!/bin/bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
  echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
fi
```

---

## Execution Details

| Aspect | Behavior |
| --- | --- |
| **Parallelism** | All matching hooks in a group run in parallel |
| **Deduplication** | Identical commands/URLs deduplicated automatically |
| **Environment** | Runs in cwd with Claude Code's environment |
| **Terminal** | No controlling terminal (macOS/Linux v2.1.139+). Cannot open `/dev/tty`. Use `terminalSequence` JSON output for bell/notification |
| **Block cap** | Stop/SubagentStop hooks blocked 8 consecutive times triggers override — subagent is forced to stop |

---

## Security Considerations

Command hooks run with your system user's full permissions and can modify, delete, or access any files your account can access.

**Best practices:**
1. Validate and sanitize inputs — never trust stdin data blindly
2. Quote shell variables — use `"$VAR"` not `$VAR`
3. Block path traversal — check for `..` in file paths
4. Use `${CLAUDE_PROJECT_DIR}` for absolute paths — never relative
5. Skip sensitive files — avoid `.env`, `.git/`, keys, etc.

---

## Debugging

```bash
# Write debug log to file
claude --debug-file /tmp/claude.log

# Enable verbose mode mid-session
ctrl+O
```

Debug output shows which hooks matched, exit codes, and full stdout/stderr.

For more granular matcher details: `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose`.

### Troubleshooting

| Problem | Cause | Fix |
| --- | --- | --- |
| Hook not running | Wrong matcher pattern | Check case-sensitivity; run `/hooks` to confirm registration |
| Command not found | Relative path in command | Use `${CLAUDE_PROJECT_DIR}` or exec form with `args` |
| JSON not processed | Non-zero exit code | Exit 0 for JSON output; use exit 2 only for blocking |
| Hook times out | Script too slow | Optimize or increase `timeout` field |
| Stop hook loops | Missing `stop_hook_active` check | Check `stop_hook_active` in Stop input; exit 0 when true |
| Stop hook runs inside subagents unexpectedly | Missing `agent_id` guard | Check `data.agent_id` in Stop hooks; exit 0 when present |
| JSON parse error | Shell profile printing text | Wrap profile `echo` in `if [[ $- == *i* ]]` guard |
| Plugin hook not loading | Invalid `hooks.json` | Run `claude plugin validate .` |

### Test Commands Manually

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"npm test"}}' | ./your-hook.sh
```

---

## Sources

- [Hooks Reference](https://docs.anthropic.com/en/docs/claude-code/hooks.md) (accessed 2026-05-21)
- [Hooks Guide](https://docs.anthropic.com/en/docs/claude-code/hooks-guide.md) (accessed 2026-05-21)
- [Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings.md)
- [Plugin Components Reference](https://docs.anthropic.com/en/docs/claude-code/plugins-reference.md#hooks)
