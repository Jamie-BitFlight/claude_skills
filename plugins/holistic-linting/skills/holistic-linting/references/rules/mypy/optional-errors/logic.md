# Logic and Control Flow Errors

## comparison-overlap: Warn about invalid comparisons

**Error Code**: `[comparison-overlap]`

**Configuration**: Enable with `strict_equality = True`

**Type Safety Principle**: Comparisons should not be obviously true or false.

### When This IS an Error

```python
# Error: Comparison is always true [comparison-overlap]
if 5 == 5:
    print("always true")

# Error: Comparison is always false [comparison-overlap]
x: int = 5
if isinstance(x, str):
    print("never happens")
```

### Examples of Corrected Code

```python
# Remove obvious comparisons
print("value is 5")

# Use meaningful comparisons
x: int = 5
if x > 0:
    print("positive")
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
strict_equality = True
```

---

## unreachable: Identify dead code

**Error Code**: `[unreachable]`

**Configuration**: Enable with `warn_unreachable = True`

**Type Safety Principle**: Remove code that can never execute.

### When This IS an Error

```python
def process() -> int:
    return 42
    # Error: Statement is unreachable [unreachable]
    print("never runs")


if True:
    return 0
# Error: Statement is unreachable [unreachable]
process()
```

### Examples of Corrected Code

```python
def process() -> int:
    return 42
    # Remove unreachable code


if condition:
    return 0
else:
    process()  # Now reachable
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
warn_unreachable = True
```

---

## possibly-undefined: Warn about conditionally defined variables

**Error Code**: `[possibly-undefined]`

**Configuration**: Enable with `enable_error_code = possibly-undefined`

**Type Safety Principle**: Variables used later must be defined in all code paths.

### When This IS an Error

```python
# Error: Variable "value" may be undefined [possibly-undefined]
if condition:
    value = 5
else:
    pass

print(value)  # May not exist if condition is False
```

### Examples of Corrected Code

```python
value = None
if condition:
    value = 5
else:
    value = 0

print(value)  # Now definitely defined

# Or define in all branches
if condition:
    value = 5
else:
    value = 0

print(value)
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = possibly-undefined
```

---

## truthy-bool: Check non-boolean context usage

**Error Code**: `[truthy-bool]`

**Configuration**: Optional check

**Type Safety Principle**: Use explicit bool checks rather than truthy values.

### When This IS an Error

```python
from decimal import Decimal

value = Decimal("0")
# Error: Expression of type "Decimal" cannot be used as a boolean [truthy-bool]
if value:
    print("truthy")
```

### Examples of Corrected Code

```python
from decimal import Decimal

value = Decimal("0")
if value != 0:
    print("non-zero")

if bool(value):
    print("truthy")
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = truthy-bool
```

---

## truthy-iterable: Check Iterable in boolean context

**Error Code**: `[truthy-iterable]`

**Configuration**: Optional check

**Type Safety Principle**: Use explicit length checks for iterables.

### When This IS an Error

```python
from typing import Iterable

items: Iterable[int] = iter([1, 2, 3])
# Error: Iterables are not guaranteed to have __bool__ or __len__ [truthy-iterable]
if items:
    print("has items")
```

### Examples of Corrected Code

```python
from typing import Iterable

items: list[int] = [1, 2, 3]
if items:  # OK - list has __len__
    print("has items")

items_iter: Iterable[int] = iter([1, 2, 3])
items_list = list(items_iter)  # Convert to list first
if items_list:  # OK
    print("has items")
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = truthy-iterable
```

---

## exhaustive-match: Ensure match statements are exhaustive

**Error Code**: `[exhaustive-match]`

**Configuration**: Enable with `enable_error_code = exhaustive-match`

**Type Safety Principle**: Pattern matching should cover all possible cases (Python 3.10+).

### When This IS an Error

```python
def process(value: int | str) -> None:
    # Error: match statement without default case [exhaustive-match]
    match value:
        case int():
            print("integer")
        case str():
            print("string")
```

### Examples of Corrected Code

```python
def process(value: int | str | bool) -> None:
    match value:
        case int():
            print("integer")
        case str():
            print("string")
        case bool():
            print("boolean")
        case _:
            # Default case handles any other type
            pass
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = exhaustive-match
```

### Best Practices

```python
from enum import Enum
from typing import Union


class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"


def handle_status(status: Status) -> str:
    # With enum, match can be exhaustive
    match status:
        case Status.PENDING:
            return "waiting"
        case Status.RUNNING:
            return "in progress"
        case Status.COMPLETE:
            return "finished"
        # No default case needed with enum
```
