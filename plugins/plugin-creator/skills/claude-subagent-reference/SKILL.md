---
name: claude-subagent-reference
description: Reference spec and schema for Claude Code subagents — covers built-in agents (Explore, Plan, general-purpose), all frontmatter fields (name, description, tools, disallowedTools, model, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, effort, isolation, color, initialPrompt), scope and file locations, invocation patterns (@-mention, --agent, --agents CLI), tool restrictions, and example subagent definitions. Use when creating, configuring, or debugging a subagent definition file, looking up a frontmatter field, choosing between subagents and agent teams, or understanding what loads at subagent startup.
user-invocable: true
---

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> (accessed 2026-05-28)

# Claude Code Subagents — Reference

Subagents are specialized AI assistants that run in their own context window with custom system prompts, specific tool access, and independent permissions. Use one when a task would flood your main conversation with output you won't reference again; the subagent does the work in its own context and returns only a summary.

Subagents help you:
- **Preserve context** by keeping exploration and implementation out of your main conversation
- **Enforce constraints** by limiting which tools a subagent can use
- **Reuse configurations** across projects with user-level subagents
- **Control costs** by routing tasks to faster, cheaper models like Haiku

Subagents cannot spawn other subagents. For coordinated parallel work with inter-agent messaging, see [./references/agent-teams.md](./references/agent-teams.md).

---

## Built-in subagents

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Built-in subagents (accessed 2026-05-28)

Claude Code includes built-in subagents. **Explore and Plan skip CLAUDE.md files and the parent session's git status** for speed. Every other built-in and custom subagent loads both.

| Agent | Model | Tools | Purpose |
|:------|:------|:------|:--------|
| **Explore** | Haiku (fast) | Read-only | File discovery, code search, codebase exploration. Thoroughness: `quick` / `medium` / `very thorough` |
| **Plan** | Inherits | Read-only | Codebase research during [plan mode](https://code.claude.com/docs/en/permission-modes.md#analyze-before-you-edit-with-plan-mode) |
| **general-purpose** | Inherits | All | Complex multi-step tasks requiring both exploration and modification |
| **statusline-setup** | Sonnet | — | Invoked automatically for `/statusline` |
| **claude-code-guide** | Haiku | — | Invoked automatically for Claude Code questions |

> **Explore limitation**: Haiku-based, read-only retrieval only. Do not delegate reasoning or analysis to Explore — validated ~50% accuracy on ambiguous queries. Use `general-purpose` for any task requiring interpretation.

---

## Scope and file locations

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Choose the subagent scope (accessed 2026-05-28)

Subagent files are Markdown files with YAML frontmatter. When multiple subagents share the same name, the higher-priority location wins.

| Location | Scope | Priority |
|:---------|:------|:---------|
| Managed settings | Organization-wide | 1 (highest) |
| `--agents` CLI flag | Current session only | 2 |
| `.claude/agents/` | Current project | 3 |
| `~/.claude/agents/` | All your projects | 4 |
| Plugin `agents/` directory | Where plugin is enabled | 5 (lowest) |

**Project subagents** (`.claude/agents/`) are scanned recursively — subdirectories are allowed but do not affect the agent's name (identity comes only from the `name` frontmatter field). Keep `name` values unique across the whole tree.

**Plugin subagents** use scoped identifiers: `agents/review/security.md` in plugin `my-plugin` registers as `my-plugin:review:security`.

> For plugin subagent security restrictions (`hooks`, `mcpServers`, `permissionMode` are silently ignored in plugin agents), see `/claude-plugins-reference-2026`.

**Subagents load at session start.** If you add or edit a subagent file directly on disk, restart your session to load it. Subagents created through the `/agents` interface take effect immediately.

---

## Frontmatter fields

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Supported frontmatter fields (accessed 2026-05-28)

Only `name` and `description` are required. All other fields are optional.

| Field | Required | Description |
|:------|:---------|:------------|
| `name` | **Yes** | Unique identifier: lowercase letters and hyphens, max 64 chars. Hooks receive this as `agent_type`. Filename need not match |
| `description` | **Yes** | When Claude should delegate to this subagent. Write clearly — Claude uses this for routing. Include "use proactively" to encourage automatic delegation |
| `tools` | No | Allowlist of tools the subagent can use. Inherits all tools when omitted. Accepts exact tool names and MCP server-level patterns (`mcp__<server>` or `mcp__<server>__*`). Use `Agent(worker, researcher)` syntax to restrict which subagent types can be spawned. A subagent whose entries all resolve to nothing refuses to launch. See [./references/tool-and-permission-control.md](./references/tool-and-permission-control.md) |
| `disallowedTools` | No | Denylist — removed from inherited or specified list. Accepts the same MCP server-level patterns as `tools`. When both fields set, `disallowedTools` applied first |
| `model` | No | Model to use: `sonnet`, `opus`, `haiku`, a full model ID (e.g., `claude-opus-4-7`), or `inherit`. Defaults to `inherit`. See [./references/model-and-effort.md](./references/model-and-effort.md) |
| `permissionMode` | No | Permission mode: `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, or `plan`. **Silently ignored for plugin subagents.** See [./references/tool-and-permission-control.md](./references/tool-and-permission-control.md) |
| `maxTurns` | No | Maximum agentic turns before the subagent stops |
| `skills` | No | Skills to preload into the subagent's context at startup. Full skill content is injected (not just the description). Cannot preload skills with `disable-model-invocation: true`. See `/claude-skills-overview-2026` for skill authoring |
| `mcpServers` | No | MCP servers available to this subagent. Each entry: a server name string (reuses parent connection) or an inline definition. **Silently ignored for plugin subagents.** Inline servers connect when the subagent starts and disconnect when it finishes |
| `hooks` | No | Lifecycle hooks scoped to this subagent. **Silently ignored for plugin subagents.** `Stop` hooks are auto-converted to `SubagentStop` at runtime. See [./references/hooks-for-subagents.md](./references/hooks-for-subagents.md) |
| `memory` | No | Persistent memory scope: `user`, `project`, or `local`. Enables cross-session learning. See [./references/memory-and-context.md](./references/memory-and-context.md) |
| `background` | No | Set `true` to always run this subagent as a background task. Default: `false` |
| `effort` | No | Effort level override when this subagent is active: `low`, `medium`, `high`, `xhigh`, `max`. Overrides session level but not `CLAUDE_CODE_EFFORT_LEVEL` env var. See [./references/model-and-effort.md](./references/model-and-effort.md) |
| `isolation` | No | Set `worktree` to run the subagent in a temporary git worktree (isolated repo copy). Auto-cleaned up if no changes made. Supported in plugin subagents. See [./references/memory-and-context.md](./references/memory-and-context.md) |
| `color` | No | Display color in task list: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, or `cyan` |
| `initialPrompt` | No | Auto-submitted as the first user turn when this agent runs as the main session via `--agent` or the `agent` setting. Commands and skills are processed. Prepended to any user-provided prompt |

---

## Tools not available in subagents

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Available tools (accessed 2026-05-28)

These tools are unavailable to subagents even when listed in the `tools` field (they depend on the main conversation's UI or session state):

- `Agent`
- `AskUserQuestion`
- `EnterPlanMode`
- `ExitPlanMode` (unless `permissionMode: plan`)
- `ScheduleWakeup`
- `WaitForMcpServers`

---

## Minimal example

```markdown
---
name: code-reviewer
description: Expert code reviewer. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked, run git diff to see recent changes, focus on modified files, and begin review immediately.

Provide feedback organized by priority: Critical issues (must fix), Warnings (should fix), Suggestions (consider improving).
```

---

## Invocation patterns

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Invoke subagents explicitly (accessed 2026-05-28)

Three patterns in escalating strength:

**Natural language** — Claude decides whether to delegate:

```
Use the test-runner subagent to fix failing tests
```

**@-mention** — guarantees this specific subagent runs for one task (type `@` and pick from typeahead, or type manually):

```
@"code-reviewer (agent)" look at the auth changes
```

For plugin subagents, type `@agent-` followed by the scoped name, for example `@agent-` + `my-plugin:code-reviewer`.

**Session-wide** — entire session uses this subagent's system prompt, tool restrictions, and model:

```bash
claude --agent code-reviewer
```

For plugin subagents with name conflicts, use the scoped name: `claude --agent my-plugin:security-reviewer`

Set as project default in `.claude/settings.json`:

```json
{ "agent": "code-reviewer" }
```

The `--agent` CLI flag overrides the `agent` setting when both are present.

---

## CLI-defined subagents

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Choose the subagent scope (accessed 2026-05-28)

Define subagents in JSON at launch — exist only for that session:

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

The `--agents` flag accepts the same fields as file-based frontmatter. Use `prompt` for the system prompt (equivalent to the markdown body in file-based subagents).

---

## Key environment variables

SOURCE: <https://code.claude.com/docs/en/env-vars.md> (accessed 2026-05-28)

| Variable | Purpose |
|:---------|:--------|
| `CLAUDE_CODE_SUBAGENT_MODEL` | Override model for ALL subagents. Overrides per-invocation parameter and frontmatter `model`. Set to `inherit` to use normal resolution |
| `CLAUDE_CODE_FORK_SUBAGENT=1` | Enable fork mode (v2.1.117+). See [./references/fork-mode.md](./references/fork-mode.md) |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Enable agent teams (v2.1.32+). See [./references/agent-teams.md](./references/agent-teams.md) |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` | Disable all background task functionality |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | % of context capacity at which auto-compaction triggers (default ~95%) |
| `TASK_MAX_OUTPUT_LENGTH` | Max characters in subagent output before truncation (default 32000, max 160000) |
| `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` | Disable all built-in subagent types (non-interactive mode only) |

---

## Reference files

| Topic | File |
|:------|:-----|
| Tool allowlist/denylist, Agent() spawn restrictions, permission modes | [./references/tool-and-permission-control.md](./references/tool-and-permission-control.md) |
| Model aliases, CLAUDE_CODE_SUBAGENT_MODEL, effort levels | [./references/model-and-effort.md](./references/model-and-effort.md) |
| Hooks in frontmatter vs settings.json, SubagentStart/Stop schemas | [./references/hooks-for-subagents.md](./references/hooks-for-subagents.md) |
| Memory scopes, what loads at startup, worktrees, compaction, resume | [./references/memory-and-context.md](./references/memory-and-context.md) |
| Fork mode (experimental, v2.1.117+) | [./references/fork-mode.md](./references/fork-mode.md) |
| Agent teams vs subagents, enabling, best practices | [./references/agent-teams.md](./references/agent-teams.md) |
| Full example subagent definitions with hook scripts | [./references/example-subagents.md](./references/example-subagents.md) |
