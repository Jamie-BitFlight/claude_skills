---
category: build-system
topics:
- output-directory
- build-location
- environment-variables
- ci-cd-integration
related:
- build-options
- environment-variables
- reproducible-builds
---

# Output Directory Configuration Guide for Claude

This reference helps Claude configure where Hatchling places build artifacts (wheels and source distributions). Use this to help users set custom build output paths.

## Default Behavior

By default, Hatchling creates a `dist` directory:

<eg>
project/
├── pyproject.toml
├── src/
└── dist/                        # Default output
    ├── mypackage-1.0.0-py3-none-any.whl
    └── mypackage-1.0.0.tar.gz
</eg>

## Configuration Methods

### In pyproject.toml

Set the directory option:

```toml
[tool.hatch.build]
# Change output directory
directory = "build"              # Relative path
directory = "build/packages"     # Nested path
directory = "../shared-builds"   # Parent directory
directory = "/tmp/builds"        # Absolute path
```

### Via Environment Variable

Override at build time:

```bash
# Environment variable takes precedence
export HATCH_BUILD_LOCATION="/custom/path"
hatch build

# Or inline
HATCH_BUILD_LOCATION="/tmp/build" hatch build
```

## Path Types and Expansion

### Environment Variable Expansion

Use environment variables in paths:

```toml
[tool.hatch.build]
# Unix/Linux/macOS
directory = "${BUILD_DIR}/myproject"
directory = "$HOME/builds"
directory = "${CI_OUTPUT_DIR}"

# Windows
directory = "%USERPROFILE%/builds"
directory = "%TEMP%/artifacts"
```

### CI/CD Integration Patterns

Suggest these for different CI systems:

```toml
[tool.hatch.build]
# GitHub Actions
directory = "${GITHUB_WORKSPACE}/dist"

# GitLab CI
directory = "${CI_PROJECT_DIR}/artifacts"

# Jenkins
directory = "${WORKSPACE}/build/packages"

# Azure DevOps
directory = "${BUILD_ARTIFACTSTAGINGDIRECTORY}"

# Generic CI
directory = "${CI_BUILD_DIR:-dist}"
```

## Target-Specific Directories

### Different Directories per Target

Configure separate output for wheels and sdist:

```toml
# Global default
[tool.hatch.build]
directory = "dist"

# Wheel-specific directory
[tool.hatch.build.targets.wheel]
directory = "dist/wheels"

# Source distribution directory
[tool.hatch.build.targets.sdist]
directory = "dist/source"

# Custom target directory
[tool.hatch.build.targets.custom]
directory = "dist/custom"
```

## Platform-Specific Configuration

### Cross-Platform Paths

Help users handle different operating systems:

```bash
# Shell script for platform detection
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    export HATCH_BUILD_LOCATION="/var/builds"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    export HATCH_BUILD_LOCATION="$HOME/Library/Builds"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    export HATCH_BUILD_LOCATION="C:/builds"
fi
```

### Docker Builds

For containerized builds:

```dockerfile
# Dockerfile
FROM python:3.11

# Set build directory
ENV HATCH_BUILD_LOCATION=/app/dist

WORKDIR /app
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install hatchling && hatch build

# Artifacts available at /app/dist/
```

## Directory Management

### Clean Build Directory

Control cleaning behavior:

```bash
# Clean before building
export HATCH_BUILD_CLEAN=true
hatch build

# Clean after hooks
export HATCH_BUILD_CLEAN_HOOKS_AFTER=true
hatch build

# Manual cleaning
rm -rf dist/
hatch clean
```

### Directory Creation

Hatchling creates directories automatically:

- Parent directories must exist for absolute paths
- Relative paths are created as needed
- Check permissions in shared environments

## Common Patterns

### Version-Organized Builds

Organize by version:

```bash
# Script to organize by version
VERSION=$(hatch version)
HATCH_BUILD_LOCATION="dist/v${VERSION}" hatch build

# Results in:
# dist/
#   └── v1.0.0/
#       ├── mypackage-1.0.0-py3-none-any.whl
#       └── mypackage-1.0.0.tar.gz
```

### Development vs Production

Different locations for different environments:

```toml
# Development
[tool.hatch.envs.dev]
[tool.hatch.envs.dev.env-vars]
HATCH_BUILD_LOCATION = "./build"

# Production
[tool.hatch.envs.production]
[tool.hatch.envs.production.env-vars]
HATCH_BUILD_LOCATION = "/var/builds"
```

### Shared Team Directories

For team environments:

```toml
[tool.hatch.build]
# User-specific subdirectory
directory = "/shared/builds/${USER}"

# Pipeline-specific
directory = "/shared/builds/${CI_PIPELINE_ID:-local}"

# Timestamp-based
directory = "/shared/builds/${BUILD_ID:-$(date +%Y%m%d_%H%M%S)}"
```

## Troubleshooting Common Issues

### Directory Not Created

When users encounter permission or path issues:

```bash
# Check parent directory exists
ls -la $(dirname dist)

# Fix permissions
chmod 755 dist

# Create manually if needed
mkdir -p /custom/build/path
```

### Path Too Long (Windows)

For Windows MAX_PATH issues:

```toml
[tool.hatch.build]
# Use short paths on Windows
directory = "D:/b"  # Avoid long paths
```

### Permission Denied

For permission issues:

```bash
# Check directory permissions
ls -la dist/

# Change ownership if needed
sudo chown $USER:$USER dist/

# Use user-writable location
HATCH_BUILD_LOCATION="$HOME/builds" hatch build
```

## Best Practices to Recommend

### Path Strategy

1. Use relative paths for portability
2. Use environment variables for CI/CD flexibility
3. Avoid hardcoded absolute paths in shared configs
4. Document custom paths in README

### Directory Management

1. Clean old artifacts before new builds
2. Organize by version or timestamp for history
3. Separate development and production builds
4. Consider disk space in CI environments

### Validation Commands

Suggest these for testing:

```bash
# Verify directory configuration
python -c "
import tomli
with open('pyproject.toml', 'rb') as f:
    config = tomli.load(f)
    print(config.get('tool', {}).get('hatch', {}).get('build', {}).get('directory', 'dist'))
"

# Test with different locations
for dir in dist build /tmp/test; do
    HATCH_BUILD_LOCATION="$dir" hatch build
    ls -la "$dir"
done
```

## Priority Order

Help users understand precedence:

1. Command-line arguments (when supported)
2. `HATCH_BUILD_LOCATION` environment variable
3. Target-specific `directory` in pyproject.toml
4. Global `directory` in `[tool.hatch.build]`
5. Default: "dist"

## Navigation

- `build-options.md` - General build configuration
- `environment-variables.md` - All build-time variables
- `reproducible-builds.md` - Consistent output
