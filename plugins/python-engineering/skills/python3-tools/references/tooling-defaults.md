# Tooling Defaults

## Package Management

**uv** is the default. Key rules:

- `uv add` for project dependencies (not `uv pip install`)
- `uv run` for execution (not `source .venv/bin/activate`)
- `uv sync --frozen` for CI
- `uv sync --locked` to detect stale lockfiles
- `uv venv --clear` since 0.10.0 to overwrite existing environments
- PEP 723 shebang: `#!/usr/bin/env -S uv --quiet run --active --script`

## Type Checker

- **Default**: ty (Astral) for new work
- **Detection**: check `.pre-commit-config.yaml` then CI, not config file presence
- **Existing projects on mypy**: keep mypy, do not force migration
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
```

## Pre-commit

Detect from `.git/hooks/pre-commit` line 2. prek is a drop-in Rust replacement.

## TOML

- `tomlkit` for read/write (preserves formatting)
- `tomllib` (stdlib) for read-only in stdlib scripts
