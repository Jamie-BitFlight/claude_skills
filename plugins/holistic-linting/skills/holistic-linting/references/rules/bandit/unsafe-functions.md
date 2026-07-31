# Unsafe Built-in Functions

Python provides several built-in functions that can execute arbitrary code or bypass security checks when misused.

## B101: Assert Used

**Severity**: LOW

**What It Detects**: Using `assert` statements for security checks.

### When This Is a Vulnerability

`assert` statements can be disabled at runtime with Python's `-O` flag:

```python
# VULNERABLE - Using assert for security
def authenticate(username, password):
    assert username != ""  # Can be disabled!
    assert is_valid_password(password)  # Can be disabled!

    login(username, password)
```

Running: `python -O script.py` disables all asserts, bypassing security checks.

### When This IS NOT a Vulnerability

- Assert used for debugging or testing (not production security)
- Assert for documenting programmer assumptions

```python
# OK - For testing/development
def calculate(x, y):
    assert x > 0, "x must be positive"
    assert y > 0, "y must be positive"
    return x / y


# OK - For documenting assumptions (code review)
def process_data(data):
    assert data is not None  # Programmer assumption, not security check
    return data.transform()
```

### How to Fix

**Use Explicit Validation**:

```python
# WRONG - Using assert for security
def authenticate(username, password):
    assert username != ""
    assert is_valid_password(password)


# RIGHT - Explicit validation that can't be disabled
def authenticate(username, password):
    if not username:
        raise ValueError("Username required")
    if not is_valid_password(password):
        raise ValueError("Invalid password")

    login(username, password)


# RIGHT - For type checking
def process(data: str) -> None:
    if not isinstance(data, str):
        raise TypeError(f"Expected str, got {type(data)}")
    # ... rest of function
```

---

## B102: Exec Used

**Severity**: HIGH

**What It Detects**: Using `exec()` function, which executes arbitrary Python code.

### When This Is a Vulnerability

`exec()` can run arbitrary code, especially if given user input:

```python
# VULNERABLE - exec with user input
user_code = request.args.get("code")
exec(user_code)  # Executes arbitrary Python!

# VULNERABLE - Dynamic code generation
formula = user_input  # "import os; os.system('rm -rf /')"
result = exec(f"x = {formula}")
```

### How to Fix

**Avoid exec() Entirely**:

```python
# WRONG
user_formula = "1 + 2 * 3"
result = exec(f"x = {user_formula}")

# RIGHT - Use safer alternatives
import ast
import operator


def evaluate_math(expression):
    """Safely evaluate math expressions."""
    # Parse and validate it's only numbers and operators
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("Invalid expression")

    # Verify it only contains safe operations
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Expression, ast.BinOp, ast.Num, ast.Add, ast.Sub, ast.Mult, ast.Div)):
            raise ValueError("Operation not allowed")

    # Evaluate safely
    return eval(compile(tree, "<string>", "eval"))


result = evaluate_math("1 + 2 * 3")
```

**Using numexpr for Math Expressions**:

```python
import numexpr

# Safe math evaluation
x = 1
y = 2
result = numexpr.evaluate("x + y * 2")  # Evaluates safely
```

---

## B307: Use of eval()

**Severity**: MEDIUM

**What It Detects**: Using `eval()` function, which executes arbitrary Python expressions.

### When This Is a Vulnerability

`eval()` evaluates arbitrary Python expressions:

```python
# VULNERABLE - eval with user input
user_input = "import os; os.system('rm -rf /')"
eval(user_input)

# VULNERABLE - Evaluating user formulas
formula = request.args.get("formula")  # "1 + 2"
result = eval(formula)  # Could be "import os; ..."
```

### How to Fix

**Use ast.literal_eval() for Safe Data**:

```python
import ast

# Safe - Evaluates only literals (strings, numbers, lists, dicts, tuples, booleans)
user_data = '{"name": "Alice", "age": 30}'
data = ast.literal_eval(user_data)

# WRONG - For complex expressions
result = eval("1 + 2 * 3")

# RIGHT - Use safer alternatives
import operator

result = operator.add(1, operator.mul(2, 3))
```

**For Python Code Compilation**:

```python
# Safe compilation without execution
code_string = "x = 1 + 2"
code_obj = compile(code_string, "<string>", "exec")

# Then execute in controlled namespace
namespace = {}
exec(code_obj, {"__builtins__": {}}, namespace)
# Limited builtins prevent dangerous operations
```

---

## B310: URL Open with Dangerous Schemes

**Severity**: MEDIUM

**What It Detects**: Using `urllib.urlopen()` without validating the URL scheme, allowing file:// or other dangerous schemes.

### When This Is a Vulnerability

File scheme allows reading local files:

```python
# VULNERABLE - No URL scheme validation
from urllib.request import urlopen

user_url = request.args.get("url")  # "file:///etc/passwd"
response = urlopen(user_url)  # Reads local file!

content = response.read()
```

### How to Fix

**Validate URL Scheme**:

```python
from urllib.request import urlopen
from urllib.parse import urlparse


def safe_url_open(url_string):
    """Open URL but only allow http/https."""
    parsed = urlparse(url_string)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme {parsed.scheme} not allowed")

    return urlopen(url_string)


# Safe - only http/https allowed
response = safe_url_open("https://example.com")
```

**Using Requests Library** (Recommended):

```python
import requests

# Requests is safer than urllib
response = requests.get("https://example.com", timeout=10)

# Still validate user URLs
user_url = request.args.get("url")
if not user_url.startswith(("http://", "https://")):
    raise ValueError("URL must use http or https")

response = requests.get(user_url, timeout=10)
```

---

## B311: Random for Security

**Severity**: LOW

**What It Detects**: Using the `random` module for security-sensitive purposes (cryptographic randomness).

### When This Is a Vulnerability

`random.random()` is not cryptographically secure:

```python
# VULNERABLE - Using random for tokens/keys
import random
import string

# Weak token - predictable
token = "".join(random.choices(string.ascii_letters, k=32))

# Weak cryptographic key
key = random.getrandbits(256)
```

### How to Fix

**Use os.urandom() or secrets**:

```python
import secrets
import os

# RIGHT - Cryptographically secure random
token = secrets.token_hex(32)  # 64 character hex string
key = secrets.token_bytes(32)  # 32 bytes of random data

# RIGHT - Using os.urandom directly
key = os.urandom(32)  # 32 bytes of cryptographic randomness

# RIGHT - For secure integer
secure_random = int.from_bytes(os.urandom(32), "big")

# RIGHT - For secure choice from list
import random as random_module  # OK for non-crypto

choice = secrets.choice(["option1", "option2", "option3"])
```

---

See also: [index.md](./index.md) for all Bandit security checks.
