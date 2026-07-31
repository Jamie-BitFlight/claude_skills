---
category: project-structure
topics: [single module, auto-detection, simple packages, CLI tools]
related: [single-module-layout.md, src-layout-structure.md]
---

# Single Module Layout Auto-detection in Hatchling

## Overview

Hatchling can automatically detect and properly package projects that consist of a single Python module file rather than a full package directory. When assisting users with simple tools and scripts, reference this feature to simplify their packaging process.

## Auto-detection Behavior

### What Hatchling Detects

Starting with version 1.4.0, Hatchling automatically detects single module layouts when:

1. There's a single `.py` file at the root or in `src/`
2. The module name matches or relates to the project name
3. No package directory exists with an `__init__.py`

### Examples of Auto-detected Layouts

**Root level single module:**

<eg>
myproject/
├── mymodule.py
└── pyproject.toml
</eg>

**Src-layout single module:**

<eg>
myproject/
├── src/
│   └── mymodule.py
└── pyproject.toml
</eg>

## Basic Configuration

### Minimal Configuration (Auto-detection)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mymodule"
version = "1.0.0"

# That's it! Hatchling auto-detects mymodule.py
```

### Explicit Configuration

```toml
[tool.hatch.build.targets.wheel]
packages = ["."]  # or ["src"] for src-layout
include = ["mymodule.py"]
```

## Single Module Patterns

### Simple Script

```python
# mytool.py
"""A simple command-line tool."""


def main():
    print("Hello from mytool!")


if __name__ == "__main__":
    main()
```

```toml
[project]
name = "mytool"
version = "1.0.0"

[project.scripts]
mytool = "mytool:main"
```

### Module with Functions

```python
# utils.py
"""Utility functions module."""


def calculate(x, y):
    return x + y


def process(data):
    return data.upper()


class Helper:
    def __init__(self):
        self.ready = True
```

```toml
[project]
name = "utils"
version = "1.0.0"
description = "Utility functions"
```

## Import Names

### Matching Project Name

When the module name matches the project name:

```toml
[project]
name = "calculator"  # Package name on PyPI

# File: calculator.py
```

After installation:

```python
import calculator

result = calculator.add(1, 2)
```

### Different Names

When module name differs from project name:

```toml
[project]
name = "my-awesome-tool"  # Package name on PyPI

# File: awesome.py
```

After installation:

```python
import awesome  # Import uses module filename
```

## Advanced Single Module Configurations

### With Additional Resources

<eg>
project/
├── src/
│   └── mytool.py
├── data/
│   └── config.json
├── templates/
│   └── default.html
└── pyproject.toml
</eg>

```toml
[project]
name = "mytool"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
packages = ["src"]
include = ["src/mytool.py"]
artifacts = [
    "data/*.json",
    "templates/*.html"
]

[tool.hatch.build.targets.wheel.force-include]
"data" = "mytool/data"
"templates" = "mytool/templates"
```

### With Type Stubs

<eg>
project/
├── mymodule.py
├── mymodule.pyi  # Type stub file
├── py.typed      # PEP 561 marker
└── pyproject.toml
</eg>

```toml
[tool.hatch.build.targets.wheel]
include = [
    "mymodule.py",
    "mymodule.pyi",
    "py.typed"
]
```

### Multiple Single Modules

<eg>
project/
├── module1.py
├── module2.py
├── helper.py
└── pyproject.toml
</eg>

```toml
[project]
name = "my-tools"

[tool.hatch.build.targets.wheel]
include = [
    "module1.py",
    "module2.py",
    "helper.py"
]
```

After installation:

```python
import module1
import module2
import helper
```

## Console Scripts

### Single Entry Point

```python
# cli.py
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    args = parser.parse_args()
    print(f"Hello, {args.name}!")


if __name__ == "__main__":
    main()
```

```toml
[project]
name = "greeter"
version = "1.0.0"

[project.scripts]
greet = "cli:main"
```

### Multiple Entry Points

```python
# tools.py
def encrypt():
    print("Encrypting...")


def decrypt():
    print("Decrypting...")


def hash_file():
    print("Hashing...")
```

```toml
[project.scripts]
encrypt = "tools:encrypt"
decrypt = "tools:decrypt"
hash = "tools:hash_file"
```

## Version Management

### Version in Module

```python
# mymodule.py
__version__ = "1.0.0"


def get_version():
    return __version__
```

```toml
[project]
name = "mymodule"
dynamic = ["version"]

[tool.hatch.version]
path = "mymodule.py"
```

### Version from Environment

```python
# tool.py
import os

__version__ = os.environ.get("TOOL_VERSION", "dev")
```

```toml
[project]
name = "tool"
dynamic = ["version"]

[tool.hatch.version]
source = "env"
variable = "TOOL_VERSION"
```

## Testing Single Modules

### Test Structure

<eg>
project/
├── src/
│   └── calculator.py
├── tests/
│   └── test_calculator.py
└── pyproject.toml
</eg>

```python
# tests/test_calculator.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import calculator


def test_add():
    assert calculator.add(2, 2) == 4
```

### With pytest

```toml
[tool.hatch.envs.default]
dependencies = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]  # or ["."] for root-level modules
```

## Edge Cases

### Module Name Conflicts

When module name conflicts with standard library:

```python
# json.py (conflicts with stdlib json)
def parse():
    return {"custom": "parser"}
```

Better naming:

```python
# myjson.py or json_tools.py
def parse():
    return {"custom": "parser"}
```

### Unicode Module Names

```python
# café.py (with non-ASCII character)
def brew():
    return "☕"
```

Note: While Python supports Unicode identifiers, it's better to use ASCII for module names for compatibility.

## Migration from Package to Single Module

### Before (Package Structure)

<eg>
mypackage/
├── mypackage/
│   ├── __init__.py
│   └── core.py
└── pyproject.toml
</eg>

### After (Single Module)

<eg>
mypackage/
├── mypackage.py  # Consolidated module
└── pyproject.toml
</eg>

Consolidate code:

```python
# mypackage.py
"""All functionality in one module."""

# Previous __init__.py content
__version__ = "1.0.0"


# Previous core.py content
def main_function():
    pass


class MainClass:
    pass
```

## Build Output

### What Gets Built

For a single module project:

<eg>
mymodule.py
pyproject.toml
</eg>

The wheel contains:

<eg>
mymodule.py
mymodule-1.0.0.dist-info/
├── METADATA
├── WHEEL
├── top_level.txt
└── RECORD
</eg>

### Installation Result

After `pip install mymodule-1.0.0.whl`:

<eg>
site-packages/
├── mymodule.py
└── mymodule-1.0.0.dist-info/
    └── ...
</eg>

## Best Practices

When recommending single module layouts to users, reference these best practices:

1. **Use for simple tools**: Guide users that single modules are perfect for simple utilities
2. **Consider growth**: Advise users that if they might need multiple modules, they should start with a package
3. **Clear naming**: Recommend users choose descriptive and unique module names
4. **Include type hints**: Encourage users to include type annotations even in single modules
5. **Add docstrings**: Remind users to document their module's purpose and functions

## Common Patterns

### CLI Tool Pattern

```python
#!/usr/bin/env python
"""Command-line tool description."""

import argparse
import sys

__version__ = "1.0.0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    # Add more arguments
    args = parser.parse_args()
    # Process arguments
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Library Pattern

```python
"""Library module description."""

__version__ = "1.0.0"
__all__ = ["function1", "function2", "Class1"]


def function1(param):
    """Function description."""
    pass


def function2(param):
    """Function description."""
    pass


class Class1:
    """Class description."""

    pass


# Private helper
def _internal_function():
    pass
```

## Troubleshooting

### Module Not Found After Installation

**Issue:** Users' module can't be imported after installation

**Solutions:** Help users debug by:

1. Checking the module is included in wheel:
   ```bash
   unzip -l dist/*.whl
   ```
2. Verifying module name matches import name
3. Ensuring no naming conflicts with installed packages

### Auto-detection Not Working

**Issue:** Hatchling doesn't auto-detect single module

**Solution:** Guide users to use explicit configuration:

```toml
[tool.hatch.build.targets.wheel]
packages = ["."]  # or ["src"]
include = ["mymodule.py"]
```

## Complete Example

**Project structure:**

<eg>
math-tools/
├── src/
│   └── mathtools.py
├── tests/
│   └── test_mathtools.py
├── README.md
└── pyproject.toml
</eg>

**mathtools.py:**

```python
"""Mathematical utility functions."""

__version__ = "2.0.0"


def factorial(n):
    """Calculate factorial of n."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n):
    """Generate fibonacci sequence."""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


class Calculator:
    """Simple calculator class."""

    @staticmethod
    def add(x, y):
        return x + y

    @staticmethod
    def multiply(x, y):
        return x * y
```

**pyproject.toml:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "math-tools"
dynamic = ["version"]
description = "Mathematical utility functions"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]
keywords = ["math", "tools", "utilities"]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]

[project.optional-dependencies]
test = ["pytest>=7.0"]

[tool.hatch.version]
path = "src/mathtools.py"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

## References

- [Hatch Build - Single Module Support](https://hatch.pypa.io/latest/config/build/)
- [Python Packaging - Single Module](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Hatchling v1.4.0 Release Notes](https://github.com/pypa/hatch/releases/tag/hatchling-v1.4.0)
