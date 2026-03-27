---
category: Build System Configuration
topics: [build-targets, target-configuration, pyproject.toml, wheel, sdist, custom-targets]
related: [target-specific-hooks.md, target-dependencies.md, versions-option.md, config-precedence.md]
---

# Build Targets Configuration Reference

Complete reference guide for configuring hatchling build targets using `[tool.hatch.build.targets.<TARGET>]` in `pyproject.toml`.

## Overview

When assisting users with Hatchling build system configuration, reference this guide to explain how build targets define how projects are packaged into distributable formats. Each target can be customized independently with its own configuration, hooks, and dependencies. The three built-in targets are:

- **wheel**: Binary distribution (`.whl` files)
- **sdist**: Source distribution (`.tar.gz` files)
- **custom**: User-defined build targets

## Topics

### Core Configuration

- `target-specific-hooks.md` - Execute code at specific stages of each target's build process
- `target-dependencies.md` - Declare dependencies needed only for specific build targets
- `versions-option.md` - Build multiple variations of the same target using different strategies

### Dependency Management

- `runtime-dependencies.md` - Include or require project runtime dependencies during builds
- `feature-dependencies.md` - Depend on specific optional features of the project

### Configuration Patterns

- `config-precedence.md` - Understand how target settings override global build configuration
- `default-targets.md` - Control which targets are built when not explicitly specified

## All Reference Files

1. `index.md` - This overview document
2. `target-specific-hooks.md` - Hooks for individual targets
3. `target-dependencies.md` - Target-specific build dependencies
4. `runtime-dependencies.md` - Using project runtime dependencies in builds
5. `feature-dependencies.md` - Using optional features in builds
6. `versions-option.md` - Multi-version build strategies
7. `config-precedence.md` - Configuration hierarchy and precedence
8. `default-targets.md` - Default target selection behavior

## Quick Reference

### Basic Target Configuration Structure

```toml
[tool.hatch.build.targets.wheel]
# Target-specific options here

[tool.hatch.build.targets.wheel.hooks.your-hook]
# Hook configuration for this target

[tool.hatch.build.targets.sdist]
# Source distribution specific options
```

### Global vs Target-Level Settings

Global settings apply to all targets:

```toml
[tool.hatch.build]
reproducible = true  # Applies to all targets

[tool.hatch.build.targets.wheel]
reproducible = false  # Overrides global setting for wheel target
```

## Building with Targets

```bash
# Build all targets
hatch build

# Build specific target
hatch build -t wheel

# Build specific target with specific version
hatch build -t wheel:standard

# Build multiple specific targets
hatch build -t wheel -t sdist
```

## Related Documentation

- `../build-targets/index.md` - Detailed builder implementations (wheel, sdist, custom, binary)
- `../build-hooks/index.md` - Hook system and available hooks
- `../core-concepts/INDEX.md` - PEP 517 and build system fundamentals
