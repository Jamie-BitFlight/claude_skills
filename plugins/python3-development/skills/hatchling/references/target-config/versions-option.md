---
category: Build System Configuration
topics: [build-versions, multi-variant-builds, build-strategies, version-selection]
related: [index.md, target-specific-hooks.md, default-targets.md]
---

# Versions Option Configuration

Build multiple variations of the same target using different build strategies.

## Overview

When guiding users through multi-variant build configurations, reference this document to explain the `versions` option. This option allows a single build target to support multiple build modes or strategies, enabling users to build different variants of their distribution (e.g., standard and optimized wheels) from a single configuration.

**Source**: [Hatch Build Configuration - Versions](https://hatch.pypa.io/1.13/config/build/#versions)

## Configuration Syntax

```toml
[tool.hatch.build.targets.<TARGET>]
versions = [
    "version1",
    "version2",
    "version3",
]
```

## Built-In Wheel Versions

The wheel target provides real-world examples of versioning:

```toml
[tool.hatch.build.targets.wheel]
versions = [
    "standard",    # Standard wheel, no optimization
    "cp311",       # CPython 3.11 specific
    "cp312",       # CPython 3.12 specific
]
```

**Source**: [Hatch Wheel Builder - Versions](https://hatch.pypa.io/1.13/plugins/builder/wheel/#versions)

## Building with Versions

Specify which versions to build:

```bash
# Build all versions of a target
hatch build -t wheel

# Build specific version
hatch build -t wheel:standard

# Build multiple specific versions
hatch build -t wheel:standard -t wheel:cp311
```

## Practical Use Cases

### Use Case 1: Optimized vs Standard Wheels

```toml
[tool.hatch.build.targets.wheel]
versions = [
    "standard",      # Pure Python, maximum compatibility
    "optimized",     # With C extensions for performance
]
```

Different hooks can run for each version:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
# Hook adjusts build behavior based on version
```

### Use Case 2: Python Version-Specific Wheels

```toml
[tool.hatch.build.targets.wheel]
versions = [
    "py38",   # Python 3.8 specific
    "py39",   # Python 3.9 specific
    "py310",  # Python 3.10 specific
    "py311",  # Python 3.11 specific
]
```

### Use Case 3: Platform-Specific Distributions

```toml
[tool.hatch.build.targets.binary]
versions = [
    "linux-x86_64",
    "linux-aarch64",
    "macos-x86_64",
    "macos-aarch64",
    "windows-x86_64",
]
```

## Version-Specific Hooks

Hooks receive the version being built:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class OptimizationHook(BuildHookInterface):
    PLUGIN_NAME = 'custom'

    def initialize(self, version: str, build_data: dict) -> None:
        if version == "optimized":
            # Add C extension sources
            build_data['artifacts'].append('src/**/*.c')
        elif version == "standard":
            # Pure Python only
            pass
```

## Version-Specific Dependencies

Different versions can have different dependencies:

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "optimized"]

# Hooks can declare version-conditional dependencies
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = [
    "cython>=0.29.0",  # Needed for optimized version
]
```

## Custom Build Strategy Example

```toml
[tool.hatch.build.targets.custom]
versions = [
    "basic",          # Core functionality only
    "full",           # All features
    "enterprise",     # Enterprise edition
]
```

Configuration can be version-aware:

```python
class CustomBuilder:
    def build(self, target_name: str, version: str):
        if version == "basic":
            self.include_basic_modules()
        elif version == "full":
            self.include_all_modules()
        elif version == "enterprise":
            self.include_enterprise_features()
```

## Real-World Example: Data Science Library

```toml
[project]
name = "datascilib"
version = "2.0.0"
dependencies = ["numpy>=1.19"]

[project.optional-dependencies]
pandas = ["pandas>=1.0"]
ml = ["scikit-learn>=0.24", "xgboost>=1.3"]
gpu = ["cupy>=8.0", "rapids>=0.19"]

[build-system]
requires = ["hatchling", "cython>=0.29.0", "numpy>=1.19"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
versions = [
    "universal",   # Pure Python, works everywhere
    "accelerated", # With compiled extensions
    "gpu",        # GPU-accelerated version
]

[tool.hatch.build.targets.wheel.hooks.build-ext]
dependencies = [
    "cython>=0.29.0",
    "numpy>=1.19",
]
```

Build process:

```bash
# Build all variations
hatch build -t wheel

# Build specific variations
hatch build -t wheel:universal
hatch build -t wheel:accelerated
hatch build -t wheel:gpu
```

## Version Metadata

Some builders attach version information to outputs:

```bash
hatch build -t wheel:standard
# Creates: datascilib-2.0.0-py3-none-any.whl

hatch build -t wheel:accelerated
# Creates: datascilib-2.0.0-py3-none-any.whl (with different content)
```

The filename might be identical, but contents differ based on version.

## Version Selection Strategies

### Sequential Versions

```toml
[tool.hatch.build.targets.wheel]
versions = ["v1", "v2", "v3"]
```

Used when versions represent different API or behavior versions.

### Feature-Based Versions

```toml
[tool.hatch.build.targets.wheel]
versions = ["minimal", "standard", "full"]
```

Different feature levels based on dependencies.

### Platform-Based Versions

```toml
[tool.hatch.build.targets.binary]
versions = [
    "linux",
    "macos",
    "windows",
]
```

Different distributions for each platform.

### Optimization Levels

```toml
[tool.hatch.build.targets.wheel]
versions = [
    "debug",      # With symbols and debug info
    "standard",   # Optimized, no debug
    "profiling",  # With profiling instrumentation
]
```

## Conditional Configuration

Versions can affect target configuration:

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "optimized"]
# Shared configuration

[tool.hatch.build.targets.wheel.hooks.custom]
# This hook applies to all versions
dependencies = ["cython"]
```

Version-specific behavior is handled within hooks, not in TOML.

## Distribution and Release

When building for distribution, include all versions:

```bash
# Create distribution with all variants
hatch build -c

# Creates:
# dist/datascilib-2.0.0-py3-none-any.whl          (standard)
# dist/datascilib-2.0.0-py3-none-any.whl          (optimized)
# dist/datascilib-2.0.0.tar.gz                     (source)
```

Upload all `.whl` files to PyPI with different architecture/platform tags.

## Performance Considerations

Each version triggers a separate build:

```bash
# Builds 3 times
hatch build -t wheel
# Builds once each
hatch build -t wheel:standard
hatch build -t wheel:accelerated
```

This is intentional—each version may have different outputs.

## Version Documentation

Document what each version provides:

```markdown
# datascilib Distributions

- **standard**: Pure Python, maximum compatibility
- **accelerated**: Includes compiled C extensions for faster numerical operations
- **gpu**: GPU-accelerated routines using CuPy and RAPIDS

Choose based on your environment and performance needs.
```

## Troubleshooting

### Version Not Found

```bash
hatch build -t wheel:nonexistent
# ERROR: Version 'nonexistent' not found
```

Check `versions` list in `[tool.hatch.build.targets.wheel]`.

### All Versions Build Same Output

If different versions produce identical files:

```python
# In hook, ensure version affects behavior
def initialize(self, version: str, build_data: dict) -> None:
    if version == "standard":
        pass  # No changes
    elif version == "optimized":
        build_data['artifacts'].append('*.so')  # Add compiled objects
    # Otherwise versions produce same output
```

### Build Time Increased

Building multiple versions takes longer:

```bash
# Profile builds
hatch -v build -t wheel

# Build one version only during development
hatch build -t wheel:standard
```

## Best Practices

1. **Clear Naming**: Version names should indicate their purpose

   - Good: `standard`, `optimized`, `gpu-accelerated`
   - Bad: `v1`, `v2`, `version-x`

2. **Document Differences**: Explain what makes each version distinct

3. **Minimal Versions**: Don't create unnecessary version variants

4. **Consistent Compatibility**: Ensure all versions maintain API compatibility (usually)

5. **Test Each Version**: Verify each version works correctly:

```bash
hatch build -t wheel:standard
# test standard version

hatch build -t wheel:optimized
# test optimized version
```

## See Also

- `../build-targets/multi-version-builds.md` - Building multiple targets with versions
- `../build-targets/wheel-builder.md` - Wheel-specific version strategies
- `../build-hooks/index.md` - Hooks to customize version behavior
- `../build-targets/index.md` - Available build targets
