---
name: Hatchling Wheel Builder
description: 'Configure wheel builds for binary distributions: file selection, platform-specific wheels, metadata control, and editable wheels'
---

# Wheel Builder

A wheel is a binary distribution format for Python packages that can be installed directly into an environment without requiring compilation. This is the standard format for Python package distribution.

## Configuration

The wheel builder is configured in the `pyproject.toml` file:

```toml
[tool.hatch.build.targets.wheel]
# Configuration options here
```

## Options

### Core Metadata

| Option                  | Default | Description                                                                                       |
| ----------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `core-metadata-version` | `"2.3"` | The version of [core metadata](https://packaging.python.org/specifications/core-metadata/) to use |
| `strict-naming`         | `true`  | Whether file names should contain the normalized version of the project name                      |
| `macos-max-compat`      | `true`  | Whether to signal broad macOS support in wheel names                                              |
| `bypass-selection`      | `false` | Whether to suppress errors when no file selection is defined                                      |

### Data and Scripts

| Option           | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `shared-data`    | Mapping for files to be installed globally in `sys.prefix`          |
| `shared-scripts` | Mapping for scripts to be installed in `Scripts` (Windows) or `bin` |
| `extra-metadata` | Additional metadata shipped in `extra_metadata` directory           |

### Example Configuration

```toml
[tool.hatch.build.targets.wheel]
core-metadata-version = "2.3"
strict-naming = true

# Include additional data files
shared-data = {
  "data/config.yaml" = "share/myapp/config.yaml"
}

# Include executable scripts
shared-scripts = {
  "scripts/runner.sh" = "runner"
}

# Additional metadata
extra-metadata = {
  "licenses/LICENSE.txt" = "LICENSE.txt"
}
```

## Versions

The wheel target supports multiple build versions:

| Version    | Description                                                   |
| ---------- | ------------------------------------------------------------- |
| `standard` | The default wheel format                                      |
| `editable` | Development wheel with `.pth` files for real-time development |

### Building Specific Versions

```bash
# Build standard wheel
hatch build -t wheel:standard

# Build editable wheel
hatch build -t wheel:editable
```

## File Selection

### Default Behavior

When no file selection is configured, the wheel builder will:

1. Look for packages matching the project name
2. Include Python modules in the project root
3. Include `py.typed` marker files

### Explicit Package Selection

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

# Only include packages, no additional files
only-packages = true
```

### Including/Excluding Files

```toml
[tool.hatch.build.targets.wheel]
include = [
  "src/**/*.py",
  "src/**/*.pyi",
  "src/**/py.typed",
]

exclude = [
  "**/__pycache__",
  "**/*.pyc",
  "tests/",
]
```

### Force Include

Force specific files into the wheel, even if they would normally be excluded:

```toml
[tool.hatch.build.targets.wheel]
force-include = {
  "LICENSE" = "LICENSE",
  "README.md" = "README.md",
  "data/config.yaml" = "mypackage/config.yaml"
}
```

## Build Data

Build hooks can modify the following wheel-specific build data:

- `tag` - The full tag part of the filename (e.g., `py3-none-any`)
- `infer_tag` - Use platform-specific tag when `tag` is not set
- `pure_python` - Whether the package contains platform-specific files (default: `true`)
- `dependencies` - Extra project dependencies
- `shared_data` - Additional shared-data entries
- `shared_scripts` - Additional shared-scripts entries
- `extra_metadata` - Additional extra-metadata entries
- `force_include_editable` - Force inclusion for editable version

## Platform-Specific Wheels

### Pure Python Wheels

Default configuration for pure Python packages:

```toml
[tool.hatch.build.targets.wheel]
# This is the default - no C extensions
pure-python = true
```

### Platform-Specific Wheels

For packages with compiled extensions:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
# Custom hook to handle compilation

[tool.hatch.build.targets.wheel]
# Build hook will set this based on compiled extensions
pure-python = false
```

## Common Patterns

### Library Package

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mylib"]
include = [
  "src/mylib/**/*.py",
  "src/mylib/py.typed",
]
```

### Application with Data Files

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myapp"]

shared-data = {
  "data/templates" = "share/myapp/templates",
  "data/config" = "share/myapp/config",
}

shared-scripts = {
  "scripts/myapp-cli" = "myapp"
}
```

### Namespace Package

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/namespace/mypackage"]
include = [
  "src/namespace/**/*.py",
]
# Don't include __init__.py for namespace packages
exclude = [
  "src/namespace/__init__.py"
]
```

## Quick Decision Guide

**Use wheel builder when:**

- Distributing a pure Python package (no C extensions)
- Creating an editable install for development (editable version)
- Packaging an application or library for PyPI

**Don't use wheel builder alone:**

- If you need to distribute source code → also use `sdist`
- If you need a standalone executable → use `binary` builder

## Troubleshooting

### Error: Cannot determine what to ship

This occurs when the wheel builder cannot determine which files to include. Solutions:

1. Explicitly define packages:

   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src/mypackage"]
   ```

2. Use `only-include` for specific files:

   ```toml
   [tool.hatch.build.targets.wheel]
   only-include = ["src/mypackage"]
   ```

3. Enable `bypass-selection` (not recommended):
   ```toml
   [tool.hatch.build.targets.wheel]
   bypass-selection = true
   ```

### Platform Tag Issues

For platform-specific wheels, ensure build hooks properly set the tag:

```python
# In your build hook
def initialize(self, version, build_data):
    build_data["tag"] = "cp39-cp39-linux_x86_64"
    # Or let it be inferred
    build_data["infer_tag"] = True
```

## See Also

- [Wheel Specification (PEP 427)](https://www.python.org/dev/peps/pep-0427/)
- [Binary Distribution Format](https://packaging.python.org/specifications/binary-distribution-format/)
- [Core Metadata Specifications](https://packaging.python.org/specifications/core-metadata/)
