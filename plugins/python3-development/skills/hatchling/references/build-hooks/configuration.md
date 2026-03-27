---
category: Hatchling Build System
topics: [configuration, hooks, pyproject-toml, hook-setup]
related: [index.md, execution-order.md, conditional-execution.md]
---

# Configuration Basics

Build hooks are configured in `pyproject.toml` (or `hatch.toml`) under the `[tool.hatch.build.hooks]` or `[tool.hatch.build.targets.<TARGET_NAME>.hooks]` sections. When helping users set up build hooks, use this reference to guide them through configuration options and patterns.

## Global Build Hooks

Global hooks are applied to all build targets. Configure them in the global build configuration:

```toml
[tool.hatch.build.hooks.<HOOK_NAME>]
# Hook-specific options here
```

**Example: Global custom hook**

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

**Example: Global version hook**

```toml
[tool.hatch.build.hooks.version]
path = "src/myproject/__version__.py"
```

All build targets will execute these hooks during their build process.

## Target-Specific Build Hooks

Target-specific hooks apply only to a designated build target (e.g., `wheel`, `sdist`). Configure them in the target configuration:

```toml
[tool.hatch.build.targets.<TARGET_NAME>.hooks.<HOOK_NAME>]
# Hook-specific options here
```

**Example: Version hook only for wheels**

```toml
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/myproject/__version__.py"
template = '__version__ = "{version}"'
```

**Example: Custom hook only for sdist**

```toml
[tool.hatch.build.targets.sdist.hooks.custom]
path = "build_sdist.py"
```

Target-specific hooks override global configuration for that target.

## Combined Global and Target-Specific Hooks

You can combine global and target-specific hooks. Both will execute in order:

```toml
# Global hook - runs for all targets
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

# Target-specific hook - runs only for wheel target
[tool.hatch.build.targets.wheel.hooks.version]
path = "src/version.txt"
```

When building wheels, both hooks will run (in the order they're defined).

## Hook-Specific Options

Each hook type has its own configuration options. Refer to the specific hook documentation:

- **Custom hooks**: See `custom-build-hooks.md`
- **Version hooks**: See `version-build-hook.md`
- **Third-party hooks**: Refer to the plugin's documentation

## Common Configuration Pattern

Most build hook configurations follow this pattern:

```toml
[tool.hatch.build.hooks.<HOOK_NAME>]
# Enable/disable the hook
enable-by-default = true

# Hook-specific options (vary by hook type)
option1 = "value1"
option2 = ["value2", "value3"]

# Dependencies for the hook
dependencies = ["some-package>=1.0"]

# Runtime dependency requirements
require-runtime-dependencies = false
require-runtime-features = []
```

See `hook-dependencies.md` for details on dependency configuration.

## Configuration Scope Precedence

When the same hook is configured both globally and target-specifically:

1. **Global configuration** applies first
2. **Target-specific configuration** overrides global settings

**Example: Override global hook path for specific target**

```toml
# Global configuration
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"

# Override path for wheel target only
[tool.hatch.build.targets.wheel.hooks.custom]
path = "build/wheel_hook.py"
```

When building wheels, `build/wheel_hook.py` is used. For sdist, `hatch_build.py` is used.

## Verifying Hook Configuration

To verify your hook configuration, use Hatch's introspection:

```bash
# Show all configured hooks
hatch config show

# Build with verbose output to see hook execution
hatch build -v
```

## Configuration File Formats

### pyproject.toml

The standard Python project configuration file:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

### hatch.toml

Project-specific Hatch configuration (takes precedence over pyproject.toml):

```toml
[build.hooks.custom]
path = "hatch_build.py"
```

Both files can be used together, with `hatch.toml` providing overrides.

## Best Practices

1. **Keep hook configuration minimal**: Only specify what's necessary
2. **Use global hooks for shared logic**: When all targets need the same hook
3. **Use target-specific hooks for specialized logic**: When certain targets need different behavior
4. **Document hook dependencies**: Make it clear what external tools or libraries hooks require
5. **Test hook configuration**: Verify hooks run correctly for each target type

## Troubleshooting Configuration Issues

### Hook not running

Check that:

1. Configuration syntax is correct (proper indentation and section names)
2. `enable-by-default` is not set to `false` (unless using `HATCH_BUILD_HOOK_ENABLE_*`)
3. The hook is configured in the right section (global vs target-specific)
4. Required dependencies are specified in `dependencies`

### Hook configuration conflicts

If the same hook is configured both globally and target-specifically:

- Target-specific configuration takes precedence
- Both initialization and finalization will run (in execution order)

See `execution-order.md` for details.
