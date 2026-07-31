# Async and Coroutine Errors

## await-not-async: Check await used in coroutines

**Error Code**: `[await-not-async]`

**Configuration**: Enabled by default

**Type Safety Principle**: `await` must be used inside a coroutine (async def function).

### When This Is an Error

```python
async def f() -> None: ...


def g() -> None:
    # Error: "await" outside coroutine ("async def") [await-not-async]
    await f()
```

### Examples of Corrected Code

```python
async def f() -> None: ...


async def g() -> None:
    await f()  # OK - inside async function
```

### Configuration Options

Suppress specific instances:

```python
def g() -> None:
    await f()  # type: ignore[await-not-async]
```

---

## unused-coroutine: Check coroutine return value used

**Error Code**: `[unused-coroutine]`

**Configuration**: Enabled by default

**Type Safety Principle**: Async function calls must be awaited to actually execute.

### When This Is an Error

```python
async def f() -> None: ...


async def g() -> None:
    f()  # Error: missing await [unused-coroutine]
    await f()  # OK
```

### Examples of Corrected Code

```python
async def f() -> None: ...


async def g() -> None:
    await f()  # OK - awaited


# Or assign if intentional
async def h() -> None:
    _ = f()  # OK - explicitly ignored
```

### Configuration Options

Suppress specific instances:

```python
async def g() -> None:
    f()  # type: ignore[unused-coroutine]
```

---

## top-level-await: Warn about top-level await expressions

**Error Code**: `[top-level-await]`

**Configuration**: Enabled by default

**Type Safety Principle**: Top-level await is only valid in certain environments.

### When This Is an Error

```python
async def f() -> None: ...


top = await f()  # Error: "await" outside function [top-level-await]
```

### When THIS IS NOT an Error

#### In async function

```python
async def main() -> None:
    top = await f()  # OK - inside async function
```

#### In IPython REPL

```python
# In IPython, top-level await is allowed
top = await f()
```

### Configuration Options

```ini
[mypy]
disable_error_code = top-level-await
```

---

## Key Async Patterns for Type Checking

### Correct async pattern

```python
import asyncio
from typing import Coroutine


async def fetch_data(url: str) -> dict:
    # Simulate async operation
    return {"data": "value"}


async def process() -> None:
    result = await fetch_data("https://example.com")
    print(result)


# Run the coroutine
asyncio.run(process())  # OK
```

### Common mistakes

```python
async def fetch_data(url: str) -> dict:
    return {"data": "value"}


# Error: missing await
result = fetch_data("https://example.com")

# Error: not in async context
await fetch_data("https://example.com")
```

### Proper type annotations for async functions

```python
from typing import Awaitable, Coroutine


# Return type includes automatic Coroutine wrapping
async def get_value() -> int:
    return 42


# If you need to type a variable holding a coroutine
coro: Coroutine[None, None, int] = get_value()

# Or use Awaitable for more flexibility
awaitable: Awaitable[int] = get_value()
```
