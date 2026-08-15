---
name: AnyIO - Async Concurrency and Networking Library
description: AnyIO is a high-level asynchronous networking and concurrency library that provides a unified API across asyncio and Trio backends. It implements Trio-style structured concurrency on top of asyncio...
license: MIT
metadata:
  topic: anyio
  category: async-libraries
  source_url: https://github.com/anyio
  github: agronholm/anyio
  version: "4.12.1"
  verified: "2026-02-04"
  next_review: "2026-05-04"
---

## Overview

AnyIO is a high-level asynchronous networking and concurrency library that provides a unified API across asyncio and Trio backends. It implements Trio-style structured concurrency on top of asyncio while harmonizing with Trio's native structured concurrency. Applications and libraries written against AnyIO's API run unmodified on either asyncio or Trio, enabling backend-agnostic async code and incremental adoption without full refactoring.

---

## Problem Addressed

| Problem | AnyIO Solution |
|---------|----------------|
| Asyncio edge cancellation causes lost results when tasks resume with values | Level cancellation via cancel scopes - never cancels when scheduled to resume with value |
| Asyncio tasks can silently swallow CancelledError with bare `except` blocks | Stateful cancel scopes re-raise CancelledError on every await until properly handled |
| Asyncio TaskGroup cannot cancel all tasks or list contained tasks | Task groups contain cancel scopes enabling group-wide cancellation |
| Asyncio TaskGroup lacks task readiness signaling (`start()` method) | `TaskGroup.start()` waits until task signals initialization complete |
| Asyncio queues unbounded by default causing memory issues | Memory object streams default to 0 capacity (synchronous handoff) |
| Asyncio queues lack async iteration support | Memory object receive streams support `async for` |
| Asyncio streams require separate write/drain calls and close/wait_closed | Single async context manager with unified send/receive methods |
| Asyncio `get_extra_info()` returns untyped dict | Typed attributes system with type-safe access |
| Asyncio `to_thread()` cannot specify custom executor | `to_thread.run_sync()` accepts capacity limiters for pool control |
| No asyncio facility to call sync functions in event loop from worker thread | `from_thread.run_sync()` blocks until function completes in event loop |
| asyncio.shield orphans tasks if host cancelled; no protection from loop shutdown | Shielded cancel scopes protect code sections without launching separate tasks |
| Asyncio lacks async file I/O and Path support | Built-in async file streams and async Path class |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 2,374 | 2026-02-04 |
| GitHub Forks | 178 | 2026-02-04 |
| Open Issues | 76 | 2026-02-04 |
| PyPI Downloads (last month) | 426,490,365 | 2026-02-04 |
| PyPI Downloads (last week) | 103,187,741 | 2026-02-04 |
| Created | 2018-08-19 | - |
| Latest Release | 4.12.1 (2026-01-06) | 2026-02-04 |

---

## Key Features

### Concurrency Primitives

- **Task Groups**: Trio-style nurseries with structured concurrency guarantees
- **Cancel Scopes**: Level cancellation with deadline and shielding support
- **Task Initialization**: `TaskGroup.start()` for waiting on task readiness
- **ExceptionGroup Handling**: Python 3.11+ `except*` syntax support

### Networking

- **TCP Sockets**: Client and server with Happy Eyeballs algorithm
- **UDP Sockets**: Async/await style (unlike asyncio's Transport/Protocol)
- **UNIX Domain Sockets**: Stream and datagram variants
- **File Descriptor Passing**: Send/receive file descriptors over UNIX sockets
- **TLS Support**: Via `TLSStream` wrapper for any byte stream

### Synchronization

- **Events**: One-shot notification (non-reusable, race-condition safe)
- **Semaphores**: With optional `fast_acquire` for performance
- **Locks**: Ownership-enforced with `fast_acquire` option
- **Conditions**: Lock + event combination for complex signaling
- **Capacity Limiters**: Single-token-per-borrower semaphores for thread pools

### Streams API

- **ByteStream/ObjectStream**: Hierarchical stream abstractions
- **Memory Object Streams**: In-process object passing with clone support
- **Buffered Streams**: Delimiter and exact-length reads
- **Text Streams**: Unicode string conversion
- **File Streams**: Async file read/write
- **Stapled Streams**: Combine separate read/write into full-duplex
- **Typed Attributes**: Type-safe extra info access (replaces `get_extra_info()`)

### Threading

- **Worker Threads**: Via `to_thread.run_sync()` with capacity limiters
- **Event Loop Calls**: `from_thread.run()` and `from_thread.run_sync()`
- **Context Variable Propagation**: Automatic across thread boundaries

### Process Management

- **Subprocesses**: `run_process()` for one-shot, `open_process()` for interactive
- **Worker Processes**: `to_process.run_sync()` for CPU-intensive work
- **Subinterpreters**: Python 3.13+ parallelization without GIL (experimental)

### File I/O

- **Async File Operations**: Read, write, seek without blocking
- **Async Path**: `pathlib.Path` equivalent with async methods
- **Temporary Files**: Async temp file and directory management

### Testing

- **pytest Plugin**: Built-in async test support
- **Hypothesis Integration**: Property-based testing compatibility
- **Async Fixtures**: First-class support

### Python 3.14+ Features

- **Call Graph Introspection**: Task waiter tracking for debugging tools

---

## Technical Architecture

### Backend Abstraction

<eg>
Application Code
       |
       v
   AnyIO API
       |
   +---+---+
   |       |
   v       v
asyncio   Trio
</eg>

### Structured Concurrency Model

```python
async with create_task_group() as tg:
    tg.start_soon(task1)
    tg.start_soon(task2)
    # All tasks guaranteed complete or cancelled on exit
```

### Cancel Scope Nesting

<eg>
CancelScope (outer, timeout=10s)
    |
    +-- CancelScope (inner, shielded=True)
    |       |
    |       +-- await critical_operation()  # Protected from outer timeout
    |
    +-- await normal_operation()  # Subject to 10s timeout
</eg>

### Memory Object Streams

<eg>
create_memory_object_stream(max_buffer_size=0)
         |
    +----+----+
    |         |
    v         v
SendStream  ReceiveStream
    |         |
    +-- clone() for multiple producers/consumers
</eg>

---

## Installation and Usage

### Installation

```bash
pip install anyio

# With Trio backend support
pip install anyio[trio]
```

### Basic Usage

```python
from anyio import run, create_task_group, sleep


async def worker(name: str, delay: float) -> None:
    await sleep(delay)
    print(f"{name} complete")


async def main() -> None:
    async with create_task_group() as tg:
        tg.start_soon(worker, "A", 1.0)
        tg.start_soon(worker, "B", 0.5)
    print("All workers done")


# Run on asyncio (default)
run(main)

# Run on Trio
run(main, backend="trio")

# With backend options
run(main, backend="asyncio", backend_options={"use_uvloop": True})
```

### Task Initialization Pattern

```python
from anyio import create_task_group, create_tcp_listener, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus


async def server(port: int, *, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
    async with await create_tcp_listener(local_port=port) as listener:
        task_status.started()  # Signal ready
        await listener.serve(handler)


async def main():
    async with create_task_group() as tg:
        await tg.start(server, 8080)  # Waits until started() called
        # Server is now listening, safe to connect
```

### Cancel Scope with Timeout

```python
from anyio import move_on_after, sleep


async def with_timeout():
    with move_on_after(5.0) as scope:
        await long_operation()

    if scope.cancelled_caught:
        print("Operation timed out")
```

### Memory Object Streams

```python
from anyio import create_task_group
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


async def producer(send: MemoryObjectSendStream[int]):
    async with send:
        for i in range(10):
            await send.send(i)


async def consumer(receive: MemoryObjectReceiveStream[int]):
    async with receive:
        async for item in receive:
            print(item)


async def main():
    send, receive = create_memory_object_stream[int](max_buffer_size=10)
    async with create_task_group() as tg:
        tg.start_soon(producer, send)
        tg.start_soon(consumer, receive)
```

---

## Relevance to Claude Code Development

### Applications

1. **MCP Server Development**: AnyIO provides the async foundation for building Model Context Protocol servers that need to handle concurrent requests, manage connections, and integrate with various async backends.

2. **Agent Tool Implementations**: Tools that perform network operations, subprocess management, or file I/O benefit from AnyIO's unified API and structured concurrency guarantees.

3. **Testing Infrastructure**: The built-in pytest plugin simplifies async test writing for Claude Code tooling and skills.

4. **Multi-Backend Compatibility**: Libraries built on AnyIO work with both asyncio (default Python) and Trio, increasing deployment flexibility.

### Patterns Worth Adopting

1. **Structured Concurrency**: Task groups ensure no orphaned tasks - critical for resource cleanup in long-running agent processes.

2. **Cancel Scope Shielding**: Protect critical operations (like saving state) from cancellation during shutdown.

3. **Memory Object Streams**: Type-safe async communication between tasks, superior to `asyncio.Queue` for multi-producer scenarios.

4. **Typed Attributes**: Replace untyped `get_extra_info()` dicts with compile-time-checkable attribute access.

5. **Task Initialization**: Use `TaskGroup.start()` pattern when services must be ready before dependent tasks begin.

### Integration Opportunities

1. **FastMCP/MCP Servers**: AnyIO as async runtime for MCP server implementations.

2. **Subprocess Orchestration**: `run_process()` and `open_process()` for tool execution.

3. **Worker Process Pool**: `to_process.run_sync()` for CPU-intensive operations without blocking event loop.

4. **Async File Operations**: Replace blocking file I/O in skill scripts with `anyio.Path` and async file streams.

---

## References

1. **AnyIO Documentation** - <https://anyio.readthedocs.io/en/stable/> (accessed 2026-02-04)
2. **AnyIO GitHub Repository** - <https://github.com/agronholm/anyio> (accessed 2026-02-04)
3. **AnyIO README** - <https://raw.githubusercontent.com/agronholm/anyio/master/README.rst> (accessed 2026-02-04)
4. **PyPI Package Info** - <https://pypi.org/project/anyio/> (accessed 2026-02-04)
5. **Why AnyIO** - <https://anyio.readthedocs.io/en/stable/why.html> (accessed 2026-02-04)
6. **AnyIO Tasks Documentation** - <https://raw.githubusercontent.com/agronholm/anyio/master/docs/tasks.rst> (accessed 2026-02-04)
7. **AnyIO Networking Documentation** - <https://raw.githubusercontent.com/agronholm/anyio/master/docs/networking.rst> (accessed 2026-02-04)
8. **AnyIO Synchronization Documentation** - <https://raw.githubusercontent.com/agronholm/anyio/master/docs/synchronization.rst> (accessed 2026-02-04)
9. **GitHub API** - Repository statistics via api.github.com (accessed 2026-02-04)
10. **PyPI Stats API** - <https://pypistats.org/api/packages/anyio/recent> (accessed 2026-02-04)
