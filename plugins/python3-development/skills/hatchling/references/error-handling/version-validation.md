---
category: Error Handling
topics: [version-validation, pep-440, version-bumping, version-schemes, dynamic-versions]
related: [./spdx-validation.md, ./metadata-compatibility.md, ./build-validation.md]
---

# Version Validation and Bumping Errors in Hatchling

## Overview

When guiding users through version management in Hatchling projects, reference this document to help them understand and resolve version-related errors. Hatchling implements strict version validation following PEP 440 and provides version bumping through the standard version scheme. This document covers version-related errors, validation rules, and bumping strategies.

## Version Validation Errors

### Invalid Version Format

**Error Message:**

<eg>
ValueError: Invalid version: 'x.y.z'
</eg>

**Common Invalid Formats:**

```python
# Invalid versions
"1.0"           # Missing patch (should be "1.0.0")
"v1.0.0"        # 'v' prefix not allowed
"1.0.0-SNAPSHOT" # Invalid pre-release identifier
"1.0.0.0"       # Too many components (without epoch)
"1.0.0-x-y-z.–" # Invalid characters
"1_0_0"         # Underscores not allowed
```

**Valid PEP 440 Formats:**

```python
# Valid versions
"1.0.0"         # Standard
"2.1.3"         # Semantic versioning
"1.0.0a1"       # Alpha pre-release
"1.0.0b2"       # Beta pre-release
"1.0.0rc3"      # Release candidate
"1.0.0.dev4"    # Development release
"1.0.0.post5"   # Post-release
"1!1.0.0"       # Version with epoch
```

## Standard Version Scheme

### Configuration

```toml
[tool.hatch.version]
scheme = "standard"
validate-bump = true  # v1.11.0+
```

### Version Bumping Commands

```bash
# Basic bumps
hatch version patch    # 1.0.0 -> 1.0.1
hatch version minor    # 1.0.0 -> 1.1.0
hatch version major    # 1.0.0 -> 2.0.0

# Pre-release bumps
hatch version alpha    # 1.0.0 -> 1.0.1a1
hatch version beta     # 1.0.0 -> 1.0.1b1
hatch version rc       # 1.0.0 -> 1.0.1rc1

# Release from pre-release
hatch version release  # 1.0.1rc1 -> 1.0.1

# Set specific version
hatch version "1.2.3"
```

### Validate-Bump Option (v1.11.0+)

```toml
[tool.hatch.version]
scheme = "standard"
validate-bump = true
```

**Validation Rules:**

- New version must be higher than current
- Version must follow PEP 440
- Pre-release progression must be valid

**Error Examples:**

```bash
# Current version: 1.2.0
hatch version "1.1.0"  # Error: version would go backwards
hatch version "1.2.0"  # Error: version unchanged
```

## Version Epoch Handling

### Non-Zero Epoch Support (v1.19.0+)

```toml
[project]
version = "1!1.0.0"  # Epoch 1, version 1.0.0
```

**Use Cases:**

- Package renamed/restructured
- Breaking API changes requiring epoch bump
- Fork with incompatible changes

**Epoch Rules:**

```python
# Epoch comparison
"1!1.0.0" > "2.0.0"  # Epoch takes precedence
"2!0.1.0" > "1!99.0.0"  # Higher epoch always wins
```

## Dynamic Version Configuration

### From File (Most Common)

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/mypackage/__about__.py"
```

**Version File Format:**

```python
# src/mypackage/__about__.py
__version__ = "1.0.0"
```

### From Environment Variable (v1.11.0+)

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "env"
variable = "MY_APP_VERSION"
```

**Usage:**

```bash
export MY_APP_VERSION="1.2.3"
hatch build
```

### From Code

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "code"
path = "src/mypackage/version.py"
expression = "get_version()"
search-paths = ["src"]  # v1.6.0+
```

**Version Module:**

```python
# src/mypackage/version.py
def get_version():
    return "1.0.0"
```

## Version Validation in Build Process

### Pre-Build Validation

```python
#!/usr/bin/env python3
"""Validate version before build."""

import re
import sys
from packaging.version import Version, InvalidVersion

def validate_version(version_string):
    """Validate PEP 440 compliance."""
    try:
        v = Version(version_string)
        print(f"Valid version: {v}")
        print(f"  Base: {v.base_version}")
        print(f"  Pre: {v.pre}")
        print(f"  Dev: {v.dev}")
        print(f"  Post: {v.post}")
        print(f"  Local: {v.local}")
        return True
    except InvalidVersion as e:
        print(f"Invalid version: {e}")
        return False

if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    if not validate_version(version):
        sys.exit(1)
```

### Build Hook Validation

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging.version import Version, InvalidVersion

class VersionValidationHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Validate version during build."""
        try:
            v = Version(version)

            # Custom validation rules
            if v.pre and v.dev:
                raise ValueError(
                    "Cannot have both pre-release and dev markers"
                )

            if v.local:
                raise ValueError(
                    "Local version identifiers not allowed in builds"
                )

        except InvalidVersion:
            raise ValueError(f"Invalid PEP 440 version: {version}")
```

## Version Bumping Strategies

### Semantic Versioning Pattern

```python
#!/usr/bin/env python3
"""Semantic version bumping utilities."""

from packaging.version import Version

def bump_version(current: str, bump_type: str) -> str:
    """Bump version following semantic versioning."""
    v = Version(current)

    if v.pre or v.dev or v.post:
        # Strip pre/dev/post for clean bump
        base = v.base_version
    else:
        base = str(v)

    major, minor, patch = map(int, base.split('.'))

    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == 'alpha':
        return f"{major}.{minor}.{patch + 1}a1"
    elif bump_type == 'beta':
        return f"{major}.{minor}.{patch + 1}b1"
    elif bump_type == 'rc':
        return f"{major}.{minor}.{patch + 1}rc1"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")
```

### Pre-Release Progression

```python
def next_prerelease(current: str) -> str:
    """Progress through pre-release stages."""
    v = Version(current)

    if not v.pre:
        # Start pre-release cycle
        return f"{v.base_version}a1"

    phase, number = v.pre
    if phase == 'a':  # Alpha
        return f"{v.base_version}a{number + 1}"
    elif phase == 'b':  # Beta
        return f"{v.base_version}b{number + 1}"
    elif phase == 'rc':  # Release Candidate
        return f"{v.base_version}rc{number + 1}"
```

## Common Version Errors and Solutions

### Error: Version String Contains Invalid Characters

**Problem:**

```toml
[project]
version = "1.0.0-RELEASE"  # Invalid suffix
```

**Solution:**

```toml
[project]
version = "1.0.0"  # Remove invalid suffix
# or
version = "1.0.0.post1"  # Use valid post-release
```

### Error: Version Comparison Fails

**Problem:**

```python
# In requirements
"mypackage>=1.0.0-beta"  # Invalid specifier
```

**Solution:**

```python
"mypackage>=1.0.0b1"  # Use valid pre-release format
```

### Error: Local Version in Published Package

**Problem:**

```toml
[project]
version = "1.0.0+local.version"  # Local version identifier
```

**Solution:**

```toml
[project]
version = "1.0.0"  # Remove local identifier for publishing
```

## Version Validation Automation

### Pre-Commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-version
        name: Validate PEP 440 Version
        entry: python scripts/validate_version.py
        language: python
        files: pyproject.toml
        additional_dependencies: [packaging]
```

### CI/CD Validation

```yaml
# .github/workflows/validate.yml
name: Validate Version

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Extract version
        id: version
        run: |
          VERSION=$(hatch version)
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      - name: Validate PEP 440
        run: |
          python -c "
          from packaging.version import Version
          Version('${{ steps.version.outputs.version }}')
          print('Version valid: ${{ steps.version.outputs.version }}')
          "
```

## Best Practices

1. **Always use PEP 440** compliant versions
2. **Validate before publishing** to PyPI
3. **Use semantic versioning** for clarity
4. **Automate version bumping** in CI/CD
5. **Document version scheme** in contributing guide

## Version History

- **v1.11.0**: Added `env` version source and `validate-bump`
- **v1.19.0**: Fixed non-zero epoch handling
- **v1.6.0**: Added `search-paths` for code source
- **v1.4.0**: Added version build hook

## Related Documentation

- `build-validation.md`
- `metadata-validation.md`
- `spdx-validation.md`
