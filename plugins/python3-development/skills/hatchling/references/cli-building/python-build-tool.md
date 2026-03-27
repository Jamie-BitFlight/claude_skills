---
category: cli-building
topics: [python-build, build-tool, build-isolation, pep-517]
related: [index.md, overview.md, building-wheels.md, building-sdist.md, building-all-targets.md]
---

# Building with Python's Build Tool

## Overview

The `build` module is Python's official standards-compliant build tool, providing a simple interface for building packages from any PEP 517-compatible backend including Hatchling. Reference this when helping users understand build isolation, configuration options, CI/CD integration, and the comparison with direct hatch build commands.

## Installation

```bash
# Install the build module
pip install build

# Or with pipx for isolated installation
pipx install build

# Verify installation
python -m build --version
```

## Basic Usage

### Build All Formats

```bash
# Build both sdist and wheel (default)
python -m build

# Equivalent to
python -m build --sdist --wheel
```

### Build Specific Formats

```bash
# Build only source distribution
python -m build --sdist

# Build only wheel
python -m build --wheel

# Build from a specific directory
python -m build /path/to/project
```

## Command-Line Options

### Output Directory

```bash
# Specify output directory (default: dist/)
python -m build --outdir build/
python -m build -o custom_dist/

# Build in a specific directory
python -m build --wheel --outdir wheels/
python -m build --sdist --outdir source/
```

### Build Isolation

```bash
# Build with isolation (default)
python -m build

# Build without isolation (uses current environment)
python -m build --no-isolation

# Skip dependency check
python -m build --skip-dependency-check
```

### Configuration Settings

```bash
# Pass configuration to the backend
python -m build --config-setting="--option=value"

# Multiple config settings
python -m build \
  --config-setting="--build-option=value1" \
  --config-setting="--global-option=value2"

# Example for limited API
python -m build -w --config-setting="--build-option=--py-limited-api=cp37"
```

## Working with pyproject.toml

The build tool reads configuration from `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "My Python package"
```

## Build Process

### What Happens During Build

1. **Create isolated environment** (unless `--no-isolation`)
2. **Install build dependencies** from `build-system.requires`
3. **Call the build backend** specified in `build-backend`
4. **Generate artifacts** in the output directory

### Build Output

```bash
$ python -m build
* Creating venv isolated environment...
* Installing packages in isolated environment... (hatchling)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
* Creating venv isolated environment...
* Installing packages in isolated environment... (hatchling)
* Getting build dependencies for wheel...
* Building wheel...
Successfully built my_package-0.1.0.tar.gz and my_package-0.1.0-py3-none-any.whl
```

## Advanced Usage

### Verbose Output

```bash
# Show detailed build information
python -m build --verbose

# Quiet mode (minimal output)
python -m build --quiet
```

### Building from Source Distribution

```bash
# Extract an sdist first
tar -xzf dist/package-1.0.0.tar.gz

# Build wheel from extracted sdist
python -m build --wheel package-1.0.0/
```

### Environment Variables

```bash
# Set SOURCE_DATE_EPOCH for reproducible builds
SOURCE_DATE_EPOCH=1609459200 python -m build

# Specify pip cache directory
PIP_CACHE_DIR=.cache python -m build

# Use custom index URL
PIP_INDEX_URL=https://pypi.org/simple python -m build
```

## Integration with Hatchling

When using Hatchling as the backend:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
# Hatchling-specific configuration
directory = "dist"
reproducible = true
```

### Hatchling Configuration via Build

```bash
# Pass Hatchling-specific options
python -m build --config-setting="--target=wheel"

# Build specific Hatchling target
python -m build --wheel --config-setting="--target=wheel:editable"
```

## Comparison with Hatch Build

| Feature         | `python -m build`      | `hatch build`           |
| --------------- | ---------------------- | ----------------------- |
| Build isolation | Default                | Optional                |
| Backend support | Any PEP 517            | Any PEP 517             |
| Configuration   | Via `--config-setting` | Direct options          |
| Output          | Both by default        | Both by default         |
| Verbosity       | `--verbose` flag       | `-v` flag               |
| Backend         | Backend-agnostic       | Optimized for Hatchling |

## CI/CD Examples

### GitHub Actions

```yaml
name: Build Package

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.x"

      - name: Install build
        run: pip install build

      - name: Build package
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

### GitLab CI

```yaml
build:
  stage: build
  image: python:3.11
  script:
    - pip install build
    - python -m build --outdir artifacts/
  artifacts:
    paths:
      - artifacts/
```

### Local Build Script

```bash
#!/bin/bash
# build.sh

set -e

echo "Installing build dependencies..."
pip install --upgrade pip build

echo "Cleaning previous builds..."
rm -rf dist/ build/

echo "Building package..."
python -m build

echo "Verifying build artifacts..."
ls -la dist/

echo "Build complete!"
```

## Docker Build

```dockerfile
# Dockerfile for building Python package
FROM python:3.11-slim

WORKDIR /build

# Install build tool
RUN pip install --no-cache-dir build

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build package
RUN python -m build --wheel --outdir /dist

# Final stage
FROM scratch
COPY --from=0 /dist/*.whl /
```

## Troubleshooting

### Common Issues

1. **Missing build module**

   ```bash
   pip install --upgrade build
   ```

2. **Build dependency conflicts**

   ```bash
   # Use isolation to avoid conflicts
   python -m build
   # Or upgrade pip and setuptools
   pip install --upgrade pip setuptools
   ```

3. **Permission errors**

   ```bash
   # Use --user flag or virtual environment
   pip install --user build
   # Or
   python -m venv venv && source venv/bin/activate
   ```

4. **Backend not found**
   ```toml
   # Ensure build-system is properly configured
   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"
   ```

## Best Practices

1. **Always use build isolation** for reproducible builds
2. **Test both sdist and wheel** formats
3. **Verify output** with `tar -tzf` (sdist) and `unzip -l` (wheel)
4. **Use CI/CD** for automated building
5. **Clean previous builds** before release builds
6. **Document build requirements** in pyproject.toml

## PEP 517 Compliance

The build module ensures PEP 517 compliance:

- Reads `pyproject.toml` for build configuration
- Creates isolated build environments
- Calls standard backend hooks
- Produces standard-compliant artifacts

## See Also

- [PEP 517 - Build System Interface](https://www.python.org/dev/peps/pep-0517/)
- [Python Build Documentation](https://build.pypa.io/)
- `overview.md`
- `output-customization.md`
