---
category: Advanced Build Features
topics: [artifact-directories, build-output, ci-cd-integration, custom-directories, build-workflows]
related: [distributed-artifacts.md, build-context.md, build-data-passing.md]
---

# Artifact Directories

When helping users configure build pipelines and CI/CD integration, guide them to understand how artifact directories control where Hatchling places build outputs. Understanding directory configuration enables customized build workflows.

## Overview

Hatchling can output artifacts to configurable locations, supporting:

- Default `dist/` directory
- Custom output directories per target type
- Separate directories for wheels, sdists, and other artifacts
- Integration with build systems and CI/CD pipelines

## Default Artifact Directory

By default, all artifacts go to `dist/`:

```bash
hatch build
# Output:
# dist/mypackage-1.0.0-py3-none-any.whl
# dist/mypackage-1.0.0.tar.gz
```

The `dist/` directory is created if it doesn't exist.

## Configuring Artifact Directories

### Command-Line Override

Specify output directory when building:

```bash
# Single directory for all artifacts
hatch build -d build/artifacts

# Output:
# build/artifacts/mypackage-1.0.0-py3-none-any.whl
# build/artifacts/mypackage-1.0.0.tar.gz
```

### Per-Target Configuration

Configure different directories for different artifact types:

```toml
[tool.hatchling.builders.wheel]
# Standard build backend
# Note: wheel directory configuration in pyproject.toml is typically not directly supported
# Use command-line for now
```

Different backends can be configured:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.builders.wheel"

# Wheel-specific configuration
[tool.hatchling.targets.wheel]
# Artifact content configuration
packages = ["src/mypackage"]
```

### Build Script Integration

In build scripts, control output directory:

```bash
#!/bin/bash
# build.sh

# Build wheels to one location
hatch build --target wheel -d dist/wheels

# Build source distribution to another
hatch build --target sdist -d dist/sources

# Result:
# dist/wheels/mypackage-1.0.0-py3-none-any.whl
# dist/sources/mypackage-1.0.0.tar.gz
```

## Directory Structure Patterns

### Flat Structure

All artifacts in single directory:

```bash
hatch build -d dist

# dist/
# ├── mypackage-1.0.0-py3-none-any.whl
# └── mypackage-1.0.0.tar.gz
```

### Hierarchical Structure

Separate directories for artifact types:

```bash
#!/bin/bash
mkdir -p build/{wheels,sdists,other}

hatch build --target wheel -d build/wheels
hatch build --target sdist -d build/sdists

# build/
# ├── wheels/
# │   └── mypackage-1.0.0-py3-none-any.whl
# └── sdists/
#     └── mypackage-1.0.0.tar.gz
```

### Platform-Specific Structure

Organize by target platform:

```bash
#!/bin/bash
# build.sh

PLATFORMS=("linux" "macos" "windows")

for platform in "${PLATFORMS[@]}"; do
    mkdir -p "dist/${platform}"
    # Build for platform
    # Copy to appropriate directory
    hatch build -d "dist/${platform}"
done
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - run: pip install hatchling

      - name: Build artifacts
        run: |
          mkdir -p dist/wheels dist/sdists
          hatch build --target wheel -d dist/wheels
          hatch build --target sdist -d dist/sdists

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: python-package
          path: dist/
```

### GitLab CI

```yaml
build:
  image: python:3.11
  script:
    - pip install hatchling
    - mkdir -p dist/{wheels,sdists}
    - hatch build --target wheel -d dist/wheels
    - hatch build --target sdist -d dist/sdists
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
```

### Local Build Directory

Keep source clean, separate build outputs:

```bash
#!/bin/bash
# setup-build.sh

BUILD_DIR="build"
DIST_DIR="${BUILD_DIR}/dist"

# Clean previous builds
rm -rf "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

# Build to custom location
hatch build -d "${DIST_DIR}"

# Artifacts in build/dist/
ls -lah "${DIST_DIR}/"
```

## Artifact Inspection

### Listing Artifacts

```bash
ls -lah dist/

# Output:
# -rw-r--r--  1 user  staff  1.2M Nov  2 10:30 mypackage-1.0.0-py3-none-any.whl
# -rw-r--r--  1 user  staff  2.3M Nov  2 10:30 mypackage-1.0.0.tar.gz
```

### Verifying Artifact Integrity

```bash
# Check wheel contents
unzip -t dist/mypackage-1.0.0-py3-none-any.whl

# Check sdist contents
tar -tzf dist/mypackage-1.0.0.tar.gz | head -20
```

## Build Hook Integration

Build hooks can determine artifact locations:

```python
class ArtifactLocationHook(BuildHookInterface):
    def finalize(self, version, build_data, artifact):
        """Called after artifact is created"""
        # 'artifact' is the full path to created file
        artifact_dir = os.path.dirname(artifact)
        artifact_name = os.path.basename(artifact)

        print(f"Built: {artifact_name}")
        print(f"Location: {artifact_dir}")

        # Perform post-build operations
        # - Copy to staging area
        # - Sign the artifact
        # - Update artifact registry
```

## Practical Examples

### Multi-Platform Build

```bash
#!/bin/bash
# build-all.sh

DIST_BASE="dist"

# Clean
rm -rf "${DIST_BASE}"

# Linux build
echo "Building for Linux..."
hatch build -d "${DIST_BASE}/linux"

# Run tests on artifacts
python -m pytest

# Stage for release
mkdir -p "release/artifacts"
cp "${DIST_BASE}/linux"/* "release/artifacts/"
```

### Conditional Directory Selection

```bash
#!/bin/bash
# smart-build.sh

if [ "$CI" = "true" ]; then
    # CI environment - use standardized locations
    OUTPUT_DIR="ci/artifacts"
else
    # Local development - use standard location
    OUTPUT_DIR="dist"
fi

mkdir -p "${OUTPUT_DIR}"
hatch build -d "${OUTPUT_DIR}"

echo "Artifacts in: ${OUTPUT_DIR}"
ls "${OUTPUT_DIR}"
```

### Versioned Artifact Storage

```bash
#!/bin/bash
# versioned-build.sh

VERSION=$(hatch version)
DIST_DIR="dist/releases/${VERSION}"

mkdir -p "${DIST_DIR}"
hatch build -d "${DIST_DIR}"

echo "Built version ${VERSION}:"
ls -lah "${DIST_DIR}/"
```

## Cleanup and Maintenance

### Clean Build Directory

```bash
# Remove previous artifacts
rm -rf dist/

# Fresh build
hatch build
```

### Archive Old Artifacts

```bash
#!/bin/bash
# archive-old-builds.sh

DIST_DIR="dist"
ARCHIVE_DIR="archive"

# Archive artifacts older than 30 days
find "${DIST_DIR}" -type f -mtime +30 \
    -exec mv {} "${ARCHIVE_DIR}/" \;
```

## Best Practices

- **Consistent naming**: Use same directory structure across builds
- **CI/CD integration**: Document artifact locations in CI configuration
- **Cleanup scripts**: Automatically remove old artifacts to save space
- **Versioning**: Consider including version in artifact paths
- **Staging areas**: Separate build outputs from release artifacts
- **Documentation**: Document artifact location requirements
- **Security**: Don't commit build artifacts to version control (add to `.gitignore`)

## Troubleshooting

### "Permission denied" writing to directory

**Issue**: Cannot write artifacts to specified directory

**Solution**: Verify directory permissions:

```bash
mkdir -p dist
chmod 755 dist

# Or create with proper permissions
mkdir -m 755 -p dist
```

### Path doesn't exist

**Issue**: Directory specified doesn't exist

**Solution**: Create directories before building:

```bash
# Ensure directory exists
mkdir -p build/artifacts
hatch build -d build/artifacts
```

### Artifact not found after build

**Issue**: Build completes but artifacts not in specified directory

**Solution**: Verify correct directory path:

```bash
# Check where artifacts were created
find . -name "*.whl" -o -name "*.tar.gz"

# Use absolute path if relative path unclear
hatch build -d /absolute/path/to/dist
```

## See Also

- `distributed-artifacts.md` - Understanding artifact content and structure
- `build-context.md` - Accessing build information in hooks
- `build-data-passing.md` - Modifying what goes in artifacts
