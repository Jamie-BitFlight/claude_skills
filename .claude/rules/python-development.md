# Python Development Rules

## Plugin Python — PEP 723 Self-Resolving Scripts, No Workspace

**CONSTRAINT — there is NO uv workspace in this repo. Do not add `[tool.uv.workspace]` entries. Plugin sub-projects are NOT workspace members.**

### Architecture

Plugin MCP servers are **PEP 723 self-resolving scripts**. The script shebang and inline `# /// script … dependencies = [...] # ///` block are the **runtime source of truth** for that server's dependencies. `uv` resolves and installs them at launch from the inline metadata — no `pyproject.toml`, no `uv.lock`, no workspace lookup.

SOURCE: [`./plugins/development-harness/scripts/run_backlog_server.py`](./../../plugins/development-harness/scripts/run_backlog_server.py) lines 1–15 — shebang `#!/usr/bin/env -S uv --quiet run --active --script` plus `# /// script … dependencies = [...] # ///` block.

The plugin's `.claude-plugin/plugin.json` (or `.mcp.json`) declares the runtime launch command. The MCP server is started via `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/<server>.py` — the `${CLAUDE_PLUGIN_ROOT}` path resolves at runtime inside the **installed plugin cache**, not the source tree.

SOURCE: [`./plugins/development-harness/.claude-plugin/plugin.json`](./../../plugins/development-harness/.claude-plugin/plugin.json) — `"command": "uv"`, `"args": ["run", "--script", "${CLAUDE_PLUGIN_ROOT}/scripts/run_backlog_server.py"]`.

Plugins are **zipped and distributed** outside this git repository. At runtime, no `uv.lock` from the source tree is consulted; `uv` resolves the script's inline `dependencies` list on each launch.

### Dev-Tooling Mirror (root pyproject.toml)

The same dependencies declared in a PEP 723 script's inline block are **also mirrored** into the root [`./pyproject.toml`](./../../pyproject.toml) `[dependency-groups] dev` list. This mirror exists **purely** so tools that cannot read PEP 723 inline metadata — `ty`, `ruff`, and IDE/LSP plugins — can resolve imports while editing inside this repo.

SOURCE: [`./pyproject.toml`](./../../pyproject.toml) `[dependency-groups] dev` — contains `fastmcp[tasks]`, `gitpython`, `pygithub`, `pydantic`, `marko`, `ruamel.yaml`, `tiktoken`, `typer`, and others that mirror the PEP 723 blocks across plugin scripts.

This mirror is a **developer-tooling convenience only**. It is not the runtime or distribution mechanism.

### Consequences — Follow These Exactly

- **No uv workspace.** The root `pyproject.toml` has no `[tool.uv.workspace]` section. Do not add one.
- **No per-plugin `uv.lock`.** A per-plugin lock file is never consulted at runtime (PEP 723 self-resolves) or by the linters (they use the root dev-dependency group). Remove any per-plugin `uv.lock` if one appears.
- **Adding a new plugin MCP server — do both steps:**
  1. Declare the server's dependencies in the script's PEP 723 `# /// script … dependencies # ///` frontmatter (source of truth for runtime).
  2. Mirror those same dependencies into the root `[dependency-groups] dev` in `./pyproject.toml` so `ty`, `ruff`, and the IDE can resolve imports.
  Do **not** create a per-plugin `pyproject.toml`-based sub-project or `uv.lock`.

### Verification Invariant

```bash
git ls-files | grep uv.lock
```

This command must return only `uv.lock` (the root lock file). Any additional `uv.lock` entry is a policy violation — per-plugin lock files are never consulted and must not exist.

**Rationale for this invariant:** Plugins are distributed as zipped archives and launched via PEP 723 self-resolving scripts. A per-plugin `uv.lock` inside the source tree would never be read by the runtime (`uv --script` ignores it), would never be read by the linters (they resolve from the root dev-dependency group), and would drift silently from the actual runtime dependency set.
