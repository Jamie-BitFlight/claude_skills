---
name: project-coverage-sysmon-core
description: How this repo's pytest coverage core is configured and verified (sysmon vs ctrace)
metadata:
  type: project
---

Root `pyproject.toml` `[tool.coverage.run]` sets `core = "sysmon"` (added PR #2936, 2026-08-17),
switching coverage.py from the default `ctrace` (`sys.settrace`) core to the PEP 669
`sys.monitoring` core on Python 3.13. Measured 84% user-CPU reduction / 48% wall reduction on a
`tests_sam` run with byte-identical coverage output — see
`.tmp/scratch/reports/pytest-fix-options-coverage-overhead.md` for the full A/B/C measurement.

**Why sysmon was safe here**: nothing in this repo's own CI consumes the coverage report as a
quality gate (`test-python` job just runs `uv run -q pytest`, no `--cov`/`fail_under`/upload) —
verified before switching, not assumed. Also: branch coverage was already off, no coverage
plugins configured, no dynamic contexts configured — the three documented sysmon limitations on
pre-3.14 Python.

**How to verify which core is actually active** (the config key silently no-ops if misspelled or
below coverage 7.9.0):

```bash
uv run coverage debug config | grep -i core   # -> "core: sysmon"
```

or programmatically:

```python
import coverage
c = coverage.Coverage()
c.start(); c.stop()
type(c._collector.core.tracer_class)  # -> coverage.sysmon.SysMonitor when active
```

Note the attribute is `c._collector.core` (not `._collector._core` — that raises
`AttributeError`, the underscore-prefixed name doesn't exist on `Collector`).

`[tool.coverage.run] omit` also had to gain `tests_sam/*`, `*/tests_sam/*`, `tests_backlog/*`,
`*/tests_backlog/*` in the same PR — the pre-existing `tests/*`/`*/tests/*` patterns don't match
those directory names, so files under them (mainly non-`test_*.py` helpers/conftest) were being
counted as measured "source" in the coverage report.

If this repo ever needs branch coverage before moving to Python 3.14, `core = "sysmon"` must be
turned back off first (sysmon lacks branch-coverage support on 3.12/3.13).
