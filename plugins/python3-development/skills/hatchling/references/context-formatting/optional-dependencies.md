---
category: Context Formatting & Dependencies
topics: [optional-dependencies, context-formatting, monorepo, dynamic-dependencies, configuration-interpolation]
related: [README.md, global-fields.md, dynamic-configuration.md, configuration-interpolation.md]
---

# Context Formatting for Optional Dependencies

Reference documentation for context formatting in optional dependencies, available in Hatchling v1.2.0+. Use this to help users understand how to enable dynamic dependency resolution based on environment, platform, or other contextual factors.

## Overview

Optional dependencies (also called "extras") are groups of dependencies that are conditionally installed based on user choice. When assisting users, explain that context formatting allows:

- Reference project paths in optional dependency URLs
- Use environment variables as defaults or substitutes
- Create monorepo-friendly configurations
- Build platform-specific dependency chains

## Basic Configuration

### Defining Optional Dependencies with Context Formatting

Standard optional dependencies without context formatting:

```toml
[project.optional-dependencies]
dev = ["pytest", "pytest-cov"]
docs = ["sphinx", "sphinx-rtd-theme"]
```

With context formatting (Hatchling v1.2.0+):

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "local-plugin @ {root}/plugins/pytest-plugin",
]
docs = [
    "sphinx",
    "sphinx-rtd-theme",
    "custom-docs @ {root}/docs/extensions",
]
```

## Supported Context Fields in Optional Dependencies

### Global Fields

All globally available context formatting fields work in optional dependencies:

#### Path Fields

**root** — Project root directory:

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root}/vendor/pkg",
]
```

**home** — User home directory:

```toml
[project.optional-dependencies]
local = [
    "pkg @ {home}/.local/packages/pkg",
]
```

#### Path Modifiers

**uri** — Convert to file URI:

```toml
[project.optional-dependencies]
dev = [
    "pkg-a @ {root:uri}/packages/pkg-a",
    "pkg-b @ {root:parent:uri}/sibling",
]
```

**real** — Resolve symbolic links:

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root:real}/vendor",
]
```

**parent** — Navigate parent directories:

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root:parent}/sibling-project",
    "other @ {root:parent:parent}/vendor",
]
```

#### Environment Variables

**env** — Access environment variables:

```toml
[project.optional-dependencies]
enterprise = [
    "pkg @ {env:ENTERPRISE_REPO_URL:https://default.repo/packages}",
]
```

With defaults (recommended):

```toml
[project.optional-dependencies]
custom = [
    "pkg @ {env:CUSTOM_PKG_URL:file:///opt/packages}",
    "private @ {env:PRIVATE_INDEX:https://pypi.org/simple}",
]
```

## Practical Patterns

### Monorepo Local Packages

Organize optional groups for different consumer types:

```toml
[project.optional-dependencies]
# Development includes all local packages
dev = [
    "pytest",
    "pytest-cov",
    "core @ {root}/packages/core",
    "utils @ {root}/packages/utils",
    "plugins @ {root}/packages/plugins",
]

# Documentation includes doc tools and documentation packages
docs = [
    "sphinx",
    "sphinx-rtd-theme",
    "api-docs @ {root}/packages/api-docs",
]

# Testing includes test tools and test utilities
test = [
    "pytest",
    "pytest-mock",
    "test-utils @ {root}/packages/test-utils",
]
```

Install specific extras:

```bash
# Install with all development dependencies
pip install -e .[dev]

# Install only documentation dependencies
pip install -e .[docs]

# Install test dependencies
pip install -e .[test]

# Install multiple optional groups
pip install -e .[dev,docs]
```

### Cross-Monorepo References

For monorepos with multiple root projects:

```toml
[project.optional-dependencies]
integration = [
    "service-a @ {root:parent}/service-a",
    "service-b @ {root:parent}/service-b",
    "shared @ {root:parent:parent}/shared-libs",
]
```

This structure assumes:

<eg>
projects/
├── service-a/
├── service-b/
└── main-project/
    └── pyproject.toml
</eg>

### Environment-Based Optional Dependencies

Use environment variables to select different dependency sources:

```toml
[project.optional-dependencies]
# Production dependencies
prod = [
    "gunicorn",
    "psycopg2-binary",
]

# Development dependencies with optional local builds
dev = [
    "pytest",
    "pytest-cov",
    "db-client @ {env:DB_CLIENT_PATH:{root}/tools/db-client}",
    "debugger @ {env:DEBUGGER_PATH:{root}/tools/debugger}",
]

# CI/CD environment with specific tools
ci = [
    "coverage",
    "pytest",
    "build",
    "twine @ {env:TWINE_OVERRIDE:https://pypi.org/simple}",
]
```

### Platform or Distribution-Specific Extras

```toml
[project.optional-dependencies]
# All platforms get these
core = [
    "requests",
    "ruamel.yaml",
]

# Add platform-specific packages (with context)
windows = [
    "pywin32",
    "win-inet-pton",
    "windows-curses @ {env:WIN_CURSES_PATH:{root}/vendor/windows-curses}",
]

linux = [
    "dbus-python",
    "systemd",
    "linux-tools @ {root}/tools/linux",
]
```

## Context Formatting Constraints

### Restrictions

- **Version specifiers**: Context formatting works in dependency URLs but not in version constraints

**Invalid:**

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {env:VERSION}",  # Wrong: can't interpolate version directly
]
```

**Valid:**

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root}/build-outputs/pkg-1.0.0",  # Path interpolation works
    "pkg=={env:PKG_VERSION}",  # Version constraint without URL works
]
```

- **Dynamic field requirement**: If you use context formatting in optional dependencies, you may need to declare them as dynamic

**When to declare dynamic:**

If you're using environment variables that may not be set during static configuration reading:

```toml
[project]
name = "myproject"
dynamic = ["optional-dependencies"]
```

Then implement a metadata hook to handle the dynamic resolution.

## Using Optional Dependencies with Environment Overrides

Hatch environments can select specific optional dependency groups:

```toml
[tool.hatch.envs.test]
features = ["test"]

[tool.hatch.envs.dev]
features = ["dev"]

[tool.hatch.envs.docs]
features = ["docs"]
```

This installs the corresponding optional dependencies for each environment.

## Combining with Hatch Environment Dependencies

Hatch environment dependencies also support context formatting:

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "local-plugin @ {root}/plugins/pytest",
]

[tool.hatch.envs.test]
features = ["dev"]
dependencies = [
    "additional-tool @ {root}/tools/extra",
]
```

This allows:

- `[project.optional-dependencies]` — For installable package extras
- `[tool.hatch.envs.<ENV>.dependencies]` — For environment-specific development tools

## Error Handling

### Missing Context During Build

If a context field references a missing environment variable without a default, the build will fail:

<eg>
ConfigError: Environment variable 'ENTERPRISE_REPO_URL' not set and no default provided
</eg>

**Solution**: Always provide defaults for optional environment variables:

```toml
[project.optional-dependencies]
enterprise = [
    "pkg @ {env:ENTERPRISE_REPO_URL:https://default.pypi/simple}",
]
```

### Circular Dependencies

Avoid circular references when using relative path context formatting:

**Problematic:**

```toml
# In main-project/pyproject.toml
[project.optional-dependencies]
sibling = [
    "pkg @ {root:parent}/sibling",
]

# In sibling/pyproject.toml (if it references back)
[project.optional-dependencies]
main = [
    "pkg @ {root:parent}/main-project",
]
```

### Verification

Verify optional dependencies resolve correctly:

```bash
# List resolved dependencies
pip index versions "pkg @ {root:parent}/sibling"

# Install and check
pip install -e .[optional-group] --dry-run
```

## Hatchling v1.2.0+ Enhancements

**Release**: Hatchling v1.2.0 (January 2024)

**Feature**: "Allow context formatting for `project.dependencies` and `project.optional-dependencies`"

This enabled:

- Dynamic dependency URLs using context fields
- Monorepo-friendly configurations
- Environment-aware optional dependency selection
- Build-time variable interpolation in optional groups

## Migration from Hardcoded Paths

**Before (Hatchling < v1.2.0):**

```toml
[project.optional-dependencies]
dev = [
    "pkg @ file:///home/user/projects/monorepo/packages/pkg",
]
```

**After (Hatchling v1.2.0+):**

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root}/packages/pkg",
]
```

Benefits:

- No hardcoded absolute paths
- Works across different machines
- Relocatable monorepos
- CI/CD friendly

## Related Topics

- `global-fields.md` — Available context fields and modifiers
- `environment-fields.md` — Fields for Hatch environments
- `dynamic-configuration.md` — Programmatic metadata setup
- `configuration-interpolation.md` — Advanced field nesting
