# uv Troubleshooting Guide

Common issues and solutions for uv (v0.10.2).

## Installation and Setup Issues

### uv Command Not Found

**Problem**: `uv: command not found` after installation

**Solutions**:

```bash
# Check if uv is installed
which uv

# Check PATH
echo $PATH

# Add to PATH (Unix)
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Windows: Add to PATH
# %USERPROFILE%\.local\bin

# Verify installation
uv --version

# Reinstall if necessary
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Permission Denied

**Problem**: Permission errors during installation or execution

**Solutions**:

```bash
# Unix: Fix permissions
chmod +x ~/.local/bin/uv

# Don't use sudo with uv (creates permission issues)
# Instead use virtual environments

# If accidentally used sudo
sudo chown -R $USER:$USER ~/.local/share/uv
sudo chown -R $USER:$USER ~/.cache/uv
```

## Environment Management Issues

### "Externally Managed" Error

**Problem**: `error: The Python interpreter at ... is externally managed`

**Cause**: Trying to install to uv-managed or system Python with `--system` flag

**Solutions**:

```bash
# Solution 1: Use virtual environment (recommended)
uv venv
source .venv/bin/activate
uv pip install package

# Solution 2: Use project context
uv add package  # For projects
uv run python script.py  # Automatically manages environment

# Solution 3: For scripts with PEP 723 metadata
uv run --script script.py  # Creates isolated environment

# Don't use --system with uv-managed Python
```

### Virtual Environment Won't Recreate (0.10.0+)

**Problem**: `uv venv` errors when `.venv` already exists

**Cause**: Since 0.10.0, `uv venv` no longer auto-removes existing environments

**Solutions**:

```bash
# Pass --clear to explicitly remove and recreate
uv venv --clear

# Or set environment variable globally
export UV_VENV_CLEAR=1

# Or use a different path
uv venv myenv
```

**Recovery after accidental venv loss**:

```bash
# Recreate and reinstall
uv venv
uv sync  # If using project with lockfile
# or
uv pip install -r requirements.txt
```

### Can't Activate Virtual Environment

**Problem**: Virtual environment activation fails

**Solutions**:

```bash
# Unix/macOS - bash/zsh
source .venv/bin/activate

# Unix/macOS - fish
source .venv/bin/activate.fish

# Windows - cmd
.venv\Scripts\activate.bat

# Windows - PowerShell
.venv\Scripts\Activate.ps1

# If PowerShell execution policy blocks
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Alternative: Use uv run (no activation needed)
uv run python script.py
```

## Dependency Resolution Issues

### Conflicting Dependencies

**Problem**: `error: No solution found when resolving dependencies`

**Diagnosis**:

```bash
# See detailed resolution output
uv add package -vvv

# Check dependency tree for conflicts
uv tree

# Check specific package requirements
uv pip show package
```

**Solutions**:

```bash
# 1. Update packages to resolve conflict
uv lock --upgrade
uv sync

# 2. Upgrade specific conflicting package
uv lock --upgrade-package problematic-package

# 3. Use constraint to force specific version
# In pyproject.toml:
[tool.uv]
constraint-dependencies = ["conflicting-package<2.0"]

# 4. Try different resolution strategy
[tool.uv]
resolution = "lowest-direct"  # Instead of "highest"

# 5. Use override for absolute control
[tool.uv]
override-dependencies = ["problematic-package==1.5.0"]
```

### Lockfile Out of Sync

**Problem**: `error: The lockfile is out of sync with the project dependencies`

**Solutions**:

```bash
# Regenerate lockfile
uv lock

# If intentional (CI), use --frozen
uv sync --frozen

# If must match exactly (strict CI), use --locked
uv sync --locked  # Fails if out of sync

# Update dependencies and lockfile
uv lock --upgrade
```

### Pre-release Dependencies

**Problem**: uv won't install pre-release version you need

**Solutions**:

```bash
# Allow pre-releases in pyproject.toml
[tool.uv]
prerelease = "allow"  # or "if-necessary" or "if-necessary-or-explicit"

# Or specify explicitly in dependencies
dependencies = ["package>=1.0.0a1"]  # Explicit pre-release version

# Command-line override
uv add --prerelease allow package
```

## Build Failures

### Build Dependencies Missing

**Problem**: `error: Failed to build` with missing module errors

**Common Errors**:

<eg>
ModuleNotFoundError: No module named 'setuptools'
ModuleNotFoundError: No module named 'distutils'
ModuleNotFoundError: No module named 'Cython'
</eg>

**Solutions**:

```bash
# 1. For modern packages, uv should handle this
# Check if package is compatible with your Python version

# 2. Install build dependencies manually (rarely needed)
uv pip install setuptools wheel

# 3. For packages requiring Cython
[tool.uv.extra-build-dependencies]
problematic-package = ["Cython"]

# 4. Python 3.12+ removed distutils
# Update to newer package version
uv add "package>=newer-version"

# 5. Use pre-built wheels instead
uv add package --only-binary package
```

### System Dependencies Missing

**Problem**: Build fails with C compiler or library errors

**Common Errors**:

<eg>
error: command 'gcc' failed
fatal error: Python.h: No such file or directory
error: openssl/ssl.h: No such file or directory
</eg>

**Solutions**:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev

# macOS
xcode-select --install
brew install openssl postgresql

# RHEL/CentOS/Fedora
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel openssl-devel

# Arch Linux
sudo pacman -S base-devel python

# Verify compiler
gcc --version
python3-config --includes
```

### Build Isolation Issues

**Problem**: Package build fails due to missing dependencies in isolated environment

**Solutions**:

```bash
# Disable isolation for specific package
[tool.uv]
no-build-isolation-package = ["flash-attn", "deepspeed"]

# Provide extra build dependencies
[tool.uv.extra-build-dependencies]
flash-attn = ["torch", "setuptools", "ninja"]

# Match runtime version
[tool.uv.extra-build-dependencies]
deepspeed = [{ requirement = "torch", match-runtime = true }]

# Set build environment variables
[tool.uv.extra-build-variables]
flash-attn = { FLASH_ATTENTION_SKIP_CUDA_BUILD = "TRUE" }
```

## Package Index Issues

### Authentication Failures

**Problem**: `error: Failed to download` from private registry

**Solutions**:

```bash
# Set credentials via environment variables
export UV_INDEX_PRIVATE_USERNAME="user"
export UV_INDEX_PRIVATE_PASSWORD="password"

# Or use keyring
export UV_KEYRING_PROVIDER=subprocess

# For PyPI token
export UV_PUBLISH_TOKEN="pypi-..."

# In pyproject.toml for named index
[[tool.uv.index]]
name = "private"
url = "https://packages.example.com/simple"
authenticate = "always"

# URL-embedded credentials (less secure)
[[tool.uv.index]]
url = "https://user:pass@packages.example.com/simple"
```

### SSL Certificate Errors

**Problem**: SSL verification fails

**Solutions**:

```bash
# Use system certificates (recommended)
export UV_NATIVE_TLS=1
[tool.uv]
native-tls = true

# Allow specific insecure host (not recommended)
export UV_INSECURE_HOST="packages.example.com"
[tool.uv]
allow-insecure-host = ["packages.example.com"]

# Update certificates
# Ubuntu/Debian
sudo apt-get install ca-certificates
sudo update-ca-certificates

# macOS
# Certificates usually managed by system
```

### Package Not Found

**Problem**: `error: Package 'X' not found`

**Diagnosis**:

```bash
# Check index configuration
uv pip install package -vvv

# Verify index URL
curl https://pypi.org/simple/package-name/

# Check index strategy
[tool.uv]
index-strategy = "first-index"  # Try "unsafe-best-match" if needed
```

**Solutions**:

```bash
# 1. Check package name spelling
uv add correct-package-name

# 2. Add appropriate index
[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cu121"

[tool.uv.sources]
torch = { index = "pytorch" }

# 3. Install from URL directly
uv add https://files.pythonhosted.org/.../package.whl

# 4. Check Python version compatibility
requires-python = ">=3.11"  # Package may require newer Python
```

## Performance Issues

### Slow Downloads

**Problem**: Package downloads are slow

**Solutions**:

```bash
# Increase concurrent downloads
export UV_CONCURRENT_DOWNLOADS=50
[tool.uv]
concurrent-downloads = 50

# Use mirror
export UV_PYTHON_INSTALL_MIRROR="https://mirror.example.com"

# Check network
curl -o /dev/null https://pypi.org/simple/

# Disable progress bars (slight speedup)
export UV_NO_PROGRESS=1
```

### Cache Issues

**Problem**: Cache grows too large or contains stale data

**Solutions**:

```bash
# Check cache size (0.9.8+)
uv cache size

# Clean entire cache
uv cache clean

# Prune unreachable entries
uv cache prune

# CI optimization (keep wheels, remove downloads)
uv cache prune --ci

# Bypass cache temporarily
uv sync --no-cache

# Custom cache location
export UV_CACHE_DIR=/path/to/cache
[tool.uv]
cache-dir = "/path/to/cache"
```

## Script and Tool Issues

### PEP 723 Script Errors

**Problem**: Script with inline metadata won't run

**Solutions**:

```bash
# Verify metadata block format
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///

# Must use exact format (no spaces before ///)
# Block must be at top of file (after shebang)

# Run with explicit --script flag
uv run --script script.py

# Check for syntax errors
python3 -m py_compile script.py

# Lock script dependencies
uv lock --script script.py

# Verify with verbose output
uv run --script script.py -v
```

### Tool Installation Fails

**Problem**: `uv tool install` fails or tool not in PATH

**Solutions**:

```bash
# Verify installation
uv tool list
uv tool dir

# Check PATH
echo $PATH | grep -o '\.local/bin'

# Add tools to PATH
export PATH="$(uv tool dir)/bin:$PATH"
echo 'export PATH="$(uv tool dir)/bin:$PATH"' >> ~/.bashrc

# Update shell integration
uv tool update-shell

# Reinstall tool
uv tool install --force package

# Try with specific Python
uv tool install --python 3.11 package
```

## Python Version Issues

### Wrong Python Version Used

**Problem**: uv uses unexpected Python version

**Diagnosis**:

```bash
# Check detected Python
uv python find

# Check project pin
cat .python-version

# Check preference
echo $UV_PYTHON_PREFERENCE
```

**Solutions**:

```bash
# Pin project Python version
uv python pin 3.11

# Set preference
export UV_PYTHON_PREFERENCE=managed
[tool.uv]
python-preference = "managed"

# Install required Python
uv python install 3.11

# Specify explicitly
uv run --python 3.11 script.py
uv venv --python 3.12
```

### Python Download Fails

**Problem**: `error: Failed to download Python`

**Solutions**:

```bash
# Check network connectivity
curl -I https://github.com/indygreg/python-build-standalone/releases

# Use manual download
export UV_PYTHON_DOWNLOADS=manual

# Use mirror
export UV_PYTHON_INSTALL_MIRROR="https://mirror.example.com"

# Disable downloads, use system Python
export UV_PYTHON_PREFERENCE=system
```

## Workspace Issues

### Workspace Member Not Found

**Problem**: Workspace member not detected

**Solutions**:

```bash
# Verify workspace configuration
[tool.uv.workspace]
members = ["packages/*"]  # Check glob pattern

# Verify member has pyproject.toml
ls packages/*/pyproject.toml

# Check exclusions
[tool.uv.workspace]
exclude = ["packages/deprecated"]

# Run from workspace root
cd workspace-root
uv sync

# Build specific member
uv build --package member-name
```

## CI/CD Issues

### CI Cache Not Working

**Problem**: CI doesn't use cache effectively

**Solutions**:

```yaml
# GitHub Actions
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: |
      uv-${{ runner.os }}-

# Use frozen mode in CI
- run: uv sync --frozen

# Prune cache for CI efficiency
- run: uv cache prune --ci
```

### Different Results Locally vs CI

**Problem**: CI builds differently than local

**Solutions**:

```bash
# Use same Python version
uv python install $(cat .python-version)

# Use frozen lockfile
uv sync --frozen

# Use locked for strict matching
uv sync --locked

# Match Python preference
export UV_PYTHON_PREFERENCE=managed

# Check environment differences
uv run python -c "import sys; print(sys.version)"
uv pip list
```

## Debugging

### Enable Verbose Logging

```bash
# Increasing verbosity
uv sync -v        # Basic verbose
uv sync -vv       # More verbose
uv sync -vvv      # Maximum verbosity

# Rust-level debugging
export RUST_LOG=uv=debug
export RUST_BACKTRACE=1
uv sync

# Log to file
uv sync -vvv 2>&1 | tee uv-debug.log
```

### Check System Information

```bash
# uv version and build info
uv self version
uv --version

# Python information
uv python list
uv python find

# Cache information
uv cache dir
uv cache size

# Tool information
uv tool dir
uv tool list --show-paths

# Project information
cat pyproject.toml
cat uv.lock | head -20

# System information
python3 --version
which python3
echo $PATH
env | grep UV_
```

## Getting Help

### Report Issues

```bash
# Gather diagnostic information
uv --version
python3 --version
uname -a  # or systeminfo on Windows
uv sync -vvv 2>&1 | tee debug.log

# Check existing issues
# https://github.com/astral-sh/uv/issues

# Create minimal reproduction
# Include pyproject.toml, uv.lock, commands run, full error output
```

### Resources

- Documentation: <https://docs.astral.sh/uv/>
- GitHub Issues: <https://github.com/astral-sh/uv/issues>
- Discussions: <https://github.com/astral-sh/uv/discussions>
- Discord: Astral community server
