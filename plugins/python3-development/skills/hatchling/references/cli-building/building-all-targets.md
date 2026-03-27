---
category: cli-building
topics: [build-targets, multi-target, sdist, wheels, hatchling]
related: [index.md, overview.md, building-wheels.md, building-sdist.md, output-customization.md]
---

# Building All Targets with Hatchling

## Overview

Building multiple targets simultaneously is the default Hatchling behavior, producing both sdist and wheel artifacts in a single operation. Reference this when helping users understand multi-target configuration, parallel building strategies, version consistency across targets, and CI/CD integration patterns.

## Command-Line Usage

### Using Hatch

```bash
# Build all targets (default behavior)
hatch build

# Explicitly build all targets
hatch build --target all

# Clean build (remove old artifacts first)
hatch build --clean
```

Output example:

```console
$ hatch build
[sdist]
dist/my_package-1.0.0.tar.gz

[wheel]
dist/my_package-1.0.0-py3-none-any.whl
```

### Using Python's Build Module

```bash
# Build both sdist and wheel (default)
python -m build

# Equivalent to
python -m build --sdist --wheel

# With custom output directory
python -m build --outdir dist/

# With verbose output
python -m build --verbose
```

### Using Build with Options

```bash
# Skip dependency check
python -m build --skip-dependency-check

# Without build isolation
python -m build --no-isolation

# Specify config settings
python -m build --config-setting="--build-option=value"
```

## Multiple Target Configuration

Configure multiple targets in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Configure sdist target
[tool.hatch.build.targets.sdist]
include = [
  "src/**/*.py",
  "tests/**/*.py",
  "README.md",
  "LICENSE",
]
exclude = ["*.pyc", "__pycache__"]

# Configure wheel target
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
exclude = ["tests"]

# Configure binary target (optional)
[tool.hatch.build.targets.binary]
scripts = ["myapp=mypackage.cli:main"]
```

## Building Specific Target Combinations

### Build Multiple Specific Targets

```bash
# Build wheel and binary (skip sdist)
hatch build -t wheel -t binary

# Build with different versions
hatch build -t wheel:standard -t wheel:editable
```

### Sequential Building

```bash
# Build targets sequentially
hatch build -t sdist && hatch build -t wheel

# With cleanup between builds
rm -rf dist/*.tar.gz && hatch build -t sdist
rm -rf dist/*.whl && hatch build -t wheel
```

## Parallel Building

Using GNU parallel or similar tools:

```bash
# Parallel build (Unix-like systems)
parallel hatch build -t ::: sdist wheel

# Using xargs
echo -e "sdist\nwheel" | xargs -I {} -P 2 hatch build -t {}
```

## Build Output Organization

### Default Output Structure

<eg>
project/
├── dist/
│   ├── my_package-1.0.0.tar.gz      # sdist
│   ├── my_package-1.0.0-py3-none-any.whl  # wheel
│   └── my_package                    # binary (if configured)
</eg>

### Custom Output Directories

```toml
[tool.hatch.build]
# Global output directory
directory = "build/dist"

# Per-target directories
[tool.hatch.build.targets.sdist]
directory = "build/source"

[tool.hatch.build.targets.wheel]
directory = "build/wheels"
```

### Build with Custom Directories

```bash
# Override output directory via command line
HATCH_BUILD_DIRECTORY=custom_dist hatch build

# Using Python build module
python -m build --outdir custom_dist/
```

## Build Hooks for All Targets

Configure hooks that run for all targets:

```toml
# Global build hooks
[tool.hatch.build.hooks.custom]
path = "build_hooks.py"

# Hooks for specific targets
[tool.hatch.build.targets.wheel.hooks.custom]
path = "wheel_hooks.py"

[tool.hatch.build.targets.sdist.hooks.custom]
path = "sdist_hooks.py"
```

## Version Management

Ensure consistent versions across all targets:

```toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"

# Dynamic version for all targets
[project]
dynamic = ["version"]

# Version hook for build time
[tool.hatch.build.hooks.version]
```

## Build Validation

### Validating All Artifacts

```bash
# Build everything
hatch build

# Validate sdist
tar -tzf dist/*.tar.gz | head -20

# Validate wheel
unzip -l dist/*.whl | head -20

# Check metadata
python -m pip show dist/*.whl
```

### Automated Validation Script

```bash
#!/bin/bash
# build-and-validate.sh

echo "Building all targets..."
hatch build --clean

echo "Validating sdist..."
for sdist in dist/*.tar.gz; do
    echo "Checking $sdist"
    tar -tzf "$sdist" | grep -E "(pyproject\.toml|README|LICENSE)" || exit 1
done

echo "Validating wheels..."
for wheel in dist/*.whl; do
    echo "Checking $wheel"
    unzip -t "$wheel" > /dev/null || exit 1
done

echo "All artifacts validated successfully!"
```

## CI/CD Integration

### GitHub Actions Example

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

      - name: Install build dependencies
        run: |
          pip install --upgrade pip
          pip install build hatch

      - name: Build all targets
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

### GitLab CI Example

```yaml
build:
  stage: build
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
```

## Performance Optimization

### Caching Build Dependencies

```bash
# Cache pip packages
pip install --cache-dir .pip-cache build

# Cache hatch environments
export HATCH_ENV_DIR=.hatch-env
hatch build
```

### Incremental Builds

```toml
[tool.hatch.build]
# Skip unchanged files
skip-excluded-dirs = true

# Use build cache
[tool.hatch.build.targets.wheel]
# Only rebuild changed files
skip-gitignored = true
```

## Troubleshooting

### Common Issues

1. **Missing files in one target but not another**

   ```toml
   # Ensure consistent file selection
   [tool.hatch.build]
   include = ["src/**/*.py"]  # Applies to all targets
   ```

2. **Different versions between targets**

   ```bash
   # Clean build to ensure consistency
   hatch build --clean
   ```

3. **Build failures for specific targets**
   ```bash
   # Build targets individually to isolate issues
   hatch build -t sdist  # Test sdist alone
   hatch build -t wheel  # Test wheel alone
   ```

## Best Practices

1. **Always build all targets before release**: Ensures both sdist and wheel are available
2. **Test installation from both formats**: `pip install dist/*.tar.gz` and `pip install dist/*.whl`
3. **Automate in CI/CD**: Build all targets in continuous integration
4. **Clean builds for releases**: Use `--clean` flag for release builds
5. **Validate all artifacts**: Check contents and metadata of all built files

## See Also

- `building-wheels.md`
- `building-sdist.md`
- `output-customization.md`
- `python-build-tool.md`
