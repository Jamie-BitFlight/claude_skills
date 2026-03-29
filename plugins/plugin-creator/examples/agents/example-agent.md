---
name: example-agent
description: Demonstrates all available agent frontmatter fields. Use when you need a reference for agent configuration or when learning about agent capabilities. Handles example tasks, demonstration requests, and tutorial scenarios.
tools: Read, Grep, Glob, WebFetch, WebSearch
disallowedTools: Bash, Write, Edit
model: sonnet
permissionMode: default
skills:
  - python3-development
  - plugin-creator:claude-skills-overview-2026
hooks:
  PreToolUse:
  - matcher: Read
    hooks:
    - type: command
      command: echo 'About to read a file'
      timeout: 5
color: cyan
---

# Example Agent

This agent demonstrates all available frontmatter fields for Claude Code agents.

## Purpose

Use this as a reference when creating new agents. All fields shown above are valid agent frontmatter options.

## Field Descriptions

| Field             | Type   | Purpose                                  | Constraints                              | Required |
| ----------------- | ------ | ---------------------------------------- | ---------------------------------------- | -------- |
| `name`            | string | Unique identifier                        | kebab-case, lowercase, max 64 characters | Yes      |
| `description`     | string | When to delegate to this agent           | Trigger keywords, max 1024 characters    | Yes      |
| `tools`           | string | Allowlist of tools the agent can use     | Comma-separated tool names               | No       |
| `disallowedTools` | string | Denylist of tools the agent cannot use   | Comma-separated tool names               | No       |
| `model`           | string | Which model to use                       | sonnet, opus, haiku, or inherit          | No       |
| `permissionMode`  | string | Permission behavior for tool usage       | default, relaxed, strict                 | No       |
| `skills`          | string | Skills to load when agent is active      | Comma-separated skill names              | No       |
| `hooks`           | object | Scoped hooks for agent lifecycle         | Valid hook configuration object          | No       |
| `color`           | string | Terminal output color for agent messages | Valid color name (cyan, green, yellow)   | No       |

**Critical:** `tools`, `disallowedTools`, and `skills` fields MUST be comma-separated strings, NOT YAML arrays.

## Validation

Validate your agent using:

```bash
# Frontmatter validation
uvx skilllint@latest check ./path/to/agent.md

# Auto-fix common issues
uvx skilllint@latest check --check ./path/to/agent.md
uvx skilllint@latest check --fix ./path/to/agent.md

# Plugin validation (if agent is part of a plugin)
claude plugin validate ./path/to/plugin/
```

## Common Validation Errors

| Error                           | Cause                     | Fix                                     |
| ------------------------------- | ------------------------- | --------------------------------------- |
| `name: Required`                | Missing name field        | Add `name` field to frontmatter         |
| `description: Required`         | Missing description field | Add `description` with trigger keywords |
| `tools must be string`          | Used YAML array format    | Change to comma-separated string        |
| `YAML array detected`           | Used `- Tool1` format     | Change to `Tool1, Tool2` format         |
| `model must be sonnet/opus/...` | Invalid model name        | Use valid model identifier              |
| `name exceeds 64 characters`    | Name too long             | Shorten to max 64 characters            |
| `description exceeds 1024 ...`  | Description too long      | Shorten to max 1024 characters          |

## Agent Location

Agents can be located in:

- **User-level:** `~/.claude/agents/agent-name.md` - Personal agents available across all projects
- **Project-level:** `.claude/agents/agent-name.md` - Version controlled, shared with team
- **Plugin:** `plugins/plugin-name/agents/agent-name.md` - Bundled in a plugin

When creating an agent in a plugin, update the plugin's `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "agents": ["./agents/example-agent.md"]
}
```

**Important:** The `agents` field in plugin.json must be an array of individual file paths, not a directory string.

**Skills vs agents registration distinction:** This explicit registration requirement applies to agents only. Skills placed under the plugin's `skills/` directory are auto-discovered by Claude Code — no `plugin.json` update is needed for skills. Adding a `skills` field to `plugin.json` opts the plugin into manual allowlist mode (SK009 fires as an INFO reminder).

## Creating Agents

Use the `/plugin-creator:agent-creator` skill to create new agents interactively:

```bash
/plugin-creator:agent-creator
```

The skill will:

1. Gather requirements through questions
2. Suggest templates from existing agents
3. Generate validated frontmatter
4. Save to appropriate location (user/project/plugin)
5. Update plugin.json if creating a plugin agent
6. Validate the created file

## Usage

This agent is for demonstration purposes only. When creating real agents, include only the fields you need.

## Sources

- [Claude Code Documentation](https://code.claude.com/docs/en/sub-agents.md) (accessed 2026-01-28)
- [Agent Creator Skill](./plugins/plugin-creator/skills/agent-creator/SKILL.md)
- [Plugin Creator Validation Scripts](./plugins/plugin-creator/scripts/README.md)
