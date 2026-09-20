---
name: tests-backlog-not-collected
description: plugins/development-harness/tests_backlog/ is outside pytest testpaths — a bare `uv run pytest` and CI never run it; pass the path explicitly in any validation plan touching backlog_core
metadata:
  type: project
---

`plugins/development-harness/tests_backlog/` is missing from root `pyproject.toml`
`[tool.pytest.ini_options] testpaths`, so `uv run pytest` (and the CI `test-python` job)
never collects it. Tracked as backlog #2930; delete this memory once that closes.

When a change touches `backlog_core/` (file cache, sync, GitHub providers), name the
`tests_backlog/` files in the validation plan and run them by explicit path:

    uv run pytest plugins/development-harness/tests_backlog/<file>.py -q --no-cov
