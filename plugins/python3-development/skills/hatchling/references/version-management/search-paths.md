---
title: Search Paths Configuration
description: Configure multiple directories for version file discovery. Covers search order, relative paths, monorepo support, and fallback strategies.
---

# Search Paths Configuration

The search paths feature in Hatchling's code version source allows specification of multiple directories where version files can be located. This is particularly useful for monorepos, complex project structures, or when version information might be in different locations depending on the environment.

## Basic Configuration

Configure search paths in your `pyproject.toml`:

```toml
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = ["src", "lib", "tools", "."]
```

Hatchling will search for `_version.py` in this order:

1. `src/_version.py`
2. `lib/_version.py`
3. `tools/_version.py`
4. `./_version.py`

## How Search Paths Work

### Search Order

Directories are searched in the order specified:

```toml
[tool.hatch.version]
source = "code"
path = "version.py"
search-paths = [
    "src/package",       # Check first
    "src",               # Check second
    ".",                 # Check third
]
```

The first matching file is used.

### Relative Paths

All paths are relative to the project root:

```toml
[tool.hatch.version]
source = "code"
path = "__version__.py"
search-paths = [
    "src/my_package",           # {root}/src/my_package/__version__.py
    "lib/core",                 # {root}/lib/core/__version__.py
    "packages/main",            # {root}/packages/main/__version__.py
]
```

### Nested Paths

Support deeply nested structures:

```toml
[tool.hatch.version]
source = "code"
path = "version.py"
search-paths = [
    "src/company/product/core",
    "src/company/product",
    "src/company",
    "src",
]
```

## Use Cases

### Monorepo Structure

For projects with multiple packages:

<eg>
my-monorepo/
├── packages/
│   ├── core/
│   │   └── _version.py
│   ├── cli/
│   │   └── _version.py
│   └── api/
│       └── _version.py
└── pyproject.toml
</eg>

```toml
# Root pyproject.toml
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = [
    "packages/core",    # Primary package
    "packages/cli",     # Fallback
    "packages/api",     # Fallback
]
```

### Development vs Production

Different locations for different environments:

```toml
[tool.hatch.version]
source = "code"
path = "version.py"
search-paths = [
    "build",          # CI/CD generated version
    "src/package",    # Development version
    ".",              # Fallback
]
```

### Platform-Specific Paths

Handle platform differences:

```toml
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = [
    "src/windows",    # Windows-specific
    "src/linux",      # Linux-specific
    "src/macos",      # macOS-specific
    "src/common",     # Cross-platform fallback
]
```

## Complex Examples

### Multiple Version Files

Search for different version file names:

```python
# hatch_build.py
from pathlib import Path

def get_version_paths():
    """Get potential version file locations."""
    search_paths = ["src", "lib", ".", "build"]
    file_names = ["_version.py", "__version__.py", "version.py", "VERSION"]

    for directory in search_paths:
        for filename in file_names:
            path = Path(directory) / filename
            if path.exists():
                return str(path)

    raise FileNotFoundError("No version file found")

# Use in version source configuration
```

### Dynamic Search Paths

Generate search paths based on project structure:

```python
# version_helper.py
import os
from pathlib import Path

def find_version_file():
    """Dynamically find version file."""
    # Look for all Python packages
    packages = []
    for root, dirs, files in os.walk("src"):
        if "__init__.py" in files:
            packages.append(root)

    # Search each package for version file
    for package in packages:
        version_file = Path(package) / "_version.py"
        if version_file.exists():
            return version_file

    # Fallback locations
    fallbacks = [
        Path("VERSION"),
        Path(".version"),
        Path("version.txt"),
    ]

    for fallback in fallbacks:
        if fallback.exists():
            return fallback

    raise FileNotFoundError("No version file found")

# Read version from found file
version_file = find_version_file()
__version__ = version_file.read_text().strip()
```

### Conditional Search Paths

Search based on environment:

```python
# version_loader.py
import os
from pathlib import Path

def get_version():
    """Get version from appropriate source."""
    # Different paths for different environments
    if os.environ.get("CI"):
        search_paths = ["build", "dist"]
    elif os.environ.get("DEVELOPMENT"):
        search_paths = ["src/dev", "src"]
    else:
        search_paths = ["src/package", "src", "."]

    # Search for version file
    for directory in search_paths:
        version_file = Path(directory) / "_version.py"
        if version_file.exists():
            # Execute the version file
            namespace = {}
            exec(version_file.read_text(), namespace)
            return namespace.get("__version__", "0.0.0")

    return "0.0.0+unknown"

__version__ = get_version()
```

## Integration with Other Features

### With Version Build Hook

Combine search paths with build hooks:

```toml
[tool.hatch.version]
source = "code"
path = "version_source.py"
search-paths = ["tools", "scripts", "."]

[tool.hatch.build.hooks.version]
path = "src/my_package/_version.py"
```

This setup:

1. Searches for `version_source.py` in multiple locations
2. Writes the found version to `src/my_package/_version.py` during build

### With Multiple Packages

For projects with multiple Python packages:

```toml
# Main package version
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = [
    "src/main_package",
    "src/core",
    "src",
]

# Build hooks for each package
[tool.hatch.build.hooks.custom]
path = "build_scripts/sync_versions.py"
```

```python
# build_scripts/sync_versions.py
def initialize(version, build_config):
    """Sync version across all packages."""
    packages = ["main_package", "plugin_a", "plugin_b"]

    for package in packages:
        version_file = Path(f"src/{package}/_version.py")
        version_file.write_text(f'__version__ = "{version}"\n')
```

## Error Handling

### File Not Found

When no file is found in any search path:

```python
# version.py with fallback
import sys
from pathlib import Path

def find_version():
    """Search for version with fallback."""
    search_paths = ["src", "lib", "build", "."]
    filename = "_version.py"

    for directory in search_paths:
        path = Path(directory) / filename
        if path.exists():
            namespace = {}
            exec(path.read_text(), namespace)
            return namespace.get("__version__")

    # Fallback strategies
    if "pytest" in sys.modules:
        return "0.0.0+test"
    elif any("sphinx" in arg for arg in sys.argv):
        return "0.0.0+docs"
    else:
        return "0.0.0+dev"

__version__ = find_version()
```

### Multiple Matches

Handle multiple matching files:

```python
# version_resolver.py
from pathlib import Path

def get_version():
    """Get version with conflict resolution."""
    search_paths = ["src", "lib", "."]
    found_versions = []

    for directory in search_paths:
        version_file = Path(directory) / "_version.py"
        if version_file.exists():
            namespace = {}
            exec(version_file.read_text(), namespace)
            version = namespace.get("__version__")
            found_versions.append((str(version_file), version))

    if not found_versions:
        raise FileNotFoundError("No version files found")

    if len(found_versions) > 1:
        # Log warning about multiple versions
        print(f"Warning: Found {len(found_versions)} version files:")
        for path, version in found_versions:
            print(f"  {path}: {version}")

    # Use first found (highest priority)
    return found_versions[0][1]

__version__ = get_version()
```

## Best Practices

### 1. Order by Priority

Place most likely locations first:

```toml
search-paths = [
    "src/package",      # Most specific
    "src",              # Less specific
    ".",                # Fallback
]
```

### 2. Avoid Overlapping Paths

Don't include parent and child directories:

```toml
# Bad - overlapping
search-paths = ["src", "src/package", "src/package/submodule"]

# Good - non-overlapping
search-paths = ["src/package/submodule", "lib", "tools"]
```

### 3. Document Search Strategy

Add comments explaining the search order:

```toml
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = [
    "build",          # CI/CD generated versions (highest priority)
    "src/package",    # Standard location
    ".",              # Fallback for simple projects
]
```

### 4. Use Consistent Naming

Standardize version file names across projects:

```toml
# Always use the same filename
path = "_version.py"  # Consistent across all projects
```

### 5. Test Search Behavior

Verify search paths work correctly:

```python
# test_version_search.py
import tempfile
from pathlib import Path

def test_search_paths():
    """Test version file discovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create directory structure
        (root / "src").mkdir()
        (root / "lib").mkdir()

        # Create version file in lib (lower priority)
        (root / "lib" / "_version.py").write_text('__version__ = "1.0.0"')

        # Should find lib version
        assert find_version(root) == "1.0.0"

        # Create version in src (higher priority)
        (root / "src" / "_version.py").write_text('__version__ = "2.0.0"')

        # Should now find src version
        assert find_version(root) == "2.0.0"
```

## Performance Considerations

### File System Operations

Minimize file system checks:

```python
# Inefficient - checks existence multiple times
for path in search_paths:
    if (Path(path) / "version.py").exists():
        version = (Path(path) / "version.py").read_text()

# Efficient - single Path object
for path in search_paths:
    version_file = Path(path) / "version.py"
    if version_file.exists():
        version = version_file.read_text()
```

### Caching Results

Cache found paths for repeated access:

```python
# cached_version.py
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def find_version_file():
    """Find version file (cached)."""
    search_paths = ["src", "lib", "."]
    for directory in search_paths:
        path = Path(directory) / "_version.py"
        if path.exists():
            return path
    raise FileNotFoundError("Version file not found")

def get_version():
    """Get version from cached file location."""
    version_file = find_version_file()
    namespace = {}
    exec(version_file.read_text(), namespace)
    return namespace["__version__"]

__version__ = get_version()
```

## Troubleshooting

### Debug Search Process

Add debugging to understand search behavior:

```python
# debug_version.py
import os
from pathlib import Path

DEBUG = os.environ.get("DEBUG_VERSION_SEARCH")

def find_version():
    """Find version with debug output."""
    search_paths = ["src", "lib", "build", "."]

    if DEBUG:
        print("Version search starting...")
        print(f"Current directory: {os.getcwd()}")
        print(f"Search paths: {search_paths}")

    for directory in search_paths:
        path = Path(directory) / "_version.py"
        if DEBUG:
            print(f"Checking: {path}")
            print(f"  Exists: {path.exists()}")

        if path.exists():
            if DEBUG:
                print(f"  Found! Using {path}")
            return path

    raise FileNotFoundError(
        f"Version file not found in: {search_paths}"
    )
```

## See Also

- `code-version-source.md`
- `monorepo-setup.md`
- `version-build-hook.md`
- `dynamic-version-overview.md`
