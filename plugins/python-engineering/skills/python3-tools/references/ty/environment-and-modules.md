# Environment and Module Resolution

How ty discovers Python environments, resolves first-party and third-party modules, and what environment variables affect behavior. Load when the user asks about import resolution, unresolved imports, virtual environments, or environment variables.

## Table of Contents

1. [Environment Discovery Flow](#environment-discovery-flow)
2. [First-Party Module Resolution](#first-party-module-resolution)
3. [Third-Party Module Resolution](#third-party-module-resolution)
4. [Environment Variables](#environment-variables)
5. [Python Version Resolution](#python-version-resolution)

---

## Environment Discovery Flow

See `../resources/workflows/environment-discovery.md` for the full decision flowchart.

Summary of precedence:

1. `--python` flag or `environment.python` config (explicit override)
2. `VIRTUAL_ENV` env var (active virtual environment)
3. `CONDA_PREFIX` env var (active Conda environment; `VIRTUAL_ENV` takes precedence if both set)
4. `.venv` directory in project root or working directory
5. `python3` or `python` binary in `PATH`

When using uv, Poetry, or other project management tools with a `run` subcommand, the virtual environment is typically activated automatically and detected via `VIRTUAL_ENV`.

---

## First-Party Module Resolution

First-party modules are Python files that are part of your project source code.

Default search locations (checked in order, all included if they exist and are not packages):

- Project root (`.`)
- `./src` — if it exists and contains no `__init__.py` or `__init__.pyi`
- `./<project-name>` — if a `./<project-name>/<project-name>` directory exists
- `./python` — if it exists and is not a package

Override with `environment.root`:

```toml
[tool.ty.environment]
root = ["./app"]
```

`environment.root` accepts a list; paths are searched in priority order (first = highest priority).

Additional search paths that do not fit normal project layout:

```toml
[tool.ty.environment]
extra-paths = ["./shared/my-search-path"]
```

---

## Third-Party Module Resolution

Third-party modules are resolved from the configured Python environment's `site-packages` directory.

ty requires a Python environment to resolve third-party imports. Without one, all third-party imports are unresolved.

Suppress specific unresolved import errors without fixing the environment:

```toml
[tool.ty.analysis]
# Suppress unresolved-import for all stubs packages
allowed-unresolved-imports = ["pandas-stubs.**"]
```

Replace an entire module's types with `typing.Any`:

```toml
[tool.ty.analysis]
# Treat pandas imports as Any (useful for partial stubs)
replace-imports-with-any = ["pandas.**", "numpy.**"]
```

`PYTHONPATH` env var adds directories to ty's search paths (same format as shell PATH).

---

## Environment Variables

### ty-defined variables

| Variable | Description |
|----------|-------------|
| `TY_CONFIG_FILE` | Path to a `ty.toml` config file. Equivalent to `--config-file` |
| `TY_LOG` | Log level filter for `--verbose` output. Example: `ty=debug` for `-vv` equivalent |
| `TY_LOG_PROFILE` | Set to `"1"` or `"true"` to enable flamegraph profiling (creates `tracing.folded`) |
| `TY_MAX_PARALLELISM` | Upper limit for parallel tasks (e.g., parallel file checks) |
| `TY_OUTPUT_FORMAT` | Output format. Same values as `--output-format` flag |

### External variables read by ty

| Variable | Description |
|----------|-------------|
| `VIRTUAL_ENV` | Path to active virtual environment |
| `CONDA_PREFIX` | Path to active Conda environment (`VIRTUAL_ENV` takes precedence if both set) |
| `CONDA_DEFAULT_ENV` | Name of active Conda environment |
| `_CONDA_ROOT` | Root install path of Conda |
| `PYTHONPATH` | Additional directories added to module search paths |
| `RAYON_NUM_THREADS` | Upper limit for parallel threads. Equivalent to `TY_MAX_PARALLELISM` |
| `XDG_CONFIG_HOME` | User-level config directory on Unix (default: `~/.config`) |

---

## Python Version Resolution

See `../resources/workflows/python-version-resolution.md` for the full decision flowchart.

The target Python version affects:
- Allowed syntax (e.g., `match` statements require Python 3.10+)
- Standard library type definitions
- `sys.version_info` conditional branch evaluation
- Availability of symbols conditional on Python version

Version is resolved in this order when not explicitly set:

1. `--python-version` flag or `environment.python-version` config
2. Minimum version from `project.requires-python` in `pyproject.toml`
3. Inferred from activated or configured Python environment
4. Falls back to `"3.14"` (latest stable supported by ty)
