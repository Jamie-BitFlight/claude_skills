---
name: project-coverage-sysmon-core
description: pytest coverage runs the sysmon (PEP 669) core — turn it off before enabling branch coverage, coverage plugins, or dynamic contexts on Python < 3.14
metadata:
  type: project
---

Root `pyproject.toml` sets `[tool.coverage.run] core = "sysmon"` (Python 3.13) for a large
CPU/wall-time cut on the suite. It is safe only because nothing gates on the coverage report:
CI's `test-python` job runs plain `uv run -q --locked pytest`, with no `fail_under` and no upload.

Before Python 3.14, sysmon cannot do branch coverage, coverage plugins, or dynamic contexts.
To add any of those, remove `core = "sysmon"` in the same change.

Confirm the active core with `uv run coverage debug config | grep -i core` → `core: sysmon`.
A misspelled key silently falls back to ctrace.
