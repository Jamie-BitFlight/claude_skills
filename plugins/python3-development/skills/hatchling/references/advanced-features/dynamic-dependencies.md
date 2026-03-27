---
category: Advanced Build Features
topics: [dynamic-dependencies, build-hooks, platform-specific, conditional-dependencies]
related: [build-context.md, build-data-passing.md]
---

# Dynamic Dependencies in Hooks

When assisting users with complex build scenarios, guide them to use dynamic dependencies to specify build requirements at build time rather than declaring them statically in `pyproject.toml`. This is essential when build dependencies depend on environmental factors or platform-specific conditions.

## Overview

The `dependencies()` method in a custom build hook allows users to declare build-time dependencies that Hatchling will install before executing hook code. This enables sophisticated build scenarios where dependencies cannot be determined statically.

## Configuration

To use dynamic dependencies, implement the `dependencies()` method in your custom hook class:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def dependencies(self):
        """Return list of build dependencies required for this hook"""
        return [
            'numpy>=1.20.0',
            'cython>=0.29.0',
        ]

    def initialize(self, version, build_data):
        # Your hook initialization code
        pass
```

## Requirements

1. The hook must be declared in your `pyproject.toml` under `[build-system]` requires:

```toml
[build-system]
requires = ["hatchling", "hatchling-custom-hook"]
build-backend = "hatchling.builders.wheel"

[tool.hatchling.hooks.custom]
path = "hooks/custom.py"
```

2. The custom hook package itself must be available during build initialization so Hatchling can call its `dependencies()` method

3. Returned dependencies should be PEP 440 compatible version specifiers

## Use Cases

### Platform-Specific Dependencies

```python
import platform

class PlatformSpecificHook(BuildHookInterface):
    def dependencies(self):
        deps = []
        if platform.system() == 'Windows':
            deps.append('pywin32>=300')
        elif platform.system() == 'Darwin':
            deps.append('pyobjc>=8.0')
        return deps
```

### Python Version Dependent Dependencies

```python
import sys

class VersionSpecificHook(BuildHookInterface):
    def dependencies(self):
        deps = ['wheel']
        if sys.version_info < (3, 10):
            deps.append('typing-extensions>=4.0.0')
        return deps
```

### Environment Variable Dependencies

```python
import os

class EnvDependentHook(BuildHookInterface):
    def dependencies(self):
        if os.getenv('BUILD_WITH_CYTHON'):
            return ['cython>=0.29.0']
        return []
```

## Execution Order

1. Hatchling discovers the hook module
2. Hatchling calls `dependencies()` to get required packages
3. Hatchling installs returned dependencies
4. Hatchling calls the standard hook methods (`initialize()`, `finalize()`, etc.)

This ensures all dependencies are available before any hook code executes.

## Best Practices

- Keep the `dependencies()` method lightweight - it may be called during dependency resolution
- Return only essential build dependencies needed for your hook logic
- Use version constraints to ensure compatibility with your hook code
- Document which environments require which dependencies
- Consider performance implications of complex dependency logic

## See Also

- `build-context.md` - Access to build environment information
- `build-data-passing.md` - Communicating between hooks and the build process
