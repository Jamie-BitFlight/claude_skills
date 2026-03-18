---
name: Deterministic time injection in task_status_hook.py
description: "**Current state**: The `get_iso_timestamp()` function at line 227 of `task_status_hook.py` calls `datetime.now(UTC).isoformat(timespec='seconds')` directly. All callers (`handle_subagent_stop`, `handle_post_tool_use`) use this function without the ability to inject a fixed time. Tests for this hook must either mock `datetime.now` at the module level or accept non-deterministic timestamps, making assertions about timestamp ordering or staleness detection fragile.\n\nFile: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`, line 227-233.\n\n**Target state**: `get_iso_timestamp()` accepts an optional `now` parameter (callable returning `datetime`) that defaults to `lambda: datetime.now(UTC)`. Test code passes a fixed `now` callable, enabling deterministic timestamp assertions. The same pattern is applied to any future time-dependent logic (e.g., stall detection threshold comparison).\n\n**Measurable signal**: File `task_status_hook.py` contains `def get_iso_timestamp(*, now: Callable[[], datetime] | None = None)`. At least one test in `tests/test_task_status_hook/` calls `get_iso_timestamp(now=lambda: fixed_dt)` and asserts the exact returned string."
metadata:
  topic: deterministic-time-injection-in-taskstatushookpy
  source: 'Research entry: ./research/developer-tools/tori-cli.md -- pattern: deterministic time injection for testing'
  added: '2026-03-18'
  priority: P2
  type: Refactor
  status: open
  issue: '#782'
  last_synced: '2026-03-18T04:17:10Z'
---