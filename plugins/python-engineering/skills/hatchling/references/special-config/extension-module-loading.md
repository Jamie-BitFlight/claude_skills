---
category: advanced-build
topics: [extension modules, compiled extensions, build hooks, Cython, Rust, PyO3]
related: [extension-module-loading.md, pep-561-type-hinting.md]
---

# Extension Module Loading in Hatchling

## Overview

Hatchling supports building and packaging Python extension modules (compiled C/C++/Rust extensions). When assisting users with compiled extensions, reference Hatchling's support for automatic detection, proper wheel tagging, and integration with build tools.

## Extension Module Types

### C/C++ Extensions

Traditional compiled extensions using Python's C API:

```c
// mymodule.c
#include <Python.h>

static PyObject* hello(PyObject* self, PyObject* args) {
    return PyString_FromString("Hello from C!");
}

static PyMethodDef methods[] = {
    {"hello", hello, METH_VARARGS, "Say hello"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initmymodule(void) {
    Py_InitModule("mymodule", methods);
}
```

### Cython Extensions

Extensions written in Cython:

```python
# mymodule.pyx
def calculate(int x, int y):
    return x * y * 2
```

### Rust Extensions (PyO3)

Extensions written in Rust using PyO3:

```rust
// src/lib.rs
use pyo3::prelude::*;

#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pymodule]
fn mymodule(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    Ok(())
}
```

## Configuration

### Basic Extension Setup

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-mypyc",  # For mypyc compilation
    # or "hatch-cython" for Cython
    # or "maturin" for Rust
]
build-backend = "hatchling.build"

[project]
name = "my-extension-package"
version = "1.0.0"
```

### With Build Hooks

```toml
[tool.hatch.build.hooks.custom]
dependencies = ["setuptools", "wheel", "Cython"]

[tool.hatch.build.targets.wheel.hooks.custom]
enable = true
```

## Build Hooks for Extensions

### Custom Build Hook

Create a `hatch_build.py` at the project root:

```python
# hatch_build.py
import sys
import sysconfig
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Initialize the build hook."""
        # Set up extension modules
        if self.target_name == "wheel":
            self._build_extensions()
            build_data["infer_tag"] = True  # Auto-detect platform tag

    def _build_extensions(self):
        """Build C extensions."""
        import subprocess
        from setuptools import Extension
        from Cython.Build import cythonize

        extensions = [Extension("mypackage.fast_module", ["src/mypackage/fast_module.pyx"], include_dirs=["."])]

        # Compile extensions
        ext_modules = cythonize(extensions)
        # Build logic here
```

### Hook Registration

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

[tool.hatch.build.targets.wheel.hooks.custom]
enable = true
```

## Artifacts Configuration

### Including Compiled Extensions

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
    "*.so",      # Unix/Linux
    "*.pyd",     # Windows
    "*.dll",     # Windows dependencies
    "*.dylib",   # macOS
]
```

### Platform-Specific Artifacts

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
    # Include all compiled extensions
    "src/**/*.so",
    "src/**/*.pyd",

    # Exclude build artifacts
    "!src/**/*.c",
    "!src/**/*.cpp",
    "!src/**/*.o",
]
```

## Wheel Tagging

### Automatic Tag Inference

When building extensions, set `infer_tag` to automatically detect the platform:

```python
# In build hook
def initialize(self, version, build_data):
    build_data["infer_tag"] = True
    build_data["pure_python"] = False
```

### Manual Tag Configuration

```python
# In build hook
def initialize(self, version, build_data):
    build_data["tag"] = f"cp{sys.version_info[0]}{sys.version_info[1]}"
    build_data["abi_tag"] = "none"
    build_data["platform_tag"] = sysconfig.get_platform().replace("-", "_")
```

## Version Source for Extensions

### Loading Version from Compiled Module

```toml
[tool.hatch.version]
source = "code"
path = "src/mypackage/__init__.py"
search-paths = ["src"]
```

With extension module version:

```python
# src/mypackage/__init__.py
try:
    from . import _version  # Compiled module

    __version__ = _version.VERSION
except ImportError:
    __version__ = "unknown"
```

## Integration with Build Systems

### Scikit-build-core

```toml
[build-system]
requires = ["hatchling", "scikit-build-core"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.scikit-build]
enable = true

[tool.scikit-build]
cmake.minimum-version = "3.15"
ninja.minimum-version = "1.10"
```

### Maturin (Rust)

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
bindings = "pyo3"
features = ["pyo3/extension-module"]
```

### MyPyC

```toml
[build-system]
requires = ["hatchling", "hatch-mypyc"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.mypyc]
enable = true
dependencies = ["hatch-mypyc"]

[tool.hatch.build.targets.wheel.hooks.mypyc]
dependencies = ["hatch-mypyc"]
require-runtime-dependencies = true
```

## Platform-Specific Builds

### Architecture Detection

```python
# hatch_build.py
import platform


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        arch = platform.machine()
        if arch == "x86_64":
            self._build_x64_extensions()
        elif arch == "aarch64":
            self._build_arm64_extensions()
```

### Environment Variables

```python
# Use environment variables for build configuration
import os


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Respect ARCHFLAGS on macOS
        archflags = os.environ.get("ARCHFLAGS", "")
        if archflags:
            # Configure build for specified architectures
            pass
```

## Development Workflow

### Editable Installs with Extensions

When helping users set up editable installs with extensions, reference this configuration:

```toml
[tool.hatch.build]
dev-mode-dirs = ["src"]

[tool.hatch.build.targets.wheel]
bypass-selection = false  # Ensure extensions are built
```

### Building Extensions

Guide users to build their extensions with these commands:

```bash
# Build extensions
hatch build -t wheel

# Build with specific Python version
hatch build -t wheel --python /path/to/python3.11
```

### Testing Extensions

When helping users test their extensions, reference this pattern:

```python
# tests/test_extension.py
import pytest
import mypackage.extension_module


def test_extension_loads():
    # Verify extension module loads
    assert hasattr(mypackage.extension_module, "fast_function")


def test_extension_performance():
    import time

    # Test that extension is actually faster
    result = mypackage.extension_module.fast_function(1000000)
    assert result is not None
```

## Common Extension Patterns

### NumPy Extensions

```python
# hatch_build.py
import numpy as np
from setuptools import Extension


class NumpyBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        extensions = [
            Extension(
                "mypackage.numpy_ext",
                ["src/numpy_ext.c"],
                include_dirs=[np.get_include()],
                define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
            )
        ]
        # Build extensions...
```

### Multi-Module Extensions

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
    "mypackage/*.so",
    "mypackage/submodule/*.so",
    "mypackage/accelerated/*.pyd",
]
```

## Troubleshooting

### Extension Not Found

**Problem:** Users' extension module not found after installation

**Solution:** Help users with this configuration:

```toml
[tool.hatch.build.targets.wheel]
# Ensure extensions are included
artifacts = ["**/*.so", "**/*.pyd", "**/*.dll"]

# Check build output
bypass-selection = false
```

### Platform Mismatch

**Problem:** Users' wheel platform doesn't match their system

**Solution:** Guide users to configure their build hook:

```python
# In build hook
def initialize(self, version, build_data):
    # Force correct platform tag
    build_data["pure_python"] = False
    build_data["infer_tag"] = True
```

### Build Failures

**Problem:** Users' extension fails to compile

**Debug steps:** Help users troubleshoot with these commands:

```bash
# Verbose build
hatch build -v

# Check compiler
python -c "import sysconfig; print(sysconfig.get_config_var('CC'))"

# Test build hook
python -c "from hatch_build import CustomBuildHook; print('Hook loads')"
```

## Complete Example: Cython Extension

**Project structure:**

<eg>
fast-math/
├── src/
│   └── fast_math/
│       ├── __init__.py
│       ├── pure.py          # Pure Python fallback
│       └── _accelerated.pyx # Cython extension
├── hatch_build.py
├── setup.py  # For Cython compilation
└── pyproject.toml
</eg>

**pyproject.toml:**

```toml
[build-system]
requires = ["hatchling", "Cython>=3.0"]
build-backend = "hatchling.build"

[project]
name = "fast-math"
version = "1.0.0"
description = "Fast math operations with Cython"

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

[tool.hatch.build.targets.wheel]
artifacts = [
    "src/fast_math/*.so",
    "src/fast_math/*.pyd",
]

[tool.hatch.build.targets.wheel.hooks.custom]
enable = true
dependencies = ["Cython>=3.0", "setuptools"]
```

**hatch_build.py:**

```python
import sys
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CythonBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != "wheel":
            return

        from Cython.Build import cythonize
        from setuptools import Extension

        extensions = [Extension("fast_math._accelerated", ["src/fast_math/_accelerated.pyx"], language="c")]

        # Compile Cython modules
        ext_modules = cythonize(extensions, compiler_directives={"language_level": "3", "embedsignature": True})

        # Build extensions (simplified)
        self._compile_extensions(ext_modules)

        # Set wheel tags
        build_data["infer_tag"] = True
        build_data["pure_python"] = False

    def _compile_extensions(self, extensions):
        """Compile the extensions."""
        # Implementation depends on your build system
        pass
```

**src/fast_math/**init**.py:**

```python
"""Fast math operations."""

try:
    from ._accelerated import fast_multiply, fast_power

    HAS_ACCELERATION = True
except ImportError:
    from .pure import fast_multiply, fast_power

    HAS_ACCELERATION = False

__all__ = ["fast_multiply", "fast_power", "HAS_ACCELERATION"]
```

## References

- [Hatchling Build Hooks](https://hatch.pypa.io/latest/plugins/build-hook/reference/)
- [Python Packaging - Binary Extensions](https://packaging.python.org/en/latest/guides/packaging-binary-extensions/)
- [Cython Documentation](https://cython.readthedocs.io/)
- [PyO3 User Guide](https://pyo3.rs/)
- [scikit-build-core](https://scikit-build-core.readthedocs.io/)
