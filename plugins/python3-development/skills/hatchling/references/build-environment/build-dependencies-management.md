---
category: build-environment
topics: [dependencies, build-system, version-management, cython-integration]
related: [build-environment-configuration.md, environment-variables.md, cython-build-tools.md, environment-isolation.md]
---

# Build Dependencies Management

## Overview

Reference this guide when helping users manage build dependencies in hatchling at multiple levels, from build system requirements to target-specific dependencies. This documentation covers all aspects of dependency management during the build process that users may need assistance with.

## Dependency Levels

### 1. Build System Dependencies

Core dependencies required by the build backend itself:

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-vcs",  # Version from VCS
  "hatch-fancy-pypi-readme",  # Dynamic README
]
build-backend = "hatchling.build"
```

### 2. Build Environment Dependencies

Additional dependencies for the build environment:

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "cmake>=3.22",
  "ninja",
]
```

### 3. Build Target Dependencies

Dependencies specific to build targets:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
  "wheel-builder-plugin",
]
require-runtime-dependencies = true
require-runtime-features = ["accelerated", "viz"]
```

### 4. Build Hook Dependencies

Dependencies for build hooks:

```toml
[tool.hatch.build.hooks.cython]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
]
```

### 5. Runtime Dependencies

Project runtime dependencies that may be needed during build:

```toml
[project]
dependencies = [
  "requests>=2.28.0",
  "numpy>=1.24.0,<2.0.0",
  "pandas>=1.5.0",
]
```

### 6. Optional Dependencies (Extras)

Optional features that can be included:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=7.0",
  "pytest-cov>=4.0",
]
accelerated = [
  "numba>=0.57.0",
  "cython>=3.0.0",
]
viz = [
  "matplotlib>=3.5.0",
  "seaborn>=0.12.0",
]
```

## Dependency Specification Formats

### Version Specifiers

```toml
dependencies = [
  # Exact version
  "package==1.0.0",

  # Minimum version
  "package>=1.0.0",

  # Maximum version
  "package<2.0.0",

  # Version range
  "package>=1.0.0,<2.0.0",

  # Exclude specific version
  "package!=1.5.0",

  # Compatible release
  "package~=1.4.0",  # >=1.4.0, <1.5.0

  # Wildcard
  "package==1.4.*",
]
```

### Environment Markers

```toml
dependencies = [
  # Platform-specific
  "pywin32; platform_system == 'Windows'",
  "pyobjc; platform_system == 'Darwin'",

  # Python version specific
  "dataclasses; python_version < '3.7'",
  "tomli; python_version < '3.11'",

  # Implementation specific
  "numpy; implementation_name == 'cpython'",

  # Combined markers
  "torch; python_version >= '3.8' and platform_system == 'Linux'",
]
```

### Direct References

```toml
[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
  # Git repository
  "package @ git+https://github.com/user/repo.git@main",

  # Local directory
  "package @ file:///path/to/package",

  # URL to archive
  "package @ https://github.com/user/repo/archive/v1.0.0.zip",

  # With hash verification
  "package @ https://example.com/package.tar.gz#sha256=abcd1234...",
]
```

### Local Dependencies

```toml
[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
  # Relative to project root
  "shared @ {root:uri}/shared",

  # Parent directory
  "common @ {root:parent:uri}/common",

  # Multiple parent levels
  "core @ {root:parent:parent:uri}/core",
]
```

## Dependency Resolution Strategies

### Using UV (Default)

UV provides fast, reliable dependency resolution:

```toml
[tool.hatch.envs.hatch-build]
installer = "uv"  # Default

[tool.hatch.envs.hatch-build.env-vars]
UV_EXTRA_INDEX_URL = "https://pypi.org/simple/"
UV_INDEX_URL = "https://your.private.index/simple/"
```

### Using pip

Traditional pip resolution:

```toml
[tool.hatch.envs.hatch-build]
installer = "pip"

[tool.hatch.envs.hatch-build.env-vars]
PIP_INDEX_URL = "https://your.private.index/simple/"
PIP_EXTRA_INDEX_URL = "https://pypi.org/simple/"
PIP_TRUSTED_HOST = "your.private.index"
```

## Cython and Compiled Extensions

### Basic Cython Setup

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "cython>=3.0.0",
  "numpy>=1.24.0",
]
build-backend = "hatchling.build"

[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
]
```

### Using hatch-cython Plugin

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cython>=0.5.0",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cython]
# Compile all .pyx files
include = ["**/*.pyx"]

# Include numpy headers
include_numpy = true

# Cython compiler directives
directives = {
  "language_level" = "3",
  "boundscheck" = false,
  "wraparound" = false,
}

# Compiler flags
compile_args = ["-O3", "-march=native"]
```

### Using hatch-cythonize Plugin

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cythonize>=0.6.0",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cythonize]
# Source files pattern
src = "src/**/*.pyx"

# Parallel compilation
parallel = true
nthreads = 4

# Compiler options
compiler_directives = {
  "language_level" = "3",
  "embedsignature" = true,
}
```

## Build Tools Integration

### CMake Integration

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "cmake>=3.22",
  "ninja",
  "scikit-build-core>=0.9.0",
]

[tool.hatch.envs.hatch-build.env-vars]
CMAKE_BUILD_TYPE = "Release"
CMAKE_C_COMPILER = "gcc"
CMAKE_CXX_COMPILER = "g++"
```

### setuptools Integration

For projects migrating from setuptools:

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "setuptools>=65.0",
  "setuptools-scm>=7.0",
  "wheel",
]
```

## Dependency Management Patterns

### Multi-Package Repository

```toml
# shared/pyproject.toml
[project]
name = "shared"
version = "1.0.0"

# app/pyproject.toml
[tool.hatch.metadata]
allow-direct-references = true

[project]
name = "app"
dependencies = [
  "shared @ {root:parent:uri}/shared",
]
```

### Build Matrix

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.9", "3.10", "3.11"]
numpy = ["1.24", "1.25", "1.26"]

[tool.hatch.envs.test.overrides]
matrix.numpy.dependencies = [
  { value = "numpy==1.24.*", if = ["1.24"] },
  { value = "numpy==1.25.*", if = ["1.25"] },
  { value = "numpy==1.26.*", if = ["1.26"] },
]
```

## Dependency Caching and Optimization

### Dependency Hash Optimization

Hatch caches dependency resolution using hashes:

```python
# Hatch automatically manages this
# Dependencies only reinstalled when hash changes
```

### Pre-built Wheels

Prefer binary wheels for faster installation:

```toml
[tool.hatch.envs.hatch-build.env-vars]
PIP_ONLY_BINARY = ":all:"  # Only use wheels
PIP_PREFER_BINARY = "1"     # Prefer wheels over source
```

### Local Package Index

```toml
[tool.hatch.envs.hatch-build.env-vars]
PIP_INDEX_URL = "file:///local/package/index"
UV_INDEX_URL = "file:///local/package/index"
```

## Troubleshooting Dependencies

### Common Issues

1. **Version Conflicts**

   ```toml
   # Be specific about version ranges
   dependencies = [
     "numpy>=1.24.0,<2.0.0",  # Avoid numpy 2.x
   ]
   ```

2. **Missing Build Dependencies**

   ```toml
   [build-system]
   requires = [
     "hatchling",
     "setuptools",  # If needed for legacy code
     "wheel",       # For wheel building
   ]
   ```

3. **Platform-Specific Dependencies**
   ```toml
   dependencies = [
     "pywin32; platform_system == 'Windows'",
     "python-magic-bin; platform_system == 'Windows'",
     "python-magic; platform_system != 'Windows'",
   ]
   ```

### Debugging Commands

```bash
# Check resolved dependencies
hatch dep show

# Build with verbose output
hatch build -v

# Build without isolation (for debugging)
pip install --no-build-isolation .

# Check environment
hatch env show
```

## Best Practices

1. **Pin Build Dependencies**: Use exact versions for reproducibility
2. **Minimize Build Dependencies**: Only include what's necessary
3. **Use Binary Wheels**: Faster than building from source
4. **Leverage Caching**: Let Hatch cache dependency resolution
5. **Test Multiple Versions**: Use matrix builds for compatibility
6. **Document Requirements**: Explain why each dependency is needed
7. **Regular Updates**: Keep build dependencies current

## Complete Example

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cython>=0.5.0",
]
build-backend = "hatchling.build"

[project]
name = "scientific-package"
version = "1.0.0"
dependencies = [
  "numpy>=1.24.0,<2.0.0",
  "scipy>=1.10.0",
  "pandas>=2.0.0",
]

[project.optional-dependencies]
accelerated = [
  "numba>=0.57.0",
  "cython>=3.0.0",
]
viz = [
  "matplotlib>=3.7.0",
  "plotly>=5.14.0",
]
dev = [
  "pytest>=7.3.0",
  "pytest-cov>=4.1.0",
  "black>=23.3.0",
  "ruff>=0.0.270",
]

[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "setuptools>=68.0.0",
]
installer = "uv"

[tool.hatch.build.hooks.cython]
include_numpy = true
directives = {
  "language_level" = "3",
  "embedsignature" = true,
}

[tool.hatch.metadata]
allow-direct-references = true
```

## Related Topics

- `build-environment-configuration.md`
- `uv-vs-pip-installer.md`
- `cython-build-tools.md`
- `environment-isolation.md`
