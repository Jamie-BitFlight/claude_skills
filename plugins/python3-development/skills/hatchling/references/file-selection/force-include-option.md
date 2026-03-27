---
description: The force-include configuration option for Hatchling builds. Explains highest precedence behavior, flexible source path formats, exact mapping requirements, security considerations, and use cases for including external files.
keywords: [force-include, hatchling, external files, highest precedence, file mapping, build configuration]
---

# Force-Include Option

Configuration reference for Hatchling's `force-include` option. Provides highest precedence for including files from anywhere in the filesystem with exact path mapping to distribution locations. Explains security considerations, path resolution rules, and interaction with build hooks.

## Basic Usage

```toml
[tool.hatch.build.targets.wheel.force-include]
"../external/lib.so" = "mypackage/lib.so"
"~/configs/production.yaml" = "mypackage/config.yaml"
"/absolute/path/to/file.txt" = "mypackage/data/file.txt"
```

## Key Features

### Highest Precedence

Force-include overrides everything:

- ✅ Overrides `exclude` patterns
- ✅ Overrides VCS ignore files
- ✅ Works with files outside project
- ✅ Can overwrite existing paths

### Flexible Source Paths

Accepts various path formats:

- **Relative paths**: `"../sibling/file.txt"`
- **Home directory**: `"~/configs/settings.json"`
- **Absolute paths**: `"/opt/shared/lib.so"`
- **Project paths**: `"src/excluded/but_needed.py"`

### Exact Mapping Required

Files must be mapped to exact destinations:

```toml
# ✅ Correct: File to file
"source/file.py" = "dest/file.py"

# ✅ Correct: Directory to directory
"source/dir" = "dest/dir"

# ❌ Wrong: File to directory
"source/file.py" = "dest/"  # Error!
```

## Common Use Cases

### 1. Including External Dependencies

```toml
[tool.hatch.build.targets.wheel.force-include]
# Shared libraries
"../shared/libs/custom.so" = "mypackage/lib/custom.so"

# Configuration from outside project
"~/company/configs/api_keys.json" = "mypackage/configs/api_keys.json"

# System libraries
"/usr/local/lib/special.so" = "mypackage/lib/special.so"
```

### 2. Overriding Exclusions

```toml
[tool.hatch.build.targets.wheel]
exclude = ["tests/**"]  # Exclude all tests

[tool.hatch.build.targets.wheel.force-include]
# But include specific test fixtures
"tests/fixtures/essential.json" = "mypackage/data/fixtures.json"
```

### 3. Build-Time Generated Files

```toml
[tool.hatch.build.targets.wheel.force-include]
# Files generated during build
"build/generated/version.py" = "mypackage/_version.py"
"build/compiled/extension.so" = "mypackage/extension.so"
```

### 4. Vendoring Dependencies

```toml
[tool.hatch.build.targets.wheel.force-include]
# Include specific version of a dependency
"../vendor/lib-1.2.3" = "mypackage/_vendor/lib"
"../vendor/patches/fix.py" = "mypackage/_vendor/patches/fix.py"
```

## Directory Mapping

### Including Entire Directories

```toml
[tool.hatch.build.targets.wheel.force-include]
# Map entire directory and contents
"../external/assets" = "mypackage/assets"
# Includes all files recursively
```

### Directory Contents to Root

```toml
[tool.hatch.build.targets.wheel.force-include]
# Map directory contents to distribution root
"../resources" = "/"
```

## Path Resolution

### Relative Paths

Resolved from project root:

```toml
[tool.hatch.build.targets.wheel.force-include]
# From project root
"../sibling" = "package/sibling"  # Parent directory
"../../shared" = "package/shared"  # Two levels up
"./local" = "package/local"  # Current directory
```

### Home Directory Expansion

```toml
[tool.hatch.build.targets.wheel.force-include]
# Expands to user's home directory
"~/.config/myapp/settings.json" = "mypackage/default_settings.json"
"~/Documents/data.csv" = "mypackage/data/sample.csv"
```

### Absolute Paths

```toml
[tool.hatch.build.targets.wheel.force-include]
# Full system paths
"/opt/mycompany/lib.so" = "mypackage/lib.so"
"/usr/share/myapp/data" = "mypackage/data"
```

## Advanced Scenarios

### Multiple Build Targets

Different force-includes for different targets:

```toml
# Development wheel
[tool.hatch.build.targets.dev.force-include]
"../dev-configs" = "mypackage/configs"
"../test-data" = "mypackage/test_data"

# Production wheel
[tool.hatch.build.targets.wheel.force-include]
"../prod-configs" = "mypackage/configs"
"/secure/keys/prod.key" = "mypackage/keys/api.key"
```

### Platform-Specific Files

```toml
# Linux wheel
[tool.hatch.build.targets.linux-wheel.force-include]
"../build/linux/lib.so" = "mypackage/lib.so"

# Windows wheel
[tool.hatch.build.targets.windows-wheel.force-include]
"../build/windows/lib.dll" = "mypackage/lib.dll"

# macOS wheel
[tool.hatch.build.targets.macos-wheel.force-include]
"../build/macos/lib.dylib" = "mypackage/lib.dylib"
```

### Overwriting Files

Force-include can overwrite files from other sources:

```toml
[tool.hatch.build.targets.wheel]
include = ["mypackage/**"]

[tool.hatch.build.targets.wheel.force-include]
# Overwrite the included version with custom one
"../custom/special.py" = "mypackage/special.py"
```

## Working with Build Hooks

### Including Hook-Generated Files

```toml
# Build hook generates files
[tool.hatch.build.hooks.custom]
path = "build_hooks.py"

# Force-include the generated files
[tool.hatch.build.targets.wheel.force-include]
"build/generated/bindings.py" = "mypackage/bindings.py"
"build/generated/lib.so" = "mypackage/lib.so"
```

### Example Build Hook

```python
# build_hooks.py
import subprocess
from pathlib import Path

def build():
    # Generate files
    subprocess.run(["make", "build"])

    # Files will be force-included by configuration
    assert Path("build/generated/bindings.py").exists()
```

## Error Handling

### Non-Existent Source

```toml
[tool.hatch.build.targets.wheel.force-include]
"nonexistent/file.txt" = "package/file.txt"
# Error: Source path does not exist!
```

### Invalid Mapping

```toml
[tool.hatch.build.targets.wheel.force-include]
# ❌ Cannot map file to directory path
"file.txt" = "package/"

# ✅ Must specify complete path
"file.txt" = "package/file.txt"
```

## Best Practices

### 1. Document External Dependencies

```toml
[tool.hatch.build.targets.wheel.force-include]
# Company-wide shared library (must be built first)
"../shared-libs/company.so" = "mypackage/lib/company.so"

# Generated by pre-build script
"build/generated/version.py" = "mypackage/_version.py"
```

### 2. Use for Exceptional Cases

```toml
# Good: Specific external file needed
[tool.hatch.build.targets.wheel.force-include]
"../license/COMPANY_LICENSE" = "mypackage/LICENSE"

# Bad: Using for regular project files
[tool.hatch.build.targets.wheel.force-include]
"src/mypackage/module.py" = "mypackage/module.py"
# Use include/only-include instead!
```

### 3. Verify Paths Exist

```bash
# Before configuring force-include
ls -la ../external/lib.so
ls -la ~/configs/settings.json

# Test build
hatch build -t wheel
```

### 4. Keep Mappings Organized

```toml
[tool.hatch.build.targets.wheel.force-include]
# External libraries
"../libs/custom.so" = "mypackage/lib/custom.so"
"../libs/helper.so" = "mypackage/lib/helper.so"

# Configuration files
"~/configs/prod.yaml" = "mypackage/configs/prod.yaml"
"~/configs/defaults.yaml" = "mypackage/configs/defaults.yaml"

# Generated files
"build/version.py" = "mypackage/_version.py"
"build/metadata.json" = "mypackage/_metadata.json"
```

## Real-World Examples

### Example 1: C Extension with External Dependencies

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]

[tool.hatch.build.targets.wheel.force-include]
# Compiled C extension
"build/lib/myext.cpython-39-x86_64-linux-gnu.so" = "mypackage/myext.so"

# Required shared libraries
"/usr/local/lib/libcustom.so.1" = "mypackage/.libs/libcustom.so.1"
```

### Example 2: Including Test Data Selectively

```toml
[tool.hatch.build.targets.wheel]
exclude = ["tests/**", "test_data/**"]

[tool.hatch.build.targets.wheel.force-include]
# Include only essential test fixtures
"test_data/fixtures/minimal.json" = "mypackage/data/test_fixture.json"
```

### Example 3: Multi-Project Shared Resources

```toml
[tool.hatch.build.targets.wheel.force-include]
# Shared across multiple projects
"../../shared/assets/logo.png" = "mypackage/static/logo.png"
"../../shared/templates/base.html" = "mypackage/templates/base.html"
"../../shared/configs/common.yaml" = "mypackage/configs/common.yaml"
```

## Troubleshooting

### Files Not Included

1. **Check source exists**: `ls -la path/to/source`
2. **Verify path format**: Use correct path style for your OS
3. **Check destination**: Ensure valid destination path

### Files in Wrong Location

```toml
# Problem: File appears in wrong place
"../file.txt" = "wrong/path.txt"

# Solution: Fix destination path
"../file.txt" = "correct/path.txt"
```

### Build Errors

```bash
# Debug with verbose output
hatch build -t wheel -v

# Check resulting package
unzip -l dist/*.whl | grep "forced_file"
```

## Security Considerations

### Sensitive Files

Be careful with sensitive data:

```toml
# ⚠️ Warning: Including sensitive files
[tool.hatch.build.targets.wheel.force-include]
"~/.ssh/id_rsa" = "package/keys/private.key"  # DON'T DO THIS!
"/etc/passwd" = "package/data/users.txt"  # DON'T DO THIS!

# ✅ Better: Use environment variables or secure storage
# Include only public/non-sensitive configuration
"configs/public_settings.json" = "package/settings.json"
```

### Path Traversal

Be aware of security implications:

```toml
# Validate sources are intentional
[tool.hatch.build.targets.wheel.force-include]
"../../../../etc/passwd" = "data/file.txt"  # Suspicious!
```

## See Also

- `pattern-precedence.md`
- `include-exclude-patterns.md`
- `artifacts.md`
