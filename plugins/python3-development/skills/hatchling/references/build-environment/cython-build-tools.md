---
category: build-environment
topics: [cython, compiled-extensions, build-tools, cmake, rust]
related: [build-environment-configuration.md, build-dependencies-management.md, environment-variables.md]
---

# Cython and Build Tools

## Overview

Reference this guide when helping users build Python extensions using various methods including Cython, C/C++ extensions, and integration with build systems like CMake. This document covers configuration and best practices for building compiled extensions with hatchling that users may need assistance implementing.

## Cython Integration

### Basic Cython Setup

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "cython>=3.0.0",
]
build-backend = "hatchling.build"

[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
]
```

### Using hatch-cython Plugin

The `hatch-cython` plugin provides automatic Cython compilation:

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cython>=0.5.1",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cython]
# Include all .pyx files
include = [
  "**/*.pyx",
]

# Exclude specific files
exclude = [
  "**/test_*.pyx",
]
```

### hatch-cython Configuration Options

```toml
[tool.hatch.build.hooks.cython]
# Include numpy headers
include_numpy = true

# Cython compiler directives
directives = {
  language_level = "3",
  embedsignature = true,
  boundscheck = false,
  wraparound = false,
  nonecheck = false,
  cdivision = true,
  always_allow_keywords = true,
}

# Compiler arguments
compile_args = [
  "-O3",
  "-march=native",
  "-ffast-math",
]

# Linker arguments
link_args = [
  "-lm",  # Link math library
]

# Define macros
define_macros = [
  ["NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"],
  ["CYTHON_FAST_PYCALL", "1"],
]

# Platform-specific options
[tool.hatch.build.hooks.cython.platforms.windows]
compile_args = ["/O2", "/fp:fast"]

[tool.hatch.build.hooks.cython.platforms.linux]
compile_args = ["-O3", "-march=native"]

[tool.hatch.build.hooks.cython.platforms.macos]
compile_args = ["-O3", "-arch", "x86_64", "-arch", "arm64"]
```

### Using hatch-cythonize Plugin

Alternative plugin with more features:

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cythonize>=0.6.0",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cythonize]
# Source file patterns
src = "src/**/*.pyx"

# Parallel compilation
parallel = true
nthreads = 4

# Cython compiler directives
compiler_directives = {
  language_level = "3",
  embedsignature = true,
  binding = true,
  annotation_typing = true,
}

# Annotate output (generates HTML)
annotate = true

# Build in-place
inplace = true
```

## NumPy Integration

### NumPy Headers in Cython

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "hatch-cython>=0.5.0",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cython]
include_numpy = true

# For older numpy compatibility
define_macros = [
  ["NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"],
]
```

### NumPy Build Configuration

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "numpy>=1.24.0",
  "cython>=3.0.0",
]

[tool.hatch.envs.hatch-build.env-vars]
# NumPy build settings
NPY_NUM_BUILD_JOBS = "4"
NPY_BLAS_ORDER = "openblas,mkl,blas"
NPY_LAPACK_ORDER = "openblas,mkl,lapack"
NPY_DISABLE_CPU_FEATURES = "AVX512F,AVX512_SKX"
```

## C/C++ Extensions

### Direct C Extension

```python
# setup_hook.py
from setuptools import Extension

def get_extensions():
    return [
        Extension(
            "mypackage._speedups",
            sources=["src/mypackage/_speedups.c"],
            include_dirs=["/usr/local/include"],
            libraries=["m"],
            extra_compile_args=["-O3", "-march=native"],
        )
    ]
```

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "setuptools>=65.0",
]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.custom]
path = "setup_hook.py"
```

### C++ Extension with C++17

```python
# setup_hook.py
from setuptools import Extension
import platform

def get_extensions():
    cpp_args = []
    if platform.system() == "Windows":
        cpp_args = ["/std:c++17", "/O2"]
    else:
        cpp_args = ["-std=c++17", "-O3", "-march=native"]

    return [
        Extension(
            "mypackage._cpp_ext",
            sources=["src/mypackage/_cpp_ext.cpp"],
            language="c++",
            extra_compile_args=cpp_args,
        )
    ]
```

## CMake Integration

### Using scikit-build-core

```toml
[build-system]
requires = [
  "scikit-build-core>=0.9.0",
  "cmake>=3.22",
]
build-backend = "scikit_build_core.build"

[tool.scikit-build]
# Minimum CMake version
cmake.minimum-version = "3.22"

# Build directory
build-dir = "build/{wheel_tag}"

# CMake arguments
cmake.args = [
  "-DCMAKE_BUILD_TYPE=Release",
  "-DBUILD_SHARED_LIBS=OFF",
]

# Build tool arguments
cmake.build-type = "Release"

# Ninja generator
cmake.generator = "Ninja"

# Parallel build
build.parallel = true
build.verbose = true

# Install components
install.components = ["python"]
```

### CMakeLists.txt Example

```cmake
cmake_minimum_required(VERSION 3.22)
project(myextension LANGUAGES CXX)

# Find Python and pybind11
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# Create extension module
pybind11_add_module(_core src/core.cpp)

# Set properties
target_compile_features(_core PRIVATE cxx_std_17)
target_compile_options(_core PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-O3 -march=native>
  $<$<CXX_COMPILER_ID:MSVC>:/O2>
)

# Install
install(TARGETS _core DESTINATION mypackage)
```

## Build Tool Chains

### Compiler Configuration

```toml
[tool.hatch.envs.hatch-build.env-vars]
# C compiler
CC = "gcc-12"
CC = "clang-15"
CC = "cl.exe"  # MSVC on Windows

# C++ compiler
CXX = "g++-12"
CXX = "clang++-15"
CXX = "cl.exe"  # MSVC on Windows

# Compiler flags
CFLAGS = "-O3 -march=native -fPIC -Wall"
CXXFLAGS = "-O3 -march=native -fPIC -std=c++17 -Wall"

# Preprocessor flags
CPPFLAGS = "-I/usr/local/include -DNDEBUG"

# Linker flags
LDFLAGS = "-L/usr/local/lib -Wl,-rpath,/usr/local/lib"
```

### Platform-Specific Configuration

```toml
# Windows with MSVC
[tool.hatch.envs.hatch-build.windows]
env-vars = {
  CC = "cl.exe",
  CXX = "cl.exe",
  CFLAGS = "/O2 /fp:fast",
  INCLUDE = "C:\\Program Files\\Microsoft SDKs\\Windows\\v10.0\\Include",
  LIB = "C:\\Program Files\\Microsoft SDKs\\Windows\\v10.0\\Lib",
}

# macOS with Universal Binary
[tool.hatch.envs.hatch-build.macos]
env-vars = {
  ARCHFLAGS = "-arch x86_64 -arch arm64",
  MACOSX_DEPLOYMENT_TARGET = "10.15",
}

# Linux with specific architecture
[tool.hatch.envs.hatch-build.linux]
env-vars = {
  CFLAGS = "-O3 -march=native -mtune=native",
  NPY_NUM_BUILD_JOBS = "8",
}
```

## CUDA Extensions

### Setup for CUDA

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "cupy-cuda12x>=12.0.0",  # or appropriate CUDA version
]
build-backend = "hatchling.build"

[tool.hatch.envs.hatch-build.env-vars]
CUDA_HOME = "/usr/local/cuda"
CUDA_PATH = "/usr/local/cuda"
CUDACXX = "/usr/local/cuda/bin/nvcc"
CUDA_ARCH_LIST = "7.5;8.0;8.6"  # GPU architectures
```

### CUDA with CMake

```cmake
cmake_minimum_required(VERSION 3.22)
project(cuda_extension LANGUAGES CXX CUDA)

# Find CUDA
find_package(CUDAToolkit REQUIRED)

# Create CUDA library
add_library(cuda_kernels STATIC src/kernels.cu)
target_compile_features(cuda_kernels PUBLIC cuda_std_14)
set_target_properties(cuda_kernels PROPERTIES
  CUDA_ARCHITECTURES "75;80;86"
)

# Link with Python extension
target_link_libraries(_core PRIVATE cuda_kernels CUDA::cudart)
```

## Rust Extensions (with maturin)

### Basic Rust Extension

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "mypackage"
version = "0.1.0"

[tool.maturin]
# Build for Python 3.8+
python-source = "python"
# Include Python source
include = ["python/mypackage/**/*.py"]
```

### Cargo.toml

```toml
[package]
name = "mypackage"
version = "0.1.0"
edition = "2021"

[lib]
name = "_rust_ext"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }

[profile.release]
lto = true
opt-level = 3
```

## Fortran Extensions

### Using meson-python

```toml
[build-system]
requires = ["meson-python>=0.13.0", "meson>=1.1.0"]
build-backend = "mesonpy"

[tool.meson-python.args]
setup = ["-Dbuildtype=release", "-Db_lto=true"]
compile = ["-j4"]
install = ["--tags", "python-runtime"]
```

### meson.build

```meson
project('fortran_ext', 'fortran',
  version : '0.1.0',
  default_options : ['warning_level=2'])

py = import('python').find_installation()

fortran_sources = files('src/module.f90')

py.extension_module('_fortran',
  fortran_sources,
  install : true,
  subdir : 'mypackage'
)
```

## Build Optimization

### Parallel Compilation

```toml
[tool.hatch.envs.hatch-build.env-vars]
# General parallel build
MAKEFLAGS = "-j8"

# NumPy parallel build
NPY_NUM_BUILD_JOBS = "8"

# CMake parallel build
CMAKE_BUILD_PARALLEL_LEVEL = "8"

# Cython parallel
CYTHON_PARALLEL = "1"
```

### Link-Time Optimization (LTO)

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Enable LTO
CFLAGS = "-O3 -flto"
CXXFLAGS = "-O3 -flto"
LDFLAGS = "-flto"

# For MSVC
CFLAGS = "/O2 /GL"
LDFLAGS = "/LTCG"
```

### Profile-Guided Optimization (PGO)

```bash
# Step 1: Build with profiling
export CFLAGS="-O3 -fprofile-generate"
hatch build

# Step 2: Run representative workload
python -m mypackage.benchmark

# Step 3: Build with profile data
export CFLAGS="-O3 -fprofile-use"
hatch build
```

## Debugging Builds

### Debug Configuration

```toml
[tool.hatch.envs.debug]
dependencies = [
  "cython>=3.0.0",
  "gdb",  # or lldb on macOS
]

[tool.hatch.envs.debug.env-vars]
CFLAGS = "-O0 -g -DDEBUG"
CYTHON_TRACE = "1"
CYTHON_COVERAGE = "1"
```

### Verbose Build Output

```toml
[tool.hatch.envs.hatch-build.env-vars]
# Verbose compiler output
VERBOSE = "1"
CMAKE_VERBOSE_MAKEFILE = "ON"

# setuptools verbose
DISTUTILS_DEBUG = "1"
```

## Complete Example: Scientific Package

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-cython>=0.5.0",
  "numpy>=1.24.0",
  "cython>=3.0.0",
]
build-backend = "hatchling.build"

[project]
name = "scientific-package"
version = "1.0.0"
dependencies = [
  "numpy>=1.24.0,<2.0.0",
  "scipy>=1.10.0",
]

[tool.hatch.build.hooks.cython]
# Include all Cython files
include = ["src/**/*.pyx"]

# NumPy support
include_numpy = true

# Optimization directives
directives = {
  language_level = "3",
  embedsignature = true,
  boundscheck = false,
  wraparound = false,
  nonecheck = false,
  cdivision = true,
  profile = false,
  linetrace = false,
}

# Compiler optimization
compile_args = ["-O3", "-march=native", "-ffast-math"]

# Define macros
define_macros = [
  ["NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"],
]

[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "setuptools>=68.0.0",
]

[tool.hatch.envs.hatch-build.env-vars]
# Compiler configuration
CC = "gcc-12"
CXX = "g++-12"
CFLAGS = "-O3 -march=native -fPIC"

# NumPy configuration
NPY_NUM_BUILD_JOBS = "8"

# Build reproducibility
SOURCE_DATE_EPOCH = "1580601600"
```

## Troubleshooting

### Common Issues

1. **Missing Compiler**:

   ```toml
   [tool.hatch.envs.hatch-build.env-vars]
   CC = "/usr/bin/gcc"  # Explicit path
   ```

2. **NumPy ABI Compatibility**:

   ```toml
   [tool.hatch.build.hooks.cython]
   define_macros = [
     ["NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"],
   ]
   ```

3. **Cython Not Found**:

   ```toml
   [build-system]
   requires = [
     "hatchling",
     "cython>=3.0.0",  # Add to build requirements
   ]
   ```

4. **Platform-Specific Failures**:

   ```toml
   [tool.hatch.build.hooks.cython.platforms.windows]
   compile_args = ["/O2"]  # Windows-specific

   [tool.hatch.build.hooks.cython.platforms.linux]
   compile_args = ["-O3"]  # Linux-specific
   ```

## Best Practices

1. **Pin Build Tool Versions**: Ensure reproducible builds
2. **Use NumPy's Oldest-Supported**: Build against oldest numpy for compatibility
3. **Enable Compiler Warnings**: Catch issues early
4. **Test Multiple Platforms**: Use CI to test Windows/Linux/macOS
5. **Profile Before Optimizing**: Measure performance improvements
6. **Document Build Requirements**: List system dependencies
7. **Use Build Isolation**: Default behavior for clean builds

## Related Topics

- `build-environment-configuration.md`
- `build-dependencies-management.md`
- `environment-variables.md`
- `environment-isolation.md`
