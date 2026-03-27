---
category: Context Formatting & Dynamic Configuration
topics: [context-formatting, dynamic-fields, configuration-interpolation, dependencies, metadata-hooks, monorepo]
related: [global-fields.md, environment-fields.md, optional-dependencies.md, dynamic-configuration.md, configuration-interpolation.md]
---

# Context Formatting & Dynamic Configuration in Hatchling

Reference documentation for context formatting and dynamic configuration in Hatchling, the PyPA build backend powering Hatch. Use this to help users understand how to populate Hatchling configuration with dynamic values using Python's format string syntax.

## Overview

When assisting users with Hatchling configuration, reference context formatting capabilities for:

- **Dynamic dependency resolution** — Help users reference local packages using relative paths
- **Environment-aware configuration** — Guide users in setting different configurations based on environment variables
- **Monorepo support** — Advise on portable references to sibling packages
- **Cross-platform paths** — Show how to automatically handle Windows vs Unix differences
- **Metadata hooks** — Explain programmatic project information setup at build time

## Key Concepts

### Understanding Context Formatting

Context formatting enables placeholders like `{root}`, `{env:VAR}`, or `{home}` in configuration values. These placeholders are replaced with actual values during build time. Help users understand that:

```toml
[project.optional-dependencies]
dev = [
    "local-pkg @ {root}/packages/local-pkg",
]
```

The `{root}` placeholder is replaced with the project's root directory path at build time.

### Understanding Dynamic Configuration

Dynamic configuration refers to setting metadata fields programmatically at build time instead of hardcoding them in `pyproject.toml`. When assisting users, explain that this combined with context formatting enables flexible project setup:

```toml
[project]
dynamic = ["version", "dependencies"]
```

Users then implement a metadata hook to set these values based on external sources or computation.

## Documentation Structure

### `global-fields.md`

Core fields available everywhere in Hatchling configuration:

- **Path fields**: `root`, `home`
- **Path modifiers**: `uri` (convert to file:// URI), `real` (resolve symlinks), `parent` (navigate up)
- **System separators**: `{/}`, `{;}` (platform-specific path/PATH separators)
- **Environment variables**: `{env:VAR}` or `{env:VAR:default}`

**Reference this to help users with**: Any configuration that needs filesystem paths or environment variables.

### `environment-fields.md`

Fields available in Hatch environment configurations. Reference this when helping users with:

- **Environment metadata**: `env_name`, `env_type`
- **Matrix variables**: `{matrix:VARIABLE}` with optional defaults
- **Verbosity**: `{verbosity}` with `flag` modifier for CLI-style flags

**Use to assist with**: `[tool.hatch.envs.<ENV>]` scripts, dependencies, and environment variables.

### `optional-dependencies.md`

Using context formatting in optional dependency groups (Hatchling v1.2.0+). Guide users through:

- Monorepo package references
- Environment-based dependency selection
- Cross-repository references
- Platform or distribution-specific extras

**Reference this when helping users with**: Defining `[project.optional-dependencies]` with local or computed URLs.

### `dynamic-configuration.md`

Programmatically setting project metadata. Help users understand:

- Version from files, git, or APIs
- Authors and license from external sources
- Dependencies computed at build time
- Metadata hooks (custom Python code)

**Use when users need to**: Set metadata from external sources or computed at build time.

### `configuration-interpolation.md`

Advanced techniques for complex configurations. Reference this to guide users through:

- Field nesting for fallback chains
- Modifier chaining for path manipulation
- Environment variable precedence
- Monorepo patterns
- Error prevention

**Use to assist with**: Complex setups requiring flexible, environment-aware configuration.

## Quick Start Examples

### Example 1: Monorepo with Local Packages

Reference local packages in a monorepo:

```toml
[project.optional-dependencies]
dev = [
    "core @ {root}/packages/core",
    "utils @ {root}/packages/utils",
]
```

**Requirements**: Hatchling v1.2.0+

**Resolves to**:

<eg>
core @ /home/user/projects/monorepo/packages/core
utils @ /home/user/projects/monorepo/packages/utils
</eg>

### Example 2: Environment-Aware Dependencies

Use different dependencies based on environment variables:

```toml
[project.optional-dependencies]
database = [
    "psycopg2 @ {env:POSTGRES_DRIVER_URL:https://pypi.org/simple}",
]
```

Set at install time:

```bash
export POSTGRES_DRIVER_URL=https://custom.repo/packages
pip install -e .[database]
```

### Example 3: Dynamic Version from File

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/myproject/__init__.py"
```

Or using a metadata hook:

```python
# hatch_build.py
from hatchling.metadata.plugin.interface import MetadataHookInterface
from pathlib import Path

class VersionHook(MetadataHookInterface):
    def update(self, metadata):
        version_file = Path(self.root) / "VERSION"
        metadata["version"] = version_file.read_text().strip()
```

### Example 4: Fallback Chain for Configuration

Try multiple sources with fallbacks:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest --config={env:PYTEST_CONFIG:{root}/pytest.ini}"
```

Or deeper chains:

```toml
[tool.hatch.envs.default.env-vars]
DB_URL = "{env:PROD_DB:{env:DEV_DB:{env:LOCAL_DB:sqlite:///app.db}}}"
```

### Example 5: Cross-Platform Paths in Scripts

```toml
[tool.hatch.envs.test.scripts]
find = "find {root}{/}src -name '*.py'"
test = "pytest {root}{/}tests"
```

Expands to:

<eg>
- **Unix**: `find /project/src -name '*.py'`
- **Windows**: `find C:\project\src -name '*.py'`
</eg>

## Hatchling Version Support

### Hatchling v1.2.0 (January 2024)

Major feature release:

- Context formatting for `project.dependencies` (NEW)
- Context formatting for `project.optional-dependencies` (NEW)

### Hatchling v1.3.0 (February 2024)

Improvements:

- Improved error messages for missing `env` context fields
- Fixed `uri` context formatting on Windows (proper drive letter handling)
- Fixed space escaping in URI paths

### Hatchling 1.1.0 (November 2023)

Initial release:

- Global context formatting fields
- Path modifiers (`uri`, `real`, `parent`)
- Environment variable interpolation

## Common Scenarios

### Scenario 1: Local Development with Linked Packages

Working on a monorepo during development:

```toml
[project.optional-dependencies]
dev = [
    "core @ {root}/packages/core",
    "plugins @ {root}/packages/plugins",
    "test-fixtures @ {root}/test-fixtures",
]
```

Install and work with local versions:

```bash
pip install -e .[dev]
```

### Scenario 2: CI/CD with Different Repositories

Different dependency sources in different environments:

```toml
[project.optional-dependencies]
enterprise = [
    "auth @ {env:ENTERPRISE_REPO}",
]

[tool.hatch.envs.ci]
features = ["enterprise"]
env-vars = { ENTERPRISE_REPO = "https://enterprise.repo/packages" }

[tool.hatch.envs.local]
features = ["dev"]
env-vars = { ENTERPRISE_REPO = "{root}/vendor/auth" }
```

### Scenario 3: Platform-Specific Optional Dependencies

Different dependencies per platform:

```toml
[project.optional-dependencies]
gui = ["pyqt6"]
gui-windows = ["pywin32"]
gui-linux = ["dbus-python"]
```

Or using context formatting for file paths:

```toml
[project.optional-dependencies]
tools = [
    "windows-tools @ {env:WIN_TOOLS_PATH:{root}/tools/windows}",
]
```

### Scenario 4: Single Source of Truth for Metadata

All metadata from one JSON file:

```python
# hatch_build.py
import json
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class MetadataHook(MetadataHookInterface):
    def update(self, metadata):
        with open(Path(self.root) / "metadata.json") as f:
            info = json.load(f)

        metadata["version"] = info["version"]
        metadata["authors"] = info["authors"]
        metadata["license"] = {"text": info["license"]}
        metadata["urls"] = info["urls"]
```

## Best Practices

When assisting users, reference these patterns:

### 1. Always Provide Defaults for Environment Variables

Guide users to provide defaults to prevent build failures:

```toml
# Avoid (fails if variable not set)
[project.optional-dependencies]
dev = ["pkg @ {env:PACKAGE_URL}"]

# Recommended (graceful fallback)
[project.optional-dependencies]
dev = ["pkg @ {env:PACKAGE_URL:https://pypi.org/simple}"]
```

### 2. Use Relative Paths Over Absolute Paths

Advise users to use context formatting for portability:

```toml
# Avoid (hardcoded absolute path)
dev = ["pkg @ file:///home/user/projects/pkg"]

# Recommended (portable relative path)
dev = ["pkg @ {root:parent}/pkg"]
```

### 3. Prefer Built-in Version Sources

When helping users with versioning, recommend built-in sources first:

```toml
# For version specifically, use built-in sources first
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/myproject/__init__.py"
```

Advise users to use custom metadata hooks only for complex version logic.

### 4. Document Dynamic Fields and Requirements

Help users maintain clarity about which fields are dynamic:

```toml
[project]
# Fields set dynamically by hooks/metadata.py
dynamic = ["version", "license", "authors"]
```

And in `hatch_build.py`:

```python
class MyHook(MetadataHookInterface):
    """
    Sets version, license, authors from metadata.json.
    Requires metadata.json to exist in project root.
    """
```

### 5. Keep Monorepo References Consistent

Guide users to use consistent patterns for monorepo layouts:

<eg>
monorepo/
├── core/
├── utils/
└── app/
    └── pyproject.toml
</eg>

Show users to apply consistent patterns:

```toml
[project.optional-dependencies]
all = [
    "core @ {root:parent}/core",
    "utils @ {root:parent}/utils",
]
```

### 6. Test Dynamic Configuration

Advise users to test dynamic metadata resolution:

```bash
# Test that metadata resolves correctly
pip install --dry-run -e .

# List dynamic fields that were resolved
hatch env show
```

## Common Issues & Solutions

Use these patterns when helping users troubleshoot context formatting issues:

### Issue: "Environment variable not set" error

**Root cause**: A context field references an environment variable that doesn't exist and no default was provided.

**Guide users to add a default**:

```toml
# Problematic (fails if variable not set)
[project.optional-dependencies]
dev = ["pkg @ {env:PACKAGE_URL}"]

# Recommended (provides fallback)
[project.optional-dependencies]
dev = ["pkg @ {env:PACKAGE_URL:https://pypi.org/simple}"]
```

### Issue: "Field defined both statically and dynamically"

**Root cause**: A field is defined in both static config and in the `dynamic` array.

**Advise users to remove the static definition**:

```toml
[project]
# name = "myproject"  # Remove this line
dynamic = ["version"]  # version is now dynamic

# Define version in hook instead
```

### Issue: Windows paths with backslashes not working

**Root cause**: Using `\` directly in TOML strings requires escaping.

**Guide users to use context formatting path fields**:

```toml
# Problematic (unescaped backslashes)
[project.optional-dependencies]
dev = ["pkg @ C:\projects\pkg"]  # Fails!

# Recommended (use context formatting)
[project.optional-dependencies]
dev = ["pkg @ {root:parent}{/}sibling"]  # {/} handles Windows automatically
```

## Related Documentation

When assisting users, reference these authoritative sources:

- **[Hatch Documentation](https://hatch.pypa.io/)** — Official Hatch project manager reference
- **[Hatchling Documentation](https://hatch.pypa.io/latest/)** — Build backend specification
- **[PEP 621](https://peps.python.org/pep-0621/)** — Project metadata standard
- **[PEP 508](https://peps.python.org/pep-0508/)** — Dependency specification format

## File Structure

<eg>
context-formatting/
├── README.md                           # This file
├── global-fields.md                    # root, home, env fields
├── environment-fields.md               # env_name, matrix, verbosity
├── optional-dependencies.md            # Using context formatting in extras
├── dynamic-configuration.md            # Metadata hooks and dynamic fields
└── configuration-interpolation.md      # Advanced patterns and nesting
</eg>

## Information Sources

These references are based on the Hatch project and official Hatchling documentation:

- **GitHub Repository**: <https://github.com/pypa/hatch>
- **Issue Tracker**: <https://github.com/pypa/hatch/issues>
- **Discussions**: <https://github.com/pypa/hatch/discussions>
- **Release Notes**: Check `/docs/history/` in the Hatch repo for latest features

## License

These references are based on the Hatch project, which is licensed under MIT.

---

**Last Updated**: 2024-11 **Hatchling Versions Covered**: 1.1.0 - 1.22.x **Format**: Markdown, targeting Hatch v1.2.0+ for modern context formatting support **Audience**: Claude AI assistants helping users with Hatchling configuration
