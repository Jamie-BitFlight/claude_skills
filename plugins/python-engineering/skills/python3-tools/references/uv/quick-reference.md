# uv Command Quick Reference

## Project Commands

```bash
# Initialize
uv init [name]                    # Create new project
uv init --lib                     # Create library (vs application)
uv init --package                 # Create packaged application

# Dependencies
uv add <package>                  # Add dependency
uv add <pkg1> <pkg2>              # Add multiple
uv add '<pkg>>=1.0'               # With version constraint
uv add '<pkg>==1.0.0'             # Exact version
uv add --dev <pkg>                # Dev dependency
uv add --optional <extra> <pkg>   # Optional dependency
uv add --group <name> <pkg>       # Dependency group
uv add -r requirements.txt        # From requirements file
uv add git+https://github.com/org/repo  # Git dependency

uv remove <package>               # Remove dependency

# Sync & Lock
uv sync                           # Sync env with lockfile
uv sync --locked                  # Fail if lockfile outdated
uv sync --frozen                  # Don't update lockfile
uv sync --no-dev                  # Skip dev dependencies
uv sync --all-extras              # Include all optional deps

uv lock                           # Update lockfile
uv lock --upgrade                 # Upgrade all packages
uv lock --upgrade-package <pkg>   # Upgrade specific package

# Run
uv run <script.py>                # Run Python script
uv run <command>                  # Run command in env
uv run --with <pkg> <script>      # Run with extra package
uv run --env-file .env <script>   # Run with env file
uv run --no-sync <command>        # Skip sync step

# Build & Publish
uv build                          # Build distributions
uv build --sdist                  # Source dist only
uv build --wheel                  # Wheel only
uv publish                        # Publish to PyPI
uv publish --token <token>        # With API token
```

## Python Management

```bash
uv python install                 # Install latest
uv python install 3.12            # Install specific
uv python install 3.11 3.12       # Install multiple
uv python install pypy@3.10       # Install PyPy
uv python install --default       # Set as default

uv python list                    # List available
uv python list --only-installed   # Only installed

uv python find 3.12               # Find matching version
uv python pin 3.12                # Pin project version
uv python uninstall 3.11          # Remove version
```

## Tool Management

```bash
uvx <tool>                        # Run tool (alias for uv tool run)
uvx ruff check .                  # Example: run ruff
uvx --python 3.12 <tool>          # With specific Python

uv tool install <tool>            # Install globally
uv tool install '<tool>>=1.0'     # With version
uv tool install --python 3.12 <tool>  # With Python version

uv tool upgrade <tool>            # Upgrade tool
uv tool upgrade --all             # Upgrade all tools

uv tool uninstall <tool>          # Remove tool
uv tool list                      # List installed
uv tool dir                       # Show tool directory
```

## pip Interface

```bash
# Install
uv pip install <pkg>              # Install package
uv pip install '<pkg>>=1.0'       # With constraint
uv pip install -r requirements.txt
uv pip install -e .               # Editable install
uv pip install --upgrade <pkg>    # Upgrade package

# Uninstall
uv pip uninstall <pkg>
uv pip uninstall -r requirements.txt

# List & Show
uv pip list                       # List installed
uv pip show <pkg>                 # Show package info
uv pip freeze                     # Output requirements format
uv pip check                      # Check for conflicts

# Compile
uv pip compile requirements.in    # Generate requirements.txt
uv pip compile -o requirements.txt requirements.in
uv pip compile --upgrade          # Upgrade all
uv pip compile --upgrade-package <pkg>

# Sync
uv pip sync requirements.txt      # Sync to requirements
```

## Virtual Environment

```bash
uv venv                           # Create .venv
uv venv myenv                     # Create named venv
uv venv --python 3.12             # With specific Python
uv venv --seed                    # Include pip/setuptools
uv venv --clear                   # Remove and recreate (required in 0.10.0+)
```

## Cache Management

```bash
uv cache clean                    # Clear all cache
uv cache clean <pkg>              # Clear package cache
uv cache dir                      # Show cache directory
uv cache prune                    # Remove unused entries
uv cache size                     # Show disk usage (0.9.8+)
```

## Self Management

```bash
uv self update                    # Update uv
uv version                        # Show version
```

## Global Options

```bash
--quiet, -q                       # Suppress output
--verbose, -v                     # Increase verbosity
--no-cache                        # Disable cache
--offline                         # No network requests
--python <version>                # Use specific Python
--project <path>                  # Use specific project
```
