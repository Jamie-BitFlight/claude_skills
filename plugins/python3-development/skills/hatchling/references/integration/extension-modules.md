---
category: integration
topics: [extensions, compiled-modules, c-api, pybind11, pyo3, cython, performance]
related: [./cmake-scikit-build.md]
---

# Extension Modules & Compiled Code

Reference guide for helping users package C, C++, Rust, and other compiled modules with hatchling. Use this when assisting with extension module development and compiled code integration.

## Overview

Extension modules allow Python packages to include compiled code for performance-critical operations. Hatchling supports this through build hooks and integration with build tools.

### Extension Module Approaches

| Approach    | Language | Complexity | Performance | Maintenance |
| ----------- | -------- | ---------- | ----------- | ----------- |
| Pure Python | Python   | Low        | Good        | Easy        |
| ctypes      | C/C++    | Low        | Excellent   | Easy        |
| cffi        | C/C++    | Medium     | Excellent   | Medium      |
| pybind11    | C++      | Medium     | Excellent   | Medium      |
| SWIG        | C/C++    | Medium     | Excellent   | Medium      |
| PyO3        | Rust     | Medium     | Excellent   | Medium      |
| C API       | C        | High       | Excellent   | Hard        |

---

## Architecture

### How Extension Modules Work

<eg>
Python Code (mypackage/__init__.py)
    ↓ (imports)
Extension Module (mypackage/_ext.cp39-win_amd64.pyd or .so)
    ↓ (Python C API calls)
Compiled Code (C++/Rust/etc.)
    ↓ (system calls)
System Libraries (libc, etc.)
</eg>

### Module Location

<eg>
mypackage/
├── __init__.py           # Python code
├── _ext.cpython-39-darwin.so    # Compiled extension (macOS)
├── _ext.cpython-39-win_amd64.pyd # Compiled extension (Windows)
└── _ext.cpython-39-x86_64-linux-gnu.so  # Compiled extension (Linux)
</eg>

**Note**: Different `.so`/`.pyd` extensions needed for different platforms.

---

## Pure Python Alternatives (When Possible)

Before building compiled modules, consider:

### Option 1: NumPy/SciPy (Vectorization)

```python
# Instead of C loop:
# for i in range(len(arr)):
#     result[i] = expensive_calc(arr[i])

# Use NumPy (compiled in C):
import numpy as np

result = np.array([expensive_calc(x) for x in arr])
```

**Advantages**: No compilation, excellent performance, widely known

### Option 2: Cython (Python to C compiler)

```cython
# mymodule.pyx
def fast_function(int n):
    cdef int result = 0
    for i in range(n):
        result += i
    return result
```

```toml
[build-system]
requires = ["hatchling", "Cython"]
```

**Advantages**: Write in near-Python syntax, automatic compilation

### Option 3: Specialized Libraries

```python
# Instead of writing custom C code:
import polars  # Rust-based, compiled, fast
import pandas  # NumPy-based, compiled, fast
```

**Advantages**: Leverage existing optimized code, no build complexity

---

## C API Extensions

### Direct Python C API (Lowest Level)

**When to use**: Need maximum control, integrating legacy C code

**Complexity**: High - must manage reference counting, types manually

### Basic C Extension

**src/myext.c**:

```c
#include <Python.h>

static PyObject* add(PyObject* self, PyObject* args) {
    double x, y;
    if (!PyArg_ParseTuple(args, "dd", &x, &y))
        return NULL;
    return PyFloat_FromDouble(x + y);
}

static PyMethodDef Methods[] = {
    {"add", add, METH_VARARGS, "Add two numbers"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "myext",
    NULL,
    -1,
    Methods
};

PyMODINIT_FUNC PyInit_myext(void) {
    return PyModule_Create(&module);
}
```

**CMakeLists.txt** (with scikit-build-core):

```cmake
add_library(myext MODULE src/myext.c)
target_link_libraries(myext PRIVATE Python::Module)

set_target_properties(myext PROPERTIES
    PREFIX ""
    SUFFIX ${Python_SOABI_SUFFIX}
)

install(TARGETS myext DESTINATION mypackage)
```

---

## pybind11 (C++ Recommended)

### Why pybind11

- **Modern C++**: Use C++11/14/17 features naturally
- **Type conversion**: Automatic Python ↔ C++ type conversion
- **Exception handling**: Python exceptions work seamlessly
- **Less boilerplate**: Minimal code compared to C API
- **Header-only**: No separate compilation step (usually)

### Basic pybind11 Extension

**src/myext.cpp**:

```cpp
#include <pybind11/pybind11.h>

double add(double x, double y) {
    return x + y;
}

class Calculator {
public:
    int multiply(int a, int b) { return a * b; }
};

PYBIND11_MODULE(myext, m) {
    m.def("add", &add, "Add two numbers");

    pybind11::class_<Calculator>(m, "Calculator")
        .def("multiply", &Calculator::multiply);
}
```

**CMakeLists.txt**:

```cmake
find_package(pybind11 REQUIRED)

pybind11_add_module(myext src/myext.cpp)

install(TARGETS myext DESTINATION mypackage)
```

**Python usage**:

```python
from mypackage import myext

result = myext.add(3.5, 2.1)  # 5.6
calc = myext.Calculator()
product = calc.multiply(4, 5)  # 20
```

### Advanced Features

**NumPy arrays**:

```cpp
#include <pybind11/numpy.h>

void process_array(pybind11::array_t<double> array) {
    auto buf = array.request();
    double *ptr = static_cast<double *>(buf.ptr);
    int n = buf.shape[0];

    for(int i = 0; i < n; ++i) {
        ptr[i] *= 2.0;
    }
}

PYBIND11_MODULE(myext, m) {
    m.def("process_array", &process_array);
}
```

---

## SWIG (Multiple Language Bindings)

### When to Use SWIG

- Wrapping existing C/C++ library
- Need bindings for multiple languages (Python, R, Java)
- Legacy codebase not originally designed for Python

### Basic SWIG Setup

**src/myext.i** (SWIG interface):

```swig
%module myext

%{
#include "myext.h"
%}

double add(double x, double y);
```

**src/myext.h**:

```c
double add(double x, double y) {
    return x + y;
}
```

**CMakeLists.txt**:

```cmake
find_package(SWIG REQUIRED)
include(UseSWIG)

set_source_files_properties(myext.i PROPERTIES
    CPLUSPLUS ON
    SWIG_MODULE_NAME myext
)

swig_add_library(myext
    TYPE SHARED
    LANGUAGE python
    SOURCES myext.i
)

target_link_libraries(myext PRIVATE Python::Module)

install(TARGETS myext DESTINATION mypackage)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/myext.py
        DESTINATION mypackage)
```

---

## Rust Extensions

### Using PyO3

**Cargo.toml**:

```toml
[package]
name = "myext"
version = "0.1.0"

[dependencies]
pyo3 = { version = "0.21", features = ["extension-module"] }

[lib]
crate-type = ["cdylib"]
```

**src/lib.rs**:

```rust
use pyo3::prelude::*;

#[pyfunction]
fn add(x: f64, y: f64) -> f64 {
    x + y
}

#[pymodule]
fn myext(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}
```

**pyproject.toml**:

```toml
[build-system]
requires = ["maturin"]
build-backend = "maturin"

[project]
name = "myext"
```

**Build**:

```bash
pip install maturin
maturin develop  # Editable install
maturin build    # Create wheel
```

---

## Binary Wheels (Pre-built)

### Pre-compiled Wheels

For maximum performance and user convenience, distribute pre-compiled wheels:

```bash
# Build for multiple platforms
cibuildwheel --output-dir wheelhouse

# Upload to PyPI
twine upload wheelhouse/*
```

### Wheel Naming

<eg>
mypackage-1.0.0-cp310-cp310-win_amd64.whl
                └──┬───┘ └──────┬──────┘
                Python 3.10    Windows 64-bit

mypackage-1.0.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
                                └─────────────────┬──────────────────┘
                                glibc version & arch
</eg>

---

## Performance Considerations

### When Compiled Code Helps

| Scenario            | Speedup | Language         |
| ------------------- | ------- | ---------------- |
| Tight loops (math)  | 10-100x | C/C++, Rust      |
| Array operations    | 5-20x   | NumPy, C         |
| Regular expressions | 2-10x   | C (already used) |
| String processing   | 2-5x    | C/C++            |

### When Overhead Exceeds Benefit

- Function called rarely
- Processing small data (<1KB)
- I/O bound (network, disk)
- Already using NumPy/pandas

---

## Distribution & Compatibility

### Source Distribution (sdist)

Must include source code + build instructions:

<eg>
mypackage-1.0.0.tar.gz
└── mypackage-1.0.0/
    ├── CMakeLists.txt
    ├── pyproject.toml
    ├── src/
    │   └── myext.cpp
    └── mypackage/
        └── __init__.py
</eg>

When user installs from sdist, build system is triggered:

```bash
pip install mypackage-1.0.0.tar.gz
# → runs cmake, compiles extension, creates wheel, installs
```

### Binary Wheels

Pre-compiled for specific platform:

```bash
mypackage-1.0.0-cp39-cp39-linux_x86_64.whl
# User just unpacks and installs (fast, no compilation)
```

### Universal Wheels (Pure Python Only)

<eg>
mypackage-1.0.0-py3-none-any.whl
# works on all platforms if no compiled code
</eg>

---

## Troubleshooting

### Issue: Import Error After Install

<eg>
ImportError: cannot import name '_ext'
</eg>

**Causes**:

- Extension not compiled
- Python version mismatch
- Platform mismatch
- Missing dependencies

**Debug**:

```bash
# Check what's in the wheel
unzip -l mypackage-1.0.0-py3-none-any.whl | grep -E '\.(so|pyd)$'

# Force rebuild
pip install --force-reinstall --no-cache-dir mypackage

# Check Python version
python --version
```

### Issue: Compilation Errors

<eg>
error: command 'gcc' not found
</eg>

**Solution**: Install compiler

```bash
# Ubuntu
sudo apt install build-essential python3-dev

# macOS (Xcode)
xcode-select --install

# Windows
# Install Visual Studio Build Tools
```

### Issue: Segmentation Fault

<eg>
Segmentation fault (core dumped)
</eg>

**Causes**:

- Accessing NULL pointer
- Buffer overflow
- Memory corruption
- Incompatible libraries

**Solutions**:

- Use safer language (Rust with PyO3)
- Run under debugger (gdb, lldb)
- Add bounds checking
- Use AddressSanitizer (-fsanitize=address)

---

## Best Practices

1. **Start with pure Python**: Use NumPy, SciPy first
2. **Profile before optimizing**: Use cProfile to find bottlenecks
3. **Use safe languages**: Prefer Rust (PyO3) for new code
4. **Test thoroughly**: Extension bugs are hard to track
5. **Provide wheels**: Reduce user compilation burden
6. **Document platform requirements**: Specify dependencies
7. **Version carefully**: ABI changes break compatibility
8. **Type hints**: Provide .pyi stub files for IDE support

---

## Resources

- [pybind11 Documentation](https://pybind11.readthedocs.io/)
- [PyO3 Documentation](https://pyo3.rs/)
- [SWIG Documentation](https://swig.org/)
- [Python C API Reference](https://docs.python.org/3/c-api/)
- [scikit-build-core Documentation](https://scikit-build-core.readthedocs.io/)
- [cibuildwheel](https://cibuildwheel.readthedocs.io/) - Build multi-platform wheels

**Key Takeaway**: Modern Python C/C++ extensions use pybind11 or PyO3 for safety and ease, built via CMake with hatchling providing the integration glue.
