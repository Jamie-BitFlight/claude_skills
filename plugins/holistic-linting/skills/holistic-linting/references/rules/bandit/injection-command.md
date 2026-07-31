# Injection Vulnerabilities

Command injection, SQL injection, and shell injection allow attackers to execute arbitrary code or database commands. These occur when user input is not properly escaped or when shell expansion is enabled.

## B602: Subprocess with shell=True

**Severity**: HIGH

**What It Detects**: Using `subprocess.Popen()` with `shell=True`, which enables shell command injection.

### When This Is a Vulnerability

With `shell=True`, user input can break out of intended command and execute arbitrary commands:

```python
# VULNERABLE - shell=True allows injection
import subprocess

user_input = "; rm -rf /"  # Attacker input
filename = user_input

# Shell interprets the semicolon as command separator
subprocess.Popen(f"ls {filename}", shell=True)
# Actually executes: "ls ; rm -rf /"  <- Disaster!
```

### When This IS NOT a Vulnerability

- When the command is entirely hardcoded with no user input
- When user input is strictly validated/escaped

```python
# Safe - no user input in command
subprocess.Popen("ls -la", shell=True)

# Safe - input strictly validated to alphanumeric
import re

if re.match(r"^[a-zA-Z0-9_]+$", filename):
    subprocess.Popen(f"ls {filename}", shell=True)
```

### How to Fix

**Use shell=False (Recommended)**:

```python
import subprocess

# WRONG - shell=True
user_input = "report.txt"
subprocess.Popen(f"cat {user_input}", shell=True)

# RIGHT - shell=False with argument list
subprocess.run(["cat", user_input], check=True)
# Arguments are passed directly without shell interpretation

# User input in arguments is safe
subprocess.run(["grep", "pattern", user_input], check=True)
```

---

## B603-B607: Subprocess Variations

**Severity**: MEDIUM to HIGH

**What It Detects**: Various subprocess calls that may have injection risks.

- **B603**: `subprocess.Popen()` without `shell=True` (can still be dangerous with shell=True in parents)
- **B604**: Any function call with `shell=True`
- **B605**: Starting a process with a shell (OS-specific issues)
- **B606**: Starting a process without a shell
- **B607**: Starting a process with partial path (path traversal risk)

### B607: Partial Path in subprocess

**Severity**: MEDIUM

**What It Detects**: Using partial/relative paths instead of full paths in subprocess calls.

```python
# VULNERABLE - Partial path (could use different binary from PATH)
subprocess.run(["python", "script.py"])  # Which python? Could be attacker's version

# VULNERABLE - Command lookup from PATH
subprocess.run(["ls"], shell=False)  # Which ls? Could be hijacked
```

### How to Fix

**Use Full Absolute Paths**:

```python
import subprocess
import sys

# RIGHT - Full path to executable
subprocess.run(["/bin/ls", "-la"], check=True)
subprocess.run([sys.executable, "script.py"], check=True)
subprocess.run(["/usr/bin/python3", "script.py"], check=True)
```

---

## B608: Hardcoded SQL Expression

**Severity**: HIGH

**What It Detects**: String formatting or concatenation used to build SQL queries, leading to SQL injection.

### When This Is a Vulnerability

SQL injection allows attackers to execute arbitrary database commands:

```python
# VULNERABLE - String formatting (SQL injection)
import sqlite3

user_input = "admin'; DROP TABLE users; --"
query = f"SELECT * FROM users WHERE username = '{user_input}'"
# Actually executes: "SELECT * FROM users WHERE username = 'admin'; DROP TABLE users; --'"

conn = sqlite3.connect(":memory:")
conn.execute(query)

# VULNERABLE - String concatenation
query = "SELECT * FROM users WHERE username = '" + user_input + "'"

# VULNERABLE - Python % formatting
query = "SELECT * FROM users WHERE id = %d" % user_id
```

### When This IS NOT a Vulnerability

- When using parameterized queries (safe)
- When building non-SQL strings

```python
# Safe - parameterized query
cursor.execute("SELECT * FROM users WHERE username = ?", (user_input,))

# Safe - ORM handles parameterization
User.objects.filter(username=user_input)
```

### How to Fix

**Use Parameterized Queries**:

```python
import sqlite3

user_input = "admin'; DROP TABLE users; --"

# RIGHT - Parameterized query with placeholder
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

cursor.execute("SELECT * FROM users WHERE username = ?", (user_input,))
results = cursor.fetchall()

# Django ORM (automatic parameterization)
from django.contrib.auth.models import User

users = User.objects.filter(username=user_input)

# SQLAlchemy (parameterized)
from sqlalchemy import text

result = db.session.execute(text("SELECT * FROM users WHERE username = :username"), {"username": user_input})
```

---

## B609: Linux Commands Wildcard Injection

**Severity**: MEDIUM

**What It Detects**: Using wildcards in command arguments that can expand to unintended files.

### When This Is a Vulnerability

Wildcards expand with shell=True, potentially matching unintended files:

```python
# VULNERABLE - Wildcard with shell=True
import subprocess

user_directory = "/var/log"
subprocess.run(f"rm -f {user_directory}/*", shell=True)
# Could match unexpected files
```

### How to Fix

**Use Explicit File Paths or shell=False**:

```python
import subprocess
import glob

# Option 1: Use glob in Python (no shell needed)
user_directory = "/var/log"
for filename in glob.glob(f"{user_directory}/*.log"):
    subprocess.run(["rm", filename], check=True)

# Option 2: Use shell=False with explicit file list
files_to_remove = glob.glob(f"{user_directory}/*.log")
for file in files_to_remove:
    subprocess.run(["rm", file], check=True)
```

---

## B610: Django Extra Used

**Severity**: MEDIUM

**What It Detects**: Using Django's `.extra()` method for raw SQL, which can lead to SQL injection.

### When This Is a Vulnerability

`.extra()` bypasses Django's parameterization:

```python
# VULNERABLE - Django .extra() with string formatting
from django.contrib.auth.models import User

user_input = "1 OR 1=1"
users = User.objects.extra(where=[f"id = {user_input}"])
# Potential SQL injection
```

### How to Fix

**Use Parameterized Queries**:

```python
from django.contrib.auth.models import User
from django.db.models import Q

# RIGHT - Use Django ORM with parameterization
users = User.objects.filter(id=user_id)

# RIGHT - Use Q objects for complex queries
users = User.objects.filter(Q(id=user_id) | Q(username=username))

# If raw SQL is necessary
from django.db.models import Model

users = User.objects.raw("SELECT * FROM auth_user WHERE id = %s", [user_id])
```

---

## B611: Django RawSQL Used

**Severity**: MEDIUM

**What It Detects**: Using Django's raw SQL methods that may not be properly parameterized.

### When This Is a Vulnerability

Raw SQL without parameterization leads to injection:

```python
# VULNERABLE - Raw SQL without parameterization
from django.contrib.auth.models import User

user_input = "admin'; --"
users = User.objects.raw(f"SELECT * FROM auth_user WHERE username = '{user_input}'")
```

### How to Fix

**Use Parameterized Raw SQL**:

```python
from django.contrib.auth.models import User

# RIGHT - Parameterized raw SQL
users = User.objects.raw("SELECT * FROM auth_user WHERE username = %s", [user_input])
```

---

## B614: PyTorch Unsafe Load

**Severity**: HIGH

**What It Detects**: Using `torch.load()` with untrusted model files, allowing arbitrary code execution.

### When This Is a Vulnerability

PyTorch model files can contain arbitrary Python code:

```python
# VULNERABLE - Loading untrusted model
import torch

# Model file from user upload or internet
model = torch.load("user_uploaded_model.pth")
# Could execute arbitrary code
```

### How to Fix

**Use Safer Loading Options**:

```python
import torch

# RIGHT - Use map_location to restrict loading
model = torch.load("model.pth", map_location=torch.device("cpu"))

# RIGHT - Use weights_only=True (PyTorch 2.13+)
model = torch.load("model.pth", weights_only=True)

# RIGHT - Verify model source and signature
import hashlib

expected_hash = "abc123def456"
with open("model.pth", "rb") as f:
    actual_hash = hashlib.sha256(f.read()).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("Model file signature mismatch")
model = torch.load("model.pth")
```

---

## B615: Hugging Face Unsafe Download

**Severity**: HIGH

**What It Detects**: Using Hugging Face `transformers` library without proper safety checks for model downloads.

### When This Is a Vulnerability

Downloading models from untrusted sources can result in compromised models:

```python
# VULNERABLE - Downloading from untrusted source
from transformers import AutoModel

# Model from untrusted user
model = AutoModel.from_pretrained("user_namespace/model")
```

### How to Fix

**Use Trusted Model Sources**:

```python
from transformers import AutoModel

# RIGHT - Use official/verified models
model = AutoModel.from_pretrained("bert-base-uncased")

# RIGHT - From official organization
model = AutoModel.from_pretrained("huggingface/bert-base-uncased")

# RIGHT - With cache verification
import torch

model = AutoModel.from_pretrained(
    "bert-base-uncased",
    trust_remote_code=False,  # Don't execute remote code
    cache_dir="/safe/cache/dir",
    force_download=False,
)
```

---

See also: [index.md](./index.md) for all Bandit security checks.
