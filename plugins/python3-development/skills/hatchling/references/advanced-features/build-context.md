---
category: Advanced Build Features
topics: [build-context, build-hooks, hook-interface, environment-variables, platform-detection]
related: [build-data-passing.md, dynamic-dependencies.md, force-include.md]
---

# Build Context

When helping users write sophisticated build hooks, guide them to understand how the build context provides essential information about the build environment, project configuration, and build parameters. This enables hooks to make intelligent decisions based on the current build state.

## Overview

Build context information is passed to hooks through the `BuildHookInterface` class. Reference this to show users the properties and methods available to access build configuration and environment details.

## BuildHookInterface Properties

### directory Property

The project root directory where the build is occurring:

```python
class ContextAwareHook(BuildHookInterface):
    def initialize(self, version, build_data):
        project_root = self.directory
        # Access files relative to project root
        config = os.path.join(project_root, 'build_config.json')
```

Type: `str` (absolute filesystem path)

### root Property

The root directory of the build. In most cases identical to `directory`:

```python
def initialize(self, version, build_data):
    root = self.root
    # Same as self.directory in standard builds
    assert self.root == self.directory
```

Type: `str` (absolute filesystem path)

## BuilderConfig Access

Hooks receive access to builder configuration through the context:

```python
class ConfigInspectionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Access build configuration
        # Available through self when properly initialized
        pass
```

Configuration includes:

- Target type (wheel, sdist, or custom)
- Package metadata
- Build options
- Source directories
- Artifact patterns

## Environment Access

### Working Directory

Always the project root:

```python
def initialize(self, version, build_data):
    # Current working directory is project root
    cwd = os.getcwd()
    assert cwd == self.directory
```

### Environment Variables

Access to all environment variables from build shell:

```python
import os

def initialize(self, version, build_data):
    # Read custom build variables
    build_variant = os.getenv('BUILD_VARIANT', 'release')
    include_debug = os.getenv('DEBUG_BUILD', '0') == '1'

    if include_debug:
        build_data['artifacts']['wheel'].append('mypackage/_debug.py')
```

### System Information

```python
import sys
import platform

def initialize(self, version, build_data):
    python_version = sys.version_info
    platform_name = platform.system()

    # Conditional behavior based on platform
    if platform_name == 'Windows':
        build_data['force_include']['windows/lib.dll'] = 'mypackage/lib.dll'
```

## Version Parameter

The `version` passed to hook methods is determined from:

1. `pyproject.toml` static version
2. Build hook's own `set_version()` method
3. Dynamic versioning configuration

```python
def initialize(self, version, build_data):
    # version is a string like '1.2.3' or '1.2.3.dev0'
    print(f"Building version: {version}")

    # Use version in generated code
    with open('mypackage/_version.py', 'w') as f:
        f.write(f'__version__ = "{version}"\n')
```

## Detecting Build Target

Determine which target is being built (wheel, sdist, etc.):

```python
class TargetAwareHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # build_data contains target-specific information
        # Hooks are called once per target
        pass

    def finalize(self, version, build_data, artifact):
        # The 'artifact' parameter indicates build result path
        # Use this to detect what was built
        if artifact.endswith('.whl'):
            print("Built a wheel")
        else:
            print("Built a source distribution")
```

## File System Access

Hooks have full filesystem access relative to project root:

```python
class FileSystemHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Read project configuration
        with open(os.path.join(self.directory, 'myconfig.json')) as f:
            config = json.load(f)

        # Create directories
        os.makedirs('build/artifacts', exist_ok=True)

        # Write generated files
        with open('mypackage/_generated.py', 'w') as f:
            f.write(f'CONFIG = {config!r}\n')

        # Add to distribution
        build_data['artifacts']['wheel'].append('mypackage/_generated.py')
```

## Hook Execution Context

### Initialization Context

During `initialize()`:

```python
def initialize(self, version, build_data):
    # Working directory: project root
    # Files: readable and writable
    # Context: early build phase - modifications affect build output
    # Can: generate files, read configuration, modify build_data
```

### Finalization Context

During `finalize()`:

```python
def finalize(self, version, build_data, artifact):
    # Working directory: project root
    # Files: most created; artifact file finalized
    # Context: after build completion
    # Can: inspect what was built, clean up temporary files
    # Should not: modify build_data in ways that affect current artifact
```

### Clean Context

During `clean()`:

```python
def clean(self, version, build_data):
    # Called for 'hatch build --target=wheel -c'
    # Clean up build artifacts
    import shutil
    if os.path.exists('build/generated'):
        shutil.rmtree('build/generated')
```

## Practical Examples

### Reading Build Configuration

```python
import toml

class ConfigAwareHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Read pyproject.toml
        config_path = os.path.join(self.directory, 'pyproject.toml')
        config = toml.load(config_path)

        # Access custom configuration
        build_config = config.get('tool', {}).get('myapp', {})
        include_benchmarks = build_config.get('include_benchmarks', False)

        if include_benchmarks:
            build_data['force_include']['benchmarks'] = 'mypackage/benchmarks'
```

### Conditional Features Based on Environment

```python
class FeatureHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Check for optional build dependencies
        try:
            import cython
            has_cython = True
        except ImportError:
            has_cython = False

        if has_cython:
            # Compile Cython extensions
            build_data['force_include']['dist/compiled.so'] = 'mypackage/compiled.so'
        else:
            # Use pure Python fallback
            build_data['artifacts']['wheel'].append('mypackage/_pure_python.py')
```

### Version Injection

```python
class VersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Create version file with build info
        import datetime

        version_info = {
            'version': version,
            'build_time': datetime.datetime.utcnow().isoformat(),
            'platform': platform.system(),
        }

        with open('mypackage/_build_info.py', 'w') as f:
            f.write(f'BUILD_INFO = {version_info!r}\n')

        build_data['artifacts']['wheel'].append('mypackage/_build_info.py')
```

## Best Practices

- Use `self.directory` instead of hardcoded relative paths
- Access environment variables for build customization
- Check platform/Python version for conditional behavior
- Keep hook logic simple and deterministic
- Document any environment variables your hook uses
- Handle missing files gracefully (check existence before reading)
- Use proper absolute paths for all file operations

## Debugging Context

Print context information for troubleshooting:

```python
import json

class DebugContextHook(BuildHookInterface):
    def initialize(self, version, build_data):
        context_info = {
            'version': version,
            'directory': self.directory,
            'cwd': os.getcwd(),
            'python': sys.version_info,
            'platform': platform.system(),
            'environ': dict(os.environ)
        }

        with open('build/context_debug.json', 'w') as f:
            json.dump(context_info, f, indent=2, default=str)
```

## See Also

- `build-data-passing.md` - Modifying build_data in hooks
- `dynamic-dependencies.md` - Build-time dependencies
- `force-include.md` - Including external files
