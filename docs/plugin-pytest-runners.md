# Pytest runner boundary

Every plugin that owns pytest tests owns one root-level `run_pytests.py`.

The runner is the authoritative declaration of that plugin's test roots and test execution dependencies. It MUST be a PEP 723 script, resolve paths from `__file__`, run from outside the monorepo checkout, and propagate pytest's exit code.

Repository-owned tests use `uv run scripts/run_repo_pytests.py` and intentionally consume the root locked development environment; they are not an extraction boundary. CI chooses which runner to execute; CI must not reconstruct a plugin's internal pytest paths.

The root `pyproject.toml` remains authoritative for monorepo development policy (lint, type checking, shared pytest policy while running in the monorepo). Plugin runners repeat only the minimum execution semantics needed when the plugin is isolated. They do not create plugin-local Python projects.

A runner MAY expose plugin-specific modes such as integration or backend selection when the plugin actually owns those concepts. Do not standardize unused flags.
