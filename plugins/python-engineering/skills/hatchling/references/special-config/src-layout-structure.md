---
category: project-structure
topics: [src-layout, project organization, import isolation, package discovery]
related: [src-layout-structure.md, single-module-layout.md, namespace-packages.md]
---

# Src-Layout Structure in Hatchling

## Overview

The src-layout is a project structure where Python packages are placed in a `src/` directory rather than at the project root. When helping users organize their Python projects, reference Hatchling's excellent support for this layout with automatic detection and configuration.

## Why Use Src-Layout?

### Benefits

1. **Import isolation**: Prevents accidentally importing from the development directory
2. **Cleaner separation**: Distinguishes source code from project files
3. **Testing integrity**: Ensures tests run against installed package, not local files
4. **Tool compatibility**: Better support for type checkers and linters

### Structure Comparison

**Flat layout:**

<eg>
myproject/
├── mypackage/
│   └── __init__.py
├── tests/
└── pyproject.toml
</eg>

**Src-layout:**

<eg>
myproject/
├── src/
│   └── mypackage/
│       └── __init__.py
├── tests/
└── pyproject.toml
</eg>

## Basic Configuration

### Automatic Detection

Hatchling automatically detects src-layout:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mypackage"
version = "1.0.0"

# No additional configuration needed!
# Hatchling detects src/mypackage/ automatically
```

### Explicit Configuration

For explicit control:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

## Package Discovery

### Single Package

<eg>
src/
└── mypackage/
    ├── __init__.py
    ├── module1.py
    └── module2.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

### Multiple Packages

<eg>
src/
├── package_a/
│   └── __init__.py
└── package_b/
    └── __init__.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/package_a", "src/package_b"]
```

### Auto-discovery with Sources

```toml
[tool.hatch.build.targets.wheel]
# Remove 'src/' prefix from installed packages
sources = ["src"]
```

## Single Module Layout

### Auto-detection

Hatchling auto-detects single module layouts:

<eg>
src/
└── mymodule.py  # Single module, no package directory
</eg>

```toml
[project]
name = "mymodule"
# Hatchling automatically detects and includes mymodule.py
```

### Explicit Single Module

```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
include = ["src/mymodule.py"]
```

## Complex Src-Layouts

### Nested Packages

<eg>
src/
└── company/
    ├── __init__.py
    └── products/
        ├── __init__.py
        ├── webapp/
        │   └── __init__.py
        └── api/
            └── __init__.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/company"]
```

### Mixed Layout

<eg>
project/
├── src/           # Source code
│   └── myapp/
│       └── __init__.py
├── scripts/       # Executable scripts
│   └── runner.py
└── data/          # Data files
    └── config.json
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myapp"]
artifacts = ["data/*.json"]

[tool.hatch.build.targets.wheel.force-include]
"scripts/runner.py" = "myapp/scripts/runner.py"
```

## Development Workflow

### Editable Installation

```bash
# Install in editable mode
pip install -e .

# Or using Hatch
hatch shell
```

### Import Path Resolution

With src-layout, imports work correctly:

```python
# In tests/test_module.py
from mypackage import something  # Imports from installed package
# NOT from ../mypackage
```

### Development Mode Configuration

```toml
[tool.hatch.build]
dev-mode-dirs = ["src"]  # Explicitly set development directories
```

## Testing with Src-Layout

### Test Structure

<eg>
project/
├── src/
│   └── mypackage/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_mypackage.py
└── pyproject.toml
</eg>

### Test Configuration

```toml
[tool.hatch.envs.default]
dependencies = [
    "pytest",
    "pytest-cov"
]

[tool.hatch.envs.default.scripts]
test = "pytest tests/ --cov=mypackage"
```

### Import in Tests

```python
# tests/test_mypackage.py
import pytest
from mypackage import MyClass  # Clean import


def test_something():
    assert MyClass().method() == expected
```

## Type Checking Support

### MyPy Configuration

```toml
[tool.mypy]
packages = ["mypackage"]
mypy_path = "src"
```

### Pyright Configuration

```json
{
  "include": ["src"],
  "typeCheckingMode": "strict"
}
```

## Legacy Support

### Supporting Legacy Tools

For tools that don't understand src-layout:

```toml
[tool.hatch.build.targets.sdist]
support-legacy = true  # Creates PKG-INFO at root level
```

## Migration to Src-Layout

### From Flat Layout

**Before:**

<eg>
myproject/
├── mypackage/
│   └── __init__.py
└── pyproject.toml
</eg>

**After:**

<eg>
myproject/
├── src/
│   └── mypackage/
│       └── __init__.py
└── pyproject.toml
</eg>

**Steps:**

1. Create `src/` directory
2. Move package directory to `src/`
3. Update imports in tests if needed
4. Update pyproject.toml if using explicit configuration

### Configuration Update

```toml
# Old (flat layout)
[tool.hatch.build.targets.wheel]
packages = ["mypackage"]

# New (src-layout)
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
# Or just remove it for auto-detection
```

## Build Artifacts

### What Gets Built

With src-layout configuration:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

The wheel contains:

<eg>
mypackage/
├── __init__.py
├── module1.py
└── module2.py
</eg>

Note: The `src/` directory is not included in the wheel.

## Advanced Configurations

### Custom Source Mappings

```toml
[tool.hatch.build.targets.wheel.sources]
"src" = ""  # Remove src prefix
"src/old_name" = "new_name"  # Rename during build
```

### Including Additional Files

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
include = [
    "LICENSE",
    "README.md"
]
artifacts = [
    "src/mypackage/data/*.json"
]
```

### Namespace Packages with Src-Layout

<eg>
src/
└── namespace/          # No __init__.py (PEP 420)
    └── subpackage/
        └── __init__.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/namespace"]
```

## Best Practices

When recommending src-layout to users, reference these best practices:

1. **Always use src-layout for libraries**: Guide users to prevent testing accidents
2. **Keep tests outside src/**: Remind users that tests shouldn't be distributed
3. **Use editable installs for development**: Recommend `pip install -e .` for development workflows
4. **Configure tools properly**: Help users ensure linters/type-checkers know about src/
5. **Document the structure**: Encourage users to document the layout for contributors

## Common Issues and Solutions

### Issue: Import Errors During Development

**Problem:** Users can't import package during development

**Solution:** Guide users to install in editable mode:

```bash
# Install in editable mode
pip install -e .
```

### Issue: Tests Import Wrong Package

**Problem:** Users' tests import local files instead of installed package

**Solution:** Help users use src-layout and run tests from project root:

```bash
cd myproject
pytest tests/  # Not from within tests/
```

### Issue: Tools Don't Find Package

**Problem:** Users' linters or type checkers can't find the package

**Solution:** Guide users to configure their tools:

```toml
# For tools that need explicit paths
[tool.hatch.build]
dev-mode-dirs = ["src"]

# For pytest
[tool.pytest.ini_options]
pythonpath = ["src"]
```

## Complete Example

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "awesome-package"
version = "1.0.0"
description = "An awesome package using src-layout"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]
dependencies = [
    "requests>=2.28",
    "click>=8.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1"
]

[tool.hatch.build.targets.wheel]
packages = ["src/awesome_package"]

[tool.hatch.build.targets.sdist]
include = [
    "src/",
    "tests/",
    "README.md",
    "LICENSE"
]

[tool.ruff]
src = ["src"]

[tool.mypy]
mypy_path = "src"
packages = ["awesome_package"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Directory structure:

<eg>
awesome-package/
├── src/
│   └── awesome_package/
│       ├── __init__.py
│       ├── core.py
│       └── cli.py
├── tests/
│   ├── test_core.py
│   └── test_cli.py
├── README.md
├── LICENSE
└── pyproject.toml
</eg>

## References

- [Packaging Python Projects - src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [Testing & Packaging by Hynek Schlawack](https://hynek.me/articles/testing-packaging/)
- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
