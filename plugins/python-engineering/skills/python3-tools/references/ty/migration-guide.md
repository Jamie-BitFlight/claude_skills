# Migration Guide to ty

Migrate from mypy or pyright to ty. Covers command mapping, configuration translation, suppression comment conversion, and behavioral differences.

SOURCE: [ty documentation](https://docs.astral.sh/ty/) (accessed 2026-02-28), [mypy docs](https://mypy.readthedocs.io/) (accessed 2026-02-28), [pyright docs](https://microsoft.github.io/pyright/) (accessed 2026-02-28), [pydevtools migration guide](https://pydevtools.com/handbook/how-to/how-to-migrate-from-mypy-to-ty/) (accessed 2026-02-28)

## Quick-Lookup Cheatsheet

| Old Tool | Old Command | ty Equivalent |
|----------|-------------|---------------|
| mypy | `mypy .` | `ty check` |
| mypy | `mypy --strict .` | `ty check --error all` |
| mypy | `mypy --ignore-missing-imports .` | `ty check` + `allowed-unresolved-imports = ["**"]` |
| mypy | `mypy --python-version 3.12 .` | `ty check --python-version 3.12` |
| mypy | `mypy --exclude 'tests/'` | `ty check --exclude 'tests/'` |
| mypy | `mypy --show-error-codes .` | Default behavior (ty always shows rule names) |
| mypy | `mypy --no-error-summary .` | `ty check --quiet` |
| mypy | `dmypy run .` | `ty check --watch` |
| pyright | `pyright .` | `ty check` |
| pyright | `pyright --pythonversion 3.12` | `ty check --python-version 3.12` |
| pyright | `pyright --pythonplatform Linux` | `ty check --python-platform linux` |
| pyright | `pyright --outputjson` | `ty check --output-format gitlab` (JSON) |
| pyright | `pyright -p pyrightconfig.json` | `ty check --config-file ty.toml` |

---

## From mypy

### Migration Steps

```bash
# 1. Install ty
uv add --dev ty
# or run without installing:
uvx ty check

# 2. Run ty on your project
ty check

# 3. Review diagnostics — ty may find different issues than mypy
# ty uses its own type inference engine and rule set

# 4. Migrate configuration (see below)

# 5. Convert suppression comments (see below)

# 6. Update CI configuration
# Replace: mypy src/ tests/
# With:    ty check
```

### Configuration Mapping

#### mypy.ini / setup.cfg to ty.toml

```ini
# mypy.ini (old)
[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
ignore_missing_imports = True
exclude = tests/fixtures

[mypy-pandas.*]
ignore_missing_imports = True
```

```toml
# ty.toml (new)
[environment]
python-version = "3.12"

[rules]
# ty has its own rule names — not a 1:1 mapping with mypy flags
# Use --error all for strict mode similar to mypy --strict
all = "error"

[analysis]
# Equivalent to ignore_missing_imports for specific modules
allowed-unresolved-imports = ["pandas.**"]

[src]
exclude = ["tests/fixtures"]
```

#### pyproject.toml migration

```toml
# Old: [tool.mypy]
[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

```toml
# New: [tool.ty]
[tool.ty.environment]
python-version = "3.12"

[tool.ty.rules]
all = "error"

[tool.ty.analysis]
allowed-unresolved-imports = ["tests.**"]

[[tool.ty.overrides]]
include = ["tests/**"]

[tool.ty.overrides.rules]
# Relax rules in test files
possibly-unresolved-reference = "warn"
```

### IDE coexistence: stub legacy checkers (mypy, basedpyright, pyright)

After **ty** owns pre-commit and CI, this plugin treats **ty** as sufficient for the same class of static typing checks that **mypy**, **basedpyright**, and **pyright** addressed in CI — run **one** enforced checker in hooks/CI (**ty**), not parallel runs unless the team explicitly wants that.

Editors still probe **mypy**, **Pylance/pyright**, and **basedpyright** when they find config. **Keep stub sections** so IDE-integrated checkers do not re-analyze the tree or fight **ty**.

#### mypy (`pyproject.toml`)

```toml
[tool.mypy]
# Project uses ty for type checking (pre-commit / CI). Exclude all so IDE-integrated mypy stays quiet.
exclude = [".*"]
```

**Do not** remove `[tool.mypy]` solely to “clean up” after migrating — that often makes IDE mypy run again with default settings.

#### basedpyright (`pyproject.toml`)

```toml
[tool.basedpyright]
# Disabled: project uses ty for type checking. Config kept so the IDE loads project settings, not aggressive defaults.
typeCheckingMode = "off"
```

Adjust fields if your editor reads other keys; goal is **no second full-project analysis** competing with **ty**.

#### pyright (`pyproject.toml` or `pyrightconfig.json`)

Prefer the same idea: **`typeCheckingMode = "off"`** (or disable type checking in the JSON equivalent) while **ty** is canonical. If the team keeps a file for editor metadata only, document that **ty** enforces types in CI.

**Automation** must still decide which tool to run from **hooks and CI** (`ty check` vs `mypy` vs `basedpyright`). **Stub `[tool.mypy]` / `[tool.basedpyright]` / pyright config does not mean** those tools run in CI — same rule as `../../python3-development/references/python3-standards.md`: do not infer the primary checker from stub tables alone.

### mypy Flag to ty Equivalent

| mypy Flag | ty Equivalent | Notes |
|-----------|---------------|-------|
| `--strict` | `--error all` | Not identical; ty has different rules |
| `--python-version X.Y` | `--python-version X.Y` | Same syntax |
| `--ignore-missing-imports` | `allowed-unresolved-imports = ["**"]` | Config only |
| `--exclude PATTERN` | `--exclude PATTERN` | Same flag |
| `--show-error-codes` | Default | ty always shows rule names |
| `--no-color` | `--color never` | Different flag name |
| `--pretty` | Default (`--output-format full`) | Default in ty |
| `--warn-return-any` | No direct equivalent | ty has its own rule set |
| `--disallow-untyped-defs` | No direct equivalent | ty has its own rule set |
| `--follow-imports skip` | `allowed-unresolved-imports` | Different mechanism |
| `--cache-dir` | No equivalent | ty does not use a persistent cache |
| `--incremental` | `--watch` | ty watch mode re-checks on change |
| `--daemon` / `dmypy` | `ty server` (LSP) | Different architecture |

### Error Code Mapping (mypy to ty)

| mypy Code | ty Rule |
|-----------|---------|
| `import-not-found` | `unresolved-import` |
| `attr-defined` | `unresolved-attribute` |
| `arg-type` | `invalid-argument-type` |
| `assignment` | `invalid-assignment` |
| `return-value` | `invalid-return-type` |
| `union-attr` | `possibly-missing-attribute` |
| `override` | `invalid-method-override` |
| `redundant-cast` | `redundant-cast` |
| `name-defined` | `unresolved-reference` |
| `call-arg` | `missing-argument` |
| `operator` | `unsupported-operator` |
| `index` | `index-out-of-bounds` |

Rule names are not 1:1 — run `ty check` and use the rule names ty reports in its diagnostics.

SOURCE: [ty Rules Reference](https://docs.astral.sh/ty/reference/rules/) (accessed 2026-02-28)

### Suppression Comment Conversion

```python
# mypy style (old)
x = foo()  # type: ignore[assignment]
y = bar()  # type: ignore

# ty style (new)
x = foo()  # ty: ignore[invalid-assignment]
y = bar()  # ty: ignore
```

ty also respects `type: ignore` comments by default (PEP 484 compatibility). To require `ty: ignore` only:

```toml
[tool.ty.analysis]
respect-type-ignore-comments = false
```

Key difference: `type: ignore[code]` suppresses ALL violations on the line in ty, regardless of the code specified. `ty: ignore[rule]` suppresses only the named rule.

---

## From pyright

### Migration Steps

```bash
# 1. Install ty
uv add --dev ty

# 2. Run ty on your project
ty check

# 3. Migrate configuration from pyrightconfig.json to ty.toml

# 4. Update CI and editor configuration
```

### Configuration Mapping

#### pyrightconfig.json to ty.toml

```json
{
    "pythonVersion": "3.12",
    "pythonPlatform": "Linux",
    "include": ["src"],
    "exclude": ["**/node_modules", "**/__pycache__"],
    "typeCheckingMode": "strict",
    "reportMissingImports": "error",
    "reportMissingTypeStubs": "warning",
    "venvPath": ".",
    "venv": ".venv"
}
```

```toml
# ty.toml
[environment]
python-version = "3.12"
python-platform = "linux"
python = ".venv"

[rules]
all = "error"

[src]
include = ["src"]
exclude = ["**/node_modules", "**/__pycache__"]
```

### pyright Setting to ty Equivalent

| pyright Setting | ty Equivalent | Notes |
|-----------------|---------------|-------|
| `pythonVersion` | `environment.python-version` | Same format |
| `pythonPlatform` | `environment.python-platform` | Lowercase in ty |
| `include` | `src.include` | Same concept |
| `exclude` | `src.exclude` | Same concept |
| `typeCheckingMode = "strict"` | `rules.all = "error"` | Approximate equivalent |
| `typeCheckingMode = "basic"` | Default ty behavior | Approximate equivalent |
| `venvPath` + `venv` | `environment.python` | Single path in ty |
| `reportMissingImports` | Rule-based config | Different rule names |
| `extraPaths` | `environment.extra-paths` | Same concept |

### Suppression Comment Conversion

```python
# pyright style (old)
x = foo()  # type: ignore[reportGeneralClassIssue]
y = bar()  # pyright: ignore[reportMissingImports]

# ty style (new)
x = foo()  # ty: ignore[invalid-assignment]
y = bar()  # ty: ignore[unresolved-import]
```

Note: `pyright: ignore` comments are NOT recognized by ty. Convert to `ty: ignore` with the corresponding ty rule name.

---

## Behavioral Differences

### ty vs mypy

| Aspect | mypy | ty |
|--------|------|----|
| Language | Python | Rust |
| Speed | Moderate (Python) | Fast (Rust, incremental) |
| Cache | Persistent `.mypy_cache/` | No persistent cache |
| Daemon | `dmypy` for speed | `--watch` mode or LSP |
| Plugin system | Yes (mypy plugins) | No |
| Stubs | typeshed + third-party | Vendored typeshed |
| Config format | INI, TOML, or setup.cfg | TOML only (ty.toml or pyproject.toml) |
| Rule names | Error codes (`[assignment]`) | Descriptive names (`invalid-assignment`) |

### ty vs pyright

| Aspect | pyright | ty |
|--------|---------|-----|
| Language | TypeScript (Node.js) | Rust |
| Config format | JSON (pyrightconfig.json) | TOML (ty.toml or pyproject.toml) |
| LSP | Built-in (Pylance in VS Code) | `ty server` (any LSP editor) |
| Type checking modes | off/basic/standard/strict | Rule-level granularity |
| Custom stubs | stubPath setting | environment.extra-paths |
| Watch mode | Via editor | `ty check --watch` |

### Features ty Does Not Support (yet)

ty is under active development. As of early 2026, some features available in mypy/pyright may not have direct equivalents:

- **mypy plugins** — ty does not have a plugin system
- **Pyright strict mode presets** — ty uses per-rule configuration instead of named modes
- **Per-module overrides by import path** — ty uses file glob patterns (`overrides.include`), not module paths
- **Type stub generation** — ty does not generate stub files

---

## Common Migration Issues

### "Rule name not found"

ty uses its own rule names. There is no 1:1 mapping from mypy error codes or pyright diagnostic names. Run `ty check` and use the rule names ty reports in its diagnostics.

### Automated Baseline Suppression

For large codebases, use `--add-ignore` to suppress all current diagnostics and adopt ty incrementally:

```bash
# Add ty: ignore comments to suppress all existing errors
ty check --add-ignore

# Then enable strict mode — only new code must pass
ty check --error all
```

This is the recommended approach for gradual migration from mypy or pyright on large projects.

### Different errors found

ty has its own type inference engine. It may find errors mypy/pyright missed, and may not flag some issues they do. This is expected — review new diagnostics on their merits.

### Third-party library imports unresolved

If ty reports unresolved imports for well-typed libraries:

```toml
[tool.ty.environment]
python = ".venv"

[tool.ty.analysis]
# Suppress specific libraries while investigating
allowed-unresolved-imports = ["problematic_lib.**"]
```

### CI integration

```yaml
# GitHub Actions
- name: Type check with ty
  run: uvx ty check --output-format github
```

Replace mypy/pyright steps with the above. The `github` output format produces GitHub Actions annotations.
