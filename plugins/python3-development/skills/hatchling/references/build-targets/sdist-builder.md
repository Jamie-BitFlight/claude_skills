---
name: Hatchling Source Distribution Builder
description: 'Build source distributions (sdist): file selection, VCS integration, reproducible builds, legacy support, and archive configuration'
---

# Source Distribution Builder

A source distribution (sdist) is an archive containing the source code and metadata needed to build and install a Python package without making network requests. SDists allow end users to build from source on their target platform.

## Quick Start

The sdist builder is configured in the `pyproject.toml` file:

```toml
[tool.hatch.build.targets.sdist]
# Configuration options here
```

## Core Options

| Option                  | Default | Description                                              |
| ----------------------- | ------- | -------------------------------------------------------- |
| `core-metadata-version` | `"2.4"` | The version of core metadata to use                      |
| `strict-naming`         | `true`  | Whether file names should contain the normalized version |
| `support-legacy`        | `false` | Include `setup.py` for legacy installation mechanisms    |

### Example Configuration

```toml
[tool.hatch.build.targets.sdist]
core-metadata-version = "2.4"
strict-naming = true
support-legacy = false
```

## File Selection

### Default Behavior

By default, sdist includes:

- All Python source files
- `pyproject.toml`
- `README` files
- `LICENSE` files
- Files tracked by version control (respecting `.gitignore`)

### Including Files

```toml
[tool.hatch.build.targets.sdist]
include = [
  "src/",
  "tests/",
  "docs/",
  "CHANGELOG.md",
]
```

### Excluding Files

```toml
[tool.hatch.build.targets.sdist]
exclude = [
  "/.github/",
  "/docs/_build/",
  "*.pyc",
  "__pycache__/",
]
```

### Ignoring VCS

To ignore version control system ignore files:

```toml
[tool.hatch.build.targets.sdist]
ignore-vcs = true
```

## Versions

The sdist target supports a single version:

| Version    | Description                                          |
| ---------- | ---------------------------------------------------- |
| `standard` | The default and only format for source distributions |

## Archive Format

Source distributions are created as compressed tar archives (`.tar.gz`) containing:

1. **Source Code**: All Python modules and packages
2. **Metadata**: `PKG-INFO`, `pyproject.toml`
3. **Build Configuration**: Files needed to build the package
4. **Documentation**: README, LICENSE, etc.

## Common Patterns

### Library with Tests

```toml
[tool.hatch.build.targets.sdist]
include = [
  "/src",
  "/tests",
  "/pyproject.toml",
  "/README.md",
  "/LICENSE",
  "/CHANGELOG.md",
]

exclude = [
  "*.pyc",
  "__pycache__",
  ".pytest_cache",
]
```

### Documentation Included

```toml
[tool.hatch.build.targets.sdist]
include = [
  "/src",
  "/docs",
  "!/docs/_build",  # Exclude built docs
]
```

### Minimal Distribution

```toml
[tool.hatch.build.targets.sdist]
# Only include source code and essential files
only-include = [
  "src/",
  "pyproject.toml",
  "README.md",
  "LICENSE",
]
```

## Legacy Support

For compatibility with older installation tools:

```toml
[tool.hatch.build.targets.sdist]
support-legacy = true
```

This will generate a minimal `setup.py` file:

```python
# Generated setup.py
from setuptools import setup
setup()
```

## Build Data

Build hooks can modify sdist-specific build data:

- `dependencies` - Extra project dependencies

## Special Handling

### UNIX Socket Files

The sdist builder gracefully ignores UNIX socket files that cannot be archived.

### Reproducible Builds

Sdist archives are built reproducibly by default when `SOURCE_DATE_EPOCH` is set:

```bash
export SOURCE_DATE_EPOCH=$(date +%s)
hatch build -t sdist
```

### Archive Naming

Archive names follow the pattern: `{name}-{version}.tar.gz`

With `strict-naming = true` (default), the name is normalized according to PEP standards.

## File Path Handling

### Root Directory Structure

The archive contains a single root directory named `{name}-{version}/` containing all files.

### Path Rewriting

Use the `sources` option to rewrite paths:

```toml
[tool.hatch.build.targets.sdist.sources]
"src" = ""  # Move src/ contents to root
"docs" = "documentation"  # Rename docs/ to documentation/
```

## Validation

The sdist builder performs several validation checks:

1. **Metadata Validation**: Ensures required metadata fields are present
2. **File Existence**: Verifies all included files exist
3. **Path Safety**: Prevents inclusion of absolute paths or parent directory references

## Differences from Wheel

| Aspect       | SDist                       | Wheel                                   |
| ------------ | --------------------------- | --------------------------------------- |
| Format       | Source archive (`.tar.gz`)  | Binary distribution (`.whl`)            |
| Contents     | Source code + build config  | Compiled/ready-to-install files         |
| Installation | Requires build step         | Direct installation                     |
| Platform     | Platform-independent source | Can be platform-specific                |
| Size         | Usually smaller             | Can be larger (includes compiled files) |

## Quick Decision Guide

**Use sdist builder when:**

- Distributing source code to PyPI (standard practice)
- Users may need to build locally for their platform
- You want to enable custom build configurations

**SDist requirements:**

- Always pair with wheel for complete distribution
- Include all files needed for building (C headers, build scripts, etc.)
- Exclude build artifacts and cache directories

## Best Practices

### Include Everything Needed to Build

Ensure the sdist contains all files necessary to build the wheel:

```toml
[tool.hatch.build.targets.sdist]
include = [
  "/src",
  "/pyproject.toml",
  "/setup.py",  # If needed for C extensions
  "/MANIFEST.in",  # If used
  "/requirements.txt",  # If needed for development
]
```

### Exclude Build Artifacts

```toml
[tool.hatch.build.targets.sdist]
exclude = [
  "dist/",
  "build/",
  "*.egg-info/",
  "*.pyc",
  "__pycache__/",
  ".tox/",
  ".pytest_cache/",
]
```

### Version Control Integration

```toml
[tool.hatch.build.targets.sdist]
# Use VCS to determine included files (default)
ignore-vcs = false

# Or explicitly list everything
include = [
  "src/",
  "tests/",
  # ... all other files
]
```

## Troubleshooting

### Missing Files in Archive

Check if files are:

1. Ignored by VCS (`.gitignore`)
2. Not explicitly included
3. Explicitly excluded

### Large Archive Size

Review included files:

```bash
tar -tzf dist/package-1.0.0.tar.gz | head -20
```

Common culprits:

- Build artifacts
- Cache directories
- Large test data files
- Documentation builds

### Build Failures from SDist

Ensure all build dependencies are specified:

```toml
[build-system]
requires = [
  "hatchling",
  "wheel",
  # Other build dependencies
]
```

## Detailed Reference Documentation

For comprehensive information on specific topics, see:

- `../sdist-target/index.md` - Complete reference covering all aspects
- `../sdist-target/core-metadata-versions.md` - Metadata version selection and PEP 639
- `../sdist-target/vcs-integration.md` - File selection via .gitignore and .hgignore
- `../sdist-target/legacy-setup-py.md` - Backward compatibility configuration
- `../sdist-target/unix-socket-handling.md` - Special file handling
- `../sdist-target/reproducible-builds.md` - Deterministic distribution creation

## External References

- [Source Distribution Format](https://packaging.python.org/specifications/source-distribution-format/)
- [Core Metadata Specifications](https://packaging.python.org/specifications/core-metadata/)
- [PEP 517 - Build System Interface](https://www.python.org/dev/peps/pep-0517/)
- [PEP 639 - License Metadata](https://peps.python.org/pep-0639/)
