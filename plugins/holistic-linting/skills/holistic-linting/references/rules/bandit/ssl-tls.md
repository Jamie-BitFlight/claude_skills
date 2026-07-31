# SSL/TLS Configuration

Insecure SSL/TLS configurations, missing certificate validation, and outdated protocol versions expose applications to man-in-the-middle attacks and encryption failures.

## B501: Request with No Certificate Validation

**Severity**: HIGH

**What It Detects**: HTTP requests without verifying SSL/TLS certificates, allowing man-in-the-middle attacks.

### When This Is a Vulnerability

Without certificate validation, attackers can intercept and decrypt HTTPS traffic:

```python
# VULNERABLE - No certificate verification
import requests

response = requests.get("https://api.example.com", verify=False)
response = requests.get("https://api.example.com", verify="")  # Also bad

# VULNERABLE - Requests library default without proper setup
import urllib3

urllib3.disable_warnings()  # Disables SSL warnings

import requests

requests.get("https://api.example.com")  # If warnings were disabled
```

### When This IS NOT a Vulnerability

Certificate validation disabled only for:

- Local development with self-signed certificates (with proper documentation)
- Internal testing networks with explicit security review

```python
# Safe in development with documentation
# TODO: Remove before production - only for local development with self-signed certs
response = requests.get("https://localhost:8443", verify=False)
```

### How to Fix

**Enable Certificate Verification (Default)**:

```python
import requests

# RIGHT - Certificate verification enabled (default)
response = requests.get("https://api.example.com")
# Equivalent to: verify=True

# Explicit certificate verification
response = requests.get("https://api.example.com", verify=True)

# Custom certificate bundle
response = requests.get("https://api.example.com", verify="/path/to/ca-bundle.crt")
```

**For Development with Self-Signed Certificates**:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class SSLAdapter(HTTPAdapter):
    """Adapter for self-signed cert development (dev only)."""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = "CERT_NONE"
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


# Use only in development
session = requests.Session()
session.mount("https://", SSLAdapter())
response = session.get("https://localhost:8443")  # Self-signed cert OK here
```

---

## B502: SSL with Bad Version

**Severity**: HIGH

**What It Detects**: Explicitly specifying outdated SSL/TLS protocol versions (SSLv2, SSLv3, TLSv1.0, TLSv1.1).

### When This Is a Vulnerability

Old SSL/TLS versions have known cryptographic breaks:

- **SSLv2/v3**: Completely broken, removed from all modern libraries
- **TLSv1.0/v1.1**: Vulnerable to POODLE and other attacks, deprecated by major browsers

```python
# VULNERABLE - Explicitly using old TLS version
import ssl

context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1  # Too old!

# VULNERABLE - In Paramiko
import paramiko

client = paramiko.SSHClient()
client.get_transport().security_options.key_types = ["ssh-rsa"]
# Should also enforce minimum TLS 1.2+

# VULNERABLE - In urllib3
import urllib3

http = urllib3.PoolManager(
    ssl_version=ssl.PROTOCOL_TLSv1  # Wrong!
)
```

### When This IS NOT a Vulnerability

- Connecting to legacy systems requires explicit temporary version negotiation with migration plan
- Explicit documentation of why older versions are necessary

```python
# Acceptable with strong justification and timeline
# TODO: Migrate legacy system to TLS 1.2+
# Temporary: accepting TLSv1.0 from legacy device (deprecated in 2024)
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1
```

### How to Fix

**Use Modern TLS Versions**:

```python
import ssl

# CORRECT - Enforce TLS 1.2 minimum (Python 3.10+)
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
# Or TLSv1.3 if all clients support it
context.minimum_version = ssl.TLSVersion.TLSv1_3

# For Python 3.9 and earlier
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
```

**For Web Frameworks**:

```python
# Django
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Flask with SSL
from flask_talisman import Talisman

app = Flask(__name__)
Talisman(app, force_https=True)
```

---

## B503: SSL with Bad Defaults

**Severity**: MEDIUM

**What It Detects**: SSL/TLS context with insecure default cipher suites or configurations.

### When This Is a Vulnerability

Default cipher suites may include weak ciphers that allow attackers to downgrade connections:

```python
# VULNERABLE - Using default ciphers without hardening
import ssl

context = ssl.create_default_context()
# May include weak ciphers in older Python versions

# VULNERABLE - Setting insecure cipher list
context.set_ciphers("LOW:!aNULL:!eNULL:!EXPORT:!DES:!MD5")
```

### How to Fix

**Enforce Strong Cipher Suites**:

```python
import ssl

context = ssl.create_default_context()

# Explicitly set strong ciphers only
context.set_ciphers(
    ":".join([
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
    ])
)

# Disable problematic protocol versions
context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

# Enable additional security options
context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
context.options |= ssl.OP_NO_TICKET
```

---

## B504: SSL with No Version

**Severity**: MEDIUM

**What It Detects**: SSL/TLS context created without explicitly setting a protocol version, relying on system defaults.

### When This Is a Vulnerability

Not explicitly setting TLS version can result in negotiation of weak protocols on older systems:

```python
# VULNERABLE - No explicit TLS version
import ssl
import socket

sock = socket.socket()
context = ssl.SSLContext()  # No version specified - relies on system default
ssock = context.wrap_socket(sock, server_hostname="example.com")
```

### How to Fix

**Always Specify Minimum TLS Version**:

```python
import ssl

context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
# Explicitly require modern TLS version
```

---

## B507: SSH No Host Key Verification

**Severity**: HIGH

**What It Detects**: SSH connections without verifying the host key, vulnerable to man-in-the-middle attacks.

### When This Is a Vulnerability

Without host key verification, attackers can intercept SSH connections:

```python
# VULNERABLE - No host key verification
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Accepts any host key!

client.connect("example.com", username="user", password="pass")
stdin, stdout, stderr = client.exec_command("ls")
```

### When This IS NOT a Vulnerability

Explicitly accepting keys with strong justification:

```python
# Safe with known_hosts verification
import paramiko

client = paramiko.SSHClient()
client.load_system_host_keys()  # Uses system known_hosts
# This will reject unknown hosts
client.connect("example.com", username="user", password="pass")
```

### How to Fix

**Use known_hosts File**:

```python
import paramiko

client = paramiko.SSHClient()

# Load system known_hosts (requires prior SSH connection or manual addition)
client.load_system_host_keys()

# Or load custom known_hosts file
client.load_host_keys("/path/to/known_hosts")

# This will now reject unknown hosts
client.connect("example.com", username="user", password="pass")
```

**For First Connection**:

```python
import paramiko
import os

client = paramiko.SSHClient()

# Load existing known_hosts
known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
client.load_host_keys(known_hosts_file)

# Optional: add policy to auto-add new keys with CAUTION
# Only if you've verified the host fingerprint independently
# client.set_missing_host_key_policy(paramiko.WarningPolicy())

client.connect("example.com", username="user", password="pass")
```

---

## B508: SNMP Insecure Version

**Severity**: HIGH

**What It Detects**: Using SNMPv1 or SNMPv2c (community strings) instead of SNMPv3 (authenticated and encrypted).

### When This Is a Vulnerability

SNMPv1/v2c send community strings in cleartext:

```python
# VULNERABLE - SNMPv1/v2c with cleartext community string
from pysnmp.hlapi import *

errorIndication, errorStatus, errorIndex, varBinds = next(
    getCmd(
        SnmpEngine(),
        CommunityData("public"),  # Sent in cleartext!
        UdpTransportTarget(("example.com", 161)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
    )
)
```

### How to Fix

**Use SNMPv3 with Authentication and Encryption**:

```python
from pysnmp.hlapi import *

errorIndication, errorStatus, errorIndex, varBinds = next(
    getCmd(
        SnmpEngine(),
        UsmUserData(
            "username",
            "authPassword",  # Authentication password
            "privPassword",  # Privacy (encryption) password
            authProtocol=usmHMACSHAAuthProtocol,
            privProtocol=usmAesCfb128Protocol,
        ),
        UdpTransportTarget(("example.com", 161)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
    )
)
```

---

## B509: SNMP Weak Cryptography

**Severity**: MEDIUM

**What It Detects**: SNMPv3 with weak encryption algorithms or authentication mechanisms.

### When This Is a Vulnerability

Using DES encryption or weak authentication in SNMPv3:

```python
# VULNERABLE - DES encryption (weak)
from pysnmp.hlapi import *

UsmUserData(
    "username",
    "authPassword",
    "privPassword",
    authProtocol=usmHMAC96Md5AuthProtocol,  # MD5 auth (weak)
    privProtocol=usm3DESEDEPrivProtocol,  # 3DES (weak)
)
```

### How to Fix

**Use Strong SNMPv3 Algorithms**:

```python
from pysnmp.hlapi import *

# Correct - SHA and AES
UsmUserData(
    "username",
    "authPassword",
    "privPassword",
    authProtocol=usmHMACSHAAuthProtocol,  # SHA (strong)
    privProtocol=usmAesCfb128Protocol,  # AES-128 (strong)
)

# Or SHA-2 variants if available
# authProtocol=usmHMAC192Sha256AuthProtocol
# privProtocol=usmAesCfb256Protocol
```

---

See also: [index.md](./index.md) for all Bandit security checks.
