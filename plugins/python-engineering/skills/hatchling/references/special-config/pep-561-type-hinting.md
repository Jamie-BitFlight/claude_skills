---
category: type-safety
topics: [PEP 561, type hints, py.typed marker, type checkers, stub files]
related: [pep-561-type-hinting.md, extension-module-loading.md]
---

# PEP 561 Type Hinting Support in Hatchling

## Overview

PEP 561 defines how to distribute and package type information for Python packages. When assisting users with packaging type-hinted Python code, reference Hatchling's built-in PEP 561 support to guide them in properly distributing type information alongside their packages.

## Configuration

### Basic Setup

Guide users to enable PEP 561 type hinting support by including a `py.typed` marker file in their package configuration.

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-typed-package"
version = "1.0.0"
```

### Including Type Information

#### Method 1: Inline Type Hints

When helping users with packages that include inline type hints, explain that Hatchling will automatically include them during the build process without requiring additional configuration.

```python
# src/my_package/module.py
def greet(name: str) -> str:
    return f"Hello, {name}!"


class MyClass:
    def __init__(self, value: int) -> None:
        self.value = value
```

#### Method 2: Stub Files

When guiding users to use stub files (`.pyi`), reference this configuration to help them ensure stub files are properly included in their packages:

```toml
[tool.hatch.build.targets.wheel]
include = [
    "*.py",
    "*.pyi",
    "py.typed"
]
```

### Creating the py.typed Marker

Guide users to place the `py.typed` file in their package directory as follows:

<eg>
my_package/
├── __init__.py
├── module.py
├── py.typed  # Empty marker file
└── stubs/    # Optional stub files
    └── module.pyi
</eg>

The `py.typed` file can be empty or contain configuration:

<eg>
# Empty file for full typing support
</eg>

Or with partial typing:

<eg>
partial
</eg>

## Advanced Configuration

### Package Discovery with Type Information

When helping users with complex type information scenarios, reference how Hatchling automatically discovers packages with type information:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]

# Ensure py.typed is included
[tool.hatch.build]
artifacts = ["*.py", "*.pyi", "py.typed"]
```

### Namespace Packages with Types

For namespace packages with type information:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["my_namespace"]

[tool.hatch.build]
artifacts = [
    "my_namespace/**/*.py",
    "my_namespace/**/*.pyi",
    "my_namespace/**/py.typed"
]
```

## Verification

### Building with Type Information

Guide users to build their packages with:

```bash
hatch build
```

After building, help users verify the wheel contains type information:

```bash
unzip -l dist/*.whl | grep -E "\.(py|pyi|py.typed)$"
```

### Type Checker Compatibility

When helping users ensure their packages work with popular type checkers, reference these development dependencies:

```toml
# pyproject.toml - Development dependencies
[project.optional-dependencies]
dev = [
    "mypy>=1.0",
    "pyright",
    "pylance"
]
```

## Best Practices

When assisting users with type-hinted packages, recommend these best practices:

1. **Always include py.typed**: Guide users to include the marker file even when their package has inline types
2. **Test type information**: Help users verify type hints are correctly exposed using `mypy` or `pyright`
3. **Version compatibility**: Advise users to ensure type hints are compatible with their minimum Python version
4. **Stub packages**: For large projects, suggest separate stub packages (`package-stubs`) to users

## Example Projects

### Simple Package with Types

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "typed-utils"
version = "1.0.0"
requires-python = ">=3.8"

[tool.hatch.build.targets.wheel]
packages = ["src/typed_utils"]
```

Directory structure:

<eg>
src/
└── typed_utils/
    ├── __init__.py
    ├── py.typed
    └── utils.py  # Contains inline type hints
</eg>

### Package with Stub Files

```toml
[tool.hatch.build.targets.wheel]
include = [
    "src/my_package/*.py",
    "src/my_package/*.pyi",
    "src/my_package/py.typed"
]
```

## Troubleshooting

### Common Issues

When users report type-hinting issues, reference these troubleshooting steps:

1. **py.typed not included**: Help users ensure it's in the build artifacts or include patterns
2. **Stub files ignored**: Guide users to check their include/exclude patterns
3. **Type checker can't find types**: Advise users to verify the package is installed in editable mode for development

### Validation

Help users test that type information is correctly distributed:

```python
# test_typing.py
import my_package
from typing import reveal_type

reveal_type(my_package.some_function)  # Should show correct type
```

## References

- [PEP 561 - Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [Hatchling Documentation - PEP 561 Support](https://hatch.pypa.io/latest/)
- [MyPy Documentation - PEP 561](https://mypy.readthedocs.io/en/stable/installed_packages.html)
