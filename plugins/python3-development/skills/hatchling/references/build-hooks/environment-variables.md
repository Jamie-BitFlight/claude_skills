---
category: Hatchling Build System
topics: [environment-variables, build-control, ci-integration, hook-enablement]
related: [conditional-execution.md, configuration.md, execution-order.md]
---

# Environment Variables

Build hook execution and behavior can be controlled through environment variables. When helping users optimize their build workflows or integrate with CI/CD systems, reference this documentation to show them how to control hook behavior at build time.

## Overview

Environment variables allow:

- Enabling/disabling specific hooks at build time
- Running only hooks without the actual build
- Cleaning hook artifacts
- Controlling whether hooks run in specific scenarios

## Variable Reference

| Variable                              | Default | Description                                      |
| ------------------------------------- | ------- | ------------------------------------------------ |
| `HATCH_BUILD_CLEAN`                   | `false` | Remove existing artifacts before build           |
| `HATCH_BUILD_CLEAN_HOOKS_AFTER`       | `false` | Remove hook artifacts after each build           |
| `HATCH_BUILD_HOOKS_ONLY`              | `false` | Execute hooks but skip actual build              |
| `HATCH_BUILD_NO_HOOKS`                | `false` | Skip all hooks; takes precedence                 |
| `HATCH_BUILD_HOOKS_ENABLE`            | `false` | Enable all hooks (overrides `enable-by-default`) |
| `HATCH_BUILD_HOOK_ENABLE_<HOOK_NAME>` | `false` | Enable specific hook by name                     |
| `HATCH_BUILD_LOCATION`                | `dist`  | Output directory for built artifacts             |

## Individual Variables

### HATCH_BUILD_CLEAN

Remove existing build artifacts before building.

```bash
HATCH_BUILD_CLEAN=true hatch build
```

Equivalent to:

```bash
hatch build -c
# or
hatch build --clean
```

**Effect**:

- Removes contents of output directory before building
- Useful for ensuring clean builds without leftover artifacts
- Triggers `clean()` method in all hooks

### HATCH_BUILD_CLEAN_HOOKS_AFTER

Remove hook-generated artifacts after each build.

```bash
HATCH_BUILD_CLEAN_HOOKS_AFTER=true hatch build
```

**Effect**:

- After `finalize()` runs, temporary hook artifacts are removed
- Useful for keeping working directory clean
- Artifacts still included in final distribution

**Example workflow**:

```bash
# Build and clean temporary hook artifacts
HATCH_BUILD_CLEAN_HOOKS_AFTER=true hatch build

# Working directory is clean, but dist/ contains artifacts
ls dist/
```

### HATCH_BUILD_HOOKS_ONLY

Execute only build hooks, skip the actual build.

```bash
HATCH_BUILD_HOOKS_ONLY=true hatch build
```

**Effect**:

- Runs all enabled `initialize()` methods
- Skips the actual build process
- Skips all `finalize()` methods
- Does not create distribution artifacts

**Use cases**:

- Validate hook setup
- Generate files for inspection
- Pre-build environment setup
- Testing hook logic

**Example**:

```bash
# Validate hooks work correctly
HATCH_BUILD_HOOKS_ONLY=true hatch build

# Check if generated files exist
ls generated/
```

### HATCH_BUILD_NO_HOOKS

Disable all build hooks. Takes precedence over other options.

```bash
HATCH_BUILD_NO_HOOKS=true hatch build
```

**Effect**:

- Skips all configured hooks
- No `initialize()` or `finalize()` methods run
- Ignores `HATCH_BUILD_HOOKS_ENABLE` and hook-specific enables
- Build proceeds without hook modifications

**Use cases**:

- Troubleshoot build issues
- Build without optional hook behavior
- Skip expensive hook operations for quick builds

**Precedence**:

```bash
# Even with HOOKS_ENABLE set, NO_HOOKS takes priority
HATCH_BUILD_HOOKS_ENABLE=true HATCH_BUILD_NO_HOOKS=true hatch build
# No hooks run
```

### HATCH_BUILD_HOOKS_ENABLE

Enable all hooks, overriding `enable-by-default = false`.

```bash
HATCH_BUILD_HOOKS_ENABLE=true hatch build
```

**Effect**:

- All configured hooks run, regardless of `enable-by-default` setting
- Doesn't affect hooks already disabled
- Useful for enabling optional features across the board

**Example**:

```toml
[tool.hatch.build.hooks.cython]
enable-by-default = false

[tool.hatch.build.hooks.numpy]
enable-by-default = false

[tool.hatch.build.hooks.custom]
enable-by-default = true  # Always runs
```

```bash
# Default: only custom hook runs
hatch build

# Enable all hooks
HATCH_BUILD_HOOKS_ENABLE=true hatch build
```

### HATCH*BUILD_HOOK_ENABLE*<HOOK_NAME>

Enable a specific hook, overriding its `enable-by-default` setting.

```bash
HATCH_BUILD_HOOK_ENABLE_<HOOK_NAME>=true hatch build
```

**Format**:

- Hook name in uppercase
- Hyphens converted to underscores
- Case-insensitive value (`true`, `false`, `yes`, `no`)

**Examples**:

```bash
# Hook name: my-hook
HATCH_BUILD_HOOK_ENABLE_MY_HOOK=true hatch build

# Hook name: cython
HATCH_BUILD_HOOK_ENABLE_CYTHON=true hatch build

# Hook name: jupyter-builder
HATCH_BUILD_HOOK_ENABLE_JUPYTER_BUILDER=true hatch build
```

**Hook name to variable mapping**:

| Hook Name         | Environment Variable                      |
| ----------------- | ----------------------------------------- |
| `custom`          | `HATCH_BUILD_HOOK_ENABLE_CUSTOM`          |
| `cython`          | `HATCH_BUILD_HOOK_ENABLE_CYTHON`          |
| `my-hook`         | `HATCH_BUILD_HOOK_ENABLE_MY_HOOK`         |
| `version`         | `HATCH_BUILD_HOOK_ENABLE_VERSION`         |
| `jupyter-builder` | `HATCH_BUILD_HOOK_ENABLE_JUPYTER_BUILDER` |

**Effect**:

- Only the specified hook is enabled
- Other hooks retain their `enable-by-default` setting
- Can be combined with other `ENABLE_*` variables

**Example**:

```bash
# Enable multiple specific hooks
HATCH_BUILD_HOOK_ENABLE_CYTHON=true HATCH_BUILD_HOOK_ENABLE_NUMPY=true hatch build
```

### HATCH_BUILD_LOCATION

Set the output directory for built artifacts.

```bash
HATCH_BUILD_LOCATION=build hatch build
```

**Effect**:

- Changes default output from `dist/` to specified directory
- Directory is created if it doesn't exist
- Only used by the `hatch build` command

**Examples**:

```bash
# Output to build/ directory
HATCH_BUILD_LOCATION=build hatch build

# Output to absolute path
HATCH_BUILD_LOCATION=/tmp/builds hatch build

# Output relative to current directory
HATCH_BUILD_LOCATION=output hatch build
```

## Common Workflows

### Validation Build

Verify hooks work correctly without creating artifacts:

```bash
HATCH_BUILD_HOOKS_ONLY=true hatch build
```

### Clean Build

Remove old artifacts and build fresh:

```bash
HATCH_BUILD_CLEAN=true hatch build
```

Or:

```bash
hatch build -c
hatch build --clean
```

### Build With Optional Hooks

Enable optional hooks for a specific build:

```bash
HATCH_BUILD_HOOK_ENABLE_CYTHON=true HATCH_BUILD_HOOK_ENABLE_NUMPY=true hatch build
```

### Fast Build Without Optional Features

Skip expensive optional hooks:

```bash
HATCH_BUILD_NO_HOOKS=true hatch build
```

### Development Build With Cleanup

Build and clean temporary hook artifacts:

```bash
HATCH_BUILD_CLEAN_HOOKS_AFTER=true hatch build
```

### CI/CD Full Build

Enable all hooks, clean artifacts:

```bash
HATCH_BUILD_CLEAN=true HATCH_BUILD_HOOKS_ENABLE=true hatch build
```

## Setting Environment Variables

### Bash/Linux/macOS

```bash
# Single command
HATCH_BUILD_HOOKS_ONLY=true hatch build

# Export for multiple commands
export HATCH_BUILD_LOCATION=output
hatch build
hatch build -t wheel
```

### Windows (Command Prompt)

```batch
REM Single command
set HATCH_BUILD_HOOKS_ONLY=true && hatch build

REM Export for session
set HATCH_BUILD_LOCATION=output
hatch build
```

### Windows (PowerShell)

```powershell
# Single command
$env:HATCH_BUILD_HOOKS_ONLY='true'; hatch build

# Export for session
$env:HATCH_BUILD_LOCATION='output'
hatch build
```

## Hook Execution with Environment Variables

### Variable Combination Examples

**Enable all hooks, run hooks only**:

```bash
HATCH_BUILD_HOOKS_ENABLE=true HATCH_BUILD_HOOKS_ONLY=true hatch build
```

**Disable all hooks**:

```bash
HATCH_BUILD_NO_HOOKS=true hatch build
```

**Precedence**: `NO_HOOKS` > specific hook enables > `HOOKS_ENABLE`

```bash
# NO_HOOKS takes precedence
HATCH_BUILD_HOOKS_ENABLE=true HATCH_BUILD_NO_HOOKS=true hatch build
# Result: No hooks run
```

### Configuration + Variables

Configuration and environment variables work together:

```toml
[tool.hatch.build.hooks.expensive-hook]
enable-by-default = false
```

**Behavior**:

- Default: Hook doesn't run
- With `HATCH_BUILD_HOOK_ENABLE_EXPENSIVE_HOOK=true`: Hook runs
- With `HATCH_BUILD_HOOKS_ENABLE=true`: Hook runs
- With `HATCH_BUILD_NO_HOOKS=true`: Hook doesn't run (precedence)

## CI/CD Integration

### GitHub Actions

```yaml
name: Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build with all hooks
        env:
          HATCH_BUILD_HOOKS_ENABLE: "true"
          HATCH_BUILD_LOCATION: "dist"
        run: hatch build

      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: dist
          path: dist/
```

### GitLab CI

```yaml
build:
  stage: build
  script:
    - export HATCH_BUILD_HOOKS_ENABLE=true
    - export HATCH_BUILD_LOCATION=dist
    - hatch build
  artifacts:
    paths:
      - dist/
```

## Troubleshooting

### Hook Not Running When Expected

Check:

1. Variable is set correctly: `echo $HATCH_BUILD_HOOK_ENABLE_*`
2. Hook name is correct (uppercase, hyphens to underscores)
3. `HATCH_BUILD_NO_HOOKS` is not set (precedence issue)

### Variable Not Taking Effect

Check:

1. Variable is exported (not just set): `export VAR=value`
2. Variable name spelling is correct
3. Running correct command (`hatch build` not just `build`)

### Hook Running When Should Be Disabled

If a hook is running despite `enable-by-default = false`:

1. Check if `HATCH_BUILD_HOOK_ENABLE_*` is set
2. Check if `HATCH_BUILD_HOOKS_ENABLE` is set
3. Check `HATCH_BUILD_NO_HOOKS` is not set

## Related Topics

- `conditional-execution.md` - Using `enable-by-default` option
- `execution-order.md` - How hooks execute
- `configuration.md` - Hook configuration
