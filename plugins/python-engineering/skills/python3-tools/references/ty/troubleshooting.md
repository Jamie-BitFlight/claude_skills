# ty Troubleshooting Guide

Common issues and solutions for ty.

SOURCE: [ty documentation](https://docs.astral.sh/ty/) (accessed 2026-02-28)

## Installation and Setup Issues

### ty Command Not Found

**Problem**: `ty: command not found` after installation

**Solutions**:

```bash
# Run without installing (recommended)
uvx ty check

# Or install as project dev dependency
uv add --dev ty
uv run ty check

# Install as global tool
uv tool install ty

# Verify installation
ty --version

# Check PATH includes tool directory
echo $PATH | tr ':' '\n' | grep -E '\.local/bin|\.cargo/bin'

# Add uv tools to PATH if missing
export PATH="$(uv tool dir)/bin:$PATH"
```

### Configuration File Not Detected

**Problem**: ty ignores your configuration settings

**Diagnosis**:

```bash
# Check which config file ty finds (verbose output)
ty check -vv 2>&1 | head -20

# Verify config file exists and is valid TOML
cat ty.toml
# or
cat pyproject.toml | grep -A 20 '\[tool\.ty'
```

**Solutions**:

```bash
# Explicitly specify config file
ty check --config-file ./ty.toml

# Or set via environment variable
export TY_CONFIG_FILE=./ty.toml

# Common mistake: ty.toml uses bare keys, pyproject.toml uses [tool.ty] prefix
```

```toml
# WRONG in ty.toml — do not use [tool.ty] prefix
[tool.ty.rules]
all = "error"

# CORRECT in ty.toml — bare keys
[rules]
all = "error"

# CORRECT in pyproject.toml — with [tool.ty] prefix
[tool.ty.rules]
all = "error"
```

Note: If both `ty.toml` and `pyproject.toml` exist in the same directory, `ty.toml` takes precedence and the `[tool.ty]` section in `pyproject.toml` is ignored.

---

## Import Resolution Issues

### Unresolved Imports

**Problem**: `unresolved-import` errors for installed packages

**Diagnosis**:

```bash
# Check which Python environment ty is using
ty check -vv 2>&1 | grep -i "python\|venv\|environment"

# Verify package is installed in the environment
uv run python -c "import package_name"
```

**Solutions**:

```bash
# Point ty to your virtual environment explicitly
ty check --python .venv

# Or in configuration
```

```toml
[tool.ty.environment]
python = ".venv"
```

```bash
# For packages without type stubs, suppress the import
```

```toml
[tool.ty.analysis]
allowed-unresolved-imports = ["untyped_package.**"]

# Or replace with Any (suppresses all downstream errors too)
[tool.ty.analysis]
replace-imports-with-any = ["untyped_package.**"]
```

### First-Party Module Not Found

**Problem**: ty cannot find your own project modules

**Diagnosis**:

```bash
# Check project structure — ty auto-detects src/ layouts
ls -la src/ 2>/dev/null
ls -la */  # Check for package directories
```

**Solutions**:

```toml
# Explicit source roots
[tool.ty.environment]
root = ["./src", "./lib"]

# Additional search paths for non-standard layouts
[tool.ty.environment]
extra-paths = ["./shared/modules"]
```

### Third-Party Stubs Missing

**Problem**: Warnings about missing type stubs for third-party libraries

**Solutions**:

```bash
# Install type stubs if available
uv add --dev types-requests types-PyYAML

# Or suppress for specific libraries
```

```toml
[tool.ty.analysis]
allowed-unresolved-imports = ["library_without_stubs.**"]
```

---

## Python Version Issues

### Wrong Python Version Assumed

**Problem**: ty reports errors about features not available in your Python version, or uses a different version than expected

**Diagnosis**:

```bash
# Check what version ty detects
ty check -vv 2>&1 | grep -i "python.*version"

# Check .python-version file
cat .python-version 2>/dev/null

# Check pyproject.toml requires-python
grep requires-python pyproject.toml
```

**Solutions**:

```bash
# Override on command line
ty check --python-version 3.12

# Or in configuration
```

```toml
[tool.ty.environment]
python-version = "3.12"
```

ty resolves the target Python version in this order:
1. `--python-version` CLI flag
2. `environment.python-version` in config
3. Version from the resolved Python environment
4. `requires-python` from `pyproject.toml` (upper bound)
5. Fallback: `3.14`

### Platform-Specific Type Errors

**Problem**: Errors related to platform-specific APIs (e.g., `sys.platform` branches)

**Solutions**:

```bash
# Target a specific platform
ty check --python-platform linux

# Or make no platform assumptions
ty check --python-platform all
```

```toml
[tool.ty.environment]
python-platform = "linux"
```

---

## Rule and Diagnostic Issues

### Suppression Comment Not Working

**Problem**: `ty: ignore` comment does not suppress the diagnostic

**Common causes**:

1. **Wrong rule name** — check the exact rule name ty reports:

    ```text
    error[invalid-assignment]: ...
    ```

    Use exactly `invalid-assignment` in the suppression:

    ```python
    x = foo()  # ty: ignore[invalid-assignment]
    ```

2. **Comment on wrong line** — for multi-line violations, place the comment on the first or last line:

    ```python
    result = function_call(  # ty: ignore[missing-argument]
        arg1,
        arg2
    )
    # OR
    result = function_call(
        arg1,
        arg2
    )  # ty: ignore[missing-argument]
    ```

3. **Using `type: ignore[code]` expecting per-rule suppression** — `type: ignore[code]` suppresses ALL violations on the line in ty, not just the named code. Use `ty: ignore[rule]` for targeted suppression.

### Unused Suppression Comment Warnings

**Problem**: `unused-ignore-comment` diagnostics after fixing code

**Solutions**:

```bash
# Auto-add missing suppression comments
ty check --add-ignore

# Disable the rule if too noisy during migration
ty check --ignore unused-ignore-comment
```

```toml
[tool.ty.rules]
unused-ignore-comment = "ignore"
```

Note: `unused-ignore-comment` can only be suppressed with `# ty: ignore[unused-ignore-comment]` — bare `# ty: ignore` and `# type: ignore` do not work for this specific rule.

### Too Many Diagnostics

**Problem**: Overwhelming number of errors on first run

**Solutions**:

```bash
# Start with warnings only (no error exit code)
ty check --exit-zero

# Focus on one rule at a time
ty check --ignore all --error possibly-unresolved-reference

# Relax rules in test files
```

```toml
[[tool.ty.overrides]]
include = ["tests/**"]

[tool.ty.overrides.rules]
all = "warn"
```

---

## CI Integration Issues

### GitHub Actions Annotations Not Showing

**Problem**: ty output does not create GitHub Actions annotations

**Solution**: Use the `github` output format:

```yaml
- name: Type check
  run: uvx ty check --output-format github
```

### CI Exit Code Issues

**Problem**: CI fails on warnings when only errors should fail

**Solution**: Warnings produce exit code 0 by default. If CI still fails, check:

```bash
# Ensure --error-on-warning is NOT set unless intended
ty check  # exits 0 for warnings, 1 for errors

# If you want strict CI (fail on warnings too):
ty check --error-on-warning
```

### CI Cache

ty does not use a persistent cache directory. No cache configuration is needed for CI.

---

## Editor Integration Issues

### VS Code — Language Server Not Starting

**Problem**: ty language server does not start in VS Code

**Solutions**:

1. Install the ty VS Code extension (if available) or configure a generic LSP client
2. Verify ty is accessible:

    ```bash
    which ty
    ty server  # Should start without errors — Ctrl+C to stop
    ```

3. Check VS Code output panel for error messages

### Neovim — LSP Configuration

**Problem**: ty LSP not connecting in Neovim

**Solution**: Configure via `nvim-lspconfig` or manual LSP setup:

```lua
-- nvim-lspconfig
require('lspconfig').ty.setup{}

-- Or manual setup if ty is not in lspconfig yet
vim.lsp.start({
    name = 'ty',
    cmd = {'ty', 'server'},
    root_dir = vim.fs.dirname(vim.fs.find({'ty.toml', 'pyproject.toml'}, { upward = true })[1]),
})
```

---

## Performance Issues

### Slow on Large Projects

**Problem**: ty takes too long on a large codebase

**Solutions**:

```bash
# Exclude non-essential directories
ty check --exclude 'vendor/**' --exclude 'generated/**'

# Check specific directories only
ty check src/

# Use watch mode for incremental rechecks during development
ty check --watch
```

```toml
[tool.ty.src]
exclude = [
    "vendor/**",
    "generated/**",
    "docs/**",
    "**/migrations/**",
]
```

---

## Debugging

### Enable Verbose Output

```bash
# Basic verbose
ty check -v

# More verbose
ty check -vv

# Maximum verbosity
ty check -vvv

# Capture to file for reporting
ty check -vvv 2>&1 | tee ty-debug.log
```

### Check System Information

```bash
# ty version
ty version
ty version --output-format json

# Python environment
uv run python --version
uv run python -c "import sys; print(sys.prefix)"

# Config file in use
ty check -vv 2>&1 | head -5
```

### Report Issues

When reporting issues to the ty project:

```bash
# Gather diagnostic information
ty version --output-format json
uv run python --version
uname -a
ty check -vvv 2>&1 | tee debug.log

# Include: ty version, Python version, OS, config file, and full verbose output
# GitHub Issues: https://github.com/astral-sh/ty/issues
```
