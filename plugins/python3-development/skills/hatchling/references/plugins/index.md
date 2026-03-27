---
name: Hatchling Plugins - Reference Navigation
description: Navigation guide and overview for Hatchling plugin system documentation, including quick start guides, plugin type references, and documentation index.
---

# Hatchling Plugin System Reference Documentation

This directory contains comprehensive reference documentation for Hatchling's plugin system and extensibility architecture.

## Quick Start

**New to Hatchling plugins?** Start with these guides in order:

1. `PLUGIN-GUIDE.md` - Complete overview of plugin types, development workflow, and best practices
2. `index.md` - Core architecture, registration patterns, and configuration concepts

## Documentation Files

### Core Reference

| Document                                      | Purpose                                                                                                  |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `PLUGIN-GUIDE.md` | **Start here** - Comprehensive guide covering all plugin types, development workflow, and best practices |
| `index.md`          | Plugin architecture, registration mechanisms, lifecycle management, and configuration patterns           |

### Plugin Type References

| Plugin Type     | Reference                                             | Use Case                                                                  |
| --------------- | ----------------------------------------------------- | ------------------------------------------------------------------------- |
| Builders        | `builder-plugins.md`               | Create distributable package formats (wheels, sdists, custom)             |
| Build Hooks     | `build-hook-plugins.md`         | Execute code during build phases (initialize, finalize, clean)            |
| Metadata Hooks  | `metadata-hook-plugins.md`   | Dynamically generate project metadata (version, description, classifiers) |
| Version Sources | `version-source-plugins.md` | Determine project version from various sources                            |
| Version Schemes | `version-scheme-plugins.md` | Validate and normalize version numbers                                    |

### Plugin Implementations

| Plugin    | Reference                                       | Features                                                           |
| --------- | ----------------------------------------------- | ------------------------------------------------------------------ |
| hatch-vcs | `hatch-vcs-plugin.md` | VCS-based versioning (Git, Mercurial), auto-generate version files |

## Plugin Types at a Glance

<eg>
┌─────────────────────────────────────────────────────────┐
│         Hatchling Plugin System Architecture             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Build-Time Plugins (Hatchling)                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Builder Plugins      (create distributions)    │   │
│  │ • Build Hook Plugins   (customize build steps)   │   │
│  │ • Metadata Hooks       (generate metadata)       │   │
│  │ • Version Sources      (determine version)       │   │
│  │ • Version Schemes      (validate versions)       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Runtime Plugins (Hatch)                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Environment Plugins  (custom environments)     │   │
│  │ • Publisher Plugins    (publish to repositories) │   │
│  │ • Environment Collectors (discover environments) │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
</eg>

## Common Tasks

### "I want to..."

- **Auto-generate version files** → See `hatch-vcs-plugin.md`
- **Read version from VCS tags** → See `version-source-plugins.md`
- **Customize the build process** → See `build-hook-plugins.md`
- **Generate metadata dynamically** → See `metadata-hook-plugins.md`
- **Create a custom builder** → See `builder-plugins.md`
- **Enforce version format rules** → See `version-scheme-plugins.md`
- **Build a reusable plugin** → See `PLUGIN-GUIDE.md`

## Key Concepts

### Plugin Registration Pattern

All Hatchling plugins follow this pattern:

```python
# hooks.py - Plugin registration
from hatchling.plugin import hookimpl
from .plugin import MyPlugin

@hookimpl
def hatch_register_builder():
    return MyPlugin

# plugin.py - Plugin implementation
class MyPlugin(BuilderInterface):
    PLUGIN_NAME = 'my-plugin'  # User-facing identifier
    # ... implement required methods
```

### Configuration in pyproject.toml

```toml
# Enable plugins via configuration
[tool.hatch.version]
source = "vcs"  # Select version source plugin

[tool.hatch.build.hooks.custom]
# Configure build hook plugin

[tool.hatch.metadata.hooks.dynamic-description]
# Configure metadata hook plugin
```

### Plugin Ecosystem

- **Official**: hatch-vcs, scikit-build-core (hatchling plugin)
- **Community**: hatch-cython, hatch-requirements-txt, hatch-nodejs-version, and many more
- **Custom**: Develop your own for project-specific needs

## Additional Resources

For more detailed information about Hatchling beyond plugins:

- **Build Targets** - Configuration for wheel, sdist, and binary targets
- **Build Hooks Configuration** - Specific build hook setup and options
- **File Selection** - Include/exclude patterns and Git-aware file selection
- **Version Management** - Version source and scheme configuration

## Sources

This documentation is based on:

1. **Official Hatchling Documentation**

   - Plugin system architecture and interfaces
   - Plugin registration mechanisms
   - Configuration patterns

2. **Official Plugin Registry**

   - hatch-vcs plugin implementation
   - Third-party plugin references
   - Community contributions

3. **pluggy Framework**

   - Hook registration and management
   - Plugin loading mechanisms

4. **PEP Standards**
   - PEP 517 (Build System Interface)
   - PEP 440 (Version Identification)
   - PEP 621 (Project Metadata)

## Content Quality

Each reference document includes:

- **Comprehensive Interface Documentation** - All required and optional methods
- **Configuration Examples** - Real-world usage patterns
- **Code Examples** - Complete, runnable implementations
- **Best Practices** - Lessons learned from community plugins
- **Troubleshooting** - Common issues and solutions
- **Cross-References** - Links to related documentation

## How to Use These References

These documentation files are organized for progressive discovery:

1. **Start with overview**: `PLUGIN-GUIDE.md` covers the complete workflow
2. **Learn architecture**: `index.md` explains how plugins work internally
3. **Deep dive by type**: Use specific plugin type references for detailed interface documentation
4. **Real-world implementation**: See PLUGIN-GUIDE for complete working examples

Each reference includes code examples, configuration patterns, and best practices for immediate application.

---

**Next step**: Read `PLUGIN-GUIDE.md` to begin learning how to create and use plugins
