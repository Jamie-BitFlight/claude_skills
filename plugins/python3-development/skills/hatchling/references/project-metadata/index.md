---
category: project-metadata
topics: [project-structure, pyproject.toml, PEP 621, configuration]
related: [build-system, version-management, build-hooks]
---

# Project Metadata & Configuration Reference

This section provides comprehensive documentation for configuring project metadata in Hatchling-based Python projects using `pyproject.toml`. All metadata follows the PEP 621 standard for interoperability across Python packaging tools.

When Claude is asked to help configure project metadata or understand Hatchling's metadata system, reference the relevant category below to locate specific configuration examples and explanations.

## Overview

Project metadata in Hatchling is stored entirely in the `[project]` table of `pyproject.toml`. Hatchling uses sensible defaults and supports dynamic metadata injection through metadata hooks for advanced use cases.

## Core Topics

### Essential Metadata

- `basic-metadata.md` - Name, version, description, readme, and Python version requirements
- `ownership.md` - Authors and maintainers configuration
- `keywords-classifiers.md` - Discovery aids and Trove classifier configuration

### Dependencies & Features

- `dependencies.md` - Required and optional dependencies with version specifiers
- `version-specifiers.md` - Complete guide to version constraint syntax
- `direct-references.md` - Git, VCS, and local path dependencies

### Project Information

- `urls.md` - Homepage, documentation, repository, bug tracker, and custom URLs
- `licenses.md` - SPDX expressions and license files (PEP 639)

### Entry Points & Plugins

- `entry-points-cli.md` - Command-line tool configuration
- `entry-points-gui.md` - GUI application entry points
- `entry-points-plugins.md` - Plugin discovery and registration

### Dynamic Configuration

- `dynamic-metadata.md` - Overview of dynamic field declaration
- `metadata-hooks.md` - Hook system overview and built-in hooks
- `custom-hooks.md` - Implementing MetadataHookInterface

### Advanced Topics

- `metadata-options.md` - Direct references, ambiguous features, and configuration flags

## Quick Start Example

```toml

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "A short description"
readme = "README.md"
requires-python = ">=3.8"
authors = [
    {name = "Your Name", email = "you@example.com"},
]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]
keywords = ["keyword1", "keyword2"]
dependencies = [
    "requests>=2.28.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = ["pytest", "black", "mypy"]
docs = ["sphinx", "sphinx-rtd-theme"]

[project.scripts]
my-cli = "my_package.cli:main"

[project.urls]
Documentation = "https://example.com/docs"
Repository = "https://github.com/user/my-package"

```

## Standards & Specifications

- **PEP 621**: Python Project Metadata specification - Defines the `[project]` table format
- **PEP 427**: Wheel Binary Package Format - Binary distribution metadata
- **PEP 440**: Version Identification and Dependency Specification - Version number and specifier syntax
- **PEP 427**: Entry Points - Mechanism for plugin discovery
- **PEP 639**: Licence Specification for Distributions - SPDX-based license configuration

## Related Configuration

For build-specific metadata and configuration:

- `../build-hooks/index.md` - Dynamic code execution during build
- `../version-management.md` - Version sources and automatic injection

## Validation & Checking

When using Hatchling, metadata is validated when:

1. Building distributions (wheel and sdist)
2. Running `hatch project metadata` command
3. Installing the project (development or production)

Invalid metadata will cause build failures with descriptive error messages identifying the specific issue.
