---
title: Typing Strategy Reference
description: Guide for choosing Protocol, TypeVar, ParamSpec, or concrete types in stdlib-only scripts
version: 1.0.0
last_updated: '2026-02-15'
document_type: reference
python_compatibility: 3.11+
---

# Typing Strategy Reference

Comprehensive guide for type hint patterns in stdlib-only Python scripts.

## Choose Protocol, TypeVar, ParamSpec, or Concrete Types

### 1. Prefer Protocol When Contract is Behavioral

Use when you only need operations, not identity.

**Examples:** file-like, writer/reader, closable, path-provider

```python
from typing import Protocol

class Reader(Protocol):
    def read(self, n: int = -1) -> bytes: ...

class Writer(Protocol):
    def write(self, data: bytes) -> int: ...

def copy(src: Reader, dst: Writer) -> int:
    buf = src.read()
    return dst.write(buf)
```

### 2. Prefer TypeVar When Output Type Relates to Input Type

Use for containers and transformers that preserve or map element types.

```python
from typing import TypeVar, Iterable, Callable

T = TypeVar("T")
U = TypeVar("U")

def transform(xs: Iterable[T], f: Callable[[T], U]) -> list[U]:
    return [f(x) for x in xs]
```

### 3. Prefer ParamSpec for Higher-Order Callables

Forward parameter lists through decorators and wrappers.

```python
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def traced(fn: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
    return wrapper
```

### 4. Prefer Abstract Collections for API Flexibility

- `Iterable[T]` for simple iteration
- `Sequence[T]` for ordered, indexable, sized inputs
- `Mapping[K, V]` for read-only dict-like
- Use concrete `list[T]` or `dict[K, V]` only when you require that implementation

```python
from collections.abc import Sequence, Mapping

def first(xs: Sequence[str]) -> str | None:
    return xs[0] if xs else None

def keys(m: Mapping[str, int]) -> list[str]:
    return list(m.keys())
```

### 5. Prefer `object` Over `Any` When Type Unknown

`object` forces explicit narrowing at use sites.

`Any` is allowed at dynamic boundaries, but keep its scope tight and eliminate it quickly.

## Guidance on Any

- Accept `Any` only at boundaries (JSON, YAML, untyped plugins)
- Narrow immediately using runtime checks, TypedDict, dataclasses, or validators
- Do not expose `Any` in public APIs
- Prefer aliases that communicate shape (e.g., `Json`)

**Recommended alias for clarity:**

```python
from typing import Any, TypeAlias

Json: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
```

**Narrowing pattern:**

```python
import json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> Json:
    return json.loads(path.read_text())

def load_object(path: Path) -> dict[str, Any]:
    data: Any = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Expected top-level JSON object")
    return data
```

## Overloads vs Unions vs Protocols

- **Overloads:** Return type depends on distinct input shapes and you want precise call-site inference
- **Unions:** Multiple shapes accepted and treated uniformly
- **Protocols:** Behavior drives compatibility more than shape

## Type Aliases: Path-Like and Command Vectors

Use concise aliases to make signatures readable and correct across platforms.

```python
import os
from typing import TypeAlias
from collections.abc import Sequence

StrPath: TypeAlias = str | os.PathLike[str]
BytesPath: TypeAlias = bytes | os.PathLike[bytes]
Pathish: TypeAlias = StrPath | BytesPath
Cmd: TypeAlias = Sequence[Pathish]
```

**Rules:**

- Prefer `Sequence` over `list` in APIs that only read arguments
- Use `StrPath` in most file APIs; only use `BytesPath` when you truly handle bytes paths
- Convert to `str` at execution boundaries: `str(p)` for logging and subprocess

## Protocols for File-Like and Path-Providing Objects

**File-like inputs:**

```python
from typing import Protocol

class Readable(Protocol):
    def read(self, n: int = -1) -> bytes: ...

def digest(stream: Readable) -> bytes:
    data = stream.read()
    # compute hash...
    return data
```

**Path-providing inputs:**

```python
from typing import Protocol
import os

class HasPath(Protocol):
    def __fspath__(self) -> str | bytes: ...

def open_text(x: HasPath) -> str:
    with open(os.fspath(x), "rt", encoding="utf-8") as fh:
        return fh.read()
```

**Why Protocol:**

- You want behavior (read, `__fspath__`) without binding to concrete classes
- Extensible: works with pathlib objects, custom wrappers, or in-memory fakes

## Choosing Between Sequence vs List and Mapping vs Dict

- Accept `Sequence[T]` when you only iterate or index and do not mutate
- Accept `Mapping[K, V]` when you only read by key
- Return concrete `list[T]`/`dict[K, V]` if you construct new containers and callers can rely on mutability

```python
from collections.abc import Sequence, Mapping

def first(xs: Sequence[str]) -> str | None:
    return xs[0] if xs else None

def keys(m: Mapping[str, int]) -> list[str]:
    return list(m.keys())
```

## Overloads for Precise APIs

Use overloads when output type depends on input flags. Keep implementation single and type-safe.

```python
from typing import overload

@overload
def parse_int(s: str, *, strict: bool) -> int: ...
@overload
def parse_int(s: str, *, strict: bool = ...) -> int | None: ...

def parse_int(s: str, *, strict: bool = False) -> int | None:
    try:
        return int(s)
    except ValueError:
        if strict:
            raise
        return None
```

## JSON Boundary Standard

- Alias `Json` for clarity
- Parse, then narrow quickly to precise models using TypedDict or dataclasses

```python
from typing import Any, TypedDict, TypeAlias

Json: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None

class AppConfig(TypedDict):
    host: str
    port: int

def to_app_config(j: Json) -> AppConfig:
    if not isinstance(j, dict):
        raise ValueError("expected object")
    host = j.get("host")
    port = j.get("port")
    if not isinstance(host, str) or not isinstance(port, int):
        raise ValueError("invalid schema")
    return {"host": host, "port": port}
```

## Validation Hooks for Typing Policy

Fail the build if legacy typing forms are found:

```bash
grep -E "from typing import .*(Dict|List|Set|Tuple|Optional|Union)\b" <file>
```

**Allow:** Protocol, TypeVar, ParamSpec, TypedDict, Any (boundary only), TypeAlias

**Report count of `Any` uses and require inline comments at use sites:**

```python
raw: Any  # boundary: json.loads
```
