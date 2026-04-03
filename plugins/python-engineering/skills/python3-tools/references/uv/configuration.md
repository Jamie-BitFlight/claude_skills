# uv Configuration Reference

Complete configuration guide for uv (v0.10.2).

## Configuration Files

### File Discovery Hierarchy

1. **Project-level** (current or parent directories):

   - `pyproject.toml` (under `[tool.uv]`)
   - `uv.toml` (no prefix required)

2. **User-level**:

   - Linux/macOS: `~/.config/uv/uv.toml`
   - Windows: `%APPDATA%\uv\uv.toml`

3. **System-level**:
   - Linux/macOS: `/etc/uv/uv.toml`
   - Windows: `%PROGRAMDATA%\uv\uv.toml`

### Precedence Order

1. Command-line arguments (highest)
2. Environment variables
3. Project-level configuration
4. User-level configuration
5. System-level configuration (lowest)

**Note**: `uv.toml` takes precedence over `pyproject.toml` in same directory.

## pyproject.toml Configuration

### Project Metadata

```toml
[project]
name = "myproject"
version = "1.0.0"
description = "Project description"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "fastapi>=0.115",
]

# Preferred: Use PEP 735 dependency groups
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "ruff>=0.13.3",
    "mypy>=1.18.2",
]
docs = ["sphinx", "mkdocs"]
test = ["pytest-cov", "hypothesis"]

# Alternative: project.optional-dependencies (older pattern)
# [project.optional-dependencies]
# dev = ["pytest>=8.3", "ruff>=0.5"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Core uv Settings

```toml
[tool.uv]
# Project management
managed = true              # uv manages project
package = true              # Project is Python package
default-groups = ["dev"]    # Default dependency groups

# Resolution
resolution = "highest"      # highest/lowest/lowest-direct
fork-strategy = "requires-python"  # requires-python/fewest
index-strategy = "first-index"     # first-index/unsafe-first-match/unsafe-best-match

# Environment restrictions
environments = [
    "sys_platform == 'darwin'",
    "sys_platform == 'linux'",
]

# Dependency constraints
constraint-dependencies = ["grpcio<1.65"]
override-dependencies = ["werkzeug==2.3.0"]

# Build configuration
compile-bytecode = true
no-build-isolation-package = ["flash-attn"]
config-settings = { editable_mode = "compat" }

# Cache configuration
cache-dir = "./.uv_cache"
cache-keys = [
    { file = "pyproject.toml" },
    { git = { commit = true } },
]

# Network configuration
concurrent-downloads = 20
concurrent-builds = 8
offline = false

# Python management
python-preference = "managed"  # only-managed/managed/system/only-system
python-downloads = "automatic"  # automatic/manual/never

# Security
keyring-provider = "subprocess"  # subprocess/disabled
allow-insecure-host = ["packages.example.com"]

# Dependency exclusions (0.9.8+)
dependency-exclusions = ["unwanted-package"]

# PyTorch accelerator backend (0.9.18+ in config)
torch-backend = "auto"  # or "cu121", "rocm7.0", "rocm7.1", "cpu"

# Git LFS (0.9.15+)
git-lfs = true

# Preview features
preview = true
```

### Package Indexes

**Breaking (0.10.0)**: Multiple `default = true` indexes now error. Unnamed `explicit` indexes now error (must have a `name`).

```toml
[[tool.uv.index]]
name = "pytorch-cu121"
url = "https://download.pytorch.org/whl/cu121"
explicit = true              # Require explicit pinning (must have name)
default = false              # Replace PyPI as default (only one allowed)
authenticate = "always"      # always/never
cache-control = "max-age=3600"

[[tool.uv.index]]
name = "private-registry"
url = "https://packages.example.com/simple"
explicit = true
```

### Dependency Sources

```toml
[tool.uv.sources]
# Workspace dependencies
internal-lib = { workspace = true }

# Git repositories
httpx = { git = "https://github.com/encode/httpx" }
fastapi = { git = "https://github.com/tiangolo/fastapi", branch = "main" }
requests = { git = "https://github.com/psf/requests", tag = "v2.31.0" }

# Local paths
local-pkg = { path = "../local-pkg" }
editable-pkg = { path = "./pkg", editable = true }

# URLs
package-url = { url = "https://example.com/package.tar.gz" }

# Index pinning
torch = { index = "pytorch-cu121" }

# Conditional sources
package = [
    { index = "linux-index", marker = "sys_platform == 'linux'" },
    { index = "macos-index", marker = "sys_platform == 'darwin'" },
]
```

### Workspace Configuration

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
exclude = ["packages/deprecated"]
```

### Build Configuration

```toml
[tool.uv]
# Build isolation control
no-build-isolation-package = ["flash-attn", "deepspeed"]

# Extra build dependencies
[tool.uv.extra-build-dependencies]
flash-attn = ["torch", "setuptools"]
deepspeed = [{ requirement = "torch", match-runtime = true }]

# Build environment variables
[tool.uv.extra-build-variables]
flash-attn = { FLASH_ATTENTION_SKIP_CUDA_BUILD = "TRUE" }
opencv-python = { CMAKE_ARGS = "-DWITH_CUDA=ON" }

# Dependency metadata (for packages without proper metadata)
[[tool.uv.dependency-metadata]]
name = "package-name"
version = "1.0.0"
requires-dist = ["dependency1>=1.0"]
requires-python = ">=3.8"

# Per-package build settings
[tool.uv.config-settings-package]
numpy = { editable_mode = "compat" }
scipy = { use_system_blas = "true" }

# Build constraints
build-constraint-dependencies = ["setuptools==60.0.0"]
```

### Conflict Resolution

```toml
[tool.uv]
# Declare mutually exclusive extras/groups
conflicts = [
    [
        { extra = "cuda" },
        { extra = "rocm" },
    ],
    [
        { group = "prod" },
        { group = "dev" },
    ],
]
```

### pip-Specific Settings

```toml
[tool.uv.pip]
compile-bytecode = true
strict = true
generate-hashes = true
annotation-style = "line"      # line/split
extra = ["dev", "test"]
output-file = "requirements.txt"
break-system-packages = false
no-strip-markers = false
universal = false
```

## Environment Variables

### Core Configuration

```bash
# Directories
UV_CACHE_DIR=/custom/cache
UV_PROJECT_ENVIRONMENT=.venv
UV_WORKING_DIR=/path/to/project  # Preferred name since 0.9.14

# Configuration
UV_CONFIG_FILE=/path/to/uv.toml
UV_NO_CONFIG=1

# Python management
UV_PYTHON=3.11
UV_PYTHON_PREFERENCE=managed     # only-managed/managed/system/only-system
UV_PYTHON_DOWNLOADS=automatic    # automatic/manual/never
UV_PYTHON_INSTALL_DIR=~/.python
UV_MANAGED_PYTHON=1
UV_SYSTEM_PYTHON=1
```

### Network and Performance

```bash
# Downloads and builds
UV_CONCURRENT_DOWNLOADS=20
UV_CONCURRENT_BUILDS=8
UV_CONCURRENT_INSTALLS=4
UV_HTTP_TIMEOUT=30
UV_HTTP_RETRIES=3

# Network control
UV_OFFLINE=1
UV_NO_CACHE=1
```

### Index Configuration

```bash
# Primary index
UV_DEFAULT_INDEX=https://pypi.org/simple
UV_INDEX_URL=https://pypi.org/simple  # Deprecated

# Additional indexes
UV_INDEX="name1=https://index1.com name2=https://index2.com"
UV_EXTRA_INDEX_URL=https://custom.index.com  # Deprecated

# Index authentication
UV_INDEX_PRIVATE_REGISTRY_USERNAME=user
UV_INDEX_PRIVATE_REGISTRY_PASSWORD=pass
```

### Build Configuration

```bash
# Build control
UV_COMPILE_BYTECODE=1
UV_NO_BUILD_ISOLATION=1
UV_NO_BUILD=1
UV_NO_BUILD_PACKAGE="numpy scipy"
UV_NO_BINARY=1
UV_NO_BINARY_PACKAGE="numpy scipy"
UV_CONFIG_SETTINGS='{"editable_mode": "compat"}'

# Build constraints
UV_BUILD_CONSTRAINT=/path/to/constraints.txt
```

### Resolution Control

```bash
# Resolution strategy
UV_RESOLUTION=highest          # highest/lowest/lowest-direct
UV_PRERELEASE=if-necessary     # allow/disallow/if-necessary/if-necessary-or-explicit
UV_EXCLUDE_NEWER=2025-01-01T00:00:00Z  # Also supports relative: "2 days ago", "1w" (0.9.17+)

# Lock and sync
UV_FROZEN=1
UV_LOCKED=1
UV_NO_SYNC=1

# Dependencies
UV_DEV=1
UV_NO_DEV=1
UV_NO_EDITABLE=1
```

### Security

```bash
# Authentication
UV_KEYRING_PROVIDER=subprocess  # subprocess/disabled
UV_NATIVE_TLS=1

# Insecure hosts
UV_INSECURE_HOST="host1.com host2.com"

# Publishing
UV_PUBLISH_USERNAME=__token__
UV_PUBLISH_PASSWORD=$PYPI_TOKEN
UV_PUBLISH_TOKEN=$PYPI_TOKEN
UV_TRUSTED_PUBLISHING=automatic
```

### Output Control

```bash
# Output format
UV_NO_PROGRESS=1
UV_NO_WRAP=1
UV_QUIET=1
UV_VERBOSE=1
UV_COLOR=always  # always/never/auto
UV_LOG_CONTEXT=1
```

### Tool Management

```bash
UV_TOOL_DIR=~/.local/share/uv/tools
UV_TOOL_BIN_DIR=~/.local/bin
```

### Dependency Groups (0.9.8+)

```bash
UV_NO_GROUP="docs"             # Exclude specific groups
UV_NO_SOURCES=1                # Ignore [tool.uv.sources]
UV_NO_DEFAULT_GROUPS=1         # Skip default dependency groups
```

### Virtual Environment (0.10.0+)

```bash
UV_VENV_CLEAR=1                # Auto-remove existing venvs on uv venv
```

### Build Output (0.9.15+)

```bash
UV_HIDE_BUILD_OUTPUT=1         # Suppress build log output
```

### Git LFS (0.9.15+)

```bash
UV_GIT_LFS=1                  # Enable Git LFS for dependencies
```

### PyTorch Backend

```bash
UV_TORCH_BACKEND="cu121"      # Accelerator backend (cu121/rocm7.0/rocm7.1/cpu/auto)
```

### SSL Certificates (0.9.10+)

```bash
SSL_CERT_DIR="/path/to/certs"  # Custom CA certificate directory
```

### Preview Features

```bash
UV_PREVIEW=1
UV_PREVIEW_FEATURES=feature1,feature2
```

### Advanced Settings

```bash
# Installation
UV_LINK_MODE=copy           # clone/copy/hardlink/symlink
UV_REINSTALL=1
UV_UPGRADE=1
UV_NO_INDEX=1
UV_ISOLATED=1

# Environment files
UV_ENV_FILE=.env.production
UV_NO_ENV_FILE=1

# S3 support (preview)
UV_S3_ENDPOINT_URL=https://s3.amazonaws.com

# Mirrors
UV_PYTHON_INSTALL_MIRROR=https://mirror.example.com
UV_PYPY_INSTALL_MIRROR=https://pypy-mirror.example.com

# Debug
RUST_LOG=uv=debug
RUST_BACKTRACE=1
```

## Complete Example Configuration

```toml
[project]
name = "myproject"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "torch"]

# Preferred: Use PEP 735 dependency groups
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "ruff>=0.13.3",
    "mypy>=1.18.2",
]
test = ["pytest-cov", "pytest-asyncio"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
# Project configuration
managed = true
package = true
default-groups = ["dev"]

# Resolution
resolution = "highest"
fork-strategy = "requires-python"
index-strategy = "first-index"

# Environment restrictions
environments = ["sys_platform == 'linux'"]
required-environments = ["sys_platform == 'linux' and platform_machine == 'x86_64'"]

# Constraints
constraint-dependencies = ["grpcio<1.65"]
override-dependencies = ["werkzeug==2.3.0"]
build-constraint-dependencies = ["setuptools==60.0.0"]

# Build configuration
compile-bytecode = true
no-build-isolation-package = ["flash-attn"]
config-settings = { editable_mode = "compat" }

# Cache configuration
cache-dir = "./.uv_cache"
cache-keys = [
    { file = "pyproject.toml" },
    { git = { commit = true } },
]

# Network
concurrent-downloads = 20
concurrent-builds = 8

# Python management
python-preference = "managed"
python-downloads = "automatic"

# Security
keyring-provider = "subprocess"

# Preview features
preview = true

# Extra build configuration
[tool.uv.extra-build-dependencies]
flash-attn = [{ requirement = "torch", match-runtime = true }]

[tool.uv.extra-build-variables]
flash-attn = { FLASH_ATTENTION_SKIP_CUDA_BUILD = "TRUE" }

# Package sources
[tool.uv.sources]
torch = { index = "pytorch-cu121" }
internal-lib = { workspace = true }

# Custom indexes
[[tool.uv.index]]
name = "pytorch-cu121"
url = "https://download.pytorch.org/whl/cu121"
explicit = true

[[tool.uv.index]]
name = "private"
url = "https://packages.example.com/simple"
authenticate = "always"

# Workspace configuration
[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/deprecated"]

# pip-specific settings
[tool.uv.pip]
compile-bytecode = true
strict = true
generate-hashes = false

# Conflict resolution
[[tool.uv.conflicts]]
extra = ["cuda", "rocm"]
```

## Configuration Best Practices

1. **Project vs User Config**: Keep project-specific settings in `pyproject.toml`, user preferences in `~/.config/uv/uv.toml`
2. **Security**: Never commit credentials to version control, use environment variables
3. **Index Pinning**: Use `explicit = true` for custom indexes to prevent accidents
4. **Build Isolation**: Only disable for problematic packages, document why
5. **Cache**: Use project-local cache (`.uv_cache`) for CI reproducibility
6. **Python Preference**: Use `managed` for consistent team environments
7. **Lockfiles**: Always commit `uv.lock` for reproducible installs
8. **Environment Restrictions**: Use `environments` to prevent platform-specific resolution issues
9. **Preview Features**: Test in development before enabling in production

## uv.toml Format

`uv.toml` uses same structure as `pyproject.toml` but **without** `[tool.uv]` prefix:

```toml
# uv.toml (no [tool.uv] prefix)
managed = true
resolution = "highest"
compile-bytecode = true

[[index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cpu"
```

Equivalent to:

```toml
# pyproject.toml (with [tool.uv] prefix)
[tool.uv]
managed = true
resolution = "highest"
compile-bytecode = true

[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cpu"
```
