# Plugin Caching and Runtime Paths

Read this reference when resolving plugin files, storing writable state, or explaining why an
installed edit is not visible.

Marketplace sources are copied into versioned cache directories unless their source mode loads in
place. `--plugin-dir`, marketplace link mode, and local-directory sources load in place;
`--plugin-url` fetches an archive for the session. Component paths cannot escape the resolved
plugin root in either mode.

Use these runtime variables:

| Variable | Use |
| --- | --- |
| `${CLAUDE_PLUGIN_ROOT}` | Read files bundled with the installed plugin |
| `${CLAUDE_PROJECT_DIR}` | Address the project where Claude Code started |
| `${CLAUDE_PLUGIN_DATA}` | Store dependencies, generated files, and caches that survive updates |

Do not write durable state into `${CLAUDE_PLUGIN_ROOT}`. Copied installations can be replaced on
update. Old copied versions are marked orphaned and removed by a background sweep after roughly 14
days; active sessions can finish against their original version. `Glob` and `Grep` skip orphaned
version directories.

For repository portability, keep dependencies inside the plugin boundary rather than traversing to
siblings. If a marketplace plugin must contain a larger tree, make that parent the marketplace
source root and declare component paths within it.

Installation scopes map to settings files:

| Scope | Settings file |
| --- | --- |
| `user` | `~/.claude/settings.json` |
| `project` | `.claude/settings.json` |
| `local` | `.claude/settings.local.json` |
| `managed` | managed settings |

SOURCE: [Plugins reference: plugin caching and file resolution](https://code.claude.com/docs/en/plugins-reference#plugin-caching-and-file-resolution) and [Create plugins](https://code.claude.com/docs/en/plugins) (accessed 2026-09-24)
