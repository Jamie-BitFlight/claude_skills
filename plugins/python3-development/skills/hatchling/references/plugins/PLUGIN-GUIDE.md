---
name: Hatchling Plugin Development Guide
description: Comprehensive guide to developing and using Hatchling plugins, covering plugin types, development workflow, configuration patterns, testing, and best practices for creating reusable plugins.
---

# Hatchling Plugin System - Comprehensive Reference Guide

This directory contains comprehensive documentation of Hatchling's plugin system and extensibility capabilities.

## Quick Navigation

### By Plugin Type

1. **`builder-plugins.md`** - Create distributable packages

   - Wheel builder
   - Source distribution (sdist) builder
   - Custom/third-party builders
   - Interface: `BuilderInterface`

2. **`build-hook-plugins.md`** - Execute code during builds

   - Initialize phase (before build)
   - Finalize phase (after build)
   - Clean phase (with --clean flag)
   - Interface: `BuildHookInterface`

3. **`metadata-hook-plugins.md`** - Dynamically modify project metadata

   - Dynamic version, description, dependencies
   - Custom classifiers
   - Interface: `MetadataHookInterface`

4. **`version-source-plugins.md`** - Determine project version

   - VCS tags (via hatch-vcs)
   - Code extraction (regex/file parsing)
   - Environment variables
   - Interface: `VersionSourceInterface`

5. **`version-scheme-plugins.md`** - Validate version bumping

   - PEP 440 validation
   - Custom version formats
   - Interface: `VersionSchemeInterface`

6. **`hatch-vcs-plugin.md`** - VCS-based versioning (Git/Mercurial)
   - Complete guide to hatch-vcs
   - Configuration and usage patterns
   - Migration from setuptools

### By Use Case

**I want to...**

- **Customize the build process** → `build-hook-plugins.md`
- **Auto-generate version files** → `hatch-vcs-plugin.md`
- **Read version from VCS tags** → `version-source-plugins.md` + `hatch-vcs-plugin.md`
- **Create a custom package format** → `builder-plugins.md`
- **Generate metadata dynamically** → `metadata-hook-plugins.md`
- **Enforce versioning rules** → `version-scheme-plugins.md`
- **Create a reusable plugin** → `index.md`

## Key Concepts

### Plugin Architecture

Hatchling uses **pluggy** for plugin registration and management:

```python
# Registration in hooks.py
from hatchling.plugin import hookimpl
from .plugin import SpecialBuilder

@hookimpl
def hatch_register_builder():
    return SpecialBuilder

# Implementation in plugin.py
class SpecialBuilder(BuilderInterface):
    PLUGIN_NAME = 'special'  # User-facing identifier
```

### Plugin Categories

1. **Hatchling Plugins** (Build-time)

   - Builder plugins
   - Build hook plugins
   - Metadata hook plugins
   - Version source plugins
   - Version scheme plugins
   - _Auto-installed in build environments_

2. **Hatch Plugins** (Runtime)
   - Environment plugins
   - Environment collector plugins
   - Publisher plugins
   - _Must be installed in Hatch's own environment_

### Configuration Pattern

Plugins are configured in `pyproject.toml`:

```toml
# Select version source
[tool.hatch.version]
source = "vcs"  # PLUGIN_NAME

# Configure build hook
[tool.hatch.build.hooks.custom]
option = "value"

# Configure metadata hook
[tool.hatch.metadata.hooks.dynamic-description]
file = "description.txt"

# Define builder target
[tool.hatch.build.targets.special]
# Configuration
```

## Common Plugin Patterns

### Example 1: Version File Generation

**Use**: Auto-generate version file from VCS tags

**Solution**: `hatch-vcs-plugin.md`

```toml
[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/mypackage/_version.py"
```

### Example 2: Custom Build Steps

**Use**: Compile Cython files, generate code, build extensions

**Solution**: `build-hook-plugins.md`

```python
class CythonBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'cython'

    @staticmethod
    def dependencies():
        return ['cython>=0.29']

    def initialize(self, version, build_data):
        # Compile .pyx files
        pass
```

### Example 3: Dynamic Metadata

**Use**: Set dependencies from `requirements.txt`, description from README

**Solution**: `metadata-hook-plugins.md`

```python
class RequirementsTxtHook(MetadataHookInterface):
    PLUGIN_NAME = 'requirements-txt'

    def update(self, metadata):
        with open(os.path.join(self.root, 'requirements.txt')) as f:
            metadata['dependencies'] = f.read().splitlines()
```

### Example 4: Custom Version Format

**Use**: Calendar versioning (YYYY.MM.DD), custom schemes

**Solution**: `version-scheme-plugins.md`

```python
class CalendarVersionScheme(VersionSchemeInterface):
    PLUGIN_NAME = 'calver'

    def update(self, desired_version, original_version, version_data):
        # Validate calendar version format
        pass
```

## Plugin Development Workflow

### 1. Initialize Plugin Project

```bash
mkdir hatch-myfeature
cd hatch-myfeature
```

### 2. Create Project Structure

<eg>
hatch-myfeature/
├── pyproject.toml
├── README.md
├── src/
│   └── hatch_myfeature/
│       ├── __init__.py
│       ├── hooks.py          # Plugin registration
│       └── plugin.py         # Plugin implementation
└── tests/
    └── test_plugin.py
</eg>

### 3. Define Plugin Class

```python
# src/hatch_myfeature/plugin.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class MyBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'myfeature'

    def initialize(self, version, build_data):
        # Implementation
        pass
```

### 4. Register Plugin

```python
# src/hatch_myfeature/hooks.py
from hatchling.plugin import hookimpl
from .plugin import MyBuildHook

@hookimpl
def hatch_register_build_hook():
    return MyBuildHook
```

### 5. Configure in pyproject.toml

```toml
[project]
name = "hatch-myfeature"
version = "0.1.0"

[project.entry-points.hatchling]
build-hook = "hatch_myfeature.hooks"

[tool.hatch.build.hooks.myfeature]
# Plugin configuration
```

### 6. Test Locally

```toml
# pyproject.toml in test project
[build-system]
requires = ["hatchling", "hatch-myfeature @ file:///path/to/hatch-myfeature"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.myfeature]
# Test configuration
```

### 7. Test with Proper Caching

```python
# tests/test_plugin.py
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

@pytest.fixture(scope='session')
def plugin_dir():
    with TemporaryDirectory() as d:
        directory = Path(d, 'plugin')
        shutil.copytree(
            Path.cwd(),
            directory,
            ignore=shutil.ignore_patterns('.git', '.venv')
        )
        yield directory.resolve()

@pytest.fixture
def new_project(tmp_path, plugin_dir):
    project_dir = tmp_path / 'my-app'
    project_dir.mkdir()
    project_file = project_dir / 'pyproject.toml'
    project_file.write_text(f'''
[build-system]
requires = ["hatchling", "hatch-myfeature @ {plugin_dir.as_uri()}"]
build-backend = "hatchling.build"

[project]
name = "my-app"
version = "0.1.0"
''')
    return project_dir
```

## Official Plugin Registry

### Version Source Plugins

- **hatch-vcs** - Git/Mercurial tags
- **hatch-nodejs-version** - `package.json` version
- **versioningit** - Git/Mercurial with custom formatting
- **hatch-regex-commit** - Regex + auto-commit

### Build Hook Plugins

- **hatch-vcs** - Auto-generate version file
- **hatch-cython** - Cython compilation
- **hatch-mypyc** - MyPyC compilation
- **scikit-build-core** - C/C++/Rust extensions

### Metadata Hook Plugins

- **hatch-fancy-pypi-readme** - Dynamic README construction
- **hatch-requirements-txt** - Dependencies from requirements.txt
- **hatch-nodejs-version** - Metadata from package.json
- **hatch-docstring-description** - Description from docstring
- **UniDep** - Unified pip/conda dependencies

### Builder Plugins

- **scikit-build-core** (hatchling plugin) - C/C++/Fortran extensions
- **hatch-aws-publisher** - AWS Lambda packages
- **hatch-containers** - Container images

## Best Practices

### Plugin Design

1. **Single Responsibility**: Each plugin should do one thing well
2. **Configuration**: Allow configuration via `pyproject.toml`
3. **Error Messages**: Provide clear, actionable error messages
4. **Documentation**: Document configuration options and examples
5. **Testing**: Include comprehensive tests in plugin package

### Plugin Usage

1. **Pin Dependencies**: Specify plugin versions in `build-system.requires`
2. **Idempotency**: Plugins should produce consistent results
3. **Logging**: Use Hatchling's logging for debugging
4. **Validation**: Validate configuration and inputs
5. **Cleanup**: Clean up temporary files properly

### Plugin Publication

1. **PyPI**: Publish to PyPI for discoverability
2. **Naming**: Use `hatch-*` prefix in package name
3. **Classifier**: Add `Framework :: Hatch` classifier
4. **Documentation**: Include README with configuration examples
5. **Tests**: Include CI tests (GitHub Actions, etc.)

## Reference Materials

- `index.md`
- [Official Hatch Documentation](https://hatch.pypa.io/latest/plugins/)
- [pluggy Documentation](https://pluggy.readthedocs.io/)
- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)

## Troubleshooting

### Plugin Not Loading

1. Check entry point configuration in `pyproject.toml`
2. Verify plugin is installed in build environment
3. Check for import errors: `python -c "from module import Plugin"`
4. Enable verbose logging: `hatch -v build`

### Version File Not Generated

1. Ensure build hook is configured
2. Check `version-file` path is relative to project root
3. Verify `hatch build --hooks-only` generates file
4. Check for hook errors in build output

### Configuration Not Applied

1. Verify `PLUGIN_NAME` matches configuration section name
2. Check `pyproject.toml` for syntax errors
3. Ensure configuration section exists
4. Verify plugin is installed

## Getting Help

- **GitHub Issues**: Report bugs or request features on plugin repository
- **Hatch Discussions**: Ask questions in [Hatch discussions](https://github.com/pypa/hatch/discussions)
- **PyPI**: View plugin documentation and downloads on PyPI
- **Stack Overflow**: Tag questions with `hatchling` and `python`

## Contributing to Plugins

Most Hatchling plugins are open source. Contributions are welcome:

1. Fork plugin repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Engage with maintainers

---

**Last Updated**: November 2024 **Hatchling Version**: 1.24+
