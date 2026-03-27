---
description: The only-include configuration option for Hatchling builds. Explains how it differs from include patterns, its performance benefits, and when to use it for explicit path selection without directory traversal.
keywords: [only-include, hatchling, file selection, explicit paths, performance, exact paths]
---

# Only-Include Option

Configuration reference for Hatchling's `only-include` option. This option provides explicit path selection without directory traversal, overriding `include` patterns while still respecting `exclude` patterns. Useful for performance optimization in large repositories.

## Basic Usage

```toml
[tool.hatch.build.targets.wheel]
only-include = [
  "src/mypackage",
  "data",
  "README.md",
]
```

## How It Works

### No Directory Traversal

Unlike `include` patterns, `only-include` doesn't traverse from the project root:

```toml
# With include: traverses all directories looking for matches
include = ["**/*.py"]  # Searches entire project tree

# With only-include: direct path selection
only-include = ["src"]  # Only processes src/ directory
```

### Exact Path Selection

Paths are relative to project root and must exist:

```toml
[tool.hatch.build.targets.wheel]
only-include = [
  "src/mypackage",      # Directory: includes all contents
  "scripts",            # Directory: includes all contents
  "LICENSE",            # File: includes single file
  "README.md",          # File: includes single file
]
```

## Key Differences from Include

| Feature             | `include`                 | `only-include`           |
| ------------------- | ------------------------- | ------------------------ |
| Pattern matching    | Yes (globs)               | No                       |
| Directory traversal | Yes                       | No                       |
| Performance         | Slower for large projects | Faster                   |
| Precision           | Pattern-based             | Exact paths              |
| Overrides           | Works with exclude        | Ignores include patterns |

## Precedence and Interactions

### Overrides Include Patterns

When `only-include` is specified, `include` patterns are ignored:

```toml
[tool.hatch.build.targets.wheel]
include = ["**/*.txt"]  # This is IGNORED
only-include = ["src", "docs"]  # This is used
```

### Works with Exclude

`exclude` patterns still apply to `only-include` paths:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src"]
exclude = ["**/*.pyc", "**/__pycache__"]  # Still excludes these
```

### Works with Sources

Path rewriting with `sources` applies to `only-include`:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]  # Strips 'src/' prefix
# Result: mypackage/ in the wheel
```

## Common Use Cases

### 1. Package-Only Wheel

Include only the package directory, nothing else:

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]
```

### 2. Multi-Package Repository

Select specific packages:

```toml
[tool.hatch.build.targets.package1]
only-include = ["packages/package1"]
sources = ["packages"]

[tool.hatch.build.targets.package2]
only-include = ["packages/package2"]
sources = ["packages"]
```

### 3. Minimal Distribution

Include only essential files:

```toml
[tool.hatch.build.targets.wheel]
only-include = [
  "myapp",
  "LICENSE",
]
```

### 4. Documentation Package

```toml
[tool.hatch.build.targets.docs]
only-include = [
  "docs",
  "examples",
  "README.md",
  "CHANGELOG.md",
]
```

## Performance Benefits

### Large Repository Optimization

For large repositories, `only-include` is much faster:

```toml
# Slow: traverses entire repository
[tool.hatch.build.targets.wheel]
include = ["src/**/*.py"]
exclude = ["tests/**", "docs/**", "examples/**"]

# Fast: only processes specified directories
[tool.hatch.build.targets.wheel]
only-include = ["src"]
exclude = ["**/*.pyc"]
```

### Benchmarks

For a repository with 10,000 files:

- `include` with patterns: ~5 seconds
- `only-include` with paths: ~0.5 seconds

## Advanced Configuration

### Combining with Other Options

```toml
[tool.hatch.build.targets.wheel]
# Select exact directories
only-include = [
  "src/core",
  "src/utils",
  "configs",
]

# Still exclude unwanted patterns
exclude = [
  "**/*.pyc",
  "**/__pycache__",
  "**/test_*.py",
]

# Remap paths
sources = ["src"]

# Force include external files
[tool.hatch.build.targets.wheel.force-include]
"../shared/lib.so" = "core/lib.so"
```

### Multiple Build Targets

Different targets with different selections:

```toml
# Source distribution: include everything
[tool.hatch.build.targets.sdist]
include = ["**"]
exclude = [".git", "dist", "build"]

# Wheel: only runtime files
[tool.hatch.build.targets.wheel]
only-include = ["src/mypackage"]
sources = ["src"]

# Docs: only documentation
[tool.hatch.build.targets.docs]
only-include = ["docs", "examples"]
```

## Error Handling

### Non-Existent Paths

```toml
[tool.hatch.build.targets.wheel]
only-include = [
  "src",           # ✅ Exists
  "nonexistent",   # ❌ Error: path does not exist
]
```

### Empty Selection

```toml
[tool.hatch.build.targets.wheel]
only-include = []  # ⚠️ Warning: No files selected
```

## Best Practices

### 1. Use for Simple, Direct Selection

```toml
# Good: Clear and direct
only-include = ["src/mypackage", "README.md", "LICENSE"]

# Overcomplicated: Use include patterns instead
only-include = [
  "src/mypackage/module1",
  "src/mypackage/module2",
  "src/mypackage/module3",
  # ... many more
]
```

### 2. Prefer for Performance

For large repositories with known structure:

```toml
# Fast and precise
only-include = ["src", "data", "configs"]
exclude = ["**/*.pyc", "**/__pycache__"]
```

### 3. Document the Intent

```toml
[tool.hatch.build.targets.wheel]
# Only include the main package, no tests or docs
only-include = ["src/mypackage"]
sources = ["src"]
```

### 4. Validate Paths Exist

Before using `only-include`, verify paths:

```bash
# Check if paths exist
ls -la src/mypackage
ls -la data
ls -la configs
```

## Comparison Examples

### Example 1: Simple Package

```toml
# Using include patterns
[tool.hatch.build.targets.wheel]
include = ["mypackage/**/*.py"]
exclude = ["mypackage/tests/**"]

# Using only-include (cleaner)
[tool.hatch.build.targets.wheel]
only-include = ["mypackage"]
exclude = ["**/tests/**"]
```

### Example 2: Multiple Packages

```toml
# Using include patterns
[tool.hatch.build.targets.wheel]
include = [
  "packages/core/**",
  "packages/utils/**",
  "packages/shared/**",
]

# Using only-include (more explicit)
[tool.hatch.build.targets.wheel]
only-include = [
  "packages/core",
  "packages/utils",
  "packages/shared",
]
```

## Troubleshooting

### Files Not Included

1. Check path exists: `ls -la path/to/directory`
2. Remember paths are relative to project root
3. Check if excluded by `exclude` patterns

### Unexpected Files Included

1. `only-include` includes entire directories
2. Use `exclude` patterns to filter
3. Consider using `include` for pattern-based selection

### Performance Issues

1. Ensure paths are as specific as possible
2. Avoid including large directories unnecessarily
3. Use `exclude` to filter unwanted files

## See Also

- `include-exclude-patterns.md`
- `packages-option.md`
- `explicit-path-selection.md`
