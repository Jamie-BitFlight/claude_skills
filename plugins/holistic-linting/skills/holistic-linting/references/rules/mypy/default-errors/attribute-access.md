# Attribute and Member Access Errors

## attr-defined: Check that attribute exists

**Error Code**: `[attr-defined]`

**Configuration**: Enabled by default

**Type Safety Principle**: Attributes must be defined before use to prevent AttributeError at runtime.

### What This Error Prevents

MyPy checks that an attribute is defined in the target class or module when using the dot operator. This applies to both getting and setting attributes. New attributes are defined by assignments in the class body or assignments to `self.x` in methods.

### When This Is an Error

#### Accessing undefined instance attributes

```python
class Resource:
    def __init__(self, name: str) -> None:
        self.name = name


r = Resource("x")
print(r.name)  # OK
print(r.id)  # Error: "Resource" has no attribute "id" [attr-defined]
r.id = 5  # Error: "Resource" has no attribute "id" [attr-defined]
```

#### Importing non-existent module attributes

```python
# Error: Module "os" has no attribute "non_existent" [attr-defined]
from os import non_existent
```

#### Accessing attributes on third-party libraries without type information

```python
import untyped_library

x = untyped_library.some_function()
y = x.undefined_attr  # May produce [attr-defined] error
```

### When This Is NOT an Error

#### Legitimate attribute initialization in methods

```python
class Resource:
    def __init__(self, name: str) -> None:
        self.name = name  # OK - attribute defined

    def set_description(self, desc: str) -> None:
        self.description = desc  # OK - attribute defined in method


r = Resource("test")
r.set_description("My resource")  # OK
```

#### Using typed attributes with explicit type hints

```python
from typing import Optional


class Resource:
    name: str
    description: Optional[str]

    def __init__(self, name: str) -> None:
        self.name = name
        self.description = None
```

### Examples of Error-Producing Code

```python
class Car:
    def __init__(self, make: str) -> None:
        self.make = make


car = Car("Toyota")
print(car.model)  # Error: "Car" has no attribute "model" [attr-defined]
car.color = "red"  # Error: "Car" has no attribute "color" [attr-defined]

# Also applies to modules:
from typing import Any
from unknown_module import something  # May error if not found

# And wrong attribute names:
import json

data = json.loads("{}")
result = data.validate()  # Error if validate doesn't exist on dict
```

### Examples of Corrected Code

```python
class Car:
    def __init__(self, make: str, model: str, color: str) -> None:
        self.make = make
        self.model = model
        self.color = color


car = Car("Toyota", "Camry", "red")
print(car.model)  # OK
print(car.color)  # OK

# Or with explicit type annotations:
from typing import Optional


class Car:
    make: str
    model: str
    color: Optional[str]

    def __init__(self, make: str, model: str) -> None:
        self.make = make
        self.model = model
        self.color = None


car = Car("Toyota", "Camry")
car.color = "red"  # OK
```

### Configuration Options

This error is enabled by default and cannot be disabled directly. However, you can suppress specific instances:

```python
# Suppress for one line
x = obj.undefined  # type: ignore[attr-defined]


# Suppress for a block
# mypy: disable-error-code="attr-defined"
class MyClass: ...


# mypy: enable-error-code="attr-defined"
```

---

## union-attr: Check attribute exists in each union item

**Error Code**: `[union-attr]`

**Configuration**: Enabled by default

**Type Safety Principle**: Union types require attributes to exist on all possible types in the union to prevent runtime errors.

### What This Error Prevents

If you access an attribute of a value with a union type, MyPy checks that the attribute is defined for every type in that union. Otherwise the operation can fail at runtime. This also applies to optional types (which are `Type | None`).

### When This Is an Error

#### Accessing union attributes not present on all types

```python
class Cat:
    def sleep(self) -> None: ...
    def miaow(self) -> None: ...


class Dog:
    def sleep(self) -> None: ...
    def follow_me(self) -> None: ...


def func(animal: Cat | Dog) -> None:
    # OK: 'sleep' is defined for both Cat and Dog
    animal.sleep()
    # Error: Item "Cat" of "Cat | Dog" has no attribute "follow_me" [union-attr]
    animal.follow_me()
```

#### Accessing attributes on optional types

```python
class User:
    def greet(self) -> str:
        return "hello"


def process(user: User | None) -> str:
    # Error: Item "None" of "User | None" has no attribute "greet" [union-attr]
    return user.greet()
```

### When This Is NOT an Error

#### Narrowing the type with isinstance checks

```python
class Cat:
    def sleep(self) -> None: ...
    def miaow(self) -> None: ...


class Dog:
    def sleep(self) -> None: ...
    def follow_me(self) -> None: ...


def func(animal: Cat | Dog) -> None:
    animal.sleep()  # OK

    if isinstance(animal, Dog):
        animal.follow_me()  # OK - type narrowed to Dog
```

#### Checking for None with type guards

```python
class User:
    def greet(self) -> str:
        return "hello"


def process(user: User | None) -> str:
    if user is None:
        return "no user"
    return user.greet()  # OK - type narrowed to User
```

### Examples of Error-Producing Code

```python
from typing import Union


class Circle:
    def get_radius(self) -> float: ...


class Square:
    def get_side(self) -> float: ...


def get_area(shape: Circle | Square) -> float:
    # Error: Item "Square" of "Circle | Square" has no attribute "get_radius" [union-attr]
    return 3.14159 * shape.get_radius() ** 2


def greet(person: object | None) -> None:
    # Error: Item "None" of "object | None" has no attribute "say_hello" [union-attr]
    person.say_hello()
```

### Examples of Corrected Code

```python
from typing import Union


class Circle:
    def __init__(self, radius: float):
        self.radius = radius


class Square:
    def __init__(self, side: float):
        self.side = side


def get_area(shape: Circle | Square) -> float:
    if isinstance(shape, Circle):
        return 3.14159 * shape.radius**2
    else:
        return shape.side**2


def greet(person: object | None) -> None:
    if person is not None and hasattr(person, "say_hello"):
        person.say_hello()


# Or use common interface:
from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...


class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14159 * self.radius**2


class Square(Shape):
    def __init__(self, side: float):
        self.side = side

    def area(self) -> float:
        return self.side**2


def get_area(shape: Shape) -> float:
    return shape.area()  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
# Suppress for one line
animal.follow_me()  # type: ignore[union-attr]

# Use type assertion to narrow type
from typing import cast

dog = cast(Dog, animal)
dog.follow_me()  # OK
```

---

## has-type: Check that type of target is known

**Error Code**: `[has-type]`

**Configuration**: Enabled by default

**Type Safety Principle**: Variable types must be determinable during static analysis to ensure safe type checking.

### What This Error Prevents

MyPy sometimes generates this error when it hasn't inferred any type for a variable being referenced. This typically happens for:

- References to variables initialized later in the source file
- References across modules that form an import cycle
- Variables in complex control flow that prevent type inference

### When This Is an Error

#### Referencing variables defined later

```python
class Problem:
    def set_x(self) -> None:
        # Error: Cannot determine type of "y" [has-type]
        self.x = self.y

    def set_y(self) -> None:
        self.y = self.x
```

#### Circular imports

```python
# module_a.py
from module_b import process

value = process()  # Error if module_b imports from module_a

# module_b.py
from module_a import value


def process():
    return value * 2
```

### When This Is NOT an Error

#### Explicit type annotations prevent the error

```python
class Problem:
    def set_x(self) -> None:
        self.x = self.y  # OK with annotation

    def set_y(self) -> None:
        self.y: int = self.x  # Annotation here resolves circular reference
```

#### Variables defined before use

```python
def process() -> int:
    x = get_value()  # OK - type is inferred
    return x * 2


def get_value() -> int:
    return 42
```

### Examples of Error-Producing Code

```python
class DataProcessor:
    def process(self) -> None:
        # Error: Cannot determine type of "cache" [has-type]
        self.data = self.cache

    def init_cache(self) -> None:
        self.cache = {}
```

### Examples of Corrected Code

```python
from typing import Dict, Any


class DataProcessor:
    cache: Dict[str, Any]

    def process(self) -> None:
        self.data = self.cache  # OK - cache type is known

    def init_cache(self) -> None:
        self.cache = {}
```

### Configuration Options

This error is enabled by default and typically appears only in complex codebases. Suppress specific instances:

```python
# Type annotation solution (preferred)
self.x: Any = self.y

# Or use explicit type annotation
from typing import Optional

self.y: Optional[int] = None
```
