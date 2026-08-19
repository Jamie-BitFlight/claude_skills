---
paths:
- '**/SKILL.md'
- '**/agents/**/*.md'
- '**/commands/**/*.md'
---

# Frontmatter Requirements

## Skills

- `name`: Required — lowercase, hyphens, must match directory name, satisfies `^[a-z][a-z0-9-]*$`
- `description`: Optional (uses first paragraph if omitted)
- `tools`: Must be comma-separated string — `Read, Grep, Glob` — not a YAML array

## Agents

- `name`: Required — lowercase, hyphens, max 64 chars
- `description`: Required — include trigger keywords, max 1024 chars
- `model`: Must be `sonnet`, `opus`, `haiku`, or `inherit` if specified
- `tools`: Must be comma-separated string (not YAML array)
- No YAML multiline indicators (`>-`, `|-`, `>`, `|`) in any field

## Commands

- `description`: Required
- `allowed-tools`: Must be comma-separated string (not YAML array)

## Validator Auto-Fix

Run after writing or editing any frontmatter file:

```bash
uvx skilllint@latest check --fix {path}
```

The validator auto-adds `name:` derived from the directory name when absent (plugin skills only).

**SOURCE:** `skilllint` and [agentskills.io specification](https://agentskills.io/specification)

## `skills:` — Never List an Externally-Sourced Plugin's Skill

An agent's `skills:` field preloads skill content at subagent startup. A listed skill absent from
the host (an uninstalled plugin) is a **silent no-op** — no error, agent just starts without that
content. Never name a skill from an externally-sourced plugin (a marketplace entry whose `source`
is `github`, `git-subdir`, `url`, or `npm`, not a local path) in `skills:`. Reference such skills
only in prose (a `Skill(skill="...")` call, a routing table), where a dangling name degrades to a
harmless no-op instead of silently starting an agent with no fallback and no signal.

## Multi-Ecosystem Frontmatter Preservation

A top-level `mcp:` key also targets OpenCode. Treat it and its nested content as opaque: copy
verbatim, never rewrite/rename/reorder sub-keys, never validate against Claude Code schemas.

```yaml
mcp:
  server: ./scripts/mcp_server.py
  transport: stdio
```

Any other unrecognized top-level key gets flagged as UNKNOWN and reported to the user — never
silently stripped.
