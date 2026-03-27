---
category: standards
topics: [pep-508, dependency-specification, version-specifiers, environment-markers, extras, dependency-groups, pep-440]
related: [pep-references.md, core-metadata.md, python-packaging-overview.md, distribution-formats.md]
---

# Dependency Specification Formats

## Overview

Dependencies in Python packaging are specified using standardized formats defined by the Python Packaging Authority. The primary standard is **PEP 508**, which defines a grammar for dependency specifications including version constraints and environment markers. Use this reference when helping users declare dependencies in `pyproject.toml`, explain dependency resolution, or troubleshoot version constraint issues.

**Authority**: PEP 508 - BDFL-Delegate Donald Stufft **Repository**: [python/peps - PEP 508](https://github.com/python/peps/blob/main/peps/pep-0508.rst) **Canonical Spec**: [packaging.python.org - Dependency Specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)

## PEP 508 Dependency Specification

### Basic Syntax

A dependency specification in its simplest form:

<eg>
package-name
</eg>

The full syntax supports multiple optional components:

<eg>
name [extras] ( version specifier ) ; environment marker @ URL
</eg>

### Components Explained

#### Package Name

The distribution name to install.

**Rules:**

- Normalized per PEP 503 (lowercase, replace `-_.` with `-`)
- Case-insensitive in practice
- Examples: `requests`, `Django`, `Pillow`

#### Extras (Optional)

Optional features that add extra dependencies.

**Syntax:**

<eg>
package-name[extra1,extra2]
</eg>

**Examples:**

<eg>
requests[security]
Django[postgres,redis]
cryptography[dev,test]
</eg>

**Definition:** Extras are defined in `pyproject.toml` under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
security = ["cryptography>=3.0", "pyOpenSSL"]
dev = ["pytest>=6.0", "black"]
```

**Installation:**

```bash
pip install requests[security]
pip install Django[postgres,redis]
```

#### Version Specifier (Optional)

Constraints on which versions of a package are acceptable.

**Syntax:**

<eg>
package-name (>=1.0,<2.0)
package-name>=1.0,!=1.5,<2.0
</eg>

**Operators:**

| Operator | Meaning                       | Example                  |
| -------- | ----------------------------- | ------------------------ |
| `==`     | Exact version or prefix match | `==1.0`, `==1.0.*`       |
| `!=`     | Exclude specific version      | `!=1.5.0`                |
| `~=`     | Compatible release            | `~=1.4.5` (≥1.4.5, <1.5) |
| `<`      | Earlier than                  | `<2.0`                   |
| `>`      | Later than                    | `>1.0`                   |
| `<=`     | Earlier or equal              | `<=2.0`                  |
| `>=`     | Later or equal                | `>=1.0`                  |

**Combining Specifiers:**

<eg>
requests>=2.20,<3.0        # At least 2.20, before 3.0
Django>=3.2,!=4.0,<5.0    # At least 3.2, not 4.0, before 5.0
numpy~=1.20               # Compatible with 1.20
</eg>

**PEP 440 Version Specifiers**: See `core-metadata.md` for detailed version scheme.

#### Environment Markers (Optional)

Conditional expressions that determine when a dependency applies.

**Syntax:**

<eg>
package-name; python_version < "3.10"
package-name; sys_platform == "win32"
</eg>

**Available Variables:**

| Variable                 | Type   | Examples                           |
| ------------------------ | ------ | ---------------------------------- |
| `python_version`         | String | `"3.9"`, `"3.10"` (major.minor)    |
| `python_full_version`    | String | `"3.10.5"` (major.minor.micro)     |
| `os_name`                | String | `"posix"`, `"nt"`                  |
| `sys_platform`           | String | `"linux"`, `"win32"`, `"darwin"`   |
| `platform_machine`       | String | `"x86_64"`, `"arm64"`              |
| `platform_system`        | String | `"Linux"`, `"Windows"`, `"Darwin"` |
| `platform_release`       | String | OS release version                 |
| `platform_version`       | String | OS version details                 |
| `implementation_name`    | String | `"cpython"`, `"pypy"`, `"jython"`  |
| `implementation_version` | String | `"3.10.5"`                         |

**Operators:**

| Operator | Meaning            |
| -------- | ------------------ |
| `==`     | String equality    |
| `!=`     | String inequality  |
| `<`      | Version comparison |
| `>`      | Version comparison |
| `<=`     | Version comparison |
| `>=`     | Version comparison |
| `and`    | Logical AND        |
| `or`     | Logical OR         |
| `(`, `)` | Grouping           |

**Examples:**

<eg>
colorama; sys_platform == "win32"
pywin32; sys_platform == "win32"
pyobjc; sys_platform == "darwin"
typing-extensions; python_version < "3.8"
dataclasses; python_version < "3.7"
greenlet!=0.4.17; platform_python_implementation == "CPython"
</eg>

#### Direct URL References (Optional)

Specify a package from a URL instead of version constraint.

**Syntax:**

<eg>
package @ URL
</eg>

**Supported URL Schemes:**

- `file://` - Local file path
- `http://` / `https://` - Web URLs
- `git+https://` - Git repositories
- `git+ssh://` - Git over SSH

**Examples:**

<eg>
requests @ https://github.com/psf/requests/archive/v2.28.1.zip
my-package @ file:///path/to/my-package.whl
project @ git+https://github.com/user/project.git@main
</eg>

**Hash Verification:**

<eg>
requests @ https://files.pythonhosted.org/packages/.../requests-2.28.1.tar.gz#sha256=abc123...
</eg>

### Complete Examples

**Simple:**

<eg>
requests
</eg>

**With version:**

<eg>
Django>=3.2,<5.0
</eg>

**With extras:**

<eg>
SQLAlchemy[postgresql,asyncio]>=2.0
</eg>

**With environment marker:**

<eg>
typing-extensions; python_version < "3.10"
</eg>

**Complex:**

<eg>
cryptography[ssh]>=38.0.0; sys_platform != "win32" and python_version >= "3.7"
</eg>

**URL-based:**

<eg>
my-package @ https://github.com/user/project/archive/main.zip
</eg>

## PEP 440 Version Specifiers

Version specifiers are defined in PEP 440 and control which package versions are acceptable.

**Full Reference**: See `core-metadata.md` for PEP 440 version scheme details.

### Compatible Release Clause

The `~=` operator specifies compatible versions.

**Examples:**

<eg>
~=1.4.5      # >=1.4.5, <1.5
~=1.4        # >=1.4, <2
~=2020.1.1   # >=2020.1.1, <2020.2
</eg>

### Pre-release and Post-release Handling

Pre-releases (alpha, beta, rc) are excluded by default unless:

- Already installed
- Only available version
- Explicitly requested in version spec

**Examples:**

<eg>
package>=1.0a1    # Accept pre-releases from 1.0a1 onward
package>=1.0      # Exclude pre-releases (1.0a1, 1.0b2 rejected)
</eg>

## Dependency Groups (PEP 735)

**Status**: Draft (2024)

Emerging standard for organizing optional dependencies into groups:

```toml
[dependency-groups]
dev = [
    "pytest>=7.0",
    "pytest-cov>=3.0",
    "black>=22.0",
]
test = [
    "pytest>=7.0",
    "hypothesis>=6.0",
]
docs = [
    "sphinx>=4.0",
    "sphinx-rtd-theme>=1.0",
]
```

**Current Status**: Proposed extension to PEP 621 and Core Metadata.

## Usage in pyproject.toml

### Runtime Dependencies

```toml
[project]
dependencies = [
    "requests>=2.20.0",
    "click>=7.0",
    "pydantic>=1.0",
]
```

### Optional Dependencies (Extras)

```toml
[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "pytest-cov>=3.0",
    "black>=22.0",
    "mypy>=0.900",
]
docs = [
    "sphinx>=4.0",
    "sphinx-rtd-theme>=1.0",
]
postgres = [
    "psycopg2-binary>=2.9",
]
```

### Conditional Dependencies

```toml
[project]
dependencies = [
    "requests>=2.20.0",
    "typing-extensions>=3.7; python_version < '3.8'",
    "colorama>=0.4; sys_platform == 'win32'",
]
```

## Build Dependencies

Build dependencies are specified in `[build-system]` table (PEP 518):

```toml
[build-system]
requires = ["hatchling>=1.0", "hatch-vcs>=0.3.0"]
build-backend = "hatchling.build"
```

## Hatchling Integration

Hatchling processes dependencies:

1. **Declaration** - Reads from `pyproject.toml` `[project]` table
2. **Parsing** - Parses PEP 508 dependency strings
3. **Validation** - Validates syntax and version specifiers
4. **Metadata** - Includes in wheel/sdist metadata
5. **Installation** - Communicates to installers (pip, etc.)

Hatchling supports:

- PEP 508 dependency specifications
- Environment markers for conditional dependencies
- Extras for optional feature groups
- Version specifier constraints
- Direct URL references (when supported by installer)

## Best Practices

### Version Specifications

**Do:**

- Use lower bounds: `>=1.0.0`
- Specify upper bounds for major versions: `<2.0`
- Use compatible release for stability: `~=1.4.5`

**Avoid:**

- Overly tight constraints: `==1.2.3` (prevents fixes)
- Missing upper bounds: `>=1.0` (may break on major release)
- Conflicting specs: `>2.0,<1.5` (unsatisfiable)

### Environment Markers

**Do:**

- Use for platform-specific deps: `sys_platform == "win32"`
- Use for version-dependent deps: `python_version < "3.8"`
- Group markers for clarity: `(sys_platform == "linux" or sys_platform == "darwin")`

**Avoid:**

- Overly complex markers (keep readable)
- Duplicate functionality in extras
- Unsupported variables

### Optional Dependencies

**Do:**

- Group related functionality: `dev`, `test`, `docs`
- Use descriptive names
- Document purpose in README

**Avoid:**

- Excessive granularity (one package per extra)
- Conflicting extras
- Undocumented extras

## Related Standards

- [PEP 508 - Dependency Specification](https://peps.python.org/pep-0508/)
- `core-metadata.md`
- `pep-references.md#project-metadata-specification-pep-621`
- `core-metadata.md`
