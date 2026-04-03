---
category: build-system
topics:
- pep-517
- pep-518
- pep-660
- build-hooks
- build-isolation
- config-settings
related:
- build-system-declaration
- build-options
- reproducible-builds
---

# PEP Standards Implementation Guide for Claude

This reference helps Claude understand and implement Python Enhancement Proposals (PEPs) 517, 518, and 660 in Hatchling projects. Use this to ensure standards compliance when helping users.

## PEP 517 - Build System Interface

### Required Build Hooks

Hatchling implements these required hooks that Claude should understand:

#### build_wheel Hook

```python
# Builds a wheel from the project
# Frontend calls: build_wheel(wheel_directory, config_settings, metadata_directory)
# Returns: Name of created wheel file
```

When users build wheels:

```bash
python -m build --wheel
pip wheel .
hatch build --target wheel
```

#### build_sdist Hook

```python
# Builds source distribution
# Frontend calls: build_sdist(sdist_directory, config_settings)
# Returns: Name of created sdist file
```

When users build source distributions:

```bash
python -m build --sdist
hatch build --target sdist
```

### Optional Hooks for Optimization

#### get_requires_for_build_wheel

Returns additional dependencies needed for building wheels. Hatchling uses this for:

- Extension module dependencies (cmake, cython)
- Build hook requirements
- Platform-specific tools

#### prepare_metadata_for_build_wheel

Generates metadata without building the full wheel. This enables:

- Faster dependency resolution
- Metadata inspection without full build
- Efficient environment preparation

### PEP 660 - Editable Installs

#### build_editable Hook

Creates editable wheels for development:

```python
# Creates wheel that links to development source
# Supports both .pth and import hook methods
```

Configure in pyproject.toml:

```toml
[tool.hatch.build]
dev-mode-dirs = ["."]
dev-mode-exact = false
```

## PEP 518 - Build System Declaration

### pyproject.toml Requirements

Help users structure the build-system table correctly:

```toml
[build-system]
# REQUIRED: Dependencies for build process
requires = ["hatchling>=1.21.0"]

# REQUIRED: Python module path to backend
build-backend = "hatchling.build"
```

### Build Isolation Principles

Explain to users:

1. **Isolated Environment**: Builds happen in clean virtual environment
2. **Declared Dependencies**: Only packages in `requires` are available
3. **No System Packages**: System-wide installations are not accessible
4. **Reproducible Builds**: Same requirements = same environment

## Config Settings Support

### Passing Configuration to Backend

Users can pass settings during build:

```bash
# Pass version override
python -m build --config-setting version=1.0.0

# Pass multiple settings
python -m build \
  --config-setting version=1.0.0 \
  --config-setting pure-python=true
```

### Hatchling Config Settings

Recognized settings to suggest:

```python
config_settings = {
    # Version override
    "version": "1.2.3",

    # Build target options
    "pure-python": "true",
    "py-limited-api": "cp37",

    # Hook control
    "hook.enabled": "false",

    # Output directory
    "directory": "/custom/output",
}
```

## Build Isolation Control

### Standard Isolated Build

Default behavior - recommend for production:

```bash
# pip uses isolation by default
pip install .
pip wheel .

# python -m build uses isolation
python -m build
```

### Development Without Isolation

For debugging only:

```bash
# Skip isolation for development
pip install --no-build-isolation -e .

# Build without isolation
python -m build --no-isolation
```

## Validation Commands for Users

### Check PEP Compliance

Provide these validation commands:

```bash
# Validate PEP 517 compliance
python -m pep517.check .

# Build with strict validation
python -m build --strict

# Test all required hooks
pip install --force-reinstall --no-deps .

# Verify metadata generation
python -m build --wheel --outdir /tmp/test
```

### Common Compliance Issues

Help users resolve these issues:

1. **Missing Required Hooks**

   - Ensure hatchling is in `requires`
   - Verify `build-backend = "hatchling.build"`

2. **Invalid Return Types**

   - Hooks must return strings (filenames)
   - Metadata hook returns directory name

3. **Non-Reproducible Builds**

   - Enable `reproducible = true`
   - Set SOURCE_DATE_EPOCH

4. **Isolation Violations**
   - Declare all build dependencies
   - Don't rely on system packages

## Backend Compatibility

### Hatchling vs Other Backends

Key differences to explain:

| Feature           | Hatchling      | Setuptools   | Poetry         | Flit           |
| ----------------- | -------------- | ------------ | -------------- | -------------- |
| Config File       | pyproject.toml | setup.py/cfg | pyproject.toml | pyproject.toml |
| PEP 517           | Full support   | Full support | Full support   | Full support   |
| PEP 660           | Yes            | Yes          | Yes            | Limited        |
| Dynamic Metadata  | Yes            | Yes          | Limited        | No             |
| Extension Support | Via hooks      | Native       | Limited        | No             |

### Migration Considerations

When helping users migrate:

- Hatchling uses modern standards throughout
- No setup.py required (unlike setuptools)
- More flexible than Poetry/Flit
- Better plugin ecosystem than alternatives

## Best Practices for PEP Compliance

### Recommend to Users

1. **Always declare build dependencies** explicitly
2. **Test in isolated environments** to catch missing dependencies
3. **Version pin for production** builds
4. **Document requirements** for team members
5. **Validate compliance** in CI/CD pipelines

### CI/CD Integration

Suggest PEP-compliant CI workflows:

```yaml
# GitHub Actions example
- name: Build with PEP 517
  run: |
    pip install build
    python -m build --sdist --wheel

- name: Validate packages
  run: |
    pip install check-wheel-contents
    check-wheel-contents dist/*.whl
```

## Benefits to Emphasize

When users ask why PEP compliance matters:

- **Universal Tool Support**: Works with pip, build, poetry, pdm, uv
- **Reproducible Builds**: Consistent across environments
- **Clear Dependencies**: No hidden requirements
- **Future Compatibility**: Standards-based approach
- **Better Caching**: Tools can cache based on requirements

## Navigation

- `build-system-declaration.md` - Configure build-system table
- `build-options.md` - Backend-specific options
- `reproducible-builds.md` - Deterministic builds
