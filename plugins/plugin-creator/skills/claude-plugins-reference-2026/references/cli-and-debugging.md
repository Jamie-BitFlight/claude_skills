# Plugin CLI and Debugging

Read this reference when installing, enabling, validating, or troubleshooting a Claude Code plugin.

Use `claude plugin <command> <plugin> --scope <user|project|local>` for `install`, `uninstall`,
`enable`, and `disable`. `update` also accepts managed scope. Use `claude plugin list --json` for
machine-readable installed state and add `--available` to include marketplace candidates.

Prefer the live CLI help over copied option tables:

```bash
claude plugin --help
claude plugin install --help
```

Validate and test without installing:

```bash
claude plugin validate ./path/to/plugin
claude --plugin-dir ./path/to/plugin
claude --debug
```

`--plugin-dir` takes precedence over an installed plugin with the same name for that session,
except a marketplace plugin force-enabled by managed settings.

Common diagnostics:

| Symptom | Check |
| --- | --- |
| Plugin does not load | Run `claude plugin validate` and `claude --debug` |
| Default agents disappear | Remove the `agents` field or include every retained default-path agent |
| Commands do not appear | Keep `commands/` at the plugin root |
| Hooks do not fire | Check executable permissions and hook logs |
| MCP process cannot find files | Resolve bundled paths through `${CLAUDE_PLUGIN_ROOT}` |
| LSP reports missing executable | Install the language-server binary separately |

SOURCE: [Plugins reference](https://code.claude.com/docs/en/plugins-reference) and [Create plugins](https://code.claude.com/docs/en/plugins) (accessed 2026-09-24)
