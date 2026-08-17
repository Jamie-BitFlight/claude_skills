---
name: project-dh-conftest-lazy-import-cost
description: plugins/development-harness/conftest.py (rootdir conftest) must keep heavy imports lazy inside fixtures, not module-level — breaks nested pytest subprocess timeouts
metadata:
  type: project
---

`plugins/development-harness/conftest.py` is the pytest **rootdir** conftest for the whole
plugin subtree (`tests/`, `tests_sam/`, `sam_schema/tests/`, `backlog_core/tests/`, and eventually
`tests_backlog/` — see backlog #2930). Every pytest process that collects anything under this
subtree pays whatever import cost this file's module-level statements incur, including nested
`subprocess.run([..., "-m", "pytest", ...])` calls that `tests/test_network_guard.py`'s guard-probe
tests spawn to test socket-guard behaviour in isolation — those probes run under **tight
wall-clock timeouts (15-30s)** calibrated for a lightweight nested pytest startup.

**Why:** discovered while promoting `_disable_startup_sync` (originally scoped only to
`tests/conftest.py`) up to this rootdir conftest so it'd cover `tests_backlog/` too (PR #2946,
`fix/startup-sync-teardown-scoping`). Fixing the resulting `ruff` `import-outside-top-level`
(PLC0415) by moving `import backlog_core.server` to module level made `test_network_guard.py`'s
subprocess probes start timing out — `backlog_core.server` pulls in FastMCP + the full MCP tool
surface, measured at ~4.5s CPU / much more wall-clock under any contention, verified via
`time uv run python -c "import backlog_core.server"`. That cost, previously paid lazily only when
a fixture body actually executed (and skipped entirely for e2e-marked tests), became a mandatory
per-process cost for every nested subprocess.

**How to apply:** when adding a fixture to this specific file that needs a heavy plugin import
(`backlog_core.server`, `fastmcp`, etc.), keep the import **inside the fixture function body**
(lazy), not at module level — matching the original pattern that lived in `tests/conftest.py`
before promotion. This trips `ruff`'s PLC0415; the correct fix is a `pyproject.toml`
`[tool.ruff.lint.per-file-ignores]` entry for the specific file
(`"plugins/development-harness/conftest.py" = ["import-outside-top-level"]`, with a comment
explaining why), mirroring the existing `"**/assets/version.py"` entry for the same rule — not an
inline `noqa`. Verify by re-running `tests/test_network_guard.py` in isolation
(`uv run pytest plugins/development-harness/tests/test_network_guard.py --no-cov -n 2`) after any
edit to this file's top-level imports.

See also [[project-dh-multi-agent-worktree-contention]] for why isolated timing verification on
this machine needs a throwaway `git worktree add <path> HEAD` baseline rather than `git stash`
(blocked by the auto-mode classifier) — many concurrent agent worktrees run full `pytest -n auto`
suites simultaneously and can starve subprocess-timeout-sensitive tests for CPU, so a failure must
be reproduced against an unmodified baseline under the same contention before concluding it's a
real regression.
