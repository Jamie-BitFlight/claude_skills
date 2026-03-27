---
category: Dynamic Configuration & Metadata
topics: [dynamic-fields, metadata-hooks, version-management, field-resolution, context-formatting]
related: [README.md, configuration-interpolation.md, optional-dependencies.md, global-fields.md]
---

# Dynamic Configuration and Field Resolution

Reference documentation for dynamic configuration and field resolution in Hatchling. Use this to help users understand how to programmatically set project metadata fields at build time rather than hardcoding them into `pyproject.toml`.

## Overview

Dynamic configuration is the process of determining metadata values (like version, author, license) during the build process instead of statically defining them. When assisting users, explain this is useful when:

- Metadata comes from external sources (JSON files, APIs, git)
- Values need to be computed at build time
- You want a single source of truth across your project
- Different build contexts require different values

## Declaring Dynamic Fields

### Configuration

In `pyproject.toml`, declare which fields will be set dynamically:

```toml
[project]
name = "myproject"
description = "My project"
dynamic = ["version", "authors", "license"]

# NOTE: Do NOT define these statically when they're dynamic
# [project]
# version = "1.0.0"  # ERROR: Cannot be both static and dynamic
```

### Supported Dynamic Fields

Common fields that can be made dynamic:

- `version` — Project version
- `description` — Project description
- `readme` — README file reference
- `license` — License identifier
- `authors` — Project authors
- `maintainers` — Project maintainers
- `keywords` — Project keywords
- `classifiers` — Package classifiers
- `urls` — Project URLs
- `dependencies` — Project dependencies (Hatchling v1.2.0+)
- `optional-dependencies` — Optional dependency groups (Hatchling v1.2.0+)
- `entry-points` — Console and GUI scripts, plugins

## Implementation Approaches

### Approach 1: Built-in Version Sources

For version specifically, use built-in version source plugins before custom hooks:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/myproject/__init__.py"
```

This reads version from a Python file:

```python
# src/myproject/__init__.py
__version__ = "1.2.3"
```

**Built-in version sources:**

- `regex` — Extract from file using regex pattern
- `env` — Read from environment variable
- `python` — Import from Python module

### Approach 2: Custom Metadata Hooks

For other fields or complex logic, implement a custom metadata hook:

```python
# hatch_build.py
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        # metadata is a dict; modify it in place
        metadata["version"] = "1.2.3"
        metadata["authors"] = [
            {"name": "Author Name", "email": "author@example.com"}
        ]
```

Configure it in `pyproject.toml`:

```toml
[project]
dynamic = ["version", "authors"]

[tool.hatch.metadata.hooks.custom]
```

### Approach 3: External File Sources

Read metadata from JSON, TOML, or YAML files:

```python
# hatch_build.py
import json
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class JSONMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        json_file = Path(self.root) / "metadata.json"
        with open(json_file) as f:
            data = json.load(f)

        metadata["version"] = data["version"]
        metadata["license"] = data["license"]
        metadata["authors"] = data["authors"]
        metadata["keywords"] = data.get("keywords", [])
```

With `metadata.json`:

```json
{
  "version": "1.2.3",
  "license": "MIT",
  "authors": [{ "name": "Author Name", "email": "author@example.com" }],
  "keywords": ["python", "package", "tool"]
}
```

## Combining Dynamic Fields with Context Formatting

### Dynamic Dependencies with Context Formatting

Since Hatchling v1.2.0, you can use context formatting in dynamic dependencies:

```toml
[project]
dynamic = ["dependencies", "optional-dependencies"]

[tool.hatch.metadata.hooks.custom]
path = "hooks/metadata.py"
```

In the hook:

```python
# hooks/metadata.py
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class DynamicDepsHook(MetadataHookInterface):
    def update(self, metadata):
        root = Path(self.root)

        metadata["dependencies"] = [
            "requests",
            f"local-pkg @ {root}/packages/local-pkg",
            f"utils @ {{{root.parent.as_uri()}}}/utils",
        ]

        metadata["optional-dependencies"] = {
            "dev": [
                "pytest",
                f"test-utils @ {root}/test-utils",
            ],
            "docs": [
                "sphinx",
                f"api-docs @ {root}/docs/api-docs",
            ],
        }
```

**Important**: Context formatting fields must be evaluated as strings in the hook, not directly interpolated.

### Environment-Aware Dynamic Configuration

Adjust metadata based on build environment:

```python
# hatch_build.py
import os
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class EnvAwareMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        root = Path(self.root)
        env = os.getenv("HATCH_ENV", "dev")

        # Base metadata
        metadata["version"] = self._get_version()
        metadata["authors"] = [
            {"name": "Project Team", "email": "team@example.com"}
        ]

        # Environment-specific dependencies
        if env == "dev":
            metadata["optional-dependencies"] = {
                "dev": [
                    "pytest",
                    f"dev-tools @ {root}/tools/dev",
                ]
            }
        elif env == "prod":
            metadata["optional-dependencies"] = {
                "prod": [
                    "gunicorn",
                    "psycopg2",
                ]
            }

    def _get_version(self):
        # Try multiple sources
        version_file = Path(self.root) / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()

        # Fall back to environment variable
        return os.getenv("PROJECT_VERSION", "0.0.0-dev")
```

## Metadata Hook Interface

### MetadataHookInterface Contract

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class MyMetadataHook(MetadataHookInterface):
    def __init__(self, root, config):
        """
        root: Path to project root
        config: Hook configuration from [tool.hatch.metadata.hooks.custom]
        """
        self.root = root
        self.config = config

    def update(self, metadata):
        """
        Modify metadata dictionary in place.

        metadata keys (see PEP 621):
        - name, version, description, readme
        - requires-python, authors, maintainers
        - license, keywords, classifiers
        - urls, dependencies, optional-dependencies
        - entry-points
        """
```

### Available Attributes

- `self.root` — Project root path (Path object)
- `self.config` — Hook configuration dictionary from `[tool.hatch.metadata.hooks.custom]`

### Important Rules

1. **Modify in place**: The `update()` method receives a dictionary and modifies it directly. Return value is ignored.

2. **Use correct types**:

   - Arrays → `list` (e.g., `metadata["authors"]`)
   - Objects → `dict` (e.g., `metadata["urls"]`)
   - Strings → `str`

   **Example:**

   ```python
   metadata["authors"] = [  # Use list
       {"name": "Alice", "email": "alice@example.com"},
       {"name": "Bob", "email": "bob@example.com"},
   ]

   metadata["urls"] = {  # Use dict
       "Homepage": "https://example.com",
       "Documentation": "https://docs.example.com",
   }

   metadata["keywords"] = ["python", "tool"]  # Use list
   ```

3. **Only set declared dynamic fields**: Only modify fields listed in `[project] dynamic = [...]`

4. **Don't redefine static fields**: If a field is defined statically, don't set it in the hook.

## Error Handling and Validation

### Build Failures

The build fails if:

1. A dynamic field is also defined statically:

   ```console
   Error: Field 'version' is defined both statically and dynamically
   ```

2. A required field is not set:

   ```console
   Error: Missing required field 'version'
   ```

3. A context formatting field is missing:
   ```console
   Error: Environment variable 'REQUIRED_VAR' not set and no default provided
   ```

### Validation

Validate metadata in hooks:

```python
def update(self, metadata):
    version = self._get_version()

    # Validate
    if not version or not isinstance(version, str):
        raise ValueError(f"Invalid version: {version}")

    if not version[0].isdigit():
        raise ValueError(f"Version must start with digit: {version}")

    metadata["version"] = version
```

## Hatchling Implementation Notes

### Hatchling v1.2.0+ (January 2024)

Added support for context formatting in `project.dependencies` and `project.optional-dependencies`.

```python
metadata["optional-dependencies"] = {
    "dev": [
        "pytest",
        "pkg @ {root}/packages/pkg",  # Context formatting now works!
    ]
}
```

### Hatchling v1.3.0+ (February 2024)

Improved error messages for missing context formatting fields:

- Clear indication of which environment variables are missing
- Helpful error messages suggesting default values
- Fixed context formatting field resolution on Windows

## Practical Patterns

### Single Source of Truth Pattern

Keep all metadata in one place:

```python
# hooks/metadata.py
import json
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class SinceMetadataHook(MetadataHookInterface):
    """Read all metadata from a single metadata.json file."""

    def update(self, metadata):
        metadata_file = Path(self.root) / ".metadata" / "info.json"

        with open(metadata_file) as f:
            info = json.load(f)

        # Map JSON keys to PEP 621 metadata
        metadata["version"] = info["version"]
        metadata["description"] = info["description"]
        metadata["license"] = {"text": info["license"]}
        metadata["authors"] = [
            {"name": author["name"], "email": author["email"]}
            for author in info.get("authors", [])
        ]
        metadata["urls"] = info.get("urls", {})
        metadata["keywords"] = info.get("keywords", [])
```

### Git-Based Versioning

Extract version from git tags:

```python
# hooks/metadata.py
import subprocess
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class GitVersionHook(MetadataHookInterface):
    def update(self, metadata):
        try:
            version = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.root,
                text=True
            ).strip()
            # Remove 'v' prefix if present
            version = version.lstrip('v')
            metadata["version"] = version
        except subprocess.CalledProcessError:
            # No tags; use development version
            metadata["version"] = "0.0.0-dev"
```

### Conditional Metadata

Generate metadata based on build context:

```python
# hooks/metadata.py
import os
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class ConditionalMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        metadata["version"] = self._get_version()

        # Build context dependent
        build_type = os.getenv("BUILD_TYPE", "local")

        metadata["optional-dependencies"] = {
            "dev": ["pytest", "pytest-cov"],
        }

        if build_type == "ci":
            metadata["optional-dependencies"]["ci"] = [
                "coverage",
                "codecov",
            ]

        if build_type == "release":
            metadata["optional-dependencies"]["release"] = [
                "build",
                "twine",
            ]

    def _get_version(self):
        # Production: from VERSION file
        # CI: from git tag
        # Local: from git with -dev suffix
        pass
```

## Related Topics

- `global-fields.md` — Fields used in dynamic configuration
- `configuration-interpolation.md` — Advanced field nesting and fallbacks
- `optional-dependencies.md` — Dynamic optional dependency groups
- `../build-system/publishing.md` — How dynamic metadata affects build/publish workflows
