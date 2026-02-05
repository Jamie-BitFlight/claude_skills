# RustPython

| Field         | Value                                                              |
| ------------- | ------------------------------------------------------------------ |
| Research Date | 2026-02-05                                                         |
| Primary URL   | <https://rustpython.github.io/>                                    |
| GitHub        | <https://github.com/RustPython/RustPython>                         |
| Crates.io     | <https://crates.io/crates/rustpython>                              |
| Docs.rs       | <https://docs.rs/rustpython/>                                      |
| Version       | 0.4.0 (Rust Edition 2024, requires Rust 1.93.0+)                   |
| License       | MIT                                                                |
| Discord       | <https://discord.gg/vru8NypEhv>                                    |

---

## Overview

RustPython is a Python 3 interpreter written entirely in Rust. It provides CPython 3.14.0+ compatibility and can run as a standalone interpreter, be compiled to WebAssembly for browser execution, or be embedded into Rust applications for scripting. The project shares its parser with Ruff (the fast Python linter) via the `ruff_python_parser` crate, and includes an experimental JIT compiler for native code generation.

---

## Problem Addressed

| Problem                                              | Solution                                                                      |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- |
| Python cannot run natively in browsers               | WebAssembly (WASI) compilation enables Python execution in any WASM runtime   |
| Embedding Python in Rust requires FFI complexity     | Native Rust library provides safe, ergonomic Python scripting integration     |
| CPython has large runtime footprint                  | Lean Rust implementation with configurable features and freeze-stdlib option  |
| Python security in sandboxed environments            | WASM isolation provides security boundaries for untrusted code execution      |
| Cross-platform Python deployment complexity          | Single WASM binary runs on any platform with WASM runtime support             |
| Python interpreter extension requires C knowledge    | Rust-native extension model for adding Python modules and types               |

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 21,752                    | 2026-02-05    |
| GitHub Forks      | 1,400                     | 2026-02-05    |
| Open Issues       | 372                       | 2026-02-05    |
| Contributors      | 360+                      | 2026-02-05    |
| Primary Language  | Rust                      | 2026-02-05    |
| Repository Age    | Since May 2018            | 2026-02-05    |
| Rust Edition      | 2024                      | 2026-02-05    |
| Min Rust Version  | 1.93.0                    | 2026-02-05    |

---

## Key Features

### Core Interpreter

- **CPython 3.14.0+ Compatibility**: Targets modern Python 3 language features
- **Stack-based VM**: Executes compiled bytecode using stack machine architecture
- **Standard Library**: Partial stdlib implementation in Rust with CPython Lib/ fallback
- **pip Support**: Full pip installation and package management with SSL features
- **venv Support**: Virtual environment creation for isolated package management
- **Threading**: Optional multi-threading support via `threading` feature flag

### WebAssembly Support

- **WASI Compilation**: Build standalone WASM binary for any WASI-compatible runtime
- **Browser Execution**: Run Python directly in web browsers via wasm-bindgen
- **Freeze Stdlib**: Embed standard library in WASM binary for self-contained deployment
- **JS Interop**: Bidirectional JavaScript/Python data exchange in browser context
- **Runtime Compatibility**: Works with wasmer, wasmtime, and browser WASM engines

### Embedding in Rust

- **Library Crate**: Use as dependency for adding Python scripting to Rust applications
- **PyModule/PyClass Macros**: Ergonomic derive macros for exposing Rust types to Python
- **Safe FFI Alternative**: No unsafe C FFI required, pure Rust integration
- **Configurable Features**: Fine-grained control over included functionality

### JIT Compiler (Experimental)

- **Native Code Generation**: Compile Python functions to machine code
- **Opt-in Compilation**: Call `__jit__()` on functions to enable JIT
- **Cranelift Backend**: Uses Cranelift for code generation
- **Requirements**: Requires autoconf, automake, libtool, clang at build time

### Parser (via ruff_python_parser)

- **Shared with Ruff**: Uses the same parser as Ruff Python linter
- **Fast Parsing**: Rust-native lexer and parser for Python source
- **AST Generation**: Produces standard Python AST for compilation

---

## Technical Architecture

### Component Stack

```text
Python Source Code
       |
   ruff_python_parser (Lexer + Parser)
       |
   Abstract Syntax Tree (AST)
       |
   rustpython-compiler (AST to Bytecode)
       |
   Bytecode
       |
   rustpython-vm (Stack-based VM execution)
       |
   Output / Side Effects
```

### Crate Structure

| Crate                    | Purpose                                           |
| ------------------------ | ------------------------------------------------- |
| rustpython               | Main binary and library entry point               |
| rustpython-vm            | Virtual machine, builtins, core execution         |
| rustpython-compiler      | AST to bytecode compilation                       |
| rustpython-compiler-core | Core compiler data structures                     |
| rustpython-codegen       | Code generation utilities                         |
| rustpython-stdlib        | Rust-implemented standard library modules         |
| rustpython-pylib         | Python-side standard library (from CPython)       |
| rustpython-jit           | Experimental JIT compiler                         |
| rustpython-derive        | Procedural macros for PyModule/PyClass            |
| rustpython-common        | Shared utilities (float ops, etc.)                |
| rustpython-sre_engine    | Regular expression engine                         |
| rustpython-literal       | Literal parsing utilities                         |

### VM Architecture

- **Stack Machine**: Operations push/pop values from evaluation stack
- **Frame-based Execution**: Each function call creates new frame with local namespace
- **Object Model**: Python objects implemented as Rust structs with trait implementations
- **GC**: Reference counting with cycle detection (via Rust's ownership where possible)

---

## Installation and Usage

### Build from Source

```bash
# Clone repository
git clone https://github.com/RustPython/RustPython
cd RustPython

# Windows: enable symlinks for Lib/
git config core.symlinks true

# Build and run demo
cargo run --release demo_closures.py

# Interactive REPL
cargo run --release
```

### Install via Cargo

```bash
# Install from Git
cargo install --git https://github.com/RustPython/RustPython rustpython

# Run interpreter
rustpython
```

### Install via Conda

```bash
conda install rustpython -c conda-forge
```

### Feature Flags

```bash
# Default features
cargo run --release  # threading, stdlib, stdio, importlib, ssl-rustls

# Enable JIT compiler
cargo run --release --features jit

# Enable SQLite support
cargo run --release --features sqlite

# Build with OpenSSL instead of rustls
cargo run --release --no-default-features --features "threading stdlib stdio importlib ssl-openssl"
```

### pip Installation

```bash
# Install with SSL support first
cargo install --git https://github.com/RustPython/RustPython

# Bootstrap pip
rustpython --install-pip

# Use pip normally
rustpython -m pip install requests
```

### Virtual Environment

```bash
# Create venv
rustpython -m venv myenv

# Activate (Linux/macOS)
source myenv/bin/activate

# Now 'python' points to rustpython
python --version
```

### WebAssembly Build

```bash
# Add WASI target
rustup target add wasm32-wasip1

# Build WASM binary with frozen stdlib
cargo build --target wasm32-wasip1 --no-default-features \
    --features freeze-stdlib,stdlib --release

# Run with wasmer
wasmer run --dir . -- target/wasm32-wasip1/release/rustpython.wasm script.py
```

### Embedding in Rust

```rust
use rustpython_vm as vm;

fn main() -> vm::PyResult<()> {
    vm::Interpreter::without_stdlib(Default::default()).enter(|vm| {
        let scope = vm.new_scope_with_builtins();
        let code = vm.compile(
            r#"print("Hello from RustPython!")"#,
            vm::compile::Mode::Exec,
            "<embedded>".to_owned(),
        )?;
        vm.run_code_obj(code, scope)?;
        Ok(())
    })
}
```

### JIT Compilation

```python
def compute(n):
    total = 0
    for i in range(n):
        total += i
    return total

# Enable JIT for this function
compute.__jit__()

# Subsequent calls execute native code
result = compute(1000000)
```

---

## Notable Projects Using RustPython

| Project       | Description                                                    | URL                                           |
| ------------- | -------------------------------------------------------------- | --------------------------------------------- |
| GreptimeDB    | Cloud-native distributed time-series database with RustPython scripting | <https://github.com/GreptimeTeam/greptimedb> |
| Ruff          | Extremely fast Python linter (shares parser with RustPython)   | <https://github.com/astral-sh/ruff>           |
| pyckitup      | Game engine written in Rust with Python scripting              | <https://github.com/pickitup247/pyckitup>     |
| Robot Rumble  | Arena-based AI competition platform                            | <https://github.com/robot-rumble/logic>       |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Browser-based Python Execution**: RustPython's WASM support enables running Python code in browser environments, potentially useful for web-based development tools or sandboxed code execution.

2. **Embedded Scripting for Tools**: Rust-based Claude Code tools could embed RustPython for user-extensible scripting without CPython dependency.

3. **Sandboxed Code Execution**: WASM isolation provides security boundaries for executing untrusted Python code in agent workflows.

4. **Lightweight Python Runtime**: For scenarios where full CPython is too heavy, RustPython with frozen stdlib provides smaller deployment footprint.

5. **Cross-Platform Consistency**: Single WASM binary ensures identical Python behavior across all platforms.

### Patterns Worth Adopting

1. **Feature Flag Architecture**: RustPython's fine-grained feature flags enable precise control over included functionality - applicable to Claude Code skill configuration.

2. **Parser Reuse (ruff_python_parser)**: Sharing parser implementation between RustPython and Ruff demonstrates effective code reuse across projects.

3. **Freeze-stdlib Pattern**: Embedding standard library in binary for self-contained deployment - applicable to Claude Code plugin distribution.

4. **Opt-in JIT**: Manual JIT activation via `__jit__()` provides user control over optimization - similar to opt-in performance features in skills.

5. **Derive Macros for Extension**: `PyModule`/`PyClass` macros demonstrate ergonomic Rust extension patterns.

### Integration Opportunities

1. **MCP Server in WASM**: Deploy MCP servers as WASM modules using RustPython for portable, sandboxed execution.

2. **Python Code Analysis**: Use ruff_python_parser (shared with RustPython) for fast Python AST analysis in code review skills.

3. **Browser-based Code Execution**: Run Python examples in documentation or tutorials without server-side execution.

4. **Embedded Scripting Layer**: Add Python scripting to Rust-based Claude Code tools without CPython FFI complexity.

5. **Security Sandbox**: Use WASM isolation for running user-provided Python code safely in agentic workflows.

### Comparison with Other Python Runtimes

| Aspect              | RustPython           | CPython              | PyPy                 | MicroPython          |
| ------------------- | -------------------- | -------------------- | -------------------- | -------------------- |
| Implementation      | Rust                 | C                    | Python (RPython)     | C                    |
| WASM Support        | Native               | Via Emscripten       | Limited              | Limited              |
| Embedding Ease      | Rust-native          | C FFI required       | Complex              | Easy (embedded)      |
| Startup Time        | Fast                 | Moderate             | Slow                 | Very fast            |
| Runtime Performance | Moderate             | Fast                 | Very fast (JIT)      | Slow                 |
| Memory Footprint    | Moderate             | Large                | Large                | Very small           |
| CPython Compat      | 3.14.0+ target       | Reference            | High                 | Subset               |
| JIT                 | Experimental         | No (PEP 659 adaptive)| Yes (mature)         | No                   |

### Limitations to Consider

1. **Not Production-Ready**: Project documentation explicitly states RustPython is in development and not fully production-ready.

2. **Performance Gap**: Pure interpretation without mature JIT is slower than CPython for compute-intensive workloads.

3. **Incomplete stdlib**: Not all standard library modules are implemented; some require CPython fallback.

4. **C Extension Incompatibility**: Cannot run CPython C extensions (numpy, pandas, etc.) - pure Python packages only.

5. **JIT Maturity**: JIT compiler is experimental with limited optimization coverage.

---

## References

| Source                      | URL                                                                | Accessed   |
| --------------------------- | ------------------------------------------------------------------ | ---------- |
| Official Website            | <https://rustpython.github.io/>                                    | 2026-02-05 |
| GitHub Repository           | <https://github.com/RustPython/RustPython>                         | 2026-02-05 |
| GitHub README               | <https://github.com/RustPython/RustPython/blob/main/README.md>     | 2026-02-05 |
| Architecture Documentation  | <https://github.com/RustPython/RustPython/blob/main/architecture/architecture.md> | 2026-02-05 |
| WASM Documentation          | <https://github.com/RustPython/RustPython/blob/main/wasm/README.md> | 2026-02-05 |
| Cargo.toml (version info)   | <https://github.com/RustPython/RustPython/blob/main/Cargo.toml>    | 2026-02-05 |
| User Guide                  | <https://rustpython.github.io/docs/>                               | 2026-02-05 |
| Online Demo                 | <https://rustpython.github.io/demo/>                               | 2026-02-05 |
| Docs.rs API Documentation   | <https://docs.rs/rustpython/>                                      | 2026-02-05 |
| FOSDEM 2019 Talk            | <https://www.youtube.com/watch?v=nJDY9ASuiLc>                      | 2026-02-05 |
| EuroPython 2018 Talk        | <https://www.youtube.com/watch?v=YMmio0JHy_Y>                      | 2026-02-05 |

**Research Method**: Information gathered from official GitHub repository README, architecture documentation, WASM documentation, Cargo.toml workspace configuration, and GitHub API for statistics. All statistics verified via direct API calls on 2026-02-05.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 0.4.0                               |
| Rust Edition       | 2024                                |
| Min Rust Version   | 1.93.0                              |
| GitHub Stars       | 21,752 (as of 2026-02-05)           |
| Contributors       | 360+ (as of 2026-02-05)             |
| Next Review Date   | 2026-05-05                          |

**Review Triggers**:

- Major version release (0.5.0, 1.0.0)
- JIT compiler exits experimental status
- Significant CPython compatibility milestone (e.g., 3.15 support)
- GitHub stars milestone (25K, 30K)
- Production-ready announcement
- Notable new production users
- Breaking changes to embedding API
