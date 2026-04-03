# Type System Pattern Examples

Before/after code examples for replacing `Any` types with modern Python 3.11+ type constructs. Each pattern includes when to use it and a concrete transformation.

## Protocol (Structural Subtyping)

Use when: Multiple unrelated classes share behavior but not inheritance.

```python
# Before: Any for duck-typed objects
def process(handler: Any) -> None:
    handler.handle(data)

# After: Protocol defines required interface
class Handler(Protocol):
    def handle(self, data: bytes) -> None: ...

def process(handler: Handler) -> None:
    handler.handle(data)
```

## Generic (Parameterized Types)

Use when: Container or function works with multiple types while preserving type info.

```python
# Before: Any loses type information
def first(items: list[Any]) -> Any:
    return items[0]

# After: Generic preserves type
T = TypeVar("T")
def first(items: list[T]) -> T:
    return items[0]
```

## TypeGuard (Type Narrowing)

Use when: Runtime check should narrow type for type checker.

```python
# Before: Type checker doesn't understand the check
def process(data: str | dict[str, Any]) -> None:
    if isinstance(data, dict):
        # data still str | dict here without TypeGuard

# After: TypeGuard narrows the type
def is_dict_response(data: str | dict[str, Any]) -> TypeGuard[dict[str, Any]]:
    return isinstance(data, dict)

def process(data: str | dict[str, Any]) -> None:
    if is_dict_response(data):
        # data is dict[str, Any] here
```

## TypeAlias (Named Types)

Use when: Complex type is repeated or needs documentation.

```python
# Before: Repeated complex type
def fetch(url: str) -> dict[str, str | int | list[str] | None]: ...
def parse(data: dict[str, str | int | list[str] | None]) -> Model: ...

# After: Named alias
JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
APIResponse: TypeAlias = dict[str, JSONValue]

def fetch(url: str) -> APIResponse: ...
def parse(data: APIResponse) -> Model: ...
```

## TypedDict (Dict Shape)

Use when: Dict has known keys with specific types.

```python
# Before: dict[str, Any]
def get_user() -> dict[str, Any]:
    return {"name": "Alice", "age": 30, "active": True}

# After: TypedDict defines shape
class User(TypedDict):
    name: str
    age: int
    active: bool

def get_user() -> User:
    return {"name": "Alice", "age": 30, "active": True}
```

## Dataclass / Pydantic

Use when: Need structured data with validation.

```python
# Before: Plain dict or untyped class
user = {"name": "Alice", "email": "alice@example.com"}

# After: Dataclass for internal data
@dataclass
class User:
    name: str
    email: str

# After: Pydantic for external/validated data
class UserInput(BaseModel):
    name: str
    email: EmailStr
```

## Library Modernization Reference

| Legacy     | Modern    | Benefit                           |
| ---------- | --------- | --------------------------------- |
| `requests` | `httpx`   | Async support, HTTP/2, type hints |
| `json`     | `orjson`  | 10x faster, better types          |
| `toml`     | `tomlkit` | Preserves formatting, comments    |
| `argparse` | `typer`   | Type-driven CLI, auto-help        |
| `print()`  | `rich`    | Formatted output, progress bars   |
| `curses`   | `textual` | Modern TUI framework              |
