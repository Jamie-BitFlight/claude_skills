---
title: Dynamic Version Sources Overview
description: Guide to implementing dynamic versioning in Hatchling. Covers available sources (regex, code, env), choosing appropriate sources, version resolution at build time, and troubleshooting strategies.
---

# Dynamic Version Sources Overview

Dynamic versioning in Hatchling allows projects to determine versions at build time from external sources rather than hardcoding in `pyproject.toml`. This approach enables automated version management, integration with version control systems, and flexible deployment workflows.

## Configuration Basics

To use dynamic versioning, declare `version` as dynamic in your project metadata:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "regex"  # Version source plugin to use
# Additional configuration specific to the source
```

## Available Version Sources

Hatchling provides several built-in version source plugins:

| Source  | Description                               | Use Case                                     |
| ------- | ----------------------------------------- | -------------------------------------------- |
| `regex` | Extract version using regular expressions | Default; simple file-based versioning        |
| `code`  | Import and execute Python code            | Complex version logic or multiple sources    |
| `env`   | Read from environment variables           | CI/CD integration, containerized deployments |

Third-party sources are also available:

| Source   | Description                            | Installation                       |
| -------- | -------------------------------------- | ---------------------------------- |
| `vcs`    | Version from VCS tags (Git, Mercurial) | `pip install hatch-vcs`            |
| `nodejs` | Read from package.json                 | `pip install hatch-nodejs-version` |

## Version Source Plugin Interface

All version source plugins implement the `VersionSourceInterface`:

```python
class VersionSourceInterface:
    """Interface for version source plugins."""

    PLUGIN_NAME: str  # Unique identifier for the plugin
    root: Path        # Project root directory
    config: dict      # Configuration from pyproject.toml

    def get_version_data(self) -> dict:
        """
        Retrieve version information.

        Returns:
            dict: Must contain 'version' key with version string
        """
        pass

    def set_version(self, version: str) -> None:
        """
        Update the version in the source.

        Args:
            version: New version string to set
        """
        pass
```

## Choosing a Version Source

### Decision Tree

<eg>
Is your version in a Python file?
├─ Yes → Is it a simple string assignment?
│  ├─ Yes → Use `regex` source
│  └─ No → Use `code` source
└─ No → Is it in environment/CI?
   ├─ Yes → Use `env` source
   └─ No → Consider third-party sources (vcs, nodejs, etc.)
</eg>

### Comparison Matrix

| Feature               | `regex` | `code` | `env`     |
| --------------------- | ------- | ------ | --------- |
| **Setup Complexity**  | Low     | Medium | Low       |
| **Performance**       | Fast    | Slower | Fast      |
| **Flexibility**       | Medium  | High   | Low       |
| **CI/CD Integration** | Good    | Good   | Excellent |
| **Version Bumping**   | Yes     | Yes    | External  |
| **Multiple Files**    | No      | Yes    | N/A       |
| **Custom Logic**      | No      | Yes    | No        |

## Common Configuration Patterns

### Single Version File

Most projects use a dedicated version file:

```toml
[tool.hatch.version]
source = "regex"
path = "src/my_package/__about__.py"
```

With `__about__.py`:

```python
__version__ = "1.2.3"
```

### Version from Package **init**

Store version in the main package module:

```toml
[tool.hatch.version]
source = "regex"
path = "src/my_package/__init__.py"
pattern = "__version__ = ['\"](?P<version>[^'\"]+)['\"]"
```

### Environment-Based Versioning

For containerized or CI/CD workflows:

```toml
[tool.hatch.version]
source = "env"
variable = "PROJECT_VERSION"
default = "0.0.0+unknown"
```

### Complex Version Logic

For versions derived from multiple sources:

```toml
[tool.hatch.version]
source = "code"
path = "version_helper.py"
expression = "get_version()"
```

## Version Data Structure

Version source plugins return a dictionary that must contain at minimum:

```python
{
    "version": "1.2.3"  # Required: The version string
}
```

Some sources may return additional metadata:

```python
{
    "version": "1.2.3",
    "raw_version": "v1.2.3",  # Original format
    "source_file": "/path/to/file",  # Where version was found
    "timestamp": "2024-01-01T00:00:00Z"  # When determined
}
```

## Integration with Build Process

### Build-Time Resolution

Dynamic versions are resolved during:

1. **Package Building**: When creating wheels or source distributions
2. **Editable Installs**: When installing in development mode
3. **Metadata Generation**: When tools request project metadata
4. **Version Commands**: When using `hatch version` CLI

### Caching Behavior

Hatchling caches resolved versions during a build session to ensure consistency:

```python
# Version is resolved once per build
building wheel...  # Resolves version
building sdist...  # Uses cached version
```

## Working with Dynamic Versions

### Displaying Current Version

```bash
$ hatch version
1.2.3
```

### Updating Dynamic Versions

The update capability depends on the source plugin:

```bash
# For sources that support setting (regex, code)
$ hatch version patch
Old: 1.2.3
New: 1.2.4

# For read-only sources (env)
$ hatch version patch
Error: The 'env' source does not support setting versions
```

## Fallback Strategies

### Default Values

Some sources support fallback values:

```toml
[tool.hatch.version]
source = "env"
variable = "VERSION"
default = "0.0.0+dev"  # Used if variable not set
```

### Error Handling

Configure behavior when version cannot be determined:

```toml
[tool.hatch.version]
source = "regex"
path = "src/version.py"
strict = false  # Don't fail if file missing (uses 0.0.0)
```

## Metadata Hooks

For advanced scenarios, use metadata hooks to modify version data:

```python
# hatch_build.py
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        # Modify version after source resolution
        version = metadata.get("version", "0.0.0")
        metadata["version"] = f"{version}+custom"
```

## Performance Considerations

### Resolution Timing

- **Build Time**: Version resolved when package is built
- **Not at Import**: Version isn't resolved when package is imported
- **Development Mode**: Resolved once during editable install

### Optimization Tips

1. **Use regex over code** when possible (faster)
2. **Cache expensive operations** in code source
3. **Avoid network calls** in version resolution
4. **Keep version files small** for quick parsing

## Migration Guide

### From setuptools-scm

```toml
# Old: setuptools-scm
[build-system]
requires = ["setuptools>=45", "setuptools-scm[toml]>=6.2"]

[tool.setuptools_scm]

# New: hatch-vcs
[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"
```

### From Static to Dynamic

```toml
# Old: Static
[project]
version = "1.2.3"

# New: Dynamic
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "regex"
path = "src/my_package/__about__.py"
```

## Troubleshooting

### Common Issues

| Issue                        | Cause                                       | Solution                                |
| ---------------------------- | ------------------------------------------- | --------------------------------------- |
| Version not found            | File doesn't exist or pattern doesn't match | Check path and pattern configuration    |
| Import errors                | Circular dependencies in code source        | Isolate version logic from main package |
| Environment variable not set | Missing in environment                      | Provide default value                   |
| Version mismatch             | Multiple version sources                    | Ensure single source of truth           |

### Debugging

Enable verbose output to debug version resolution:

```bash
$ hatch version -v
Looking for version in src/my_package/__about__.py
Pattern: __version__ = ["']([^"']+)["']
Found: 1.2.3
```

## Best Practices

1. **Single Source of Truth**: Define version in one place only
2. **Simple Patterns**: Use straightforward regex patterns
3. **Fast Resolution**: Avoid expensive operations during version resolution
4. **Clear Errors**: Provide helpful error messages when version not found
5. **Document Choice**: Explain version source selection in README
6. **Test Resolution**: Verify version resolution in CI/CD
7. **Provide Fallbacks**: Include default values for resilience

## See Also

- `code-version-source.md`
- `regex-version-source.md`
- `env-version-source.md`
- `version-source-interface.md`
- `custom-version-sources.md`
