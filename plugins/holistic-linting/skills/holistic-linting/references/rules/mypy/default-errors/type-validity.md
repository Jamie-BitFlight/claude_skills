# Type Annotation and Validity Errors

## valid-type: Check validity of types

**Error Code**: `[valid-type]`

**Configuration**: Enabled by default

**Type Safety Principle**: Type annotations must use actual types, not values or functions.

### What This Error Prevents

MyPy checks that each type annotation and any expression that represents a type is a valid type. Examples of valid types include classes, union types, callable types, type aliases, and literal types.

### When This Is an Error

#### Using function as a type

```python
def log(x: object) -> None:
    print("log:", repr(x))


# Error: Function "t.log" is not valid as a type [valid-type]
def log_all(objs: list[object], f: log) -> None:
    for x in objs:
        f(x)
```

#### Using variable as a type

```python
int_type = int


# Error: Variable "int_type" is not valid as a type [valid-type]
def process(value: int_type) -> None: ...
```

#### Using integer literal as type

```python
# Error: Integer literal is not valid as a type [valid-type]
def process(count: 5) -> None: ...
```

### When THIS IS NOT an Error

#### Using Callable for function types

```python
from collections.abc import Callable


def log_all(objs: list[object], f: Callable[[object], None]) -> None:
    for x in objs:
        f(x)  # OK
```

#### Using type aliases

```python
from typing import TypeAlias

UserId: TypeAlias = int


def get_user(user_id: UserId) -> None: ...  # OK
```

#### Using forward references for forward-declared types

```python
def create_user(data: dict) -> "User":
    return User(**data)


class User: ...  # OK with forward reference
```

### Examples of Error-Producing Code

```python
# Error: not valid as a type
class Processor:
    def handle(self, data: list) -> None: ...


processor = Processor()


# Error: processor is not a type
def execute(handler: processor) -> None: ...


# Error: integer is not a type
def repeat(x: 5) -> None: ...
```

### Examples of Corrected Code

```python
from typing import Callable, TypeAlias


# Use Callable for function types
def execute(handler: Callable[[Any], None]) -> None: ...


# Use type alias for complex types
Handler: TypeAlias = Callable[[Any], None]


def process(data: list, handler: Handler) -> None:
    handler(data)


# Use actual types
def repeat(count: int) -> None: ...
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
def log_all(objs: list[object], f: log) -> None:  # type: ignore[valid-type]
    ...
```

---

## var-annotated: Require annotation if variable type unclear

**Error Code**: `[var-annotated]`

**Configuration**: Enabled by default

**Type Safety Principle**: Variable types must be explicit when they cannot be inferred from initialization.

### What This Error Prevents

In some cases MyPy can't infer the type of a variable without an explicit annotation. MyPy treats this as an error, typically when you initialize a variable with an empty collection or `None`.

### When This Is an Error

#### Initializing with empty collection

```python
class Bundle:
    def __init__(self) -> None:
        # Error: Need type annotation for "items"
        # (hint: "items: list[] = ...") [var-annotated]
        self.items = []
```

#### Initializing with None

```python
def process() -> None:
    # Error: Need type annotation for "result" [var-annotated]
    result = None
    result = fetch_data()
```

### When THIS IS NOT an Error

#### Type is inferrable

```python
class Bundle:
    def __init__(self) -> None:
        self.items = [1, 2, 3]  # OK - type inferred as list[int]
```

#### Explicit annotation provided

```python
class Bundle:
    def __init__(self) -> None:
        self.items: list[str] = []  # OK


reveal_type(Bundle().items)  # list[str]
```

### Examples of Error-Producing Code

```python
# Error: Need type annotation
cache = {}

# Error: Need type annotation
result = None

# Error: Need type annotation
pending = []

# Error: Need type annotation
config = {}
```

### Examples of Corrected Code

```python
from typing import Optional, Dict, List

# Specify the types
cache: Dict[str, int] = {}
result: Optional[str] = None
pending: List[int] = []
config: Dict[str, str] = {}

# Or use modern syntax
cache: dict[str, int] = {}
result: str | None = None
pending: list[int] = []
config: dict[str, str] = {}
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
self.items = []  # type: ignore[var-annotated]

# Or use explicit annotation (preferred)
self.items: list = []
```

---

## metaclass: Check class metaclass validity

**Error Code**: `[metaclass]`

**Configuration**: Enabled by default

**Type Safety Principle**: Metaclasses must inherit from `type` and form a consistent class hierarchy.

### What This Error Prevents

MyPy checks whether the metaclass of a class is valid. The metaclass must be a subclass of `type`.

### When This Is an Error

#### Non-type metaclass

```python
class GoodMeta(type):
    pass


class BadMeta:
    pass


class A1(metaclass=GoodMeta):  # OK
    pass


class A2(metaclass=BadMeta):  # Error: Metaclasses not inheriting from "type" are not supported [metaclass]
    pass
```

### When THIS IS NOT an Error

#### Metaclass inherits from type

```python
class MyMeta(type):
    def __new__(mcs, name, bases, namespace):
        return super().__new__(mcs, name, bases, namespace)


class MyClass(metaclass=MyMeta):
    pass  # OK
```

### Examples of Error-Producing Code

```python
# Error: not a metaclass
class NotMeta:
    pass


class MyClass(metaclass=NotMeta):  # Error [metaclass]
    pass
```

### Examples of Corrected Code

```python
# Correct metaclass
class MyMeta(type):
    pass


class MyClass(metaclass=MyMeta):
    pass  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
class A2(metaclass=BadMeta):  # type: ignore[metaclass]
    pass
```

---

## valid-newtype: Check NewType target validity

**Error Code**: `[valid-newtype]`

**Configuration**: Enabled by default

**Type Safety Principle**: NewType must wrap a class type, not unions, Any, or other special types.

### What This Error Prevents

The target of a `NewType` definition must be a class type. It can't be a union type, `Any`, or various other special types.

### When This Is an Error

#### NewType with invalid target

```python
from typing import NewType

# Error: Argument 2 to NewType(...) must be subclassable (got "Any") [valid-newtype]
UserId = NewType("UserId", Any)

# Error: NewType target must be a subclass [valid-newtype]
Result = NewType("Result", int | None)
```

### When THIS IS NOT an Error

#### Valid NewType with class

```python
from typing import NewType

UserId = NewType("UserId", int)  # OK
Email = NewType("Email", str)  # OK
```

### Examples of Error-Producing Code

```python
from typing import NewType, Any

# Error: any is not subclassable
UserId = NewType("UserId", Any)

# Error: Union is not subclassable
Status = NewType("Status", str | int)
```

### Examples of Corrected Code

```python
from typing import NewType

# Use concrete types
UserId = NewType("UserId", int)
Email = NewType("Email", str)

# Or for unions, use classes
from typing import Union


class Status(str):
    pass


StatusId = NewType("StatusId", Status)
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
UserId = NewType("UserId", Any)  # type: ignore[valid-newtype]
```

---

## type-var: Check type variable values

**Error Code**: `[type-var]`

**Configuration**: Enabled by default

**Type Safety Principle**: Type variable values must respect their constraints and upper bounds.

### What This Error Prevents

MyPy checks that value of a type variable is compatible with a value restriction or the upper bound type.

### When This Is an Error

#### Type variable value out of bounds

```python
def add[T1: (int, float)](x: T1, y: T1) -> T1:  # Python 3.12 syntax
    return x + y


add(4, 5.5)  # OK

# Error: Value of type variable "T1" of "add" cannot be "str" [type-var]
add("x", "y")
```

### When THIS IS NOT an Error

#### Correct type variable usage

```python
def process[T: (int, str)](value: T) -> T:
    return value


process(42)  # OK - int is in constraint
process("text")  # OK - str is in constraint
```

### Examples of Error-Producing Code

```python
T = TypeVar("T", int, str)


def process(value: T) -> T:
    return value


# Error: Value of type variable "T" cannot be "float" [type-var]
process(3.14)
```

### Examples of Corrected Code

```python
from typing import TypeVar

T = TypeVar("T", int, str)


def process(value: T) -> T:
    return value


process(42)  # OK
process("text")  # OK


# Or for Python 3.12+
def process[T: (int, str)](value: T) -> T:
    return value


process(42)  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
add("x", "y")  # type: ignore[type-var]
```

---

## literal-required: Check that literal is used where expected

**Error Code**: `[literal-required]`

**Configuration**: Enabled by default

**Type Safety Principle**: Some contexts require literal values for static type checking.

### What This Error Prevents

There are some places where only a (string) literal value is expected for the purposes of static type checking, such as TypedDict keys or `__match_args__` items.

### When This Is an Error

#### Non-literal TypedDict key

```python
from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


def test(p: Point) -> None:
    key = "x"  # Inferred type of key is str
    # Error: TypedDict key must be a string literal [literal-required]
    p[key]
```

### When THIS IS NOT an Error

#### Using Literal or Final types

```python
from typing import Final, Literal, TypedDict


class Point(TypedDict):
    x: int
    y: int


def test(p: Point) -> None:
    X: Final = "x"
    p[X]  # OK

    Y: Literal["y"] = "y"
    p[Y]  # OK
```

### Examples of Error-Producing Code

```python
from typing import TypedDict


class Config(TypedDict):
    debug: bool
    level: str


def get_config(name: str) -> str:  # Error: non-literal key
    config: Config = {"debug": True, "level": "info"}
    return config[name]  # Error: key must be a string literal [literal-required]
```

### Examples of Corrected Code

```python
from typing import TypedDict, Literal


class Config(TypedDict):
    debug: bool
    level: str


def get_config(name: Literal["debug", "level"]) -> str:
    config: Config = {"debug": True, "level": "info"}
    return str(config[name])  # OK


# Or use literal directly
def get_debug(config: Config) -> bool:
    return config["debug"]  # OK - literal string
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
p[key]  # type: ignore[literal-required]
```
