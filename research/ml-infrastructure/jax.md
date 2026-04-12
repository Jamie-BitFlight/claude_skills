# JAX

**Research Date**: 2026-04-12
**Source URL**: <https://docs.jax.dev/en/latest/quickstart.html>
**GitHub Repository**: <https://github.com/jax-ml/jax>
**Version at Research**: 0.9.2 (released 2026-03-18)
**License**: Apache-2.0

---

## Overview

JAX is a Python library for accelerator-oriented array computation and program transformation, designed for high-performance numerical computing and large-scale machine learning. It provides a NumPy-like interface while enabling automatic differentiation, just-in-time (JIT) compilation via OpenXLA, and efficient vectorization across CPU, GPU, and TPU hardware. JAX's composable transformations allow researchers to differentiate, vectorize, and compile code with minimal modifications to existing NumPy programs.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual gradient computation is error-prone and tedious | JAX provides automatic differentiation (grad, jacfwd, jacrev) supporting reverse and forward modes to any order |
| NumPy code cannot efficiently run on accelerators (GPU/TPU) | JAX wraps NumPy operations with XLA backend compilation via `jax.jit` for end-to-end hardware-accelerated execution |
| Batching operations across array axes requires manual loop rewrites | JAX's `vmap` (vectorize map) automatically transforms element-wise functions into batch operations for better performance |
| Maintaining separate code paths for CPU vs accelerator deployment | Unified JAX code runs unchanged across CPU, GPU (NVIDIA, AMD), and TPU (Google Cloud) with simple backend selection |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 35,307 | 2026-04-12 |
| GitHub Forks | 3,505 | 2026-04-12 |
| Latest Release | 0.9.2 | 2026-03-18 |
| Python Version Required | 3.11+ | 2026-04-12 |
| PyPI Weekly Downloads | ~500K+ (estimated) | 2026-04-12 |

---

## Key Features

### Automatic Differentiation Transformations

JAX can automatically differentiate native Python and NumPy functions, including through control flow (loops, branches, recursion, closures). It supports:

- **Reverse-mode differentiation** via `jax.grad()` for efficient gradient computation (backpropagation)
- **Forward-mode differentiation** via `jax.jacfwd()` for Jacobian computation along forward axes
- **Reverse-mode Jacobian** via `jax.jacrev()` for computing Jacobians efficiently in reverse
- **Higher-order derivatives** via composition — take derivatives of derivatives to any order, and compose forward and reverse modes arbitrarily
- **Experimental higher-order derivatives** via `jax.experimental.jet` for Taylor-mode automatic differentiation

### Just-In-Time Compilation

JAX integrates with OpenXLA for end-to-end compilation and optimization:

- `@jax.jit` decorator compiles functions automatically on first call, caching compilations for subsequent calls with matching array shapes
- Supports both CPU and accelerator targets (GPU/TPU) with transparent backend selection
- Enables complex control flow and data structures while maintaining compilation benefits

### Automatic Vectorization

The `jax.vmap` function transforms element-wise operations into vectorized operations:

- Maps functions over one or more array axes without explicit loops
- Pushes loops down to primitive operations (e.g., turns matrix-vector multiply into matrix-matrix multiply for better hardware utilization)
- Composable with `jit` and `grad` for efficient batched gradient computation
- Single-program multiple-data (SPMD) execution via `jax.pmap` for distributed training across multiple devices

### NumPy-compatible API

JAX provides `jax.numpy` — a drop-in NumPy-like interface with the same function signatures, enabling researchers to write familiar code that runs on accelerators:

- Array creation, manipulation, and mathematical operations match NumPy conventions
- Broadcasting and indexing semantics identical to NumPy
- Common operations optimized for GPU/TPU execution via XLA

---

## Technical Architecture

JAX is built on a functional, composable design that separates concerns across multiple layers:

**Frontend Layer**: User-facing Python API via `jax.numpy`, `jax.grad`, `jax.jit`, `jax.vmap` — these are composable transformations that can be nested arbitrarily.

**Primitive Operations Layer**: JAX decomposes all operations (including control flow) into a set of primitives with defined transformation rules. Each primitive registers handlers for forward-mode and reverse-mode differentiation, vectorization, and lowering to XLA.

**Compiler Backend**: JAX lowers its intermediate representation (IR) to OpenXLA, which performs hardware-specific optimization and code generation. XLA provides the abstraction for targeting CPU, GPU (NVIDIA CUDA/cuDNN, AMD ROCM, Apple Metal), and TPU (Google TPU).

**Key Design Decisions**:

1. **Functional Programming Model**: JAX functions must be pure (no side effects) to enable safe composition of transformations. This constraint enables efficient JIT compilation and correct automatic differentiation.

2. **Static Shape Tracing**: JIT compilation traces through Python code with concrete array shapes, producing specialized executable code. Dynamic shapes require tracing at runtime or using control flow primitives.

3. **Composable Transformations**: Transformations (grad, jit, vmap) are first-class operations that can be nested: `jax.jit(jax.vmap(jax.grad(loss_fn)))` compiles a vectorized gradient computation across a batch.

4. **Hardware Abstraction via XLA**: JAX does not implement backend-specific kernels; it relies on XLA's optimizer to generate efficient code for each hardware target. This decouples JAX's API from hardware evolution.

---

## Installation & Usage

### Basic Installation

```bash
# CPU-only installation
pip install -U jax

# GPU support (NVIDIA CUDA 12)
pip install -U "jax[cuda12]"

# GPU support (NVIDIA CUDA 13)
pip install -U "jax[cuda13]"

# AMD GPU support (ROCM 5.7)
pip install -U "jax[amd]"

# Apple Silicon (Metal acceleration)
pip install -U "jax[metal]"

# TPU support (requires Google Cloud environment)
pip install -U "jax[tpu]"
```

### Basic Usage Example

```python
import jax
import jax.numpy as jnp

# Define a simple function
def f(x):
    return x ** 2 + 2 * x + 1

# Automatic differentiation
x = 3.0
print(jax.grad(f)(x))  # Output: 8.0 (derivative of f at x=3)

# Compile with JIT for performance
@jax.jit
def compiled_f(x):
    return jnp.sin(x) + jnp.cos(x)

# Vectorize over batch dimension
def loss_fn(params, x, y):
    return jnp.mean((params * x - y) ** 2)

# Compute gradients efficiently across batches
batched_grad = jax.vmap(jax.grad(loss_fn), in_axes=(None, 0, 0))
```

### Training Loop Pattern

```python
import jax
import jax.numpy as jnp
from jax import grad, jit

# Initialize parameters
params = jnp.array([1.0, 2.0, 3.0])

# Define loss function
def loss(params, x, y):
    return jnp.mean((params @ x - y) ** 2)

# Compiled gradient function
grad_loss = jit(grad(loss))

# Training step
lr = 0.01
for epoch in range(100):
    grads = grad_loss(params, x_batch, y_batch)
    params = params - lr * grads
```

---

## Relevance to Claude Code Development

### Applications

JAX's approach to composable program transformations has relevance to Claude Code development in several ways:

1. **Compiler Design Patterns**: JAX's functional transformation model (tracing, primitive registration, staged computation) provides a proven approach for building composable compiler infrastructure. This pattern applies to any system requiring flexible code transformation (agents executing varied tasks, multi-stage compilation of prompts).

2. **Automatic Differentiation for Feedback Loops**: JAX's ability to differentiate through arbitrary Python code (including control flow) is relevant for agent systems that need to optimize behavior based on feedback signals — e.g., refining prompts or strategies based on observed task outcomes.

3. **Vectorization and Batch Processing**: JAX's `vmap` pattern for transparent batching without code changes applies to orchestrating multiple independent agent tasks in parallel while maintaining single-task readability.

### Patterns Worth Adopting

1. **Composable Function Transformations**: JAX's stacking of transformations (e.g., `jit(vmap(grad(...)))`) demonstrates how to layer functionality orthogonally. In Claude Code, agent behaviors could be enhanced through composable middleware patterns (logging, caching, validation).

2. **Functional Purity Constraints**: JAX's requirement that functions be pure enables aggressive optimization and composition. Applying similar principles to agent task definitions (pure input→output mapping) would improve testability and reusability.

3. **Lazy Compilation and Tracing**: JAX's just-in-time compilation strategy could inform how Claude Code orchestrates expensive operations (long-running agent tasks, external API calls) — deferring evaluation until shapes/types are concrete.

### Integration Opportunities

1. **Prompt Optimization via Differentiation**: If Claude Code tracked metrics of agent task quality (success rate, token efficiency, user satisfaction) as differentiable signals, JAX-style autodiff could optimize prompt templates automatically — similar to how JAX optimizes neural network parameters.

2. **Hardware-Agnostic Agent Execution**: JAX's abstraction of hardware targets via XLA suggests that Claude Code could benefit from a similar abstraction layer for agent execution — defining agent logic once, with transparent routing to local, remote, or specialized execution environments.

3. **Batched Agent Operations**: For orchestrating many similar agent tasks (e.g., apply a code review agent to 100 PRs), adopting JAX's vmap pattern would allow writing the single-PR logic once while executing batched operations efficiently.

---

## References

- [JAX Official Documentation](https://docs.jax.dev/en/latest/) (accessed 2026-04-12)
- [JAX GitHub Repository](https://github.com/jax-ml/jax) (accessed 2026-04-12)
- [JAX on PyPI](https://pypi.org/project/jax/) (accessed 2026-04-12)
- [A Quick Start Guide to JAX — Intel Developer Zone](https://www.intel.com/content/www/us/en/developer/articles/technical/a-quick-start-guide-to-jax.html) (accessed 2026-04-12)
- [Getting Started with JAX — JAX Documentation](https://docs.jax.dev/en/latest/beginner_guide.html) (accessed 2026-04-12)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [TrainLoop](./trainloop.md) | ml-infrastructure | Managed RL fine-tuning platform using automatic differentiation for reward model training |
| [Ray](./ray.md) | ml-infrastructure | Distributed compute engine for scaling JAX-based ML workloads across clusters |
| [microgpt Playground](./microgpt-playground.md) | ml-infrastructure | Browser-native ML model training implementing automatic differentiation concepts |
| [Zvec](./zvec.md) | ml-infrastructure | Embedded vector database for similarity search in JAX-powered applications |
| [RustPython](../python-runtimes/rustpython.md) | python-runtimes | Alternative Python runtime enabling JAX execution in embedded and WebAssembly contexts |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-12 |
| Version at Verification | 0.9.2 |
| Next Review Recommended | 2026-07-12 |
| Confidence Map | Overview: high; Key Statistics: high (dated); Key Features: high; Technical Architecture: medium (inferred from public docs + code); Installation & Usage: high; Relevance to Claude Code: medium (speculative); References: high |
