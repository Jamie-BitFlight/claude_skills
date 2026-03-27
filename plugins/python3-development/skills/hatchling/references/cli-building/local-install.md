---
category: cli-building
topics: [local-installation, editable-install, development-workflow, pip]
related: [index.md, overview.md, building-wheels.md, building-sdist.md, output-customization.md]
---

# Installing from Local Path

## Overview

Local installation enables developers to install packages directly from project directories, supporting development workflows, testing scenarios, and private package deployment. Reference this when helping users understand editable installs, optional dependencies, virtual environment setup, and package manager options (pip, uv, pipx, Poetry).

## Basic Local Installation

### Install from Current Directory

```bash
# Install package from current directory
pip install .

# Install with verbose output
pip install -v .

# Install without build isolation
pip install --no-build-isolation .
```

### Install from Specific Path

```bash
# Install from absolute path
pip install /path/to/package

# Install from relative path
pip install ../my-package

# Install from user home directory
pip install ~/projects/my-package
```

## Editable (Development) Installation

Editable installs create a link to your development directory instead of copying files, allowing changes to take effect immediately without reinstalling.

### Basic Editable Install

```bash
# Install in editable/development mode
pip install -e .
pip install --editable .

# From specific path
pip install -e /path/to/package

# With verbose output
pip install -v -e .
```

### With Optional Dependencies

```bash
# Install with development dependencies
pip install -e ".[dev]"
pip install -e ".[test]"
pip install -e ".[dev,test,docs]"

# On zsh (escape brackets)
pip install -e ".\[dev\]"

# Or use quotes
pip install -e '.[dev]'
```

## Configuration in pyproject.toml

### Basic Configuration

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
dependencies = [
  "requests>=2.28.0",
  "click>=8.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=7.0.0",
  "black>=22.0.0",
  "mypy>=0.990",
]
test = [
  "pytest>=7.0.0",
  "pytest-cov>=4.0.0",
]
```

### Editable Install Configuration

```toml
# Configure editable installs
[tool.hatch.build]
dev-mode-dirs = ["."]
dev-mode-exact = false

# Force include for editable installs
[tool.hatch.build.targets.wheel.force-include-editable]
"src/mypackage" = "mypackage"
```

## Using Different Package Managers

### pip

```bash
# Standard install
pip install .

# Editable install
pip install -e .

# With extras
pip install -e ".[dev,test]"

# Force reinstall
pip install --force-reinstall .

# Upgrade
pip install --upgrade .
```

### uv (Fast Python Package Manager)

```bash
# Install with uv
uv pip install .

# Editable install
uv pip install -e .

# With extras
uv pip install -e ".[dev]"

# From requirements
uv pip install -r requirements.txt -e .
```

### pipx (For Applications)

```bash
# Install application globally
pipx install .

# Install from path
pipx install /path/to/package

# Install editable
pipx install --editable .
```

### Poetry

```toml
# In pyproject.toml
[tool.poetry.dependencies]
my-local-package = {path = "../my-local-package", develop = true}
```

```bash
# Install with poetry
poetry install
```

### Pipenv

```toml
# In Pipfile
[packages]
my-package = {editable = true, path = "."}
```

```bash
# Install with pipenv
pipenv install -e .
```

## Advanced Installation Options

### Build and Install

```bash
# Build first, then install
python -m build
pip install dist/*.whl

# Build and install in one step
pip install --no-build-isolation -e .
```

### Install with Specific Python Version

```bash
# Use specific Python version
python3.11 -m pip install .

# With virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
```

### Install with Environment Variables

```bash
# Set environment variables during install
SETUPTOOLS_ENABLE_FEATURES=legacy-editable pip install -e .

# With custom build options
PIP_NO_BUILD_ISOLATION=1 pip install .
```

## Virtual Environment Setup

### Create and Activate Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install package
pip install -e .
```

### Using conda

```bash
# Create conda environment
conda create -n myenv python=3.11
conda activate myenv

# Install local package
pip install -e .
```

## Development Workflow

### Typical Development Setup

```bash
# Clone repository
git clone https://github.com/user/package.git
cd package

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Project Structure

<eg>
my-package/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── main.py
├── tests/
│   └── test_main.py
├── pyproject.toml
├── README.md
└── requirements-dev.txt
</eg>

### Install with Requirements Files

```bash
# Install package and additional requirements
pip install -e .
pip install -r requirements-dev.txt

# Or in one command
pip install -e . -r requirements-dev.txt
```

## Verification

### Verify Installation

```bash
# Check if package is installed
pip list | grep my-package

# Show package information
pip show my-package

# Test import
python -c "import mypackage; print(mypackage.__version__)"
```

### Run Tests

```bash
# Run tests after installation
pytest

# Run with coverage
pytest --cov=mypackage

# Run specific test file
pytest tests/test_main.py
```

## Troubleshooting

### Common Issues

1. **Import errors after editable install**

   ```bash
   # Ensure package structure is correct
   # Check PYTHONPATH
   echo $PYTHONPATH

   # Reinstall
   pip uninstall my-package
   pip install -e .
   ```

2. **Dependencies not installed**

   ```bash
   # Install with all dependencies
   pip install -e ".[all]"

   # Or install dependencies separately
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Changes not reflected in editable mode**

   ```bash
   # Restart Python interpreter
   # Or reload module
   import importlib
   importlib.reload(mypackage)
   ```

4. **Permission errors**

   ```bash
   # Use --user flag
   pip install --user -e .

   # Or use virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

## Best Practices

1. **Always use virtual environments** for development
2. **Use editable installs** for active development
3. **Include development dependencies** in optional-dependencies
4. **Test both editable and normal** installations
5. **Document installation steps** in README
6. **Use absolute paths** in CI/CD pipelines
7. **Clean install for testing**: `pip install --force-reinstall --no-deps .`

## CI/CD Local Installation

### GitHub Actions

```yaml
- name: Install package
  run: |
    pip install --upgrade pip
    pip install -e ".[test]"
```

### Docker

```dockerfile
FROM python:3.11

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

CMD ["python", "-m", "mypackage"]
```

## File URI Installation

```bash
# Install from file URI
pip install file:///absolute/path/to/package

# On Windows
pip install file:///C:/path/to/package

# Editable install with file URI
pip install -e file:///path/to/package
```

## See Also

- [pip Documentation](https://pip.pypa.io/)
- [Editable Installs (PEP 660)](https://www.python.org/dev/peps/pep-0660/)
- `building-wheels.md`
- [Development Mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html)
