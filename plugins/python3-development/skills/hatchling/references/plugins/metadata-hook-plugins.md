---
name: Metadata Hook Plugins Reference
description: Guide to implementing metadata hook plugins in Hatchling, covering the MetadataHookInterface, dynamic metadata modification, custom classifiers, and configuration examples.
---

# Metadata Hook Plugins

Metadata hook plugins dynamically modify project metadata after it has been loaded from `pyproject.toml`.

## Overview

Metadata hooks enable computation of project metadata from external sources (files, APIs, build artifacts) instead of requiring static entry in `pyproject.toml`. Common use cases include dynamically setting version, description, authors, dependencies, or classifiers.

## Core Interface: MetadataHookInterface

### PLUGIN_NAME

Each metadata hook must define a string identifier:

```python
class DynamicDescriptionHook(MetadataHookInterface):
    PLUGIN_NAME = "dynamic-description"
```

Users select metadata hooks via configuration:

```toml
[project]
dynamic = ["version", "description"]

[tool.hatch.metadata.hooks.dynamic-description]
# Configuration for this hook
```

## Essential Methods

### update(metadata)

**Required**: Modify project metadata mapping in-place.

```python
def update(self, metadata: dict) -> None:
    """
    This updates the metadata mapping of the project table in-place.

    The metadata dict contains all standard project fields:
    - name, version, description, readme
    - authors, maintainers, license
    - keywords, classifiers
    - dependencies, optional-dependencies
    - urls (homepage, documentation, repository, etc.)

    Args:
        metadata: Mutable dictionary of project metadata
    """
    # Example: Set version from file
    with open(os.path.join(self.root, "VERSION")) as f:
        metadata["version"] = f.read().strip()

    # Example: Set description from README
    readme_path = os.path.join(self.root, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path) as f:
            metadata["description"] = f.read()

    # Example: Add dynamic classifiers
    metadata["classifiers"].extend(["Environment :: Console", "Topic :: Software Development"])
```

### get_known_classifiers()

**Optional**: Return additional valid classifiers beyond PyPI's standard list.

```python
def get_known_classifiers(self) -> list[str]:
    """
    This returns extra classifiers that should be considered valid
    in addition to the ones known to PyPI.

    Useful when using custom or vendor-specific classifiers.

    Returns:
        list[str]: List of valid classifier strings
    """
    return ["Topic :: Documentation", "Topic :: System :: Shells"]
```

## Configuration & Properties

### root (Property)

Project root directory:

```python
@property
def root(self) -> str:
    """The root of the project tree."""
    return self._root
```

### config (Property)

Metadata hook configuration from `[tool.hatch.metadata.hooks.<PLUGIN_NAME>]`:

```python
@property
def config(self) -> dict:
    """
    Hook configuration from [tool.hatch.metadata.hooks.<PLUGIN_NAME>]

    Example:
    [tool.hatch.metadata.hooks.readme-file]
    file = "docs/description.md"
    """
    return self._config
```

## Official Metadata Hooks

### custom

Enables custom metadata hook via `hatch_build.py`.

Configuration:

```toml
[project]
dynamic = ["version", "description"]

[tool.hatch.metadata.hooks.custom]
```

Implement in `hatch_build.py`:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "custom"

    def update(self, metadata):
        # Custom logic here
        pass
```

## Third-Party Metadata Hooks

### hatch-fancy-pypi-readme

Dynamically construct README content from multiple sources and templates.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-fancy-pypi-readme"]
```

Configuration:

```toml
[project]
dynamic = ["readme"]

[tool.hatch.metadata.hooks.fancy-pypi-readme]
content-type = "text/markdown"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
text = "# My Project\n"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
path = "README.md"
start-line = 2  # Skip title line
```

Features:

- Compose README from fragments
- Template substitution
- Conditional includes based on environment

### hatch-requirements-txt

Read project dependencies from `requirements.txt` files.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-requirements-txt"]
```

Configuration:

```toml
[project]
dynamic = ["dependencies", "optional-dependencies"]

[tool.hatch.metadata.hooks.requirements_txt]
files = ["requirements/base.txt"]

[tool.hatch.metadata.hooks.requirements_txt.optional-dependencies]
dev = ["requirements/dev.txt"]
docs = ["requirements/docs.txt"]
```

### hatch-nodejs-version

Read metadata fields from Node.js `package.json`.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-nodejs-version"]
```

Configuration:

```toml
[project]
dynamic = ["version", "description"]

[tool.hatch.metadata.hooks.nodejs]
```

Reads from `package.json` fields:

- `version` → project version
- `description` → project description
- `author` → project authors
- `keywords` → project keywords

### hatch-docstring-description

Set project description from package docstring.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-docstring-description"]
```

Configuration:

```toml
[project]
dynamic = ["description"]

[tool.hatch.metadata.hooks.docstring-description]
```

Extracts first docstring from main package as description.

### hatch-odoo

Determine dependencies from Odoo add-on manifests.

Installation:

```toml
[build-system]
requires = ["hatchling", "hatch-odoo"]
```

Configuration:

```toml
[project]
dynamic = ["dependencies"]

[tool.hatch.metadata.hooks.odoo]
```

### UniDep

Unified dependency management for pip and conda.

Installation:

```toml
[build-system]
requires = ["hatchling", "unidep"]
```

Configuration:

```toml
[project]
dynamic = ["dependencies"]

[tool.hatch.metadata.hooks.unidep]
dependencies-file = "requirements.yaml"
```

## Example: Custom Metadata Hook

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface
import os
import json


class JSONMetadataHook(MetadataHookInterface):
    """Load metadata from JSON configuration file."""

    PLUGIN_NAME = "json-config"

    def update(self, metadata: dict) -> None:
        config_file = os.path.join(self.root, self.config.get("file", "metadata.json"))

        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Metadata config not found: {config_file}")

        with open(config_file) as f:
            config = json.load(f)

        # Update version
        if "version" in config:
            metadata["version"] = config["version"]

        # Update description
        if "description" in config:
            metadata["description"] = config["description"]

        # Update classifiers
        if "classifiers" in config:
            metadata["classifiers"].extend(config["classifiers"])

        # Update urls
        if "urls" in config:
            metadata.setdefault("urls", {}).update(config["urls"])

    def get_known_classifiers(self) -> list[str]:
        """Return any custom classifiers from config."""
        return self.config.get("known_classifiers", [])
```

## Configuration Examples

### Dynamic Version and Description

```toml
[project]
name = "my-project"
dynamic = ["version", "description"]

[tool.hatch.metadata.hooks.custom]
# Custom hook configuration
```

### Multiple Dynamic Fields

```toml
[project]
dynamic = ["version", "description", "readme", "dependencies"]

[tool.hatch.metadata.hooks.requirements_txt]
files = ["requirements.txt"]

[tool.hatch.metadata.hooks.fancy-pypi-readme]
content-type = "text/markdown"
text = "# Project\n"
```

### Environment-Specific Metadata

```toml
[project]
dynamic = ["dependencies"]

[tool.hatch.metadata.hooks.custom]
environment = "production"  # Custom config for hook
```

## Usage Patterns

### Dynamic Version in Metadata

```python
class VersionMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "version"

    def update(self, metadata: dict) -> None:
        # Read version from __init__.py
        init_file = os.path.join(self.root, self.config.get("path", "src/mypackage/__init__.py"))
        with open(init_file) as f:
            for line in f:
                if line.startswith("__version__"):
                    # Extract: __version__ = "1.0.0"
                    version = line.split("=")[1].strip().strip("\"'")
                    metadata["version"] = version
                    break
```

### Dynamic Classifiers

```python
class PlatformClassifiersHook(MetadataHookInterface):
    PLUGIN_NAME = "platform-classifiers"

    def update(self, metadata: dict) -> None:
        import sys

        classifiers = ["Environment :: Console"]

        if sys.platform == "win32":
            classifiers.append("Operating System :: Microsoft :: Windows")
        elif sys.platform == "darwin":
            classifiers.append("Operating System :: MacOS")
        else:
            classifiers.append("Operating System :: POSIX :: Linux")

        metadata["classifiers"].extend(classifiers)
```

### Combined with Version Source

Use metadata hooks with dynamic version sources:

```toml
[project]
dynamic = ["version", "description"]

[tool.hatch.version]
source = "regex"
path = "src/__version__.py"
pattern = '__version__\s*=\s*["\']([^"\']+)["\']'

[tool.hatch.metadata.hooks.custom]
description_file = "docs/description.txt"
```

## Best Practices

1. **Idempotent**: Ensure hook produces same metadata on repeated calls
2. **Error Handling**: Raise clear exceptions for missing files or invalid data
3. **Performance**: Minimize file I/O; cache when possible
4. **Validation**: Verify updated metadata is valid (e.g., valid classifiers)
5. **Documentation**: Document required files and configuration options
6. **Testing**: Test metadata hooks independently of build process
7. **Backwards Compatibility**: Handle missing optional config gracefully

## Validation

Metadata hooks should validate classifier values:

```python
def update(self, metadata: dict) -> None:
    classifiers = metadata.get("classifiers", [])

    # Ensure classifiers are valid strings
    if not all(isinstance(c, str) for c in classifiers):
        raise ValueError("Classifiers must be strings")

    # Check for duplicates
    if len(classifiers) != len(set(classifiers)):
        raise ValueError("Duplicate classifiers found")

    metadata["classifiers"] = classifiers
```

## See Also

- [Dynamic Metadata Configuration](https://hatch.pypa.io/latest/how-to/config/dynamic-metadata/)
- [MetadataHookInterface Reference](https://hatch.pypa.io/latest/plugins/metadata-hook/reference/)
- [Hatchling Metadata Documentation](https://hatch.pypa.io/latest/plugins/metadata-hook/)
- [Project Metadata Reference](https://hatch.pypa.io/latest/config/metadata/)
