---
name: Hatchling Build Targets - Index
description: Navigation guide to all Hatchling build target types with quick reference configuration examples
---

# Hatchling Build Targets Reference

This directory contains comprehensive documentation for all build target types available in Hatchling, the modern Python packaging backend. Use this index to understand which build target solves your packaging problem.

## Available Build Targets

### Core Build Targets

- `wheel-builder.md` - Binary distribution format for Python packages
- `sdist-builder.md` - Source archive format for Python packages
- `binary-builder.md` - Standalone executable applications using PyApp

### Custom & Third-Party

- `custom-builder.md` - Creating custom build targets for specialized needs
- `third-party-builders.md` - Integration with external build systems

### Advanced Features

- `multi-version-builds.md` - Building multiple versions of targets
- `target-dependencies.md` - Managing dependencies per build target

## Quick Reference

### Basic Configuration

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
# Wheel-specific configuration

[tool.hatch.build.targets.sdist]
# Source distribution configuration

[tool.hatch.build.targets.binary]
# Binary executable configuration
```

### Building Targets

```bash
# Build all default targets (sdist and wheel)
hatch build

# Build specific target
hatch build -t wheel

# Build specific target version
hatch build -t wheel:standard

# Build multiple targets
hatch build -t sdist -t wheel -t binary
```

## Target Types Overview

| Target   | Purpose             | Output Format  | Use Case                             |
| -------- | ------------------- | -------------- | ------------------------------------ |
| `wheel`  | Binary distribution | `.whl` file    | Standard Python package installation |
| `sdist`  | Source distribution | `.tar.gz` file | Source code distribution             |
| `binary` | Standalone app      | Executable     | Self-contained applications          |
| `custom` | User-defined        | Varies         | Specialized build requirements       |

## Common Patterns

### Excluding Files from Specific Targets

```toml
[tool.hatch.build.targets.sdist]
exclude = [
  "/.github",
  "/docs",
  "/tests",
]

[tool.hatch.build.targets.wheel]
exclude = [
  "/tests",
]
```

### Including Only Specific Packages

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
only-packages = true
```

### Forced Inclusion

```toml
[tool.hatch.build.targets.wheel]
force-include = {
  "LICENSE" = "LICENSE",
  "README.md" = "README.md",
}
```

## Build Hooks

Build targets can use hooks to customize the build process:

```toml
[tool.hatch.build.hooks.custom]
# Global hook configuration

[tool.hatch.build.targets.wheel.hooks.custom]
# Target-specific hook configuration
```

## Environment Variables

Key environment variables that affect builds:

- `HATCH_BUILD_CLEAN` - Clean before building
- `HATCH_BUILD_HOOKS_ONLY` - Only run hooks
- `HATCH_BUILD_NO_HOOKS` - Skip all hooks
- `HATCH_BUILD_LOCATION` - Override output directory

## Decision Tree: Choosing a Build Target

When building a Python package, ask yourself:

1. **Do you need to distribute source code?** → Use `sdist`
2. **Do you need binary distribution for pip install?** → Use `wheel`
3. **Do you need a standalone executable?** → Use `binary`
4. **Do you have non-standard build requirements?** → Use `custom` or third-party builders

For most packages: use both `sdist` and `wheel` (the default).

## See Also

- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- [Hatchling Documentation](https://hatch.pypa.io/latest/build/)
- [Python Packaging User Guide](https://packaging.python.org/)
