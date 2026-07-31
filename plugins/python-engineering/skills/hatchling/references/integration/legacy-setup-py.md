---
category: integration
topics: [migration, setup.py, setuptools, pyproject.toml, modernization]
related: [./pep-standards.md, ./setuptools-compatibility.md]
---

# Legacy setup.py Migration to Hatchling

Reference guide for helping users transition projects from setuptools-based `setup.py` to modern hatchling-based `pyproject.toml` configuration. Use this when assisting with modernization efforts.

## Overview

The `setup.py` pattern (setuptools) was the dominant build approach for decades. Hatchling provides a cleaner, standards-based alternative while maintaining ecosystem compatibility.

### Key Differences

| Aspect               | setup.py (setuptools)               | hatchling (pyproject.toml)        |
| -------------------- | ----------------------------------- | --------------------------------- |
| Configuration File   | `setup.py` (Python code)            | `pyproject.toml` (TOML)           |
| Manifest             | `MANIFEST.in`                       | Configuration in `pyproject.toml` |
| Installation         | `python setup.py install`           | `pip install .`                   |
| Development Mode     | `python setup.py develop`           | `pip install -e .`                |
| Building             | `python setup.py sdist bdist_wheel` | `python -m build`                 |
| Standards Compliance | Partial (predates PEP 517)          | Full (PEP 517/621/660)            |
| Metadata Format      | Python dict in setup() call         | TOML [project] table              |

---

## Migration Path

### Step 1: Minimal pyproject.toml

Create `pyproject.toml` at project root:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mypackage"
version = "0.1.0"
```

### Step 2: Port Metadata from setup.py

**From setup.py**:

```python
setup(
    name="mypackage",
    version="1.0.0",
    description="Short description",
    author="Author Name",
    author_email="author@example.com",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/user/mypackage",
    license="MIT",
    classifiers=["Development Status :: 4 - Beta", "Programming Language :: Python :: 3"],
)
```

**To pyproject.toml**:

```toml
[project]
name = "mypackage"
version = "1.0.0"
description = "Short description"
readme = "README.md"
license = {file = "LICENSE"}
authors = [{name = "Author Name", email = "author@example.com"}]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3",
]

[project.urls]
Homepage = "https://github.com/user/mypackage"
```

### Step 3: Port Dependencies

**From setup.py**:

```python
setup(
    install_requires=["requests>=2.20", "click>=7.0,<8.0"],
    extras_require={"dev": ["pytest>=6.0", "black"], "docs": ["sphinx"]},
    python_requires=">=3.8",
)
```

**To pyproject.toml**:

```toml
[project]
requires-python = ">=3.8"
dependencies = [
    "requests>=2.20",
    "click>=7.0,<8.0",
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black"]
docs = ["sphinx"]
```

### Step 4: Port Entry Points

**From setup.py**:

```python
setup(
    entry_points={
        "console_scripts": ["mycommand=mypackage.cli:main"],
        "mygroup.subgroup": ["plugin1=mypackage.plugins:plugin1"],
    }
)
```

**To pyproject.toml**:

```toml
[project.scripts]
mycommand = "mypackage.cli:main"

[project.entry-points."mygroup.subgroup"]
plugin1 = "mypackage.plugins:plugin1"
```

### Step 5: Port Package Discovery

**From setup.py**:

```python
from setuptools import find_packages

setup(packages=find_packages(where="src"), package_dir={"": "src"})
```

**To pyproject.toml** (hatchling auto-discovers):

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

Or for standard layout (no configuration needed):

<eg>
mypackage/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
├── pyproject.toml
└── README.md
</eg>

### Step 6: Port File Inclusion (MANIFEST.in → pyproject.toml)

**From MANIFEST.in**:

<eg>
include LICENSE
include README.md
recursive-include mypackage *.txt
</eg>

**To pyproject.toml**:

```toml
[tool.hatch.build.targets.wheel]
# Include patterns
include = [
    "LICENSE",
    "README.md",
    "src/mypackage/*.txt",
]

# Exclude patterns
exclude = [
    "*.pyc",
    "__pycache__",
]
```

### Step 7: Port Dynamic Metadata

**From setup.py**:

```python
with open("mypackage/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break

setup(version=version)
```

**To pyproject.toml**:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/mypackage/__init__.py"
```

---

## Complete Migration Example

### Original setup.py

```python
from setuptools import setup, find_packages

with open("README.md") as f:
    long_description = f.read()

setup(
    name="example-pkg",
    version="1.2.0",
    description="Example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jane Doe",
    author_email="jane@example.com",
    url="https://github.com/jane/example-pkg",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["requests>=2.25.0", "pydantic>=1.8.0"],
    extras_require={"dev": ["pytest>=6.0", "black", "mypy"], "docs": ["sphinx", "sphinx-rtd-theme"]},
    entry_points={"console_scripts": ["example-cli=example_pkg.cli:main"]},
)
```

### Equivalent pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-pkg"
version = "1.2.0"
description = "Example package"
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.8"
authors = [{name = "Jane Doe", email = "jane@example.com"}]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
]
dependencies = [
    "requests>=2.25.0",
    "pydantic>=1.8.0",
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black", "mypy"]
docs = ["sphinx", "sphinx-rtd-theme"]

[project.scripts]
example-cli = "example_pkg.cli:main"

[project.urls]
Homepage = "https://github.com/jane/example-pkg"

[tool.hatch.build.targets.wheel]
packages = ["src/example_pkg"]
```

---

## Setuptools Compatibility

### Can You Keep setup.py?

**Yes**, but with caveats:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Even with this, if `setup.py` exists, pip will use it unless you explicitly configure hatchling. Modern approach: remove `setup.py` entirely.

### Gradual Migration

If gradual migration is required:

1. Create `pyproject.toml` with hatchling
2. Keep `setup.py` for compatibility
3. Use `pip install -e .` (respects pyproject.toml)
4. Remove `setup.py` once downstream adapts

### Setuptools to Hatchling Feature Mapping

| Setuptools Feature     | Hatchling Support                  | Notes                           |
| ---------------------- | ---------------------------------- | ------------------------------- |
| `packages`             | `packages` option                  | Auto-detection in `src/` layout |
| `py_modules`           | `[tool.hatch.build.targets.wheel]` | Configure explicitly            |
| `package_data`         | `force-include`                    | More flexible                   |
| `include_package_data` | Auto-included                      | By default                      |
| `exclude_package_data` | `exclude` pattern                  | Glob-based                      |
| `zip_safe=False`       | Always False                       | Wheels not zipped               |
| `setup_requires`       | `[build-system] requires`          | Build dependencies              |
| `python_requires`      | `requires-python`                  | PEP 621 standard                |
| Custom commands        | Build hooks                        | `[tool.hatch.build.hooks.*]`    |

---

## Verification Checklist

After migration, verify:

- [ ] `pip install .` works
- [ ] `pip install -e .` works (editable install)
- [ ] `python -m build` produces wheel and sdist
- [ ] Metadata correctly shows in `pip show mypackage`
- [ ] Entry points/scripts are executable
- [ ] All dependencies correctly specified
- [ ] Tests still pass with new configuration
- [ ] Package installable from source on clean Python environment

---

## Common Issues

### Issue: Package Not Found

**Cause**: Hatchling can't locate packages

**Solution**: Explicitly configure:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

### Issue: Dynamic Metadata Not Working

**Cause**: Incorrect path pattern

**Solution**: Verify pattern matches actual file:

```toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"
# Must contain: __version__ = "..."
```

### Issue: Missing Files in Wheel

**Cause**: File inclusion/exclusion patterns

**Solution**: Use force-include for unconventional layouts:

```toml
[tool.hatch.build.targets.wheel.force-include]
"data" = "mypackage/data"
```

---

## Resources

- [Hatchling Quick Start](https://hatch.pypa.io/)
- [Packaging.org Migration Guide](https://packaging.python.org/guides/modernize-setup-py-project)
- [PyPA Setup.py Deprecation](https://packaging.python.org/discussions/setup-py-deprecated/)
