---
category: project-metadata
topics: [project-name, version-specification, description, readme, python-requirements]
related: [version-specifiers, dynamic-metadata, ownership, keywords-classifiers]
---

# Basic Metadata Fields

Basic metadata fields provide the essential information about a Python project. These fields are fundamental to project discovery, installation, and presentation on package indexes like PyPI.

When Claude helps users configure their Hatchling project, start with these essential fields: project name, version, description, README, and Python version requirements. These form the foundation of all `[project]` configuration.

## Name (Required)

The project name must be provided as a string following PEP 425 normalization rules.

```toml

[project]
name = "my-package"

```

**Rules:**

- Contains ASCII letters, digits, hyphens, underscores, and periods only
- Case-insensitive (normalized to lowercase with hyphens)
- Must be unique on package indexes (e.g., PyPI)
- Recommended to use lowercase with hyphens as separators

**Examples:**

- `requests`
- `django-rest-framework`
- `python_dateutil`
- `beautiful-soup4`

## Version (Required)

Specifies the project version. Can be static or dynamic (read from code or configuration).

### Static Version

```toml

[project]
version = "0.1.0"

```

### Dynamic Version

For dynamic versioning, declare in the `dynamic` list and configure via Hatchling:

```toml

[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/my_package/__about__.py"

```

**Version Format:** Must follow `version-specifiers.md#pep-440-overview` version identification scheme:

- Examples: `0.1.0`, `1.0.0a1`, `2.0.0rc1`, `3.1.0.post1`

**Note:** See `../version-management.md` for comprehensive versioning strategies.

## Description

A brief, one-line summary of the project.

```toml

[project]
description = "A short description of the project"

```

**Rules:**

- Keep under 200 characters for optimal display on package indexes
- Written in present tense
- Complements the README but doesn't duplicate it
- Should be informative to someone unfamiliar with the project

**Examples:**

- "HTTP library for Python"
- "Relational query interface for Python"
- "ASGI web framework for building APIs"

## Python Support (requires-python)

Specifies the Python version requirements for the project.

```toml

[project]
requires-python = ">=3.8"

```

**Common Patterns:**

- `">=3.8"` - Python 3.8 and later
- `">=3.8,<4"` - Python 3.8 through 3.x (before major version 4)
- `">=3.8,!=3.9"` - Python 3.8+ but not 3.9
- `">=3.11"` - Python 3.11 and later

**Guidance:**

- Set the minimum version your project actually supports
- Consider available dependencies and their Python requirements
- Update as dependencies drop support for older Python versions

## Readme

The full description of the project as documentation.

### Simple File Reference

```toml

[project]
readme = "README.md"

```

Supported formats: `.md` (markdown), `.rst` (reStructuredText), `.txt` (plain text)

### Complex Configuration with Content Type

```toml

[project]
readme = {file = "README.md", content-type = "text/markdown"}

```

Valid content types:

- `text/markdown` - Markdown format
- `text/x-rst` - reStructuredText format
- `text/plain` - Plain text

### Charset Specification

```toml

[project]
readme = {file = "README.md", content-type = "text/markdown", charset = "utf-8"}

```

### Inline Text

```toml

[project]
readme = {text = "# My Project\n\nThis is my project.", content-type = "text/markdown"}

```

**Rules:**

- If specified as a file, it's always included in source distributions for consistent builds
- Markdown is the recommended format for modern packages
- Package indexes typically render README content on the project page

## Example Configuration

```toml

[project]
name = "my-awesome-package"
version = "1.2.0"
description = "An awesome package for doing cool things"
readme = "README.md"
requires-python = ">=3.8,<4"

```

## Related Configuration

- `ownership.md` - Authors and maintainers
- `keywords-classifiers.md` - Discovery and categorization
- `dynamic-metadata.md` - Runtime metadata injection
