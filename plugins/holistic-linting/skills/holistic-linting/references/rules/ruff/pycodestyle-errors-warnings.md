# E/W: pycodestyle Errors and Warnings

**Source**: [pycodestyle](https://pycodestyle.pycqa.org/) **Total Rules**: 76 (69 E errors, 7 W warnings)

This rule family enforces Python style conventions as defined by PEP 8. Rules are divided into two categories:

- **E rules** (E1xx-E7xx): Style errors that typically indicate genuine problems
- **W rules** (W1xx-W3xx): Style warnings that represent less critical issues

---

## Indentation Rules (E1xx)

### E101: mixed-spaces-and-tabs

Checks for mixing tabs and spaces for indentation.

**What it prevents**: Inconsistent indentation that can cause parsing ambiguities and readability issues.

**When it's a violation**:

```python
def function():
	x = 1  # Tab character
    y = 2  # Spaces
```

**When it's NOT a violation**:

```python
def function():
    x = 1
    y = 2
```

**Configuration**: Set `indent-style = "space"` in `[tool.ruff.format]` to enforce spaces.

---

### E111-E117: Indentation with Invalid Multiple

Rules E111-E117 detect various indentation problems:

- **E111**: Indentation is not a multiple of 4
- **E112**: Expected an indented block
- **E113**: Unexpected indentation
- **E114-E116**: Related indentation issues with comments
- **E117**: Over-indented

**What it prevents**: Code that doesn't follow consistent indentation patterns, which can cause logic errors and syntax issues.

**When it's a violation**:

```python
def func():
  x = 1  # 2 spaces, not 4

if True:
x = 1  # No indentation where expected
```

**When it's NOT a violation**:

```python
def func():
    x = 1


if True:
    x = 1
```

---

## Whitespace Rules (E2xx)

### E201-E204: Whitespace Around Brackets

- **E201**: Whitespace after opening bracket
- **E202**: Whitespace before closing bracket
- **E203**: Whitespace before punctuation
- **E204**: Whitespace after decorator

**What it prevents**: Unnecessary whitespace that reduces readability.

**When it's a violation**:

```python
func(x, y)  # E201, E202
x = [1, 2, 3]  # E201, E202
result = func()  # E201, E202
```

**When it's NOT a violation**:

```python
func(x, y)
x = [1, 2, 3]
result = func()
```

**Safe to auto-fix**: Yes

---

### E211: Whitespace Before Parameters

**What it prevents**: Unnecessary space between function name and parameter list.

**When it's a violation**:

```python
def func(x):
    pass


func(1, 2)
```

**When it's NOT a violation**:

```python
def func(x):
    pass


func(1, 2)
```

---

### E221-E228: Operator Whitespace

- **E221**: Multiple spaces before operator
- **E222**: Multiple spaces after operator
- **E223**: Tab before operator
- **E224**: Tab after operator
- **E225**: Missing whitespace around operator
- **E226**: Missing whitespace around arithmetic operator (often disabled)
- **E227**: Missing whitespace around bitwise or shift operator
- **E228**: Missing whitespace around modulo operator

**What it prevents**: Inconsistent spacing around operators.

**When it's a violation**:

```python
x = 1 + 2  # E225
x = 1 + 2  # E225
x = 1 + 2  # E221
x = 1 + 2  # E222
```

**When it's NOT a violation**:

```python
x = 1 + 2
y = 3
result = func(a, b)
```

**Note**: E226 is often ignored when using formatters, as they handle spacing.

---

### E231: Missing Whitespace After Comma

**What it prevents**: Missing space after commas in lists, tuples, function calls.

**When it's a violation**:

```python
x = [1, 2, 3]
func(a, b, c)
```

**When it's NOT a violation**:

```python
x = [1, 2, 3]
func(a, b, c)
```

**Safe to auto-fix**: Yes

---

### E241-E242: Whitespace After Comma

- **E241**: Multiple spaces after comma
- **E242**: Tab after comma

**When it's a violation**:

```python
x = [1, 2, 3]  # E241
```

---

### E251-E252: Parameter Equals

- **E251**: Unexpected spaces around keyword parameter equals
- **E252**: Missing whitespace around parameter equals

**What it prevents**: Inconsistent spacing in function definitions and calls.

**When it's a violation (E251)**:

```python
def func(x=1):  # Space around = in default parameter
    pass
```

**When it's NOT a violation (E251)**:

```python
def func(x=1):
    pass


# Note: With annotations, spaces are allowed
def func(x: int = 1):
    pass
```

---

### E261-E266: Comment Spacing

- **E261**: Too few spaces before inline comment
- **E262**: No space after inline comment
- **E265**: No space after block comment
- **E266**: Multiple leading hashes for block comment

**What it prevents**: Improper comment formatting.

**When it's a violation**:

```python
x = 1  # comment  # E261 - should have 2 spaces before
x = 1  # comment  # E262 - need space after #
# comment  # E265 - need space after #
##comment  # E266 - multiple hashes
```

**When it's NOT a violation**:

```python
x = 1  # comment
x = 1  # comment

# comment
```

---

### E271-E275: Keyword Whitespace

- **E271**: Multiple spaces after keyword
- **E272**: Multiple spaces before keyword
- **E273**: Tab after keyword
- **E274**: Tab before keyword
- **E275**: Missing whitespace after keyword

**When it's a violation**:

```python
if x:  # E271
    pass

for item in items:  # E271
    pass
```

---

## Blank Line Rules (E3xx)

### E301-E306: Blank Lines

- **E301**: Expected 1 blank line, found 0 (between methods)
- **E302**: Expected 2 blank lines, found N (top-level definitions)
- **E303**: Too many blank lines
- **E304**: Blank line after decorator
- **E305**: Expected 2 blank lines, found N (after function/class)
- **E306**: Expected 1 blank line before nested definition

**What it prevents**: Improper vertical spacing that affects readability.

**When it's a violation (E302)**:

```python
def func1():
    pass


def func2():  # Should have 2 blank lines before
    pass
```

**When it's NOT a violation (E302)**:

```python
def func1():
    pass


def func2():
    pass
```

**When it's a violation (E303)**:

```python
x = 1


# More than 2 blank lines above
y = 2
```

**When it's NOT a violation (E303)**:

```python
x = 1


y = 2
```

---

## Import and Statement Rules (E4xx)

### E401: Multiple Imports on One Line

**What it prevents**: Multiple module imports in a single statement.

**When it's a violation**:

```python
import os, sys
```

**When it's NOT a violation**:

```python
import os
import sys

from x import a, b  # Multiple from same module is OK
```

---

### E402: Module Import Not at Top of File

**What it prevents**: Code that runs before imports.

**When it's a violation**:

```python
import os

x = 1  # Code before imports

import sys
```

**When it's NOT a violation**:

```python
import os
import sys

x = 1
```

---

### E501: Line Too Long

**What it prevents**: Lines exceeding the configured maximum length (default: 88 characters).

**Configuration**:

```toml
[tool.ruff]
line-length = 88  # Adjust as needed

[tool.ruff.lint]
# Often ignored when using a formatter
ignore = ["E501"]
```

**When it's a violation**:

```python
result = some_function(arg1, arg2, arg3) + another_function(arg4, arg5, arg6)  # Very long
```

**When it's NOT a violation** (with line-length=88):

```python
result = some_function(arg1, arg2, arg3) + another_function(arg4, arg5, arg6)
```

**Note**: Often disabled when using a formatter (Ruff, Black), as formatters handle line length.

---

### E502: Redundant Backslash

**What it prevents**: Unnecessary line continuation characters.

**When it's a violation**:

```python
x = 1 + 2  # Backslash not needed in parentheses
```

**When it's NOT a violation**:

```python
x = 1 + 2  # No backslash needed in parentheses

x = 1 + 2  # OK when backslash is necessary
```

---

## Statement Rules (E7xx)

### E701-E703: Multiple Statements

- **E701**: Multiple statements on one line (colon)
- **E702**: Multiple statements on one line (semicolon)
- **E703**: Useless semicolon

**What it prevents**: Code that violates single-responsibility principle.

**When it's a violation**:

```python
if x:
    y = 1  # E701
x = 1
y = 2  # E702
x = 1  # E703
```

**When it's NOT a violation**:

```python
if x:
    y = 1

x = 1
y = 2
```

---

### E711: None Comparison

**What it prevents**: Using `==` or `!=` to compare with None.

**When it's a violation**:

```python
if x == None:
    pass

if x != None:
    pass
```

**When it's NOT a violation**:

```python
if x is None:
    pass

if x is not None:
    pass
```

**Safe to auto-fix**: Yes

---

### E712: True/False Comparison

**What it prevents**: Using `==` or `!=` to compare boolean values.

**When it's a violation**:

```python
if x == True:
    pass

if y == False:
    pass
```

**When it's NOT a violation**:

```python
if x is True:
    pass

if y is False:
    pass

if x:  # Preferred
    pass
```

**Safe to auto-fix**: Yes

---

### E713-E714: Membership and Identity

- **E713**: Test for membership should use `in`
- **E714**: Test for object identity should use `is`

**When it's a violation (E713)**:

```python
if not x in list:  # Should use 'not in'
    pass
```

**When it's NOT a violation (E713)**:

```python
if x in list:
    pass

if x not in list:
    pass
```

---

### E721-E722: Type Checking

- **E721**: Use isinstance() instead of type() for comparisons
- **E722**: Do not use bare except

**When it's a violation (E721)**:

```python
if type(x) == int:
    pass
```

**When it's NOT a violation (E721)**:

```python
if isinstance(x, int):
    pass
```

**When it's a violation (E722)**:

```python
try:
    something()
except:
    pass
```

**When it's NOT a violation (E722)**:

```python
try:
    something()
except Exception:
    pass
```

---

## W: Warning Rules

### W191: Indentation Contains Tabs

**What it prevents**: Using tabs for indentation (should use spaces).

**Configuration**: Set `indent-style = "space"` to enforce spaces.

---

### W291: Trailing Whitespace

**What it prevents**: Whitespace at the end of lines.

**Safe to auto-fix**: Yes

---

### W292: Missing Newline at End of File

**What it prevents**: Files that don't end with a newline character.

**Safe to auto-fix**: Yes

---

### W293: Blank Line with Whitespace

**What it prevents**: Blank lines containing whitespace.

**Safe to auto-fix**: Yes

---

### W391: Too Many Newlines at End of File

**What it prevents**: Multiple blank lines at the end of files.

**Safe to auto-fix**: Yes

---

## Configuration Examples

### Strict Configuration

```toml
[tool.ruff.lint]
select = ["E", "W"]
ignore = ["E501"]  # Line length handled by formatter
```

### Common Ignores

```toml
[tool.ruff.lint]
select = ["E", "W"]
ignore = [
    "E501",  # Line too long (formatter handles)
    "E731",  # Lambda assignment (sometimes acceptable)
]
```

### Flexible Configuration

```toml
[tool.ruff.lint]
select = ["E", "W"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["E501"]  # Allow longer lines in tests
"__init__.py" = ["E402"]  # Allow imports after code in __init__
```

---

**Last Updated**: 2025-11-04 **Documentation Format**: Complete with examples and configuration options
