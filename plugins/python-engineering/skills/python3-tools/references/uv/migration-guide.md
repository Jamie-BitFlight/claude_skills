# Migration Guide to uv

## Quick-Lookup Cheatsheet

| Old Tool | Old Command | uv Equivalent |
| -------- | ----------- | ------------- |
| pip | `pip install X` | `uv add X` |
| pip | `pip install -r requirements.txt` | `uv add -r requirements.txt` |
| pip | `python -m pip install --upgrade X` | `uv add X` (updates pyproject.toml + lockfile) |
| pip | `python script.py` | `uv run script.py` |
| pip-tools | `pip-compile` | `uv pip compile` |
| pip-tools | `pip-sync` | `uv pip sync` |
| pipx | `pipx run ruff` | `uvx ruff` |
| pipx | `pipx install ruff` | `uv tool install ruff` |
| pipx | `pipx upgrade ruff` | `uv tool upgrade ruff` |
| pipx | `pipx list` | `uv tool list` |
| pipx | `pipx reinstall-all` | `uv tool upgrade --all` |
| pyenv | `pyenv install 3.12` | `uv python install 3.12` |
| pyenv | `pyenv versions` | `uv python list` |
| pyenv | `pyenv local 3.12` | `uv python pin 3.12` |
| pyenv | `pyenv global 3.12` | `uv python install 3.12 --default` |
| pyenv | `pyenv uninstall 3.12` | `uv python uninstall 3.12` |
| poetry | `poetry init` | `uv init` |
| poetry | `poetry add X` | `uv add X` |
| poetry | `poetry add -D X` | `uv add --dev X` |
| poetry | `poetry remove X` | `uv remove X` |
| poetry | `poetry install` | `uv sync` |
| poetry | `poetry lock` | `uv lock` |
| poetry | `poetry run X` | `uv run X` |
| poetry | `poetry shell` | N/A — use `uv run` instead |
| poetry | `poetry build` | `uv build` |
| poetry | `poetry publish` | `uv publish` |
| virtualenv | `python -m venv .venv` | `uv venv` |
| conda | `conda install X` | `uv add X` |

---

## From pip + requirements.txt

### Basic Migration

```bash
# 1. Initialize uv project
uv init

# 2. Import existing dependencies
uv add -r requirements.txt

# 3. Import dev dependencies (if separate file)
uv add --dev -r requirements-dev.txt

# 4. Verify everything works
uv run python -c "import myapp"

# 5. Remove old files (optional)
rm requirements.txt requirements-dev.txt
```

### Keep requirements.txt (Hybrid Approach)

If you need to maintain `requirements.txt` for other tools:

```bash
# Generate requirements.txt from lockfile
uv pip compile pyproject.toml -o requirements.txt
```

---

## From Poetry

### Migration Steps

```bash
# Option 1: Automated (recommended)
uvx migrate-to-uv
uvx migrate-to-uv --dry-run  # Preview first

# Option 2: Manual export
poetry export -f requirements.txt --output requirements.txt
poetry export -f requirements.txt --dev --output requirements-dev.txt
uv init
uv add -r requirements.txt
uv add --dev -r requirements-dev.txt
rm requirements.txt requirements-dev.txt
```

### Command Mapping

| Poetry | uv |
| ------ | -- |
| `poetry init` | `uv init` |
| `poetry add X` | `uv add X` |
| `poetry add -D X` | `uv add --dev X` |
| `poetry remove X` | `uv remove X` |
| `poetry install` | `uv sync` |
| `poetry lock` | `uv lock` |
| `poetry run X` | `uv run X` |
| `poetry shell` | N/A (use `uv run`) |
| `poetry build` | `uv build` |
| `poetry publish` | `uv publish` |

### pyproject.toml Differences

Poetry uses `[tool.poetry]` section. uv uses standard `[project]` (PEP 621):

```toml
# Poetry style (old)
[tool.poetry]
name = "myapp"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.28"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
```

```toml
# uv style (PEP 621 standard)
[project]
name = "myapp"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28",
]

[dependency-groups]
dev = [
    "pytest>=7.0",
]

[tool.uv]
# uv-specific settings
```

---

## From pipx

### Tool Migration

```bash
# List pipx tools
pipx list

# Install each with uv
uv tool install ruff
uv tool install black
uv tool install mypy

# Verify
uv tool list

# Uninstall pipx tools (optional)
pipx uninstall-all
```

### Command Mapping

| pipx | uv |
| ---- | -- |
| `pipx install X` | `uv tool install X` |
| `pipx run X` | `uvx X` |
| `pipx upgrade X` | `uv tool upgrade X` |
| `pipx uninstall X` | `uv tool uninstall X` |
| `pipx list` | `uv tool list` |
| `pipx reinstall-all` | `uv tool upgrade --all` |

---

## From pyenv

### Python Version Migration

```bash
# List pyenv versions
pyenv versions

# Install same versions with uv
uv python install 3.10 3.11 3.12

# Set default
uv python install --default

# Verify
uv python list --only-installed
```

### Command Mapping

| pyenv | uv |
| ----- | -- |
| `pyenv install 3.12` | `uv python install 3.12` |
| `pyenv versions` | `uv python list` |
| `pyenv local 3.12` | `uv python pin 3.12` |
| `pyenv global 3.12` | `uv python install 3.12 --default` |
| `pyenv uninstall 3.12` | `uv python uninstall 3.12` |

---

## From Conda

### Basic Migration

```bash
# Export conda environment
conda list --export > conda-packages.txt

# Review packages and install PyPI equivalents
uv init
uv add numpy pandas scikit-learn  # etc.
```

### Notes

- Conda packages are not always on PyPI
- Some scientific packages may need system dependencies
- Consider keeping conda for complex scientific stacks where PyPI equivalents are unavailable

---

## Common Issues

### Missing System Dependencies

Some packages require system libraries:

```bash
# Ubuntu/Debian example for psycopg2
sudo apt install libpq-dev

# Then add the package
uv add psycopg2
```

### Private Package Index

```toml
# pyproject.toml
[tool.uv]
index-url = "https://pypi.company.com/simple"
extra-index-url = ["https://pypi.org/simple"]
```

### Editable Installs

```bash
# Install local package in editable mode
uv add -e ./path/to/local/package
```

```toml
# Or in pyproject.toml
[tool.uv.sources]
mypackage = { path = "./packages/mypackage", editable = true }
```

### Platform-Specific Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "pywin32; sys_platform == 'win32'",
    "uvloop; sys_platform != 'win32'",
]
```
