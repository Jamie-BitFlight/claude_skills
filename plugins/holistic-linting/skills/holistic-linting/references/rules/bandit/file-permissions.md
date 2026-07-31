# File Permissions and Temporary Files

Overly permissive file permissions expose sensitive data. Insecure temporary file creation creates race conditions and directory traversal vulnerabilities.

## B103: Set Bad File Permissions

**Severity**: MEDIUM

**What It Detects**: Creating files with overly permissive mode (permissions that allow others to read/write).

### When This Is a Vulnerability

Files with world-readable permissions expose sensitive data:

```python
# VULNERABLE - World-readable file (644 in octal)
import os

# Create config file readable by everyone
os.chmod("config.txt", 0o644)

# File created with permissive umask (via open or os.open)
open("secret_key.txt", "w").write(secret_key)
# May be readable by others depending on umask

# B103 detects mode with too many permissions
os.chmod("sensitive_data.json", 0o777)  # Everyone can read/write!
```

### When This IS NOT a Vulnerability

- Reading/writing your own files in /tmp (mode 0o600 for user only)
- Config files intentionally public (web server files, CSS, etc.)

```python
# Safe - restrictive permissions
os.chmod("secret_file.txt", 0o600)  # User only

# Safe - public assets
os.chmod("public/index.html", 0o644)  # Public web file
```

### How to Fix

**Use Restrictive Permissions**:

```python
import os
from pathlib import Path

# WRONG - Readable by others
os.chmod("secret.txt", 0o644)

# RIGHT - Only for you (user)
os.chmod("secret.txt", 0o600)

# RIGHT - Using pathlib
Path("secret.txt").chmod(0o600)

# RIGHT - When creating a file
with open("secret.txt", "w") as f:
    f.write(secret_data)
os.chmod("secret.txt", 0o600)

# RIGHT - Create restrictive from the start
flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
fd = os.open("secret.txt", flags, mode=0o600)
with os.fdopen(fd, "w") as f:
    f.write(secret_data)
```

---

## B104: Hardcoded Bind All Interfaces

**Severity**: MEDIUM

**What It Detects**: Binding to all network interfaces (0.0.0.0) instead of specific interfaces.

### When This Is a Vulnerability

Binding to 0.0.0.0 exposes services to:

- Unauthenticated network access
- Potential attacks from other machines on the network
- Unintended service exposure

```python
# VULNERABLE - Binds to all interfaces
import socket
import http.server

# B104: Listening on all interfaces
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 5000))
server.listen(1)

# In HTTP frameworks
from flask import Flask

app = Flask(__name__)
app.run(host="0.0.0.0", port=5000)  # Exposed!

# Django
ALLOWED_HOSTS = ["*"]  # Too permissive
```

### When This IS NOT a Vulnerability

- Docker containers where port forwarding is controlled
- Development machines with firewall protection
- Services explicitly intended for network access with authentication

```python
# Acceptable - with authentication and firewall
app.run(host="0.0.0.0", port=5000)  # OK if behind auth + firewall
```

### How to Fix

**Bind to Specific Interfaces**:

```python
import socket

# RIGHT - Localhost only (development)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 5000))
server.listen(1)

# RIGHT - Specific network interface
server.bind(("192.168.1.100", 5000))

# In Flask
from flask import Flask

app = Flask(__name__)

# Development - localhost only
app.run(host="127.0.0.1", port=5000)

# Production - behind reverse proxy
if os.getenv("ENV") == "production":
    app.run(host="127.0.0.1", port=5000)  # Still localhost, proxied

# Environment-driven binding
allowed_host = os.getenv("BIND_HOST", "127.0.0.1")
app.run(host=allowed_host, port=5000)
```

---

## B306: MkTemp Usage

**Severity**: MEDIUM

**What It Detects**: Using `os.mktemp()` which is vulnerable to race conditions.

### When This Is a Vulnerability

`os.mktemp()` returns a filename but doesn't create it, allowing race conditions:

```python
# VULNERABLE - Race condition window
import os

# os.mktemp returns a name but doesn't create the file
tmpfile = os.mktemp()  # e.g., "/tmp/tmp12345"

# TIME WINDOW: Attacker can create /tmp/tmp12345 here
# with their content

with open(tmpfile, "w") as f:
    f.write(sensitive_data)
# Your sensitive data went to attacker's file!
```

### How to Fix

**Use tempfile Module**:

```python
import tempfile
import os

# RIGHT - Creates file securely and atomically
with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write(sensitive_data)
    tmpfile = f.name

# File exists and is securely created
# Only you can access it (mode 0o600)

# RIGHT - Automatic cleanup
with tempfile.NamedTemporaryFile(mode="w") as f:
    f.write(sensitive_data)
    # File automatically deleted on close

# RIGHT - Temporary directory
tmpdir = tempfile.mkdtemp()
tmpfile = os.path.join(tmpdir, "myfile.txt")
with open(tmpfile, "w") as f:
    f.write(data)

# Clean up when done
import shutil

shutil.rmtree(tmpdir)
```

---

## B325: Tempnam Usage

**Severity**: MEDIUM

**What It Detects**: Using deprecated `os.tempnam()` and `os.tmpnam()`, which are vulnerable to symlink attacks.

### When This Is a Vulnerability

Like `mktemp()`, these functions have race conditions:

```python
# VULNERABLE - Symlink attack window
import os

tmpfile = os.tempnam("/tmp", "myapp_")  # Returns filename only
# Attacker creates symlink: /tmp/myapp_XXX -> /etc/passwd

with open(tmpfile, "w") as f:
    f.write(data)  # Writes to /etc/passwd!
```

### How to Fix

**Use tempfile.NamedTemporaryFile()**:

```python
import tempfile

# RIGHT - Secure temporary file
with tempfile.NamedTemporaryFile(dir="/tmp", prefix="myapp_", delete=False) as f:
    f.write(b"data")
    tmpfile = f.name

# File is created securely, symlink attacks impossible
```

---

See also: [index.md](./index.md) for all Bandit security checks.
