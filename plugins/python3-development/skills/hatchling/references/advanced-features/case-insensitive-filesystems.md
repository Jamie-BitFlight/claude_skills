---
category: Advanced Build Features
topics: [case-insensitive-filesystems, portability, cross-platform, package-naming, pep-503]
related: [path-rewriting.md, distributed-artifacts.md, build-context.md]
---

# Case-Insensitive Filesystems

When helping users debug cross-platform issues, guide them to understand how case-insensitive filesystems (macOS HFS+/APFS, Windows NTFS) present challenges for Python packaging where the standard is case-sensitive. Understanding these differences prevents portability problems.

## Overview

Python package names are case-sensitive on Linux but case-insensitive on macOS and Windows. Show users how this creates:

- Import path mismatches between platforms
- Distribution naming issues
- Package discovery problems
- Data file location conflicts

## Filesystem Differences

### Linux Filesystems

Ext4, btrfs, XFS are case-sensitive:

```bash
# Linux - both files can exist simultaneously
MyPackage.py
mypackage.py

# Python imports are case-sensitive
import MyPackage   # Imports MyPackage.py
import mypackage   # Imports mypackage.py
```

### macOS Filesystems

HFS+ and APFS are case-insensitive but case-preserving:

```bash
# macOS - only one file despite case differences
MyPackage.py
mypackage.py  # Overwrites or renames MyPackage.py

# Python behavior
import MyPackage   # Works
import mypackage   # Works (case-insensitive match)
```

### Windows Filesystems

NTFS is case-insensitive:

```bash
# Windows - case preserved but insensitive
MyPackage.py
mypackage.py  # Creates same file, preserves casing

# Python behavior
import MyPackage   # Works
import mypackage   # Works (case-insensitive match)
```

## Package Name Normalization

PEP 503 normalizes package names by:

- Converting to lowercase
- Replacing runs of `[-_.]+` with a single underscore

<eg>
MyPackage      → mypackage
my-package     → my_package
My.Package.v1  → my_package_v1
</eg>

Hatchling applies normalization for distribution metadata:

```toml
[project]
name = "MyPackage"
# Normalized to: mypackage
```

Distribution filename:

- Built wheel: `mypackage-1.0.0-py3-none-any.whl` (lowercase)
- Metadata: `mypackage-1.0.0.dist-info/` (lowercase)

## Import Path Mismatches

### Common Problem

Package directory on disk with non-standard casing:

<eg>
# Actual directory structure (created on macOS)
MyPackage/
├── __init__.py
└── module.py

# Import statement
import MyPackage

# On Linux - works
# On macOS/Windows - works
# But distribution name is: mypackage
</eg>

When installed from PyPI, the package installs as lowercase:

<eg>
site-packages/mypackage/
</eg>

But the import path expected might differ:

```python
import MyPackage   # Fails after installation from PyPI
```

### Solution: Canonical Case

Use lowercase package names throughout:

```bash
# Directory name - lowercase
mypackage/
├── __init__.py
└── module.py

# pyproject.toml
[project]
name = "mypackage"

# Import
import mypackage
```

## Hatchling's Case Handling

### Package Discovery

Hatchling finds packages with glob patterns:

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]
```

On case-insensitive systems, discovery is more permissive but normalizes names.

### Wheel Metadata

Wheel filenames and metadata always use normalized (lowercase) names:

<eg>
Distribution: MyPackage (pyproject.toml)
Wheel file: mypackage-1.0.0-py3-none-any.whl
dist-info dir: mypackage-1.0.0.dist-info
</eg>

### Top-Level File

The `top_level.txt` file in wheel metadata specifies importable names:

<eg>
# mypackage-1.0.0.dist-info/top_level.txt
mypackage
</eg>

This tells tools what can be imported - typically lowercase.

## Handling Mixed-Case Namespaces

Namespace packages can have mixed casing issues:

```toml
[project]
name = "mycompany-core"

[tool.hatchling.targets.wheel]
packages = ["src/mycompany/core"]
```

Directory structure:

<eg>
src/mycompany/core/
├── __init__.py
└── service.py

# For namespace package support
src/mycompany/__init__.py  # Empty or namespace config
</eg>

Import path:

```python
import mycompany.core  # Lowercase throughout
```

## Platform-Specific Behavior

### Data Files and Resource Paths

```python
import mypackage
import os

# Get package directory
package_dir = os.path.dirname(mypackage.__file__)

# On Linux: /usr/lib/python3.x/site-packages/mypackage
# On macOS/Windows: C:\Python\Lib\site-packages\mypackage
#                   or /usr/local/lib/python3.x/site-packages/mypackage

# Case doesn't matter on macOS/Windows but do for Linux
data_file = os.path.join(package_dir, 'data/config.json')
```

### Path Joining

Always use `os.path.join()` for portability:

```python
# Good - portable across case-sensitive and insensitive systems
config_path = os.path.join(package_dir, 'config', 'settings.json')

# Risky - may fail on case-sensitive systems if naming differs
config_path = 'mypackage/config/settings.json'
```

## Practical Examples

### Fixing Case-Sensitivity Issues

Problem: Package works on macOS, fails on Linux:

<eg>
# Current structure (created on macOS)
MyPackage/
├── __init__.py
└── module.py

# Error on Linux
ImportError: cannot import name MyPackage
</eg>

Solution: Rename to lowercase:

```bash
git mv MyPackage mypackage
# Update any hardcoded imports
```

### Build Hook for Case Validation

```python
class CaseValidationHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Validate package names follow case conventions"""
        # Get package names from configuration
        # Compare against expected lowercase versions

        for file in build_data['artifacts']['wheel']:
            if file != file.lower():
                if file.lower() in [f.lower() for f in build_data['artifacts']['wheel']]:
                    raise ValueError(
                        f"Case mismatch: {file} conflicts with lowercase version. "
                        f"Use lowercase package names for portability."
                    )
```

### macOS Specific: Case-Sensitive Volume

Developers can create case-sensitive APFS volumes:

```bash
# Create case-sensitive volume (development only)
diskutil apfs createVolume disk0s2 APFS DevelopmentVolume -caseinsensitive no
```

This catches case-sensitivity issues during development before release.

## Best Practices

### Naming Conventions

1. **Package names**: Always lowercase

   ```toml
   name = "mypackage"  # Not "MyPackage"
   ```

2. **Module names**: Lowercase with underscores

   ```python
   # mypackage/my_module.py
   import mypackage.my_module
   ```

3. **Directory names**: Lowercase matching import path
   <eg>
   src/mypackage/my_subpackage/
</eg>

### Testing Across Platforms

- Develop on Linux if possible (reveals case-sensitivity issues)
- Use CI/CD to test on macOS and Windows
- Run tests in case-sensitive Docker containers
- Use pre-commit hooks to catch case issues

### Package Configuration

```toml
[project]
name = "mypackage"

[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]

# Never use mixed case
# [tool.hatchling.targets.wheel]
# packages = ["src/MyPackage"]  # ❌ Wrong
```

### Documentation

````markdown
## Installation

```bash
pip install mypackage  # Lowercase as distributed
```

## Usage

```python
import mypackage  # Lowercase for imports
```
````

## Troubleshooting

### "No module named 'MyPackage'" on Linux

**Issue**: Works on macOS/Windows, fails on Linux

**Cause**: Uppercase in import but lowercase distribution

**Solution**: Use lowercase consistently:

```python
import mypackage  # Change from 'MyPackage'
```

### Package Discovery Fails

**Issue**: `hatch build` reports package not found

**Solution**: Verify directory name matches configured package path:

```bash
ls -la src/mypackage/__init__.py  # Must exist

# In pyproject.toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]  # Must match directory exactly (case-sensitive)
```

### Entry Points Not Working

**Issue**: Console scripts fail with import error

**Solution**: Ensure entry point target uses correct case:

```toml
[project.scripts]
mycli = "mypackage.cli:main"  # Lowercase package name
```

### Namespace Package Import Fails

**Issue**: Cannot import nested namespace

**Solution**: Verify all directory levels in namespace have proper `__init__.py`:

<eg>
src/
├── mycompany/           # Must have __init__.py
│   ├── __init__.py
│   └── core/            # Must have __init__.py
│       ├── __init__.py
│       └── service.py
</eg>

## See Also

- `path-rewriting.md` - Package path configuration
- `distributed-artifacts.md` - Understanding artifact naming
- `build-context.md` - Platform detection in hooks
