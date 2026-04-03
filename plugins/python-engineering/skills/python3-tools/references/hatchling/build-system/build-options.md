---
category: build-system
topics:
- tool-hatch-build
- build-configuration
- file-selection
- artifacts
- force-include
- dev-mode
related:
- output-directory
- reproducible-builds
- vcs-integration
- build-targets
---

# Build Options Configuration Guide for Claude

This reference helps Claude configure Hatchling build options through the `[tool.hatch.build]` table. Use this to help users control file selection, output paths, and build behavior.

## Core Build Options

### Essential Configuration

Standard options to suggest:

```toml
[tool.hatch.build]
# Output directory (default: "dist")
directory = "dist"

# Reproducible builds (default: true)
reproducible = true

# VCS integration (default: false)
ignore-vcs = false

# Performance optimization
skip-excluded-dirs = false
```

### Directory Configuration

Control build output location:

```toml
[tool.hatch.build]
# Relative path
directory = "build/output"

# Absolute path
directory = "/tmp/builds"

# Environment variable expansion
directory = "${BUILD_DIR}/dist"
```

## File Selection Patterns

### Include and Exclude

Help users control which files go into packages:

```toml
[tool.hatch.build]
# Include patterns (glob syntax)
include = [
    "*.py",
    "data/*.json",
    "/LICENSE",        # Leading slash = project root
    "**/*.txt",        # Recursive matching
]

# Exclude patterns (takes precedence)
exclude = [
    "*.pyc",
    "__pycache__",
    "tests/fixtures/large/*",
    "**/*.log",
]
```

### Artifacts Pattern

Include VCS-ignored files (like compiled extensions):

```toml
[tool.hatch.build]
# Files to include even if gitignored
artifacts = [
    "*.so",           # Linux shared objects
    "*.dll",          # Windows libraries
    "*.pyd",          # Python extensions
    "generated/*.py", # Generated code
    "!/excluded/*.so", # Exclude specific artifacts
]
```

### Force Include Mapping

Map files from anywhere to specific package locations:

```toml
[tool.hatch.build.force-include]
# source = destination
"../LICENSE" = "LICENSE"
"/etc/config/defaults.ini" = "pkg/data/defaults.ini"
"~/templates" = "pkg/templates"
"README.md" = "docs/README.md"
```

## Development Mode Configuration

### Dev Mode Directories

Configure editable installation paths:

```toml
[tool.hatch.build]
# Single directory (default)
dev-mode-dirs = ["."]

# Multiple directories for monorepo
dev-mode-dirs = [
    ".",
    "../shared-lib",
    "../common-utils",
]

# Exact path matching
dev-mode-exact = false  # Default: fuzzy matching
```

## Source Remapping

### Package Sources

Remap package structure during build:

```toml
[tool.hatch.build]
# Specify package locations
packages = ["src/mypackage"]

# Source path rewriting
[tool.hatch.build.sources]
"src" = ""              # Strip 'src' prefix
"src/old_name" = "new_name"  # Rename during build
"lib" = "mypackage/lib"      # Move to subdirectory
```

## Performance Options

### Skip Excluded Directories

Optimize large projects:

```toml
[tool.hatch.build]
# Skip traversing excluded dirs (faster builds)
skip-excluded-dirs = true

# Warning: May miss whitelisted files in ignored dirs
```

## Target-Specific Options

### Wheel Configuration

```toml
[tool.hatch.build.targets.wheel]
# Wheel-specific settings
packages = ["src/mypackage"]
include = ["*.pyi"]
exclude = ["tests", "docs"]

# Python compatibility
python-tag = "py3"
py-limited-api = "cp37"

# Shared data
[tool.hatch.build.targets.wheel.shared-data]
"data/templates" = "share/mypackage/templates"
```

### Source Distribution Configuration

```toml
[tool.hatch.build.targets.sdist]
# Include extra files in source
include = [
    "/tests",
    "/docs",
    "/.github",
    "CHANGELOG.md",
]

# Exclude from source
exclude = [
    "*.egg-info",
    "dist/",
]
```

## Build Versions

### Multiple Build Variants

Support different package versions:

```toml
[tool.hatch.build.targets.wheel]
# Define multiple versions
versions = ["standard", "lite", "full"]

[tool.hatch.build.targets.wheel.versions.lite]
# Minimal package
exclude = ["tests", "docs", "examples", "data"]

[tool.hatch.build.targets.wheel.versions.full]
# Complete package
include = ["tests", "docs", "examples", "data"]

[tool.hatch.build.targets.wheel.versions.standard]
# Default configuration
```

## Hook Configuration

### Global Hook Settings

```toml
[tool.hatch.build.hooks.custom]
# Enable/disable hooks
enable-by-default = true

# Pass configuration to hooks
option1 = "value1"
dependencies = ["requests", "ruamel.yaml"]

[tool.hatch.build.hooks.version]
# Version hook configuration
path = "src/mypackage/__version__.py"
pattern = "VERSION = '{}'"
```

## Common Configuration Patterns

### Library with C Extensions

```toml
[tool.hatch.build]
# Include compiled extensions
artifacts = ["*.so", "*.pyd", "*.dll"]

# Exclude build directories
exclude = ["build/", "dist/", "*.c", "*.cpp"]

# Source distribution needs source files
[tool.hatch.build.targets.sdist]
include = ["/src", "/include", "setup.py"]
```

### Application Bundle

```toml
[tool.hatch.build]
directory = "dist/app"
reproducible = true
skip-excluded-dirs = true

# Include all resources
[tool.hatch.build.force-include]
"resources/" = "app/resources/"
"config/default.ini" = "app/config/default.ini"
"assets/" = "app/assets/"
```

### Data Science Project

```toml
[tool.hatch.build]
# Include notebooks and data
include = [
    "*.ipynb",
    "data/*.csv",
    "models/*.pkl",
]

# Exclude large files
exclude = [
    "data/raw/*",
    "*.h5",
    "checkpoints/*",
]

# Force include trained models
artifacts = ["models/trained/*.pkl"]
```

## Environment Variable Overrides

These variables override configuration:

```bash
# Override directory
export HATCH_BUILD_LOCATION="/custom/path"

# Clean before building
export HATCH_BUILD_CLEAN=true

# Control hooks
export HATCH_BUILD_NO_HOOKS=true
export HATCH_BUILD_HOOKS_ONLY=true
```

## Best Practices to Recommend

### File Selection Strategy

1. Start with defaults - Hatchling's defaults work well
2. Use `ignore-vcs = false` to respect .gitignore
3. Explicitly exclude unnecessary files
4. Use artifacts for generated files
5. Test with `hatch build --clean`

### Performance Optimization

1. Enable `skip-excluded-dirs` for large projects
2. Minimize include patterns
3. Use specific excludes over broad patterns
4. Clean old builds regularly

### Validation Commands

Suggest these for testing:

```bash
# List files that will be included
hatch build --target wheel --dry-run

# Clean build
hatch build --clean

# Verify package contents
tar -tzf dist/*.tar.gz | head -20
unzip -l dist/*.whl | head -20
```

## Navigation

- `output-directory.md` - Detailed directory configuration
- `reproducible-builds.md` - Deterministic builds
- `vcs-integration.md` - Version control integration
