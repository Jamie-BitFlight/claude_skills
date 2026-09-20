# Plugin.json Requirements

## Manifest Location

`plugin.json` is always at `<plugin-root>/.claude-plugin/plugin.json` (or `.cursor-plugin/plugin.json` when developing a Cursor plugin, or both).

## Path Rules

- All paths must start with `./`
- See `plugin-development.md`'s "plugin.json Auto-Discovery Rules" section — declaring `agents` overrides auto-discovery entirely. Omit the key to use auto-discovery for all agents in `agents/`.
- `agents` field must be an array of individual file paths — `["./agents/file.md"]` — not a directory string `"./agents/"`
- Plugins cannot reference files outside their directory (`../shared-utils` fails after installation)

## Validate After Editing

```bash
uvx skilllint@latest check {plugin-path}
claude plugin validate {plugin-directory}
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `agents: Invalid input` | Used `"./agents/"` instead of array | Change to `["./agents/file.md"]` |
| `name: Required` | Missing name field | Add `"name": "plugin-name"` |
| Invalid JSON syntax | Malformed JSON | Validate with `python3 -m json.tool plugin.json` |
