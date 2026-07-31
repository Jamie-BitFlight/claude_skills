---
name: Hatchling Custom Builder
description: 'Extend Hatchling with custom build targets: implementing BuilderInterface, build hooks, configuration management, and testing strategies'
---

# Custom Builder

Custom builders allow you to create specialized build targets for unique requirements that aren't covered by the standard wheel, sdist, or binary builders. Implement custom builders when you need to generate unique output formats or integrate specialized build processes.

## Creating a Custom Builder

### Basic Structure

Create a Python class that inherits from `BuilderInterface`:

```python
from hatchling.builders.plugin.interface import BuilderInterface


class CustomBuilder(BuilderInterface):
    PLUGIN_NAME = "custom"

    def get_version_api(self):
        return {"standard": self.build_standard}

    def build_standard(self, directory, **kwargs):
        # Your build logic here
        artifact_path = self.build_artifact(directory)
        return artifact_path
```

## Builder Interface

### Required Methods

#### `get_version_api()`

Returns a dictionary mapping version names to build methods:

```python
def get_version_api(self):
    return {"standard": self.build_standard, "minified": self.build_minified, "debug": self.build_debug}
```

#### Build Methods

Each build method receives:

- `directory`: Output directory path
- `**kwargs`: Additional build arguments

Must return the path to the created artifact.

### Available Properties

| Property       | Description                         |
| -------------- | ----------------------------------- |
| `root`         | Project root directory              |
| `plugin_name`  | Name of the builder plugin          |
| `app`          | Application instance                |
| `config`       | Build configuration                 |
| `build_config` | Target-specific build configuration |
| `target_name`  | Name of the build target            |
| `metadata`     | Project metadata                    |

## Configuration

### Registering the Builder

In `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling", "my-custom-builder"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.custom]
# Custom builder configuration
```

### Entry Points

Register your builder as a Hatchling plugin:

```toml
[project.entry-points."hatchling.builders"]
custom = "my_package.builders:CustomBuilder"
```

## Complete Example

### JSON Builder Example

A builder that creates JSON metadata files:

```python
import json
from pathlib import Path
from hatchling.builders.plugin.interface import BuilderInterface


class JSONBuilder(BuilderInterface):
    PLUGIN_NAME = "json"

    def get_version_api(self):
        return {"standard": self.build_standard, "pretty": self.build_pretty}

    def build_standard(self, directory, **kwargs):
        """Build compact JSON metadata."""
        return self._build_json(directory, indent=None)

    def build_pretty(self, directory, **kwargs):
        """Build formatted JSON metadata."""
        return self._build_json(directory, indent=2)

    def _build_json(self, directory, indent):
        """Common JSON building logic."""
        metadata = {
            "name": self.metadata.core.name,
            "version": self.metadata.version,
            "description": self.metadata.core.description,
            "dependencies": list(self.metadata.core.dependencies),
            "files": self.get_included_files(),
        }

        output_file = Path(directory) / f"{self.metadata.core.name}-{self.metadata.version}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=indent)

        return str(output_file)

    def get_included_files(self):
        """Get list of files to document."""
        # Use file selection configuration
        return list(self.get_files())
```

Usage:

```toml
[tool.hatch.build.targets.json]
# Builds package-version.json with metadata
```

## Advanced Features

### File Selection

Access Hatch's file selection system:

```python
def get_included_files(self):
    for file_path in self.get_files():
        # Process each included file
        relative_path = file_path.relative_to(self.root)
        yield str(relative_path)
```

### Configuration Options

Read custom configuration:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.compression = self.target_config.get("compression", "gzip")
    self.include_tests = self.target_config.get("include-tests", False)
```

Configuration in `pyproject.toml`:

```toml
[tool.hatch.build.targets.custom]
compression = "bzip2"
include-tests = true
```

### Build Data Modification

Modify build data for other builders:

```python
def initialize(self, version, build_data):
    """Called before building."""
    build_data["custom_field"] = "custom_value"
    build_data["artifacts"].append("*.custom")
```

## Practical Examples

### Documentation Builder

```python
class DocsBuilder(BuilderInterface):
    PLUGIN_NAME = "docs"

    def get_version_api(self):
        return {"standard": self.build_docs}

    def build_docs(self, directory, **kwargs):
        import subprocess
        from pathlib import Path

        # Build Sphinx documentation
        docs_dir = self.root / "docs"
        output_dir = Path(directory) / "docs"

        subprocess.run(["sphinx-build", "-b", "html", str(docs_dir), str(output_dir)], check=True)

        # Create archive
        archive_name = f"{self.metadata.core.name}-docs-{self.metadata.version}.tar.gz"
        archive_path = Path(directory) / archive_name

        subprocess.run(["tar", "-czf", str(archive_path), "-C", str(directory), "docs"], check=True)

        return str(archive_path)
```

### Installer Builder

```python
class InstallerBuilder(BuilderInterface):
    PLUGIN_NAME = "installer"

    def get_version_api(self):
        return {"windows": self.build_windows, "macos": self.build_macos, "linux": self.build_linux}

    def build_windows(self, directory, **kwargs):
        """Build Windows installer using NSIS."""
        # Create NSIS script
        # Run NSIS compiler
        # Return .exe path
        pass

    def build_macos(self, directory, **kwargs):
        """Build macOS installer package."""
        # Create .app bundle
        # Build .dmg or .pkg
        # Return installer path
        pass

    def build_linux(self, directory, **kwargs):
        """Build Linux packages."""
        # Create .deb or .rpm
        # Return package path
        pass
```

## Build Hooks Integration

### Using Build Hooks

Custom builders can use build hooks:

```python
def build_standard(self, directory, **kwargs):
    # Initialize build data
    build_data = {}

    # Run initialization hooks
    for hook in self.get_build_hooks():
        hook.initialize(self.metadata.version, build_data)

    # Build process
    artifact = self.create_artifact(directory, build_data)

    # Run finalization hooks
    for hook in self.get_build_hooks():
        hook.finalize(self.metadata.version, build_data)

    return artifact
```

### Creating Custom Hooks

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom-hook"

    def initialize(self, version, build_data):
        """Run before build."""
        # Modify build_data
        pass

    def finalize(self, version, build_data):
        """Run after build."""
        # Post-processing
        pass
```

## Error Handling

### Validation

```python
def build_standard(self, directory, **kwargs):
    # Validate configuration
    if not self.target_config.get("required-option"):
        raise ValueError("'required-option' must be specified")

    # Validate environment
    if not shutil.which("required-tool"):
        raise RuntimeError("'required-tool' not found in PATH")

    # Proceed with build
    return self._do_build(directory)
```

### Graceful Failures

```python
def build_standard(self, directory, **kwargs):
    try:
        return self._build_primary(directory)
    except BuildError as e:
        self.logger.warning(f"Primary build failed: {e}")
        return self._build_fallback(directory)
```

## Testing Custom Builders

### Unit Testing

```python
import pytest
from pathlib import Path
from my_builder import CustomBuilder


def test_builder_configuration(tmp_path):
    builder = CustomBuilder(root=tmp_path, plugin_name="custom", config={}, target_config={"option": "value"})

    assert builder.target_config["option"] == "value"


def test_build_artifact(tmp_path, mock_project):
    builder = CustomBuilder(root=mock_project, plugin_name="custom", config={}, target_config={})

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    artifact = builder.build_standard(str(output_dir))
    assert Path(artifact).exists()
```

### Integration Testing

Use Hatch's testing utilities:

```python
from hatch.utils.runner import Runner


def test_integration(tmp_path):
    runner = Runner()
    project_dir = create_test_project(tmp_path)

    result = runner(["build", "-t", "custom"], cwd=project_dir)
    assert result.exit_code == 0
    assert "custom" in result.output
```

## Performance Optimization

### Parallel Processing

```python
import concurrent.futures


def build_standard(self, directory, **kwargs):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for component in self.get_components():
            future = executor.submit(self.build_component, component, directory)
            futures.append(future)

        results = [f.result() for f in futures]

    return self.combine_components(results, directory)
```

### Caching

```python
def build_standard(self, directory, **kwargs):
    cache_key = self.get_cache_key()
    cached_artifact = self.get_cached_artifact(cache_key)

    if cached_artifact and not kwargs.get("force"):
        return cached_artifact

    artifact = self._do_build(directory)
    self.cache_artifact(cache_key, artifact)

    return artifact
```

## Quick Decision Guide

**Create a custom builder when:**

- Standard builders don't produce your required output format (JSON, XML, Docker image, etc.)
- You need to integrate a specialized tool into the build pipeline
- You want to create a domain-specific build system

**Use existing builders instead if:**

- You just need to customize file selection → use wheel/sdist configuration
- You need to modify the build process → use build hooks instead
- You need to integrate another tool → check for third-party builders first

## Best Practices

### 1. Follow Conventions

- Use consistent naming for versions
- Return absolute paths to artifacts
- Respect output directory parameter

### 2. Provide Clear Configuration

```toml
[tool.hatch.build.targets.custom]
# Well-documented options with sensible defaults
compression = "gzip"  # Options: gzip, bzip2, xz
include-source = true
strip-binaries = false
```

### 3. Support Standard Options

Honor common Hatch options:

- File inclusion/exclusion patterns
- VCS ignore files
- Reproducible builds

### 4. Log Progress

```python
def build_standard(self, directory, **kwargs):
    self.app.display_info("Starting custom build...")

    # Build steps with progress
    with self.app.status("Building components..."):
        self.build_components()

    self.app.display_success("Build complete!")
```

## See Also

- [Hatchling Plugin Development](https://hatch.pypa.io/latest/plugins/about/)
- [Build Hook Reference](https://hatch.pypa.io/latest/plugins/build-hook/reference/)
- [Python Packaging - Entry Points](https://packaging.python.org/specifications/entry-points/)
