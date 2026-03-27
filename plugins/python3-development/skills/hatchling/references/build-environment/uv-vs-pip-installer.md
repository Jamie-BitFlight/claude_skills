---
category: build-environment
topics: [package-installers, uv, pip, performance, dependency-resolution]
related: [build-environment-configuration.md, build-dependencies-management.md, environment-variables.md]
---

# UV vs Pip Installer

## Overview

Reference this guide when helping users choose between the two package installers that hatchling supports for managing dependencies: UV (default) and pip. UV is a fast, Rust-based Python package installer and resolver that offers significant performance improvements over pip while maintaining compatibility.

## Quick Comparison

| Feature                   | UV                      | pip                       |
| ------------------------- | ----------------------- | ------------------------- |
| **Speed**                 | 10-100x faster          | Standard speed            |
| **Memory Usage**          | Lower                   | Higher for large projects |
| **Dependency Resolution** | Fast, deterministic     | Slower, can vary          |
| **Cache Management**      | Efficient, shared cache | Per-environment cache     |
| **Binary Wheel Support**  | Excellent               | Good                      |
| **Source Builds**         | Supported               | Native support            |
| **Compatibility**         | High (pip-compatible)   | Universal                 |
| **Default in Hatch**      | Yes (since 1.10.0)      | Was default before        |

## Configuration

### Using UV (Default)

UV is enabled by default in Hatch. No configuration needed:

```toml
# UV is used by default, no configuration required
```

Or explicitly:

```toml
[tool.hatch.envs.hatch-build]
installer = "uv"
```

### Using pip

To use pip instead of UV:

```toml
[tool.hatch.envs.hatch-build]
installer = "pip"
```

### Per-Environment Configuration

Different installers for different environments:

```toml
# Use UV for development (default)
[tool.hatch.envs.default]
installer = "uv"

# Use pip for testing environment
[tool.hatch.envs.test]
installer = "pip"

# Use pip for build environment
[tool.hatch.envs.hatch-build]
installer = "pip"
```

## UV Installer

### Advantages

1. **Speed**: 10-100x faster than pip
2. **Deterministic Resolution**: Consistent dependency resolution
3. **Efficient Caching**: Shared cache across environments
4. **Lower Memory Usage**: More efficient for large dependency trees
5. **Modern Architecture**: Written in Rust for performance
6. **Drop-in Replacement**: Compatible with pip commands

### UV-Specific Configuration

```toml
[tool.hatch.envs.default]
installer = "uv"

[tool.hatch.envs.default.env-vars]
# UV index configuration
UV_INDEX_URL = "https://pypi.org/simple/"
UV_EXTRA_INDEX_URL = "https://test.pypi.org/simple/"

# UV cache configuration
UV_CACHE_DIR = "/tmp/uv-cache"
UV_NO_CACHE = "0"  # Enable cache (default)

# UV behavior
UV_COMPILE_BYTECODE = "1"  # Compile .pyc files
UV_RESOLUTION_STRATEGY = "highest"  # or "lowest"
UV_PRERELEASE = "allow"  # or "disallow"
```

### External UV Management

Use your own UV installation:

```bash
# Set path to UV binary (implicitly enables UV)
export HATCH_ENV_TYPE_VIRTUAL_UV_PATH=/usr/local/bin/uv
```

### UV Version Control

Specify UV version:

```toml
[tool.hatch.envs.hatch-uv]
dependencies = [
  "uv>=0.2.0",
]
```

### UV with Private Indexes

```toml
[tool.hatch.envs.default.env-vars]
# GitLab Package Registry
UV_EXTRA_INDEX_URL = "https://token:{env:GITLAB_API_TOKEN}@gitlab.com/api/v4/groups/mygroup/-/packages/pypi/simple/"

# Multiple indexes
UV_INDEX_URL = "https://private.index/simple/ https://pypi.org/simple/"
```

### UV Command Aliases

Create pip-compatible commands:

```toml
[tool.hatch.envs.default.scripts]
pip = "{env:HATCH_UV} pip {args}"

# Or using extra scripts
[tool.hatch.envs.hatch-test.extra-scripts]
pip = "{env:HATCH_UV} pip {args}"
```

## Pip Installer

### Advantages

1. **Universal Compatibility**: Works everywhere Python works
2. **Mature Ecosystem**: Extensive documentation and support
3. **Source Builds**: Native support for building from source
4. **Legacy Support**: Better for older packages
5. **Familiar Interface**: Standard Python tool

### Pip-Specific Configuration

```toml
[tool.hatch.envs.default]
installer = "pip"

[tool.hatch.envs.default.env-vars]
# Pip index configuration
PIP_INDEX_URL = "https://pypi.org/simple/"
PIP_EXTRA_INDEX_URL = "https://test.pypi.org/simple/"

# Pip cache configuration
PIP_CACHE_DIR = "/tmp/pip-cache"
PIP_NO_CACHE_DIR = "0"  # Enable cache

# Pip behavior
PIP_COMPILE = "1"  # Compile .pyc files
PIP_PREFER_BINARY = "1"  # Prefer wheels
PIP_ONLY_BINARY = ":all:"  # Only use wheels
PIP_FORCE_REINSTALL = "0"  # Don't force reinstall
PIP_VERBOSE = "0"  # Verbosity level
```

### Pip with Private Indexes

```toml
[tool.hatch.envs.default.env-vars]
# Basic authentication
PIP_INDEX_URL = "https://user:password@private.index/simple/"

# Trusted host (for self-signed certificates)
PIP_TRUSTED_HOST = "private.index"

# Multiple indexes
PIP_EXTRA_INDEX_URL = "https://index1/simple/ https://index2/simple/"
```

### Pip Constraints

Using constraints file:

```toml
[tool.hatch.envs.default.env-vars]
PIP_CONSTRAINT = "constraints.txt"
```

## Performance Comparison

### Installation Speed

```bash
# UV (typical times)
Creating environment: 0.5s
Installing dependencies: 2-5s
Total: 3-6s

# pip (typical times)
Creating environment: 2s
Installing dependencies: 30-60s
Total: 32-62s
```

### Dependency Resolution

```bash
# Complex project with 100+ dependencies

# UV
Resolution time: 0.5-2s
Installation time: 3-5s
Memory usage: ~50MB

# pip
Resolution time: 10-30s
Installation time: 45-90s
Memory usage: ~200MB
```

## Use Case Recommendations

### When to Use UV

1. **Large Projects**: Many dependencies benefit from UV's speed
2. **CI/CD Pipelines**: Faster builds save time and money
3. **Development Environments**: Quick environment recreation
4. **Modern Projects**: Using recent package versions
5. **Reproducible Builds**: Deterministic resolution

### When to Use pip

1. **Legacy Projects**: Older packages may have compatibility issues
2. **Complex Source Builds**: Custom build requirements
3. **Debugging**: When you need familiar pip behavior
4. **Specific pip Features**: Using pip-only functionality
5. **Conservative Environments**: Where stability is paramount

## Migration Guide

### From pip to UV

1. **Test First**:

   ```toml
   # Create test environment with UV
   [tool.hatch.envs.test-uv]
   installer = "uv"
   ```

2. **Compare Results**:

   ```bash
   # With pip
   hatch env create test-pip
   hatch run -e test-pip pip list > pip-packages.txt

   # With UV
   hatch env create test-uv
   hatch run -e test-uv pip list > uv-packages.txt

   # Compare
   diff pip-packages.txt uv-packages.txt
   ```

3. **Gradual Migration**:

   ```toml
   # Start with development environment
   [tool.hatch.envs.default]
   installer = "uv"

   # Keep pip for production builds
   [tool.hatch.envs.hatch-build]
   installer = "pip"
   ```

### From UV to pip

```toml
# Disable UV globally
[tool.hatch.envs.default]
installer = "pip"

# Or per-environment
[tool.hatch.envs.hatch-build]
installer = "pip"
```

## Troubleshooting

### UV Issues

1. **Package Not Found**:

   ```toml
   # Try additional index
   [tool.hatch.envs.default.env-vars]
   UV_EXTRA_INDEX_URL = "https://pypi.org/simple/"
   ```

2. **Resolution Conflicts**:

   ```toml
   # Use different resolution strategy
   [tool.hatch.envs.default.env-vars]
   UV_RESOLUTION_STRATEGY = "lowest"  # More conservative
   ```

3. **Cache Issues**:

   ```bash
   # Clear UV cache
   uv cache clean

   # Or disable cache temporarily
   UV_NO_CACHE=1 hatch env create
   ```

### Pip Issues

1. **Slow Installation**:

   ```toml
   # Use binary packages only
   [tool.hatch.envs.default.env-vars]
   PIP_ONLY_BINARY = ":all:"
   ```

2. **SSL Certificate Issues**:

   ```toml
   [tool.hatch.envs.default.env-vars]
   PIP_TRUSTED_HOST = "pypi.org files.pythonhosted.org"
   PIP_CERT = "/path/to/cert.pem"
   ```

3. **Memory Issues**:
   ```toml
   # Disable cache to save memory
   [tool.hatch.envs.default.env-vars]
   PIP_NO_CACHE_DIR = "1"
   ```

## Matrix Configuration

### Testing Both Installers

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.10", "3.11"]
installer = ["uv", "pip"]

[tool.hatch.envs.test.overrides]
matrix.installer.installer = { value = "{matrix:installer}" }
```

### Conditional Scripts

```toml
[[tool.hatch.envs.example.matrix]]
tool = ["uv", "pip"]

[tool.hatch.envs.example.overrides]
matrix.tool.installer = { value = "{matrix:tool}" }
matrix.tool.scripts = [
  { key = "pip", value = "{env:HATCH_UV} pip {args}", if = ["uv"] },
]
```

## Complete Examples

### High-Performance Configuration (UV)

```toml
[tool.hatch.envs.default]
installer = "uv"

[tool.hatch.envs.default.env-vars]
# Optimize for speed
UV_COMPILE_BYTECODE = "1"
UV_RESOLUTION_STRATEGY = "highest"
UV_CACHE_DIR = "{env:HOME}/.cache/uv"

# Private index with caching
UV_INDEX_URL = "https://fast.pypi.org/simple/"
UV_EXTRA_INDEX_URL = "https://pypi.org/simple/"
```

### Compatible Configuration (pip)

```toml
[tool.hatch.envs.default]
installer = "pip"

[tool.hatch.envs.default.env-vars]
# Conservative settings
PIP_PREFER_BINARY = "1"
PIP_NO_BUILD_ISOLATION = "0"
PIP_DISABLE_PIP_VERSION_CHECK = "1"

# Standard index
PIP_INDEX_URL = "https://pypi.org/simple/"
PIP_TRUSTED_HOST = "pypi.org files.pythonhosted.org"
```

### Mixed Configuration

```toml
# Fast development with UV
[tool.hatch.envs.default]
installer = "uv"

# Compatible testing with pip
[tool.hatch.envs.test]
installer = "pip"

# Reliable builds with pip
[tool.hatch.envs.hatch-build]
installer = "pip"

# Fast linting with UV
[tool.hatch.envs.lint]
installer = "uv"
```

## Best Practices

1. **Start with UV**: Default choice for new projects
2. **Test Thoroughly**: Verify packages work with chosen installer
3. **Document Choice**: Explain why pip is used if not using UV
4. **Monitor Performance**: Track build times and optimize
5. **Use Appropriate Caching**: Configure cache for your workflow
6. **Handle Authentication Securely**: Use environment variables for tokens
7. **Consider CI/CD**: UV can significantly reduce build times

## Related Topics

- `build-environment-configuration.md`
- `build-dependencies-management.md`
- `environment-variables.md`
- `environment-isolation.md`
