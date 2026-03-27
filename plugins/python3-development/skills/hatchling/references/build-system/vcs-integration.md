---
category: build-system
topics:
- vcs-integration
- gitignore
- hgignore
- file-selection
- ignore-vcs
- artifacts
related:
- build-options
- file-selection
- artifacts
---

# VCS Integration Guide for Claude

This reference helps Claude understand how Hatchling integrates with Version Control Systems (Git, Mercurial) to handle file inclusion/exclusion during builds. Use this to help users control VCS ignore file handling.

## Default Behavior

```toml
[tool.hatch.build]
# Default: respect VCS ignore files
ignore-vcs = false
```

When `ignore-vcs = false` (default):

- Files in `.gitignore` are excluded from builds
- Files in `.hgignore` are excluded for Mercurial
- Provides sensible defaults automatically

## Controlling VCS Integration

### Enable VCS Ignore (Default)

```toml
[tool.hatch.build]
# Respect .gitignore/.hgignore
ignore-vcs = false
```

Benefits:

- Automatic exclusion of development files
- Consistent with repository state
- No manual exclude configuration needed

### Disable VCS Ignore

```toml
[tool.hatch.build]
# Ignore all VCS ignore files
ignore-vcs = true
```

When disabled:

- `.gitignore` and `.hgignore` not read
- All matching files included
- Only explicit exclude patterns apply

## File Selection Priority

Help users understand the order (highest to lowest):

1. `force-include` mappings - Always included
2. `artifacts` patterns - Include even if gitignored
3. `exclude` patterns - Explicit exclusions
4. VCS ignore patterns - If `ignore-vcs = false`
5. `include` patterns - Base inclusion

## Including VCS-Ignored Files

### Using Artifacts Pattern

Include normally ignored files:

```toml
[tool.hatch.build]
# Respect gitignore but include specific files
ignore-vcs = false

# Include compiled extensions even if gitignored
artifacts = [
    "*.so",              # Linux shared libraries
    "*.dll",             # Windows DLLs
    "*.pyd",             # Python extensions
    "src/generated/*.py", # Generated Python files
]
```

### Using Force Include

Map and include specific files:

```toml
[tool.hatch.build.force-include]
# Force include even if gitignored
".env.example" = ".env.example"
"build/data/defaults.json" = "mypackage/data/defaults.json"
"dist/bundled.whl" = "mypackage/vendor/bundled.whl"
```

## Common .gitignore Patterns

### Python Project Standard

Help users understand typical patterns:

```gitignore
# Python artifacts
*.py[cod]
__pycache__/
*.so
*.egg-info/
dist/
build/

# Virtual environments
.venv/
venv/
env/

# IDE files
.vscode/
.idea/
*.swp

# Testing
.coverage
.pytest_cache/
.tox/

# Local config
.env
*.log
```

### Whitelisting in .gitignore

Show users how to whitelist:

```gitignore
# Ignore all logs
*.log

# But include important ones
!critical.log
!errors.log

# Ignore build directory
build/

# But include required subdirectory
!build/required/
!build/required/**
```

## Performance Optimization

### Skip Excluded Directories

For large projects with many ignored directories:

```toml
[tool.hatch.build]
# Skip traversing VCS-ignored directories
ignore-vcs = false
skip-excluded-dirs = true
```

Benefits:

- Faster builds for large projects
- Skips node_modules, .git, .venv
- Reduces filesystem operations

Caution:

- May miss whitelisted files in ignored directories
- Test thoroughly with complex .gitignore patterns

## Target-Specific Configuration

### Different Settings per Target

```toml
# Wheels respect VCS
[tool.hatch.build.targets.wheel]
ignore-vcs = false

# Source distributions include everything
[tool.hatch.build.targets.sdist]
ignore-vcs = true
include = [
    "src/",
    "tests/",
    "docs/",
    ".github/",
]
```

## Common Scenarios

### Including Generated Files

When users need generated files in packages:

```toml
[tool.hatch.build]
# Respect .gitignore for most files
ignore-vcs = false

# But include generated files
artifacts = [
    "src/mypackage/_version.py",    # Generated version
    "src/mypackage/schema.py",      # Generated from JSON
    "data/processed/*.pkl",          # Processed data files
]
```

### Monorepo Configuration

For monorepo projects:

```toml
[tool.hatch.build]
# Ignore VCS to control explicitly
ignore-vcs = true

# Include only this package's files
include = [
    "src/package_a/**/*.py",
    "src/package_a/**/*.pyi",
    "README.md",
    "LICENSE",
]

# Exclude other packages
exclude = [
    "src/package_b/",
    "src/package_c/",
]
```

### CI/CD Builds

For clean CI builds:

```yaml
# GitHub Actions
- name: Clean build
  run: |
    # Ensure clean VCS state
    git clean -fdx

    # Build respects .gitignore
    hatch build
```

## Debugging VCS Integration

### Check What's Ignored

Help users debug:

```bash
# Check if file is gitignored
git check-ignore -v myfile.py

# List all ignored files
git ls-files --ignored --exclude-standard

# List tracked files
git ls-files

# See what Hatchling will include (conceptual)
python -c "
from hatchling.builders.wheel import WheelBuilder
from pathlib import Path
builder = WheelBuilder(str(Path.cwd()))
for file in sorted(builder.get_files()):
    print(file)
"
```

## Best Practices to Recommend

### VCS Strategy

1. Keep `ignore-vcs = false` (default) for most projects
2. Use `artifacts` for generated files
3. Document any `ignore-vcs = true` usage
4. Test builds with fresh clones

### File Organization

1. Keep build artifacts in .gitignore
2. Use artifacts pattern for necessary generated files
3. Be explicit about what goes in packages
4. Review .gitignore regularly

### Common Patterns

For standard Python library:

```toml
[tool.hatch.build]
# Use git's ignore patterns
ignore-vcs = false

# Include compiled extensions
artifacts = ["*.so", "*.pyd", "*.dll"]
```

For application with assets:

```toml
[tool.hatch.build]
# Ignore VCS for explicit control
ignore-vcs = true

# Include everything needed
include = [
    "src/**/*.py",
    "assets/**/*",
    "config/*.json",
    "templates/**/*.html",
]
```

## Troubleshooting

### Files Missing from Package

When files are unexpectedly excluded:

```bash
# Check if gitignored
git check-ignore -v missing_file.py

# Solutions:
# 1. Remove from .gitignore
# 2. Use artifacts pattern
# 3. Use force-include
# 4. Set ignore-vcs = true
```

### Unwanted Files Included

When files are unexpectedly included:

```bash
# Check VCS status
git status --ignored

# Solutions:
# 1. Add to .gitignore
# 2. Use exclude patterns
# 3. Keep ignore-vcs = false
```

### Build Size Issues

For large builds:

```toml
[tool.hatch.build]
# Optimize performance
skip-excluded-dirs = true

# Be specific with includes
include = [
    "src/**/*.py",
    "README.md",
    "LICENSE",
]

# Explicit excludes
exclude = [
    "**/__pycache__",
    "**/*.pyc",
    "tests/fixtures/large/*",
]
```

## Navigation

- `build-options.md` - General build configuration
- `../core-concepts/file-selection.md` - Detailed file selection
- `../core-concepts/artifacts.md` - Including VCS-ignored files
