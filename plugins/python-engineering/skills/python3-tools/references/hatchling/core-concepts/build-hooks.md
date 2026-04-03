---
category: core-concepts
topics: [build-hooks, extensibility, customization, patterns]
related: [minimal-philosophy.md, version-management.md, development-vs-distribution.md]
---

# Build Hook Patterns

## Overview

When helping users extend Hatchling with custom build logic, reference this document to understand how build hooks work as extensions that run during the build process to perform custom operations, enabling Hatchling to handle complex build scenarios without requiring custom build backends.

**Source:** [Hatch Build Hook Plugins Reference](https://hatch.pypa.io/1.13/plugins/build-hook/reference/) [Custom Build Hook Documentation](https://hatch.pypa.io/latest/plugins/build-hook/custom/)

## What Are Build Hooks?

### Definition

Build hooks are Python code that executes at specific stages of the build process:

1. **Initialization (initialize):** Runs before each build
2. **Finalization (finalize):** Runs after each build

### When to Use

Build hooks are appropriate for:

- Generating source files during build
- Compiling extensions (C, C++, Rust)
- Processing non-Python files
- Modifying wheel metadata
- Running build-time scripts

### When NOT to Use

Build hooks are not appropriate for:

- Installing build dependencies (use `[build-system] requires`)
- Modifying runtime behavior (that's application code)
- Build configuration that fits patterns (use Hatchling config instead)
- Simple file inclusion/exclusion (use `include`/`exclude` instead)

## Hook Interface

### BuildHookInterface

All build hooks inherit from `BuildHookInterface`:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "my-hook"

    def initialize(self, version, build_data):
        # Run before build
        pass

    def finalize(self, version, build_data):
        # Run after build
        pass
```

### Parameters

**initialize(version, build_data)**

- `version`: The version being built
- `build_data`: Dictionary for modifying build output
  - `build_data['artifacts']`: Paths to create/modify
  - `build_data['force_include']`: Files to force into build
  - `build_data['infer_tag']`: Tag inference for wheels

**finalize(version, build_data)**

- Same parameters
- Runs after build is written

### Build Data

Build hooks communicate with the builder via `build_data`:

```python
def initialize(self, version, build_data):
    # Declare artifacts to create
    build_data['artifacts'] = {
        'src/package/generated.py': 'generated.py'
    }

    # Force include files
    build_data['force_include'] = {
        'data/resource.dat': 'package/data/resource.dat'
    }

    # Infer platform tag for wheels
    build_data['infer_tag'] = True
```

## Hook Types

### 1. Custom Hooks

Custom Python classes inheriting BuildHookInterface.

**Configuration:**

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

**Example:**

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Generate files
        with open('src/package/__version__.py', 'w') as f:
            f.write(f'__version__ = "{version}"\n')

        build_data['force_include'] = {
            'src/package/__version__.py': 'package/__version__.py'
        }
```

### 2. Third-Party Hooks

Community-provided build hooks for specific needs.

**Common Examples:**

- **hatch-cython:** Compile Cython extensions
- **hatch-mypyc:** Compile with Mypyc for performance
- **scikit-build-core:** Build C/C++/Rust extensions with CMake
- **hatch-jupyter-builder:** Build Jupyter Lab extensions
- **hatch-gettext:** Compile GNU gettext translations

**Configuration:**

```toml
[build-system]
requires = ["hatchling", "scikit-build-core"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.scikit-build]
experimental = true
```

## Common Hook Patterns

### Pattern 1: Generate Version File

**Problem:** Want version in single location, available at runtime.

**Solution:**

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class VersionBuildHook(BuildHookInterface):
    PLUGIN_NAME = "version"

    def initialize(self, version, build_data):
        # Create version file
        version_file = self.root / "src" / "package" / "_version.py"
        version_file.write_text(f'__version__ = "{version}"\n')

        # Include in wheel
        build_data['force_include'] = {
            str(version_file): "package/_version.py"
        }
```

**Configuration:**

```toml
[tool.hatch.version]
path = "src/package/__init__.py"

[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

### Pattern 2: Compile C Extensions

**Problem:** Need to compile C code into extension modules.

**Solution:** Use scikit-build-core hook:

```toml
[build-system]
requires = ["hatchling", "scikit-build-core"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.scikit-build]
experimental = true

[tool.scikit-build]
cmake.build-type = "Release"
```

### Pattern 3: Copy Non-Python Files

**Problem:** Package has data files in non-standard location.

**Solution:**

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from pathlib import Path

class DataFilesBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Copy data files into package
        data_dir = self.root / "data"
        build_data['force_include'] = {}

        for data_file in data_dir.glob("**/*"):
            if data_file.is_file():
                rel_path = data_file.relative_to(self.root)
                build_data['force_include'][str(rel_path)] = f"package/data/{data_file.name}"
```

**Configuration:**

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

### Pattern 4: Modify Metadata

**Problem:** Need to set platform-specific wheel tags.

**Solution:**

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class PlatformTagBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Mark wheel as platform-specific
        build_data['infer_tag'] = True
```

## Lifecycle and Execution

### Build Process with Hooks

<eg>
1. Load configuration (pyproject.toml)
2. Discover hooks for this target
3. FOR EACH VERSION:
   a. Call hook.initialize()
   b. Build wheel/sdist
   c. Call hook.finalize()
4. Output built packages
</eg>

### Hook Execution Order

Multiple hooks execute in order:

```toml
[tool.hatch.build.targets.wheel.hooks.hook1]
# Runs first

[tool.hatch.build.targets.wheel.hooks.hook2]
# Runs second

[tool.hatch.build.targets.wheel.hooks.hook3]
# Runs third
```

### Error Handling

Hooks can raise exceptions to fail builds:

```python
class ValidatingHook(BuildHookInterface):
    def initialize(self, version, build_data):
        config_file = self.root / "config.toml"
        if not config_file.exists():
            raise FileNotFoundError(f"Required {config_file} not found")
```

## Hook Configuration

### Parameters

Hooks can accept configuration parameters:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
param1 = "value1"
param2 = 123
```

Access in hook:

```python
class ConfigurableHook(BuildHookInterface):
    def initialize(self, version, build_data):
        param1 = self.config.get("param1")
        param2 = self.config.get("param2", 0)
```

### Global Configuration

Set hook configuration for all targets:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
shared = "value"

# Override per target
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
specific = "to-wheel"
```

## Best Practices

### 1. Keep Hooks Simple

Hooks should do one thing well:

```python
# Good: Single responsibility
class GenerateVersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Generate version file only
        self._write_version_file(version)
```

### 2. Use Hook Name Descriptively

```python
class VersionBuildHook(BuildHookInterface):
    PLUGIN_NAME = "generate-version"  # Descriptive
```

### 3. Document Hook Purpose

```python
class VersionBuildHook(BuildHookInterface):
    """Generate version file from build version.

    Creates src/package/_version.py with __version__
    based on the build version, making it available
    to the package at runtime.
    """
    PLUGIN_NAME = "generate-version"
```

### 4. Fail Early

Validate conditions at initialization:

```python
def initialize(self, version, build_data):
    required_file = self.root / "VERSION"
    if not required_file.exists():
        raise FileNotFoundError(f"{required_file} required for build")
```

### 5. Use build_data Correctly

Only modify data structures hook is designed to modify:

```python
def initialize(self, version, build_data):
    # Correct: Modify expected fields
    build_data['force_include'] = {...}

    # Wrong: Don't add arbitrary keys
    # build_data['custom_key'] = value
```

## Common Gotchas

### Gotcha 1: Relative Paths

Always use absolute paths via `self.root`:

```python
# Wrong: Relative to working directory
open('src/file.py', 'w')

# Correct: Relative to project root
version_file = self.root / 'src' / 'file.py'
version_file.write_text('...')
```

### Gotcha 2: Force Include Not Auto-Detected

Files created by hooks must be explicitly included:

```python
def initialize(self, version, build_data):
    # Create file
    output_file = self.root / 'src' / 'generated.py'
    output_file.write_text('# generated')

    # Must force include
    build_data['force_include'] = {
        str(output_file): 'package/generated.py'
    }
```

### Gotcha 3: Hook Runs for Every Version

If building multiple versions, hook runs for each:

```toml
[tool.hatch.version]
path = "src/package/__init__.py"
# If building both current and previous version,
# hook initialize() runs twice
```

### Gotcha 4: Different Hooks per Target

Wheel and sdist can have different hooks:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"

[tool.hatch.build.targets.sdist.hooks.custom]
# Different hook or configuration
path = "hatch_build_sdist.py"
```

## Migration from setuptools

### setuptools Custom Commands

Old way (setup.py):

```python
from setuptools import setup
from setuptools.command.build_py import build_py

class custom_build_py(build_py):
    def run(self):
        self.generate_version()
        super().run()

    def generate_version(self):
        # Generate version file

setup(
    cmdclass={'build_py': custom_build_py}
)
```

New way (Hatchling):

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class VersionBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Generate version file
```

Configuration:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

## Key Takeaways

1. **Hooks execute at build stages** (initialize/finalize)
2. **Use build_data to modify build output** (force_include, artifacts, etc.)
3. **Custom hooks inherit BuildHookInterface** and implement initialize/finalize
4. **Third-party hooks** available for common needs (Cython, CMake, etc.)
5. **Keep hooks simple** - single responsibility
6. **Hooks run for each version** being built
7. **Different hooks per target** (wheel vs sdist) if needed

## References

- [Hatch Build Hook Plugins Reference](https://hatch.pypa.io/1.13/plugins/build-hook/reference/)
- [Custom Build Hook Documentation](https://hatch.pypa.io/latest/plugins/build-hook/custom/)
- [BuildHookInterface Source](https://github.com/pypa/hatch/blob/master/backend/src/hatchling/builders/hooks/plugin/interface.py)
- [scikit-build-core Hatchling Plugin](https://scikit-build-core.readthedocs.io/en/stable/plugins/hatchling.html)
