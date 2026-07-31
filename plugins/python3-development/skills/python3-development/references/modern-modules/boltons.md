---
title: 'Boltons: Pure-Python Standard Library Extensions'
library_name: boltons
pypi_package: boltons
category: utilities
python_compatibility: 3.7+
last_updated: '2025-11-02'
official_docs: https://boltons.readthedocs.io
official_repository: https://github.com/mahmoud/boltons
maintenance_status: active
---

# Boltons: Pure-Python Standard Library Extensions

## Overview

**boltons should be builtins.**

Boltons is a collection of over 230 BSD-licensed, pure-Python utilities designed to extend Python's standard library with functionality that is conspicuously missing. Created and maintained by @mahmoud (Mahmoud Hashemi), it provides battle-tested implementations of commonly needed utilities without any external dependencies.

### Core Value Proposition

- **Zero Dependencies**: Pure-Python with no external requirements
- **Module Independence**: Each module can be vendored individually
- **Battle-Tested**: 6,765+ stars, tested against Python 3.7-3.13 and PyPy3
- **Standard Library Philosophy**: Follows stdlib design principles
- **Production Ready**: Used in production by numerous projects

## Problem Space

Boltons solves the "reinventing the wheel" problem for common utilities that should be in the standard library but aren't. Without boltons, developers repeatedly write custom implementations for:

- LRU caches with better APIs than `functools.lru_cache`
- Chunked and windowed iteration patterns
- Atomic file operations
- Advanced dictionary types (OrderedMultiDict)
- Enhanced traceback formatting and debugging
- Recursive data structure traversal
- File system utilities beyond `shutil`

### What Would Be Reinventing the Wheel

Using boltons prevents rewriting:

- Custom LRU cache implementations with size limits and TTL
- Iteration utilities like `chunked()`, `windowed()`, `unique()`
- Atomic file write operations (write-to-temp, rename)
- Enhanced `namedtuple` with defaults and mutation
- Traceback extraction and formatting utilities
- URL parsing and manipulation beyond `urllib.parse`
- Table formatting for 2D data

## Design Principles

Per @boltons/docs/architecture.rst, each "bolton" must:

1. **Be pure-Python and self-contained**: No C extensions, minimal dependencies
2. **Perform a common task**: Address frequently needed functionality
3. **Mitigate stdlib insufficiency**: Fill gaps in the standard library
4. **Follow stdlib practices**: Balance best practice with pragmatism
5. **Include documentation**: At least one doctest, links to related tools

## Key Modules

### 1. **cacheutils** - Advanced Caching [@context7]

Better caching than `functools.lru_cache`:

```python
from boltons.cacheutils import LRU, cached, cachedmethod

# LRU cache with size limit
cache = LRU(max_size=256)
cache["user:123"] = user_data


# Decorator with custom cache backend
@cached(cache={})
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# Threshold counter - only track frequently occurring items
from boltons.cacheutils import ThresholdCounter

tc = ThresholdCounter(threshold=0.1)
tc.update([2] * 10)  # Only remembers items > 10% frequency
```

**When to use**: Need size-limited caches, TTL expiration, or custom eviction policies.

### 2. **iterutils** - Enhanced Iteration [@context7]

Powerful iteration utilities beyond `itertools`:

```python
from boltons.iterutils import (
    chunked,
    chunked_iter,  # Split into chunks
    windowed,
    windowed_iter,  # Sliding windows
    unique,
    unique_iter,  # Deduplicate preserving order
    one,
    first,
    same,  # Reduction utilities
    remap,
    get_path,  # Recursive data structure traversal
    backoff,  # Exponential backoff with jitter
    pairwise,  # Overlapping pairs
)

# Chunking for batch processing
for batch in chunked(user_ids, 100):
    process_batch(batch)
# [1,2,3,4,5] with size=2 → [1,2], [3,4], [5]

# Sliding window for moving averages
for window in windowed(prices, 7):
    avg = sum(window) / len(window)
# [1,2,3,4,5] with size=3 → [1,2,3], [2,3,4], [3,4,5]

# Safe reduction
user = one(users)  # Raises if != 1 item
first_or_none = first(results, default=None)


# Recursive data structure traversal
def visit(path, key, value):
    if isinstance(value, str) and "secret" in key.lower():
        return "***REDACTED***"
    return value


clean_data = remap(user_data, visit=visit)

# Exponential backoff with jitter
for wait_time in backoff(start=0.1, stop=60, count=5, jitter=True):
    if try_operation():
        break
    time.sleep(wait_time)
```

**When to use**: Batch processing, sliding windows, recursive data transformation, retry logic.

### 3. **tbutils** - Enhanced Tracebacks [@context7]

Better exception handling and debugging:

```python
from boltons.tbutils import TracebackInfo, ExceptionInfo, ParsedException

try:
    risky_operation()
except Exception as e:
    # Capture full traceback info
    exc_info = ExceptionInfo.from_current()

    # Access structured traceback data
    tb_info = TracebackInfo.from_current()
    for frame in tb_info.frames:
        print(f"{frame.filename}:{frame.lineno} in {frame.func_name}")

    # Format for logging
    formatted = exc_info.get_formatted()
    logger.error(formatted)
```

**When to use**: Enhanced error logging, debugging tools, error analysis.

### 4. **fileutils** - Safe File Operations [@context7]

Atomic writes and safe file handling:

```python
from boltons.fileutils import atomic_save, mkdir_p, FilePerms

# Atomic file write (write-to-temp, rename)
with atomic_save("config.json") as f:
    json.dump(config, f)
# File only replaced if write succeeds

# Create directory path (like mkdir -p)
mkdir_p("/path/to/nested/directory")

# Readable permission management
perms = FilePerms(0o755)
perms.apply("/path/to/script.sh")
```

**When to use**: Configuration files, data persistence, safe concurrent writes.

### 5. **dictutils** - Advanced Dictionaries [@context7]

Enhanced dictionary types:

```python
from boltons.dictutils import OrderedMultiDict, OMD

# Preserve order + allow duplicate keys (like HTTP headers)
headers = OMD([
    ("Accept", "application/json"),
    ("Accept", "text/html"),  # Multiple values for same key
    ("User-Agent", "MyBot/1.0"),
])

for accept in headers.getlist("Accept"):
    print(accept)  # application/json, text/html
```

**When to use**: HTTP headers, query parameters, configuration with duplicate keys.

### 6. **strutils** - String Utilities [@github/README.md]

Common string operations:

```python
from boltons.strutils import (
    slugify,  # URL-safe slugs
    bytes2human,  # Human-readable byte sizes
    find_hashtags,  # Extract #hashtags
    pluralize,  # Smart pluralization
    strip_ansi,  # Remove ANSI codes
)

slugify("Hello, World!")  # "hello-world"
bytes2human(1234567)  # "1.18 MB"
```

### 7. **queueutils** - Priority Queues [@context7]

Enhanced queue types:

```python
from boltons.queueutils import HeapPriorityQueue, PriorityQueue

pq = HeapPriorityQueue()
pq.add("low priority", priority=3)
pq.add("high priority", priority=1)
item = pq.pop()  # Returns "high priority"
```

## Integration Patterns

### Full Install

```bash
pip install boltons
```

### Import Individual Modules

```python
# Import only what you need
from boltons.cacheutils import LRU
from boltons.iterutils import chunked
from boltons.fileutils import atomic_save
```

### Vendoring (Copy Into Project)

Since boltons has **zero dependencies** and each module is **independent**:

```bash
# Copy specific module
cp /path/to/site-packages/boltons/iterutils.py myproject/utils/

# Copy entire package
cp -r /path/to/site-packages/boltons myproject/vendor/
```

This is explicitly supported by the project design [@context7/architecture.rst].

## Real-World Usage Examples [@github/search]

### Example 1: Clastic Web Framework [@mahmoud/clastic]

```python
# Enhanced traceback handling
from boltons.tbutils import ExceptionInfo, TracebackInfo


class ErrorMiddleware:
    def handle_error(self, exc):
        exc_info = ExceptionInfo.from_current()
        return self.render_error_page(exc_info.get_formatted())
```

### Example 2: Click-Extra CLI Framework [@kdeldycke/click-extra]

```python
# Enhanced traceback formatting for CLI error messages
from boltons.tbutils import print_exception

try:
    run_command()
except Exception:
    print_exception()  # Beautiful formatted traceback
```

### Example 3: Reader Feed Library [@lemon24/reader]

```python
# Type checking utilities
from boltons.typeutils import make_sentinel

NOT_SET = make_sentinel("NOT_SET")  # Better than None for defaults
```

### Example 4: Batch Processing Pattern

```python
from boltons.iterutils import chunked

# Process database records in batches
for batch in chunked(fetch_all_records(), 1000):
    bulk_insert(batch)
    db.commit()
```

### Example 5: API Rate Limiting

```python
from boltons.iterutils import backoff
from boltons.cacheutils import LRU

# Exponential backoff for API retries
cache = LRU(max_size=1000)


def call_api_with_retry(endpoint):
    for wait in backoff(start=0.1, stop=60, count=5):
        try:
            return requests.get(endpoint)
        except requests.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                time.sleep(wait)
            else:
                raise
```

## Python Version Compatibility

- **Minimum**: Python 3.7
- **Maximum Tested**: Python 3.13
- **Also Tested**: PyPy3
- **3.11-3.14 Status**: Fully compatible (tested 3.11, 3.12, 3.13)

Per @github/README.md:

> Boltons is tested against Python 3.7-3.13, as well as PyPy3.

## When to Use Boltons

### Use Boltons When

1. **Need stdlib-style utilities with no dependencies**

   - Building libraries that avoid dependencies
   - Corporate environments with strict dependency policies
   - Want vendorable, copy-pasteable code

2. **Iteration patterns beyond itertools**

   - Chunking/batching data
   - Sliding windows
   - Recursive data structure traversal
   - Exponential backoff

3. **Enhanced caching needs**

   - Size-limited LRU caches
   - TTL expiration
   - Custom eviction policies
   - Better API than `functools.lru_cache`

4. **Atomic file operations**

   - Safe configuration file updates
   - Preventing corrupted writes
   - Concurrent file access

5. **Advanced debugging**

   - Structured traceback information
   - Custom error formatting
   - Error analysis tools

6. **OrderedMultiDict needs**
   - HTTP headers/query parameters
   - Configuration with duplicate keys
   - Preserving insertion order + duplicates

### Use Standard Library When

1. **Basic iteration**: `itertools` suffices
2. **Simple caching**: `functools.lru_cache` is enough
3. **Basic file ops**: `pathlib` and `shutil` work fine
4. **Standard dicts**: `dict` or `collections.OrderedDict` meets needs

### Use more-itertools When

- Need even more specialized iteration utilities
- Already using `more-itertools` in project
- Want community recipes from itertools docs

**Key Difference**: Boltons is broader (files, caching, debugging) while `more-itertools` focuses purely on iteration.

## Decision Matrix

| Scenario                   | Use Boltons                | Use Stdlib                       | Use Alternative              |
| -------------------------- | -------------------------- | -------------------------------- | ---------------------------- |
| LRU cache with size limits | ✅ `cacheutils.LRU`        | ⚠️ `lru_cache` (no size control) | `cachetools` (more features) |
| Chunked iteration          | ✅ `iterutils.chunked`     | ❌ Manual slicing                | `more-itertools.chunked`     |
| Atomic file writes         | ✅ `fileutils.atomic_save` | ❌ Manual temp+rename            | `atomicwrites` (archived)    |
| Enhanced tracebacks        | ✅ `tbutils.TracebackInfo` | ❌ `traceback` (basic)           | `rich.traceback` (prettier)  |
| OrderedMultiDict           | ✅ `dictutils.OMD`         | ❌ Custom solution               | `werkzeug.datastructures`    |
| Exponential backoff        | ✅ `iterutils.backoff`     | ❌ Manual implementation         | `tenacity`, `backoff`        |
| URL parsing                | ✅ `urlutils.URL`          | ⚠️ `urllib.parse` (basic)        | `yarl`, `furl`               |
| Zero dependencies          | ✅ Pure Python             | ✅ Built-in                      | ❌ Most alternatives         |

## When NOT to Use Boltons

1. **Already using specialized libraries**

   - Have `cachetools` for advanced caching
   - Have `tenacity` for retry logic
   - Have `rich` for pretty output

2. **Need high-performance implementations**

   - Boltons prioritizes correctness over speed
   - C-extension alternatives may be faster

3. **Want cutting-edge features**

   - Boltons is conservative, stdlib-like
   - Specialized libraries may innovate faster

4. **Framework-specific needs**
   - Django/Flask have their own utils
   - Web frameworks provide similar functionality

## Maintenance and Stability

- **Versioning**: CalVer (YY.MINOR.MICRO) [@github/README.md]
- **Latest**: 25.0.0 (February 2025)
- **Maintenance**: Active, 71 open issues, 373 forks
- **Author**: Mahmoud Hashemi (@mahmoud)
- **License**: BSD (permissive)

## Related Libraries

### Complementary

- **more-itertools**: Extended iteration recipes
- **toolz/cytoolz**: Functional programming utilities
- **attrs/dataclasses**: Enhanced class definitions

### Overlapping

- **cachetools**: More advanced caching (but has dependencies)
- **atomicwrites**: Atomic file writes (now archived)
- **werkzeug**: Web utilities including MultiDict

### When to Combine

```python
# Use both boltons and more-itertools
from boltons.iterutils import chunked  # For chunking
from more_itertools import flatten  # For flattening
from boltons.cacheutils import LRU  # For caching

cache = LRU(max_size=1000)


@cached(cache=cache)
def process_data(records):
    for batch in chunked(records, 100):
        yield process_batch(batch)
```

## Key Takeaways

1. **Zero Dependencies**: Pure-Python, no external requirements
2. **Vendorable**: Copy individual modules into your project
3. **Battle-Tested**: 6,765+ stars, production-proven
4. **Stdlib Philosophy**: Familiar API, conservative design
5. **Broad Coverage**: Caching, iteration, files, debugging, data structures
6. **Production Ready**: Python 3.7-3.13, PyPy3 support

## Quick Start

```python
# Install
pip install boltons

# Common patterns
from boltons.cacheutils import LRU
from boltons.iterutils import chunked, windowed, backoff
from boltons.fileutils import atomic_save
from boltons.tbutils import ExceptionInfo

# LRU cache
cache = LRU(max_size=256)

# Batch processing
for batch in chunked(items, 100):
    process(batch)

# Atomic writes
with atomic_save('data.json') as f:
    json.dump(data, f)

# Enhanced error handling
try:
    risky()
except Exception:
    exc_info = ExceptionInfo.from_current()
    logger.error(exc_info.get_formatted())
```

## References

- **Repository**: [@github/mahmoud/boltons](https://github.com/mahmoud/boltons)
- **Documentation**: [@readthedocs](https://boltons.readthedocs.io/)
- **PyPI**: [@pypi/boltons](https://pypi.org/project/boltons/)
- **Context7**: [@context7/mahmoud/boltons](/mahmoud/boltons)
- **Architecture**: [@readthedocs/architecture](https://boltons.readthedocs.io/en/latest/architecture.html)

---

_Research completed: 2025-10-21_ _Sources: Context7, GitHub, PyPI, ReadTheDocs, Exa code search_ _Trust Score: 9.8/10 (Context7)_
