---
category: Hatchling Build System
topics: [version-hook, version-injection, build-hooks, version-management]
related: [configuration.md, buildhook-interface.md, custom-build-hooks.md]
---

# Version Build Hook

The version build hook is a built-in hook that writes the project's version to a designated file during the build process. Help users understand how to dynamically include version information in packages without hardcoding it by referencing this documentation.

## Overview

The version hook:

- Automatically injects the project version into files
- Supports multiple methods: full file replacement, regex pattern matching, or template rendering
- Runs during the `initialize()` stage before the build
- Modifies files in-place or from templates

## Configuration

### Plugin Name

The version hook plugin name is `version`.

### Configuration Location

```toml
# Global version hook
[tool.hatch.build.hooks.version]

# Target-specific version hook
[tool.hatch.build.targets.<TARGET_NAME>.hooks.version]
```

### Required and Optional Options

| Option     | Required | Description                                                                                |
| ---------- | -------- | ------------------------------------------------------------------------------------------ |
| `path`     | Yes      | A relative path to the file that will receive the version                                  |
| `template` | No       | A string with the entire contents of the file, formatted with `{version}` variable         |
| `pattern`  | No       | A regex pattern with a named group `version` to match and replace version in existing file |

**Note**: Only one of `template` or `pattern` should be used. If neither is provided, the pattern defaults to matching `__version__` or `VERSION` variables.

## Configuration Options

### `path` (Required)

The path to the file that will receive the version information. This must be a relative path from the project root.

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
```

The file is modified during the build process.

### `template` (Optional)

A complete file template that will be used as the entire contents of the target file. The template supports formatting with a `version` variable.

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '''"""Version information"""
__version__ = "{version}"
'''
```

When the build runs, the `{version}` placeholder is replaced with the actual project version.

### `pattern` (Optional)

A regular expression with a named group called `version` that specifies which text in the file to replace with the version.

#### Using `pattern = true` (Default Pattern)

Setting `pattern` to `true` uses a built-in pattern that matches:

- Variables named `__version__` or `VERSION`
- Optional lowercase `v` prefix
- Version string in quotes

```toml
[tool.hatch.build.hooks.version]
path = "myproject/__init__.py"
pattern = true
```

This pattern matches:

```python
__version__ = "1.0.0"
__version__ = "v1.0.0"
VERSION = "1.0.0"
version = "1.0.0"
```

#### Using Custom Regex Pattern

Provide a custom regex pattern with a `version` named group:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__init__.py"
pattern = "__version__\\s*=\\s*['\"](?P<version>[^'\"]+)['\"]"
```

The pattern must include `(?P<version>...)` to capture the version.

**Example**: Match version in a JSON file:

```toml
[tool.hatch.build.hooks.version]
path = "package.json"
pattern = '"version":\\s*"(?P<version>[^"]+)"'
```

**Example**: Match version in a YAML file:

```toml
[tool.hatch.build.hooks.version]
path = "version.yaml"
pattern = 'version:\\s*"?(?P<version>[^"\\n]+)"?'
```

## Common Use Cases

### Writing Version to Python File

The most common use case: store version in a Python file.

**Using template (recommended for simple cases)**:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

**Using pattern with default matching**:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
pattern = true
```

File before build:

```python
__version__ = "0.0.0"
```

File after build (if version is 1.0.0):

```python
__version__ = "1.0.0"
```

### Writing Version to Text File

Store version in a simple text file:

```toml
[tool.hatch.build.hooks.version]
path = "VERSION"
template = "{version}"
```

### Updating Version in Multiple Locations

Use multiple version hooks with different target files:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'

[tool.hatch.build.hooks.version-init]
path = "myproject/__init__.py"
pattern = true
```

**Note**: In `pyproject.toml`, you cannot have multiple sections with the same name. Use target-specific hooks instead:

```toml
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'

[tool.hatch.build.targets.sdist.hooks.version]
path = "VERSION"
template = "{version}"
```

### Version in Package JSON

```toml
[tool.hatch.build.hooks.version]
path = "package.json"
pattern = '"version":\\s*"(?P<version>[^"]+)"'
```

File before build:

```json
{
  "name": "my-package",
  "version": "0.0.0"
}
```

File after build (if version is 1.2.3):

```json
{
  "name": "my-package",
  "version": "1.2.3"
}
```

### Version in Configuration File

```toml
[tool.hatch.build.hooks.version]
path = "config.ini"
pattern = "version\\s*=\\s*(?P<version>[^\\n]+)"
```

File before build:

```ini
[metadata]
version = 0.0.0
```

File after build (if version is 1.0.0):

```ini
[metadata]
version = 1.0.0
```

## How It Works

1. **Before build starts** (during `initialize()`), the version hook:

   - Reads the project version from the configured version source
   - Modifies the specified file with the version

2. **File modification**:

   - **If `template` is provided**: Replaces entire file contents with template, substituting `{version}`
   - **If `pattern` is provided**: Finds matching text and replaces the `version` group with actual version
   - **If neither provided**: Uses default pattern (matching `__version__` or `VERSION`)

3. **Version is now available**: The modified file is included in the build and distributed with the package

## Integration with Version Sources

The version hook works in conjunction with Hatchling's version sources. The version is obtained from the configured version source:

```toml
[tool.hatch.version]
path = "src/myproject/__about__.py"

[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

In this example:

- `[tool.hatch.version]` specifies where to _read_ the version (version source)
- `[tool.hatch.build.hooks.version]` specifies where to _write_ the version (version hook)

## Examples by File Type

### Python Module

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__init__.py"
pattern = true
```

### setup.py Compatibility

```toml
[tool.hatch.build.hooks.version]
path = "setup.py"
pattern = "version\\s*=\\s*['\"](?P<version>[^'\"]+)['\"]"
```

### Markdown

```toml
[tool.hatch.build.hooks.version]
path = "README.md"
pattern = "Version:\\s*(?P<version>[^\\n]+)"
```

### TOML Configuration

```toml
[tool.hatch.build.hooks.version]
path = "pyproject.toml"
pattern = 'version\\s*=\\s*"(?P<version>[^"]+)"'
```

## Best Practices

### 1. Keep Version File Minimal

If using `template`, keep it simple:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

Not:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '''"""Version information for myproject.

This is the authoritative source of version information.
It is automatically updated during builds.
"""
__version__ = "{version}"
'''
```

### 2. Use Patterns for Existing Files

When modifying existing files, use `pattern` to preserve other content:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__init__.py"
pattern = true  # or custom regex pattern
```

### 3. Avoid VCS-Ignored Generated Files

If the version file is generated, it should typically be in `.gitignore`:

```gitignore
# .gitignore
src/myproject/__version__.py
```

This ensures the generated file isn't committed to version control.

### 4. Document Version Source

Clearly indicate where the version comes from:

```toml
# Version is read from here
[tool.hatch.version]
path = "src/myproject/__about__.py"

# Version is written here (during build)
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

### 5. Test Different Build Scenarios

Test that version hooks work for:

- Wheel builds
- Sdist builds
- Both local and CI builds

## Troubleshooting

### Version Not Updated

Check that:

1. Hook is configured in the correct section
2. `path` points to the correct file
3. `pattern` regex is correct (if using custom pattern)
4. File exists or will be created by another hook

### Pattern Not Matching

Test your regex pattern:

```bash
python3 -c "
import re
pattern = r'__version__\\s*=\\s*['\\\"](?P<version>[^'\\\"]+)['\\\"]'
text = '__version__ = \"1.0.0\"'
match = re.search(pattern, text)
print(match.group('version') if match else 'No match')
"
```

### Multiple Version Placeholders

If your file has multiple version references, use a more specific pattern:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__init__.py"
pattern = "^__version__\\s*=\\s*['\"](?P<version>[^'\"]+)['\"]"
```

The `^` anchor ensures it matches at the line start.

## Related Topics

- `configuration.md` - How to configure version hooks
- `../version-management.md` - Understanding version sources
- `custom-build-hooks.md` - Writing custom hooks that work with versions
