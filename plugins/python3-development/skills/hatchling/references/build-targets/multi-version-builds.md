---
name: Hatchling Multi-Version Builds
description: 'Build multiple variants from one source: platform-specific wheels, feature variants, dev vs production, and version-specific configurations'
---

# Multi-Version Build Support

Hatchling supports building multiple versions of a target, allowing you to create different variants of your package from the same source code. This is useful for conditional feature sets, platform-specific builds, or development vs. production variants.

## Understanding Versions

Build target versions are different variants of the same target type, not to be confused with your project's version number.

### Key Concepts

- **Target**: The type of build (wheel, sdist, binary, custom)
- **Version**: A variant of that target with specific configuration
- **Artifact**: The output file produced by building a target version

## Configuration

### Defining Versions

Versions are defined in the target's configuration:

```toml
[tool.hatch.build.targets.<TARGET_NAME>]
versions = [
    "standard",
    "minimal",
    "full",
]
```

### Version-Specific Configuration

Each version can have its own configuration:

```toml
# Base configuration for all versions
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

# Version-specific configurations
[tool.hatch.build.targets.wheel.versions.standard]
# Standard version configuration

[tool.hatch.build.targets.wheel.versions.minimal]
exclude = ["**/tests", "**/docs"]

[tool.hatch.build.targets.wheel.versions.full]
include = ["src/**", "tests/**", "docs/**"]
```

## Building Specific Versions

### Command Line Usage

```bash
# Build all versions of a target
hatch build -t wheel

# Build specific version
hatch build -t wheel:standard

# Build multiple versions
hatch build -t wheel:minimal,full

# Build multiple targets and versions
hatch build -t wheel:standard -t sdist:standard
```

### Verbose Output

```bash
$ hatch -v build -t wheel:standard
[wheel]
Building `wheel` version `standard`
dist/mypackage-1.0.0-py3-none-any.whl
```

## Common Use Cases

### 1. Platform-Specific Wheels

Different wheels for different platforms:

```toml
[tool.hatch.build.targets.wheel]
versions = ["universal", "windows", "linux", "macos"]

[tool.hatch.build.targets.wheel.versions.universal]
# Pure Python wheel
pure-python = true

[tool.hatch.build.targets.wheel.versions.windows]
# Windows-specific build
[tool.hatch.build.targets.wheel.versions.windows.hooks.custom]
platform = "win32"

[tool.hatch.build.targets.wheel.versions.linux]
# Linux-specific build
[tool.hatch.build.targets.wheel.versions.linux.hooks.custom]
platform = "linux"

[tool.hatch.build.targets.wheel.versions.macos]
# macOS-specific build
[tool.hatch.build.targets.wheel.versions.macos.hooks.custom]
platform = "darwin"
```

### 2. Feature Variants

Different feature sets in different versions:

```toml
[tool.hatch.build.targets.wheel]
versions = ["core", "standard", "full"]

[tool.hatch.build.targets.wheel.versions.core]
# Minimal dependencies
packages = ["src/mypackage/core"]
dependencies = []

[tool.hatch.build.targets.wheel.versions.standard]
# Standard features
packages = ["src/mypackage"]
dependencies = ["requests", "click"]

[tool.hatch.build.targets.wheel.versions.full]
# All features
packages = ["src/mypackage"]
dependencies = [
    "requests",
    "click",
    "pandas",
    "numpy",
    "matplotlib",
]
include = ["src/**", "examples/**"]
```

### 3. Development vs Production

Different builds for different environments:

```toml
[tool.hatch.build.targets.wheel]
versions = ["dev", "prod"]

[tool.hatch.build.targets.wheel.versions.dev]
# Development version with debug symbols and tests
include = [
    "src/**",
    "tests/**",
    "*.pdb",  # Debug symbols
]
[tool.hatch.build.targets.wheel.versions.dev.hooks.custom]
debug = true
optimization = false

[tool.hatch.build.targets.wheel.versions.prod]
# Production version, optimized and minimal
exclude = [
    "tests/**",
    "**/*.pyc",
    "**/__pycache__",
    "*.pdb",
]
[tool.hatch.build.targets.wheel.versions.prod.hooks.custom]
debug = false
optimization = true
strip = true
```

## Binary Target Versions

The binary target commonly uses versions for different deployment scenarios:

```toml
[tool.hatch.build.targets.binary]
scripts = ["myapp"]
versions = ["standalone", "portable", "installer"]

[tool.hatch.build.targets.binary.versions.standalone]
python-version = "3.11"
pyapp-version = "latest"

[tool.hatch.build.targets.binary.versions.portable]
python-version = "3.10"  # Broader compatibility
[tool.hatch.build.targets.binary.versions.portable.hooks.custom]
compress = true
single-file = true

[tool.hatch.build.targets.binary.versions.installer]
[tool.hatch.build.targets.binary.versions.installer.hooks.custom]
create-installer = true
include-runtime = true
```

## Custom Builder Versions

Custom builders can implement version-specific logic:

```python
from hatchling.builders.plugin.interface import BuilderInterface


class CustomBuilder(BuilderInterface):
    PLUGIN_NAME = 'custom'

    def get_version_api(self):
        return {
            'minimal': self.build_minimal,
            'standard': self.build_standard,
            'extended': self.build_extended,
        }

    def build_minimal(self, directory, **kwargs):
        """Build with minimal features."""
        config = self.get_version_config('minimal')
        # Minimal build logic
        return artifact_path

    def build_standard(self, directory, **kwargs):
        """Build with standard features."""
        config = self.get_version_config('standard')
        # Standard build logic
        return artifact_path

    def build_extended(self, directory, **kwargs):
        """Build with extended features."""
        config = self.get_version_config('extended')
        # Extended build logic
        return artifact_path

    def get_version_config(self, version):
        """Get configuration for specific version."""
        base_config = self.target_config.copy()
        version_config = self.target_config.get('versions', {}).get(version, {})
        return {**base_config, **version_config}
```

## Quick Decision Guide

**Use multi-version builds when:**

- You need different feature sets (minimal, standard, full)
- You build platform-specific variants (Windows, Linux, macOS)
- You build environment-specific variants (dev, test, prod)

**Avoid multi-version builds if:**

- You only have a single standard build
- All customers get identical packages
- Complexity isn't worth the benefit

## Version Selection Strategy

### Default Version

When no version is specified, the first defined version is used:

```toml
[tool.hatch.build.targets.wheel]
versions = ["standard", "minimal"]  # "standard" is default
```

Or explicitly set default:

```toml
[tool.hatch.build.targets.wheel]
default-version = "minimal"
versions = ["standard", "minimal"]
```

### Building All Versions

Create a build script to build all versions:

```python
# build_all.py
import subprocess
import sys

targets = {
    'wheel': ['minimal', 'standard', 'full'],
    'binary': ['standalone', 'portable'],
}

for target, versions in targets.items():
    for version in versions:
        print(f"Building {target}:{version}")
        result = subprocess.run(
            ['hatch', 'build', '-t', f'{target}:{version}'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Failed to build {target}:{version}")
            print(result.stderr)
            sys.exit(1)
        print(result.stdout)
```

## Conditional Version Building

### Based on Environment

```python
# build_hook.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ConditionalVersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        env = os.environ.get('BUILD_ENV', 'dev')

        if env == 'production' and version == 'dev':
            raise ValueError("Cannot build dev version in production")

        if env == 'dev' and version == 'prod':
            self.app.display_warning("Building production version in dev environment")
```

### Based on Platform

```python
import platform


class PlatformVersionHook(BuildHookInterface):
    def initialize(self, version, build_data):
        system = platform.system().lower()

        version_platforms = {
            'windows': ['Windows'],
            'linux': ['Linux'],
            'macos': ['Darwin'],
            'universal': ['Windows', 'Linux', 'Darwin'],
        }

        if version in version_platforms:
            if platform.system() not in version_platforms[version]:
                raise ValueError(
                    f"Version '{version}' not supported on {platform.system()}"
                )
```

## Version Naming Conventions

### Semantic Naming

Use descriptive names that indicate the version's purpose:

```toml
versions = [
    "minimal",      # Bare minimum functionality
    "standard",     # Default feature set
    "extended",     # Additional features
    "enterprise",   # Full feature set with enterprise additions
]
```

### Platform Naming

For platform-specific versions:

```toml
versions = [
    "any",          # Platform-independent
    "win_amd64",    # Windows 64-bit
    "linux_x86_64", # Linux 64-bit
    "macosx_arm64", # macOS Apple Silicon
]
```

### Environment Naming

For environment-specific versions:

```toml
versions = [
    "dev",          # Development
    "test",         # Testing
    "staging",      # Staging
    "prod",         # Production
]
```

## Version Artifacts

### Output Naming

Versions typically produce artifacts with the same base name:

<eg>
dist/
├── mypackage-1.0.0-py3-none-any.whl  # standard version
├── mypackage-1.0.0-py3-none-any.whl  # minimal version (overwrites!)
└── mypackage-1.0.0-py3-none-any.whl  # full version (overwrites!)
</eg>

### Custom Naming

To avoid overwrites, use build hooks to customize names:

```python
class VersionNameHook(BuildHookInterface):
    def finalize(self, version, build_data):
        if version != 'standard':
            # Modify artifact name to include version
            build_data['tag'] = f"{build_data.get('tag', '')}.{version}"
```

Results in:

<eg>
dist/
├── mypackage-1.0.0-py3-none-any.whl          # standard
├── mypackage-1.0.0-py3-none-any.minimal.whl  # minimal
└── mypackage-1.0.0-py3-none-any.full.whl     # full
</eg>

## Testing Multiple Versions

### Automated Testing

```python
# test_versions.py
import pytest
import subprocess
from pathlib import Path


@pytest.mark.parametrize("version", ["minimal", "standard", "full"])
def test_wheel_versions(tmp_path, version):
    """Test building different wheel versions."""
    result = subprocess.run(
        ['hatch', 'build', '-t', f'wheel:{version}'],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )

    assert result.returncode == 0
    assert Path(tmp_path / 'dist').exists()

    # Version-specific assertions
    if version == 'minimal':
        # Check minimal version specifics
        pass
    elif version == 'standard':
        # Check standard version specifics
        pass
    elif version == 'full':
        # Check full version specifics
        pass
```

### Version Compatibility Testing

```python
def test_version_compatibility():
    """Ensure all versions maintain API compatibility."""
    versions = ['minimal', 'standard', 'full']

    for version in versions:
        # Build version
        subprocess.run(['hatch', 'build', '-t', f'wheel:{version}'])

        # Install and test
        subprocess.run(['pip', 'install', f'dist/*{version}*.whl'])

        # Run compatibility tests
        import mypackage
        assert hasattr(mypackage, 'core_function')
        # Additional compatibility checks
```

## Performance Considerations

### Build Time

Building multiple versions sequentially can be slow:

```python
# Parallel building
from concurrent.futures import ThreadPoolExecutor


def build_version(version):
    subprocess.run(['hatch', 'build', '-t', f'wheel:{version}'])


with ThreadPoolExecutor(max_workers=4) as executor:
    versions = ['minimal', 'standard', 'full', 'extended']
    executor.map(build_version, versions)
```

### Storage

Multiple versions increase storage requirements:

```python
# Clean old versions before building new ones
import shutil
from pathlib import Path


def clean_old_versions(dist_dir='dist'):
    dist_path = Path(dist_dir)
    if dist_path.exists():
        for file in dist_path.glob('*.whl'):
            if any(v in file.name for v in ['minimal', 'full']):
                file.unlink()
```

## Best Practices

### 1. Clear Version Documentation

Document what each version includes:

```toml
[tool.hatch.build.targets.wheel]
# Version Documentation:
# - minimal: Core functionality only, no optional dependencies
# - standard: Recommended for most users, includes common features
# - full: All features, development tools, and documentation
versions = ["minimal", "standard", "full"]
```

### 2. Version Validation

Validate version configurations:

```python
def validate_versions():
    """Validate all version configurations."""
    import tomli

    with open('pyproject.toml', 'rb') as f:
        config = tomli.load(f)

    wheel_config = config['tool']['hatch']['build']['targets']['wheel']
    versions = wheel_config.get('versions', [])

    for version in versions:
        version_config = wheel_config.get('versions', {}).get(version)
        if not version_config:
            print(f"Warning: Version '{version}' has no configuration")
```

### 3. CI/CD Integration

Build versions in CI/CD:

```yaml
# .github/workflows/build.yml
name: Build Multiple Versions

on: [push, pull_request]

jobs:
  build:
    strategy:
      matrix:
        version: [minimal, standard, full]

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install hatch
      - run: hatch build -t wheel:${{ matrix.version }}
      - uses: actions/upload-artifact@v3
        with:
          name: wheel-${{ matrix.version }}
          path: dist/*.whl
```

## See Also

- [Build Configuration](https://hatch.pypa.io/latest/config/build/)
- `wheel-builder.md`
- `binary-builder.md`
- `custom-builder.md`
