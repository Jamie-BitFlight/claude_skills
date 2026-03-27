---
name: Version Source Plugins Reference
description: Comprehensive guide to implementing version source plugins in Hatchling, covering the VersionSourceInterface, version retrieval, version updates, and configuration patterns.
---

# Version Source Plugins

Version source plugins determine how a project's version number is obtained. They provide an alternative to static version declarations.

## Overview

Version source plugins retrieve project version from various sources (VCS tags, code files, environment variables, etc.) instead of requiring manual version updates in `pyproject.toml`.

## Core Interface: VersionSourceInterface

### PLUGIN_NAME

Each version source must define a string identifier:

```python
class GitVersionSource(VersionSourceInterface):
    PLUGIN_NAME = 'git'
```

Users select version sources via configuration:

```toml
[tool.hatch.version]
source = "git"
```

## Essential Methods

### get_version_data()

**Required**: Retrieve current version information.

```python
def get_version_data(self) -> dict:
    """
    Should return a mapping with a 'version' key representing the
    current version of the project.

    Can include additional metadata that is passed to set_version().

    Returns:
        dict: Must contain 'version' key with version string.
              May contain other keys for custom data.
    """
    return {
        'version': '1.2.3',
        # Additional metadata
        'commit': 'abc123def456',
        'dirty': False,
    }
```

### set_version()

**Optional**: Update the version to a new value.

```python
def set_version(self, desired_version: str, original_data: dict) -> None:
    """
    Updates the version using data from get_version_data().

    The base implementation raises NotImplementedError, so custom
    behavior must be defined.

    Args:
        desired_version: The new version string
        original_data: Return value from get_version_data()
    """
    # Example: Write version to file
    version_file = os.path.join(self.root, 'src/__version__.py')
    with open(version_file, 'w') as f:
        f.write(f"__version__ = '{desired_version}'\n")
```

## Configuration & Properties

### root (Property)

Project root directory:

```python
@property
def root(self) -> str:
    """The root of the project tree."""
    return self._root
```

### config (Property)

Version source configuration from `[tool.hatch.version]`:

```python
@property
def config(self) -> dict:
    """
    Hook configuration from [tool.hatch.version]

    Example:
    [tool.hatch.version]
    path = "src/__version__.py"
    pattern = '__version__ = "([^"]+)"'
    """
    return self._config
```

## Official Version Sources

### code

Extract version from Python source code.

Configuration:

```toml
[tool.hatch.version]
source = "code"
path = "src/mypackage/__about__.py"
expression = '__version__'
```

Options:

- `path` - File containing version
- `expression` - Python expression to evaluate

Supports:

- Simple string assignments: `__version__ = "1.0.0"`
- Nested data structures
- Module importing and extension modules

### regex

Extract version from file using regular expression.

Configuration:

```toml
[tool.hatch.version]
source = "regex"
path = "src/mypackage/__init__.py"
pattern = '__version__\s*=\s*["\']([^"\']+)["\']'
```

Options:

- `path` - File to search
- `pattern` - Regex with version capture group or named `version` group

The pattern must contain exactly one capture group or a named `version` group:

```python
# Pattern: __version__\s*=\s*["\']([^"\']+)["\']
__version__ = "1.2.3"  # Matches: captures "1.2.3"

# Named group pattern
pattern = '__version__\s*=\s*["\'](?P<version>[^"\']+)["\']'
```

### env

Extract version from environment variable.

Configuration:

```toml
[tool.hatch.version]
source = "env"
variable = "PROJECT_VERSION"
```

Options:

- `variable` - Environment variable name (default: `<PROJECT_NAME>_VERSION`)

Examples:

```bash
# Using default naming (PROJECT_VERSION)
PROJECT_VERSION=1.0.0 hatch build

# Using custom variable
MY_VERSION=2.0.0 hatch build
```

## Third-Party Version Sources

### hatch-vcs

Version from version control system tags (Git, Mercurial, etc.).

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
```

Configuration:

```toml
[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/mypackage/_version.py"
```

Key features:

- Git/Mercurial tag support
- Automatic fallback version
- Setuptools-scm compatibility
- Custom tag pattern matching

See `hatch-vcs-plugin.md` for details.

### hatch-nodejs-version

Read version from Node.js `package.json`.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-nodejs-version"]
```

Configuration:

```toml
[tool.hatch.version]
source = "nodejs"
```

Reads `version` field from `package.json` in project root.

### versioningit

Git/Mercurial tag-based versioning with customizable formatting.

Installation:

```toml
[build-system]
requires = ["hatchling", "versioningit"]
```

Configuration:

```toml
[tool.hatch.version]
source = "versioningit"

[tool.versioningit]
default-branch = "main"
```

Features:

- Multiple VCS support
- Custom version formatting
- Template-based version building

### hatch-regex-commit

Automatically commit and tag after version bumping.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-regex-commit"]
```

Configuration:

```toml
[tool.hatch.version]
source = "regex"
# ... regex source config

[tool.hatch.version.hatch-regex-commit]
commit-message = "Bump version to {version}"
commit-tag = "v{version}"
```

## Example: Custom Version Source

```python
from hatchling.version.source.plugin.interface import VersionSourceInterface
import os
import json

class ManifestVersionSource(VersionSourceInterface):
    """Extract version from a manifest.json file."""

    PLUGIN_NAME = 'manifest'

    def get_version_data(self) -> dict:
        manifest_path = os.path.join(self.root, 'manifest.json')

        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f'Manifest not found: {manifest_path}')

        with open(manifest_path) as f:
            manifest = json.load(f)

        version = manifest.get('version')
        if not version:
            raise ValueError('No version field in manifest.json')

        return {
            'version': version,
            'build_number': manifest.get('build_number'),
            'release_date': manifest.get('release_date'),
        }

    def set_version(self, desired_version: str, original_data: dict) -> None:
        manifest_path = os.path.join(self.root, 'manifest.json')

        with open(manifest_path) as f:
            manifest = json.load(f)

        manifest['version'] = desired_version
        manifest['build_number'] = int(manifest.get('build_number', 0)) + 1

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
```

## Configuration Examples

### Code Source with Search Path

```toml
[tool.hatch.version]
source = "code"
path = "src/mypackage/__about__.py"
search-paths = ["src"]  # Alternative paths to search
```

### Regex with Named Group

```toml
[tool.hatch.version]
source = "regex"
path = "README.md"
pattern = '## Release (?P<version>[\d.]+)'
```

### Environment Variable

```toml
[tool.hatch.version]
source = "env"
variable = "RELEASE_VERSION"
```

Alternatively, default environment variable based on project name:

```toml
[project]
name = "my-project"  # Generates MY_PROJECT_VERSION variable

[tool.hatch.version]
source = "env"
```

### Dynamic Version in Build Hook

Combine with build hooks for version file generation:

```toml
[tool.hatch.version]
source = "regex"
path = "src/mypackage/__version__.py"
pattern = '__version__\s*=\s*["\']([^"\']+)["\']'

[tool.hatch.build.hooks.version]
path = "src/mypackage/__version__.py"
pattern = '__version__ = "{version}"'
```

## Usage Patterns

### Version Bumping

Update version using the source:

```bash
hatch version patch  # Increment patch version
hatch version minor  # Increment minor version
hatch version major  # Increment major version
```

### Dynamic Builds

Use `hatch version` to display current version:

```bash
VERSION=$(hatch version)
echo "Building version $VERSION"
hatch build
```

### CI/CD Integration

Set version via environment variable in CI:

```bash
# GitHub Actions
export PROJECT_VERSION=${{ github.ref_name }}
hatch build
```

## Best Practices

1. **Single Source of Truth**: Use one authoritative version source
2. **Fail Loudly**: Raise clear exceptions for missing or invalid versions
3. **Handle Missing Config**: Provide sensible defaults
4. **Performance**: Cache version lookups when possible
5. **Documentation**: Document custom source configuration clearly
6. **Test Extensively**: Version sources are critical build components
7. **Version Validation**: Ensure retrieved versions are valid PEP 440 format

## Validation

Versions from sources should follow [PEP 440](https://peps.python.org/pep-0440/):

```python
from packaging.version import Version

def get_version_data(self) -> dict:
    version_str = self._retrieve_version()

    # Validate version format
    try:
        Version(version_str)
    except Exception as exc:
        raise ValueError(f'Invalid version format: {version_str}') from exc

    return {'version': version_str}
```

## See Also

- `version-scheme-plugins.md` - Validate and normalize versions
- `hatch-vcs-plugin.md` - VCS-based versioning
- [VersionSourceInterface Reference](https://hatch.pypa.io/latest/plugins/version-source/reference/)
- [Hatchling Version Documentation](https://hatch.pypa.io/latest/plugins/version-source/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
