# Type Safety with Mypy

**Tooling policy**: **ty** is the default type checker for new work in this ecosystem. **mypy** remains fully supported when an existing project already uses it — follow that project's `pyproject.toml` / `mypy.ini` and CI; do not require migration to ty. Annotation guidance below applies to both; mypy doc links are the authoritative reference for mypy diagnostics and for patterns that are checker-specific.

**REQUIREMENT**: All Python code MUST be comprehensively typed using Python 3.11+ native type hints.

**Python Version**: Python 3.11+ is required unless explicitly documented otherwise. Older versions are rare, documented exceptions.

**The model MUST read the official mypy documentation examples before implementing type patterns** (especially when resolving mypy output). Each subsection links to authoritative mypy docs. When using **ty** as the primary checker, still use these patterns; map diagnostics via the `/python3-development:ty` skill and migration reference where ty differs from mypy.

## When to Use Generics

Use generics for type-safe container classes and functions that work with multiple types.

**Applicable scenarios:**

- Custom collection classes (stacks, queues, boxes)
- Functions accepting multiple type variants
- Decorators and factory methods
- Reusable protocols and type aliases

**MUST read examples before implementing**: `mypy-docs/generics.rst`

**Python 3.11 Generic Pattern** (TypeVar with Generic):

```python
from typing import TypeVar, Generic, Sequence

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

def first(seq: Sequence[T]) -> T:
    return seq[0]
```

**Python 3.12+ Generic Pattern** (Native Syntax):

```python
class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

def first[T](seq: Sequence[T]) -> T:
    return seq[0]
```

**Type Variable Bounds** (restrict to subtypes):

```python
from collections.abc import Sequence
from typing import Protocol

class SupportsAbs[T](Protocol):
    def __abs__(self) -> T: ...

def max_by_abs[T: SupportsAbs[float]](*xs: T) -> T:
    return max(xs, key=abs)
```

**Value Restrictions** (limit to specific types):

```python
def concat[S: (str, bytes)](x: S, y: S) -> S:
    return x + y  # Type-safe for str OR bytes, but not mixed
```

**Generic Method Chaining** (precise return types):

```python
from typing import Self

class Shape:
    scale: float = 1.0

    def set_scale(self, scale: float) -> Self:
        self.scale = scale
        return self  # Returns precise subclass type
```

## When to Use Protocols

Use protocols for structural subtyping when you need duck typing with type safety. Protocols check whether an object has required methods/attributes regardless of inheritance.

**Applicable scenarios:**

- Accept any object with specific capabilities without requiring inheritance
- Define interfaces for duck-typed code
- Create flexible callback types
- Ensure compatibility without tight coupling

**MUST read examples before implementing**: `mypy-docs/protocols.rst`

**Basic Protocol Pattern**:

```python
from typing import Protocol

class SupportsClose(Protocol):
    def close(self) -> None: ...

def close_resource(resource: SupportsClose) -> None:
    resource.close()  # Works with ANY object having close() method

# No inheritance needed - structural match
class FileHandler:
    def close(self) -> None:
        print("Closing file")

close_resource(FileHandler())  # Type-safe
```

**Read-Only Attributes** (use @property to avoid invariance issues):

```python
from typing import Protocol

class Named(Protocol):
    @property
    def name(self) -> str: ...  # Read-only via property
```

**Recursive Protocols** (tree structures):

```python
from typing import Protocol

class TreeLike(Protocol):
    value: int

    @property
    def left(self) -> TreeLike | None: ...

    @property
    def right(self) -> TreeLike | None: ...
```

**Runtime Checks**:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: object) -> None:
    if isinstance(obj, Drawable):  # Runtime check enabled
        obj.draw()
```

**WARNING**: `isinstance()` with protocols only verifies attribute existence, NOT type correctness. Use for structural validation, not precise type guarantees.

## TypedDict for Dictionary Typing

Use TypedDict for dictionaries with fixed schemas and string keys where each key has a specific value type.

**Applicable scenarios:**

- Dictionaries representing objects with predictable structure
- JSON-like data structures
- Configuration dictionaries
- API request/response payloads

**MUST read examples before implementing**: `mypy-docs/typed_dict.rst`

**Required Fields Pattern** (all keys required):

```python
from typing import TypedDict

class Movie(TypedDict):
    name: str
    year: int
    director: str

movie: Movie = {
    "name": "Blade Runner",
    "year": 1982,
    "director": "Ridley Scott"
}  # All keys required
```

**Optional Fields Pattern** (total=False):

```python
from typing import TypedDict

class MovieOptions(TypedDict, total=False):
    subtitles: bool
    audio_language: str

options: MovieOptions = {}  # Empty dict valid
options2: MovieOptions = {"subtitles": True}  # Partial valid
```

**Mixed Required/Optional Pattern**:

```python
from typing import TypedDict

class MovieBase(TypedDict):
    name: str  # Required
    year: int  # Required

class Movie(MovieBase, total=False):
    director: str  # Optional
    rating: float  # Optional

movie: Movie = {"name": "Alien", "year": 1979}  # Valid
```

**CRITICAL**: Always annotate variables when assigning TypedDict literals. Without annotation, mypy infers `dict[str, Any]`:

```python
# Wrong - inferred as dict[str, Any]
movie = {"name": "Alien", "year": 1979}

# Correct - explicitly typed
movie: Movie = {"name": "Alien", "year": 1979}
```

## Type Narrowing

Use type narrowing to refine broad union types to specific types based on runtime checks.

**Applicable scenarios:**

- Handling union types (e.g., `str | int | None`)
- Optional value processing
- Validating input types
- Control flow-based type refinement

**MUST read examples before implementing**: `mypy-docs/type_narrowing.rst`

**isinstance() Narrowing**:

```python
def process_value(value: str | int) -> str:
    if isinstance(value, str):
        return value.upper()  # Narrowed to str
    else:
        return str(value * 2)  # Narrowed to int
```

**None Checks**:

```python
def greet(name: str | None) -> str:
    if name is not None:
        return f"Hello, {name}"  # Narrowed to str
    return "Hello, stranger"
```

**Type Guards** (custom narrowing functions):

```python
from typing import TypeGuard

def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)

def process(values: list[object]) -> None:
    if is_str_list(values):
        # Narrowed to list[str] in this branch
        print(" ".join(values))
```

**TypeIs (Python 3.13+, more powerful than TypeGuard)**:

```python
from typing import TypeIs

def is_str(val: object) -> TypeIs[str]:
    return isinstance(val, str)

def process(val: str | int) -> None:
    if is_str(val):
        print(val.upper())  # Narrowed to str
    else:
        print(val * 2)  # Narrowed to int (complement type)
```

**Key difference**: TypeGuard narrows only the if-branch; TypeIs narrows both branches (if-branch to the specified type, else-branch to the complement).

## attrs vs dataclasses vs pydantic

**Decision Matrix**:

| Feature                | attrs                              | dataclasses                            | pydantic                                 |
| ---------------------- | ---------------------------------- | -------------------------------------- | ---------------------------------------- |
| **Performance**        | Fastest (compiled)                 | Fast (native)                          | Slower (validation overhead)             |
| **Validation**         | Basic (via converters/validators)  | None (requires custom `__post_init__`) | Comprehensive (built-in)                 |
| **Immutability**       | `@frozen`                          | `frozen=True`                          | `frozen=True` (v2)                       |
| **Evolution**          | Excellent (`evolve()`)             | Basic (`replace()`)                    | Good (`model_copy()`)                    |
| **Slots**              | Automatic                          | Manual (`slots=True`)                  | Automatic (v2)                           |
| **Type Coercion**      | Manual                             | None                                   | Automatic                                |
| **JSON Serialization** | Manual                             | Manual                                 | Native (`model_dump_json()`)             |
| **Use When**           | High-performance, pure Python data | Stdlib-only requirement                | External data validation (APIs, configs) |

**attrs Pattern** (high performance, pure Python):

```python
from attrs import define, field

@define
class User:
    name: str
    age: int = field(validator=lambda i, a, v: v >= 0)
    email: str | None = None
```

**MUST read examples**: `mypy-docs/additional_features.rst`

**dataclasses Pattern** (stdlib-only):

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class User:
    name: str
    age: int
    email: str | None = None

    def __post_init__(self) -> None:
        if self.age < 0:
            raise ValueError("Age must be non-negative")
```

**pydantic Pattern** (external data validation):

```python
from pydantic import BaseModel, Field, field_validator

class User(BaseModel):
    name: str
    age: int = Field(ge=0)
    email: str | None = None

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Age must be non-negative')
        return v
```

**Recommendation**:

- **Default**: Use `attrs` for internal data structures (best performance, most features)
- **Stdlib-only requirement**: Use `dataclasses`
- **External data (APIs, configs, user input)**: Use `pydantic` (if already a dependency)

**NEVER add pydantic as a dependency solely for dataclasses. Use attrs or stdlib dataclasses instead.**

## Additional Mypy Features

**MUST read before using advanced patterns**: `mypy-docs/additional_features.rst`

**Generic Dataclasses**:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass
class Box(Generic[T]):
    value: T

int_box: Box[int] = Box(value=42)
str_box: Box[str] = Box(value="hello")
```

**Self Type for Method Chaining**:

```python
from typing import Self

class Builder:
    def set_name(self, name: str) -> Self:
        self.name = name
        return self

    def set_value(self, value: int) -> Self:
        self.value = value
        return self

# Type-safe chaining
builder = Builder().set_name("test").set_value(42)
```

## Mypy Configuration Best Practices

**Strict Mode Configuration** (pyproject.toml):

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_reexport = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
```

**Per-Module Overrides** (for gradual typing):

```toml
[[tool.mypy.overrides]]
module = "third_party_lib.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "legacy_code.*"
disallow_untyped_defs = false
```

**See**: `tool-library-registry.md` for complete configuration examples.
