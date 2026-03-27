---
category: Build System Configuration
topics: [build-dependencies, target-dependencies, dependency-management, build-environment]
related: [index.md, runtime-dependencies.md, feature-dependencies.md, target-specific-hooks.md]
---

# Target-Specific Dependencies Configuration

Declare additional dependencies that must be installed only for specific build targets.

## Overview

When guiding users through Hatchling dependency configuration, reference this document to explain how target-specific dependencies work. Build targets often require dependencies that are not needed at runtime. Rather than adding them to global build dependencies, users can declare target-specific dependencies that are installed only when building that target.

**Source**: [Hatch Build Configuration - Target Dependencies](https://hatch.pypa.io/1.13/config/build/#target-dependencies)

## Configuration Syntax

```toml
[tool.hatch.build.targets.<TARGET>]
dependencies = [
    "dependency-name>=1.0.0",
    "another-package",
]
```

### Example

```toml
[tool.hatch.build.targets.wheel]
dependencies = []

[tool.hatch.build.targets.sdist]
dependencies = []

[tool.hatch.build.targets.custom]
dependencies = [
    "my-custom-builder>=2.0",
    "build-utils",
]
```

## Dependency Types

### Basic Build Dependencies

Packages required during the build of a specific target:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "setuptools>=40.0",
    "wheel",
    "cython>=0.29.0",
]
```

These are installed in the build environment before building that target.

## Runtime Dependency Inclusion

### Including All Runtime Dependencies

Declare that a target requires the project's runtime dependencies:

```toml
[tool.hatch.build.targets.custom]
require-runtime-dependencies = true
```

This is useful when:

- Building targets that embed the runtime environment
- Creating combined distributions (application bundles)
- Custom builders that need access to the full dependency tree

### Including Specific Features

Include only specific optional features of the project:

```toml
[tool.hatch.build.targets.custom]
require-runtime-features = [
    "database",
    "analytics",
]
```

This installs only the dependencies specified in:

```toml
[project.optional-dependencies]
database = ["sqlalchemy>=1.4.0", "alembic"]
analytics = ["pandas>=1.0.0", "numpy"]
```

## Dependency Version Specifications

Use standard PEP 440 version specifiers:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "package>=1.0.0",           # Minimum version
    "package<2.0.0",            # Maximum version
    "package>=1.0.0,<2.0.0",    # Version range
    "package~=1.4.2",           # Compatible release
    "package[extra]>=1.0.0",    # With extras
    "package @ git+https://github.com/...",  # Direct URL
]
```

## Practical Examples

### Example 1: Custom Builder with Third-Party Plugin

```toml
[tool.hatch.build.targets.wheel]
# No extra dependencies needed for standard wheel

[tool.hatch.build.targets.custom]
dependencies = [
    "hatch-fancy-builder>=1.0",
]
```

### Example 2: C Extension Building

```toml
[build-system]
requires = ["hatchling", "cython>=0.29.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
dependencies = [
    "cython>=0.29.0",
    "numpy>=1.19.0",
]

[tool.hatch.build.targets.sdist]
# Source dist doesn't need Cython, just source files
dependencies = []
```

### Example 3: Different Dependencies per Target

```toml
[project]
name = "myproject"
version = "1.0.0"
dependencies = ["requests>=2.25.0"]

[project.optional-dependencies]
cli = ["click>=7.0.0", "rich>=10.0.0"]
web = ["flask>=1.0.0"]

[tool.hatch.build.targets.wheel]
dependencies = ["wheel"]

[tool.hatch.build.targets.sdist]
dependencies = []

[tool.hatch.build.targets.binary]
dependencies = [
    "pyinstaller>=4.0",
    "setuptools>=40.0",
]
require-runtime-dependencies = true
require-runtime-features = ["cli"]
```

## Constraint Handling

### Version Pinning

For reproducible builds, pin specific versions:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "setuptools==65.5.0",
    "wheel==0.38.0",
    "cython==0.29.32",
]
```

### Optional Dependencies

Include packages only when necessary:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "cython>=0.29.0 ; sys_platform=='linux'",
    "windows-curses ; sys_platform=='win32'",
]
```

## Interaction with Build Hooks

Build hooks can also declare dependencies independently:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = [
    "jinja2>=3.0.0",
]

# Target itself needs different dependencies
[tool.hatch.build.targets.wheel]
dependencies = [
    "cython>=0.29.0",
]
```

Both sets are installed in the build environment.

## Environment Variables

Control dependency installation behavior:

```bash
# Build with specific dependency cache
HATCH_BUILD_LOCATION=/custom/path hatch build

# Force clean build environment
hatch build -c
```

## Build Environment Isolation

Target dependencies are installed in isolated build environments:

1. Fresh virtual environment created per build
2. Only specified dependencies installed
3. No interference with global packages
4. Clean state between builds

This ensures reproducibility and prevents dependency conflicts.

## Conflict Resolution

If the same package is specified with different versions:

```toml
[tool.hatch.build]
dependencies = ["package>=1.0.0"]

[tool.hatch.build.targets.wheel]
dependencies = ["package>=2.0.0"]  # More specific, takes precedence
```

The target-level specification takes precedence.

## Third-Party Builder Dependencies

When using third-party builders, declare them as target dependencies:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
dependencies = [
    "scikit-build-core>=0.5.0",  # C++ extension builder
]

[tool.hatch.build.targets.custom]
dependencies = [
    "hatch-jupyter-builder>=0.5",  # JupyterLab extension builder
]
```

The dependency must be added to `build-system.requires` for hatchling to find it during initialization.

## Performance Considerations

- Dependencies are installed fresh for each build target
- Use minimal dependency specifications to reduce installation time
- Combine related dependencies rather than splitting across targets
- Pin versions for reproducible, faster installs

## Troubleshooting

### Dependency Not Found During Build

Ensure the dependency is:

1. Properly specified in `dependencies` array
2. Available on PyPI or accessible URL
3. Compatible with the build Python version
4. Listed in `build-system.requires` if required by build system

### Version Conflicts

```bash
# View what would be installed
hatch build --dry-run

# Use verbose output to see dependency resolution
hatch -v build
```

## See Also

- `../build-hooks/hook-dependencies.md` - Dependencies for build hooks
- `index.md` - Overview of all target configuration options
- `../build-environment/build-dependencies-management.md` - Global build dependencies
