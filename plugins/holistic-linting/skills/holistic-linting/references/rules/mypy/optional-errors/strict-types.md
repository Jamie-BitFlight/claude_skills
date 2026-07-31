# Strict Type Checking Errors

## no-untyped-def: Require function type annotations

**Error Code**: `[no-untyped-def]`

**Configuration**: Enable with `disallow_untyped_defs = True`

**Type Safety Principle**: All functions should have explicit type annotations for parameters and return values.

### What This Error Prevents

Requires that all functions have type annotations (either Python 3 annotations or type comments).

### When This IS an Error

```python
# Error: Function is missing a return type annotation [no-untyped-def]
def greet(name):
    return f"Hello, {name}!"


# Error: Function is missing parameter type annotations [no-untyped-def]
def add(x, y):
    return x + y


# Error: Missing return type annotation [no-untyped-def]
def process(data: list):
    return len(data)
```

### When THIS IS NOT an Error

#### All parameters and return types annotated

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"


def add(x: int, y: int) -> int:
    return x + y


def process(data: list[str]) -> int:
    return len(data)
```

#### Type comments (older style)

```python
def greet(name):
    # type: (str) -> str
    return f"Hello, {name}!"
```

### Examples of Error-Producing Code

```python
# Error: no-untyped-def
def calculate(values):
    return sum(values)


class DataProcessor:
    # Error: no-untyped-def
    def process(self, data):
        return len(data)
```

### Examples of Corrected Code

```python
def calculate(values: list[int]) -> int:
    return sum(values)


class DataProcessor:
    def process(self, data: list) -> int:
        return len(data)
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
disallow_untyped_defs = True
```

---

## no-untyped-call: Prevent calling untyped functions

**Error Code**: `[no-untyped-call]`

**Configuration**: Enable with `disallow_untyped_calls = True`

**Type Safety Principle**: Only call functions with known type signatures.

### When This IS an Error

```python
def untyped_function(x):
    return x * 2


def typed_function(value: int) -> int:
    # Error: Call to untyped function "untyped_function" in typed context [no-untyped-call]
    return untyped_function(value)
```

### Examples of Corrected Code

```python
def typed_function(x: int) -> int:
    return x * 2


def caller(value: int) -> int:
    return typed_function(value)  # OK
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
disallow_untyped_calls = True
```

---

## type-arg: Require generic type arguments

**Error Code**: `[type-arg]`

**Configuration**: Enable with `disallow_any_generics = True`

**Type Safety Principle**: Generic types must have explicit type arguments, not implicit Any.

### When This IS an Error

```python
from typing import List


# Error: Missing type argument for generic type "list" [type-arg]
def process(items: list) -> None:
    pass


# Error: Missing type argument for generic type "List" [type-arg]
x: List = [1, 2, 3]
```

### Examples of Corrected Code

```python
from typing import List


def process(items: list[int]) -> None:
    pass


x: list[int] = [1, 2, 3]
y: List[str] = ["a", "b"]
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
disallow_any_generics = True
```

---

## no-any-return: Check return values are not Any

**Error Code**: `[no-any-return]`

**Configuration**: Enable with `warn_return_any = True`

**Type Safety Principle**: Functions should not return Any unless explicitly annotated.

### When This IS an Error

```python
from typing import Any


def process(value: Any) -> int:
    # Error: Returning Any from function declared to return "int" [no-any-return]
    return value
```

### Examples of Corrected Code

```python
from typing import Any


def process(value: int) -> int:
    return value


# Or explicitly return Any if needed
def flexible(value: Any) -> Any:
    return value
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
warn_return_any = True
```

---

## no-any-unimported: Check Any from unimported sources

**Error Code**: `[no-any-unimported]`

**Configuration**: Enable with `disallow_any_unimported = True`

**Type Safety Principle**: Don't accept Any types from untyped imports.

### When This IS an Error

```python
# Error: Argument 1 to "process" has type "Any" from an untyped source [no-any-unimported]
import untyped_module


def process(value: int) -> None:
    pass


process(untyped_module.something)
```

### Examples of Corrected Code

```python
# Install type stubs
# pip install types-untyped-module
import typed_module


def process(value: int) -> None:
    pass


process(typed_module.value)  # OK - has type information
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
disallow_any_unimported = True
```

---

## explicit-any: Disallow explicit Any annotations

**Error Code**: `[explicit-any]`

**Configuration**: Enable with `disallow_any_explicit = True`

**Type Safety Principle**: Avoid explicit Any annotations; use type variables or unions instead.

### When This IS an Error

```python
from typing import Any


# Error: Explicit "Any" is not allowed [explicit-any]
def process(value: Any) -> Any:
    return value
```

### Examples of Corrected Code

```python
from typing import TypeVar

T = TypeVar("T")


def process(value: T) -> T:
    return value


# Or use union for known types
def flexible(value: int | str) -> int | str:
    return value
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
disallow_any_explicit = True
```
