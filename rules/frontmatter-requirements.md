# Frontmatter Requirements

## Skills

- Claude Code runtime: every field is optional. An omitted `name` uses the directory name; an
  omitted `description` uses the first non-empty markdown line.
- Portable Agent Skills: `name` and `description` are required. `name` is 1-64 Unicode lowercase
  alphanumeric characters or hyphens, with no leading, trailing, or consecutive hyphen, and must
  match the directory after NFKC normalization. `description` must be non-empty and at most 1024
  characters; describing both what the skill does and when to use it is a SHOULD, not a MUST.
- `allowed-tools`: Claude Code accepts a space- or comma-separated string or YAML list. Portable
  Agent Skills accepts a space-separated string only and marks the field experimental. In Claude
  Code it pre-approves listed tools rather than restricting all other tools.

SOURCE: <https://agentskills.io/specification.md>,
<https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/validator.py>, and
<https://code.claude.com/docs/en/skills#frontmatter-reference> (accessed 2026-09-24)

## Agents

- `name`: Required — must not start with `-` or contain `:`
- `description`: Required — state when Claude should delegate
- `model`: Accepts `sonnet`, `opus`, `haiku`, `fable`, `inherit`, or a full model ID
- `tools` and `disallowedTools`: Accept a comma-separated string or YAML list
- `hooks`, `mcpServers`, and `permissionMode` are valid for project/user agents but ignored for
  plugin-shipped agents

## Commands

- `description`: Required
- `allowed-tools`: Accepts a documented string or YAML list

## Validator Auto-Fix

Run after writing or editing any frontmatter file:

```bash
uvx skilllint@latest check --fix {path}
```

The validator may add `name:` under this repository's portable-profile checks; Claude Code itself
does not require the field.

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
