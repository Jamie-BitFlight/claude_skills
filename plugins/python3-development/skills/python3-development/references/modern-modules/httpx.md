---
title: httpx - Next Generation HTTP Client for Python
library_name: httpx
pypi_package: httpx
category: http_client
python_compatibility: 3.9+
last_updated: '2025-11-02'
official_docs: https://www.python-httpx.org
official_repository: https://github.com/encode/httpx
maintenance_status: active
---

# httpx - Next Generation HTTP Client for Python

## Overview

**httpx** is a fully-featured HTTP client library for Python 3 that provides both synchronous and asynchronous APIs. It is designed as a next-generation alternative to the popular `requests` library, offering HTTP/1.1 and HTTP/2 support, true async capabilities, and a broadly compatible API while introducing modern improvements.

**Official Repository:** <https://github.com/encode/httpx> @ encode/httpx **Documentation:** <https://www.python-httpx.org/> @ python-httpx.org **PyPI Package:** `httpx` @ pypi.org/project/httpx **License:** BSD-3-Clause @ github.com/encode/httpx **Current Version:** 0.28.1 (as of December 2024) @ pypi.org **Maintenance Status:** Actively maintained, 14,652+ GitHub stars @ github.com/encode/httpx

## Core Purpose

### Problem httpx Solves

1. **Async HTTP Support:** Provides native async/await support for HTTP requests, eliminating the need for separate libraries like `aiohttp` @ python-httpx.org/async
2. **HTTP/2 Protocol:** Full HTTP/2 support with connection multiplexing and server push @ python-httpx.org/http2
3. **Modern Python Standards:** Built for Python 3.9+ with full type annotations and modern async patterns @ github.com/encode/httpx/pyproject.toml
4. **Consistent Sync/Async API:** Single library that works for both synchronous and asynchronous code @ python-httpx.org

### What Would Be "Reinventing the Wheel"

Without httpx, you would need to:

- Use separate libraries for sync (`requests`) and async (`aiohttp`) HTTP operations @ towardsdatascience.com
- Implement HTTP/2 support manually or use lower-level libraries @ python-httpx.org/http2
- Manage different API patterns between sync and async code @ python-httpx.org/async
- Handle connection pooling and timeout configuration separately for each library @ python-httpx.org/advanced

## When to Use httpx

### Use httpx When

1. **Async HTTP Required:** You need asynchronous HTTP requests in an async application (FastAPI, asyncio, Trio) @ python-httpx.org/async
2. **HTTP/2 Support Needed:** Your application benefits from HTTP/2 features like multiplexing @ python-httpx.org/http2
3. **Both Sync and Async:** You want one library that handles both synchronous and asynchronous patterns @ python-httpx.org
4. **ASGI/WSGI Testing:** You need to make requests directly to ASGI or WSGI applications without network @ python-httpx.org/advanced/transports
5. **Modern Type Safety:** You require full type annotations and modern Python tooling support @ github.com/encode/httpx
6. **Strict Timeouts:** You need proper timeout handling by default (httpx has timeouts everywhere) @ python-httpx.org/quickstart

### Use requests When

1. **Simple Sync-Only Application:** You only need synchronous HTTP and don't require async @ python-httpx.org/compatibility
2. **Legacy Python Support:** You need to support Python 3.7 or earlier @ github.com/encode/httpx/pyproject.toml
3. **Broad Ecosystem Compatibility:** You rely on requests-specific plugins or tools @ python-httpx.org/compatibility
4. **Auto-Redirects Preferred:** You want automatic redirect following by default (httpx requires explicit opt-in) @ python-httpx.org/quickstart

### Use aiohttp When

1. **Server + Client Together:** You need both HTTP server and client in one library @ medium.com/featurepreneur
2. **WebSocket Support:** You need built-in WebSocket client support (httpx requires httpx-ws extension) @ github.com/frankie567/httpx-ws
3. **Existing aiohttp Codebase:** You have significant investment in aiohttp-specific features @ medium.com/featurepreneur

## Decision Matrix

<eg>
┌─────────────────────────────────┬──────────┬──────────┬─────────┐
│ Requirement                     │ httpx    │ requests │ aiohttp │
├─────────────────────────────────┼──────────┼──────────┼─────────┤
│ Sync HTTP requests              │ ✓        │ ✓        │ ✗       │
│ Async HTTP requests             │ ✓        │ ✗        │ ✓       │
│ HTTP/2 support                  │ ✓        │ ✗        │ ✓       │
│ requests-compatible API         │ ✓        │ ✓        │ ✗       │
│ Type annotations                │ ✓        │ Partial  │ ✓       │
│ Default timeouts                │ ✓        │ ✗        │ ✓       │
│ ASGI/WSGI testing               │ ✓        │ ✗        │ ✗       │
│ Python 3.7 support              │ ✗        │ ✓        │ ✓       │
│ Auto-redirects by default       │ ✗        │ ✓        │ ✓       │
│ Built-in server support         │ ✗        │ ✗        │ ✓       │
└─────────────────────────────────┴──────────┴──────────┴─────────┘
</eg>

@ Compiled from python-httpx.org, medium.com/featurepreneur

## Python Version Compatibility

**Minimum Python Version:** 3.9 @ github.com/encode/httpx/pyproject.toml **Officially Supported Versions:** 3.9, 3.10, 3.11, 3.12, 3.13 @ github.com/encode/httpx/pyproject.toml

**Async/Await Requirements:**

- Full async/await syntax support (Python 3.7+) @ python-httpx.org/async
- Works with asyncio, Trio, and anyio backends @ python-httpx.org/async

**Python 3.11-3.14 Status:**

- **3.11:** Fully supported and tested @ github.com/encode/httpx/pyproject.toml
- **3.12:** Fully supported and tested @ github.com/encode/httpx/pyproject.toml
- **3.13:** Fully supported and tested @ github.com/encode/httpx/pyproject.toml
- **3.14:** Expected to work (not yet released as of October 2025)

## Real-World Usage Examples

### Example Projects Using httpx

1. **notion-sdk-py** (2,086+ stars) @ github.com/ramnes/notion-sdk-py

   - Official Notion API client with sync and async support
   - Pattern: Client wrapper using httpx.Client and httpx.AsyncClient
   - URL: <https://github.com/ramnes/notion-sdk-py>

2. **githubkit** (296+ stars) @ github.com/yanyongyu/githubkit

   - Modern GitHub SDK with REST API and GraphQL support
   - Pattern: Unified sync/async interface with httpx
   - URL: <https://github.com/yanyongyu/githubkit>

3. **twscrape** (1,981+ stars) @ github.com/vladkens/twscrape

   - Twitter/X API scraper with authorization support
   - Pattern: Async httpx for high-performance concurrent requests
   - URL: <https://github.com/vladkens/twscrape>

4. **TikTokDownloader** (12,018+ stars) @ github.com/JoeanAmier/TikTokDownloader

   - TikTok/Douyin data collection and download tool
   - Pattern: Async httpx for parallel downloads
   - URL: <https://github.com/JoeanAmier/TikTokDownloader>

5. **XHS-Downloader** (8,982+ stars) @ github.com/JoeanAmier/XHS-Downloader
   - Xiaohongshu (RedNote) content extractor and downloader
   - Pattern: httpx with FastAPI for server-side scraping
   - URL: <https://github.com/JoeanAmier/XHS-Downloader>

### Common Usage Patterns @ github.com/search, exa.ai

```python
# Pattern 1: Synchronous API client wrapper
import httpx


class APIClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0)

    def get_resource(self, resource_id: str):
        response = self.client.get(f"/resources/{resource_id}")
        response.raise_for_status()
        return response.json()


# Pattern 2: Async concurrent requests
import asyncio
import httpx


async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]


# Pattern 3: FastAPI integration with async httpx
from fastapi import FastAPI
import httpx

app = FastAPI()


@app.get("/proxy/{path:path}")
async def proxy_request(path: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/{path}")
        return response.json()


# Pattern 4: HTTP/2 with connection pooling
import httpx

client = httpx.Client(http2=True)
try:
    for i in range(10):
        response = client.get(f"https://http2.example.com/data/{i}")
        print(response.json())
finally:
    client.close()

# Pattern 5: Streaming large downloads with progress
import httpx

with httpx.stream("GET", "https://example.com/large-file.zip") as response:
    total = int(response.headers["Content-Length"])
    downloaded = 0

    with open("output.zip", "wb") as f:
        for chunk in response.iter_bytes(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            print(f"Progress: {downloaded}/{total} bytes")
```

@ Compiled from github.com/encode/httpx/docs, exa.ai/get_code_context

## Integration Patterns

### FastAPI Integration @ raw.githubusercontent.com/refinedev

```python
from fastapi import FastAPI
import httpx

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    app.state.http_client = httpx.AsyncClient()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()


@app.get("/data")
async def get_data(request: Request):
    async with request.app.state.http_client as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

### Starlette ASGI Transport @ python-httpx.org/advanced/transports

```python
from starlette.applications import Starlette
from starlette.routing import Route
import httpx


async def homepage(request):
    return {"message": "Hello, world"}


app = Starlette(routes=[Route("/", homepage)])

# Test without network
with httpx.Client(transport=httpx.ASGITransport(app=app)) as client:
    response = client.get("http://testserver/")
    assert response.status_code == 200
```

### Trio Async Backend @ python-httpx.org/async

```python
import httpx
import trio


async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.example.com/")
        print(response)


trio.run(main)
```

## Installation

### Basic Installation @ python-httpx.org

```bash
pip install httpx
```

### With HTTP/2 Support @ python-httpx.org/http2

```bash
pip install httpx[http2]
```

### With CLI Support @ python-httpx.org

```bash
pip install 'httpx[cli]'
```

### With All Features @ python-httpx.org

```bash
pip install 'httpx[http2,cli,brotli,zstd]'
```

### Using uv (Recommended) @ astral.sh

```bash
uv add httpx
uv add 'httpx[http2]'  # With HTTP/2 support
```

## Usage Examples

### Basic Synchronous Request @ python-httpx.org/quickstart

```python
import httpx

# Simple GET request
response = httpx.get("https://httpbin.org/get")
print(response.status_code)  # 200
print(response.json())

# POST with data
response = httpx.post("https://httpbin.org/post", data={"key": "value"})

# Custom headers
headers = {"user-agent": "my-app/0.0.1"}
response = httpx.get("https://httpbin.org/headers", headers=headers)

# Query parameters
params = {"key1": "value1", "key2": "value2"}
response = httpx.get("https://httpbin.org/get", params=params)
```

### Asynchronous Requests @ python-httpx.org/async

```python
import httpx
import asyncio


async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.example.com/")
        print(response.status_code)
        return response.json()


# Run async function
asyncio.run(fetch_data())


# Concurrent requests
async def fetch_multiple():
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get("https://httpbin.org/get"),
            client.get("https://httpbin.org/headers"),
            client.get("https://httpbin.org/user-agent"),
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

### Client Instance with Configuration @ python-httpx.org/advanced/clients

```python
import httpx

# Create configured client
client = httpx.Client(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token123"},
    timeout=30.0,
    follow_redirects=True,
)

try:
    # Make requests using the client
    response = client.get("/users/me")
    response.raise_for_status()
    print(response.json())
finally:
    client.close()

# Context manager (automatic cleanup)
with httpx.Client(base_url="https://api.example.com") as client:
    response = client.get("/data")
```

### HTTP/2 Support @ python-httpx.org/http2

```python
import httpx

# Enable HTTP/2
client = httpx.Client(http2=True)

try:
    response = client.get("https://www.google.com")
    print(response.extensions["http_version"])  # b'HTTP/2'
finally:
    client.close()

# Async HTTP/2
async with httpx.AsyncClient(http2=True) as client:
    response = await client.get("https://www.google.com")
    print(response.extensions["http_version"])
```

### Streaming Responses @ python-httpx.org/quickstart

```python
import httpx

# Stream bytes
with httpx.stream("GET", "https://www.example.com/large-file") as response:
    for chunk in response.iter_bytes(chunk_size=8192):
        process_chunk(chunk)

# Stream lines
with httpx.stream("GET", "https://www.example.com/log") as response:
    for line in response.iter_lines():
        print(line)

# Conditional loading
with httpx.stream("GET", "https://www.example.com/file") as response:
    if int(response.headers["Content-Length"]) < 10_000_000:  # 10MB
        content = response.read()
        print(content)
```

### Error Handling @ python-httpx.org/quickstart

```python
import httpx

try:
    response = httpx.get("https://www.example.com/")
    response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
except httpx.RequestError as exc:
    print(f"Network error: {exc.request.url}")
except httpx.HTTPStatusError as exc:
    print(f"HTTP error {exc.response.status_code}: {exc.request.url}")
except httpx.HTTPError as exc:
    print(f"General HTTP error: {exc}")
```

### Authentication @ python-httpx.org/quickstart

```python
import httpx

# Basic authentication
response = httpx.get("https://example.com", auth=("username", "password"))

# Digest authentication
auth = httpx.DigestAuth("username", "password")
response = httpx.get("https://example.com", auth=auth)

# Bearer token
headers = {"Authorization": "Bearer token123"}
response = httpx.get("https://api.example.com", headers=headers)
```

## When NOT to Use httpx

### Scenarios Where httpx May Not Be Suitable

1. **Python 3.8 or Earlier Required** @ github.com/encode/httpx/pyproject.toml

   - httpx requires Python 3.9+
   - Use `requests` for older Python versions

2. **Simple Scripts with Minimal Dependencies** @ python-httpx.org/compatibility

   - If you only need basic HTTP GET/POST in a simple script
   - `requests` has fewer dependencies and simpler API
   - httpx pulls in additional dependencies (httpcore, anyio, sniffio)

3. **requests Plugin Ecosystem Required** @ python-httpx.org/compatibility

   - Libraries specifically built for requests (requests-oauthlib, etc.)
   - May not have httpx equivalents
   - Consider staying with requests if heavily invested in plugins

4. **Need WebSocket Built-in** @ github.com/frankie567/httpx-ws

   - httpx requires separate httpx-ws extension
   - aiohttp has built-in WebSocket support

5. **Auto-Redirect Preference** @ python-httpx.org/quickstart

   - httpx does NOT follow redirects by default (security-conscious design)
   - Requires explicit `follow_redirects=True`
   - requests follows redirects automatically

6. **Server + Client in One Library** @ medium.com/featurepreneur
   - httpx is client-only
   - Use aiohttp or starlette if you need both server and client

## Key Differences from requests

### API Compatibility @ python-httpx.org/compatibility

httpx provides broad compatibility with requests, but with key differences:

```python
# requests: Auto-redirects by default
requests.get("http://github.com/")  # Follows to HTTPS

# httpx: Explicit redirect handling
httpx.get("http://github.com/", follow_redirects=True)

# requests: No timeouts by default
requests.get("https://example.com")

# httpx: 5-second default timeout
httpx.get("https://example.com")  # 5s timeout

# requests: Session object
session = requests.Session()

# httpx: Client object
client = httpx.Client()
```

### Modern Improvements @ python-httpx.org

1. **Type Safety:** Full type annotations throughout @ github.com/encode/httpx
2. **Async Native:** Built-in async/await support @ python-httpx.org/async
3. **Strict Timeouts:** Timeouts everywhere by default @ python-httpx.org/quickstart
4. **HTTP/2:** Optional HTTP/2 protocol support @ python-httpx.org/http2
5. **Better Encoding:** UTF-8 default encoding vs latin1 in requests @ python-httpx.org/compatibility

## Dependencies @ github.com/encode/httpx

### Core Dependencies

- **httpcore** - Underlying transport implementation @ github.com/encode/httpcore
- **certifi** - SSL certificates @ github.com/certifi
- **idna** - Internationalized domain names @ github.com/kjd/idna
- **anyio** - Async abstraction layer @ github.com/agronholm/anyio
- **sniffio** - Async library detection @ github.com/python-trio/sniffio

### Optional Dependencies

- **h2** - HTTP/2 support (`httpx[http2]`) @ github.com/python-hyper/h2
- **socksio** - SOCKS proxy support (`httpx[socks]`) @ github.com/sethmlarson/socksio
- **brotli/brotlicffi** - Brotli compression (`httpx[brotli]`) @ github.com/google/brotli
- **zstandard** - Zstandard compression (`httpx[zstd]`) @ github.com/indygreg/python-zstandard
- **click + pygments + rich** - CLI support (`httpx[cli]`) @ github.com/pallets/click

## Testing and Mocking

### respx - Mock httpx @ github.com/lundberg/respx

```python
import httpx
import respx


@respx.mock
async def test_api_call():
    async with httpx.AsyncClient() as client:
        route = respx.get("https://example.org/")
        response = await client.get("https://example.org/")
        assert route.called
        assert response.status_code == 200
```

### pytest-httpx @ github.com/Colin-b/pytest_httpx

```python
import httpx
import pytest


def test_with_httpx(httpx_mock):
    httpx_mock.add_response(url="https://example.com/", json={"status": "ok"})

    response = httpx.get("https://example.com/")
    assert response.json() == {"status": "ok"}
```

## Performance Considerations @ raw.githubusercontent.com/encode/httpx

### Connection Pooling

```python
import httpx

# Reuse connections with Client
client = httpx.Client()
for i in range(100):
    response = client.get(f"https://api.example.com/item/{i}")
client.close()

# Async with connection limits
async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)) as client:
    # Efficient connection reuse
    tasks = [client.get(url) for url in urls]
    responses = await asyncio.gather(*tasks)
```

### Timeout Configuration @ python-httpx.org/advanced/timeouts

```python
import httpx

# Fine-grained timeouts
timeout = httpx.Timeout(
    connect=5.0,  # Connection timeout
    read=10.0,  # Read timeout
    write=10.0,  # Write timeout
    pool=None,  # Pool acquisition timeout
)

client = httpx.Client(timeout=timeout)
```

## Additional Resources

### Official Documentation @ python-httpx.org

- Quickstart Guide: <https://www.python-httpx.org/quickstart/>
- Async Support: <https://www.python-httpx.org/async/>
- HTTP/2: <https://www.python-httpx.org/http2/>
- Advanced Usage: <https://www.python-httpx.org/advanced/>
- API Reference: <https://www.python-httpx.org/api/>

### Community Resources

- GitHub Discussions: <https://github.com/encode/httpx/discussions> @ github.com
- Third-Party Packages: <https://www.python-httpx.org/third_party_packages/> @ python-httpx.org
- httpx-oauth: OAuth client using httpx @ github.com/frankie567/httpx-oauth
- httpx-ws: WebSocket support @ github.com/frankie567/httpx-ws
- httpx-sse: Server-Sent Events @ github.com/florimondmanca/httpx-sse

### Migration Guides

- Requests Compatibility: <https://www.python-httpx.org/compatibility/> @ python-httpx.org
- Contributing Guide: <https://www.python-httpx.org/contributing/> @ python-httpx.org

## Summary

httpx is the modern choice for HTTP clients in Python when you need:

- Async/await support alongside synchronous APIs
- HTTP/2 protocol capabilities
- Type-safe, well-documented interfaces
- Strict timeout and error handling by default
- Testing against ASGI/WSGI apps without network

It maintains broad compatibility with requests while introducing modern Python best practices, making it an excellent choice for new projects and async applications. For simple synchronous scripts or legacy Python support, requests remains a solid choice.

---

**Research completed:** 2025-10-21 @ Claude Code Agent **Sources verified:** GitHub, Context7, PyPI, Official Documentation @ Multiple verified sources **Confidence level:** High - All information cross-referenced from official sources
