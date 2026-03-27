# Hatchling Special Configuration Options

This directory contains comprehensive documentation for special and advanced configuration options in Hatchling, the modern Python build backend.

## Topics Covered

### `pep-561-type-hinting.md`

Complete guide to distributing type information with your Python packages, including:

- py.typed marker configuration
- Inline type hints vs stub files
- Type checker compatibility
- Namespace packages with types

### `spdx-license-metadata.md`

Comprehensive documentation for license configuration following modern standards:

- SPDX license identifiers and expressions
- PEP 639 License-Expression metadata
- License-File metadata and automatic discovery
- Multi-licensing scenarios and migration guides

### `package-name-normalization.md`

Understanding how Hatchling handles package naming:

- PEP 503/508 normalization rules
- strict-naming option for build artifacts
- Display name preservation on PyPI
- Import names vs package names
- Edge cases and Unicode handling

### `namespace-packages.md`

Complete guide to namespace package support:

- PEP 420 native namespace packages
- Legacy namespace package support
- Multiple sub-packages in namespaces
- Configuration with only-include and sources
- Enterprise/plugin system patterns

### `src-layout-structure.md`

Best practices for src-layout project structure:

- Benefits and import isolation
- Automatic detection by Hatchling
- Development workflow with editable installs
- Testing with src-layout
- Migration from flat layout

### `single-module-layout.md`

Auto-detection and configuration for single-file Python modules:

- Automatic detection behavior
- Console script configuration
- Version management in single modules
- Testing single modules
- Migration from package to single module

### `extension-module-loading.md`

Building and packaging compiled Python extensions:

- C/C++, Cython, and Rust extensions
- Build hooks for compilation
- Platform-specific builds
- Wheel tagging and artifacts
- Integration with scikit-build, maturin, and mypyc

## Quick Reference

### Minimal pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
```

### Common Configurations

**Type hints with PEP 561:**

```toml
[tool.hatch.build]
artifacts = ["py.typed", "*.pyi"]
```

**SPDX license:**

```toml
[project]
license = "MIT OR Apache-2.0"
license-files = {paths = ["LICENSE", "THIRD-PARTY.txt"]}
```

**Namespace package:**

```toml
[tool.hatch.build.targets.wheel]
only-include = ["mycompany/mypackage"]
```

**Src-layout:**

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]  # Or auto-detected
```

**Single module:**

```toml
# Auto-detected if mymodule.py exists
# Or explicitly:
[tool.hatch.build.targets.wheel]
include = ["mymodule.py"]
```

## Best Practices

1. **Use src-layout** for libraries to prevent import accidents
2. **Include type information** with py.typed marker for better IDE support
3. **Use SPDX identifiers** for license specification
4. **Let Hatchling auto-detect** when possible to reduce configuration
5. **Test your builds** with `hatch build` and inspect the results

## Verification Commands

```bash
# Build and inspect wheel contents
hatch build
unzip -l dist/*.whl

# Check metadata
unzip -p dist/*.whl '*/METADATA'

# Verify in development
pip install -e .
python -c "import mypackage; print(mypackage.__file__)"

# Test type hints
mypy --install-types --non-interactive mypackage
```

## Resources

- [Hatch Documentation](https://hatch.pypa.io/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Hatchling Source Code](https://github.com/pypa/hatch/tree/master/backend)

## Contributing

Found an issue or want to add more special configuration documentation? Please contribute to the [claude_skills repository](https://github.com/yourusername/claude_skills).
