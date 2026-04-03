---
title: Type Safety Patterns
description: Advanced type safety patterns for stdlib scripts including overloads, protocols, and linter settings
version: 1.0.0
last_updated: '2026-02-15'
document_type: reference
python_compatibility: 3.11+
---

# Type Safety Patterns

Advanced patterns for type-safe stdlib Python code.

## Linter and Type-Checker Settings

**mypy strict mode with at minimum:**

```ini
[mypy]
python_version = 3.11
strict = True
disallow_any_explicit = True
disallow_any_generics = True
disallow_any_expr = True
warn_unused_ignores = True
no_implicit_optional = True
```

**pyright strict mode:**

```json
{
  "typeCheckingMode": "strict",
  "reportUnknownParameterType": "error",
  "reportUnknownArgumentType": "error",
  "reportUnknownVariableType": "error",
  "reportImplicitAny": "error"
}
```

**ruff:**

```toml
[tool.ruff.lint]
select = [
    "ANN",  # Require type annotations
    "PYI",  # Typing hygiene
]
```

**Enforce imports from collections.abc:**

```python
# Correct
from collections.abc import Iterable, Sequence, Mapping

# Wrong - old forms
from typing import List, Dict, Set, Tuple, Optional, Union
```

## Overloads for Type-Safe APIs

Use overloads when return type depends on input parameters.

```python
from typing import overload

@overload
def get_config(*, as_dict: bool = False) -> str: ...

@overload
def get_config(*, as_dict: bool) -> dict[str, str]: ...

def get_config(*, as_dict: bool = False) -> str | dict[str, str]:
    """Get configuration as string or dict."""
    config = {"key": "value"}
    if as_dict:
        return config
    return str(config)
```

## Protocols for Duck Typing

Define behavioral contracts without inheritance.

```python
from typing import Protocol

class Closable(Protocol):
    def close(self) -> None: ...

class Flushable(Protocol):
    def flush(self) -> None: ...

def cleanup(resource: Closable & Flushable) -> None:
    """Clean up a resource that can be flushed and closed."""
    resource.flush()
    resource.close()
```

## Type Narrowing with isinstance

Use type guards to narrow union types.

```python
from typing import Any

def process_data(data: str | dict[str, Any]) -> str:
    """Process string or dict data."""
    if isinstance(data, str):
        # Type narrowed to str
        return data.upper()
    else:
        # Type narrowed to dict[str, Any]
        return str(data)
```

## TypedDict for Structured Dicts

Define dict schemas with type checking.

```python
from typing import TypedDict, NotRequired

class UserConfig(TypedDict):
    name: str
    email: str
    age: NotRequired[int]  # Optional field

def validate_config(config: dict[str, Any]) -> UserConfig:
    """Validate and narrow config dict."""
    if not isinstance(config.get("name"), str):
        raise ValueError("name must be string")
    if not isinstance(config.get("email"), str):
        raise ValueError("email must be string")
    # age is optional
    if "age" in config and not isinstance(config["age"], int):
        raise ValueError("age must be int")
    return config  # type: ignore[return-value]
```

## Generic Functions

Create reusable type-safe functions.

```python
from typing import TypeVar
from collections.abc import Callable, Iterable

T = TypeVar("T")
U = TypeVar("U")

def map_values(items: Iterable[T], fn: Callable[[T], U]) -> list[U]:
    """Apply function to each item."""
    return [fn(item) for item in items]

# Usage with full type inference
numbers = [1, 2, 3]
strings = map_values(numbers, str)  # list[str] inferred
```

## Literal Types for Constants

Use Literal for finite sets of values.

```python
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

def set_log_level(level: LogLevel) -> None:
    """Set logging level to one of the valid values."""
    import logging
    logging.basicConfig(level=level)

# Type checker catches invalid values
set_log_level("DEBUG")  # OK
set_log_level("INVALID")  # Type error
```

## Final for Constants

Mark variables as constant.

```python
from typing import Final

MAX_RETRIES: Final = 3
API_ENDPOINT: Final = "https://api.example.com"

# Type checker prevents reassignment
MAX_RETRIES = 5  # Type error
```

## NewType for Type Safety

Create distinct types from existing types.

```python
from typing import NewType

UserId = NewType("UserId", int)
ProductId = NewType("ProductId", int)

def get_user(user_id: UserId) -> str:
    """Get user by ID."""
    return f"User {user_id}"

# Type checker enforces distinction
uid = UserId(123)
pid = ProductId(456)

get_user(uid)  # OK
get_user(pid)  # Type error - ProductId is not UserId
```

## Validation Pattern for External Data

Handle external data boundaries with type narrowing.

```python
import json
from pathlib import Path
from typing import Any, TypedDict

class Config(TypedDict):
    host: str
    port: int
    debug: bool

def load_config(path: Path) -> Config:
    """Load and validate config from JSON file."""
    raw: Any = json.loads(path.read_text())

    if not isinstance(raw, dict):
        raise ValueError("Config must be JSON object")

    host = raw.get("host")
    port = raw.get("port")
    debug = raw.get("debug", False)

    if not isinstance(host, str):
        raise ValueError("host must be string")
    if not isinstance(port, int):
        raise ValueError("port must be int")
    if not isinstance(debug, bool):
        raise ValueError("debug must be bool")

    return {"host": host, "port": port, "debug": debug}
```
