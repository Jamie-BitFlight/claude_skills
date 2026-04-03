---
category: core-concepts
topics: [design-philosophy, configuration, defaults, best-practices]
related: [pep-517-backend.md, vcs-file-selection.md, build-hooks.md]
---

# Minimal Configuration Philosophy

## Core Principle

When guiding users on Hatchling configuration, emphasize that Hatchling embraces a "minimal configuration" philosophy where sensible defaults handle most use cases, and explicit configuration is only required for specialized needs.

**Source:** [DrivenData - The Basics of Python Packaging in Early 2023](https://drivendata.co/blog/python-packaging-2023)

## The Problem Hatchling Solves

Traditional packaging tools required extensive configuration:

```toml
# Before: Lots of configuration needed
[tool.setuptools]
packages = ["src/mypackage"]
py-modules = ["myscript"]

[tool.setuptools.package-data]
mypackage = ["data/*.txt"]

[tool.setuptools.entry-points."console_scripts"]
my-script = "mypackage.cli:main"
```

This created friction:

- Developers spent time understanding configuration
- Repetitive patterns across projects
- Inconsistent structures across codebases
- Configuration drift as projects evolved

## Hatchling's Approach

### Smart Defaults

Hatchling uses intelligent discovery:

**Package Discovery**

- Automatically finds packages in common locations
- Supports `src/` layout (recommended by PyPA)
- Supports flat layout (single package at root)
- Supports `package/` layout
- Detects `__init__.py` files (pure namespace packages supported)

**File Selection**

- Includes only source files (respects .gitignore)
- Excludes test files, build artifacts, CI config
- Uses Git-style glob patterns for predictable behavior

**Version Management**

- Single source of truth via configuration
- Dynamic version from file, VCS, or external source
- No duplication between metadata and code

### Typical Configuration

A typical project requires minimal setup:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "Brief description"
readme = "README.md"
requires-python = ">=3.8"
authors = [
    { name = "Author Name", email = "author@example.com" },
]
dependencies = [
    "requests>=2.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
my-script = "my_package.cli:main"
```

This is sufficient for most projects. Additional configuration is added only when needed.

## When Configuration is Needed

### Custom File Selection

Only needed if default behavior doesn't work:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
]
exclude = [
    "*.pyc",
    "__pycache__",
]
```

**When to use:**

- Non-standard project layout
- Complex include/exclude patterns
- Different files for wheel vs sdist

### Custom Version Management

Only needed if you want dynamic versioning:

```toml
[tool.hatch.version]
path = "src/my_package/__about__.py"
```

Or with VCS plugin:

```toml
[tool.hatch.version]
source = "vcs"
```

**When to use:**

- Automatic version from git tags
- Version stored in single location
- Avoiding manual version bumps

### Build Hooks

Only needed for complex build processes:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

**When to use:**

- Generating files during build
- Building C extensions
- Creating package data
- Integration with other build tools

## Design Principles

### Convention Over Configuration

Hatchling follows established Python packaging conventions:

- PEP 427 for wheel format
- PEP 317 for metadata
- Git-style .gitignore patterns
- Standard project layouts

When conventions are followed, no configuration needed.

### Progressive Disclosure

Configuration is revealed as needed:

1. **Default:** No configuration (works for 70% of projects)
2. **Targeted:** File selection configuration (works for 25%)
3. **Custom:** Build hooks (works for 5%)

Users only learn what they need.

### Explicit Over Implicit (When It Matters)

While defaults are sensible, they're not magic:

- File patterns use standard Git glob syntax
- Version sources are explicit (file, VCS, environment)
- Build hooks inherit from documented interface
- Metadata follows PEP 621 standard format

Developers understand what happens without debugging.

## Comparison with Other Tools

### Poetry

```toml
[tool.poetry]
name = "my-package"
version = "0.1.0"
description = "Description"
authors = ["Author <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.28.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
```

Poetry uses custom metadata format (not PEP 621). More configuration required for non-standard structures.

### uv (Modern Alternative)

```toml
[build-system]
requires = ["uv"]
build-backend = "uv.build"

[project]
name = "my-package"
version = "0.1.0"
```

Very similar philosophy to Hatchling. Both emphasize minimal configuration.

### setuptools (Traditional)

Requires either setup.py or extensive setup.cfg configuration. Defaults are less sensible for modern Python packaging.

## Best Practices for Minimal Configuration

### 1. Use Standard Layouts

Hatchling works best with standard layouts:

<eg>
my-package/
├── src/
│   └── my_package/
│       ├── __init__.py
│       └── module.py
├── tests/
├── README.md
└── pyproject.toml
</eg>

Avoids need for custom file selection.

### 2. Single Source of Truth

Store version in one place:

```python
# src/my_package/__about__.py
__version__ = "0.1.0"
```

Configure Hatchling to read it:

```toml
[tool.hatch.version]
path = "src/my_package/__about__.py"
```

### 3. Let .gitignore Drive Builds

Hatchling respects .gitignore by default. Keep it current:

```gitignore
# .gitignore
build/
dist/
*.egg-info/
__pycache__/
.pytest_cache/
.tox/
```

Automatic file selection then excludes these.

### 4. Use PEP 621 Format

Use standard `[project]` section, not custom tool formats:

```toml
[project]
name = "my-package"
version = "0.1.0"
description = "Description"
readme = "README.md"
requires-python = ">=3.8"
authors = [
    { name = "Author", email = "email@example.com" }
]
```

Portable across tools and standards-compliant.

### 5. Add Configuration Only When Needed

Start with minimal config. Add custom configuration only when:

- Default behavior doesn't match your project
- You need specific build behavior
- Performance requires optimization

Don't "just in case" configure things.

## Trade-offs

### Advantages of Minimal Philosophy

- **Lower learning curve:** Fewer options to understand
- **Faster setup:** Most projects need < 20 lines of config
- **Maintainability:** Less configuration to maintain over time
- **Portability:** Works with any PEP 517 frontend
- **Future-proof:** Compatible with standards evolution

### When Minimal Philosophy Limits

- **Complex builds:** If you need C extensions or complex generation, use build hooks
- **Non-standard layouts:** If you have unusual structure, explicit configuration needed
- **Monorepos:** If managing multiple packages, may need custom build hooks
- **Specialized requirements:** If you have unique needs, custom hooks or build system integration

In these cases, Hatchling remains minimal - it doesn't force complex configuration, but supports extensions when needed.

## Key Takeaways

1. **Sensible defaults** work for most Python projects
2. **Configuration grows with complexity**, not upfront
3. **Standards compliance** means you're never locked in
4. **Convention over configuration** reduces cognitive load
5. **Progressive disclosure** matches learning curve to need
6. **Explicit when it matters** keeps customization clear and debuggable

## References

- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- [DrivenData: The Basics of Python Packaging in Early 2023](https://drivendata.co/blog/python-packaging-2023)
- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
