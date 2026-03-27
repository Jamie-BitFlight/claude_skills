---
description: Pattern precedence rules for Hatchling file selection. Explains the five-level precedence hierarchy from force-include (highest) to VCS ignore files (lowest), with examples and algorithms for understanding resolution order.
keywords: [precedence, hatchling, force-include, exclude, file selection, pattern resolution]
---

# Pattern Precedence in Hatchling

Reference for Hatchling's five-level pattern precedence hierarchy. Explains how `force-include`, `exclude`, `artifacts`, `include`, and VCS ignore files are evaluated, with resolution algorithms and common precedence mistakes to avoid.

## Precedence Hierarchy

From highest to lowest precedence:

1. **force-include** - Always wins, overrides everything
2. **exclude** - Overrides include and VCS patterns
3. **artifacts** - Like include but for VCS-ignored files
4. **include** / **only-include** - Overrides VCS patterns
5. **VCS ignore files** (.gitignore/.hgignore) - Base behavior

<eg>
┌─────────────────┐
│  force-include  │  ← Highest Priority
├─────────────────┤
│     exclude     │
├─────────────────┤
│    artifacts    │
├─────────────────┤
│  include/only   │
├─────────────────┤
│   VCS ignore    │  ← Lowest Priority
└─────────────────┘
</eg>

## How Precedence Works

### Rule 1: Force-Include Overrides Everything

```toml
[tool.hatch.build.targets.wheel]
exclude = ["tests/**"]  # Excludes tests directory

[tool.hatch.build.targets.wheel.force-include]
"tests/fixtures/data.json" = "package/test_data.json"
# This file WILL be included despite the exclude pattern
```

### Rule 2: Exclude Beats Include

```toml
[tool.hatch.build.targets.wheel]
include = ["src/**/*.py"]     # Include all Python files
exclude = ["src/**/test_*.py"] # But exclude test files

# Result: All Python files EXCEPT test_*.py are included
```

### Rule 3: Include Beats VCS Ignore

```toml
# Even if .gitignore contains "*.log"
[tool.hatch.build.targets.wheel]
include = ["debug.log"]  # This file WILL be included
```

### Rule 4: Artifacts for VCS-Ignored Files

```toml
# If .gitignore contains "*.so"
[tool.hatch.build.targets.wheel]
artifacts = ["lib/*.so"]  # These files WILL be included
exclude = ["lib/test.so"]  # But this one will be excluded
```

## Detailed Examples

### Example 1: Complex Precedence Chain

```toml
# .gitignore contains:
# *.pyc
# __pycache__/
# build/
# *.log

[tool.hatch.build.targets.wheel]
# Level 4: Include overrides .gitignore
include = [
  "src/**",           # Includes everything in src/
  "important.log",    # Includes this despite .gitignore
]

# Level 3: Artifacts for ignored files
artifacts = [
  "build/lib.so",     # Includes this despite .gitignore
]

# Level 2: Exclude overrides include
exclude = [
  "src/debug/**",     # Excludes debug directory
  "**/__pycache__",   # Ensures no cache directories
]

# Level 1: Force-include overrides everything
[tool.hatch.build.targets.wheel.force-include]
"src/debug/critical.py" = "package/critical.py"  # Included despite exclude
```

Result:

- ✅ All of `src/` except `src/debug/`
- ✅ `important.log` (include overrides .gitignore)
- ✅ `build/lib.so` (artifacts)
- ✅ `src/debug/critical.py` → `package/critical.py` (force-include)
- ❌ `src/debug/**` other files (excluded)
- ❌ `**/__pycache__` (excluded)
- ❌ Other `*.pyc`, `*.log` files (gitignored)

### Example 2: Pattern Order Within Same Level

Within the same precedence level, patterns are evaluated in order:

```toml
[tool.hatch.build.targets.wheel]
include = [
  "data/**",         # First: Include everything in data/
  "!data/temp/**",   # Second: Would exclude temp/ if negation worked
]

# Since negation doesn't work in include, use exclude:
include = ["data/**"]
exclude = ["data/temp/**"]
```

### Example 3: Multiple Exclude Patterns

```toml
[tool.hatch.build.targets.wheel]
include = ["package/**"]

exclude = [
  "**/*.pyc",        # Pattern 1: Compiled files
  "**/__pycache__",  # Pattern 2: Cache directories
  "**/test_*.py",    # Pattern 3: Test files
  "package/old/**",  # Pattern 4: Old code
]

# All exclude patterns are combined with OR logic
# A file is excluded if it matches ANY pattern
```

## Special Cases

### Only-Include vs Include

`only-include` has special behavior:

```toml
[tool.hatch.build.targets.wheel]
# Method 1: Include with patterns
include = ["src/**/*.py"]  # Uses pattern matching

# Method 2: Only-include with exact paths
only-include = ["src"]  # Includes entire directory, no traversal
```

When `only-include` is used:

- It takes precedence over `include`
- No directory traversal from root
- More efficient for large projects

### Packages Option

The `packages` option is a special case:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

# Equivalent to:
only-include = ["src/mypackage"]
sources = ["src"]
```

### Artifacts with Negation

Artifacts support negation for fine-grained control:

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
  "**/*.so",          # Include all .so files
  "!tests/**/*.so",   # Except those in tests/
  "!**/debug_*.so",   # And debug versions
]

# Negation patterns must come after inclusive patterns
```

## Precedence Resolution Algorithm

Here's how Hatchling resolves file inclusion:

```python
# Pseudo-code for file inclusion logic
def should_include_file(path):
    # 1. Check force-include (highest priority)
    if path in force_include_mappings:
        return True

    # 2. Check exclude patterns
    if matches_any_pattern(path, exclude_patterns):
        return False

    # 3. Check artifacts (for VCS-ignored files)
    if is_vcs_ignored(path):
        if matches_any_pattern(path, artifact_patterns):
            # Check for negation in artifacts
            if not matches_any_pattern(path, artifact_negation_patterns):
                return True
        return False  # Ignored and not an artifact

    # 4. Check include/only-include
    if only_include_paths:
        return path in only_include_paths
    if include_patterns:
        return matches_any_pattern(path, include_patterns)

    # 5. Default: include if not VCS-ignored
    return not is_vcs_ignored(path)
```

## Debugging Precedence Issues

### Check Pattern Order

```bash
# Use verbose mode to see pattern matching
hatch build -t wheel -v

# Check what's included
tar -tzf dist/*.tar.gz  # For sdist
unzip -l dist/*.whl     # For wheel
```

### Common Precedence Mistakes

1. **Expecting include to override exclude**

   ```toml
   # WRONG: exclude always wins
   exclude = ["tests/**"]
   include = ["tests/important.py"]  # Won't work!

   # RIGHT: Use force-include
   exclude = ["tests/**"]
   [tool.hatch.build.targets.wheel.force-include]
   "tests/important.py" = "tests/important.py"
   ```

2. **Negation in wrong place**

   ```toml
   # WRONG: Negation doesn't work in include/exclude
   include = ["src/**", "!src/debug/**"]

   # RIGHT: Use exclude
   include = ["src/**"]
   exclude = ["src/debug/**"]
   ```

3. **Artifact patterns too late**

   ```toml
   # WRONG: Order matters in artifacts
   artifacts = [
     "!tests/*.so",  # Negation before inclusion
     "*.so",
   ]

   # RIGHT: Include first, then negate
   artifacts = [
     "*.so",
     "!tests/*.so",
   ]
   ```

## Best Practices

1. **Use the right tool for the job**

   - `force-include`: For files that must be included
   - `exclude`: For filtering unwanted files
   - `artifacts`: For VCS-ignored build products
   - `include`: For standard file selection

2. **Layer patterns by precedence**

   ```toml
   # Start broad
   include = ["src/**"]

   # Filter with exclude
   exclude = ["src/**/test_*", "src/**/*.pyc"]

   # Force critical files
   [tool.hatch.build.targets.wheel.force-include]
   "external/required.so" = "package/required.so"
   ```

3. **Document complex precedence**

   ```toml
   # This file is gitignored but needed in wheel
   artifacts = ["build/generated.py"]

   # Override exclude pattern for critical file
   [tool.hatch.build.targets.wheel.force-include]
   "tests/fixtures/essential.json" = "package/data/essential.json"
   ```

## See Also

- `include-exclude-patterns.md`
- `force-include-option.md`
- `artifacts.md`
