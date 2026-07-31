---
category: wheel-target
topics: [extra-metadata, metadata-directory, distribution, custom-metadata]
related: [wheel-configuration.md, shared-data.md]
---

# Extra Metadata Directory

When assisting users with shipping additional metadata files in wheels beyond standard wheel metadata, reference this guide to explain the extra-metadata option and its use cases.

## What Is Extra Metadata?

The `extra-metadata` option allows packages to include additional metadata files in a special directory within the wheel. When explaining this feature:

Reference that extra-metadata:

- Ships extra metadata files in an `extra_metadata` directory in the wheel
- Files are installed alongside the wheel's standard metadata
- Useful for custom metadata, supplementary documentation, or build information
- Respects file selection rules when included

## Installation and Access

Help users understand where extra metadata goes:

Extra metadata files are stored in a directory named `extra_metadata` within the wheel's `.dist-info` directory:

```toml
mypackage-1.0.0.dist-info/
├── METADATA
├── WHEEL
├── RECORD
├── entry_points.txt
└── extra_metadata/
    ├── custom.json
    ├── build_info.txt
    └── other_file
```

After installation, these files are accessible relative to the wheel's dist-info directory.

## Basic Configuration

When users ask how to include extra metadata:

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/build-info.txt" = "build-info.txt"
"metadata/custom.json" = "custom.json"
"metadata/provenance" = "provenance"
```

Explain that:

- **Left side** - Path to the metadata file in the project
- **Right side** - Filename/path in the extra_metadata directory
- Can be files or directories

## Common Use Cases

Help users understand when to use extra-metadata:

### Build Information

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/build-timestamp.txt" = "build-timestamp.txt"
"metadata/build-commit.txt" = "build-commit.txt"
```

For recording build-time information like timestamps, commit hashes, or build environment details.

### Custom Metadata

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/provenance.json" = "provenance.json"
"metadata/sbom.json" = "sbom.json"
```

For custom metadata formats like Software Bill of Materials (SBOM), provenance information, or custom JSON metadata.

### Supplementary Documentation

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/CHANGELOG.md" = "CHANGELOG.md"
"metadata/CONTRIBUTORS.txt" = "CONTRIBUTORS.txt"
```

For additional documentation, contributor lists, or changelog entries that should accompany the package.

### Version and Build History

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/version-history.txt" = "version-history.txt"
"metadata/build-matrix.json" = "build-matrix.json"
```

For tracking version history or multi-platform build information.

## Build Data Modifications

When users need programmatic control:

```toml
# In hatch_build.py
import json
from datetime import datetime

def get_wheel_config():
    # Generate build info dynamically
    build_info = {
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'platform': 'linux-x86_64',
    }

    # This would require writing to a file first
    with open('metadata/build-info.json', 'w') as f:
        json.dump(build_info, f)

    return {
        'extra_metadata': {
            'metadata/build-info.json': 'build-info.json',
        }
    }
```

Build hooks can add or modify extra-metadata entries dynamically.

## File Selection Integration

Explain that extra-metadata respects wheel file selection rules:

```toml
[tool.hatch.build.targets.wheel]
include = [
  "metadata/**",
]

[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/custom.json" = "custom.json"
```

If metadata files aren't included via file selection patterns, they won't be included as extra metadata. Users must ensure metadata files are in the include patterns.

## Accessing Extra Metadata at Runtime

When users ask how to read extra metadata from installed wheels:

Explain that accessing extra metadata requires reading from the installed dist-info directory:

```python
import sys
from pathlib import Path


def get_extra_metadata(filename):
    # Find the dist-info directory
    import mypackage

    pkg_path = Path(mypackage.__file__).parent

    # Navigate to dist-info
    dist_info = pkg_path.parent / f"{pkg_path.name}-{__version__}.dist-info"
    extra_metadata_dir = dist_info / "extra_metadata"

    return extra_metadata_dir / filename


# Usage
build_info = get_extra_metadata("build-info.json").read_text()
```

Or using importlib.metadata (Python 3.8+):

```toml
from importlib.metadata import distribution
import json

def get_extra_metadata(filename):
    dist = distribution('mypackage')

    # files() returns metadata files
    for file in dist.files:
        if f'extra_metadata/{filename}' in str(file):
            return file.read_text()

    return None

# Usage
build_info_content = get_extra_metadata('build-info.json')
if build_info_content:
    build_info = json.loads(build_info_content)
```

## Relationship to Other Options

Help users distinguish extra-metadata from similar options:

| Feature               | Extra Metadata               | Shared Data          | Package Data        |
| --------------------- | ---------------------------- | -------------------- | ------------------- |
| Location              | `.dist-info/extra_metadata/` | Global `/share/`     | site-packages       |
| Access                | Via dist-info directory      | File system path     | importlib.resources |
| Use case              | Build info, SBOM, provenance | Config, docs, models | Package resources   |
| Persists on uninstall | No                           | Yes                  | No                  |

## Strict Naming

When users enable strict naming:

```toml
[tool.hatch.build.targets.wheel]
strict-naming = true
```

The extra-metadata directory name also uses the strict naming option. Hatchling v1.6.0+ applies strict-naming to the metadata directory as well as the wheel filename.

## Metadata Format Recommendations

Help users choose appropriate formats:

### JSON for Structured Data

```toml
{
  "build_timestamp": "2024-01-15T10:30:00Z",
  "commit_hash": "abc123def456",
  "build_machine": "ubuntu-latest"
}
```

Ideal for programmatic access, tooling integration.

### Text for Human-Readable Info

<eg>
Build Information
=================
Built: 2024-01-15 10:30:00 UTC
Commit: abc123def456
Machine: ubuntu-latest
</eg>

Better for documentation, changelog-style information.

### SBOM (Software Bill of Materials) Format

```toml
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [...]
}
```

For security tracking and supply chain transparency.

## Versioning Considerations

When users track version information in extra-metadata:

Explain that version information should match the package version. Consider using build hooks to dynamically generate version-specific metadata:

```python
def get_wheel_config():
    from mypackage import __version__

    with open("metadata/version.txt", "w") as f:
        f.write(__version__)

    return {"extra_metadata": {"metadata/version.txt": "version.txt"}}
```

## Common Patterns

### Recording Build Environment

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/python-version.txt" = "python-version.txt"
"metadata/dependencies.json" = "dependencies.json"
"metadata/build-flags.json" = "build-flags.json"
```

Useful for CI/CD environments and reproducible builds.

### Licensing and Attribution

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/LICENSES" = "LICENSES"
"metadata/ATTRIBUTION.txt" = "ATTRIBUTION.txt"
```

For complex licensing scenarios or third-party attribution.

### Debug Information

```toml
[tool.hatch.build.targets.wheel.extra-metadata]
"metadata/debug-symbols.txt" = "debug-symbols.txt"
"metadata/build-log.txt" = "build-log.txt"
```

Useful for debugging deployed packages.

## Troubleshooting

When users report extra-metadata issues:

1. **Files not found** - Confirm metadata files exist and are included via file selection
2. **Directory vs. file** - Ensure the source path type (file or directory) matches intention
3. **Access failures** - Verify the dist-info path includes the extra_metadata directory
4. **Installation issues** - Check with `pip show -f mypackage` to see where files were installed
