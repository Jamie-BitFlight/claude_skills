# ty Command Quick Reference

## Type Checking

```bash
# Run without installation (latest version)
uvx ty check

# Check project (in uv project)
uv run ty check

# Check specific file
ty check example.py

# Check specific directories
ty check src scripts/benchmark.py

# Watch mode (recheck on file changes)
ty check --watch

# Treat all warnings as errors
ty check --error all

# Treat specific rule as error
ty check --error possibly-unresolved-reference

# Ignore a specific rule
ty check --ignore unused-ignore-comment

# Target Python 3.11
ty check --python-version 3.11

# Target specific platform
ty check --python-platform linux

# Explicit venv path
ty check --python .venv

# Override config option inline
ty check --config "terminal.output-format='concise'"
```

## Output Formats

```bash
# Full output (default — source context, annotations, hints)
ty check --output-format full

# Concise (one line per diagnostic)
ty check --output-format concise

# GitHub Actions annotations
ty check --output-format github

# GitLab Code Quality JSON
ty check --output-format gitlab

# JUnit XML report
ty check --output-format junit
```

## Exit Code Control

```bash
# Always exit 0 (useful for advisory checks)
ty check --exit-zero

# Exit 1 on warnings too (strict CI)
ty check --error-on-warning

# Combine: strict mode + GitHub output
ty check --error all --error-on-warning --output-format github
```

## File Exclusion

```bash
# Exclude pattern
ty check --exclude 'tests/fixtures/**'

# Multiple exclusions
ty check --exclude 'generated/' --exclude '*.proto'

# Force exclusions on explicit paths too
ty check --force-exclude --exclude 'legacy/' legacy/check_this.py

# Ignore .gitignore patterns
ty check --no-respect-ignore-files
```

## Language Server

```bash
# Start LSP server (connect from any editor)
ty server
```

## Version and Completion

```bash
# Show version
ty version

# Show version as JSON
ty version --output-format json

# Generate shell completions
ty generate-shell-completion bash
ty generate-shell-completion zsh
ty generate-shell-completion fish
```

## Configuration Quick Setup

```toml
# ty.toml — minimal project config
[environment]
python-version = "3.12"

[rules]
all = "error"

[src]
exclude = ["tests/fixtures/**"]
```

```toml
# pyproject.toml — same settings
[tool.ty.environment]
python-version = "3.12"

[tool.ty.rules]
all = "error"

[tool.ty.src]
exclude = ["tests/fixtures/**"]
```

## Suppression Comments

```python
# Suppress specific rule on one line
x = foo()  # ty: ignore[unsupported-operator]

# Suppress multiple rules
x = foo()  # ty: ignore[missing-argument, invalid-argument-type]

# Suppress all rules on line (discouraged)
x = foo()  # ty: ignore

# PEP 484 compatible (suppresses all violations on line)
x = foo()  # type: ignore

# Coexist with formatter
x = foo()  # ty: ignore[invalid-argument-type]  # fmt: skip

# Suppress inside decorated function (all violations)
from typing import no_type_check

@no_type_check
def legacy_function():
    ...
```

## Common Configuration Patterns

```toml
# Strict CI mode
[rules]
all = "error"

[terminal]
error-on-warning = true
output-format = "github"

# Relaxed rules for tests
[[overrides]]
include = ["tests/**", "**/test_*.py"]

[overrides.rules]
possibly-unresolved-reference = "warn"

# Suppress unresolved imports for untyped libraries
[analysis]
allowed-unresolved-imports = ["pandas.**", "numpy.**"]

# Replace imports with Any (stronger than allowed-unresolved)
[analysis]
replace-imports-with-any = ["legacy_lib.**"]

# Custom source roots
[environment]
root = ["./src", "./lib"]
extra-paths = ["./shared/stubs"]
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TY_CONFIG_FILE` | Path to ty.toml config file |
| `TY_OUTPUT_FORMAT` | Default output format |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No error-level violations found |
| `1` | Error-level violations found |
| `2` | Invalid CLI options, configuration, or IO error |
| `101` | Internal error |
