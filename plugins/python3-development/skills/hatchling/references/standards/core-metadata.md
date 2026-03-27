---
category: standards
topics: [core-metadata, metadata-version, package-metadata, metadata-fields, license-metadata, import-discovery]
related: [pep-references.md, python-packaging-overview.md, distribution-formats.md, dependency-formats.md]
---

# Core Metadata Specifications

## Overview

The **Core Metadata Specification** defines the standard format for package metadata used in wheels, source distributions, and published package information. The specification uses an email header format (RFC 822 style) for broad compatibility. Use this reference when helping users understand how Hatchling generates, validates, or troubleshoots package metadata.

**Current Version**: 2.5 (approved September 2025) **Authority**: Python Packaging Authority **Location**: [packaging.python.org - Core Metadata](https://packaging.python.org/en/latest/specifications/core-metadata/)

## File Locations

Metadata is stored in:

- **Wheels**: `{name}-{version}.dist-info/METADATA`
- **Source distributions**: `{name}-{version}/PKG-INFO`
- **Published packages**: Retrieved from package index (PyPI, etc.)

## Metadata Format

The format follows RFC 822 email header conventions parsed by Python's standard `email.parser` module:

<eg>
Metadata-Version: 2.5
Name: example-package
Version: 1.0.0
Summary: A brief description
Author: John Doe
Author-Email: john@example.com
License-Expression: MIT
Requires-Python: >=3.8
Requires-Dist: requests>=2.20.0
Requires-Dist: colorama; sys_platform=="win32"
Provides-Extra: dev
Requires-Dist: pytest>=7.0; extra=="dev"
</eg>

## Required Fields

Only three fields are mandatory in any metadata version:

1. **Metadata-Version** - Version of the metadata specification (e.g., `2.5`)
2. **Name** - Package/distribution name
3. **Version** - Package version (PEP 440 compliant)

All other fields are optional.

## Field Reference

### Identity Fields

#### Name

- Distribution name, normalized per PEP 503
- Exactly one occurrence

#### Version

- PEP 440 compliant version identifier
- Exactly one occurrence
- Examples: `1.0.0`, `1.0.0a1`, `2024.1.0`

#### Metadata-Version

- Version of the core metadata specification
- Exactly one occurrence
- Current: `2.5`

### Description Fields

#### Summary

- Single-line project summary
- At most one occurrence
- Typically under 100 characters

#### Description

- Full project description
- At most one occurrence
- May contain:
  - Plain text (default)
  - reStructuredText (rst)
  - Markdown (markdown)
- Specified via `Description-Content-Type` field

#### Description-Content-Type

- MIME type for description content
- Format: `text/x-rst` or `text/markdown`
- Default: plain text
- Example: `Description-Content-Type: text/markdown; charset=UTF-8`

### Contact Fields

#### Author

- Project author name
- Multiple occurrences permitted
- Often combined with `Author-Email`

#### Author-Email

- Author contact email
- Multiple occurrences permitted
- Format: `Name <email@example.com>` or just `email@example.com`
- Deprecated field; prefer `Author` with email

#### Maintainer

- Current project maintainer
- Multiple occurrences permitted
- Format same as `Author`

#### Maintainer-Email

- Maintainer contact email
- Multiple occurrences permitted
- Format: `Name <email@example.com>`
- Deprecated; prefer `Maintainer` with email

#### Home-Page

- Project homepage URL
- At most one occurrence
- Deprecated; use `Project-URL` instead
- Kept for backwards compatibility

#### Download-URL

- URL for downloading the project
- At most one occurrence
- Deprecated; use `Project-URL` instead

### License Fields

#### License

- License identifier or file reference
- At most one occurrence
- **Deprecated in v2.4+** - Use `License-Expression` instead
- Kept for backwards compatibility

#### License-Expression (v2.4+)

- SPDX license expression
- At most one occurrence
- Examples:
  - `MIT`
  - `Apache-2.0 OR MIT`
  - `GPL-2.0-only WITH Classpath-exception-2.0`

#### License-File (v2.4+)

- Path to license file
- Multiple occurrences permitted
- Paths relative to package root in sdist
- Example: `License-File: LICENSE`, `License-File: COPYING.txt`

### Project URL Fields

#### Project-URL

- Arbitrary project-related URL
- Multiple occurrences permitted
- Format: `Label, URL`
- Examples:
  - `Project-URL: Homepage, https://example.com`
  - `Project-URL: Repository, https://github.com/user/repo`
  - `Project-URL: Documentation, https://docs.example.com`
  - `Project-URL: Bug Tracker, https://github.com/user/repo/issues`

### Dependency Fields

#### Requires-Python

- Python version specifier (PEP 440)
- At most one occurrence
- Interpreted per PEP 508 version specification rules
- Examples:
  - `Requires-Python: >=3.8`
  - `Requires-Python: >=3.8,<4.0`
  - `Requires-Python: !=3.9.*`

#### Requires-Dist

- Runtime dependency specification (PEP 508 format)
- Multiple occurrences permitted
- Includes version specifiers and environment markers
- Examples:
  - `Requires-Dist: requests>=2.20.0`
  - `Requires-Dist: colorama; sys_platform=="win32"`
  - `Requires-Dist: numpy>=1.20; python_version>="3.10"`

#### Provides-Extra

- Name of an optional dependency group (extra)
- Multiple occurrences permitted
- Used with conditional `Requires-Dist` entries
- Example: `Provides-Extra: dev` with `Requires-Dist: pytest; extra=="dev"`

#### Provides-Dist

- Distribution name provided by this package
- Multiple occurrences permitted
- Rarely used; indicates renamed distributions
- Example: `Provides-Dist: backport-datetime`

#### Obsoletes-Dist

- Distribution name made obsolete by this package
- Multiple occurrences permitted
- Rarely used; indicates replacement packages

### Classifier Fields

#### Classifier

- PyPI trove classifier for categorization
- Multiple occurrences permitted
- Structured taxonomy (Development Status, License, Programming Language, etc.)
- Examples:
  - `Classifier: Development Status :: 4 - Beta`
  - `Classifier: License :: OSI Approved :: MIT License`
  - `Classifier: Programming Language :: Python :: 3.8`
  - `Classifier: Environment :: Console`

### Keywords

#### Keywords

- List of search keywords
- At most one occurrence
- Format: comma-separated or space-separated terms
- Example: `Keywords: database, query, async`

### Module and Import Information (v2.5+)

#### Import-Name

- Import name(s) provided by this package
- Multiple occurrences permitted
- Used for import discovery
- Example: `Import-Name: requests`

#### Import-Namespace

- Shared namespace packages
- Multiple occurrences permitted
- Used when multiple packages share a namespace
- Example: `Import-Namespace: zope`

### Metadata Versioning Fields (v2.2+)

#### Dynamic

- Field names that are computed at build time
- Multiple occurrences permitted
- Only valid in source distributions
- Examples:
  - `Dynamic: version`
  - `Dynamic: requires-dist`
  - `Dynamic: description`
- **Restriction**: `Name` and `Version` MUST NOT be marked as Dynamic

## Field Occurrence Rules

| Field                    | Min | Max | Versions              |
| ------------------------ | --- | --- | --------------------- |
| Metadata-Version         | 1   | 1   | All                   |
| Name                     | 1   | 1   | All                   |
| Version                  | 1   | 1   | All                   |
| Summary                  | 0   | 1   | All                   |
| Description              | 0   | 1   | All                   |
| Description-Content-Type | 0   | 1   | 2.1+                  |
| Author                   | 0   | inf | 2.1+                  |
| Author-Email             | 0   | inf | 2.1+                  |
| Maintainer               | 0   | inf | 2.1+                  |
| Maintainer-Email         | 0   | inf | 2.1+                  |
| Home-page                | 0   | 1   | 2.0+ (deprecated 2.1) |
| Download-URL             | 0   | 1   | 2.0+ (deprecated 2.1) |
| License                  | 0   | 1   | All (deprecated 2.4)  |
| License-Expression       | 0   | 1   | 2.4+                  |
| License-File             | 0   | inf | 2.4+                  |
| Project-URL              | 0   | inf | 2.1+                  |
| Requires-Python          | 0   | 1   | 2.1+                  |
| Requires-Dist            | 0   | inf | 2.1+                  |
| Provides-Extra           | 0   | inf | 2.1+                  |
| Provides-Dist            | 0   | inf | 2.1+                  |
| Obsoletes-Dist           | 0   | inf | 2.1+                  |
| Classifier               | 0   | inf | All                   |
| Keywords                 | 0   | 1   | All                   |
| Import-Name              | 0   | inf | 2.5+                  |
| Import-Namespace         | 0   | inf | 2.5+                  |
| Dynamic                  | 0   | inf | 2.2+                  |

## Version History

### Version 2.5 (September 2025)

**New Fields:**

- `Import-Name` - Documents import names provided by package
- `Import-Namespace` - Identifies shared namespace packages

**Rationale**: Enables better import discovery and namespace package management.

### Version 2.4 (December 2024)

**Changes (PEP 639):**

- Deprecated `License` field
- Added `License-Expression` field (SPDX format)
- Added `License-File` field (repeatable)

### Version 2.3 (August 2023)

**Changes (PEP 722):**

- Added repeatable `Author`, `Maintainer` fields
- Deprecated single-use `Author-Email`, `Maintainer-Email`

### Version 2.2 (November 2020)

**Changes (PEP 643):**

- Added `Dynamic` field for metadata computed at build time
- Updated source distribution metadata requirements

### Version 2.1 (September 2016)

**Changes:**

- Added `Description-Content-Type`
- Added `Project-URL` (replaces Home-page, Download-URL)
- Added `Author`, `Maintainer` (repeatable)
- Added `Requires-Dist`, `Provides-Extra`

### Version 2.0 (June 2012)

**Changes:**

- Standardized field format
- Added `Classifier` field
- Added `Download-URL`

## Hatchling Integration

Hatchling generates core metadata files conforming to:

- Core Metadata v2.4+ (default) or specified version
- PEP 440 version compliance
- PEP 508 dependency specification
- SPDX license expressions (PEP 639)

The metadata is computed during wheel and sdist creation and stored in:

- `PKG-INFO` for sdists
- `{name}.dist-info/METADATA` for wheels

## Consumption Best Practices

Tools consuming metadata should:

- Parse metadata using `email.parser` module
- Validate `Metadata-Version` and warn if it exceeds tool support
- Handle repeatable fields as lists
- Normalize names per PEP 503
- Canonicalize versions per PEP 440

## Related Standards

- `pep-references.md#version-identification-pep-440`
- `dependency-formats.md`
- `pep-references.md#license-metadata-pep-639`
- `distribution-formats.md`
