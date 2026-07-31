# Name Definition and Resolution Errors

## name-defined: Check that name is defined

**Error Code**: `[name-defined]`

**Configuration**: Enabled by default

**Type Safety Principle**: All referenced names must have corresponding definitions to prevent NameError at runtime.

### What This Error Prevents

MyPy expects that all references to names have a corresponding definition in an active scope. This catches missing definitions, missing imports, and typos in function names.

### When This Is an Error

#### Calling non-existent functions

```python
x = sort([3, 2, 4])  # Error: Name "sort" is not defined [name-defined]
```

#### Using undefined variables

```python
result = undefined_variable + 5  # Error: Name "undefined_variable" is not defined [name-defined]
```

#### Typos in function names

```python
data = [3, 1, 4, 1, 5]
sorted_data = soted(data)  # Error: Name "soted" is not defined [name-defined]
```

#### Missing imports

```python
df = pd.DataFrame({"x": [1, 2, 3]})  # Error: Name "pd" is not defined [name-defined]
```

### When This Is NOT an Error

#### Properly defined variables

```python
x = 5
result = x + 10  # OK
```

#### Imported names

```python
from typing import List


def process(items: List[int]) -> int:
    return sum(items)  # OK - List is imported
```

#### Built-in names

```python
result = len([1, 2, 3])  # OK - len is built-in
value = max([1, 5, 3])  # OK - max is built-in
```

### Examples of Error-Producing Code

```python
# Missing import
from datetime import datetime

timestamp = datetime.now()
formatted = timestamp.format_date()  # Error: might work if method exists


# Typo in name
def calculate_sum(numbers):
    return summ(numbers)  # Error: Name "summ" is not defined [name-defined]


# Forward reference without import
def process():
    return load_data()  # Error if load_data not defined yet


# Undefined class
obj = MyClass()  # Error: Name "MyClass" is not defined [name-defined]
```

### Examples of Corrected Code

```python
# Import the name
from datetime import datetime

timestamp = datetime.now()


# Fix typo
def calculate_sum(numbers):
    return sum(numbers)  # OK


# Define before use or import
def load_data():
    return {"key": "value"}


def process():
    return load_data()


# Import the class
from mymodule import MyClass

obj = MyClass()
```

### Configuration Options

This error is enabled by default and cannot be disabled. Suppress specific instances:

```python
# Type ignore for one line
result = undefined_name  # type: ignore[name-defined]
```

---

## used-before-def: Check variable not used before definition

**Error Code**: `[used-before-def]`

**Configuration**: Enabled by default

**Type Safety Principle**: Variables must be defined before use to prevent undefined behavior and runtime errors.

### What This Error Prevents

MyPy will generate an error if a name is used before it's defined. While `name-defined` checks for undefined names in general, `used-before-def` specifically catches cases where a variable is used and then defined later in the same scope.

### When This Is an Error

#### Using variable before assignment

```python
print(x)  # Error: Name "x" is used before definition [used-before-def]
x = 123
```

#### Using variable in function body before class definition

```python
def create_user(name: str) -> User:
    return User(name=name)  # Error: Name "User" is used before definition [used-before-def]


class User:
    def __init__(self, name: str):
        self.name = name
```

#### Using function before definition

```python
result = helper()  # Error: Name "helper" is used before definition [used-before-def]


def helper() -> int:
    return 42
```

### When This Is NOT an Error

#### Using function defined later (in function bodies only)

```python
def outer() -> int:
    def inner() -> int:
        return 42

    return inner()  # OK - inner defined earlier in the function


class MyClass:
    def method_a(self) -> int:
        return self.method_b()  # OK - method_b defined on class

    def method_b(self) -> int:
        return 10
```

#### Forward references in type annotations

```python
def process(value: "User") -> None:  # OK - string annotation
    ...


class User: ...
```

#### Type annotation with string forward reference

```python
from __future__ import annotations  # Allows forward references


def process(value: User) -> None:  # OK with __future__ import
    ...


class User: ...
```

### Examples of Error-Producing Code

```python
# Variable used before assignment
def calculate() -> int:
    total = sum(items)  # Error: Name "items" is used before definition [used-before-def]
    items = [1, 2, 3, 4, 5]
    return total


# Function called before definition
def run():
    return process_data()  # Error: Name "process_data" is used before definition [used-before-def]


def process_data():
    return [1, 2, 3]


# Exception from undefined variable in condition
def get_value():
    if flag:  # Error: Name "flag" is used before definition [used-before-def]
        return 1
    flag = True
    return 0
```

### Examples of Corrected Code

```python
# Define variable before use
def calculate() -> int:
    items = [1, 2, 3, 4, 5]
    total = sum(items)  # OK
    return total


# Define function before use (at module level)
def process_data():
    return [1, 2, 3]


def run():
    return process_data()  # OK


# Or import from typing for forward references
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import User


def process(user: User) -> None:  # OK in TYPE_CHECKING block
    ...
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
# Use forward reference in quotes
def func(value: "UndefinedClass") -> None: ...


# Or import TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from module import UndefinedClass
```

---

## no-redef: Check each name defined once

**Error Code**: `[no-redef]`

**Configuration**: Enabled by default

**Type Safety Principle**: Multiple definitions of the same name in a namespace create ambiguity about which definition is being referenced.

### What This Error Prevents

MyPy generates an error if you have multiple definitions for a name in the same namespace. The reason is that this is often an error, as the second definition may overwrite the first one. Also, MyPy often can't determine whether references point to the first or the second definition, which compromises type checking.

If you silence this error, all references to the defined name refer to the first definition.

### When This Is an Error

#### Redefining a class

```python
class A:
    def __init__(self, x: int) -> None: ...


class A:  # Error: Name "A" already defined on line 1 [no-redef]
    def __init__(self, x: str) -> None: ...


# MyPy uses first definition
A("x")  # Error: Argument 1 to "A" has incompatible type "str"; expected "int"
```

#### Redefining a function

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"


def greet(name: str, greeting: str = "Hi") -> str:  # Error: Name "greet" already defined [no-redef]
    return f"{greeting}, {name}!"
```

#### Redefining a variable

```python
x = 5
x = "string"  # Error: Name "x" already defined [no-redef]
```

### When This Is NOT an Error

#### Type narrowing assignments (within control flow)

```python
x = 5
if some_condition:
    x = "string"  # Reassignment in conditional, OK in Python semantics

# MyPy handles this with type narrowing
```

#### Conditional imports

```python
import platform

if platform.system() == "Windows":
    import winreg as registry  # OK - conditional
else:
    import pathlib as registry  # OK - different condition

# Type refinement to common base
```

#### Function overloads with implementation

```python
from typing import overload


@overload
def func(value: int) -> int: ...


@overload
def func(value: str) -> str: ...


def func(value):  # OK - implementation of overload
    return value
```

### Examples of Error-Producing Code

```python
# Accidental duplicate class
class User:
    def authenticate(self) -> bool:
        return True


class User:  # Error: Name "User" already defined [no-redef]
    def authenticate(self) -> bool:
        return False


# Duplicate function with signature change
def process(data: list) -> list:
    return sorted(data)


def process(data: list, reverse: bool = False) -> list:  # Error: already defined [no-redef]
    return sorted(data, reverse=reverse)
```

### Examples of Corrected Code

```python
# Use different names if both definitions needed
class User:
    def authenticate(self) -> bool:
        return True


class AdminUser:  # Different name
    def authenticate(self) -> bool:
        return False


# Or update the single definition
def process(data: list, reverse: bool = False) -> list:
    return sorted(data, reverse=reverse)


# For overloads, use @overload decorator
from typing import overload


@overload
def func(value: int) -> int: ...


@overload
def func(value: str) -> str: ...


def func(value: int | str) -> int | str:  # Single implementation
    return value
```

### Configuration Options

This error is enabled by default and cannot be disabled. Suppress specific instances:

```python
# Type ignore for the redefinition
class A: ...


class A:  # type: ignore[no-redef]
    ...
```
