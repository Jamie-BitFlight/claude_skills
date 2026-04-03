---
category: core-concepts
topics: [version-management, versioning, single-source-of-truth, PEP-440]
related: [build-hooks.md, development-vs-distribution.md, minimal-philosophy.md]
---

# Version Management Strategies

## Overview

When helping users establish version management in Hatchling projects, reference this document to explain multiple version management strategies, allowing projects to choose the approach that best fits their workflow—versions can come from source files, VCS tags, environment variables, or external sources.

**Source:** [Hatch Configuration FAQ](https://hatch.pypa.io/latest/meta/faq/) [Various Hatch Documentation Pages](https://hatch.pypa.io/latest/)

## Core Principle: Single Source of Truth

All version management strategies follow one principle: **maintain version in a single location** and read it during the build, ensuring version is always consistent.

```toml
# Version defined once, used everywhere
[tool.hatch.version]
path = "src/package/__init__.py"  # Version lives here
```

Then in code:

```python
# src/package/__init__.py
__version__ = "0.1.0"
```

And accessed via:

```python
# setup.py or elsewhere
from package import __version__
# or
import importlib.metadata
version = importlib.metadata.version("package-name")
```

## Version Sources

### 1. File-Based Version (Recommended for Most Projects)

Store version in a Python file, read it at build time.

**Configuration:**

```toml
[tool.hatch.version]
path = "src/package/__init__.py"
```

**Usage in Code:**

```python
# src/package/__init__.py
__version__ = "0.2.5"

# Access at runtime
from . import __version__
# or
import importlib.metadata
__version__ = importlib.metadata.version("package-name")
```

**Advantages:**

- Simple and transparent
- Version visible in source code
- Works everywhere (IDE, tests, runtime)
- No special tooling needed

**When to use:**

- Manual version bumping
- Simple versioning scheme
- Traditional development workflow

**Example: Dedicated Version File**

```python
# src/package/__about__.py
__version__ = "1.2.3"
__author__ = "John Doe"
__email__ = "john@example.com"
__license__ = "MIT"
```

Configuration:

```toml
[tool.hatch.version]
path = "src/package/__about__.py"
```

### 2. VCS-Based Version

Derive version from git tags automatically.

**Installation:**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"
```

**Configuration:**

```toml
[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/package/_version.py"
```

**Git Setup:**

```bash
# Tag releases
git tag v0.1.0
git tag v0.2.0
git push --tags
```

**Behavior:**

- Version determined from closest git tag
- Commits after tag get `+dev` suffix
- During release: version matches tag exactly
- During development: version is `X.Y.Z.devN+commits.ghash`

**Example:**

```bash
git tag v1.0.0          # Build version = 1.0.0
git commit ...          # Build version = 1.0.0.dev1+g1234567
git tag v1.0.1          # Build version = 1.0.1
git commit ...          # Build version = 1.0.1.dev1+g7654321
```

**Advantages:**

- No manual version bumping
- Version tied to releases
- Semantic versioning friendly
- Reproducible builds from tags

**When to use:**

- Frequent releases
- Semantic versioning
- Want version automation
- Using git workflow

**Third-Party Options:**

- `hatch-vcs`: Use git tags
- `setuptools_scm`: Similar functionality
- `pdm-backend`: Built-in PEP 440 versioning

### 3. Dynamic Metadata Hook

Use a hook to compute version at build time.

**Configuration:**

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

**Example:**

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import subprocess

class DynamicVersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if not version or version == "0.0.0":
            # Compute version from git
            try:
                version = subprocess.check_output(
                    ["git", "describe", "--tags"],
                    cwd=self.root,
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                version = "0.0.0.dev0"

            # Write to version file
            version_file = self.root / "src/package/_version.py"
            version_file.write_text(f'__version__ = "{version}"\n')

            build_data['force_include'] = {
                str(version_file): "package/_version.py"
            }
```

**Advantages:**

- Complete flexibility
- Can use any versioning scheme
- Can integrate with external tools

**When to use:**

- Non-standard versioning needs
- Complex version computation
- Integration with other systems

### 4. Environment Variable

Read version from environment at build time.

**Configuration:**

```toml
[tool.hatch.version]
source = "regex"
path = "src/package/__init__.py"
pattern = """
    __version__\\s*=\\s*['\\\"]
    (?P<version>[^'\\\"]*?)
    ['\\\"]
"""
```

Or with custom hook:

```python
# hatch_build.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class EnvVersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Read from environment
        env_version = os.getenv("BUILD_VERSION")
        if env_version:
            # Write to version file
            version_file = self.root / "src/package/_version.py"
            version_file.write_text(f'__version__ = "{env_version}"\n')

            build_data['force_include'] = {
                str(version_file): "package/_version.py"
            }
```

**Usage in CI/CD:**

```bash
BUILD_VERSION=1.2.3 python -m build
# or
BUILD_VERSION=1.2.3 hatch build
```

**Advantages:**

- External version control
- Works with CI/CD systems
- Can be automated in release process

**When to use:**

- Version managed by CI/CD pipeline
- Release process owned by infrastructure team
- Dynamic version assignment

## Comparing Strategies

### File-Based vs VCS-Based

| Aspect                    | File-Based              | VCS-Based               |
| ------------------------- | ----------------------- | ----------------------- |
| **Setup**                 | Simple, no dependencies | Requires plugin         |
| **Version bumping**       | Manual (edit file)      | Automatic (tag release) |
| **During development**    | Same as release version | Has dev suffix          |
| **Source visibility**     | Clear in **init**.py    | Not visible in source   |
| **Build reproducibility** | Always same version     | Depends on git state    |
| **CI/CD integration**     | Commit version bump     | Tag commit              |

### Which to Choose?

**File-Based if:**

- Small project or team
- Infrequent releases
- Simple versioning scheme
- Want simplicity

**VCS-Based if:**

- Frequent releases (weekly+)
- Using semantic versioning strictly
- Want to automate version bumping
- Team mature with git workflow

**Custom Hook if:**

- Special requirements
- Integration with external system
- Non-standard versioning

## Best Practices

### 1. Version Location

Store in a consistent location:

```python
# Option 1: In __init__.py (most common)
# src/package/__init__.py
__version__ = "1.0.0"

# Option 2: Dedicated version file
# src/package/__version__.py
__version__ = "1.0.0"

# Option 3: Version file in metadata
# src/package/_version.py  (internal, not exported)
```

Most common is Option 1 for simplicity.

### 2. Make Version Accessible at Runtime

Ensure applications can determine their version:

```python
# Good: Available via import
from package import __version__
print(__version__)

# Also good: Available via importlib.metadata
import importlib.metadata
version = importlib.metadata.version("package-name")
```

### 3. Use PEP 440 Versioning

Follow Python versioning standard:

<eg>
# Release versions
1.0.0
1.0.1
1.1.0
2.0.0

# Pre-releases
1.0.0a1
1.0.0b1
1.0.0rc1

# Development versions (for VCS)
1.0.0.dev0
1.0.0.dev1

# Post-releases
1.0.0.post1
</eg>

### 4. Document Version Strategy

Add to README or documentation:

```markdown
## Versioning

Version is maintained in `src/myproject/__init__.py` as `__version__`.

To release a new version:

1. Update `__version__` to new version number
2. Commit with message "Bump version to X.Y.Z"
3. Tag commit: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`
5. CI/CD builds and publishes automatically
```

### 5. Handle Dynamic Version in Tests

Tests should work with both static and dynamic versions:

```python
# In your test setup
import importlib.metadata

try:
    __version__ = importlib.metadata.version("myproject")
except importlib.metadata.PackageNotFoundError:
    # Development mode, read from source
    from myproject import __version__
```

## Version Management by Release Phase

### During Development

Use file-based version with dev suffix:

```python
# src/package/__init__.py
__version__ = "0.2.0.dev0"
```

### For Release Candidate Testing

Use release candidate version:

```python
__version__ = "1.0.0rc1"
```

### For Production Release

Use release version exactly:

```python
__version__ = "1.0.0"
```

### After Release (VCS Approach)

Tag release:

```bash
git tag v1.0.0
```

Continue development with next version:

```bash
# Auto-generated: 1.0.1.dev0
# (from git describe --tags)
```

## Avoiding Version Duplication

### The Problem

Maintaining version in multiple places is error-prone:

```python
# Bad: Version duplicated
# setup.py
version = "1.0.0"

# src/package/__init__.py
__version__ = "1.0.0"

# docs/conf.py
version = "1.0.0"
```

If you bump one, forget the others → inconsistent version.

### The Solution

Single source of truth:

```toml
# pyproject.toml
[tool.hatch.version]
path = "src/package/__init__.py"
```

```python
# src/package/__init__.py
__version__ = "1.0.0"
```

```python
# Any file needing version
from package import __version__
# or
import importlib.metadata
version = importlib.metadata.version("package-name")
```

## Migration Patterns

### From setuptools + version in setup.py

```python
# Old setup.py
setup(
    name="myproject",
    version="1.0.0",
    packages=find_packages(),
)
```

To Hatchling:

```toml
# pyproject.toml
[tool.hatch.version]
path = "src/myproject/__init__.py"
```

```python
# src/myproject/__init__.py
__version__ = "1.0.0"
```

### From Poetry with version file

```toml
# Old pyproject.toml
[tool.poetry]
name = "myproject"
version = "1.0.0"
```

To Hatchling:

```toml
# New pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
dynamic = ["version"]  # Mark dynamic

[tool.hatch.version]
path = "src/myproject/__init__.py"
```

## Key Takeaways

1. **Single source of truth** - version defined once, read everywhere
2. **File-based** is simplest and most common
3. **VCS-based** is best for frequent releases
4. **Custom hooks** for special needs
5. **PEP 440** for version format
6. **Access at runtime** via `__version__` or importlib.metadata
7. **Avoid duplication** across multiple files

## References

- [Hatch Version Configuration](https://hatch.pypa.io/latest/config/version/)
- [hatch-vcs Plugin](https://github.com/ofek/hatch-vcs)
- [PEP 440 - Version Identification and Dependency Specification](https://peps.python.org/pep-0440/)
- [importlib.metadata Documentation](https://docs.python.org/3/library/importlib.metadata.html)
