---
name: project-coverage-sysmon-core
description: pytest coverage runs the sysmon (PEP 669) core — turn it off before enabling a plugin file tracer; on Python 3.13, branch coverage or dynamic contexts fall back to ctrace with a `no-sysmon` warning
metadata:
  type: project
---

Root `pyproject.toml` sets `[tool.coverage.run] core = "sysmon"` (Python 3.13). CI's `test-python` job runs plain `uv run -q --locked pytest`, with no `fail_under` and no upload.

On Python 3.13 with coverage 7.15.2, sysmon cannot do branch coverage, plugin file tracers, or dynamic contexts. Branch coverage or dynamic contexts make coverage warn `no-sysmon` and fall back to ctrace; a plugin file tracer only gets a warning that sysmon does not support it.
To add a plugin file tracer, remove `core = "sysmon"` in the same change.

Confirm the active core with `uv run coverage debug config | grep -i core` → `core: sysmon`.
A misspelled key prints `CoverageWarning: Unrecognized option` and leaves `core` unset, so coverage uses ctrace.
