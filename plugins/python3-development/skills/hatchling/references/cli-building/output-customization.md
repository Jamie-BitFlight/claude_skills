---
category: cli-building
topics: [build-output, artifact-management, ci-cd-integration, build-directory]
related: [index.md, overview.md, building-wheels.md, building-sdist.md, building-all-targets.md]
---

# Build Output Directory Customization

## Overview

Hatchling supports flexible artifact placement through configuration and environment variables, enabling organized builds, CI/CD integration, and multi-configuration management. Reference this when helping users customize output directories, organize development vs release builds, integrate with CI/CD pipelines, and manage build artifacts.

## Default Output Location

By default, all build artifacts are placed in the `dist/` directory:

<eg>
project/
└── dist/
    ├── package-0.1.0.tar.gz      # sdist
    └── package-0.1.0-py3-none-any.whl  # wheel
</eg>

## Global Output Directory

### Configuration in pyproject.toml

```toml
[tool.hatch.build]
# Set global output directory for all targets
directory = "build/artifacts"

# Other global settings
reproducible = true
skip-excluded-dirs = true
```

### Using Environment Variables

```bash
# Set via environment variable
export HATCH_BUILD_DIRECTORY="custom_dist"
hatch build

# Or inline
HATCH_BUILD_DIRECTORY=/tmp/builds hatch build
```

## Per-Target Output Directories

### Configure Different Directories for Each Target

```toml
# Global build configuration
[tool.hatch.build]
directory = "build/default"

# Override for specific targets
[tool.hatch.build.targets.sdist]
directory = "build/source"

[tool.hatch.build.targets.wheel]
directory = "build/wheels"

[tool.hatch.build.targets.binary]
directory = "build/binaries"
```

Result structure:

<eg>
project/
└── build/
    ├── source/
    │   └── package-0.1.0.tar.gz
    ├── wheels/
    │   └── package-0.1.0-py3-none-any.whl
    └── binaries/
        └── package
</eg>

## Command-Line Output Control

### Using Hatch

```bash
# Hatch respects the configuration in pyproject.toml
hatch build  # Uses configured directory

# Clean build (removes artifacts before building)
hatch build --clean
```

### Using Python's Build Module

```bash
# Specify output directory
python -m build --outdir build/
python -m build -o custom_dist/

# Build specific target to specific directory
python -m build --wheel --outdir wheels/
python -m build --sdist --outdir source/
```

## Organized Build Structure

### Development vs Release Builds

```toml
# Development builds
[tool.hatch.build]
directory = "build/dev"

# For release builds, override via environment
# HATCH_BUILD_DIRECTORY=build/release hatch build
```

### Platform-Specific Directories

```bash
# Build script for platform-specific outputs
#!/bin/bash

PLATFORM=$(uname -s)
OUTPUT_DIR="build/${PLATFORM,,}"

python -m build --outdir "$OUTPUT_DIR"
```

### Version-Specific Directories

```python
# build_with_version.py
import subprocess
import tomllib
from pathlib import Path

# Read version from pyproject.toml
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    version = data["project"]["version"]

# Build to version-specific directory
output_dir = f"build/v{version}"
subprocess.run(["python", "-m", "build", "--outdir", output_dir])
```

## CI/CD Integration

### GitHub Actions with Custom Output

```yaml
name: Build and Release

on:
  push:
    tags:
      - "v*"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.x"

      - name: Install dependencies
        run: |
          pip install build hatch

      - name: Build to release directory
        run: |
          VERSION=${GITHUB_REF#refs/tags/}
          python -m build --outdir "release/${VERSION}"

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: release-artifacts
          path: release/
```

### GitLab CI with Stage-Specific Outputs

```yaml
stages:
  - build
  - test
  - deploy

build:dev:
  stage: build
  script:
    - python -m build --outdir build/dev
  artifacts:
    paths:
      - build/dev/

build:release:
  stage: build
  only:
    - tags
  script:
    - python -m build --outdir build/release
  artifacts:
    paths:
      - build/release/
```

## Multi-Configuration Builds

### Build Matrix with Different Outputs

```bash
#!/bin/bash
# build_matrix.sh

CONFIGS=("minimal" "full" "dev")
PYTHONS=("3.9" "3.10" "3.11")

for config in "${CONFIGS[@]}"; do
    for python in "${PYTHONS[@]}"; do
        output="build/${config}/py${python}"
        echo "Building ${config} for Python ${python} to ${output}"

        python${python} -m build --outdir "${output}"
    done
done
```

### Separate Debug and Release Builds

```toml
# pyproject.toml can't directly handle this,
# use environment variables or build scripts

# debug.toml (separate config file)
[tool.hatch.build]
directory = "build/debug"

# release.toml
[tool.hatch.build]
directory = "build/release"
```

```bash
# Build with different configs
PYPROJECT_TOML=debug.toml hatch build
PYPROJECT_TOML=release.toml hatch build
```

## Clean Build Management

### Automatic Cleanup

```bash
#!/bin/bash
# clean_build.sh

# Remove old builds
find build/ -name "*.whl" -mtime +7 -delete
find build/ -name "*.tar.gz" -mtime +7 -delete

# Build fresh
python -m build --outdir build/latest

# Create symlink to latest
ln -sfn build/latest dist
```

### Makefile for Build Management

```makefile
# Makefile

BUILD_DIR ?= build
DIST_DIR ?= dist
VERSION := $(shell python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")

.PHONY: build clean release

build:
	python -m build --outdir $(BUILD_DIR)

clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR)

release: clean
	python -m build --outdir $(DIST_DIR)/$(VERSION)

dev-build:
	python -m build --outdir $(BUILD_DIR)/dev

test-build:
	python -m build --outdir $(BUILD_DIR)/test
	pip install $(BUILD_DIR)/test/*.whl
```

## Docker Build Outputs

```dockerfile
# Multi-stage build with custom outputs
FROM python:3.11 as builder

WORKDIR /build
COPY . .

# Build to specific directory
RUN pip install build
RUN python -m build --outdir /artifacts

# Final stage
FROM python:3.11-slim

# Copy only the built artifacts
COPY --from=builder /artifacts /dist
```

## Temporary Build Directories

### Using System Temp Directory

```python
# build_to_temp.py
import tempfile
import shutil
from pathlib import Path
import subprocess

# Create temporary build directory
with tempfile.TemporaryDirectory(prefix="build_") as tmpdir:
    print(f"Building to {tmpdir}")

    # Build
    subprocess.run(["python", "-m", "build", "--outdir", tmpdir])

    # Copy to final destination
    dest = Path("dist")
    dest.mkdir(exist_ok=True)

    for file in Path(tmpdir).glob("*"):
        shutil.copy2(file, dest)
```

### RAM Disk Builds (Linux)

```bash
# Create RAM disk for faster builds
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=512M tmpfs /mnt/ramdisk

# Build to RAM disk
python -m build --outdir /mnt/ramdisk/build

# Copy results
cp /mnt/ramdisk/build/* dist/

# Cleanup
sudo umount /mnt/ramdisk
```

## Validation and Testing

### Verify Output Structure

```bash
#!/bin/bash
# verify_outputs.sh

OUTPUT_DIR="${1:-dist}"

echo "Checking build outputs in ${OUTPUT_DIR}"

# Check for expected files
if [ ! -f "${OUTPUT_DIR}"/*.tar.gz ]; then
    echo "ERROR: No sdist found"
    exit 1
fi

if [ ! -f "${OUTPUT_DIR}"/*.whl ]; then
    echo "ERROR: No wheel found"
    exit 1
fi

# List all artifacts
echo "Found artifacts:"
ls -la "${OUTPUT_DIR}"
```

### Test Installation from Custom Directory

```bash
# Build to custom directory
python -m build --outdir build/test

# Test installation
pip install build/test/*.whl

# Verify
python -c "import mypackage; print(mypackage.__version__)"
```

## Best Practices

1. **Use consistent directory structure** across projects
2. **Separate development and release builds** into different directories
3. **Clean old builds regularly** to save disk space
4. **Version your output directories** for release builds
5. **Use CI/CD artifacts** for build outputs
6. **Document output structure** in README
7. **Validate outputs** after building
8. **Use relative paths** in configuration for portability

## Troubleshooting

### Directory Not Created

```bash
# Ensure parent directory exists
mkdir -p build/output
python -m build --outdir build/output
```

### Permission Issues

```bash
# Use user-writable directory
python -m build --outdir ~/builds

# Or fix permissions
chmod 755 build/
```

### Path Resolution Issues

```python
# Use absolute paths in scripts
from pathlib import Path

output_dir = Path(__file__).parent / "build"
output_dir.mkdir(exist_ok=True)
```

## See Also

- `building-all-targets.md`
- `ci-cd-integration.md`
- [Build Configuration](https://hatch.pypa.io/latest/config/build/)
