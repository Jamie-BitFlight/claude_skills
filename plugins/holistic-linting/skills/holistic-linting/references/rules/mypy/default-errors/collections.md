# Collection and Container Operation Errors

## index: Check indexing operations

**Error Code**: `[index]`

**Configuration**: Enabled by default

**Type Safety Principle**: Index values must match the container's expected key type.

### When This Is an Error

```python
a = {"x": 1, "y": 2}
a["x"]  # OK

# Error: Invalid index type "int" for "dict[str, int]"; expected type "str" [index]
print(a[1])

# Error: Invalid index type "bytes" for "dict[str, int]"; expected type "str" [index]
a[b"x"] = 4
```

### Examples of Corrected Code

```python
a = {"x": 1, "y": 2}
print(a["x"])  # OK
a["z"] = 3  # OK

items = [1, 2, 3]
print(items[0])  # OK
print(items[-1])  # OK
```

### Configuration Options

Suppress specific instances:

```python
print(a[1])  # type: ignore[index]
```

---

## list-item: Check list items

**Error Code**: `[list-item]`

**Configuration**: Enabled by default

**Type Safety Principle**: List items must match the declared list type.

### When This Is an Error

```python
# Error: List item 0 has incompatible type "int"; expected "str" [list-item]
a: list[str] = [0]
```

### Examples of Corrected Code

```python
a: list[str] = ["a", "b", "c"]  # OK
items: list[int] = [1, 2, 3]  # OK
```

### Configuration Options

Suppress specific instances:

```python
a: list[str] = [0]  # type: ignore[list-item]
```

---

## dict-item: Check dict items

**Error Code**: `[dict-item]`

**Configuration**: Enabled by default

**Type Safety Principle**: Dictionary keys and values must match declared types.

### When This Is an Error

```python
# Error: Dict entry 0 has incompatible type "str": "str"; expected "str": "int" [dict-item]
d: dict[str, int] = {"key": "value"}
```

### Examples of Corrected Code

```python
d: dict[str, int] = {"key": 1}  # OK
d: dict[str, str] = {"key": "value"}  # OK
```

### Configuration Options

Suppress specific instances:

```python
d: dict[str, int] = {"key": "value"}  # type: ignore[dict-item]
```

---

## typeddict-item: Check TypedDict items

**Error Code**: `[typeddict-item]`

**Configuration**: Enabled by default

**Type Safety Principle**: TypedDict items must match declared field types.

### When This Is an Error

```python
from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


# Error: Incompatible types (expression has type "float",
#        TypedDict item "x" has type "int") [typeddict-item]
p: Point = {"x": 1.2, "y": 4}
```

### Examples of Corrected Code

```python
from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


p: Point = {"x": 1, "y": 4}  # OK
```

### Configuration Options

Suppress specific instances:

```python
p: Point = {"x": 1.2, "y": 4}  # type: ignore[typeddict-item]
```

---

## typeddict-unknown-key: Check TypedDict keys

**Error Code**: `[typeddict-unknown-key]`

**Configuration**: Enabled by default

**Type Safety Principle**: TypedDict construction must use only declared keys.

### When This Is an Error

```python
from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


# Error: Extra key "z" for TypedDict "Point" [typeddict-unknown-key]
add_x_coordinates(a, {"x": 1, "y": 4, "z": 5})

a: Point = {"x": 1, "y": 2}
# Error: Extra key "z" for TypedDict "Point" [typeddict-unknown-key]
a["z"] = 3
```

### Examples of Corrected Code

```python
from typing import TypedDict


class Point(TypedDict):
    x: int
    y: int


p: Point = {"x": 1, "y": 2}  # OK
p["x"] = 5  # OK

# For dynamic keys, use dict instead
config: dict[str, int] = {"x": 1, "y": 2, "z": 3}  # OK
```

### Configuration Options

Suppress specific instances:

```python
a["z"] = 3  # type: ignore[typeddict-unknown-key]
```
