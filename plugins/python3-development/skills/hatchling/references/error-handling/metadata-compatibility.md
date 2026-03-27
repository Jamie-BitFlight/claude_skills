---
category: Error Handling
topics: [metadata-compatibility, core-metadata, pep-517, pep-621, pep-639, version-management]
related: [./spdx-validation.md, ./version-validation.md, ./build-validation.md]
---

# Core Metadata Version Compatibility in Hatchling

## Overview

When guiding users through Hatchling metadata configuration, reference this document to help them understand and manage compatibility across different versions of Python package metadata specifications (Core Metadata). This document covers version compatibility, field mapping, and migration strategies.

## Core Metadata Versions

### Current Default: 2.4 (v1.27.0+)

```toml
# Automatically uses latest metadata version
[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"
```

### Version History in Hatchling

| Hatchling Version | Default Metadata | Key Changes                  |
| ----------------- | ---------------- | ---------------------------- |
| v1.27.0+          | 2.4              | Latest license fields format |
| v1.22.1           | 2.3              | Fixed version setting        |
| v1.22.0           | 2.2              | Added dependencies method    |
| v1.12.0+          | 2.1              | License-Expression support   |
| Earlier           | 2.1              | Base support                 |

## License Field Compatibility

### Metadata Version 2.4 (Latest)

```toml
[project]
license = "MIT OR Apache-2.0"
license-files = ["LICENSE*"]
```

**Generated Core Metadata:**

<eg>
Metadata-Version: 2.4
License-Expression: MIT OR Apache-2.0
License-File: LICENSE
</eg>

### Metadata Version 2.3 and Earlier

**Back-Population Behavior (v1.26.2+):**

```toml
[project]
license = "MIT"
```

**Generated Core Metadata:**

<eg>
Metadata-Version: 2.3
License: MIT  # Back-populated for compatibility
</eg>

### Version-Specific Field Handling

```python
# How Hatchling handles license fields by version
if metadata_version >= (2, 4):
    # Use License-Expression and License-File
    write_field("License-Expression", license_expr)
    for file in license_files:
        write_field("License-File", file)
elif metadata_version >= (2, 1):
    # Use License for simple expressions
    if is_simple_license(license_expr):
        write_field("License", license_expr)
    # License-File retroactively supported
else:
    # Older format
    write_field("License", license_text)
```

## Dynamic Metadata Handling

### Source Distribution Metadata

**v1.22.0+ Behavior:**

```toml
[project]
dynamic = ["version", "dependencies"]

[tool.hatch.version]
path = "src/package/__about__.py"
```

**PKG-INFO Priority:**

- Wheel builds from sdist use PKG-INFO
- Dynamic fields only read if explicitly marked
- Prevents duplicate processing

### Metadata Hooks

```python
# Custom metadata hook (v1.22.0+)
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        """Modify metadata during build."""
        # Works with all metadata versions
        metadata['description'] = self.process_description(
            metadata.get('description', '')
        )

    def dependencies(self):
        """Dynamically define dependencies (v1.22.0+)."""
        return ["requests>=2.28.0"]
```

## PEP Compatibility

### PEP 517/660 Compliance

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Fixed Function Signatures (v1.12.1):**

```python
# Correct PEP 517 signatures maintained
def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    pass

def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    pass
```

### PEP 621 Project Metadata

```toml
[project]
name = "package"
version = "1.0.0"
description = "Description"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}  # Old style
# or
license = "MIT"  # SPDX style
authors = [
    {name = "Author", email = "email@example.com"}
]
```

### PEP 639 License Files

```toml
[project]
# Modern format (v1.26.0+)
license-files = [
    "LICENSE",
    "LICENSES/*",
    "NOTICE"
]

# Legacy format (backward compatible)
license-files = {paths = ["LICENSE"], globs = ["licenses/*"]}
```

## Dependency Specification Compatibility

### PEP 508 Dependencies

```toml
[project]
dependencies = [
    "requests>=2.28.0",
    "click>=8.0.0,<9.0.0",
    "numpy>=1.21.0; python_version>='3.8'",
    # Direct references (need allow-direct-references)
    "package @ git+https://github.com/user/repo.git@main"
]
```

### Optional Dependencies with Markers

**Fixed in v1.20.0:**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0; python_version>='3.8'",
    "pytest>=6.0.0; python_version<'3.8'"
]
```

**Generated Metadata:**

<eg>
Requires-Dist: pytest>=7.0.0; python_version>='3.8' and extra == 'dev'
Requires-Dist: pytest>=6.0.0; python_version<'3.8' and extra == 'dev'
</eg>

## Compatibility Configuration

### Allowing Direct References

```toml
[tool.hatch.metadata]
allow-direct-references = true

[project]
dependencies = [
    "package @ git+https://github.com/user/repo.git"
]
```

### Allowing Ambiguous Features (Deprecated)

```toml
# Temporary compatibility option
# Will be removed after Jan 1, 2024
[tool.hatch.metadata]
allow-ambiguous-features = true

[project.optional-dependencies]
# Non-normalized names allowed
Dev-Tools = ["pytest"]
test_utils = ["coverage"]
```

## Migration Strategies

### From Metadata 2.1 to 2.4

```python
#!/usr/bin/env python3
"""Check metadata version compatibility."""

import tomllib
from pathlib import Path

def check_metadata_compatibility():
    """Analyze project for metadata version requirements."""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    project = config.get("project", {})
    issues = []

    # Check license format
    if "license" in project:
        license_val = project["license"]
        if isinstance(license_val, dict):
            issues.append(
                "Using dict-style license - consider SPDX expression"
            )

    # Check for deprecated options
    metadata_config = (
        config.get("tool", {})
        .get("hatch", {})
        .get("metadata", {})
    )

    if metadata_config.get("allow-ambiguous-features"):
        issues.append(
            "allow-ambiguous-features is deprecated"
        )

    return issues
```

### Ensuring Backward Compatibility

```toml
# Support older pip versions
[build-system]
requires = ["hatchling>=1.12.0,<2"]  # Pin major version
build-backend = "hatchling.build"

[project]
# Use simple SPDX identifier for maximum compatibility
license = "MIT"
# Avoid bleeding-edge features
requires-python = ">=3.8"
```

## Testing Metadata Generation

### Validate Generated Metadata

```bash
# Build and inspect metadata
hatch build -t wheel
unzip -p dist/*.whl '*.dist-info/METADATA' | head -20
```

### Test Different Metadata Versions

```python
#!/usr/bin/env python3
"""Test metadata generation for different versions."""

from hatchling.metadata.core import ProjectMetadata
from pathlib import Path

def test_metadata_versions():
    """Generate metadata for different versions."""
    root = Path.cwd()

    # Load project metadata
    metadata = ProjectMetadata(root, None, {})

    # Check core metadata version
    print(f"Core metadata version: {metadata.core.metadata_version}")

    # Validate fields
    core = metadata.core
    print(f"Name: {core.name}")
    print(f"Version: {core.version}")
    print(f"License: {core.license}")
    print(f"License-Expression: {core.license_expression}")
    print(f"License-Files: {core.license_files}")

if __name__ == "__main__":
    test_metadata_versions()
```

## Common Compatibility Issues

### Issue: Fedora Build Failures (v1.12.1)

**Problem:** Function signature regression **Solution:** Fixed in v1.12.1

### Issue: Broken Distribution Dependencies

**Problem:** Encountering broken packages during build **Solution:** Fixed in v1.12.0 with better error handling

### Issue: packaging Library URL Validation

**Problem:** Conflict with context formatting **Solution:** Set minimum packaging>=23.2 (v1.23.0)

### Issue: Source Distribution Field Reading

**Problem:** Dynamic fields read incorrectly from sdist **Solution:** Only read explicitly dynamic fields (v1.22.4)

## Best Practices

1. **Use latest Hatchling** for new projects
2. **Pin major version** for stability
3. **Test with target Python versions**
4. **Validate metadata** before publishing
5. **Use SPDX expressions** for licenses
6. **Avoid deprecated features**

## Debugging Metadata Issues

### Check Effective Metadata

```python
#!/usr/bin/env python3
"""Debug metadata generation."""

import subprocess
import json

def debug_metadata():
    """Extract and display effective metadata."""
    # Build wheel
    subprocess.run(["hatch", "build", "-t", "wheel"], check=True)

    # Extract metadata
    result = subprocess.run(
        ["python", "-m", "zipfile", "-l", "dist/*.whl"],
        capture_output=True,
        text=True,
        shell=True
    )

    print("Wheel contents:")
    print(result.stdout)

    # Get metadata file
    # ... extract and parse METADATA file ...

if __name__ == "__main__":
    debug_metadata()
```

## Version History

- **v1.27.0**: Default metadata 2.4
- **v1.26.2**: Fixed license back-population
- **v1.26.0**: Updated license-files format
- **v1.22.1**: Fixed metadata version default
- **v1.22.0**: Added dependencies method
- **v1.12.1**: Fixed PEP 517/660 signatures
- **v1.12.0**: Added License-Expression support

## Related Documentation

- `spdx-validation.md`
- `version-validation.md`
- `build-validation.md`
