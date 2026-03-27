---
title: Version Validation and Bumping
description: Validate version formats and control version progression. Covers PEP 440 compliance, valid formats, invalid formats, and version bumping validation rules.
---

# Version Validation and Bumping

Version validation ensures that version strings follow the correct format and that version changes follow logical progression. Hatchling provides comprehensive validation based on PEP 440 and customizable bumping rules.

## PEP 440 Validation

All versions in Hatchling must comply with [PEP 440](https://peps.python.org/pep-0440/):

### Valid Version Formats

```python
# Release versions
"1.2.3"              # Standard
"2024.12.1"          # Calendar
"1.2"                # Short form (normalized to 1.2.0)

# Pre-releases
"1.0a1"              # Alpha
"1.0b2"              # Beta
"1.0rc3"             # Release candidate

# Development
"1.0.dev0"           # Development

# Post-releases
"1.0.post1"          # Post release

# Combinations
"1.0a1.dev0"         # Dev version of alpha
"1.0rc1.post2"       # Post release of RC

# Epochs
"1!2.0.0"            # Version 2.0.0, epoch 1

# Local versions
"1.0+local"          # With local identifier
"1.0+ubuntu1"        # Distribution specific
```

### Invalid Formats

```python
# These will cause errors
"v1.2.3"             # No 'v' prefix
"1.2.3-alpha"        # Wrong pre-release format
"latest"             # Not a version
"1.x"                # No wildcards
"1.2.3.4.5"          # Too many segments (without .dev/.post)
```

## Validate-Bump Configuration

Control whether new versions must be higher than current:

### Enabled (Default)

```toml
[tool.hatch.version.scheme.standard]
validate-bump = true  # Default behavior
```

Behavior:

```bash
# Current version: 2.0.0
$ hatch version "1.9.0"
Error: Version '1.9.0' is not higher than current version '2.0.0'

$ hatch version "2.0.1"
Old: 2.0.0
New: 2.0.1  # Allowed - higher version
```

### Disabled

```toml
[tool.hatch.version.scheme.standard]
validate-bump = false
```

Behavior:

```bash
# Current version: 2.0.0
$ hatch version "1.9.0"
Old: 2.0.0
New: 1.9.0  # Downgrade allowed
```

## Version Comparison Rules

### Standard Comparison

Versions are compared according to PEP 440:

```python
from packaging.version import Version

# Comparison order (lowest to highest)
versions = [
    "1.0.dev0",      # Development releases (lowest)
    "1.0a1.dev0",    # Dev of pre-release
    "1.0a1",         # Alpha releases
    "1.0a2",
    "1.0b1",         # Beta releases
    "1.0b2",
    "1.0rc1",        # Release candidates
    "1.0rc2",
    "1.0",           # Final release
    "1.0.post1",     # Post releases
    "1!0.0",         # Epoch 1 (always higher)
]

# Sort versions
sorted_versions = sorted(versions, key=Version)
```

### Epoch Comparison

Epochs override all other version components:

```python
"1!0.0" > "99.99.99"  # True - epoch 1 is higher
"2!0.0" > "1!99.99"   # True - epoch 2 > epoch 1
"0!2.0" < "1!1.0"     # True - epoch 0 < epoch 1
```

### Local Version Comparison

Local versions are higher than their base:

```python
"1.0+local" > "1.0"           # True
"1.0+a" < "1.0+b"            # True - alphabetical
"1.0+1" < "1.0+2"            # True - numerical
```

## Bumping Validation

### Valid Bump Sequences

Each bump type has validation rules:

#### Patch Bumps

```bash
# Valid patch bumps
"1.2.3" -> "1.2.4"    # Standard patch
"1.2" -> "1.2.1"      # From short form
"2024.1.1" -> "2024.1.2"  # Calendar versioning

# Invalid patch bumps
"1.2.3a1" -> ERROR    # Can't patch from pre-release
"1.2.3.dev0" -> ERROR # Can't patch from dev
```

#### Minor Bumps

```bash
# Valid minor bumps
"1.2.3" -> "1.3.0"    # Reset patch to 0
"1.2" -> "1.3.0"      # From short form

# Invalid minor bumps
"1.2.3b1" -> ERROR    # Can't bump from pre-release
```

#### Major Bumps

```bash
# Valid major bumps
"1.2.3" -> "2.0.0"    # Reset minor and patch
"0.9.9" -> "1.0.0"    # From 0.x to 1.0

# Invalid from pre-release
"2.0.0a1" -> ERROR    # Release first
```

### Pre-release Progression

Pre-releases must follow order:

```bash
# Valid progressions
"1.0a1" -> "1.0a2"    # Continue alpha
"1.0a2" -> "1.0b0"    # Alpha to beta
"1.0b1" -> "1.0rc0"   # Beta to RC
"1.0rc1" -> "1.0"     # RC to final

# Invalid progressions
"1.0b1" -> "1.0a1"    # Can't go backwards
"1.0rc1" -> "1.0b1"   # Can't downgrade stage
"1.0" -> "1.0a1"      # Can't add pre-release to final
```

## Validation in CI/CD

### GitHub Actions

```yaml
name: Validate Version

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install hatch packaging

      - name: Validate version format
        run: |
          python -c "
          import subprocess
          from packaging.version import Version, InvalidVersion

          # Get version from hatch
          result = subprocess.run(['hatch', 'version'], capture_output=True, text=True)
          version_str = result.stdout.strip()

          # Validate PEP 440
          try:
              v = Version(version_str)
              print(f'✓ Valid PEP 440 version: {v}')
          except InvalidVersion as e:
              print(f'✗ Invalid version: {e}')
              exit(1)

          # Check for common issues
          if version_str.startswith('v'):
              print('✗ Version should not start with v')
              exit(1)

          # Check version components
          if v.is_prerelease:
              print(f'ℹ Pre-release version: {v}')
          if v.is_postrelease:
              print(f'ℹ Post-release version: {v}')
          if v.is_devrelease:
              print(f'⚠ Development version: {v}')
          "

      - name: Check version bump
        if: github.event_name == 'pull_request'
        run: |
          python -c "
          import subprocess
          from packaging.version import Version

          # Get base branch version
          subprocess.run(['git', 'checkout', 'origin/main'], check=True)
          result = subprocess.run(['hatch', 'version'], capture_output=True, text=True)
          base_version = Version(result.stdout.strip())

          # Get PR version
          subprocess.run(['git', 'checkout', 'HEAD'], check=True)
          result = subprocess.run(['hatch', 'version'], capture_output=True, text=True)
          pr_version = Version(result.stdout.strip())

          # Validate bump
          if pr_version <= base_version:
              print(f'✗ Version not bumped: {base_version} -> {pr_version}')
              exit(1)

          print(f'✓ Version bumped: {base_version} -> {pr_version}')
          "
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-version
        name: Validate version format
        entry: python scripts/validate_version.py
        language: script
        files: pyproject.toml
```

```python
# scripts/validate_version.py
#!/usr/bin/env python3
import subprocess
import sys
from packaging.version import Version, InvalidVersion

def main():
    # Get current version
    result = subprocess.run(
        ["hatch", "version"],
        capture_output=True,
        text=True
    )
    version_str = result.stdout.strip()

    # Validate format
    try:
        version = Version(version_str)
    except InvalidVersion:
        print(f"ERROR: Invalid version format: {version_str}")
        return 1

    # Check for v prefix
    if version_str.startswith("v"):
        print("ERROR: Version should not start with 'v'")
        return 1

    # Warn about dev versions
    if version.is_devrelease:
        print(f"WARNING: Development version: {version}")

    print(f"✓ Valid version: {version}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Custom Validation Rules

### Organization-Specific Rules

```python
# validate_version_policy.py
from packaging.version import Version

def validate_version(version_str: str) -> bool:
    """Validate version against org policy."""
    version = Version(version_str)

    # Rule 1: No local versions in releases
    if version.local:
        print("ERROR: Local versions not allowed")
        return False

    # Rule 2: Must use 3-part versions
    parts = str(version.base_version).split(".")
    if len(parts) != 3:
        print("ERROR: Version must be X.Y.Z format")
        return False

    # Rule 3: Major version 0 only for beta
    if parts[0] == "0" and not version.is_prerelease:
        print("ERROR: Version 0.x must be pre-release")
        return False

    # Rule 4: No dev versions in main branch
    if version.is_devrelease:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip() == "main":
            print("ERROR: Dev versions not allowed on main")
            return False

    return True
```

### Calendar Versioning Validation

```python
def validate_calver(version_str: str) -> bool:
    """Validate calendar versioning format."""
    from datetime import datetime

    parts = version_str.split(".")
    if len(parts) != 3:
        return False

    try:
        year = int(parts[0])
        month = int(parts[1])
        patch = int(parts[2])
    except ValueError:
        return False

    # Validate year
    current_year = datetime.now().year
    if year < 2020 or year > current_year:
        print(f"ERROR: Invalid year: {year}")
        return False

    # Validate month
    if month < 1 or month > 12:
        print(f"ERROR: Invalid month: {month}")
        return False

    return True
```

## Version Normalization

Hatchling normalizes versions to canonical form:

### Normalization Rules

```python
# Input -> Normalized
"1.0"           -> "1.0.0"      # Pad with zeros
"1.0.0.0"       -> "1.0.0"      # Remove extra zeros
"1.0.alpha"     -> "1.0a0"      # Normalize pre-release
"1.0-beta"      -> "1.0b0"      # Fix separator
"1.0c1"         -> "1.0rc1"     # Normalize RC
"01.02.03"      -> "1.2.3"      # Remove leading zeros
"1.0.dev"       -> "1.0.dev0"   # Add pre-release number
```

### Validation vs Normalization

```python
from packaging.version import Version

# These are equivalent after normalization
assert Version("1.0") == Version("1.0.0")
assert Version("1.0a") == Version("1.0a0")
assert Version("1.0.dev") == Version("1.0.dev0")

# But the canonical form is:
assert str(Version("1.0")) == "1.0"  # No trailing zeros
assert str(Version("1.0a")) == "1.0a0"  # Explicit pre-release number
```

## Troubleshooting

### Common Validation Errors

| Error                         | Cause                 | Solution                                  |
| ----------------------------- | --------------------- | ----------------------------------------- |
| "Invalid version"             | Non-PEP 440 format    | Remove prefixes, fix format               |
| "Version not higher"          | validate-bump enabled | Use higher version or disable             |
| "Can't bump from pre-release" | Invalid bump type     | Use `release` first                       |
| "Unknown bump command"        | Typo in command       | Check available: patch, minor, major, etc |

### Debug Validation

```bash
# Check what version is detected
$ hatch version -v
Looking for version...
Found: 1.2.3

# Test version format
$ python -c "from packaging.version import Version; print(Version('1.2.3'))"
1.2.3

# Compare versions
$ python -c "
from packaging.version import Version
v1 = Version('1.2.3')
v2 = Version('1.2.4')
print(f'{v1} < {v2}: {v1 < v2}')
"
```

## Best Practices

1. **Always Use PEP 440**: Stick to standard formats for compatibility
2. **Enable validate-bump**: Prevent accidental downgrades
3. **Automate Validation**: Add CI checks for all version changes
4. **Document Policy**: Create clear versioning guidelines
5. **Test Bumping**: Verify bump commands work correctly
6. **No Manual Editing**: Use `hatch version` commands
7. **Pre-release for Testing**: Use alpha/beta/rc for test releases

## See Also

- `version-schemes.md`
- `version-cli.md`
- [PEP 440 Specification](https://peps.python.org/pep-0440/)
- [Semantic Versioning](https://semver.org/)
