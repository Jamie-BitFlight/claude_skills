---
category: build-environment
topics: [environment-variables, configuration, compiler-flags, build-control]
related: [build-environment-configuration.md, build-dependencies-management.md, cython-build-tools.md, uv-vs-pip-installer.md]
---

# Environment Variables

## Overview

Reference this guide when helping users work with environment variables that play a crucial role in hatchling's build system. Environment variables control everything from build behavior to compiler flags and dependency resolution. This document provides a comprehensive reference for all environment variables used in hatchling build environments.

## Build Control Variables

### Core Build Variables

```bash
# Clean build artifacts before building
HATCH_BUILD_CLEAN=true

# Clean build artifacts after hooks run
HATCH_BUILD_CLEAN_HOOKS_AFTER=true

# Run only build hooks (skip actual build)
HATCH_BUILD_HOOKS_ONLY=true

# Skip all build hooks
HATCH_BUILD_NO_HOOKS=true

# Enable specific hooks
HATCH_BUILD_HOOKS_ENABLE=true

# Enable/disable specific named hook
HATCH_BUILD_HOOK_ENABLE_CYTHON=true
HATCH_BUILD_HOOK_ENABLE_CUSTOM=false

# Custom build output location
HATCH_BUILD_LOCATION=/path/to/build/output
```

### Reproducible Builds

```bash
# Timestamp for reproducible builds (Unix timestamp)
SOURCE_DATE_EPOCH=1580601600

# Ensure deterministic file ordering
PYTHONHASHSEED=0
```

## Python Configuration Variables

### Python Interpreter Selection

```bash
# Use specific Python version
HATCH_PYTHON=3.11

# Use current Python executable
HATCH_PYTHON=self

# Custom Python path
HATCH_PYTHON=/usr/local/bin/python3.11
```

### Python Build Variants

```bash
# CPU optimization level (Linux only)
# v1: Generic x86-64
# v2: Nehalem-era (SSE4.2, POPCNT)
# v3: Haswell-era (AVX2, FMA) - default
# v4: Skylake-era (AVX512)
HATCH_PYTHON_VARIANT_CPU=v3

# Free-threaded Python (no GIL)
HATCH_PYTHON_VARIANT_GIL=freethreaded
```

### Custom Python Distributions

```bash
# Define custom Python distribution source
HATCH_PYTHON_CUSTOM_SOURCE_MYPY=https://example.com/python-3.11.tar.gz

# Path to Python within the archive
HATCH_PYTHON_CUSTOM_PATH_MYPY=python/bin/python3

# Version identifier
HATCH_PYTHON_CUSTOM_VERSION_MYPY=3.11.0
```

## Installer Configuration

### UV Installer Variables

```bash
# Path to UV binary (implicitly sets installer to 'uv')
HATCH_ENV_TYPE_VIRTUAL_UV_PATH=/usr/local/bin/uv

# UV index configuration
UV_INDEX_URL=https://pypi.org/simple/
UV_EXTRA_INDEX_URL=https://test.pypi.org/simple/

# UV cache directory
UV_CACHE_DIR=/tmp/uv-cache

# UV resolution strategy
UV_RESOLUTION_STRATEGY=highest  # or 'lowest'

# Disable UV cache
UV_NO_CACHE=1

# UV compile Python files
UV_COMPILE_BYTECODE=1
```

### Pip Installer Variables

```bash
# Pip index configuration
PIP_INDEX_URL=https://pypi.org/simple/
PIP_EXTRA_INDEX_URL=https://test.pypi.org/simple/

# Trusted hosts (for self-signed certificates)
PIP_TRUSTED_HOST=your.private.index

# Pip cache directory
PIP_CACHE_DIR=/tmp/pip-cache

# Disable pip cache
PIP_NO_CACHE_DIR=1

# Only use binary packages
PIP_ONLY_BINARY=:all:

# Prefer binary over source
PIP_PREFER_BINARY=1

# Force reinstall
PIP_FORCE_REINSTALL=1

# Pip verbosity
PIP_VERBOSE=1
PIP_QUIET=1
```

## Compiler and Build Tool Variables

### C/C++ Compiler Variables

```bash
# C compiler
CC=gcc
CC=clang
CC=/usr/bin/gcc-12

# C++ compiler
CXX=g++
CXX=clang++
CXX=/usr/bin/g++-12

# Compiler flags
CFLAGS="-O3 -march=native -fPIC"
CXXFLAGS="-O3 -march=native -fPIC -std=c++17"
CPPFLAGS="-I/usr/local/include"

# Linker flags
LDFLAGS="-L/usr/local/lib -Wl,-rpath,/usr/local/lib"
LDSHARED="gcc -shared"

# Archiver
AR=ar
ARFLAGS=rc

# Make parallel jobs
MAKEFLAGS="-j4"
```

### Platform-Specific Variables

#### Windows

```bash
# Visual Studio environment
INCLUDE="C:\Program Files\Microsoft SDKs\Windows\v10.0\Include"
LIB="C:\Program Files\Microsoft SDKs\Windows\v10.0\Lib"
LIBPATH="C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.35.32215\lib\x64"

# Windows SDK
WindowsSdkDir="C:\Program Files (x86)\Windows Kits\10"
WindowsSdkVersion="10.0.22621.0"

# MSVC
VSINSTALLDIR="C:\Program Files\Microsoft Visual Studio\2022\Community"
VCINSTALLDIR="C:\Program Files\Microsoft Visual Studio\2022\Community\VC"
```

#### macOS

```bash
# macOS SDK
SDKROOT=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk

# Deployment target
MACOSX_DEPLOYMENT_TARGET=10.15

# Architecture
ARCHFLAGS="-arch x86_64 -arch arm64"
```

#### Linux

```bash
# Library paths
LD_LIBRARY_PATH=/usr/local/lib:/opt/cuda/lib64
PKG_CONFIG_PATH=/usr/local/lib/pkgconfig

# RPATH settings
LD_RUN_PATH=/usr/local/lib

# Distribution-specific
DEBIAN_FRONTEND=noninteractive
```

## Build Tool Specific Variables

### Cython Variables

```bash
# Cython tracing
CYTHON_TRACE=1

# Cython coverage
CYTHON_COVERAGE=1

# Cython language level
CYTHON_LANGUAGE_LEVEL=3

# Cython directives
CYTHON_FAST_FAIL=1
CYTHON_ANNOTATE=1
```

### NumPy Variables

```bash
# NumPy parallel build jobs
NPY_NUM_BUILD_JOBS=4

# NumPy BLAS/LAPACK
NPY_BLAS_ORDER=openblas,mkl,blas
NPY_LAPACK_ORDER=openblas,mkl,lapack

# Disable NumPy CPU features
NPY_DISABLE_CPU_FEATURES=AVX512F,AVX512_SKX
```

### CMake Variables

```bash
# CMake configuration
CMAKE_BUILD_TYPE=Release
CMAKE_INSTALL_PREFIX=/usr/local

# CMake compilers
CMAKE_C_COMPILER=gcc
CMAKE_CXX_COMPILER=g++

# CMake generator
CMAKE_GENERATOR="Unix Makefiles"
CMAKE_GENERATOR="Ninja"

# CMake parallel build
CMAKE_BUILD_PARALLEL_LEVEL=4

# CMake verbose output
CMAKE_VERBOSE_MAKEFILE=ON
```

### Setuptools Variables

```bash
# Setuptools configuration
SETUPTOOLS_USE_DISTUTILS=stdlib
SETUPTOOLS_ENABLE_FEATURES="legacy-editable"

# Disable setup.py operations
DISTUTILS_DEBUG=1
DISTUTILS_USE_SDK=1
```

## Environment Configuration in pyproject.toml

### Setting Environment Variables

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Build configuration
SOURCE_DATE_EPOCH = "1580601600"
PYTHONHASHSEED = "0"

# Compiler configuration
CC = "gcc-12"
CXX = "g++-12"
CFLAGS = "-O3 -march=native"

# Tool configuration
NPY_NUM_BUILD_JOBS = "4"
CMAKE_BUILD_TYPE = "Release"

# Index configuration
UV_INDEX_URL = "https://pypi.org/simple/"
UV_EXTRA_INDEX_URL = "https://test.pypi.org/simple/"
```

### Environment Variable Filtering

```toml
[tool.hatch.envs.hatch-build]
# Include specific variables
env-include = [
  "PATH",
  "HOME",
  "CC*",     # All variables starting with CC
  "CXX*",    # All variables starting with CXX
]

# Exclude specific variables (takes precedence)
env-exclude = [
  "SECRET*",
  "TOKEN*",
  "PASSWORD",
]
```

### Context Formatting

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Use context formatting for dynamic values
PROJECT_ROOT = "{root}"
BUILD_DIR = "{root}/build"
PARENT_DIR = "{root:parent}"

# Environment variable expansion
CUSTOM_PATH = "{env:HOME}/.local/bin:{env:PATH}"
API_KEY = "{env:MY_SECRET_KEY}"
```

## Private Index Configuration

### With Authentication

```toml
[tool.hatch.envs.hatch-build.env-vars]
# GitLab Package Registry
UV_INDEX_URL = "https://token:{env:GITLAB_API_TOKEN}@gitlab.com/api/v4/groups/mygroup/-/packages/pypi/simple/"

# Artifactory
PIP_INDEX_URL = "https://{env:ARTIFACTORY_USER}:{env:ARTIFACTORY_PASSWORD}@artifactory.example.com/pypi/simple/"

# AWS CodeArtifact
PIP_INDEX_URL = "https://aws:{env:CODEARTIFACT_AUTH_TOKEN}@my-domain-123456789012.d.codeartifact.us-east-1.amazonaws.com/pypi/my-repo/simple/"
```

## Build Matrix Variables

### Matrix-Based Environment Variables

```toml
[[tool.hatch.envs.test.matrix]]
python = ["3.9", "3.10", "3.11"]
numpy = ["1.24", "1.25"]

[tool.hatch.envs.test.overrides]
matrix.python.env-vars = { PYTHON_VERSION = "{matrix:python}" }
matrix.numpy.env-vars = { NUMPY_VERSION = "{matrix:numpy}" }
```

## Debugging Environment Variables

### Debug Commands

```bash
# Show all environment variables
hatch env show

# Show specific environment
hatch env show hatch-build

# Run command with environment
hatch run -e hatch-build env

# Build with verbose output
HATCH_VERBOSE=3 hatch build

# Enable debug output
DEBUG=1 hatch build
```

### Common Debugging Variables

```bash
# Python debugging
PYTHONVERBOSE=1
PYTHONDEBUG=1
PYTHONTRACEMALLOC=1

# Build debugging
DISTUTILS_DEBUG=1
SETUPTOOLS_DEBUG=1

# Dependency debugging
PIP_VERBOSE=3
UV_VERBOSE=1
```

## Complete Example

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "cmake>=3.22",
]
installer = "uv"

[tool.hatch.envs.hatch-build.env-vars]
# Reproducible builds
SOURCE_DATE_EPOCH = "1580601600"
PYTHONHASHSEED = "0"

# Compiler configuration
CC = "gcc-12"
CXX = "g++-12"
CFLAGS = "-O3 -march=native -fPIC"
CXXFLAGS = "-O3 -march=native -fPIC -std=c++17"

# Build tools
NPY_NUM_BUILD_JOBS = "4"
CMAKE_BUILD_TYPE = "Release"
CMAKE_BUILD_PARALLEL_LEVEL = "4"
CYTHON_LANGUAGE_LEVEL = "3"

# Package indexes
UV_INDEX_URL = "https://pypi.org/simple/"
UV_EXTRA_INDEX_URL = "https://test.pypi.org/simple/"

# Platform specific
MACOSX_DEPLOYMENT_TARGET = "10.15"  # macOS only
ARCHFLAGS = "-arch x86_64 -arch arm64"  # macOS only

[tool.hatch.envs.hatch-build]
# Filter environment variables
env-include = [
  "PATH",
  "HOME",
  "CC*",
  "CXX*",
  "PYTHON*",
]
env-exclude = [
  "SECRET*",
  "TOKEN*",
]
```

## Best Practices

1. **Use Context Formatting**: Leverage `{root}`, `{env:VAR}` for portability
2. **Set Reproducible Build Variables**: Always set `SOURCE_DATE_EPOCH`
3. **Document Custom Variables**: Explain why each variable is needed
4. **Use Appropriate Installer Variables**: UV vs pip based on needs
5. **Platform-Specific Sections**: Use environment markers for platform code
6. **Secure Sensitive Data**: Never hardcode tokens, use `{env:TOKEN}`
7. **Validate Variable Effects**: Test builds with different configurations

## Related Topics

- `build-environment-configuration.md`
- `uv-vs-pip-installer.md`
- `build-dependencies-management.md`
- `environment-isolation.md`
