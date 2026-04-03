---
category: build-system
topics:
- hatchling-configuration
- pyproject-toml
- build-backend
- pep-517
- pep-518
related:
- build-hooks
- build-targets
- build-environment
---

# Build System Configuration Guide for Claude

This reference helps Claude assist users with Hatchling's build system configuration in `pyproject.toml`. Focus on PEP 517/518 compliance, build options, and environment controls.

## Core Configuration Topics

### Essential Build Setup

- `build-system-declaration.md` - Configure `[build-system]` table correctly
- `pep-standards.md` - Implement PEP 517/518 standards properly
- `build-options.md` - Configure `[tool.hatch.build]` settings

### Build Control Configuration

- `output-directory.md` - Set custom build output paths with `directory` option
- `reproducible-builds.md` - Use SOURCE_DATE_EPOCH for deterministic builds
- `vcs-integration.md` - Control `.gitignore` file handling with `ignore-vcs`

### Environment Configuration

- `environment-variables.md` - Use HATCH*BUILD*\* variables for dynamic configuration
- `dev-mode.md` - Configure editable/development installations with `dev-mode-dirs`

## Quick Configuration Templates for Claude

### Minimal Build System

When users need basic Hatchling setup:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Standard Build Options

Common configuration patterns to suggest:

```toml
[tool.hatch.build]
# Custom output path (default: "dist")
directory = "dist"

# Reproducible builds (default: true)
reproducible = true

# Respect .gitignore (default: false)
ignore-vcs = false

# Performance optimization
skip-excluded-dirs = true

# Development mode paths
dev-mode-dirs = ["."]
dev-mode-exact = false
```

## Key Concepts for Claude to Remember

### Build System Declaration Requirements

- `requires` list must include "hatchling" at minimum
- `build-backend` must be "hatchling.build"
- Version pinning improves reproducibility

### Build Options Priority

- Environment variables override pyproject.toml settings
- HATCH_BUILD_LOCATION overrides `directory` setting
- SOURCE_DATE_EPOCH controls reproducible timestamps

### File Selection Logic

1. `force-include` mappings (highest priority)
2. `artifacts` patterns
3. `exclude` patterns
4. VCS ignore patterns (if `ignore-vcs = false`)
5. `include` patterns (lowest priority)

## Common User Scenarios

### Migrating from Setuptools

When users migrate from setuptools, replace:

```toml
# Old
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

# New
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### CI/CD Build Configuration

For automated builds, suggest environment variables:

```bash
export HATCH_BUILD_LOCATION="${CI_PROJECT_DIR}/artifacts"
export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
export HATCH_BUILD_CLEAN=true
```

### Including Generated Files

When users need to include VCS-ignored files:

```toml
[tool.hatch.build]
# Include compiled extensions
artifacts = ["*.so", "*.dll", "*.pyd"]
```

## Navigation

- `../build-hooks/index.md` - Customize build process
- `../build-targets/index.md` - Configure wheel and sdist targets
- `../build-environment/README.md` - Manage build environments
