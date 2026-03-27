---
name: hooks-core-reference
description: Hook system fundamentals — all events, configuration structure, matchers per event type, environment variables, execution behavior, security, and debugging. Use when creating hooks, understanding hook events, matchers, configuration locations, environment variables, or troubleshooting hook issues.
user-invocable: true
---

# Claude Code Hooks — Core Reference (January 2026)

Hooks execute custom commands or prompts in response to Claude Code events. Use for automation, validation, formatting, and security.

For JSON input/output schemas, activate `Skill(skill: "plugin-creator:hooks-io-api")`.
For working examples and patterns, activate `Skill(skill: "plugin-creator:hooks-patterns")`.

---

## All Hook Events

| Event                | When Fired                                                   | Matcher Applies                        | Common Uses             |
| -------------------- | ------------------------------------------------------------ | -------------------------------------- | ----------------------- |
| `PreToolUse`         | Before tool execution                                        | Yes — tool name                        | Validation, blocking    |
| `PermissionRequest`  | When user shown permission dialog                            | Yes — tool name                        | Auto-approval policies  |
| `PostToolUse`        | After successful tool execution                              | Yes — tool name                        | Formatting, linting     |
| `PostToolUseFailure` | After tool fails                                             | Yes — tool name                        | Error handling          |
| `Notification`       | When Claude wants attention                                  | Yes — notification type                | Custom notifications    |
| `UserPromptSubmit`   | User submits prompt                                          | No                                     | Input validation        |
| `Stop`               | Claude finishes response                                     | No                                     | Cleanup, final checks   |
| `SubagentStart`      | When spawning a subagent                                     | Yes — agent type name                  | Subagent initialization |
| `SubagentStop`       | Subagent (Agent tool) completes                              | Yes — agent type name                  | Result validation       |
| `TeammateIdle`       | Agent team teammate about to go idle                         | No                                     | Quality gates           |
| `TaskCompleted`      | Task being marked as completed                               | No                                     | Completion enforcement  |
| `InstructionsLoaded` | CLAUDE.md or rules file loaded into context                  | No                                     | Observability           |
| `ConfigChange`       | Configuration file changes during session                    | Yes — config source                    | Settings auditing       |
| `WorktreeCreate`     | Worktree being created (`--worktree` or `isolation: worktree`) | No                                   | Custom VCS integration  |
| `WorktreeRemove`     | Worktree being removed at session exit or subagent finish    | No                                     | Custom VCS cleanup      |
| `PreCompact`         | Before context compaction                                    | Yes — `manual` or `auto`               | State backup            |
| `PostCompact`        | After context compaction completes                           | Yes — `manual` or `auto`               | React to new state      |
| `Elicitation`        | MCP server requests user input mid-task                      | Yes — MCP server name                  | Programmatic responses  |
| `ElicitationResult`  | User responds to MCP elicitation                             | Yes — MCP server name                  | Observe/modify response |
| `Setup`              | Repository setup/maintenance                                 | Yes — `init` or `maintenance`          | One-time operations     |
| `SessionStart`       | Session begins or resumes                                    | Yes — `startup`, `resume`, etc.        | Environment setup       |
| `SessionEnd`         | Session ends                                                 | Yes — exit reason                      | Cleanup, persistence    |

> **Note:** The Agent tool was renamed from Task in Claude Code v2.1.63. Use `Agent` as the matcher name for tool-based hooks targeting subagent operations.

For a visual overview of the full event sequence, see the `../hooks-guide/references/hooks-lifecycle.png`.

---

## Configuration

### Configuration Locations (Precedence highest to lowest)

1. **Managed** - `managed-settings.json` (enterprise)
2. **Local** - `.claude/settings.local.json` (gitignored)
3. **Project** - `.claude/settings.json` (shared via git)
4. **User** - `~/.claude/settings.json` (personal)
5. **Plugin** - `hooks/hooks.json` or frontmatter
6. **Capability** - Skill/Command/Agent frontmatter

**Note**: Enterprise administrators can use `allowManagedHooksOnly` to block user, project, and plugin hooks.

### Structure

Hooks are organized by matchers, where each matcher can have multiple hooks:

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here"
          }
        ]
      }
    ]
  }
}
```

**Fields:**

- **matcher**: Pattern to match tool names, case-sensitive (for `PreToolUse`, `PermissionRequest`, `PostToolUse`); matches agent type name for `SubagentStart`/`SubagentStop`; matches exit reason for `SessionEnd`; matches config source for `ConfigChange`; matches MCP server name for `Elicitation`/`ElicitationResult`
  - Simple strings match exactly: `Write` matches only the Write tool
  - Supports regex: `Edit|Write` or `Notebook.*`
  - Use `*` to match all tools. Also accepts empty string (`""`) or omit `matcher`
- **hooks**: Array of hooks to execute when pattern matches
  - `type`: `"command"` for bash commands, `"prompt"` for LLM evaluation, `"http"` for HTTP POST requests, or `"agent"` for agentic verifiers with tool access
  - `command`: (For `type: "command"`) The bash command to execute
  - `url`: (For `type: "http"`) The URL to POST the hook input to
  - `prompt`: (For `type: "prompt"` or `type: "agent"`) The prompt to send to the model
  - `timeout`: (Optional) Seconds before canceling (default: 600 for commands, 30 for prompts, 60 for agent hooks)

### Project-Specific Hook Scripts

Use `$CLAUDE_PROJECT_DIR` to reference scripts in your project:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-style.sh"
          }
        ]
      }
    ]
  }
}
```

### Events Without Matchers

For `UserPromptSubmit` and `Stop`, omit the matcher. `SubagentStart` and `SubagentStop` support matchers filtered by agent type name. `SessionEnd` supports matchers filtered by exit reason. Example for events that don't use matchers:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/prompt-validator.py"
          }
        ]
      }
    ]
  }
}
```

---

## Event-Specific Matchers

### PreToolUse / PermissionRequest / PostToolUse Common Matchers

| Matcher             | Description                    |
| ------------------- | ------------------------------ |
| `Agent`             | Subagent operations            |
| `Bash`              | Shell commands                 |
| `Glob`              | File pattern matching          |
| `Grep`              | Content search                 |
| `Read`              | File reading                   |
| `Edit`              | File editing                   |
| `Write`             | File writing                   |
| `WebFetch`          | Web fetching                   |
| `WebSearch`         | Web search                     |
| `Notebook.*`        | NotebookEdit, NotebookRead     |
| `mcp__<server>__.*` | All tools from MCP server      |
| `mcp__.*__write.*`  | MCP write tools across servers |

### SessionStart Matchers

| Matcher   | Trigger                                |
| --------- | -------------------------------------- |
| `startup` | New session started                    |
| `resume`  | `--resume`, `--continue`, or `/resume` |
| `clear`   | `/clear` command                       |
| `compact` | Auto or manual compact                 |

### PreCompact Matchers

| Matcher  | Trigger                     |
| -------- | --------------------------- |
| `manual` | `/compact` command          |
| `auto`   | Auto-compact (full context) |

### Setup Matchers

| Matcher       | Trigger                         |
| ------------- | ------------------------------- |
| `init`        | `--init` or `--init-only` flags |
| `maintenance` | `--maintenance` flag            |

### SubagentStart / SubagentStop Matchers

Matched against the agent type name. Values include built-in agents (`Bash`, `Explore`, `Plan`) and custom agent names from `.claude/agents/`.

Note: The Agent tool was renamed from Task in Claude Code v2.1.63. Use `Agent` as the matcher name for `PreToolUse`/`PostToolUse` hooks targeting the subagent-spawning tool call.

### SessionEnd Matchers

| Matcher                        | Trigger                                        |
| ------------------------------ | ---------------------------------------------- |
| `clear`                        | Session cleared with `/clear` command          |
| `logout`                       | User logged out                                |
| `prompt_input_exit`            | User exited while prompt input was visible     |
| `bypass_permissions_disabled`  | Bypass permissions mode was disabled           |
| `other`                        | Other exit reasons                             |

### ConfigChange Matchers

| Matcher             | When it fires                             |
| ------------------- | ----------------------------------------- |
| `user_settings`     | `~/.claude/settings.json` changes         |
| `project_settings`  | `.claude/settings.json` changes           |
| `local_settings`    | `.claude/settings.local.json` changes     |
| `policy_settings`   | Managed policy settings (non-blocking)    |
| `skill`             | Skill file changes                        |

### PostCompact Matchers

| Matcher  | Trigger                                             |
| -------- | --------------------------------------------------- |
| `manual` | After `/compact` command                            |
| `auto`   | After auto-compact when the context window is full  |

### Elicitation / ElicitationResult Matchers

Matched against the MCP server name (the server requesting or receiving user input).

### Notification Matchers

| Matcher              | Trigger                              |
| -------------------- | ------------------------------------ |
| `permission_prompt`  | Permission requests from Claude      |
| `idle_prompt`        | Claude waiting for input (60s+ idle) |
| `auth_success`       | Authentication success               |
| `elicitation_dialog` | MCP tool elicitation                 |

---

## Important Hook Events

### Setup Hook

Runs when Claude Code is invoked with repository setup and maintenance flags (`--init`, `--init-only`, or `--maintenance`).

**Use Setup hooks for**:

- One-time or occasional operations (dependency installation, migrations, cleanup)
- Operations you don't want on every session start

**Key characteristics**:

- Requires explicit flags because running automatically would slow down every session start
- Has access to `CLAUDE_ENV_FILE` for persisting environment variables
- Output added to Claude's context

### SessionStart Hook

Runs when Claude Code starts a new session or resumes an existing session.

**Use SessionStart hooks for**:

- Loading development context (existing issues, recent changes)
- Setting up environment variables

**Important**: For one-time operations like installing dependencies or running migrations, use Setup hooks instead. SessionStart runs on every session, so keep these hooks fast.

### PostToolUseFailure Hook

Runs immediately after a tool fails (returns an error). This complements PostToolUse, which only runs on successful tool execution.

**Use PostToolUseFailure hooks for**:

- Error recovery actions
- Logging tool failures
- Custom error handling and reporting

**Recognizes the same matcher values as PreToolUse and PostToolUse.**

### SubagentStart Hook

Runs when a Claude Code subagent (Agent tool call) is spawned.

**Use SubagentStart hooks for**:

- Subagent initialization
- Logging subagent creation
- Context injection for specific agent types

**Input includes**:

- `agent_id`: Unique identifier for the subagent
- `agent_type`: Agent name (built-in like "Bash", "Explore", "Plan", or custom agent names)

---

## Environment Variables

| Variable             | Description                        | Available In        |
| -------------------- | ---------------------------------- | ------------------- |
| `CLAUDE_PROJECT_DIR` | Project root (absolute path)       | All hooks           |
| `CLAUDE_CODE_REMOTE` | `"true"` if remote, empty if local | All hooks           |
| `CLAUDE_ENV_FILE`    | Path for persisting env vars       | SessionStart, Setup |
| `CLAUDE_PLUGIN_ROOT` | Plugin directory (absolute)        | Plugin hooks        |

### SessionStart Environment Persistence

**Example: Setting individual environment variables**

```bash
#!/bin/bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
  echo 'export API_KEY=your-api-key' >> "$CLAUDE_ENV_FILE"
  echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
fi
exit 0
```

**Example: Persisting all environment changes (e.g., nvm use)**

```bash
#!/bin/bash
ENV_BEFORE=$(export -p | sort)

# Run setup commands that modify environment
source ~/.nvm/nvm.sh
nvm use 20

if [ -n "$CLAUDE_ENV_FILE" ]; then
  ENV_AFTER=$(export -p | sort)
  comm -13 <(echo "$ENV_BEFORE") <(echo "$ENV_AFTER") >> "$CLAUDE_ENV_FILE"
fi
exit 0
```

Variables in `$CLAUDE_ENV_FILE` are sourced before each Bash command.

---

## Working with MCP Tools

MCP tools follow the pattern `mcp__<server>__<tool>`:

- `mcp__memory__create_entities` - Memory server's create entities tool
- `mcp__filesystem__read_file` - Filesystem server's read file tool
- `mcp__github__search_repositories` - GitHub server's search tool

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__memory__.*",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Memory operation initiated' >> ~/mcp-operations.log"
          }
        ]
      },
      {
        "matcher": "mcp__.*__write.*",
        "hooks": [
          {
            "type": "command",
            "command": "/home/user/scripts/validate-mcp-write.py"
          }
        ]
      }
    ]
  }
}
```

---

## Execution Details

| Aspect              | Behavior                                |
| ------------------- | --------------------------------------- |
| **Timeout**         | 600 seconds default for commands, 30s for prompts, 60s for agent hooks, configurable |
| **Parallelization** | All matching hooks run in parallel      |
| **Deduplication**   | Identical commands deduplicated         |
| **Environment**     | Runs in cwd with Claude Code's env      |
| **Hook order**      | Hooks from all sources execute together |

### Output Handling by Event

| Event                                                      | stdout Handling                  |
| ---------------------------------------------------------- | -------------------------------- |
| UserPromptSubmit, SessionStart, Setup                      | Added to Claude's context        |
| PreToolUse, PostToolUse, Stop                              | Shown in verbose mode (Ctrl+O)   |
| Notification, SessionEnd, SubagentStart, InstructionsLoaded | Logged to debug only (`--debug`) |
| PostCompact                                                | Logged to debug only (`--debug`) |
| TeammateIdle, TaskCompleted, ConfigChange                  | Shown in verbose mode (Ctrl+O)   |
| WorktreeCreate                                             | Stdout must be the absolute path to the created worktree directory |
| WorktreeRemove                                             | Non-blocking; logged to debug    |
| Elicitation, ElicitationResult                             | JSON response controls MCP input |

---

## Security Considerations

### Disclaimer

**USE AT YOUR OWN RISK**: Claude Code hooks execute arbitrary shell commands on your system automatically. By using hooks, you acknowledge that:

- You are solely responsible for the commands you configure
- Hooks can modify, delete, or access any files your user account can access
- Malicious or poorly written hooks can cause data loss or system damage
- Anthropic provides no warranty and assumes no liability for any damages
- You should thoroughly test hooks in a safe environment before production use

### Security Best Practices

1. **Validate and sanitize inputs** - Never trust input data blindly
2. **Always quote shell variables** - Use `"$VAR"` not `$VAR`
3. **Block path traversal** - Check for `..` in file paths
4. **Use absolute paths via the $CLAUDE_PROJECT_DIR variable** - Specify full paths for scripts (use `$CLAUDE_PROJECT_DIR`)
5. **Skip sensitive files** - Avoid `.env`, `.git/`, keys, etc.

### Configuration Safety

Direct edits to hooks in settings files don't take effect immediately:

1. Hooks snapshot captured at startup
2. Snapshot used throughout the session
3. Warns if hooks are modified externally
4. Requires review in `/hooks` menu for changes to apply

This prevents malicious hook modifications from affecting your current session.

---

## Debugging

### Enable Debug Mode

```bash
claude --debug
claude --debug "hooks"  # Filter to hooks only
```

### Debug Output Example

```text
[DEBUG] Executing hooks for PostToolUse:Write
[DEBUG] Getting matching hook commands for PostToolUse with query: Write
[DEBUG] Found 1 hook matchers in settings
[DEBUG] Matched 1 hooks for query "Write"
[DEBUG] Found 1 hook commands to execute
[DEBUG] Executing hook command: <Your command> with timeout 600000ms
[DEBUG] Hook command completed with status 0: <Your stdout>
```

### Basic Troubleshooting

1. **Check configuration** - Run `/hooks` to see if your hook is registered
2. **Verify syntax** - Ensure your JSON settings are valid
3. **Test commands** - Run hook commands manually first
4. **Check permissions** - Make sure scripts are executable
5. **Review logs** - Use `claude --debug` to see hook execution details
6. **Validate plugin hooks** - Use `claude plugin validate` or `/plugin validate` for plugin-level hooks

### Common Issues

| Problem              | Cause                            | Fix                                      |
| -------------------- | -------------------------------- | ---------------------------------------- |
| Hook not running     | Wrong matcher pattern            | Check case-sensitivity, regex            |
| Command not found    | Relative path                    | Use `$CLAUDE_PROJECT_DIR`                |
| JSON not processed   | Non-zero exit code               | Exit 0 for JSON processing               |
| Hook times out       | Slow script                      | Optimize or increase timeout             |
| Quotes breaking      | Unescaped in JSON                | Use `\"` inside JSON strings             |
| Plugin hook not load | Invalid plugin.json hooks config | Validate with `claude plugin validate .` |
| Path not found       | Missing `${CLAUDE_PLUGIN_ROOT}`  | Use variable for plugin scripts          |

### Validation Commands

**For plugin hooks**:

```bash
# CLI (from terminal)
claude plugin validate .
claude plugin validate ./path/to/plugin

# In Claude Code session
/plugin validate .
/plugin validate ./path/to/plugin
```

**For settings hooks**: JSON validation with:

```bash
python3 -m json.tool .claude/settings.json
```

### Test Commands Manually

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"test.txt"}}' | ./your-hook.sh
```

---

## Sources

- [Hooks Reference](https://code.claude.com/docs/en/hooks.md) (accessed 2026-01-28)
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide.md)
- [Settings Reference](https://code.claude.com/docs/en/settings.md)
- [Plugin Components Reference](https://code.claude.com/docs/en/plugins-reference.md#hooks)
