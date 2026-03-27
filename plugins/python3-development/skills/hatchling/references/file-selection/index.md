---
description: Reference guide for Hatchling's file selection, pattern matching, and build target configuration system. Provides comprehensive documentation on include/exclude patterns, path remapping, precedence rules, and real-world configuration examples.
keywords: [hatchling, file selection, build configuration, patterns, wheel, sdist]
---

# Hatchling File Selection and Patterns

Reference documentation for Hatchling's file selection and pattern matching system. Covers configuration options for controlling which files are included in distributions, how patterns are matched and prioritized, and how to remap paths during the build process.

## Contents

- `git-style-globs.md` - Pattern syntax and matching rules
- `include-exclude-patterns.md` - How to select and filter files
- `pattern-precedence.md` - Order of operations and precedence rules
- `only-include-option.md` - Explicit path selection
- `packages-option.md` - Package directory configuration
- `sources-option.md` - Path mapping and rewriting
- `force-include-option.md` - Forced file inclusion from anywhere
- `vcs-integration.md` - Git and Mercurial ignore file support
- `default-behavior.md` - Default inclusion/exclusion rules
- `explicit-path-selection.md` - Direct file and directory selection
- `artifacts.md` - Including VCS-ignored files
- `advanced-patterns.md` - Complex pattern examples

## Quick Reference

### Basic File Selection

```toml
[tool.hatch.build.targets.wheel]
# Include patterns (Git-style globs)
include = [
  "src/**/*.py",
  "data/*.json",
  "/LICENSE",
]

# Exclude patterns (takes precedence over include)
exclude = [
  "**/*.pyc",
  "tests/**",
  "*.tmp",
]
```

### VCS Integration

```toml
# Respect .gitignore/.hgignore (default behavior)
[tool.hatch.build.targets.sdist]
ignore-vcs = false  # Default

# Ignore VCS files
[tool.hatch.build.targets.wheel]
ignore-vcs = true
```

### Path Rewriting

```toml
[tool.hatch.build.targets.wheel.sources]
"src/mypackage" = "mypackage"  # Map src/mypackage → mypackage
"" = "prefix"  # Add prefix to all paths
```

### Forced Inclusion

```toml
[tool.hatch.build.targets.wheel.force-include]
"../external/lib.so" = "mypackage/lib.so"
"~/configs/settings.json" = "mypackage/data/settings.json"
```

## Key Concepts

1. **Pattern Matching**: Uses Git-style glob patterns (same as `.gitignore`)
2. **Precedence**: Exclude > Include > VCS ignore files
3. **Build Targets**: Different rules for `wheel`, `sdist`, and custom targets
4. **Path Mapping**: Rewrite paths during build with `sources`
5. **Artifacts**: Include VCS-ignored files (e.g., compiled extensions)

## Common Use Cases

### Exclude Tests from Wheel

```toml
[tool.hatch.build.targets.wheel]
exclude = ["tests", "**/test_*.py"]
```

### Include Only Package Code

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

### Add Generated Files

```toml
[tool.hatch.build.targets.wheel]
artifacts = ["*.so", "*.dll"]
```

### Map Source Layout

```toml
[tool.hatch.build.targets.wheel]
sources = ["src"]  # Strip 'src/' prefix
```

## See Also

- [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- `../build-targets/`
- `../build-hooks/`
