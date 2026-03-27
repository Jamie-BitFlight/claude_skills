---
name: uv
description: Use when working with Astral's uv — managing Python project dependencies, creating PEP 723 scripts, installing tools, managing Python versions, configuring package indexes, or migrating from pip/poetry. Covers project initialization, virtual environments, workspace configuration, and CI/CD integration.
---

# uv: Modern Python Package and Project Manager

## Overview

uv is Astral's extremely fast Python package and project manager written in Rust, designed as a unified replacement for pip, pip-tools, pipx, poetry, pyenv, and virtualenv. It delivers 10-100x faster performance while providing modern dependency management with lockfiles and reproducible environments.

## When to Use This Skill

Use this skill when:

- Initializing new Python projects or scripts
- Managing project dependencies with pyproject.toml
- Creating portable single-file scripts with PEP 723 inline metadata
- Installing or running command-line tools (ruff, black, httpie, etc.)
- Managing Python interpreter versions
- Setting up virtual environments
- Configuring package indexes or private registries
- Migrating from pip, pip-tools, poetry, or conda
- Configuring CI/CD pipelines for Python projects
- Setting up Docker containers for Python applications
- Troubleshooting dependency resolution or build failures

## Migration Quick Reference

If you're coming from another tool, here's the fast lookup:

| Old Tool | Old Command | uv Equivalent |
| -------- | ----------- | ------------- |
| pip | `pip install X` | `uv add X` |
| pip | `pip install -r requirements.txt` | `uv add -r requirements.txt` |
| pip | `python -m pip install --upgrade X` | `uv add X` (updates pyproject.toml + lockfile) |
| pip-tools | `pip-compile` | `uv pip compile` |
| pip-tools | `pip-sync` | `uv pip sync` |
| pipx | `pipx run ruff` | `uvx ruff` |
| pipx | `pipx install ruff` | `uv tool install ruff` |
| pipx | `pipx upgrade ruff` | `uv tool upgrade ruff` |
| pyenv | `pyenv install 3.12` | `uv python install 3.12` |
| pyenv | `pyenv local 3.12` | `uv python pin 3.12` |
| pyenv | `pyenv global 3.12` | `uv python install 3.12 --default` |
| poetry | `poetry add X` | `uv add X` |
| poetry | `poetry add -D X` | `uv add --dev X` |
| poetry | `poetry install` | `uv sync` |
| poetry | `poetry run X` | `uv run X` |
| poetry | `poetry shell` | N/A — use `uv run` instead |
| virtualenv | `python -m venv .venv` | `uv venv` |
| conda | `conda install X` | `uv add X` |

For full step-by-step migration workflows, see `references/migration-guide.md`.

## Core Capabilities

Consult `../python3-development/references/python3-standards.md` when applying shared architecture, typing, testing, or CLI rules; full standards, graphs, and amendment process are documented there.

### 1. Project Initialization and Management

**Initialize new projects:**

```bash
# Standard project with recommended structure
uv init myproject

# Application project (default)
uv init myapp --app

# Library/package project (includes src/ layout)
uv init mylib --lib --build-backend hatchling

# Bare project (pyproject.toml only)
uv init --bare
```

**Project structure created:**

```text
myproject/
├── .venv/           # Virtual environment (auto-created)
├── .python-version  # Pinned Python version
├── README.md
├── main.py          # Sample entry point
├── pyproject.toml   # Project metadata and dependencies
└── uv.lock          # Lockfile (like Cargo.lock or package-lock.json)
```

### 2. Dependency Management

**Add dependencies to project:**

```bash
# Production dependencies
uv add requests 'flask>=2.0,<3.0' pydantic

# With automatic version bounds (stable in 0.10.0)
uv add --bounds compatible requests  # Adds requests>=2.31,<3
uv add --bounds exact flask          # Adds flask==3.0.0

# Development dependencies
uv add --dev pytest pytest-cov ruff mypy black

# Optional dependency groups
uv add --group docs sphinx sphinx-rtd-theme
uv add --group test pytest-asyncio hypothesis

# From various sources
uv add git+https://github.com/psf/requests@main
uv add --editable ./local-package
uv add ../sibling-package
```

**Remove dependencies:**

```bash
uv remove requests flask
uv remove --dev pytest
uv remove --group docs sphinx
```

**Lock and sync environments:**

```bash
# Update lockfile with latest compatible versions
uv lock

# Upgrade all packages
uv lock --upgrade

# Upgrade specific packages
uv lock --upgrade-package requests --upgrade-package flask

# Install all dependencies from lockfile
uv sync

# Install without dev dependencies (production)
uv sync --no-dev

# Install with optional groups
uv sync --extra docs --extra test
uv sync --extra docs,test  # Comma-separated (0.9.30+)

# Sync without updating lockfile (CI mode)
uv sync --frozen

# Error if lockfile out of sync (strict CI mode)
uv sync --locked
```

### 3. Running Code in Project Context

**Execute scripts and commands:**

```bash
# Run Python script in project environment
uv run python script.py

# Run module (like python -m)
uv run -m pytest
uv run -m flask run --port 8000

# Run with specific Python version
uv run --python 3.11 script.py
uv run --python pypy@3.9 test.py

# Run without syncing first (use current environment state)
uv run --frozen script.py

# Run with additional temporary dependencies
uv run --with httpx --with rich script.py

# Run without project dependencies (standalone)
uv run --no-project example.py

# Run with environment variables from file
uv run --env-file .env script.py
```

### 4. PEP 723 Inline Script Metadata

**Create portable single-file scripts with dependencies:**

```bash
# Initialize script with metadata block
uv init --script example.py --python 3.12

# Add dependencies to existing script
uv add --script example.py requests rich
```

**Example script structure:**

```python
#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31",
#   "rich>=13.0",
# ]
# ///

import requests
from rich import print

response = requests.get("https://api.github.com/repos/astral-sh/uv")
print(f"Stars: {response.json()['stargazers_count']}")
```

**Run scripts:**

```bash
# Auto-creates isolated environment and runs
uv run example.py

# Run with additional dependencies
uv run --with beautifulsoup4 example.py

# Lock script for reproducibility
uv lock --script example.py  # Creates example.py.lock

# Make executable and run directly
chmod +x example.py
./example.py
```

**Best practices for scripts:**

- Always include `requires-python` for compatibility
- Use version constraints for critical dependencies
- Lock scripts before sharing for reproducibility
- Add `exclude-newer` in `[tool.uv]` for time-based pinning (supports relative durations like `"2 days ago"` or `"1w"` since 0.9.17)

### 5. Tool Management

**One-off tool execution (ephemeral environments):**

```bash
# Run tool without installing (uvx is alias)
uvx ruff check
uvx pycowsay "hello from uv"

# Run specific version
uvx ruff@0.3.0 check
uvx --from 'ruff>=0.3.0,<0.4.0' ruff check

# Run tool from different package
uvx --from httpie http GET example.com

# Run with plugin/additional dependencies
uvx --with mkdocs-material mkdocs serve
```

**Persistent tool installation:**

```bash
# Install tool globally (adds to PATH)
uv tool install ruff black mypy

# Install with version constraint
uv tool install 'httpie>0.1.0'

# Install from git
uv tool install git+https://github.com/httpie/cli

# Install with additional packages
uv tool install mkdocs --with mkdocs-material

# Upgrade tools
uv tool upgrade ruff
uv tool upgrade --all

# List installed tools
uv tool list
uv tool list --show-paths

# Uninstall tool
uv tool uninstall ruff

# Update shell configuration for tools
uv tool update-shell
```

### 6. Python Version Management

**Install and manage Python versions:**

```bash
# Install specific Python version (auto-downloads if needed)
uv python install 3.12
uv python install 3.11 3.12 3.13  # Multiple at once

# Install and compile standard library bytecode (0.9.25+)
uv python install --compile-bytecode 3.12

# Request GIL-enabled interpreter for free-threaded Python (0.9.8+)
uv python install 3.13+gil

# List available versions
uv python list
uv python list --all-versions

# Pin Python version for project
uv python pin 3.12  # Creates .python-version
uv python pin --global 3.12  # Global pin

# Find Python executable
uv python find 3.11

# Upgrade Python installations (stable in 0.10.0)
uv python upgrade 3.11
uv python upgrade --all
uv python upgrade --compile-bytecode 3.11

# Use specific Python for command
uv run --python 3.11 script.py
uv venv --python 3.12.0
```

**Python is automatically downloaded when needed:**

- Supports CPython, PyPy, GraalPy, Pyodide, and other implementations
- Managed installations stored in `~/.local/share/uv/python/` (Unix)
- Preference configurable: `only-managed`, `managed`, `system`, `only-system`
- **0.10.0 change**: Alternative implementations (PyPy, GraalPy, Pyodide) now install executables under their implementation name (e.g., `pypy3.10` instead of `python3.10`)

### 7. Virtual Environment Management

**Create virtual environments:**

```bash
# Create in .venv directory (default)
uv venv

# Clear and recreate existing environment (required since 0.10.0)
uv venv --clear

# Create with specific Python version
uv venv --python 3.11
uv venv --python pypy3.9

# Create with custom path
uv venv myenv

# Create with system packages access
uv venv --system-site-packages

# Create with seed packages (pip, setuptools, wheel)
uv venv --seed

# Activate (standard Python activation)
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows
```

**Warning (changed in 0.10.0)**: `uv venv` now **refuses to overwrite** an existing environment. Pass `--clear` (or set `UV_VENV_CLEAR=1`) to remove and recreate it.

### 8. pip-Compatible Interface

**Direct pip replacement commands:**

```bash
# Install packages
uv pip install flask requests
uv pip install -r requirements.txt
uv pip install -e .  # Editable install

# Install from git
uv pip install git+https://github.com/psf/requests
uv pip install git+https://github.com/pallets/flask@main

# Compile requirements (like pip-compile)
uv pip compile pyproject.toml -o requirements.txt
uv pip compile requirements.in -o requirements.txt
uv pip compile --upgrade-package ruff requirements.in

# Sync environment to exact requirements (like pip-sync)
uv pip sync requirements.txt

# Uninstall packages
uv pip uninstall flask requests
uv pip uninstall -r requirements.txt

# List installed packages
uv pip list
uv pip list --format json
uv pip freeze > requirements.txt
uv pip freeze --exclude setuptools --exclude pip  # Exclude packages (0.9.27+)

# Show package info
uv pip show requests

# Check for conflicts
uv pip check

# Display dependency tree
uv pip tree
uv pip tree --depth 2

# Check if package is installed
uv pip freeze | grep -q '^requests=='
uv pip list --format json | jq -e '.[] | select(.name == "requests")'
uv pip show requests
```

**Package check benchmarks** (76 packages installed):

| Command                     | Time  | Output Size |
| --------------------------- | ----- | ----------- |
| `uv pip freeze`             | ~8ms  | ~1.5 KB     |
| `uv pip list`               | ~10ms | ~2.5 KB     |
| `uv pip list --format json` | ~10ms | ~3.2 KB     |
| `uv pip show <pkg>`         | ~40ms | ~0.3 KB     |

`uv pip show` is slower because it resolves `Requires` and `Required-by` relationships.

### 9. Workspace Management (Monorepos)

**Configure workspaces in root pyproject.toml:**

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
exclude = ["packages/deprecated"]
```

**Workspace dependency references:**

```toml
[project]
name = "myapp"
dependencies = ["shared-lib", "core-utils"]

[tool.uv.sources]
shared-lib = { workspace = true }
core-utils = { workspace = true }
```

**Workspace commands:**

```bash
# Build specific workspace package
uv build --package my-package

# Run in workspace package context
uv run --package my-package python script.py

# Lock workspace (single lockfile for all members)
uv lock
```

### 10. Workspace Commands (Stable in 0.10.0)

**List and inspect workspace members:**

```bash
# List all workspace members
uv workspace list

# Show workspace member paths
uv workspace list --paths

# Print workspace root directory
uv workspace dir
```

### 11. Dependency Exclusions (0.9.8+)

**Exclude packages from resolution:**

```toml
# In pyproject.toml
[tool.uv]
dependency-exclusions = ["unwanted-package"]
```

```bash
# Or via CLI
uv sync --exclude unwanted-package
```

### 12. SBOM Export (0.9.11+)

**Export Software Bill of Materials:**

```bash
# Export dependencies as CycloneDX SBOM
uv export --format cyclonedx-json -o sbom.json
```

### 13. Package Building and Publishing

**Build distributions:**

```bash
# Build wheel and source distribution
uv build

# Build only wheel
uv build --wheel

# Build specific workspace package
uv build --package my-package

# Output to custom directory
uv build --out-dir dist/
```

**Publish to PyPI:**

```bash
# Publish directly with uv
uv publish

# Publish with token
uv publish --token $PYPI_TOKEN

# Publish to test PyPI
uv publish --publish-url https://test.pypi.org/legacy/

# Smoke test before publishing
uv run --isolated --no-project --with dist/*.whl python -c "import my_package"
```

**PEP 740 attestations (0.9.12+)**: `uv publish` automatically collects and uploads attestations when available.

**Build before publishing:**

```bash
uv build --clear  # Remove old artifacts first (0.9.6+)
uv publish --build  # Build and publish in one step
```

## Configuration

### pyproject.toml Structure

**Standard project configuration:**

```toml
[project]
name = "myproject"
version = "1.0.0"
description = "My awesome project"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.2",
    "pydantic>=2.5.3",
]

# Development dependencies using PEP 735 dependency groups
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.15.1",
    "ruff>=0.13.3",
    "pyright>=1.1.406",
    "mypy>=1.18.2",
    "pre-commit>=4.3.0",
]
docs = ["sphinx>=7.0", "sphinx-rtd-theme>=1.3.0"]
test = ["pytest-cov>=6.0.0", "pytest-asyncio>=0.21.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
# Core settings
managed = true
package = true
default-groups = ["dev"]

# Resolution
resolution = "highest"  # or "lowest", "lowest-direct"
index-strategy = "first-index"

# Build configuration
compile-bytecode = true
no-build-isolation-package = ["flash-attn"]

# Dependency exclusions (0.9.8+)
dependency-exclusions = ["unwanted-package"]

# PyTorch accelerator backend (0.9.18+ in config)
torch-backend = "auto"  # or "cu121", "rocm7.0", "cpu"

# Python management
python-preference = "managed"
python-downloads = "automatic"

# Custom package sources
[tool.uv.sources]
torch = { index = "pytorch-cu121" }
internal-lib = { workspace = true }

# Custom indexes
[[tool.uv.index]]
name = "pytorch-cu121"
url = "https://download.pytorch.org/whl/cu121"
explicit = true
```

### Environment Variables

**Key environment variables:**

```bash
# Cache and directories
export UV_CACHE_DIR="/custom/cache"
export UV_PROJECT_ENVIRONMENT=".venv"
export UV_WORKING_DIR="/path/to/project"  # Preferred over UV_WORKING_DIRECTORY (0.9.14+)

# Python management
export UV_PYTHON_PREFERENCE="managed"
export UV_PYTHON_DOWNLOADS="automatic"

# Network configuration
export UV_CONCURRENT_DOWNLOADS=20
export UV_CONCURRENT_BUILDS=8

# Index authentication
export UV_INDEX_PRIVATE_USERNAME="user"
export UV_INDEX_PRIVATE_PASSWORD="pass"

# Preview features
export UV_PREVIEW=1

# Disable cache
export UV_NO_CACHE=1

# System Python
export UV_SYSTEM_PYTHON=1

# Dependency group control (0.9.8+)
export UV_NO_GROUP="docs"
export UV_NO_SOURCES=1
export UV_NO_DEFAULT_GROUPS=1

# Virtual environment (0.10.0+)
export UV_VENV_CLEAR=1  # Auto-remove existing venvs

# Build output control (0.9.15+)
export UV_HIDE_BUILD_OUTPUT=1

# Git LFS (0.9.15+)
export UV_GIT_LFS=1

# PyTorch accelerator backend
export UV_TORCH_BACKEND="cu121"  # or rocm7.0, rocm7.1, cpu, auto

# SSL certificate directory (0.9.10+)
export SSL_CERT_DIR="/path/to/certs"
```

For complete configuration reference, see `references/configuration.md`.

## Common Workflows

### Starting a New Project

```bash
# 1. Initialize project
uv init myproject
cd myproject

# 2. Add dependencies
uv add fastapi uvicorn sqlalchemy

# 3. Add dev dependencies
uv add --dev pytest ruff mypy

# 4. Run application
uv run python main.py

# 5. Run tests
uv run pytest
```

### Creating a Portable Script

```bash
# 1. Create script with metadata
uv init --script analyze.py --python 3.11

# 2. Add dependencies
uv add --script analyze.py pandas matplotlib

# 3. Edit script content
# (add your code to analyze.py)

# 4. Lock for reproducibility
uv lock --script analyze.py

# 5. Make executable
chmod +x analyze.py

# 6. Run
./analyze.py
```

### Migrating from pip/requirements.txt

```bash
uv init --bare
uv add -r requirements.txt
uv add --dev -r requirements-dev.txt
uv sync
```

For full workflow including hybrid approach and common issues, see `references/migration-guide.md`.

### Migrating from Poetry

```bash
# Option 1: Automated (recommended)
uvx migrate-to-uv
uvx migrate-to-uv --dry-run  # Preview first

# Option 2: Manual
# poetry export -f requirements.txt --output requirements.txt
# uv init && uv add -r requirements.txt
```

For command mapping table and pyproject.toml conversion, see `references/migration-guide.md`.

### CI/CD Integration (GitHub Actions)

**Basic CI workflow:**

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --frozen --all-extras

      - name: Run tests
        run: uv run pytest

      - name: Run linters
        run: |
          uv run ruff check .
          uv run mypy .
```

**Publishing workflow with trusted publishing:**

```yaml
name: Publish
on:
  push:
    tags:
      - v*

jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
      - run: uv python install 3.13
      - run: uv build
      - run: uv run --isolated --no-project --with dist/*.whl tests/smoke_test.py
      - run: uv publish # Uses trusted publishing
```

### Docker Integration

**Note (0.10.0)**: Debian Bookworm, Alpine 3.21, and Python 3.8 Docker images are no longer published. Use `uv:trixie`/`uv:debian` and `uv:alpine3.22`/`uv:alpine` instead.

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

# Use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]
```

### Git Hook Integration (pre-commit / prek)

**Configure uv-managed tools in `.pre-commit-config.yaml`:**

**Note**: Both pre-commit and prek use the same configuration file with identical syntax.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: custom-hook
        name: Run Custom Hook
        entry: uv run my-hook-script
        language: system
        stages: [commit]
        pass_filenames: false
        always_run: true
```

**Benefits of uv run in git hooks:**

- Uses project's locked dependencies automatically
- No separate hook environment needed
- Ensures consistency between development and git hook checks
- Works with both pre-commit (Python) and prek (Rust)

## Troubleshooting

### "Externally Managed" Error

**Problem**: `error: The interpreter is externally managed`

**Solution**: Use virtual environments instead of `--system`:

```bash
uv venv
source .venv/bin/activate
uv pip install package
```

### Build Failures

**Problem**: Package fails to build from source

**Common causes**:

- Missing system dependencies (compilers, headers)
- Python version incompatibility
- Outdated package version

**Solutions**:

- Install system dependencies: `apt-get install python3-dev build-essential`
- Add version constraints: `uv add "numpy>=1.20"`
- Check error message for missing modules

### Lockfile Out of Sync

**Problem**: Dependencies changed but lockfile not updated

**Solutions**:

```bash
uv lock           # Regenerate lockfile
uv sync --locked  # Error if out of sync (CI mode)
uv sync --frozen  # Don't update lockfile
```

### Cache Issues

**Problem**: Stale cache causing problems

**Solutions**:

```bash
uv cache size           # Show cache disk usage (0.9.8+)
uv cache clean          # Clean entire cache
uv cache prune          # Remove unreachable entries
uv --no-cache <command> # Bypass cache temporarily
```

### Common Pitfalls

**1. Forgetting `--clear` when recreating venvs (0.10.0+):**

```bash
# Since 0.10.0, uv venv refuses to overwrite
uv venv          # Errors if .venv already exists
uv venv --clear  # Required to remove and recreate
```

**2. Forgetting to sync after adding dependencies:**

```bash
uv add requests  # Adds to pyproject.toml and updates lockfile
uv sync          # Required to actually install the package
```

**3. Incorrect workspace glob patterns:**

- Wrong: `members = ["packages/"]` (missing asterisk)
- Correct: `members = ["packages/*"]`

**4. Missing build-system for libraries:**

Libraries and packages require a `[build-system]` section:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**5. Wrong file mode for TOML operations:**

- Use text mode `'r'` and `'w'` with tomlkit
- Do not use binary mode `'rb'` or `'wb'`

**6. Incorrect workspace source syntax:**

- Wrong: `{ workspace = "true" }` (string "true")
- Correct: `{ workspace = true }` (boolean true)

**7. Not using --frozen in CI:**

```bash
# CI should fail if lockfile is outdated
uv sync --frozen
```

**8. Incompatible Python version ranges in workspaces:**

All workspace members must have compatible `requires-python` ranges. If one member requires `>=3.11` and another requires `>=3.12`, the workspace will use `>=3.12`.

For more troubleshooting scenarios, see `references/troubleshooting.md`.

## Resources

This skill includes comprehensive reference documentation:

### references/

- `cli_reference.md` - Complete CLI commands and arguments reference
- `configuration.md` - All configuration options and environment variables
- `migration-guide.md` - Step-by-step migration from pip, poetry, pipx, pyenv, conda — command mapping tables and common issues
- `quick-reference.md` - Command quick reference organized by subcommand with flags
- `workflows.md` - Detailed workflow guides and examples
- `troubleshooting.md` - Common issues and solutions

### assets/

- `pyproject_templates/` - Example pyproject.toml configurations
- `script_examples/` - PEP 723 script templates
- `docker_examples/` - Docker configuration templates
- `github_actions/` - CI/CD workflow examples

## Key Principles

1. **Speed**: uv is 10-100x faster than traditional tools
2. **Reproducibility**: Lockfiles ensure consistent environments
3. **Simplicity**: Single tool replaces multiple Python tools
4. **Modern Standards**: PEP 723 scripts, standard pyproject.toml
5. **Developer Experience**: Automatic Python installation, smart defaults

## Usage Guidelines

### Do

- Use `uv run` instead of activating venv — it auto-syncs and is faster
- Commit `uv.lock` — it ensures reproducible builds across machines and CI
- Use `--locked` in CI/CD — fails fast if lockfile is out of sync
- Use `--dev` flag for test/lint/type-check dependencies
- Use `uvx` for one-off tool usage — no permanent installation needed
- Use `uv add` not `uv pip install` for project dependencies — it updates pyproject.toml

### Don't

- Don't activate venv manually (`source .venv/bin/activate`) — use `uv run`
- Don't use `pip install` alongside `uv add` in the same project — they don't share state
- Don't skip committing `uv.lock` — without it, CI and teammates get different versions
- Don't use `uv pip install` for project deps — it bypasses pyproject.toml and lockfile
- Don't use `uv run` without `--frozen` or `--locked` in CI — let it fail explicitly if stale

## Version Information

Current latest version: **0.10.2** (February 2026)

### 0.10.0 Breaking Changes (February 2026)

- `uv venv` no longer auto-removes existing environments -- pass `--clear` or set `UV_VENV_CLEAR=1`
- Multiple `default = true` indexes now error (previously silently accepted)
- Unnamed `explicit` indexes now error (must have a `name` for `[tool.uv.sources]` references)
- Alternative Python implementations (PyPy, GraalPy, Pyodide) install under their implementation name (e.g., `pypy3.10` not `python3.10`)
- `uv tool run` and `uv tool install` respect the global Python version pin
- Docker: Debian Bookworm, Alpine 3.21, and Python 3.8 images removed; use `uv:trixie`/`uv:debian` and `uv:alpine3.22`/`uv:alpine`
- `uv format` upgraded to Ruff 0.15.0 (2026 style guide); pin with `uv format --version 0.14.14` to opt out
- `exclude-newer` lockfile changes no longer cause full version upgrades; use `--upgrade` explicitly

### Features Stabilized in 0.10.0

- `uv python upgrade` / `uv python install --upgrade`
- `uv workspace list` / `uv workspace dir`
- `uv add --bounds` and `add-bounds` configuration
- `extra-build-dependencies` configuration

### Key Features Added Since 0.9.5

- `uv cache size` command (0.9.8)
- First-class dependency exclusions via `tool.uv.dependency-exclusions` (0.9.8)
- Free-threaded Python `+gil` suffix for interpreter requests (0.9.8)
- SBOM export format in `uv export` (0.9.11)
- PEP 740 attestation auto-collection in `uv publish` (0.9.12)
- Git LFS support via `UV_GIT_LFS` (0.9.15)
- Relative durations for `exclude-newer` (e.g., `"2 days ago"`, `"1w"`) (0.9.17)
- `--torch-backend` in `[tool.uv]` configuration (0.9.18)
- ROCm 6.4, 7.0, 7.1 accelerator backend support (0.9.15, 0.9.27)
- Pyodide interpreter support on Windows (0.9.28)
- `--compile-bytecode` for `uv python install`/`upgrade` (0.9.25)
- `uv pip freeze --exclude` (0.9.27)
- Comma-separated values for `--extra`, `--no-binary`, `--only-binary` (0.9.30, 0.9.20)
- `uv build --clear` to remove old build artifacts (0.9.6)
- 5-minute default timeout on file locks (0.9.16)
- Proxy variables configurable via global/user config files (0.9.23)

### Python Versions Added Since 0.9.5

- CPython 3.15.0a2 through 3.15.0a5
- CPython 3.14.1, 3.14.2, 3.14.3
- CPython 3.13.10, 3.13.11, 3.13.12
- Pyodide 0.29.2, 0.29.3
- GraalPy 25.0.1, 25.0.2

### Deprecations

- `--project` flag in `uv init` deprecated; use positional argument or `--name` (0.9.9)
- `UV_WORKING_DIRECTORY` superseded by `UV_WORKING_DIR` (0.9.14)

## External Resources

- Official docs: <https://docs.astral.sh/uv/>
- GitHub: <https://github.com/astral-sh/uv>
- Concepts guide: <https://docs.astral.sh/uv/concepts/>
- Migration guides: <https://docs.astral.sh/uv/guides/migration/>
