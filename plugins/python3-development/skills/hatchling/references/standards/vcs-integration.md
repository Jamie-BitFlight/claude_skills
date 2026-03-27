---
category: standards
topics: [vcs-integration, git-tags, version-management, file-selection, reproducible-builds, hatch-vcs, pep-440]
related: [pep-references.md, python-packaging-overview.md, distribution-formats.md, core-metadata.md]
---

# Version Control System Integration Standards

## Overview

Version Control Systems (VCS) integration with Python packaging allows projects to:

- Automatically determine versions from VCS tags
- Include only tracked files in distributions
- Build reproducible packages from source checkouts
- Manage development workflow metadata

Reference this documentation when helping users configure version management from Git, understand how Hatchling's `hatch-vcs` plugin works, or troubleshoot reproducible build issues.

## VCS-Based Version Management

### Git Tag Versioning

Many projects derive versions from Git tags following PEP 440 conventions.

**Pattern Examples:**

<eg>
v1.0.0          # Prefixed with 'v'
1.0.0           # Bare version
release-1.0.0   # Custom prefix
</eg>

### Hatchling VCS Integration

Hatchling provides the `hatch-vcs` plugin for dynamic versioning from Git:

**Configuration:**

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
```

**Tag Detection:**

- Automatically finds latest version tag
- Supports custom tag patterns
- Generates development versions for intermediate commits

### Version Source Interface

Hatchling defines a standard interface for version sources (PEP 517 extension):

**Custom Version Source:**

```python
class VersionSource:
    def get_version_data(self):
        """Return dict with 'version' key containing PEP 440 version."""
        return {"version": "1.0.0"}
```

## File Selection from VCS

### Git-Based File Inclusion

Build tools typically include only files tracked by Git to:

- Exclude build artifacts
- Exclude development dependencies
- Ensure reproducible distributions
- Minimize sdist size

**Hatchling Behavior:**

- Includes files tracked in Git
- Respects `.gitignore` patterns
- Includes `pyproject.toml` and other config files
- Excludes build directories and cache

### Force-Include Patterns

Additional files can be explicitly included:

```toml
[tool.hatch.build.targets.sdist]
include = [
    "/path/to/file.txt",
    "/docs/**/*.md",
]
```

### Exclude Patterns

Files can be excluded from distributions:

```toml
[tool.hatch.build.targets.sdist]
exclude = [
    "/.git",
    "/tests",
    "**/__pycache__",
]
```

## Reproducible Builds

### Source Distribution Reproducibility

For reproducible sdists, tools should:

- Use consistent file ordering (sort paths)
- Normalize file timestamps
- Use modern TAR formats (PAX)
- Document environment requirements

**Hatchling Approach:**

- Sorts files by name in archives
- Normalizes timestamps in TAR headers
- Uses PAX format for wide compatibility
- Creates reproducible checksums

### Wheel Reproducibility

Building the same wheel multiple times should produce identical output.

**Requirements:**

- Consistent file order in ZIP
- Normalized timestamps
- Deterministic Python compilation
- Consistent entry point ordering

### Reproducible Build Declaration

Projects can declare reproducibility support:

```toml
[tool.hatch.build]
reproducible = true
```

## PEP 440 and VCS Integration

### Development Versions

Commits between tags are versioned as development releases:

**Pattern:**

<eg>
1.0.0.dev5        # 5 commits after tag 1.0.0
1.0.0.dev5+g1a2b3c4  # With commit hash suffix
</eg>

**Rules (PEP 440):**

- Format: `X.Y.Z.devN`
- Development versions are pre-releases
- Ordered before final release
- Used for pre-release testing

### Local Version Identifiers

Local versions identify private builds:

**Pattern:**

<eg>
1.0.0+debian.1    # Debian rebuild
1.0.0+ubuntu.1    # Ubuntu rebuild
1.0.0+local.3     # Local build
</eg>

**Rules:**

- Use `+` separator before local version
- Alphanumeric, periods, dashes allowed
- Greater than upstream version in ordering
- NOT allowed on PyPI

## Standard Project Layouts

### Source Tree Structure

Standard structure for version-controlled projects:

<eg>
project-name/
├── .git/
├── .gitignore
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── project_name/
│       ├── __init__.py
│       └── module.py
├── tests/
│   ├── __init__.py
│   └── test_module.py
└── docs/
    └── index.rst
</eg>

### VCS Metadata in Distributions

**Not included in wheels:**

- `.git/` directory
- `.gitignore` file
- `.gitattributes` file
- Branch/commit information

**Included in sdists:**

- Source files (tracked)
- `pyproject.toml`
- Build configuration
- Tests (in some cases)
- Documentation (in some cases)

## Standards and PEPs

### PEP 517 - Build Backend Interface

Defines hooks for build tools to query:

- Build requirements
- Metadata
- Wheel/sdist location

Version sources integrate as extensions to the build backend.

### PEP 625 - Source Distribution Filename

Standardizes sdist naming:

<eg>
{name}-{version}.tar.gz
</eg>

Both name and version come from VCS tags or configuration.

### PEP 427 - Wheel Format

Wheels contain no VCS information:

- No `.git` directory
- No commit metadata
- No branch information
- Fixed version in filename

### PEP 440 - Version Identification

Governs how versions derived from VCS are formatted:

- Final releases: `1.0.0`
- Pre-releases: `1.0.0a1`, `1.0.0b2`
- Development: `1.0.0.dev5`
- Post-releases: `1.0.0.post1`
- Local: `1.0.0+local.1` (not on PyPI)

## Common VCS Integration Patterns

### Git Tags as Versions

```bash
# Create release tag
git tag v1.0.0

# Build automatically uses tag as version
hatchling build
# Produces: my-package-1.0.0-py3-none-any.whl
```

### Automatic Development Versions

```bash
# Between tags, version is determined dynamically
git log --oneline
# 1a2b3c4 (HEAD) Add feature
# 5d6e7f8 Add another feature
# abc1234 (tag: v1.0.0) Release 1.0.0

# Build creates:
# my-package-1.0.0.dev2+g1a2b3c4-py3-none-any.whl
```

### Version Control Integration Tools

**hatch-vcs:**

- Official Hatchling integration plugin
- Extracts version from Git tags
- Supports custom tag patterns
- Generates development versions

**setuptools_scm:**

- Independent VCS integration tool
- Works with multiple build systems
- Supported by setuptools and flit

**poetry:**

- Built-in VCS version management
- Uses Git-based versioning natively

## Best Practices

### Version Tags

**Do:**

- Use semantic versioning: `1.0.0`, `1.1.0`, `2.0.0`
- Prefix consistently: `v1.0.0` or `release-1.0.0`
- Tag releases on main branch
- Create annotated tags (with messages)

**Avoid:**

- Inconsistent tag formats
- Tagging development branches
- Tags without version information
- Bare commit hashes as versions

### File Inclusion

**Do:**

- Use `.gitignore` to exclude non-essentials
- Use explicit `include` for necessary files
- Keep build artifacts out of VCS
- Include all source files needed to build

**Avoid:**

- Tracking build output
- Committing virtual environment
- Large binary files
- Dependency lock files (sometimes)

### Reproducibility

**Do:**

- Build from clean checkout
- Use fixed dependency versions in lock files
- Document build environment requirements
- Test builds on clean systems

**Avoid:**

- Local-only modifications affecting builds
- Undocumented environment assumptions
- Random ordering in distributions

## Related Standards

- `distribution-formats.md`
- `core-metadata.md`
- `pep-references.md#build-system-interface-pep-517`
- `pep-references.md#source-distribution-format-pep-625`
