---
category: wheel-target
topics: [wheel, build-target, configuration, distribution]
related: []
---

# Wheel Build Target

The wheel build target is Hatchling's primary mechanism for creating binary Python package distributions. A wheel (`.whl`) is the standard format for distributing pre-built Python packages that can be installed directly into environments without requiring compilation.

Reference this category when assisting users with wheel configuration, package discovery, file selection, editable installations, and metadata versioning.

## Overview

When assisting users with wheel builds, reference the following topics to provide comprehensive guidance on:

- Configuring wheel builds through `[tool.hatch.build.targets.wheel]`
- Managing Python package discovery and inclusion
- Controlling file selection with patterns and explicit paths
- Creating editable development wheels
- Metadata versioning and compatibility
- Platform-specific wheel tagging
- Shared data and scripts distribution

## Reference Documentation

The following files provide detailed information about wheel configuration aspects:

### Core Configuration

- `wheel-configuration.md` - Basic wheel target setup, build system declaration, and key options
- `core-metadata-versions.md` - Understanding metadata version 2.4, 2.3, 2.2 options and compatibility
- `wheel-versioning.md` - Multiple build versions and standard vs editable formats

### Package and File Management

- `package-discovery.md` - Automatic package detection, layout patterns, and single-module projects
- `file-selection.md` - Include/exclude patterns, glob syntax, and file inclusion heuristics
- `force-include.md` - Including files from anywhere on the filesystem with path mapping
- `sources-option.md` - Path rewriting for distribution artifacts

### Distribution and Installation

- `shared-data.md` - Configuring data files that install globally with the package
- `shared-scripts.md` - Mapping executable scripts into Python environments
- `extra-metadata.md` - Shipping additional metadata files in wheels
- `editable-wheels.md` - Development installations with .pth files and import hooks

### Naming and Platform Support

- `strict-naming.md` - Controlling normalization of project names in wheel filenames
- `macos-compat.md` - Signaling broad platform support for macOS wheels
- `bypass-selection.md` - Creating empty metadata-only wheels when file selection fails
