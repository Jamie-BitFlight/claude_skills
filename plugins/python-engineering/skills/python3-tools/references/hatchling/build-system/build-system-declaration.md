---
category: build-system
topics:
- build-system-table
- pyproject-toml
- build-backend
- build-requirements
- pep-517
- pep-518
related:
- pep-standards
- build-options
- build-hooks
---

# Build System Declaration Guide for Claude

This reference helps Claude configure the `[build-system]` table in `pyproject.toml` for Hatchling projects. This table tells Python packaging tools which build backend to use and what dependencies are required.

## Core Declaration Pattern

### Standard Hatchling Declaration

Always suggest this as the default:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Version-Pinned Declaration

For reproducible builds, pin versions:

```toml
[build-system]
requires = ["hatchling>=1.21.0,<2"]
build-backend = "hatchling.build"
```

## Advanced Build Requirements

### With Hatch Plugins

When users need additional build-time plugins:

```toml
[build-system]
requires = [
    "hatchling>=1.21.0",
    "hatch-vcs>=0.3.0",           # Version from VCS tags
    "hatch-fancy-pypi-readme>=22.5.0",  # Dynamic README
    "hatch-requirements-txt>=0.4.0",    # Dependencies from requirements.txt
]
build-backend = "hatchling.build"
```

### With Extension Modules

For projects with compiled extensions:

```toml
[build-system]
requires = [
    "hatchling>=1.24.2",
    "scikit-build-core~=0.9.3",   # CMake support
    "cython>=3.0.0",               # Cython compilation
]
build-backend = "hatchling.build"
```

### With Custom Build Hooks

When users create custom hooks:

```toml
[build-system]
requires = [
    "hatchling>=1.21.0",
    "my-custom-hook>=1.0.0",       # Custom build processing
]
build-backend = "hatchling.build"
```

## Platform-Specific Requirements

### Conditional Requirements

Use environment markers for platform-specific needs:

```toml
[build-system]
requires = [
    "hatchling>=1.21.0",
    "cython>=3.0.0; platform_system != 'PyPy'",
    "setuptools-rust>=1.5.2; sys_platform == 'win32'",
    "cmake>=3.21; platform_machine == 'x86_64'",
]
build-backend = "hatchling.build"
```

## Migration Patterns

### From Setuptools

Help users migrate from setuptools:

```toml
# Replace this setuptools configuration:
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

# With this Hatchling configuration:
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### From Poetry

Help users migrate from Poetry:

```toml
# Replace Poetry:
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

# With Hatchling:
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### From Flit

Help users migrate from Flit:

```toml
# Replace Flit:
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"

# With Hatchling:
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Validation Commands

Provide these commands to validate configuration:

```bash
# Verify build backend is importable
python -c "import hatchling.build"

# Validate full build configuration
python -m build --check

# Test build process
hatch build

# Build with pip to test isolation
pip wheel --use-pep517 .
```

## Common Issues and Solutions

### Missing Build System Table

When users encounter:

<terminal_output>
ERROR: pyproject.toml does not contain a [build-system] table
</terminal_output>

Solution - Add minimal declaration:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Import Error for Backend

When users encounter:

<terminal_output>
ERROR: Could not import 'hatchling.build'
</terminal_output>

Solution - Ensure hatchling is in requires:

```toml
[build-system]
requires = ["hatchling"]  # This line is essential
build-backend = "hatchling.build"
```

### Incompatible Version Requirements

When dependency conflicts occur, suggest compatible version ranges:

```toml
[build-system]
requires = [
    "hatchling>=1.21.0,<2",      # Compatible range
    "hatch-vcs>=0.3.0,<1",        # Avoid major version jumps
]
```

## Best Practices to Recommend

### Version Constraints

- Use `>=X.Y.Z` for minimum version requirements
- Add `<X+1` to avoid breaking changes in major versions
- Use `~=X.Y` for compatible releases

### Build Requirements Management

- Keep build requirements minimal - only what's needed for building
- Document why each additional requirement is needed
- Test builds in clean environments regularly
- Use compatible version specifiers for related packages

### Development Workflow

For local development with custom plugins:

```toml
[build-system]
requires = [
    "hatchling",
    "my-local-plugin @ file:///path/to/local/plugin",
]
build-backend = "hatchling.build"
```

## Key Points for Claude

### Always Required Fields

- `requires` - List of build dependencies (must include "hatchling")
- `build-backend` - Module path to build backend (must be "hatchling.build")

### Optional But Recommended

- Version pinning for reproducibility
- Environment markers for platform-specific requirements
- Comments explaining non-obvious requirements

### Build Isolation Context

- Build happens in isolated environment with only specified dependencies
- System packages are not accessible during build
- All build-time dependencies must be declared in `requires`

## Navigation

- `pep-standards.md` - Detailed PEP 517/518 compliance
- `build-options.md` - Configure build behavior
- `../build-hooks/index.md` - Extend build process
