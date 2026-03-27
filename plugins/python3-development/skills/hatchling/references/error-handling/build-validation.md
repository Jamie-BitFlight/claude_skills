---
category: Error Handling
topics: [build-validation, build-hooks, artifact-validation, metadata-validation, dependency-validation]
related: [./path-validation.md, ./wheel-file-selection.md, ./version-validation.md]
---

# Build-Time Artifact Validation in Hatchling

## Overview

When helping users troubleshoot Hatchling build failures, reference this guide to understand the validation checks performed at build time. Hatchling performs extensive validation during the build process to ensure package integrity and reproducibility. This document covers build-time validation, artifact handling, and error resolution.

## Build Target Validation

### Wheel Target Validation

**Key Validations:**

- File selection options defined
- Force-included paths exist
- Metadata fields valid
- Dependencies parseable
- License expressions valid

**Error Example:**

```python
# During wheel build
File "hatchling/builders/wheel.py", line 405, in build_standard
    for included_file in self.recurse_included_files():
        # Validates all included files exist and are accessible
```

### SDist Target Validation

**Key Validations:**

- Source files exist
- VCS patterns respected
- Required files included
- Archive structure valid

## Build Hooks and Validation

### Build Hook Interface

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class ValidationBuildHook(BuildHookInterface):
    """Custom build validation hook."""

    def initialize(self, version, build_data):
        """Run validation before build starts."""
        self._validate_version(version)
        self._validate_files()
        self._validate_dependencies()

    def _validate_version(self, version):
        """Validate version format."""
        from packaging.version import Version, InvalidVersion
        try:
            Version(version)
        except InvalidVersion:
            raise ValueError(f"Invalid version: {version}")

    def _validate_files(self):
        """Ensure required files exist."""
        required = ["README.md", "LICENSE", "CHANGELOG.md"]
        for file in required:
            if not Path(file).exists():
                raise FileNotFoundError(f"Required file missing: {file}")

    def _validate_dependencies(self):
        """Validate dependency specifications."""
        from packaging.requirements import Requirement, InvalidRequirement

        deps = self.metadata.core.dependencies
        for dep in deps:
            try:
                Requirement(dep)
            except InvalidRequirement:
                raise ValueError(f"Invalid dependency: {dep}")
```

### Build Data Validation

```python
class ArtifactValidationHook(BuildHookInterface):
    """Validate build artifacts."""

    def initialize(self, version, build_data):
        """Add and validate artifacts."""
        # Generate artifacts
        artifacts = self._generate_artifacts()

        # Validate artifacts exist
        for artifact in artifacts:
            if not Path(artifact).exists():
                raise FileNotFoundError(f"Artifact missing: {artifact}")

        # Add to build data
        build_data['artifacts'] = artifacts

    def _generate_artifacts(self):
        """Generate build artifacts."""
        artifacts = []

        # Generate version file
        version_file = Path("src/package/_version.py")
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(f'__version__ = "{self.metadata.version}"')
        artifacts.append(str(version_file))

        return artifacts
```

## File Inclusion Validation

### Force-Include Validation (v1.19.0+)

```toml
[tool.hatch.build.targets.wheel]
force-include = {
    "external/lib.so" = "package/lib.so",  # Must exist
    "../shared/config.json" = "package/config.json"  # Must exist
}
```

**Validation Logic:**

```python
def validate_force_include(force_include):
    """Validate all force-included paths exist."""
    for source, _ in force_include.items():
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(
                f"Force-included path does not exist: {source}"
            )
```

### Artifact Validation

```python
def validate_artifacts(artifacts):
    """Validate build artifacts."""
    for artifact in artifacts:
        path = Path(artifact)

        # Check existence
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact}")

        # Check accessibility
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Cannot read artifact: {artifact}")

        # Check size (prevent huge files)
        if path.stat().st_size > 100_000_000:  # 100MB
            raise ValueError(f"Artifact too large: {artifact}")
```

## Metadata Validation

### Field Validation

```python
from hatchling.metadata.core import ProjectMetadata

class MetadataValidator:
    """Validate project metadata."""

    def __init__(self, root_path):
        self.metadata = ProjectMetadata(root_path, None, {})

    def validate(self):
        """Run all metadata validations."""
        self._validate_required_fields()
        self._validate_classifiers()
        self._validate_urls()
        self._validate_dependencies()

    def _validate_required_fields(self):
        """Ensure required fields present."""
        required = ['name', 'version']
        for field in required:
            if not getattr(self.metadata.core, field, None):
                raise ValueError(f"Required field missing: {field}")

    def _validate_classifiers(self):
        """Validate trove classifiers."""
        from trove_classifiers import classifiers as valid_classifiers

        for classifier in self.metadata.core.classifiers:
            if classifier not in valid_classifiers:
                raise ValueError(f"Invalid classifier: {classifier}")

    def _validate_urls(self):
        """Validate project URLs."""
        import urllib.parse

        for label, url in self.metadata.core.urls.items():
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme:
                raise ValueError(f"Invalid URL for {label}: {url}")
```

### Dynamic Metadata Validation

```toml
[project]
dynamic = ["version", "dependencies"]

[tool.hatch.version]
path = "src/package/__about__.py"
```

**Validation During Build:**

```python
def validate_dynamic_metadata(metadata):
    """Validate dynamically generated metadata."""
    # Check version was resolved
    if 'version' in metadata.config.get('dynamic', []):
        if not metadata.version:
            raise ValueError("Dynamic version not resolved")

    # Check dependencies were resolved
    if 'dependencies' in metadata.config.get('dynamic', []):
        if metadata.dependencies is None:
            raise ValueError("Dynamic dependencies not resolved")
```

## Dependency Validation

### Requirement Parsing

```python
from packaging.requirements import Requirement, InvalidRequirement

def validate_dependencies(dependencies):
    """Validate dependency specifications."""
    errors = []

    for dep_str in dependencies:
        try:
            req = Requirement(dep_str)

            # Additional validation
            if req.url and not allow_direct_references:
                errors.append(f"Direct reference not allowed: {dep_str}")

        except InvalidRequirement as e:
            errors.append(f"Invalid requirement: {dep_str} - {e}")

    if errors:
        raise ValueError("\n".join(errors))
```

### Environment Marker Validation

```python
def validate_markers(requirement):
    """Validate environment markers."""
    if requirement.marker:
        try:
            # Evaluate marker syntax
            requirement.marker.evaluate({'extra': ''})
        except Exception as e:
            raise ValueError(f"Invalid marker: {requirement.marker} - {e}")
```

## Build Output Validation

### Wheel Content Validation

```python
import zipfile
from pathlib import Path

def validate_wheel(wheel_path):
    """Validate wheel file contents."""
    with zipfile.ZipFile(wheel_path, 'r') as zf:
        # Check for required files
        names = zf.namelist()

        # Must have dist-info
        dist_info = [n for n in names if '.dist-info/' in n]
        if not dist_info:
            raise ValueError("No .dist-info directory in wheel")

        # Check METADATA file
        metadata_files = [n for n in dist_info if n.endswith('/METADATA')]
        if not metadata_files:
            raise ValueError("No METADATA file in wheel")

        # Validate RECORD file
        record_files = [n for n in dist_info if n.endswith('/RECORD')]
        if not record_files:
            raise ValueError("No RECORD file in wheel")

        # Check for Python files
        py_files = [n for n in names if n.endswith('.py')]
        if not py_files and not bypass_selection:
            raise ValueError("No Python files in wheel")
```

### SDist Content Validation

```python
import tarfile

def validate_sdist(sdist_path):
    """Validate source distribution contents."""
    with tarfile.open(sdist_path, 'r:gz') as tf:
        names = tf.getnames()

        # Must have PKG-INFO
        pkg_info = [n for n in names if n.endswith('/PKG-INFO')]
        if not pkg_info:
            raise ValueError("No PKG-INFO in sdist")

        # Must have pyproject.toml
        pyproject = [n for n in names if n.endswith('/pyproject.toml')]
        if not pyproject:
            raise ValueError("No pyproject.toml in sdist")

        # Check for source files
        py_files = [n for n in names if n.endswith('.py')]
        if not py_files:
            raise ValueError("No Python source files in sdist")
```

## Continuous Validation

### Pre-commit Validation

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-build
        name: Validate Build Configuration
        entry: python scripts/validate_build.py
        language: python
        files: pyproject.toml
        additional_dependencies:
          - hatchling
          - packaging
```

### CI/CD Validation

```yaml
# .github/workflows/validate-build.yml
name: Validate Build

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install hatchling build twine

      - name: Validate metadata
        run: |
          python -m build --wheel .
          twine check dist/*.whl

      - name: Validate wheel contents
        run: |
          unzip -l dist/*.whl
          python scripts/validate_wheel.py dist/*.whl

      - name: Test installation
        run: |
          pip install dist/*.whl
          python -c "import mypackage; print(mypackage.__version__)"
```

## Build Validation Script

```python
#!/usr/bin/env python3
"""Comprehensive build validation script."""

import sys
import subprocess
from pathlib import Path
import tomllib

def validate_build():
    """Run comprehensive build validation."""
    errors = []

    # Load configuration
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    # Validate metadata
    project = config.get("project", {})
    if not project.get("name"):
        errors.append("Missing project name")
    if not project.get("version") and "version" not in project.get("dynamic", []):
        errors.append("Missing project version")

    # Validate build configuration
    build_config = config.get("tool", {}).get("hatch", {}).get("build", {})
    wheel_config = build_config.get("targets", {}).get("wheel", {})

    # Check file selection
    has_selection = any([
        wheel_config.get("packages"),
        wheel_config.get("include"),
        wheel_config.get("only-include"),
        wheel_config.get("force-include"),
        wheel_config.get("bypass-selection")
    ])

    if not has_selection:
        errors.append("No file selection options defined for wheel")

    # Check force-included paths
    force_include = wheel_config.get("force-include", {})
    for source in force_include:
        if not Path(source).exists():
            errors.append(f"Force-included path missing: {source}")

    # Report errors
    if errors:
        print("Build validation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return 1

    print("Build validation passed ✓")
    return 0

if __name__ == "__main__":
    sys.exit(validate_build())
```

## Best Practices

1. **Validate early** in development cycle
2. **Automate validation** in CI/CD
3. **Use build hooks** for custom validation
4. **Test build outputs** before publishing
5. **Document validation requirements**

## Version History

- **v1.19.0**: Added force-include validation
- **v1.19.1**: Build artifacts count for selection
- **v1.22.0**: Improved validation messages
- **v1.12.0**: Better dependency validation

## Related Documentation

- `path-validation.md`
- `wheel-file-selection.md`
- `version-validation.md`
- `metadata-compatibility.md`
