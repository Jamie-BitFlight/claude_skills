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

## `skills:` — Externally-Sourced Plugins Are Forbidden

An agent's `skills:` frontmatter list preloads full skill content at subagent startup. If a listed
skill is absent from the host — for example a plugin the user hasn't installed — the entry is a
**silent no-op**: no error, no warning, the agent simply starts without that content. This differs
from `tools:`, which resolves an unknown name to zero tools with the same silence but a different
failure surface (a missing capability vs. missing context).

Never list a skill from an externally-sourced plugin (a marketplace entry whose `source` is
`github`, `git-subdir`, `url`, or `npm` rather than a local repo-relative path) in any agent's
`skills:` field. A user who hasn't installed that plugin gets an agent that silently loses the
skill's guidance with no signal anywhere — the default state for fresh clones and CI unless that
plugin is explicitly wired into `enabledPlugins`. Reference externally-sourced skills only in
prose (a `Skill(skill="...")` call inside a SKILL.md body, a routing table) where a dangling name
degrades to a no-op the reading agent can reason about, never in frontmatter that preloads at
startup with no fallback.

SOURCE: confirmed 2026-08-19 during the Astral plugin adoption migration — this is why that
migration kept `python-engineering:uv`/`:ty`/`:ruff` as thin first-party wrapper skills rather
than repointing agent frontmatter at the externally-sourced `astral:uv`/`:ty`/`:ruff`.

## Multi-Ecosystem Frontmatter Preservation

A SKILL.md or agent file whose frontmatter has a top-level `mcp:` key also targets OpenCode. `mcp:`
is currently the only known ecosystem-owned field. Treat it and its nested content as opaque: copy
it verbatim when rewriting frontmatter, never rewrite, rename, or reorder its sub-keys, never
validate them against Claude Code schemas.

Any other unrecognized top-level key — one that is neither `mcp:` nor a Claude Code field — gets
flagged as UNKNOWN and reported to the user, never silently stripped or discarded.

```yaml
mcp:
  server: ./scripts/mcp_server.py
  transport: stdio
```

