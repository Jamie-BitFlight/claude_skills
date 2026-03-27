---
category: release-notes
topics: [hatchling, navigation, index, features, pep-639, metadata-hooks, build-hooks, performance, version-management]
related: [RELEASE_NOTES.md, PEP_639_LICENSE_METADATA.md, METADATA_HOOKS_AND_VERSION_SOURCES.md, BUILD_HOOKS_AND_PERFORMANCE.md, README.md]
---

# Hatchling Release Notes & Version History Index

Navigation and reference index for Hatchling's comprehensive release notes documentation. Use this collection to locate information about version history and feature evolution of the Hatchling Python build backend from v1.0.0 through the current release. Reference this index when helping users find version-specific information, feature availability, or migration guidance.

## Documentation Structure

### Core Documentation

#### `RELEASE_NOTES.md`

**Complete version history with all releases**

The main release notes document covering:

- All releases from v1.0.0 (2022-03-28) through v1.27.0 (2024-11-26)
- Organized by era and release timeline
- Feature highlights by topic
- Deprecations and breaking changes
- Related standards and documentation links

**Key Sections:**

- Release Timeline (all releases with links)
- Version History by Era (5 major development eras)
- Feature Highlights by Topic (PEP 639, metadata hooks, etc.)
- Deprecations & Breaking Changes
- Complete version timeline summary

**Use this for:** Quick lookup of specific versions, understanding development timeline, reviewing feature history

---

### Feature-Specific Guides

#### `PEP_639_LICENSE_METADATA.md`

**PEP 639 license metadata support implementation guide**

Comprehensive coverage of license metadata evolution:

- Implementation timeline (v1.5.0 through v1.27.0)
- Core metadata version evolution
- Configuration examples and best practices
- SPDX license expression syntax
- Migration guide for existing projects
- Known issues and workarounds

**Key Topics:**

- Initial support (v1.5.0)
- License-File support (v1.9.0)
- License-Expression support (v1.12.0)
- Full PEP 639 implementation (v1.26.0)
- Core metadata version compatibility
- Backward compatibility features

**Use this for:** Implementing license metadata, understanding PEP 639, migrating from old formats

---

#### `METADATA_HOOKS_AND_VERSION_SOURCES.md`

**Metadata hooks and dynamic version source implementation**

Detailed guide to dynamic metadata and version management:

- Metadata hooks evolution (v1.3.0 through v1.22.0)
- Version source implementations (regex, code, env)
- Version source timeline and examples
- Hook interface evolution
- Dynamic metadata field support
- Build hook dependencies (v1.22.0+)
- Configuration examples for all version sources

**Key Topics:**

- Introduction of metadata hooks (v1.3.0)
- Version hook launch (v1.4.0)
- Classifier methods (v1.8.0)
- Hook dependencies (v1.22.0)
- Regex version source (v1.2.0+)
- Code version source with extensions (v1.6.0+)
- Environment variable source (v1.11.0+)

**Use this for:** Dynamic version management, metadata customization, implementing build hooks

---

#### `BUILD_HOOKS_AND_PERFORMANCE.md`

**Build hooks and performance optimization features**

Comprehensive performance and extensibility guide:

- Build hook evolution (v1.4.0 through v1.22.0)
- Directory traversal optimizations across versions
- File selection improvements
- Wheel optimization features
- Metadata optimization strategies
- Build data features (shared artifacts)
- Performance metrics and best practices

**Key Topics:**

- Build hook foundation (v1.4.0)
- Directory traversal optimization (v1.4.0+)
- Pattern matching improvements (v1.9.0)
- Selection validation (v1.19.0)
- macOS compatibility (v1.12.2)
- PKG-INFO reuse (v1.22.0)
- Shared artifacts (v1.24.0)
- Pixi support (v1.26.0)

**Use this for:** Optimizing build performance, implementing custom hooks, understanding build process

---

## Quick Navigation by Topic

### By Version Range

**Very Latest (v1.26-1.27)**

- `RELEASE_NOTES.md#era-1-recent-releases-v1241-27`
- `PEP_639_LICENSE_METADATA.md#v1260-2024-11-10---full-pep-639-implementation`
- `BUILD_HOOKS_AND_PERFORMANCE.md#latest-updates-v1260`

**Python 3.12 Era (v1.15-1.23)**

- `RELEASE_NOTES.md#era-3-python-312-support--build-system-improvements-v1519`
- `BUILD_HOOKS_AND_PERFORMANCE.md#build-hook-categories`

**Core Features Era (v1.4-1.14)**

- `RELEASE_NOTES.md#era-4-core-features--major-enhancements-v1414`
- `METADATA_HOOKS_AND_VERSION_SOURCES.md`
- `BUILD_HOOKS_AND_PERFORMANCE.md#build-hooks-evolution`

**Initial Release (v1.0-1.3)**

- `RELEASE_NOTES.md#era-5-initial-release--foundation-v101-3`

### By Feature

**License & Metadata**

- `PEP_639_LICENSE_METADATA.md` - License metadata evolution
- `METADATA_HOOKS_AND_VERSION_SOURCES.md#metadata-hooks-history`
- `BUILD_HOOKS_AND_PERFORMANCE.md#metadata-optimization`

**Version Management**

- `METADATA_HOOKS_AND_VERSION_SOURCES.md#version-sources-implementation`
- `RELEASE_NOTES.md#feature-highlights-by-topic`

**Build System**

- `BUILD_HOOKS_AND_PERFORMANCE.md#build-hooks-evolution`
- `BUILD_HOOKS_AND_PERFORMANCE.md#performance-optimizations`
- `RELEASE_NOTES.md#era-3-python-312-support--build-system-improvements-v1519`

**Performance**

- `BUILD_HOOKS_AND_PERFORMANCE.md#performance-optimizations`
- `BUILD_HOOKS_AND_PERFORMANCE.md#build-performance-metrics`

**Python Support**

- `RELEASE_NOTES.md#era-3-python-312-support--build-system-improvements-v1519`
- `BUILD_HOOKS_AND_PERFORMANCE.md#v1180-2023-06-12---python-37-end-of-support`

### By Standards Compliance

**PEP Implementations**

- **PEP 517** - Build system interface (v1.0.0)
- **PEP 560** - Type hints support (v1.4.0)
- **PEP 639** - License metadata
  - `PEP_639_LICENSE_METADATA.md`
  - Initial: v1.5.0
  - Current: v1.26.0+
- **PEP 660** - Editable installs (v1.0.0)
- **PEP 427** - Wheel format (v1.0.0)

---

## Finding Information

### When Helping Users Find Information

**Users needing specific version's changes**

- Reference `RELEASE_NOTES.md`
- Help them search for version number (e.g., "1.22.0")
- All releases linked to GitHub with detailed notes

**Users configuring license metadata**

- Guide them to `PEP_639_LICENSE_METADATA.md`
- Provide configuration examples from the document
- Share documented migration paths

**Users exploring dynamic versioning options**

- Direct them to `METADATA_HOOKS_AND_VERSION_SOURCES.md`
- Help compare regex, code, and environment variable sources
- Show examples for each approach

**Users implementing build hooks**

- Reference `BUILD_HOOKS_AND_PERFORMANCE.md`
- Also point to `METADATA_HOOKS_AND_VERSION_SOURCES.md`
- Provide examples and best practices

**Users optimizing build performance**

- Guide to `BUILD_HOOKS_AND_PERFORMANCE.md#performance-optimizations`
- Explain optimization timeline and strategies
- Share applicable best practices

**Users understanding backward compatibility**

- Reference `PEP_639_LICENSE_METADATA.md#backward-compatibility`
- Also check `RELEASE_NOTES.md#deprecations--breaking-changes`

---

## Key Milestones

### Major Releases

| Version    | Date       | Milestone                                  |
| ---------- | ---------- | ------------------------------------------ |
| **1.0.0**  | 2022-03-28 | Initial public release                     |
| **1.4.0**  | 2022-07-03 | Build hooks & PEP 561 support              |
| **1.5.0**  | 2022-07-11 | PEP 639 support (draft)                    |
| **1.9.0**  | 2022-09-09 | Metadata inspection, License-File support  |
| **1.11.0** | 2022-10-08 | Environment variable version source        |
| **1.12.0** | 2022-12-30 | Enhanced type hints, SPDX updates          |
| **1.15.0** | 2023-05-09 | App/binary build target                    |
| **1.19.0** | 2023-12-11 | Python 3.12 support                        |
| **1.22.0** | 2024-03-16 | Metadata hooks enhanced, core metadata 2.2 |
| **1.26.0** | 2024-11-10 | Full PEP 639 implementation                |
| **1.27.0** | 2024-11-26 | Core metadata 2.4 default                  |

### Feature Introduction Timeline

- **v1.0.0** - Basic build backend (wheels, sdists)
- **v1.2.0** - Regex version source
- **v1.3.0** - Metadata hooks
- **v1.4.0** - Build hooks & type hints
- **v1.5.0** - PEP 639 support
- **v1.6.0** - Code version source
- **v1.9.0** - Metadata inspection
- **v1.11.0** - Environment version source
- **v1.15.0** - Binary build target
- **v1.19.0** - Python 3.12 support
- **v1.22.0** - Enhanced metadata hooks
- **v1.26.0** - Full PEP 639

---

## Version Support & Compatibility

### Python Version Support

- **v1.0-1.17**: Python 3.7+
- **v1.18+**: Python 3.8+ (dropped 3.7)
- **v1.27+ (upcoming)**: Python 3.8+ (planning to drop 3.8)

### Core Metadata Support

| Version   | v2.1 | v2.2 | v2.3 | v2.4          |
| --------- | ---- | ---- | ---- | ------------- |
| v1.8-1.21 | Yes  | -    | -    | -             |
| v1.22.0   | Yes  | Yes  | -    | -             |
| v1.22.1+  | Yes  | Yes  | Yes  | -             |
| v1.26.0+  | Yes  | Yes  | Yes  | Yes           |
| v1.27.0+  | Yes  | Yes  | Yes  | Yes (default) |

---

## Coverage Summary

### Releases Covered

- v1.0.0 through v1.27.0
- 27 major versions + patch releases
- 2+ years of development history
- All significant features and improvements

### Topics Covered

**Core Features**

- Build targets (wheel, sdist, app/binary)
- Dynamic metadata support
- Version management
- File selection and inclusion
- Build hooks and extensibility

**Standards Compliance**

- PEP 517 (Build System Interface)
- PEP 560 (Type Hints)
- PEP 639 (License Metadata)
- PEP 660 (Editable Installs)
- PEP 427 (Wheel Format)

**Quality & Performance**

- Performance optimizations
- Directory exclusions
- Metadata reuse and caching
- Build time improvements
- File handling robustness

**Developer Experience**

- Error messages
- Configuration options
- CLI tools
- Metadata inspection
- Hook interfaces

---

## External Resources

### Official Documentation

- [Hatchling Homepage](https://hatch.pypa.io/)
- [GitHub Repository](https://github.com/pypa/hatch)
- [GitHub Releases](https://github.com/pypa/hatch/releases)

### Python Enhancement Proposals (PEPs)

- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)
- [PEP 560 - Core Support for typing](https://peps.python.org/pep-0560/)
- [PEP 639 - License Metadata](https://peps.python.org/pep-0639/)
- [PEP 660 - Editable Install](https://peps.python.org/pep-0660/)

### Standards & Specifications

- [SPDX License List](https://spdx.org/licenses/)
- [Wheel Format (PEP 427)](https://peps.python.org/pep-0427/)
- [pyproject.toml (PEP 518)](https://peps.python.org/pep-0518/)

---

## Search Tips

### Using Ctrl+F in Your Browser/Editor

- **Find version info**: Search for version number (e.g., "1.22.0")
- **Find feature**: Search for feature name (e.g., "PEP 639", "metadata hooks")
- **Find date**: Search for year (e.g., "2024", "2022")
- **Find Python version**: Search "Python 3.X" or "support"
- **Find build target**: Search "wheel", "sdist", "app", "binary"

### Navigating Between Documents

Each document contains:

- Internal cross-references via markdown links
- "Related Documentation" sections at the end
- Cross-references in this index file

---

## About This Documentation

**Created:** November 2024 **Coverage:** Hatchling v1.0.0 through v1.27.0 **Source:** Official Hatchling releases and GitHub changelog **Format:** Keep a Changelog style with Semantic Versioning

This documentation is organized for quick navigation by version, feature, and use case. Each document focuses on a specific aspect while cross-referencing related topics.

### Document Details

- **RELEASE_NOTES.md** - 800+ lines, complete chronological history
- **PEP_639_LICENSE_METADATA.md** - 300+ lines, license implementation guide
- **METADATA_HOOKS_AND_VERSION_SOURCES.md** - 400+ lines, hooks and versioning
- **BUILD_HOOKS_AND_PERFORMANCE.md** - 400+ lines, build system guide
- **index.md** (this file) - Navigation and overview

### Document Statistics

| Document                              | Lines | Topics     | Versions        |
| ------------------------------------- | ----- | ---------- | --------------- |
| RELEASE_NOTES.md                      | 850+  | 15+        | All (v1.0-1.27) |
| PEP_639_LICENSE_METADATA.md           | 300+  | 8+         | v1.5-1.27       |
| METADATA_HOOKS_AND_VERSION_SOURCES.md | 400+  | 10+        | v1.2-1.22       |
| BUILD_HOOKS_AND_PERFORMANCE.md        | 400+  | 12+        | v1.4-1.26       |
| index.md                              | 450+  | Navigation | All             |
| README.md                             | 150+  | Overview   | All             |

**Total:** 2,500+ lines of release documentation

---

## Contributing Updates

This documentation reflects Hatchling's official release history as documented in:

1. GitHub release notes (<https://github.com/pypa/hatch/releases>)
2. Official changelog (<https://hatch.pypa.io/dev/history/hatchling/>)
3. Project documentation (<https://hatch.pypa.io/>)

## Document Format

All documents follow:

- **Markdown format** for easy reading and navigation
- **Keep a Changelog** style for release notes
- **Semantic Versioning** version references
- **Cross-references** between related topics
- **Configuration examples** for practical use
- **Best practices** sections for guidance

## Questions or Feedback?

- Check this index for navigation help
- Search relevant document for your topic
- Refer to official Hatchling documentation
- Check GitHub issues for known problems

---

**Last Updated:** November 2024 **Coverage:** Hatchling v1.0.0 through v1.27.0 **Format:** Markdown (GitHub-compatible)
