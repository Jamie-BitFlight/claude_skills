---
category: build-environment
topics: [configuration, environment-setup, dependencies, installer-selection]
related: [build-dependencies-management.md, environment-variables.md, environment-isolation.md, uv-vs-pip-installer.md]
---

# Build Environment Configuration

## Overview

Reference this guide when helping users understand the build environment in hatchling—a specialized environment used by the `hatch build` command and other build operations. It can be fully customized to meet specific build requirements, including dependencies, environment variables, and installer selection.

## Configuration Location

Build environment configuration is defined in `pyproject.toml` under the `[tool.hatch.envs.hatch-build]` section:

```toml
[tool.hatch.envs.hatch-build]
# Configuration options here
```

## Core Configuration Options

### Dependencies

Build environments always include requirements from:

- Build system (`[build-system]` table)
- Build targets
- Build hooks

Additional dependencies can be specified:

```toml
[tool.hatch.envs.hatch-build]
dependencies = [
  "cython",
  "numpy",
  "wheel",
  "setuptools-scm",
]
```

**Note**: It's recommended to use standard mechanisms for build dependencies rather than this option for better compatibility with other tools.

### Environment Variables

Set environment variables during builds:

```toml
[tool.hatch.envs.hatch-build.env-vars]
SOURCE_DATE_EPOCH = "1580601600"
PYTHONPATH = "/custom/path"
CC = "gcc"
CXX = "g++"
CFLAGS = "-O3 -march=native"
```

### Installer Selection

Choose between UV (default) or pip:

```toml
[tool.hatch.envs.hatch-build]
installer = "pip"  # Disable UV, use pip instead
```

Or to explicitly enable UV:

```toml
[tool.hatch.envs.hatch-build]
installer = "uv"  # Use UV (default)
```

## Build System Configuration

### Basic Setup

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### With Additional Build Requirements

```toml
[build-system]
requires = [
  "hatchling>=1.25.0",
  "hatch-vcs",
  "hatch-fancy-pypi-readme",
]
build-backend = "hatchling.build"
```

## Build Targets Configuration

### Wheel Target

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
exclude = [
  "*.pyc",
  "__pycache__",
]
```

### Source Distribution Target

```toml
[tool.hatch.build.targets.sdist]
include = [
  "/src",
  "/tests",
  "/LICENSE",
  "/README.md",
]
exclude = [
  "/.github",
  "/.gitignore",
]
```

## Build Hooks Configuration

### Custom Build Hook

```toml
[tool.hatch.build.hooks.custom]
# Hook-specific configuration
```

### Build Hook Dependencies

```toml
[tool.hatch.build.hooks.your-hook-name]
dependencies = [
  "your-build-hook-plugin",
]
require-runtime-dependencies = true
require-runtime-features = ["feature1", "feature2"]
```

### Conditional Hook Execution

```toml
[tool.hatch.build.hooks.your-hook-name]
enable-by-default = false
```

Control via environment variable:

```bash
export HATCH_BUILD_HOOK_ENABLE_YOUR_HOOK_NAME=true
```

## Environment Types

### Virtual Environment Options

```toml
[tool.hatch.envs.hatch-build]
type = "virtual"  # Default
python = "3.11"
system-packages = false
path = ".venv/build"
```

### Detached Environment

For self-contained build environments:

```toml
[tool.hatch.envs.hatch-build]
detached = true
skip-install = true
```

## Reproducible Builds

### Enable Reproducible Builds (Default)

```toml
[tool.hatch.build]
reproducible = true  # Default
```

### Disable Reproducible Builds

```toml
[tool.hatch.build]
reproducible = false
```

### Set Build Timestamp

```toml
[tool.hatch.envs.hatch-build.env-vars]
SOURCE_DATE_EPOCH = "1580601600"
```

## Platform-Specific Configuration

### Windows-Specific

```toml
[tool.hatch.envs.hatch-build.env-vars]
INCLUDE = "C:\\Program Files\\Microsoft SDKs\\Windows\\v10.0\\Include"
LIB = "C:\\Program Files\\Microsoft SDKs\\Windows\\v10.0\\Lib"
```

### Unix-Specific

```toml
[tool.hatch.envs.hatch-build.env-vars]
LD_LIBRARY_PATH = "/usr/local/lib:$LD_LIBRARY_PATH"
PKG_CONFIG_PATH = "/usr/local/lib/pkgconfig"
```

## Complete Example

```toml
[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[tool.hatch.envs.hatch-build]
dependencies = [
  "cython>=3.0.0",
  "numpy>=1.24.0",
  "setuptools>=65.0",
]
installer = "uv"

[tool.hatch.envs.hatch-build.env-vars]
SOURCE_DATE_EPOCH = "1580601600"
CYTHON_TRACE = "1"
NPY_NUM_BUILD_JOBS = "4"

[tool.hatch.build]
reproducible = true

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.hatch.build.targets.sdist]
include = [
  "/src",
  "/tests",
  "/pyproject.toml",
  "/README.md",
  "/LICENSE",
]
```

## Environment Variables Reference

### Build Control Variables

- `HATCH_BUILD_CLEAN` - Clean build artifacts
- `HATCH_BUILD_CLEAN_HOOKS_AFTER` - Clean after hooks
- `HATCH_BUILD_HOOKS_ONLY` - Run only hooks
- `HATCH_BUILD_NO_HOOKS` - Skip all hooks
- `HATCH_BUILD_HOOKS_ENABLE` - Enable specific hooks
- `HATCH_BUILD_HOOK_ENABLE_<HOOK_NAME>` - Enable named hook
- `HATCH_BUILD_LOCATION` - Build output directory

### Python Variant Variables

- `HATCH_PYTHON_VARIANT_CPU` - CPU optimization level (Linux)
- `HATCH_PYTHON_VARIANT_GIL` - Free-threaded Python variant

## Best Practices

1. **Minimal Build Dependencies**: Only include essential build dependencies
2. **Use Standard Mechanisms**: Prefer `[build-system]` requires over custom dependencies
3. **Reproducible Builds**: Keep reproducible builds enabled for consistency
4. **Environment Isolation**: Use build isolation for clean builds
5. **Version Constraints**: Specify minimum versions for build dependencies
6. **Platform Independence**: Use context formatting for paths

## Troubleshooting

### Build Failures

1. Check build dependencies are installed
2. Verify environment variables are set correctly
3. Try with `--no-isolation` to debug
4. Check for conflicting package versions

### Performance Issues

1. Use UV installer for faster dependency resolution
2. Limit parallel build jobs if memory constrained
3. Use cached builds when possible
4. Consider using binary wheels for dependencies

## Related Topics

- `build-dependencies-management.md`
- `uv-vs-pip-installer.md`
- `environment-variables.md`
- `environment-isolation.md`
