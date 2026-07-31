# Credentials and Secrets Management

Hardcoded passwords, API keys, access tokens, and other secrets should never be stored in source code. These checks identify secrets that could be exposed in version control, compiled bytecode, or when code is shared.

## B105: Hardcoded Password String

**Severity**: MEDIUM

**What It Detects**: String literals that appear to be passwords based on variable names or string content.

### When This Is a Vulnerability

Any password literal in source code is exposed to:

- Version control history (even after deletion)
- Accidental code sharing or open-source release
- Extraction from compiled Python bytecode
- Team members with repository access
- Anyone who reviews the code

```python
# VULNERABLE - Password hardcoded in string
database_password = "super_secret_password_123"
db_connection = connect(host="localhost", password="super_secret_password_123")


# VULNERABLE - In function arguments
def login(username, password="default_password"):
    authenticate(username, password)


# VULNERABLE - In configuration strings
config = {"db_password": "mypassword", "api_key": "sk_live_abc123xyz"}
```

### When This Is NOT a Vulnerability

- Placeholder strings in documentation or examples clearly marked as such
- Default test passwords in unit test files (though still risky)
- Non-sensitive strings that only look like passwords

```python
# NOT vulnerable - test-only placeholder marked clearly
TEST_PASSWORD = "test_password_do_not_use_in_production"  # Only for unit tests

# NOT vulnerable - clear documentation example
"""
Example:
    connect(password="your_password_here")
"""
```

### How to Fix

**Recommended Approaches**:

1. **Environment Variables** (Most Common)

```python
import os

database_password = os.environ.get("DB_PASSWORD")
db_connection = connect(host="localhost", password=database_password)
```

2. **Configuration Files** (Git-Ignored)

```python
import configparser

config = configparser.ConfigParser()
config.read("config.ini")  # Add config.ini to .gitignore
database_password = config.get("database", "password")
```

3. **Secrets Management Services**

```python
from aws_secretsmanager_caching import SecretCache

cache = SecretCache()
database_password = cache.get_secret_string("prod/db/password")
```

4. **.env Files with python-dotenv**

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads from .env (must be in .gitignore)
database_password = os.getenv("DB_PASSWORD")
```

---

## B106: Hardcoded Password Function Argument

**Severity**: MEDIUM

**What It Detects**: Function parameters with default values that appear to be passwords.

### When This Is a Vulnerability

Function arguments with password defaults expose secrets when:

- The function signature is visible in documentation or IDE tooltips
- The code is decompiled or analyzed statically
- The default is used accidentally in production

```python
# VULNERABLE - Password default in function signature
def connect_to_database(host, user, password="admin123"):
    """Connect to database."""
    # ...


# VULNERABLE - Even in private functions
def _internal_authenticate(api_key="sk_live_secret_key"):
    return validate(api_key)
```

### When This Is NOT a Vulnerability

- Functions that explicitly don't accept production credentials
- Test fixtures where passwords are clearly non-production

```python
# Safe in test files
def test_login(username, password="test_user_password"):
    result = authenticate(username, password)
    assert result is True
```

### How to Fix

**Remove Default Arguments**:

```python
import os


def connect_to_database(host, user, password=None):
    """Connect to database."""
    if password is None:
        password = os.environ.get("DB_PASSWORD")

    if not password:
        raise ValueError("Database password required. Set DB_PASSWORD environment variable.")

    # ... connection logic
```

**For Configuration-Heavy Functions**:

```python
from dataclasses import dataclass
import os


@dataclass
class DatabaseConfig:
    host: str
    user: str
    password: str = None

    def __post_init__(self):
        if self.password is None:
            self.password = os.environ.get("DB_PASSWORD")


def connect_to_database(config: DatabaseConfig):
    """Connect using config object."""
    # ... connection logic
```

---

## B107: Hardcoded Password Default Value

**Severity**: MEDIUM

**What It Detects**: Hardcoded default values for parameters in assignment statements, even outside function signatures.

### When This Is a Vulnerability

This catches hardcoded password assignments in variable initialization:

```python
# VULNERABLE - Direct assignment with hardcoded default
DEFAULT_PASSWORD = "hardcoded_password"
admin_password = admin_password or "fallback_admin_pass"


# VULNERABLE - In class defaults
class DatabaseConnector:
    password = "default_password"
```

### When This Is NOT a Vulnerability

- Variables with secure defaults from other sources
- Variables that are explicitly overridden at runtime

```python
# Safe - password sourced from environment
DEFAULT_PASSWORD = os.environ.get("DB_PASSWORD", "")

# Safe - placeholder clearly marked
EXAMPLE_PASSWORD = "your_password_here"  # Do not use in production
```

### How to Fix

```python
import os

# Instead of:
# DEFAULT_PASSWORD = "hardcoded_password"

# Use:
DEFAULT_PASSWORD = os.environ.get("DB_PASSWORD")
if not DEFAULT_PASSWORD:
    raise RuntimeError("DB_PASSWORD environment variable must be set")


class DatabaseConnector:
    def __init__(self, password=None):
        self.password = password or os.environ.get("DB_PASSWORD")
```

---

## B109: Password Config Option Not Marked Secret

**Severity**: MEDIUM

**What It Detects**: Configuration options that look like passwords but aren't marked as sensitive/secret in configuration frameworks.

### When This Is a Vulnerability

Configuration systems may log or display all values by default. Without marking a field as secret, passwords could appear in:

- Log files
- Configuration export dumps
- Debug output
- Monitoring systems

```python
# VULNERABLE - Django settings without secret_key protection
PASSWORD_FIELD = "user_password"  # Not marked as secret

# VULNERABLE - Flask config without SECRET marking
FLASK_PASSWORD = "app_password"

# VULNERABLE - SQLAlchemy without masking
DATABASE_PASSWORD = "connection_password"
```

### When This Is NOT a Vulnerability

- Configuration fields that genuinely aren't passwords
- Third-party configurations that handle marking automatically

```python
# Safe - third-party libraries handle this
from some_library import Config

config = Config(password="from_env_or_secret_manager")  # Handled by library
```

### How to Fix

**For Django**:

```python
# Mark secrets in settings
from django.core.management.utils import get_random_secret_key

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "PASSWORD": os.environ.get("DB_PASSWORD"),  # Environment variable
    }
}
```

**For Flask**:

```python
import os


class Config:
    """Configuration marked with environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    API_KEY = os.environ.get("API_KEY")
```

**For Custom Configurations**:

```python
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SecureConfig:
    """Configuration with marked secrets."""

    database_password: Optional[str] = field(default=None, metadata={"secret": True})
    api_key: Optional[str] = field(default=None, metadata={"secret": True})

    def __post_init__(self):
        if self.database_password is None:
            self.database_password = os.environ.get("DB_PASSWORD")
        if self.api_key is None:
            self.api_key = os.environ.get("API_KEY")
```

---

## B401: Import Telnetlib

**Severity**: HIGH

**What It Detects**: Importing the `telnetlib` module.

### When This Is a Vulnerability

Telnet transmits all data, including passwords, in cleartext. An attacker on the network can intercept:

- Login credentials
- Commands being executed
- Response data

```python
# VULNERABLE - Telnet import
import telnetlib


def remote_command(host, username, password, command):
    tn = telnetlib.Telnet(host)
    tn.read_until(b"login: ")
    tn.write(username.encode() + b"\n")
    tn.read_until(b"Password: ")
    tn.write(password.encode() + b"\n")  # Sent in cleartext!
    # ...
```

### When This Is NOT a Vulnerability

Telnet should never be used in production systems. Even in isolated networks, SSH is superior.

### How to Fix

**Use SSH/Paramiko Instead**:

```python
import paramiko


def remote_command(host, username, password, command):
    """Execute remote command over SSH (encrypted)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        return stdout.read().decode()
    finally:
        client.close()
```

**For System Administration**:

```python
import subprocess


def remote_command(host, username, command):
    """Execute remote command via SSH subprocess."""
    cmd = ["ssh", f"{username}@{host}", command]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout
```

---

## B402: Import FTPlib

**Severity**: HIGH

**What It Detects**: Importing the `ftplib` module.

### When This Is a Vulnerability

FTP transmits credentials and data in plaintext:

- Login credentials visible on the network
- File contents transmitted unencrypted
- Vulnerable to man-in-the-middle attacks

```python
# VULNERABLE - FTP with cleartext credentials
import ftplib


def upload_file(host, username, password, local_file, remote_file):
    ftp = ftplib.FTP(host)
    ftp.login(username, password)  # Credentials in cleartext!
    with open(local_file, "rb") as f:
        ftp.storbinary(f"STOR {remote_file}", f)
    ftp.quit()
```

### When This Is NOT a Vulnerability

FTP should not be used. Even FTPS (FTP over SSL) is deprecated in favor of SFTP.

### How to Fix

**Use SFTP (SSH File Transfer Protocol)**:

```python
import paramiko
from io import BytesIO


def upload_file(host, username, password, local_file, remote_file):
    """Upload file via SFTP (encrypted)."""
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        sftp.put(local_file, remote_file)
    finally:
        sftp.close()
        transport.close()
```

**Using SSH-based Tools**:

```python
import subprocess


def upload_file(host, username, local_file, remote_file):
    """Upload file via scp (SSH copy)."""
    cmd = ["scp", local_file, f"{username}@{host}:{remote_file}"]
    subprocess.run(cmd, check=True)
```

---

See also: [index.md](./index.md) for all Bandit security checks.
