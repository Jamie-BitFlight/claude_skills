---
category: Build System Configuration
topics: [configuration-precedence, build-hierarchy, target-configuration, settings-inheritance]
related: [index.md, target-dependencies.md, target-specific-hooks.md]
---

# Target Configuration Precedence

Understand how configuration at different levels interacts and which settings take precedence.

## Overview

When helping users troubleshoot Hatchling configuration issues, reference this guide to explain configuration precedence rules. Hatchling allows build configuration at multiple levels. When the same setting is defined at multiple levels, specific precedence rules determine which value is used.

**Source**: [Hatch Build Configuration - Build Targets](https://hatch.pypa.io/1.13/config/build/#build-targets)

## Configuration Hierarchy

Build configuration can be specified at three levels (from lowest to highest precedence):

1. **Global Build Level** (`[tool.hatch.build]`)
2. **Target Level** (`[tool.hatch.build.targets.<TARGET>]`)
3. **Hook/Feature Level** (`[tool.hatch.build.targets.<TARGET>.hooks.<HOOK>]`)

## Precedence Rule

**Target-level settings override global settings.**

```toml
[tool.hatch.build]
reproducible = true           # Global setting

[tool.hatch.build.targets.wheel]
reproducible = false          # Overrides global setting for wheel
# This wheel target uses reproducible = false

[tool.hatch.build.targets.sdist]
# This sdist target uses global reproducible = true (inherited)
```

**Source**: [Hatch Build Configuration](https://hatch.pypa.io/1.13/config/build/#build-targets) - "Although not recommended, you may define global configuration in the `tool.hatch.build` table. Keys may then be overridden by target config."

## Configuration Example

### Global Configuration

Global settings apply to all targets:

```toml
[tool.hatch.build]
# These apply to all targets
reproducible = true
skip-excluded-dirs = true
directory = "dist"

[build]
# These apply to all build environment configurations
dev-mode-dirs = ["."]
```

### Target-Level Overrides

Individual targets override specific settings:

```toml
[tool.hatch.build.targets.wheel]
# Override specific global settings
reproducible = false

# Add target-specific settings
packages = ["src/mypackage"]

[tool.hatch.build.targets.sdist]
# Different settings for sdist
include = [
    "src/mypackage",
    "tests",
    "docs",
]
```

## File Selection Precedence

File selection options follow target-level precedence:

```toml
[tool.hatch.build]
# Global file selection
include = ["pkg/**/*.py"]
exclude = ["**/test_*.py"]

[tool.hatch.build.targets.wheel]
# Override for wheel target only
exclude = ["**/test_*.py", "docs/**/*"]
# include is inherited from global unless overridden

[tool.hatch.build.targets.sdist]
# Different file selection for sdist
include = ["pkg", "tests", "docs"]
# exclude would come from global unless overridden
```

**Result**:

- wheel: Global include with wheel-specific exclude
- sdist: sdist-specific include, global exclude

## Hook Execution Precedence

Hooks execute in a specific order considering both levels:

```toml
[tool.hatch.build.hooks.global-hook1]
# Global hook 1

[tool.hatch.build.hooks.global-hook2]
# Global hook 2

[tool.hatch.build.targets.wheel.hooks.target-hook1]
# Target-specific hook for wheel
```

**Execution order for wheel target**:

1. global-hook1
2. global-hook2
3. target-hook1

Global hooks always run first, regardless of definition order.

**Source**: [Hatch Build Configuration - Order of Execution](https://hatch.pypa.io/1.13/config/build/#order-of-execution)

## Dependency Precedence

Dependencies are combined, not overridden:

```toml
[tool.hatch.build]
# These are NOT available as this is not a valid global dependencies option

[tool.hatch.build.targets.wheel]
dependencies = [
    "setuptools>=40.0",
    "wheel",
]

[tool.hatch.build.targets.sdist]
dependencies = [
    "toml>=0.10.0",
]

# Both target dependencies are installed, they are not merged or overridden
# There is no inheritance of dependencies between targets
```

Each target's dependencies are independent.

## Real-World Example

Complete configuration with precedence in action:

```toml
[project]
name = "myproject"
version = "1.0.0"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# GLOBAL: Applies to all targets unless overridden
[tool.hatch.build]
reproducible = true
skip-excluded-dirs = true

# Global file selection
include = [
    "src/**/*.py",
    "data/**/*",
]

exclude = [
    "**/.*",
    "*/__pycache__/**",
    "tests/**/*",
]

# Global hooks
[tool.hatch.build.hooks.version]
path = "src/myproject/_version.py"
template = '__version__ = "{version}"'

# WHEEL TARGET: Overrides some global settings
[tool.hatch.build.targets.wheel]
# Override global reproducible setting
reproducible = false

# Add target-specific settings
packages = ["src/myproject"]

# Wheel-specific hook
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = ["cython>=0.29.0"]

# SDIST TARGET: Uses defaults where not specified
[tool.hatch.build.targets.sdist]
# Inherits global reproducible = true
# Inherits global include/exclude rules

# Override exclude to include tests
exclude = [
    "**/.*",
    "**/__pycache__/**",
]

# Add tests to source distribution
include = [
    "src/**/*.py",
    "data/**/*",
    "tests/**/*",
    "docs/**/*",
]
```

**Result**:

- **wheel**:

  - reproducible = false (overridden)
  - skip-excluded-dirs = true (inherited from global)
  - packages = ["src/myproject"]
  - version hook runs first, then custom hook

- **sdist**:
  - reproducible = true (inherited from global)
  - skip-excluded-dirs = true (inherited from global)
  - Custom include/exclude (overridden)
  - Only version hook runs (no custom hook for sdist)

## Configuration Inheritance Rules

### Settings That Are Overridden (Not Inherited)

```toml
[tool.hatch.build]
reproducible = true

[tool.hatch.build.targets.wheel]
reproducible = false        # Replaces global value
```

### Settings That Are Combined/Merged

Hooks are combined (not replaced):

```toml
[tool.hatch.build.hooks.hook1]

[tool.hatch.build.targets.wheel.hooks.hook2]
# hook1 still runs, then hook2 runs
```

### Settings Specific to Level

Some settings only exist at specific levels:

```toml
[tool.hatch.build]
directory = "dist"          # Only at global level

[tool.hatch.build.targets.wheel]
packages = ["src/pkg"]      # Only at target level
```

## Best Practices for Configuration Precedence

1. **Use Global for Common Settings**: Put shared settings in `[tool.hatch.build]`

```toml
[tool.hatch.build]
reproducible = true
skip-excluded-dirs = true
```

2. **Use Target-Level for Differences**: Only override when necessary

```toml
[tool.hatch.build.targets.wheel]
reproducible = false  # Only if wheel needs different value
```

3. **Document Why You Override**: Comment on non-obvious overrides

```toml
[tool.hatch.build.targets.custom]
# Custom target needs different reproducibility handling
reproducible = false
```

4. **Avoid Duplication**: Don't repeat global settings in every target

```toml
# BAD: Repeating in every target
[tool.hatch.build.targets.wheel]
reproducible = true
skip-excluded-dirs = true

[tool.hatch.build.targets.sdist]
reproducible = true
skip-excluded-dirs = true

# GOOD: Set once globally
[tool.hatch.build]
reproducible = true
skip-excluded-dirs = true
```

5. **Test with Multiple Targets**: Verify precedence works as expected

```bash
# Build all targets to verify precedence rules work
hatch build -c

# Check wheel was built with correct settings
# Check sdist was built with correct settings
```

## Troubleshooting Precedence Issues

### Settings Not Taking Effect

Verify precedence level:

```bash
# Enable verbose output to see effective configuration
hatch -v build
```

Check:

1. Is the setting defined at the correct level?
2. Is there a target-level override hiding the global setting?
3. Are hooks defined in the correct order?

### Unexpected Hook Execution

If a hook doesn't run:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
enable-by-default = false  # Make sure it's enabled
```

### File Selection Not Working

Verify target-level overrides:

```toml
[tool.hatch.build]
exclude = ["tests/**/*"]

[tool.hatch.build.targets.sdist]
exclude = ["**/.*"]  # This overrides global exclude
```

When you override `exclude` in a target, global `exclude` doesn't apply.

## Configuration Precedence Summary

<eg>
Global [tool.hatch.build]
    ↓ (inherited unless overridden)
Target [tool.hatch.build.targets.<TARGET>]
    ↓ (can be modified by)
Hook [tool.hatch.build.targets.<TARGET>.hooks.<HOOK>]
</eg>

Hooks can modify build data, but can't override TOML settings.

## See Also

- `../build-targets/index.md` - Target configuration details
- `../build-hooks/index.md` - Hook configuration and execution
- `target-dependencies.md` - Dependency configuration
