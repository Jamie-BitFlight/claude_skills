# F: Pyflakes Rules

**Source**: [Pyflakes](https://github.com/PyCQA/pyflakes/) **Total Rules**: 92 rules **Purpose**: Detects logical errors, undefined names, unused imports, and other code quality issues

Pyflakes rules are the foundation of Python linting. These rules detect real bugs and incorrect code patterns that can lead to runtime errors. Unlike style rules (E/W), Pyflakes violations typically indicate genuine problems that should be fixed.

---

## Undefined Names and Imports (F4xx)

### F401: Unused Import

**What it prevents**: Import statements that are not used in the code.

**When it's a violation**:

```python
import os  # Not used anywhere
from sys import argv  # Never referenced

x = 1
```

**When it's NOT a violation**:

```python
import os

path = os.path.join("a", "b")
```

**Special case - Re-exports**:

```python
# In a package __init__.py, importing for re-export is OK
from .module import some_function  # Exposed via __all__

__all__ = ["some_function"]
```

**Safe to auto-fix**: Yes

**Ignore pattern**: Use in `__init__.py` or `__main__.py` where imports enable re-exports:

```toml
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"__main__.py" = ["F401"]
```

---

### F402: Import Shadowed by Loop Variable

**What it prevents**: Import names that are shadowed by loop variables, causing the import to become inaccessible.

**When it's a violation**:

```python
import sys

for sys in range(10):  # 'sys' import is now inaccessible
    print(sys)
```

**When it's NOT a violation**:

```python
import sys

for item in range(10):
    print(item, sys.version_info)
```

---

### F403: Undefined Names from `import *`

**What it prevents**: Using `from module import *` which makes undefined names ambiguous.

**When it's a violation**:

```python
from os.path import *

# Now referencing functions like:
join("a", "b")  # F405 - undefined name 'join'
exists("file")  # F405 - undefined name 'exists'
```

**When it's NOT a violation**:

```python
from os.path import join, exists

result = join("a", "b")
```

**Note**: F403 warns about `import *`, while F405 warns about undefined names from it.

**Safe to auto-fix**: Partial (can add `# noqa` but not the imports)

---

### F404: Late Future Import

**What it prevents**: `__future__` imports that appear after other code.

**When it's a violation**:

```python
import os
from __future__ import annotations  # Must be first!
```

**When it's NOT a violation**:

```python
from __future__ import annotations

import os
```

**Rule**: `__future__` imports must appear before all other imports (except docstrings and comments).

**Safe to auto-fix**: No (requires manual reordering)

---

### F405: Undefined Name from `import *`

**What it prevents**: Using names that are undefined because they come from `import *`.

**When it's a violation**:

```python
from os import *

# References to undefined names:
path.join("a", "b")  # 'path' not explicitly imported
```

**When it's NOT a violation**:

```python
from os import path

path.join("a", "b")
```

---

## Unused Variables and Assignments (F8xx)

### F841: Local Variable Never Used

**What it prevents**: Variables that are assigned but never used.

**When it's a violation**:

```python
def func():
    x = 1  # Assigned but never used
    y = 2
    return y
```

**When it's NOT a violation**:

```python
def func():
    x = 1
    y = 2
    return x + y
```

**Special case - Intent to use later**:

```python
def func():
    x = 1  # noqa: F841  - Will use in debugger
    import pdb

    pdb.set_trace()
```

**Underscore convention**:

```python
def unpack():
    x, _, z = values  # '_' indicates intentional non-use
    return x, z
```

---

## Undefined and Built-in Names (F6xx, F9xx)

### F821: Undefined Name

**What it prevents**: References to names that are not defined anywhere in the code.

**When it's a violation**:

```python
def func():
    return undefined_variable  # Name not defined


print(NonExistentClass())  # Class not defined
```

**When it's NOT a violation**:

```python
x = 1


def func():
    return x  # Global x is defined


class MyClass:
    pass


obj = MyClass()
```

**Common causes**:

- Typos in variable names
- Forgotten imports
- Scope issues with closures

---

### F823: Local Variable Referenced Before Assignment

**What it prevents**: Using a local variable before it's assigned.

**When it's a violation**:

```python
def func():
    print(x)  # Referenced before assignment
    x = 1
```

**When it's NOT a violation**:

```python
def func():
    x = 1
    print(x)  # OK - assigned first
```

**Global/nonlocal keyword**:

```python
x = 1


def func():
    global x
    print(x)  # OK - using global


def nested():
    x = 2

    def inner():
        nonlocal x
        print(x)  # OK - using nonlocal from enclosing scope
```

---

### F901: `raise NotImplemented` Error

**What it prevents**: Raising `NotImplemented` instead of `NotImplementedError`.

**When it's a violation**:

```python
def abstract_method():
    raise NotImplemented  # Wrong!
```

**When it's NOT a violation**:

```python
def abstract_method():
    raise NotImplementedError  # Correct!
```

**Context**: `NotImplemented` is a singleton value for comparison operators, not an exception.

---

## Redefined and Shadowing (F8xx)

### F811: Redefined While Unused

**What it prevents**: Redefining a name before the first definition is used.

**When it's a violation**:

```python
def func():
    pass


def func():  # Redefined without using first version
    pass


x = 1
x = 2  # Redefined without using first value
```

**When it's NOT a violation**:

```python
def func(version=1):
    pass


def func(version=2):  # Deliberate overload
    pass


x = 1
y = x + 1  # Use before redefine
x = 2
```

**Special cases - Overloading**:

```python
from typing import overload


@overload
def process(x: int) -> int: ...


@overload
def process(x: str) -> str: ...


def process(x):
    return x
```

---

### F812: Redefined While Unused (in same scope)

Similar to F811 but specifically within the same scope.

---

## Syntax and Expression Issues

### F631: Assert Tuple

**What it prevents**: Using `assert` with a tuple, which is always truthy.

**When it's a violation**:

```python
assert (x == 5, "x should be 5")  # Tuple is always truthy!
```

**When it's NOT a violation**:

```python
assert x == 5, "x should be 5"  # Correct syntax
```

---

### F632: Use `==` for Equality Comparison

**What it prevents**: Using `is` to compare values (should use `==`).

**When it's a violation**:

```python
if x is 5:  # Wrong - comparing identity
    pass
```

**When it's NOT a violation**:

```python
if x == 5:  # Correct - comparing equality
    pass

if x is None:  # Correct - None should use 'is'
    pass
```

---

### F633: Use of `>>` in Print Statement

**What it prevents**: Old Python 2 print statement syntax.

**When it's a violation**:

```python
print >> file, "text"  # Python 2 syntax
```

**When it's NOT a violation**:

```python
print("text", file=file)  # Python 3 syntax
```

---

### F634: If Test is a Tuple

**What it prevents**: Using a tuple literal in a boolean context (always truthy).

**When it's a violation**:

```python
if (x, y):  # Tuple is always truthy
    pass
```

**When it's NOT a violation**:

```python
if x and y:
    pass

if (x, y):  # With trailing comma - still tuple
    pass
```

---

### F701: `return` Statement Outside Function

**What it prevents**: Using `return` outside a function.

**When it's a violation**:

```python
x = 1
return x  # Can't return from module level
```

**When it's NOT a violation**:

```python
def func():
    return 1


x = func()
```

---

### F702: `yield` Statement Outside Function

**What it prevents**: Using `yield` outside a function.

**When it's a violation**:

```python
yield 1  # Can't yield from module level
```

**When it's NOT a violation**:

```python
def generator():
    yield 1
```

---

### F703: `yield from` Statement Outside Function

**What it prevents**: Using `yield from` outside a function.

---

### F704: `yield` with Value in Async Function

**What it prevents**: Using `yield` in async functions (should use `yield from` or async generators).

---

### F705: `return` with Arguments in Generator

**What it prevents**: Using `return` with a value in a generator (should use `raise StopIteration`).

**When it's a violation**:

```python
def generator():
    yield 1
    return 2  # Wrong in generators
```

**When it's NOT a violation**:

```python
def generator():
    yield 1
    return  # Bare return is OK


def generator_with_return():
    yield 1
    return  # Just exit generator
```

---

### F706: `return` Statement in Finally Block

**What it prevents**: Using `return` in a `finally` block (suppresses exceptions).

**When it's a violation**:

```python
try:
    raise ValueError()
except:
    pass
finally:
    return  # Suppresses the exception!
```

**When it's NOT a violation**:

```python
try:
    x = 1
finally:
    cleanup()  # No return
```

---

## Dictionary and Expression Errors

### F601: Dictionary Key Repeated

**What it prevents**: Using the same key multiple times in dictionary literals.

**When it's a violation**:

```python
d = {"a": 1, "b": 2, "a": 3}  # 'a' appears twice
```

**When it's NOT a violation**:

```python
d = {"a": 1, "b": 2}  # All unique keys
```

---

### F602: Dictionary Key Variable Repeated

**What it prevents**: Using the same variable as a key multiple times.

**When it's a violation**:

```python
key = "a"
d = {key: 1, "b": 2, key: 3}  # 'key' used twice
```

---

## Expression and Loop Issues

### F706: `return` in Finally Block

(See above)

### F707: Exception Handler With Multiple Except Clauses

**What it prevents**: Multiple exception types in except clause without using tuple.

**When it's a violation**:

```python
try:
    pass
except ValueError, TypeError:  # Python 2 syntax
    pass
```

**When it's NOT a violation**:

```python
try:
    pass
except (ValueError, TypeError):  # Correct - tuple of exceptions
    pass
```

---

## Configuration and Usage

### Recommended Configuration

```toml
[tool.ruff.lint]
select = ["F"]  # Enable all Pyflakes rules
```

### Common Exceptions

```toml
[tool.ruff.lint]
select = ["F"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports for re-exports
"__main__.py" = ["F401"]  # Allow unused imports in scripts
"tests/*" = ["F841"]  # Allow unused variables in tests
```

### Using Underscore for Intent

```python
def process_data(x, y, _z):
    """Process only x and y, ignore z.

    Using underscore convention makes intent clear
    and avoids F841 (unused variable) warnings.
    """
    return x + y
```

---

## Summary

Pyflakes rules detect real bugs:

1. **Always enable** F rules in your configuration
2. **F401** is safe to auto-fix with `ruff check --fix`
3. **F821** (undefined names) is critical for catching errors
4. **F841** (unused variables) helps clean up code
5. Use `# noqa` sparingly - usually the code should be fixed

**Common Pyflakes rule combinations**:

- F401, F402, F403, F404, F405: Import issues
- F821, F823: Undefined or misplaced references
- F841: Unused variables
- F631-F634: Expression/syntax issues

---

**Last Updated**: 2025-11-04 **Documentation Format**: Complete with examples and explanations
