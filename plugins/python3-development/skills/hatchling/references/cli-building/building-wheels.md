---
category: cli-building
topics: [wheels, binary-distribution, package-distribution, hatchling]
related: [index.md, overview.md, building-sdist.md, building-all-targets.md, output-customization.md]
---

# Building Wheels with Hatchling

## Overview

Wheels are the standard binary distribution format for Python packages, enabling faster installation without requiring a build step. Reference this when helping users configure wheel building, manage file selection, handle platform-specific wheels, and optimize wheel metadata.

## Command-Line Usage

### Using Hatch

```bash
# Build wheel with default settings
hatch build -t wheel

# Build wheel with verbose output
hatch -v build -t wheel:standard

# Build specific wheel version
hatch build -t wheel:standard
```

### Using Python's Build Module

```bash
# Build only wheel
python -m build --wheel

# Build wheel with custom output directory
python -m build --wheel --outdir dist/

# Build with specific backend settings
python -m build --wheel --config-settings=--build-option=value
```

## Wheel Configuration

Configure wheel building in `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
# Include specific packages
packages = ["src/mypackage"]

# Exclude files
exclude = [
  "*.pyc",
  "__pycache__",
]

# Include files
include = [
  "src/**/*.py",
  "README.md",
]

# Use only these files (overrides include)
only-include = ["src/mypackage"]

# Force include files from anywhere
[tool.hatch.build.targets.wheel.force-include]
"../artifacts" = "mypackage/data"
"~/configs/prod.yaml" = "mypackage/config.yaml"
```

## Wheel Options

```toml
[tool.hatch.build.targets.wheel]
# Core metadata version
core-metadata-version = "2.4"

# Strict naming (normalized package names)
strict-naming = true

# macOS compatibility
macos-max-compat = false

# Bypass file selection errors
bypass-selection = false

# Shared data and scripts
[tool.hatch.build.targets.wheel.shared-data]
"data" = "share/mypackage"

[tool.hatch.build.targets.wheel.shared-scripts]
"scripts" = "bin"

# Extra metadata
[tool.hatch.build.targets.wheel.extra-metadata]
"License" = "LICENSE.txt"
```

## Wheel Versions

Hatchling supports different wheel versions:

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "editable"]
```

- **standard**: Regular wheel for distribution
- **editable**: Development wheel with `.pth` files for editable installs

## Build Data

Build hooks can modify wheel metadata:

```toml
# Wheel tag configuration
[tool.hatch.build.targets.wheel]
# Full tag (e.g., py3-none-any)
tag = "py3-none-any"

# Or infer tag from platform
infer-tag = false

# Pure Python wheel
pure-python = true
```

## Path Rewriting with Sources

Remap source paths to different locations in the wheel:

```toml
[tool.hatch.build.targets.wheel.sources]
# Remove src/ prefix
"src" = ""

# Add prefix
"" = "lib"

# Rename directory
"src/old_name" = "new_name"
```

## Output Structure

A typical wheel contains:

<eg>
my_package-0.1.0-py3-none-any.whl
├── mypackage/
│   ├── __init__.py
│   └── main.py
├── mypackage-0.1.0.dist-info/
│   ├── METADATA
│   ├── WHEEL
│   ├── RECORD
│   ├── LICENSE
│   └── entry_points.txt
└── mypackage.data/
    └── data/
        └── config.yaml
</eg>

## Wheel Naming Convention

Wheels follow the naming pattern:

<eg>
{package}-{version}(-{build})?-{python}-{abi}-{platform}.whl
</eg>

Example: `mypackage-1.0.0-py3-none-any.whl`

- **py3**: Python 3.x compatible
- **none**: No ABI requirement
- **any**: Platform independent

## Platform-Specific Wheels

For wheels with C extensions:

```toml
[tool.hatch.build.targets.wheel]
# Let hatchling infer the platform tag
infer-tag = true

# Or specify explicitly
tag = "cp39-cp39-linux_x86_64"
```

## Development/Editable Wheels

For development installations:

```bash
# Build editable wheel
hatch build -t wheel:editable

# Install in editable mode
pip install -e .
```

Configuration for editable wheels:

```toml
[tool.hatch.build.targets.wheel.force-include-editable]
"src/mypackage" = "mypackage"
```

## Best Practices

1. **Use strict-naming**: Ensures consistent package names on PyPI
2. **Include licenses**: Always include license files in wheels
3. **Exclude unnecessary files**: Don't include tests, docs, or build artifacts
4. **Use sources for clean structure**: Remove unnecessary path prefixes
5. **Test wheels**: Always test installation from built wheels before publishing

## Troubleshooting

### No Files Selected Error

If you get an error about no files being selected:

```toml
[tool.hatch.build.targets.wheel]
# Explicitly define what to include
packages = ["src/mypackage"]

# Or use bypass-selection (not recommended)
bypass-selection = true
```

### Path Not Found Error

For force-include paths:

```toml
[tool.hatch.build.targets.wheel.force-include]
# Use absolute paths or paths relative to project root
"./data" = "mypackage/data"  # Relative to project root
```

## See Also

- [Wheel Specification (PEP 427)](https://www.python.org/dev/peps/pep-0427/)
- `building-sdist.md`
- `output-customization.md`
