# Testing

## Commands

```bash
uv run pytest                              # Fast suite (parallel via xdist); e2e, cross_backend, and integration are deselected by addopts
uv run pytest -m "not slow"                # Additionally skip slow tests
uv run pytest -m integration plugins/development-harness/tests/   # Integration tests (deselected by default)
uv run pytest plugins/development-harness/tests/  # Specific test directory
uv run pytest plugins/development-harness/tests/test_migrate_tasks_to_github.py  # Specific test file
```

Coverage (`--cov=scripts --cov=plugins`) is always on via addopts — passing `--cov` again is redundant.

## Plugin installation testing

```bash
claude --plugin-dir ./plugins/python3-development       # Load single plugin
claude --plugin-dir ./plugins/holistic-linting          # Load multiple plugins
/plugin marketplace add ./.claude-plugin/marketplace.json  # Add local marketplace
/plugin install python3-development@jamie-bitflight-skills --scope local
/plugin validate ./plugins/plugin-name                  # Validate plugin structure
```

## Patterns and conventions

- **Framework**: pytest with `pytest-xdist` (parallel), `pytest-asyncio` (async), `pytest-mock`
- **Markers**: `unit`, `integration`, `e2e`, `slow`, `demos`, `cross_backend`, `critical`,
  `allow_startup_sync`
- **Default deselection**: addopts include `-m "not e2e and not cross_backend and not integration"`,
  so a bare `uv run pytest` runs the fast in-process suite only. Integration tests (real-subprocess
  CLI/network-guard behavior, ~2-30s each) and cross-backend tests run as separate CI jobs; e2e
  tests need a live `GITHUB_TOKEN` and run only on main.
- **Async mode**: `asyncio_mode = "auto"` — tests auto-detect async
- **Test discovery**: Multiple test directories configured in `pyproject.toml [tool.pytest.ini_options] testpaths`
  (plugin `tests/` dirs, `development-harness`'s `tests_sam`/`sam_schema/tests`/`backlog_core/tests`,
  root `tests/`, `examples/solid-review-ab/tests`, and the scripts dirs that host colocated tests)
- **Type checker exclusions**: Test files get relaxed rules in `pyproject.toml` per-file overrides
- **Test file placement**: A test lives beside the code it exercises. Tests for code inside a
  plugin go in that plugin's own test directory (`plugins/{name}/tests/`, or the module-local
  directory a plugin already uses, e.g. `sam_schema/tests/`). Root `tests/` is only for code that
  serves repository maintenance and systems — `scripts/`, `.claude/` skill scripts, and CI
  tooling. Placement follows the import target, not convenience: a test that imports plugin code
  belongs in that plugin even when it also touches root tooling. A plugin test placed in root
  `tests/` runs in CI but is invisible to that plugin's standalone runner, so its coverage
  silently disappears for anyone who installs the plugin on its own. Move a misplaced test file
  to the correct location rather than leaving it and noting the exception.
- **Close criteria**: passing pre-existing tests proves no regression, not correctness — do not
  mark a fix or issue closed without a test that specifically demonstrates the new/fixed behavior
- **SAM/backlog MCP error contract**: `sam_schema/server.py` tool handlers let exceptions
  (`PlanNotFoundError`, `TaskNotFoundError`, etc.) propagate rather than returning
  `{"error": ...}` dicts — FastMCP converts them to `isError=true` responses. Tests for
  invalid-input paths must use `pytest.raises(ToolError)` (`fastmcp.exceptions.ToolError`), not
  `assert result["error"]`.
- **pytest parallelism**: Tests run with `-n 2 --dist loadgroup` (xdist): one controller plus two
  workers. Tests marked with `@pytest.mark.xdist_group` run in same worker.
- **conftest name collision**: `plugins/scientific-method/mcp/experiment-registry/tests` is
  excluded from pytest testpaths because its conftest collides with development-harness's conftest
  (both resolve as "tests.conftest").
- **Validation warnings**: Warnings fail validation unless a versioned, scope-limited exception is
  recorded in the relevant plan with an expiry/review condition. Never disable pytest's strict
  configuration to make a warning non-fatal; a minimal runner must explicitly retain
  `--strict-config` and install each configured pytest plugin it needs.
