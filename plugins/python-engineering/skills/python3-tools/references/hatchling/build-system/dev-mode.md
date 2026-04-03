---
category: build-system
topics:
- dev-mode
- editable-installs
- development-mode
- pip-editable
- dev-mode-dirs
related:
- build-options
- editable-installs
- build-environment
---

# Development Mode Configuration Guide for Claude

This reference helps Claude configure development/editable installations for Hatchling projects. Development mode allows code changes to take effect immediately without reinstalling.

## Core Concept

In development mode:

- Source code changes reflect immediately
- No reinstall needed after modifications
- Import statements work as if installed
- Debugging and testing simplified

## Basic Configuration

### Default Setup

```toml
[tool.hatch.build]
# Current directory is dev root (default)
dev-mode-dirs = ["."]

# Exact path matching
dev-mode-exact = false  # Default: fuzzy matching
```

### Multiple Development Directories

For monorepo or shared libraries:

```toml
[tool.hatch.build]
# Include multiple directories
dev-mode-dirs = [
    ".",
    "../shared-library",
    "../common-utils",
]
```

## Installation Methods

### Using pip

Standard editable installation:

```bash
# Install in editable mode
pip install -e .

# With extras
pip install -e ".[dev,test]"

# From different directory
pip install -e /path/to/project
```

### Using Hatch

Automatic dev mode in Hatch environments:

```bash
# Enter development environment
hatch shell

# Package automatically in dev mode
python -c "import mypackage"  # Works immediately
```

### Using uv

Fast editable installation:

```bash
# Install with uv
uv pip install -e .

# Or sync environment
uv sync
```

## Source Layouts

### Flat Layout

<eg>
project/
├── pyproject.toml
├── mypackage/
│   ├── __init__.py
│   └── module.py
└── tests/
</eg>

Configuration:

```toml
[tool.hatch.build]
dev-mode-dirs = ["."]
```

### Src Layout

<eg>
project/
├── pyproject.toml
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
└── tests/
</eg>

Configuration:

```toml
[tool.hatch.build]
dev-mode-dirs = ["src"]

# Or with path mapping
[tool.hatch.build.sources]
"src" = ""
```

### Monorepo Layout

<eg>
monorepo/
├── packages/
│   ├── lib-a/
│   │   ├── pyproject.toml
│   │   └── src/
│   └── lib-b/
│       ├── pyproject.toml
│       └── src/
└── apps/
</eg>

In lib-b's pyproject.toml:

```toml
[tool.hatch.build]
dev-mode-dirs = [
    "src",
    "../../packages/lib-a/src",  # Include lib-a
]
```

## Dev Mode Mechanisms

### Path File Method (.pth)

Default method - creates `.pth` file:

- Simple and reliable
- Works with all tools
- Standard Python mechanism

Example `.pth` file in site-packages:

<eg>
/absolute/path/to/project/src
</eg>

### Import Hook Method

Alternative using import hooks:

- More flexible path mapping
- Better for complex layouts
- Supports dynamic resolution

## IDE Integration

### VS Code

Configure for development:

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.analysis.extraPaths": ["./src", "../shared-lib/src"]
}
```

### PyCharm

1. Mark directories as "Sources Root"
2. Configure Python interpreter
3. Add content roots for dev-mode-dirs

### Jupyter/IPython

Auto-reload for development:

```python
# Enable auto-reload
%load_ext autoreload
%autoreload 2

# Changes reflect immediately
import mypackage
```

## Advanced Configurations

### Namespace Packages

```toml
[tool.hatch.build]
# For namespace packages
dev-mode-dirs = ["src"]
dev-mode-exact = true

# Structure:
# src/
#   namespace/
#     package/
#       __init__.py
```

### Conditional Dev Mode

Different modes for environments:

```toml
# Development environment
[tool.hatch.envs.dev]
dev-mode = true
dev-mode-dirs = [".", "../lib"]

# Test environment
[tool.hatch.envs.test]
dev-mode = true
dev-mode-dirs = ["."]

# Production environment
[tool.hatch.envs.production]
dev-mode = false
```

### With Compiled Extensions

Handle extensions in dev mode:

```python
# Build extensions in-place
# setup.py compatibility
from setuptools import setup, Extension

ext_modules = [
    Extension(
        "mypackage._speedups",
        sources=["src/speedups.c"],
    )
]

# Build command
# python setup.py build_ext --inplace
```

## Common Workflows

### Local Development

Standard setup process:

```bash
# Clone and setup
git clone https://github.com/user/project
cd project

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in dev mode
pip install -e ".[dev]"

# Start developing
python -c "import mypackage"
```

### Multi-Package Development

Develop multiple packages together:

```toml
[tool.hatch.build]
dev-mode-dirs = [
    ".",
    "../package-a",
    "../package-b",
]

[tool.hatch.envs.default]
dependencies = [
    "package-a @ file:///../package-a",
    "package-b @ file:///../package-b",
]
```

## Troubleshooting

### Module Not Found

When imports fail:

```bash
# Verify installation
pip list | grep mypackage

# Check import paths
python -c "import sys; print(sys.path)"

# Reinstall in dev mode
pip uninstall mypackage
pip install -e .
```

### Changes Not Reflected

When code changes don't appear:

```python
# Force reload in Python
import importlib
import mypackage
importlib.reload(mypackage)

# Or restart interpreter
```

### Path Issues

For path problems:

```toml
[tool.hatch.build]
# Use absolute paths if relative fail
dev-mode-dirs = ["/absolute/path/to/project"]

# Or use environment variables
dev-mode-dirs = ["${PROJECT_ROOT}"]
```

## CI/CD Considerations

### Development Builds

For testing with live code:

```yaml
# GitHub Actions
- name: Install in dev mode
  run: |
    pip install -e .
    pytest tests/

# Test with coverage
- name: Test with live code
  run: |
    pip install -e ".[test]"
    pytest --cov=mypackage
```

### Production Builds

Never use dev mode in production:

```yaml
# Build and install wheel
- name: Build for production
  run: |
    pip install build
    python -m build
    pip install dist/*.whl
```

## Best Practices to Recommend

### Project Structure

1. Use src layout for clear separation
2. Keep dev-mode-dirs simple
3. Document dev setup in README

### Development Workflow

1. Test both dev and regular installation
2. Use consistent paths across team
3. Configure IDE properly

### Environment Management

1. Use virtual environments
2. Pin development dependencies
3. Clean install periodically

## Testing Dev Mode

### Verify Dev Mode Active

```python
# test_dev_mode.py
import sys
from pathlib import Path

def test_dev_mode_active():
    """Verify package is in dev mode."""
    import mypackage

    # Check if imported from source
    package_file = Path(mypackage.__file__)
    assert "site-packages" not in str(package_file)
    assert package_file.exists()
```

### Integration Test

```bash
#!/bin/bash
# test_dev_install.sh

# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install in dev mode
pip install -e .

# Test import
python -c "import mypackage; print(mypackage.__file__)"

# Modify source
echo "TEST = 'modified'" >> src/mypackage/test.py

# Verify change reflected
python -c "from mypackage.test import TEST; assert TEST == 'modified'"
```

## Navigation

- `build-options.md` - General build configuration
- `../advanced-features/editable-installs.md` - Advanced editable installation
- `../build-environment/README.md` - Environment setup
