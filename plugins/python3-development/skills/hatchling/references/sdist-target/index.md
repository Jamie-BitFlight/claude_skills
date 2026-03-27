---
name: sdist-reference-overview
description: Navigation guide to comprehensive documentation for Hatchling's source distribution build target, including configuration options, file selection, metadata versions, and advanced features
---

# Source Distribution (Sdist) Build Target Reference

This directory provides comprehensive reference documentation for configuring Hatchling's source distribution (sdist) build target. Use these references to understand all configuration options, advanced use cases, and troubleshooting approaches when building Python source distributions.

## Files in This Reference

### `index.md` - Main Reference (642 lines)

Complete guide to the sdist build target configuration:

- Core concepts and architecture
- Configuration options (core-metadata-version, strict-naming, support-legacy)
- File selection and archive structure
- Default file inclusion rules
- Common configuration patterns
- Troubleshooting guide

**Start here** to understand sdist configuration fundamentals and common patterns.

### `core-metadata-versions.md` - Metadata Versions (315 lines)

Detailed documentation on core metadata versions:

- Version history (2.1 → 2.4)
- PEP 639 and SPDX license expressions
- License handling across versions
- Migration guides
- Field reference and format specifications

**Read this** when working with license metadata or upgrading metadata versions.

### `vcs-integration.md` - File Selection via VCS (482 lines)

Comprehensive guide to Hatchling's version control system integration:

- How .gitignore and .hgignore work with sdist
- Git-style glob pattern syntax
- Explicit include/exclude patterns
- VCS-based file selection defaults
- Combining VCS and explicit patterns
- Debugging file selection

**Consult this** when configuring which files to include/exclude.

### `legacy-setup-py.md` - Legacy Support (327 lines)

Complete reference for backward compatibility:

- When and why to use `support-legacy = true`
- How legacy setup.py works
- Migration from old setup.py to pyproject.toml
- Compatibility with old Python versions and tools
- Troubleshooting legacy installations

**Review this** if supporting Python 2.7 or very old pip versions.

### `unix-socket-handling.md` - Socket Files (362 lines)

Detailed handling of UNIX socket files:

- What UNIX sockets are and why they can't be archived
- How Hatchling gracefully skips sockets
- Best practices for preventing sockets in distributions
- Development setup recommendations
- Troubleshooting socket-related issues

**Check this** if encountering socket files in your source tree.

### `reproducible-builds.md` - Reproducible Builds (443 lines)

Complete guide to creating byte-for-byte identical distributions:

- What reproducible builds are and why they matter
- Using SOURCE_DATE_EPOCH environment variable
- Verification and testing reproducibility
- CI/CD integration examples
- Security and compliance benefits

**Learn about this** for security-sensitive projects or compliance requirements.

## Quick Navigation

### By Use Case

| When configuring...               | Consult...                                               |
| --------------------------------- | -------------------------------------------------------- |
| Basic sdist configuration         | `index.md`                                   |
| Core metadata version selection   | `core-metadata-versions.md` |
| File inclusion/exclusion patterns | `vcs-integration.md`               |
| Python 2.7 or legacy pip support  | `legacy-setup-py.md`               |
| UNIX socket file handling         | `unix-socket-handling.md`     |
| Reproducible build requirements   | `reproducible-builds.md`       |

### By Topic

| Topic                  | Primary                                                  | Related                                                  |
| ---------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| Configuration Options  | `index.md`                                   | `legacy-setup-py.md`               |
| File Selection         | `vcs-integration.md`               | `index.md`                                   |
| Metadata               | `core-metadata-versions.md` | `index.md`                                   |
| Backward Compatibility | `legacy-setup-py.md`               | `core-metadata-versions.md` |
| Special Files          | `unix-socket-handling.md`     | `vcs-integration.md`               |
| Build Integrity        | `reproducible-builds.md`       | `index.md`                                   |

## Key Topics Covered

### Configuration

- **core-metadata-version:** Choose between 2.1, 2.2, 2.3, 2.4 (default)
- **strict-naming:** Normalize package names (default true)
- **support-legacy:** Include setup.py for old tools (default false)

### File Selection

- VCS-based (uses .gitignore/.hgignore)
- Explicit include/exclude patterns
- Mandatory files always included
- UNIX socket graceful handling

### Advanced Features

- PEP 639 SPDX license expressions
- Reproducible builds with SOURCE_DATE_EPOCH
- Archive structure and naming
- Build hooks integration

### Troubleshooting

- Missing files in archive
- Large archive size
- Build failures from sdist
- Reproducibility issues
- Legacy tool compatibility

## Common Tasks

### Build a basic sdist

```toml
[tool.hatch.build.targets.sdist]
# Uses defaults - VCS-based file selection
```

### Control file inclusion

See `vcs-integration.md`:

```toml
[tool.hatch.build.targets.sdist]
include = ["/tests", "/docs"]
exclude = ["*.pyc", "__pycache__"]
```

### Update core metadata version

See `core-metadata-versions.md`:

```toml
[tool.hatch.build.targets.sdist]
core-metadata-version = "2.4"  # Latest with PEP 639
```

### Support legacy Python

See `legacy-setup-py.md`:

```toml
[tool.hatch.build.targets.sdist]
support-legacy = true
```

### Create reproducible builds

See `reproducible-builds.md`:

```bash
export SOURCE_DATE_EPOCH=$(date +%s)
hatch build -t sdist
```

## External References

- [Hatchling Documentation](https://hatch.pypa.io/)
- [PEP 517 - Build System Interface](https://www.python.org/dev/peps/pep-0517/)
- [PEP 639 - License Metadata](https://peps.python.org/pep-0639/)
- [Source Distribution Format Spec](https://packaging.python.org/specifications/source-distribution-format/)
- [Core Metadata Spec](https://packaging.python.org/specifications/core-metadata/)

## Document Statistics

| File                      | Lines    | Topics                                            |
| ------------------------- | -------- | ------------------------------------------------- |
| index.md                  | 642      | Core concepts, options, patterns, troubleshooting |
| core-metadata-versions.md | 315      | Version history, PEP 639, migration               |
| vcs-integration.md        | 482      | .gitignore, patterns, file selection              |
| legacy-setup-py.md        | 327      | Backward compatibility, migration                 |
| unix-socket-handling.md   | 362      | Socket files, prevention, best practices          |
| reproducible-builds.md    | 443      | Deterministic builds, verification, CI/CD         |
| **Total**                 | **2571** | **All aspects of sdist configuration**            |

---

**Last Updated:** 2025-11-02 **Target Audience:** Python package maintainers, Hatchling users, build system integrators
