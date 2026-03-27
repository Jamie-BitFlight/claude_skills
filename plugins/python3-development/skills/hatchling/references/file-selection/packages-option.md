---
description: The packages configuration option for Hatchling wheel builds. Explains path collapsing behavior, comparison with only-include plus sources, common source layouts, and when to use packages versus alternative approaches.
keywords: [packages, hatchling, wheel builds, path collapsing, source layouts, src layout]
---

# Packages Option

Configuration reference for Hatchling's `packages` option. Shorthand for explicit package selection with automatic path collapsing, equivalent to `only-include` plus `sources`. Explains path collapsing behavior, multiple packages, and comparison with alternatives.

## Basic Usage

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

This single line is equivalent to:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]
```

## How It Works

The `packages` option:

1. Selects specific directories (like `only-include`)
2. Automatically strips parent directories (like `sources`)
3. Only affects wheel builds (not sdist)

## Common Source Layouts

### Src Layout

Most common for modern Python projects:

<eg>
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
├── tests/
└── pyproject.toml
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
# Result: mypackage/ in wheel root
```

### Flat Layout

Package at project root:

<eg>
project/
├── mypackage/
│   ├── __init__.py
│   └── module.py
├── tests/
└── pyproject.toml
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = ["mypackage"]
# Result: mypackage/ in wheel root
```

### Nested Packages

Multiple packages in different locations:

<eg>
project/
├── src/
│   ├── core/
│   └── utils/
├── lib/
│   └── helpers/
└── pyproject.toml
</eg>

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "src/core",
  "src/utils",
  "lib/helpers",
]
# Result: core/, utils/, helpers/ in wheel root
```

## Path Collapsing Behavior

The key feature of `packages` is path collapsing:

```toml
# With packages: collapses path
packages = ["src/mypackage"]
# Wheel contains: mypackage/

# With only-include: preserves path
only-include = ["src/mypackage"]
# Wheel contains: src/mypackage/

# Unless combined with sources
only-include = ["src/mypackage"]
sources = ["src"]
# Wheel contains: mypackage/
```

## Multiple Packages

### Monorepo with Multiple Packages

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "packages/package-a",
  "packages/package-b",
  "packages/shared",
]
# Result: package-a/, package-b/, shared/ in wheel
```

### Different Source Directories

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "src/main_package",      # From src/
  "vendor/third_party",    # From vendor/
  "libs/utility",          # From libs/
]
# Result: main_package/, third_party/, utility/ in wheel
```

## Interaction with Other Options

### Precedence

1. `only-include` takes precedence over `packages`
2. `packages` overrides `include` patterns

```toml
[tool.hatch.build.targets.wheel]
include = ["**/*.py"]          # Ignored
packages = ["src/mypackage"]   # Used if only-include not set
only-include = ["src"]          # Takes precedence if set
```

### With Exclude Patterns

`exclude` patterns still apply:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
exclude = [
  "**/*.pyc",
  "**/__pycache__",
  "**/tests/**",
]
```

### With Force-Include

Can combine for additional files:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.hatch.build.targets.wheel.force-include]
"configs/prod.yaml" = "mypackage/config.yaml"
```

## Use Cases

### 1. Standard Python Package

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/myproject"]

[tool.hatch.build.targets.sdist]
# Different config for source distribution
include = [
  "src/**",
  "tests/**",
  "docs/**",
  "*.md",
]
```

### 2. Namespace Package

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "src/mycompany/package1",
  "src/mycompany/package2",
]
# Result: mycompany/package1/, mycompany/package2/
```

### 3. Plugin Architecture

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "src/core",
  "plugins/builtin",
]
# Result: core/, builtin/ in wheel
```

### 4. Selective Package Building

Build different wheels from same source:

```toml
# Client package
[tool.hatch.build.targets.client-wheel]
packages = ["src/myapp/client"]

# Server package
[tool.hatch.build.targets.server-wheel]
packages = ["src/myapp/server"]

# Shared utilities
[tool.hatch.build.targets.utils-wheel]
packages = ["src/myapp/utils"]
```

## Best Practices

### 1. Use for Simple Package Structures

Good for:

```toml
# Simple and clear
packages = ["src/mypackage"]
```

Not ideal for:

```toml
# Complex selection - use only-include + sources
packages = [
  "src/pkg/subpkg1",
  "src/pkg/subpkg2",
  # ... many more
]
```

### 2. Consistent Source Layout

Maintain consistent structure:

```toml
# Good: All packages from same root
packages = [
  "src/package1",
  "src/package2",
  "src/package3",
]

# Confusing: Mixed layouts
packages = [
  "src/package1",
  "package2",        # Different depth
  "lib/src/package3", # Nested differently
]
```

### 3. Document Non-Standard Layouts

```toml
[tool.hatch.build.targets.wheel]
# We keep packages in 'lib/' for historical reasons
packages = ["lib/ourpackage"]
```

## Comparison with Alternatives

### Packages vs Only-Include + Sources

Functionally equivalent:

```toml
# Method 1: Using packages
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

# Method 2: Using only-include + sources
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]
```

Choose `packages` when:

- You have a standard src layout
- You want concise configuration
- Path collapsing is desired

Choose `only-include + sources` when:

- You need more control
- You have complex path remapping
- You're mixing with other options

### Packages vs Include Patterns

```toml
# Method 1: Using packages (explicit)
packages = ["src/mypackage"]

# Method 2: Using include (pattern-based)
include = ["src/mypackage/**"]
sources = ["src"]
```

Choose `packages` when:

- You want entire directories
- You have simple structure
- Performance is important

Choose `include` when:

- You need pattern matching
- You want partial directory inclusion
- You have complex file selection

## Troubleshooting

### Package Not Found in Wheel

Check:

1. Path exists: `ls -la src/mypackage`
2. Contains `__init__.py` for Python to recognize it
3. Not excluded by `exclude` patterns

### Wrong Path in Wheel

```toml
# Problem: Full path in wheel
packages = ["src/mypackage"]
# If you see: src/mypackage/ in wheel

# Solution: Check for conflicting options
only-include = ["src"]  # This overrides packages!
```

### Multiple Packages Collision

```toml
# Problem: Name collision
packages = [
  "client/utils",
  "server/utils",  # Both become 'utils/'
]

# Solution: Use unique names or only-include
only-include = ["client", "server"]
```

## Examples

### Real-World Project

```toml
[project]
name = "my-awesome-lib"

[tool.hatch.build.targets.wheel]
packages = ["src/awesome_lib"]
exclude = [
  "**/*.pyc",
  "**/__pycache__",
  "**/.pytest_cache",
]

[tool.hatch.build.targets.sdist]
include = [
  "src/**",
  "tests/**",
  "*.md",
  "LICENSE",
]
```

### Namespace Package

```toml
[tool.hatch.build.targets.wheel]
packages = [
  "src/acme/anvils",
  "src/acme/rockets",
  "src/acme/common",
]
# Creates proper namespace package structure
```

### Development vs Production

```toml
# Production wheel
[tool.hatch.build.targets.wheel]
packages = ["src/myapp"]
exclude = ["**/debug.py", "**/test_*.py"]

# Development wheel
[tool.hatch.build.targets.dev-wheel]
packages = ["src/myapp"]
# Includes everything for development
```

## See Also

- `only-include-option.md`
- `sources-option.md`
- `explicit-path-selection.md`
