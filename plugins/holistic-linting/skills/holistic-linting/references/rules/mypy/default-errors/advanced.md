# Advanced Type Checking Errors

## name-match: Check naming is consistent

**Error Code**: `[name-match]`

**Configuration**: Enabled by default

**Type Safety Principle**: Named tuple and TypedDict definitions must match their variable names.

### When This Is an Error

```python
from typing import NamedTuple

# Error: First argument to namedtuple() should be "Point2D", not "Point"
Point2D = NamedTuple("Point", [("x", int), ("y", int)])
```

### Examples of Corrected Code

```python
from typing import NamedTuple

Point2D = NamedTuple("Point2D", [("x", int), ("y", int)])  # OK


# Or use class syntax
class Point(NamedTuple):
    x: int
    y: int
```

### Configuration Options

Suppress specific instances:

```python
Point2D = NamedTuple("Point", [("x", int), ("y", int)])  # type: ignore[name-match]
```

---

## no-overload-impl: Check overloads have implementation

**Error Code**: `[no-overload-impl]`

**Configuration**: Enabled by default

**Type Safety Principle**: Overloaded functions must have a non-overloaded implementation.

### When This IS an Error

```python
from typing import overload


@overload
def func(value: int) -> int: ...


@overload
def func(value: str) -> str: ...


# Missing actual implementation
```

### Examples of Corrected Code

```python
from typing import overload


@overload
def func(value: int) -> int: ...


@overload
def func(value: str) -> str: ...


def func(value):  # OK - implementation required
    return value
```

### Configuration Options

Suppress specific instances:

```python
# Use # type: ignore on final definition
def func(value):  # type: ignore[no-overload-impl]
    return value
```

---

## overload-overlap: Check overloaded functions don't overlap

**Error Code**: `[overload-overlap]`

**Configuration**: Enabled by default

**Type Safety Principle**: Multiple overload variants with overlapping signatures create ambiguity.

### When This IS an Error

```python
from typing import overload


class A: ...


class B(A): ...


@overload
def foo(x: B) -> int: ...
# Error: Overloaded function signatures 1 and 2 overlap with incompatible return types [overload-overlap]
@overload
def foo(x: A) -> str: ...


def foo(x):
    return 1 if isinstance(x, B) else "str"
```

### Examples of Corrected Code

```python
from typing import overload


class A: ...


class B(A): ...


@overload
def foo(x: A) -> str: ...  # More general first


@overload
def foo(x: B) -> int: ...  # More specific second


def foo(x):
    if isinstance(x, B):
        return 1
    return str(x)
```

### Configuration Options

Suppress specific instances:

```python
@overload
def foo(x: B) -> int: ...  # type: ignore[overload-overlap]
```

---

## overload-cannot-match: Check overload signatures can match

**Error Code**: `[overload-cannot-match]`

**Configuration**: Enabled by default

**Type Safety Principle**: All overload variants should be reachable by some call signature.

### When This IS an Error

```python
from typing import overload


@overload
def process(response1: object, response2: object) -> object: ...


# Error: Overloaded function signature 2 will never be matched [overload-cannot-match]
@overload
def process(response1: int, response2: int) -> int: ...


def process(response1, response2):
    return response1 + response2
```

### Examples of Corrected Code

```python
from typing import overload


@overload
def process(response1: int, response2: int) -> int: ...


@overload
def process(response1: str, response2: str) -> str: ...


@overload
def process(response1: object, response2: object) -> object: ...


def process(response1, response2):
    if isinstance(response1, int):
        return response1 + response2
    elif isinstance(response1, str):
        return response1 + response2
    return response1
```

### Configuration Options

Suppress specific instances:

```python
@overload
def process(response1: int, response2: int) -> int: ...  # type: ignore[overload-cannot-match]
```

---

## narrowed-type-not-subtype: Check TypeIs narrows types

**Error Code**: `[narrowed-type-not-subtype]`

**Configuration**: Enabled by default

**Type Safety Principle**: TypeIs must narrow to a subtype of the input type (PEP 742).

### When This IS an Error

```python
from typing_extensions import TypeIs


# Error: str is not a subtype of int [narrowed-type-not-subtype]
def f(x: int) -> TypeIs[str]: ...
```

### Examples of Corrected Code

```python
from typing_extensions import TypeIs


def f(x: object) -> TypeIs[str]:  # OK - str is subtype of object
    return isinstance(x, str)


def g(x: int | str) -> TypeIs[str]:  # OK - str is subtype of int|str
    return isinstance(x, str)
```

### Configuration Options

Suppress specific instances:

```python
def f(x: int) -> TypeIs[str]:  # type: ignore[narrowed-type-not-subtype]
    ...
```

---

## exit-return: Check **exit** return type

**Error Code**: `[exit-return]`

**Configuration**: Enabled by default

**Type Safety Principle**: **exit** return type must reflect whether exceptions are suppressed.

### When This IS an Error

```python
class MyContext:
    def __exit__(self, exc, value, tb) -> bool:  # Error - if always returns False
        print("exit")
        return False
```

### Examples of Corrected Code

```python
from typing import Literal


class MyContext:
    def __exit__(self, exc, value, tb) -> Literal[False]:  # OK
        print("exit")
        return False


class MyContextOrNone:
    def __exit__(self, exc, value, tb) -> None:  # OK - same as False
        print("exit")
```

### Configuration Options

Suppress specific instances:

```python
class MyContext:
    def __exit__(self, exc, value, tb) -> bool:  # type: ignore[exit-return]
        return False
```

---

## assert-type: Check types in assert_type

**Error Code**: `[assert-type]`

**Configuration**: Enabled by default

**Type Safety Principle**: assert_type verifications must match the actual inferred type.

### When This IS an Error

```python
from typing_extensions import assert_type

assert_type([1], list[int])  # OK
assert_type([1], list[str])  # Error - inferred type is list[int]
```

### Examples of Corrected Code

```python
from typing_extensions import assert_type

assert_type([1], list[int])  # OK
assert_type(["text"], list[str])  # OK

x: list[int | str] = [1, "text"]
assert_type(x, list[int | str])  # OK
```

### Configuration Options

Suppress specific instances:

```python
assert_type([1], list[str])  # type: ignore[assert-type]
```

---

## truthy-function: Check function not used in boolean context

**Error Code**: `[truthy-function]`

**Configuration**: Enabled by default

**Type Safety Principle**: Functions always evaluate to true in boolean contexts.

### When This IS an Error

```python
def f(): ...


# Error: Function "Callable[[], Any]" could always be true in boolean context [truthy-function]
if f:
    pass
```

### Examples of Corrected Code

```python
def f(): ...


# Call the function
if f():
    pass

# Or check for None
func: Callable[[], None] | None = ...
if func is not None:
    func()
```

### Configuration Options

Suppress specific instances:

```python
if f:  # type: ignore[truthy-function]
    pass
```

---

## annotation-unchecked: Notify about annotation in unchecked function

**Error Code**: `[annotation-unchecked]`

**Configuration**: Enabled by default

**Type Safety Principle**: Functions with annotations should have their bodies checked.

### When This OCCURS

```python
def test_assignment():  # "-> None" return annotation is missing
    # Note: By default the bodies of untyped functions are not checked,
    # consider using --check-untyped-defs [annotation-unchecked]
    x: int = "no way"
```

### Examples of Corrected Code

```python
def test_assignment() -> None:  # Add return annotation
    x: int = 42
    assert x == 42
```

### Configuration Options

```ini
[mypy]
check_untyped_defs = True
disallow_untyped_defs = True
```

---

## prop-decorator: Decorator preceding property not supported

**Error Code**: `[prop-decorator]`

**Configuration**: Enabled by default (as subcode of misc)

**Type Safety Principle**: Decorators before @property can break type inference.

### When This OCCURS

```python
class MyClass:
    @special  # Error: Decorator preceding property not supported [prop-decorator]
    @property
    def magic(self) -> str:
        return "xyzzy"
```

### Examples of Corrected Code

```python
class MyClass:
    @property
    def magic(self) -> str:
        return "xyzzy"  # OK

    # Or move decorator after property
    @property
    @special  # Not supported, but may work depending on decorator
    def value(self) -> int:
        return 42
```

### Configuration Options

Suppress specific instances:

```python
class MyClass:
    @special  # type: ignore[prop-decorator]
    @property
    def magic(self) -> str:
        return "xyzzy"
```

---

## syntax: Report syntax errors

**Error Code**: `[syntax]`

**Configuration**: Enabled by default

**Type Safety Principle**: Code must be syntactically valid to be type-checked.

### When This IS an Error

```python
def invalid(
    # Missing closing parenthesis
```

### Examples of Corrected Code

```python
def valid():
    pass
```

---

## misc: Miscellaneous checks

**Error Code**: `[misc]`

**Configuration**: Enabled by default

**Type Safety Principle**: Various other type safety checks not covered by specific codes.

### When THIS OCCURS

Various miscellaneous checks including:

- Type compatibility issues without specific codes
- Unusual type patterns
- Implementation-specific issues

### Configuration Options

Suppress specific instances:

```python
x = ...  # type: ignore[misc]
```
