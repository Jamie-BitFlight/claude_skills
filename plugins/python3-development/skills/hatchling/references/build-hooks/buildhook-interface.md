---
category: Hatchling Build System
topics: [buildhook-interface, api-reference, hook-methods, hook-properties]
related: [custom-build-hooks.md, build-data.md, hook-dependencies.md]
---

# BuildHookInterface Reference

`BuildHookInterface` is the base class for all build hooks. When helping users write custom hooks, reference this documentation to guide them through the interface properties and methods they can use to modify the build process.

## Interface Overview

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class MyBuildHook(BuildHookInterface):
    PLUGIN_NAME = "my-hook"  # For third-party hooks only

    def dependencies(self) -> list[str]:
        """Return extra dependencies needed for this hook"""
        return []

    def clean(self, versions: list[str]) -> None:
        """Called during clean operation"""
        pass

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Called before each build"""
        pass

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        """Called after each build"""
        pass
```

## Constructor

The hook is instantiated with the following parameters:

```python
def __init__(
    self,
    root: str,                      # Project root directory
    config: dict[str, Any],         # Hook configuration
    build_config: BuilderConfig,    # Builder configuration
    metadata: ProjectMetadata,      # Project metadata
    directory: str,                 # Build directory
    target_name: str,               # Build target name (wheel, sdist, etc.)
    app: Application | None = None, # Hatch application instance
) -> None:
```

You typically don't need to call `__init__` directly; Hatchling handles instantiation.

## Properties

### `root: str`

The root of the project tree (project directory path).

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Generate file in project root
    generated_file = os.path.join(self.root, "generated.py")
    with open(generated_file, 'w') as f:
        f.write("# Generated file\n")
```

### `config: dict[str, Any]`

The cumulative hook configuration from `pyproject.toml` or `hatch.toml`.

This includes both global and target-specific configuration merged together.

```toml
[tool.hatch.build.hooks.custom]
output-dir = "build"
verbose = true
```

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    output_dir = self.config.get('output-dir', 'dist')
    verbose = self.config.get('verbose', False)
    if verbose:
        print(f"Output directory: {output_dir}")
```

### `build_config: BuilderConfig`

An instance of `BuilderConfig` containing the builder configuration. Use this to access builder-specific settings.

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Access builder-specific configuration
    targets = self.build_config.get('targets', {})
```

### `directory: str`

The build directory where artifacts are created.

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Create directory for build artifacts
    artifact_dir = os.path.join(self.directory, 'artifacts')
    os.makedirs(artifact_dir, exist_ok=True)
```

### `target_name: str`

The plugin name of the build target (e.g., `wheel`, `sdist`, `custom`).

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    if self.target_name == 'wheel':
        # Wheel-specific logic
        print("Building wheel")
    elif self.target_name == 'sdist':
        # Sdist-specific logic
        print("Building source distribution")
```

### `app: Application`

An instance of the Hatch `Application` object. Lazy-loaded on first access.

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Access Hatch application utilities
    app = self.app
    # Use app for logging, configuration, etc.
```

### `metadata: ProjectMetadata`

Project metadata from `pyproject.toml`. Undocumented property, use with caution.

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Access project metadata
    name = self.metadata.config.get('name', 'unknown')
    version_config = self.metadata.config.get('version', '')
```

## Methods

### `dependencies() -> list[str]`

Returns a list of extra dependencies that must be installed before the build.

**Important restrictions**:

- The hook dependency itself cannot be dynamic (must be in `build-system.requires`)
- Imports requiring these dependencies must be evaluated lazily (inside methods)
- Used by third-party hooks to declare their own dependencies

```python
def dependencies(self) -> list[str]:
    """Declare that this hook needs Cython"""
    return ["cython>=0.29"]
```

```toml
# Configuration for a third-party hook
[build-system]
requires = ["hatchling", "my-hook-plugin"]

[tool.hatch.build.hooks.my-hook]
dependencies = ["cython"]  # Extra dependencies for the hook
```

### `clean(versions: list[str]) -> None`

Called before the build process when the `-c`/`--clean` flag is passed to `hatch build` or when running `hatch clean`.

Used to remove artifacts created by the hook in previous builds.

```python
def clean(self, versions: list[str]) -> None:
    """Remove previously generated files"""
    generated_dir = os.path.join(self.root, 'generated')
    if os.path.exists(generated_dir):
        shutil.rmtree(generated_dir)
```

**Parameters**:

- `versions`: List of versions being cleaned (from build configuration)

### `initialize(version: str, build_data: dict[str, Any]) -> None`

Called immediately before each build. Modifications to `build_data` will be seen by the build target.

**Purpose**: Prepare for the build, generate files, modify build configuration.

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Generate source files
    self.generate_source_code(version)

    # Add generated files to artifacts
    build_data['artifacts'].append('generated/**/*.py')

    # Add forced inclusions
    build_data['force_include']['generated'] = 'generated'
```

**Parameters**:

- `version`: The version being built (from multiple versions config, if applicable)
- `build_data`: Mutable dictionary for modifying build behavior

**Cannot access**:

- Generated artifact paths (not created yet)
- Final build results

### `finalize(version: str, build_data: dict[str, Any], artifact_path: str) -> None`

Called immediately after each build. Receives the path to the generated artifact.

**Skipped if**: `--hooks-only` flag is passed to the build command.

**Purpose**: Post-process artifacts, verify build output, clean up temporary files.

```python
def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
    # artifact_path is the actual built artifact (wheel, tar.gz, etc.)
    print(f"Built artifact: {artifact_path}")

    # Verify the artifact
    self.verify_artifact(artifact_path)

    # Sign the artifact
    self.sign_artifact(artifact_path)
```

**Parameters**:

- `version`: The version being built
- `build_data`: Final build data reflecting any modifications by the build target
- `artifact_path`: Path to the built artifact (wheel, sdist, etc.)

**Cannot**:

- Modify `build_data` (too late, build already completed)
- Modify build behavior (build already happened)

## Build Data Structure

Build data is a mutable dictionary that hooks can modify to influence build behavior:

```python
{
    'artifacts': [         # Extra artifacts to include
        '*.so',
        '*.dll',
        'generated/**/*.py'
    ],
    'force_include': {     # Forced file inclusions
        '/path/to/lib.so': 'lib/lib.so',
        'docs': 'docs'
    },
    'build_hooks': (       # Immutable tuple of hook names in execution order
        'hook1',
        'hook2',
        'hook3'
    )
}
```

### Working with Build Data

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # Add artifacts (files to include in build)
    if 'artifacts' not in build_data:
        build_data['artifacts'] = []
    build_data['artifacts'].append('generated/*.py')

    # Add forced inclusions (map source to destination)
    if 'force_include' not in build_data:
        build_data['force_include'] = {}
    build_data['force_include']['/absolute/path/to/lib.so'] = 'mylib/lib.so'

    # Read hook execution order
    hooks = build_data['build_hooks']  # Immutable tuple
    if 'previous-hook' in hooks:
        # Can depend on earlier hooks' modifications
        pass
```

## Target-Specific Methods

Hooks can adjust behavior based on the build target:

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    if self.target_name == 'wheel':
        # Wheel-specific setup
        self.compile_extensions()
    elif self.target_name == 'sdist':
        # Sdist-specific setup
        self.include_source_templates()
```

## Accessing Configuration

Hooks access their configuration through `self.config`:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
output-dir = "dist"
include-patterns = ["*.py", "*.so"]
```

```python
class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        # Access hook-specific configuration
        output_dir = self.config.get('output-dir', 'dist')
        patterns = self.config.get('include-patterns', [])

        # Use configuration
        for pattern in patterns:
            build_data['artifacts'].append(pattern)
```

## Raising Exceptions

Hooks can raise exceptions to signal errors:

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    if not self.validate_environment():
        raise RuntimeError(
            f"Missing required tool: {self.required_tool}"
        )
```

The build will fail if the hook raises an exception.

## Example: Complete Custom Hook

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["jinja2>=2.11"]

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        # Import here to avoid requiring jinja2 if hook is disabled
        from jinja2 import Template

        # Generate files
        template_path = os.path.join(self.root, 'templates', 'version.j2')
        output_path = os.path.join(self.root, 'src', 'version.py')

        with open(template_path) as f:
            template = Template(f.read())

        output = template.render(version=version)

        with open(output_path, 'w') as f:
            f.write(output)

        # Include in build
        build_data['artifacts'].append('src/version.py')

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        print(f"Built {artifact_path} successfully")
```

## Related Topics

- `custom-build-hooks.md` - Writing custom hooks
- `build-data.md` - Understanding and using build data
- `hook-dependencies.md` - Declaring hook dependencies
