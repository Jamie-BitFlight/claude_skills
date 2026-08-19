# Tooling Defaults

## Package Management

**uv** is the default. Key rules:

- `uv add` for project dependencies (not `uv pip install`)
- `uv run` for execution (not `source .venv/bin/activate`)
- `uv sync --frozen` for CI
- `uv sync --locked` to detect stale lockfiles
- `uv venv --clear` since 0.10.0 to overwrite existing environments
- PEP 723 shebang: `#!/usr/bin/env -S uv run --quiet --script` — never `--active`, which resolves
  into an ambient `VIRTUAL_ENV` instead of an isolated ephemeral one, installing the script's
  dependencies into whatever venv the caller happens to have active

## Type Checker

Detection order: `.pre-commit-config.yaml` → CI config → `pyproject.toml`. Do not infer the
active checker from config-key presence alone (`[tool.mypy]` may be stub config for IDEs).

- **Default**: ty (Astral) for new work
- **Existing projects on mypy**: keep mypy, do not force migration
- **Existing projects on pyright/basedpyright**: respect that, do not force ty
- **IDEs**: keep stub config so built-in checkers stay quiet after migration

## Linter / Formatter

**ruff** for both linting and formatting.

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", "TCH", "PTH", "ERA", "PL", "RUF", "ANN", "D", "S", "T20"]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

## Build Backend

**hatchling** preferred:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]
```

## Pre-commit

Detect from `.git/hooks/pre-commit` line 2. prek is a drop-in Rust replacement using the same config file.

## TOML

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
