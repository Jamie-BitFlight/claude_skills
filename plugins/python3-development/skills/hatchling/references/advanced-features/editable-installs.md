---
category: Advanced Build Features
topics: [editable-installs, pep-660, development-workflow, dev-mode, package-discovery]
related: [build-context.md, build-data-passing.md, dynamic-dependencies.md]
---

# Editable Installs

When helping users set up rapid development workflows, guide them to use editable installs (PEP 660) where installed packages reflect source code changes without reinstallation. Hatchling provides flexible configuration for different editable install strategies.

## Overview

Editable installs create a lightweight installation that forwards imports to the source directory, allowing rapid iteration during development. Show users how changes to source files become immediately visible without rebuild steps.

## PEP 660 Support

Hatchling implements PEP 660 - "Editable Installs for Python Packages". This standard specifies how build backends support development mode installations.

## Installation Methods

### Standard Editable Install

```bash
pip install -e .
```

This creates an editable installation in your environment. The package is installed but imports resolve to your source tree.

### With Extras

```bash
pip install -e ".[dev,docs]"
```

Install in editable mode with optional dependency groups.

## Configuration Options

### dev-mode-dirs

Specify which directories to include in editable installs:

```toml
[tool.hatchling.targets.wheel.editable]
packages = ["src/mypackage", "src/myutils"]
```

This tells Hatchling which package directories should be included in editable mode.

### dev-mode-exact

Control whether to use exact package discovery or path searching:

```toml
[tool.hatchling.targets.wheel.editable]
packages = ["src/mypackage"]
```

When set, only explicitly listed packages are included.

## Build Hook Integration

Custom hooks can control editable install behavior:

```python
class EditableHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Modify editable installation configuration
        # during build process
        pass

    def finalize(self, version, build_data, artifact):
        # Verify editable artifacts after build
        pass
```

## How Editable Installs Work

### The .pth File Approach

Traditional editable installs (before PEP 660) used `.pth` files:

<eg>
site-packages/mypackage.pth
Contents: /path/to/your/project/src
</eg>

When Python starts, it reads `.pth` files and adds listed paths to `sys.path`.

### PEP 660 Approach

Hatchling's PEP 660 implementation creates a more sophisticated mechanism that:

1. Creates a small installed package (`.dist-info`)
2. Adds source directories to import path
3. Maintains metadata compatibility
4. Supports entry points and extras

### Finder Mechanism

The editable install creates a path-based finder that intercepts imports:

```python
# Internal mechanism (conceptual)
import sys
sys.path.insert(0, '/path/to/project/src')

# Now 'import mypackage' finds /path/to/project/src/mypackage
```

## Package Discovery in Editable Mode

### Automatic Discovery

By default, Hatchling discovers packages in configured source directories:

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage", "src/myutils"]
```

Both packages are available in editable installs.

### Namespace Packages

Namespace packages are fully supported:

```toml
[tool.hatchling.targets.wheel]
packages = [
    "src/mycompany.core",
    "src/mycompany.utils"
]
```

The `mycompany` namespace spans multiple packages.

## Development Workflow Benefits

### Immediate Testing

```bash
# Install once in editable mode
pip install -e .

# Make code changes - no reinstall needed
# Changes visible immediately on next import
```

### Testing Multiple Packages

```bash
# Install multiple related packages in editable mode
pip install -e ./core -e ./utils -e ./api

# Changes in any package reflected immediately
# Perfect for monorepo development
```

### Integration with IDEs

Most Python IDEs recognize editable installs:

- PyCharm: Detects editable packages and enables debugging
- VS Code with Pylance: Full type checking and intellisense
- IDEs can follow imports directly to source

## Constraints and Limitations

### Entry Points

Entry points (console scripts, plugins) work but have limitations:

```toml
[project.scripts]
mycli = "mypackage.cli:main"
```

Entry point in editable mode will:

- Resolve to your source code
- Require reinstall if entry point definition changes
- Work correctly for function calls themselves

### Data Files

Non-Python data files in editable installs:

```python
# This works - finding package
import mypackage
package_dir = os.path.dirname(mypackage.__file__)
data_file = os.path.join(package_dir, 'data.json')
```

Files must be alongside Python modules in source directory.

### C Extensions

Compiled extensions in editable installs:

```toml
[build-system]
requires = ["hatchling", "hatchling-fancy-pypi-readme"]
```

Compiled extensions require recompilation after changes. They don't benefit from the "editable" aspect - reinstall needed.

## Best Practices

- Use editable installs for all local development work
- Combine with `pip install -e ".[dev]"` to include test/lint dependencies
- Test final wheel builds separately before release
- Document editable setup in project's CONTRIBUTING guide
- Create simple setup script for developers:

```bash
#!/bin/bash
# development-setup.sh
python -m pip install -e ".[dev,docs]"
pre-commit install
```

- Verify entry points work by reinstalling periodically

## Troubleshooting

### Import Not Finding Changes

**Issue**: Changes to source files not visible after import

**Solution**: Reload module in Python:

```python
import importlib
import mypackage

# Make changes to source
importlib.reload(mypackage)
```

### Entry Point Not Working

**Issue**: Console script fails after code changes

**Solution**: Reinstall to update entry point:

```bash
pip install -e .  # Reinstall to update entry point metadata
```

### Namespace Package Not Working

**Issue**: Multiple editable packages in same namespace conflict

**Solution**: Ensure all packages have proper `__init__.py` or namespace declarations:

```python
# src/mycompany/__init__.py
# For namespace package support
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
```

## See Also

- `build-context.md` - Access to build environment during editable installs
- `build-data-passing.md` - Modifying editable behavior in hooks
- `dynamic-dependencies.md` - Dev dependencies for editable installs
