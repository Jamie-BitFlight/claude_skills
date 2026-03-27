---
name: Build Hook Plugins Reference
description: Complete reference for implementing build hook plugins in Hatchling, covering the BuildHookInterface, lifecycle methods (initialize, finalize, clean), configuration patterns, and practical examples.
---

# Build Hook Plugins

Build hooks execute code at specific stages of the build process, enabling customization without creating custom builders.

## Overview

Build hooks provide extension points during package building. Rather than implementing a full builder, hooks modify behavior at key lifecycle stages: before build initialization, after build completion, and cleanup.

## Core Interface: BuildHookInterface

### PLUGIN_NAME

Each hook must define a string identifier:

```python
class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'custom'
```

Users select hooks via configuration:

```toml
[tool.hatch.build.hooks.custom]
# Configuration for this hook

[tool.hatch.build.targets.wheel.hooks.custom]
# Hook configuration specific to wheel target
```

## Lifecycle Methods

### initialize(version, build_data)

**Called**: Immediately before each build for each version.

**Purpose**: Modify build data before the builder executes.

```python
def initialize(self, version: str, build_data: dict) -> None:
    """
    This occurs immediately before each build.

    Any modifications to the build data will be seen by the build target.

    Args:
        version: The version string being built
        build_data: Mutable dictionary of build configuration
    """
    # Example: Add extra artifacts to include
    build_data['artifacts'].append('generated_file.txt')

    # Example: Force include files
    build_data['force_include']['/path/to/file'] = 'dest/file'
```

### finalize(version, build_data, artifact_path)

**Called**: Immediately after each build completes (unless `--hooks-only` flag used).

**Purpose**: Process built artifacts or perform post-build actions.

```python
def finalize(
    self,
    version: str,
    build_data: dict,
    artifact_path: str,
) -> None:
    """
    This occurs immediately after each build.

    The build data will reflect any modifications done by the target.
    This method will not run if the `--hooks-only` flag was passed.

    Args:
        version: The version string that was built
        build_data: Dictionary reflecting target's modifications
        artifact_path: Absolute path to generated artifact
    """
    # Example: Sign or notarize the artifact
    import subprocess
    subprocess.run(['gpg', '--sign', artifact_path])

    # Example: Upload build metadata
    with open(artifact_path + '.sha256', 'w') as f:
        f.write(compute_hash(artifact_path))
```

### clean()

**Called**: Before building when `-c`/`--clean` flag is passed.

**Purpose**: Remove temporary or cached files from previous builds.

```python
def clean(self) -> None:
    """
    Executes before the build process when the -c/--clean flag is used.

    This is useful for removing temporary files or caches from prior builds.
    """
    import shutil
    build_cache = os.path.join(self.root, '.build_cache')
    if os.path.exists(build_cache):
        shutil.rmtree(build_cache)
```

## Build Data

Build data is a dictionary containing configuration that can be modified by hooks:

### Common Keys

```python
{
    'artifacts': [],           # Extra artifact patterns (append-only)
    'force_include': {},       # Mapping: source_path -> dist_path
    'build_hooks': (...),      # Immutable: configured hook names
}
```

### Modifying Build Data

Only `initialize()` should modify build_data; `finalize()` receives read-only data:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # SAFE: Modifying in initialize
    build_data['artifacts'].append('*.pyc')

    # SAFE: Adding to force_include
    build_data['force_include']['/src/generated'] = 'generated/'

    # NOT SAFE: Modifying immutable build_hooks
    # build_data['build_hooks'] = [...]  # Will fail

def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
    # OK to READ build_data
    if 'metadata_hook' in build_data.get('hooks', []):
        pass
    # But modifications won't be used - builder already executed
```

## Configuration & Properties

### PLUGIN_NAME (Class Attribute)

String identifier for user selection:

```python
class VersionBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'version'
```

### root (Property)

Project root directory:

```python
@property
def root(self) -> str:
    """The root of the project tree."""
    return self._root
```

### config (Property)

Hook configuration from `pyproject.toml`:

```python
@property
def config(self) -> dict:
    """Hook configuration from [tool.hatch.build.hooks.<PLUGIN_NAME>]"""
    return self._config
```

### target_config (Property)

Builder-specific configuration:

```python
@property
def target_config(self) -> dict:
    """Configuration from [tool.hatch.build.targets.<TARGET>.hooks.<PLUGIN_NAME>]"""
    return self._target_config
```

### build_config (Property)

Global build configuration:

```python
@property
def build_config(self) -> dict:
    """Configuration from [tool.hatch.build]"""
    return self._build_config
```

## Hook Execution Order

### Global Before Target-Specific

Hooks execute in order:

1. Global hooks from `[tool.hatch.build.hooks.*]`
2. Target-specific hooks from `[tool.hatch.build.targets.<TARGET>.hooks.*]`

### Multiple Hooks

When multiple hooks are configured, each runs in sequence:

```toml
[tool.hatch.build.hooks.hook1]
# Runs first

[tool.hatch.build.hooks.hook2]
# Runs second
```

### Execution Order Control

Hooks execute in configuration order; use `[build.hooks.name]` TOML table order:

```toml
[tool.hatch.build.hooks.version]
[tool.hatch.build.hooks.cython]  # Cython runs after version
[tool.hatch.build.hooks.custom]  # Custom runs after cython
```

## Hook Dependencies

Hooks can declare dependencies required during build:

```python
class CMakeBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'cmake'

    @staticmethod
    def dependencies() -> list[str]:
        """
        Returns list of package names required for building.
        These are added to build-system.requires automatically.
        """
        return ['cmake>=3.15', 'ninja']
```

## Conditional Execution

Control hook execution with `enable-by-default`:

```toml
[tool.hatch.build.hooks.custom]
enable-by-default = false  # Disabled by default

[tool.hatch.build.targets.wheel.hooks.custom]
enable-by-default = true  # Enabled for wheel target
```

## Official Build Hooks

### version

Auto-generates version file during builds.

```toml
[tool.hatch.build.hooks.version]
path = "mypackage/__about__.py"
```

Generates:

```python
# Auto-generated by hatchling
__version__ = "1.2.3"
```

### custom

Enables custom hook implementation via `hatch_build.py`:

```toml
[tool.hatch.build.hooks.custom]
```

Implement in `hatch_build.py`:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomHook(BuildHookInterface):
    PLUGIN_NAME = 'custom'

    def initialize(self, version, build_data):
        # Custom logic
        pass
```

## Third-Party Build Hooks

### Official Plugins

- **hatch-vcs** - Auto-generate version from VCS tags
- **hatch-gradle** - Gradle build integration
- **scikit-build-core** - C/C++/Rust extension building

### Community Hooks

- **hatch-cython** - Cython compilation (.pyx → .c)
- **hatch-mypyc** - MyPyC compilation (.py → .c)
- **hatch-fancy-pypi-readme** - Dynamic README generation
- **hatch-gettext** - Gettext message compilation

## Example: Custom Build Hook

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import os
import subprocess

class ProtobufBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'protobuf'

    @staticmethod
    def dependencies():
        return ['protobuf>=3.20']

    def initialize(self, version: str, build_data: dict) -> None:
        """Compile .proto files to Python."""
        proto_dir = os.path.join(self.root, self.config.get('proto_dir', 'proto'))

        if not os.path.exists(proto_dir):
            return

        # Compile protobuf files
        for filename in os.listdir(proto_dir):
            if filename.endswith('.proto'):
                proto_path = os.path.join(proto_dir, filename)
                output_dir = os.path.join(self.root, 'src')

                subprocess.run([
                    'protoc',
                    '--python_out', output_dir,
                    proto_path,
                ], check=True)

        # Ensure generated files are included
        build_data['force_include'][
            os.path.join(output_dir, 'src')
        ] = 'mypackage/'

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Log build completion."""
        self.app.verbose(f'Built artifact: {artifact_path}')
```

## Configuration Examples

### Version Hook

```toml
[tool.hatch.build.hooks.version]
path = "src/mypackage/__version__.py"
pattern = '__version__ = "([^"]+)"'
input-file = "pyproject.toml"
```

### Custom Hook with Options

```toml
[tool.hatch.build.hooks.custom]
proto_dir = "protos"
output_dir = "src/generated"
enable-by-default = true
```

### Target-Specific Hooks

```toml
# Global hook
[tool.hatch.build.hooks.version]

# Only for wheel builds
[tool.hatch.build.targets.wheel.hooks.custom]
option = "wheel-only-value"

# Different config for sdist
[tool.hatch.build.targets.sdist.hooks.custom]
option = "sdist-only-value"
```

## Best Practices

1. **Minimal Side Effects**: Keep initialization lightweight for build performance
2. **Handle Errors**: Raise exceptions with clear messages for debugging
3. **Idempotent**: Ensure hooks can run multiple times safely
4. **Respect Config**: Read options from `config` property
5. **Document Hooks**: Provide clear examples in plugin README
6. **Test Locally**: Use `hatch build --hooks-only` to test hook logic
7. **Version Compatibility**: Check Hatchling version requirements

## Debugging Hooks

### Run Hooks Only

Test hook logic without full build:

```bash
hatch build --hooks-only
```

### Control Finalization

Skip finalization for debugging:

```bash
hatch build --no-finalize  # Hypothetical flag; actual command may vary
```

### Environment Variables

Some hooks support environment variables:

```bash
HATCH_BUILD_HOOKS_ONLY=1 hatch build
```

## See Also

- `builder-plugins.md` - Custom builder implementations
- [BuildHookInterface Reference](https://hatch.pypa.io/latest/plugins/build-hook/reference/)
- [Hatchling Build Hook Documentation](https://hatch.pypa.io/latest/plugins/build-hook/)
- `hatch-vcs-plugin.md` - Example plugin with build hook
