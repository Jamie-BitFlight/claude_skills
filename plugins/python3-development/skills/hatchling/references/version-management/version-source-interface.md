---
title: Version Source Plugin Interface
description: Define custom version source plugins for Hatchling. Covers interface requirements, required methods, configuration, registration, and implementation best practices.
---

# Version Source Plugin Interface

The version source plugin interface defines how custom version sources integrate with Hatchling. This documentation covers API requirements, implementation patterns, and best practices for creating version source plugins.

## Interface Definition

All version source plugins must inherit from `VersionSourceInterface`:

```python
from hatchling.version.source.plugin.interface import VersionSourceInterface

class CustomVersionSource(VersionSourceInterface):
    """Custom version source implementation."""

    PLUGIN_NAME = "custom"  # Required: unique identifier

    def get_version_data(self) -> dict:
        """
        Retrieve version information.

        Returns:
            dict: Must contain 'version' key at minimum
        """
        # Implementation required

    def set_version(self, version: str, version_data: dict) -> None:
        """
        Update the version.

        Args:
            version: New version string
            version_data: Additional version metadata

        Raises:
            NotImplementedError: If setting not supported
        """
        # Optional implementation
```

## Required Attributes

### PLUGIN_NAME

Unique identifier for the plugin:

```python
class GitVersionSource(VersionSourceInterface):
    PLUGIN_NAME = "git"  # Used in pyproject.toml: source = "git"
```

## Inherited Attributes

The base class provides these attributes:

### root

Project root directory as a `pathlib.Path`:

```python
def get_version_data(self):
    # Access project root
    project_file = self.root / "VERSION"
    if project_file.exists():
        return {"version": project_file.read_text().strip()}
```

### config

Configuration dictionary from `pyproject.toml`:

```python
def get_version_data(self):
    # Access configuration
    pattern = self.config.get("pattern", r"__version__ = ['\"]([^'\"]+)['\"]")
    path = self.config.get("path", "src/__about__.py")
```

Configuration comes from:

```toml
[tool.hatch.version]
source = "custom"
path = "version.txt"  # Available as self.config["path"]
pattern = "Version: (.+)"  # Available as self.config["pattern"]
```

## Required Methods

### get_version_data()

Must return a dictionary containing at least the `version` key:

```python
def get_version_data(self) -> dict:
    """Retrieve version information."""
    # Minimal return
    return {"version": "1.2.3"}

    # With metadata
    return {
        "version": "1.2.3",
        "source_file": str(self.root / "VERSION"),
        "raw_version": "v1.2.3",
        "timestamp": datetime.now().isoformat()
    }
```

### Error Handling

Raise descriptive exceptions on errors:

```python
def get_version_data(self) -> dict:
    version_file = self.root / self.config["path"]

    if not version_file.exists():
        raise FileNotFoundError(
            f"Version file not found: {version_file}"
        )

    try:
        version = version_file.read_text().strip()
    except Exception as e:
        raise RuntimeError(
            f"Failed to read version from {version_file}: {e}"
        )

    if not version:
        raise ValueError(
            f"Version file {version_file} is empty"
        )

    return {"version": version}
```

## Optional Methods

### set_version()

Implement to support `hatch version` commands:

```python
def set_version(self, version: str, version_data: dict) -> None:
    """Update the version in the source."""
    version_file = self.root / self.config["path"]
    version_file.write_text(f"{version}\n")
```

If not implemented, raise `NotImplementedError`:

```python
def set_version(self, version: str, version_data: dict) -> None:
    """Version setting not supported."""
    raise NotImplementedError(
        f"The {self.PLUGIN_NAME} source does not support setting versions"
    )
```

## Complete Example: File Version Source

```python
# my_package/hatch_plugins.py
from pathlib import Path
from hatchling.version.source.plugin.interface import VersionSourceInterface

class FileVersionSource(VersionSourceInterface):
    """Read version from a plain text file."""

    PLUGIN_NAME = "file"

    def get_version_data(self) -> dict:
        """Read version from configured file."""
        # Get configuration
        filename = self.config.get("filename", "VERSION")
        strip_prefix = self.config.get("strip_prefix", "")

        # Read file
        version_file = self.root / filename
        if not version_file.exists():
            raise FileNotFoundError(
                f"Version file '{filename}' not found at {version_file}"
            )

        # Parse version
        content = version_file.read_text().strip()
        version = content

        # Strip optional prefix
        if strip_prefix and version.startswith(strip_prefix):
            version = version[len(strip_prefix):]

        return {
            "version": version,
            "raw_content": content,
            "source_file": str(version_file)
        }

    def set_version(self, version: str, version_data: dict) -> None:
        """Write version to file."""
        filename = self.config.get("filename", "VERSION")
        add_prefix = self.config.get("add_prefix", "")

        version_file = self.root / filename
        content = f"{add_prefix}{version}"
        version_file.write_text(content + "\n")
```

Usage in `pyproject.toml`:

```toml
[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "file"
filename = "VERSION.txt"
strip_prefix = "v"
add_prefix = "v"
```

## Advanced Example: Git Tag Source

```python
import subprocess
from pathlib import Path
from hatchling.version.source.plugin.interface import VersionSourceInterface

class GitTagVersionSource(VersionSourceInterface):
    """Derive version from git tags."""

    PLUGIN_NAME = "git-tag"

    def get_version_data(self) -> dict:
        """Get version from git describe."""
        # Configuration
        tag_pattern = self.config.get("tag_pattern", "v*")
        strict = self.config.get("strict", False)

        try:
            # Run git describe
            result = subprocess.run(
                ["git", "describe", "--tags", "--match", tag_pattern],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=True
            )
            raw_version = result.stdout.strip()

        except subprocess.CalledProcessError:
            if strict:
                raise RuntimeError(
                    "No git tags found matching pattern: " + tag_pattern
                )
            # Fallback to commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=True
            )
            commit = result.stdout.strip()
            raw_version = f"0.0.0+g{commit}"

        # Clean version
        version = self._clean_version(raw_version)

        return {
            "version": version,
            "raw_version": raw_version,
            "source": "git"
        }

    def _clean_version(self, raw: str) -> str:
        """Clean git version to PEP 440 format."""
        # Remove 'v' prefix
        if raw.startswith("v"):
            raw = raw[1:]

        # Handle git describe format: 1.2.3-4-gabc123
        parts = raw.split("-")
        if len(parts) == 3 and parts[1].isdigit():
            # Has commits since tag
            base = parts[0]
            commits = parts[1]
            sha = parts[2][1:] if parts[2].startswith("g") else parts[2]
            return f"{base}.post{commits}+g{sha}"

        return raw

    def set_version(self, version: str, version_data: dict) -> None:
        """Create a git tag for the version."""
        tag_prefix = self.config.get("tag_prefix", "v")
        tag_name = f"{tag_prefix}{version}"

        # Check if tag exists
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            cwd=self.root,
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            raise ValueError(f"Tag {tag_name} already exists")

        # Create tag
        subprocess.run(
            ["git", "tag", tag_name],
            cwd=self.root,
            check=True
        )

        print(f"Created git tag: {tag_name}")
```

## Registration

### Entry Points

Register plugins via entry points in `pyproject.toml`:

```toml
[project.entry-points."hatchling.version.source"]
file = "my_package.hatch_plugins:FileVersionSource"
git-tag = "my_package.hatch_plugins:GitTagVersionSource"
```

### Plugin Discovery

Hatchling automatically discovers registered plugins:

```toml
# Now available for use
[tool.hatch.version]
source = "file"  # Uses FileVersionSource
# or
source = "git-tag"  # Uses GitTagVersionSource
```

## Configuration Schema

Document your plugin's configuration:

```python
class CustomVersionSource(VersionSourceInterface):
    """
    Custom version source.

    Configuration:
        path (str): Path to version file (required)
        encoding (str): File encoding (default: utf-8)
        strict (bool): Fail on errors (default: true)
        fallback (str): Fallback version (default: 0.0.0)
    """

    PLUGIN_NAME = "custom"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Validate required configuration
        if "path" not in self.config:
            raise ValueError("'path' configuration is required")
```

## Testing Plugins

### Unit Tests

```python
import pytest
from pathlib import Path
from my_package.hatch_plugins import FileVersionSource

class MockConfig:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = config

def test_file_version_source(tmp_path):
    # Create version file
    version_file = tmp_path / "VERSION.txt"
    version_file.write_text("v1.2.3\n")

    # Create source
    source = FileVersionSource.__new__(FileVersionSource)
    source.root = tmp_path
    source.config = {
        "filename": "VERSION.txt",
        "strip_prefix": "v"
    }

    # Test get_version_data
    data = source.get_version_data()
    assert data["version"] == "1.2.3"
    assert data["raw_content"] == "v1.2.3"

    # Test set_version
    source.config["add_prefix"] = "v"
    source.set_version("2.0.0", {})
    assert version_file.read_text().strip() == "v2.0.0"
```

### Integration Tests

```python
def test_with_hatch(tmp_path, monkeypatch):
    # Create project
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-package"
dynamic = ["version"]

[tool.hatch.version]
source = "file"
filename = "VERSION"

[build-system]
requires = ["hatchling", "my-package"]
build-backend = "hatchling.build"
""")

    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3")

    # Test with hatch
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        ["hatch", "version"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == "1.2.3"
```

## Best Practices

### 1. Fail Fast

Provide clear error messages immediately:

```python
def get_version_data(self):
    if "required_config" not in self.config:
        raise ValueError(
            f"{self.PLUGIN_NAME} source requires 'required_config' in configuration"
        )
```

### 2. Document Configuration

Use docstrings and type hints:

```python
from typing import Dict, Any

class CustomSource(VersionSourceInterface):
    """
    Custom version source.

    Configuration:
        path: Path to version file
        encoding: File encoding (default: utf-8)
    """

    def get_version_data(self) -> Dict[str, Any]:
        """Get version data."""
        pass
```

### 3. Validate Versions

Ensure versions are PEP 440 compliant:

```python
from packaging.version import Version, InvalidVersion

def get_version_data(self):
    version_str = self._read_version()

    try:
        Version(version_str)  # Validate
    except InvalidVersion:
        raise ValueError(
            f"Invalid PEP 440 version: {version_str}"
        )

    return {"version": version_str}
```

### 4. Handle Edge Cases

```python
def get_version_data(self):
    # Handle missing files
    if not path.exists():
        if self.config.get("create_missing"):
            path.write_text("0.0.0")
        else:
            raise FileNotFoundError(f"Version file not found: {path}")

    # Handle empty files
    content = path.read_text().strip()
    if not content:
        return {"version": self.config.get("default", "0.0.0")}
```

### 5. Performance

Cache expensive operations:

```python
class ExpensiveSource(VersionSourceInterface):
    _cache = {}

    def get_version_data(self):
        cache_key = str(self.root)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Expensive operation
        result = self._compute_version()
        self._cache[cache_key] = result
        return result
```

## See Also

- `dynamic-version-overview.md`
- `custom-plugins.md`
- `version-scheme-interface.md`
- `plugin-best-practices.md`
