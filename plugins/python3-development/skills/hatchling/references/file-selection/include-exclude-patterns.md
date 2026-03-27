---
description: Include and exclude pattern configuration for Hatchling builds. Explains how to use include/exclude options, precedence rules, pattern combination strategies, and target-specific configuration for wheel and sdist builds.
keywords: [include patterns, exclude patterns, hatchling, precedence, file selection, build targets]
---

# Include and Exclude Patterns

Configuration guide for Hatchling's `include` and `exclude` options. Explains how these patterns control file selection, the precedence hierarchy (exclude overrides include), pattern combination strategies, and target-specific configurations for different build outputs.

## Basic Configuration

### Include Patterns

The `include` option specifies which files should be included in the build:

```toml
[tool.hatch.build.targets.wheel]
include = [
  "src/**/*.py",    # All Python files under src/
  "data/*.json",    # JSON files in data/ directory
  "/LICENSE",       # LICENSE file in root
]
```

### Exclude Patterns

The `exclude` option specifies files to exclude, taking precedence over `include`:

```toml
[tool.hatch.build.targets.wheel]
exclude = [
  "**/*.pyc",       # All compiled Python files
  "tests/**",       # Everything in tests directory
  "*.tmp",          # All temporary files
]
```

## Precedence Rules

**Key Rule: `exclude` ALWAYS wins over `include`**

```toml
[tool.hatch.build]
include = ["src/**/*.py"]    # Include all Python files in src/
exclude = ["**/test_*.py"]   # But exclude all test files

# Result: All Python files except test_*.py will be included
```

### Precedence Order (Highest to Lowest)

1. **force-include** - Overrides everything
2. **exclude** - Overrides include and VCS patterns
3. **include** - Overrides VCS patterns
4. **VCS ignore files** - Default behavior

## Pattern Combination Examples

### Example 1: Python Package with Tests

```toml
[tool.hatch.build.targets.wheel]
# Include all Python source files
include = [
  "mypackage/**/*.py",
  "mypackage/**/*.pyi",
]
# But exclude tests and cache
exclude = [
  "**/tests/**",
  "**/__pycache__/**",
  "**/*.pyc",
]
```

### Example 2: Data Science Project

```toml
[tool.hatch.build.targets.sdist]
include = [
  "src/**/*.py",           # Source code
  "notebooks/**/*.ipynb",  # Jupyter notebooks
  "data/raw/*.csv",        # Raw data files
  "configs/*.yaml",        # Configuration files
]
exclude = [
  "data/processed/**",     # Exclude processed data
  "notebooks/.ipynb_checkpoints/**",  # Jupyter checkpoints
  "**/*.log",              # Log files
]
```

### Example 3: Web Application

```toml
[tool.hatch.build.targets.wheel]
include = [
  "app/**/*.py",           # Python backend
  "app/static/**",         # Static assets
  "app/templates/**",      # Template files
]
exclude = [
  "app/static/node_modules/**",  # Node dependencies
  "app/**/*.scss",         # Source SCSS files
  "app/**/*.map",          # Source maps
  "**/*.test.js",          # JavaScript tests
]
```

## Advanced Pattern Techniques

### Whitelisting with Exclude

Sometimes it's easier to exclude everything except specific patterns:

```toml
[tool.hatch.build.targets.wheel]
# Start with minimal include
include = ["mypackage/**"]

# Exclude everything except Python files
exclude = [
  "mypackage/**",           # Exclude everything
  "!mypackage/**/*.py",     # Except Python files (doesn't work in exclude!)
]

# Correct approach:
include = ["mypackage/**/*.py"]  # Only include Python files
```

### Layered Selection

Build different targets with different file sets:

```toml
# Source distribution: include everything
[tool.hatch.build.targets.sdist]
include = [
  "src/**",
  "tests/**",
  "docs/**",
  "*.md",
  "*.toml",
]

# Wheel: only runtime files
[tool.hatch.build.targets.wheel]
include = [
  "src/**/*.py",
]
exclude = [
  "**/tests/**",
  "**/*.pyc",
]

# Documentation build
[tool.hatch.build.targets.docs]
include = [
  "docs/**",
  "examples/**",
  "README.md",
]
```

## Common Patterns

### Development Files to Exclude

```toml
exclude = [
  # Version control
  ".git/**",
  ".gitignore",
  ".gitattributes",

  # CI/CD
  ".github/**",
  ".gitlab-ci.yml",
  ".travis.yml",

  # Development
  ".pre-commit-config.yaml",
  ".flake8",
  ".pylintrc",
  "mypy.ini",

  # IDE
  ".vscode/**",
  ".idea/**",
  "*.swp",
  "*.swo",

  # Testing
  ".pytest_cache/**",
  ".coverage",
  "htmlcov/**",
  ".tox/**",

  # Documentation build
  "docs/_build/**",
  "docs/.doctrees/**",
]
```

### Binary and Compiled Files

```toml
include = [
  "mypackage/**/*.py",
]
# Also include compiled extensions
artifacts = [
  "mypackage/**/*.so",     # Linux/Mac
  "mypackage/**/*.pyd",    # Windows
  "mypackage/**/*.dll",    # Windows
]
exclude = [
  "**/*.pyc",               # Bytecode
  "**/*.pyo",               # Optimized bytecode
  "**/__pycache__/**",      # Cache directories
]
```

## Target-Specific Patterns

Different build targets often need different file sets:

### Source Distribution (sdist)

```toml
[tool.hatch.build.targets.sdist]
# Include source and development files
include = [
  "src/**",
  "tests/**",
  "docs/**",
  "requirements*.txt",
  "*.md",
  "*.rst",
  "LICENSE*",
  "MANIFEST.in",
]
```

### Wheel Distribution

```toml
[tool.hatch.build.targets.wheel]
# Only include runtime necessities
include = [
  "mypackage/**/*.py",
  "mypackage/data/**",
]
exclude = [
  "**/tests/**",
  "**/*.pyc",
]
```

### Custom Target

```toml
[tool.hatch.build.targets.app]
# Application bundle
include = [
  "app/**",
  "configs/production.yaml",
  "scripts/start.sh",
]
exclude = [
  "app/debug/**",
  "**/*.dev.*",
]
```

## Troubleshooting

### Files Not Included

Check precedence:

1. Is it excluded by a pattern?
2. Is it ignored by VCS?
3. Is the include pattern correct?

```bash
# Debug with verbose output
hatch build -t wheel -v
```

### Files Unexpectedly Included

Check for:

1. Too broad include patterns
2. Missing exclude patterns
3. VCS whitelist entries

### Pattern Not Matching

Common issues:

- Missing `**` for recursion: Use `src/**/*.py` not `src/*.py`
- Wrong anchoring: Use `/LICENSE` for root file
- Platform paths: Always use `/` even on Windows

## Best Practices

1. **Start with broad includes, refine with excludes**

   ```toml
   include = ["src/**"]
   exclude = ["src/**/test_*", "src/**/*.pyc"]
   ```

2. **Be explicit about what you ship**

   ```toml
   # Good: Clear what's included
   include = ["mypackage/**/*.py", "mypackage/data/**"]

   # Bad: Too implicit
   include = ["**"]
   exclude = ["everything", "except", "what", "i", "want"]
   ```

3. **Use different patterns for different targets**

   - sdist: Include source, tests, docs
   - wheel: Include only runtime files
   - custom: Target-specific needs

4. **Comment complex patterns**
   ```toml
   exclude = [
     "data/cache/**",  # Temporary processing cache
     "**/*.log",       # All log files anywhere
     "!errors.log",    # Would keep errors.log if negation worked in exclude
   ]
   ```

## See Also

- `pattern-precedence.md`
- `git-style-globs.md`
- `artifacts.md`
