---
category: Build System Configuration
topics: [optional-dependencies, feature-dependencies, build-targets, dependency-selection]
related: [index.md, runtime-dependencies.md, target-dependencies.md]
---

# Optional Feature Requirements Configuration

Configure build targets to depend on specific optional features of the project.

## Overview

When helping users work with optional dependencies in Hatchling, reference this guide to explain the `require-runtime-features` option. This option allows build targets to access specific subsets of a project's optional dependencies without including everything.

**Source**: [Hatch Build Configuration - Target Dependencies](https://hatch.pypa.io/1.13/config/build/#target-dependencies)

## Configuration Syntax

```toml
[tool.hatch.build.targets.<TARGET>]
require-runtime-features = [
    "feature1",
    "feature2",
    "feature3",
]
```

## Relationship to Project Features

Features are defined in `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
database = ["sqlalchemy>=1.4.0"]
cache = ["redis>=3.5.0"]
monitoring = ["prometheus-client>=0.9.0"]
```

When a target specifies:

```toml
[tool.hatch.build.targets.binary]
require-runtime-features = ["database", "cache"]
```

The build environment receives:

- Base dependencies from `[project]` `dependencies` (if needed)
- All packages from `[project.optional-dependencies]` `database`
- All packages from `[project.optional-dependencies]` `cache`

## Common Use Cases

### Use Case 1: Selective Feature Installation for Hooks

Build hooks that analyze the codebase:

```toml
[project]
name = "myapp"
dependencies = ["click>=7.0"]

[project.optional-dependencies]
database = ["sqlalchemy>=1.4"]
cache = ["redis>=3.5"]

[tool.hatch.build.targets.wheel.hooks.custom]
# Hook can import and analyze database features
require-runtime-features = ["database"]
```

### Use Case 2: Binary Builds with Partial Features

```toml
[project]
dependencies = ["requests>=2.25"]

[project.optional-dependencies]
full = [
    "sqlalchemy>=1.4",
    "pytest>=6.0",
    "sphinx>=3.0",
]
development = [
    "black>=21.0",
    "mypy>=0.900",
]

[tool.hatch.build.targets.binary-lite]
# Lightweight binary with only runtime
require-runtime-features = []

[tool.hatch.build.targets.binary-full]
# Full binary with all features
require-runtime-features = ["full"]
```

### Use Case 3: Documentation Building

```toml
[project]
dependencies = ["dataclasses-json"]

[project.optional-dependencies]
docs = ["sphinx>=4.0", "sphinx-rtd-theme", "sphinx-autodoc-typehints"]
dev = ["pytest", "pytest-cov", "black"]

[tool.hatch.build.targets.custom]
dependencies = ["sphinx-build>=2.0"]
# Only need docs features, not dev tools
require-runtime-features = ["docs"]
```

## Multiple Feature Selection

Select multiple features to create a rich build environment:

```toml
[tool.hatch.build.targets.analysis]
require-runtime-features = [
    "database",
    "cache",
    "monitoring",
]
```

This installs:

- All base dependencies
- All packages from database feature
- All packages from cache feature
- All packages from monitoring feature

## Feature Examples from Real Projects

### Framework with Plugin System

```toml
[project]
name = "myplugins"
dependencies = ["pluggy>=1.0"]

[project.optional-dependencies]
sql = ["sqlalchemy>=1.4", "alembic>=1.6"]
http = ["aiohttp>=3.7", "httpx>=0.20"]
async = ["asyncio>=3.4.3"]
cache = ["cachetools>=4.2"]

[tool.hatch.build.targets.wheel]
# Standard wheel, no extra features

[tool.hatch.build.targets.wheel.hooks.custom]
# Hook generates plugin registry
require-runtime-features = ["sql", "http", "async", "cache"]
```

### Data Science Package

```toml
[project]
dependencies = ["numpy>=1.19", "pandas>=1.0"]

[project.optional-dependencies]
plotting = ["matplotlib>=3.0", "seaborn>=0.11"]
ml = ["scikit-learn>=0.24", "xgboost>=1.3"]
gpu = ["cupy>=8.0", "tensorflow>=2.5"]

[tool.hatch.build.targets.wheel]
# Standard wheel with just numpy and pandas

[tool.hatch.build.targets.conda-package]
# Conda package with all features
require-runtime-features = ["plotting", "ml", "gpu"]
```

## Combining with Other Options

### With Direct Target Dependencies

```toml
[tool.hatch.build.targets.custom]
# Own dependencies
dependencies = [
    "my-builder>=2.0",
    "jinja2>=3.0",
]

# Plus runtime features
require-runtime-features = [
    "database",
    "cache",
]
```

### With All Runtime Dependencies

Include all base dependencies plus specific features:

```toml
[tool.hatch.build.targets.binary]
# Include all base dependencies
require-runtime-dependencies = true

# Plus specific features
require-runtime-features = [
    "database",
    "monitoring",
]
```

Order of installation:

1. Base project dependencies (from `require-runtime-dependencies`)
2. Feature dependencies (from `require-runtime-features`)
3. Target's own dependencies

## Feature Dependency Specifications

Features can contain version specifiers:

```toml
[project.optional-dependencies]
database = [
    "sqlalchemy>=1.4.0,<2.0.0",
    "psycopg2-binary>=2.8",
    "mysql-connector-python[with-openssl]>=8.0",
]

monitoring = [
    "prometheus-client[asynchronous]>=0.9.0",
]
```

When a target requires these features, all version constraints are respected:

```toml
[tool.hatch.build.targets.custom]
require-runtime-features = ["database", "monitoring"]
```

## Platform-Specific Features

Features can include platform-specific dependencies:

```toml
[project.optional-dependencies]
windows-tools = [
    "windows-curses ; sys_platform == 'win32'",
    "pywin32 ; sys_platform == 'win32'",
]
linux-tools = [
    "fcntl ; sys_platform == 'linux'",
]

[tool.hatch.build.targets.native]
require-runtime-features = ["windows-tools", "linux-tools"]
```

The appropriate packages are installed based on the build platform.

## Practical Example: Full Project

```toml
[project]
name = "webservice"
version = "1.0.0"
description = "A web service with optional features"
requires-python = ">=3.8"

dependencies = [
    "flask>=2.0.0",
    "requests>=2.25.0",
]

[project.optional-dependencies]
database = [
    "sqlalchemy>=1.4.0",
    "psycopg2-binary>=2.8.0",
]
cache = [
    "redis>=3.5.0",
    "cachetools>=4.2.0",
]
monitoring = [
    "prometheus-client>=0.9.0",
    "python-json-logger>=2.0.0",
]
development = [
    "pytest>=6.0.0",
    "pytest-cov>=2.12.0",
    "black>=21.0.0",
    "mypy>=0.900",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Standard wheel - minimal dependencies
[tool.hatch.build.targets.wheel]
packages = ["src/webservice"]

# Docker image build - include database and monitoring
[tool.hatch.build.targets.custom]
dependencies = ["docker-package-builder>=1.0"]
require-runtime-dependencies = true
require-runtime-features = ["database", "cache", "monitoring"]

# Development environment - everything
[tool.hatch.build.targets.development]
require-runtime-dependencies = true
require-runtime-features = ["database", "cache", "monitoring", "development"]
```

## Troubleshooting

### Feature Not Found Error

<terminal_output>
ERROR: Feature 'nonexistent' not found
</terminal_output>

Check:

1. Feature name is spelled correctly
2. Feature is defined in `[project.optional-dependencies]`
3. No typos in `require-runtime-features` list

### Dependency Conflicts

If features have conflicting version requirements:

```toml
[project.optional-dependencies]
feature-a = ["package>=1.0,<2.0"]
feature-b = ["package>=2.0,<3.0"]

[tool.hatch.build.targets.custom]
require-runtime-features = ["feature-a", "feature-b"]  # CONFLICT!
```

Solution: Refactor features to have compatible constraints, or create separate targets.

### Empty Features

A feature with no packages is valid but has no effect:

```toml
[project.optional-dependencies]
empty = []

[tool.hatch.build.targets.custom]
require-runtime-features = ["empty"]  # No packages installed
```

## Best Practices

1. **Name Features Clearly**: Use descriptive names indicating what they're for

   - Good: `database`, `monitoring`, `testing`
   - Bad: `stuff`, `extra`, `things`

2. **Keep Features Focused**: Each feature should represent a cohesive set of functionality

   - Group related packages together
   - Avoid creating catch-all features

3. **Document Purpose**: Add comments explaining why targets require specific features

4. **Version Compatibility**: Ensure feature versions are compatible with base dependencies

5. **Test Builds**: Verify that your target builds successfully with required features

## See Also

- `runtime-dependencies.md` - Including all runtime dependencies
- `target-dependencies.md` - Direct target dependencies
- `../build-targets/index.md` - Available build targets
- `../build-hooks/hook-dependencies.md` - Hook-specific dependencies
