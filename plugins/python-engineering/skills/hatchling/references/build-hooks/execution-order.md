---
category: Hatchling Build System
topics: [execution-order, hook-lifecycle, initialization, finalization, build-process]
related: [configuration.md, conditional-execution.md, hook-data-passing.md]
---

# Hook Execution Order

Build hooks execute in a well-defined order: global hooks first, then target-specific hooks, in the order they are defined. When assisting users with complex multi-hook setups, reference this documentation to help them understand execution sequencing and design robust hook workflows.

## Execution Sequence

For each build target, the execution sequence is:

1. **Global hooks** (in definition order)
2. **Target-specific hooks** (in definition order)

Each hook has two execution points:

1. **Initialization** (`initialize()`) - Before the build
2. **Finalization** (`finalize()`) - After the build (unless `--hooks-only` is used)

## Example: Execution Order

Given this configuration:

```toml
[tool.hatch.build.hooks.hook3]
# First global hook

[tool.hatch.build.hooks.hook1]
# Second global hook

[tool.hatch.build.targets.wheel.hooks.hook2]
# Target-specific hook for wheel
```

When building a wheel, the execution order is:

1. `hook3.initialize()`
2. `hook1.initialize()`
3. `hook2.initialize()`
4. **[Wheel build happens here]**
5. `hook3.finalize()`
6. `hook1.finalize()`
7. `hook2.finalize()`

## Global Hooks Always Run First

Global hooks run before any target-specific hooks, regardless of where they're defined in the configuration file:

```toml
[tool.hatch.build.targets.wheel.hooks.my-target-hook]
# Runs SECOND (after global hooks)

[tool.hatch.build.hooks.my-global-hook]
# Runs FIRST
```

This ensures consistent behavior: global setup happens before target-specific customization.

## Multiple Global Hooks

When multiple global hooks are defined, they execute in the order they appear in the configuration file:

```toml
[tool.hatch.build.hooks.setup]
# Runs first

[tool.hatch.build.hooks.generate]
# Runs second

[tool.hatch.build.hooks.cleanup]
# Runs third
```

Initialization order: `setup` → `generate` → `cleanup` Finalization order: `setup` → `generate` → `cleanup` (same order)

## Multiple Target-Specific Hooks

When a single target has multiple hooks, they execute in definition order:

```toml
[tool.hatch.build.targets.wheel.hooks.generate-code]
# Runs first (after global hooks)

[tool.hatch.build.targets.wheel.hooks.compile-resources]
# Runs second
```

## Mixed Global and Target-Specific Hooks

When both global and target-specific hooks exist:

```toml
[tool.hatch.build.hooks.global-hook]
path = "global_hook.py"

[tool.hatch.build.targets.wheel.hooks.wheel-hook]
path = "wheel_hook.py"

[tool.hatch.build.targets.sdist.hooks.sdist-hook]
path = "sdist_hook.py"
```

**For wheel builds**:

1. `global-hook.initialize()`
2. `wheel-hook.initialize()`
3. Wheel build
4. `global-hook.finalize()`
5. `wheel-hook.finalize()`

**For sdist builds**:

1. `global-hook.initialize()`
2. `sdist-hook.initialize()`
3. Sdist build
4. `global-hook.finalize()`
5. `sdist-hook.finalize()`

## Build Data Modifications

Each hook can modify the `build_data` dictionary, which influences all subsequent operations:

```python
# hook1.initialize()
build_data["artifacts"].append("*.so")

# hook2.initialize() - sees the modified build_data from hook1
# Can further modify based on hook1's changes
build_data["force_include"]["/path/to/lib"] = "lib"
```

The final build uses the modified `build_data` from all hooks.

## Initialization vs Finalization

**Initialization** (`initialize()`)

- Runs before the build starts
- Can modify `build_data` to influence build behavior
- Cannot access generated artifacts

**Finalization** (`finalize()`)

- Runs after the build completes
- Receives the artifact path
- Receives final `build_data` reflecting target modifications
- Skipped if `--hooks-only` flag is used
- Cannot modify build behavior (too late)

**Example: Initialization modifies, finalization observes**

```python
class MyHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        # Modify build_data BEFORE build
        build_data["artifacts"].append("generated/*.py")

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        # Observe what was built, perform post-processing
        print(f"Artifact created at: {artifact_path}")
        # artifact_path is the actual built artifact
```

## Dependencies Between Hooks

If one hook depends on output from another, order them accordingly:

```toml
[tool.hatch.build.hooks.generate]
# Generates files

[tool.hatch.build.hooks.compile]
# Compiles the generated files - must run AFTER generate
```

The hooks will execute in this order during initialization and finalization.

## Controlling Execution with Environment Variables

You can disable specific hooks, which affects execution order:

```toml
[tool.hatch.build.hooks.hook-a]
enable-by-default = false

[tool.hatch.build.hooks.hook-b]
# Always enabled
```

**Default execution**: `hook-b` only **With environment variable**:

```bash
HATCH_BUILD_HOOK_ENABLE_HOOK_A=true hatch build
```

Now executes: `hook-a` → `hook-b`

## Disabling All Hooks

To skip all hook execution:

```bash
HATCH_BUILD_NO_HOOKS=true hatch build
```

No hooks run at all (neither initialization nor finalization).

## Hooks-Only Build

To run only hooks without the actual build:

```bash
HATCH_BUILD_HOOKS_ONLY=true hatch build
```

This runs only the `initialize()` methods, skipping the actual build and `finalize()` methods. Useful for pre-build setup validation.

## Predictable Behavior

The execution order is deterministic and predictable:

1. **Global hooks run first** - Establishes baseline state
2. **Target-specific hooks run second** - Customizes for specific target
3. **Initialization before build** - Prepares for build
4. **Finalization after build** - Post-processes results
5. **Definition order within scope** - Consistent order within global/target-specific

This design ensures that hooks can safely depend on earlier hooks' modifications and that the build process is consistent and reproducible.
