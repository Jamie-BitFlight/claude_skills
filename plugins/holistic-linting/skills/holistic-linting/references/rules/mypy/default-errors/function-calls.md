# Function Call and Return Errors

## call-arg: Check arguments in calls

**Error Code**: `[call-arg]`

**Configuration**: Enabled by default

**Type Safety Principle**: Function calls must match the declared function signature in terms of argument count and names.

### What This Error Prevents

MyPy expects that the number and names of arguments match the called function. Note that argument type checks have a separate error code `arg-type`.

### When This Is an Error

#### Too many arguments

```python
def greet(name: str) -> None:
    print("hello", name)


greet("jack")  # OK
greet("jill", "jack")  # Error: Too many arguments for "greet" [call-arg]
```

#### Too few arguments

```python
def process(x: int, y: int) -> int:
    return x + y


result = process(5)  # Error: Missing positional argument "y" for "process" [call-arg]
```

#### Unexpected keyword argument

```python
def calculate(value: int) -> int:
    return value * 2


result = calculate(value=5, factor=2)  # Error: Unexpected keyword argument "factor" [call-arg]
```

### When This Is NOT an Error

#### Correct argument count

```python
def greet(name: str) -> None:
    print("hello", name)


greet("jack")  # OK
greet(name="jill")  # OK
```

#### Default arguments

```python
def process(x: int, y: int = 10) -> int:
    return x + y


result = process(5)  # OK - y has default value
result = process(5, 20)  # OK - y provided explicitly
```

#### Variable arguments

```python
def sum_all(*values: int) -> int:
    return sum(values)


total = sum_all(1, 2, 3, 4, 5)  # OK
```

### Examples of Error-Producing Code

```python
def register(name: str, email: str) -> None: ...


# Error: Missing positional argument "email"
register("Alice")

# Error: Too many arguments
register("Bob", "bob@example.com", "extra")

# Error: Unexpected keyword argument
register("Charlie", email="charlie@example.com", verified=True)
```

### Examples of Corrected Code

```python
def register(name: str, email: str, verified: bool = False) -> None: ...


register("Alice", "alice@example.com")  # OK
register("Bob", "bob@example.com", True)  # OK
register("Charlie", email="charlie@example.com", verified=True)  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
greet("jill", "jack")  # type: ignore[call-arg]
```

---

## arg-type: Check argument types

**Error Code**: `[arg-type]`

**Configuration**: Enabled by default

**Type Safety Principle**: Argument types in function calls must match the declared parameter types.

### What This Error Prevents

MyPy checks that argument types in a call match the declared argument types in the signature of the called function.

### When This Is an Error

#### Passing incompatible types

```python
def first(x: list[int]) -> int:
    return x[0] if x else 0


t = (5, 4)
# Error: Argument 1 to "first" has incompatible type "tuple[int, int]";
#        expected "list[int]" [arg-type]
print(first(t))
```

#### Wrong type for parameter

```python
def process(value: str) -> str:
    return value.upper()


# Error: Argument 1 to "process" has incompatible type "int"; expected "str" [arg-type]
result = process(42)
```

### When This Is NOT an Error

#### Correct types

```python
def first(x: list[int]) -> int:
    return x[0] if x else 0


t = [5, 4]
print(first(t))  # OK
```

#### Subclass instances passed to superclass parameters

```python
class Animal:
    pass


class Dog(Animal):
    pass


def process(animal: Animal) -> None: ...


dog = Dog()
process(dog)  # OK - Dog is a subclass of Animal
```

#### Union types containing the argument type

```python
def process(value: int | str) -> None: ...


process(42)  # OK
process("text")  # OK
```

### Examples of Error-Producing Code

```python
def divide(x: float, y: float) -> float:
    return x / y


# Error: Argument 2 has incompatible type "str"; expected "float" [arg-type]
result = divide(10, "2")


def greet(user: dict) -> str:
    # Error: Argument has incompatible type "list"; expected "dict" [arg-type]
    return greet([1, 2, 3])
```

### Examples of Corrected Code

```python
def divide(x: float, y: float) -> float:
    return x / y


result = divide(10.0, 2.0)  # OK
result = divide(10, 2)  # OK - int is compatible with float


def greet(user: dict) -> str:
    return f"Hello {user['name']}"


greet({"name": "Alice"})  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
result = process(42)  # type: ignore[arg-type]
```

---

## call-overload: Check calls to overloaded functions

**Error Code**: `[call-overload]`

**Configuration**: Enabled by default

**Type Safety Principle**: Calls to overloaded functions must match at least one declared overload signature.

### What This Error Prevents

When you call an overloaded function, MyPy checks that at least one of the signatures of the overload items match the argument types in the call.

### When This Is an Error

#### No matching overload

```python
from typing import overload


@overload
def inc_maybe(x: None) -> None: ...


@overload
def inc_maybe(x: int) -> int: ...


def inc_maybe(x: int | None) -> int | None:
    if x is None:
        return None
    else:
        return x + 1


inc_maybe(None)  # OK
inc_maybe(5)  # OK

# Error: No overload variant of "inc_maybe" matches argument type "float" [call-overload]
inc_maybe(1.2)
```

### When This Is NOT an Error

#### Matching one of the overloads

```python
from typing import overload


@overload
def process(value: int) -> int: ...


@overload
def process(value: str) -> str: ...


def process(value):
    return value if isinstance(value, str) else value * 2


process(5)  # OK - matches first overload
process("text")  # OK - matches second overload
```

### Examples of Error-Producing Code

```python
from typing import overload


@overload
def transform(x: list[int]) -> int: ...


@overload
def transform(x: str) -> str: ...


def transform(x):
    return sum(x) if isinstance(x, list) else x.upper()


# Error: No overload variant matches argument type "dict" [call-overload]
transform({"key": "value"})
```

### Examples of Corrected Code

```python
from typing import overload


@overload
def transform(x: list[int]) -> int: ...


@overload
def transform(x: str) -> str: ...


def transform(x):
    return sum(x) if isinstance(x, list) else x.upper()


result1 = transform([1, 2, 3])  # OK
result2 = transform("hello")  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
transform({"key": "value"})  # type: ignore[call-overload]
```

---

## return: Check function returns value

**Error Code**: `[return]`

**Configuration**: Enabled by default

**Type Safety Principle**: Functions with non-None return types must explicitly return a value on all code paths.

### What This Error Prevents

If a function has a non-None return type, MyPy expects that the function always explicitly returns a value (or raises an exception). The function should not fall off the end, as this is often a bug.

### When This Is an Error

#### Missing return statement

```python
# Error: Missing return statement [return]
def show(x: int) -> int:
    print(x)


# Error: Missing return statement [return]
def pred1(x: int) -> int:
    if x > 0:
        return x - 1
```

#### Conditional return not covering all paths

```python
# Error: Missing return statement [return]
def get_status(value: int) -> str:
    if value > 0:
        return "positive"
    elif value < 0:
        return "negative"
    # Missing case for value == 0
```

### When This IS an Error (Correctly Allowed)

#### Returns None explicitly

```python
def process(x: int) -> None:
    print(x)  # OK - return type is None
```

#### All code paths return or raise

```python
def pred2(x: int) -> int:
    if x > 0:
        return x - 1
    else:
        raise ValueError("not defined for zero")  # OK - raises exception
```

#### Unreachable code after return

```python
def get_value() -> int:
    return 42
    print("unreachable")  # OK - after return
```

### Examples of Error-Producing Code

```python
# Error: Missing return statement
def max_value(items: list[int]) -> int:
    if items:
        return max(items)
    # Doesn't return for empty list


# Error: Missing return statement
def validate_age(age: int) -> bool:
    if age >= 18:
        return True
    # Doesn't handle age < 18
```

### Examples of Corrected Code

```python
# Add default return
def max_value(items: list[int]) -> int:
    if items:
        return max(items)
    return 0


# Handle all cases
def validate_age(age: int) -> bool:
    if age >= 18:
        return True
    return False


# Or use shorter form
def validate_age(age: int) -> bool:
    return age >= 18
```

### Configuration Options

This error is enabled by default. To allow missing returns (not recommended):

```python
# Use type: ignore
def process(x: int) -> int:  # type: ignore[return]
    if x > 0:
        return x
```

---

## return-value: Check return value compatibility

**Error Code**: `[return-value]`

**Configuration**: Enabled by default

**Type Safety Principle**: Returned values must match the declared return type.

### What This Error Prevents

MyPy checks that the returned value is compatible with the type signature of the function.

### When This Is an Error

#### Wrong return type

```python
def func(x: int) -> str:
    # Error: Incompatible return value type (got "int", expected "str") [return-value]
    return x + 1
```

#### Union type mismatch

```python
def process(flag: bool) -> int | None:
    if flag:
        return 42
    # Error: Incompatible return value type (got "str", expected "int | None") [return-value]
    return "error"
```

### When This IS NOT an Error

#### Correct type

```python
def func(x: int) -> str:
    return str(x + 1)  # OK
```

#### Subclass return type (covariant)

```python
class Animal:
    pass


class Dog(Animal):
    pass


def get_pet() -> Animal:
    return Dog()  # OK - Dog is subclass of Animal
```

### Examples of Error-Producing Code

```python
def get_count() -> int:
    # Error: Incompatible return value type (got "str", expected "int") [return-value]
    return "42"


def process(data: list) -> dict:
    # Error: Incompatible return value type (got "list", expected "dict") [return-value]
    return data
```

### Examples of Corrected Code

```python
def get_count() -> int:
    return int("42")  # OK


def process(data: list) -> list:
    return data  # OK - type matches


# Or convert to dict
def process_to_dict(data: list) -> dict:
    return {"items": data}  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
def func(x: int) -> str:
    return x + 1  # type: ignore[return-value]
```

---

## empty-body: Check functions have non-empty bodies

**Error Code**: `[empty-body]`

**Configuration**: Enabled by default

**Type Safety Principle**: Functions with declared return types should have implementations, not just pass statements.

### What This Error Prevents

This error code is similar to `[return]` but is emitted specifically for functions and methods with empty bodies (if they are annotated with non-trivial return type).

### When This IS an Error

#### Empty function body with return type

```python
def process(x: int) -> int:
    pass  # Error: Missing return statement [empty-body]


def calculate() -> str: ...  # Error: Missing return statement [empty-body]
```

### When This IS NOT an Error

#### Abstract methods

```python
from abc import abstractmethod


class Base:
    @abstractmethod
    def foo(self) -> int:
        pass  # OK - abstract method


class Derived(Base):
    def foo(self) -> int:
        pass  # Error: Missing return statement [empty-body]
```

#### Protocol methods

```python
from typing import Protocol


class Compute(Protocol):
    def process(self) -> int:
        pass  # OK - in Protocol


class Implementation(Compute):
    def process(self) -> int:
        pass  # Error: Missing return statement [empty-body]
```

### Examples of Error-Producing Code

```python
# Error: Missing return statement [empty-body]
def get_data() -> dict: ...


# Error: Missing return statement [empty-body]
def validate(value: int) -> bool:
    pass
```

### Examples of Corrected Code

```python
from abc import abstractmethod


# For abstract methods
class Base:
    @abstractmethod
    def get_data(self) -> dict: ...


# For actual implementation
def get_data() -> dict:
    return {}


def validate(value: int) -> bool:
    return value > 0
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
def get_data() -> dict:
    pass  # type: ignore[empty-body]
```

---

## func-returns-value: Check called function returns value

**Error Code**: `[func-returns-value]`

**Configuration**: Enabled by default

**Type Safety Principle**: Functions with None return type should have their return value ignored.

### What This Error Prevents

MyPy reports an error if you call a function with a `None` return type and don't ignore the return value, as this is usually a programming error.

### When This IS an Error

#### Using return value from None-returning function

```python
def f() -> None: ...


# Error: "f" does not return a value (it only ever returns None) [func-returns-value]
if f():
    print("not false")

result = f()  # Error: assigned value of None is usually not needed
```

### When THIS IS NOT an Error

#### Not using the return value

```python
def f() -> None: ...


f()  # OK - we don't do anything with the return value
```

#### Function actually returns non-None

```python
def f() -> str:
    return "value"


if f():  # OK - returns str
    print("not false")
```

### Examples of Error-Producing Code

```python
def log(message: str) -> None:
    print(message)


# Error: does not return a value [func-returns-value]
status = log("hello")

# Error: does not return a value [func-returns-value]
if log("error"):
    handle_error()
```

### Examples of Corrected Code

```python
def log(message: str) -> None:
    print(message)


log("hello")  # OK - don't use return value


# Or make function return a value
def log_and_get_length(message: str) -> int:
    print(message)
    return len(message)


length = log_and_get_length("hello")  # OK
```

### Configuration Options

This error is enabled by default. Suppress specific instances:

```python
result = f()  # type: ignore[func-returns-value]
```
