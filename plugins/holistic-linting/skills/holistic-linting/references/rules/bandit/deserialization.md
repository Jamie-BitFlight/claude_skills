# Deserialization Vulnerabilities

Unsafe deserialization of untrusted data allows attackers to execute arbitrary code. Python's pickle, marshal, and other serialization formats can include executable code.

## B301: Pickle Deserialization

**Severity**: MEDIUM

**What It Detects**: Using `pickle.load()`, `dill.load()`, `shelve`, or similar deserialization functions on untrusted data.

### When This Is a Vulnerability

Pickle files can contain arbitrary Python code that executes during deserialization:

```python
# VULNERABLE - Deserializing untrusted pickle data
import pickle

# Data from user upload, network, or file
untrusted_data = open("user_file.pkl", "rb").read()

# This can execute arbitrary code during unpickling
object = pickle.loads(untrusted_data)
```

### When This IS NOT a Vulnerability

- Deserializing only pickle files you created and control
- Deserializing data that's been cryptographically signed

```python
# Safe - data you created and control
my_object = MyClass()
pickled = pickle.dumps(my_object)
# Later, unpickling your own data is safe
restored = pickle.loads(pickled)

# Safe with signature verification
import hmac
import hashlib


def safe_loads(data, key):
    """Load pickle only if HMAC signature is valid."""
    signature = data[:32]
    payload = data[32:]

    expected_sig = hmac.new(key, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_sig):
        raise ValueError("Invalid signature")

    return pickle.loads(payload)
```

### How to Fix

**Use JSON for Simple Data**:

```python
import json

# WRONG - Pickle for untrusted data
user_data = pickle.loads(untrusted_bytes)

# RIGHT - JSON for untrusted data (safer by design)
user_data = json.loads(untrusted_string)

# JSON only supports basic types:
# - strings, numbers, booleans, null
# - lists, dicts
# Can't execute code
```

**Use restricted_loads() for Pickle** (If You Must Use Pickle):

```python
import pickle
import io


def restricted_loads(data):
    """Load pickle with restricted unpickler."""

    class RestrictedUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            # Only allow safe types
            SAFE_MODULES = {"__main__", "collections", "datetime"}

            if module not in SAFE_MODULES:
                raise pickle.UnpicklingError(f"Unpickling of module {module} is not allowed")
            return super().find_class(module, name)

    return RestrictedUnpickler(io.BytesIO(data)).load()
```

**Use Third-Party Libraries**:

```python
# Use msgpack (safer than pickle)
import msgpack

data = msgpack.packb({"user": "alice", "age": 30})
restored = msgpack.unpackb(data, raw=False)

# Use pydantic for validation
from pydantic import BaseModel, ValidationError


class User(BaseModel):
    username: str
    age: int


try:
    user = User(**json.loads(untrusted_json))
except ValidationError as e:
    print(f"Invalid data: {e}")
```

---

## B302: Marshal Deserialization

**Severity**: MEDIUM

**What It Detects**: Using `marshal.load()` or `marshal.loads()` on untrusted data.

### When This Is a Vulnerability

Marshal is Python's internal serialization format, used for bytecode:

```python
# VULNERABLE - Marshaling untrusted data
import marshal

untrusted_bytecode = open("user_code.pyc", "rb").read()

# This can execute compiled code
code_object = marshal.loads(untrusted_bytecode)
exec(code_object)
```

### How to Fix

**Use JSON or Safer Formats**:

```python
import json

# Instead of marshal, use JSON for data interchange
data = json.dumps({"result": 42})
restored = json.loads(data)
```

**If You Need Code Serialization**:

```python
# Use cloudpickle with validation
import cloudpickle


def safe_function_load(data, allowed_names):
    """Load function but verify it matches allowed list."""
    func = cloudpickle.loads(data)
    if func.__name__ not in allowed_names:
        raise ValueError(f"Function {func.__name__} not allowed")
    return func
```

---

## B506: YAML Load

**Severity**: HIGH

**What It Detects**: Using `yaml.load()` without a safe loader, allowing arbitrary code execution.

### When This Is a Vulnerability

`yaml.load()` with the default loader can execute arbitrary Python code:

```python
# VULNERABLE - Unsafe YAML deserialization
import yaml

untrusted_yaml = open("user_config.yaml").read()

# Can execute code via Python object tags
config = yaml.load(untrusted_yaml)
# YAML like: "!!python/object/apply:os.system ['rm -rf /']"
```

### When This IS NOT a Vulnerability

Using `ruamel.yaml` with `typ='safe'` is always safe:

```python
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
untrusted_yaml = open("user_config.yaml").read()

# Safe - can't execute code
config = yaml.load(untrusted_yaml)
```

### How to Fix

**Use ruamel.yaml safe mode**:

```python
from ruamel.yaml import YAML

yaml = YAML(typ="safe")

# WRONG - pyyaml default loader
# config = yaml_module.load(config_string)

# RIGHT - ruamel.yaml safe loader
config = yaml.load(config_string)
```

**For Custom YAML Types**:

```python
from ruamel.yaml import YAML
from datetime import datetime


def create_safe_yaml():
    """Create ruamel.yaml instance with safe custom types."""
    yaml = YAML(typ="safe")

    def date_constructor(loader, node):
        value = loader.construct_scalar(node)
        return datetime.fromisoformat(value)

    yaml.constructor.add_constructor("!date", date_constructor)
    return yaml


# Use custom safe loader
yaml = create_safe_yaml()
config = yaml.load(config_string)
```

---

See also: [index.md](./index.md) for all Bandit security checks.
