---
title: Environment Version Source
description: Retrieve project versions from environment variables for CI/CD integration. Covers configuration, CI/CD workflows (GitHub, GitLab, Jenkins), Docker/Kubernetes integration, and best practices for external version management.
---

# Environment Version Source

The environment version source plugin retrieves project versions from environment variables. This approach is particularly useful for CI/CD pipelines, containerized deployments, and build systems where versions are determined externally.

## Basic Configuration

Configure the env source in your `pyproject.toml`:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "env"
variable = "MY_PROJECT_VERSION"
```

## Configuration Options

### Required Options

| Option     | Type   | Description                                             |
| ---------- | ------ | ------------------------------------------------------- |
| `variable` | string | Name of the environment variable containing the version |

### Optional Options

| Option    | Type   | Default | Description                            |
| --------- | ------ | ------- | -------------------------------------- |
| `default` | string | None    | Default version if variable is not set |

## Usage Patterns

### Simple Environment Variable

Basic usage with a single environment variable:

```toml
[tool.hatch.version]
source = "env"
variable = "VERSION"
```

```bash
# Set the version
export VERSION="1.2.3"

# Build the package
hatch build
```

### With Default Value

Provide a fallback when the variable isn't set:

```toml
[tool.hatch.version]
source = "env"
variable = "PACKAGE_VERSION"
default = "0.0.0+dev"
```

### CI/CD Specific Variables

Use CI/CD system variables directly:

```toml
# GitHub Actions
[tool.hatch.version]
source = "env"
variable = "GITHUB_REF_NAME"  # Uses git tag as version

# GitLab CI
[tool.hatch.version]
source = "env"
variable = "CI_COMMIT_TAG"  # Uses git tag as version

# Jenkins
[tool.hatch.version]
source = "env"
variable = "BUILD_VERSION"  # Custom Jenkins variable
```

## CI/CD Integration Examples

### GitHub Actions

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set version from tag
        run: |
          # Remove 'v' prefix from tag
          echo "PACKAGE_VERSION=${GITHUB_REF_NAME#v}" >> $GITHUB_ENV

      - name: Build package
        run: |
          pip install hatch
          hatch build

      - name: Publish to PyPI
        run: |
          hatch publish
```

```toml
# pyproject.toml
[tool.hatch.version]
source = "env"
variable = "PACKAGE_VERSION"
default = "0.0.0+dev"
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - deploy

variables:
  PROJECT_VERSION: ${CI_COMMIT_TAG}

build:
  stage: build
  script:
    - pip install hatch
    - hatch build
  only:
    - tags

deploy:
  stage: deploy
  script:
    - hatch publish
  only:
    - tags
```

```toml
# pyproject.toml
[tool.hatch.version]
source = "env"
variable = "PROJECT_VERSION"
```

### Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        BUILD_VERSION = "${env.TAG_NAME ?: '0.0.0+ci.' + env.BUILD_NUMBER}"
    }

    stages {
        stage('Build') {
            steps {
                sh '''
                    pip install hatch
                    hatch build
                '''
            }
        }

        stage('Publish') {
            when {
                tag pattern: "v\\d+\\.\\d+\\.\\d+", comparator: "REGEXP"
            }
            steps {
                sh 'hatch publish'
            }
        }
    }
}
```

```toml
# pyproject.toml
[tool.hatch.version]
source = "env"
variable = "BUILD_VERSION"
```

## Docker Integration

### Dockerfile with Build Args

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Accept version as build argument
ARG VERSION=0.0.0+docker
ENV PACKAGE_VERSION=$VERSION

WORKDIR /app
COPY . .

# Install and build
RUN pip install hatch && \
    hatch build && \
    pip install dist/*.whl

CMD ["python", "-m", "my_package"]
```

```bash
# Build with specific version
docker build --build-arg VERSION=1.2.3 -t my-app:1.2.3 .
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  app:
    build:
      context: .
      args:
        VERSION: ${VERSION:-0.0.0+dev}
    environment:
      - PACKAGE_VERSION=${VERSION:-0.0.0+dev}
```

```bash
# Run with version
VERSION=1.2.3 docker-compose up
```

## Development Workflows

### Local Development

Set up development environment with custom version:

```bash
# .env.local
export PACKAGE_VERSION="0.0.0+dev.$(git rev-parse --short HEAD)"

# Load environment
source .env.local

# Develop with current version
hatch run python -c "import my_package; print(my_package.__version__)"
# Output: 0.0.0+dev.abc1234
```

### Multiple Environments

Use different variables for different environments:

```toml
[tool.hatch.version]
source = "env"
variable = "VERSION"
default = "0.0.0+unknown"
```

```bash
# Development
VERSION="0.0.0+dev" hatch build

# Staging
VERSION="1.2.3-rc1" hatch build

# Production
VERSION="1.2.3" hatch build
```

## Version Formatting

### Cleaning Version Strings

Sometimes environment variables need processing:

```toml
# When variable contains 'v' prefix
[tool.hatch.version]
source = "env"
variable = "GIT_TAG"  # e.g., "v1.2.3"
```

Use a wrapper script to clean:

```bash
#!/bin/bash
# build.sh
export CLEAN_VERSION="${GIT_TAG#v}"  # Remove 'v' prefix
export PACKAGE_VERSION="$CLEAN_VERSION"
hatch build
```

### Version Validation

The env source validates versions against PEP 440:

```bash
# Valid versions
export VERSION="1.2.3"
export VERSION="1.0.0a1"
export VERSION="2023.12.1"
export VERSION="1.0.0+build.123"

# Invalid versions (will error)
export VERSION="v1.2.3"  # No 'v' prefix
export VERSION="1.2"     # Incomplete
export VERSION="latest"  # Not a version
```

## Automation Examples

### Automatic Versioning Script

```bash
#!/bin/bash
# scripts/auto-version.sh

# Determine version based on git state
if git describe --exact-match --tags HEAD 2>/dev/null; then
    # On a tag
    VERSION=$(git describe --exact-match --tags HEAD | sed 's/^v//')
elif [ -n "$CI_COMMIT_SHA" ]; then
    # In CI, use commit SHA
    VERSION="0.0.0+ci.$(echo $CI_COMMIT_SHA | cut -c1-8)"
else
    # Local development
    VERSION="0.0.0+dev.$(git rev-parse --short HEAD)"
fi

export PACKAGE_VERSION="$VERSION"
echo "Building version: $VERSION"
hatch build
```

### Pre-commit Hook

Ensure version is set before commits:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-version-env
        name: Check VERSION environment variable
        entry: sh -c 'test -n "$VERSION" || (echo "VERSION not set" && exit 1)'
        language: system
        pass_filenames: false
```

## Multi-Version Builds

Build multiple versions in CI:

```yaml
# .github/workflows/multi-version.yml
name: Multi-Version Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        version: ["1.0.0", "1.1.0", "2.0.0-beta"]

    steps:
      - uses: actions/checkout@v3

      - name: Build version ${{ matrix.version }}
        env:
          PACKAGE_VERSION: ${{ matrix.version }}
        run: |
          pip install hatch
          hatch build
          mkdir -p artifacts/${{ matrix.version }}
          mv dist/* artifacts/${{ matrix.version }}/

      - uses: actions/upload-artifact@v3
        with:
          name: packages
          path: artifacts/
```

## Kubernetes Integration

### ConfigMap Version

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  VERSION: "1.2.3"
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          image: my-app:latest
          envFrom:
            - configMapRef:
                name: app-config
```

### Helm Chart

```yaml
# helm/values.yaml
version: "1.2.3"
```

```yaml
# helm/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: { { .Release.Name } }
spec:
  template:
    spec:
      containers:
        - name: app
          env:
            - name: PACKAGE_VERSION
              value: { { .Values.version | quote } }
```

## Limitations

### Read-Only Source

The env source doesn't support setting versions:

```bash
$ hatch version patch
Error: The environment version source does not support setting the version
```

Workaround: Update the environment variable externally:

```bash
# Update version
export VERSION="1.2.4"

# Verify
hatch version
# Output: 1.2.4
```

### No Version Bumping

Unlike file-based sources, env source can't bump versions:

```bash
# This won't work
$ hatch version minor
Error: Cannot bump version with environment source
```

Solution: Implement version bumping in your CI/CD:

```bash
#!/bin/bash
# Bump version script
current_version="${VERSION:-0.0.0}"
IFS='.' read -ra parts <<< "$current_version"
parts[2]=$((parts[2] + 1))  # Bump patch
new_version="${parts[0]}.${parts[1]}.${parts[2]}"
export VERSION="$new_version"
```

## Best Practices

### 1. Always Provide Default Values

Prevent build failures by configuring sensible defaults:

```toml
[tool.hatch.version]
source = "env"
variable = "VERSION"
default = "0.0.0+unknown"
```

### 2. Document Required Variable Names

Clearly specify which environment variables are needed:

```toml
# pyproject.toml
[tool.hatch.version]
source = "env"
variable = "PACKAGE_VERSION"  # Set by CI/CD pipeline
default = "0.0.0+dev"  # Used in local development
```

### 3. Implement CI Validation

Add CI/CD checks to ensure version format compliance:

```yaml
# .github/workflows/check.yml
- name: Validate version
  run: |
    python -c "
    import os
    from packaging.version import Version, InvalidVersion
    try:
        v = Version(os.environ['VERSION'])
        print(f'Valid version: {v}')
    except InvalidVersion:
        print(f'Invalid version: {os.environ.get('VERSION', 'not set')}')
        exit(1)
    "
```

### 4. Use Descriptive and Project-Specific Variable Names

Choose clear names that identify the project:

```toml
# Good
variable = "MY_PACKAGE_VERSION"
variable = "WIDGET_LIB_VERSION"

# Avoid generic names
variable = "VERSION"  # Too generic
variable = "V"        # Too short
```

## Troubleshooting

### Variable Not Set

```bash
$ hatch version
Error: Environment variable 'VERSION' is not set
```

Solutions:

1. Set the variable: `export VERSION="1.2.3"`
2. Add a default: `default = "0.0.0+dev"`
3. Check variable name spelling

### Invalid Version Format

```bash
$ export VERSION="v1.2.3"
$ hatch version
Error: Invalid version 'v1.2.3'
```

Fix: Remove invalid characters:

```bash
export VERSION="1.2.3"  # No 'v' prefix
```

### Variable Not Updating

```bash
# Shell doesn't see updated variable
$ VERSION=1.2.3
$ hatch version
Error: Environment variable 'VERSION' is not set
```

Fix: Export the variable:

```bash
export VERSION=1.2.3
```

## Integration with Other Tools

### Poetry Migration

```toml
# From Poetry with poetry-dynamic-versioning
[tool.poetry-dynamic-versioning]
enable = true

# To Hatchling
[tool.hatch.version]
source = "env"
variable = "VERSION"
```

### Setuptools-scm Migration

```toml
# From setuptools-scm
[tool.setuptools_scm]
write_to = "src/_version.py"

# To Hatchling with env source
[tool.hatch.version]
source = "env"
variable = "SETUPTOOLS_SCM_PRETEND_VERSION"
```

## See Also

- `dynamic-version-overview.md`
- `code-version-source.md` - For programmatic version logic
- `regex-version-source.md` - For file-based versions
- `cicd-integration.md` - Advanced CI/CD patterns
