# Plugin test-runner migration

This migration intentionally starts from the repository's known-good development dependency superset for newly introduced plugin runners. That preserves behavior while test ownership moves to the plugin boundary. Dependency minimization is a follow-up validation exercise: remove a dependency only after the plugin runner passes in isolation without it.

The dependency list in each plugin runner is runtime/test execution metadata, not a plugin-local Python project. Root `pyproject.toml` remains the monorepo lint/type/development-policy authority.

Root pytest `testpaths` kept the plugin entries only while the runners were introduced. Runners are now authoritative: root `testpaths` lists repository-owned tests only, and CI runs each plugin through its `run_pytests.py`.
