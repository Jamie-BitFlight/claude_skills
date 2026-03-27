---
category: Hatchling Build System
topics: [build-data, hook-communication, artifacts, force-include]
related: [buildhook-interface.md, custom-build-hooks.md, hook-data-passing.md]
---

# Build Data

Build data is a mutable dictionary that hooks can inspect and modify to influence build behavior. When helping users write hooks that interact with the build system, reference this documentation to explain how hooks can access and modify build data to control artifact inclusion and file handling.

## Overview

Build data allows hooks to:

- Add extra artifacts to include in the distribution
- Force inclusion of files from anywhere on the filesystem
- Query which hooks are running
- Communicate modifications between hooks

## Build Data Structure

The build data dictionary has this structure:

```python
{
    'artifacts': [
        'pattern1/**/*.so',
        'pattern2/**/*.py',
    ],
    'force_include': {
        'source/path': 'destination/path',
        '/absolute/path/file.so': 'lib/file.so',
    },
    'build_hooks': ('hook1', 'hook2', 'hook3'),
    # Target-specific fields may be added by the build target
}
```

## Standard Fields

### `artifacts`

A list of extra artifact patterns to include in the distribution.

- **Type**: `list[str]`
- **Purpose**: Include generated or external files in the build
- **Patterns**: Git-style glob patterns
- **Append-only**: Should append to existing list, not replace

**Usage**:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Ensure the field exists
    if 'artifacts' not in build_data:
        build_data['artifacts'] = []

    # Add patterns
    build_data['artifacts'].append('generated/**/*.py')
    build_data['artifacts'].append('compiled/**/*.so')
```

**What it does**: Files matching these patterns will be included in the wheel or sdist, regardless of VCS ignore rules or other exclusions. Artifacts are not subject to the `exclude` option.

**Negation syntax**: Use `!` to exclude specific patterns:

```python
build_data['artifacts'].extend([
    '*.so',      # Include all .so files
    '!/tmp/*.so' # Except those in /tmp
])
```

### `force_include`

A dictionary mapping source paths to destination paths in the distribution.

- **Type**: `dict[str, str]`
- **Purpose**: Include specific files from anywhere on the filesystem
- **Keys**: Source paths (absolute or relative to project root)
- **Values**: Destination paths in the distribution
- **Override**: Takes precedence over other file selection options

**Usage**:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Ensure the field exists
    if 'force_include' not in build_data:
        build_data['force_include'] = {}

    # Map single file
    build_data['force_include']['/path/to/lib.so'] = 'mylib/lib.so'

    # Map directory (recursive inclusion)
    build_data['force_include']['/external/assets'] = 'assets'

    # Relative path from project root
    build_data['force_include']['../sibling-project/lib.a'] = 'libs/lib.a'
```

**What it does**: Files specified here will be included exactly as mapped, overriding any exclude patterns or VCS ignore rules.

**Important notes**:

- Directory source paths will recursively include all contents
- Files must be mapped to specific paths, not directories
- Use `/` (forward slash) to map directory contents to the root
- Source paths that don't exist will raise an error

**Example: Map directory contents to root**:

```python
build_data['force_include']['dist'] = '/'
```

This includes all files from the `dist` directory at the package root.

### `build_hooks`

An immutable tuple of hook names in execution order.

- **Type**: `tuple[str, ...]`
- **Purpose**: Discover which hooks are configured and their execution order
- **Immutable**: Cannot be modified
- **Read-only**: Use to query hook execution sequence

**Usage**:

```python
def initialize(self, version: str, build_data: dict) -> None:
    hooks = build_data['build_hooks']

    # Check if a specific hook already ran
    if 'custom' in hooks:
        custom_index = hooks.index('custom')
        my_index = hooks.index('my-hook')

        if custom_index < my_index:
            # Custom hook ran before us, use its output
            self.process_custom_output()
```

## Target-Specific Fields

Build targets may add their own fields to build data. These vary by target type.

### Wheel Target Fields

The wheel target may add:

- `wheels_version`: The version of the wheel being built

### Sdist Target Fields

The sdist target may add fields related to source distribution specific behavior.

Check the build target documentation for target-specific fields.

## Modifying Build Data

### Adding Artifacts

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Ensure field exists (safe approach)
    if 'artifacts' not in build_data:
        build_data['artifacts'] = []

    # Add pattern
    build_data['artifacts'].append('generated/**/*.py')

    # Add multiple patterns
    build_data['artifacts'].extend([
        'compiled/**/*.so',
        'resources/**/*.json',
    ])
```

### Adding Forced Inclusions

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Ensure field exists
    if 'force_include' not in build_data:
        build_data['force_include'] = {}

    # Single file
    build_data['force_include']['/path/to/lib.so'] = 'lib/lib.so'

    # Update with multiple files
    build_data['force_include'].update({
        '/path/to/file1': 'dest1',
        '/path/to/file2': 'dest2',
    })
```

### Safe Field Access

Always check if fields exist before using them:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Safe: Check before accessing
    if 'artifacts' in build_data:
        artifacts = build_data['artifacts']
    else:
        artifacts = []

    # Add new artifacts
    artifacts.append('new_pattern/**/*.py')
    build_data['artifacts'] = artifacts
```

## Common Patterns

### Conditional Modifications Based on Target

```python
def initialize(self, version: str, build_data: dict) -> None:
    if self.target_name == 'wheel':
        # Add compiled extensions for wheels
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('**/*.so')

    elif self.target_name == 'sdist':
        # Add source templates for sdist
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('templates/**/*')
```

### Depending on Previous Hook's Output

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Check what hooks have already run
    previous_hooks = build_data.get('build_hooks', ())

    if 'generate-code' in previous_hooks:
        # Previous hook generated code, include it
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('generated/**/*.py')
```

### Including External Libraries

When you need to include compiled libraries or dependencies from external sources:

```python
import os
from pathlib import Path

def initialize(self, version: str, build_data: dict) -> None:
    if 'force_include' not in build_data:
        build_data['force_include'] = {}

    # Find and include all .so files from external directory
    external_dir = os.path.join(self.root, '../external/libs')
    if os.path.exists(external_dir):
        for lib_file in Path(external_dir).glob('**/*.so'):
            # Map to mylib directory in distribution
            destination = f'mylib/{lib_file.name}'
            build_data['force_include'][str(lib_file)] = destination
```

### Building Multi-Level Directory Structure

```python
def initialize(self, version: str, build_data: dict) -> None:
    if 'force_include' not in build_data:
        build_data['force_include'] = {}

    # Create nested directory structure
    build_data['force_include'].update({
        'resources/icons': 'mylib/resources/icons',
        'resources/themes': 'mylib/resources/themes',
        'resources/data': 'mylib/resources/data',
    })
```

## Artifacts vs Force Include

Both `artifacts` and `force_include` add files to the build, but they work differently:

| Aspect        | Artifacts              | Force Include     |
| ------------- | ---------------------- | ----------------- |
| **Source**    | Files in project       | Files anywhere    |
| **Pattern**   | Git-style globs        | Exact paths       |
| **Exclusion** | Not subject to exclude | Overrides exclude |
| **Use case**  | Generated files        | External files    |

**Use `artifacts` for**: Files generated by hooks within the project **Use `force_include` for**: Files from external sources or specific absolute paths

## Observing Build Data in Finalization

The `finalize()` method receives the final build data after the target has potentially modified it:

```python
def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
    # See all artifacts that were actually included
    artifacts = build_data.get('artifacts', [])
    print(f"Included artifacts: {artifacts}")

    # See all forced inclusions
    forced = build_data.get('force_include', {})
    print(f"Forced inclusions: {forced}")

    # Verify the artifact was created
    if os.path.exists(artifact_path):
        size = os.path.getsize(artifact_path)
        print(f"Artifact size: {size} bytes")
```

## Real-World Example: Complete Hook Using Build Data

```python
import os
from pathlib import Path
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Generate files and add them to build"""

        # Generate version file
        generated_dir = os.path.join(self.root, 'generated')
        os.makedirs(generated_dir, exist_ok=True)

        version_file = os.path.join(generated_dir, '__version__.py')
        with open(version_file, 'w') as f:
            f.write(f'__version__ = "{version}"\n')

        # Compile assets (hypothetical)
        self.compile_assets(generated_dir)

        # Add generated files to build
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].extend([
            'generated/**/*.py',
            'generated/**/*.css',
        ])

        # Include external library if on certain target
        if self.target_name == 'wheel':
            if 'force_include' not in build_data:
                build_data['force_include'] = {}

            # External library path (absolute)
            lib_path = os.path.join(self.root, '../external/lib.so')
            build_data['force_include'][lib_path] = 'mylib/lib.so'

    def compile_assets(self, output_dir: str) -> None:
        """Hypothetical asset compilation"""
        # This would be your actual compilation logic
        pass

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Verify build and sign artifact"""
        print(f"Successfully built {os.path.basename(artifact_path)}")
```

## Related Topics

- `buildhook-interface.md` - Hook methods and properties
- `custom-build-hooks.md` - Writing hooks that use build data
- `hook-data-passing.md` - Communication between hooks
