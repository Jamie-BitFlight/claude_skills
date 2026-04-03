Features added in Python 3.13 (released October 7, 2024). Available when `requires-python >= '3.13'`. For 3.12 additions, see `python312-features.md`.

## Type System

### `TypeIs` — Bidirectional type narrowing (PEP 742)

Narrows BOTH the if-branch and the else-branch. Replaces `TypeGuard` for most use cases — `TypeGuard` only narrows the if-branch.

```python
from typing import TypeIs

def is_str(val: object) -> TypeIs[str]:
    return isinstance(val, str)

def process(val: str | int) -> None:
    if is_str(val):
        print(val.upper())   # narrowed to str
    else:
        print(val * 2)       # narrowed to int (TypeIs narrows both branches)
```

Pre-3.13 equivalent (`TypeGuard` — else-branch NOT narrowed):

```python
from typing import TypeGuard

def is_str(val: object) -> TypeGuard[str]:
    return isinstance(val, str)
```

### `ReadOnly` for TypedDict — Immutable fields (PEP 705)

Type checkers prevent mutation of `ReadOnly` fields.

```python
from typing import ReadOnly, TypedDict

class Config(TypedDict):
    name: str              # mutable
    version: ReadOnly[str] # immutable — assignment is a type error
```

### `@deprecated` decorator — Type-level deprecation warnings (PEP 702)

Type checkers emit warnings at every call site.

```python
from warnings import deprecated

@deprecated("Use new_function() instead")
def old_function() -> None: ...
```

### Type parameter defaults (PEP 696)

Default type when a generic parameter is not specified.

```python
class Queue[T=str]:
    def push(self, item: T) -> None: ...

q = Queue()        # T defaults to str
q.push("hello")    # ok
q.push(42)         # type error
```

## Stdlib Additions

### `copy.replace()` — Generic shallow copy with field replacement

Works with NamedTuples, dataclasses, and objects with `__replace__`.

```python
import copy
from typing import NamedTuple

class Point(NamedTuple):
    x: int
    y: int

p = Point(1, 2)
p2 = copy.replace(p, y=10)  # Point(x=1, y=10)
```

### `glob.translate()` — Convert glob pattern to regex pattern

```python
import glob
pattern = glob.translate("*.py")  # returns regex string
```

### Improved `pathlib.glob()` — Consistent `**` matching

`**` now matches both files and directories. In 3.12 it matched directories only.

### `python -m random` — Random value CLI

```bash
python -m random          # random float
python -m random 6        # random int 1–6
python -m random a b c    # random choice from args
```

### Defined mutation semantics for `locals()` — PEP 667

`locals()` now returns a snapshot in optimized scopes (functions). Mutations to the returned dict no longer affect local variables, and vice versa. This standardizes behavior that was previously implementation-defined — affects debuggers and introspection tools.

### Docstring whitespace stripping

`__doc__` attributes have leading whitespace automatically stripped, reducing memory overhead.

## Removals and Deprecations (PEP 594)

**Dead batteries removed** — the following stdlib modules were deleted in 3.13. Code importing them will raise `ModuleNotFoundError`:

`aifc`, `audioop`, `chunk`, `cgi`, `cgitb`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib`, `lib2to3`

**Impact**: any project upgrading to 3.13 must audit imports for these modules. Common replacements:
- `cgi` → `urllib.parse.parse_qs()` or web framework equivalents
- `telnetlib` → `telnetlib3` (third-party) or raw sockets
- `crypt` → `bcrypt` or `passlib` (third-party)
- `lib2to3` → `ruff` or manual migration

### `dbm.sqlite3` — New default backend

`dbm` now uses SQLite as its default backend when creating new database files, replacing the platform-dependent default (`dbm.gnu`, `dbm.ndbm`, or `dbm.dumb`).

## Runtime / Performance (architectural awareness only)

- **Free-threaded build** (`python3.13t`) — experimental, NOT for production architecture
- **Experimental JIT compiler** — not enabled by default, NOT for production architecture

## `typing_extensions` Backports

All 3.13 type features are available for Python 3.10+ via `typing_extensions`:

| Feature | Import |
|---|---|
| `TypeIs` | `from typing_extensions import TypeIs` |
| `ReadOnly` | `from typing_extensions import ReadOnly` |
| `@deprecated` | `from typing_extensions import deprecated` |
| Type parameter defaults | `from typing_extensions import TypeVar` with `default=` |

When using backports, note in the spec: "Import from `typing_extensions` until `requires-python >= '3.13'`."

## SOURCE

Real Python — Python 3.13: Cool New Features for You to Try (<https://realpython.com/python313-new-features/>, accessed 2026-03-23), Python 3.13 What's New (<https://docs.python.org/3.13/whatsnew/3.13.html>)
