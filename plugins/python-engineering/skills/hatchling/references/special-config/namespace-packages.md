---
category: package-patterns
topics: [namespace packages, PEP 420, package organization, multi-distribution]
related: [namespace-packages.md, package-name-normalization.md, src-layout-structure.md]
---

# Namespace Packages in Hatchling

## Overview

Namespace packages allow multiple separate distributions to contribute modules to a single parent package. When assisting users with organizing code across multiple distributions, reference Hatchling's comprehensive support for both PEP 420 (native) and legacy namespace packages.

## Types of Namespace Packages

### PEP 420 - Native Namespace Packages (Recommended)

No `__init__.py` file in the namespace directory:

<eg>
mycompany/             # No __init__.py here
├── package_a/
│   └── __init__.py
└── package_b/
    └── __init__.py
</eg>

### Legacy Namespace Packages

Using `pkgutil-style` or `setuptools-style` with `__init__.py`:

```python
# mycompany/__init__.py
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
```

## Configuration

### Basic Namespace Package

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mycompany-subpackage"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
packages = ["src/mycompany"]
```

### Using only-include

For more control over what's included:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["mycompany/subpackage"]
```

### Directory Structure Examples

#### Standard Namespace Layout

<eg>
project-root/
├── pyproject.toml
├── src/
│   └── mycompany/          # Namespace (no __init__.py)
│       └── subpackage/      # Your package
│           ├── __init__.py
│           └── module.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mycompany"]
```

#### Flat Namespace Layout

<eg>
project-root/
├── pyproject.toml
└── mycompany/              # Namespace (no __init__.py)
    └── subpackage/         # Your package
        ├── __init__.py
        └── module.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
only-include = ["mycompany"]
```

## Multiple Namespace Packages

### Publishing Multiple Sub-packages

Each sub-package gets its own distribution:

**Package A: mycompany-auth**

```toml
[project]
name = "mycompany-auth"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
only-include = ["mycompany/auth"]
```

**Package B: mycompany-utils**

```toml
[project]
name = "mycompany-utils"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
only-include = ["mycompany/utils"]
```

After installing both:

```python
import mycompany.auth  # From mycompany-auth
import mycompany.utils  # From mycompany-utils
```

## Complex Namespace Scenarios

### Nested Namespaces

<eg>
src/
└── company/                # First namespace level
    └── products/           # Second namespace level
        └── webapp/         # Actual package
            ├── __init__.py
            └── app.py
</eg>

```toml
[project]
name = "company-products-webapp"

[tool.hatch.build.targets.wheel]
packages = ["src/company"]
```

### Mixed Regular and Namespace Packages

<eg>
src/
├── mycompany/              # Namespace (no __init__.py)
│   └── shared/             # Sub-package
│       └── __init__.py
└── myapp/                  # Regular package
    └── __init__.py
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mycompany", "src/myapp"]
```

## Sources Configuration for Namespaces

### Removing src/ Prefix

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mycompany"]
sources = ["src"]  # Removes 'src/' from the installed path
```

### Custom Path Mappings

```toml
[tool.hatch.build.targets.wheel.sources]
"src/mycompany" = "corporate"  # Install as 'corporate' instead
```

## Common Patterns

### Enterprise/Organization Packages

```toml
# For package: acme-roadrunner
[project]
name = "acme-roadrunner"

[tool.hatch.build.targets.wheel]
only-include = ["acme/roadrunner"]
```

### Plugin Systems

```toml
# For plugin: myapp-plugins-database
[project]
name = "myapp-plugins-database"

[tool.hatch.build.targets.wheel]
packages = ["myapp/plugins/database"]
sources = []  # Keep the full path
```

### Scientific/Data Packages

```toml
# For package: scikit-mylearn
[project]
name = "scikit-mylearn"

[tool.hatch.build.targets.wheel]
only-include = ["sklearn/mylearn"]
```

## Build Configuration Tips

### Artifacts and Namespace Packages

Include non-Python files in namespace packages:

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
    "mycompany/*/data/*.json",
    "mycompany/*/templates/*.html"
]
```

### Excluding Tests from Namespace

```toml
[tool.hatch.build.targets.wheel]
exclude = [
    "mycompany/*/tests",
    "mycompany/*/*_test.py"
]
```

## Development Setup

### Editable Installs

```bash
# Install in development mode
pip install -e .

# Or using Hatch
hatch develop
```

### Testing Multiple Namespace Packages

```toml
# hatch.toml for testing
[envs.test]
dependencies = [
    "mycompany-auth",
    "mycompany-utils",
    "mycompany-core"
]
```

## Migration Guide

### From setuptools

**Old (setuptools with find_namespace_packages):**

```python
# setup.py
from setuptools import setup, find_namespace_packages

setup(name="mycompany-subpackage", packages=find_namespace_packages(where="src"), package_dir={"": "src"})
```

**New (Hatchling):**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mycompany-subpackage"

[tool.hatch.build.targets.wheel]
packages = ["src/mycompany"]
```

### From Poetry

**Poetry doesn't have built-in namespace package support**

Workaround in Hatchling:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["namespace_pkg/subpkg"]
```

## Troubleshooting

### Common Issues

When users encounter namespace package issues, help them debug:

1. **ImportError after installation**

   - Guide users to ensure no `__init__.py` in namespace directories (for PEP 420)
   - Help users verify that all parts use the same namespace style

2. **Files not included**

   - Reference this configuration to help users with precise control:

   ```toml
   # Use only-include for precise control
   [tool.hatch.build.targets.wheel]
   only-include = ["mycompany/mypackage"]
   ```

3. **Namespace collision**
   - Inform users when different packages try to own the namespace `__init__.py`
   - Recommend users use PEP 420 (no `__init__.py`) as the solution

### Debugging

When helping users troubleshoot namespace packages, reference these commands:

```bash
# Check what's included in the wheel
hatch build
unzip -l dist/*.whl | grep mycompany/

# Verify namespace package structure
python -c "import mycompany; print(mycompany.__path__)"

# Should show multiple paths if multiple packages installed:
# _NamespacePath(['/path/to/site-packages/mycompany'])
```

### Validation

Help users validate namespace packages with this test:

```python
# test_namespace.py
import mycompany

assert hasattr(mycompany, "__path__")  # It's a namespace
assert not hasattr(mycompany, "__file__")  # No __init__.py

import mycompany.subpackage

assert hasattr(mycompany.subpackage, "__file__")  # Regular package
```

## Best Practices

When helping users design namespace package structures, recommend these best practices:

1. **Use PEP 420**: Guide users to prefer native namespace packages (no `__init__.py`)
2. **Consistent naming**: Advise users to use organization or project prefix consistently
3. **Clear boundaries**: Help users establish that each distribution owns specific sub-packages
4. **Document dependencies**: Encourage users to make clear which namespace packages work together
5. **Test imports**: Remind users to verify namespace packages work correctly after installation

## Example: Complete Namespace Package

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "acme-explosives"
version = "2.0.0"
description = "ACME Corporation Explosives Module"
authors = [{name = "Wile E. Coyote"}]
requires-python = ">=3.8"
dependencies = [
    "acme-common>=1.0",  # Another namespace package
]

[tool.hatch.build.targets.wheel]
# Include only our sub-package
only-include = ["acme/explosives"]

[tool.hatch.build.targets.sdist]
# Include tests in source distribution
include = [
    "acme/explosives",
    "tests"
]
```

Directory structure:

<eg>
acme-explosives/
├── pyproject.toml
├── acme/                  # No __init__.py (namespace)
│   └── explosives/        # Our package
│       ├── __init__.py
│       ├── dynamite.py
│       └── tnt.py
└── tests/
    └── test_explosives.py
</eg>

## References

- [PEP 420 - Implicit Namespace Packages](https://peps.python.org/pep-0420/)
- [Python Packaging Guide - Namespace Packages](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/)
- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
