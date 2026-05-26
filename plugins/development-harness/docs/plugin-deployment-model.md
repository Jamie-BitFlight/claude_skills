# Plugin Deployment Model — The Zip-and-Move Test

## The test to apply before any change to a plugin script

Before designing or implementing any change to a script inside a plugin directory, apply this test:

> **If I zip this plugin directory, move it to a completely different path on a different machine, and unzip it — does this script still work?**

If the answer is no, the design is wrong for a distributed plugin. This test catches every cross-boundary dependency before it becomes a runtime failure on a user's machine.

## What survives the zip-and-move

- Paths constructed from `Path(__file__).parent` or `Path(__file__).parents[N]` that stay **within the plugin directory tree**
- Standard library imports
- Packages declared in the script's PEP 723 dependencies or the plugin's declared package dependencies
- `${CLAUDE_PLUGIN_ROOT}` — resolves to wherever the plugin was unzipped

## What breaks the zip-and-move

- Any `sys.path.insert` that reaches **outside** the plugin directory (e.g. to `.claude/utilities/`, to a sibling plugin, to the repo root)
- Hardcoded paths to development repository locations
- Imports that rely on a particular directory structure that only exists in the source repository
- Assumptions that other plugins are installed at a known relative path

## How Claude Code installs plugins

Plugins are copied into a cache directory:

```text
~/.claude/plugins/cache/<marketplace>/<plugin-name>/<version>/
```

This cache directory has no git root, no `.claude/utilities/`, no sibling plugins from the development repo, and no connection to the path where the plugin was authored. The environment variable `${CLAUDE_PLUGIN_ROOT}` resolves to this cache directory.

## The cross-boundary problem

Scripts in `.claude/skills/*/scripts/` and `.claude/utilities/` run in the user's home directory and can reach `.claude/utilities/` as a sibling. Plugin scripts in `plugins/*/scripts/` cannot — after installation they are inside the plugin cache with no path to `.claude/`.

A utility shared between a `.claude/` script and a plugin script cannot live in a single file. Options:

1. **Duplicate inside each plugin** — copy the utility into the plugin's own `scripts/` directory. Accept the duplication.
2. **Publish as a package** — declare it as a PEP 723 dependency. Works everywhere.
3. **Split scope** — `.claude/` scripts share their utility; plugin scripts each carry their own copy.

## RT-ICA condition for cross-boundary items

Any backlog item proposing to share code or utilities across the `.claude/` and `plugins/` boundary must include this condition in its RT-ICA:

> "All affected scripts share the same deployment context after installation" | AVAILABLE or MISSING

If scripts span `.claude/` and `plugins/`, this condition is MISSING. The item must be re-scoped before planning proceeds.

## Quick reference — does this path survive?

| Path type | Survives? |
|---|---|
| `Path(__file__).parent / "utils.py"` (sibling in same plugin) | Yes |
| `Path(__file__).parents[1] / "shared.py"` (within plugin bundle) | Yes — if that file is in the bundle |
| `Path(__file__).parents[3] / ".claude" / "utilities" / "rich_utils.py"` | No — `.claude/` doesn't exist in the cache |
| `sys.path.insert(0, "/home/user/repos/claude_skills/.claude/utilities")` | No — hardcoded dev path |
| `importlib.import_module("rich")` (declared PEP 723 dep) | Yes |

SOURCE: Claude Code plugin caching behaviour — `plugin-creator:claude-plugins-reference-2026` skill (accessed 2026-05-24).
