## Plugin Python — PEP 723 Scripts, No uv Workspace

**This repo has NO uv workspace.** Do not add `[tool.uv.workspace]` entries; plugin sub-projects are not workspace members. Plugin MCP servers are PEP 723 self-resolving scripts, not installed projects.

- **Runtime source of truth** is the script's inline `# /// script … dependencies = [...] # ///` block — `uv` resolves it at launch, with no `pyproject.toml`, `uv.lock`, or workspace lookup. See the PEP 723 shebang and block in [`run_backlog_server.py`](plugins/development-harness/scripts/run_backlog_server.py), launched via the `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/…` command in [`plugin.json`](plugins/development-harness/.claude-plugin/plugin.json). `${CLAUDE_PLUGIN_ROOT}` resolves in the installed plugin cache, not the source tree.
- **Plugins ship zipped, outside this repo** — no source-tree `uv.lock` is consulted at runtime.
- **Root dev-dependencies mirror the script blocks**, solely so `ty`, `ruff`, and the IDE/LSP (which don't read PEP 723) can resolve imports while editing here — tooling convenience, not the runtime or distribution path. See `[dependency-groups] dev` in [`pyproject.toml`](pyproject.toml).

### Adding a new plugin MCP server

1. Declare dependencies in the script's PEP 723 frontmatter (runtime source of truth).
2. Mirror them into the root `[dependency-groups] dev` so `ty`, `ruff`, and the IDE resolve them.

Do not create a per-plugin `pyproject.toml` sub-project or a per-plugin `uv.lock`.

This extends to every directory a script imports (`backlog_core/`, `dh_core/`, `sam_schema/`,
etc.): they have `__init__.py` and dotted imports for internal organization, but are not
distributable packages — never build, bundle, publish, or add a `pyproject.toml` beside them.
Doing so creates two dependency sources of truth (the script's own inline deps vs. a new
package's) that silently diverge — a split-brain, not a cleanup.

### Invariant

```bash
git ls-files | grep uv.lock
```

Must return only the root `uv.lock`. A per-plugin `uv.lock` is never read — the runtime self-resolves via PEP 723 and the linters use the root dev group — so it would only drift from the real dependency set.

---

## ty Type Checker Errors

Fix the code to satisfy the type checker — inline `# ty: ignore` suppressions are prohibited.
Config-level relaxation via `[[tool.ty.overrides]]` in `pyproject.toml` is allowed, but only for a
case matching one of the acceptable-exception categories in
[`linting-exceptions.md`](rules/linting-exceptions.md) — cite the matching category by name in a
comment beside the override (the SOLID-corpus override in `pyproject.toml` shows the pattern).
Load `python-engineering:ty` for suppression syntax, diagnostics, and unresolved-import/environment
resolution. Load `python-engineering:python3-typing` for the boundary-validation pattern
(`model_validate()` on raw input) instead of passing untyped values to typed constructors.

### `unresolved-import` errors

When `ty` reports `unresolved-import` for a module that genuinely exists on disk, the module's
directory is almost always missing from `[tool.ty.environment] extra-paths` in `pyproject.toml`.
Add the directory there, then re-verify with `uv run ty check <path>` before investigating the
importing code itself. A root-level `ty.toml`, if one exists, takes precedence over
`pyproject.toml`'s `[tool.ty]` table — check for one first if an `extra-paths` addition doesn't
resolve the error. For the related `unresolved-attribute` failure on a `ModuleType` (a different
symptom, same environment-resolution root cause), see [AGENTS.md's "Common ty Failure
Patterns"](AGENTS.md#common-ty-failure-patterns).

### `unresolved-import` on a PEP 723 script, specifically in the language server

If the file is a PEP 723 script (has a `# /// script … # ///` block, per the pattern above) and
the false `unresolved-import` shows up in **live editor/LSP diagnostics** but `uv run ty check
<path>` passes clean on the same file, this is **not** an `extra-paths` problem — do not add
entries for it. Confirmed root cause (evidence trail and minimal 7-line reproduction in the PR that
added this note): ty 0.0.75–0.0.80 type-checks a `# /// script` file as an isolated single-file
project and never consults `[tool.ty.environment]` (from either `pyproject.toml` or `ty.toml`) for
it — `extra-paths`, `root`, and every other environment key are silently ignored for that file,
regardless of where they're declared. Tracked upstream, open, unfixed as of ty 0.0.80:
<https://github.com/astral-sh/ty/issues/691>.

The only thing that resolves this for a PEP 723 file is the `VIRTUAL_ENV` environment variable
(config-file settings and `[[tool.ty.overrides]]` cannot carry an `environment` table — schema only
accepts `include`/`exclude`/`rules`/`analysis`). `uv run ty check` already works because `uv run`
sets `VIRTUAL_ENV`. The Astral plugin's bundled language server does not: its `lspServers.ty` entry
launches `uvx ty@latest server` with no ambient `uv run`, no CLI flags (`ty server --help` takes
only `-h`), and no supported way to override or add args to a single plugin-provided LSP server
without disabling the whole plugin. This repo's fix is `.claude/settings.json`'s `env.VIRTUAL_ENV =
".venv"` — a relative path so it resolves correctly from whichever project root Claude Code (or a
`.claude/worktrees/*` worktree) launches the server from, once `uv sync` has created that
directory's own `.venv` per the Environment Setup step in `AGENTS.md`. See
[`docs/linting-and-type-checking.md`](docs/linting-and-type-checking.md) for the trustworthy-channel
guidance and [`tests/test_ty_pep723_environment.py`](tests/test_ty_pep723_environment.py) for the
regression coverage.
