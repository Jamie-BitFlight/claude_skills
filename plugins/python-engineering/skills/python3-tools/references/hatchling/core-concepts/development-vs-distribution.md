---
category: core-concepts
topics: [editable-installs, development-workflow, distribution, PEP-660]
related: [wheel-vs-sdist.md, build-hooks.md, version-management.md]
---

# Development vs Distribution Builds

## Overview

When guiding users through development and release workflows, reference this document to understand how Hatchling distinguishes between builds for development (editable installs) and builds for distribution (wheels and sdists for end users), explaining the differences, trade-offs, and best practices.

**Source:** [PEP 660 - Editable Installs](https://peps.python.org/pep-0660/) [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)

## Core Concepts

### Distribution Build

A distribution build creates packages for end users on PyPI.

**Characteristics:**

- Standalone and self-contained
- Optimized for installation speed
- No build artifacts included
- Immutable once released
- Usually built once per version

**Format:**

- Wheel (.whl)
- Source distribution (.tar.gz)

**Example:**

```bash
hatch build
# Creates:
# dist/myproject-1.0.0-py3-none-any.whl
# dist/myproject-1.0.0.tar.gz
```

### Development Build

A development build is for working on the package locally.

**Characteristics:**

- Live connection to source code
- Changes immediately visible
- Includes development tools and tests
- Mutable (updated when code changes)
- Built once per environment

**Format:**

- Editable install (PEP 660)

**Example:**

```bash
pip install -e .
# Creates link from site-packages to source code
# Changes immediately visible
```

## Editable Installs (Development Builds)

### What is an Editable Install?

An editable install (PEP 660) links to your source code without copying it.

**How it works:**

<eg>
Python path:
  site-packages/myproject-1.0.0.dist-info/
    direct_url.json  → /home/user/projects/myproject

Import:
  import myproject  → /home/user/projects/myproject/__init__.py
</eg>

**Effect:** Changes to source are immediately visible.

### Creating Editable Installs

```bash
# Basic editable install
pip install -e .

# With optional dependencies
pip install -e ".[dev]"

# With extras
pip install -e ".[dev,docs]"
```

### Editable Install Process

<eg>
1. pip discovers build backend (hatchling)
2. hatchling builds editable wheel
3. Wheel contains:
   - direct_url.json (points to source)
   - .pth files (add source to path)
4. pip installs wheel
5. Result: import finds source code
</eg>

### Benefits of Editable Installs

**For Active Development:**

```python
# Edit src/myproject/module.py
def function():
    return "v2"  # Changed from v1

# In REPL:
>>> import myproject
>>> myproject.function()
'v2'  # Immediately sees change (no reinstall needed)
```

**Compared to non-editable:**

```bash
# Without editable install:
# Must reinstall after every change
pip install .  # Slow!

# With editable install:
# Changes visible immediately
# No reinstall needed
```

### Editable Install Limitations

Some things still require reinstall even with editable install:

**Require reinstall:**

- Metadata changes (new dependencies)
- Entry point changes
- Package data changes
- C extension changes

**Work without reinstall:**

- Python source code edits
- Data file edits (if already discovered)
- Configuration changes

### Hatchling's Editable Implementation

Hatchling creates minimal editable wheels:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
```

Creates editable wheel with:

<eg>
- `.pth` file pointing to src/
- Metadata from pyproject.toml
- No build steps (unless configured)
</eg>

## Distribution Builds (Production)

### Purpose

Distribution builds are for packaging versions to share on PyPI.

**Goals:**

- Reproducible builds
- Maximum compatibility
- Fast installation (pre-built)
- Verifiable integrity

### Build Configuration

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
# No special handling needed

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]
```

### Wheel Distribution

Wheels are pre-built, ready to install:

```bash
hatch build --target wheel

# Creates:
pip install dist/myproject-1.0.0-py3-none-any.whl
# Installation: copy files (fast)
# No build needed
```

### Source Distribution

Source distributions allow building on different platforms:

```bash
hatch build --target sdist

# Creates:
pip install dist/myproject-1.0.0.tar.gz
# Installation: extract and build
# Uses your build backend
```

## Different Configurations for Different Contexts

### Same Configuration Works for Both

For most projects, same configuration works:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
]
```

**Behavior:**

```bash
pip install -e .           # Editable: uses wheel config
hatch build --target wheel # Distribution: uses wheel config
hatch build --target sdist # Distribution: uses sdist config
```

### Different Configurations if Needed

Different wheels and sdists (uncommon):

```toml
# Editable install
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
# Minimal, quick to build

# Distribution wheel
[tool.hatch.build.targets.wheel.versions.standard]
packages = ["src/myproject"]
# Could have different configuration

# Distribution sdist
[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/docs",
    "/README.md",
    "/LICENSE",
]
# Includes more for developers
```

## Installation Workflows

### Development Workflow

```bash
# 1. Clone repository
git clone https://github.com/org/myproject.git
cd myproject

# 2. Create virtual environment
python -m venv venv
. venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Editable install for development
pip install -e ".[dev]"

# 4. Work on code
# - Edit src/myproject/module.py
# - Changes immediately visible
# - No reinstall needed

# 5. Run tests
pytest

# 6. Commit and push
git commit -m "..."
git push
```

### Distribution Installation (User)

```bash
# 1. Install from PyPI (wheel preferred)
pip install myproject

# 2. Or from source (sdist)
pip install myproject[version]
# pip downloads sdist, builds, installs

# 3. Use installed package
python -c "import myproject; print(myproject.__version__)"
```

### Release Workflow

```bash
# 1. Update version
# Edit src/myproject/__init__.py
__version__ = "1.1.0"

# 2. Tag release
git tag v1.1.0

# 3. Build distributions
hatch build
# Creates wheel and sdist

# 4. Upload to PyPI
twine upload dist/*

# 5. Users can now install
pip install myproject==1.1.0
```

## Build Hooks and Development vs Distribution

### Build Hooks Behavior

Hooks run for both editable and distribution builds.

**Editable build:**

```bash
pip install -e .
# Runs: BuildHookInterface.initialize()
# Runs: BuildHookInterface.finalize()
```

**Distribution build:**

```bash
hatch build
# Runs: BuildHookInterface.initialize()
# Runs: BuildHookInterface.finalize()
```

### Conditional Hook Logic

Hooks can behave differently based on context:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class ConditionalHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Determine if editable or distribution build
        builder_name = self.builder.name  # 'wheel' or 'sdist'

        if builder_name == 'wheel':
            # For both editable and wheel distribution
            # Generate minimal artifacts
            self._generate_version_file(version)
        elif builder_name == 'sdist':
            # Only for source distribution
            # Can include more files
            self._include_test_data()
```

## Best Practices

### 1. Use Editable Install for Development

```bash
# Always editable when developing
pip install -e ".[dev]"

# Never for development:
pip install .  # Don't do this while developing
```

Why: Changes visible immediately, no reinstall needed.

### 2. Test Distribution Builds Before Release

```bash
# Build what you're about to release
hatch build

# Test wheel installation in clean environment
python -m venv test_env
test_env/bin/pip install dist/*.whl
test_env/bin/python -c "import myproject; print(myproject.__version__)"

# Test sdist installation
test_env/bin/pip install dist/*.tar.gz
test_env/bin/python -c "import myproject; print(myproject.__version__)"
```

### 3. Different Dependencies for Development

```toml
[project]
name = "myproject"
dependencies = [
    "requests>=2.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black",
    "ruff",
]

doc = [
    "sphinx>=5.0",
    "sphinx-rtd-theme",
]
```

Development install:

```bash
pip install -e ".[dev,doc]"  # All extras
```

Distribution:

```bash
hatch build  # Only requires `requests`
```

### 4. Document Installation

In README:

````markdown
## Installation

### For Users

```bash
pip install myproject
```

### For Development

```bash
git clone https://github.com/org/myproject.git
cd myproject
pip install -e ".[dev]"
```

Run tests with: `pytest`
````

### 5. Version Source Strategy

**For development:**

```python
# Easy to edit for testing
__version__ = "0.2.0.dev0"
```

**For VCS-based versioning:**

```bash
# Automatic in distribution builds
# During development: 0.2.0.dev3+g12345
# After tag: 0.2.0 exactly
```

## Common Issues and Solutions

### Issue 1: Changes Not Visible After Edit

**Problem:**

```bash
pip install -e .
# Edit module.py
python -c "import myproject; print(myproject.func())"
# Still old behavior
```

**Solution:**

- Python caches imports
- Either restart Python or use importlib.reload()

```python
import myproject
import importlib
importlib.reload(myproject)
print(myproject.func())  # Now shows new behavior
```

### Issue 2: Editable Install Doesn't Include New Dependencies

**Problem:**

```toml
# Added new dependency
[project]
dependencies = [
    "requests>=2.28.0",
    "aiohttp>=3.8.0",  # New!
]
```

**Solution:** Reinstall editable

```bash
pip install -e .  # Re-reads pyproject.toml
```

### Issue 3: Metadata Not Updated in Editable

**Problem:**

```toml
# Changed entry point
[project.scripts]
my-script = "myproject.cli:main"  # Added new entry point
```

**Solution:** Reinstall editable

```bash
pip install -e .  # Re-reads pyproject.toml
```

## Key Takeaways

1. **Editable installs** (`pip install -e .`) link to source for development
2. **Distribution builds** create wheels and sdists for users
3. **Same configuration** usually works for both
4. **Changes visible immediately** with editable installs
5. **Metadata changes** (dependencies, entry points) require reinstall even with editable
6. **Test distributions** before release
7. **Separate optional dependencies** for dev from runtime

## References

- [PEP 660 - Editable installs for pyproject.toml based builds](https://peps.python.org/pep-0660/)
- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- [Python Packaging Guide - Installation](https://packaging.python.org/tutorials/installing-packages/)
