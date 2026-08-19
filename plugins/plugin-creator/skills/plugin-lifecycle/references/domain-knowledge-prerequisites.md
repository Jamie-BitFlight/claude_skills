# Plugin Lifecycle — Domain Knowledge Prerequisites

Load these reference skills at session start before executing any phase. Without them, the agent lacks foundational plugin domain knowledge needed to make informed decisions about plugin structure, component design, and validation requirements.

## Required — Load at Session Start

1. `Skill(skill="plugin-creator:claude-plugins-reference-2026")`

Provides: plugin definition, directory structure, plugin.json schema (all field types and constraints), component types (skills, agents, hooks, MCP servers, LSP servers, output styles), plugin caching mechanics, environment variables (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`), installation scopes (user, project, local, managed), marketplace configuration, path behavior rules, CLI commands.

2. `Skill(skill="plugin-creator:claude-skills-overview-2026")`

Provides: SKILL.md format, all 14 frontmatter fields (name, description, allowed-tools, model, context, agent, user-invocable, disable-model-invocation, hooks, argument-hint), YAML multiline bug (do not use `>-` or `|` in descriptions), skill tokenomics and progressive disclosure, string substitutions (`$ARGUMENTS`, `${CLAUDE_SESSION_ID}`), dynamic context injection (`!` backtick syntax), invocation control, tool assignment via allowed-tools (comma-separated string, not array), context fork behavior and tool restrictions.

## Required for Phases Involving Hooks (Phase 4: Create, Phase 5: Debug)

3. `Skill(skill="plugin-creator:hooks-guide")`

Provides: hook event types (13 events), hook types (command, prompt, agent), hook authoring guides for Python and Node.js (CommonJS), exit codes for PreToolUse decision control, PermissionRequest hooks, tool denial mechanisms (disallowedTools, permission rules, hook-based denial), pre-approval mechanisms (allowed-tools, permissionMode, hook auto-allow), agent frontmatter fields (allowedTools, disallowedTools, mcpServers, permissionMode, background).

## Required for Phases Involving Agents (Phase 4: Create)

4. `Skill(skill="plugin-creator:claude-subagent-reference")`

Provides: all agent frontmatter fields (name, description, tools, disallowedTools, model, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, effort, isolation, color, initialPrompt) with full descriptions and examples; built-in agents (Explore, Plan, general-purpose); scope and file locations (project, user, plugin, managed, CLI-defined); tool allowlist/denylist and Agent() spawn restriction syntax; all permission modes and protected paths; hooks in frontmatter vs settings.json; memory scopes and what loads at startup; worktree isolation; fork mode (experimental); agent teams vs subagents comparison.

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> (accessed 2026-05-28)

## Why These Matter

These skills contain the answers to fundamental questions: what is a plugin, what are its capabilities, how are tools assigned/hidden/denied, how is the namespace defined, what environment variables exist, how are MCP servers configured, and what scripting languages to prefer. The lifecycle phases orchestrate the workflow — these reference skills provide the domain expertise.
