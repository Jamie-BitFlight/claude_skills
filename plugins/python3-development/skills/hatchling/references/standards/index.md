---
category: standards
topics: [python-packaging, standards-reference, hatchling-standards, pep-reference-guide, metadata-standards]
related: [python-packaging-overview.md, pep-references.md, core-metadata.md, distribution-formats.md, dependency-formats.md, vcs-integration.md]
---

# Related Standards & Specifications for Hatchling

This directory contains comprehensive reference documentation on Python packaging standards that underpin hatchling's functionality and design. Use these documents to understand what standards Hatchling implements and to explain those standards to users when they ask about specific packaging behaviors.

## Quick Navigation

### `python-packaging-overview.md`

Starting point for understanding the landscape of Python packaging standards. Covers:

- Python Packaging Authority governance
- Six core specification categories
- Historical evolution of packaging standards
- Links to detailed specifications

### `pep-references.md`

Detailed reference to Python Enhancement Proposals (PEPs) directly applicable to hatchling:

- **PEP 517** - Build system interface (what hatchling implements)
- **PEP 518** - Build system requirements in pyproject.toml
- **PEP 621** - Project metadata specification
- **PEP 625** - Source distribution filename conventions
- **PEP 639** - Modern license metadata with SPDX
- **PEP 640** - Version flexibility
- **PEP 643** - Metadata for source distributions
- **PEP 660** - Editable installs
- **PEP 440** - Version identification schemes

### `core-metadata.md`

Complete reference for package metadata format used in wheels and sdists:

- Metadata version history and evolution
- All fields with detailed descriptions
- Field occurrence rules
- Hatchling integration points
- Best practices for consumption

### `distribution-formats.md`

Technical specifications for distributable packages:

- **Wheel format** (PEP 427) - ZIP-based binary distributions
  - Filename conventions
  - Archive structure
  - Required and optional files
  - Installation process
- **Source distribution** (sdist) - TAR-based source code
  - Filename conventions
  - Archive structure
  - Required and recommended files
  - Security considerations
- Distribution selection guidance
- Hatchling build process

### `dependency-formats.md`

How dependencies are declared and constrained:

- **PEP 508** dependency specification grammar
  - Package names and normalization
  - Extras (optional features)
  - Version specifiers (PEP 440)
  - Environment markers for conditional dependencies
  - Direct URL references
- Usage in pyproject.toml
- Build vs. runtime dependencies
- Best practices for dependency management
- Complex dependency examples

### `vcs-integration.md`

Integration between VCS and packaging:

- Git-based version management
- Hatchling VCS integration with hatch-vcs plugin
- File selection from VCS (git tracking)
- Reproducible builds from source
- Development version numbering
- Standard project layouts
- VCS integration best practices

## Documentation Structure

Each document follows a consistent structure:

1. **Overview** - Context and authority (PEPs, standards body)
2. **Key concepts** - Main ideas and terminology
3. **Detailed reference** - Comprehensive specification
4. **Hatchling integration** - How hatchling uses this standard
5. **Best practices** - Recommended approaches
6. **Related documents** - Cross-references to related standards

## Standards Authority Hierarchy

Standards are maintained in the following authority order:

1. **PyPA Specifications** (primary authority)

   - Active, maintained by Python Packaging Authority
   - Updated with fixes and clarifications
   - Found at: <https://packaging.python.org/specifications/>

2. **PEP Documents** (historical authority)

   - Reference documents, final versions
   - Superseded by PyPA Specifications where conflicting
   - Found at: <https://peps.python.org/>

3. **Tool Documentation** (informational)
   - How specific tools implement standards
   - Hatchling behavior and conventions

## Key Concepts Across Standards

### Package Naming

- Names normalized per PEP 503 (lowercase, replace `-_.` with `-`)
- Same normalization in wheels, sdists, and PyPI
- Case-insensitive matching

### Version Identification (PEP 440)

Universal versioning scheme for all Python packages:

- Format: `[N!]N(.N)*[{a|b|rc}N][.postN][.devN]`
- Examples: `1.0.0`, `1.0.0a1`, `1.0.0.dev5`
- All tools must parse and order versions identically

### Dependency Specifications (PEP 508)

Standard format for declaring package dependencies:

- Name with optional extras: `package[extra1,extra2]`
- Version constraints: `>=1.0,<2.0`
- Environment markers: `; python_version < "3.10"`
- Direct URLs: `@ https://github.com/...`

### Metadata Format (Core Metadata)

RFC 822 email header format for package information:

- Used in wheels, sdists, and registry
- Current version 2.5 (September 2025)
- Defines 30+ standardized fields
- Extensible for tool-specific metadata

### Build System Interface (PEP 517)

Standard hooks between build tools and installers:

- `build_wheel()` - Create wheel distribution
- `build_sdist()` - Create source distribution
- `prepare_metadata_for_build_wheel()` - Pre-build metadata
- `get_requires_for_build_wheel()` - Declare build dependencies

### Project Configuration (PEP 621)

Standard location for project metadata in `pyproject.toml`:

- `[project]` table for package metadata
- `[build-system]` table for build requirements
- `[tool.hatch]` namespace for tool-specific config
- Dynamic field declarations for computed values

## Evolution Timeline

| Year | Event                             | Impact                              |
| ---- | --------------------------------- | ----------------------------------- |
| 2012 | Wheel format (PEP 427)            | End of egg era, binary packages     |
| 2015 | Dependency spec (PEP 508)         | Unified dependency format           |
| 2017 | Build requirements (PEP 518)      | Escape setuptools monopoly          |
| 2018 | Build backend interface (PEP 517) | Hatchling and alternatives possible |
| 2021 | Project metadata (PEP 621)        | Setup.py optional                   |
| 2023 | Core Metadata v2.4                | SPDX license expressions            |
| 2024 | License metadata (PEP 639)        | Explicit license file tracking      |
| 2025 | Core Metadata v2.5                | Import name tracking                |

## Using These Standards with Hatchling

When assisting users, reference these standards to explain and validate their Hatchling configurations:

### When Users Declare Project Metadata

Reference `pep-references.md#project-metadata-specification-pep-621` and `core-metadata.md` to explain:

- How to structure `[project]` table in `pyproject.toml`
- Why version must follow PEP 440 format
- How to specify dependencies using PEP 508 syntax
- What metadata fields are optional vs. required

### When Users Configure Build System

Reference `pep-references.md#build-system-interface-pep-517` and `pep-references.md#build-system-requirements-pep-518` to explain:

- What the `[build-system]` table defines
- Why Hatchling must be listed in `requires`
- How build backends implement standard hooks
- What dependencies are needed only during build

### When Users Manage Versions

Reference `core-metadata.md` and `vcs-integration.md` to explain:

- How to format versions for PEP 440 compliance
- How `hatch-vcs` derives versions from Git tags
- What development versions look like between releases
- How to configure version sources

### When Users Build and Distribute

Reference `distribution-formats.md` and `distribution-formats.md` to explain:

- What Hatchling creates when running `build`
- The difference between wheels and sdists
- How metadata is included in distributions
- Why both formats are recommended for publishing

## Related Resources

### Official References

- [Python Packaging Authority](https://www.pypa.io/)
- [PyPA Specifications](https://packaging.python.org/specifications/)
- [Python Enhancement Proposals](https://peps.python.org/)

### Build System Documentation

- [Hatchling Documentation](https://hatch.pypa.io/latest/build/)
- [PEP 517 Implementation Guide](https://packaging.python.org/guides/building-and-packaging-projects-using-setuptools/)

### Tools and Implementations

- [Hatchling](https://github.com/pypa/hatch)
- [setuptools](https://github.com/pypa/setuptools)
- [Flit](https://github.com/pypa/flit)
- [PDM](https://github.com/pdm-project/pdm)
- [Poetry](https://github.com/python-poetry/poetry)

### Complementary Skills

For comprehensive hatchling documentation, see:

- `../SKILL.md` - Complete hatchling usage guide
- `../advanced-features/index.md` - Detailed build customization
- `../build-system/` - Build system setup

## Document Maintenance

These standards documents are maintained to reflect:

- Current PyPA specifications
- Latest PEP approvals (as of 2025)
- Hatchling's implementation details
- Real-world best practices

**Last Updated**: November 2025 **Specification Versions**:

- Core Metadata: 2.5 (September 2025)
- PEP 440: Current (Version Identification)
- PEP 508: Current (Dependency Specification)
- PEP 517: Final (Build Backend Interface)
- PEP 621: Final (Project Metadata)
