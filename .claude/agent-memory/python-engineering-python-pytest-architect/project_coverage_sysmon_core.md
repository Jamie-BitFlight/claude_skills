---
name: project-coverage-sysmon-core
description: Before enabling a plugin file tracer, turn off sysmon — coverage otherwise asks for the sysmon (PEP 669) core, which only a local Python 3.12+ run gets; CI's 3.11 run falls back to ctrace regardless
metadata:
  type: project
---

Root `pyproject.toml` sets `[tool.coverage.run] core = "sysmon"`. The core that a run actually uses depends on its interpreter. Locally `.python-version` pins 3.13, so a local run gets sysmon. CI installs 3.11 (`.github/actions/setup-python/action.yml`), and its pytest header reads `platform linux -- Python 3.11.16`, so CI falls back to ctrace. Nothing gates on the coverage report: CI's `test-python` job runs plain `uv run -q --locked pytest`, with no `fail_under` and no upload.

On Python 3.12+ with coverage 7.15.2, sysmon cannot do branch coverage, plugin file tracers, or dynamic contexts. Branch coverage or dynamic contexts make coverage warn `no-sysmon` and fall back to ctrace; a plugin file tracer only gets a warning that sysmon does not support it.
To add a plugin file tracer, remove `core = "sysmon"` in the same change.

Confirm the configured core with `uv run coverage debug config | grep -i core` → `core: sysmon`; the core a run actually uses is whatever survives the fallbacks above, and a `no-sysmon` warning on the run names it.
A misspelled key prints `CoverageWarning: Unrecognized option` and leaves `core` unset, so coverage uses ctrace.
