---
category: core-concepts
topics: [standards, PEP-517, PEP-518, build-system, compliance]
related: [minimal-philosophy.md, vcs-file-selection.md, reproducible-builds.md]
---

# Hatchling as a PEP 517/518 Backend

## Overview

When helping users understand how Hatchling implements Python packaging standards, reference this document to explain PEP 517/518 compliance and standards-based build systems. Hatchling is a standards-compliant Python build backend that fully implements PEP 517 and PEP 518 specifications.

**Source:** [Hatch Documentation - Build Configuration](https://hatch.pypa.io/latest/config/build/) [Source](https://hatch.pypa.io/1.1/config/build/)

## What is PEP 517/518?

### PEP 517 - A Build-System Independent Format

PEP 517 defines a standard interface for Python packaging tools to build packages. Key aspects:

- Decouples build backend from installation tool (pip)
- Defines hook functions that build systems must implement:
  - `build_wheel(wheel_directory, config_settings=None, metadata_directory=None)`
  - `build_sdist(sdist_directory, config_settings=None)`
  - `get_requires_for_build_wheel(config_settings=None)`
  - `get_requires_for_build_sdist(config_settings=None)`
- Allows installation tools to discover build requirements without executing setup.py

**Impact:** Projects no longer need setup.py for installation or dependency discovery.

### PEP 518 - Specifying Build System Requirements

PEP 518 introduces the `[build-system]` section in pyproject.toml:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

This section:

- Lists build dependencies (e.g., `hatchling`)
- Specifies the build backend module
- Allows tools to isolate build environment from runtime environment

**Impact:** Build dependencies no longer pollute runtime environments; they're installed in isolated environments by package managers.

## Hatchling as Standards-Compliant Backend

### Implementation Status

Hatchling is fully PEP 517/518 compliant and also supports PEP 660 (editable installations).

**Source:** [PyPI - hatchling](https://pypi.org/project/hatchling/) [Hatch Documentation - Build Configuration](https://hatch.pypa.io/1.1/config/build/)

### Minimal Configuration

For standards compliance, projects need only:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
```

This configuration:

- Declares hatchling as the build backend
- Relies on Hatchling's defaults for file discovery and build process
- Achieves compliance without custom setup.py or setup.cfg

### What Hatchling Does

Hatchling:

- Discovers packages automatically using standard layouts (src/, package/, or flat)
- Respects .gitignore/.hgignore for reproducible builds
- Supports both wheel (PEP 427) and sdist (tar.gz) distribution formats
- Supports editable installs (PEP 660) via pip install -e
- Integrates with VCS for version management

## Standards Ecosystem

### Complementary Standards

Hatchling works within the broader standards ecosystem:

- **PEP 621:** Package metadata specification (pyproject.toml `[project]` table)
- **PEP 427:** Wheel binary package format
- **PEP 660:** Editable installs for development workflows
- **PEP 345/566:** Core metadata format versions (1.0 through 2.4)

### Tool Integration

Because Hatchling implements PEP 517/518, any tool that respects these standards can work with projects using Hatchling:

- `pip` - installation tool
- `build` - PEP 517 build frontend
- `twine` - PyPI upload tool
- Virtual environment managers
- IDE/editor integration

### Example: Building with Standard Tools

```bash
# Using the 'build' frontend (PEP 517)
python -m build /path/to/project
# or
pip install build
build

# Using Hatch (recommended for Hatchling projects)
hatch build

# Using uv (modern alternative)
uv build
```

All three methods work because they understand PEP 517.

## Why Standards Matter

### Reproducible Builds

Standards enable:

- Deterministic builds across different machines
- Consistent package discovery
- Isolation of build dependencies
- Verification of package integrity

### Reduced Complexity

Projects no longer need:

- setup.py with imperative build logic
- setup.cfg with duplicate metadata
- setuptools-specific extensions
- Custom installation hooks

### Ecosystem Compatibility

Standards-compliance means:

- Works with any PEP 517 frontend (pip, build, uv, poetry, pdm)
- Compatible with all package repositories
- Integrates with CI/CD systems expecting standards
- Future-proof as standards evolve

## Hatchling vs Legacy Build Systems

### Legacy (setuptools + setup.py)

```python
# setup.py - imperative, tool-specific
from setuptools import setup, find_packages

setup(
    name="my-package",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8",
)
```

Problems:

- Mixes metadata with build logic
- Tool-specific format
- Requires execution for dependency discovery
- No build isolation

### Modern (Hatchling + pyproject.toml)

```toml
# pyproject.toml - declarative, standards-based
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
requires-python = ">=3.8"
```

Benefits:

- Metadata is declarative
- Tool-agnostic format
- Build isolation
- Clear separation of concerns

## Key Takeaways

1. **PEP 517/518 are standards**, not Hatchling-specific features
2. **Hatchling implements these standards** correctly and completely
3. **Standards enable tool-agnostic packaging** - you're not locked into Hatch
4. **Minimal configuration** is possible because Hatchling has sensible defaults
5. **Reproducible builds** come from respecting standards and VCS-aware file selection

## References

- [PEP 517 - A build-system independent format for source trees](https://peps.python.org/pep-0517/)
- [PEP 518 - Specifying build system requirements for Python projects](https://peps.python.org/pep-0518/)
- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 660 - Editable installs for pyproject.toml based builds](https://peps.python.org/pep-0660/)
- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
