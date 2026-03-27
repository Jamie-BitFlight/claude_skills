---
name: hatchling
description: Use when working with Hatchling — configuring build system setup, pyproject.toml metadata, dependencies, entry points, build hooks, version management, wheel and sdist builds, package distribution, setuptools migration, or troubleshooting Hatchling build errors. Covers PEP 517/518/621/660 standards.
---

# Hatchling

## Overview

Hatchling is a modern, standards-compliant Python build backend that replaces legacy setuptools for package building. It provides clear configuration through `pyproject.toml`, intelligent defaults, and extensibility through hooks and plugins. This skill enables understanding Hatchling's architecture, configuration options, and build customization capabilities.

## Key Capabilities

Consult `../python3-development/references/python3-standards.md` when applying shared architecture, typing, testing, or CLI rules; full standards, graphs, and amendment process are documented there.

- **Configuration via pyproject.toml**: Standards-compliant PEP 621 metadata with sensible defaults
- **Build Targets**: Wheel and source distribution builds with extensive customization
- **Build Hooks**: Dynamic code execution during build for artifacts, version management, and compilation
- **Version Management**: Multiple version sources with automatic version injection
- **File Selection**: Git-aware VCS integration with glob pattern matching
- **Plugins**: Extensible architecture for custom builders, hooks, and metadata hooks

## Reference Documentation

This skill provides comprehensive reference documentation organized by topic. Each section links to detailed guides covering configuration, usage patterns, and examples.

### Project Configuration

- `references/project-metadata/index.md` - Package metadata, dependencies, entry points, dynamic fields
- `references/build-system/index.md` - Build backend setup, PEP 517/518, reproducible builds, environment variables

### Build Targets

- `references/wheel-target/index.md` - Wheel configuration, package discovery, file selection, editable installs
- `references/sdist-target/index.md` - Sdist configuration, VCS integration, legacy setup.py support
- `references/build-targets/index.md` - Wheel, sdist, binary, custom builders, multi-version builds
- `references/target-config/index.md` - Target-specific hooks, dependencies, versions, precedence

### File Selection & Build Customization

- `references/file-selection/index.md` - Git-style globs, include/exclude patterns, VCS integration, force-include
- `references/build-hooks/index.md` - Hook interface, execution order, custom hooks, version hooks, build data passing
- `references/advanced-features/index.md` - Dynamic dependencies, force-include, path rewriting, editable installs, build context

### Version & Metadata Management

- `references/version-management/index.md` - Version sources (code, regex, env), schemes, validation, build hooks
- `references/metadata-hooks/index.md` - Metadata hook interface, custom hooks, dynamic metadata generation
- `references/context-formatting/index.md` - Context variables, environment-based config, interpolation

### Plugin System

- `references/plugins/index.md` - Builder, hook, metadata, version plugins, hatch-vcs, plugin development

### Build Environment & Integration

- `references/build-environment/index.md` - Environment config, dependencies, UV vs pip, Cython integration, isolation
- `references/integration/index.md` - PEP standards compliance, setup.py migration, setuptools compatibility, CMake/extensions
- `references/special-config/index.md` - PEP 561 type hints, SPDX licenses, namespace packages, src-layout, extensions

### Core Concepts & Standards

- `references/core-concepts/index.md` - PEP 517 backend, minimal philosophy, VCS file selection, reproducible builds
- `references/standards/index.md` - Python packaging overview, PEP references, metadata specs, distribution formats

### Operational Guides

- `references/cli-building/index.md` - hatch build commands, python -m build, pip install, output customization
- `references/error-handling/index.md` - Path validation, file selection errors, version/license validation, heuristic failures
- `references/release-notes/index.md` - Hatchling version history, feature additions, PEP 639 support, performance improvements
