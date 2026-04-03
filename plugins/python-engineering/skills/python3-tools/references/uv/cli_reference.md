# uv CLI Reference

Complete command-line interface reference for uv (v0.10.2).

## Global Flags

Available across all commands:

```bash
--help, -h              Display help
--verbose, -v           Verbose logging (repeat for more: -vv, -vvv)
--quiet, -q             Suppress output
--color <WHEN>          Color output (auto/always/never)
--no-progress           Hide progress indicators
--cache-dir <DIR>       Cache directory
--no-cache              Disable caching
--offline               Disable network access
--python <VERSION>      Python interpreter/version
--directory <PATH>      Working directory
--config-file <PATH>    Custom config file
--no-config             Ignore config files
--preview               Enable preview features
```

## Project Commands

### uv init

Create new project or script.

```bash
uv init [OPTIONS] [PATH]

--lib, --library        Create library (implies --package)
--app, --application    Create application (default)
--script                Create PEP 723 script
--package               Distributable package with src/
--no-package            Non-package (virtual) project
--bare                  Minimal configuration only
--build-backend <BACKEND>  Build system (hatchling/setuptools/uv_build)
--python <VERSION>      Python version requirement
--vcs <VCS>             Version control (git/none)
--python-pin            Create .python-version
--name <NAME>           Project name (replaces deprecated --project)
```

**Deprecation (0.9.9)**: `--project` flag deprecated. Use positional argument or `--name`.

### uv add

Add dependencies to project.

```bash
uv add [OPTIONS] <PACKAGES>...

--dev                   Add to dev dependencies
--group <GROUP>         Add to dependency group
--optional <EXTRA>      Add to optional dependencies
--editable, -e          Editable/development mode
--frozen                Skip lockfile updates
--locked                Assert lockfile unchanged
--no-sync               Skip environment sync
--bounds <TYPE>         Version constraint (lowest/compatible/exact) [stable 0.10.0]
--branch <BRANCH>       Git branch
--tag <TAG>             Git tag
--rev <REV>             Git revision
--raw-sources           Raw source specifiers
```

### uv remove

Remove dependencies.

```bash
uv remove [OPTIONS] <PACKAGES>...

--dev                   Remove from dev dependencies
--group <GROUP>         Remove from dependency group
--optional <EXTRA>      Remove from optional dependencies
--frozen                Skip lockfile updates
--locked                Assert lockfile unchanged
```

### uv sync

Synchronize project environment with lockfile.

```bash
uv sync [OPTIONS]

--extra <EXTRA>, -E     Include optional dependencies (comma-separated OK since 0.9.30)
--all-extras            Include all optional dependencies
--no-dev                Exclude dev dependencies
--only-dev              Only dev dependencies
--group <GROUP>         Include dependency group
--only-group <GROUP>    Only specified group
--no-install-project    Skip installing project itself
--frozen                Use existing lockfile
--locked                Assert lockfile unchanged
--inexact               Allow non-exact versions
--python <VERSION>      Target Python version
--package <PKG>         Sync specific workspace packages (multiple OK since 0.9.8)
--exclude <PKG>         Exclude packages from resolution (0.9.8+)
```

### uv lock

Update project lockfile.

```bash
uv lock [OPTIONS]

--frozen                Don't update lockfile
--locked                Assert lockfile unchanged
--upgrade, -U           Allow package upgrades
--upgrade-package <PKG>, -P  Upgrade specific packages
--dry-run               Show changes without writing
```

### uv run

Execute commands in project environment.

```bash
uv run [OPTIONS] <COMMAND> [ARGS]...

--python <VERSION>      Python version
--module, -m            Run as module
--script, -s            Treat as PEP 723 script
--with <PKG>, -w        Include temporary packages
--isolated              Fresh isolated environment
--frozen                Skip lockfile updates
--locked                Assert lockfile unchanged
--no-sync               Skip environment sync
--no-project            Don't load project environment
--no-dev                Exclude dev dependencies
--extra <EXTRA>         Include optional dependencies
--all-extras            Include all optional dependencies
--package <PKG>         Run for specific workspace package
--env-file <FILE>       Load environment variables
```

### uv tree

Display dependency tree.

```bash
uv tree [OPTIONS]

--depth <DEPTH>         Maximum display depth
--prune <PKG>           Prune packages from tree
--package <PKG>         Show tree for specific package
--invert                Show reverse dependencies
--no-dedupe             Show all occurrences
```

### uv export

Export dependencies to various formats.

```bash
uv export [OPTIONS]

--format <FORMAT>       Output format (requirements-txt/pylock/cyclonedx-json) [SBOM since 0.9.11]
-o, --output-file <FILE>  Output file path
--extra <EXTRA>         Include optional dependencies
--all-extras            Include all optional dependencies
--no-dev                Exclude dev dependencies
--frozen                Use existing lockfile
--package <PKG>         Export for specific workspace packages (multiple OK since 0.9.8)
--only-emit-workspace   Filter to workspace-only dependencies (0.9.9+)
```

## Tool Management

### uv tool run (alias: uvx)

Execute tool without persistent installation.

```bash
uvx [OPTIONS] <COMMAND> [ARGS]...
uv tool run [OPTIONS] <COMMAND> [ARGS]...

--from <PACKAGE>        Source package
--with <PACKAGE>        Include additional packages
--python <VERSION>      Python version
--isolated              Fresh environment
```

### uv tool install

Install tool persistently.

```bash
uv tool install [OPTIONS] <PACKAGE>

--from <PACKAGE>        Install from specific package
--with <PACKAGE>        Include additional packages
--python <VERSION>      Python version
--force                 Overwrite existing
--editable, -e          Editable mode
```

### uv tool upgrade

Update installed tool.

```bash
uv tool upgrade [OPTIONS] [PACKAGE]

--all                   Upgrade all tools
```

### uv tool list

List installed tools.

```bash
uv tool list [OPTIONS]

--show-paths            Display installation paths
```

### uv tool uninstall

Remove installed tool.

```bash
uv tool uninstall <PACKAGE>
```

## Python Management

### uv python install

Install Python versions.

```bash
uv python install [OPTIONS] <VERSIONS>...

--force                 Reinstall if present
--preview               Allow preview versions
--upgrade               Upgrade to latest patch version [stable 0.10.0]
--compile-bytecode      Compile standard library to bytecode (0.9.25+)
```

### uv python list

List Python versions.

```bash
uv python list [OPTIONS]

--all-versions          Show all available versions
--only-installed        Show only installed versions
```

### uv python pin

Pin Python version for project.

```bash
uv python pin [OPTIONS] <VERSION>

--global                Pin globally for user
--rm                    Remove pin
--python-preference <PREF>  Preference (only-managed/managed/system/only-system)
```

### uv python find

Locate Python interpreter.

```bash
uv python find <VERSION>
```

### uv python upgrade

Update Python installations.

```bash
uv python upgrade [OPTIONS] [VERSION]

--all                   Upgrade all installations
--compile-bytecode      Compile standard library to bytecode (0.9.25+)
```

**Stable in 0.10.0** (was preview).

## pip Interface

### uv pip install

Install packages.

```bash
uv pip install [OPTIONS] <PACKAGES>...

--requirement <FILE>, -r     Install from requirements
--editable <PATH>, -e        Editable mode
--constraint <FILE>, -c      Apply constraints
--override <FILE>            Apply overrides
--extra <EXTRA>              Install optional dependencies
--all-extras                 Install all optional dependencies
--no-deps                    Don't install dependencies
--python <PYTHON>            Target Python environment
--system                     Install into system Python
--break-system-packages      Allow system modifications
--target <DIR>               Install to directory
--upgrade, -U                Upgrade packages
--upgrade-package <PKG>, -P  Upgrade specific packages
--force-reinstall            Reinstall even if satisfied
--no-build                   Don't build from source
--no-binary <PKG>            Don't use wheels
--only-binary <PKG>          Only use wheels
--dry-run                    Show changes without installing
```

### uv pip compile

Generate requirements file.

```bash
uv pip compile [OPTIONS] <INPUT_FILES>...

-o, --output-file <FILE>     Output file
--extra <EXTRA>              Include optional dependencies
--all-extras                 Include all optional dependencies
--constraint <FILE>, -c      Apply constraints
--override <FILE>            Apply overrides
--python <VERSION>           Target Python version
--python-platform <PLATFORM> Target platform
--python-version <VERSION>   Python version constraint
--universal                  Cross-platform requirements
--no-strip-markers           Preserve environment markers
--resolution <STRATEGY>      Resolution strategy (highest/lowest/lowest-direct)
--prerelease <MODE>          Pre-release handling (allow/disallow/if-necessary/if-necessary-or-explicit)
--upgrade, -U                Allow upgrades
--upgrade-package <PKG>, -P  Upgrade specific packages
--generate-hashes            Include package hashes
--annotation-style <STYLE>   Annotation format (line/split)
```

### uv pip sync

Install from requirements file.

```bash
uv pip sync [OPTIONS] <FILE>

--python <PYTHON>            Target Python environment
--system                     Install into system Python
--break-system-packages      Allow system modifications
--target <DIR>               Install to directory
--no-build                   Don't build from source
--dry-run                    Show changes without installing
--reinstall                  Reinstall all packages
--link-mode <MODE>           Installation link mode (clone/copy/hardlink/symlink)
--compile-bytecode           Compile to bytecode
--require-hashes             Require package hashes
```

### uv pip uninstall

Remove packages.

```bash
uv pip uninstall [OPTIONS] <PACKAGES>...

--requirement <FILE>, -r     Uninstall from requirements
--python <PYTHON>            Target Python environment
--system                     Uninstall from system Python
```

### uv pip freeze

List installed packages.

```bash
uv pip freeze [OPTIONS]

--exclude-editable           Exclude editable packages
--exclude <PKG>              Exclude specific packages (0.9.27+)
--strict                     Fail on missing dependencies
--python <PYTHON>            Target Python environment
```

### uv pip list

List installed packages with formatting.

```bash
uv pip list [OPTIONS]

--editable, -e               Show only editable packages
--exclude-editable           Exclude editable packages
--format <FORMAT>            Output format (columns/freeze/json)
--python <PYTHON>            Target Python environment
--system                     Target system Python
```

### uv pip show

Display package information.

```bash
uv pip show <PACKAGE>

--python <PYTHON>            Target Python environment
--system                     Target system Python
```

### uv pip tree

Display dependency tree.

```bash
uv pip tree [OPTIONS]

--depth <DEPTH>              Maximum display depth
--prune <PKG>                Prune packages
--package <PKG>              Show tree for specific package
--invert                     Show reverse dependencies
--python <PYTHON>            Target Python environment
--no-dedupe                  Show all occurrences
```

### uv pip check

Verify dependencies.

```bash
uv pip check [OPTIONS]

--python <PYTHON>            Target Python environment
--system                     Target system Python
```

## Virtual Environments

### uv venv

Create virtual environment.

```bash
uv venv [OPTIONS] [PATH]

--python <VERSION>           Python version
--seed                       Install seed packages (pip, setuptools, wheel)
--prompt <PROMPT>            Custom environment prompt
--system-site-packages       Access to system packages
--relocatable                Relocatable environment
--clear                      Remove existing venv first [required since 0.10.0]
--allow-existing             Allow existing directory
--no-project                 Don't detect project
```

**Breaking (0.10.0)**: `uv venv` no longer auto-removes existing environments. Use `--clear` or `UV_VENV_CLEAR=1`.

## Build and Publish

### uv build

Build Python packages.

```bash
uv build [OPTIONS] [SRC]

--sdist                      Build source distribution only
--wheel                      Build wheel only
--out-dir <DIR>              Output directory (default: dist/)
--package <PACKAGE>          Build specific workspace package
--no-build-isolation         Disable build isolation
--build-constraint <FILE>    Apply build constraints
--config-setting <KEY=VALUE> Pass settings to build backend
--clear                      Remove old build artifacts first (0.9.6+)
--no-create-gitignore        Don't create .gitignore in output dir (0.9.6+)
```

### uv publish

Upload distributions to package indexes.

```bash
uv publish [OPTIONS] [FILES]...

--username <USER>, -u        Registry username
--password <PASS>, -p        Registry password
--token <TOKEN>, -t          Authentication token
--publish-url <URL>          Registry URL (default: PyPI)
--index <NAME>               Named index from config
--keyring-provider <PROVIDER> Keyring authentication
--trusted-publishing <MODE>  OIDC trusted publishing (always/if-available/never)
--check-url <URL>            Verify package existence URL
--build                      Build packages before publishing
--no-build                   Publish existing distributions
```

## Cache Management

### uv cache clean

Clear cache.

```bash
uv cache clean [OPTIONS] [PACKAGE]

--package <PACKAGE>          Clean specific package only
```

### uv cache prune

Remove unreachable entries.

```bash
uv cache prune [OPTIONS]

--ci                         Optimize for CI (keep wheels, remove downloads)
```

### uv cache size (0.9.8+)

Show cache disk usage.

```bash
uv cache size
```

### uv cache dir

Show cache directory path.

```bash
uv cache dir
```

## Workspace Commands (Stable in 0.10.0)

### uv workspace list

List all workspace members.

```bash
uv workspace list [OPTIONS]

--paths                      Show member paths
```

### uv workspace dir

Print workspace root directory.

```bash
uv workspace dir
```

## Self Management

### uv self update

Update uv itself.

```bash
uv self update [OPTIONS]

--version <VERSION>          Update to specific version
```

### uv self version

Show uv version.

```bash
uv self version
uv --version      # Equivalent
uv -V             # Short form
```

## Utility Commands

### uv generate-shell-completion

Generate shell completions.

```bash
uv generate-shell-completion <SHELL>

# Shells: bash, zsh, fish, elvish, powershell
```

## Index and Resolution Flags

Control package index behavior:

```bash
--index <NAME>=<URL>         Named package index
--default-index <URL>        Primary index
--extra-index-url <URL>      Supplementary index
--find-links <PATH_OR_URL>   Find-links location
--no-index                   Ignore all indexes
--index-strategy <STRATEGY>  Resolution strategy (first-index/unsafe-first-match/unsafe-best-match)
--resolution <STRATEGY>      Version selection (highest/lowest/lowest-direct)
--prerelease <MODE>          Pre-release handling
--exclude-newer <TIMESTAMP>  Exclude packages newer than timestamp
--no-sources                 Ignore [tool.uv.sources]
```

## Build Flags

Control build and installation:

```bash
--no-build                   Don't build from source
--no-binary <PKG>            Don't use wheels (use :all: for all)
--only-binary <PKG>          Only use wheels (use :all: for all)
--no-build-isolation         Disable build isolation
--no-build-isolation-package <PKG>  Disable for specific packages
--build-constraint <FILE>    Build dependency constraints
--config-setting <KEY=VALUE> PEP 517 build backend settings
--link-mode <MODE>           Installation method (clone/copy/hardlink/symlink)
--compile-bytecode           Compile to bytecode
--reinstall                  Reinstall all packages
--reinstall-package <PKG>    Reinstall specific packages
--require-hashes             Require package hashes
```

## Examples

**Initialize and manage project:**

```bash
uv init myproject --lib
cd myproject
uv add requests pytest --dev
uv lock
uv sync
uv run pytest
```

**Create and run script:**

```bash
uv init --script analyze.py
uv add --script analyze.py pandas matplotlib
uv run analyze.py
```

**Install and use tools:**

```bash
uvx ruff check
uv tool install black
black myfile.py
```

**Python version management:**

```bash
uv python install 3.12
uv python pin 3.12
uv run --python 3.11 script.py
```

**pip interface:**

```bash
uv pip install flask
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt
```

**Build and publish:**

```bash
uv build
uv publish --token $PYPI_TOKEN
```
