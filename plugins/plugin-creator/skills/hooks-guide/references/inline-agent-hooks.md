# Inline Agent Frontmatter — Hooks, MCP, Skills, Memory

SOURCE: [Create custom subagents](https://code.claude.com/docs/en/sub-agents.md) (accessed 2026-03-01)

## Table of Contents

1. [Supported Frontmatter Fields](#supported-frontmatter-fields)
2. [Define Hooks in Agent Frontmatter](#define-hooks-in-agent-frontmatter)
3. [Stop Hook Auto-Conversion to SubagentStop](#stop-hook-auto-conversion-to-subagentstop)
4. [SubagentStart and SubagentStop in settings-json](#subagentstart-and-subagentstop-in-settings-json)
5. [mcpServers Field](#mcpservers-field)
6. [skills Field](#skills-field)
7. [memory Field](#memory-field)
8. [background Field](#background-field)
9. [isolation: worktree Field](#isolation-worktree-field)

---

## Supported Frontmatter Fields

Project, user, and managed agents require `name` and `description`. Plugin agents have filename
and generic-description fallbacks, but should provide both fields for reliable routing. All other
fields are optional.

| Field             | Required | Description                                                                                                                                                                                                                                                                 |
| :---------------- | :------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`            | Yes      | Unique identifier using lowercase letters and hyphens                                                                                                                                                                                                                       |
| `description`     | Yes      | When Claude should delegate to this subagent                                                                                                                                                                                                                                |
| `tools`           | No       | Tools the subagent can use. Inherits all tools if omitted                                                                                                                                                                                                                   |
| `disallowedTools` | No       | Tools to deny, removed from inherited or specified list                                                                                                                                                                                                                     |
| `model`           | No       | Model to use: `sonnet`, `opus`, `haiku`, or `inherit`. Defaults to `inherit`                                                                                                                                                                                                |
| `permissionMode`  | No       | Permission mode: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, or `plan`                                                                                                                                                                                        |
| `maxTurns`        | No       | Maximum number of agentic turns before the subagent stops                                                                                                                                                                                                                   |
| `skills`          | No       | Skills to load into the subagent's context at startup. Full skill content is injected, not just made available for invocation. Subagents do not inherit skills from the parent conversation                                                                                  |
| `mcpServers`      | No       | MCP servers available to this subagent. Each entry is either a server name referencing an already-configured server (e.g., `"slack"`) or an inline definition with the server name as key and a full MCP server config as value                                              |
| `hooks`           | No       | Lifecycle hooks scoped to this subagent                                                                                                                                                                                                                                     |
| `memory`          | No       | Persistent memory scope: `user`, `project`, or `local`. Enables cross-session learning                                                                                                                                                                                      |
| `background`      | No       | Set to `true` to always run this subagent as a background task. Default: `false`                                                                                                                                                                                            |
| `isolation`       | No       | Set to `worktree` to run the subagent in a temporary git worktree, giving it an isolated copy of the repository. The worktree is automatically cleaned up if the subagent makes no changes                                                                                   |

---

## Define Hooks in Agent Frontmatter

Hooks defined in agent frontmatter run only while that specific subagent is active and are cleaned up when it finishes.

All hook events are supported. Common events for subagents:

| Event         | Matcher input | When it fires                                                       |
| :------------ | :------------ | :------------------------------------------------------------------ |
| `PreToolUse`  | Tool name     | Before the subagent uses a tool                                     |
| `PostToolUse` | Tool name     | After the subagent uses a tool                                      |
| `Stop`        | (none)        | When the subagent finishes (converted to `SubagentStop` at runtime) |

Example — validate Bash commands before execution, run linter after file edits:

```yaml
---
name: code-reviewer
description: Review code changes with automatic linting
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh $TOOL_INPUT"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
---
```

Example — allow only read-only database queries via `PreToolUse` validation:

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

Claude Code passes hook input as JSON via stdin to hook commands. Exit code `2` blocks the operation and returns stderr to Claude.

---

## Stop Hook Auto-Conversion to SubagentStop

`Stop` hooks defined in agent frontmatter are automatically converted to `SubagentStop` events at runtime.

Declare a `Stop` hook in frontmatter:

```yaml
hooks:
  Stop:
    - hooks:
        - type: command
          command: "./scripts/cleanup.sh"
```

At runtime, this fires as `SubagentStop` in the main session context — no separate `settings.json` entry is required for per-agent cleanup logic.

---

## SubagentStart and SubagentStop in settings-json

Configure hooks in `settings.json` that respond to subagent lifecycle events in the main session. These run outside the subagent, in the main session.

| Event           | Matcher input   | When it fires                    |
| :-------------- | :-------------- | :------------------------------- |
| `SubagentStart` | Agent type name | When a subagent begins execution |
| `SubagentStop`  | Agent type name | When a subagent completes        |

Both events support matchers to target specific agent types by name. Omit the matcher to match all subagents.

Example — setup script fires only when `db-agent` starts; cleanup fires when any subagent stops:

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db-connection.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup-db-connection.sh" }
        ]
      }
    ]
  }
}
```

---

## mcpServers Field

Declare MCP servers available to a specific subagent. Each entry is either:

- A string referencing an already-configured server by name (e.g., `"slack"`)
- An inline definition with the server name as key and a full MCP server config object as value

Example referencing a pre-configured server:

```yaml
---
name: slack-notifier
description: Send Slack notifications after task completion
mcpServers:
  - slack
---
```

Example with an inline server definition:

```yaml
---
name: api-agent
description: Interact with the internal API
mcpServers:
  internal-api:
    type: http
    url: "https://api.internal/mcp"
---
```

Subagents do not inherit MCP servers from the parent session unless listed in `mcpServers`.

> **Plugin Agent Restriction**: For plugin agents (agents bundled in a plugin's `agents/` directory), the `mcpServers`, `hooks`, and `permissionMode` frontmatter fields are **silently ignored** at runtime. Claude Code strips these fields for security reasons. If you need these fields to take effect, copy the agent file to `.claude/agents/` (project-level) or `~/.claude/agents/` (user-level), where these fields ARE honored.
>
> SOURCE: [Create custom subagents](https://code.claude.com/docs/en/sub-agents.md) — "For security reasons, plugin subagents do not support the hooks, mcpServers, or permissionMode frontmatter fields. These fields are ignored when loading agents from a plugin." (accessed 2026-03-17)

---

## skills Field

Use the `skills` field to inject skill content into a subagent's context at startup. The full content of each named skill is injected — not just made available for invocation.

Subagents do not inherit skills from the parent conversation. Skills must be listed explicitly.

```yaml
---
name: api-developer
description: Implement API endpoints following team conventions
skills:
  - api-conventions
  - error-handling-patterns
---

Implement API endpoints. Follow the conventions and patterns from the preloaded skills.
```

Skills are identified by name, matching the skill's `name` field. The skill's full markdown body is injected into the subagent's system context before the subagent's own prompt.

---

## memory Field

The `memory` field gives the subagent a persistent directory that survives across conversations.

Choose a scope:

| Scope     | Location                                      | Use when                                                                     |
| :-------- | :-------------------------------------------- | :--------------------------------------------------------------------------- |
| `user`    | `~/.claude/agent-memory/<name-of-agent>/`     | the subagent should remember learnings across all projects                   |
| `project` | `.claude/agent-memory/<name-of-agent>/`       | the subagent's knowledge is project-specific and shareable via version control |
| `local`   | `.claude/agent-memory-local/<name-of-agent>/` | the subagent's knowledge is project-specific but must not be version-controlled |

When `memory` is enabled:

- The subagent's system prompt includes instructions for reading and writing to the memory directory.
- The first 200 lines of `MEMORY.md` in the memory directory are injected into the subagent's system prompt, with instructions to curate `MEMORY.md` if it exceeds 200 lines.
- `Read`, `Write`, and `Edit` tools are automatically enabled so the subagent can manage its memory files.

Example:

```yaml
---
name: code-reviewer
description: Reviews code for quality and best practices
memory: user
---

You are a code reviewer. As you review code, update your agent memory with
patterns, conventions, and recurring issues you discover.
```

To prompt the subagent to use its memory, include explicit instructions in the agent body:

```markdown
Update your agent memory as you discover codepaths, patterns, library
locations, and key architectural decisions. This builds up institutional
knowledge across conversations. Write concise notes about what you found
and where.
```

---

## background Field

Set `background: true` to always run the subagent as a background task (concurrent with the main conversation).

```yaml
---
name: log-analyzer
description: Analyze application logs and report anomalies
background: true
---
```

Default is `false` (foreground, blocking).

Background subagents:

- Run concurrently while you continue working.
- Require upfront permission approval before launch — Claude Code prompts for any tool permissions the subagent will need.
- Auto-deny any permission not pre-approved once running.
- Cannot pass through `AskUserQuestion` tool calls — that tool call fails but the subagent continues.

To disable all background task functionality, set `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`.

---

## isolation: worktree Field

Set `isolation: worktree` to run the subagent in a temporary git worktree — an isolated copy of the repository.

```yaml
---
name: experimental-refactor
description: Attempt refactoring in isolation without affecting the working tree
isolation: worktree
---
```

Behavior:

- The subagent operates in a separate worktree, not the main working directory.
- If the subagent makes no changes, the worktree is automatically cleaned up on completion.
- If the subagent makes changes, the worktree persists and can be reviewed or merged.

Use `isolation: worktree` for subagents that perform destructive or exploratory changes that should not touch the user's working files.
