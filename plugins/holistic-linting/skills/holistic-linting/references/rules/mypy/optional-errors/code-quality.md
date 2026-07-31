# Code Quality and Redundancy Errors

## redundant-cast: Flag unnecessary type casts

**Error Code**: `[redundant-cast]`

**Configuration**: Enable with `warn_redundant_casts = True`

**Type Safety Principle**: Unnecessary casts obscure code and reduce readability.

### When This IS an Error

```python
from typing import cast

x = 5
# Error: Redundant cast from "int" to "int" [redundant-cast]
y = cast(int, x)
```

### Examples of Corrected Code

```python
from typing import cast

x = 5
y = x  # OK - no cast needed

# Cast is needed when narrowing from union
value: int | str = 5
integer = cast(int, value)  # OK if necessary
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
warn_redundant_casts = True
```

---

## redundant-self: Detect redundant Self annotations

**Error Code**: `[redundant-self]`

**Configuration**: Enabled with optional checks

**Type Safety Principle**: Self type is already implied in method signatures.

### When This IS an Error

```python
from typing_extensions import Self


class MyClass:
    # Error: Redundant Self annotation [redundant-self]
    def method(self: Self) -> Self:
        return self
```

### Examples of Corrected Code

```python
from typing_extensions import Self


class MyClass:
    def method(self) -> Self:
        return self


# Or explicit if really needed
class MyClass:
    def method(self: "MyClass") -> "MyClass":
        return self
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = redundant-self
```

---

## redundant-expr: Detect redundant expressions

**Error Code**: `[redundant-expr]`

**Configuration**: Enable with `enable_error_code = redundant-expr`

**Type Safety Principle**: Remove unnecessary code that has no effect.

### When This IS an Error

```python
# Error: Redundant condition; condition is always true [redundant-expr]
if True:
    print("always runs")

# Error: Redundant comparison; comparison is always true [redundant-expr]
x = 5
if x == x:
    pass
```

### Examples of Corrected Code

```python
print("always runs")  # Remove unnecessary condition

x = 5
if x > 0:
    pass  # Use meaningful condition
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = redundant-expr
```

---

## unused-ignore: Detect unnecessary type ignores

**Error Code**: `[unused-ignore]`

**Configuration**: Enable with `warn_unused_ignores = True`

**Type Safety Principle**: Remove type: ignore comments that don't suppress errors.

### When This IS an Error

```python
# Error: Unused "type: ignore" comment [unused-ignore]
x = 5
result = x + 10  # type: ignore[operator]
```

### Examples of Corrected Code

```python
# Remove unnecessary ignores
x = 5
result = x + 10  # OK - no error, no ignore needed

# Keep useful ignores
x = 5
result = x + "string"  # type: ignore[operator]
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
warn_unused_ignores = True
```

---

## unused-awaitable: Flag unawaited async values

**Error Code**: `[unused-awaitable]`

**Configuration**: Enable with `enable_error_code = unused-awaitable`

**Type Safety Principle**: Async function results must be awaited to execute.

### When This IS an Error

```python
async def fetch() -> str:
    return "data"


async def process() -> None:
    # Error: "await" expected (coroutine "fetch" is not awaited) [unused-awaitable]
    result = fetch()
```

### Examples of Corrected Code

```python
async def fetch() -> str:
    return "data"


async def process() -> None:
    result = await fetch()  # OK
    _ = fetch()  # OK - explicitly ignored
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = unused-awaitable
```

---

## ignore-without-code: Ensure type ignores have error codes

**Error Code**: `[ignore-without-code]`

**Configuration**: Enable with `enable_error_code = ignore-without-code`

**Type Safety Principle**: Type ignores should specify which errors they suppress.

### When This IS an Error

```python
# Error: Missing error code for type: ignore comment [ignore-without-code]
x = 5  # type: ignore
```

### Examples of Corrected Code

```python
x = 5  # OK - no error, no ignore needed

# Or specify the error code
result = x + "string"  # type: ignore[operator]
```

### Configuration

Enable in mypy configuration:

```ini
[mypy]
enable_error_code = ignore-without-code
```

### Best Practice

Always specify error codes in type: ignore comments:

```python
# Good - specific error code
result = x + "string"  # type: ignore[operator]

# Acceptable - multiple specific codes
data = load_any()  # type: ignore[no-any-return, arg-type]

# Avoid - no specific code
data = load_any()  # type: ignore
```
