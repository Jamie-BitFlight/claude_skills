---
category: project-metadata
topics: [required-dependencies, optional-dependencies, extras, version-constraints, PEP 508]
related: [version-specifiers, direct-references, metadata-options]
---

# Dependency Specifications

Dependencies specify packages and libraries required by a project. Hatchling supports required dependencies, optional dependencies organized by feature, and detailed version constraints.

When Claude helps users define dependencies, explain that required dependencies are installed automatically while optional dependencies (extras) are installed only when explicitly requested by the user. Show PEP 508 syntax for version constraints and environment markers. For version constraints, refer to `version-specifiers.md` for comprehensive PEP 440 syntax documentation.

## Required Dependencies

Required dependencies are installed automatically when the project is installed.

```toml

[project]
dependencies = [
    "requests>=2.28.0",
    "click>=8.0",
    "python-dateutil",
]

```

## Dependency Syntax (PEP 508)

Dependencies follow PEP 508 format: `name [extras] (comparison operators version) ; environment marker`

### Simple Requirements

```toml

dependencies = [
    "requests",  # Any version
    "click>=8.0",  # Version 8.0 and later
    "numpy>=1.20,<2.0",  # Range constraints
]

```

### With Extras

Some packages provide optional features via extras:

```toml

dependencies = [
    "requests[security]>=2.28.0",
    "pillow[imaging]>=8.0",
]

```

### Environment Markers

Conditional dependencies based on system or Python version:

```toml

dependencies = [
    "typing-extensions; python_version<'3.8'",
    "importlib-metadata; python_version<'3.8'",
    'pywin32; sys_platform=="win32"',
]

```

## Optional Dependencies (Extras)

Optional dependencies are feature-specific groups installed only when requested.

```toml

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "mypy>=1.0",
]
docs = [
    "sphinx>=5.0",
    "sphinx-rtd-theme>=1.0",
]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

```

### Installation with Extras

Users install optional dependencies by specifying extras:

```bash

# Install with dev dependencies
pip install my-package[dev]

# Install with multiple extras
pip install my-package[dev,docs]

# Install all optional dependencies
pip install my-package[dev,docs,test]

```

## Complex Dependency Scenarios

### Multiple Version Constraints

```toml

dependencies = [
    "flask>=2.0,<3.0",
    "werkzeug>=2.0,!=2.0.1",
    "jinja2>=3.0,<4.0",
]

```

### Extras with Version Constraints

```toml

dependencies = [
    "requests[security]>=2.28.0,<3.0",
]

```

### Context Formatting

Dependencies can use context variables for dynamic configuration:

```toml

dependencies = [
    "typing-extensions; python_version<'3.8'",
]

```

## Direct References

Direct references (Git URLs, local paths) are allowed only when enabled. See `direct-references.md` for comprehensive documentation.

## Dependency Best Practices

1. **Specificity**: Use meaningful version constraints (avoid overly restrictive or loose constraints)
2. **Documentation**: Document why version constraints are needed
3. **Upper Bounds**: Consider upper bounds for major version changes
4. **Testing**: Test with minimum and maximum supported versions
5. **Extras**: Organize optional dependencies logically by use case

### Good Version Constraints

```toml

dependencies = [
    "requests>=2.28.0",  # Require specific minimum version
    "click>=8.0,<9.0",  # Allow compatible patches
    "numpy>=1.20,<2.0",  # Account for major version changes
]

```

### Avoid

```toml

# Too restrictive
dependencies = [
    "requests==2.28.0",  # Locks exact version
    "click>=8.1.3,!=8.1.4,!=8.1.5",  # Over-specific constraints
]

# Too loose
dependencies = [
    "requests",  # No version constraint
    "click>0",  # Too broad
]

```

## Complete Example

```toml

[project]
name = "web-framework"
version = "1.0.0"
description = "A modern web framework"
dependencies = [
    "werkzeug>=2.0,<3.0",
    "jinja2>=3.0",
    "click>=8.0",
    "typing-extensions; python_version<'3.8'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
]
docs = [
    "sphinx>=5.0",
    "sphinx-rtd-theme>=1.0",
    "sphinx-autodoc-typehints>=1.19.0",
]
performance = [
    "uvloop>=0.17.0",
    "orjson>=3.8.0",
]

```

## Version Specifier Syntax Reference

For comprehensive version specifier documentation, see `version-specifiers.md`.

### Common Operators

- `==X.Y.Z` - Exact version match
- `!=X.Y.Z` - Not equal to version
- `>=X.Y.Z` - Greater than or equal
- `<=X.Y.Z` - Less than or equal
- `>X.Y.Z` - Greater than
- `<X.Y.Z` - Less than
- `~=X.Y.Z` - Compatible release (equivalent to `>=X.Y.Z,==X.Y.*`)
- `===` - Arbitrary equality (rarely used)

## Related Configuration

- `version-specifiers.md` - Complete version syntax guide
- `direct-references.md` - VCS and local path dependencies
- `dependencies.md#optional-dependencies-extras` - Feature-based dependency groups
