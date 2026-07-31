# Cryptography and Hashing

Weak or broken cryptographic algorithms expose data to decryption, collision attacks, and other cryptographic failures. Modern standards require specific algorithms and key sizes.

## B303: MD5 and Weak Hash Functions

**Severity**: MEDIUM

**What It Detects**: Use of MD2, MD4, MD5, or SHA1 for cryptographic purposes, or weak hash algorithms in any cryptography library.

### When This Is a Vulnerability

MD5, SHA1, and other weak algorithms have known cryptographic breaks:

- **MD5**: Collision attacks allow generating two different inputs with the same hash
- **SHA1**: Practical collision attacks have been demonstrated
- These are unsuitable for:
  - Password hashing
  - Digital signatures
  - Message authentication
  - Integrity verification where collision resistance matters

```python
# VULNERABLE - MD5 hashing
import hashlib

user_password_hash = hashlib.md5(user_password.encode()).hexdigest()

# VULNERABLE - SHA1 (also broken)
file_signature = hashlib.sha1(file_content).hexdigest()

# VULNERABLE - In django.contrib.auth (older versions)
from django.contrib.auth.hashers import MD5PasswordHasher

hasher = MD5PasswordHasher()

# VULNERABLE - Using hashlib.new with weak algorithm
hash_obj = hashlib.new("md5")
hash_obj.update(data)
```

### When This Is NOT a Vulnerability

MD5 and SHA1 are acceptable only for:

- **Non-security purposes**: checksums for data integrity verification (not security)
- **Legacy systems**: when compatibility is unavoidable (temporary, with migration plan)
- **Compatibility hashes**: alongside modern secure hashing

```python
# Safe - MD5 for non-security checksum
import hashlib

file_checksum = hashlib.md5(file_content).hexdigest()  # For deduplication, not security

# Safe - SHA256 for security
secure_hash = hashlib.sha256(password.encode()).hexdigest()
```

### How to Fix

**For Password Hashing (Most Important)**:

```python
# WRONG - MD5
import hashlib

hashed = hashlib.md5(password.encode()).hexdigest()

# RIGHT - Use bcrypt (recommended)
import bcrypt

hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# RIGHT - Use argon2 (excellent for passwords)
from argon2 import PasswordHasher

ph = PasswordHasher()
hashed = ph.hash(password)

# RIGHT - Use scrypt
from hashlib import scrypt

hashed = scrypt(password.encode(), salt=os.urandom(32), n=2**14, r=8, p=1)
```

**For Data Integrity (Non-Security)**:

```python
import hashlib

# Instead of MD5
# hashed = hashlib.md5(data).hexdigest()

# Use SHA256
hashed = hashlib.sha256(data).hexdigest()

# Or for HMAC-based integrity
import hmac

signature = hmac.new(secret_key, data, hashlib.sha256).hexdigest()
```

**For Digital Signatures**:

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# WRONG - SHA1
signature = private_key.sign(data, padding.PSS(...), hashes.SHA1())

# RIGHT - SHA256 or stronger
signature = private_key.sign(data, padding.PSS(...), hashes.SHA256())
```

---

## B304: Insecure Cipher

**Severity**: HIGH

**What It Detects**: Use of weak or deprecated encryption algorithms like DES, 3DES, ARC2, ARC4, Blowfish, or XOR.

### When This Is a Vulnerability

Weak ciphers are vulnerable to:

- **DES/3DES**: Brute-force attacks (64-bit key space)
- **ARC4**: Known biases in key scheduling
- **Blowfish**: Only 64-bit block size (prone to birthday attacks)
- **Any XOR**: No real encryption security
- **ECB mode**: Identical plaintext blocks produce identical ciphertext

```python
# VULNERABLE - DES cipher
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

cipher = Cipher(algorithms.TripleDES(key), modes.CBC(iv), backend=backend)

# VULNERABLE - Using PyCrypto (deprecated) with weak cipher
from Crypto.Cipher import DES

cipher = DES.new(key, DES.MODE_CBC, iv)

# VULNERABLE - Blowfish (64-bit block size is too small)
from Crypto.Cipher import Blowfish

cipher = Blowfish.new(key, Blowfish.MODE_ECB)
```

### When This Is a Vulnerability (Details)

- Any encryption using symmetric ciphers other than AES-128, AES-192, or AES-256
- Legacy encryption data that must be decrypted (migrating away)
- Test/development code that will reach production

### When This IS NOT a Vulnerability

Legacy decryption of older data (temporary):

```python
# Acceptable temporarily while migrating from DES to AES
def decrypt_legacy_data(ciphertext, key):
    """Decrypt data encrypted with DES (legacy only)."""
    # Should have immediate migration plan to AES
    from Crypto.Cipher import DES

    cipher = DES.new(key, DES.MODE_CBC, iv)
    return cipher.decrypt(ciphertext)
```

### How to Fix

**Use AES (Correct)**:

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os


def encrypt_with_aes(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt using AES-256-GCM (authenticated encryption)."""
    iv = os.urandom(12)  # 96-bit IV for GCM
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return iv + encryptor.tag + ciphertext  # Prepend IV and auth tag


def decrypt_with_aes(ciphertext_bundle: bytes, key: bytes) -> bytes:
    """Decrypt using AES-256-GCM."""
    iv = ciphertext_bundle[:12]
    tag = ciphertext_bundle[12:28]
    ciphertext = ciphertext_bundle[28:]

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()
```

**Using Modern Cryptography Library**:

```python
from cryptography.fernet import Fernet

# Fernet handles all encryption details securely
key = Fernet.generate_key()
cipher_suite = Fernet(key)
ciphertext = cipher_suite.encrypt(plaintext)
plaintext = cipher_suite.decrypt(ciphertext)
```

---

## B305: Insecure Cipher Mode

**Severity**: MEDIUM

**What It Detects**: Use of ECB (Electronic Code Book) mode, which doesn't provide proper encryption semantics.

### When This Is a Vulnerability

ECB mode encrypts each block independently, revealing patterns:

<eg>
Plaintext blocks:  [BLOCK_A] [BLOCK_A] [BLOCK_B]
ECB ciphertext:    [0x12AB]  [0x12AB]  [0x34CD]  <- identical blocks leak information!

CBC ciphertext:    [0x12AB]  [0x5F4E]  [0x7C91]  <- blocks are independent
</eg>

This leaks information about the plaintext structure.

```python
# VULNERABLE - ECB mode (don't do this)
from Crypto.Cipher import AES

cipher = AES.new(key, AES.MODE_ECB)  # ECB is bad!
ciphertext = cipher.encrypt(plaintext)
```

### When This IS NOT a Vulnerability

ECB is only acceptable for:

- Single-block encryption (one 16-byte block)
- Non-sensitive data

```python
# Safe - encrypting exactly one block
from Crypto.Cipher import AES

plaintext = b"1234567890123456"  # Exactly 16 bytes
cipher = AES.new(key, AES.MODE_ECB)
ciphertext = cipher.encrypt(plaintext)
```

### How to Fix

**Use CBC, CTR, or GCM Instead**:

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os


# Option 1: GCM (Galois/Counter Mode) - RECOMMENDED
def encrypt_gcm(key: bytes, plaintext: bytes) -> bytes:
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return iv + encryptor.tag + ciphertext


# Option 2: CBC (Cipher Block Chaining)
def encrypt_cbc(key: bytes, plaintext: bytes) -> bytes:
    from Crypto.Util.Padding import pad

    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext, AES.block_size)
    ciphertext = cipher.encrypt(padded)
    return iv + ciphertext


# Option 3: CTR (Counter Mode)
def encrypt_ctr(key: bytes, plaintext: bytes) -> bytes:
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CTR, nonce=iv)
    ciphertext = cipher.encrypt(plaintext)
    return iv + ciphertext
```

---

## B324: Hashlib with Insecure Configuration

**Severity**: MEDIUM

**What It Detects**: Using hashlib with `usedforsecurity=True` (or not specified) when using weak hash functions, or other insecure hash configurations.

### When This Is a Vulnerability

When explicitly using weak hashes for security purposes:

```python
# VULNERABLE - Explicitly weak hash for security
import hashlib

# Using MD5 with security intent
secure_hash = hashlib.md5(data, usedforsecurity=True)

# Using SHA1 with security intent
signature = hashlib.sha1(message, usedforsecurity=True)
```

### When This IS NOT a Vulnerability

Using weak hashes explicitly for non-security purposes:

```python
import hashlib

# Safe - explicitly non-security (e.g., content deduplication)
checksum = hashlib.md5(file_content, usedforsecurity=False)

# Safe - using secure hash for security
secure_hash = hashlib.sha256(password, usedforsecurity=True)
```

### How to Fix

```python
import hashlib

# If you need security, use SHA256 or stronger
# WRONG:
weak_hash = hashlib.md5(data, usedforsecurity=True)

# RIGHT:
secure_hash = hashlib.sha256(data, usedforsecurity=True)

# If using for non-security (e.g., checksums):
checksum = hashlib.md5(data, usedforsecurity=False)
```

---

## B505: Weak Cryptographic Key

**Severity**: MEDIUM

**What It Detects**: Generating cryptographic keys that are too short to provide adequate security.

### When This Is a Vulnerability

Weak keys are vulnerable to brute-force attacks:

- RSA keys < 2048 bits
- Elliptic curve keys < 224 bits
- Symmetric keys < 128 bits

```python
# VULNERABLE - Too short RSA key
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=512,  # Way too short! Should be 2048+
)

# VULNERABLE - Too short ECC key
from cryptography.hazmat.primitives.asymmetric import ec

private_key = ec.generate_private_key(ec.SECP192R1())  # Only 192 bits
```

### When This IS NOT a Vulnerability

Testing or temporary keys where security isn't critical:

```python
# Testing/demo - not for production
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=512,  # Only for testing/demos
)
```

### How to Fix

**Generate Proper Key Sizes**:

```python
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

# RSA: Use 2048 bits minimum (4096 recommended)
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,  # Minimum acceptable
)

# Elliptic Curve: Use P-256 (256-bit) or stronger
private_key = ec.generate_private_key(ec.SECP256R1())

# Symmetric keys: 128 bits minimum (256 recommended)
encryption_key = os.urandom(32)  # 256-bit key for AES
```

---

See also: [index.md](./index.md) for all Bandit security checks.
