---
category: Advanced Build Features
topics: [distributed-artifacts, wheel-format, sdist-format, artifact-configuration, packaging]
related: [artifact-directories.md, force-include.md, path-rewriting.md]
---

# Distributed Artifacts

When helping users understand and configure what gets packaged, guide them to understand the packages created by Hatchling's build process: wheels and source distributions. Understanding artifact configuration enables control over package contents and format.

## Overview

Artifacts are the output files from the build process. Reference this to show users the multiple artifact types Hatchling supports:

- **Wheels** (`.whl`): Binary distribution format - the modern Python standard
- **Source distributions** (`.tar.gz`, `.zip`): Source archives with metadata
- **Custom artifacts**: User-defined output formats via builder plugins

## Wheel Artifacts

### Wheel Naming and Structure

Wheels follow the naming convention: `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`

Example: `mypackage-1.0.0-py3-none-any.whl`

Components:

- **distribution**: Package name (normalized)
- **version**: Package version
- **build tag**: Optional, for multiple builds of same version
- **python tag**: `py3`, `cp310`, etc.
- **abi tag**: `none`, `cp310`, etc.
- **platform tag**: `any`, `win_amd64`, `manylinux2014_x86_64`, etc.

### Wheel Contents

A wheel contains:

<eg>
mypackage-1.0.0-py3-none-any.whl
├── mypackage/                    # Your package
│   ├── __init__.py
│   ├── module.py
│   └── data/
├── mypackage-1.0.0.dist-info/    # Metadata
│   ├── WHEEL
│   ├── METADATA
│   ├── RECORD
│   ├── entry_points.txt
│   └── top_level.txt
</eg>

### Configuring Wheel Artifacts

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]

[tool.hatchling.targets.wheel.force-include]
assets = "mypackage/assets"
```

Configure what goes into wheels:

- `packages`: Which Python packages to include
- `force-include`: Additional files from anywhere
- `sources`: How to rewrite package paths
- `only-packages`: Exclude non-package Python files

## Source Distribution Artifacts

### Sdist Contents

Source distributions (sdists) include:

<eg>
mypackage-1.0.0.tar.gz
├── mypackage-1.0.0/
│   ├── PKG-INFO              # Metadata copy
│   ├── setup.py              # Legacy, if configured
│   ├── pyproject.toml        # Build config
│   ├── src/
│   │   └── mypackage/
│   ├── tests/
│   ├── docs/
│   └── MANIFEST.in           # File inclusion rules
</eg>

### Configuring Source Distributions

```toml
[tool.hatchling.targets.sdist]
packages = ["src/mypackage"]
include = [
    "tests/",
    "docs/",
    "LICENSE",
    "README.md"
]
exclude = [
    ".git*",
    "*.pyc",
    "__pycache__"
]
```

Include/exclude patterns:

- `include`: Glob patterns to include
- `exclude`: Glob patterns to explicitly exclude
- Relative to project root

## Build Artifacts List

Accessing artifact list in build hooks:

```python
class ArtifactInspectionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # See what will be included
        wheel_files = build_data['artifacts']['wheel']
        sdist_files = build_data['artifacts']['sdist']

        print(f"Wheel will include: {wheel_files}")
        print(f"Sdist will include: {sdist_files}")
```

## Output Directory Configuration

### Default Artifact Location

By default, Hatchling places artifacts in the `dist/` directory:

```bash
hatch build
# Creates:
# dist/mypackage-1.0.0-py3-none-any.whl
# dist/mypackage-1.0.0.tar.gz
```

### Custom Output Directory

Configure with builder options:

```bash
hatch build --target wheel -d build/wheels
```

Or in configuration:

```toml
[tool.hatchling.builders.wheel]
directory = "dist/wheels"
```

## Multiple Artifact Strategies

### Wheel-Only Distribution

Build only wheels, skip source distributions:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.builders.wheel"
```

Build only wheels when using the wheel backend.

### Selective Platform Builds

Build different wheels for different platforms:

```python
import platform

class PlatformSpecificBuildsHook(BuildHookInterface):
    def initialize(self, version, build_data):
        plat = platform.system()

        if plat == 'Windows':
            build_data['force_include']['dist/windows'] = 'mypackage/windows'
        elif plat == 'Darwin':
            build_data['force_include']['dist/macos'] = 'mypackage/macos'
```

### Universal Wheels

Wheels compatible with all Python versions:

Name: `mypackage-1.0.0-py2.py3-none-any.whl`

These work with both Python 2 and 3. Modern practice uses `py3-none-any` for Python 3-only.

## Artifact Patterns and File Selection

### Glob Pattern Matching

Artifacts are selected using glob patterns:

```toml
[tool.hatchling.targets.wheel]
# Match specific files
include = ["src/**/*.py", "src/**/*.pyi"]

# Pattern rules
# * = matches anything except /
# ** = matches anything including /
# ? = matches single character
# [abc] = matches character class
```

### Git-Aware Selection

If your project uses Git, Hatchling defaults to including only tracked files:

```python
# Hatchling checks:
# - Files tracked in git
# - .gitignore rules respected
# - Untracked files excluded by default
```

To include untracked files:

```toml
[tool.hatchling.targets.sdist]
force-include = { "untracked-file.txt" = "untracked-file.txt" }
```

## Artifact Verification

### Checking Wheel Contents

```bash
# List wheel contents
unzip -l dist/mypackage-1.0.0-py3-none-any.whl

# Extract for inspection
unzip -d wheel_contents dist/mypackage-1.0.0-py3-none-any.whl
```

### Checking Sdist Contents

```bash
# List sdist contents
tar -tzf dist/mypackage-1.0.0.tar.gz

# Extract for inspection
tar -xzf dist/mypackage-1.0.0.tar.gz
```

## Practical Examples

### Minimal Wheel Distribution

Only Python code, no extras:

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]
```

### Wheel with Data Files

Include non-Python data:

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]

[tool.hatchling.targets.wheel.force-include]
data = "mypackage/data"
templates = "mypackage/templates"
```

### Complete Distribution

Wheel with everything; sdist with development files:

```toml
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]
[tool.hatchling.targets.wheel.force-include]
assets = "mypackage/assets"

[tool.hatchling.targets.sdist]
packages = ["src/mypackage"]
include = ["tests/", "docs/", "*.md"]
exclude = [".git*", "__pycache__"]
```

## Best Practices

- Wheel: Include only runtime requirements (Python code + data)
- Sdist: Include development files (tests, docs, examples)
- Use consistent naming for both wheel and sdist versions
- Test wheel installation on target platforms
- Verify no sensitive files in artifacts (credentials, keys)
- Document artifact contents in release notes
- Use version tags in filenames for clarity
- Test sdist builds reproduce from source

## Troubleshooting

### Missing Files in Wheel

**Issue**: Expected files not in built wheel

**Solution**: Check package discovery and force-include:

```toml
# Verify packages found
[tool.hatchling.targets.wheel]
packages = ["src/mypackage"]

# Add missing non-Python files
[tool.hatchling.targets.wheel.force-include]
missing_files = "mypackage/missing_files"
```

### Wheel Installation Failures

**Issue**: Wheel installs but imports fail

**Solution**: Verify package paths in wheel match imports:

```bash
unzip -l dist/mypackage*.whl | grep __init__
# Should show: mypackage/__init__.py
```

### Sdist Build from Wheel Fails

**Issue**: `pip install` from sdist fails when wheel works

**Solution**: Ensure all source files in sdist:

```toml
[tool.hatchling.targets.sdist]
include = ["src/", "tests/", "setup.py"]
```

## See Also

- `artifact-directories.md` - Output directory configuration
- `force-include.md` - Adding arbitrary files
- `path-rewriting.md` - Package path configuration
