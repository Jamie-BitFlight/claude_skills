# Python Development Rules

## Plugin Python — PEP 723 Scripts, No uv Workspace

**This repo has NO uv workspace.** Do not add `[tool.uv.workspace]` entries; plugin sub-projects are not workspace members. Plugin MCP servers are PEP 723 self-resolving scripts, not installed projects.

- **Runtime source of truth** is the script's inline `# /// script … dependencies = [...] # ///` block — `uv` resolves it at launch, with no `pyproject.toml`, `uv.lock`, or workspace lookup. See the PEP 723 shebang and block in [`run_backlog_server.py`](./../../plugins/development-harness/scripts/run_backlog_server.py), launched via the `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/…` command in [`plugin.json`](./../../plugins/development-harness/.claude-plugin/plugin.json). `${CLAUDE_PLUGIN_ROOT}` resolves in the installed plugin cache, not the source tree.
- **Plugins ship zipped, outside this repo** — no source-tree `uv.lock` is consulted at runtime.
- **Root dev-dependencies mirror the script blocks**, solely so `ty`, `ruff`, and the IDE/LSP (which don't read PEP 723) can resolve imports while editing here. Tooling convenience only — not the runtime or distribution path. See `[dependency-groups] dev` in [`pyproject.toml`](./../../pyproject.toml).

### Adding a new plugin MCP server

1. Declare dependencies in the script's PEP 723 frontmatter (runtime source of truth).
2. Mirror them into the root `[dependency-groups] dev` so `ty`, `ruff`, and the IDE resolve them.

Do not create a per-plugin `pyproject.toml` sub-project or a per-plugin `uv.lock`.

### Invariant

```bash
git ls-files | grep uv.lock
```

Must return only the root `uv.lock`. A per-plugin `uv.lock` is never read — the runtime self-resolves via PEP 723 and the linters use the root dev group — so it would only drift from the real dependency set.
