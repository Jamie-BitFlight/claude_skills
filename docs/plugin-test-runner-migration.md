# Plugin test-runner migration

This migration intentionally starts from the repository's known-good development dependency superset for newly introduced plugin runners. That preserves behavior while test ownership moves to the plugin boundary. Dependency minimization is a follow-up validation exercise: remove a dependency only after the plugin runner passes in isolation without it.

The dependency list in each plugin runner is runtime/test execution metadata, not a plugin-local Python project. Root `pyproject.toml` remains the monorepo lint/type/development-policy authority.

During this compatibility stage root pytest `testpaths` remain present so existing CI continues to work. The next stage makes runners authoritative and removes plugin test topology from root discovery.
