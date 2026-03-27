---
category: Advanced Configuration Patterns
topics: [configuration-interpolation, field-nesting, modifier-chaining, advanced-patterns, context-formatting]
related: [README.md, global-fields.md, environment-fields.md, optional-dependencies.md]
---

# Configuration Interpolation and Advanced Patterns

Reference documentation for advanced configuration interpolation patterns in Hatchling. Use this to help users understand how to use context formatting to dynamically compute or substitute values in configuration.

## Overview

When assisting users with advanced configuration, explain that interpolation extends basic context formatting by:

- **Nesting fields** for fallback chains
- **Combining modifiers** for complex path manipulation
- **Chaining lookups** across multiple sources
- **Building dynamic paths** for platform-independent configuration

## Field Nesting and Fallback Chains

### Basic Nesting

Fields can be nested to create fallback chains where evaluation proceeds left-to-right:

```toml
{field1:{field2:{field3:default}}}
```

### Environment Variable Chain Example

Scenario: Try multiple environment variables with a final fallback:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest --config={env:TEST_CONFIG:{env:HATCH_CONFIG:{root}/pytest.ini}}"
```

Evaluation order:

1. Check `TEST_CONFIG` environment variable
2. If not set, check `HATCH_CONFIG` environment variable
3. If neither is set, use `{root}/pytest.ini`

### Path Preference Chain

Scenario: Check for a tool in multiple locations:

```toml
[tool.hatch.envs.lint.scripts]
check = "flake8 --exclude={env:FLAKE8_EXCLUDE:{root}/.flake8-excludes}"
```

With further nesting:

```toml
[tool.hatch.envs.lint.scripts]
setup = "flake8 --config={env:FLAKE8_CONFIG:{root}/.flake8:{home}/.flake8:default}"
```

This attempts three locations before using "default".

## Modifier Chaining

### Path Modifier Combinations

Path modifiers can be chained for complex path transformations:

```toml
{root:parent:parent:uri}
```

Evaluation:

1. Start with `{root}` — Project root
2. Apply `parent` — Go up one level
3. Apply `parent` — Go up another level
4. Apply `uri` — Convert to file:// URI

**Result**: A file URI pointing two levels above the project root.

### Real and Parent Combination

Follow symlinks while traversing:

```toml
{root:real:parent:uri}
```

This resolves symlinks first, then navigates to the parent.

### Multiple URI Conversions

While unusual, some configurations need the uri modifier applied:

```toml
# Standard file reference URI
"pkg @ {root:parent:uri}/packages/pkg"

# With real (follow symlinks)
"pkg @ {root:parent:real:uri}/packages/pkg"
```

## Environment-Specific Configuration

### Platform-Specific Paths

Build platform-aware paths using separator fields:

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {root}{/}vendor{/}pkg",
]
```

This expands to:

- Unix: `{root}/vendor/pkg`
- Windows: `{root}\vendor\pkg`

### PATH-like Environment Variables

Build colon/semicolon-separated variable lists:

```toml
[tool.hatch.envs.default.env-vars]
PYTHONPATH = "{root}{/}src{;}{root}{/}lib{;}{env:ADDITIONAL_PATHS:}"
```

Expands to:

- Unix: `/project/src:/project/lib:$ADDITIONAL_PATHS`
- Windows: `C:\project\src;C:\project\lib;%ADDITIONAL_PATHS%`

### Conditional Directory Selection

Use environment variables to select between configurations:

```toml
[tool.hatch.envs.test]
dependencies = [
    "config @ {env:CONFIG_TYPE:{root}/config/default}",
]
```

Users can override:

```bash
export CONFIG_TYPE=/opt/custom-config
hatch run test
```

## Environment Variable Patterns

### Required vs Optional Variables

**Required** (fails if not set):

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {env:REQUIRED_URL}",
]
```

**Optional** (uses default if not set):

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {env:OPTIONAL_VAR:https://default.repo}",
]
```

### Variable Precedence Chains

Implement fallback priority:

```toml
[tool.hatch.envs.deploy.env-vars]
DB_URL = "{env:PROD_DB_URL:{env:DEV_DB_URL:{env:LOCAL_DB_URL:sqlite:///./app.db}}}"
API_KEY = "{env:API_KEY_OVERRIDE:{env:DEFAULT_API_KEY:}}"
```

This allows:

- Override with `PROD_DB_URL`
- Fall back to `DEV_DB_URL`
- Fall back to `LOCAL_DB_URL`
- Finally fall back to SQLite

### Secret Management Pattern

Reference secrets from environment while providing safe defaults for development:

```toml
[tool.hatch.envs.dev.env-vars]
DATABASE_URL = "{env:DATABASE_URL:postgresql://user:password@localhost/mydb}"
SECRET_KEY = "{env:SECRET_KEY:dev-insecure-key-only-for-testing}"
API_TOKEN = "{env:API_TOKEN:test-token-123}"

[tool.hatch.envs.prod.env-vars]
DATABASE_URL = "{env:DATABASE_URL}"
SECRET_KEY = "{env:SECRET_KEY}"
API_TOKEN = "{env:API_TOKEN}"
```

In production, environment variables must be set. In development, safe defaults work.

## Monorepo Patterns

### Sibling Package References

Reference packages at the same level in the monorepo:

```toml
[project.optional-dependencies]
all = [
    "core @ {root:parent}/core",
    "utils @ {root:parent}/utils",
    "plugins @ {root:parent}/plugins",
    "docs @ {root:parent}/docs",
]
```

### Vendor Directory References

Reference vendored dependencies:

```toml
[project.dependencies]
vendored-lib = "lib @ {root}/vendor/lib"

[project.optional-dependencies]
extra = [
    "vendored-tool @ {root}/vendor/tools",
]
```

### Multi-Level Monorepo

For deeply nested monorepos:

```toml
[tool.hatch.envs.test]
dependencies = [
    "shared @ {root:parent:parent}/shared",
    "services @ {root:parent}/service-libs",
    "local @ {root}/vendor",
]
```

Project structure:

<eg>
monorepo/
├── shared/
├── services/
│   ├── service-libs/
│   ├── service-a/
│   └── service-b/
│       └── pyproject.toml (this is {root})
└── vendor/
</eg>

## Script and Command Interpolation

### Verbosity-Aware Commands

Commands that adapt to user verbosity:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest tests/ {verbosity:flag}"
build = "python build.py {verbosity:flag:-1}"
verbose-build = "python build.py {verbosity:flag:1}"
```

### Environment-Aware Script Paths

Scripts that reference different tools by environment:

```toml
[tool.hatch.envs.test.scripts]
test = "pytest -c {root}/config/pytest_{env_name}.ini {args}"

[tool.hatch.envs.lint.scripts]
check = "ruff check --config={root}/config/ruff_{env_type}.toml"
```

### Matrix-Based Test Commands

Tests that change based on matrix variables:

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.8", "3.9", "3.10"]
django = ["3.2", "4.0"]

[tool.hatch.envs.test.scripts]
test = "pytest tests/django_{matrix:django:latest}/ -v"
report = "coverage report > {root}/coverage/py{matrix:python}.txt"
```

## Error Prevention Patterns

### Always Provide Defaults for Optional Values

**Bad** (will fail if variable not set):

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {env:PACKAGE_URL}",
]
```

**Good** (graceful fallback):

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {env:PACKAGE_URL:https://pypi.org/simple/}",
]
```

### Validate Path Existence

When using environment variables for paths, consider validation:

```python
# hooks/metadata.py
import os
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class ValidatingMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        # Get path with fallback
        pkg_path = os.getenv("PACKAGE_PATH", str(Path(self.root) / "packages"))

        # Validate
        if not Path(pkg_path).exists():
            raise ValueError(f"Package path does not exist: {pkg_path}")

        metadata["dependencies"] = [
            f"pkg @ {pkg_path}/pkg",
        ]
```

### Use Relative Paths Over Absolute

**Avoid absolute paths:**

```toml
# Bad: Hardcoded absolute path
[project.optional-dependencies]
dev = [
    "pkg @ file:///home/user/projects/monorepo/pkg",
]
```

**Use context formatting:**

```toml
# Good: Portable relative path
[project.optional-dependencies]
dev = [
    "pkg @ {root:parent}/pkg",
]
```

## Performance Considerations

### Lazy Evaluation

Context formatting fields are evaluated:

- During build time (static configuration)
- During install time (dynamic values)
- During environment creation (Hatch environments)

### Caching

Environment variable values are read once during configuration parsing. Changing environment variables during a Hatch session may not take effect until the next session.

### Path Resolution

Path operations (`parent`, `real`) are computed during configuration parsing. Changes to the filesystem after configuration load won't be reflected until next configuration parse.

## Debugging Interpolation

### Print Resolved Values

Add debug scripts to see interpolated values:

```toml
[tool.hatch.envs.test.scripts]
debug = "echo 'Root: {root}' && echo 'Home: {home}' && echo 'Config: {env:TEST_CONFIG:default}'"
```

Run to see resolved values:

```bash
hatch run test:debug
```

### Inspect Environment Variables

Script to view all relevant environment variables:

```toml
[tool.hatch.envs.default.scripts]
debug-env = """
echo "Environment Variables:"
echo "TEST_CONFIG=${{TEST_CONFIG}}"
echo "HATCH_CONFIG=${{HATCH_CONFIG}}"
echo "PATH=$PATH"
"""
```

## Common Pitfalls

### Mixing Context Formatting with f-strings

**Don't do this in pyproject.toml:**

```toml
# Wrong! f-strings don't work in TOML
[tool.hatch.envs.test.scripts]
test = f"pytest {root}/tests"
```

**Use context formatting syntax:**

```toml
# Correct
[tool.hatch.envs.test.scripts]
test = "pytest {root}/tests"
```

### Escaping in Nested Fields

When using nested context formatting, the inner format is literal:

```toml
# This is correct
display = "echo {env:FOO:{env:BAR:{home}}}"

# This is wrong (double braces don't work as escape)
display = "echo {{env:FOO}}"
```

### Version Constraints in Interpolated URLs

**Don't try to interpolate versions directly:**

```toml
# Wrong: Version in URL
[project.optional-dependencies]
dev = [
    "pkg @ {root}/pkg-{env:PKG_VERSION}",
]
```

**Use static constraints instead:**

```toml
# Better: Path only, version as constraint
[project]
dependencies = [
    'pkg @ {root}/pkg; version="{env:PKG_VERSION:1.0}"'
]
```

Or simpler:

```toml
[project.optional-dependencies]
dev = [
    "pkg @ {root}/pkg",  # Version defined elsewhere
]
```

## Related Topics

- `global-fields.md` — Available fields and modifiers
- `environment-fields.md` — Environment name, matrix, verbosity
- `optional-dependencies.md` — Context formatting in extras
- `dynamic-configuration.md` — Programmatic metadata hooks
