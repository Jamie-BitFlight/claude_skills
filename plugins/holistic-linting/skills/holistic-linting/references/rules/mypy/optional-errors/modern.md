# Modern Python Feature Errors

## explicit-override: Require @override decorator

**Error Code**: `[explicit-override]`

**Configuration**: Enable with `enable_error_code = explicit-override`

**Type Safety Principle**: Per PEP 698, explicitly mark method overrides with @override decorator (Python 3.12+).

### What This Error Prevents

Requires the `@override` decorator when overriding a base class method, making overrides explicit and catching accidental shadowing.

### When This IS an Error

```python
from typing import override  # Python 3.12+


class Base:
    def method(self) -> int:
        return 42


class Derived(Base):
    # Error: Method is not overriding any base class method [explicit-override]
    def method(self) -> int:
        return 43
```

### Examples of Corrected Code

```python
from typing import override


class Base:
    def method(self) -> int:
        return 42


class Derived(Base):
    @override
    def method(self) -> int:
        return 43

    @override
    def new_method(self) -> str:
        return "new"
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = explicit-override
```

### Practical Usage

```python
from typing import override


class Animal:
    def speak(self) -> str:
        return "generic sound"

    def move(self) -> None:
        print("moving")


class Dog(Animal):
    @override
    def speak(self) -> str:
        return "woof"

    # Error if not marked with @override
    def bark(self) -> None:
        print("bark bark")
```

---

## mutable-override: Check unsafe mutable attribute overrides

**Error Code**: `[mutable-override]`

**Configuration**: Optional check

**Type Safety Principle**: Mutable attribute overrides can violate Liskov substitution principle.

### When This IS an Error

```python
class Base:
    attr: list[int] = []


class Derived(Base):
    # Error: Mutable attribute in override is unsafe [mutable-override]
    attr: list[int] = []
```

### Examples of Corrected Code

```python
from typing import ClassVar


class Base:
    attr: ClassVar[list[int]] = []


class Derived(Base):
    attr: ClassVar[list[int]] = []  # OK - class variable


# Or use instance attributes
class Base:
    def __init__(self):
        self.attr: list[int] = []


class Derived(Base):
    def __init__(self):
        super().__init__()
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = mutable-override
```

---

## unimported-reveal: Ensure reveal_type is imported

**Error Code**: `[unimported-reveal]`

**Configuration**: Enable with `enable_error_code = unimported-reveal`

**Type Safety Principle**: Use imported reveal_type to avoid implicit imports.

### When This IS an Error

```python
# Error: "reveal_type" is not imported [unimported-reveal]
reveal_type(x)
```

### Examples of Corrected Code

```python
from typing import reveal_type  # Python 3.11+

# or
from typing_extensions import reveal_type  # Older Python versions

x = 5
reveal_type(x)  # OK - imported
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = unimported-reveal
```

### Debugging Pattern

```python
from typing import reveal_type


def process(value: int | str) -> None:
    reveal_type(value)  # Shows: int | str

    if isinstance(value, int):
        reveal_type(value)  # Shows: int (narrowed)
    else:
        reveal_type(value)  # Shows: str (narrowed)
```

---

## deprecated: Flag use of deprecated features

**Error Code**: `[deprecated]`

**Configuration**: Enable with `enable_error_code = deprecated`

**Type Safety Principle**: Use current features instead of deprecated ones per PEP 702.

### What This Error Prevents

Flags code using functions or classes decorated with `@warnings.deprecated` or type checker equivalents.

### When This IS an Error

```python
import warnings


@warnings.deprecated("Use new_function instead", category=DeprecationWarning)
def old_function():
    return 42


# Error: "old_function" is deprecated [deprecated]
result = old_function()
```

### Examples of Corrected Code

```python
def new_function():
    return 42


result = new_function()  # OK - not deprecated
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = deprecated
```

### Marking Functions as Deprecated

```python
import warnings
from typing_extensions import deprecated


@deprecated("Use process_v2 instead")
def process_old(data: list) -> int:
    return len(data)


def process_v2(data: list) -> int:
    """New implementation with better performance."""
    return len(data)
```

---

## Summary of Modern Python Best Practices

### Python 3.10+

- Use `@override` decorator for explicit method overrides
- Use pattern matching with `match/case` statements
- Use union operator `|` instead of `Union[A, B]`
- Use `X | None` instead of `Optional[X]`

### Python 3.11+

- Use `from typing import reveal_type` for debugging
- Use `typing_extensions.TypeIs` for custom type guards
- Use `typing_extensions.Self` for return types

### Python 3.12+

- Use `@override` from `typing` module
- Use PEP 695 type parameter syntax: `def func[T: int](x: T) -> T:`
- Use `type` aliases with `type Name = Value`

### Compatibility

For older Python versions, use `typing_extensions`:

```python
from typing_extensions import override, TypeIs, Self
```

---

## Configuration for Modern Python

```ini
[mypy]
# Require Python 3.12+
python_version = 3.12

# Enable modern error codes
enable_error_code = explicit-override,unused-awaitable,exhaustive-match,deprecated

# Strict type checking
disallow_untyped_defs = True
disallow_untyped_calls = True
disallow_any_generics = True
disallow_any_unimported = True
disallow_any_explicit = True

# Code quality
warn_return_any = True
warn_unused_ignores = True
warn_redundant_casts = True
warn_unreachable = True

# Compatibility
strict_equality = True
check_untyped_defs = True
```
