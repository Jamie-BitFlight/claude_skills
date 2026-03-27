---
category: Build System Configuration
topics: [build-hooks, target-specific-hooks, hook-execution, build-customization]
related: [index.md, target-dependencies.md, config-precedence.md]
---

# Target-Specific Hooks Configuration

Configure build hooks to run only for specific build targets, allowing fine-grained control over build behavior.

## Overview

When helping users customize Hatchling build behavior, reference this guide to explain how build hooks can be applied to individual build targets. Hooks execute at specific stages of a target's build process. Target-specific hooks execute after global hooks and are ordered as defined in the configuration.

**Source**: [Hatch Build Configuration - Build Hooks](https://hatch.pypa.io/1.13/config/build/#build-hooks)

## Configuration Syntax

Target hooks are defined within a target's configuration section:

```toml
[tool.hatch.build.targets.<TARGET>.hooks.<HOOK_NAME>]
```

### Example

```toml
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/mypackage/_version.py"
template = '''
__version__ = "{version}"
'''

[tool.hatch.build.targets.wheel.hooks.custom]
# Custom hook configuration

[tool.hatch.build.targets.sdist.hooks.custom]
# Different custom hook for sdist
```

## Hook Execution Order

For each build target, hooks execute in a specific order:

1. Global hooks (defined in `[tool.hatch.build.hooks.*]`) execute first, in definition order
2. Target-specific hooks (defined in `[tool.hatch.build.targets.<TARGET>.hooks.*]`) execute after, in definition order

### Execution Order Example

Given this configuration:

```toml
[tool.hatch.build.hooks.hook1]

[tool.hatch.build.targets.wheel.hooks.hook2]

[tool.hatch.build.hooks.hook3]
```

When building the wheel target, execution order is: `hook1` → `hook3` → `hook2`

**Source**: [Hatch Build Configuration - Order of Execution](https://hatch.pypa.io/1.13/config/build/#order-of-execution)

## Hook Lifecycle Stages

Each hook can participate in three stages of the build process:

### 1. Clean Stage

Triggered by `hatch build -c` or `hatch clean` command:

```python
def clean(self, versions: list[str]) -> None:
    """Remove artifacts before building if -c/--clean flag passed"""
```

### 2. Initialize Stage

Occurs immediately before each build:

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    """
    Modify build_data before the build.
    Changes here are visible to the build target.
    """
```

### 3. Finalize Stage

Occurs immediately after each build (unless `--hooks-only` flag used):

```python
def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
    """
    Post-process after build completes.
    Can see modifications made by the target during build.
    """
```

## Conditional Hook Execution

Control whether hooks run by default:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
enable-by-default = false
```

When disabled by default, enable via environment variable:

```bash
# Enable all hooks
HATCH_BUILD_HOOKS_ENABLE=true hatch build

# Enable specific hook
HATCH_BUILD_HOOK_ENABLE_custom=true hatch build
```

**Source**: [Hatch Build Configuration - Conditional Execution](https://hatch.pypa.io/1.13/config/build/#conditional-execution)

## Available Built-In Hooks

### custom

Allows executing arbitrary Python code:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"  # Optional: specify hook module location
```

### version

Dynamically writes version information:

```toml
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/mypackage/_version.py"
template = '''
__version__ = "{version}"
'''
```

## Hook Dependencies

Hooks can declare additional build-time dependencies:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = [
    "requests>=2.25.0",
    "my-build-tool",
]

# Depend on project's runtime dependencies
require-runtime-dependencies = true

# Depend on specific optional features
require-runtime-features = [
    "feature1",
    "feature2",
]
```

**Constraints**:

- Hook dependency itself must be defined in `build-system.requires`
- Dependencies that are required must be imported lazily in hooks
- For effect, the hook dependency cannot be dynamic

**Source**: [Hatch Build Configuration - Hook Dependencies](https://hatch.pypa.io/1.13/config/build/#hook-dependencies)

## Build Data Modification

Hooks can modify build data to influence target behavior. Standard fields include:

```python
build_data = {
    'artifacts': [],        # List of artifact patterns to include
    'force_include': {},    # Dict of paths to force include in build
    'build_hooks': tuple()  # Immutable sequence of configured hook names
}
```

Always append to `artifacts` rather than replacing:

```python
def initialize(self, version: str, build_data: dict[str, Any]) -> None:
    # CORRECT: Append to existing artifacts
    build_data['artifacts'].append('**/*.so')

    # INCORRECT: Don't replace
    # build_data['artifacts'] = ['**/*.so']
```

**Source**: [Hatch Build Hook Plugins - Build Data](https://hatch.pypa.io/1.13/plugins/build-hook/reference/#build-data)

## Practical Examples

### Example 1: Generate Files Before Wheel Build

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"
```

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomHook(BuildHookInterface):
    PLUGIN_NAME = 'custom'

    def initialize(self, version: str, build_data: dict) -> None:
        # Generate version file
        with open('src/mypackage/_version.py', 'w') as f:
            f.write(f'__version__ = "{version}"\n')

        # Add generated file as artifact
        build_data['artifacts'].append('src/mypackage/_version.py')
```

### Example 2: Different Hooks for Different Targets

```toml
# Wheel gets version hook
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/_version.py"
template = '__version__ = "{version}"'

# Sdist only gets custom hook for documentation
[tool.hatch.build.targets.sdist.hooks.custom]
enable-by-default = true
```

### Example 3: Conditional Hook Based on Environment

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
enable-by-default = false  # Disabled by default
```

```bash
# Enable only when building release
HATCH_BUILD_HOOK_ENABLE_custom=true hatch build -t wheel
```

## Environment Variables for Hook Control

Standard environment variables for hook control:

| Variable                         | Purpose                                |
| -------------------------------- | -------------------------------------- |
| `HATCH_BUILD_HOOKS_ONLY`         | Execute only hooks, skip target build  |
| `HATCH_BUILD_NO_HOOKS`           | Disable all hooks (takes precedence)   |
| `HATCH_BUILD_HOOKS_ENABLE`       | Enable all hooks                       |
| `HATCH_BUILD_HOOK_ENABLE_<NAME>` | Enable specific hook by name           |
| `HATCH_BUILD_CLEAN_HOOKS_AFTER`  | Remove hook artifacts after each build |

**Source**: [Hatch Build Configuration - Environment Variables](https://hatch.pypa.io/1.13/config/build/#environment-variables)

## Debugging Hooks

Common debugging strategies:

```bash
# Run only hooks to test their behavior
HATCH_BUILD_HOOKS_ONLY=true hatch build

# Enable verbose output
hatch -v build

# Run with specific Python debugging
python -m pdb hatch_build.py
```

## See Also

- `../build-hooks/index.md` - Complete hook documentation
- `../build-hooks/custom-build-hooks.md` - Writing custom hooks
- `../build-hooks/build-data-passing.md` - Modifying build data
