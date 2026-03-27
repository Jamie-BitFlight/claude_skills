---
category: standards
topics: [wheel-format, sdist-format, pep-427, pep-625, distribution-naming, archive-structure, installation-process]
related: [pep-references.md, core-metadata.md, python-packaging-overview.md, vcs-integration.md]
---

# Package Distribution Formats

## Overview

Python packages are distributed in two primary formats:

1. **Wheels (Binary)** - Pre-built, ready-to-install distributions
2. **Source Distributions (Sdists)** - Source code with build information

Both formats are standardized by the Python Packaging Authority. Reference this documentation when helping users understand distribution formats, troubleshoot wheel or sdist generation issues, or explain what Hatchling creates during the build process.

## Wheel Format (PEP 427)

### Purpose

Wheels are ZIP archive files containing a pre-built package ready for installation. They eliminate the need to run build scripts on the target system.

**Status**: Final (February 2013) **Authority**: BDFL-Delegate Alyssa Coghlan **Repository**: [python/peps - PEP 427](https://github.com/python/peps/blob/main/peps/pep-0427.rst) **Canonical Spec**: [packaging.python.org - Binary Distribution Format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)

### Filename Convention

<eg>
{distribution}-{version}(-{build tag})?-{python}-{abi}-{platform}.whl
</eg>

**Components:**

- `distribution` - Package name (normalized)
- `version` - Version (canonicalized per PEP 440)
- `build tag` (optional) - Build number for distinguishing multiple builds of the same version
- `python` - Python implementation and version (e.g., `py3`, `cp38`, `py27.py33`)
- `abi` - ABI tag indicating binary compatibility (e.g., `none`, `cp38`, `abi3`)
- `platform` - Platform tag (e.g., `any`, `linux_x86_64`, `win_amd64`)

### Examples

<eg>
requests-2.28.1-py3-none-any.whl          # Pure Python, any platform
numpy-1.24.0-cp311-cp311-win_amd64.whl    # CPython 3.11, Windows 64-bit
cryptography-40.0.0-cp37-abi3-manylinux2014_x86_64.whl
</eg>

### Wheel Archive Structure

<eg>
example_package-1.0.0-py3-none-any.whl (ZIP archive)
├── example_package/
│   ├── __init__.py
│   ├── module1.py
│   └── module2.py
├── example_package-1.0.0.dist-info/
│   ├── WHEEL
│   ├── METADATA
│   ├── RECORD
│   ├── entry_points.txt (optional)
│   ├── top_level.txt (optional)
│   └── licenses/
│       ├── LICENSE
│       └── COPYING
└── example_package-1.0.0.data/
    ├── scripts/
    ├── data/
    └── headers/
</eg>

### Required Wheel Files

#### .dist-info Directory

**METADATA**

- Core metadata file (Core Metadata specification format)
- Contains package name, version, author, dependencies, etc.
- Format: RFC 822 email headers

**WHEEL**

- Wheel-specific metadata
- Declares wheel version and compatibility information
- Example:
  <eg>
  Wheel-Version: 1.0
  Generator: hatchling
  Root-Is-Purelib: true
  Tag: py3-none-any
</eg>

**RECORD**

- List of all files in the wheel with their SHA256 hashes
- Format: CSV with columns: path, hash algorithm, hash value
- RECORD file itself has empty hash
- Example:
  <eg>
  example_package/__init__.py,sha256=xxx,150
  example_package-1.0.0.dist-info/METADATA,sha256=yyy,3000
  example_package-1.0.0.dist-info/WHEEL,sha256=zzz,100
  example_package-1.0.0.dist-info/RECORD,,
</eg>

#### Optional Wheel Files

**entry_points.txt**

- INI format file defining entry points for scripts and plugins
- Format: ConfigParser sections
- Example:

  ```ini
  [console_scripts]
  my-script = example_package.cli:main

  [gui_scripts]
  my-gui = example_package.gui:run
  ```

**top_level.txt**

- One line per top-level module/package provided by the wheel
- Used for uninstall discovery
- Example:
  <eg>
  example_package
</eg>

### .data Directory

The `.data` directory contains files that don't belong in `site-packages`:

<eg>
example_package-1.0.0.data/
├── purelib/              # Pure Python libraries (sitelib)
├── platlib/              # Platform-specific libraries
├── scripts/              # Executable scripts
├── data/                 # Arbitrary data files
└── headers/              # C header files
</eg>

### Installation Process

1. **Unpack** - Extract the wheel ZIP archive
2. **Place files** - Install files from wheel root to site-packages
3. **Spread .data** - Place .data subdirectories to target locations
4. **Update RECORD** - Install RECORD file with installed paths
5. **Compile** - Optionally compile .py files to .pyc

## Source Distribution Format (Sdist)

### Purpose

Source distributions contain the source code and build information needed to build the package on target systems. They support projects that require build steps.

**Status**: Final **Repository**: [packaging.python.org - Source Distribution Format](https://packaging.python.org/en/latest/specifications/source-distribution-format/)

### Filename Convention

<eg>
{name}-{version}.tar.gz
</eg>

**Components:**

- `name` - Package name (normalized per PEP 503)
- `version` - Version (canonicalized per PEP 440)
- Archive format: `.tar.gz` (gzip-compressed TAR)

### Examples

<eg>
requests-2.28.1.tar.gz
numpy-1.24.0.tar.gz
cryptography-40.0.0.tar.gz
</eg>

### Sdist Archive Structure

<eg>
example_package-1.0.0.tar.gz (TAR archive, gzip compressed)
└── example_package-1.0.0/
    ├── pyproject.toml
    ├── PKG-INFO
    ├── README.md
    ├── LICENSE
    ├── example_package/
    │   ├── __init__.py
    │   ├── module1.py
    │   └── module2.py
    ├── tests/
    │   └── test_module1.py
    ├── docs/
    │   └── index.rst
    └── build_scripts/ (optional)
        └── custom_builder.py
</eg>

### Required Sdist Files

**pyproject.toml**

- Build system configuration (PEP 517, PEP 518, PEP 621)
- Specifies build backend and dependencies
- Contains project metadata

**PKG-INFO**

- Core metadata file (Core Metadata v2.2 or later)
- Must include metadata version
- May include `Dynamic` field entries for computed metadata
- Format: RFC 822 email headers

### Recommended Sdist Files

**README**

- Project description document
- Supported formats: `.md`, `.rst`, `.txt`
- Referenced in `pyproject.toml` as `readme`

**LICENSE**

- License file(s)
- Referenced in `PKG-INFO` via `License-File` fields
- Multiple license files supported (PEP 639)

### Sdist Archive Features

**TAR Format:**

- Must use modern POSIX.1-2001 pax format
- UTF-8 encoded filenames
- Readable by Python's standard `tarfile` module with mode `'r:gz'`

**Security Considerations (PEP 721):**

- When extracting, must use `tarfile.data_filter()` or follow unpacking rules
- Rejects files outside destination directory
- Rejects device files and suspicious links
- Normalizes file permissions

### Source Tree vs. Source Distribution

**Source Tree** (in version control):

- Active development state
- Contains build configuration
- May omit some distribution content
- Not meant for end users

**Source Distribution** (packaged sdist):

- Archived snapshot at release time
- Contains all files needed to build
- Includes PKG-INFO with fixed metadata
- Ready for archival and redistribution

## Distribution Selection

| Format | Use Case            | Advantages                                          | Disadvantages                              |
| ------ | ------------------- | --------------------------------------------------- | ------------------------------------------ |
| Wheel  | Most packages       | Fast install, no compilation needed, consistent     | Requires building for each platform/Python |
| Sdist  | Source availability | Single file for all platforms, enables local builds | Requires build tools installed, slower     |

## Best Practices

### Wheel Creation

1. Include all necessary build artifacts
2. Use correct compatibility tags (see PEP 425 for tag rules)
3. Include license files in `.dist-info/licenses/`
4. Make wheels reproducible (consistent file order, timestamps)
5. Test wheel installation on target platforms

### Sdist Creation

1. Include `pyproject.toml` and `PKG-INFO`
2. Use gzip compression with `.tar.gz` extension
3. Use modern PAX TAR format
4. Include source files but exclude build artifacts
5. Ensure source tree can rebuild the exact same wheels

### Publishing

1. Build both wheel and sdist for each release
2. Validate compatibility tags match intended platforms
3. Sign distributions (optional but recommended)
4. Upload to PyPI with consistent versioning
5. Maintain source trees in version control

## Hatchling Integration

Hatchling implements:

**Wheel Building:**

- PEP 427 compliant wheel format
- Automatic compatibility tag detection
- Metadata generation (Core Metadata v2.4+)
- Entry point generation
- Pure Python and platform-specific wheels

**Sdist Building:**

- PEP 625 compliant naming
- Modern PAX TAR format with gzip
- PKG-INFO generation (Core Metadata v2.2+)
- VCS-aware file inclusion
- Dynamic metadata support

## Compatibility Tags

See [PEP 425 - Compatibility Tags](https://peps.python.org/pep-0425/) for detailed tag definitions.

Common tags:

- `py3` - Any Python 3
- `py3.8` - Specific Python version
- `cp38` - CPython 3.8
- `none` - No ABI requirements
- `abi3` - Stable ABI (forward compatible)
- `any` - Any platform
- `linux_x86_64` - Specific platform

## Related Standards

- `core-metadata.md`
- `pep-references.md#wheel-format-pep-427`
- `pep-references.md#source-distribution-format-pep-625`
- `pep-references.md#metadata-for-source-distributions-pep-643`
