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

### Trustworthy channel: `uv run ty check` / CI, not the live LSP squiggle on PEP 723 files

CI and `prek` gate on `uv run ty check`, which sets `VIRTUAL_ENV` via `uv run` and passes clean.
The bundled Astral **language server** (`uvx ty@latest server`, no ambient `uv run`) has one known,
upstream-confirmed blind spot: any `.py` file with a PEP 723 `# /// script … # ///` block — every
standalone script in this repo per `rules/python-development.md` — gets checked as an isolated
single-file project that ignores `[tool.ty.environment]` entirely, so a live `unresolved-import`
squiggle on a PEP 723 script's own declared third-party dependency is a known false positive, not a
real regression. Do not add `extra-paths` entries to chase it and do not add a rule-level
suppression. Confirm with `uv run ty check <path>` (or `prek run ty --files <path>`) before treating
any ty diagnostic as real; if that passes clean, trust it over the editor's live diagnostic. Full
root cause, the upstream tracking issue, and the `.claude/settings.json` mitigation live in
[`rules/python-development.md`](../rules/python-development.md#unresolved-import-on-a-pep-723-script-specifically-in-the-language-server).
Regression coverage: [`tests/test_ty_pep723_environment.py`](../tests/test_ty_pep723_environment.py).

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
