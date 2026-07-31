---
title: 'uvloop: Ultra-Fast AsyncIO Event Loop'
library_name: uvloop
pypi_package: uvloop
category: async-io
python_compatibility: 3.8+
last_updated: '2025-11-02'
official_docs: https://uvloop.readthedocs.io
official_repository: https://github.com/MagicStack/uvloop
maintenance_status: active
---

# uvloop: Ultra-Fast AsyncIO Event Loop

## Overview

uvloop is a drop-in replacement for Python's built-in asyncio event loop that delivers 2-4x performance improvements for network-intensive applications. Built on top of libuv (the same C library that powers Node.js) and implemented in Cython, uvloop enables Python asyncio code to approach the performance characteristics of compiled languages like Go.

## The Problem It Solves

### Without uvloop (Reinventing the Wheel)

Python's standard asyncio event loop, while functional, has performance limitations that become apparent in high-throughput scenarios:

1. **Pure Python implementation** with overhead from interpreter execution
2. **Slower I/O operations** compared to C-based event loops
3. **Limited networking throughput** for concurrent connections
4. **Higher CPU utilization** for equivalent workloads

Writing a custom event loop or using lower-level libraries like epoll directly adds complexity and defeats the purpose of asyncio's high-level abstractions.

### With uvloop (Best Practice)

uvloop provides a zero-code-change performance boost by simply replacing the event loop implementation:

- **2-4x faster** than standard asyncio @ [magic.io/blog/uvloop](https://magic.io/blog/uvloop-blazing-fast-python-networking/)
- **Drop-in replacement** requiring minimal code changes
- **Production-proven** in high-performance applications like Sanic, uvicorn, and vLLM
- **libuv foundation** providing battle-tested async I/O primitives

## Core Use Cases

### 1. High-Performance Web Servers

uvloop is the default event loop for production ASGI servers:

```python
# uvicorn with uvloop (automatic with standard install)
# @ https://github.com/encode/uvicorn
import uvloop
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


# Run with uvloop
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, loop="uvloop")
```

### 2. WebSocket Servers

High-throughput WebSocket applications @ [sanic-org/sanic](https://github.com/sanic-org/sanic):

```python
import uvloop
from sanic import Sanic, response

app = Sanic("websocket_app")


@app.websocket("/feed")
async def feed(request, ws):
    while True:
        data = await ws.recv()
        await ws.send(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### 3. Concurrent Network Clients

Web scraping and API clients @ [howie6879/ruia](https://github.com/howie6879/ruia):

```python
import asyncio
import uvloop
import aiohttp


async def fetch_many(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return responses


# Use uvloop for 2-4x faster concurrent requests
uvloop.run(fetch_many(["https://example.com"] * 1000))
```

## Integration Patterns

### Pattern 1: Global Installation (Recommended for Python <3.11)

```python
import asyncio
import uvloop

# Install uvloop as default event loop policy
uvloop.install()


async def main():
    # Your async code here
    await asyncio.sleep(1)


# Now all asyncio.run() calls use uvloop
asyncio.run(main())
```

### Pattern 2: Direct Run (Preferred for Python >=3.11)

```python
import uvloop


async def main():
    # Your async application entry point
    pass


# Simplest usage - replaces asyncio.run()
# @ https://github.com/MagicStack/uvloop/blob/master/README.rst
uvloop.run(main())
```

### Pattern 3: Explicit Event Loop (Advanced)

```python
import asyncio
import sys
import uvloop


async def main():
    # Application logic
    pass


# Python 3.11+ with explicit loop factory
if sys.version_info >= (3, 11):
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
else:
    uvloop.install()
    asyncio.run(main())
```

### Pattern 4: Platform-Specific Installation

```python
import asyncio
import os

# Only use uvloop on POSIX systems (Linux/macOS)
# @ https://github.com/wanZzz6/Modules-Learn
if os.name == "posix":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Windows will use default asyncio (proactor loop)
async def main():
    pass


asyncio.run(main())
```

## Real-World Examples

### FastAPI/Uvicorn Production Setup

```python
# @ https://medium.com/israeli-tech-radar/so-you-think-python-is-slow-asyncio-vs-node-js-fe4c0083aee4
import asyncio
import uvloop
from fastapi import FastAPI
import uvicorn

# Enable uvloop globally
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = FastAPI()


@app.get("/api/data")
async def handle_data():
    # Simulate async database query
    await asyncio.sleep(0.1)
    return {"message": "Hello from Python"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, loop="uvloop")
```

### Discord Bot (hikari-py)

```python
# @ https://github.com/hikari-py/hikari
import asyncio
import os

if os.name != "nt":  # Not Windows
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Discord bot code follows - automatic 2-4x performance boost
```

### Async Web Scraper

```python
# @ https://github.com/elliotgao2/gain
import asyncio
import uvloop
import aiohttp


async def handle_response(session, url):
    async with session.get(url) as response:
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [handle_response(session, f"https://api.example.com/item/{i}") for i in range(1000)]
        results = await asyncio.gather(*tasks)
    return results


# Install and run
uvloop.install()
asyncio.run(main())
```

## Python Version Compatibility

| Python Version | uvloop Support | Notes                                                                                           |
| -------------- | -------------- | ----------------------------------------------------------------------------------------------- |
| 3.8-3.10       | ✅ Full        | Use `uvloop.install()` or `asyncio.set_event_loop_policy()`                                     |
| 3.11-3.13      | ✅ Full        | Can use `uvloop.run()` or `asyncio.Runner(loop_factory=uvloop.new_event_loop)`                  |
| 3.14           | ✅ Full        | Free-threading support added in v0.22.0 @ [#693](https://github.com/MagicStack/uvloop/pull/693) |

### Platform Support

- **Linux**: ✅ Full support (best performance)
- **macOS**: ✅ Full support
- **Windows**: ⚠️ Not supported (use default asyncio proactor loop)
- **BSD**: ✅ Supported (via libuv)

## Performance Benchmarks

### Official Benchmarks

From @ [magic.io/blog/uvloop](https://magic.io/blog/uvloop-blazing-fast-python-networking/):

**Echo Server Performance (1 KiB messages):**

- uvloop: 105,000 req/sec
- Node.js: ~50,000 req/sec
- Standard asyncio: ~30,000 req/sec

**Throughput (100 KiB messages):**

- uvloop: 2.3 GiB/s
- Standard asyncio: 0.8 GiB/s

### Community Benchmarks (2024-2025)

@ [discuss.python.org](https://discuss.python.org/t/is-uvloop-still-faster-than-built-in-asyncio-event-loop/71136):

- **I/O-bound operations**: Python + uvloop is ~22% faster than Node.js
- **Native epoll comparison**: uvloop reaches 88% performance of native C epoll implementation
- **Overall speedup**: 2-4x faster than standard asyncio across workloads

## When NOT to Use uvloop

### 1. Windows-Only Applications

```python
# BAD: uvloop doesn't work on Windows
import uvloop

uvloop.install()  # Will fail on Windows

# GOOD: Platform detection
import os

if os.name == "posix":
    import uvloop

    uvloop.install()
```

### 2. CPU-Bound Tasks

uvloop optimizes I/O operations but won't speed up CPU-intensive work:

```python
# uvloop provides NO benefit here
async def cpu_intensive():
    result = sum(i**2 for i in range(10_000_000))
    return result


# Use multiprocessing instead for CPU-bound work
```

### 3. Debugging AsyncIO Code

The default asyncio loop has better debugging support:

```python
# For debugging, use standard asyncio with debug mode
import asyncio

# Don't install uvloop during development/debugging
asyncio.run(main(), debug=True)  # Better error messages with standard loop
```

### 4. Simple Scripts with Minimal I/O

```python
# Overkill for trivial async work
async def simple_task():
    await asyncio.sleep(1)
    print("Done")


# uvloop adds minimal value here - overhead not justified
```

## Decision Matrix

### Use uvloop when

- ✅ Building production web servers (FastAPI, Sanic, etc.)
- ✅ High-throughput network applications
- ✅ WebSocket servers with many concurrent connections
- ✅ Async web scrapers/crawlers
- ✅ Running on Linux or macOS
- ✅ I/O-bound workloads dominate
- ✅ Zero-code-change performance boost desired

### Use default asyncio when

- ❌ Running on Windows
- ❌ Debugging complex async code
- ❌ CPU-bound workloads
- ❌ Simple scripts with minimal networking
- ❌ Maximum compatibility needed
- ❌ Educational/learning purposes (asyncio is simpler)

## Installation

### Basic Installation

```bash
pip install uvloop
```

### With uvicorn (ASGI server)

```bash
# uvloop automatically included with standard install
pip install 'uvicorn[standard]'
```

### Development/Source Build

```bash
# Requires Cython
pip install Cython
git clone --recursive https://github.com/MagicStack/uvloop.git
cd uvloop
pip install -e .[dev]
make
make test
```

## Integration with Common Frameworks

### FastAPI/Uvicorn

uvloop is automatically used when uvicorn is installed with `[standard]` extras:

```bash
pip install 'uvicorn[standard]'  # Includes uvloop
```

### Sanic

Sanic automatically detects and uses uvloop if available:

```bash
pip install sanic uvloop
```

### aiohttp + gunicorn

```bash
# Use uvloop worker class
gunicorn app:create_app --worker-class aiohttp.worker.GunicornUVLoopWebWorker
```

### Tornado

```python
from tornado.platform.asyncio import AsyncIOMainLoop
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
AsyncIOMainLoop().install()
```

## Common Pitfalls

### Pitfall 1: Installing After Event Loop Created

```python
# BAD: Event loop already created
import asyncio

loop = asyncio.get_event_loop()  # Creates default loop
import uvloop

uvloop.install()  # Too late!

# GOOD: Install before any event loop operations
import uvloop

uvloop.install()
import asyncio

loop = asyncio.get_event_loop()  # Now uses uvloop
```

### Pitfall 2: Windows Compatibility Assumptions

```python
# BAD: Crashes on Windows
import uvloop

uvloop.install()

# GOOD: Platform check
import sys

if sys.platform != "win32":
    import uvloop

    uvloop.install()
```

### Pitfall 3: Expecting CPU Performance Gains

```python
# BAD: uvloop won't help CPU-bound code
async def calculate_primes(n):
    return [i for i in range(2, n) if all(i % j != 0 for j in range(2, i))]


# uvloop provides NO benefit for pure computation
```

## Maintenance and Ecosystem

- **Active Development**: ✅ Maintained by MagicStack (creators of EdgeDB)
- **Release Cadence**: Regular updates (v0.22.1 released Oct 2025)
- **Community Size**: 10,000+ stars on GitHub, used in production by major projects
- **Dependency**: libuv (bundled, no external dependency management)
- **Python 3.14 Support**: ✅ Free-threading support added

## Related Libraries

- **httptools**: Fast HTTP parser (also by MagicStack, pairs with uvloop)
- **uvicorn**: ASGI server using uvloop by default
- **aiohttp**: Async HTTP client/server framework
- **websockets**: WebSocket library compatible with uvloop
- **Sanic**: Web framework optimized for uvloop

## References

- Official Repository: @ [MagicStack/uvloop](https://github.com/MagicStack/uvloop)
- Documentation: @ [uvloop.readthedocs.io](https://uvloop.readthedocs.io/)
- Original Blog Post: @ [magic.io/blog/uvloop](https://magic.io/blog/uvloop-blazing-fast-python-networking/)
- PyPI: @ [pypi.org/project/uvloop](https://pypi.org/project/uvloop/)
- Performance Discussion (2024): @ [discuss.python.org](https://discuss.python.org/t/is-uvloop-still-faster-than-built-in-asyncio-event-loop/71136)
- uvicorn Integration: @ [encode/uvicorn](https://github.com/encode/uvicorn)
- Sanic Framework: @ [sanic-org/sanic](https://github.com/sanic-org/sanic)

## Summary

uvloop represents the gold standard for asyncio performance optimization in Python. It requires minimal code changes (often just 2 lines) while delivering 2-4x performance improvements for I/O-bound async applications. Production deployments should default to uvloop on Linux/macOS systems unless specific compatibility or debugging requirements dictate otherwise. The library's maturity, active maintenance, and widespread adoption in high-performance Python web frameworks make it a critical component of the modern Python async ecosystem.
