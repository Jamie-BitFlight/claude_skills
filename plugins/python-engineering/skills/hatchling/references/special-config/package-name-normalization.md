---
category: package-configuration
topics: [package naming, PEP 503, PEP 508, normalization, strict-naming]
related: [package-name-normalization.md, namespace-packages.md]
---

# Package Name Normalization in Hatchling

## Overview

Hatchling handles package name normalization according to Python packaging standards (PEP 503, PEP 508). When assisting users with package naming and configuration, reference this guide to help them understand and control how names are displayed and stored.

## Normalization Rules

### Standard Normalization

Package names are normalized by:

1. Converting to lowercase
2. Replacing runs of `[-_.]` with a single hyphen `-`

<eg>
Examples:
My-Package      → my-package
my_package      → my-package
My.Package      → my-package
my__package     → my-package
My-.-Package    → my-package
</eg>

## Configuration Options

### strict-naming Option

Control whether normalization is applied to build artifacts:

```toml
[tool.hatch.build.targets.wheel]
strict-naming = false  # Keep original name in artifacts

[tool.hatch.build.targets.sdist]
strict-naming = false  # Keep original name in artifacts
```

### Effects of strict-naming

#### When `strict-naming = true` (default)

- Artifact names are normalized
- Distribution: `my_package-1.0.0-py3-none-any.whl`
- Metadata directory: `my_package-1.0.0.dist-info/`

#### When `strict-naming = false`

- Original project name is preserved
- Distribution: `My.Package-1.0.0-py3-none-any.whl`
- Metadata directory: `My.Package-1.0.0.dist-info/`

## Project Metadata

### Display Name Preservation

Starting with Hatchling 1.5.0, the project name in metadata is stored exactly as defined:

```toml
[project]
name = "My-Package"  # Preserved in metadata as "My-Package"
```

This affects how the package appears on PyPI:

- URL will be normalized: `pypi.org/project/my-package/`
- Display name will be preserved: "My-Package"

### Core Metadata

```toml
[project]
name = "My.Package"
```

Generates in PKG-INFO/METADATA:

<eg>
Name: My.Package
</eg>

But the distribution name is normalized:

<eg>
my-package-1.0.0.tar.gz
</eg>

## Import Names vs Package Names

### Automatic Detection

Hatchling automatically maps between package names and import names:

```toml
[project]
name = "my-awesome-package"  # PyPI name

# Directory structure
src/
└── my_awesome_package/   # Import name (underscores)
    └── __init__.py
```

### Explicit Mapping

For non-standard mappings:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]  # Different from project name
```

## Namespace Packages

### Name Normalization in Namespaces

```toml
[project]
name = "my-namespace.my-package"  # PyPI name

# Directory structure
src/
└── my_namespace/          # Import uses underscores
    └── my_package/
        └── __init__.py
```

### Configuration

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_namespace"]
```

## Edge Cases and Special Handling

### Case Sensitivity

#### Case-Insensitive Filesystems (Windows, macOS)

Hatchling handles case-insensitive filesystems correctly:

```toml
[project]
name = "MyPackage"

# Works even if directory is:
# mypackage/
# MyPackage/
# MYPACKAGE/
```

### Unicode and Special Characters

```toml
[project]
# Unicode is normalized to ASCII
name = "café-package"  # Becomes: cafe-package

# Special characters are replaced
name = "my@package"    # Invalid - will error
name = "my+package"    # Invalid - will error
```

### Leading/Trailing Characters

```toml
[project]
# Hyphens and underscores are handled
name = "-my-package-"   # Becomes: my-package
name = "_my_package_"   # Becomes: my-package
```

## Build Artifacts

### Wheel Naming

Standard wheel naming convention:

<eg>
{distribution}-{version}(-{build_tag})?-{python_tag}-{abi_tag}-{platform_tag}.whl
</eg>

With normalization:

```toml
[project]
name = "My.Package"
version = "1.0.0"

# Creates: my-package-1.0.0-py3-none-any.whl (strict-naming = true)
# Creates: My.Package-1.0.0-py3-none-any.whl (strict-naming = false)
```

### Source Distribution Naming

```toml
[project]
name = "My.Package"
version = "1.0.0"

# Creates: my-package-1.0.0.tar.gz (strict-naming = true)
# Creates: My.Package-1.0.0.tar.gz (strict-naming = false)
```

## Compatibility Considerations

### pip and Other Tools

All modern Python packaging tools handle normalized names:

```bash
# All of these work for the same package:
pip install my-package
pip install my_package
pip install My-Package
pip install MY.PACKAGE
```

### Import Statements

Import names must use underscores:

```python
# Package name: my-awesome-package
import my_awesome_package  # Correct
# import my-awesome-package  # SyntaxError
```

## Best Practices

### Naming Recommendations

When guiding users on package naming conventions, recommend these best practices:

1. **Use hyphens in package names**: Advise users to use `my-package-name` format
2. **Use underscores in module names**: Guide users to use `my_package_name/` directory structure
3. **Be consistent**: Encourage users to match package and module names when possible
4. **Avoid mixed case**: Suggest users prefer `mypackage` over `MyPackage`

### Configuration Examples

#### Standard Package

```toml
[project]
name = "awesome-utils"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
packages = ["src/awesome_utils"]
```

#### Preserving Display Name

```toml
[project]
name = "AwesomeUtils"  # Display name on PyPI
version = "1.0.0"

[tool.hatch.build.targets.wheel]
strict-naming = true  # Artifacts will be normalized
packages = ["src/awesomeutils"]
```

#### Legacy Compatibility

```toml
[project]
name = "My.Legacy.Package"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
strict-naming = false  # Keep dots in artifact names
```

## Troubleshooting

### Common Issues

When users encounter naming-related issues, help them debug with these steps:

1. **Import errors after installation**

   - Guide users to check that import name uses underscores
   - Help them verify package structure matches configuration

2. **Package not found on PyPI**

   - Remind users that PyPI URLs use normalized names
   - Explain that search is case-insensitive

3. **Duplicate packages**
   - Inform users that PyPI treats normalized names as the same package
   - Clarify they cannot upload `my-package` and `my_package` separately

### Debugging

When helping users troubleshoot naming issues, reference these commands:

```bash
# Check how name is normalized
python -c "from packaging.utils import canonicalize_name; print(canonicalize_name('My.Package'))"

# Verify built package names
hatch build
ls dist/

# Check metadata
unzip -p dist/*.whl '*/METADATA' | grep "^Name:"
```

## Migration Guide

### From setuptools

```python
# setup.py (old)
setup(
    name="My-Package"  # Sometimes inconsistent normalization
)
```

```toml
# pyproject.toml (new)
[project]
name = "My-Package"  # Consistent handling

[tool.hatch.build.targets.wheel]
strict-naming = false  # If you need exact compatibility
```

### From Poetry

```toml
# Poetry
[tool.poetry]
name = "my-package"
packages = [{include = "my_package"}]

# Hatchling
[project]
name = "my-package"

[tool.hatch.build.targets.wheel]
packages = ["my_package"]
```

## References

- [PEP 503 - Simple Repository API (Normalization Rules)](https://peps.python.org/pep-0503/#normalized-names)
- [PEP 508 - Dependency Specification](https://peps.python.org/pep-0508/)
- [Packaging User Guide - Package Name Normalization](https://packaging.python.org/en/latest/specifications/name-normalization/)
