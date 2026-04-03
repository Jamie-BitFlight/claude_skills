---
name: python3-tools
description: Python tooling expertise for uv, Hatchling, ty type checker, pre-commit, TOML editing, and PyPI packaging. Activates on uv commands, pyproject.toml configuration, type checker setup, build system, git hooks, packaging, or release workflows.
user-invocable: false
---

# Python Tooling

Consult `python3-core` for standing defaults.

## uv Package Management

- `uv add` for dependencies (not `uv pip install`)
- `uv run` for execution (not `source .venv/bin/activate`)
- `uv sync --frozen` for CI; `uv sync --locked` to detect stale lockfiles
- PEP 723 shebang: `#!/usr/bin/env -S uv --quiet run --active --script`
- `uv venv --clear` to overwrite existing environments (since 0.10.0)

## Type Checker Detection

Check `.pre-commit-config.yaml` → CI config → `pyproject.toml`:

- **Default for new work**: ty (Astral)
- **Project runs mypy**: respect mypy.ini / `[tool.mypy]`; do not force ty
- **Project runs pyright/basedpyright**: respect that; do not force ty
- Do NOT infer active checker from presence of `[tool.mypy]` alone (may be stub config)

## Build Backend

Hatchling preferred:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]
```

## Pre-commit

Detect installed tool: read `.git/hooks/pre-commit` line 2 to identify pre-commit vs prek. Both use the same config file.

## TOML Editing

- `tomlkit` for read/write (preserves formatting) — open in text mode
- `tomllib` (stdlib) for read-only — `tomllib.load()` requires binary mode (`"rb"`), `tomllib.loads()` takes a string

## PyPI Packaging

```toml
# pyproject.toml
[project]
name = "my-package"
version = "0.1.0"
requires-python = ">=3.11"
classifiers = ["Typing :: Typed"]

[project.scripts]
my-cli = "my_package.cli:app"
```

## References

- `references/tooling-defaults.md` — full tooling reference
- `references/compatibility-lanes.md` — version compatibility
