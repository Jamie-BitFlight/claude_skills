---
name: Builder Plugins Reference
description: Comprehensive guide to implementing builder plugins in Hatchling, covering the BuilderInterface, essential methods, configuration, and examples for creating custom package builders.
---

# Builder Plugins

Builder plugins extend Hatchling's package building capabilities. They determine how Python distributions are created and packaged.

## Overview

Builder plugins are responsible for transforming a Python project into distributable artifacts (wheels, source distributions, or custom formats). Each builder must implement the `BuilderInterface` abstract base class.

## Core Interface: BuilderInterface

### PLUGIN_NAME

Each builder must define a string identifier:

```python
class SpecialBuilder(BuilderInterface):
    PLUGIN_NAME = 'special'
```

Users select builders via configuration:

```toml
[tool.hatch.build.targets.special]
# Configuration for this builder
```

### Essential Methods

#### get_version_api()

**Required**: Returns a mapping of versions to build callables.

```python
def get_version_api(self) -> dict[str, callable]:
    """
    Returns a mapping of str versions to a callable used for building.

    Each callable receives:
    - build_dir: str - Directory for intermediate artifacts
    - build_data: dict - Data modified by build hooks

    Returns: Absolute path to artifact
    """
    return {
        '1.0.0': self.build_wheel_for_version,
    }

def build_wheel_for_version(self, build_dir: str, build_data: dict) -> str:
    # Build implementation
    artifact_path = ...
    return artifact_path
```

#### get_default_versions()

**Optional**: Specifies which versions build when user doesn't explicitly request any.

```python
def get_default_versions(self) -> list[str]:
    """
    Returns list of versions to build by default.
    If not overridden, defaults to all available versions.
    """
    return ['1.0.0']
```

#### clean()

**Optional**: Handles cleanup before builds when `--clean` flag is used.

```python
def clean(self, build_dir: str, build_data: dict) -> None:
    """
    Clean up temporary or intermediate build artifacts.
    """
    import shutil
    shutil.rmtree(build_dir, ignore_errors=True)
```

#### get_default_build_data()

**Optional**: Provides initial build data that build hooks can modify.

```python
def get_default_build_data(self) -> dict[str, any]:
    """
    Returns mapping of data that can be modified by build hooks.
    Common keys: artifacts, force_include
    """
    return {
        'artifacts': [],
        'force_include': {},
    }
```

## Configuration Access

### build_config

Access global build settings from `[tool.hatch.build]`:

```python
@property
def build_config(self) -> dict:
    # Returns [tool.hatch.build] section
    pass
```

### target_config

Access builder-specific settings from `[tool.hatch.build.targets.<PLUGIN_NAME>]`:

```python
@property
def target_config(self) -> dict:
    # Returns [tool.hatch.build.targets.special] section
    pass
```

### root

Project root directory:

```python
@property
def root(self) -> str:
    # Project directory path
    pass
```

### app

Hatch application instance for advanced integrations:

```python
@property
def app(self) -> Application:
    # Access to Hatch application context
    pass
```

## File Processing

### recurse_included_files()

Yields files that should be distributed:

```python
def recurse_included_files(self) -> Generator[IncludedFile, None, None]:
    """
    Yields IncludedFile objects for each distributable file.

    Each IncludedFile has:
    - path: str - Absolute path to file
    - relative_path: str - Path relative to project root
    - distribution_path: str - Path in distributed artifact
    """
    for included_file in super().recurse_included_files():
        # Filter, process, or yield files
        yield included_file
```

## Build Data

Build hooks can modify build data to influence builder behavior:

```python
def initialize(self, version: str, build_data: dict):
    """
    Hooks can modify:
    - artifacts: List[str] - Patterns for extra artifacts (append-only)
    - force_include: Dict[str, str] - Forced inclusion mappings
    - build_hooks: Immutable sequence of hook names
    """
    build_data['artifacts'].append('extra_pattern')
```

## Official Builders

### wheel

Builds standard Python wheels (`.whl` format) per [PEP 427](https://peps.python.org/pep-0427/).

Configuration:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/hatchling"]
```

Key options:

- `packages` - Python packages to include
- `py-api` - Python version tag (e.g., `cp311`)
- `strict-naming` - Enforce strict wheel naming
- `force-include` - Map of forced inclusion paths
- `data` - Shared data directory mapping
- `scripts` - Shared scripts directory mapping

### sdist

Builds source distributions (`.tar.gz` format) per [PEP 427](https://peps.python.org/pep-0427/).

Configuration:

```toml
[tool.hatch.build.targets.sdist]
include = ["src/"]
exclude = ["tests/"]
```

Key options:

- `include` - Patterns to include
- `exclude` - Patterns to exclude
- `strict-naming` - Enforce strict naming

## Third-Party Builders

### Custom Builders

Implement `BuilderInterface` for specialized formats:

```python
from hatchling.builders.plugin.interface import BuilderInterface

class LambdaBuilder(BuilderInterface):
    PLUGIN_NAME = 'aws-lambda'

    def get_version_api(self) -> dict[str, callable]:
        return {
            'default': self.build_lambda,
        }

    def build_lambda(self, build_dir: str, build_data: dict) -> str:
        # Create AWS Lambda zip package
        return artifact_path
```

### Known Third-Party Builders

- **hatch-aws-publisher** - AWS Lambda deployment packages
- **hatch-containers** - Container image builders (Docker, OCI)
- **scikit-build-core** (hatchling plugin) - C/C++/Fortran extension building
- **python-binaries-app** - Standalone executable applications

## Example: Custom Builder Implementation

```python
import os
from pathlib import Path
from hatchling.builders.plugin.interface import BuilderInterface

class ZipBuilder(BuilderInterface):
    PLUGIN_NAME = 'zip'

    def get_version_api(self) -> dict[str, callable]:
        return {'default': self.build_zip}

    def get_default_versions(self) -> list[str]:
        return ['default']

    def get_default_build_data(self) -> dict:
        return {'artifacts': [], 'force_include': {}}

    def clean(self, build_dir: str, build_data: dict) -> None:
        import shutil
        shutil.rmtree(build_dir, ignore_errors=True)

    def build_zip(self, build_dir: str, build_data: dict) -> str:
        import zipfile

        zip_path = os.path.join(build_dir, 'archive.zip')

        with zipfile.ZipFile(zip_path, 'w') as zf:
            for included_file in self.recurse_included_files():
                zf.write(
                    included_file.path,
                    arcname=included_file.distribution_path,
                )

        return zip_path
```

## Configuration Examples

### Multi-Version Building

```toml
[tool.hatch.build.targets.wheel]
versions = ["cp39", "cp310", "cp311"]
```

### Conditional Builders

```toml
[build-system]
requires = ["hatchling", "hatch-custom-builder"]

[tool.hatch.build.targets.custom]
# Custom builder configuration
```

### Build Hooks with Builders

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
# Hook configuration specific to wheel builder
```

## Best Practices

1. **Validate Configuration**: Check target_config during initialization
2. **Handle Errors Gracefully**: Raise descriptive exceptions for user debugging
3. **Respect Build Hooks**: Allow hooks to modify build_data
4. **Use Absolute Paths**: Always return absolute artifact paths
5. **Clean Up**: Implement clean() to remove temporary files
6. **Follow Naming Conventions**: Use descriptive PLUGIN_NAME values
7. **Document Configuration**: Provide clear examples in plugin documentation

## See Also

- `build-hook-plugins.md` - Customize build process
- `index.md` - Core plugin architecture and concepts
- `metadata-hook-plugins.md` - Dynamic metadata generation
