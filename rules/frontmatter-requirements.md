# Frontmatter Requirements

## Skills

- Claude Code runtime: every field is optional. An omitted `name` uses the directory name; an
  omitted `description` uses the first non-empty markdown line.
- Portable Agent Skills: `name` and `description` are required. `name` is 1-64 lowercase ASCII
  letters (`a-z`), digits (`0-9`), or hyphens, with no leading, trailing, or consecutive hyphen,
  and must match the directory exactly. `description` must be non-empty and at most 1024
  characters; describing both what the skill does and when to use it is a SHOULD, not a MUST.
- `allowed-tools`: Claude Code accepts a space- or comma-separated string or YAML list. Portable
  Agent Skills accepts a space-separated string only and marks the field experimental. In Claude
  Code it pre-approves listed tools rather than restricting all other tools.

## Agents

- Project, user, and managed agents require `name` and `description` to load. `name` must not start
  with `-` or contain `:`.
- Plugin agents fall back to the file path for the name when `name` is absent. If frontmatter does
  not parse, they also use a generic plugin description and ignore the invalid fields.
- Provide both `name` and `description` for reliable routing even where plugin loading can fall back.
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
