# Frontmatter Requirements

## Skills

- `name`: Required — lowercase, hyphens, must match directory name, satisfies `^[a-z][a-z0-9-]*$`
- `description`: Optional (uses first paragraph if omitted)
- `allowed-tools`: comma-separated for Claude Code — `Read, Grep, Glob`; space-delimited when the
  skill targets multiple platforms. Never a YAML array; that form conforms to neither delimiter
  convention. Grants permission for the listed tools while the skill is active; it does not
  restrict which tools are callable (see the `plugin-creator:claude-skills-overview-2026` skill for
  the full schema).

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

The validator auto-adds `name:` derived from the directory name when absent, confirmed for both plugin-bundled and project-level (`.claude/skills/`) SKILL.md files.

## `skills:` — Never List an Externally-Sourced Plugin's Skill

An agent's `skills:` field preloads skill content at subagent startup. Never name a skill from an
externally-sourced plugin (a marketplace entry whose `source`
is `github`, `git-subdir`, `url`, or `npm`, not a local path) in `skills:` — a listed skill absent
from the host (an uninstalled plugin) has no confirmed behavior. Reference such skills
only in prose (a routing table entry, an inline mention) — a name an agent tries to activate on
demand fails visibly instead.

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
