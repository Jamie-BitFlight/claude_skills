---
category: Hatchling Build System
topics: [hook-communication, data-passing, multi-hook-workflows, build-coordination]
related: [build-data.md, execution-order.md, custom-build-hooks.md]
---

# Passing Data Between Hooks

Build hooks can communicate with each other by modifying the shared `build_data` dictionary. This enables sophisticated build workflows where multiple hooks coordinate to accomplish complex tasks. Use this reference when helping users design complex multi-hook systems that require inter-hook communication.

## Communication Mechanism

Hooks share data through the `build_data` dictionary:

1. **Hook A** runs `initialize()` and modifies `build_data`
2. **Hook B** runs `initialize()` and sees Hook A's modifications
3. Both hooks' modifications affect the final build
4. During `finalize()`, both hooks see the complete picture

## How It Works

<eg>
Hook A           Hook B
initialize()  →  initialize()
   ↓               ↓
 modify          modify
build_data    build_data
   ↓               ↓
   └─────────────┬─────────┘
                 ↓
          Build process
                 ↓
   ┌─────────────┬─────────┐
   ↓             ↓         ↓
finalize()  finalize()  [final build_data]
   A             B
</eg>

## Example: Two-Hook Coordination

**Scenario**: Hook A generates code, Hook B compiles it.

### Configuration

```toml
[tool.hatch.build.hooks.generate]
path = "hooks/generate.py"

[tool.hatch.build.hooks.compile]
path = "hooks/compile.py"
```

### Hook A: Generate Code

```python
# hooks/generate.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class GenerateHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Generate source code"""
        # Create generated directory
        gen_dir = os.path.join(self.root, 'generated')
        os.makedirs(gen_dir, exist_ok=True)

        # Generate files
        code_file = os.path.join(gen_dir, 'codegen.py')
        with open(code_file, 'w') as f:
            f.write(f'''# Generated code for version {version}
def generated_version():
    return "{version}"
''')

        # Signal to next hook that we generated code
        if 'generated_files' not in build_data:
            build_data['generated_files'] = []
        build_data['generated_files'].append(code_file)

        print("✓ Code generation complete")
```

### Hook B: Compile Generated Code

```python
# hooks/compile.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class CompileHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Compile generated code"""
        # Check if generation hook ran and created files
        generated_files = build_data.get('generated_files', [])

        if not generated_files:
            print("⚠ No generated files found")
            return

        # Compile each generated file
        for gen_file in generated_files:
            compiled = self.compile_file(gen_file)
            print(f"✓ Compiled {gen_file} → {compiled}")

        # Include compiled files
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('generated/**/*.pyc')

    def compile_file(self, file_path: str) -> str:
        """Hypothetical compilation function"""
        # This would be your actual compilation logic
        return file_path + '.compiled'
```

**Execution order**:

1. `GenerateHook.initialize()` - Generates code, adds `generated_files` to build_data
2. `CompileHook.initialize()` - Reads `generated_files`, compiles them
3. Both hooks' artifacts are included in the final build

## Data Sharing Patterns

### Using Custom Dictionary Fields

Add arbitrary fields to `build_data` for inter-hook communication:

```python
class Hook1(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Create custom field for other hooks
        build_data['my_data'] = {
            'generated_files': ['file1.py', 'file2.py'],
            'compiled_assets': [],
            'version': version,
        }

class Hook2(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Read and modify custom field
        if 'my_data' in build_data:
            my_data = build_data['my_data']
            for file in my_data['generated_files']:
                compiled = self.compile(file)
                my_data['compiled_assets'].append(compiled)
```

### Building on Artifacts

Hook A adds artifacts, Hook B adds more:

```python
class Hook1(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('generated/**/*.py')

class Hook2(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        # Add more artifacts
        build_data['artifacts'].append('compiled/**/*.so')
        # Both are now included
```

### Conditional Logic Based on Hook Presence

Check which hooks are running before making decisions:

```python
class ConditionalHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        hooks = build_data['build_hooks']

        if 'generate' in hooks:
            # Generation hook is present, use its output
            self.process_generated_files()
        elif 'custom' in hooks:
            # No generation, but custom hook is present
            self.process_custom_output()
        else:
            # Neither present, use defaults
            self.setup_defaults()
```

## Practical Example: Multi-Stage Build

**Scenario**: Three hooks working together to build, test, and package:

### Configuration

```toml
[tool.hatch.build.hooks.prebuild]
path = "build_steps/prebuild.py"

[tool.hatch.build.hooks.build]
path = "build_steps/build.py"

[tool.hatch.build.hooks.postbuild]
path = "build_steps/postbuild.py"
```

### Step 1: Prebuild

```python
# build_steps/prebuild.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class PreBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Prepare build environment"""
        # Create build directories
        dirs = {
            'generated': os.path.join(self.root, 'generated'),
            'built': os.path.join(self.root, 'built'),
            'artifacts': os.path.join(self.root, 'artifacts'),
        }

        for dir_name, dir_path in dirs.items():
            os.makedirs(dir_path, exist_ok=True)

        # Share directory paths with other hooks
        build_data['build_dirs'] = dirs
        build_data['build_status'] = {'prebuild': True}
```

### Step 2: Build

```python
# build_steps/build.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class BuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Execute build steps"""
        # Get directories from prebuild hook
        build_dirs = build_data.get('build_dirs', {})

        if not build_dirs:
            raise RuntimeError("Prebuild hook must run first")

        # Build in generated directory
        gen_dir = build_dirs['generated']
        self.run_build(gen_dir, version)

        # Update status
        status = build_data.get('build_status', {})
        status['build'] = True
        build_data['build_status'] = status

        # Add generated files to artifacts
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('generated/**/*')

    def run_build(self, output_dir: str, version: str) -> None:
        """Hypothetical build process"""
        pass
```

### Step 3: Postbuild

```python
# build_steps/postbuild.py
import os
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

class PostBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Finalize build artifacts"""
        # Verify previous hooks ran
        status = build_data.get('build_status', {})

        if not status.get('prebuild') or not status.get('build'):
            raise RuntimeError("Previous build hooks must complete first")

        # Copy final artifacts
        build_dirs = build_data['build_dirs']
        built_dir = build_dirs['built']
        artifacts_dir = build_dirs['artifacts']

        self.copy_artifacts(built_dir, artifacts_dir)

        # Include final artifacts
        if 'artifacts' not in build_data:
            build_data['artifacts'] = []
        build_data['artifacts'].append('artifacts/**/*')

        print(f"✓ Build complete for version {version}")

    def copy_artifacts(self, src: str, dst: str) -> None:
        """Copy build artifacts to final location"""
        pass
```

## Data Persistence Across Hook Methods

Data persists within the `build_data` dictionary across all hooks:

```python
class MultiMethodHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Store information
        build_data['my_state'] = {
            'version': version,
            'initialized': True,
        }

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        # Retrieve information from initialize
        my_state = build_data.get('my_state', {})

        if my_state.get('initialized'):
            print(f"Hook initialized for version {my_state['version']}")
            print(f"Built artifact: {artifact_path}")
```

## Communication Best Practices

### 1. Use Clear Field Names

```python
# Good: Descriptive field names
build_data['generated_source_files'] = ['file1.py', 'file2.py']
build_data['compiled_extensions'] = {'lib.so': '/path/to/lib.so'}

# Less clear
build_data['gen'] = [...]
build_data['comp'] = [...]
```

### 2. Document Custom Fields

```python
class GeneratingHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """
        Add 'generated_files' field to build_data.

        Other hooks can check for this field and use its contents.
        Format: List of absolute paths to generated files.
        """
        if 'generated_files' not in build_data:
            build_data['generated_files'] = []
        build_data['generated_files'].append(...)
```

### 3. Handle Missing Dependencies Gracefully

```python
class DependentHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        """Handle case where prerequisite hook didn't run"""
        generated_files = build_data.get('generated_files', [])

        if not generated_files:
            # Gracefully handle missing prerequisite
            print("⚠ Generated files not found, skipping compilation")
            return

        # Process generated files
        for file in generated_files:
            self.compile(file)
```

### 4. Use Execution Order to Ensure Consistency

```python
# pyproject.toml
[tool.hatch.build.hooks.generate]
# Runs first

[tool.hatch.build.hooks.compile]
# Runs second, can depend on generate
```

### 5. Test Hook Independence

Ensure each hook can run independently:

```python
class RobustHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Works with or without previous hooks
        my_data = build_data.get('my_data', {})

        # Provide defaults if needed
        if not my_data:
            build_data['my_data'] = self.get_defaults()
```

## Debugging Inter-Hook Communication

### Add Logging

```python
class DebugHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        print("=== Hook Initialize ===")
        print(f"Version: {version}")
        print(f"Build data keys: {build_data.keys()}")

        for key, value in build_data.items():
            print(f"  {key}: {type(value).__name__}")
```

### Inspect Finalization State

```python
def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
    print("=== Hook Finalize ===")
    print(f"Artifact: {artifact_path}")

    artifacts = build_data.get('artifacts', [])
    print(f"Total artifacts: {len(artifacts)}")

    for artifact in artifacts:
        print(f"  - {artifact}")
```

## Related Topics

- `build-data.md` - Understanding build data
- `execution-order.md` - How hooks execute in sequence
- `custom-build-hooks.md` - Writing hooks that communicate
