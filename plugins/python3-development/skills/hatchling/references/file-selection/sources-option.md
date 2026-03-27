---
description: The sources configuration option for Hatchling builds. Explains path remapping, prefix removal and addition, multiple source roots, and how sources interact with other file selection options like include and packages.
keywords: [sources, path mapping, path remapping, hatchling, prefix, path rewriting]
---

# Sources Option - Path Mapping

Configuration reference for Hatchling's `sources` option. Enables path remapping during builds through prefix removal, addition, or complete path transformation. Explains interaction with other options and provides algorithms for understanding path resolution order.

## Basic Path Remapping

### Remove Path Prefix

Most common use: removing the `src/` prefix:

```toml
[tool.hatch.build.targets.wheel.sources]
"src/mypackage" = "mypackage"

# Or as array to remove prefix entirely
[tool.hatch.build.targets.wheel]
sources = ["src"]
```

### Add Path Prefix

Add a prefix to all paths:

```toml
[tool.hatch.build.targets.wheel.sources]
"" = "lib"  # Everything goes under lib/
```

### Rename Paths

Map one path to another:

```toml
[tool.hatch.build.targets.wheel.sources]
"old_name" = "new_name"
"legacy/module" = "modern/module"
```

## Configuration Formats

### Dictionary Format

Full control over individual mappings:

```toml
[tool.hatch.build.targets.wheel.sources]
"src/core" = "myapp/core"
"src/utils" = "myapp/utils"
"configs" = "myapp/configs"
```

### Array Format

Remove common prefixes:

```toml
[tool.hatch.build.targets.wheel]
sources = ["src", "lib"]  # Removes these prefixes
```

## Common Use Cases

### 1. Source Layout (`src/` Directory)

Standard Python project layout:

<eg>
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
└── pyproject.toml
</eg>

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]
# Result: mypackage/ in distribution
```

### 2. Multiple Source Roots

<eg>
project/
├── src/
│   └── core/
├── lib/
│   └── utils/
└── vendor/
    └── third_party/
</eg>

```toml
[tool.hatch.build.targets.wheel.sources]
"src/core" = "core"
"lib/utils" = "utils"
"vendor/third_party" = "third_party"
```

### 3. Organizing Flat Structure

Transform flat layout into organized structure:

```toml
[tool.hatch.build.targets.wheel.sources]
"models" = "myapp/models"
"views" = "myapp/views"
"controllers" = "myapp/controllers"
"static" = "myapp/static"
"templates" = "myapp/templates"
```

### 4. Namespace Packages

```toml
[tool.hatch.build.targets.wheel.sources]
"src/company/project1" = "company/project1"
"src/company/project2" = "company/project2"
"src/company/shared" = "company/shared"
```

## Advanced Mapping Patterns

### Nested Remapping

```toml
[tool.hatch.build.targets.wheel.sources]
# Deep nesting transformation
"src/old/deep/path/module" = "new/module"

# Multiple levels
"src/v1/api" = "api/v1"
"src/v2/api" = "api/v2"
```

### Conditional Mapping by Target

Different mappings for different build targets:

```toml
# Development build
[tool.hatch.build.targets.dev.sources]
"src" = "myapp"
"tests" = "myapp_tests"

# Production build
[tool.hatch.build.targets.wheel.sources]
"src" = ""  # No prefix in production
```

### Platform-Specific Paths

```toml
[tool.hatch.build.targets.linux-wheel.sources]
"platform/linux" = "myapp/platform"
"shared" = "myapp"

[tool.hatch.build.targets.windows-wheel.sources]
"platform/windows" = "myapp/platform"
"shared" = "myapp"
```

## Interaction with Other Options

### With Include/Only-Include

Sources applies to selected files:

```toml
[tool.hatch.build.targets.wheel]
include = ["src/**/*.py"]
sources = ["src"]
# Python files from src/ appear without src/ prefix
```

### With Packages

The `packages` option automatically applies source mapping:

```toml
# These are equivalent:

# Method 1: Using packages
packages = ["src/mypackage"]

# Method 2: Manual with sources
only-include = ["src/mypackage"]
sources = ["src"]
```

### With Force-Include

Force-include can use different mappings:

```toml
[tool.hatch.build.targets.wheel]
sources = ["src"]  # General mapping

[tool.hatch.build.targets.wheel.force-include]
"external/lib.so" = "mypackage/lib.so"  # Specific mapping
```

## Path Resolution Rules

### Order of Operations

1. File selection (include/exclude)
2. Source path mapping
3. Force-include additions

### Mapping Priority

More specific mappings override general ones:

```toml
[tool.hatch.build.targets.wheel.sources]
"src" = ""  # General: remove src/
"src/special" = "custom"  # Specific: src/special → custom/
```

### Empty String Handling

```toml
# Add prefix to everything
[tool.hatch.build.targets.wheel.sources]
"" = "prefix"
# file.py → prefix/file.py

# Remove prefix from everything
[tool.hatch.build.targets.wheel]
sources = ["prefix"]
# prefix/file.py → file.py
```

## Real-World Examples

### Example 1: Standard Python Package

```toml
[project]
name = "awesome-lib"

[tool.hatch.build.targets.wheel]
only-include = ["src/awesome_lib"]
sources = ["src"]

[tool.hatch.build.targets.sdist]
# Source distribution keeps original structure
include = ["src/**", "tests/**", "*.md"]
```

### Example 2: Multi-Package Repository

```toml
# Shared configuration
[tool.hatch.build]
sources = ["packages"]

# Package A
[tool.hatch.build.targets.package-a]
only-include = ["packages/package_a"]

# Package B
[tool.hatch.build.targets.package-b]
only-include = ["packages/package_b"]
```

### Example 3: Legacy Code Migration

```toml
[tool.hatch.build.targets.wheel.sources]
# Map old structure to new structure
"old_package/submodule1" = "newpackage/module1"
"old_package/submodule2" = "newpackage/module2"
"legacy_configs" = "newpackage/configs"
"scripts/old" = "newpackage/cli"
```

### Example 4: Documentation Package

```toml
[tool.hatch.build.targets.docs.sources]
"docs/source" = "docs"
"examples" = "docs/examples"
"tutorials" = "docs/tutorials"
```

## Best Practices

### 1. Keep Mappings Simple

```toml
# Good: Clear and simple
sources = ["src"]

# Avoid: Complex mappings
[tool.hatch.build.targets.wheel.sources]
"src/a/b/c" = "x/y/z"
"src/a/b/d" = "x/y/w"
# ... many more
```

### 2. Document Non-Obvious Mappings

```toml
[tool.hatch.build.targets.wheel.sources]
# Map legacy names to new structure for backward compatibility
"old_module" = "mypackage/compat/old_module"
```

### 3. Use Consistent Patterns

```toml
# Consistent prefix removal
sources = ["src", "lib", "vendor"]

# Or consistent remapping pattern
[tool.hatch.build.targets.wheel.sources]
"src/myapp" = "myapp"
"lib/myapp_utils" = "myapp_utils"
"vendor/myapp_vendor" = "myapp_vendor"
```

### 4. Test Path Mappings

```bash
# Build and inspect
hatch build -t wheel
unzip -l dist/*.whl | head -20

# Verify paths are correct
python -m zipfile -l dist/*.whl
```

## Troubleshooting

### Files in Wrong Location

```toml
# Problem: Files appear in src/mypackage/
[tool.hatch.build.targets.wheel]
include = ["src/**"]
# Missing sources configuration!

# Solution: Add sources
sources = ["src"]
```

### Mapping Not Applied

```toml
# Problem: Mapping doesn't work
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["lib/module"]  # Different path!

# Solution: Match paths
only-include = ["src/module"]
sources = ["src"]
```

### Prefix Added Instead of Removed

```toml
# Problem: Got myapp/src/module/
[tool.hatch.build.targets.wheel.sources]
"" = "myapp"  # This adds prefix!
sources = ["src"]  # This is ignored!

# Solution: Use one or the other
sources = ["src"]  # Just remove src/
```

## Complex Scenarios

### Restructuring During Build

```toml
[tool.hatch.build.targets.wheel.sources]
# Flatten structure
"src/myapp/core/models" = "myapp/models"
"src/myapp/core/views" = "myapp/views"
"src/myapp/utils/helpers" = "myapp/helpers"
"src/myapp/utils/validators" = "myapp/validators"
```

### Version-Specific Builds

```toml
[tool.hatch.build.targets.py38-wheel.sources]
"src/compat/py38" = "myapp/compat"
"src/main" = "myapp"

[tool.hatch.build.targets.py39plus-wheel.sources]
"src/modern" = "myapp"
```

### Vendor Dependencies

```toml
[tool.hatch.build.targets.wheel.sources]
# Include vendored dependencies under package
"vendor/lib1" = "myapp/_vendor/lib1"
"vendor/lib2" = "myapp/_vendor/lib2"
"src/myapp" = "myapp"
```

## See Also

- `packages-option.md`
- `only-include-option.md`
- `force-include-option.md`
