---
name: example-skill
description: Illustrative Claude Code skill configuration. Use when learning the basic SKILL.md shape; follow the canonical runtime reference for the current field inventory.
argument-hint: '[topic]'
allowed-tools: Read, Grep, Glob, WebFetch
model: sonnet
user-invocable: true
disable-model-invocation: false
hooks:
  PostToolUse:
  - matcher: Read
    hooks:
    - type: command
      command: echo 'File was read'
      timeout: 5
---

# Example Skill

This skill illustrates a subset of Claude Code runtime frontmatter.

## Purpose

See [the canonical Claude Code inventory](../../../skills/claude-skills-overview-2026/SKILL.md#claude-code-frontmatter-fields) for all current fields.

## Field Descriptions

| Field                      | Type    | Purpose                          | Constraints                     | Default         |
| -------------------------- | ------- | -------------------------------- | ------------------------------- | --------------- |
| `name`                     | string  | Display name                     | Runtime-defined string          | directory name  |
| `description`              | string  | When to load this skill          | Clear routing guidance          | first non-empty markdown line |
| `argument-hint`            | string  | Autocomplete hint for `/` menu   | Brief hint text                 | none            |
| `allowed-tools`            | string/list | Tools without permission prompts | Space/CSV string or YAML list | none |
| `model`                    | string  | Model when skill is active       | sonnet, opus, haiku, or inherit | inherit         |
| `user-invocable`           | boolean | Show in `/` menu                 | true or false                   | true            |
| `disable-model-invocation` | boolean | Prevent Claude auto-loading      | true or false                   | false           |
| `hooks`                    | object  | Scoped hooks for skill lifecycle | Valid hook configuration object | none            |

`context` and `agent` are current Claude Code runtime fields.

## Validation

Validate your skill using:

```bash
# Frontmatter and structure validation (checks token complexity, links, references)
uvx skilllint@latest check ./path/to/skill/SKILL.md

# Plugin validation (if skill is part of a plugin)
claude plugin validate ./path/to/plugin/
```

## Common Validation Errors

| Error                                  | Cause                         | Fix                              |
| -------------------------------------- | ----------------------------- | -------------------------------- |
| `model must be sonnet/opus/haiku`      | Invalid model name            | Use valid model identifier       |
| `Skill body exceeds 500 lines`         | Skill is too large            | Split into multiple skills       |
| `Internal link points to missing file` | Referenced file doesn't exist | Create file or fix path          |
| `Description too short`                | Less than 20 characters       | Add trigger keywords and context |

## Usage

This skill is for demonstration purposes only. When creating real skills, include only the fields you need.

## Skill Location

Skills can be located in:

- **User-level:** `~/.claude/skills/skill-name/SKILL.md` - Available across all projects
- **Project-level:** `.claude/skills/skill-name/SKILL.md` - Version controlled, team shared
- **Plugin:** `plugins/plugin-name/skills/skill-name/SKILL.md` - Bundled in a plugin

## Sources

- [Skills Reference](https://code.claude.com/docs/en/skills.md) (accessed 2026-01-28)
- [Skills Overview](../../../skills/claude-skills-overview-2026/SKILL.md) - Claude Code runtime reference
- [Plugin Creator Validation Scripts](../../../scripts/README.md)
- SOURCE: <https://code.claude.com/docs/en/skills#frontmatter-reference> (accessed 2026-09-24)
