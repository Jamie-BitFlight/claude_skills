Features added in Python 3.12. Available when `requires-python >= '3.12'`. For baseline 3.11
features, see `python311-features.md`.

SOURCE: Python 3.12 What's New (<https://docs.python.org/3.12/whatsnew/3.12.html>)

---

## Type System

### Native generic syntax — PEP 695

Type parameters declared inline on class and function definitions. Replaces `TypeVar` +
`Generic` boilerplate.

```python
# 3.11
from typing import TypeVar, Generic
T = TypeVar("T")
class Stack(Generic[T]):
    def push(self, item: T) -> None: ...

# 3.12
class Stack[T]:
    def push(self, item: T) -> None: ...

def first[T](items: list[T]) -> T: return items[0]          # generic function
class NumberStack[T: (int, float)]: ...                      # constrained
class Sortable[T: Comparable]: ...                           # bounded
```

### `type` statement — PEP 695

Explicit type alias declaration. Replaces `TypeAlias` annotation.

```python
# 3.11
from typing import TypeAlias
Vector: TypeAlias = list[float]
Matrix: TypeAlias = list[list[float]]

# 3.12
type Vector = list[float]
type Matrix = list[list[float]]
```

Generic type aliases: `type Lookup[K, V] = dict[K, list[V]]`

### `@override` decorator — PEP 698

Marks a method as intentionally overriding a parent class method. Type checkers error when
no matching parent method is found, catching rename-without-update bugs.

```python
from typing import override

class Child(Base):
    @override
    def process(self) -> None: ...   # type checker verifies Base.process exists
    @override
    def missing(self) -> None: ...   # ERROR: no parent method named 'missing'
```

### Typed `**kwargs` via `Unpack[TypedDict]` — PEP 692

Precise typing for keyword-only argument forwarding.

```python
from typing import Unpack, TypedDict

class Options(TypedDict, total=False):
    timeout: int
    retries: int

def fetch(url: str, **kwargs: Unpack[Options]) -> str: ...
# fetch("...", unknown=True)  # ERROR: unexpected keyword argument
```

---

## Stdlib Additions

### `itertools.batched()` — PEP 718

Batch an iterable into fixed-size tuples. The final batch may be shorter than `n`.

```python
from itertools import batched
list(batched("ABCDEFG", 3))  # [('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]
for chunk in batched(records, 100): db.bulk_insert(chunk)
```

3.11 equivalent: manual `zip(*[iter(it)] * n)` or a generator function.

### `pathlib.Path.walk()` — bpo-33428

`os.walk()` semantics with `Path` objects instead of strings.

```python
from pathlib import Path

# 3.11
import os
for root, dirs, files in os.walk("src"):
    for name in files:
        print(os.path.join(root, name))

# 3.12
for root, dirs, files in Path("src").walk():
    for name in files:
        print(root / name)
```

Parameters `top_down`, `on_error`, `follow_symlinks` match `os.walk()`.

### Improved f-string parsing — PEP 701

F-strings permit any valid Python expression: reuse of the outer quote character, nested
f-strings, and multiline expressions.

```python
# 3.11 — quote reuse forbidden; this raised SyntaxError
msg = f"{'hello'}"

# 3.12 — valid
msg = f"{'hello'}"
nested = f"{f"{name}"}"
total = f"Total: {sum(x.price for x in cart if x.in_stock)}"
```

---

## Protocol Changes

### Buffer protocol — PEP 688

`__buffer__` exposes a buffer interface. `collections.abc.Buffer` is a runtime-checkable ABC.

```python
from collections.abc import Buffer
def process(data: Buffer) -> None: view = memoryview(data)
```

### Per-interpreter GIL — PEP 684

Foundation for sub-interpreter isolation with independent GILs. Experimental in 3.12;
Python-level sub-interpreter support requires 3.13+. No application-level code changes needed.

