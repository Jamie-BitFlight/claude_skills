---
category: cli-building
topics: [command-line, build-system, hatchling, package-distribution]
related: [overview.md, building-wheels.md, building-sdist.md, python-build-tool.md, local-install.md, output-customization.md]
---

# Hatchling Command-Line Building Reference

## Table of Contents

This comprehensive reference documents command-line building workflows with Hatchling. Use this to help users understand build command options, build target selection, and artifact generation.

### Core Topics

1. **`overview.md`**

   - Quick start with basic build commands
   - Understanding build targets
   - Basic configuration in pyproject.toml

2. **`building-wheels.md`**

   - Building wheel distributions with `hatch build -t wheel`
   - Wheel configuration options
   - Platform-specific wheels
   - Editable wheels for development

3. **`building-sdist.md`**

   - Building sdist with `hatch build -t sdist`
   - File selection and exclusion
   - Archive structure and contents
   - Legacy compatibility options

4. **`building-all-targets.md`**

   - Building both sdist and wheel with `hatch build`
   - Managing multiple build targets
   - Parallel building strategies
   - CI/CD integration

5. **`python-build-tool.md`**

   - Using `python -m build` for building
   - Build isolation and dependencies
   - Configuration settings
   - Comparison with hatch build

6. **`local-install.md`**

   - Installing directly with `pip install .`
   - Editable/development installations
   - Working with optional dependencies
   - Virtual environment setup

7. **`output-customization.md`**
   - Customizing output directories
   - Per-target output locations
   - CI/CD output organization
   - Temporary and versioned builds

## Quick Command Reference

### Building Packages

```bash
# Build all targets (sdist + wheel)
hatch build
python -m build

# Build only wheel
hatch build -t wheel
python -m build --wheel

# Build only sdist
hatch build -t sdist
python -m build --sdist

# Build with custom output directory
python -m build --outdir custom_dist/
```

### Installing Locally

```bash
# Install from current directory
pip install .

# Editable/development install
pip install -e .

# With optional dependencies
pip install -e ".[dev,test]"

# Without build isolation
pip install --no-build-isolation .
```

## Configuration Example

Basic `pyproject.toml` for Hatchling:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
dependencies = ["requests>=2.28.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "black>=22.0.0"]

[tool.hatch.build]
directory = "dist"

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.hatch.build.targets.sdist]
include = ["src/**/*.py", "README.md", "LICENSE"]
```

## Common Use Cases

### Development Workflow

```bash
# Set up development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Make changes and test
pytest

# Build for distribution
hatch build --clean
```

### CI/CD Pipeline

```bash
# Install build tools
pip install build hatch

# Build artifacts
python -m build

# Verify artifacts
ls -la dist/
```

### Release Process

```bash
# Clean previous builds
rm -rf dist/

# Build release artifacts
hatch build

# Verify contents
tar -tzf dist/*.tar.gz | head
unzip -l dist/*.whl | head

# Upload to PyPI
hatch publish
```

## Key Features

- **Standard Compliance**: Full PEP 517/518/621 support
- **Fast Builds**: Efficient file selection and caching
- **Flexible Configuration**: Extensive customization options
- **Multiple Targets**: Support for sdist, wheel, and binary
- **Development Mode**: Editable installations for development
- **Reproducible Builds**: Deterministic output with SOURCE_DATE_EPOCH
- **VCS Integration**: Respects .gitignore by default

## Related Documentation

- [Hatch Documentation](https://hatch.pypa.io/)
- [Python Packaging Guide](https://packaging.python.org/)
- [PEP 517 - Build System Interface](https://www.python.org/dev/peps/pep-0517/)
- [PEP 621 - Project Metadata](https://www.python.org/dev/peps/pep-0621/)
- [PEP 660 - Editable Installs](https://www.python.org/dev/peps/pep-0660/)

## Version Information

This documentation covers:

- Hatchling: 1.25.0+
- Python: 3.8+
- pip: 21.3+
- build: 1.0.0+

Last updated: 2024
