---
category: standards
topics: [pep-517, pep-518, pep-621, pep-625, pep-639, pep-643, pep-660, pep-440, pep-508]
related: [python-packaging-overview.md, core-metadata.md, distribution-formats.md, dependency-formats.md]
---

# PEP References and Compliance

## Essential PEPs for Hatchling

This document maps Python Enhancement Proposals (PEPs) that define packaging standards directly applicable to hatchling's operations. Reference these PEPs when explaining to users how Hatchling implements Python packaging standards or when debugging configuration issues related to specific PEP requirements.

## Build System Interface (PEP 517)

**Status**: Final (February 2013) **Authority**: BDFL-Delegate Alyssa Coghlan **Repository**: [python/peps - PEP 517](https://github.com/python/peps/blob/main/peps/pep-0517.rst)

### Overview

PEP 517 defines a backend interface separating build frontends (like pip) from build systems (like hatchling). This allows projects to declare how they should be built without being coupled to setuptools.

### Core Hooks Implemented by Hatchling

**Mandatory Hooks:**

- `build_wheel(wheel_directory, config_settings=None, metadata_directory=None)` - Creates a wheel distribution
- `build_sdist(sdist_directory, config_settings=None)` - Creates a source distribution

**Optional Hooks:**

- `get_requires_for_build_wheel(config_settings=None)` - Returns additional build dependencies for wheels
- `get_requires_for_build_sdist(config_settings=None)` - Returns additional build dependencies for sdists
- `prepare_metadata_for_build_wheel(metadata_directory, config_settings=None)` - Pre-builds wheel metadata for inspection

### Configuration

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The `build-backend` specifies the module path to hatchling's backend object. The `requires` list specifies PEP 508 dependency strings needed to run the build.

---

## Build System Requirements (PEP 518)

**Status**: Final (September 2017) **Authority**: BDFL-Delegate Alyssa Coghlan **Repository**: [python/peps - PEP 518](https://github.com/python/peps/blob/main/peps/pep-0518.rst)

### Overview

PEP 518 standardizes the `[build-system]` table in `pyproject.toml` as the canonical location for specifying build dependencies.

### Required Fields

- `requires` - Array of PEP 508 dependency specifications required to build the project
- `build-backend` - Module path to the backend object (e.g., `"hatchling.build"`)
- `backend-path` (optional) - List of directories to search for the backend module

### Example Configuration

```toml
[build-system]
requires = ["hatchling", "hatch-vcs>=0.3.0"]
build-backend = "hatchling.build"
```

### Impact on Hatchling

Hatchling must be listed in `requires` to be available as a build dependency. Users can install hatchling only during the build process without requiring it as a runtime dependency.

---

## Project Metadata Specification (PEP 621)

**Status**: Final (April 2021) **Authority**: BDFL-Delegate Brett Cannon **Repository**: [python/peps - PEP 621](https://github.com/python/peps/blob/main/peps/pep-0621.rst)

### Overview

PEP 621 standardizes project metadata in the `[project]` table of `pyproject.toml`, replacing scattered configuration across multiple formats.

### Core Metadata Fields

**Required:**

- `name` - Distribution name (normalized per PEP 503)
- `version` - Project version (PEP 440 compliant)

**Recommended:**

- `description` - Short one-line description
- `readme` - Path to README file with optional content type
- `requires-python` - Python version specifier (PEP 440)
- `license` - SPDX license identifier or file reference
- `authors`, `maintainers` - Contact information with names and emails
- `keywords` - List of search terms
- `classifiers` - PyPI trove classifiers

**Optional:**

- `dependencies` - List of runtime dependency specifications (PEP 508)
- `optional-dependencies` - Mapping of extra names to dependency lists
- `urls` - Mapping of URL purposes to actual URLs

### Dynamic Fields

The `dynamic` array indicates which fields will be computed at build time:

```toml
[project]
name = "example"
dynamic = ["version", "description"]
```

Hatchling supports dynamic version extraction from code, environment variables, or regex patterns.

### Example Configuration

```toml
[project]
name = "example-package"
version = "1.0.0"
description = "A sample package"
readme = "README.md"
requires-python = ">=3.8"
license = {file = "LICENSE"}
authors = [{name = "John Doe", email = "john@example.com"}]
dependencies = [
    "httpx>=0.20.0",
    "colorama; sys_platform=='win32'"
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=3.0"]
docs = ["sphinx>=4.0"]
```

---

## Source Distribution Format (PEP 625)

**Status**: Final (September 2020) **Authority**: BDFL-Delegate Paul Moore **Repository**: [python/peps - PEP 625](https://github.com/python/peps/blob/main/peps/pep-0625.rst)

### Overview

PEP 625 standardizes the filename format for source distributions (sdists).

### Filename Format

<eg>
{name}-{version}.tar.gz
</eg>

Where:

- `{name}` is the normalized package name per PEP 503
- `{version}` is the canonicalized version per PEP 440

### Example

<eg>
my-package-1.0.0.tar.gz
requests-2.28.1.tar.gz
</eg>

### Archive Structure

The sdist must contain:

- Single top-level directory: `{name}-{version}/`
- `pyproject.toml` (project configuration)
- `PKG-INFO` (metadata file using core metadata spec v2.2+)
- Source files and build files

---

## Metadata for Source Distributions (PEP 643)

**Status**: Final (November 2020) **Authority**: BDFL-Delegate Paul Ganssle **Repository**: [python/peps - PEP 643](https://github.com/python/peps/blob/main/peps/pep-0643.rst)

### Overview

PEP 643 standardizes metadata storage in source distributions and introduces the concept of "Dynamic" metadata fields.

### Dynamic Fields

Fields marked as `Dynamic` in the `PKG-INFO` indicate values that will be computed at wheel build time:

<eg>
Name: example
Version: 1.0.0
Dynamic: requires-dist
Dynamic: description
</eg>

This allows projects to:

- Compute dependencies based on environment
- Generate descriptions from source code
- Calculate version from VCS

### Requirements

- Source distributions must use Core Metadata v2.2 or later
- The `Name` and `Version` fields MUST NOT be marked as Dynamic
- Wheel metadata must not include `Dynamic` fields (those values become fixed)

---

## Editable Installs (PEP 660)

**Status**: Final (September 2021) **Authority**: BDFL-Delegate Paul Ganssle **Repository**: [python/peps - PEP 660](https://github.com/python/peps/blob/main/peps/pep-660.rst)

### Overview

PEP 660 enables development workflows where packages are installed in "editable" mode, allowing code changes to take effect without reinstalling.

### Hatchling Support

Hatchling implements the optional hooks:

- `build_editable(wheel_directory, config_settings=None, metadata_directory=None)` - Creates an editable wheel
- `get_requires_for_build_editable(config_settings=None)` - Returns editable build dependencies
- `prepare_metadata_for_build_editable(metadata_directory, config_settings=None)` - Pre-builds editable metadata

### Installation Command

```bash
pip install -e .
```

---

## License Metadata (PEP 639)

**Status**: Final (December 2024) **Authority**: BDFL-Delegate Paul Ganssle **Repository**: [python/peps - PEP 639](https://github.com/python/peps/blob/main/peps/pep-0639.rst)

### Overview

PEP 639 modernizes license metadata using SPDX license expressions and explicit license file tracking.

### New Fields in Core Metadata v2.4+

- `License-Expression` - SPDX license expression (e.g., `MIT OR Apache-2.0`)
- `License-File` - Path to each license file (repeatable field)

### Configuration in pyproject.toml

```toml
[project]
license = "MIT"  # Simple SPDX expression

[project]
license = "MIT AND (Apache-2.0 OR BSD-2-Clause)"  # Complex expression

license-files = {globs = ["LICENSE", "LICENSE.*"]}  # Include license files
```

### Impact on Distributions

Wheel distributions must include license files in `{name}-{version}.dist-info/licenses/` as specified in the metadata.

---

## Version Identification (PEP 440)

**Status**: Final (August 2014) **Authority**: BDFL-Delegate Alyssa Coghlan **Repository**: [python/peps - PEP 440](https://github.com/python/peps/blob/main/peps/pep-0440.rst)

### Overview

PEP 440 defines the canonical versioning scheme for Python packages.

### Version Format

<eg>
[N!]N(.N)*[{a|b|rc}N][.postN][.devN]
</eg>

Components:

- `N!` - Optional epoch for version reset
- `N(.N)*` - Release segment (one or more numbers)
- `{a|b|rc}N` - Pre-release phase and number
- `.postN` - Post-release number
- `.devN` - Development release number

### Examples

<eg>
1.0.0          # Final release
1.0.0a1        # Alpha release
1.0.0b2        # Beta release
1.0.0rc1       # Release candidate
1.0.0.post1    # Post-release
1.0.0.dev0     # Development release
2!1.0.0        # Epoch reset to version 2
</eg>

### Hatchling Integration

Hatchling supports multiple version sources:

- Static version in `pyproject.toml`
- Dynamic version from Python code
- Dynamic version from environment variables
- Dynamic version from regex patterns applied to files

All sources must produce PEP 440 compliant versions.

---

## Dependency Specification (PEP 508)

**Status**: Final (September 2015) **Authority**: BDFL-Delegate Donald Stufft **Repository**: [python/peps - PEP 508](https://github.com/python/peps/blob/main/peps/pep-0508.rst)

See `dependency-formats.md` for detailed coverage.

---

## Summary Table

| PEP | Title                        | Status | Hatchling Role         |
| --- | ---------------------------- | ------ | ---------------------- |
| 517 | Build System Interface       | Final  | Backend implementation |
| 518 | Build System Requirements    | Final  | Configuration schema   |
| 621 | Project Metadata             | Final  | Metadata source        |
| 625 | Source Distribution Filename | Final  | Sdist naming           |
| 639 | License Metadata             | Final  | License handling       |
| 640 | Version Flexibility          | Final  | Version management     |
| 643 | Source Distribution Metadata | Final  | Metadata in sdists     |
| 660 | Editable Installs            | Final  | Dev installation       |

## Related Standards

- `core-metadata.md` - Metadata format for wheels/sdists
- `distribution-formats.md` - Wheel and sdist structures
- `dependency-formats.md` - PEP 508 detailed reference
