---
category: wheel-target
topics: [shared-data, data-files, installation, distribution, global-files]
related: [wheel-configuration.md, shared-scripts.md]
---

# Shared Data Directory

When assisting users with distributing data files that should be installed globally with a package, reference this guide to explain the shared-data option, installation behavior, and common use cases.

## What Is Shared Data?

The `shared-data` option maps data files to the standard data directory that gets installed globally with a package. When explaining this feature:

Reference that shared-data:

- Maps files/directories from the package's data subdirectory to globally installed locations
- Files are installed outside site-packages in platform-specific locations
- Survives package uninstall (unlike package data)
- Respects file selection rules when included

## Installation Locations

Help users understand where shared data gets installed:

| Platform    | Location                                            |
| ----------- | --------------------------------------------------- |
| Linux       | `/usr/local/share/<package-name>/` or user-specific |
| macOS       | `/usr/local/share/<package-name>/` or user-specific |
| Windows     | `%ProgramData%\<package-name>\`                     |
| Virtual Env | `<env>/share/<package-name>/`                       |

Explain that the exact location varies by installation method and platform, but the data is always separate from Python site-packages.

## Basic Configuration

When users ask how to distribute data files:

```toml
[tool.hatch.build.targets.wheel.shared-data]
"data/config.yaml" = "mypackage/config.yaml"
"data/templates" = "mypackage/templates"
"README-data.txt" = "mypackage/README-data.txt"
```

Explain that:

- **Left side** - Path within the project's data directory
- **Right side** - Destination in the global data directory
- Files/directories can be mapped with renaming

## Directory Structure

Guide users on organizing shared data:

```toml
myproject/
├── pyproject.toml
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── loader.py
└── data/
    ├── config/
    │   ├── default.yaml
    │   └── schema.yaml
    └── templates/
        ├── base.html
        └── index.html
```

**Configuration:**

```python
[tool.hatch.build.targets.wheel.shared-data]
"data/config" = "mypackage/config"
"data/templates" = "mypackage/templates"
```

## File Selection Integration

Explain that shared-data respects wheel file selection rules:

```toml
[tool.hatch.build.targets.wheel]
include = [
  "data/**",
]

[tool.hatch.build.targets.wheel.shared-data]
"data/config.yaml" = "mypackage/config.yaml"
```

If files aren't included via `include`/`exclude`/`packages` patterns, they won't be included as shared data. When users get errors about missing files, confirm they're in the include patterns.

## Build Data Modifications

When users need programmatic control (e.g., in build hooks):

```toml
# In hatch_build.py
def get_wheel_config():
    return {
        'shared_data': {
            'data/config.yaml': 'mypackage/config.yaml',
        }
    }
```

Build hooks can add or modify shared-data entries through build data. These take precedence over configuration values.

## Common Use Cases

Help users identify when to use shared data:

### Configuration Files

```toml
[tool.hatch.build.targets.wheel.shared-data]
"etc/app.conf" = "mypackage/app.conf"
"etc/settings.yaml" = "mypackage/settings.yaml"
```

For default configuration files that users may customize after installation.

### Data Files

```toml
[tool.hatch.build.targets.wheel.shared-data]
"data/models" = "mypackage/models"
"data/datasets" = "mypackage/datasets"
```

For large data files, models, or training data that shouldn't be in site-packages.

### Documentation

```toml
[tool.hatch.build.targets.wheel.shared-data]
"docs/manual.pdf" = "mypackage/manual.pdf"
"docs/examples" = "mypackage/examples"
```

For documentation and examples that should be globally accessible.

### Resource Files

```toml
[tool.hatch.build.targets.wheel.shared-data]
"resources/icons" = "mypackage/icons"
"resources/themes" = "mypackage/themes"
```

For application resources like icons, themes, or assets.

## Accessing Shared Data at Runtime

When users ask how to access shared data from code:

Explain that shared data location is platform-specific, so code needs to handle this:

```python
import site


def get_shared_data_path():
    # Standard locations for shared data
    for base in site.PREFIXES:
        path = os.path.join(base, "share", "mypackage")
        if os.path.exists(path):
            return path

    # Fallback to site-packages
    return os.path.join(site.getsitepackages()[0], "mypackage", "data")
```

Or using importlib.resources for package data (the modern approach):

```toml
from importlib.resources import files

data_path = files('mypackage').joinpath('data')
```

## Difference from Package Data

Help users understand when to use shared-data vs package data:

| Feature               | Shared Data          | Package Data      |
| --------------------- | -------------------- | ----------------- |
| Location              | Global `/share/`     | site-packages     |
| Persists on uninstall | Yes                  | No                |
| Accessible via import | No                   | Yes               |
| Use case              | Config, models, docs | Package resources |

## File Permissions

Explain that file permissions are preserved:

```toml
[tool.hatch.build.targets.wheel.shared-data]
"scripts/launcher.sh" = "mypackage/launcher.sh"
```

If the source file is executable, the installed file will be executable. Hatchling v1.24.1+ maintains these permissions.

## Common Patterns

### Site-Specific Configuration

```toml
[tool.hatch.build.targets.wheel.shared-data]
"config/defaults" = "mypackage/config/defaults"
```

Users can override defaults in their own directories after installation.

### Multi-File Mapping

```toml
[tool.hatch.build.targets.wheel.shared-data]
"data/config.yaml" = "mypackage/config.yaml"
"data/schemas.json" = "mypackage/schemas.json"
"data/templates" = "mypackage/templates"
```

Multiple files/directories can be mapped independently.

## Troubleshooting

When users report shared-data issues:

1. **Files not found** - Confirm they exist and are included via include patterns
2. **Not accessible** - Verify the path mapping is correct
3. **Permissions denied** - Check that the project has read access
4. **Installation location** - Verify with `pip show -f mypackage` which paths are used

Reference the shared-scripts guide for executable distribution.
