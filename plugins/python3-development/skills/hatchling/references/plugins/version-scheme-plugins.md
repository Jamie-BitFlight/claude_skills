---
name: Version Scheme Plugins Reference
description: Reference guide for implementing version scheme plugins in Hatchling, covering the VersionSchemeInterface, version validation, normalization, and custom version format support.
---

# Version Scheme Plugins

Version scheme plugins validate and normalize version numbers during bumping operations.

## Overview

Version scheme plugins provide custom validation logic when users bump project versions via `hatch version`. They ensure version transitions follow specific rules (semantic versioning, date-based versioning, etc.).

## Core Interface: VersionSchemeInterface

### PLUGIN_NAME

Each version scheme must define a string identifier:

```python
class SemanticVersionScheme(VersionSchemeInterface):
    PLUGIN_NAME = 'semver'
```

Users select version schemes via configuration:

```toml
[tool.hatch.version]
scheme = "semver"
```

## Essential Methods

### update(desired_version, original_version, version_data)

**Required**: Validate and normalize version bump.

```python
def update(self, desired_version: str, original_version: str, version_data: dict) -> str:
    """
    Return a normalized form of the desired version.

    When validate_bump property is enabled (default), this method must
    verify that the new version is higher than the original version.

    Args:
        desired_version: The version the user wants to update to
        original_version: The current project version
        version_data: Additional context data about the version (from version source)

    Returns:
        str: Normalized/validated version string

    Raises:
        Exception: If version is invalid or lower than original
    """
    from packaging.version import Version

    try:
        desired = Version(desired_version)
        original = Version(original_version)
    except Exception as exc:
        raise ValueError(f'Invalid version format: {desired_version}') from exc

    if desired <= original:
        raise ValueError(
            f'Version {desired_version} is not higher than current {original_version}'
        )

    return str(desired)
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

Version scheme configuration from `[tool.hatch.version]`:

```python
@property
def config(self) -> dict:
    """
    Scheme configuration from [tool.hatch.version]

    Example:
    [tool.hatch.version]
    scheme = "semver"
    validate-bump = true
    """
    return self._config
```

## Official Version Scheme

### standard

Validates versions follow PEP 440 versioning.

Configuration:

```toml
[tool.hatch.version]
scheme = "standard"
validate-bump = true
```

Features:

- Validates PEP 440 format
- Ensures new version > original version
- Supports pre-releases (alpha, beta, rc)
- Supports local version identifiers

Examples:

<eg>
1.0.0 → 1.0.1 (valid)
1.0.0 → 1.1.0 (valid)
1.0.0 → 2.0.0 (valid)
1.0.0 → 1.0.0 (invalid - same)
1.0.0 → 0.9.0 (invalid - lower)
1.0.0 → 1.0.0a1 (invalid - lower)
1.0.0a1 → 1.0.0 (valid - final release)
</eg>

## Third-Party Version Schemes

### hatch-semver

Semantic versioning with strict validation.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-semver"]
```

Configuration:

```toml
[tool.hatch.version]
scheme = "semver"

[tool.hatch.version.hatch-semver]
validate-bump = true
```

Features:

- Enforces semantic versioning (MAJOR.MINOR.PATCH)
- Validates pre-release and build metadata
- Prevents invalid version transitions

## Example: Custom Version Scheme

```python
from hatchling.version.scheme.plugin.interface import VersionSchemeInterface
from datetime import datetime

class DateVersionScheme(VersionSchemeInterface):
    """Calendar versioning (YYYY.MM.DD[.MICRO])"""

    PLUGIN_NAME = 'calver'

    def update(self, desired_version: str, original_version: str, version_data: dict) -> str:
        """
        Validate calendar version format.

        Valid formats:
        - YYYY.MM.DD (e.g., 2024.11.02)
        - YYYY.MM.DD.MICRO (e.g., 2024.11.02.1)
        """
        from datetime import datetime

        parts = desired_version.split('.')

        if len(parts) < 3 or len(parts) > 4:
            raise ValueError(
                f'Calendar version must be YYYY.MM.DD[.MICRO], got {desired_version}'
            )

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])

            # Validate date components
            datetime(year, month, day)

            if len(parts) == 4:
                micro = int(parts[3])
                if micro < 0:
                    raise ValueError('Micro version must be non-negative')

        except ValueError as exc:
            raise ValueError(f'Invalid calendar version: {desired_version}') from exc

        # Validate version progression
        try:
            desired_date = datetime(year, month, day)
            original_parts = original_version.split('.')
            original_date = datetime(
                int(original_parts[0]),
                int(original_parts[1]),
                int(original_parts[2]),
            )

            if desired_date < original_date:
                raise ValueError(
                    f'Version {desired_version} is earlier than {original_version}'
                )
            elif desired_date == original_date:
                # Same date: require micro version increment
                original_micro = int(original_parts[3]) if len(original_parts) == 4 else 0
                desired_micro = int(parts[3]) if len(parts) == 4 else 0

                if desired_micro <= original_micro:
                    raise ValueError(
                        f'Micro version must increase for same date '
                        f'({desired_micro} > {original_micro})'
                    )

        except (ValueError, IndexError) as exc:
            raise ValueError(f'Invalid version comparison: {exc}') from exc

        return desired_version
```

## Configuration Examples

### Standard Scheme with Validation

```toml
[tool.hatch.version]
scheme = "standard"
validate-bump = true  # Require new > original
```

### Custom Scheme

```toml
[tool.hatch.version]
scheme = "calver"

[tool.hatch.version.calver]
# Custom scheme-specific options
```

### No Validation

```toml
[tool.hatch.version]
scheme = "standard"
validate-bump = false  # Allow any version string
```

## Usage Patterns

### Version Bumping with Validation

```bash
# With standard scheme
hatch version 1.1.0  # Allowed if current < 1.1.0
hatch version 0.9.0  # Rejected: version is lower

# With calendar version scheme
hatch version 2024.11.02      # Allowed
hatch version 2024.11.02.1    # Allowed (second release same day)
hatch version 2024.10.31      # Rejected: date is earlier
```

### Semantic Versioning

```bash
hatch version major  # 1.0.0 → 2.0.0
hatch version minor  # 1.0.0 → 1.1.0
hatch version patch  # 1.0.0 → 1.0.1
```

## Best Practices

1. **Clear Error Messages**: Explain why version is rejected
2. **Document Format**: Clearly document expected version format
3. **Consistent Validation**: Apply same rules in `update()` and documentation
4. **Handle Edge Cases**: Consider pre-releases, local versions, etc.
5. **Test Thoroughly**: Version schemes affect all version bumping
6. **Be Permissive**: Don't unnecessarily restrict valid versions
7. **Consider Legacy**: Support existing version format transitions

## Error Handling

Version schemes should raise descriptive exceptions:

```python
def update(self, desired_version: str, original_version: str, version_data: dict) -> str:
    if not self._is_valid(desired_version):
        raise ValueError(
            f'Invalid version format. Expected: {self._format_description}, '
            f'got: {desired_version}'
        )

    if not self._is_higher(desired_version, original_version):
        raise ValueError(
            f'Version {desired_version} must be higher than {original_version}'
        )

    return self._normalize(desired_version)
```

## See Also

- `version-source-plugins.md` - Retrieve version data
- [VersionSchemeInterface Reference](https://hatch.pypa.io/latest/plugins/version-scheme/reference/)
- [Hatchling Version Scheme Documentation](https://hatch.pypa.io/latest/plugins/version-scheme/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [Semantic Versioning](https://semver.org/)
- [Calendar Versioning](https://calver.org/)
