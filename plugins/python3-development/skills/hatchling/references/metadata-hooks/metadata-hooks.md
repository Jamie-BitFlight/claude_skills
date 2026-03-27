---
category: metadata-management
topics: [metadata-hooks, hook-system, dynamic-injection, build-process]
related: [custom-hooks, dynamic-metadata, metadata-options]
---

# Metadata Hooks System

Metadata hooks provide mechanisms for dynamic metadata injection during the build process. Hatchling's hook system supports both built-in hooks and custom implementations for complex metadata requirements.

When implementing metadata hooks, configure them in `[tool.hatch.metadata.hooks.*]` sections and implement the `MetadataHookInterface` for custom behavior. Built-in hooks handle common scenarios; for specialized requirements, implement custom hooks in a file like `hatch_build.py`.

## Hook Configuration

Metadata hooks are configured in the `[tool.hatch.metadata.hooks.*]` section of `pyproject.toml`. Each hook section maps to a hook name and contains hook-specific configuration:

```toml
[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"
```

The `path` option specifies the Python file containing the hook implementation.

## Built-in Hooks

### Custom Hook

The custom metadata hook allows arbitrary Python code execution for dynamic metadata modification:

```toml
[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"
```

Implementation file (`hatch_build.py`):

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        metadata["version"] = "1.0.0"
        metadata["classifiers"] = [
            "Development Status :: 5 - Production/Stable",
        ]
```

The custom hook executes during build processes and receives a mutable metadata dictionary that can be modified in-place.

## Hook Interface

All metadata hooks implement `MetadataHookInterface`:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class MyMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        """Update project metadata in-place."""
        pass

    def get_known_classifiers(self):
        """Return list of valid classifiers."""
        return []
```

The `update()` method is required; `get_known_classifiers()` is optional.

## Hook Properties

Properties available to hook implementations:

- `self.root` - Project root directory (Path object)
- `self.config` - Hook configuration dictionary from `pyproject.toml`

## Use Cases

### Reading Version from File

Extract version from a Python source file using regex:

```python
import re

class VersionHook(MetadataHookInterface):
    def update(self, metadata):
        version_file = self.root / "src" / "pkg" / "__init__.py"
        content = version_file.read_text()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            metadata["version"] = match.group(1)
```

### Computing Classifiers

Generate classifiers based on the Python version requirement:

```python
class ClassifiersHook(MetadataHookInterface):
    def update(self, metadata):
        requires_python = metadata.get("requires-python", ">=3.8")
        classifiers = []

        # Add Python version classifiers
        if ">=3.8" in requires_python:
            classifiers.append("Programming Language :: Python :: 3.8")
        if ">=3.9" in requires_python:
            classifiers.append("Programming Language :: Python :: 3.9")

        metadata.setdefault("classifiers", []).extend(classifiers)
```

### Loading from JSON

Load metadata from a JSON configuration file:

```python
import json

class JSONHook(MetadataHookInterface):
    def update(self, metadata):
        config_file = self.root / "project_config.json"
        config = json.loads(config_file.read_text())
        metadata["version"] = config["version"]
        metadata["description"] = config["description"]
```

## Hook Configuration Options

Pass configuration from `pyproject.toml` to the hook implementation:

```toml
[tool.hatch.metadata.hooks.custom]
path = "hooks.py"
version-file = "src/pkg/__about__.py"
```

Access configuration in the hook:

```python
class MyHook(MetadataHookInterface):
    def update(self, metadata):
        version_file = self.config.get("version-file")
        # Use version_file...
```

Configuration values are passed as a dictionary to the hook and can be accessed via `self.config`.

## Hook Execution Flow

Metadata hooks execute during:

1. Building distributions (wheel and sdist)
2. Running `hatch project metadata` command
3. Installing the project
4. IDE operations requiring metadata

The execution flow ensures metadata is consistently computed across all build scenarios.

## Best Practices

1. **Keep hooks simple and deterministic** - Same input should always produce same output
2. **Handle errors gracefully** - Provide fallback values or meaningful error messages
3. **Document hook behavior clearly** - Explain what fields are modified and why
4. **Avoid external dependencies** - Minimize hook dependencies to reduce build complexity
5. **Use configuration for flexibility** - Accept configuration from `pyproject.toml` rather than hardcoding values

## Related Topics

- `custom-hooks.md` - Detailed implementation guide
- `../project-metadata/dynamic-metadata.md` - Field declaration
- `../project-metadata/metadata-options.md` - Hook configuration options
