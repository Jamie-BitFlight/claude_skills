# Dangerous Module Imports

Importing certain Python modules indicates security risks. While the import itself isn't necessarily dangerous, these modules are known to be vulnerable or frequently misused.

## B403-B404: Pickle and Subprocess Imports

**Severity**: LOW

**What It Detects**: Importing potentially dangerous modules like pickle, dill, shelve, and subprocess.

### When This Is a Vulnerability

These imports flag modules that can be dangerous if misused:

```python
# B403 - Pickle module (can execute code)
import pickle
from pickle import loads

# B404 - Subprocess module (shell injection risk)
import subprocess
from subprocess import Popen
```

### When This IS NOT a Vulnerability

Importing these modules is acceptable when used securely:

```python
# Safe - pickle your own data
import pickle

data = pickle.dumps(my_object)
restored = pickle.loads(data)  # Secure - your data

# Safe - subprocess with proper usage
import subprocess

subprocess.run(["ls", "-la"], check=True)  # No shell=True, safe
```

### Guidelines

See related security checks:

- [B301: Pickle Deserialization](./deserialization.md#b301-pickle-deserialization)
- [B602-B607: Subprocess Injection](./injection-command.md#b602-subprocess-with-shelltrue)

---

## B411: Import XMLRPC

**Severity**: HIGH

**What It Detects**: Importing `xmlrpc` module, particularly `xmlrpc.server` or `xmlrpc.client`.

### When This Is a Vulnerability

XMLRPC is vulnerable because:

- It transmits data over plaintext (without HTTPS)
- It uses XML (vulnerable to XXE)
- It's particularly dangerous for network communication

```python
# VULNERABLE - XMLRPC server
from xmlrpc.server import SimpleXMLRPCServer

# Listens on network, vulnerable to XXE attacks
server = SimpleXMLRPCServer(("0.0.0.0", 8000))

# VULNERABLE - XMLRPC client
from xmlrpc.client import ServerProxy

# Communicates over plaintext, data exposed
proxy = ServerProxy("http://example.com:8000/")  # Not encrypted!
response = proxy.some_method(user_data)
```

### When This IS NOT a Vulnerability

XMLRPC with proper security measures:

```python
# Better - Use REST API with JSON and HTTPS
import requests

response = requests.post(
    "https://example.com/api/endpoint",  # HTTPS encrypted
    json={"data": user_data},  # JSON instead of XML
)
```

### How to Fix

**Use REST APIs with HTTPS**:

```python
import requests

# RIGHT - REST API with HTTPS
response = requests.post(
    "https://api.example.com/v1/resource", json={"name": "value"}, headers={"Authorization": "Bearer token"}
)
data = response.json()

# RIGHT - Use gRPC for RPC needs
# Better security model than XMLRPC
```

---

## B412: Import HTTPoxy (CGI Handler)

**Severity**: HIGH

**What It Detects**: Importing CGI handlers vulnerable to HTTPoxy attack.

### When This Is a Vulnerability

HTTPoxy (CVE-2016-5385) exploits CGI and WSGI applications through the HTTP_PROXY environment variable:

```python
# VULNERABLE - Using CGI handler
from wsgiref.handlers import CGIHandler
from twisted.web.twcgi import CGIScript

# These are vulnerable to HTTPoxy
handler = CGIHandler()
cgi_script = CGIScript()
```

### How to Fix

**Use Modern WSGI Application Servers**:

```python
# RIGHT - Use modern application servers
# Instead of CGI, use:
# - Gunicorn
# - uWSGI
# - Waitress
# - Hypercorn

# In your application
from flask import Flask

app = Flask(__name__)

# Run with: gunicorn app:app
# NOT with CGI handlers
```

**If You Must Use CGI** (Deprecated):

```python
import os

# Clear HTTP_PROXY to prevent HTTPoxy
if "HTTP_PROXY" in os.environ:
    del os.environ["HTTP_PROXY"]

# Better: Don't use CGI at all
# Use modern WSGI instead
```

---

## B413: Import PyCrypto

**Severity**: HIGH

**What It Detects**: Importing the deprecated `pycrypto` library.

### When This Is a Vulnerability

PyCrypto (Crypto module) is deprecated due to:

- Lack of maintenance
- Known security issues
- Lack of modern cipher support
- Poor random number generation

```python
# VULNERABLE - Using deprecated PyCrypto
from Crypto.Cipher import AES, DES
from Crypto.PublicKey import RSA
from Crypto.Hash import MD5  # Also weak hash
```

### How to Fix

**Use cryptography Library**:

```python
# WRONG - PyCrypto
from Crypto.Cipher import AES

# RIGHT - cryptography library
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# For RSA
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# For hashing
from cryptography.hazmat.primitives import hashes

# Modern, maintained, secure
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
```

**Alternative: Use Fernet** (High-Level):

```python
from cryptography.fernet import Fernet

# Simple, secure encryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)
ciphertext = cipher_suite.encrypt(b"my data")
plaintext = cipher_suite.decrypt(ciphertext)
```

---

## B415: Import PyGHMI

**Severity**: HIGH

**What It Detects**: Importing `pyghmi` (Python Generic IPMI interface), which implements insecure IPMI protocol.

### When This Is a Vulnerability

IPMI (Intelligent Platform Management Interface) is considered insecure:

- Designed for local management, not remote security
- Vulnerable to network-based attacks
- Weak authentication mechanisms

```python
# VULNERABLE - Using IPMI
from pyghmi.ipmi import create_ipmi_console

# IPMI communication is insecure
console = create_ipmi_console(hostname="server.example.com")
```

### How to Fix

**Use Secure Out-of-Band Management**:

```python
# RIGHT - Use secure alternatives

# Option 1: SSH for remote administration
import paramiko

client = paramiko.SSHClient()
client.load_system_host_keys()
client.connect("server.example.com")
stdin, stdout, stderr = client.exec_command("reboot")

# Option 2: HTTPS-based management APIs
import requests

response = requests.post("https://mgmt.example.com:8443/api/reboot", auth=("admin", "password"), verify=True)

# Option 3: SSH + VPN for secure access
# Manage IPMI only through secure tunnel
```

---

See also: [index.md](./index.md) for all Bandit security checks.
