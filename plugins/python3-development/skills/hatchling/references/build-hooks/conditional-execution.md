---
category: Hatchling Build System
topics: [conditional-hooks, enable-by-default, environment-variables, optional-hooks]
related: [configuration.md, environment-variables.md, execution-order.md]
---

# Conditional Hook Execution

Build hooks can be selectively enabled or disabled at build time using the `enable-by-default` configuration option and environment variables. Use this reference when helping users create flexible build workflows that adapt to different environments or optional features.

## Basic Conditional Configuration

By default, all configured hooks are enabled. To make a hook optional, set `enable-by-default` to `false`:

```toml
[tool.hatch.build.hooks.my-hook]
enable-by-default = false
```

When `enable-by-default = false`, the hook will not run unless explicitly enabled via environment variables.

## Enabling Disabled Hooks

### Enable Specific Hook by Name

Enable a specific hook by setting the `HATCH_BUILD_HOOK_ENABLE_<HOOK_NAME>` environment variable:

```bash
HATCH_BUILD_HOOK_ENABLE_MY_HOOK=true hatch build
```

The hook name must be uppercase. If your hook is named `my-hook`, use `MY_HOOK`:

```bash
# Hook name: my-hook
HATCH_BUILD_HOOK_ENABLE_MY_HOOK=true hatch build

# Hook name: cython
HATCH_BUILD_HOOK_ENABLE_CYTHON=true hatch build
```

### Enable All Hooks Globally

To enable all hooks regardless of their `enable-by-default` setting:

```bash
HATCH_BUILD_HOOKS_ENABLE=true hatch build
```

This enables all hooks, including those with `enable-by-default = false`.

## Disabling Hooks

### Disable All Hooks

To skip all hook execution entirely:

```bash
HATCH_BUILD_NO_HOOKS=true hatch build
```

This takes precedence over other environment variables. No hooks will run.

### Disable Specific Hooks

Individual hooks cannot be disabled if `enable-by-default = true`. Instead:

1. Set `enable-by-default = false` for the hook
2. Only enable it when needed

## Use Cases for Conditional Execution

### Optional Build Tool Hooks

Some build tools are only needed in certain contexts:

```toml
[tool.hatch.build.hooks.cython]
enable-by-default = false
dependencies = ["cython>=0.29"]
```

**Build normally** (without Cython):

```bash
hatch build
```

**Build with Cython when needed**:

```bash
HATCH_BUILD_HOOK_ENABLE_CYTHON=true hatch build
```

### Development vs CI Builds

Different hooks may be needed for development and CI:

```toml
# Hook for generating code (only in CI)
[tool.hatch.build.hooks.generate-code]
enable-by-default = false

# Hook for linting (always runs)
[tool.hatch.build.hooks.lint]
enable-by-default = true
```

**Local development build**:

```bash
hatch build
```

**CI build with code generation**:

```bash
HATCH_BUILD_HOOK_ENABLE_GENERATE_CODE=true hatch build
```

### Platform-Specific Hooks

Control hooks based on the build platform:

```toml
[tool.hatch.build.targets.wheel.hooks.macos-specific]
enable-by-default = false
```

**Enable on macOS**:

```bash
# On macOS
HATCH_BUILD_HOOK_ENABLE_MACOS_SPECIFIC=true hatch build
```

### Heavy Processing Hooks

Hooks that are expensive to run can be made optional:

```toml
[tool.hatch.build.hooks.compress-assets]
enable-by-default = false
dependencies = ["pillow", "imageio"]
```

**Quick local builds** (skip compression):

```bash
hatch build
```

**Optimized release builds** (enable compression):

```bash
HATCH_BUILD_HOOK_ENABLE_COMPRESS_ASSETS=true hatch build
```

## Combining Conditions

You can combine multiple environment variables to control different hooks:

```toml
[tool.hatch.build.hooks.hook-a]
enable-by-default = false

[tool.hatch.build.hooks.hook-b]
enable-by-default = false

[tool.hatch.build.hooks.hook-c]
enable-by-default = true
```

**Enable multiple hooks**:

```bash
HATCH_BUILD_HOOK_ENABLE_HOOK_A=true HATCH_BUILD_HOOK_ENABLE_HOOK_B=true hatch build
```

**Enable all hooks**:

```bash
HATCH_BUILD_HOOKS_ENABLE=true hatch build
```

This enables `hook-a`, `hook-b`, and `hook-c`.

## Hook Name to Environment Variable Mapping

Hook names are converted to uppercase and hyphens are converted to underscores for environment variables:

| Hook Name         | Environment Variable                      |
| ----------------- | ----------------------------------------- |
| `my-hook`         | `HATCH_BUILD_HOOK_ENABLE_MY_HOOK`         |
| `cython`          | `HATCH_BUILD_HOOK_ENABLE_CYTHON`          |
| `jupyter-builder` | `HATCH_BUILD_HOOK_ENABLE_JUPYTER_BUILDER` |
| `my_custom_hook`  | `HATCH_BUILD_HOOK_ENABLE_MY_CUSTOM_HOOK`  |

## How Conditional Execution Works

1. **Configuration defines default behavior**: `enable-by-default` specifies whether the hook runs by default
2. **Environment variables override defaults**: `HATCH_BUILD_HOOK_ENABLE_*` variables enable/disable specific hooks
3. **Global disable takes precedence**: `HATCH_BUILD_NO_HOOKS=true` disables all hooks

**Priority (highest to lowest)**:

1. `HATCH_BUILD_NO_HOOKS=true` → Disable all hooks
2. `HATCH_BUILD_HOOK_ENABLE_<NAME>=true` → Enable specific hook
3. `HATCH_BUILD_HOOKS_ENABLE=true` → Enable all hooks
4. `enable-by-default` configuration → Default behavior

## Hooks-Only Execution Mode

Run hooks without performing the actual build:

```bash
HATCH_BUILD_HOOKS_ONLY=true hatch build
```

This runs `initialize()` methods for all enabled hooks but skips the actual build and `finalize()` methods. Useful for:

- Validating hook configuration
- Pre-generating files
- Setting up build environment
- Testing hook logic

## Best Practices

### 1. Use `enable-by-default = false` for Optional Tools

Make hooks optional when they:

- Depend on external tools that may not be installed
- Have significant performance impact
- Are only needed in specific contexts

```toml
[tool.hatch.build.hooks.expensive-tool]
enable-by-default = false
dependencies = ["expensive-tool"]
```

### 2. Document When Hooks Are Needed

Add comments explaining when to enable hooks:

```toml
# Generate Cython extensions for release builds
[tool.hatch.build.hooks.cython]
enable-by-default = false
```

### 3. Provide Clear Environment Variable Names

Use descriptive hook names that make their purpose clear:

```toml
# Good: purpose is clear
[tool.hatch.build.hooks.compile-assets]
enable-by-default = false

# Less clear
[tool.hatch.build.hooks.hook1]
enable-by-default = false
```

### 4. Test Both Enabled and Disabled States

Ensure your build works with and without conditional hooks:

```bash
# Test default (disabled)
hatch build

# Test enabled
HATCH_BUILD_HOOK_ENABLE_CYTHON=true hatch build
```

### 5. Use `HATCH_BUILD_HOOKS_ONLY` for Setup Validation

Verify hooks work before running full build:

```bash
HATCH_BUILD_HOOKS_ONLY=true hatch build
```

## Troubleshooting

### Hook Not Running When Expected

Check:

1. Correct hook name in environment variable (uppercase, hyphens to underscores)
2. Hook is actually configured in `pyproject.toml`
3. Environment variable is set correctly: `export HATCH_BUILD_HOOK_ENABLE_*=true`

### Hook Running When Should Be Disabled

Check:

1. `enable-by-default` is set to `false`
2. `HATCH_BUILD_HOOKS_ENABLE=true` is not set
3. `HATCH_BUILD_NO_HOOKS` is not being used elsewhere

### Multiple Hooks Conflicting

When multiple hooks are conditionally enabled, ensure:

1. They execute in the correct order (see `execution-order.md`)
2. They don't modify the same files/artifacts
3. Dependencies between hooks are satisfied

## Related Topics

- `execution-order.md` - How hooks execute when multiple are enabled
- `configuration.md` - How to configure hooks
- `environment-variables.md` - All build-related environment variables
