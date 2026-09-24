# Plugin Lifecycle — Domain Knowledge Prerequisites

Load these reference skills at session start before executing any phase. Without them, the agent lacks foundational plugin domain knowledge needed to make informed decisions about plugin structure, component design, and validation requirements.

## Required — Load at Session Start

1. `/plugin-creator:claude-plugins-reference-2026`

Provides: plugin definition, directory structure, plugin.json schema (all field types and constraints), component types (skills, agents, hooks, MCP servers, LSP servers, output styles), plugin caching mechanics, environment variables (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`), installation scopes (user, project, local, managed), marketplace configuration, path behavior rules, CLI commands.

2. `/plugin-creator:claude-skills-overview-2026`

Provides: SKILL.md format, the canonical Claude Code runtime field inventory, accepted `allowed-tools` strings and YAML lists, progressive disclosure, substitutions, dynamic context injection, invocation control, and foreground/background fork behavior.

## Required for Phases Involving Hooks (Phase 4: Create, Phase 5: Debug)

3. `/plugin-creator:hooks-guide`

Provides: hook event types (13 events), hook types (command, prompt, agent), hook authoring guides for Python and Node.js (CommonJS), exit codes for PreToolUse decision control, PermissionRequest hooks, tool denial mechanisms (disallowedTools, permission rules, hook-based denial), pre-approval mechanisms (allowed-tools, permissionMode, hook auto-allow), agent frontmatter fields (allowedTools, disallowedTools, mcpServers, permissionMode, background).

## Required for Phases Involving Agents (Phase 4: Create)

4. `/plugin-creator:claude-subagent-reference`

Provides: the current subagent fields, including `omitClaudeMd`, `experimental`, `effort`, and `initialPrompt`; plugin-supported versus ignored/unsupported fields; CSV/YAML tool forms; depth-limited nested spawning; startup context; model precedence; worktree isolation; default fork mode and `/subtask`; agent teams comparison.

SOURCE: <https://code.claude.com/docs/en/sub-agents> and <https://code.claude.com/docs/en/plugins-reference#agents> (accessed 2026-09-24)

## Why These Matter

These skills contain the answers to fundamental questions: what is a plugin, what are its capabilities, how are tools assigned/hidden/denied, how is the namespace defined, what environment variables exist, how are MCP servers configured, and what scripting languages to prefer. The lifecycle phases orchestrate the workflow — these reference skills provide the domain expertise.
