# Agent Plugin Host Boundaries

Read this reference before choosing a plugin manifest or adding host-specific fields. It identifies
the package boundary; the linked host references own detailed schemas and hook behavior.

## Portable Agent Plugins 1.0

- Put the required closed-schema manifest at root `plugin.json`; `$schema` and `name` are required.
- Put host data under reverse-domain keys in `extensions`.
- Discover skills from immediate children of root `skills/` and portable MCP configuration from
  root `mcp.json`.
- Hooks, agents, commands, settings, marketplaces, and invocation syntax remain host-specific.
- Keep paths inside the resolved plugin root. Portable MCP placeholders apply only to `args`, `env`
  values, and `cwd`; subprocesses receive `PLUGIN_ROOT` and `PLUGIN_DATA`.

SOURCE: [Agent Plugins specification](https://agent-plugins.org/specification.md) and
[1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json) (accessed 2026-09-24)

## Claude Code

Claude Code uses optional `.claude-plugin/plugin.json`, default component directories, and the
`/plugin-name:skill-name` namespace. It provides host-specific agents, commands, hooks, MCP/LSP,
marketplaces, runtime variables, and cache behavior.

Load `plugin-creator:claude-plugins-reference-2026` for package details,
`plugin-creator:claude-skills-overview-2026` for runtime skill fields, and
`plugin-creator:hooks-guide` for hook semantics.

SOURCE: [Create plugins](https://code.claude.com/docs/en/plugins) and
[Plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-24)

## OpenAI

Prefer portable root `plugin.json`, `skills/`, and `mcp.json`; place OpenAI-specific apps, hooks,
and presentation metadata under `extensions.com.openai`. `.codex-plugin/plugin.json` is a
compatibility overlay. When the root extension exists it replaces, rather than merges with, that
overlay. A recognized portable root manifest makes root `skills/` and `mcp.json` authoritative.

Read [OpenAI Codex hooks](../../hooks-guide/references/openai-codex.md) for OpenAI hook trust and
event distinctions.

SOURCE: [Build plugins](https://developers.openai.com/plugins/build/plugins),
[Build skills](https://developers.openai.com/plugins/build/skills), and
[Hooks](https://learn.chatgpt.com/docs/hooks) (accessed 2026-09-24)

## OpenCode Skill Extension

OpenCode can attach MCP servers through an `mcp:` block in SKILL.md frontmatter or an adjacent
`mcp.json`; the sidecar takes precedence. Preserve `mcp:` for OpenCode consumers, but exclude it
from portable upload and package boundaries that reject unknown fields.

```yaml
mcp:
  server-name:
    command: npx
    args: ["-y", "some-mcp-package"]
```

SOURCE: [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) skill MCP loader
(accessed 2026-03-06)

## Portable Skills Inside Plugins

The Agent Skills schema is independent of the plugin package schema. Load
`plugin-creator:agentskills` for portable frontmatter and client integration. Host runtime fields
belong only in files consumed by hosts that document them.
