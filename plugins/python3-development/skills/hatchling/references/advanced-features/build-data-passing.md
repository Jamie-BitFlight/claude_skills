---
category: Advanced Build Features
topics: [build-data-passing, build-hooks, hook-interface, artifacts, build-process]
related: [build-context.md, dynamic-dependencies.md, force-include.md]
---

# Build Data Passing

When helping users implement dynamic build behavior, guide them to understand how `build_data` enables communication between custom build hooks and Hatchling's build process. The `build_data` dictionary is the primary mechanism for hooks to influence build behavior.

## Overview

The `build_data` parameter passed to hook methods contains mutable state that the build process reads. Show users how modifications to `build_data` during hook execution affect the final build output.

## Build Data Structure

The `build_data` dictionary contains three main fields:

```python
build_data = {
    'artifacts': {
        'wheel': ['file1.py', 'file2.py'],
        'sdist': ['file1.py', 'file2.py', 'setup.py']
    },
    'force_include': {
        'source/path': 'distribution/path',
        'assets': 'mypackage/assets'
    },
    'build_hooks': ['hook_name_1', 'hook_name_2']
}
```

## Field Descriptions

### artifacts

Maps build targets to lists of files included in that build:

```python
def initialize(self, version, build_data):
    # Inspect included artifacts
    wheel_files = build_data['artifacts']['wheel']
    sdist_files = build_data['artifacts']['sdist']

    # Add custom artifacts
    build_data['artifacts']['wheel'].append('mypackage/_custom.py')
```

Modifications affect what gets included in the final distribution package.

### force_include

Dictionary mapping source filesystem paths to distribution package paths:

```python
def initialize(self, version, build_data):
    # Add dynamically determined includes
    if os.path.exists('dist/compiled'):
        build_data['force_include']['dist/compiled'] = 'mypackage/lib'

    # Include environment-specific resources
    if os.getenv('BUILD_WITH_DOCS'):
        build_data['force_include']['docs/_build/html'] = 'mypackage/docs'
```

### build_hooks

List of build hook names that will be executed:

```python
def initialize(self, version, build_data):
    # Access list of active hooks
    active_hooks = build_data['build_hooks']
    print(f"Running hooks: {', '.join(active_hooks)}")
```

## Hook Execution and Data Access

### initialize() Method

Called when hook is initialized; build_data is mutable:

```python
class DataManipulationHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Modify build data during initialization"""
        # Add generated files to artifacts
        build_data['artifacts']['wheel'].append('mypackage/_generated.py')

        # Include additional resources
        build_data['force_include']['assets'] = 'mypackage/assets'
```

### finalize() Method

Called after build target is complete; modifications affect next builds:

```python
def finalize(self, version, build_data, artifact):
    """Clean up or verify build data after build"""
    # Remove temporary files from artifacts
    temp_files = [f for f in build_data['artifacts']['wheel'] if f.startswith('_tmp_')]
    for temp in temp_files:
        build_data['artifacts']['wheel'].remove(temp)
```

## Hook Dependencies and Data Ordering

When multiple hooks are present, build_data modifications cascade:

```toml
[tool.hatchling.hooks]
custom1 = { path = "hooks/first.py" }
custom2 = { path = "hooks/second.py" }
```

**Execution order**:

1. `custom1.initialize()` modifies `build_data`
2. `custom2.initialize()` receives modified `build_data` and can further modify it
3. Both hooks see each other's modifications during finalize

## Practical Examples

### Conditional File Inclusion

```python
class ConditionalIncludeHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Include files only for specific Python versions
        if sys.version_info >= (3, 10):
            build_data['artifacts']['wheel'].append('mypackage/_py310.py')
        else:
            build_data['artifacts']['wheel'].append('mypackage/_legacy.py')

        # Include docs only if BUILD_WITH_DOCS is set
        if os.getenv('BUILD_WITH_DOCS'):
            build_data['force_include']['docs/_build'] = 'mypackage/docs'
```

### Platform-Specific Artifacts

```python
class PlatformArtifactsHook(BuildHookInterface):
    def initialize(self, version, build_data):
        platform = sys.platform

        if platform == 'win32':
            build_data['force_include']['build/windows/lib.dll'] = 'mypackage/lib.dll'
        elif platform == 'darwin':
            build_data['force_include']['build/macos/lib.dylib'] = 'mypackage/lib.dylib'
        else:  # linux
            build_data['force_include']['build/linux/lib.so'] = 'mypackage/lib.so'
```

### Generated Code Inclusion

```python
class GeneratedCodeHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Ensure generated files exist
        os.makedirs('mypackage/_generated', exist_ok=True)

        # Generate version file
        with open('mypackage/_generated/version.py', 'w') as f:
            f.write(f'__version__ = "{version}"\n')

        # Add to wheel artifacts
        build_data['artifacts']['wheel'].append('mypackage/_generated/version.py')
```

## Build Data Lifecycle

1. **Initialization**: `build_data` structure created with default artifacts
2. **Hook initialize()**: Hooks modify `build_data` for their build target
3. **Build Process**: Build uses current state of `build_data`
4. **Hook finalize()**: Hooks can verify or clean up `build_data`
5. **Artifact Creation**: Final `build_data` state determines what goes in package

## Important Notes

- `build_data` is specific to each build target (wheel vs sdist)
- Modifications in one hook affect all subsequent hooks
- Changes persist through the entire build process
- Check field types before modification (lists for artifacts, dicts for force_include)
- Invalid modifications can cause build failures - validate carefully

## Debugging Build Data

Print build_data contents to understand current state:

```python
import json

class DebugHook(BuildHookInterface):
    def initialize(self, version, build_data):
        print("=== Build Data ===")
        print(json.dumps(build_data, indent=2, default=str))

    def finalize(self, version, build_data, artifact):
        print(f"Final artifacts for {artifact}:")
        print(build_data['artifacts'].get(artifact, []))
```

## See Also

- `force-include.md` - File inclusion mechanism
- `dynamic-dependencies.md` - Build-time dependency specification
- `build-context.md` - Accessing build environment information
