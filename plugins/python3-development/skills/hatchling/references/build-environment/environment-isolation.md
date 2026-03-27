---
category: build-environment
topics: [isolation, reproducible-builds, virtual-environments, ci-cd]
related: [build-environment-configuration.md, build-dependencies-management.md, environment-variables.md, uv-vs-pip-installer.md]
---

# Environment Isolation

## Overview

Reference this guide when helping users understand environment isolation in hatchling, which ensures that builds are reproducible, dependencies don't conflict, and the build environment remains clean. This document covers all aspects of build isolation, virtual environments, and dependency management strategies.

## Build Isolation Concepts

### What is Build Isolation?

Build isolation means that:

1. Build dependencies are installed in a temporary environment
2. The build process doesn't affect the system Python
3. Dependencies are resolved independently
4. Builds are reproducible across different systems

### Default Behavior

By default, hatchling uses build isolation:

- Creates temporary virtual environment
- Installs build requirements
- Runs build in isolated environment
- Cleans up after completion

```bash
# Default: with isolation
hatch build

# Equivalent to:
pip install --use-pep517 .
```

## Isolation Configuration

### Enabling/Disabling Isolation

```bash
# Build with isolation (default)
hatch build

# Build without isolation
hatch build --no-isolation

# Using pip
pip install .  # With isolation (default)
pip install --no-build-isolation .  # Without isolation
```

### When to Disable Isolation

Disable isolation for:

- Debugging build issues
- Using system-installed build tools
- CI/CD with pre-configured environments
- Development with editable installs

```bash
# Development setup without isolation
pip install --no-build-isolation -e .
```

## Virtual Environment Management

### Environment Types

```toml
[tool.hatch.envs.hatch-build]
type = "virtual"  # Default: virtual environment
```

### Environment Location

```toml
[tool.hatch.envs.hatch-build]
# Explicit path
path = ".venv/build"

# Or use environment variable
# HATCH_ENV_TYPE_VIRTUAL_PATH=/custom/path
```

### System Packages Access

```toml
[tool.hatch.envs.hatch-build]
# Allow access to system site-packages
system-packages = false  # Default: isolated

# Or allow system packages
system-packages = true
```

### Python Version Selection

```toml
[tool.hatch.envs.hatch-build]
# Specific Python version
python = "3.11"

# Use current Python
python = "self"

# Multiple versions (for matrix)
python = ["3.9", "3.10", "3.11"]
```

## Dependency Isolation Strategies

### Strict Isolation

Complete isolation from system packages:

```toml
[tool.hatch.envs.hatch-build]
system-packages = false
skip-install = false
dev-mode = false
```

### Partial Isolation

Use some system packages:

```toml
[tool.hatch.envs.hatch-build]
system-packages = true  # Access system packages
dependencies = [
  "cython>=3.0.0",  # But ensure specific versions
  "numpy>=1.24.0",
]
```

### Detached Environment

Self-contained environment:

```toml
[tool.hatch.envs.hatch-build]
detached = true  # Self-referential
skip-install = true  # Don't install project
```

## Reproducible Builds

### Timestamp Control

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Fixed timestamp for reproducibility
SOURCE_DATE_EPOCH = "1580601600"

# Deterministic Python behavior
PYTHONHASHSEED = "0"
PYTHONDONTWRITEBYTECODE = "1"
```

### Dependency Pinning

```toml
[build-system]
# Pin exact versions
requires = [
  "hatchling==1.25.0",
  "cython==3.0.0",
  "numpy==1.24.3",
]

[tool.hatch.envs.hatch-build]
dependencies = [
  "setuptools==68.0.0",
  "wheel==0.41.0",
]
```

### Lock Files

Using constraints:

```toml
[tool.hatch.envs.hatch-build.env-vars]
PIP_CONSTRAINT = "constraints.txt"
UV_CONSTRAINT = "constraints.txt"
```

`constraints.txt`:

<eg>
cython==3.0.0
numpy==1.24.3
setuptools==68.0.0
wheel==0.41.0
</eg>

## Container-Based Isolation

### Docker Build Environment

`Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install hatch
RUN pip install hatch

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Build with isolation
RUN hatch build
```

### Multi-Stage Build

```dockerfile
# Build stage
FROM python:3.11-slim AS builder

RUN pip install hatch
WORKDIR /app
COPY . .
RUN hatch build

# Runtime stage
FROM python:3.11-slim

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

CMD ["python", "-m", "myapp"]
```

## CI/CD Isolation

### GitHub Actions

```yaml
name: Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install hatch

      - name: Build with isolation
        run: hatch build

      - name: Test installation
        run: |
          pip install dist/*.whl
          python -c "import mypackage; print(mypackage.__version__)"
```

### GitLab CI

```yaml
stages:
  - build
  - test

build:
  stage: build
  image: python:3.11
  script:
    - pip install hatch
    - hatch build
  artifacts:
    paths:
      - dist/

test-install:
  stage: test
  image: python:3.11
  needs: [build]
  script:
    - pip install dist/*.whl
    - python -m pytest tests/
```

## Development vs Production Isolation

### Development Environment

```toml
[tool.hatch.envs.dev]
# Less strict for development
system-packages = true  # Use system packages
dev-mode = true  # Editable install
skip-install = false  # Install project

dependencies = [
  "pytest>=7.0",
  "black>=23.0",
  "ruff>=0.1.0",
]
```

### Production Build

```toml
[tool.hatch.envs.hatch-build]
# Strict for production
system-packages = false  # Full isolation
dev-mode = false  # Not editable
installer = "pip"  # Conservative installer

dependencies = [
  # Only essential build deps
  "cython==3.0.0",
  "numpy==1.24.3",
]
```

## Caching Strategies

### Dependency Caching

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Cache directories
PIP_CACHE_DIR = "{env:HOME}/.cache/pip"
UV_CACHE_DIR = "{env:HOME}/.cache/uv"

# Disable cache for full isolation
PIP_NO_CACHE_DIR = "0"  # Enable cache
UV_NO_CACHE = "0"  # Enable cache
```

### Build Cache

```bash
# Use build cache
export HATCH_BUILD_LOCATION=/tmp/build-cache
hatch build

# Clear cache
rm -rf /tmp/build-cache
```

### CI Cache

GitHub Actions:

```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.cache/uv
      ~/.local/share/hatch
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
```

## Network Isolation

### Offline Builds

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Use local index only
PIP_INDEX_URL = "file:///local/pypi/simple"
UV_INDEX_URL = "file:///local/pypi/simple"

# No network access
PIP_NO_INDEX = "1"
UV_OFFLINE = "1"
```

### Private Indexes

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Private index with authentication
PIP_INDEX_URL = "https://user:pass@private.pypi/simple/"
PIP_TRUSTED_HOST = "private.pypi"

# Multiple indexes
PIP_EXTRA_INDEX_URL = "https://backup.pypi/simple/"
```

## Security Considerations

### Hash Verification

```toml
[project]
dependencies = [
  "requests @ https://files.pythonhosted.org/packages/requests-2.28.0.tar.gz#sha256=abc123...",
]

[tool.hatch.metadata]
allow-direct-references = true
```

### Signed Packages

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Require package signatures
PIP_REQUIRE_VIRTUALENV = "1"
PIP_DISABLE_PIP_VERSION_CHECK = "1"
```

## Troubleshooting Isolation Issues

### Common Problems

1. **Missing System Dependencies**:

   ```toml
   # Allow system packages temporarily
   [tool.hatch.envs.hatch-build]
   system-packages = true
   ```

2. **Conflicting Dependencies**:

   ```bash
   # Debug without isolation
   pip install --no-build-isolation -v .
   ```

3. **Permission Issues**:

   ```bash
   # Use user installation
   pip install --user --no-build-isolation .
   ```

4. **Network Issues**:
   ```toml
   [tool.hatch.envs.hatch-build.env-vars]
   # Use proxy
   HTTP_PROXY = "http://proxy.example.com:8080"
   HTTPS_PROXY = "http://proxy.example.com:8080"
   ```

### Debugging Commands

```bash
# Show environment details
hatch env show hatch-build

# List installed packages
hatch run -e hatch-build pip list

# Show dependency tree
hatch run -e hatch-build pip show numpy

# Clean environment
hatch env remove hatch-build
hatch env create hatch-build
```

## Complete Isolation Example

```toml
[build-system]
requires = [
  "hatchling==1.25.0",
  "cython==3.0.0",
  "numpy==1.24.3",
]
build-backend = "hatchling.build"

[tool.hatch.envs.hatch-build]
# Full isolation
type = "virtual"
system-packages = false
dev-mode = false
skip-install = false
detached = false

# Fixed Python version
python = "3.11"

# Pinned dependencies
dependencies = [
  "setuptools==68.0.0",
  "wheel==0.41.0",
]

# Use pip for stability
installer = "pip"

[tool.hatch.envs.hatch-build.env-vars]
# Reproducible builds
SOURCE_DATE_EPOCH = "1580601600"
PYTHONHASHSEED = "0"

# Isolated package index
PIP_INDEX_URL = "https://pypi.org/simple/"
PIP_TRUSTED_HOST = ""

# No system packages
PIP_REQUIRE_VIRTUALENV = "1"

# Cache configuration
PIP_CACHE_DIR = "/tmp/pip-cache"
PIP_NO_CACHE_DIR = "0"

# Security
PIP_DISABLE_PIP_VERSION_CHECK = "1"
```

## Best Practices

1. **Use Build Isolation by Default**: Ensures reproducibility
2. **Pin Dependencies for Production**: Exact versions prevent surprises
3. **Test Without Isolation**: Helps debug issues
4. **Cache Dependencies in CI**: Speeds up builds
5. **Use Containers for Complex Builds**: Complete environment control
6. **Document System Requirements**: List non-Python dependencies
7. **Separate Dev and Build Environments**: Different requirements
8. **Regular Dependency Updates**: Keep security patches current

## Related Topics

- `build-environment-configuration.md`
- `build-dependencies-management.md`
- `uv-vs-pip-installer.md`
- `environment-variables.md`
