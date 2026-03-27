---
title: Regex Version Source
description: Extract versions from files using regular expressions. Covers default patterns, custom pattern matching, file type support (Python, JSON, TOML, shell), version updates, and best practices.
---

# Regex Version Source

The regex version source is the default version source plugin in Hatchling. It extracts version information from files using regular expressions, providing a simple yet powerful method for managing versions stored as strings in Python files or other text formats.

## Basic Configuration

The regex source is used by default when you specify dynamic versioning:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
path = "src/my_package/__about__.py"
# source = "regex"  # Optional, as regex is the default
```

## Configuration Options

### Required Options

| Option | Type   | Description                                      |
| ------ | ------ | ------------------------------------------------ |
| `path` | string | Relative path to the file containing the version |

### Optional Options

| Option    | Type        | Default   | Description                                 |
| --------- | ----------- | --------- | ------------------------------------------- |
| `pattern` | string/bool | `true`    | Regular expression pattern to match version |
| `source`  | string      | `"regex"` | Explicitly specify the source type          |

## Default Pattern

When `pattern` is not specified or set to `true`, Hatchling uses a default pattern that matches common Python version declarations:

```python
# Default pattern matches these formats:
__version__ = "1.2.3"
__version__ = '1.2.3'
VERSION = "1.2.3"
VERSION = '1.2.3'
version = "1.2.3"
version = '1.2.3'
__version__: str = "1.2.3"  # Type hints supported
VERSION: Final[str] = "1.2.3"  # Final annotations supported
```

The default pattern in regex form:

<eg>
(?i)(?:__version__|version)\s*(?::\s*(?:str|Final\[str\]))?\s*=\s*['\"]v?[?P<version>[^'\"]+]('\")
</eg>

## Custom Patterns

### Basic Custom Pattern

Specify a custom regex pattern with a named group `version`:

```toml
[tool.hatch.version]
path = "src/my_package/__init__.py"
pattern = "VERSION = ['\"](?P<version>[^'\"]+)['\"]"
```

### Pattern with Version Prefix

Handle version strings with prefixes:

```toml
[tool.hatch.version]
path = "setup.cfg"
pattern = "version = v(?P<version>.+)"
```

Matches:

```ini
[metadata]
version = v1.2.3
```

### Multi-line Pattern

Use verbose regex for complex patterns:

```toml
[tool.hatch.version]
path = "src/config.py"
pattern = """(?x)
    \\#\\s*Version:\\s*  # Comment: Version:
    (?P<version>\\S+)     # Capture non-whitespace as version
"""
```

Matches:

```python
# Version: 1.2.3
```

### JSON File Pattern

Extract version from JSON files:

```toml
[tool.hatch.version]
path = "package.json"
pattern = '"version":\\s*"(?P<version>[^"]+)"'
```

Matches:

```json
{
  "name": "my-package",
  "version": "1.2.3"
}
```

## Common Use Cases

### Single Version File

The most common pattern - a dedicated version file:

```toml
[tool.hatch.version]
path = "src/my_package/_version.py"
```

```python
# src/my_package/_version.py
__version__ = "1.2.3"
```

### Version in **init**.py

Store version in the package's `__init__.py`:

```toml
[tool.hatch.version]
path = "src/my_package/__init__.py"
pattern = "__version__ = ['\"](?P<version>[^'\"]+)['\"]"
```

```python
# src/my_package/__init__.py
"""My package description."""

__version__ = "1.2.3"
__author__ = "Your Name"
```

### Version with Metadata

Include additional version metadata:

```toml
[tool.hatch.version]
path = "src/my_package/__about__.py"
pattern = "__version__ = ['\"](?P<version>[^'\"]+)['\"]"
```

```python
# src/my_package/__about__.py
__version__ = "1.2.3"
__version_info__ = (1, 2, 3)
__version_date__ = "2024-01-01"
```

### Multiple Version Formats

When your file contains multiple version-like strings:

```toml
[tool.hatch.version]
path = "src/config.py"
pattern = "^PACKAGE_VERSION = ['\"](?P<version>[^'\"]+)['\"]"
```

```python
# src/config.py
API_VERSION = "v1"  # Not matched
PACKAGE_VERSION = "1.2.3"  # Matched
PROTOCOL_VERSION = "2.0"  # Not matched
```

## Version Updates

The regex source supports updating versions using the `hatch version` command:

### Simple Update

```bash
$ hatch version patch
Old: 1.2.3
New: 1.2.4
```

The file is updated in place:

```python
# Before
__version__ = "1.2.3"

# After
__version__ = "1.2.4"
```

### Preserving File Structure

The regex source preserves:

- Whitespace and formatting
- Comments
- Other content in the file
- Quote style (single vs double)

```python
# Before update
"""Package metadata."""

__version__ = '1.2.3'  # Current version
__author__ = "Name"

# After `hatch version 2.0.0`
"""Package metadata."""

__version__ = '2.0.0'  # Current version
__author__ = "Name"
```

## Advanced Patterns

### Capturing Version Parts

Use groups to capture version components:

```toml
[tool.hatch.version]
path = "version.txt"
pattern = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
```

Note: Only the `version` group is used; other groups are for matching only.

### Conditional Patterns

Match different version formats:

```toml
[tool.hatch.version]
path = "src/version.py"
pattern = "(?:__version__|VERSION)\\s*=\\s*['\"](?P<version>[^'\"]+)['\"]"
```

Matches both:

```python
__version__ = "1.2.3"
# or
VERSION = "1.2.3"
```

### With Type Annotations

Support modern Python with type hints:

```toml
[tool.hatch.version]
path = "src/my_package/__init__.py"
pattern = "__version__:\\s*(?:Final\\[)?str\\]?\\s*=\\s*['\"](?P<version>[^'\"]+)['\"]"
```

Matches:

```python
__version__: str = "1.2.3"
__version__: Final[str] = "1.2.3"
```

## Working with Different File Types

### Python Files

Standard Python version declarations:

```python
# __about__.py
__version__ = "1.2.3"
```

### Configuration Files

INI/TOML style configurations:

```toml
[tool.hatch.version]
path = "setup.cfg"
pattern = "version\\s*=\\s*(?P<version>.+)"
```

### Markdown Files

Extract version from documentation:

```toml
[tool.hatch.version]
path = "README.md"
pattern = "Version:\\s*(?P<version>\\S+)"
```

### Shell Scripts

Version in shell scripts:

```toml
[tool.hatch.version]
path = "scripts/version.sh"
pattern = "VERSION=\"(?P<version>[^\"]+)\""
```

## Error Handling

### Pattern Not Matching

When your pattern doesn't match:

```bash
$ hatch version
Error: Unable to find version string in 'src/my_package/__about__.py'
```

Debug with a test script:

```python
import re
from pathlib import Path

pattern = r"__version__ = ['\"](?P<version>[^'\"]+)['\"]"
content = Path("src/my_package/__about__.py").read_text()

if match := re.search(pattern, content):
    print(f"Found version: {match.group('version')}")
else:
    print("Pattern did not match")
    print(f"File content:\n{content}")
```

### Multiple Matches

When pattern matches multiple times:

```python
# File with multiple matches
__version__ = "1.2.3"  # First match (used)
old_version = "1.2.2"  # Second match (ignored)
```

The regex source uses the first match found.

### File Not Found

```toml
[tool.hatch.version]
path = "non/existent/file.py"
```

Error:

<eg>
Error: Version source path 'non/existent/file.py' does not exist
</eg>

## Best Practices

### 1. Maintain Simple Patterns

Keep regex patterns straightforward and readable:

```toml
# Good: Simple and clear
pattern = "__version__ = ['\"](?P<version>[^'\"]+)['\"]"

# Avoid: Overly complex
pattern = "(?:(?:__)?(?:version|VERSION)(?:__)?)\\s*(?::|=)\\s*(?:['\"])?(?P<version>[^'\"\\s]+)"
```

### 2. Validate Patterns Before Deployment

Test patterns thoroughly before committing to the project:

```python
# test_pattern.py
import re

pattern = r"__version__ = ['\"](?P<version>[^'\"]+)['\"]"
test_content = '__version__ = "1.2.3"'

match = re.search(pattern, test_content)
assert match, "Pattern doesn't match"
assert match.group("version") == "1.2.3"
```

### 3. Prefer Dedicated Version Files

Use dedicated version files rather than embedding versions in package code:

```toml
# Recommended
path = "src/my_package/_version.py"

# Less ideal
path = "src/my_package/__init__.py"  # Mixed with other code
```

### 4. Document Custom Pattern Logic

When using non-standard patterns, document the reasoning:

```toml
[tool.hatch.version]
path = "version.txt"
# Custom pattern to match our versioning format: "Release: X.Y.Z"
pattern = "Release:\\s*(?P<version>\\S+)"
```

## Performance Considerations

The regex source is fast because it:

- Only reads the specified file (not the entire project)
- Stops searching after first match
- Doesn't execute any code (unlike code source)
- Uses compiled regular expressions

## Comparison with Code Source

| Feature          | Regex Source    | Code Source             |
| ---------------- | --------------- | ----------------------- |
| **Performance**  | Fast            | Slower (imports Python) |
| **Flexibility**  | Pattern-based   | Full Python logic       |
| **File Types**   | Any text file   | Python files only       |
| **Dependencies** | None            | May have imports        |
| **Complexity**   | Simple patterns | Arbitrary complexity    |
| **Default**      | Yes             | No                      |

## Migration Examples

### From setuptools

```python
# Old: setup.py
with open("src/my_package/_version.py") as f:
    version = re.search(r'__version__ = ["\']([^"\']+)', f.read()).group(1)

setup(
    version=version,
    ...
)
```

```toml
# New: pyproject.toml
[tool.hatch.version]
path = "src/my_package/_version.py"
```

### From bumpversion

```ini
# Old: .bumpversion.cfg
[bumpversion]
current_version = 1.2.3
files = src/my_package/__init__.py
```

```toml
# New: pyproject.toml
[tool.hatch.version]
path = "src/my_package/__init__.py"
```

## Troubleshooting

### Issue: Special Characters in Pattern

Problem: Regex special characters not escaped

```toml
# Wrong
pattern = "__version__ = "(?P<version>[^"]+)""

# Correct (escape quotes)
pattern = "__version__ = \"(?P<version>[^\"]+)\""
```

### Issue: Windows Path Separators

Problem: Backslashes in Windows paths

```toml
# Use forward slashes (works on all platforms)
path = "src/my_package/__about__.py"

# Not: src\my_package\__about__.py
```

### Issue: Unicode in Version Files

The regex source handles Unicode correctly:

```python
# Supported
__version__ = "1.2.3"  # ASCII
__версия__ = "1.2.3"  # Cyrillic
__版本__ = "1.2.3"  # Chinese
```

## See Also

- `code-version-source.md` - For complex version logic
- `env-version-source.md` - For CI/CD workflows
- `version-build-hook.md` - Write versions during build
- `version-cli.md` - Command-line version management
