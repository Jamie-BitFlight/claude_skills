# Python 3.11 Feature Supplement

Per-version feature reference for `requires-python >= "3.11"`. Implementation agents read this to
know which features are safe to use without `typing_extensions` and which require it or a newer
Python floor.

---

## Type System

### `Self` — PEP 673

Return type annotation for methods that return an instance of the enclosing class. Replaces
`TypeVar("T", bound="ClassName")` patterns.

```python
from __future__ import annotations
from typing import Self

class Builder:
    def set_name(self, name: str) -> Self:
        self._name = name
        return self
```

Do NOT use:

```python
# old pattern — verbose and error-prone
from typing import TypeVar
T = TypeVar("T", bound="Builder")
def set_name(self: T, name: str) -> T: ...
```

### `StrEnum` — stdlib `enum`

String enum for finite string value sets. Values compare equal to their string literals.
Use for status codes, rule IDs, categories, and CLI option choices.

```python
from enum import StrEnum

class Status(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"

assert Status.PENDING == "pending"  # True
```

Do NOT use `class Status(str, Enum)` — `StrEnum` is the stdlib replacement since 3.11.

### `ExceptionGroup` and `except*` — PEP 654

Structured concurrent error handling. Use when collecting multiple independent failures (e.g.,
from `asyncio.TaskGroup`).

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fetch("a"))
        tg.create_task(fetch("b"))
except* ValueError as eg:
    for exc in eg.exceptions:
        print(f"ValueError: {exc}")
except* TimeoutError as eg:
    print(f"{len(eg.exceptions)} timeouts")
```

### Exception notes via `e.add_note()` — PEP 678

Enrich re-raised exceptions with context at the point of re-raise.

```python
try:
    load_config(path)
except FileNotFoundError as e:
    e.add_note(f"Config path searched: {path}")
    raise
```

### `TypeVarTuple` — PEP 646

Variadic generics for tuple-like containers. Enables typed heterogeneous sequences.

```python
from typing import TypeVarTuple, Unpack

Ts = TypeVarTuple("Ts")

def first(items: tuple[*Ts]) -> tuple[*Ts]:
    return items
```

### `LiteralString` — PEP 675

Marks a parameter as accepting only string literals (not runtime-constructed strings).
Prevents SQL injection and shell injection at the type level.

```python
from typing import LiteralString

def execute(query: LiteralString) -> None:
    db.run(query)

execute("SELECT * FROM users")        # OK
execute("SELECT * FROM " + table)     # type error
```

### `Never` — PEP 655

Return type for functions that never return normally (always raise or loop forever).

```python
from typing import Never

def abort(msg: str) -> Never:
    raise SystemExit(msg)
```

### `Required` / `NotRequired` for TypedDict — PEP 655

Mark individual fields as required or optional without defining two separate TypedDicts.

```python
from typing import TypedDict, Required, NotRequired

class Config(TypedDict, total=False):
    host: Required[str]
    port: NotRequired[int]
```

### `TypeGuard` — PEP 647 (available since 3.10, standard usage at 3.11)

Runtime type narrowing for type checkers. Use when narrowing cannot be inferred from isinstance.

```python
from typing import TypeGuard

def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)
```

Note: `TypeGuard` narrows in the positive branch only. For bidirectional narrowing, use `TypeIs`
from `typing_extensions` (available at 3.11 via backport; stdlib in 3.13+).

### `dataclass_transform` — PEP 681

Marks a decorator or base class as creating dataclass-like behavior. Enables type checkers to
understand custom ORMs and frameworks that generate `__init__`, `__eq__`, etc.

```python
from typing import dataclass_transform

@dataclass_transform()
def my_model(cls: type) -> type:
    # Framework generates __init__, __eq__, etc.
    return cls

@my_model
class User:
    name: str
    age: int

User(name="Alice", age=30)  # type checker understands this
```

---

## Stdlib Additions

### `tomllib` — PEP 680

TOML reading (stdlib, read-only). Use when a stdlib-only constraint exists.

```python
import tomllib

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
```

Note: `tomllib` is read-only. Use `tomlkit` when writing or modifying TOML files — it preserves
comments and formatting. Only use `tomllib` under a confirmed stdlib-only requirement.

### `asyncio.TaskGroup` — PEP 654

Structured concurrency. Replaces manual `asyncio.gather()` with explicit error grouping.

```python
import asyncio

async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(work_a())
        tg.create_task(work_b())
    # both tasks completed or both cancelled on first error
```

Do NOT use:

```python
# old pattern — swallows partial failures
results = await asyncio.gather(work_a(), work_b(), return_exceptions=True)
```

### `datetime.UTC` — PEP 680

Timezone-aware UTC constant. Replaces `timezone.utc`.

```python
from datetime import datetime, UTC

now = datetime.now(UTC)
```

Do NOT use:

```python
from datetime import timezone
datetime.now(timezone.utc)  # still valid but verbose
```

---

## Pattern Availability at 3.11

### `match-case` — PEP 634 (since 3.10, fully mature at 3.11)

Use for all `elif` chains on discrete values, enum dispatch, and structural pattern matching.

```python
match command:
    case "quit":
        raise SystemExit(0)
    case "help":
        show_help()
    case str(unknown):
        raise ValueError(f"Unknown command: {unknown}")
```

### Builtin generics — PEP 585 (since 3.9)

Use `list[str]`, `dict[str, int]`, `tuple[int, ...]` directly. Do NOT import `List`, `Dict`,
`Tuple` from `typing`.

```python
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}
```

### Pipe union `X | None` — PEP 604 (since 3.10)

Use `str | None` instead of `Optional[str]`. Use `int | str` instead of `Union[int, str]`.

```python
def find(name: str) -> str | None:
    return registry.get(name)
```

### `from __future__ import annotations`

Required at the top of every file. Enables deferred evaluation of annotations (PEP 563),
allowing forward references and reducing runtime annotation overhead.

```python
from __future__ import annotations
```

---

## What Is NOT Available at 3.11

These features require 3.12+ or `typing_extensions`:

| Feature | Minimum version | Backport |
|---|---|---|
| Native generic syntax `class Foo[T]:` | 3.12+ | No |
| `type` alias statement | 3.12+ | No |
| `@override` decorator | 3.12+ | `typing_extensions` |
| `TypeIs` (bidirectional narrowing) | 3.13+ | `typing_extensions` |
| `ReadOnly` TypedDict fields | 3.13+ | `typing_extensions` |
| `@deprecated` decorator | 3.13+ | `typing_extensions` |

---

## `typing_extensions` Backports Available at 3.11

Import from `typing_extensions` to use these at a 3.11 floor:

```python
from typing_extensions import TypeIs, ReadOnly, deprecated, override
```

Available backports: `TypeIs`, `ReadOnly`, `@deprecated`, `@override`, `Self` (also stdlib),
`Never` (also stdlib), `Unpack`.

When using any of these, add `typing_extensions` to project dependencies:

```toml
[project]
dependencies = ["typing_extensions>=4.12"]
```

---

SOURCE: Python 3.11 What's New (<https://docs.python.org/3.11/whatsnew/3.11.html>, accessed 2026-03-23)
