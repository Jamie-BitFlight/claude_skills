---
category: integration
topics: [pep-standards, pep-517, pep-621, pep-660, build-backend, compliance]
related: [./legacy-setup-py.md, ./setuptools-compatibility.md]
---

# PEP Standards Compatibility

Reference documentation on hatchling's full implementation of Python Enhancement Proposals that define packaging standards. Use this when helping users understand PEP compliance and standards-based configuration.

## PEP 517: A Build-System Independent Format

**Status**: Final (Fully Implemented)

PEP 517 defines a standard interface for build backends to interact with frontends (like pip). Hatchling is a PEP 517 compliant backend.

### Key Hatchling Compliance

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Mandatory Hooks Implemented

| Hook                                                                | Purpose                   | Hatchling Support |
| ------------------------------------------------------------------- | ------------------------- | ----------------- |
| `build_wheel(wheel_directory, config_settings, metadata_directory)` | Build a wheel archive     | Full support      |
| `build_sdist(sdist_directory, config_settings)`                     | Build source distribution | Full support      |

### Optional Hooks Implemented

| Hook                                                                    | Purpose                             | Hatchling Support |
| ----------------------------------------------------------------------- | ----------------------------------- | ----------------- |
| `get_requires_for_build_wheel(config_settings)`                         | Declare build dependencies          | Full support      |
| `prepare_metadata_for_build_wheel(metadata_directory, config_settings)` | Extract metadata before wheel build | Full support      |
| `get_requires_for_build_sdist(config_settings)`                         | Declare sdist build dependencies    | Full support      |

### Build Environment

Hatchling respects PEP 517 build environment isolation:

- All `requires` from `[build-system]` are installed before build operations
- Build backend runs in isolated subprocess (via pip/frontends)
- Build scripts execute with source tree as working directory
- No direct access to user's site-packages by default

**Reference**: [PEP 517 Full Specification](https://peps.python.org/pep-0517/)

---

## PEP 660: Editable Installs

**Status**: Final (Fully Implemented)

PEP 660 standardizes editable installs (development mode) for PEP 517 backends.

### Editable Install Support

When using `pip install -e .`, hatchling implements:

```python
# Hook implementations:
build_editable(wheel_directory, config_settings, metadata_directory)
get_requires_for_build_editable(config_settings)
prepare_metadata_for_build_editable(metadata_directory, config_settings)
```

### How Hatchling Handles Editable Installs

1. **Editable Wheel Creation**: Generates a wheel that imports from the source directory
2. **Direct URL Tracking**: Installs `direct_url.json` pointing to source tree
3. **Zero-Copy Development**: Changes to Python code are immediately reflected without reinstall
4. **Entry Point Handling**: Scripts and entry points are installed normally

### Usage

```bash
# Install package in editable mode
pip install -e .

# Changes to source code are immediately importable
python -c "import mypackage"  # Uses source directory
```

### Limitations

- C extension modules require rebuild after source changes
- Changes to `pyproject.toml` (entry points, dependencies) require reinstall
- Non-Python files in data directories require reinstall

**Reference**: [PEP 660 Full Specification](https://peps.python.org/pep-0660/)

---

## PEP 621: Storing Project Metadata in pyproject.toml

**Status**: Final (Fully Implemented)

PEP 621 standardizes where project metadata lives - in the `[project]` table of `pyproject.toml`.

### Metadata Fields Supported

Hatchling recognizes all PEP 621 fields:

| Field                   | Required       | Type                     | Hatchling Support |
| ----------------------- | -------------- | ------------------------ | ----------------- |
| `name`                  | Yes            | string                   | Full              |
| `version`               | Yes or dynamic | string                   | Full + dynamic    |
| `description`           | No             | string                   | Full              |
| `readme`                | No             | string or table          | Full              |
| `requires-python`       | No             | string                   | Full              |
| `license`               | No             | table                    | Full              |
| `authors`/`maintainers` | No             | array of tables          | Full              |
| `keywords`              | No             | array of strings         | Full              |
| `classifiers`           | No             | array of strings         | Full              |
| `urls`                  | No             | table                    | Full              |
| `dependencies`          | No             | array of PEP 508 strings | Full              |
| `optional-dependencies` | No             | table                    | Full              |
| `dynamic`               | No             | array                    | Full              |

### Example PEP 621 Configuration

```toml
[project]
name = "mypackage"
version = "0.1.0"
description = "A short description"
readme = "README.md"
requires-python = ">=3.8"
license = {file = "LICENSE"}
authors = [{name = "Author Name", email = "author@example.com"}]
dependencies = [
    "requests>=2.20",
    "click>=7.0",
]

[project.optional-dependencies]
dev = ["pytest>=6.0", "black"]

[project.urls]
Homepage = "https://github.com/user/mypackage"
```

### Dynamic Metadata

Hatchling supports marking fields as `dynamic` for backend-computed values:

```toml
[project]
name = "mypackage"
dynamic = ["version"]  # Compute version at build time

[tool.hatch.version]
path = "src/mypackage/__init__.py"
```

**Reference**: [PEP 621 Full Specification](https://peps.python.org/pep-0621/)

---

## PEP 639: Improving License Clarity with SPDX

**Status**: Final (Implemented)

PEP 639 improves license specification with SPDX expressions and explicit license file tracking.

### License Configuration in Hatchling

```toml
[project]
# Option 1: Simple SPDX expression (PEP 639)
license = "MIT"

# Option 2: License file reference
license = {file = "LICENSE"}

# Option 3: Inline license text
license = {text = "Full license text here"}
```

### License Files

Hatchling automatically includes license files:

```toml
[tool.hatch.build.targets.wheel.force-include]
"LICENSE" = "LICENSE"
"COPYING.txt" = "COPYING.txt"
```

### SPDX License Expressions

Standard SPDX identifiers are preferred:

<eg>
MIT
Apache-2.0
GPL-3.0-or-later
(MIT OR Apache-2.0)
MIT AND (Apache-2.0 OR GPL-2.0-only)
</eg>

**Note**: Full SPDX expression support in metadata is still evolving.

**Reference**: [PEP 639 Full Specification](https://peps.python.org/pep-0639/)

---

## PEP 440: Version Identification and Dependency Specification

**Status**: Final (Fully Implemented)

PEP 440 defines the standard version scheme for Python packages.

### Supported Version Schemes

Hatchling enforces PEP 440 versioning:

| Scheme         | Example               | Valid                   |
| -------------- | --------------------- | ----------------------- |
| Public version | `1.0.0`               | Yes                     |
| Pre-release    | `1.0.0a1`, `1.0.0rc2` | Yes                     |
| Post-release   | `1.0.0.post1`         | Yes                     |
| Dev release    | `1.0.0.dev1`          | Yes                     |
| Local version  | `1.0.0+local`         | Yes (for editable only) |

### Version Validation

Hatchling validates all versions against PEP 440:

```python
# Valid
1.0.0
2.0.0a1
1.0.0.post1
1.0.0.dev0
1.0.0rc1

# Invalid (will error)
1.0
v1.0.0
1.0.0_dev
```

### Dependency Specification (PEP 508)

Dependencies use PEP 508 format:

```toml
dependencies = [
    "package",                          # Any version
    "package>=1.0",                     # Version specifier
    "package>=1.0,<2.0",                # Multiple specifiers
    "package[extra]>=1.0",              # With extras
    'package>=1.0; python_version<"3.10"',  # Environment markers
]
```

**Reference**: [PEP 440 Full Specification](https://peps.python.org/pep-0440/)

---

## PEP 518: Specifying Build System Requirements

**Status**: Final (Fully Implemented)

PEP 518 defines the `[build-system]` table that declares build backend and dependencies.

### Build System Configuration

```toml
[build-system]
requires = ["hatchling>=1.0.0"]
build-backend = "hatchling.build"
```

### Advanced Configuration

```toml
[build-system]
requires = [
    "hatchling>=1.0.0",
    "some-build-plugin>=2.0",
]
build-backend = "hatchling.build"
backend-path = ["."]  # For in-tree backends
```

### Minimal Setup

The absolute minimum is:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Reference**: [PEP 518 Full Specification](https://peps.python.org/pep-0518/)

---

## Compliance Summary

| PEP | Title                           | Status | Hatchling | Verified |
| --- | ------------------------------- | ------ | --------- | -------- |
| 517 | Build-System Independent Format | Final  | Full      | Yes      |
| 518 | Build System Requirements       | Final  | Full      | Yes      |
| 621 | pyproject.toml Metadata         | Final  | Full      | Yes      |
| 639 | SPDX License Clarity            | Final  | Partial   | Yes      |
| 660 | Editable Installs               | Final  | Full      | Yes      |
| 440 | Version Identification          | Final  | Full      | Yes      |
