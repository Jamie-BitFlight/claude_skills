---
category: build-system
topics:
- environment-variables
- hatch-build-variables
- build-configuration
- ci-cd-variables
- hook-control
related:
- output-directory
- reproducible-builds
- build-hooks
---

# Environment Variables Guide for Claude

This reference helps Claude use environment variables to control Hatchling build behavior. These variables enable dynamic configuration without modifying `pyproject.toml`.

## Build Location Variables

### HATCH_BUILD_LOCATION

Override output directory:

```bash
# Set custom build directory
export HATCH_BUILD_LOCATION="/tmp/builds"
hatch build

# Inline usage
HATCH_BUILD_LOCATION="./artifacts" hatch build
```

This overrides:

```toml
[tool.hatch.build]
directory = "dist"  # Overridden by HATCH_BUILD_LOCATION
```

## Clean Build Variables

### HATCH_BUILD_CLEAN

Clean directory before building:

```bash
# Enable cleaning
export HATCH_BUILD_CLEAN=true
hatch build

# Accepted values
HATCH_BUILD_CLEAN=true    # Enable
HATCH_BUILD_CLEAN=1        # Enable
HATCH_BUILD_CLEAN=yes      # Enable
HATCH_BUILD_CLEAN=false    # Disable (default)
```

### HATCH_BUILD_CLEAN_HOOKS_AFTER

Clean after running hooks:

```bash
# Remove intermediate files after hooks
export HATCH_BUILD_CLEAN_HOOKS_AFTER=true
hatch build
```

Use cases:

- Remove temporary files from hooks
- Keep only final artifacts
- Reduce disk usage in CI

## Hook Control Variables

### HATCH_BUILD_NO_HOOKS

Disable all build hooks:

```bash
# Build without any hooks
export HATCH_BUILD_NO_HOOKS=true
hatch build

# For debugging
HATCH_BUILD_NO_HOOKS=1 hatch build --verbose
```

### HATCH_BUILD_HOOKS_ONLY

Run only hooks without building:

```bash
# Test hooks without building
export HATCH_BUILD_HOOKS_ONLY=true
hatch build

# Hook development workflow
HATCH_BUILD_HOOKS_ONLY=1 hatch build
```

### HATCH_BUILD_HOOKS_ENABLE

Enable specific hooks by name:

```bash
# Enable only specific hooks
export HATCH_BUILD_HOOKS_ENABLE="version,custom"
hatch build

# Comma-separated list
HATCH_BUILD_HOOKS_ENABLE="hook1,hook2,hook3" hatch build
```

### HATCH*BUILD_HOOK_ENABLE*<NAME>

Control individual hooks:

```bash
# Enable/disable specific hooks
export HATCH_BUILD_HOOK_ENABLE_CUSTOM=true
export HATCH_BUILD_HOOK_ENABLE_VERSION=false
hatch build

# Per-hook control
HATCH_BUILD_HOOK_ENABLE_MYAPP=1 hatch build
```

## Reproducible Build Variables

### SOURCE_DATE_EPOCH

Set consistent timestamps:

```bash
# Unix timestamp for reproducible builds
export SOURCE_DATE_EPOCH=1704067200  # 2024-01-01
hatch build

# From git commit
export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)
hatch build

# From specific date
export SOURCE_DATE_EPOCH=$(date -d "2024-01-01" +%s)
hatch build
```

Used when:

```toml
[tool.hatch.build]
reproducible = true  # Default
```

## Python Environment Variables

### HATCH_PYTHON

Control Python version:

```bash
# Use specific Python version
export HATCH_PYTHON=3.11
hatch build

# Use current Python
export HATCH_PYTHON=self
hatch build

# Use system Python
export HATCH_PYTHON=system
hatch build
```

### HATCH*PYTHON_VARIANT*\*

Configure Python variants:

```bash
# CPU optimization (Linux)
export HATCH_PYTHON_VARIANT_CPU=v3  # v1, v2, v3 (default), v4

# Free-threaded Python
export HATCH_PYTHON_VARIANT_GIL=freethreaded

# Combined
export HATCH_PYTHON_VARIANT_CPU=v4
export HATCH_PYTHON_VARIANT_GIL=freethreaded
hatch build
```

## CI/CD Integration Examples

### GitHub Actions

```yaml
env:
  HATCH_BUILD_LOCATION: ${{ github.workspace }}/artifacts
  SOURCE_DATE_EPOCH: ${{ github.event.head_commit.timestamp }}
  HATCH_BUILD_CLEAN: true

jobs:
  build:
    steps:
      - name: Build with environment
        run: hatch build
```

### GitLab CI

```yaml
variables:
  HATCH_BUILD_LOCATION: "${CI_PROJECT_DIR}/artifacts"
  SOURCE_DATE_EPOCH: "${CI_COMMIT_TIMESTAMP}"
  HATCH_BUILD_CLEAN: "true"

build:
  script:
    - hatch build
```

### Jenkins

```groovy
pipeline {
    environment {
        HATCH_BUILD_LOCATION = "${WORKSPACE}/build"
        HATCH_BUILD_CLEAN = "true"
        SOURCE_DATE_EPOCH = sh(
            returnStdout: true,
            script: 'git log -1 --pretty=%ct'
        ).trim()
    }
    stages {
        stage('Build') {
            steps {
                sh 'hatch build'
            }
        }
    }
}
```

## Platform-Specific Usage

### Windows

```batch
:: Windows batch
set HATCH_BUILD_LOCATION=C:\builds
set HATCH_BUILD_CLEAN=1
hatch build

:: PowerShell
$env:HATCH_BUILD_LOCATION = "C:\builds"
$env:HATCH_BUILD_CLEAN = "true"
hatch build
```

### Unix/Linux/macOS

```bash
# Bash/Zsh
export HATCH_BUILD_LOCATION=/tmp/builds
export HATCH_BUILD_CLEAN=true
hatch build

# Fish shell
set -x HATCH_BUILD_LOCATION /tmp/builds
set -x HATCH_BUILD_CLEAN true
hatch build
```

## Development Workflows

### Debug Build

No hooks, verbose output:

```bash
export HATCH_BUILD_NO_HOOKS=true
export HATCH_VERBOSE=true
hatch build
```

### Quick Build

Skip cleanup and hooks:

```bash
export HATCH_BUILD_CLEAN=false
export HATCH_BUILD_NO_HOOKS=true
hatch build
```

### Test Hooks

Only run specific hooks:

```bash
export HATCH_BUILD_HOOKS_ONLY=true
export HATCH_BUILD_HOOK_ENABLE_CUSTOM=true
hatch build
```

### Clean Build

Fresh build with cleaning:

```bash
export HATCH_BUILD_CLEAN=true
export HATCH_BUILD_CLEAN_HOOKS_AFTER=true
hatch build
```

## Variable Precedence

Help users understand priority:

1. Command-line arguments (when supported)
2. Environment variables
3. Configuration in `pyproject.toml`
4. Defaults

Example:

```bash
# Environment variable wins
export HATCH_BUILD_LOCATION="/override/path"

# This is overridden:
# [tool.hatch.build]
# directory = "dist"
```

## Common Patterns

### Development Setup

```bash
# .env.development
export HATCH_BUILD_LOCATION="./build"
export HATCH_BUILD_CLEAN=true
export HATCH_BUILD_NO_HOOKS=false
export SOURCE_DATE_EPOCH=$(date +%s)

# Usage
source .env.development
hatch build
```

### Production Build

```bash
# .env.production
export HATCH_BUILD_LOCATION="/var/builds"
export HATCH_BUILD_CLEAN=true
export HATCH_BUILD_HOOKS_ENABLE="version,validation"
export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)

# Usage
source .env.production
hatch build
```

### CI Environment

```bash
# ci-build.sh
#!/bin/bash

# Set all build variables
export HATCH_BUILD_LOCATION="${CI_ARTIFACTS_DIR}"
export HATCH_BUILD_CLEAN=true
export SOURCE_DATE_EPOCH="${CI_COMMIT_TIMESTAMP}"
export HATCH_BUILD_HOOK_ENABLE_TEST=false

# Build
hatch build
```

## Debugging Variables

### View Active Variables

```bash
# Print all HATCH variables
env | grep HATCH_

# Print build-related variables
env | grep -E '(HATCH_BUILD|SOURCE_DATE_EPOCH)'

# In Python
import os
for key, value in os.environ.items():
    if key.startswith('HATCH_'):
        print(f"{key}={value}")
```

### Test Variable Effects

```bash
# Test different configurations
for clean in true false; do
    for hooks in true false; do
        echo "Testing CLEAN=$clean HOOKS=$hooks"
        HATCH_BUILD_CLEAN=$clean \
        HATCH_BUILD_NO_HOOKS=$hooks \
        hatch build
    done
done
```

## Best Practices to Recommend

### Documentation

1. Document required variables in README
2. Provide example .env files
3. List CI/CD variables in docs

### Security

1. Don't expose secrets in variables
2. Use secret management for sensitive data
3. Validate variable values before use

### Consistency

1. Use consistent naming for custom variables
2. Provide defaults for optional variables
3. Test with various combinations

## Navigation

- `output-directory.md` - HATCH_BUILD_LOCATION details
- `reproducible-builds.md` - SOURCE_DATE_EPOCH usage
- `../build-hooks/environment-variables.md` - Hook-specific variables
