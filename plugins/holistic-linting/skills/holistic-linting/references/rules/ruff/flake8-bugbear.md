# B: flake8-bugbear Rules

**Source**: [flake8-bugbear](https://github.com/PyCQA/flake8-bugbear) **Total Rules**: 43 rules **Purpose**: Detects common bugs and design problems in Python code

flake8-bugbear rules focus on practical bugs that can appear in real-world code. These are more specialized than pycodestyle (E/W) but broader than domain-specific rules.

---

## Mutable Defaults (B006-B008)

### B006: Mutable Argument Default

**What it prevents**: Using mutable objects (list, dict, set) as default argument values.

**Why it's a problem**: Mutable defaults are shared across all function calls, leading to unexpected behavior.

**When it's a violation**:

```python
def append_item(item, items=[]):  # Wrong!
    items.append(item)
    return items
```

**When it's NOT a violation**:

```python
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

**Safe to auto-fix**: No (requires logic change)

---

### B008: Function Call in Default Argument

**What it prevents**: Calling functions in default argument values.

**When it's a violation**:

```python
def func(x=list()):  # Called at definition time
    pass


def func(x=datetime.now()):  # Called once, not per call
    pass
```

**When it's NOT a violation**:

```python
def func(x=None):
    if x is None:
        x = list()
    pass


def func(x=None):
    if x is None:
        x = datetime.now()
    pass
```

---

## Variable and Name Issues (B021-B030)

### B025: Duplicate Exception Handler

**What it prevents**: Using the same exception type in multiple except clauses.

**When it's a violation**:

```python
try:
    pass
except ValueError:
    pass
except ValueError:  # Duplicate
    pass
```

---

## Common Mistakes

### B003: Assignment to os.environ

**What it prevents**: Direct assignment to `os.environ` (should use direct item assignment).

**When it's a violation**:

```python
import os

os.environ = {}  # Wrong - overwrites the mapping
```

**When it's NOT a violation**:

```python
import os

os.environ["VAR"] = "value"  # Correct
```

---

### B004: Using `hasattr` for Type Checking

**What it prevents**: Using `hasattr` with callable-related checks.

---

### B005: Using `.strip()` With Multi-Character Strings

**What it prevents**: Incorrect use of `.strip()` with multiple characters.

**When it's a violation**:

```python
"prefix_text_suffix".strip("prefix_")
# Results in: "text_suffix" NOT "text"
```

**Why**: `strip()` removes any of the characters, not the string as a prefix/suffix.

---

### B009: `get_logger()` With Identifier

**What it prevents**: Logger name that should be `__name__`.

**When it's a violation**:

```python
logger = logging.getLogger("my_module")  # Hard-coded name
```

**When it's NOT a violation**:

```python
logger = logging.getLogger(__name__)  # Dynamic name
```

---

### B010: `.set()` Called on `loop.run_until_complete()`

**What it prevents**: Incorrect event loop usage patterns.

---

## Return and Assignment Rules

### B011: `assert False` Used

**What it prevents**: Using `assert False` instead of `raise NotImplementedError`.

**When it's a violation**:

```python
def abstract_method():
    assert False, "Not implemented"
```

**When it's NOT a violation**:

```python
def abstract_method():
    raise NotImplementedError
```

---

### B012: `except` Block with Only `pass`

**What it prevents**: Bare except handlers that suppress all exceptions.

**When it's a violation**:

```python
try:
    risky_operation()
except Exception:
    pass  # Silently ignores errors
```

**When it's NOT a violation**:

```python
try:
    risky_operation()
except SpecificError:
    logger.error("Operation failed")
    # Handle or log appropriately
```

---

### B013: Redundant Except Handler

**What it prevents**: Unreachable except clauses (specific exception after general).

**When it's a violation**:

```python
try:
    pass
except Exception:
    pass
except ValueError:  # Unreachable - caught by Exception above
    pass
```

---

### B014: Duplicate `except` Handler

**What it prevents**: Same exception type in multiple clauses.

---

### B015: Useless Expression in Except Handler

**What it prevents**: Expression statements that have no effect.

**When it's a violation**:

```python
try:
    pass
except ValueError:
    x == y  # Comparison, not assignment!
```

**When it's NOT a violation**:

```python
try:
    pass
except ValueError:
    x = y  # Assignment
```

---

## Context and Loop Issues

### B016: Cannot Raise Literal

**What it prevents**: Raising non-exception literals.

**When it's a violation**:

```python
raise ValueError  # Missing parentheses
```

**When it's NOT a violation**:

```python
raise ValueError()  # Correct instantiation
```

---

### B017: `assert` With Comparison

**What it prevents**: Using `assert` for comparisons (not assertions).

**When it's a violation**:

```python
assert x < 5  # If false, shows confusing assertion error
```

**When it's NOT a violation**:

```python
assert x < 5, f"Expected x < 5, got {x}"  # With message
```

---

### B018: Found Useless Expression

**What it prevents**: Expression statements with no effect.

**When it's a violation**:

```python
x == 1  # Comparison, not assignment
"some string"  # Literal with no effect
```

**When it's NOT a violation**:

```python
x = 1  # Assignment
result = "some string"  # Assignment
func()  # Function call (has side effects)
```

---

### B019: Use of `functools.lru_cache`

**What it prevents**: Using `lru_cache` on class methods incorrectly.

---

## String and Format Rules

### B020: Found `for` Loop That Reassigns Loop Variable

**What it prevents**: Loop variable being reassigned inside the loop.

---

### B021: Found f-string is missing placeholders

**What it prevents**: F-strings without any placeholder expressions.

**When it's a violation**:

```python
result = f"text without placeholders"
```

**When it's NOT a violation**:

```python
result = f"text with {variable}"
```

---

## Loop and Comprehension Rules

### B022: `exec()` Used

**What it prevents**: Using `exec()` for dynamic code execution.

**When it's a violation**:

```python
exec("x = 1")  # Dangerous and generally not needed
```

---

### B023: Function Definition in Loop

**What it prevents**: Defining functions inside loops (closure issues).

**When it's a violation**:

```python
funcs = []
for i in range(5):

    def func():
        return i  # Always returns 4 (last value)

    funcs.append(func)
```

**When it's NOT a violation**:

```python
funcs = []
for i in range(5):

    def make_func(n):
        def func():
            return n

        return func

    funcs.append(make_func(i))
```

---

### B024: Except Block Catches Exception

Catches a bare `except Exception` when a specific exception should be caught.

---

## Configuration

### Recommended Configuration

```toml
[tool.ruff.lint]
extend-select = ["B"]  # Add bugbear to other rules
ignore = ["B008"]  # Or include specific ignores
```

### Common Ignores

```toml
[tool.ruff.lint]
select = ["E", "F", "B"]
ignore = [
    "B008",  # Function call in default argument (sometimes acceptable)
    "B009",  # When using logger names other than __name__ is intentional
]
```

---

## Summary

flake8-bugbear helps catch:

1. **Mutable defaults** (B006) - Always fix these
2. **Variable shadowing and scope issues**
3. **Common exception handling mistakes**
4. **Logic errors in comparisons and assignments**
5. **Performance issues** (caching, loops, comprehensions)

**Integration with other rules**:

- Use B006/B008 with F rules to catch all variable scope issues
- Use B012-B020 with E/F rules for comprehensive error detection
- B021+ are more specialized and can be ignored if not applicable

---

**Last Updated**: 2025-11-04 **Documentation Format**: Rule guide with violation examples and fixes
