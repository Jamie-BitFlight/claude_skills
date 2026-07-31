# Assignment and Type Override Errors

## assignment: Check types in assignment statement

**Error Code**: `[assignment]`

**Configuration**: Enabled by default

**Type Safety Principle**: Assigned expressions must be compatible with assignment target types.

### What This Error Prevents

MyPy checks that the assigned expression is compatible with the assignment target (or targets).

### When This Is an Error

#### Wrong type assignment

```python
class Resource:
    def __init__(self, name: str) -> None:
        self.name = name


r = Resource("A")

r.name = "B"  # OK

# Error: Incompatible types in assignment (expression has type "int",
#        variable has type "str") [assignment]
r.name = 5
```

#### Assigning to wrong variable type

```python
x: int = 10
# Error: Incompatible types in assignment [assignment]
x = "string"
```

### When THIS IS NOT an Error

#### Compatible types

```python
x: int = 10
x = 20  # OK

name: str = "Alice"
name = "Bob"  # OK
```

#### Subclass assignment to superclass

```python
class Animal:
    pass


class Dog(Animal):
    pass


pet: Animal = Dog()  # OK - Dog is subclass of Animal
```

### Examples of Error-Producing Code

```python
items: list[int] = []
# Error: Incompatible types in assignment [assignment]
items = ["a", "b", "c"]

count: int = 0
# Error: Incompatible types in assignment [assignment]
count = "5"
```

### Examples of Corrected Code

```python
items: list[int] = []
items = [1, 2, 3]  # OK

items_str: list[str] = []
items_str = ["a", "b", "c"]  # OK

count: int = 0
count = 5  # OK

count_str: str = ""
count_str = "5"  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
r.name = 5  # type: ignore[assignment]
```

---

## method-assign: Check assignment target is not method

**Error Code**: `[method-assign]`

**Configuration**: Enabled by default

**Type Safety Principle**: Assigning to methods is ambiguous and should be avoided.

### What This Error Prevents

Assigning to a method on a class object or instance (monkey-patching) is ambiguous in terms of types. MyPy flags both assignments by default.

### When This IS an Error

#### Assigning to method

```python
class A:
    def f(self) -> None:
        pass

    def g(self) -> None:
        pass


def h(self: A) -> None:
    pass


A.f = h  # Error: Cannot assign to method "f" [method-assign]
A().f()
```

### When THIS IS NOT an Error

#### Assigning to non-method attribute

```python
class A:
    x = 5


A.x = 10  # OK - x is an attribute, not a method
```

### Examples of Error-Producing Code

```python
class Calculator:
    def add(self, x: int, y: int) -> int:
        return x + y


def new_add(self, a: float, b: float) -> float:
    return a + b


# Error: Cannot assign to method [method-assign]
Calculator.add = new_add
```

### Examples of Corrected Code

```python
# Use inheritance instead
class Calculator:
    def add(self, x: int, y: int) -> int:
        return x + y


class AdvancedCalculator(Calculator):
    def add(self, x: int | float, y: int | float) -> int | float:
        return x + y  # OK - override in subclass


# Or use composition
class Calculator:
    def add(self, x: int, y: int) -> int:
        return x + y


class AdvancedCalculator:
    def __init__(self):
        self.calc = Calculator()

    def add(self, x: float, y: float) -> float:
        return x + y
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
A.f = h  # type: ignore[method-assign]
```

---

## override: Check validity of overrides

**Error Code**: `[override]`

**Configuration**: Enabled by default

**Type Safety Principle**: Overridden methods must follow Liskov substitution principle.

### What This Error Prevents

MyPy checks that an overridden method or attribute is compatible with the base class. A method in a subclass must accept all arguments that the base class method accepts, and the return type must conform to the return type in the base class.

### When This IS an Error

#### Incompatible argument type

```python
class Base:
    def method(self, arg: int) -> int | None: ...


class DerivedBad(Base):
    # Error: Argument 1 of "method" is incompatible with "Base" [override]
    def method(self, arg: bool) -> int: ...
```

#### More specific return type (OK, covariant)

```python
class Base:
    def method(self, arg: int) -> int | None: ...


class Derived(Base):
    def method(self, arg: int) -> int:  # OK - more specific return type
        return 42
```

#### More general argument type (OK, contravariant)

```python
class Base:
    def method(self, arg: int) -> int | None: ...


class Derived(Base):
    def method(self, arg: int | str) -> int | None:  # OK - accepts more
        ...
```

### When THIS IS NOT an Error

#### Covariant return types

```python
class Animal:
    pass


class Dog(Animal):
    pass


class Provider:
    def get_pet(self) -> Animal:
        return Animal()


class DogProvider(Provider):
    def get_pet(self) -> Dog:  # OK - Dog is subclass of Animal
        return Dog()
```

#### Contravariant parameter types

```python
class Processor:
    def process(self, value: object) -> None: ...


class SpecificProcessor(Processor):
    def process(self, value: int) -> None:  # OK - accepts subset
        ...
```

### Examples of Error-Producing Code

```python
class Logger:
    def log(self, message: str) -> None:
        print(message)


class StrictLogger(Logger):
    # Error: Argument 1 of "log" is incompatible [override]
    def log(self, message: int) -> None:
        print(str(message))
```

### Examples of Corrected Code

```python
class Logger:
    def log(self, message: str) -> None:
        print(message)


class StrictLogger(Logger):
    def log(self, message: str) -> None:  # OK - matches signature
        print(f"LOG: {message}")


class FlexibleLogger(Logger):
    def log(self, message: object) -> None:  # OK - accepts more
        print(str(message))
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
class DerivedBad(Base):
    def method(self, arg: bool) -> int:  # type: ignore[override]
        ...
```

---

## typeddict-readonly-mutated: Check ReadOnly TypedDict not mutated

**Error Code**: `[typeddict-readonly-mutated]`

**Configuration**: Enabled by default

**Type Safety Principle**: ReadOnly-marked TypedDict fields must not be modified.

### What This Error Prevents

Prevents mutation of TypedDict fields marked as ReadOnly per PEP 705.

### When This IS an Error

#### Mutating ReadOnly field

```python
from datetime import datetime
from typing import TypedDict
from typing_extensions import ReadOnly


class User(TypedDict):
    username: ReadOnly[str]
    last_active: datetime


user: User = {"username": "foobar", "last_active": datetime.now()}
user["last_active"] = datetime.now()  # OK
# Error: ReadOnly TypedDict key "username" is mutated [typeddict-readonly-mutated]
user["username"] = "other"
```

### When THIS IS NOT an Error

#### Mutating non-ReadOnly fields

```python
from datetime import datetime
from typing import TypedDict
from typing_extensions import ReadOnly


class User(TypedDict):
    username: ReadOnly[str]
    last_active: datetime


user: User = {"username": "foobar", "last_active": datetime.now()}
user["last_active"] = datetime.now()  # OK - not ReadOnly
```

### Examples of Error-Producing Code

```python
from typing import TypedDict
from typing_extensions import ReadOnly


class Config(TypedDict):
    api_key: ReadOnly[str]
    timeout: int


config: Config = {"api_key": "secret", "timeout": 30}
# Error: ReadOnly key "api_key" is mutated [typeddict-readonly-mutated]
config["api_key"] = "new_secret"

config["timeout"] = 60  # OK - not ReadOnly
```

### Examples of Corrected Code

```python
from typing import TypedDict
from typing_extensions import ReadOnly


class Config(TypedDict):
    api_key: ReadOnly[str]
    timeout: int


config: Config = {"api_key": "secret", "timeout": 30}

# Only modify non-ReadOnly fields
config["timeout"] = 60  # OK

# Create new config for different API key
config = {"api_key": "new_secret", "timeout": 60}  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
user["username"] = "other"  # type: ignore[typeddict-readonly-mutated]
```
