---
name: Hatchling Target-Specific Dependencies
description: 'Configure build-time dependencies per target: runtime dependencies, optional features, conditional dependencies, and dependency isolation'
---

# Target-Specific Dependencies and Features

Build targets in Hatchling can have their own dependencies and features, separate from the project's runtime dependencies. This allows for specialized build environments and conditional inclusion of features during the build process. Essential for C/C++ extensions, documentation builds, and conditional builds.

## Build Target Dependencies

### Basic Configuration

Specify dependencies required for building a specific target:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "wheel-specific-tool>=1.0",
    "build-helper==2.3.0",
]

[tool.hatch.build.targets.custom]
dependencies = [
    "custom-builder-plugin>=1.0.0",
    "compilation-tool",
]
```

### Runtime Dependencies

Include the project's runtime dependencies in the build environment:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "build-tool>=1.0",
]
require-runtime-dependencies = true  # Includes all project dependencies
```

### Runtime Features

Include specific optional dependency groups:

```toml
[project.optional-dependencies]
dev = ["pytest", "black", "mypy"]
docs = ["sphinx", "sphinx-rtd-theme"]
acceleration = ["numba", "cython"]

[tool.hatch.build.targets.wheel]
require-runtime-features = ["acceleration"]  # Only includes acceleration deps
```

## Build Hook Dependencies

Build hooks can also have their own dependencies:

```toml
[tool.hatch.build.hooks.custom]
dependencies = [
    "hook-requirement>=1.0",
]

# Target-specific hook dependencies
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = [
    "wheel-hook-tool",
]
require-runtime-dependencies = true
require-runtime-features = ["build-support"]
```

## Common Patterns

### 1. Compiled Extensions

For packages with C/C++ extensions:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "setuptools>=68.0",
    "wheel>=0.41",
    "cython>=3.0",
    "numpy>=1.24",  # For numpy C API
]

[tool.hatch.build.targets.wheel.hooks.cython]
dependencies = [
    "cython>=3.0",
]
```

### 2. Documentation Building

For targets that build documentation:

```toml
[tool.hatch.build.targets.docs]
dependencies = [
    "sphinx>=7.0",
    "sphinx-rtd-theme>=1.3",
    "myst-parser>=2.0",
    "sphinx-autodoc-typehints>=1.24",
]
require-runtime-dependencies = true  # Need the package itself
```

### 3. Platform-Specific Dependencies

Different dependencies for different platforms:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "universal-tool>=1.0",
    'windows-tool>=2.0; platform_system == "Windows"',
    'unix-tool>=1.5; platform_system != "Windows"',
]
```

## Conditional Dependencies

### Environment-Based

Use environment variables to control dependencies:

```python
# build_hook.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ConditionalDepsHook(BuildHookInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add dependencies based on environment
        if os.environ.get("BUILD_WITH_CUDA"):
            self.dependencies.extend(["cuda-toolkit>=11.0", "cudnn>=8.0"])

        if os.environ.get("BUILD_WITH_MKL"):
            self.dependencies.append("mkl>=2023.0")
```

### Feature-Based

Dependencies based on enabled features:

```toml
[project.optional-dependencies]
ml = ["tensorflow", "scikit-learn"]
viz = ["matplotlib", "seaborn"]
web = ["flask", "requests"]

[tool.hatch.build.targets.wheel]
# Base dependencies always included
dependencies = ["packaging>=23.0"]

# Conditionally include based on ENABLE_FEATURES env var
# Set ENABLE_FEATURES=ml,viz to include those deps
```

```python
# build_hook.py
class FeatureDepsHook(BuildHookInterface):
    def initialize(self, version, build_data):
        features = os.environ.get("ENABLE_FEATURES", "").split(",")

        if "ml" in features:
            build_data["dependencies"].extend(["tensorflow>=2.13", "scikit-learn>=1.3"])

        if "viz" in features:
            build_data["dependencies"].extend(["matplotlib>=3.7", "seaborn>=0.12"])
```

## Build Environment Configuration

### Dedicated Build Environment

Configure a dedicated environment for builds:

```toml
[tool.hatch.envs.build]
dependencies = [
    "build>=1.0",
    "twine>=4.0",
    "wheel>=0.41",
]

[tool.hatch.envs.build.scripts]
clean = "rm -rf dist build *.egg-info"
build-wheel = "hatch build -t wheel"
build-sdist = "hatch build -t sdist"
build-all = ["clean", "build-wheel", "build-sdist"]
```

### Target-Specific Environments

Create separate environments for different build targets:

```toml
# Environment for building wheels
[tool.hatch.envs.wheel-build]
dependencies = [
    "wheel>=0.41",
    "setuptools>=68.0",
]

# Environment for building documentation
[tool.hatch.envs.docs-build]
dependencies = [
    "sphinx>=7.0",
    "sphinx-rtd-theme>=1.3",
]

# Environment for building binaries
[tool.hatch.envs.binary-build]
dependencies = [
    "pyinstaller>=6.0",
    "pyoxidizer>=0.24",
]
```

## Dynamic Dependencies

### Version-Based Dependencies

Different dependencies for different Python versions:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "build-tool>=1.0",
    'typing-extensions>=4.7; python_version < "3.11"',
    'importlib-metadata>=6.8; python_version < "3.10"',
]
```

### Computed Dependencies

Calculate dependencies at build time:

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import sys


class DynamicDepsHook(BuildHookInterface):
    PLUGIN_NAME = "dynamic-deps"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies = self.compute_dependencies()

    def compute_dependencies(self):
        deps = ["base-tool>=1.0"]

        # Add Python version specific deps
        if sys.version_info < (3, 10):
            deps.append("backport-package>=1.0")

        # Add platform specific deps
        if sys.platform == "win32":
            deps.append("windows-compiler>=2.0")
        elif sys.platform == "darwin":
            deps.append("macos-sdk>=13.0")
        else:
            deps.append("gcc>=11.0")

        return deps
```

## Managing Dependency Conflicts

### Isolated Build Environments

Ensure clean build environments:

```toml
[tool.hatch.envs.hatch-build]
# Dedicated environment for builds
installer = "pip"
dependencies = []  # Start with clean slate

[tool.hatch.build.targets.wheel]
dependencies = [
    # Explicitly list all needed dependencies
    "setuptools==68.0.0",  # Pin to exact version
    "wheel==0.41.0",
]
```

### Dependency Resolution

Handle conflicting dependencies:

```python
class ConflictResolver(BuildHookInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resolve_conflicts()

    def resolve_conflicts(self):
        """Resolve dependency conflicts."""
        deps = {}

        # Collect all dependencies
        for dep in self.dependencies:
            name, version = self.parse_dependency(dep)
            if name in deps:
                # Resolve conflict - take higher version
                deps[name] = max(deps[name], version)
            else:
                deps[name] = version

        # Rebuild dependency list
        self.dependencies = [f"{name}>={version}" for name, version in deps.items()]
```

## Feature Detection

### Automatic Feature Detection

Detect available features and adjust dependencies:

```python
class FeatureDetector(BuildHookInterface):
    def initialize(self, version, build_data):
        features = self.detect_features()
        self.add_feature_dependencies(features, build_data)

    def detect_features(self):
        """Detect available system features."""
        features = []

        # Check for CUDA
        if shutil.which("nvcc"):
            features.append("cuda")

        # Check for MKL
        try:
            import mkl

            features.append("mkl")
        except ImportError:
            pass

        # Check for OpenMP
        if self.check_openmp():
            features.append("openmp")

        return features

    def add_feature_dependencies(self, features, build_data):
        """Add dependencies based on detected features."""
        if "cuda" in features:
            build_data["dependencies"].append("cuda-python>=11.0")

        if "mkl" in features:
            build_data["dependencies"].append("mkl-fft>=1.3")

        if "openmp" in features:
            build_data["dependencies"].append("pyomp>=1.0")
```

## Testing with Dependencies

### Mock Dependencies

Test builds with mock dependencies:

```python
# test_build_deps.py
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_dependencies():
    with patch("subprocess.run") as mock_run:
        # Mock successful installation
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


def test_build_with_dependencies(mock_dependencies, tmp_path):
    # Create test project
    (tmp_path / "pyproject.toml").write_text("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
dependencies = ["test-dep>=1.0"]
    """)

    # Run build
    # Assert dependencies were installed
    assert mock_dependencies.called
```

### Dependency Matrix Testing

Test with different dependency combinations:

```python
@pytest.mark.parametrize(
    "deps,expected", [(["numpy>=1.24"], True), (["numpy>=1.24", "scipy>=1.11"], True), (["incompatible>=99.0"], False)]
)
def test_dependency_combinations(deps, expected, tmp_path):
    config = create_build_config(deps)
    result = try_build(tmp_path, config)
    assert result.success == expected
```

## Performance Optimization

### Dependency Caching

Cache resolved dependencies:

```python
import pickle
from pathlib import Path


class CachedDepsHook(BuildHookInterface):
    CACHE_FILE = Path.home() / ".cache" / "hatch" / "deps.pkl"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies = self.get_cached_deps()

    def get_cached_deps(self):
        """Get cached dependencies or compute new ones."""
        cache_key = self.get_cache_key()

        if self.CACHE_FILE.exists():
            with open(self.CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
                if cache.get("key") == cache_key:
                    return cache["deps"]

        # Compute dependencies
        deps = self.compute_dependencies()

        # Cache for next time
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_FILE, "wb") as f:
            pickle.dump({"key": cache_key, "deps": deps}, f)

        return deps

    def get_cache_key(self):
        """Generate cache key based on config."""
        import hashlib

        config_str = str(self.target_config)
        return hashlib.md5(config_str.encode()).hexdigest()
```

### Parallel Dependency Installation

Install dependencies in parallel:

```python
from concurrent.futures import ThreadPoolExecutor
import subprocess


def install_dependency(dep):
    """Install a single dependency."""
    subprocess.run(["pip", "install", dep], check=True)


def install_dependencies_parallel(deps, max_workers=4):
    """Install dependencies in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(install_dependency, dep) for dep in deps]
        for future in futures:
            future.result()  # Wait for completion
```

## Quick Decision Guide

**Use target-specific dependencies when:**

- Your wheel build needs C/C++ tools (setuptools, cython, numpy headers)
- Your docs build needs sphinx and plugins
- Different targets need different tools

**Include runtime dependencies when:**

- Your build hooks need to import from your package
- You're documenting your package and need it available
- Use `require-runtime-dependencies = true`

**Include optional features when:**

- Your build needs a specific feature group (e.g., "acceleration" extras)
- Use `require-runtime-features = ["feature-name"]`

## Best Practices

### 1. Pin Critical Dependencies

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "setuptools==68.0.0",  # Pin exact version
    "wheel>=0.41,<0.42",   # Pin minor version
    "cython~=3.0.0",       # Compatible release
]
```

### 2. Document Dependencies

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "cython>=3.0",        # For compiling .pyx files
    "numpy>=1.24",        # For numpy C API headers
    "setuptools>=68.0",   # For build_ext command
]
```

### 3. Minimize Build Dependencies

Only include what's actually needed:

```toml
# Bad - includes unnecessary dependencies
[tool.hatch.build.targets.wheel]
require-runtime-dependencies = true

# Good - explicit minimal dependencies
[tool.hatch.build.targets.wheel]
dependencies = [
    "packaging>=23.0",
    "wheel>=0.41",
]
```

### 4. Test Dependency Installation

```python
def test_dependencies_installable():
    """Ensure all build dependencies can be installed."""
    import tomli
    import subprocess

    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)

    deps = config["tool"]["hatch"]["build"]["targets"]["wheel"].get("dependencies", [])

    for dep in deps:
        result = subprocess.run(["pip", "install", "--dry-run", dep], capture_output=True)
        assert result.returncode == 0, f"Cannot install {dep}"
```

## Troubleshooting

### Missing Dependencies

Check if dependencies are properly specified:

```bash
hatch env show build
hatch dep show requirements
```

### Conflicting Dependencies

Resolve conflicts explicitly:

```toml
[tool.hatch.build.targets.wheel]
dependencies = [
    "package-a>=1.0,<2.0",  # Restrict version range
    "package-b!=1.5.0",     # Exclude problematic version
]
```

### Platform-Specific Issues

Test on target platforms:

```bash
# Test on different platforms using Docker
docker run -it python:3.11 bash -c "
  pip install hatch &&
  hatch build -t wheel
"
```

## See Also

- [Build Configuration](https://hatch.pypa.io/latest/config/build/)
- [Environment Configuration](https://hatch.pypa.io/latest/config/environment/overview/)
- [Dependency Specification](https://packaging.python.org/specifications/dependency-specifiers/)
