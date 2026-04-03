---
category: core-concepts
topics: [file-selection, git-patterns, VCS, reproducibility]
related: [minimal-philosophy.md, reproducible-builds.md, wheel-vs-sdist.md]
---

# VCS-Aware File Selection and Git-Style Glob Patterns

## Overview

When assisting users with file selection in Hatchling builds, reference this document to explain how Hatchling uses Version Control System (VCS) awareness to make reproducible builds the default, respecting `.gitignore` and `.hgignore` files, and supporting Git-style glob patterns for explicit file selection.

**Source:** [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/) [Hatch Build Configuration v1.1](https://hatch.pypa.io/1.1/config/build/)

## Why VCS-Aware File Selection?

### The Problem

Traditional packaging tools had issues:

1. **Inconsistent behavior:** Manually specifying files is error-prone
2. **Duplication:** Maintaining both .gitignore and package configuration
3. **Drift:** When .gitignore changes, package config becomes stale
4. **Non-reproducibility:** Different builds on different machines

### The Solution

Let the VCS define what's included:

- Developers already maintain .gitignore for version control
- Use the same patterns for packaging
- Single source of truth for "what belongs in repository"
- Automatically excludes build artifacts, tests, CI configs

## How VCS Awareness Works

### Default Behavior

By default, Hatchling:

1. **Searches for .gitignore or .hgignore** in project root or parent directories
2. **Respects the first one found** (stops searching after finding one)
3. **Applies those patterns** to both wheel and sdist targets
4. **Excludes matched files** from distribution

```toml
# No configuration needed - works automatically
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Disabling VCS Awareness

If you want to ignore VCS files and include everything:

```toml
[tool.hatch.build.targets.wheel]
ignore-vcs = true

[tool.hatch.build.targets.sdist]
ignore-vcs = true
```

**When to use:**

- Building from git archive (no .gitignore present)
- Intentionally overriding VCS patterns
- Testing package contents independently of VCS

## Git-Style Glob Patterns

### Pattern Syntax

Hatchling uses Git's glob pattern syntax (documented in `git help gitignore`). Every entry in `include` and `exclude` is a Git-style glob pattern.

### Basic Patterns

<eg>
# Exact filename match
LICENSE
README.md

# Directory match (matches anywhere in path)
build/
dist/
__pycache__/

# Wildcard patterns
*.pyc
*.pyo
*.egg-info/

# Match in any subdirectory
**/*.tmp

# Negate pattern (include something previously excluded)
!important_cache/

# Character ranges
test_[0-9].py

# Question mark (single character)
file?.txt
</eg>

### Advanced Patterns

<eg>
# Match at start of path
/root_file.txt

# Match at any level
src/**/tests/

# Directory-specific patterns
docs/*.md
!docs/API.md

# Bracket expressions
test_[abc].py
test_[^abc].py
</eg>

### Pattern Precedence

```toml
[tool.hatch.build.targets.wheel]
# Exclude takes precedence over include
include = [
    "/src",
    "/tests",
]
exclude = [
    "/tests/fixtures/",
    "*.pyc",
]
```

Files matching exclude are removed even if they match include.

## Configuration Examples

### Example 1: Standard Project Layout

<eg>
myproject/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── myproject/
│       ├── __init__.py
│       └── module.py
├── tests/
│   ├── __init__.py
│   └── test_module.py
├── .gitignore
└── .git/
</eg>

Configuration needed: **None**

Hatchling automatically:

- Finds packages in `src/`
- Includes source files
- Respects .gitignore
- Excludes .git/, build artifacts

### Example 2: Complex File Selection

```toml
[tool.hatch.build.targets.wheel]
# Only include specific package
packages = ["src/myproject"]

# Include only Python files
only-include = [
    "/src/myproject",
]

[tool.hatch.build.targets.sdist]
# Include source and tests
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]

# Exclude temporary files
exclude = [
    "*.pyc",
    "__pycache__",
    ".pytest_cache",
    "*.egg-info",
]
```

### Example 3: Monorepo with Multiple Packages

```toml
# Root project
[tool.hatch.build.targets.wheel]
packages = ["src/root_package"]

[tool.hatch.build.targets.sdist]
include = [
    "/src/root_package",
    "/tests",
]
```

Each package would have its own pyproject.toml with similar configuration.

### Example 4: Include Package Data

```toml
[tool.hatch.build.targets.wheel]
# Include data files
include = [
    "/src/myproject",
    "/src/myproject/data/**/*",
]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/README.md",
    "/LICENSE",
]
```

## Common Patterns and Rationale

### Standard .gitignore

A typical .gitignore automatically excludes:

```gitignore
# Build artifacts
build/
dist/
*.egg-info/

# Python cache
__pycache__/
*.py[cod]
*$py.class

# Test artifacts
.pytest_cache/
.tox/
htmlcov/

# IDE files
.vscode/
.idea/
*.swp

# OS files
.DS_Store
Thumbs.db

# Virtual environments
.venv/
venv/
```

**Effect:** Hatchling automatically excludes these from packages without explicit configuration.

### Wheel vs Source Distribution

Different patterns often needed:

```toml
[tool.hatch.build.targets.wheel]
# Just the package
packages = ["src/myproject"]

[tool.hatch.build.targets.sdist]
# Include everything for development
include = [
    "/src",
    "/tests",
    "/docs",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]
exclude = [
    "*.pyc",
    "__pycache__",
]
```

**Rationale:**

- Wheels: Only runtime files needed, minimal size
- Source dists: Include everything needed to develop and test

## Why Git-Style Patterns?

### 1. Familiar Syntax

Developers already know .gitignore patterns from daily work.

### 2. Consistent Behavior

Same patterns work in multiple contexts:

- Excluding from git commits
- Excluding from package distributions
- Used in other tools (git, hg, rsync)

### 3. Well-Documented

Git pattern documentation is comprehensive and widely available.

### 4. Powerful Yet Readable

<eg>
# Complex: exclude tests except fixtures
**/*.tmp          # All temp files
tests/            # Entire tests directory
!tests/fixtures/  # Except this subdirectory
</eg>

Much more readable than alternatives.

## VCS File Selection and Reproducible Builds

### The Reproducibility Problem

Without VCS awareness, different developers might:

- Include local cache files accidentally
- Forget to exclude build artifacts
- Have different .gitignore rules
- Create non-deterministic packages

### The Hatchling Solution

With VCS awareness:

1. .gitignore is source of truth for "what to distribute"
2. Changes to .gitignore automatically affect builds
3. All developers follow same rules automatically
4. Builds are reproducible across machines

### Example: Build Artifact Leak

<eg>
myproject/
├── src/myproject/
│   └── __init__.py
├── build/              # Build artifact (in .gitignore)
│   └── lib/myproject/
├── dist/               # Distribution artifact (in .gitignore)
│   └── myproject-0.1.0-py3-none-any.whl
└── .gitignore
</eg>

Without VCS awareness: accidentally includes build/dist in distributions. With VCS awareness: automatically excluded because .gitignore lists them.

## Hgignore Support

Hatchling also supports Mercurial's `.hgignore`:

```toml
[tool.hatch.build.targets.sdist]
ignore-vcs = false  # Uses .hgignore by default
```

**Note:** For .hgignore, only glob syntax is supported (not regex patterns).

## Migration from Traditional Tools

### From setuptools

Old way (setup.cfg):

```ini
[options]
packages = find:
```

New way (Hatchling):

```toml
# No configuration needed - automatic discovery
```

Or explicit:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
```

### From Poetry

Old way (pyproject.toml):

```toml
[tool.poetry]
packages = [{include = "myproject", from = "src"}]
```

New way (Hatchling):

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
```

## Best Practices

### 1. Keep .gitignore Current

Your .gitignore drives file selection:

```gitignore
# Always exclude build artifacts
build/
dist/
*.egg-info/

# Always exclude caches
__pycache__/
.pytest_cache/

# Specific to your project
generated_files/
local_config.ini
```

### 2. Use Standard Layouts

Standard layouts work with VCS awareness out-of-box:

<eg>
src/package/              # Recommended
package/                  # Acceptable
</eg>

### 3. Explicit When Non-Standard

If you can't follow standard layout, be explicit:

```toml
[tool.hatch.build.targets.wheel]
packages = ["custom/path/myproject"]
```

### 4. Document File Selection

Add comments explaining non-obvious choices:

```toml
[tool.hatch.build.targets.sdist]
# Include tests in source dist for development
include = [
    "/src",
    "/tests",
    "/README.md",
]
# But exclude test fixtures (too large)
exclude = [
    "/tests/fixtures/**/*",
]
```

## Key Takeaways

1. **VCS awareness** makes reproducible builds the default
2. **Git-style patterns** use familiar, well-documented syntax
3. **.gitignore is source of truth** for distribution contents
4. **Automatic exclusion** of common artifacts (build/, **pycache**)
5. **Explicit configuration** only when needed for special cases
6. **Consistency** across developers comes from shared VCS rules

## References

- [Hatch Build Configuration - File Selection](https://hatch.pypa.io/latest/config/build/#file-selection)
- [Git Pattern Format Documentation](https://git-scm.com/docs/gitignore#_pattern_format)
- [PEP 427 - Wheel Binary Distribution Format](https://peps.python.org/pep-0427/)
