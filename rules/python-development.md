## Plugin Python — PEP 723 Scripts, No uv Workspace

**This repo has NO uv workspace.** Do not add `[tool.uv.workspace]` entries; plugin sub-projects are not workspace members. Plugin MCP servers are PEP 723 self-resolving scripts, not installed projects.

- **Runtime source of truth** is the script's inline `# /// script … dependencies = [...] # ///` block — `uv` resolves it at launch, with no `pyproject.toml`, `uv.lock`, or workspace lookup. See the PEP 723 shebang and block in [`run_backlog_server.py`](plugins/development-harness/scripts/run_backlog_server.py), launched via the `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/…` command in [`plugin.json`](plugins/development-harness/.claude-plugin/plugin.json). `${CLAUDE_PLUGIN_ROOT}` resolves in the installed plugin cache, not the source tree.
- **Plugins ship zipped, outside this repo** — no source-tree `uv.lock` is consulted at runtime.
- **Root dev-dependencies mirror the script blocks**, solely so `ty`, `ruff`, and the IDE/LSP (which don't read PEP 723) can resolve imports while editing here — tooling convenience, not the runtime or distribution path. See `[dependency-groups] dev` in [`pyproject.toml`](pyproject.toml).

### Adding a new plugin MCP server

1. Declare dependencies in the script's PEP 723 frontmatter (runtime source of truth).
2. Mirror them into the root `[dependency-groups] dev` so `ty`, `ruff`, and the IDE resolve them.

Do not create a per-plugin `pyproject.toml` sub-project or a per-plugin `uv.lock`. See [Plugin project architecture](../docs/plugin-project-architecture.md) for the product-vs-development-policy boundary and extraction procedure.

This extends to every directory a script imports (`backlog_core/`, `dh_core/`, `sam_schema/`,
etc.): they have `__init__.py` and dotted imports for internal organization, but are not
distributable packages — never build, bundle, publish, or add a `pyproject.toml` beside them.
Doing so creates two dependency sources of truth (the script's own inline deps vs. a new
package's) that silently diverge — a split-brain, not a cleanup.

### Splitting a PEP 723 script

Split a script that approaches or exceeds ~500 physical lines, per the shared Module Hygiene policy in
[`standards-for-python-development`](plugins/python-engineering/skills/standards-for-python-development/SKILL.md). For how the
resulting modules import each other, see `PEP723.md` in `python-engineering:python3-core`;
`sam_schema/cli.py` is this repo's worked instance of the package-relative form.

---

## ty Type Checker Errors

### `unresolved-import` errors

A PEP 723 script importing its own modules is the exception, and is fixed by `root` inside the
script's block — see `PEP723.md` in `python-engineering:python3-core`, and
`python-engineering:ty`. Everywhere else: when `ty` reports `unresolved-import` for a module that
genuinely exists on disk, the module's directory is almost always missing from
`[tool.ty.environment] extra-paths` in `pyproject.toml`.
Add the directory there, then re-verify with `uv run ty check <path>` before investigating the
importing code itself. A root-level `ty.toml`, if one exists, takes precedence over
`pyproject.toml`'s `[tool.ty]` table — check for one first if an `extra-paths` addition doesn't
resolve the error. For the related `unresolved-attribute` failure on a `ModuleType` (a different
symptom, same environment-resolution root cause), see
[docs/linting-and-type-checking.md](docs/linting-and-type-checking.md#common-ty-failure-patterns).

---

## Python Workflow Routing

Use the owning entry point for the task rather than loading shared standards as a substitute for a workflow:

| Task | Entry point |
|---|---|
| Python implementation, refactoring, or behavioral change | `/python-engineering:orchestrate` |
| Broad quality, technical-debt, Pythonic, ecosystem, or modernization audit | `/python-engineering:python-quality-audit` |
| Bounded conventional code review | `/python-engineering:review` |
| Debugging or unexpected Python behavior | `/python-engineering:debug` |

These routes consume the shared `standards-for-python-development` policy and add the appropriate adversarial scope tracing, specialists, evidence gathering, or review behavior. Load the shared standards directly only when a caller specifically needs the policy reference rather than an execution workflow.

## Repo Overrides on the Python Skills

The plugin carries the Python craft. This repo adds two rules it cannot carry, because both are about this checkout's layout:

- Before writing a new shared module, read the PEP 723 dependency block of the scripts that will
  import it (`grep dependencies plugins/*/scripts/*.py`) and reuse what is declared.
- Before writing a script, CLI, or MCP server, read
  [docs/cli-output-conventions.md](docs/cli-output-conventions.md).
