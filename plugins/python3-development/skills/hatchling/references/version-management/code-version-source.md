---
title: Code Version Source
description: Use Python code execution to determine project versions. Covers simple variable assignments, function calls, complex version logic, search paths, error handling, and performance optimization strategies.
---

# Code Version Source

The code version source plugin determines project versions by executing Python code. This approach provides maximum flexibility for complex versioning scenarios, enabling derivation of versions from multiple sources, application of custom logic, or integration with external systems.

## Basic Configuration

Configure the code version source in `pyproject.toml` as follows:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "code"
path = "src/my_package/__version__.py"
```

## Configuration Options

### Required Options

| Option | Type   | Description                                              |
| ------ | ------ | -------------------------------------------------------- |
| `path` | string | Relative path to the Python file containing version code |

### Optional Options

| Option         | Type   | Default       | Description                                           |
| -------------- | ------ | ------------- | ----------------------------------------------------- |
| `expression`   | string | `__version__` | Python expression to evaluate for the version         |
| `search-paths` | list   | `["."]`       | Additional directories to search for the version file |

## Usage Patterns

### Simple Variable Assignment

Implement the most basic usage by reading a version from a variable:

```toml
[tool.hatch.version]
source = "code"
path = "src/my_package/_version.py"
```

```python
# src/my_package/_version.py
__version__ = "1.2.3"
```

### Function Call

Compute the version with a function:

```toml
[tool.hatch.version]
source = "code"
path = "version.py"
expression = "get_version()"
```

```python
# version.py
def get_version():
    """Calculate version based on current date."""
    from datetime import datetime
    now = datetime.now()
    return f"{now.year}.{now.month}.{now.day}"
```

### Complex Version Logic

Combine multiple sources to determine version:

```toml
[tool.hatch.version]
source = "code"
path = "build/version_helper.py"
expression = "determine_version()"
```

```python
# build/version_helper.py
import os
import subprocess
from pathlib import Path

def determine_version():
    """Determine version from multiple sources."""

    # 1. Check environment variable
    if env_version := os.environ.get("FORCE_VERSION"):
        return env_version

    # 2. Try to get from git tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().lstrip("v")
    except subprocess.CalledProcessError:
        pass

    # 3. Fall back to file
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # 4. Default
    return "0.0.0+dev"
```

### Version with Metadata

Include build metadata in your version:

```python
# src/my_package/_version.py
import os
import subprocess

def get_git_revision():
    """Get current git revision."""
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return revision
    except:
        return "unknown"

def get_version():
    """Get version with build metadata."""
    base_version = "1.2.3"

    if os.environ.get("RELEASE_BUILD"):
        return base_version

    # Add git revision for dev builds
    revision = get_git_revision()
    return f"{base_version}+git.{revision}"

__version__ = get_version()
```

## Search Paths Configuration

Configure multiple locations to search for version files:

```toml
[tool.hatch.version]
source = "code"
path = "_version.py"
search-paths = ["src", "lib", "tools"]
```

Hatchling will search for `_version.py` in:

1. `src/_version.py`
2. `lib/_version.py`
3. `tools/_version.py`

## Loading Extension Modules

The code source supports loading compiled extension modules:

```toml
[tool.hatch.version]
source = "code"
path = "src/my_package/_version.pyd"  # or .so on Unix
expression = "version_string"
```

This is useful for projects that compile version information into binary extensions.

## Global Variables

The code source populates certain global variables when executing your version code:

```python
# These are available in your version file
print(__name__)     # "__main__" during version resolution
print(__file__)     # Absolute path to the version file
print(__cached__)   # None
```

Example using globals:

```python
# version.py
import json
from pathlib import Path

# Use __file__ to find relative resources
config_path = Path(__file__).parent / "version_config.json"
with open(config_path) as f:
    config = json.load(f)

__version__ = config["version"]
```

## Setting Versions

Enable version updates by implementing setter functionality in code:

```python
# src/my_package/_version.py
import json
from pathlib import Path

VERSION_FILE = Path(__file__).parent / "VERSION.json"

def get_version():
    """Read version from JSON file."""
    with open(VERSION_FILE) as f:
        return json.load(f)["version"]

def set_version(new_version):
    """Write version to JSON file."""
    with open(VERSION_FILE, "w") as f:
        json.dump({"version": new_version}, f, indent=2)

__version__ = get_version()
```

Then use the CLI:

```bash
$ hatch version patch
Old: 1.2.3
New: 1.2.4
```

## Performance Considerations

### Import Time

The code source imports and executes Python code, which can be slow:

```python
# SLOW: Imports heavy dependencies
import numpy as np
import pandas as pd

def get_version():
    # Complex computation
    return calculate_version_somehow()
```

```python
# FAST: Minimal imports
def get_version():
    return "1.2.3"
```

### Caching

Implement caching for expensive operations:

```python
# _version.py
import functools
import subprocess

@functools.lru_cache(maxsize=1)
def get_git_version():
    """Cache git version to avoid repeated subprocess calls."""
    result = subprocess.run(
        ["git", "describe", "--tags"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

__version__ = get_git_version()
```

## Error Handling

### Missing Dependencies

Handle missing optional dependencies gracefully:

```python
# version.py
try:
    import git  # Optional dependency
    repo = git.Repo(".")
    __version__ = repo.git.describe("--tags")
except ImportError:
    __version__ = "0.0.0+no-git"
except Exception:
    __version__ = "0.0.0+unknown"
```

### File Not Found

Provide fallbacks for missing files:

```python
from pathlib import Path

def get_version():
    version_file = Path("VERSION")
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0+dev"

__version__ = get_version()
```

## Common Patterns

### Date-Based Versioning

```python
# version.py
from datetime import datetime

def get_version():
    now = datetime.now()
    return f"{now.year}.{now.month}.{now.day}"

__version__ = get_version()
```

### Build Number Integration

```python
# version.py
import os

def get_version():
    base = "1.2.3"
    if build_number := os.environ.get("BUILD_NUMBER"):
        return f"{base}+build.{build_number}"
    return base

__version__ = get_version()
```

### Multi-Source Priority

```python
# version.py
import os
from pathlib import Path

def get_version():
    # Priority order: env var > file > default
    sources = [
        lambda: os.environ.get("VERSION"),
        lambda: Path("VERSION").read_text().strip() if Path("VERSION").exists() else None,
        lambda: "0.0.0+dev"
    ]

    for source in sources:
        if version := source():
            return version

__version__ = get_version()
```

## Integration Examples

### With CI/CD

```python
# version.py
import os

def get_version():
    # Different version for different CI systems
    if os.environ.get("GITHUB_ACTIONS"):
        return f"1.2.3+gh.{os.environ.get('GITHUB_RUN_NUMBER', '0')}"
    elif os.environ.get("GITLAB_CI"):
        return f"1.2.3+gl.{os.environ.get('CI_PIPELINE_ID', '0')}"
    elif os.environ.get("CIRCLECI"):
        return f"1.2.3+ci.{os.environ.get('CIRCLE_BUILD_NUM', '0')}"
    else:
        return "1.2.3+dev"

__version__ = get_version()
```

### With Package Resources

```python
# version.py
import importlib.resources as resources

def get_version():
    # Read version from package resource
    version_bytes = resources.read_text("my_package.data", "VERSION")
    return version_bytes.strip()

__version__ = get_version()
```

## Limitations

1. **No Circular Imports**: Version file cannot import the main package
2. **Build-Time Only**: Code runs during build, not at import time
3. **Side Effects**: Avoid side effects in version code
4. **Dependencies**: Keep dependencies minimal for faster builds

## Best Practices

1. **Keep logic simple**: Complex logic increases build time and failure risk
2. **Handle errors gracefully**: Always provide fallback versions
3. **Avoid side effects**: Do not modify files or state during version resolution
4. **Minimize dependencies**: Use only stdlib modules when possible
5. **Document complex logic**: Explain non-obvious version derivation
6. **Test extensively**: Verify version resolution across different environments

## Troubleshooting

### Import Errors

```python
# Problem: ImportError when resolving version
# Solution: Check Python path and dependencies

# Debug version file
import sys
print("Python path:", sys.path)
print("Searching in:", search_paths)
```

### Execution Errors

```bash
# Debug with verbose output
$ hatch version -v
Executing code source at: src/my_package/_version.py
Expression: __version__
Error: NameError: name '__version__' is not defined
```

### Version Not Updated

```python
# Problem: hatch version patch doesn't update
# Solution: Implement set_version function

def set_version(new_version):
    """This function is required for version updates."""
    # Update your version storage
    pass
```

## See Also

- `regex-version-source.md` - Simpler alternative for file-based versions
- `env-version-source.md` - For CI/CD integration
- `search-paths.md` - Configuring search locations
- `version-source-interface.md` - Plugin API reference
