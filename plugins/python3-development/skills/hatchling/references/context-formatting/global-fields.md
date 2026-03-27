---
category: Context Formatting Fields
topics: [global-fields, path-fields, environment-variables, configuration-interpolation, hatchling]
related: [README.md, environment-fields.md, optional-dependencies.md, configuration-interpolation.md]
---

# Global Context Formatting Fields

Reference documentation for globally available context formatting fields in Hatchling. Use this to help users understand how to dynamically populate configuration values using Python's format string syntax.

## Overview

When assisting users, explain that context formatting enables placeholders with the syntax `{field:modifier:default}` in configuration. Each field interprets the modifier part after the colon differently based on its semantics.

## Global Fields

### Path Fields

All path fields support three standard modifiers that control how the path is represented and resolved.

#### root

- **What it represents**: The project's root directory (where `pyproject.toml` or `hatch.toml` is located)
- **Type**: Path
- **Modifiers**: `uri`, `real`, `parent`
- **Default behavior**: Returns the filesystem path

**Show users these examples:**

```toml
[project]
dependencies = [
    "example-project @ {root}/src",
]
```

```toml
[tool.hatch.envs.test]
dependencies = [
    "local-pkg @ {root:uri}/packages/local",
]
```

#### home

- **What it represents**: The user's home directory
- **Type**: Path
- **Modifiers**: `uri`, `real`, `parent`
- **Default behavior**: Returns the filesystem path

**Show users these examples:**

```toml
[tool.hatch.envs.test.scripts]
display = "echo {home}"
```

```toml
[tool.hatch.envs.test]
dependencies = [
    "custom-tools @ {home:uri}/.local/tools",
]
```

## Path Modifiers

### uri

- **What it does**: Converts a path to a normalized absolute URI with the `file:` scheme prefix
- **When to use**: When a dependency or configuration requires a file URI (e.g., direct file references in dependencies)
- **Platform handling**: Automatically handles Windows drive letters (e.g., `C:/` becomes `file:///c:/`)
- **Space handling**: Properly escapes spaces in paths for URI validity

**Show users these examples:**

```toml
[tool.hatch.envs.test]
dependencies = [
    "example @ {root:parent:parent:uri}/example-project",
]
```

This produces (on Unix):

<eg>
example @ file:///home/user/projects/example-project
</eg>

On Windows:

<eg>
example @ file:///C:/Users/user/projects/example-project
</eg>

### real

- **What it does**: Resolves all symbolic links in the path and returns the canonical filesystem path
- **When to use**: When users need to follow symlinks to ensure consistent paths across symlink-heavy environments
- **Platform handling**: Works on all platforms with symbolic link support

**Show users this example:**

```toml
[tool.hatch.envs.default]
dependencies = [
    "pkg @ {root:real}/vendor",
]
```

### parent

- **What it does**: References the parent directory of the preceding path
- **Chainable**: Can be used multiple times in succession to traverse upward
- **Combination**: Can be combined with `uri` or `real` (with `uri`/`real` placed last)

**Show users these examples:**

Single parent traversal:

```toml
[tool.hatch.envs.test]
dependencies = [
    "sibling-pkg @ {root:parent}/sibling-project",
]
```

Multiple parent traversals (go up two levels):

```toml
[tool.hatch.envs.test]
dependencies = [
    "example-project @ {root:parent:parent:uri}/example-project",
]
```

Combined with `uri` modifier:

```toml
[tool.hatch.envs.test]
dependencies = [
    "pkg @ {root:parent:real:uri}/packages",
]
```

## System Separators

Platform-specific values for use in paths and PATH-like environment variables. Help users write platform-independent configurations:

### Forward Slash

- **Notation**: `{/}`
- **Windows**: Expands to `\` (backslash)
- **Unix-like**: Expands to `/` (forward slash)

**When to use**: Building platform-independent path strings in scripts or configuration

**Show users this example:**

```toml
[tool.hatch.envs.test.scripts]
find-files = "find {root}{/}src -name '*.py'"
```

### Path Separator

- **Notation**: `{;}`
- **Windows**: Expands to `;` (semicolon)
- **Unix-like**: Expands to `:` (colon)

**When to use**: Building PATH or other colon/semicolon-separated environment variables

**Show users this example:**

```toml
[tool.hatch.envs.default.env-vars]
PYTHONPATH = "{root}/src{;}~/.local/lib"
```

## Environment Variables

The `env` field allows users to access environment variables within configuration.

### env

- **What it does**: Retrieves the value of an environment variable
- **Syntax**: `{env:VARIABLE_NAME}` or `{env:VARIABLE_NAME:DEFAULT_VALUE}`
- **Important note**: If the variable is not set and no default is provided, configuration parsing will fail

**Show users these examples:**

Without default (fails if variable not set):

```toml
[tool.hatch.envs.test]
dependencies = [
    "custom @ {env:PACKAGE_URL}",
]
```

With default (graceful fallback):

```toml
[tool.hatch.envs.test]
dependencies = [
    "custom @ {env:PACKAGE_URL:https://pypi.org/simple/}",
]
```

## Field Nesting

Fields can be nested to create fallback chains. Explain to users that evaluation proceeds left-to-right, using the first non-empty value.

**Syntax**: `{field1:{field2:{field3:default}}}`

**Show users this example:**

```toml
[tool.hatch.envs.test.scripts]
display = "echo {env:FOO:{env:BAR:{home}}}"
```

This evaluates:

1. Check if `FOO` environment variable is set; use its value
2. If not, check if `BAR` environment variable is set; use its value
3. If neither is set, use the `{home}` path

**Use cases to explain to users:**

- Graceful degradation across multiple configuration sources
- Supporting environment-specific overrides with sensible defaults
- Backward compatibility when switching configuration strategies

## Error Handling

### Invalid References

- **What happens**: If a referenced field or modifier is invalid, configuration parsing fails with a descriptive error message
- **Common invalid patterns**:
  - `{root:invalid_modifier}` — Unknown modifier
  - `{unknown_field}` — Non-existent field
  - `{env:MISSING_VAR}` — Environment variable not set and no default provided

### Hatchling v1.3.0+ Improvements

When helping users with Hatchling v1.3.0+, note these improvements:

- Improved error messages for the `env` context string formatting field
- Clear indication of which environment variables are missing and require defaults
- Fixed URI context formatting on Windows to properly handle drive letters and spaces

## Platform-Specific Behavior

When assisting users, explain platform differences:

### Windows

- `{/}` → `\`
- `{;}` → `;`
- Path URIs use `file:///C:/` notation
- Spaces in paths are properly escaped in URI format

### Unix-like (Linux, macOS)

- `{/}` → `/`
- `{;}` → `:`
- Path URIs use `file:///` notation
- Spaces in paths are properly escaped in URI format

## Configuration Sections Supporting Global Fields

Reference this list when helping users understand where context formatting works:

- `[project.dependencies]`
- `[project.optional-dependencies]`
- `[tool.hatch.envs.<ENV_NAME>]` — All environment configurations
- `[tool.hatch.envs.<ENV_NAME>.scripts]` — Script definitions
- `[tool.hatch.envs.<ENV_NAME>.env-vars]` — Environment variable values

## Practical Patterns

Reference these patterns when assisting users:

### Monorepo Dependency References

When helping users with monorepo projects that have multiple local packages:

```toml
[project.optional-dependencies]
dev = [
    "pkg-a @ {root}/packages/pkg-a",
    "pkg-b @ {root}/packages/pkg-b",
]

[project.optional-dependencies]
tests = [
    "pytest",
    "pkg-a @ {root:uri}/packages/pkg-a",
    "pkg-b @ {root:uri}/packages/pkg-b",
]
```

### Cross-Platform Scripts

Guide users on building path-aware scripts:

```toml
[tool.hatch.envs.test.scripts]
build = "python {root}{/}scripts{/}build.py"
test = "pytest {root}{/}tests"
```

### Environment-Based Configuration

Show users fallback chains for environment-specific overrides:

```toml
[tool.hatch.envs.default.env-vars]
API_KEY = "{env:PROD_API_KEY:{env:DEV_API_KEY:local-test-key}}"
LOG_LEVEL = "{env:HATCH_LOG_LEVEL:INFO}"
```

### Relative Package References

Help users with monorepos install sibling packages:

```toml
[tool.hatch.envs.dev]
dependencies = [
    ".-e",
    "sibling @ {root:parent}/sibling-project",
    "other @ {root:parent:parent}/other-project",
]
```

## Related Topics

When assisting users further, reference:

- `environment-fields.md` — Fields specific to Hatch environments
- `optional-dependencies.md` — Context formatting for optional dependency groups
- `dynamic-configuration.md` — Programmatic metadata and dynamic field resolution
- `configuration-interpolation.md` — Advanced field nesting and chaining
