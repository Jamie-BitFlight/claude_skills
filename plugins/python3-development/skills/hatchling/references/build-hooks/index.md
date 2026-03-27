---
category: Hatchling Build System
topics: [build-hooks, hooks, initialization, finalization, dynamic-builds]
related: [configuration.md, custom-build-hooks.md, version-build-hook.md, hook-dependencies.md]
---

# Build Hooks Reference

Build hooks define code that executes at various stages of the build process, enabling dynamic modifications to build behavior, artifact generation, and metadata handling. When assisting users with Hatchling builds, reference this documentation to help them understand how hooks work and how to configure them effectively.

## Overview

Build hooks run for every selected version of build targets. When helping users implement build hooks, you can guide them to modify build behavior through:

- **Initialization**: Runs immediately before each build, allowing modifications to build data before the target sees it
- **Finalization**: Runs immediately after each build, enabling post-build operations

Build hooks can be:

- Applied globally to all build targets
- Scoped to specific build targets
- Conditionally enabled or disabled via environment variables
- Configured with custom dependencies

## Core Topics

### Configuration & Execution

- `configuration.md` - How to configure build hooks globally and per-target
- `execution-order.md` - Understanding global vs target-specific hooks and execution sequence
- `conditional-execution.md` - Using `enable-by-default` to control hook activation

### Build Hook Interfaces

- `buildhook-interface.md` - The base interface all build hooks implement
- `custom-build-hooks.md` - Creating custom hooks in `hatch_build.py`
- `version-build-hook.md` - Built-in hook for writing version information to files

### Data & Dependencies

- `build-data.md` - Understanding how to modify and use build data
- `hook-dependencies.md` - Declaring dependencies for build hooks
- `hook-data-passing.md` - Sharing information across multiple hooks

### Environment & Control

- `environment-variables.md` - Controlling hook behavior via `HATCH_BUILD_*` variables

## Built-in Build Hooks

Hatchling includes two built-in build hooks:

- **`custom`**: User-defined hooks in Python files (typically `hatch_build.py`)
- **`version`**: Automatically writes project version to designated files

## Configuration Examples

### Global Hook Configuration

```toml
[tool.hatch.build.hooks.custom]
# Global hook applied to all targets

[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

### Target-Specific Hook Configuration

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
# Hook only for wheel builds

[tool.hatch.build.targets.sdist.hooks.version]
path = "src/version.txt"
```

### Conditional Hook Execution

```toml
[tool.hatch.build.hooks.custom]
enable-by-default = false
```

Enable conditionally:

```bash
export HATCH_BUILD_HOOK_ENABLE_CUSTOM=true
hatch build
```

## Quick Reference: Environment Variables

| Variable                              | Purpose                           |
| ------------------------------------- | --------------------------------- |
| `HATCH_BUILD_HOOKS_ONLY`              | Run only hooks, skip actual build |
| `HATCH_BUILD_NO_HOOKS`                | Skip all hooks entirely           |
| `HATCH_BUILD_HOOKS_ENABLE`            | Enable all hooks                  |
| `HATCH_BUILD_HOOK_ENABLE_<HOOK_NAME>` | Enable specific hook by name      |

## Common Use Cases

### Generating Files During Build

Create build artifacts dynamically (e.g., generated code, compiled resources):

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Generate files before build starts
        self.generate_code()
        # Add generated artifacts to build
        build_data['artifacts'].append('generated/*.py')
```

### Managing Version Information

Write version to multiple locations during build:

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

### Conditional Third-Party Hook Enablement

```toml
[tool.hatch.build.hooks.cython]
enable-by-default = false
dependencies = ["cython"]
```

Enable when needed:

```bash
HATCH_BUILD_HOOK_ENABLE_CYTHON=true hatch build
```

## Known Third-Party Build Hooks

The Hatchling ecosystem includes specialized hooks for:

- **hatch-cython**: Compile Cython extensions
- **hatch-jupyter-builder**: Build Jupyter packages
- **hatch-mypyc**: Compile code with Mypyc
- **scikit-build-core**: Build extension modules with CMake
- **hatch-gettext**: Compile multilingual messages
- **hatch-argparse-manpage**: Generate man pages
- **hatch-odoo**: Package Odoo add-ons
- **hatch-autorun**: Inject pre-import initialization code

## Files in This Reference

<eg>
build-hooks/
├── index.md (this file)
├── configuration.md
├── execution-order.md
├── conditional-execution.md
├── buildhook-interface.md
├── custom-build-hooks.md
├── version-build-hook.md
├── build-data.md
├── hook-dependencies.md
├── hook-data-passing.md
└── environment-variables.md
</eg>

## Next Steps

- **Getting Started**: See `configuration.md`
- **Writing Custom Logic**: See `custom-build-hooks.md`
- **Managing Versions**: See `version-build-hook.md`
- **Understanding Execution**: See `execution-order.md`
