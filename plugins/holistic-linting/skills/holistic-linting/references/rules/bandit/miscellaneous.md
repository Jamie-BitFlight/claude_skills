# Miscellaneous Security Issues

Security patterns and code practices that don't fit other categories but still represent security or reliability concerns.

## B108: Hardcoded Temporary Directory

**Severity**: LOW

**What It Detects**: Using hardcoded paths like `/tmp` or `C:\temp` instead of platform-independent temporary directories.

### When This Is a Vulnerability

Hardcoded paths:

- Not portable across operating systems
- May conflict with other applications
- Don't follow platform conventions

```python
# VULNERABLE - Hardcoded /tmp
import os

tmpdir = "/tmp/myapp"
os.makedirs(tmpdir, exist_ok=True)

# VULNERABLE - Hardcoded Windows path
tmpdir = "C:\\temp\\myapp"
```

### How to Fix

**Use tempfile Module**:

```python
import tempfile
import os

# RIGHT - Platform-independent temp directory
tmpdir = tempfile.mkdtemp(prefix="myapp_")

# RIGHT - Within system temp directory
tmpdir = os.path.join(tempfile.gettempdir(), "myapp")
os.makedirs(tmpdir, exist_ok=True)

# Clean up when done
import shutil

shutil.rmtree(tmpdir)
```

---

## B110: Try/Except Pass

**Severity**: LOW

**What It Detects**: Using `try/except` blocks that silently ignore all exceptions with `pass`.

### When This Is a Vulnerability

Silent exception suppression:

- Hides unexpected errors
- Makes debugging difficult
- Could mask security-related issues

```python
# VULNERABLE - Silent exception hiding
try:
    connect_to_database()
except Exception:
    pass  # Silently ignores ALL errors!

# Later, code continues assuming connection succeeded
execute_query("SELECT * FROM users")  # May fail silently
```

### How to Fix

**Handle Exceptions Explicitly**:

```python
import logging

# RIGHT - Log the error
try:
    connect_to_database()
except ConnectionError as e:
    logging.error(f"Database connection failed: {e}")
    raise  # Re-raise to fail fast

# RIGHT - Handle specific exception types
try:
    parse_config()
except FileNotFoundError:
    logging.warning("Config file not found, using defaults")
except ValueError as e:
    logging.error(f"Invalid config: {e}")
    raise

# RIGHT - Set a flag or default value
result = None
try:
    result = fetch_from_cache()
except (ConnectionError, TimeoutError):
    logging.debug("Cache unavailable, using fallback")
    result = None  # Will trigger fallback logic below
```

---

## B111: Execute with Run as Root

**Severity**: MEDIUM

**What It Detects**: Using subprocess with `run_as_root=True` or `elevated_privileges=True` settings.

### When This Is a Vulnerability

Running code with elevated privileges:

- Increases impact of any vulnerability
- Allows privilege escalation attacks
- Unnecessary for most operations

```python
# VULNERABLE - Running as root
subprocess.run(
    ["script.sh"],
    run_as_root=True,  # Dangerous!
)
```

### How to Fix

**Avoid Elevated Privileges**:

```python
import subprocess
import os

# RIGHT - Run with normal privileges
subprocess.run(["script.sh"], check=True)

# RIGHT - Use sudo only when necessary with explicit validation
import shlex


def run_sudo_command(command_args):
    """Run command with sudo only if absolutely necessary."""
    # MUST validate command thoroughly
    allowed_commands = ["/usr/bin/systemctl", "/usr/bin/reboot"]

    if command_args[0] not in allowed_commands:
        raise ValueError(f"Command {command_args[0]} not allowed with sudo")

    # Use sudoers file to grant specific commands without password
    subprocess.run(["sudo"] + command_args, check=True)
```

---

## B112: Try/Except Continue

**Severity**: LOW

**What It Detects**: Using `try/except` blocks that silently continue with `continue` in a loop.

### When This Is a Vulnerability

Similar to B110, this silently ignores errors:

```python
# VULNERABLE - Silent error in loop
for user in users:
    try:
        process_user(user)
    except Exception:
        continue  # Silently skip errors!
```

### How to Fix

**Handle Exceptions Explicitly**:

```python
import logging

# RIGHT - Log and handle specific exceptions
for user in users:
    try:
        process_user(user)
    except InvalidUserError as e:
        logging.warning(f"Skipping invalid user {user.id}: {e}")
        continue
    except ProcessingError as e:
        logging.error(f"Error processing user {user.id}: {e}")
        raise  # Stop on critical error

# RIGHT - Track failures
failed_users = []
for user in users:
    try:
        process_user(user)
    except Exception as e:
        logging.error(f"Failed to process user {user.id}: {e}")
        failed_users.append((user.id, str(e)))

if failed_users:
    logging.warning(f"Processing completed with {len(failed_users)} failures")
    # Handle failures appropriately
```

---

## B113: Request Without Timeout

**Severity**: MEDIUM

**What It Detects**: Making HTTP requests without setting a timeout, which can hang indefinitely.

### When This Is a Vulnerability

Requests without timeouts:

- Can hang indefinitely on network issues
- Enable Slowloris attacks (slow client attacks)
- Waste server resources

```python
# VULNERABLE - No timeout
import requests

response = requests.get("https://api.example.com/data")  # Could hang forever!

# VULNERABLE - Implicit None timeout
response = requests.get(url, timeout=None)  # Same as no timeout
```

### How to Fix

**Always Set Timeouts**:

```python
import requests
import urllib3

# RIGHT - Set reasonable timeout
response = requests.get("https://api.example.com/data", timeout=10)

# RIGHT - Separate connect and read timeouts
response = requests.get(
    "https://api.example.com/data",
    timeout=(3.05, 10),  # (connect_timeout, read_timeout)
)

# RIGHT - For urllib3
http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=3, read=10))
response = http.request("GET", "https://api.example.com/data")

# Guidelines for timeout values
# - connect timeout: 3-5 seconds (how long to establish connection)
# - read timeout: 10-30 seconds (how long to wait for response)
# Adjust based on API performance expectations
```

---

## B613: Trojansource

**Severity**: MEDIUM

**What It Detects**: Source code containing homoglyph characters or bidirectional override characters that could be used for trojansource attacks.

### When This Is a Vulnerability

Trojansource attacks use Unicode characters to hide malicious code in source files:

```python
# VULNERABLE (conceptual) - Unicode override character
# Could make visible code appear different from actual execution
result = safe_check()  # ← Could contain hidden character
```

### How to Fix

**Use Linters and Code Review**:

```python
# RIGHT - Use tools to detect trojansource
# 1. Enable flake8 plugin: flake8-bandit
# 2. Use commitizen or pre-commit hooks
# 3. Code review process

# In .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: "1.7.5"
    hooks:
      - id: bandit
```

**Code Review Practices**:

- Review source code in text editors without special Unicode rendering
- Use git diff to verify actual character codes
- Use tools like `chardet` to verify file encoding

```bash
# Check for suspicious characters
file -i yourfile.py
chardet yourfile.py
```

---

See also: [index.md](./index.md) for all Bandit security checks.
