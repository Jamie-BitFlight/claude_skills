---
category: Hatchling Build System
topics: [hook-dependencies, dependencies, build-requirements, lazy-import]
related: [configuration.md, custom-build-hooks.md, buildhook-interface.md]
---

# Hook Dependencies

Build hooks can declare dependencies that must be installed before the build process. Help users understand how to properly manage hook-specific dependencies, which are separate from the project's runtime dependencies, by referencing this documentation.

## Overview

Hook dependencies allow:

- Third-party build hooks to declare what they need
- Custom hooks to specify external tools or libraries
- Lazy import of dependencies (only when hooks are used)
- Proper build environment setup

## Types of Hook Dependencies

### 1. Third-Party Hook Dependencies

Install external build hooks via `build-system.requires`:

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-cython>=0.11",
    "hatch-mypyc>=1.0",
]
```

Then configure them:

```toml
[tool.hatch.build.hooks.cython]
# Hook is now available

[tool.hatch.build.hooks.mypyc]
# Hook is now available
```

### 2. Hook-Level Dependencies

Additional dependencies specific to a hook:

```toml
[tool.hatch.build.hooks.custom]
dependencies = ["jinja2>=2.11", "pillow>=8.0"]
```

These are installed when the hook runs.

### 3. Runtime Dependencies

Make hooks depend on the project's runtime dependencies:

```toml
[tool.hatch.build.hooks.custom]
require-runtime-dependencies = true
```

This installs all packages listed in `[project.dependencies]`.

### 4. Optional Feature Dependencies

Depend on specific optional features:

```toml
[tool.hatch.build.hooks.custom]
require-runtime-features = ["imaging", "pdf"]
```

This installs packages from `[project.optional-dependencies]` for those features.

## Configuration

### Hook-Specific Dependencies

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
dependencies = [
    "jinja2>=2.11",
    "pillow>=8.0",
    "click>=7.0,<9.0",
]
```

Dependencies are specified as a list of version specifiers (same format as `[project.dependencies]`).

### Global vs Target-Specific

Dependencies can be specified globally or per-target:

```toml
# Global hook dependencies
[tool.hatch.build.hooks.custom]
dependencies = ["jinja2>=2.11"]

# Target-specific dependencies
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = ["pillow>=8.0"]

# Both will be installed when building wheels
# Only jinja2 when building sdist
```

### Runtime Dependency Requirements

Make hooks depend on project runtime dependencies:

```toml
[tool.hatch.build.hooks.custom]
require-runtime-dependencies = true
```

Or depend on specific optional features:

```toml
[tool.hatch.build.hooks.custom]
require-runtime-features = ["docs", "testing"]
```

## Implementation

### Declaring Dependencies in Custom Hooks

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        """Declare dependencies required by this hook"""
        return [
            "jinja2>=2.11",
            "pillow>=8.0",
            "ruamel.yaml>=0.18",
        ]

    def initialize(self, version: str, build_data: dict) -> None:
        # These imports are safe now - dependencies are installed
        from jinja2 import Template, Environment, FileSystemLoader
        from PIL import Image
        from ruamel.yaml import YAML

        # Use the libraries
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('build.jinja2')
```

### Lazy Imports

Dependencies declared via `dependencies()` should be imported inside methods, not at module level:

```python
# GOOD: Import inside method
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["jinja2>=2.11"]

    def initialize(self, version: str, build_data: dict) -> None:
        from jinja2 import Template  # Safe here
        template = Template(...)

# BAD: Import at module level
from jinja2 import Template  # May fail if hook is disabled

class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["jinja2>=2.11"]

    def initialize(self, version: str, build_data: dict) -> None:
        template = Template(...)  # Uses module-level import
```

### Dynamic Dependencies

Return different dependencies based on conditions:

```python
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        """Dependencies depend on configuration"""
        deps = []

        if self.config.get('enable-cython'):
            deps.append("cython>=0.29")

        if self.config.get('enable-numpy'):
            deps.append("numpy>=1.19")

        return deps
```

Configuration:

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
enable-cython = true
enable-numpy = true
```

## Common Dependency Patterns

### Tool-Based Hook

```python
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return ["sass>=1.50"]  # Sass compiler

    def initialize(self, version: str, build_data: dict) -> None:
        import subprocess
        subprocess.run(["sass", "styles/main.scss:dist/main.css"], check=True)
```

Configuration:

```toml
[tool.hatch.build.hooks.custom]
dependencies = ["sass>=1.50"]
```

### Multi-Library Hook

```python
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        return [
            "jinja2>=2.11",
            "pillow>=8.0",
            "click>=7.0,<9.0",
            "ruamel.yaml>=0.18",
        ]

    def initialize(self, version: str, build_data: dict) -> None:
        from jinja2 import Environment, FileSystemLoader
        from PIL import Image
        import click
        from ruamel.yaml import YAML

        # Use all libraries
        self.generate_images()
        self.build_config()
```

### Platform-Specific Dependencies

```python
import platform

class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        deps = ["jinja2>=2.11"]

        if platform.system() == "Windows":
            deps.append("pywin32>=300")

        return deps
```

### Conditional Optional Dependencies

```python
class CustomBuildHook(BuildHookInterface):
    def dependencies(self) -> list[str]:
        """Include optional dependencies if configured"""
        deps = ["jinja2>=2.11"]

        # Configuration-driven dependencies
        if self.config.get('enable-pdf'):
            deps.append("reportlab>=3.5")

        if self.config.get('enable-compression'):
            deps.append("lz4>=3.1")

        return deps

    def initialize(self, version: str, build_data: dict) -> None:
        from jinja2 import Template

        if self.config.get('enable-pdf'):
            from reportlab.pdfgen import canvas
```

## Version Specifiers

Hook dependencies use the same version specifier syntax as project dependencies:

| Specifier    | Example                   | Meaning                  |
| ------------ | ------------------------- | ------------------------ |
| No specifier | `package`                 | Any version              |
| Exact        | `package==1.0.0`          | Exactly 1.0.0            |
| Compatible   | `package~=1.4.2`          | >=1.4.2, <1.5            |
| Minimum      | `package>=1.0`            | 1.0 or later             |
| Maximum      | `package<2.0`             | Before 2.0               |
| Range        | `package>=1.0,<2.0`       | 1.0 or later, before 2.0 |
| Not equal    | `package!=1.5`            | Any except 1.5           |
| Complex      | `package>=1.0,!=1.5,<2.0` | Multiple constraints     |

## Configuration Examples

### Simple Custom Hook with Dependencies

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
dependencies = ["jinja2"]
```

### Multiple Hooks with Dependencies

```toml
[tool.hatch.build.hooks.generate]
path = "hooks/generate.py"
dependencies = ["jinja2>=2.11"]

[tool.hatch.build.hooks.compile]
path = "hooks/compile.py"
dependencies = ["cython>=0.29"]
```

### Target-Specific Dependencies

```toml
[tool.hatch.build.targets.wheel.hooks.custom]
dependencies = ["cython>=0.29"]

[tool.hatch.build.targets.sdist.hooks.custom]
dependencies = []
```

### Runtime Dependencies

```toml
[tool.hatch.build.hooks.custom]
require-runtime-dependencies = true
```

This installs all packages from `[project.dependencies]`.

### Feature Dependencies

```toml
[tool.hatch.build.hooks.custom]
require-runtime-features = ["docs", "testing"]
```

This installs packages from:

- `[project.optional-dependencies]` → `docs`
- `[project.optional-dependencies]` → `testing`

## Important Restrictions

### Hook Dependency Rule

The hook dependency itself must be defined in `build-system.requires`:

```toml
[build-system]
requires = [
    "hatchling",
    "my-custom-hook-plugin",  # Hook itself must be here
]

[tool.hatch.build.hooks.custom]
dependencies = ["jinja2"]  # Extra dependencies
```

**Why**: The hook must be importable to call its `dependencies()` method. If the hook itself were in the `dependencies()` list, it would create a circular dependency.

### Third-Party Hook Dependencies

```toml
[build-system]
requires = [
    "hatchling",
    "hatch-cython>=0.11",  # Third-party hook
]

[tool.hatch.build.hooks.cython]
dependencies = ["cython>=0.29"]  # Extra dependencies
```

### Lazy Import Rule

Always lazy-import (inside methods) any packages declared as dependencies:

```python
# Correct: Import inside method
def initialize(self, version: str, build_data: dict) -> None:
    from jinja2 import Template  # Imported here

# Incorrect: Import at module level
from jinja2 import Template  # May fail if dependencies not installed

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        template = Template(...)  # Uses module-level import
```

## Troubleshooting

### Module Not Found Error

If you get `ModuleNotFoundError` for a dependency:

1. Check it's declared in `dependencies()` method
2. Verify the package name matches the import name (sometimes different)
3. Check the version specifier is correct
4. Ensure the import is lazy (inside a method, not module-level)

### Dependency Conflict

If dependencies conflict with project dependencies:

1. Use compatible versions: `dependencies = ["jinja2>=2.11,<4.0"]`
2. Consider splitting hooks by target: separate wheel and sdist hooks
3. Use optional features instead of declaring separate dependencies

### Conditional Dependencies Not Working

Ensure you're using configuration, not environment:

```python
# Correct: Use self.config
def dependencies(self) -> list[str]:
    if self.config.get('enable-cython'):
        return ["cython"]
    return []

# Incorrect: Using environment variables
def dependencies(self) -> list[str]:
    if os.getenv('ENABLE_CYTHON'):
        return ["cython"]  # Environment not available yet
    return []
```

## Best Practices

1. **Declare all dependencies**: Every import should have a corresponding dependency declaration
2. **Use version constraints**: Be specific about version requirements
3. **Lazy imports**: Import dependencies only when needed (inside methods)
4. **Document dependencies**: Comment why each dependency is needed
5. **Minimize dependencies**: Use only what's necessary
6. **Consider optional features**: Use runtime feature dependencies for optional compilation

## Related Topics

- `configuration.md` - Hook configuration
- `buildhook-interface.md` - `dependencies()` method
- `custom-build-hooks.md` - Writing hooks with dependencies
