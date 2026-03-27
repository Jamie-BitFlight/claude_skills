---
title: Version Scheme Plugins
description: Define version validation, formatting, and bumping rules. Covers PEP 440 standard scheme, version bumping commands, pre-release workflows, custom schemes, and best practices.
---

# Version Scheme Plugins

Version scheme plugins define how versions are validated, formatted, and bumped in Hatchling. They ensure version strings follow specific patterns and control how version increments work when using commands like `hatch version patch`.

## Overview

Version schemes provide:

- **Validation**: Ensure versions follow specific formats (e.g., PEP 440)
- **Bumping Logic**: Define how version segments are incremented
- **Normalization**: Convert versions to canonical forms
- **Custom Rules**: Implement organization-specific versioning policies

## Standard Version Scheme

The `standard` scheme is the default and follows [PEP 440](https://peps.python.org/pep-0440/) versioning:

```toml
[tool.hatch.version]
scheme = "standard"  # Optional, as this is the default
```

### Configuration Options

```toml
[tool.hatch.version.scheme.standard]
validate-bump = true  # Ensure new version is higher than current
```

### Supported Version Formats

The standard scheme supports all PEP 440 version formats:

```python
# Release versions
"1.2.3"           # Final release
"2024.12.1"       # Calendar versioning

# Pre-releases
"1.0.0a1"         # Alpha
"1.0.0b2"         # Beta
"1.0.0rc3"        # Release candidate

# Development releases
"1.0.0.dev0"      # Development release
"1.0.0.dev5"      # Fifth development release

# Post releases
"1.0.0.post1"     # Post release

# Epochs
"1!2.0.0"         # Version with epoch

# Local versions
"1.0.0+local.1"   # With local version identifier
"1.0.0+git.abc123" # With git commit
```

### Version Bumping Commands

The standard scheme supports various bump commands:

#### Basic Segments

```bash
# Patch version (1.2.3 -> 1.2.4)
$ hatch version patch

# Minor version (1.2.3 -> 1.3.0)
$ hatch version minor

# Major version (1.2.3 -> 2.0.0)
$ hatch version major
```

#### Pre-release Cycles

```bash
# Start alpha cycle (1.2.3 -> 1.2.4a0)
$ hatch version alpha

# Continue alpha (1.2.4a0 -> 1.2.4a1)
$ hatch version alpha

# Move to beta (1.2.4a1 -> 1.2.4b0)
$ hatch version beta

# Release candidate (1.2.4b2 -> 1.2.4rc0)
$ hatch version rc

# Final release (1.2.4rc1 -> 1.2.4)
$ hatch version release
```

#### Combined Commands

```bash
# Bump minor and start alpha (1.2.3 -> 1.3.0a0)
$ hatch version minor,alpha

# Bump major and start beta (1.2.3 -> 2.0.0b0)
$ hatch version major,beta
```

#### Development Releases

```bash
# Start dev cycle (1.2.3 -> 1.2.4.dev0)
$ hatch version dev

# Continue dev (1.2.4.dev0 -> 1.2.4.dev1)
$ hatch version dev
```

## Version Scheme Interface

All version schemes implement the `VersionSchemeInterface`:

```python
class VersionSchemeInterface:
    """Interface for version scheme plugins."""

    PLUGIN_NAME: str  # Unique identifier
    root: Path        # Project root directory
    config: dict      # Configuration from pyproject.toml

    def validate_bump(self, version: str, bump: str) -> None:
        """
        Validate a version bump operation.

        Args:
            version: Current version string
            bump: Requested bump operation

        Raises:
            ValueError: If bump is invalid
        """
        pass

    def update(self, version: str, bump: str) -> str:
        """
        Apply bump operation to version.

        Args:
            version: Current version string
            bump: Bump operation to apply

        Returns:
            New version string
        """
        pass
```

## Validate-Bump Option

The `validate-bump` option ensures new versions are higher than the current version:

### Enabled (Default)

```toml
[tool.hatch.version.scheme.standard]
validate-bump = true
```

```bash
# Current version: 2.0.0
$ hatch version "1.9.0"
Error: Version '1.9.0' is not higher than current version '2.0.0'
```

### Disabled

```toml
[tool.hatch.version.scheme.standard]
validate-bump = false
```

```bash
# Current version: 2.0.0
$ hatch version "1.9.0"
Old: 2.0.0
New: 1.9.0  # Downgrade allowed
```

Use cases for disabling:

- Rolling back versions
- Switching versioning schemes
- Development experiments
- Special release workflows

## Version Normalization

The standard scheme normalizes versions to canonical form:

```python
# Input -> Normalized
"1.0"          -> "1.0.0"
"1.0.0.0"      -> "1.0.0"
"1.0a"         -> "1.0a0"
"1.0.alpha"    -> "1.0a0"
"1.0-beta"     -> "1.0b0"
"1.0c1"        -> "1.0rc1"
"1.0.dev"      -> "1.0.dev0"
"1.0+local"    -> "1.0+local"
"01.02.03"     -> "1.2.3"
```

## Version Epoch Handling

Epochs are supported for major version changes:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
path = "src/version.py"
```

```python
# src/version.py
__version__ = "1!2.0.0"  # Epoch 1, version 2.0.0
```

Epoch rules:

- Epochs start at 0 (implicit if not specified)
- `1!2.0.0` is always newer than `0!99.0.0`
- Epochs should rarely be used (only for critical versioning fixes)

## Custom Version Schemes

While Hatchling only includes the standard scheme by default, you can create custom schemes:

### Example: Semantic Versioning Strict

```python
# hatch_plugins.py
from hatchling.version.scheme.plugin.interface import VersionSchemeInterface

class SemanticVersionScheme(VersionSchemeInterface):
    PLUGIN_NAME = "semantic"

    def validate_bump(self, version: str, bump: str) -> None:
        """Validate semantic versioning rules."""
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Version must be X.Y.Z format, got: {version}")

        if bump not in ["major", "minor", "patch"]:
            raise ValueError(f"Invalid bump type: {bump}")

    def update(self, version: str, bump: str) -> str:
        """Apply semantic version bump."""
        major, minor, patch = version.split(".")

        if bump == "major":
            return f"{int(major) + 1}.0.0"
        elif bump == "minor":
            return f"{major}.{int(minor) + 1}.0"
        elif bump == "patch":
            return f"{major}.{minor}.{int(patch) + 1}"
```

Register in `pyproject.toml`:

```toml
[project.entry-points."hatchling.version.scheme"]
semantic = "hatch_plugins:SemanticVersionScheme"

[tool.hatch.version]
scheme = "semantic"
```

## Working with Pre-releases

### Alpha/Beta/RC Workflow

Standard development cycle:

```bash
# Development starts
$ hatch version
1.2.3

# Start alpha development
$ hatch version minor,alpha
Old: 1.2.3
New: 1.3.0a0

# Continue alpha releases
$ hatch version alpha
Old: 1.3.0a0
New: 1.3.0a1

# Move to beta
$ hatch version beta
Old: 1.3.0a1
New: 1.3.0b0

# Release candidate
$ hatch version rc
Old: 1.3.0b2
New: 1.3.0rc0

# Final release
$ hatch version release
Old: 1.3.0rc1
New: 1.3.0
```

### Development Releases

For continuous development:

```bash
# Start development
$ hatch version dev
Old: 1.2.3
New: 1.2.4.dev0

# Continue development
$ hatch version dev
Old: 1.2.4.dev0
New: 1.2.4.dev1

# Release from dev
$ hatch version release
Old: 1.2.4.dev5
New: 1.2.4
```

## Version Comparison

The standard scheme follows PEP 440 comparison rules:

```python
from packaging.version import Version

# Comparison order
versions = [
    "1.0.dev0",    # Development
    "1.0a1",       # Alpha
    "1.0b1",       # Beta
    "1.0rc1",      # Release candidate
    "1.0",         # Final
    "1.0.post1",   # Post-release
    "1!0.0",       # Epoch 1
]

# Sorted from lowest to highest
sorted_versions = sorted(versions, key=Version)
```

## Local Version Identifiers

Add local version identifiers for custom builds:

```python
# Base version
__version__ = "1.2.3"

# With local identifier
__version__ = "1.2.3+local.1"
__version__ = "1.2.3+git.abc123"
__version__ = "1.2.3+build.20240101"
```

Local version rules:

- Not uploaded to PyPI (PyPI rejects local versions)
- Useful for internal builds
- Always considered "newer" than base version
- Format: `+` followed by dot-separated identifiers

## Best Practices

### 1. Adhere to PEP 440

Follow PEP 440 standards for maximum compatibility:

```toml
[tool.hatch.version]
scheme = "standard"  # Default PEP 440 compliant
```

### 2. Use Semantic Versioning

Within PEP 440, follow semantic versioning:

- MAJOR: Breaking changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

### 3. Document Versioning Policy

Create and maintain VERSION_POLICY.md documentation:

```markdown
# Version Policy

- Production releases: X.Y.Z
- Pre-releases: X.Y.Za0, X.Y.Zb0, X.Y.Zrc0
- Development: X.Y.Z.dev0
- No local versions in releases
- Major version bumps require team approval
```

### 4. Implement Automated Version Validation

Add CI/CD checks to enforce version format requirements:

```yaml
# .github/workflows/version-check.yml
- name: Check version format
  run: |
    python -c "
    from packaging.version import Version
    import subprocess
    version = subprocess.check_output(['hatch', 'version']).decode().strip()
    v = Version(version)
    print(f'Valid PEP 440 version: {v}')
    "
```

## Common Issues and Solutions

### Issue: Invalid Version Format

```bash
$ hatch version "v1.2.3"
Error: Invalid version: 'v1.2.3'
```

Solution: Remove the 'v' prefix:

```bash
hatch version "1.2.3"
```

### Issue: Can't Bump from Pre-release

```bash
$ hatch version patch
Error: Cannot bump patch version from pre-release
```

Solution: Use `release` first:

```bash
hatch version release  # Remove pre-release
hatch version patch    # Then bump
```

### Issue: Accidental Downgrade

```bash
$ hatch version "1.0.0"  # Accidentally downgrading from 2.0.0
Error: Version '1.0.0' is not higher than '2.0.0'
```

Solution: Either use correct version or disable validation:

```toml
[tool.hatch.version.scheme.standard]
validate-bump = false  # Temporary, for special cases
```

## See Also

- `version-cli.md` - Using version commands
- `version-validation.md` - Validation rules
- `version-source-interface.md` - Source plugin API
- [PEP 440](https://peps.python.org/pep-0440/) - Python version spec
- [Semantic Versioning](https://semver.org/) - SemVer specification
