# Plugin test-runner migration

The runners first carried the repository's development dependency superset, which preserved behavior while test ownership moved to the plugin boundary. Each runner now declares only the packages its plugin's code and tests import, plus the pytest plugins its arguments or fixtures need (`pytest-asyncio` for `--asyncio-mode`, `pytest-xdist` where the runner passes `-n`, `pytest-mock` where tests use `mocker`). Add a dependency when the plugin starts importing it, and confirm with the runner's collection and a full run in a standalone copy.

The dependency list in each plugin runner is runtime/test execution metadata, not a plugin-local Python project. Root `pyproject.toml` remains the monorepo lint/type/development-policy authority.

Root pytest `testpaths` kept the plugin entries only while the runners were introduced. Runners are now authoritative: root `testpaths` lists repository-owned tests only, and CI runs each plugin through its `run_pytests.py`.
