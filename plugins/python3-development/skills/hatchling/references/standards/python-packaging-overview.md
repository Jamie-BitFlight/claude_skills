---
category: standards
topics: [python-packaging, pep-specifications, pypa-standards, version-identification, dependency-specification, build-backend]
related: [pep-references.md, core-metadata.md, distribution-formats.md, dependency-formats.md, vcs-integration.md]
---

# Python Packaging Standards Overview

## Authority and Governance

The **Python Packaging Authority (PyPA)** maintains the canonical specifications for Python packaging through the [PyPA Specifications](https://packaging.python.org/en/latest/specifications/) portal. These standards evolve through the **Python Enhancement Proposals (PEP)** process under the Python Software Foundation.

Historical specifications (PEP documents) remain authoritative references but are superseded by the current specifications maintained on the PyPA specifications page.

## Core Specification Categories

Python packaging standards are organized into six interoperability domains:

### 1. Package Distribution Metadata

Defines how package information is declared and described:

- **Package naming conventions** and normalization rules
- **Version identification and versioning schemes** (PEP 440)
- **Dependency declarations** (PEP 508)
- **Project configuration** via `pyproject.toml` (PEP 621)
- **Core metadata format** for describing packages (version 2.5 as of September 2025)

### 2. Package Installation Metadata

Addresses how installed packages are recorded and located:

- **Installation record management** (PEP 376)
- **Entry points specification** for executable scripts and plugins
- **Virtual environment standards**
- **Environment markers** for conditional installation (PEP 508)

### 3. Package Distribution File Formats

Specifies the physical format of distributable packages:

- **Wheel format** - binary distribution archives (PEP 427)
- **Source distribution (sdist) format** - source code archives (PEP 625, PEP 643)
- **Archive naming conventions** and compatibility tags
- **Metadata inclusion** within distribution files

### 4. Package Index Interfaces

Defines how packages are published and discovered:

- **Repository APIs** for package registration and retrieval
- **Authentication mechanisms** (`.pypirc` configuration)
- **Simple index protocol** for package discovery
- **File management** and version hosting

### 5. Build System Specifications

Describes the interface between build systems and packaging tools:

- **PEP 517** - Build backend interfaces (build_wheel, build_sdist)
- **PEP 518** - Build system requirements in `pyproject.toml`
- **PEP 660** - Editable installs
- **PEP 517 hooks** for customizing build processes

### 6. Python Description Formats

Standards for describing Python environments and projects:

- **Build metadata** specifications
- **Reproducible environment** definitions (emerging `pylock.toml`)
- **Configuration file formats** (TOML, INI, JSON)

## Key Standardization Process

The PyPA maintains these standards through a formal review process documented at [pypa.io/specifications](https://www.pypa.io/en/latest/specifications/#handling-fixes-and-other-minor-updates). Changes undergo community discussion and BDFL (Benevolent Dictator For Life) review before approval.

## Using These Standards with Hatchling

When helping users configure Hatchling projects, reference these standards categories to:

**Package Distribution Metadata** - Guide users in declaring package information in `pyproject.toml` following PEP 621. Explain how package names, versions (PEP 440), and dependencies (PEP 508) establish interoperability.

**Build System Specifications** - Reference when users need to understand how Hatchling implements PEP 517 interfaces. Help them configure build backends and understand the separation between build tools and installers.

**Python Description Formats** - Use when assisting with reproducible builds or explaining how metadata flows from source to distributed packages.

## Version History and Evolution

Major shifts in packaging standards:

- **Pre-2010s**: Setuptools-only ecosystem, inconsistent metadata
- **2013**: PEP 427 (Wheel) introduces binary distribution format
- **2015**: PEP 517/518 standardize build backend interfaces
- **2021**: PEP 621 standardizes project metadata in `pyproject.toml`
- **2023-2024**: PEP 639 modernizes license metadata; Core Metadata v2.5 adds import tracking
- **2025**: Emerging standards for lock file formats and dependency groups

## Related Standards Documents

- `pep-references.md`
- `core-metadata.md`
- `distribution-formats.md`
- `dependency-formats.md`
- `vcs-integration.md`
