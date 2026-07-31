# Operator and Expression Errors

## operator: Check uses of operators

**Error Code**: `[operator]`

**Configuration**: Enabled by default

**Type Safety Principle**: Operands must support the operation being performed.

### When This Is an Error

```python
# Error: Unsupported operand types for + ("int" and "str") [operator]
1 + "x"

# Error: Unsupported operand types for * ("str" and "list") [operator]
"text" * [1, 2, 3]
```

### Examples of Corrected Code

```python
1 + 2  # OK - both int
"text" + "more"  # OK - both str
[1, 2] + [3, 4]  # OK - both list

1 * 3  # OK
"text" * 3  # OK - str can repeat
```

### Configuration Options

Suppress specific instances:

```python
result = 1 + "x"  # type: ignore[operator]
```

---

## str-format: Check string formatting type-safety

**Error Code**: `[str-format]`

**Configuration**: Enabled by default

**Type Safety Principle**: String formatting must have correct placeholders and argument types.

### When This Is an Error

```python
# Error: Cannot find replacement for positional format specifier 1 [str-format]
"{} and {}".format("spam")

# Error: Not all arguments converted during string formatting [str-format]
"{} and {}".format("spam", "eggs", "cheese")

# Error: Incompatible types in string interpolation [str-format]
"{:d}".format(3.14)  # int format, float value
```

### Examples of Corrected Code

```python
"{} and {}".format("spam", "eggs")  # OK

# f-strings with correct types
value: int = 42
f"Value is {value}"  # OK

# Correct format specifiers
"{:f}".format(3.14)  # OK - float format for float
"{:d}".format(42)  # OK - int format for int
```

### Configuration Options

Suppress specific instances:

```python
"{} and {}".format("spam")  # type: ignore[str-format]
```

---

## str-bytes-safe: Check implicit bytes coercions

**Error Code**: `[str-bytes-safe]`

**Configuration**: Enabled by default

**Type Safety Principle**: Bytes and strings should not be accidentally coerced in formatting.

### When This Is an Error

```python
b = b"abc"

# Error: If x = b'abc' then f"{x}" produces "b'abc'", not "abc".
# If this is desired behavior, use f"{x!r}" or "{!r}".format(x).
# Otherwise, decode the bytes [str-bytes-safe]
print(f"The alphabet starts with {b}")
```

### Examples of Corrected Code

```python
b = b"abc"

# Decode the bytes
print(f"The alphabet starts with {b.decode('utf-8')}")  # OK

# Or use repr if intentional
print(f"The alphabet starts with {b!r}")  # OK - shows b'abc'
```

### Configuration Options

Suppress specific instances:

```python
print(f"The alphabet starts with {b}")  # type: ignore[str-bytes-safe]
```
