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

## Validation

Validate your agent using:

```bash
# Frontmatter validation
uvx skilllint@latest check ./path/to/agent.md

# Plugin validation (if agent is part of a plugin)
claude plugin validate ./path/to/plugin/
```

## Agent Location

Agents can be located in:

- **User-level:** `~/.claude/agents/agent-name.md` - Personal agents available across all projects
- **Project-level:** `.claude/agents/agent-name.md` - Version controlled, shared with team
- **Plugin:** `plugins/plugin-name/agents/agent-name.md` - Bundled in a plugin

Plugin agents in the default `agents/` directory are auto-discovered while `plugin.json` omits the `agents` field. An explicit `agents` field replaces that default scan, so it must list every agent that should load.

## Usage

This agent is for demonstration purposes only. When creating real agents, include only the fields you need.

Return `STATUS: DONE` with the requested demonstration result and `Findings: None` when there is nothing to report. Return `STATUS: BLOCKED` with the specific missing input when the example task cannot proceed.

## Sources

- [Claude Code Documentation](https://code.claude.com/docs/en/sub-agents.md) (accessed 2026-01-28)
- [Agent Creator Skill](../../skills/agent-creator/SKILL.md)
- [Plugin Creator Validation Scripts](../../scripts/README.md)
- SOURCE: <https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields> (accessed 2026-09-24)
- SOURCE: <https://code.claude.com/docs/en/plugins-reference#agents> (accessed 2026-09-24)
