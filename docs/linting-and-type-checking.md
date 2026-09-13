# Linting and Type Checking

## Commands

For full uv/ty/ruff usage guidance beyond this repo's own overrides, load the `astral` plugin
skills (`/astral:uv`, `/astral:ty`, `/astral:ruff`) if installed, or see `docs.astral.sh` directly.

Run lint, format, and type checks through `prek` — it dispatches to ruff, ty, and every other
configured hook, and skips hooks that don't apply to the given files.

```bash
uv run prek run --files path/to/file.py    # Run ALL pre-commit hooks on specific files
uv run prek run --all-files                # Run ALL hooks on all files (slow)
uv run prek run ruff --files <file>        # Run one hook by id (e.g. ruff, ty) on specific files
uvx skilllint@latest check <path>          # Validate skill/agent/plugin frontmatter
```

## Type checking

This repository enforces **ty** (Astral) only, run via `prek`. `[tool.basedpyright]` is set to
`typeCheckingMode = "off"` so IDEs do not apply a second checker's defaults.

Suppression policy (inline `# ty: ignore` prohibited; config-level `[[tool.ty.overrides]]`
relaxation allowed only for the categories in `linting-exceptions.md`) and its rationale live in
`rules/astral-tool-overrides.md` and `rules/python-development.md` ("ty Type Checker Errors") —
both load on any `*.py`/`pyproject.toml`/`uv.lock` edit. The current override list itself lives in
`pyproject.toml [tool.ty]`, not restated here.

### Trustworthy channel: `uv run ty check` / CI, not a live LSP squiggle on a PEP 723 file

CI and `prek` gate on `uv run ty check`, which already resolves every PEP 723 script correctly (its
dependencies are mirrored into the root `[dependency-groups] dev` group — see
`rules/python-development.md`). A bare **language server** launch (e.g. `uvx ty@latest server`, no
ambient `uv run`, no project `.venv` on `PATH`) has one known, upstream-confirmed blind spot: any
`.py` file with a PEP 723 `# /// script … # ///` block — every standalone script in this repo —
gets checked as an isolated single-file project that ignores `[tool.ty.environment]` entirely, so a
live `unresolved-import` squiggle on a PEP 723 script's own declared third-party dependency is a
known false positive, not a real regression. Do not add `extra-paths` entries to chase it and do
not add a rule-level suppression. Confirm with `uv run ty check <path>` (or
`prek run ty --files <path>`) before treating any ty diagnostic as real; if that passes clean,
trust it over the editor's live diagnostic.

The fix is Astral's own experimental PEP 723/uv integration (`TY_UV=scripts` — as a plain
environment variable, verified to work identically for `ty check` and `ty server` — or the
protocol-level `ty.experimental.useUv` equivalent), not an environment-pointing workaround. It has
**two separate consumers in this repo, only one of which this repo can currently configure**:

- VS Code's `astral-sh.ty` extension — covered, via
  [`.vscode/settings.json`](../.vscode/settings.json).
- Claude Code's own bundled Astral-plugin language server (the process producing live diagnostics
  inside a Claude Code session) — **not yet covered**; needs `"TY_UV": "scripts"` added to
  `.claude/settings.json`'s `env` block by a human with write access to that file. See
  [`rules/python-development.md`](../rules/python-development.md#unresolved-import-on-a-pep-723-script-specifically-in-the-language-server)
  for the full evidence trail and coverage breakdown.

`.claude/settings.json`'s `env` values do reach that spawned process (confirmed by inspecting the
live server's own environment), but no agent may write to that file. Regression coverage (CLI-level
only — see the note in `rules/python-development.md` on why the LSP-protocol verification isn't
also an automated test):
[`tests/test_ty_pep723_environment.py`](../tests/test_ty_pep723_environment.py).
### Common ty failure patterns

- **`unresolved-attribute` on a `ModuleType`**: almost always means the module's directory is
  missing from `[tool.ty.environment] extra-paths` in `pyproject.toml`. Add it there first —
  mirroring the matching entry already in `[tool.pytest.ini_options] pythonpath` — and re-run
  before investigating the importing code itself. For the related `unresolved-import` failure
  (same `extra-paths` root cause, different symptom — the module isn't found at all rather than
  an attribute on it), see `rules/python-development.md`'s "`unresolved-import` errors" section.
- **TypedDict nominal typing**: ty treats a `TypedDict` as scoped to its defining module — two
  structurally identical TypedDicts from different modules are incompatible types to ty. Avoid
  making an implementation explicitly inherit from a `@runtime_checkable` Protocol when the
  Protocol's signatures reference TypedDicts duplicated across modules (`isinstance()` checks
  still work without explicit inheritance); if inheritance is required, have all signatures import
  the TypedDicts from one canonical module.

## Gotchas

- **Skip magic trailing comma**: Ruff config has `skip-magic-trailing-comma = true` — formatting
  differences around trailing commas are expected.
- **EXE003 ignored**: Scripts with `uv run --script` shebang pattern trigger EXE003 (intentionally
  suppressed).
