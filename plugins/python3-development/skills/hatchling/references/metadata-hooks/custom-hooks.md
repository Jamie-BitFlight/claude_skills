---
category: metadata-management
topics: [custom-hooks, MetadataHookInterface, hook-implementation, metadata-modification]
related: [metadata-hooks, dynamic-metadata]
---

# Custom Metadata Hooks Implementation

Custom metadata hooks provide complete flexibility for dynamically modifying project metadata at build time through Python code. The `MetadataHookInterface` pattern enables structured implementation of custom hooks that execute during the build process.

Implementing custom metadata hooks involves creating a Python class that extends `MetadataHookInterface`, defining the `update(metadata)` method to modify metadata in-place, and configuring the hook in `pyproject.toml`. Hooks receive a mutable metadata dictionary and can modify any field dynamically.

## Basic Implementation

Create a Python file (typically `hatch_build.py` in project root):

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        # Modify metadata dictionary in-place
        metadata["version"] = "1.0.0"
```

Configure in `pyproject.toml`:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"
```

When the `dynamic` field lists a metadata field, Hatchling expects the hook to provide that field's value through the metadata dictionary.

## MetadataHookInterface API

### Properties

Properties available to hook implementations:

- `root` - Project root directory (Path object)
- `config` - Hook configuration dictionary from `pyproject.toml`

### Methods

**update(metadata: dict) -> None**

Required method that updates metadata in-place. The metadata dictionary contains all project metadata fields and can be modified directly:

```python
def update(self, metadata):
    metadata["version"] = "1.0.0"
    metadata["description"] = "Updated description"
```

**get_known_classifiers() -> list[str]**

Optional method returning a list of valid classifiers for validation. Hatchling uses this method to validate classifier strings:

```python
def get_known_classifiers(self):
    return [
        "Development Status :: 5 - Production/Stable",
        "Custom :: MyClassifier",
    ]
```

## Complete Examples

### Version from File

Extract version from a Python source file using regex pattern matching:

```python
import re
from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface

class VersionHook(MetadataHookInterface):
    def update(self, metadata):
        version_file = self.root / "src" / "mypackage" / "__about__.py"
        content = version_file.read_text(encoding="utf-8")

        match = re.search(
            r'__version__\s*=\s*["\']([^"\']+)["\']',
            content
        )
        if match:
            metadata["version"] = match.group(1)
```

This pattern is suitable for projects that maintain version information in a Python source file and want to avoid duplication in `pyproject.toml`.

### Dynamic Classifiers

Generate Python version classifiers based on the `requires-python` field:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class ClassifiersHook(MetadataHookInterface):
    def update(self, metadata):
        classifiers = []

        # Determine Python version classifiers based on requires-python
        requires_python = metadata.get("requires-python", ">=3.8")

        version_ranges = {
            "3.8": "3.8" in requires_python,
            "3.9": "3.9" in requires_python,
            "3.10": "3.10" in requires_python,
            "3.11": "3.11" in requires_python,
            "3.12": "3.12" in requires_python,
        }

        for version, included in version_ranges.items():
            if included:
                classifiers.append(
                    f"Programming Language :: Python :: {version}"
                )

        metadata.setdefault("classifiers", []).extend(classifiers)
```

This pattern eliminates the need to manually maintain Python version classifiers; they are generated from the version constraint.

### JSON Configuration

Load metadata from an external JSON configuration file:

```python
import json
from hatchling.metadata.plugin.interface import MetadataHookInterface

class JSONMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        config_file = self.root / "metadata.json"
        config = json.loads(config_file.read_text())

        metadata["version"] = config["version"]
        metadata["description"] = config["description"]
        metadata["authors"] = config["authors"]
```

This pattern is useful for projects that manage metadata in a central JSON configuration file shared across multiple build systems.

### Environment-Based Metadata

Customize metadata based on build environment variables:

```python
import os
from hatchling.metadata.plugin.interface import MetadataHookInterface

class EnvironmentHook(MetadataHookInterface):
    def update(self, metadata):
        # Customize metadata based on build environment
        build_env = os.getenv("BUILD_ENV", "dev")

        if build_env == "production":
            metadata["classifiers"] = [
                "Development Status :: 5 - Production/Stable",
            ]
        else:
            metadata["classifiers"] = [
                "Development Status :: 4 - Beta",
            ]
```

This pattern allows metadata to vary based on the build environment, enabling different metadata for development and production builds.

## Advanced: Multiple Dynamic Fields

Handle multiple dynamic metadata fields with helper methods:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class AdvancedHook(MetadataHookInterface):
    def update(self, metadata):
        # Version from source file
        self._inject_version(metadata)

        # Description from docstring
        metadata["description"] = self._extract_docstring()

        # Dynamic classifiers
        self._add_classifiers(metadata)

    def _inject_version(self, metadata):
        version_file = self.root / "src" / "pkg" / "__version__.py"
        namespace = {}
        exec(version_file.read_text(), namespace)
        metadata["version"] = namespace.get("__version__", "0.0.0.dev0")

    def _extract_docstring(self):
        main_file = self.root / "src" / "pkg" / "__init__.py"
        content = main_file.read_text()
        # Extract module docstring
        if content.startswith('"""'):
            return content.split('"""')[1].strip()
        return "No description available"

    def _add_classifiers(self, metadata):
        base_classifiers = [
            "Development Status :: 4 - Beta",
            "Programming Language :: Python :: 3",
        ]
        metadata.setdefault("classifiers", []).extend(base_classifiers)
```

Breaking complex hooks into helper methods improves readability and maintainability.

## Configuration Options

Pass configuration from `pyproject.toml` to the hook implementation:

```toml
[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"
version-file = "src/__version__.py"
include-beta = true
```

Access configuration in the hook via `self.config`:

```python
def update(self, metadata):
    version_file = self.config.get("version-file", "src/__version__.py")
    include_beta = self.config.get("include-beta", False)

    # Use configuration values...
```

Configuration allows hooks to be flexible and reusable across different projects without code modifications.

## Error Handling

Handle file not found and other errors gracefully:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class SafeHook(MetadataHookInterface):
    def update(self, metadata):
        try:
            version_file = self.root / "VERSION"
            metadata["version"] = version_file.read_text().strip()
        except FileNotFoundError:
            # Fallback to default version
            metadata["version"] = "0.0.0.dev0"
        except Exception as e:
            # Log error and provide fallback
            import sys
            print(f"Warning: Failed to read version: {e}", file=sys.stderr)
            metadata["version"] = "0.0.0.dev0"
```

Graceful error handling ensures the build process continues even if hook operations fail, with fallback values.

## Debugging

Print debug information during hook execution:

```python
import sys
from hatchling.metadata.plugin.interface import MetadataHookInterface

class DebugHook(MetadataHookInterface):
    def update(self, metadata):
        print("Debug: Hook executed", file=sys.stderr)
        print(f"Root: {self.root}", file=sys.stderr)
        print(f"Config: {self.config}", file=sys.stderr)
        print(f"Metadata keys: {list(metadata.keys())}", file=sys.stderr)
```

Debug output should be written to `sys.stderr` to avoid interfering with build output.

## Best Practices

**Deterministic behavior**: Same input should always produce the same output. Avoid random values or timestamp-based metadata.

**Performance**: Minimize I/O and computation in hooks. Complex operations slow down builds.

**Robustness**: Handle all error conditions gracefully. Provide meaningful error messages and sensible fallback values.

**Clear documentation**: Comment complex logic and explain what fields are modified and why.

**Testability**: Design hooks so their behavior can be validated independently of the build system.

**Configuration flexibility**: Use `self.config` to accept configuration rather than hardcoding values, making hooks reusable.

## Related Topics

- `metadata-hooks.md` - Hook system overview
- `../project-metadata/dynamic-metadata.md` - Field declaration
- `../project-metadata/metadata-options.md` - Configuration options
