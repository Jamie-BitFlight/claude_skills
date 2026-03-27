---
name: Hatchling Third-Party Builders
description: 'Integrate specialized build systems: scikit-build-core for C/C++, maturin for Rust, language extensions, framework integration, and plugin patterns'
---

# Third-Party Builders

Third-party builders extend Hatchling's build system with specialized functionality for specific use cases, languages, and frameworks. They provide integration points for non-Python build tools while maintaining compatibility with Hatchling's ecosystem.

## Using Third-Party Builders

### Installation

Install the third-party builder alongside Hatchling:

```toml
[build-system]
requires = [
    "hatchling",
    "your-builder-plugin",
]
build-backend = "hatchling.build"
```

### Configuration

Configure the third-party builder:

```toml
[tool.hatch.build.targets.your-target-name]
# Builder-specific configuration
```

## Popular Third-Party Builders

### scikit-build-core

Integrates CMake-based builds for C/C++ extensions.

#### Installation

```toml
[build-system]
requires = [
    "hatchling>=1.24.2",
    "scikit-build-core~=0.9.3",
]
build-backend = "hatchling.build"
```

#### Configuration

```toml
[tool.hatch.build.targets.wheel.hooks.scikit-build]
experimental = true

[tool.scikit-build]
cmake.minimum-version = "3.15"
cmake.build-type = "Release"
wheel.packages = ["src/mypackage"]
```

#### Example Usage

```python
# CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(myextension)

find_package(Python REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

pybind11_add_module(_core src/core.cpp)

install(TARGETS _core DESTINATION mypackage)
```

### maturin

Builds Python extensions written in Rust.

#### Installation

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

# Can be used with Hatchling for metadata
[tool.hatch.metadata]
allow-direct-references = true
```

#### Configuration

```toml
[tool.maturin]
features = ["pyo3/extension-module"]
python-source = "src"
module-name = "mypackage._rust"
```

### hatch-fancy-pypi-readme

Creates enhanced PyPI readme files with badges, images, and dynamic content.

#### Installation

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-fancy-pypi-readme",
]
```

#### Configuration

````toml
[tool.hatch.metadata.hooks.fancy-pypi-readme]
content-type = "text/markdown"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
path = "README.md"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
text = """
## Installation
```bash
pip install mypackage
```

"""

[[tool.hatch.metadata.hooks.fancy-pypi-readme.substitutions]]
pattern = "<!--version-->"
replacement = "v{version}"
````

### hatch-nodejs

Integrates Node.js/npm builds for JavaScript components.

#### Installation

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-nodejs",
]
```

#### Configuration

```toml
[tool.hatch.build.targets.wheel.hooks.nodejs]
path = "js"
build-command = "npm run build"
artifacts = ["dist/*"]
```

### hatch-jupyter-builder

Builds Jupyter extensions and lab extensions.

#### Installation

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-jupyter-builder>=0.8.3",
]
```

#### Configuration

```toml
[tool.hatch.build.hooks.jupyter-builder]
build-function = "hatch_jupyter_builder.npm_builder"
ensured-targets = [
    "mypackage/static/index.js",
    "mypackage/labextension/package.json",
]
skip-if-exists = [
    "mypackage/static/index.js",
]

[tool.hatch.build.hooks.jupyter-builder.build-kwargs]
npm = "npm"
build_cmd = "build"
```

## Creating Third-Party Builders

### Basic Template

```python
# my_builder_plugin/builder.py
from hatchling.builders.plugin.interface import BuilderInterface


class MyCustomBuilder(BuilderInterface):
    PLUGIN_NAME = 'my-builder'

    def get_version_api(self):
        return {'standard': self.build_standard}

    def build_standard(self, directory, **kwargs):
        # Custom build logic
        artifact = self.create_artifact(directory)
        return str(artifact)
```

### Packaging as Plugin

```toml
# pyproject.toml for the plugin
[project]
name = "hatch-my-builder"
version = "1.0.0"
description = "Custom builder plugin for Hatch"

[project.entry-points."hatchling.builders"]
my-builder = "my_builder_plugin:MyCustomBuilder"
```

## Integration Patterns

### Language Extensions

#### Cython Builder

```python
class CythonBuilder(BuilderInterface):
    PLUGIN_NAME = 'cython'

    def build_standard(self, directory, **kwargs):
        from Cython.Build import cythonize
        import subprocess

        # Cythonize .pyx files
        extensions = cythonize(
            self.get_pyx_files(),
            compiler_directives={'language_level': '3'}
        )

        # Build extensions
        for ext in extensions:
            self.build_extension(ext, directory)

        return self.create_wheel(directory)
```

#### Go Builder

```python
class GoBuilder(BuilderInterface):
    PLUGIN_NAME = 'go'

    def build_standard(self, directory, **kwargs):
        import subprocess

        # Build Go module
        subprocess.run([
            'go', 'build',
            '-buildmode=c-shared',
            '-o', f'{directory}/mypackage/_go.so',
            './...'
        ], check=True)

        return self.create_wheel(directory)
```

### Framework Integration

#### Django Builder

```python
class DjangoBuilder(BuilderInterface):
    PLUGIN_NAME = 'django'

    def build_standard(self, directory, **kwargs):
        # Collect static files
        self.run_management_command('collectstatic', '--noinput')

        # Compile messages
        self.run_management_command('compilemessages')

        # Build package
        return super().build_standard(directory, **kwargs)
```

#### Flask Builder

```python
class FlaskBuilder(BuilderInterface):
    PLUGIN_NAME = 'flask'

    def build_standard(self, directory, **kwargs):
        # Bundle assets
        self.bundle_assets()

        # Compile templates
        self.compile_templates()

        return super().build_standard(directory, **kwargs)
```

## Advanced Features

### Build Dependencies

Specify build-time dependencies:

```toml
[tool.hatch.build.targets.your-target]
dependencies = [
    "build-tool>=1.0",
    "compiler-package",
]

# Runtime dependencies needed for build
require-runtime-dependencies = true

# Specific features needed for build
require-runtime-features = ["build-support"]
```

### Environment Variables

Many third-party builders use environment variables:

```bash
# scikit-build-core
export SKBUILD_CMAKE_ARGS="-DCUSTOM_FLAG=ON"

# maturin
export MATURIN_PEP517_ARGS="--release --strip"

# Custom builders
export MY_BUILDER_DEBUG=1
```

### Build Hooks

Third-party builders can provide hooks:

```toml
[tool.hatch.build.hooks.third-party]
enable-by-default = true
config-option = "value"

[tool.hatch.build.targets.wheel.hooks.third-party]
# Target-specific hook configuration
target-option = "value"
```

## Compatibility Considerations

### Version Requirements

```toml
[build-system]
requires = [
    "hatchling>=1.24.0",  # Minimum version for features
    "third-party-builder>=2.0,<3.0",  # Compatible version range
]
```

### Platform Support

Check platform compatibility:

```python
class PlatformSpecificBuilder(BuilderInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_platform_supported():
            raise RuntimeError(f"Platform {sys.platform} not supported")

    def is_platform_supported(self):
        return sys.platform in ['linux', 'darwin']
```

## Testing with Third-Party Builders

### Mock Builder for Testing

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_builder():
    builder = Mock(spec=BuilderInterface)
    builder.PLUGIN_NAME = 'test-builder'
    builder.build_standard = Mock(return_value='/path/to/artifact')
    return builder


def test_third_party_builder_integration(mock_builder, tmp_path):
    # Test your package with the mock builder
    result = mock_builder.build_standard(tmp_path)
    assert result == '/path/to/artifact'
```

### Integration Tests

```python
def test_real_builder_integration(tmp_path):
    # Create test project
    project = tmp_path / 'test_project'
    project.mkdir()

    (project / 'pyproject.toml').write_text("""
[build-system]
requires = ["hatchling", "third-party-builder"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.custom]
# Configuration
    """)

    # Run build
    subprocess.run(['hatch', 'build', '-t', 'custom'], cwd=project)

    # Verify output
    assert (project / 'dist').exists()
```

## Performance Optimization

### Caching Build Artifacts

```python
class CachingBuilder(BuilderInterface):
    def build_standard(self, directory, **kwargs):
        cache_dir = Path.home() / '.cache' / 'hatch-builds'
        cache_key = self.get_cache_key()
        cached = cache_dir / cache_key

        if cached.exists() and not kwargs.get('no-cache'):
            shutil.copy(cached, directory)
            return str(directory / cached.name)

        artifact = self._do_build(directory)
        shutil.copy(artifact, cached)
        return artifact
```

### Parallel Builds

```python
class ParallelBuilder(BuilderInterface):
    def build_standard(self, directory, **kwargs):
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor() as executor:
            futures = []
            for target in self.get_targets():
                future = executor.submit(self.build_target, target, directory)
                futures.append(future)

            artifacts = [f.result() for f in futures]

        return self.combine_artifacts(artifacts, directory)
```

## Decision Tree: Choosing a Third-Party Builder

**For C/C++ extensions:**

- Use `scikit-build-core` (modern, maintained, CMake-based)
- Alternative: setuptools with traditional `setup.py`

**For Rust extensions:**

- Use `maturin` (best practice for Python-Rust projects)

**For Node.js/JavaScript builds:**

- Use `hatch-nodejs` (npm integration)

**For documentation generation:**

- Use `hatch-fancy-pypi-readme` (PyPI-specific readme enhancement)
- Use `hatch-jupyter-builder` (Jupyter extension builds)

**For Django/Flask projects:**

- Create custom builder or use build hooks
- Third-party builders typically not needed

## Troubleshooting

### Common Issues

#### Missing Dependencies

```toml
# Ensure all dependencies are specified
[build-system]
requires = [
    "hatchling>=1.24.0",
    "third-party-builder>=1.0",
    "build-dependency>=2.0",
]
```

#### Configuration Conflicts

```toml
# Separate configurations clearly
[tool.hatch.build]
# Global Hatch configuration

[tool.hatch.build.targets.custom]
# Target-specific configuration

[tool.third-party-builder]
# Builder-specific global configuration
```

#### Build Environment Issues

```python
# Check environment in builder
class EnvironmentAwareBuilder(BuilderInterface):
    def build_standard(self, directory, **kwargs):
        # Verify required tools
        for tool in ['tool1', 'tool2']:
            if not shutil.which(tool):
                raise RuntimeError(f"Required tool '{tool}' not found")

        # Check environment variables
        required_vars = ['VAR1', 'VAR2']
        missing = [v for v in required_vars if v not in os.environ]
        if missing:
            raise RuntimeError(f"Missing environment variables: {missing}")

        return self._do_build(directory)
```

## Resources

### Finding Third-Party Builders

- [PyPI - Search "hatch-"](https://pypi.org/search/?q=hatch-)
- [GitHub - Topic "hatch-plugin"](https://github.com/topics/hatch-plugin)
- [Awesome Hatch](https://github.com/topic/awesome-hatch)

### Documentation

- [Hatchling Plugin Interface](https://hatch.pypa.io/latest/plugins/build-hook/reference/)
- [Python Packaging - Entry Points](https://packaging.python.org/specifications/entry-points/)
- [Build System Interface (PEP 517)](https://www.python.org/dev/peps/pep-0517/)

## See Also

- `custom-builder.md` - Creating your own builders
- [Build Hooks](https://hatch.pypa.io/latest/plugins/build-hook/reference/) - Extending build process
- [Hatch Plugins](https://hatch.pypa.io/latest/plugins/about/) - Plugin development guide
