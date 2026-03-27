---
category: cli-building
topics: [command-line, quick-start, build-basics, hatchling]
related: [index.md, building-wheels.md, building-sdist.md, python-build-tool.md]
---

# Command-Line Building with Hatchling

## Overview

Hatchling is the modern build backend for Hatch, enabling standards-compliant Python package building through simple command-line interfaces. Reference this when helping users understand basic build commands, build targets (sdist and wheel), and project configuration in pyproject.toml.

## Quick Start

### Basic Build Commands

```bash
# Build all targets (both sdist and wheel)
hatch build

# Build only wheel
hatch build -t wheel

# Build only sdist
hatch build -t sdist

# Build with verbose output
hatch -v build -t wheel:standard
```

### Using Python's Build Module

```bash
# Install build module
pip install build

# Build using python -m build (builds both sdist and wheel)
python -m build

# Build only wheel
python -m build --wheel

# Build only sdist
python -m build --sdist

# Specify output directory
python -m build --outdir dist/
```

## Configuration

All build configuration is done in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
```

## Build Targets

Hatchling supports multiple build targets:

- **sdist**: Source distribution
- **wheel**: Binary distribution (wheel)
- **binary**: Standalone binary (using PyApp)

Each target can have its own configuration and versions.

## Output

By default, build artifacts are placed in the `dist/` directory:

<eg>
dist/
├── my_package-0.1.0-py3-none-any.whl
└── my_package-0.1.0.tar.gz
</eg>

## See Also

- `building-wheels.md`
- `building-sdist.md`
- `output-customization.md`
- `python-build-tool.md`
- `local-install.md`
