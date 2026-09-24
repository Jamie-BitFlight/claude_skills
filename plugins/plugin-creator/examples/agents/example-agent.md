---
name: example-agent
description: Illustrative Claude Code agent configuration. Use when learning the basic agent file shape; follow the canonical subagent reference for the current field inventory.
tools: Read, Grep, Glob, WebFetch, WebSearch
disallowedTools: Bash, Write, Edit
model: sonnet
permissionMode: default
skills:
  - python-engineering:python3-core
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

This agent illustrates a subset of Claude Code agent frontmatter.

## Purpose

Use this as a compact example. See [the canonical subagent reference](../../skills/claude-subagent-reference/SKILL.md) for current fields and plugin restrictions.

## Field Descriptions

| Field             | Type   | Purpose                                  | Constraints                              | Required |
| ----------------- | ------ | ---------------------------------------- | ---------------------------------------- | -------- |
| `name`            | string | Unique identifier                        | Recommended for plugin routing; required elsewhere | Scope-dependent |
| `description`     | string | When to delegate to this agent           | Recommended for plugin routing; required elsewhere | Scope-dependent |
| `tools`           | string/list | Allowlist of tools the agent can use | CSV string or YAML list                  | No       |
| `disallowedTools` | string/list | Denylist of tools the agent cannot use | CSV string or YAML list                  | No       |
| `model`           | string | Which model to use                       | sonnet, opus, haiku, or inherit          | No       |
| `permissionMode`  | string | Permission behavior for tool usage       | See canonical reference; ignored in plugin agents | No |
| `skills`          | string/list | Skills to load when agent is active | CSV string or YAML list                  | No       |
| `hooks`           | object | Scoped hooks for agent lifecycle         | Valid hook configuration object          | No       |
| `color`           | string | Terminal output color for agent messages | Valid color name (cyan, green, yellow)   | No       |

`tools`, `disallowedTools`, and `skills` accept CSV strings or YAML lists. Plugin agents ignore `hooks`, `mcpServers`, and `permissionMode`, and do not support `initialPrompt`. Plugin agents without valid `name` frontmatter fall back to the file path; invalid frontmatter also receives a generic description. Provide both fields for routing quality. Project, user, and managed agents require both fields to load.

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
| `name: Required`                | Missing name in a non-plugin agent | Add `name` field to frontmatter  |
| `description: Required`         | Missing description in a non-plugin agent | Add routing description |
| `model must be sonnet/opus/...` | Invalid model name        | Use valid model identifier              |

## Agent Location

Agents can be located in:

- **User-level:** `~/.claude/agents/agent-name.md` - Personal agents available across all projects
- **Project-level:** `.claude/agents/agent-name.md` - Version controlled, shared with team
- **Plugin:** `plugins/plugin-name/agents/agent-name.md` - Bundled in a plugin

When creating an agent in a plugin, drop the `.md` file into the plugin's `agents/` directory. **Do not** update `plugin.json` — every `.md` file under `agents/` is auto-discovered by Claude Code.

**Do not add the `agents` key to `plugin.json` for default-path agents.** Writing the key (even to add a single entry) OVERRIDES auto-discovery: the declared list becomes the complete set and every agent not listed becomes invisible. See `.claude/rules/plugin-development.md` for the 2026-03-17 / 2026-04-12 incident history.

The `agents` key exists for non-default agent paths. It accepts one file path as a string or multiple file paths as an array. Because declaring it replaces the default scan, include every default-path agent that must remain available.

Custom skill directories add to the default `skills/` scan. Custom `agents` and `commands` paths replace their default directories.

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
5. Confirm plugin.json was NOT modified for default-path plugin agents (auto-discovered)
6. Validate the created file

## Usage

This agent is for demonstration purposes only. When creating real agents, include only the fields you need.

## Sources

- [Claude Code Documentation](https://code.claude.com/docs/en/sub-agents.md) (accessed 2026-01-28)
- [Agent Creator Skill](../../skills/agent-creator/SKILL.md)
- [Plugin Creator Validation Scripts](../../scripts/README.md)
- SOURCE: <https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields> (accessed 2026-09-24)
- SOURCE: <https://code.claude.com/docs/en/plugins-reference#agents> (accessed 2026-09-24)
