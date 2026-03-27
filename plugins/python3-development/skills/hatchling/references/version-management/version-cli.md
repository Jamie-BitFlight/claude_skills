---
title: Version CLI Commands
description: Display and manage project versions via command line. Covers displaying versions, setting specific versions, version bumping operations, and force flags.
---

# Version CLI Commands

The `hatch version` command provides a powerful interface for displaying and managing project versions from the command line. It works with both static and dynamic version configurations.

## Basic Usage

### Display Current Version

Show the current project version:

```bash
$ hatch version
1.2.3
```

With verbose output:

```bash
$ hatch version -v
Looking for version in pyproject.toml
Found static version: 1.2.3
1.2.3
```

## Setting Versions

### Set Specific Version

Set an exact version:

```bash
$ hatch version "2.0.0"
Old: 1.2.3
New: 2.0.0
```

### Force Version Changes

Override validation with `--force`:

```bash
# Allow downgrade (normally prevented)
$ hatch version --force "1.0.0"
Old: 2.0.0
New: 1.0.0
```

## Version Bumping

### Basic Segments

Increment version segments:

```bash
# Patch: 1.2.3 -> 1.2.4
$ hatch version patch
Old: 1.2.3
New: 1.2.4

# Minor: 1.2.4 -> 1.3.0
$ hatch version minor
Old: 1.2.4
New: 1.3.0

# Major: 1.3.0 -> 2.0.0
$ hatch version major
Old: 1.3.0
New: 2.0.0

# Micro (alias for patch): 2.0.0 -> 2.0.1
$ hatch version micro
Old: 2.0.0
New: 2.0.1
```

### Pre-release Commands

Manage pre-release versions:

```bash
# Alpha: 1.2.3 -> 1.2.4a0
$ hatch version alpha
Old: 1.2.3
New: 1.2.4a0

# Continue alpha: 1.2.4a0 -> 1.2.4a1
$ hatch version a
Old: 1.2.4a0
New: 1.2.4a1

# Beta: 1.2.4a1 -> 1.2.4b0
$ hatch version beta
Old: 1.2.4a1
New: 1.2.4b0

# Continue beta: 1.2.4b0 -> 1.2.4b1
$ hatch version b
Old: 1.2.4b0
New: 1.2.4b1

# Release candidate: 1.2.4b1 -> 1.2.4rc0
$ hatch version rc
Old: 1.2.4b1
New: 1.2.4rc0

# Continue RC: 1.2.4rc0 -> 1.2.4rc1
$ hatch version c
Old: 1.2.4rc0
New: 1.2.4rc1
```

### Development Releases

Manage development versions:

```bash
# Start dev: 1.2.3 -> 1.2.4.dev0
$ hatch version dev
Old: 1.2.3
New: 1.2.4.dev0

# Continue dev: 1.2.4.dev0 -> 1.2.4.dev1
$ hatch version dev
Old: 1.2.4.dev0
New: 1.2.4.dev1
```

### Post Releases

Create post-release versions:

```bash
# Post release: 1.2.3 -> 1.2.3.post0
$ hatch version post
Old: 1.2.3
New: 1.2.3.post0

# Continue post: 1.2.3.post0 -> 1.2.3.post1
$ hatch version post
Old: 1.2.3.post0
New: 1.2.3.post1
```

### Release Command

Convert pre-release to final:

```bash
# From alpha to final: 1.2.4a1 -> 1.2.4
$ hatch version release
Old: 1.2.4a1
New: 1.2.4

# From RC to final: 2.0.0rc3 -> 2.0.0
$ hatch version release
Old: 2.0.0rc3
New: 2.0.0

# From dev to final: 1.2.4.dev5 -> 1.2.4
$ hatch version release
Old: 1.2.4.dev5
New: 1.2.4
```

## Combined Commands

### Comma-Separated Commands

Execute multiple bumps in sequence:

```bash
# Bump minor and start alpha
$ hatch version minor,alpha
Old: 1.2.3
New: 1.3.0a0

# Bump major and start beta
$ hatch version major,beta
Old: 1.3.0a0
New: 2.0.0b0

# Bump patch and start RC
$ hatch version patch,rc
Old: 2.0.0b0
New: 2.0.1rc0

# Multiple pre-release stages
$ hatch version minor,alpha,alpha,alpha
Old: 1.2.3
New: 1.3.0a2
```

### Complex Version Workflows

Full release cycle example:

```bash
# Start from stable
$ hatch version
1.2.3

# Begin next minor version development
$ hatch version minor,dev
Old: 1.2.3
New: 1.3.0.dev0

# Development iterations
$ hatch version dev
Old: 1.3.0.dev0
New: 1.3.0.dev1

# Move to alpha
$ hatch version release,alpha
Old: 1.3.0.dev1
New: 1.3.0a0

# Alpha iterations
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

## Command Options

### Global Options

```bash
# Verbose output
$ hatch version -v
$ hatch version --verbose

# Quiet mode (no output except version)
$ hatch -q version
$ hatch --quiet version

# Help
$ hatch version --help
```

### Force Option

Override safety checks:

```bash
# Force downgrade
$ hatch version --force "0.1.0"

# Force invalid version (not recommended)
$ hatch version --force "not-a-version"
```

## Version Source Compatibility

### Static Versions

Works with static versions in `pyproject.toml`:

```toml
[project]
version = "1.2.3"
```

```bash
$ hatch version patch
# Updates pyproject.toml directly
```

### Dynamic Versions

Works with all dynamic sources:

#### Regex Source

```toml
[tool.hatch.version]
source = "regex"
path = "src/__about__.py"
```

```bash
$ hatch version minor
# Updates the file specified in path
```

#### Code Source

```toml
[tool.hatch.version]
source = "code"
path = "version.py"
```

```bash
$ hatch version major
# Calls set_version() in version.py if available
```

#### Environment Source

```toml
[tool.hatch.version]
source = "env"
variable = "VERSION"
```

```bash
$ hatch version
# Displays version from environment
$ hatch version patch
Error: Environment source doesn't support setting versions
```

## Working Directory

The `hatch version` command must be run from:

- Project root (contains `pyproject.toml`)
- Any subdirectory of the project

```bash
# From project root
/my-project$ hatch version
1.2.3

# From subdirectory
/my-project/src$ hatch version
1.2.3

# From outside project (error)
/tmp$ hatch version
Error: Unable to find project root
```

## Error Messages and Solutions

### Version Not Found

```bash
$ hatch version
Error: Unable to find version
```

Solutions:

- Check `pyproject.toml` has version or dynamic version config
- Verify version source configuration
- Ensure version file exists if using regex/code source

### Invalid Version Format

```bash
$ hatch version "v1.2.3"
Error: Invalid version 'v1.2.3'
```

Solution: Remove 'v' prefix:

```bash
hatch version "1.2.3"
```

### Cannot Bump from Pre-release

```bash
# Current: 1.2.3a1
$ hatch version patch
Error: Cannot bump patch from pre-release
```

Solution: Release first, then bump:

```bash
hatch version release  # -> 1.2.3
hatch version patch    # -> 1.2.4
```

### Source Doesn't Support Setting

```bash
$ hatch version patch
Error: The 'env' source doesn't support setting versions
```

Solution: Update environment variable externally:

```bash
export VERSION="1.2.4"
```

## Scripting and Automation

### Get Version in Scripts

```bash
#!/bin/bash
# get-version.sh
VERSION=$(hatch version)
echo "Current version: $VERSION"
```

### Automated Version Bumping

```bash
#!/bin/bash
# bump-and-tag.sh

# Get bump type from argument
BUMP_TYPE=${1:-patch}

# Get old version
OLD_VERSION=$(hatch version)

# Bump version
hatch version $BUMP_TYPE

# Get new version
NEW_VERSION=$(hatch version)

# Create git commit and tag
git add pyproject.toml
git commit -m "Bump version from $OLD_VERSION to $NEW_VERSION"
git tag "v$NEW_VERSION"

echo "Version bumped from $OLD_VERSION to $NEW_VERSION"
```

### CI/CD Integration

```yaml
# .github/workflows/release.yml
name: Release

on:
  workflow_dispatch:
    inputs:
      bump:
        description: "Version bump type"
        required: true
        type: choice
        options:
          - patch
          - minor
          - major

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Hatch
        run: pip install hatch

      - name: Bump version
        run: |
          OLD_VERSION=$(hatch version)
          hatch version ${{ github.event.inputs.bump }}
          NEW_VERSION=$(hatch version)
          echo "OLD_VERSION=$OLD_VERSION" >> $GITHUB_ENV
          echo "NEW_VERSION=$NEW_VERSION" >> $GITHUB_ENV

      - name: Commit and tag
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Release v${{ env.NEW_VERSION }}"
          git tag "v${{ env.NEW_VERSION }}"
          git push origin main --tags
```

## Best Practices

### 1. Semantic Versioning

Follow semantic versioning principles:

```bash
# Bug fix -> patch
$ hatch version patch

# New feature -> minor
$ hatch version minor

# Breaking change -> major
$ hatch version major
```

### 2. Pre-release Testing

Use pre-releases for testing:

```bash
# Start testing cycle
$ hatch version minor,alpha

# Test iterations
$ hatch version alpha  # a0 -> a1
$ hatch version alpha  # a1 -> a2

# Ready for wider testing
$ hatch version beta

# Almost ready
$ hatch version rc

# Ship it!
$ hatch version release
```

### 3. Consistent Workflows

Document your versioning workflow:

```markdown
# Version Workflow

1. Feature development: `hatch version minor,dev`
2. Alpha testing: `hatch version alpha`
3. Beta testing: `hatch version beta`
4. Release candidate: `hatch version rc`
5. Production release: `hatch version release`
6. Hotfixes: `hatch version patch`
```

### 4. Version Verification

Always verify version changes:

```bash
# Check before
$ hatch version

# Make change
$ hatch version minor

# Verify change
$ hatch version

# Run tests
$ hatch run test
```

## See Also

- `static-version.md`
- `dynamic-version-overview.md`
- `version-schemes.md`
- `version-validation.md`
