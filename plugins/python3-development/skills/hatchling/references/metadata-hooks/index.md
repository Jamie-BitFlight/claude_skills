---
category: metadata-management
topics: [metadata-hooks, hook-system, dynamic-injection, build-process]
---

# Metadata Hooks

Metadata hooks provide mechanisms for dynamically injecting and modifying project metadata during the build process. Hatchling includes built-in hooks and supports custom implementations for advanced use cases.

## Navigation

- `metadata-hooks.md` - Hook configuration, built-in hooks, execution flow
- `custom-hooks.md` - Implementing custom hooks with MetadataHookInterface

## When to Use Metadata Hooks

Metadata hooks are appropriate when:

- Dynamic version injection from source files is needed
- Classifiers or other fields require computation at build time
- Metadata should be sourced from external files or configurations
- Custom metadata validation or transformation is required
- Metadata needs to vary based on build environment

## Quick Start

Configure a metadata hook in `pyproject.toml`:

```toml
[tool.hatch.metadata.hooks.custom]
path = "hatch_build.py"
```

Implement the `MetadataHookInterface` in the specified file:

```python
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        # Modify metadata in-place
        metadata["version"] = "1.0.0"
```

## Key Concepts

**Hook Configuration**: Hooks are configured in `[tool.hatch.metadata.hooks.*]` sections in `pyproject.toml`.

**Execution Timing**: Hooks execute during:

- Building distributions
- Running `hatch project metadata` command
- Installing the project
- IDE operations requiring metadata

**Metadata Dictionary**: The `update()` method receives a mutable metadata dictionary that reflects the current project metadata state. Modifications are applied in-place.

**Hook Interface**: All metadata hooks implement `MetadataHookInterface`, providing `update(metadata)` as the primary method and `get_known_classifiers()` as an optional method.

## Related Topics

- `../project-metadata/dynamic-metadata.md` - Declaring fields as dynamic
- `../project-metadata/metadata-options.md` - Configuration options
- `../build-hooks/index.md` - Build-time hook system (different from metadata hooks)
