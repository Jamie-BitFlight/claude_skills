---
category: Build System Configuration
topics: [default-targets, build-selection, automation, distribution-workflow]
related: [index.md, versions-option.md]
---

# Default Target Selection

Control which build targets are built when no specific target is specified.

## Overview

When assisting users with Hatchling build workflows, reference this guide to explain default target selection behavior. When users run `hatch build` without specifying targets, hatchling builds certain targets by default. Understanding and controlling default target selection is important for build automation and distribution workflows.

## Default Behavior

When users run `hatch build` without `-t` flags, Hatchling builds default targets:

```bash
hatch build
# Builds wheel and sdist targets by default
# Creates: dist/mypackage-1.0.0-py3-none-any.whl
#          dist/mypackage-1.0.0.tar.gz
```

The built-in targets have default behavior:

- **wheel**: Built by default
- **sdist**: Built by default
- **custom**: NOT built by default (must be explicitly selected)
- **binary**: NOT built by default (must be explicitly selected)

## Explicit Target Selection

To guide users in specifying which targets to build, reference this example:

```bash
# Build only wheel
hatch build -t wheel

# Build only sdist
hatch build -t sdist

# Build wheel and custom target
hatch build -t wheel -t custom

# Build specific version of wheel
hatch build -t wheel:standard
```

## Target Selection Examples

### Example 1: Standard Build

```bash
hatch build
# Builds: wheel, sdist
```

### Example 2: Multiple Versions

```bash
hatch build -t wheel:standard -t wheel:optimized -t sdist
# Builds: wheel (standard), wheel (optimized), sdist
```

### Example 3: Custom Build Only

```bash
hatch build -t custom
# Builds: custom target only
```

### Example 4: Conditional Builds

```bash
# For CI/CD pipelines
if [ "$BUILD_TYPE" = "release" ]; then
    hatch build  # Build wheel and sdist for release
else
    hatch build -t wheel  # Build only wheel for development
fi
```

## Build Output Defaults

### Default Output Directory

Without explicit configuration:

```bash
hatch build
# Output goes to: ./dist/
# Contains: wheel (*.whl), sdist (*.tar.gz)
```

Specify custom output directory:

```bash
hatch build /custom/path/
```

Or configure in `pyproject.toml`:

```toml
[tool.hatch.build]
directory = "build-output"
```

### Build Artifacts Created

Default build creates these files:

<eg>
dist/
├── mypackage-1.0.0-py3-none-any.whl      # Wheel (always built by default)
└── mypackage-1.0.0.tar.gz                # Source distribution (always built by default)
</eg>

## Controlling Default Behavior

### Exclude Targets from Default Build

While you cannot explicitly exclude targets from defaults in configuration, you can:

1. Always use explicit `-t` flags in automation:

```bash
# Automation script
hatch build -t wheel -t sdist  # Explicit targets
```

2. Wrap hatch with a custom script:

```bash
#!/bin/bash
# build.sh - custom build script
if [ "$1" = "wheel-only" ]; then
    hatch build -t wheel
else
    hatch build  # Default behavior
fi
```

3. Use environment variables in CI/CD:

```bash
#!/bin/bash
# build.sh
if [ "$CI" = "true" ]; then
    hatch build -t wheel  # CI builds only wheel
else
    hatch build           # Local builds both
fi
```

## CI/CD Integration Patterns

### GitHub Actions Example

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

      - run: pip install hatch

      - name: Build distributions
        run: |
          hatch build  # Builds both wheel and sdist by default

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: distributions
          path: dist/
```

### Conditional Builds

```yaml
- name: Build
  run: |
    if [ "${{ github.event_name }}" = "release" ]; then
      hatch build  # Release: build both
    else
      hatch build -t wheel  # Commit: build only wheel
    fi
```

## PyPI Release Workflow

For PyPI releases, typically build both default targets:

```bash
# Clean build
hatch build -c

# Creates for PyPI upload
ls -la dist/
# mypackage-1.0.0-py3-none-any.whl
# mypackage-1.0.0.tar.gz

# Upload all distributions
twine upload dist/*
```

## Development Workflow

For local development, you might only need wheel:

```bash
# Quick local build (faster)
hatch build -t wheel

# Full build (slower, for testing)
hatch build
```

## Version-Specific Default Selection

When a target has versions, all versions are selected by default:

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "optimized"]
```

```bash
hatch build -t wheel
# Builds both standard AND optimized versions
```

To build specific versions:

```bash
hatch build -t wheel:standard
# Builds only the standard version
```

## Multiple Targets with Versions

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "optimized"]

[tool.hatch.build.targets.sdist]
# Implies single version
```

```bash
hatch build
# Builds: wheel:standard, wheel:optimized, sdist

hatch build -t wheel
# Builds: wheel:standard, wheel:optimized

hatch build -t wheel:standard
# Builds: wheel:standard only

hatch build -t sdist
# Builds: sdist only
```

## Build Cleanup and Output

### Clean Before Build

Remove existing artifacts before building:

```bash
hatch build -c
# Cleans dist/ directory, then builds all defaults
```

### Verify Built Artifacts

```bash
hatch build
ls -lh dist/

# Output:
# -rw-r--r-- 1 user group 2.5M Nov 02 14:32 mypackage-1.0.0-py3-none-any.whl
# -rw-r--r-- 1 user group 5.2M Nov 02 14:32 mypackage-1.0.0.tar.gz
```

## Performance Considerations

Building sdist is often slower than wheel:

```bash
# Faster: wheel only
hatch build -t wheel

# Slower: both wheel and sdist
hatch build

# For development, use wheel-only builds
hatch build -t wheel
```

## Troubleshooting Default Behavior

### Custom Target Not Building

```bash
hatch build
# Custom target is NOT built by default
# Must explicitly select:
hatch build -t custom
```

### Binary Target Not Building

```bash
hatch build
# Binary target is NOT built by default
# Must explicitly select:
hatch build -t binary
```

### Unexpected Targets Built

If more targets are building than expected:

```bash
# Check what will be built without building
hatch build --help
# Review which targets are configured in pyproject.toml
```

## Best Practices

1. **Be Explicit in CI/CD**: Always specify targets in automation

```bash
# CI/CD: Explicit targets
hatch build -t wheel -t sdist
```

2. **Use Defaults for Local Development**: Simpler for manual builds

```bash
# Local: Use defaults
hatch build
```

3. **Document Build Strategy**: Explain in project documentation

```markdown
# Building

Build all distributions for release: hatch build

Build only wheel for development: hatch build -t wheel
```

4. **Test Build Configurations**: Verify defaults work as expected

```bash
# Test what gets built
hatch build -c
ls dist/
```

5. **Use Clean Flag When Needed**: Remove stale artifacts before building

```bash
# Full clean rebuild
hatch build -c
```

## See Also

- `../build-targets/index.md` - Available build targets
- `../build-targets/wheel-builder.md` - Wheel target details
- `../build-targets/sdist-builder.md` - Source distribution details
- `versions-option.md` - Version-specific selections
