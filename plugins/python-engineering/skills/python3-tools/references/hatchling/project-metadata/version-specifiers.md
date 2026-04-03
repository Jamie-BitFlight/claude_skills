---
category: project-metadata
topics: [PEP 440, version-syntax, version-specifiers, pre-release, post-release, development-release]
related: [dependencies, basic-metadata, dynamic-metadata]
---

# PEP 440 Version Specifiers & Identification

PEP 440 defines the standard version identification and dependency specification scheme for Python packages. This ensures consistent version semantics across the Python packaging ecosystem.

When Claude helps users understand version constraints or create version specifications, reference this guide for the complete PEP 440 syntax. Explain the canonical format components and show practical examples of version constraints used in dependency specifications.

## PEP 440 Overview

Version specifiers in PEP 440 define compatible versions for dependency resolution. They are used in `requires-python` field and dependency specifications.

## Version Format

PEP 440 defines this canonical version format:

<eg>
[N!]N(.N)*[{a|b|rc}N][.postN][.devN][+local]
</eg>

### Components

- **Epoch** `N!` (optional) - For version number discontinuities (rarely used)
- **Release Segment** `N(.N)*` - Required, numeric components separated by periods
- **Pre-release** `{a|b|rc}N` (optional) - alpha, beta, or release candidate
- **Post-release** `.postN` (optional) - Bug fix release after final version
- **Development** `.devN` (optional) - Development release
- **Local Version** `+local` (optional) - Local version label

## Version Examples

```toml

# Standard releases
version = "0.1.0"
version = "1.0.0"
version = "2.1.3"

# Pre-releases
version = "1.0.0a1"  # Alpha 1
version = "1.0.0b2"  # Beta 2
version = "1.0.0rc1"  # Release Candidate 1

# Post-releases
version = "1.0.0.post1"  # Bug fix after 1.0.0

# Development releases
version = "1.0.0.dev1"  # Development version
version = "1.0.0a1.dev1"  # Development alpha

# With epoch (version restart)
version = "2!0.1.0"  # Epoch 2, version 0.1.0

# Local versions
version = "1.0.0+ubuntu1"
version = "1.0.0+win32.py38"

```

## Version Specifiers

Version specifiers define which versions are compatible with a requirement.

### Compatible Release

Allows compatible patch and minor updates:

```toml

dependencies = [
    "requests~=2.28",  # >=2.28, ==2.*
    "click~=8.1.0",  # >=8.1.0, ==8.1.*
]

```

Equivalent to:

- `~=X.Y` → `>=X.Y, ==X.*`
- `~=X.Y.Z` → `>=X.Y.Z, ==X.Y.*`

### Inclusive Version Range

```toml

dependencies = [
    "requests>=2.28.0,<3.0",  # 2.28.0 and later, but before 3.0
    "click>=8.0,<9.0",
]

```

### Exclusive Ranges

```toml

dependencies = [
    "numpy>=1.20,!=1.21.0,<2.0",  # Exclude specific versions
]

```

### Equality

```toml

dependencies = [
    "requests==2.28.0",  # Exact version only (rarely recommended)
]

```

### Inequality

```toml

dependencies = [
    "requests!=2.28.0",  # Any version except 2.28.0
]

```

### Greater Than / Less Than

```toml

dependencies = [
    "requests>2.28.0",  # Strictly greater than
    "click<9.0",  # Strictly less than
]

```

### Greater Than or Equal / Less Than or Equal

```toml

dependencies = [
    "requests>=2.28.0",  # Version 2.28.0 and later
    "click<=8.1.0",  # Version 8.1.0 and earlier
]

```

## Python Version Specifiers

The `requires-python` field uses version specifiers to define Python version support:

```toml

[project]
requires-python = ">=3.8"
requires-python = ">=3.8,<4"
requires-python = ">=3.8,!=3.9,<4"
requires-python = "~=3.10"

```

### Common Python Version Patterns

```toml

# Support Python 3.8+
requires-python = ">=3.8"

# Support Python 3.8-3.12
requires-python = ">=3.8,<3.13"

# Support Python 3.10+
requires-python = ">=3.10"

# Support 3.8 and 3.9, but not 3.9.0-3.9.9 due to specific bug
requires-python = ">=3.8,!=3.9.0,!=3.9.1,!=3.9.2"

# Support Python 3.x (before major version 4)
requires-python = ">=3.8,<4"

```

## Complex Version Constraints

### Multiple Constraints

```toml

dependencies = [
    "flask>=2.0,<3.0",
    "werkzeug>=2.0,!=2.0.1",
    "jinja2>=3.0,<4.0",
    "itsdangerous>=2.0,<3.0",
]

```

### Pre-release Management

By default, package indexes exclude pre-releases. To explicitly allow them:

```toml

dependencies = [
    "requests>=2.28.0a1",  # Allows alphas and betas
]

```

### Post-release Handling

```toml

dependencies = [
    "requests>=2.28.0.post1",  # Requires post-release or later
]

```

## Environment Markers

Combine version specifiers with environment markers for conditional dependencies:

```toml

dependencies = [
    "typing-extensions>=3.7.4; python_version<'3.8'",
    "importlib-metadata; python_version<'3.8'",
    'pywin32>=300; sys_platform=="win32"',
    'pydantic[email]>=1.0; sys_platform=="linux"',
]

```

### Environment Marker Variables

- `python_version` - Python version (e.g., `"3.8"`, `"3.11.2"`)
- `python_full_version` - Full version with build info
- `sys_platform` - Platform identifier (`"linux"`, `"win32"`, `"darwin"`)
- `platform_machine` - Machine identifier (`"x86_64"`, `"arm64"`, etc.)
- `platform_system` - System name (`"Linux"`, `"Windows"`, `"Darwin"`)
- `os_name` - OS name (`"posix"`, `"nt"`)
- `platform_python_implementation` - Implementation (`"CPython"`, `"PyPy"`, etc.)

## Best Practices

### Version Constraint Guidelines

1. **Minimum Version**: Specify minimum version with tested compatibility
2. **Upper Bounds**: Include upper bounds for major version changes
3. **Test Coverage**: Test against minimum and maximum supported versions
4. **Avoid Over-Specification**: Don't exclude minor versions unnecessarily
5. **Document Changes**: Document why specific constraints are needed

### Recommended Patterns

```toml

# For stable projects with semantic versioning
dependencies = [
    "requests>=2.28.0,<3.0",
    "click>=8.0,<9.0",
]

# For pre-release software
dependencies = [
    "experimental-lib>=0.1.0a1,<1.0",
]

# With environment-specific dependencies
dependencies = [
    "requests>=2.28.0",
    "typing-extensions>=3.7.4; python_version<'3.8'",
]

```

### Avoid

```toml

# No version specification (dangerous)
dependencies = [
    "requests",
]

# Over-specification (too restrictive)
dependencies = [
    "requests==2.28.0",
    "click>=8.1.0,!=8.1.1,!=8.1.2",
]

# Unclear constraints
dependencies = [
    "requests>=2.0",  # Too broad
    "click<100.0",  # Meaningless upper bound
]

```

## Version Matching Examples

Given `requests` releases: `2.27.0`, `2.28.0`, `2.28.1`, `2.29.0`, `3.0.0a1`, `3.0.0`

<eg>
requests>=2.28.0        → 2.28.0, 2.28.1, 2.29.0, 3.0.0a1, 3.0.0
requests>=2.28.0,<3.0   → 2.28.0, 2.28.1, 2.29.0
requests~=2.28          → 2.28.0, 2.28.1, 2.29.0
requests~=2.28.0        → 2.28.0, 2.28.1
requests==2.28.0        → 2.28.0 only
requests!=2.28.0        → 2.27.0, 2.28.1, 2.29.0, 3.0.0a1, 3.0.0
</eg>

## Related Configuration

- `dependencies.md` - Dependency specification overview
- `direct-references.md` - VCS and local references (alternative to version specifiers)
- `basic-metadata.md#python-support-requires-python` - Python version requirements
