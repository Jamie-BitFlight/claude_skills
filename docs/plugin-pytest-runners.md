# Pytest runner boundary

Every plugin that owns pytest tests owns one root-level `run_pytests.py`.

The runner is the authoritative declaration of that plugin's test roots and test execution dependencies. It declares its test roots as a module-level `TEST_PATHS` constant holding a literal tuple or list of plugin-relative paths (a type annotation is allowed). Repository tooling reads that literal without importing the runner, so it must not be computed. It MUST be a PEP 723 script, resolve paths from `__file__`, run from outside the monorepo checkout, and propagate pytest's exit code. It passes its test roots to pytest as `testpaths` rather than as arguments, so an option-only invocation such as `-m <expr>` or `--collect-only` still collects only the declared roots, and explicit path arguments still override them.

A runner reads no parent configuration: it passes `-c os.devnull` and `--confcutdir` set to the plugin root, so neither a parent `pyproject.toml` nor a parent `conftest.py` reaches the run. Its `--rootdir` is the plugin root or a collection root below it that contains every declared test path. It therefore sets the pytest policy that root configuration would otherwise supply: `--strict-config`, `--strict-markers`, `--import-mode=importlib`, `--asyncio-mode=auto`, the plugin's own import roots as `pythonpath` (`IMPORT_PATHS`), and the root's default `-m` expression as its leading `-m` (`FAST_MARKER`), so a bare run selects the fast lane. A caller's `-m` replaces that default; `-m ""` selects every marker. Markers the plugin's tests use are registered by the plugin's own `conftest.py`, since `--strict-markers` rejects any other.

The runner's resolved dependencies are pinned in a committed `run_pytests.py.lock` beside it. After changing the PEP 723 block, run `uv lock --script plugins/<name>/run_pytests.py` and commit the lock. CI runs each runner with `uv run --locked --script`, which fails instead of resolving afresh when the lock is missing or stale, and `tests/test_plugin_pytest_runner_contract.py` runs `uv lock --script <runner> --check` for every runner so a stale lock fails the global shard on any change.

Repository-owned tests run with `uv run pytest` under the root `pyproject.toml` (its `testpaths` lists them), the same command CI's global shard runs as `uv run --locked pytest`. They consume the root locked development environment and are not an extraction boundary. CI chooses which runner to execute; CI must not reconstruct a plugin's internal pytest paths.

The root `pyproject.toml` remains authoritative for monorepo development policy (lint, type checking, shared pytest policy while running in the monorepo). Plugin runners repeat only the minimum execution semantics needed when the plugin is isolated. They do not create plugin-local Python projects.

A runner MAY expose plugin-specific modes such as integration or backend selection when the plugin actually owns those concepts. Do not standardize unused flags.
