# Agent Frontmatter Schema Reference

> **Canonical source**: Load `/plugin-creator:claude-subagent-reference` for the complete
> field specification (all fields with descriptions, env vars, and examples).
>
> This file contains creation-specific additions not covered by that reference.

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> (accessed 2026-05-28)

---

## Creation-specific constraints

These points are not in the canonical reference but matter during authoring:

### YAML multiline indicator bug

Do NOT use YAML multiline indicators (`>-`, `|`, `|-`, `>`) for `description`. Claude Code's
indexer does not parse them correctly — the description displays as the literal `>-` characters
instead of the content.

```yaml
# WRONG — displays as ">-"
description: >-
  This agent reviews code for quality issues.

# CORRECT — single-line string
description: 'This agent reviews code for quality issues.'
```

### MCP tool names and server patterns

Name each MCP tool by its exact registered name, case-sensitive. Grant a whole server with
`mcp__<server>__*` or `mcp__<server>` — both forms grant every tool that server exposes and
compose with named tools. A plugin-bundled server registers as
`mcp__plugin_<plugin-name>_<server-name>`.

```yaml
# CORRECT — named tool
tools: Read, mcp__Ref__ref_read_url

# CORRECT — every tool from one server, plus Read
tools: Read, mcp__plugin_dh_backlog__*

# WRONG — wrong case matches no tool and is dropped
tools: Read, mcp__ref__ref_read_url
```

An entry that matches no live tool is dropped and the rest of the grant still resolves. When every
entry resolves to nothing the agent refuses to launch, reporting that it "would be spawned with
zero tools" and naming the unresolved entries.

A server pattern grants nothing while that server is disconnected. An agent whose `tools:` list
contains only MCP entries therefore cannot be invoked at all until the server returns — give it at
least one non-MCP tool unless that runtime dependency is intended.

---

## Validation

```bash
# Validate single agent file
uvx skilllint@latest check path/to/agent.md

# Auto-fix common issues (YAML arrays → comma-separated strings, etc.)
uvx skilllint@latest check --fix path/to/agent.md

# Validate full plugin (when agent is inside a plugin)
claude plugin validate path/to/plugin/
```
