---
category: core-concepts
topics: [distribution-formats, wheel, sdist, packaging, installation]
related: [reproducible-builds.md, development-vs-distribution.md, vcs-file-selection.md]
---

# Wheel vs Source Distribution: Trade-offs and Use Cases

## Overview

When helping users understand distribution formats and packaging strategy, reference this document to explain how Hatchling builds two distribution formats—wheels (binary distributions) and source distributions (sdist)—each with different trade-offs and use cases.

**Source:** [Hatch Builder Plugins](https://hatch.pypa.io/1.1/plugins/builder/) [Wheel Builder Documentation](https://hatch.pypa.io/1.8/plugins/builder/wheel/) [Source Distribution Builder Documentation](https://hatch.pypa.io/latest/plugins/builder/sdist/)

## Format Basics

### Wheel (PEP 427)

A wheel is a pre-built binary distribution format.

**Structure:**

<eg>
myproject-1.0.0-py3-none-any.whl
├── myproject/
│   ├── __init__.py
│   ├── module.py
│   └── py.typed
├── myproject-1.0.0.dist-info/
│   ├── WHEEL
│   ├── METADATA
│   ├── RECORD
│   ├── entry_points.txt
│   └── top_level.txt
└── myproject-1.0.0.data/
    └── (optional: data files)
</eg>

**Format:**

- ZIP archive
- Binary ready to install
- Includes pre-built extension modules
- No build step during installation

**Example Installation:**

```bash
pip install myproject-1.0.0-py3-none-any.whl
# Installation is just file copying
```

### Source Distribution (sdist)

A source distribution is a compressed archive of source code.

**Structure:**

<eg>
myproject-1.0.0.tar.gz
├── myproject-1.0.0/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── myproject/
│   │       ├── __init__.py
│   │       └── module.py
│   ├── tests/
│   │   └── test_module.py
│   └── PKG-INFO
</eg>

**Format:**

- TAR.GZ archive
- Source code + metadata
- Can include anything (tests, docs, etc.)
- Build step during installation

**Example Installation:**

```bash
pip install myproject-1.0.0.tar.gz
# pip runs build backend to build wheel
# Then installs the built wheel
```

## Key Differences

| Aspect                 | Wheel                      | Sdist                    |
| ---------------------- | -------------------------- | ------------------------ |
| **Size**               | Small (pre-built)          | Larger (includes source) |
| **Installation speed** | Fast (copy files)          | Slower (must build)      |
| **Build time**         | Happens at build time      | Happens at install time  |
| **Dependencies**       | Must declare at build time | Can use dynamic deps     |
| **Editable installs**  | Supported (PEP 660)        | Not supported            |
| **Contains tests**     | Usually not                | Usually yes              |
| **Platform-specific**  | Usually generic            | Always source code       |
| **Security**           | Can audit before install   | Must be auditable later  |
| **Flexibility**        | Build options fixed        | Install options possible |

## When to Use What

### Use Wheels for Users

**When:** Installing packages for use

```bash
# Installation is fast
pip install requests
# Gets pre-built wheel, installs in seconds
```

**Why wheels:**

- No build required
- Fast installation
- Reproducible (exact same binaries)
- No build tools needed

### Use Source Distributions for Developers

**When:** Contributing to project or understanding code

```bash
pip install -e .  # Editable install from source
# or
git clone https://github.com/org/project.git
cd project
pip install -e .
```

**Why source:**

- Can modify code and test immediately
- Access to test suite
- Can debug and understand implementation
- Can submit contributions

## Building Both (Recommended)

Hatchling builds both by default:

```bash
hatch build
# Creates:
# dist/myproject-1.0.0-py3-none-any.whl  (wheel)
# dist/myproject-1.0.0.tar.gz             (sdist)
```

**Why both?**

1. **PyPI expects both** - Users can choose preferred format
2. **Fallback option** - If wheel not available, user can build from source
3. **Maximum compatibility** - Works with all pip versions
4. **Developer convenience** - Source available for contributions

## Configuration Trade-offs

### Wheel Configuration

Wheels are built once, with fixed options:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]

# Metadata version (affects compatibility)
core-metadata-version = "2.1"

# Platform tags
macos-max-compat = true
```

**Trade-off:** Decide build options at build time, not install time.

**Example:**

```bash
# Build generic wheel
hatch build --target wheel

# Creates: myproject-1.0.0-py3-none-any.whl
# Anyone can install with: pip install myproject-1.0.0-py3-none-any.whl
```

### Sdist Configuration

Source distributions can include more files:

```toml
[tool.hatch.build.targets.sdist]
packages = ["src/myproject"]

# Include tests for developers
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/docs/**/*",
]

# Exclude large non-essential files
exclude = [
    "*.pyc",
    "__pycache__",
    ".git",
]
```

**Trade-off:** Include more for developers, but larger distribution.

## File Selection Differences

### Wheel

Typically includes only runtime files:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
# Just the Python package
```

Result:

<eg>
myproject-1.0.0-py3-none-any.whl
└── myproject/
    ├── __init__.py
    ├── module.py
    └── py.typed
</eg>

### Sdist

Typically includes everything needed for development:

```toml
[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/docs",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
]
```

Result:

<eg>
myproject-1.0.0.tar.gz
└── myproject-1.0.0/
    ├── src/myproject/
    ├── tests/
    ├── docs/
    ├── README.md
    ├── LICENSE
    └── pyproject.toml
</eg>

## Platform-Specific Considerations

### Pure Python Packages

Works identically on all platforms.

**Wheel naming:**

<eg>
myproject-1.0.0-py3-none-any.whl
              ^^         ^   ^
              |          |   └─ Platform: any
              |          └────── ABI: none
              └─────────────────── Python: 3.x
</eg>

**Works everywhere:** Linux, macOS, Windows, etc.

### Packages with Extensions

C/C++ extensions must be compiled for each platform.

**Wheel naming:**

<eg>
myproject-1.0.0-cp311-cp311-win_amd64.whl
              ^^^^^^^^^^^^^^   ^^^^^^^
              |                └── Platform: Windows 64-bit
              └───────────────────── Python: 3.11, ABI: 3.11
</eg>

**Different wheels for:**

- Python versions: cp38, cp39, cp310, cp311, etc.
- ABIs (if applicable): cp38, pp38, etc.
- Platforms: linux_x86_64, macos_arm64, win_amd64, etc.

**Build approach:**

```toml
[build-system]
requires = ["hatchling", "scikit-build-core"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.scikit-build]
experimental = true
```

Hatchling (with scikit-build-core) builds wheels for each target platform.

## PyPI Distribution Strategy

### Recommended: Upload Both

```bash
hatch build
# Creates both wheel and sdist

# Upload both to PyPI
twine upload dist/*
# or
python -m build && twine upload dist/*
```

**Why both:**

- Default: pip prefers wheels (faster)
- Fallback: sdist if wheel unavailable
- Developers: can access source easily

### PyPI File Structure

After upload:

<eg>
myproject 1.0.0 - PyPI
├── myproject-1.0.0-py3-none-any.whl       (preferred)
└── myproject-1.0.0.tar.gz                 (fallback)
</eg>

User install:

```bash
pip install myproject==1.0.0
# pip downloads wheel if available
# Falls back to sdist if wheel missing
```

### When to Upload Only Wheel

Some projects only upload wheels:

```bash
hatch build --target wheel
twine upload dist/*.whl
```

**Reasons:**

- Package is complex to build
- Limited development audience
- Pure commercial product
- Confident in wheel compatibility

**Risk:** Users with unusual environments may not be able to install.

## Installation Workflows

### User Installation (Fast Path)

```bash
pip install myproject
# 1. PyPI serves wheel
# 2. pip downloads wheel
# 3. pip installs (just copies files)
# Total: seconds
```

### User Installation (Fallback Path)

```bash
# If wheel not available:
pip install myproject
# 1. PyPI serves sdist
# 2. pip downloads sdist
# 3. pip extracts sdist
# 4. pip runs build backend (hatchling)
# 5. pip installs built wheel
# Total: minutes (if compilation needed)
```

### Developer Installation (Development)

```bash
git clone https://github.com/org/myproject.git
cd myproject
pip install -e .
# 1. pip builds editable wheel (PEP 660)
# 2. pip installs with .pth file
# 3. Changes to source immediately visible
# Total: seconds, live updates
```

## Build Performance Impact

### Wheel Build Time

Typically fast for pure Python:

```bash
hatch build --target wheel
# ~2-5 seconds for pure Python package

# With C extensions:
# ~30 seconds - 5 minutes (depends on complexity)
```

### Sdist Build Time

Usually fast (just archiving):

```bash
hatch build --target sdist
# ~1-2 seconds
# (just tar + gzip source files)
```

### Total Build Time

```bash
hatch build
# ~3-7 seconds for pure Python
# ~1-5 minutes with C extensions
# (includes time for both wheel and sdist)
```

## Migration from setuptools

### Old Setup (setuptools)

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="myproject",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
```

Built with:

```bash
python setup.py sdist bdist_wheel
```

### New Setup (Hatchling)

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "1.0.0"

[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]
```

Built with:

```bash
hatch build
# or
python -m build
```

## Best Practices

### 1. Always Build Both Formats

Include both wheel and sdist in distributions:

```bash
hatch build
# Always creates both
```

### 2. Test Wheel Installation

Ensure wheel installs correctly:

```bash
# In CI/CD
pip install dist/*.whl
python -c "import myproject; print(myproject.__version__)"
```

### 3. Test Editable Installation

Ensure developers can install -e:

```bash
pip install -e .
# Should work immediately
```

### 4. Minimize Sdist Size

Use `.gitignore` to exclude unnecessary files:

```gitignore
# Large files not needed for builds
/docs/build/
/coverage/
*.whl
```

Hatchling respects .gitignore automatically.

### 5. Document Installation

In README:

````markdown
## Installation

### For Users (Recommended)

```bash
pip install myproject
```
````

### For Development

```bash
git clone https://github.com/org/myproject.git
cd myproject
pip install -e ".[dev]"
```

## Key Takeaways

1. **Wheels** are pre-built, fast to install, no build tools needed
2. **Sdists** contain source, support any platform, required for development
3. **Upload both** to PyPI for maximum compatibility
4. **Wheels** determined at build time, fixed options
5. **Sdists** can include more files for developers
6. **Editable installs** from source for live development
7. **Hatchling** builds both automatically

## References

- [PEP 427 - The Wheel Binary Distribution Format](https://peps.python.org/pep-0427/)
- [Hatch Wheel Builder](https://hatch.pypa.io/latest/plugins/builder/wheel/)
- [Hatch Source Distribution Builder](https://hatch.pypa.io/latest/plugins/builder/sdist/)
- [Python Packaging Guide](https://packaging.python.org/)
