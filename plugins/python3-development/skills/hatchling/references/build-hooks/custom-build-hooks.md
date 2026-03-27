---
category: Hatchling Build System
topics: [custom-hooks, python-hooks, hatch-build-py, hook-implementation]
related: [buildhook-interface.md, configuration.md, hook-dependencies.md, build-data.md]
---

# Custom Build Hooks

Custom build hooks allow developers to define custom Python code that runs during the build process. When helping users implement custom hooks, guide them to use a Python file (typically `hatch_build.py`) that inherits from `BuildHookInterface`.

## Configuration

The custom build hook is the only built-in hook for user-defined logic.

### Plugin Name

The custom hook plugin name is `custom`.

### Configuration Location

```toml
# Global custom hook
[tool.hatch.build.hooks.custom]

# Target-specific custom hook
[tool.hatch.build.targets.<TARGET_NAME>.hooks.custom]
```

### Configuration Options

| Option | Default          | Description                                     |
| ------ | ---------------- | ----------------------------------------------- |
| `path` | `hatch_build.py` | The path of the Python file containing the hook |

## Basic Setup

### Default Configuration (hatch_build.py)

By default, Hatchling looks for a file named `hatch_build.py` in the project root:

```toml
[tool.hatch.build.hooks.custom]
# path defaults to "hatch_build.py"
```

### Custom File Path

Specify a different file path:

```toml
[tool.hatch.build.hooks.custom]
path = "build/hooks.py"
```

Paths are relative to the project root.

## Implementation

### Basic Custom Hook

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Called before each build"""
        print(f"Building version {version}")

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Called after each build"""
        print(f"Artifact created: {artifact_path}")
```

### Multiple Hook Classes

If your custom hook file contains multiple subclasses of `BuildHookInterface`, you must define a `get_build_hook()` function that returns the desired hook:

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class WheelBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        print("Preparing wheel build")

class SdistBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        print("Preparing sdist build")

def get_build_hook():
    """Return the appropriate hook"""
    # Logic to choose which hook to use
    return WheelBuildHook()
```

## Common Patterns

### Generating Files During Build

Generate source files or artifacts before the build:

```python
# hatch_build.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Generate version file
        version_file = os.path.join(self.root, "src", "myproject", "__version__.py")
        os.makedirs(os.path.dirname(version_file), exist_ok=True)

        with open(version_file, 'w') as f:
            f.write(f'__version__ = "{version}"\n')

        # Include in build
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('src/myproject/__version__.py')
```

Configuration:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

### Compiling Resources

Compile assets (CSS, JavaScript, etc.) during build:

```python
# hatch_build.py
import subprocess
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Compile assets
        assets_dir = os.path.join(self.root, "assets")
        output_dir = os.path.join(self.root, "src/myproject/static")

        subprocess.run([
            "sass",
            "--load-path", assets_dir,
            f"{assets_dir}/main.scss:{output_dir}/main.css"
        ], check=True)

        # Include compiled assets
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('src/myproject/static/**/*.css')
```

### Conditional Logic Based on Target

Run different code for different build targets:

```python
# hatch_build.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name == 'wheel':
            # Wheel-specific setup
            self.prepare_wheel_build()
        elif self.target_name == 'sdist':
            # Sdist-specific setup
            self.prepare_sdist_build()

    def prepare_wheel_build(self) -> None:
        print("Preparing wheel build")
        # Compile extensions, etc.

    def prepare_sdist_build(self) -> None:
        print("Preparing sdist build")
        # Include source templates, etc.
```

### Post-Build Processing

Perform operations after the artifact is created:

```python
# hatch_build.py
import os
import hashlib
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Create checksums after build"""
        checksum = self.compute_checksum(artifact_path)
        checksum_file = f"{artifact_path}.sha256"

        with open(checksum_file, 'w') as f:
            f.write(f"{checksum}  {os.path.basename(artifact_path)}\n")

        print(f"Checksum written to {checksum_file}")

    def compute_checksum(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(4096), b''):
                sha256.update(block)
        return sha256.hexdigest()
```

### Accessing Configuration

Read hook configuration from `pyproject.toml`:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
output-dir = "dist"
verbose = true
```

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        output_dir = self.config.get('output-dir', 'dist')
        verbose = self.config.get('verbose', False)

        if verbose:
            print(f"Output directory: {output_dir}")
```

### Declaring Hook Dependencies

If your hook needs external packages, declare them:

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["jinja2>=2.11", "pillow>=8.0"]

    def initialize(self, version: str, build_data: dict) -> None:
        # Now safe to import these (they're installed)
        from jinja2 import Environment, FileSystemLoader
        from PIL import Image
```

Configuration:

```toml
[build-system]
requires = ["hatchling"]  # Hook itself must be available

[tool.hatch.build.hooks.custom]
dependencies = ["jinja2>=2.11", "pillow>=8.0"]
```

## Hook Lifecycle Methods

### clean(versions: list[str])

Called when cleaning build artifacts:

```python
import shutil
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def clean(self, versions: list[str]) -> None:
        """Remove hook-generated files"""
        generated_dir = os.path.join(self.root, "generated")
        if os.path.exists(generated_dir):
            shutil.rmtree(generated_dir)
            print(f"Cleaned {generated_dir}")
```

Call it with `hatch clean` or `hatch build -c`.

### initialize(version: str, build_data: dict)

Called before the build starts. Modify `build_data` to influence the build:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Add artifacts
    build_data['artifacts'].append('generated/**/*.py')

    # Add forced inclusions
    build_data['force_include']['external/lib.so'] = 'mylib/lib.so'
```

### finalize(version: str, build_data: dict, artifact_path: str)

Called after the build completes:

```python
def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
    # artifact_path is the actual built artifact (e.g., dist/package-1.0.0.tar.gz)
    print(f"Built: {artifact_path}")
    self.verify_and_sign(artifact_path)
```

## Target-Specific Hooks

Define different behavior for different build targets:

```python
# hatch_build.py
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class WheelHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name == 'wheel':
            print("Building wheel")
            # Compile extensions, create .so files, etc.

class SdistHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name == 'sdist':
            print("Building sdist")
            # Include source templates, build scripts, etc.
```

Configuration:

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"

[tool.hatch.build.targets.sdist.hooks.custom]
path = "hatch_build.py"
```

## Error Handling

Raise exceptions to fail the build:

```python
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        required_file = os.path.join(self.root, "version.txt")

        if not os.path.exists(required_file):
            raise RuntimeError(
                f"Required file not found: {required_file}\n"
                "Run 'generate-version' script first."
            )
```

## Best Practices

### 1. Keep Hooks Minimal

Hooks should do one thing well:

```python
# Good: Single responsibility
class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        self.generate_version_file(version)

# Less ideal: Multiple unrelated operations
class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        self.generate_version_file(version)
        self.compile_assets()
        self.compress_resources()
```

### 2. Lazy Import Dependencies

Only import hook dependencies inside methods:

```python
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["jinja2"]

    def initialize(self, version: str, build_data: dict) -> None:
        # Import here, not at module level
        from jinja2 import Template
```

### 3. Use Context-Aware Paths

Use `self.root` for project-relative paths:

```python
def initialize(self, version: str, build_data: dict) -> None:
    # Good: Works from any directory
    version_file = os.path.join(self.root, "src/version.py")

    # Avoid: Depends on current directory
    version_file = "src/version.py"
```

### 4. Document Configuration Options

Document all configuration parameters your hook uses:

```python
class CustomBuildHook(BuildHookInterface):
    """
    Generate version file from template.

    Configuration:
        - template-dir: Directory containing templates (default: templates)
        - output-file: Output file path (default: src/version.py)
    """
    def initialize(self, version: str, build_data: dict) -> None:
        template_dir = self.config.get('template-dir', 'templates')
        output_file = self.config.get('output-file', 'src/version.py')
```

### 5. Make Hooks Idempotent

Hooks should work correctly when run multiple times:

```python
def initialize(self, version: str, build_data: dict) -> None:
    output_file = os.path.join(self.root, 'generated.py')
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    # Overwrite existing file without error
    with open(output_file, 'w') as f:
        f.write(...)
```

## Related Topics

- `buildhook-interface.md` - Complete interface reference
- `build-data.md` - Understanding build data
- `execution-order.md` - How custom hooks execute
- `configuration.md` - Configuring custom hooks
