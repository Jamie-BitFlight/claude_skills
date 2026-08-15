---
name: Trio
description: Trio is a Python library for async concurrency and I/O that introduced the "structured concurrency" paradigm to the Python ecosystem. Unlike asyncio, Trio guarantees that tasks run to completion...
license: MIT OR Apache-2.0
metadata:
  topic: trio
  category: async-libraries
  source_url: https://trio.readthedocs.io
  github: python-trio/trio
  version: "v0.32.0"
  verified: "2026-02-04"
  next_review: "2026-05-04"
---

## Overview

Trio is a Python library for async concurrency and I/O that introduced the "structured concurrency" paradigm to the Python ecosystem. Unlike asyncio, Trio guarantees that tasks run to completion within explicit scopes called "nurseries," making concurrent code easier to reason about and debug. The library prioritizes usability and correctness over raw performance, with a design philosophy that makes it hard to write incorrect concurrent code.

---

## Problem Addressed

| Problem                                                   | Solution                                                                                      |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| asyncio callback-based APIs are error-prone               | Pure async/await API with no callbacks, futures, or promises                                  |
| Concurrent tasks can leak or outlive their callers        | Structured concurrency via nurseries ensures tasks complete within their scope                |
| Cancellation is inconsistent and hard to reason about     | Unified cancel scopes with deterministic cancellation semantics                               |
| Schedule/cancel points are unpredictable                  | Static guarantees: functions are always or never checkpoints                                  |
| Exception handling in concurrent code is complex          | Exceptions propagate naturally through nursery boundaries                                     |
| Resource cleanup in async code often fails                | try/finally and context managers work correctly with structured concurrency                   |
| Hard to identify where concurrent execution can interleave| Explicit checkpoints make interleaving points visible in code                                 |

---

## Key Statistics

| Metric                | Value                     | Date Gathered |
| --------------------- | ------------------------- | ------------- |
| GitHub Stars          | 7,143                     | 2026-02-04    |
| GitHub Forks          | 381                       | 2026-02-04    |
| Open Issues           | 316                       | 2026-02-04    |
| Contributors          | ~155                      | 2026-02-04    |
| PyPI Monthly Downloads| ~218M (30 days)           | 2026-02-04    |
| Primary Language      | Python                    | 2026-02-04    |
| Repository Age        | Since January 2017        | 2026-02-04    |
| Python Support        | 3.10+                     | 2026-02-04    |

---

## Key Features

### Structured Concurrency

- **Nurseries**: Explicit scope for spawning concurrent tasks
- **Task completion guarantee**: All tasks spawned in a nursery complete before nursery exits
- **Exception propagation**: Exceptions from child tasks propagate to parent naturally
- **No orphan tasks**: Impossible to spawn tasks that outlive their caller
- **Composability**: Nurseries can nest, preserving structured concurrency at all levels

### Cancel Scopes

- **Unified cancellation**: Single mechanism for timeouts and cancellation
- **Scope-based**: Cancellation applies to a defined scope, not arbitrary tasks
- **Composable timeouts**: `fail_after()` and `move_on_after()` context managers
- **Cancellation reasons**: v0.31.0+ supports attaching reason strings to cancellations
- **Shielding**: Protect critical sections from cancellation when needed

### Checkpoint System

- **Static guarantees**: Each function is always or never a checkpoint (no runtime variation)
- **Unified points**: Cancel points and schedule points are always the same
- **Async sandwich**: `await` marks all potential checkpoints visibly in code
- **Synchronous safety**: Regular (sync) functions never contain checkpoints

### Core Primitives

- **Tasks**: Primary unit of concurrency (no threads, no callbacks)
- **Events**: Coordination primitive for signaling between tasks
- **Channels**: Memory channels for inter-task communication (send/receive)
- **Locks and Semaphores**: Standard synchronization primitives
- **Capacity Limiters**: Control concurrent access to limited resources

### I/O Support

- **Sockets**: Full TCP/UDP networking with happy eyeballs
- **SSL/TLS**: Native TLS support with proper async integration
- **DTLS**: Datagram TLS support (v0.31.0+)
- **Subprocesses**: Async subprocess management
- **File I/O**: Via thread pool for non-blocking file operations
- **Signals**: Cross-platform signal handling

### Platform Support

- **Operating Systems**: Linux, macOS, Windows, FreeBSD
- **Python Implementations**: CPython 3.10+, PyPy3
- **Pure Python**: No C extensions required (except CFFI on Windows)

---

## Technical Architecture

### Design Principles

1. **Usability over speed**: Optimize for correctness and ease of use
2. **Explicit concurrency**: All task spawning is visible in code
3. **Causal APIs**: No callbacks or implicit concurrency
4. **Exception-based errors**: Standard Python error handling patterns
5. **Context manager cleanup**: `try/finally` and `with` work correctly

### Checkpoint Rules

<eg>
1. Synchronous functions: NEVER checkpoints
2. Trio async functions (no exception): ALWAYS checkpoints
3. Trio async functions (exception): MAY be checkpoints
4. Third-party async functions: UNKNOWN (treat as potential checkpoints)
</eg>

### Nursery Lifecycle

<eg>
async with trio.open_nursery() as nursery:
    nursery.start_soon(task1)    # Spawn task 1
    nursery.start_soon(task2)    # Spawn task 2
    # ... more spawning ...
# <-- All tasks MUST complete before reaching here
# <-- Exceptions from any task propagate here
</eg>

### Cancel Scope Nesting

<eg>
with trio.move_on_after(10):           # Outer: 10 second timeout
    with trio.fail_after(5):           # Inner: 5 second timeout
        await long_operation()         # Subject to 5-second limit
    await another_operation()          # Subject to 10-second limit
</eg>

### Dependencies

| Package          | Purpose                                      |
| ---------------- | -------------------------------------------- |
| attrs            | Class definitions and data structures        |
| sortedcontainers | Efficient sorted collections for scheduling  |
| idna             | Internationalized domain name handling       |
| outcome          | Capture function call outcomes (result/error)|
| sniffio          | Detect which async library is running        |
| cffi             | Windows-only: kernel I/O interface           |
| exceptiongroup   | Python <3.11: backport of ExceptionGroup     |

---

## Installation and Usage

### Installation

```bash
# Using pip
pip install trio

# Using uv (recommended)
uv pip install trio

# With conda
conda install -c conda-forge trio
```

### Basic Example: Hello World

```python
import trio


async def main():
    print("Hello from Trio!")


trio.run(main)
```

### Concurrent Tasks with Nursery

```python
import trio


async def fetch_page(url):
    print(f"Fetching {url}")
    await trio.sleep(1)  # Simulate I/O
    print(f"Done with {url}")


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(fetch_page, "https://example.com/1")
        nursery.start_soon(fetch_page, "https://example.com/2")
        nursery.start_soon(fetch_page, "https://example.com/3")
    # All three fetches complete before reaching here
    print("All pages fetched!")


trio.run(main)
```

### Timeout with Cancel Scope

```python
import trio


async def slow_operation():
    await trio.sleep(10)
    return "completed"


async def main():
    with trio.move_on_after(5) as cancel_scope:
        result = await slow_operation()
        print(f"Result: {result}")

    if cancel_scope.cancelled_caught:
        print("Operation timed out after 5 seconds")


trio.run(main)
```

### Echo Server Example

```python
import trio


async def echo_server(server_stream):
    async for data in server_stream:
        await server_stream.send_all(data)


async def main():
    await trio.serve_tcp(echo_server, 8000)


trio.run(main)
```

### Memory Channels

```python
import trio


async def producer(send_channel):
    async with send_channel:
        for i in range(10):
            await send_channel.send(i)


async def consumer(receive_channel):
    async with receive_channel:
        async for value in receive_channel:
            print(f"Received: {value}")


async def main():
    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(producer, send_channel)
        nursery.start_soon(consumer, receive_channel)


trio.run(main)
```

---

## Ecosystem

### Official python-trio Organization Projects

| Project           | Description                                          | Stars |
| ----------------- | ---------------------------------------------------- | ----- |
| trio              | Core async I/O library                               | 7,143 |
| purerpc           | Async gRPC client/server (asyncio, uvloop, trio)     | 225   |
| asyncclick        | Trio-compatible Click (CLI framework)                | 170   |
| async_generator   | Async iterators for Python 3.5+                      | 102   |
| hip               | HTTP client library                                  | 83    |
| pytest-trio       | Pytest plugin for testing Trio code                  | 60    |
| cookiecutter-trio | Project template for Trio applications               | 36    |
| outcome           | Capture function outcomes (result/exception)         | 34    |
| exceptiongroup    | Backport of Python 3.11 ExceptionGroup               | 29    |
| flake8-async      | Linter for Trio/asyncio code                         | 25    |

### Third-Party Integrations

- **httpx**: Async HTTP client with Trio support
- **asks**: Async HTTP requests library inspired by requests
- **trio-websocket**: WebSocket client/server for Trio
- **trio-asyncio**: Interoperability layer with asyncio
- **anyio**: Async library abstraction supporting Trio and asyncio

---

## Relevance to Claude Code Development

### Direct Applications

1. **Async Script Execution**: Trio's structured concurrency could simplify async operations in Claude Code scripts that need parallel I/O (e.g., fetching multiple URLs, concurrent file operations).

2. **Timeout Management**: Cancel scopes provide elegant timeout handling for operations that might hang, useful for tool implementations that call external services.

3. **Multi-Task Orchestration**: Nursery pattern maps well to scenarios where multiple sub-operations must all complete before proceeding.

4. **Error Propagation**: Natural exception propagation through nurseries simplifies error handling in complex async workflows.

### Patterns Worth Adopting

1. **Structured Concurrency**: The nursery pattern ensures no orphan tasks - all spawned work completes within its scope. This principle is valuable for any concurrent operation management.

2. **Explicit Checkpoints**: Static guarantees about where concurrency can interleave makes code review and reasoning about concurrent code tractable.

3. **Unified Cancellation**: Single cancellation mechanism (cancel scopes) vs separate APIs for different timeout scenarios.

4. **Task Completion Guarantees**: Nurseries guarantee all child tasks complete before exiting - prevents resource leaks and orphan operations.

5. **Composable Cancel Scopes**: Nesting timeouts naturally with predictable semantics.

### Integration Opportunities

1. **MCP Server Development**: Trio could serve as the async runtime for Python MCP servers, providing cleaner concurrency than raw asyncio.

2. **Tool Implementation**: Tools that perform parallel operations (batch API calls, concurrent file processing) could use Trio's nurseries.

3. **anyio Compatibility**: Since anyio supports both Trio and asyncio, code can be written once and run on either runtime.

4. **Testing**: pytest-trio provides clean patterns for testing async code that could inform testing strategies for Claude Code extensions.

### Comparison with asyncio

| Aspect                  | Trio                                    | asyncio                               |
| ----------------------- | --------------------------------------- | ------------------------------------- |
| Concurrency model       | Structured (nurseries)                  | Unstructured (create_task anywhere)   |
| Task lifetime           | Guaranteed within scope                 | Can outlive caller                    |
| Cancellation            | Cancel scopes (explicit scope)          | Task.cancel() (per-task)              |
| Checkpoints             | Static guarantees                       | Runtime-dependent                     |
| API style               | Pure async/await                        | Callbacks + async/await mixed         |
| Exception handling      | Natural propagation                     | gather() with return_exceptions       |
| Learning curve          | Lower (fewer concepts)                  | Higher (more historical patterns)     |
| Ecosystem size          | Smaller but growing                     | Larger (stdlib, more libraries)       |
| Production maturity     | Mature, stable API                      | Mature, stdlib since 3.4              |

---

## References

| Source                          | URL                                                                                         | Accessed   |
| ------------------------------- | ------------------------------------------------------------------------------------------- | ---------- |
| GitHub Repository               | <https://github.com/python-trio/trio>                                                       | 2026-02-04 |
| Official Documentation          | <https://trio.readthedocs.io>                                                               | 2026-02-04 |
| PyPI Package                    | <https://pypi.org/project/trio/>                                                            | 2026-02-04 |
| Structured Concurrency Essay    | <https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/>| 2026-02-04 |
| Async API Design Essay          | <https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/>| 2026-02-04 |
| PyCon 2018 Talk                 | <https://www.youtube.com/watch?v=oLkfnc_UMcE>                                               | 2026-02-04 |
| Changelog                       | <https://trio.readthedocs.io/en/latest/history.html>                                        | 2026-02-04 |
| Gitter Chat                     | <https://gitter.im/python-trio/general>                                                     | 2026-02-04 |
| Discourse Forum                 | <https://trio.discourse.group>                                                              | 2026-02-04 |
| PyPI Stats                      | <https://pypistats.org/packages/trio>                                                       | 2026-02-04 |

**Research Method**: Information gathered from GitHub API (repository metadata, releases, contributors), PyPI API (package info, download statistics), official documentation at trio.readthedocs.io, and README.rst from the repository.
