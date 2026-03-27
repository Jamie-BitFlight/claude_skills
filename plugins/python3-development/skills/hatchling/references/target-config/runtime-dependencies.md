---
category: Build System Configuration
topics: [runtime-dependencies, build-configuration, feature-dependencies, dependency-requirements]
related: [index.md, target-dependencies.md, feature-dependencies.md]
---

# Runtime Dependency Requirements Configuration

Configure build targets to depend on the project's runtime dependencies and features.

## Overview

When assisting users with build target configuration, reference this guide to explain how build targets can access the project's runtime dependencies. Some build targets need access to the project's runtime dependencies or specific optional features. Rather than duplicating dependency declarations, users can use the `require-runtime-dependencies` and `require-runtime-features` options to dynamically include them during builds.

**Source**: [Hatch Build Configuration - Target Dependencies](https://hatch.pypa.io/1.13/config/build/#target-dependencies)

## Configuration Options

### Require All Runtime Dependencies

Include all packages from the project's `dependencies` field:

```toml
[tool.hatch.build.targets.<TARGET>]
require-runtime-dependencies = true
```

When enabled, the build environment receives:

- All packages in `[project]` `dependencies`
- All packages in any `require-runtime-features` specifications
- The target's own `dependencies`

### Require Specific Runtime Features

Include only specific optional dependency groups:

```toml
[tool.hatch.build.targets.<TARGET>]
require-runtime-features = [
    "feature1",
    "feature2",
]
```

This installs packages from:

```toml
[project.optional-dependencies]
feature1 = ["package-a>=1.0", "package-b"]
feature2 = ["package-c>=2.0"]
```

## Usage Patterns

### Pattern 1: Binary Executable Target

Building standalone executables requires the full application:

```toml
[project]
name = "myapp"
dependencies = ["click>=7.0", "requests>=2.25"]

[project.optional-dependencies]
database = ["sqlalchemy>=1.4"]
cache = ["redis>=3.5"]

[tool.hatch.build.targets.binary]
dependencies = ["pyinstaller>=4.0"]
require-runtime-dependencies = true
require-runtime-features = ["database", "cache"]
```

This ensures the binary includes:

- All base dependencies (click, requests)
- Database feature (sqlalchemy)
- Cache feature (redis)

### Pattern 2: Documentation Building

Documentation tools may need to import the package:

```toml
[project]
dependencies = ["pydantic>=1.0"]

[project.optional-dependencies]
docs = ["sphinx>=3.0", "sphinx-rtd-theme"]

[tool.hatch.build.targets.custom]
require-runtime-dependencies = true
require-runtime-features = ["docs"]
```

### Pattern 3: Testing During Build

Some build targets may need to test the package:

```toml
[project]
dependencies = ["dataclasses-json"]

[project.optional-dependencies]
test = ["pytest>=6.0", "pytest-cov"]

[tool.hatch.build.targets.wheel]
# Standard wheel doesn't need test deps
dependencies = []

[tool.hatch.build.targets.custom]
require-runtime-dependencies = true
require-runtime-features = ["test"]
```

## Project Metadata Example

For reference, here's a complete project structure:

```toml
[project]
name = "myproject"
version = "1.0.0"
description = "My awesome project"
requires-python = ">=3.8"

# Base runtime dependencies
dependencies = [
    "requests>=2.25.0",
    "pydantic>=1.8.0",
    "click>=7.0.0",
]

# Optional dependency groups
[project.optional-dependencies]
database = [
    "sqlalchemy>=1.4.0",
    "psycopg2-binary>=2.8.0",
]
dev = [
    "pytest>=6.0.0",
    "black>=21.0.0",
    "mypy>=0.900",
]
docs = [
    "sphinx>=3.0.0",
    "sphinx-rtd-theme>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Different targets with different requirements
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]

[tool.hatch.build.targets.sdist]
include = [
    "src/myproject",
    "tests",
    "docs",
]

# Binary target needs everything
[tool.hatch.build.targets.binary]
dependencies = ["pyinstaller>=5.0"]
require-runtime-dependencies = true
require-runtime-features = ["database"]
```

## Combining with Target Dependencies

Runtime feature requirements can be combined with additional target dependencies:

```toml
[tool.hatch.build.targets.custom]
# Own dependencies plus runtime requirements
dependencies = [
    "my-builder-plugin>=2.0",
    "jinja2>=3.0",
]

# Include runtime dependencies
require-runtime-dependencies = true

# Include specific features
require-runtime-features = [
    "database",
    "cache",
]
```

Installation order:

1. Target's own `dependencies`
2. Project's base `dependencies` (if `require-runtime-dependencies = true`)
3. Specified optional features from `require-runtime-features`

## Practical Examples

### Example 1: Web Framework with Optional Plugins

```toml
[project]
name = "myframework"
dependencies = ["werkzeug>=2.0"]

[project.optional-dependencies]
sqlalchemy = ["sqlalchemy>=1.4"]
django = ["django>=3.0"]
flask = ["flask>=1.0"]

[tool.hatch.build.targets.wheel.hooks.custom]
# Hook needs to know about all features
require-runtime-dependencies = true
require-runtime-features = ["sqlalchemy", "django", "flask"]
```

### Example 2: Conditional Feature Installation

```toml
[project]
dependencies = ["base-package"]

[project.optional-dependencies]
linux-tools = ["linux-specific-tool ; sys_platform == 'linux'"]
windows-tools = ["windows-specific-tool ; sys_platform == 'win32'"]

[tool.hatch.build.targets.binary]
require-runtime-dependencies = true
# Platform-specific features are selected automatically
```

### Example 3: Documentation with Source Code Analysis

```toml
[project]
name = "mylib"
dependencies = ["numpy>=1.19", "scipy>=1.5"]

[project.optional-dependencies]
docs = ["sphinx", "sphinx-autodoc-typehints"]

[tool.hatch.build.targets.custom]
dependencies = ["sphinx>=4.0"]
require-runtime-dependencies = true
require-runtime-features = ["docs"]
```

The build will have numpy, scipy, sphinx, and sphinx-autodoc-typehints available.

## Edge Cases and Considerations

### Circular Dependencies

Avoid circular dependencies in runtime features:

```toml
# INCORRECT - creates circular dependency
[project.optional-dependencies]
build = ["my-build-tool"]  # Don't reference the package itself

[tool.hatch.build.targets.custom]
require-runtime-features = ["build"]
```

### Large Dependency Trees

For projects with many dependencies, consider impact:

```toml
# Be selective about which features to include
[tool.hatch.build.targets.wheel]
# Don't require all features
require-runtime-dependencies = false
require-runtime-features = ["core-plugins"]

[tool.hatch.build.targets.binary]
# Binary needs everything
require-runtime-dependencies = true
require-runtime-features = ["database", "cache", "plugins"]
```

### Version Conflicts

If target dependencies conflict with runtime dependencies:

```toml
[tool.hatch.build.targets.custom]
dependencies = [
    "tool>=2.0",  # Target requires version 2.0
]
require-runtime-dependencies = true
# If [project] dependencies requires "tool>=1.0,<2.0",
# this will cause a conflict during build environment setup
```

Solution: Use compatible version specifiers or create separate feature groups.

## Environment Variables

Control at build time:

```bash
# View what dependencies would be installed
hatch build --dry-run

# Clean rebuild with fresh environment
hatch build -c
```

## Troubleshooting

### Feature Not Found

<terminal_output>
ERROR: Feature 'nonexistent' not found in [project.optional-dependencies]
</terminal_output>

Ensure the feature name exactly matches a key in `[project.optional-dependencies]`.

### Dependency Conflicts During Build

```bash
# See detailed dependency resolution
hatch -v build
```

Check for version conflicts between:

- Target dependencies
- Runtime dependencies
- Feature dependencies
- Transitive dependencies

## Best Practices

1. **Be Explicit**: List specific features rather than using `require-runtime-dependencies = true` when possible
2. **Document Intent**: Add comments explaining why features are required
3. **Minimize Scope**: Include only necessary features for each target
4. **Version Compatibility**: Ensure target dependencies are compatible with runtime dependencies
5. **Test Build Environments**: Verify builds work in isolation before distributing

## See Also

- `target-dependencies.md` - Direct target dependencies
- `../build-hooks/hook-dependencies.md` - Dependencies for build hooks
- `../build-environment/build-dependencies-management.md` - Global build configuration
- `../build-targets/index.md` - Available build targets
