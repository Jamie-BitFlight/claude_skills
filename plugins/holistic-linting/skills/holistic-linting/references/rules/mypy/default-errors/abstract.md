# Abstract Classes and Instantiation Errors

## abstract: Check instantiation of abstract classes

**Error Code**: `[abstract]`

**Configuration**: Enabled by default

**Type Safety Principle**: Abstract classes with unimplemented methods cannot be instantiated.

### When This Is an Error

```python
from abc import ABCMeta, abstractmethod


class Persistent(metaclass=ABCMeta):
    @abstractmethod
    def save(self) -> None: ...


class Thing(Persistent):
    def __init__(self) -> None: ...

    # Missing "save" method implementation


# Error: Cannot instantiate abstract class "Thing" with abstract attribute "save" [abstract]
t = Thing()
```

### Examples of Corrected Code

```python
from abc import ABCMeta, abstractmethod


class Persistent(metaclass=ABCMeta):
    @abstractmethod
    def save(self) -> None: ...


class Thing(Persistent):
    def __init__(self) -> None: ...

    def save(self) -> None:  # OK - implementation provided
        print("Saving...")


t = Thing()  # OK
```

### Configuration Options

Suppress specific instances:

```python
t = Thing()  # type: ignore[abstract]
```

---

## type-abstract: Safe handling of abstract type objects

**Error Code**: `[type-abstract]`

**Configuration**: Enabled by default

**Type Safety Principle**: Abstract types should not be passed where concrete type objects are expected.

### When This Is an Error

```python
from abc import ABCMeta, abstractmethod


class Config(metaclass=ABCMeta):
    @abstractmethod
    def get_value(self, attr: str) -> str: ...


def make_many[T](typ: type[T], n: int) -> list[T]:
    return [typ() for _ in range(n)]  # This will raise if typ is abstract


# Error: Only concrete class can be given where "type[Config]" is expected [type-abstract]
make_many(Config, 5)
```

### Examples of Corrected Code

```python
from abc import ABCMeta, abstractmethod


class Config(metaclass=ABCMeta):
    @abstractmethod
    def get_value(self, attr: str) -> str: ...


class ConcreteConfig(Config):
    def get_value(self, attr: str) -> str:
        return f"value_{attr}"


def make_many[T](typ: type[T], n: int) -> list[T]:
    return [typ() for _ in range(n)]


configs = make_many(ConcreteConfig, 5)  # OK
```

### Configuration Options

Suppress specific instances:

```python
make_many(Config, 5)  # type: ignore[type-abstract]
```

---

## safe-super: Check abstract method calls via super

**Error Code**: `[safe-super]`

**Configuration**: Enabled by default

**Type Safety Principle**: Abstract methods without implementations cannot be safely called via super().

### When This Is an Error

```python
from abc import abstractmethod


class Base:
    @abstractmethod
    def foo(self) -> int: ...


class Sub(Base):
    def foo(self) -> int:
        # Error: Call to abstract method "foo" of "Base" with trivial body via super() is unsafe [safe-super]
        return super().foo() + 1


Sub().foo()  # This will crash at runtime
```

### When THIS IS NOT an Error

#### Base class provides implementation

```python
from abc import abstractmethod


class Base:
    @abstractmethod
    def foo(self) -> int:
        return 10  # Has implementation


class Sub(Base):
    def foo(self) -> int:
        return super().foo() + 1  # OK - base has implementation
```

### Examples of Corrected Code

```python
from abc import abstractmethod


class Base:
    @abstractmethod
    def foo(self) -> int:
        return 0  # Provide default implementation


class Sub(Base):
    def foo(self) -> int:
        return super().foo() + 1  # OK - base has implementation


print(Sub().foo())  # OK - will execute
```

### Configuration Options

Suppress specific instances:

```python
class Sub(Base):
    def foo(self) -> int:
        return super().foo() + 1  # type: ignore[safe-super]
```
