# Plugin Manifest and Components

Read this reference when defining `.claude-plugin/plugin.json`, choosing component paths, or
debugging component discovery.

## Manifest Boundary

Claude Code can load a plugin without `.claude-plugin/plugin.json` when all components use default
locations. Add the manifest for stable identity, metadata, or custom component paths. Keep every
other component at the plugin root, not inside `.claude-plugin/`.

```text
plugin-root/
├── .claude-plugin/plugin.json
├── skills/<name>/SKILL.md
├── agents/*.md
├── hooks/hooks.json
├── .mcp.json
└── .lsp.json
```

`name` is the manifest identity. Metadata fields include `version`, `description`, `author`,
`homepage`, `repository`, `license`, and `keywords`.

## Component Paths

| Field | Value | Discovery effect |
| --- | --- | --- |
| `commands` | string or array | Replaces `commands/` |
| `agents` | string or array | Replaces `agents/` |
| `skills` | string or array | Adds to `skills/` |
| `hooks` | path or object | Configures hooks |
| `mcpServers` | path or object | Configures MCP servers |
| `outputStyles` | string or array | Replaces `output-styles/` |
| `lspServers` | path or object | Configures LSP servers |
| `monitors` | string or array | Configures monitors |
| `userConfig` | object | Declares enable-time values |
| `channels` | array | Declares MCP-backed channels |

Component paths are plugin-root-relative, begin with `./`, and cannot escape the plugin root.
When a replacement field is present, list every default-path component that must remain loaded.

SOURCE: [Plugins reference: component path fields](https://code.claude.com/docs/en/plugins-reference#component-path-fields) (accessed 2026-09-24)

## Component Distinctions

- Skills use `skills/<name>/SKILL.md` and invoke as `/plugin-name:skill-name`. A one-skill plugin may
  use root `SKILL.md`.
- Agents load recursively from `agents/`; subfolders contribute to the scoped name. Valid `name`
  and `description` fields provide stable identity and routing.
- Plugin-agent `hooks`, `mcpServers`, and `permissionMode` fields are ignored. `isolation: worktree`
  is supported. See `../../claude-subagent-reference/SKILL.md` for the canonical agent schema.
- Hooks default to `hooks/hooks.json`. See `../../hooks-guide/SKILL.md` for hook behavior.
- MCP servers default to `.mcp.json`; LSP servers default to `.lsp.json`. LSP binaries must be
  installed separately.
- Read [monitors.md](./monitors.md) for monitors and [user-config.md](./user-config.md) for
  `userConfig` and channels.

SOURCE: [Plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-24)
