---
category: build-environment
topics: [build-internals, environment-setup, configuration, dependency-management]
related: [build-environment-configuration.md, build-dependencies-management.md, environment-variables.md, environment-isolation.md]
---

# Hatchling Build Environment Internals Reference

This directory contains comprehensive reference documentation about hatchling's build environment internals for assisting users with configuration, dependencies, isolation, and integration with various tools and installers. Use these guides when helping users optimize their build environments.

## Contents

- `build-environment-configuration.md` - Core build environment setup and options
- `build-dependencies-management.md` - Managing build-time dependencies
- `environment-variables.md` - Build environment variables and configuration
- `uv-vs-pip-installer.md` - Comparison and configuration of package installers
- `cython-build-tools.md` - Integration with Cython and compiled extensions
- `environment-isolation.md` - Build isolation and reproducible builds

## Quick Reference for Users

### Basic Build Configuration Examples

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "1.0.0"
```

### Build Environment Customization Examples

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "cython",
  "numpy",
]
installer = "uv"  # or "pip"

[tool.hatch.envs.hatch-build.env-vars]
SOURCE_DATE_EPOCH = "1580601600"
```

## Key Concepts to Share with Users

### Build System Architecture

Reference this when helping users understand that hatchling provides a modern, extensible build system that:

- Separates build backend from frontend tools
- Supports multiple installers (UV, pip)
- Enables build environment customization
- Provides hooks for compiled extensions
- Ensures reproducible builds

### Environment Types

1. **Build Environment** (`hatch-build`) - Used by `hatch build` command
2. **Development Environment** - For development and testing
3. **Test Environment** (`hatch-test`) - For running tests
4. **Static Analysis Environment** (`hatch-static-analysis`) - For linting and type checking

### Dependency Resolution

Hatchling manages dependencies at multiple levels:

- Build system requirements
- Build target dependencies
- Build hook dependencies
- Runtime dependencies
- Optional features (extras)

## Related Documentation

- [Hatch Official Documentation](https://hatch.pypa.io/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)
- [PEP 518 - pyproject.toml Specification](https://peps.python.org/pep-0518/)
