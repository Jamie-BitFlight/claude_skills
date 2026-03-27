---
description: Git-style glob pattern syntax for Hatchling file selection. Covers pattern matching rules, anchoring, character classes, recursive matching, and differences from standard Unix glob patterns.
keywords: [glob patterns, git-style, pattern matching, hatchling, include, exclude]
---

# Git-Style Glob Patterns in Hatchling

Hatchling file selection uses Git-style glob patterns identical to `.gitignore` syntax. This document explains pattern syntax, matching behavior, anchoring rules, and character classes Claude needs to generate correct patterns for build configuration.

## Pattern Syntax

### Basic Patterns

| Pattern              | Description                             | Example Match                                             |
| -------------------- | --------------------------------------- | --------------------------------------------------------- |
| `*`                  | Matches any string except `/`           | `*.py` matches `file.py` but not `dir/file.py`            |
| `**`                 | Matches any string including `/`        | `**/*.py` matches all `.py` files recursively             |
| `?`                  | Matches any single character except `/` | `test?.py` matches `test1.py`, `testA.py`                 |
| `[...]`              | Matches any character in brackets       | `test[123].py` matches `test1.py`, `test2.py`, `test3.py` |
| `[!...]` or `[^...]` | Matches any character NOT in brackets   | `test[!0-9].py` matches `testA.py` but not `test1.py`     |

### Path Patterns

| Pattern       | Description                      | Example                              |
| ------------- | -------------------------------- | ------------------------------------ |
| `/` prefix    | Pattern relative to project root | `/LICENSE` matches only root LICENSE |
| No `/` prefix | Pattern matches anywhere         | `*.txt` matches any `.txt` file      |
| `/` suffix    | Match directories only           | `__pycache__/` matches directories   |
| `!` prefix    | Negation (for artifacts)         | `!*.log` excludes log files          |

## Pattern Matching Rules

### 1. Anchoring

```toml
# Anchored to root (starts with /)
include = ["/README.md"]  # Only matches root README.md

# Unanchored (no leading /)
include = ["README.md"]  # Matches README.md anywhere
```

### 2. Recursive Matching

```toml
# Match all Python files recursively
include = ["**/*.py"]

# Match Python files in specific directory tree
include = ["src/**/*.py"]

# Match all files in tests directory
include = ["tests/**"]
```

### 3. Directory Matching

```toml
# Match directory and all contents
include = ["docs/"]

# Match specific files in directory
include = ["docs/*.md"]

# Exclude all __pycache__ directories
exclude = ["**/__pycache__/"]
```

## Character Classes

### Ranges

```toml
# Match numbered test files
include = ["test[0-9].py"]  # test0.py through test9.py

# Match letter suffixes
include = ["file[a-z].txt"]  # filea.txt through filez.txt

# Multiple ranges
include = ["data[0-9a-f].bin"]  # hex digit suffixes
```

### Special Characters

```toml
# Escape special characters with backslash
include = ["file\\[1\\].txt"]  # Matches "file[1].txt" literally

# Match files with spaces (no escaping needed)
include = ["my file.txt"]
```

## Examples

### Common Patterns

```toml
[tool.hatch.build]
include = [
  # All Python files
  "**/*.py",

  # All Markdown docs
  "**/*.md",

  # Config files in root
  "/*.toml",
  "/*.ini",
  "/*.cfg",

  # Specific directory trees
  "src/**",
  "tests/**/*.py",

  # Data files
  "data/**/*.json",
  "data/**/*.csv",
]

exclude = [
  # Compiled Python files
  "**/*.pyc",
  "**/*.pyo",
  "**/*.pyd",

  # Cache directories
  "**/__pycache__/",
  "**/.pytest_cache/",

  # Temporary files
  "**/*.tmp",
  "**/*.bak",
  "**/*~",

  # OS-specific files
  "**/.DS_Store",
  "**/Thumbs.db",

  # Editor files
  "**/.vscode/",
  "**/.idea/",
  "**/*.swp",
]
```

### Platform-Specific Patterns

```toml
# Include platform-specific files
include = [
  "lib/**/*.so",     # Linux shared libraries
  "lib/**/*.dylib",  # macOS dynamic libraries
  "lib/**/*.dll",    # Windows DLLs
]
```

### Negation in Artifacts

```toml
[tool.hatch.build.targets.wheel]
# Include all .so files except in test directories
artifacts = [
  "**/*.so",
  "!tests/**/*.so",
  "!**/test_*.so",
]
```

## Pattern Precedence

1. **Exclude patterns** always win over include patterns
2. **More specific patterns** override general ones
3. **Later patterns** in the same list override earlier ones

```toml
include = [
  "**/*.py",      # Include all Python files
  "!test_*.py",   # But exclude test files (if negation were allowed in include)
]

exclude = [
  "tests/**",     # Exclude tests directory
  # This overrides any include pattern for tests/
]
```

## Best Practices

### 1. Start Broad, Then Narrow

```toml
include = [
  "src/**",           # Include everything in src
]
exclude = [
  "src/**/*.pyc",     # Then exclude compiled files
  "src/**/test_*.py", # And test files
]
```

### 2. Use Anchored Paths for Precision

```toml
include = [
  "/LICENSE",         # Only root LICENSE
  "/README.md",       # Only root README
  "src/**",           # All of src/
]
```

### 3. Group Related Patterns

```toml
# Documentation
include = [
  "*.md",
  "docs/**",
  "examples/**/*.py",
]

# Source code
include = [
  "src/**/*.py",
  "src/**/*.pyi",
]

# Data files
include = [
  "data/**/*.json",
  "data/**/*.csv",
]
```

## Debugging Pattern Matching

### Test Your Patterns

Use `hatch build --target wheel` with verbose output to see which files are included:

```bash
# See what files match your patterns
hatch build -t wheel -v

# Check specific target
hatch build -t sdist -v
```

### Common Issues

1. **Forgetting to anchor**: `LICENSE` matches any LICENSE file, use `/LICENSE` for root only
2. **Missing `**`for recursion**:`src/\*.py` only matches Python files directly in src/
3. **Wrong separator**: Always use `/` even on Windows
4. **Escaping**: Most characters don't need escaping in TOML strings

## Differences from Standard Glob

Hatchling's Git-style patterns differ from standard Unix glob:

| Feature             | Git-style (Hatchling) | Standard Glob |
| ------------------- | --------------------- | ------------- |
| `**` recursive      | Yes                   | Not always    |
| `/` anchoring       | Yes                   | No            |
| `!` negation        | Yes (artifacts only)  | No            |
| `.gitignore` compat | Yes                   | No            |

## See Also

- `include-exclude-patterns.md`
- `pattern-precedence.md`
- `vcs-integration.md`
