---
category: wheel-target
topics: [editable, pth-files, development, pip-install-e, pep-660]
related: [wheel-versioning.md, wheel-configuration.md, file-selection.md]
---

# Editable Wheel Mode

When assisting users with development installations using editable wheels, reference this guide to explain editable wheel functionality, .pth file mechanisms, and development workflow setup.

## What Are Editable Wheels?

Editable wheels are special wheels that enable development installations where code changes are immediately reflected without reinstalling. When explaining this feature:

Reference that editable wheels:

- Ship only `.pth` files or import hooks instead of actual code
- Point to the source directory rather than copying code
- Allow immediate visibility of code changes during development
- Implement PEP 660 editable installs
- Support both dev-mode-dirs and dev-mode-exact approaches

## PEP 660 and Editable Installs

Help users understand the standard:

PEP 660 defines how editable installs work. When users run `pip install -e .`:

1. **Wheel is built** - Hatchling builds an "editable" version of the wheel
2. **No code copied** - Instead of packaging code, a `.pth` file is created
3. **Path added to sys.path** - The `.pth` file adds the source directory to Python's path
4. **Changes reflected** - Code changes are immediately available without reinstalling

## Implicit Editable Wheel Format

Explain that the editable format is implicit:

```bash
pip install -e .
```

This automatically uses the editable wheel format. Users don't need to specify anything in configuration; Hatchling handles it automatically for editable installs.

## How .pth Files Work

Help users understand the mechanism:

A `.pth` file is a simple text file in site-packages that modifies `sys.path`:

```toml
# mypackage-1.0.0.dist-info/mypackage__editable_install__.pth
/path/to/project/src
```

When Python starts, it reads `.pth` files in site-packages and adds those paths to `sys.path`. This allows imports to find the code in the source directory.

## Dev Mode Directories Configuration

When users need to customize dev mode:

```toml
[tool.hatch.build]
dev-mode-dirs = ["."]
```

Or target-specific:

````toml
[tool.hatch.build.targets.wheel]
# Implicit, but can be overridden if needed
```toml

This specifies which directories are added to sys.path during editable installs.

### When to Configure Dev Mode

Explain the scenarios:

1. **Src-layout** - Default works (adds `src/`)
2. **Custom layout** - May need to specify explicit paths
3. **Multiple packages** - May need multiple entries

Example:

```toml
[tool.hatch.build]
dev-mode-dirs = ["src", "vendor"]
````

## Editable Wheels with Force-Include

When users need special handling for editable installs:

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/data" = "mypackage/data"
```

The `force-include` option works with editable installs:

- **Standard wheels** - Files are copied
- **Editable wheels** - force-include is still respected by default (Hatchling v1.4.0+)

For different behavior in editable mode:

```toml
# In hatch_build.py
def get_wheel_config():
    return {
        'force_include': {
            'src/data': 'mypackage/data',
        },
        'force_include_editable': {
            'dev/data': 'mypackage/data',  # Different path for editable
        }
    }
```

## Dev Mode Exact Option

For advanced users needing exact path matching:

```toml
[tool.hatch.build]
dev-mode-exact = true
```

This uses exact path matching instead of traversal. When enabled:

- Requires exact directory paths in `dev-mode-dirs`
- No automatic subdirectory discovery
- More predictable but less flexible

Note: IDE autocompletion may not work with `dev-mode-exact`.

## Editable Installation Workflow

Guide users through the development workflow:

**Initial setup:**

```toml
git clone https://github.com/user/myproject.git
cd myproject
pip install -e .
```

**Development:**

```toml
# Edit src/mypackage/module.py
# Changes are immediately reflected:
import mypackage  # Imports latest code
```

**No reinstall needed** between edits.

## Troubleshooting Editable Installs

Help users diagnose issues:

### Changes Not Reflected

If code changes aren't visible:

1. **Restart Python** - Some tools cache modules
2. **Check sys.path** - Verify source directory is in path:

   ```python
   import sys

   print(sys.path)
   ```

3. **Verify .pth file** - Check it exists in site-packages
4. **Check file location** - Ensure edits are in the right source directory

### Import Errors

If imports fail during editable install:

1. **Verify package structure** - Ensure `__init__.py` exists
2. **Check dev-mode-dirs** - Confirm correct paths are configured
3. **Clear imports** - Restart Python interpreter
4. **Reinstall if needed** - `pip install -e . --force-reinstall`

### IDE Configuration

For IDE support during editable development:

IDEs need to know about the source paths. Configure in IDE settings:

- **VSCode** - Set pythonPath to environment with editable install
- **PyCharm** - Mark source directories as sources root
- **Others** - Configure project interpreter and source paths

## Comparison: Standard vs. Editable Wheels

Help users understand the difference:

| Aspect       | Standard Wheel         | Editable Wheel                       |
| ------------ | ---------------------- | ------------------------------------ |
| Build        | Copies code into wheel | Creates .pth file pointing to source |
| Installation | Code in site-packages  | Code in source directory             |
| Code changes | Require reinstall      | Immediately available                |
| Size         | Larger (includes code) | Tiny (only .pth file)                |
| Use case     | Distribution           | Development                          |
| Speed        | Faster execution       | Slightly slower (via sys.path)       |

## Building Editable Wheels Explicitly

When users need to build and inspect editable wheels:

```bash
python -m build --outdir dist -w -x 'wheel[editable]'
```

Or with Hatchling directly:

````toml
# Hatchling doesn't build editable wheels directly via CLI
# Use pip install -e instead for standard workflow
```toml

Editable wheels are normally only built by pip during `pip install -e`, not through normal build tools.

## Build Hooks and Editable Wheels

Explain how build hooks interact with editable installs:

```toml
# In hatch_build.py
def get_wheel_config():
    return {
        # This modifies both standard and editable wheels
        'dependencies': ['additional-dep'],
        'extra_metadata': {'build_info.json': 'metadata'},
    }
````

Build hooks still execute for editable wheels, allowing dynamic metadata generation.

## Performance Considerations

When users ask about editable install performance:

- **Import speed** - Slightly slower than standard wheels (sys.path lookup adds small overhead)
- **Modification detection** - No tracking of file changes (just reads from disk)
- **Compilation** - Any Cython or compiled code still needs to be built
- **Best practice** - Use editable installs only during development; use standard wheels for distribution

## Practical Example

Provide a complete development workflow example:

```toml
# Clone and setup
git clone https://github.com/user/myproject.git
cd myproject

# Install in editable mode
pip install -e .

# Develop
# ... make changes to src/mypackage/...

# Test changes
pytest tests/

# Changes are immediately visible without reinstalling

# When ready to distribute
python -m build  # Creates standard wheel for distribution
```

## Relation to Dev Environments

Explain how editable installs fit into the workflow:

Editable installs are part of the development environment setup. Best practices:

1. **Development** - Use `pip install -e .` for editable installs
2. **Testing** - Run tests against editable installation
3. **Distribution** - Build standard wheels with `python -m build`
4. **Production** - Install standard wheels via pip or package manager

This separation ensures development convenience without affecting distribution quality.

## Summary

Provide quick reference:

- **What**: Editable wheels point to source directory instead of copying code
- **How**: Via `.pth` files that add source to sys.path
- **Use**: `pip install -e .` for development
- **Benefit**: Immediate visibility of code changes
- **Configuration**: Usually automatic; can customize with `dev-mode-dirs`
- **Troubleshooting**: Restart Python, check sys.path, verify file locations
