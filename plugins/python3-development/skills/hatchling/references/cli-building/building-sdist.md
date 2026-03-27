---
category: cli-building
topics: [source-distribution, sdist, file-selection, hatchling]
related: [index.md, overview.md, building-wheels.md, building-all-targets.md, output-customization.md]
---

# Building Source Distributions (sdist) with Hatchling

## Overview

Source distributions (sdist) package the raw source code of Python projects, requiring a build step during installation but providing complete source access. Reference this when helping users configure sdist building, manage file selection with gitignore integration, handle archive structure, and support reproducible builds.

## Command-Line Usage

### Using Hatch

```bash
# Build sdist
hatch build -t sdist

# Build sdist with verbose output
hatch -v build -t sdist

# Build only sdist (skip wheel)
hatch build --target sdist
```

### Using Python's Build Module

```bash
# Build only sdist
python -m build --sdist

# Build sdist with custom output directory
python -m build --sdist --outdir dist/

# Skip dependency check (useful in CI)
python -m build --sdist --skip-dependency-check
```

### Using setuptools (legacy)

```bash
# Legacy method (if setup.py exists)
python setup.py sdist

# With bdist_wheel
python setup.py sdist bdist_wheel
```

## Configuration

Configure sdist in `pyproject.toml`:

```toml
[tool.hatch.build.targets.sdist]
# Include files (uses gitignore-style patterns)
include = [
  "src/**/*.py",
  "tests/**/*.py",
  "README.md",
  "LICENSE",
  "pyproject.toml",
]

# Exclude files (takes precedence over include)
exclude = [
  "*.pyc",
  "__pycache__",
  ".coverage",
  "htmlcov/",
]

# Only include these paths (overrides include)
only-include = [
  "src",
  "tests",
  "README.md",
]

# Ignore VCS ignore files
ignore-vcs = false
```

## Sdist Options

```toml
[tool.hatch.build.targets.sdist]
# Core metadata version
core-metadata-version = "2.4"

# Use strict naming (normalized package names)
strict-naming = true

# Support legacy setup.py installations
support-legacy = false
```

## Default File Selection

When no file selection options are set, sdist includes all files not ignored by VCS (.gitignore, .hgignore).

Always included files:

- `/pyproject.toml`
- `/hatch.toml`
- `/hatch_build.py`
- `/.gitignore` or `/.hgignore`
- Any defined `readme` files
- All defined `license-files`

## Archive Structure

An sdist typically contains:

<eg>
my-package-0.1.0.tar.gz
└── my-package-0.1.0/
    ├── src/
    │   └── mypackage/
    │       ├── __init__.py
    │       └── main.py
    ├── tests/
    │   └── test_main.py
    ├── pyproject.toml
    ├── README.md
    ├── LICENSE
    └── PKG-INFO
</eg>

## Including Additional Files

### Using MANIFEST.in (legacy)

While Hatchling doesn't use `MANIFEST.in`, you can achieve similar results:

```toml
[tool.hatch.build.targets.sdist]
include = [
  "*.txt",
  "docs/**/*.md",
  "data/**/*.json",
]
```

### Force Including Files

```toml
[tool.hatch.build.targets.sdist.force-include]
"../external-data" = "data"
"~/configs/default.yaml" = "config.yaml"
```

## Reproducible Builds

Hatchling creates reproducible sdists by default using SOURCE_DATE_EPOCH:

```bash
# Set specific timestamp
SOURCE_DATE_EPOCH=1609459200 hatch build -t sdist

# Disable reproducible builds
```

```toml
[tool.hatch.build]
reproducible = false
```

## Version Control Integration

By default, sdist respects VCS ignore files:

```toml
[tool.hatch.build.targets.sdist]
# Include files even if gitignored
ignore-vcs = true
```

## Excluding Directories

Certain directories are never included:

- `__pycache__`
- `*.egg-info`
- `.git`
- `.hg`
- `.svn`
- `.tox`
- `.nox`
- `.pytest_cache`
- `node_modules`
- `.mypy_cache`
- `.venv`
- `venv`

## Best Practices

1. **Include all source files**: Ensure all `.py` files are included
2. **Include test files**: Users may want to run tests
3. **Include documentation**: README and LICENSE are essential
4. **Exclude build artifacts**: Don't include `dist/`, `build/`, `*.egg-info`
5. **Use VCS ignore**: Let `.gitignore` handle most exclusions
6. **Test sdist**: Build, extract, and test installation

## Building from Source

Users can install from sdist:

```bash
# Download and extract sdist
tar -xzf my-package-0.1.0.tar.gz
cd my-package-0.1.0

# Install
pip install .

# Or install with build isolation
pip install --no-build-isolation .
```

## Sdist vs Wheel

| Aspect       | Sdist               | Wheel                    |
| ------------ | ------------------- | ------------------------ |
| Format       | `.tar.gz` archive   | `.whl` ZIP file          |
| Contents     | Source code         | Pre-built distribution   |
| Installation | Requires build step | Direct installation      |
| Size         | Usually smaller     | Usually larger           |
| Platform     | Source-only         | Can be platform-specific |
| Use case     | Source distribution | Binary distribution      |

## Troubleshooting

### Files Missing from Sdist

Check your include/exclude patterns:

```bash
# List files that will be included
hatch build -t sdist --dry-run

# Check if files are gitignored
git check-ignore path/to/file
```

### Large Sdist Size

```toml
[tool.hatch.build.targets.sdist]
exclude = [
  "tests/fixtures/**/*",
  "docs/_build/**/*",
  "*.log",
  "*.tmp",
]
```

### Legacy Setup.py Support

For compatibility with older pip versions:

```toml
[tool.hatch.build.targets.sdist]
support-legacy = true
```

## Validation

Validate your sdist:

```bash
# Build sdist
hatch build -t sdist

# List contents
tar -tzf dist/*.tar.gz

# Extract and inspect
tar -xzf dist/*.tar.gz -C /tmp
ls -la /tmp/my-package-*/

# Test installation
pip install dist/*.tar.gz
```

## See Also

- `building-wheels.md`
- `output-customization.md`
- [Source Distribution Format](https://packaging.python.org/specifications/source-distribution-format/)
