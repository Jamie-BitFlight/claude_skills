---
title: 'python-dotenv: Environment Variable Management for Python'
library_name: python-dotenv
pypi_package: python-dotenv
category: configuration
python_compatibility: 3.9+
last_updated: '2025-11-02'
official_docs: https://github.com/theskumar/python-dotenv#readme
official_repository: https://github.com/theskumar/python-dotenv
maintenance_status: active
---

# python-dotenv: Environment Variable Management for Python

## Core Purpose

python-dotenv reads key-value pairs from a `.env` file and can set them as environment variables. It helps in the development of applications following the [12-factor app](https://12factor.net/) principles.

### Problem Solved

The model must state that python-dotenv addresses development environment configuration challenges by enabling loading of environment variables from `.env` files, eliminating the need to manually set environment variables before running applications during local development.

Without python-dotenv, developers would need to:

- Manually export environment variables in shell sessions before running applications
- Hardcode configuration values in source code (security risk)
- Write custom file-reading and environment-setting code (reinventing the wheel)
- Maintain separate shell scripts for different environments

### 12-Factor App Methodology

The model must verify that python-dotenv implements the configuration principle from the 12-factor methodology: "Store config in the environment." This separation of configuration from code enables:

- Different configurations per environment (development, staging, production)
- No credentials in version control
- Configuration changes without code deployment
- Portable code across environments

## Official Information

The model must cite the following verified sources:

- **PyPI Package**: `python-dotenv` @ <https://pypi.org/project/python-dotenv/>
- **Version**: 1.1.1 (verified 2025-10-21)
- **Repository**: <https://github.com/theskumar/python-dotenv>
- **Stars**: 8,443+ GitHub stars
- **License**: BSD-3-Clause
- **Maintenance**: Production/Stable status, actively maintained by Saurabh Kumar and Bertrand Bonnefoy-Claudet
- **Python Support**: 3.9, 3.10, 3.11, 3.12, 3.13 + PyPy

## Python Version Compatibility

The model must state the following compatibility information from setup.py:

| Python Version | Support Status | Notes                         |
| -------------- | -------------- | ----------------------------- |
| 3.9            | Supported      | Minimum version               |
| 3.10           | Supported      | Full support                  |
| 3.11           | Supported      | Full support                  |
| 3.12           | Supported      | Full support                  |
| 3.13           | Supported      | Latest version                |
| 3.14           | Expected       | No breaking changes expected  |
| PyPy           | Supported      | PyPy implementation supported |

The model must verify that python-dotenv has no version-specific features and works identically across supported Python versions.

## Installation

```bash
# Basic installation
pip install python-dotenv

# With CLI support
pip install "python-dotenv[cli]"
```

## Usage Examples

### Basic .env File Loading

The model must demonstrate the standard pattern from official documentation:

```python
# app.py
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# Access environment variables
database_url = os.getenv("DATABASE_URL")
api_key = os.getenv("API_KEY")
debug = os.getenv("DEBUG", "False") == "True"
```

Corresponding `.env` file:

```bash
# .env
DATABASE_URL=postgresql://localhost/mydb
API_KEY=secret_key_12345
DEBUG=True
```

### Advanced Configuration Management

The model must show the dictionary-based pattern for merging multiple configuration sources:

```python
from dotenv import dotenv_values
import os

config = {
    **dotenv_values(".env.shared"),  # load shared development variables
    **dotenv_values(".env.secret"),  # load sensitive variables
    **os.environ,  # override with environment variables
}

# Access with priority: os.environ > .env.secret > .env.shared
database_url = config["DATABASE_URL"]
```

### Multi-Environment Loading

The model must demonstrate environment-specific configuration loading:

```python
from dotenv import load_dotenv, find_dotenv
import os

# Determine environment
env = os.getenv("ENVIRONMENT", "development")
dotenv_path = f".env.{env}"

# Load environment-specific file
load_dotenv(dotenv_path=dotenv_path)

# .env.development, .env.staging, .env.production
```

### Variable Expansion with Defaults

The model must show POSIX-style variable interpolation:

```bash
# .env with variable expansion
DOMAIN=example.org
EMAIL=admin@${DOMAIN}
API_URL=https://${DOMAIN}/api

# Default values for missing variables
DATABASE_HOST=${DB_HOST:-localhost}
DATABASE_PORT=${DB_PORT:-5432}
REDIS_URL=redis://${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}
```

### IPython/Jupyter Integration

The model must demonstrate the IPython extension usage:

```python
# In Jupyter notebook
%load_ext dotenv
%dotenv

# Load specific file
%dotenv /path/to/.env.local

# Override existing variables
%dotenv -o

# Verbose output
%dotenv -v
```

### CLI Usage

The model must show command-line interface examples:

```bash
# Set variables
dotenv set DATABASE_URL "postgresql://localhost/mydb"
dotenv set API_KEY "secret_key_123"

# Get specific value
dotenv get API_KEY

# List all variables
dotenv list

# List as JSON
dotenv list --format=json

# Run command with loaded environment
dotenv run -- python manage.py runserver
dotenv run -- pytest tests/
```

## Integration Patterns

### Django Integration

The model must demonstrate Django integration in manage.py and settings.py:

```python
# manage.py
import os
import sys
from dotenv import load_dotenv

if __name__ == "__main__":
    # Load .env before Django imports settings
    load_dotenv()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
```

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}
```

### Flask Integration

The model must show Flask application factory pattern:

```python
# app.py or __init__.py
from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "False") == "True"

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
```

### FastAPI Integration

The model must demonstrate Pydantic Settings integration:

```python
# config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

```python
# main.py
from fastapi import FastAPI
from config import settings

app = FastAPI(debug=settings.debug)


@app.get("/")
def read_root():
    return {"database": settings.database_url}
```

### Docker and Container Integration

The model must show Docker integration with environment variable precedence:

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# .env file is included in image for defaults
# But container env vars take precedence
CMD ["python", "app.py"]
```

```python
# app.py with override=False (default)
from dotenv import load_dotenv
import os

# Precedence: Docker env vars > .env file
load_dotenv(override=False)

# This respects container-injected variables
database_url = os.getenv("DATABASE_URL")
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://db/production
      - DEBUG=False
    # Container env vars override .env file
```

### Environment Variable Precedence

The model must explain the precedence rules:

**With `load_dotenv(override=False)` (default)**:

1. Existing environment variables (highest priority)
2. Variables from .env file
3. Default values in code

**With `load_dotenv(override=True)`**:

1. Variables from .env file (highest priority)
2. Existing environment variables
3. Default values in code

## Real-World Examples

The model must cite verified GitHub repositories using python-dotenv:

1. **theskumar/python-dotenv** (8,443 stars)

   - Source repository with comprehensive examples
   - @github:theskumar/python-dotenv

2. **daveebbelaar/langchain-experiments** (1,104 stars)

   - LangChain AI applications with environment configuration
   - @github:daveebbelaar/langchain-experiments

3. **iam-veeramalla/python-for-devops** (3,994 stars)

   - DevOps automation scripts using dotenv
   - @github:iam-veeramalla/python-for-devops

4. **AgentOps-AI/agentops** (4,978 stars)
   - AI agent monitoring with environment configuration
   - @github:AgentOps-AI/agentops

Common pattern observed across repositories:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")
```

## When to Use python-dotenv

The model must create a decision matrix based on verified use cases:

### Use python-dotenv when

- **Local Development**: Managing configuration during development where setting environment variables manually is impractical
- **Multiple Developers**: Team needs consistent local environment setup without sharing credentials in version control
- **Multiple Environments**: Application runs in development, staging, production with different configurations
- **Third-Party Services**: Application integrates with APIs requiring secret keys
- **Framework Integration**: Using Django, Flask, FastAPI where .env files are standard practice
- **CI/CD Pipelines**: Testing with different configurations in continuous integration
- **Jupyter Notebooks**: Interactive development requiring API keys and configuration
- **Docker Development**: Local development with Docker where .env provides defaults but containers can override
- **12-Factor Applications**: Following cloud-native application design principles

The model must verify these scenarios from real-world usage patterns in GitHub repositories.

## When NOT to Use python-dotenv

The model must state limitations and alternative approaches:

### Do NOT use python-dotenv when

1. **Production Secrets Management**:

   - Problem: .env files are plaintext and not encrypted
   - Alternative: Use HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager
   - Reason: Production secrets require encryption, rotation, audit logging, and access control

2. **Native Environment Variables Sufficient**:

   - Problem: Adds unnecessary dependency for simple cases
   - Alternative: Use `os.environ` directly
   - Reason: If environment already provides all variables, loading from file is redundant

3. **Compiled Applications**:

   - Problem: .env files must be distributed with application
   - Alternative: Bake configuration into build or use external configuration service
   - Reason: Compiled/packaged applications should not rely on external files

4. **Read-Only Filesystems**:

   - Problem: Cannot read .env file from disk
   - Alternative: Use environment variables directly
   - Reason: Some container runtimes and serverless platforms use read-only filesystems

5. **Complex Configuration Schemas**:

   - Problem: .env files only support string key-value pairs
   - Alternative: Use YAML, TOML, JSON with schema validation
   - Reason: Complex nested configuration requires structured formats

6. **Dynamic Configuration**:

   - Problem: .env files are loaded once at startup
   - Alternative: Use configuration management service (Consul, etcd)
   - Reason: Applications requiring runtime configuration updates need dynamic sources

7. **Distributed Systems Coordination**:
   - Problem: Each service would need its own .env file
   - Alternative: Use centralized configuration service
   - Reason: Distributed systems need synchronized configuration updates

## Decision Guidance Matrix

The model must provide deterministic decision criteria:

<eg>
┌─────────────────────────────────┬──────────────────┬───────────────────┐
│ Scenario                        │ Use dotenv?      │ Alternative       │
├─────────────────────────────────┼──────────────────┼───────────────────┤
│ Local development               │ YES              │ N/A               │
│ Development with team           │ YES              │ N/A               │
│ CI/CD testing                   │ YES              │ N/A               │
│ Docker local development        │ YES              │ N/A               │
│ Jupyter notebooks               │ YES              │ N/A               │
│ Production deployments          │ NO               │ Secrets manager   │
│ Production secrets storage      │ NO               │ Vault/KMS         │
│ Simple scripts (no secrets)     │ NO               │ os.environ        │
│ Complex nested config           │ NO               │ YAML/TOML         │
│ Dynamic config updates          │ NO               │ Consul/etcd       │
│ Serverless functions            │ MAYBE            │ Cloud env vars    │
│ Distributed systems             │ NO               │ Config service    │
└─────────────────────────────────┴──────────────────┴───────────────────┘
</eg>

## File Format Reference

The model must document the supported .env syntax from official documentation:

```bash
# Basic key-value pairs
API_KEY=secret123
PORT=8080
DEBUG=true

# Quoted values
DATABASE_URL='postgresql://localhost/mydb'
APP_NAME="My Application"

# Multiline values (quoted)
CERTIFICATE="-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL0UG+mRbzMMA0GCSqGSIb3DQEBCwUA
-----END CERTIFICATE-----"

# Comments
# This is a comment
LOG_LEVEL=INFO  # Inline comment

# Export directive (optional, no effect on parsing)
export PATH_EXTENSION=/usr/local/bin

# Variable expansion with POSIX syntax
DOMAIN=example.org
EMAIL=admin@${DOMAIN}
API_URL=https://${DOMAIN}/api

# Default values for missing variables
DATABASE_HOST=${DB_HOST:-localhost}
DATABASE_PORT=${DB_PORT:-5432}

# Escape sequences in double quotes
MESSAGE="Line 1\nLine 2\nLine 3"
TABS="Column1\tColumn2\tColumn3"
QUOTE="He said \"Hello\""

# Escape sequences in single quotes (only \\ and \')
PATH='C:\\Users\\Admin'
NAME='O\'Brien'

# Empty values
EMPTY_STRING=
EMPTY_VAR

# Spaces around = are ignored
REDIS_URL = redis://localhost:6379
```

Supported escape sequences:

- Double quotes: `\\`, `\'`, `\"`, `\a`, `\b`, `\f`, `\n`, `\r`, `\t`, `\v`
- Single quotes: `\\`, `\'`

## API Reference Summary

The model must list core functions from verified documentation:

| Function                                                                                                     | Purpose                   | Returns        | Common Use           |
| ------------------------------------------------------------------------------------------------------------ | ------------------------- | -------------- | -------------------- |
| `load_dotenv(dotenv_path=None, stream=None, verbose=False, override=False, interpolate=True, encoding=None)` | Load .env into os.environ | bool (success) | Application startup  |
| `dotenv_values(dotenv_path=None, stream=None, verbose=False, interpolate=True, encoding=None)`               | Parse .env to dict        | dict           | Config merging       |
| `find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)`                                 | Search for .env file      | str (path)     | Auto-discovery       |
| `get_key(dotenv_path, key_to_get, encoding=None)`                                                            | Get single value          | str or None    | Read specific key    |
| `set_key(dotenv_path, key_to_set, value_to_set, quote_mode='always', export=False, encoding=None)`           | Write key-value           | tuple          | Programmatic updates |
| `unset_key(dotenv_path, key_to_unset, encoding=None)`                                                        | Remove key                | tuple          | Cleanup              |

## Related Libraries

The model must cite verified alternatives from GitHub repository:

- **django-environ**: Django-specific with type coercion (@github:joke2k/django-environ)
- **python-decouple**: Strict separation with type casting (@github:HBNetwork/python-decouple)
- **environs**: Marshmallow-based validation (@github:sloria/environs)
- **dynaconf**: Multi-format with layered settings (@github:rochacbruno/dynaconf)
- **pydantic-settings**: Type-safe with Pydantic models (recommended for FastAPI)

The model must state that python-dotenv is the most widely adopted for simple .env loading.

## Best Practices

The model must recommend the following verified patterns:

1. **Never commit .env to version control**

   ```bash
   # .gitignore
   .env
   .env.local
   .env.*.local
   ```

2. **Provide .env.example for documentation**

   ```bash
   # .env.example
   DATABASE_URL=postgresql://localhost/mydb
   API_KEY=your_api_key_here
   DEBUG=False
   ```

3. **Load at application entry point**

   ```python
   # Load once at startup, not in modules
   if __name__ == "__main__":
       from dotenv import load_dotenv

       load_dotenv()
       main()
   ```

4. **Use override=False for production precedence**

   ```python
   # Let container/server env vars override .env
   load_dotenv(override=False)
   ```

5. **Validate required variables**

   ```python
   from dotenv import load_dotenv
   import os

   load_dotenv()

   required_vars = ["DATABASE_URL", "API_KEY", "SECRET_KEY"]
   missing = [var for var in required_vars if not os.getenv(var)]

   if missing:
       raise ValueError(f"Missing required environment variables: {missing}")
   ```

6. **Use type conversion explicitly**
   ```python
   # python-dotenv returns strings only
   DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
   PORT = int(os.getenv("PORT", "8000"))
   TIMEOUT = float(os.getenv("TIMEOUT", "30.0"))
   ```

## Common Pitfalls

The model must warn about verified issues:

1. **Strings only**: All values are strings, must convert to int/bool/float manually
2. **Load timing**: Must load before importing modules that use environment variables
3. **Override behavior**: Default `override=False` means existing env vars take precedence
4. **Variable expansion**: Disabled with `interpolate=False`, check if this is needed
5. **Production secrets**: Never use .env files for production secret storage

## Verification

The model must self-check the following criteria:

- All sections present and complete
- Code examples tested against python-dotenv 1.1.1 documentation
- Sources cited with @ references
- Decision matrix provides deterministic guidance
- No claims about functionality without documentation verification
- Python version compatibility verified from setup.py
- Real-world examples from GitHub repositories with star counts
- Integration patterns match framework documentation
- Security warnings included for production usage

## Summary

The model must state that python-dotenv is the standard Python library for loading environment variables from .env files during development. It implements 12-factor app configuration principles, supports Python 3.9-3.13, and integrates with Django, Flask, FastAPI, and other frameworks. The library is suitable for development and testing environments but should not be used for production secrets management. For production deployments, environment variables should be injected by container orchestration or cloud platforms, with secrets managed by dedicated secrets management services.
