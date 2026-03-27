---
category: Advanced Build Features
topics: [force-include, file-inclusion, permissions, symlinks, build-artifacts]
related: [build-data-passing.md, path-rewriting.md, build-context.md]
---

# Force Include Permissions and Symlinks

When helping users bundle external resources, generated files, and non-Python assets, guide them to use the `force-include` feature. This enables inclusion of files from arbitrary filesystem locations in distribution packages.

## Overview

`force-include` is a mapping of source filesystem paths to distribution paths. Reference this to help users include files that would otherwise be excluded by standard package discovery mechanisms.

## Basic Configuration

In `pyproject.toml`:

```toml
[tool.hatchling.targets.wheel]
force-include = { path = "path/in/distribution" }
```

For multiple files:

```toml
[tool.hatchling.targets.wheel.force-include]
assets/logo.png = "mypackage/assets/logo.png"
build/generated.py = "mypackage/generated.py"
../external-resource.txt = "mypackage/data/external.txt"
```

## Permissions and File Modes

Hatchling preserves file permissions from the source filesystem when including files:

- Executable files (`mode 0o755`) retain executable bit
- Regular files (`mode 0o644`) are included as readable text/data files
- Directory permissions are handled by the wheel archive format

### Setting Executable Files

```toml
[tool.hatchling.targets.wheel.force-include]
scripts/build-helper.sh = "mypackage/_scripts/build-helper.sh"
```

The source file's permission bits are preserved in the wheel archive.

## Symlink Handling

Symlinks present challenges across different platforms and in distribution formats:

### Current Behavior

- **Local Builds**: Symlinks are followed (their targets are included, not the links themselves)
- **Wheels**: Cannot contain symlinks as they're not portable across all platforms
- **Source Distributions**: Symlinks may be included depending on the version control system

### Known Limitations

GitHub Issue #1130 documents platform-specific symlink handling:

- macOS and Linux treat symlinks differently than Windows
- Symlinks in distributed wheels cause portability issues
- Broken symlinks can cause include failures

### Workaround for Symlinked Content

If you need to include content referenced via symlink:

```python
# In a build hook's initialize() method
import os
import shutil

class SymlinkResolutionHook:
    def initialize(self, version, build_data):
        # Resolve symlinks before building
        source = "build/compiled/output"
        target = "build/resolved/output"

        # Copy symlink targets to a real directory
        for root, dirs, files in os.walk(source):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, source)
                dest_path = os.path.join(target, rel_path)

                # Dereference symlinks during copy
                shutil.copy2(src_path, dest_path, follow_symlinks=True)
```

Then use `force-include` with the resolved directory.

## Use Cases

### Including Generated Files

```toml
[tool.hatchling.targets.wheel.force-include]
build/generated/version.py = "mypackage/_version.py"
dist/compiled.so = "mypackage/_compiled.so"
```

### Bundling External Assets

```toml
[tool.hatchling.targets.wheel.force-include]
../assets/icons = "mypackage/assets/icons"
../data/db.sqlite = "mypackage/data/db.sqlite"
```

### Multi-Project Resources

```toml
[tool.hatchling.targets.wheel.force-include]
../../shared-resources/templates = "mypackage/templates"
../../docs/api-reference.html = "mypackage/docs/api-reference.html"
```

## Build Hook Integration

For more complex scenarios, manipulate `build_data['force_include']` in a build hook:

```python
class DynamicIncludeHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Dynamically add files based on build conditions
        if os.path.exists('dist/wheels'):
            build_data['force_include']['dist/wheels'] = 'mypackage/wheels'

        # Include optional assets
        if os.getenv('INCLUDE_DOCS'):
            build_data['force_include']['docs/_build/html'] = 'mypackage/docs'
```

## Best Practices

- Use relative paths from project root for clarity
- Ensure source paths exist before building (validate in hooks)
- Document why external files are needed
- Consider maintenance burden of force-include patterns
- For symlinked content, resolve in build hooks rather than in force-include
- Test wheel contents on target platforms to verify portable inclusion

## Troubleshooting

**Issue**: "Path does not exist" error

- Verify source path is relative to project root
- Check that generated files are created before wheel build
- Use a build hook to generate files before force-include processes them

**Issue**: Symlinks not working

- Use symlink resolution hook to copy targets
- Include the dereferenced files instead
- Check file permissions after wheel extraction

## See Also

- `path-rewriting.md` - Distribution path modification
- `build-data-passing.md` - Modifying build data in hooks
- `build-context.md` - Accessing build environment information
