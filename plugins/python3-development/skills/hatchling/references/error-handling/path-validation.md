---
category: Error Handling
topics: [path-validation, force-include, symlinks, uri-formatting, reproducible-builds]
related: [./wheel-file-selection.md, ./build-validation.md, ./version-validation.md]
---

# Path Validation Error Handling in Hatchling

## Overview

When assisting users with Hatchling builds, reference this guide to help them understand and resolve path validation errors. Hatchling performs strict path validation to ensure build reproducibility and prevent common packaging errors. This document covers path validation mechanisms, error scenarios, and resolution strategies.

## Force-Include Path Validation

### Error: Non-existent Force-Included Path (v1.19.0+)

**Error Message:**

<eg>
An error will now be raised if a force-included path does not exist
</eg>

**Trigger Conditions:**

- Path specified in `force-include` configuration doesn't exist
- Path was renamed/moved but configuration wasn't updated
- Path is generated during build but force-include runs before generation

**Example Configuration:**

```toml
[tool.hatch.build]
force-include = [
    "src/generated/schema.py",  # Must exist at build time
    "docs/api.html"             # Will error if missing
]
```

**Resolution Strategies:**

1. **Verify Path Existence:**

   ```python
   # Check before build
   import pathlib

   force_includes = [
       "src/generated/schema.py",
       "docs/api.html"
   ]

   for path in force_includes:
       if not pathlib.Path(path).exists():
           print(f"Missing: {path}")
   ```

2. **Use Build Hooks for Generated Files:**

   ```toml
   [tool.hatch.build.hooks.custom]
   # Generate files before force-include validation
   ```

3. **Conditional Inclusion:**
   ```toml
   # Use patterns that match existing files
   [tool.hatch.build]
   include = [
       "src/**/*.py",
       "docs/*.html"  # Won't error if no matches
   ]
   ```

## Path Normalization and Case Sensitivity

### Error: Case-Insensitive Filesystem Issues

**Error Scenario:**

<eg>
Fix the wheel build target for case insensitive file systems when the
project metadata name does not match the directory name on disk
</eg>

**Example Problem:**

<eg>
Project name: my-package
Directory:    My_Package/
Filesystem:   macOS (case-insensitive)
</eg>

**Resolution:**

```toml
[project]
name = "my-package"  # PyPI name

[tool.hatch.build.targets.wheel]
packages = ["my_package"]  # Actual directory name
```

## Source Path Remapping

### Using Sources Option with Empty String

**Feature (v1.19.0+):**

```toml
[tool.hatch.build]
sources = {"" = "prefix/"}  # Add prefix to all paths
```

**Use Cases:**

1. **Namespace Packages:**

   ```toml
   sources = {"src" = "company/project"}
   # src/module.py → company/project/module.py
   ```

2. **Distribution Path Prefixes:**
   ```toml
   sources = {"" = "vendor/"}
   # All files get vendor/ prefix
   ```

## Path Validation in Dev Mode

### Error: Symlink Resolution Issues

**Fixed in v1.17.1:**

<eg>
Fix dev mode when the project has symlinks and file inclusion is
defined with the packages or only-include options
</eg>

**Best Practices:**

1. Use absolute paths for symlink targets
2. Ensure symlinks resolve within project boundary
3. Test dev mode installation with symlinks:
   ```bash
   pip install -e .
   python -c "import mypackage; print(mypackage.__file__)"
   ```

## URI Context Formatting

### Error: Unescaped Spaces in URIs

**Fixed in v1.19.0:**

<eg>
Properly escape spaces for URI context formatting
</eg>

**Problem Example:**

```toml
[project.urls]
"Bug Reports" = "file:///path with spaces/file.html"  # Error
```

**Correct Format:**

```toml
[project.urls]
"Bug Reports" = "file:///path%20with%20spaces/file.html"
```

## Path Validation Best Practices

### 1. Pre-Build Validation Script

```python
#!/usr/bin/env python3
"""Validate build paths before running hatch build."""

import sys
from pathlib import Path
import tomllib

def validate_paths():
    """Check all configured paths exist."""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    errors = []

    # Check force-include paths
    build_config = config.get("tool", {}).get("hatch", {}).get("build", {})
    force_includes = build_config.get("force-include", [])

    for path in force_includes:
        if not Path(path).exists():
            errors.append(f"force-include: {path} does not exist")

    # Check packages
    wheel_config = build_config.get("targets", {}).get("wheel", {})
    packages = wheel_config.get("packages", [])

    for package in packages:
        if not Path(package).is_dir():
            errors.append(f"package directory: {package} does not exist")

    if errors:
        print("Path validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("All paths valid ✓")

if __name__ == "__main__":
    validate_paths()
```

### 2. Directory Structure Validation

```toml
# pyproject.toml
[tool.hatch.build]
# Validate expected structure
reproducible = true
sources = {"src" = ""}  # Map src/ to package root

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]  # Must match actual directory

[tool.hatch.build.targets.wheel.force-include]
# Only include files that are guaranteed to exist
"LICENSE" = "LICENSE"
"README.md" = "README.md"
```

### 3. Build Hook for Path Validation

```python
# hatch_build.py
import os
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class PathValidationHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Validate paths before build starts."""
        required_paths = [
            "src",
            "LICENSE",
            "README.md",
        ]

        for path_str in required_paths:
            path = Path(path_str)
            if not path.exists():
                raise FileNotFoundError(
                    f"Required path missing: {path_str}"
                )

        # Validate no broken symlinks
        for root, dirs, files in os.walk("src"):
            for name in files + dirs:
                path = Path(root) / name
                if path.is_symlink() and not path.exists():
                    raise FileNotFoundError(
                        f"Broken symlink: {path}"
                    )
```

## Common Path Validation Errors and Solutions

| Error                                                | Cause                            | Solution                                  |
| ---------------------------------------------------- | -------------------------------- | ----------------------------------------- |
| `force-included path does not exist`                 | Missing file in force-include    | Ensure file exists or remove from config  |
| `At least one file selection option must be defined` | No files selected for wheel      | Define packages, include, or only-include |
| `Cannot find package directory`                      | Wrong package name/path          | Match actual directory structure          |
| `Symlink resolution failed`                          | Broken or external symlinks      | Fix symlinks or use regular files         |
| `Path contains invalid characters`                   | Special chars in filenames       | Rename files to use safe characters       |
| `Path outside project root`                          | Absolute paths or ../ references | Use relative paths within project         |

## Version History

- **v1.19.0**: Added force-include path validation
- **v1.17.1**: Fixed symlink handling in dev mode
- **v1.19.0**: Fixed URI space escaping
- **v1.11.1**: Fixed wheel path normalization

## Related Documentation

- `wheel-file-selection.md`
- `build-validation.md`
- `version-validation.md`
