---
category: Advanced Build Features
topics: [path-rewriting, sources, package-discovery, distribution-layout, namespace-packages]
related: [force-include.md, distributed-artifacts.md, build-data-passing.md]
---

# Path Rewriting with Sources

When helping users organize packages flexibly, guide them to use the `sources` configuration option to rewrite how files are distributed without requiring complex directory restructuring. This enables sophisticated package layouts while maintaining simple source organization.

## Overview

`sources` is a mapping that specifies how to rewrite paths during build. Reference this to show users how to transform source filesystem paths into different distribution paths in wheels or source distributions.

## Basic Configuration

### Dictionary Format

The simplest form maps a source directory to a distribution path:

```toml
[tool.hatchling.targets.wheel]
sources = { include = "src" }
```

This includes everything from the `src` directory at the package root level in the distribution.

### Prefix Rewriting

Use an empty string key to add a prefix to all distributions:

```toml
[tool.hatchling.targets.wheel]
sources = { "" = "mypackage" }
```

This places all discovered packages under a `mypackage` namespace.

### Array Format

For more complex rewriting scenarios:

```toml
[tool.hatchling.targets.wheel]
sources = [
    { path = "src/mypackage", name = "mypackage" },
    { path = "src/vendored", name = "mypackage/_vendored" }
]
```

Each array element specifies source and target locations.

## Common Patterns

### Src Layout Project

Standard Python project with source code in `src/`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.builders.wheel"

[tool.hatchling.targets.wheel]
sources = { include = "src" }

[tool.hatchling.targets.sdist]
sources = { include = ["src", "tests"] }
```

File structure:

<eg>
myproject/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
└── pyproject.toml
</eg>

Result in distribution: `mypackage/` at root level

### Flat Layout with Namespace Package

```toml
[tool.hatchling.targets.wheel]
sources = [
    { path = "pkgs/core", name = "mycompany.core" },
    { path = "pkgs/utils", name = "mycompany.utils" }
]
```

File structure:

<eg>
project/
├── pkgs/
│   ├── core/
│   │   ├── __init__.py
│   │   └── service.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
└── pyproject.toml
</eg>

Distribution paths: `mycompany/core/`, `mycompany/utils/`

### Rewriting with Prefix Injection

Add a common prefix to rewrite multiple sources:

```toml
[tool.hatchling.targets.wheel]
sources = [
    { path = "src/handlers", name = "myapp/_handlers" },
    { path = "src/utils", name = "myapp/_utils" },
    { path = "vendor", name = "myapp/_vendor" }
]
```

All source packages now live under `myapp/` with logical grouping.

## Anchor Point Specifications

### include Anchor

`include` specifies directories to search for packages:

```toml
sources = { include = "src" }
sources = { include = ["src", "lib"] }
```

Hatchling will discover all Python packages under these directories.

### path Anchor

Explicit path for a specific source:

```toml
sources = [
    { path = "src/mypackage" }
]
```

## Interaction with force-include

`sources` works alongside `force-include` but serves different purposes:

```toml
[tool.hatchling.targets.wheel]
# Rewrite source Python packages
sources = { include = "src" }

# Include non-Python resources from elsewhere
[tool.hatchling.targets.wheel.force-include]
assets/icons = "mypackage/assets/icons"
docs/_build = "mypackage/docs"
```

- `sources`: Python package discovery and path rewriting
- `force-include`: Adding arbitrary files from any location

## Advanced Patterns

### Conditional Source Rewriting

Use build hooks to conditionally modify source layout:

```python
class ConditionalSourcesHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Modify force_include based on sources
        # Note: sources itself is not in build_data,
        # but you can add files via force_include

        if os.path.exists('src/mypackage/_compiled'):
            build_data['force_include']['src/mypackage/_compiled'] = \
                'mypackage/_compiled'
```

### Multi-Distribution Targets

Different source layouts for wheels vs source distributions:

```toml
[tool.hatchling.targets.wheel]
sources = { include = "src" }

[tool.hatchling.targets.sdist]
sources = [
    { path = "src" },
    { path = "tests" },
    { path = "docs" }
]
```

Wheels contain only source code, sdists include development files.

## Troubleshooting

### Package Not Found

**Issue**: Configured path exists but package isn't discovered

**Solution**: Ensure the directory contains `__init__.py`:

```bash
ls -la src/mypackage/__init__.py  # Must exist
```

### Wrong Import Path

**Issue**: Installed package has unexpected import path

**Solution**: Verify the `name` parameter matches intended import path:

```toml
# Wrong - package would be imported as 'mypackage'
[tool.hatchling.targets.wheel]
sources = [{ path = "src/mypackage" }]

# Correct - package imported as 'myapp.core'
[tool.hatchling.targets.wheel]
sources = [{ path = "src/mypackage", name = "myapp.core" }]
```

### Multiple Packages Conflicting

**Issue**: Multiple sources map to same distribution path

**Solution**: Use unique names:

```toml
[tool.hatchling.targets.wheel]
sources = [
    { path = "lib1/package", name = "vendor_1.package" },
    { path = "lib2/package", name = "vendor_2.package" }
]
```

## Best Practices

- Use `sources` for Python package path rewriting, not arbitrary files
- Keep source and distribution names aligned for maintainability
- Document any complex source rewriting in project README
- Test cross-platform path handling (Linux/macOS/Windows compatibility)
- Consider namespace packages for complex multi-package structures
- Use `force-include` for non-Python resources alongside `sources`

## See Also

- `force-include.md` - File inclusion mechanism
- `artifact-directories.md` - Output directory configuration
- `build-data-passing.md` - Dynamic build data modification
