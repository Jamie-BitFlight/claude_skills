# PyO3

| Field         | Value                                                              |
| ------------- | ------------------------------------------------------------------ |
| Research Date | 2026-02-05                                                         |
| Primary URL   | <https://pyo3.rs>                                                  |
| GitHub        | <https://github.com/PyO3/pyo3>                                     |
| Crates.io     | <https://crates.io/crates/pyo3>                                    |
| Docs.rs       | <https://docs.rs/pyo3/>                                            |
| Version       | 0.28.0 (released 2026-02-01, requires Rust 1.83+)                  |
| License       | MIT OR Apache-2.0 (dual-licensed)                                  |
| Discord       | <https://discord.gg/33kcChzH7f>                                    |

---

## Overview

PyO3 provides Rust bindings for Python, enabling developers to write native Python extension modules in Rust with automatic memory management and type conversions. It supports both directions: exposing Rust code to Python (building native modules) and embedding Python interpreters in Rust applications. The library is the foundation for high-performance Python packages and is used by major projects including Pydantic, Polars, and cryptography.

---

## Problem Addressed

| Problem                                           | Solution                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------- |
| Python performance bottlenecks in compute-heavy code | Write performance-critical code in Rust with automatic Python bindings        |
| C extension complexity and memory unsafety        | Rust's ownership model provides memory safety without garbage collection pauses |
| Difficult cross-platform wheel building           | maturin and setuptools-rust provide one-command multi-platform builds           |
| Python/Rust type conversion boilerplate           | Automatic FromPyObject/IntoPy conversions for common types                      |
| GIL management complexity                         | Safe abstractions for Python::with_gil and Python::allow_threads               |
| Async/await interoperability between languages    | pyo3-async-runtimes bridges Rust futures with Python asyncio                   |
| ABI compatibility across Python versions          | abi3 stable ABI support for single binary across Python 3.7-3.14               |
| NumPy integration from Rust                       | rust-numpy crate provides ndarray bindings                                      |

---

## Key Statistics

| Metric             | Value                     | Date Gathered |
| ------------------ | ------------------------- | ------------- |
| GitHub Stars       | 15,268                    | 2026-02-05    |
| GitHub Forks       | 934                       | 2026-02-05    |
| Primary Language   | Rust                      | 2026-02-05    |
| Repository Age     | Since May 2017            | 2026-02-05    |
| Latest Version     | 0.28.0                    | 2026-02-01    |
| Min Rust Version   | 1.83                      | 2026-02-05    |
| maturin Stars      | 5,354                     | 2026-02-05    |
| Release Cadence    | ~2-3 months               | 2026-02-05    |

---

## Key Features

### Core Binding Capabilities

- **#[pyclass]**: Define Python classes from Rust structs with automatic __init__, __repr__, __str__
- **#[pymethods]**: Implement Python methods on Rust structs with signature introspection
- **#[pyfunction]**: Expose Rust functions as Python callable with automatic argument parsing
- **#[pymodule]**: Define Python modules entirely in Rust with submodule support
- **FromPyObject/IntoPy**: Automatic bidirectional type conversion for 30+ standard types
- **PyAny/Bound**: Safe handles to Python objects with lifetime tracking

### Python Distribution Support

- **CPython 3.7+**: Full support for all modern CPython releases
- **PyPy 7.3+**: Support for PyPy Python 3.11+ implementations
- **GraalPy 25.0+**: Support for GraalVM's Python 3.12+ implementation
- **Free-threaded Python 3.13t**: Experimental no-GIL Python support

### Stable ABI (abi3)

- **Single Binary Distribution**: Build once, run on Python 3.7-3.14 without recompilation
- **Version Targeting**: abi3-py37 through abi3-py314 feature flags
- **Reduced Build Matrix**: One wheel per platform instead of one per Python version
- **Forward Compatibility**: abi3 wheels continue working with future Python releases

### Async Support

- **experimental-async Feature**: Enable async fn in #[pyfunction] and #[pymethods]
- **pyo3-async-runtimes**: Bridge Rust async runtimes (tokio, async-std) with Python asyncio
- **Coroutine Objects**: Return Rust futures as Python awaitable objects

### Type Integrations

| Feature Flag   | Integration                                              |
| -------------- | -------------------------------------------------------- |
| chrono         | DateTime, Date, Time, Duration conversions               |
| chrono-tz      | Timezone-aware datetime with chrono-tz                   |
| jiff-02        | Modern date/time library integration                     |
| num-bigint     | Arbitrary precision integer support                      |
| num-complex    | Complex number conversions                               |
| rust_decimal   | Decimal type for financial calculations                  |
| indexmap       | Ordered dict preserving insertion order                  |
| hashbrown      | High-performance hashmap implementation                  |
| serde          | Serialize Python objects via Serde                       |
| anyhow/eyre    | Error handling library integration                       |
| bytes          | Zero-copy bytes buffer handling                          |
| smallvec       | Small vector optimization                                |

### Memory and Threading

- **GIL Management**: Python::with_gil and Python::allow_threads for safe GIL handling
- **py-clone Feature**: Clone Py<T> references (panics if GIL not held)
- **parking_lot Feature**: Use parking_lot primitives with Python-aware extensions
- **Reference Counting**: Automatic incref/decref for Python object lifetimes

---

## Technical Architecture

### Component Structure

```text
Python Code
    |
    v
+-------------------+
|   pyo3 (main)     |  <- User-facing API, macros, conversions
+-------------------+
    |
    v
+-------------------+
| pyo3-macros       |  <- Procedural macros (#[pyclass], #[pyfunction], etc.)
+-------------------+
    |
    v
+-------------------+
| pyo3-macros-      |  <- Macro implementation backend
| backend           |
+-------------------+
    |
    v
+-------------------+
| pyo3-ffi          |  <- Raw FFI bindings to Python C API
+-------------------+
    |
    v
+-------------------+
| pyo3-build-config |  <- Build-time Python detection and configuration
+-------------------+
    |
    v
+-------------------+
| Python C API      |  <- CPython, PyPy, or GraalPy interpreter
+-------------------+
```

### Workspace Crates

| Crate              | Purpose                                                |
| ------------------ | ------------------------------------------------------ |
| pyo3               | Main library with macros and type conversions          |
| pyo3-ffi           | Raw FFI bindings, usable independently                 |
| pyo3-build-config  | Build-time Python interpreter detection                |
| pyo3-macros        | Procedural macro definitions                           |
| pyo3-macros-backend| Macro implementation shared between macros             |
| pyo3-introspection | Type introspection for documentation generation        |

### Object Model

```text
Python Object Hierarchy:
                    Py<T>
                      |
        +-------------+-------------+
        |             |             |
   Py<PyAny>    Py<PyDict>    Py<PyList>
        |             |             |
        v             v             v
   Bound<'py, T>  - lifetime-bound reference to Python object
        |
        v
   &T (PyRef/PyRefMut) - borrowed reference to #[pyclass] data
```

### GIL and Thread Safety

```rust
// Acquire GIL for Python operations
Python::with_gil(|py| {
    let obj: Py<PyList> = PyList::new(py, [1, 2, 3])?;
    // py token proves GIL is held
});

// Release GIL for Rust-only computation
py.allow_threads(|| {
    // Expensive Rust computation without blocking Python threads
    compute_intensive_operation()
});
```

---

## Installation and Usage

### Quick Start with maturin

```bash
# Create project directory
mkdir my_module && cd my_module

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install maturin
pip install maturin

# Initialize PyO3 project
maturin init --bindings pyo3

# Build and install in development mode
maturin develop

# Test in Python
python -c "import my_module; print(my_module.sum_as_string(5, 20))"
```

### Project Structure

```text
my_module/
├── Cargo.toml
├── pyproject.toml
└── src/
    └── lib.rs
```

**Cargo.toml**:

```toml
[package]
name = "my_module"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_module"
crate-type = ["cdylib"]

[dependencies]
pyo3 = "0.28.0"
```

**src/lib.rs**:

```rust
use pyo3::prelude::*;

/// A Python class implemented in Rust
#[pyclass]
struct Calculator {
    value: f64,
}

#[pymethods]
impl Calculator {
    #[new]
    fn new(initial: f64) -> Self {
        Calculator { value: initial }
    }

    fn add(&mut self, x: f64) {
        self.value += x;
    }

    fn result(&self) -> f64 {
        self.value
    }
}

/// A Python function implemented in Rust
#[pyfunction]
fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0u64;
            let mut b = 1u64;
            for _ in 2..=n {
                let c = a + b;
                a = b;
                b = c;
            }
            b
        }
    }
}

/// Python module definition
#[pymodule]
fn my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Calculator>()?;
    m.add_function(wrap_pyfunction!(fibonacci, m)?)?;
    Ok(())
}
```

### Embedding Python in Rust

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.28.0", features = ["auto-initialize"] }
```

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Import Python module
        let sys = py.import("sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        println!("Python version: {}", version);

        // Execute Python code
        let locals = PyDict::new(py);
        py.run(c"result = sum(range(10))", None, Some(&locals))?;
        let result: i32 = locals.get_item("result")?.unwrap().extract()?;
        println!("Sum: {}", result);

        Ok(())
    })
}
```

### Building Wheels for Distribution

```bash
# Build wheel for current Python
maturin build --release

# Build abi3 wheel (works on Python 3.8+)
maturin build --release --features abi3-py38

# Build for multiple platforms (in CI)
maturin build --release --target x86_64-unknown-linux-gnu
maturin build --release --target x86_64-apple-darwin
maturin build --release --target x86_64-pc-windows-msvc

# Publish to PyPI
maturin publish
```

### Async Functions

```rust
use pyo3::prelude::*;

#[pyfunction]
async fn async_sleep(seconds: f64) -> PyResult<String> {
    tokio::time::sleep(std::time::Duration::from_secs_f64(seconds)).await;
    Ok(format!("Slept for {} seconds", seconds))
}
```

---

## Ecosystem Tools

| Tool               | Purpose                                              | Stars  |
| ------------------ | ---------------------------------------------------- | ------ |
| maturin            | Build and publish PyO3/cffi/uniffi Python packages   | 5,354  |
| setuptools-rust    | Setuptools plugin for Rust extensions                | 1,400+ |
| rust-numpy         | NumPy ndarray bindings for Rust                      | 1,100+ |
| pyo3-log           | Bridge Rust log crate to Python logging              | 100+   |
| pythonize          | Serde serializer for Python objects                  | 300+   |
| pyo3-async-runtimes| Tokio/async-std asyncio bridges                      | 200+   |
| pyo3-arrow         | Apache Arrow integration                             | New    |
| pyo3-bytes         | Zero-copy bytes buffer handling                      | New    |
| rustimport         | Direct Rust import from Python without compilation   | 500+   |

---

## Notable Projects Using PyO3

| Project         | Description                                          | Stars   |
| --------------- | ---------------------------------------------------- | ------- |
| Pydantic v2     | Data validation using Python type hints              | 24,000+ |
| Polars          | Lightning-fast DataFrame library                     | 32,000+ |
| cryptography    | Python cryptographic library                         | 6,500+  |
| tokenizers      | Hugging Face fast tokenizers                         | 9,000+  |
| orjson          | Fast JSON library for Python                         | 6,500+  |
| ruff            | Extremely fast Python linter                         | 37,000+ |
| delta-rs        | Native Delta Lake implementation                     | 2,500+  |
| tantivy-py      | Tantivy search engine bindings                       | 500+    |
| arro3           | Minimal Apache Arrow Python library                  | New     |
| connector-x     | Fastest DB to DataFrame loader                       | 2,000+  |

---

## Relevance to Claude Code Development

### Direct Applications

1. **High-Performance MCP Servers**: Write MCP server tool implementations in Rust for compute-intensive operations (code analysis, large file processing, parallel search).

2. **Fast CLI Tools**: Build Python-callable CLI utilities with Rust performance for tasks like code indexing, dependency analysis, or AST manipulation.

3. **Data Processing Plugins**: Create plugins for handling large codebases or datasets that would be slow in pure Python.

4. **Embedding Python in Rust Tools**: Rust-based Claude Code infrastructure could embed Python for user scripting without separate interpreter management.

5. **Cross-Platform Binary Distribution**: Use abi3 for distributing single binary per platform that works across Python versions.

### Patterns Worth Adopting

1. **Feature Flag Architecture**: PyO3's granular feature flags (30+ optional integrations) demonstrate precise control over functionality - applicable to skill/plugin configuration.

2. **Dual-License Model**: MIT OR Apache-2.0 dual licensing maximizes adoption while maintaining permissive terms.

3. **Build Configuration Detection**: pyo3-build-config's automatic Python environment detection is a pattern for environment-aware tooling.

4. **Type Conversion Traits**: FromPyObject/IntoPy pattern for bidirectional type conversion between language boundaries.

5. **GIL-Aware Async**: Safe patterns for mixing Rust async with Python threading constraints.

6. **Workspace Crate Organization**: Separating FFI, macros, and user API into distinct crates with precise version pinning.

### Integration Opportunities

1. **FastMCP Performance Layer**: Write performance-critical FastMCP tools in Rust with PyO3, exposing them as Python functions.

2. **Code Analysis Acceleration**: Use rust-numpy or pyo3-arrow for high-performance code metrics computation.

3. **Parallel Search Tools**: Implement grep-like search tools in Rust with Python bindings for Claude Code integration.

4. **AST Processing**: Fast Python AST manipulation using Rust's ruff_python_parser with PyO3 bindings.

5. **Binary Protocol Handlers**: Efficient binary file format parsing (protobuf, msgpack, custom formats) exposed to Python.

### Comparison with Other Binding Approaches

| Aspect              | PyO3          | ctypes        | cffi          | Cython        | SWIG          |
| ------------------- | ------------- | ------------- | ------------- | ------------- | ------------- |
| Language            | Rust          | Python        | Python/C      | Python/C      | Any           |
| Memory Safety       | Automatic     | Manual        | Manual        | Semi-auto     | Manual        |
| Type Conversions    | Automatic     | Manual        | Manual        | Semi-auto     | Generated     |
| Build Complexity    | Low (maturin) | None          | Medium        | High          | High          |
| Performance         | Excellent     | Good          | Excellent     | Excellent     | Excellent     |
| Async Support       | Yes           | No            | No            | Limited       | No            |
| Macro Ergonomics    | Excellent     | N/A           | N/A           | Good          | Poor          |
| Wheel Building      | maturin       | N/A           | setuptools    | setuptools    | setuptools    |

### Limitations to Consider

1. **Rust Learning Curve**: Developers must understand Rust ownership and borrowing for effective PyO3 usage.

2. **Compile Times**: Rust compilation is slower than pure Python development cycles.

3. **Debug Complexity**: Debugging across Rust/Python boundary requires expertise in both ecosystems.

4. **GIL Constraints**: CPU-bound parallel Rust code must use allow_threads carefully to avoid GIL contention.

5. **Binary Size**: Rust binaries are larger than equivalent C extensions.

6. **Free-threaded Python**: No-GIL Python 3.13t support is experimental.

---

## References

| Source                        | URL                                                                | Accessed   |
| ----------------------------- | ------------------------------------------------------------------ | ---------- |
| Official Website              | <https://pyo3.rs>                                                  | 2026-02-05 |
| GitHub Repository             | <https://github.com/PyO3/pyo3>                                     | 2026-02-05 |
| GitHub README                 | <https://github.com/PyO3/pyo3/blob/main/README.md>                 | 2026-02-05 |
| User Guide (stable)           | <https://pyo3.rs/v0.28.0/>                                         | 2026-02-05 |
| API Documentation             | <https://docs.rs/pyo3/0.28.0/>                                     | 2026-02-05 |
| Cargo.toml (features)         | <https://github.com/PyO3/pyo3/blob/main/Cargo.toml>                | 2026-02-05 |
| maturin Repository            | <https://github.com/PyO3/maturin>                                  | 2026-02-05 |
| pyo3-async-runtimes           | <https://github.com/PyO3/pyo3-async-runtimes>                      | 2026-02-05 |
| rust-numpy                    | <https://github.com/PyO3/rust-numpy>                               | 2026-02-05 |
| setuptools-rust               | <https://github.com/PyO3/setuptools-rust>                          | 2026-02-05 |
| GitHub API (statistics)       | API calls for stars, forks, releases                               | 2026-02-05 |

**Research Method**: Information gathered from official GitHub repository README, Cargo.toml feature definitions, raw file fetches from main branch, and GitHub API for statistics. maturin statistics verified via separate API call. All statistics verified via direct API calls on 2026-02-05.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 0.28.0                              |
| Rust Edition       | 2021                                |
| Min Rust Version   | 1.83                                |
| GitHub Stars       | 15,268 (as of 2026-02-05)           |
| maturin Stars      | 5,354 (as of 2026-02-05)            |
| Next Review Date   | 2026-05-05                          |

**Review Triggers**:

- Major version release (0.29.0, 1.0.0)
- Free-threaded Python (no-GIL) exits experimental status
- PyPy or GraalPy compatibility changes
- New significant type integrations added
- GitHub stars milestone (20K)
- maturin major release
- Breaking changes to macro API
- New stable ABI versions (abi3-py315)
