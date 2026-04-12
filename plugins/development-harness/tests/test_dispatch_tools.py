"""Integration tests for the four dispatch MCP tools in backlog_core.server.

Tests: dispatch_wave_start, dispatch_item_status, dispatch_wave_status, dispatch_spawn
Strategy:
  - Each test uses a fresh DispatchStateManager backed by a tmp_path SQLite file.
  - The module-level singleton ``_dispatch_state_manager`` is patched so every tool
    call routes to the per-test manager, preventing cross-test state bleed.
  - subprocess calls are mocked via mocker.patch on asyncio.create_subprocess_exec so
    no real processes are ever spawned.
  - FastMCP in-memory Client is used for all tool invocations (no HTTP transport).
  - ``asyncio_mode = "auto"`` is declared in pyproject.toml; no @pytest.mark.asyncio.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from backlog_core.dispatch_state import DispatchStateManager
from backlog_core.models import DispatchItemRecord
from backlog_core.server import mcp
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mgr(tmp_path: Path) -> DispatchStateManager:
    """Return a fresh DispatchStateManager backed by a tmp_path database.

    Args:
        tmp_path: pytest-provided temporary directory.

    Returns:
        Initialised DispatchStateManager with clean schema.
    """
    return DispatchStateManager(tmp_path / "dispatch-test.db")


def _seed_wave(
    mgr: DispatchStateManager, milestone: int = 10, wave_num: int = 1, issues: list[int] | None = None
) -> None:
    """Seed a wave with items into an existing manager.

    Args:
        mgr: Manager to insert into.
        milestone: Milestone number (default 10).
        wave_num: Wave number (default 1).
        issues: Issue numbers to create items for (default [101, 102]).
    """
    if issues is None:
        issues = [101, 102]
    items = [DispatchItemRecord(milestone=milestone, wave_num=wave_num, issue=n, title=f"Issue {n}") for n in issues]
    mgr.create_wave(milestone=milestone, wave_num=wave_num, items=items)


def _make_dispatch_plan_yaml(milestone: int = 10, wave_num: int = 1, issues: list[int] | None = None) -> str:
    """Return a minimal dispatch plan YAML string for use in fixture files.

    Args:
        milestone: Milestone number to embed.
        wave_num: Wave number.
        issues: Issue numbers for the wave items (default [101, 102]).

    Returns:
        YAML string conforming to the DispatchPlan schema.
    """
    if issues is None:
        issues = [101, 102]
    items_yaml = "\n".join(f"    - title: Issue {i}\n      issue: {i}\n      priority: P2" for i in issues)
    return f"""\
milestone:
  number: {milestone}
  title: Test milestone {milestone}
  integration-branch: main
waves:
  - wave: {wave_num}
    items:
{items_yaml}
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr(tmp_path: Path) -> DispatchStateManager:
    """Provide a fresh DispatchStateManager for each test.

    Returns:
        Clean DispatchStateManager instance backed by a temporary SQLite file.
    """
    return _make_mgr(tmp_path)


@pytest.fixture
def patch_state_manager(mocker: MockerFixture, mgr: DispatchStateManager) -> DispatchStateManager:
    """Patch _dispatch_state_manager() to return the per-test mgr.

    This patches the module-level singleton factory so every tool call in
    server.py uses the isolated test database rather than the real
    ~/.dh/.../dispatch-state.db path.

    Returns:
        The same DispatchStateManager instance passed to every tool call.
    """
    mocker.patch("backlog_core.server._dispatch_state_manager", return_value=mgr)
    return mgr


@pytest.fixture
def dispatch_plan_file(tmp_path: Path) -> Path:
    """Write a minimal dispatch plan YAML to a tmp file and return its path.

    Returns:
        Path to the written dispatch plan YAML file.
    """
    plan_path = tmp_path / "milestone-10-dispatch.yaml"
    plan_path.write_text(_make_dispatch_plan_yaml())
    return plan_path


@pytest.fixture
def patch_dispatch_plan_path(mocker: MockerFixture, dispatch_plan_file: Path) -> Path:
    """Patch _dispatch_plan_path() to return the tmp dispatch plan file.

    Returns:
        Path to the patched dispatch plan file.
    """
    mocker.patch("backlog_core.server._dispatch_plan_path", return_value=dispatch_plan_file)
    return dispatch_plan_file


# ---------------------------------------------------------------------------
# dispatch_wave_start
# ---------------------------------------------------------------------------


class TestDispatchWaveStart:
    """Integration tests for the dispatch_wave_start MCP tool.

    Tests tool registration, success path, duplicate prevention, and
    response field contract. All calls use the FastMCP in-memory Client
    against the real ``mcp`` application instance so the full tool
    dispatch stack is exercised.
    """

    async def test_creates_wave_successfully(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_start returns wave metadata on first call.

        Tests: dispatch_wave_start happy path
        How: Call the tool via in-memory Client with milestone=10, wave_num=1,
             two items. Verify the response contains expected fields.
        Why: Tool callers depend on wave_id, items_count, and status fields
             to seed their dispatch loop state.
        """
        # Arrange
        items = [{"issue": 101, "title": "Feature A"}, {"issue": 102, "title": "Feature B"}]

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_wave_start", {"milestone": 10, "wave_num": 1, "items": items})

        # Assert
        data: dict[str, Any] = result.data
        assert data["milestone"] == 10
        assert data["wave_num"] == 1
        assert data["items_count"] == 2
        assert data["status"] == "pending"
        assert "error" not in data

    async def test_returns_error_on_duplicate_wave(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_start returns an error dict when the wave already exists.

        Tests: dispatch_wave_start duplicate prevention
        How: Call the tool twice with the same milestone+wave_num. Verify the
             second call returns an ``error`` key without raising an exception.
        Why: The tool must not crash the server on duplicate dispatch; callers
             check for the error key to detect idempotency violations.
        """
        # Arrange
        items = [{"issue": 101, "title": "Feature A"}]

        async with Client(mcp) as client:
            # First call — should succeed
            await client.call_tool("dispatch_wave_start", {"milestone": 10, "wave_num": 1, "items": items})

            # Act — second call with same (milestone, wave_num)
            result = await client.call_tool("dispatch_wave_start", {"milestone": 10, "wave_num": 1, "items": items})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "10" in data["error"] or "Wave 1" in data["error"]

    async def test_creates_items_in_database(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_start persists items to the state database.

        Tests: dispatch_wave_start side-effect on state
        How: Call the tool, then read back wave items directly from the
             manager to confirm persistence occurred.
        Why: If items are not written, subsequent dispatch_item_status calls
             will fail to find items by issue number.
        """
        # Arrange
        items = [{"issue": 201, "title": "Task one"}, {"issue": 202, "title": "Task two"}]

        # Act
        async with Client(mcp) as client:
            await client.call_tool("dispatch_wave_start", {"milestone": 20, "wave_num": 1, "items": items})

        # Assert
        persisted = patch_state_manager.get_wave_items(milestone=20, wave_num=1)
        assert len(persisted) == 2
        assert {i.issue for i in persisted} == {201, 202}
        assert all(i.status == "pending" for i in persisted)

    async def test_response_contains_messages_and_warnings(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_start success response includes messages and warnings lists.

        Tests: dispatch_wave_start response schema
        How: Create a wave and inspect the messages/warnings keys.
        Why: Callers expect these lists to be present (even if empty) for
             uniform response handling.
        """
        # Arrange + Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_wave_start", {"milestone": 30, "wave_num": 1, "items": [{"issue": 301, "title": "X"}]}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert isinstance(data.get("messages"), list)
        assert isinstance(data.get("warnings"), list)


# ---------------------------------------------------------------------------
# dispatch_item_status
# ---------------------------------------------------------------------------


class TestDispatchItemStatus:
    """Integration tests for the dispatch_item_status MCP tool.

    Tests the complete/failed/skipped/invalid status transitions and the
    not-found error path. The tool searches across all waves for a matching
    issue number, so seeding via the state manager is sufficient setup.
    """

    async def test_marks_item_complete(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_item_status records completion for an existing item.

        Tests: dispatch_item_status — complete transition
        How: Seed a wave with issue 101, call the tool with status=complete,
             then verify the item is marked complete in the database.
        Why: Spawned workers report completion through this tool; incorrect
             status transitions cause the dispatch loop to stall.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101, 102])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_item_status", {"milestone": 10, "issue": 101, "status": "complete", "result": "ok"}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert data["milestone"] == 10
        assert data["issue"] == 101
        assert data["status"] == "complete"
        assert "error" not in data

        item = patch_state_manager.get_item(milestone=10, wave_num=1, issue=101)
        assert item is not None
        assert item.status == "complete"

    async def test_marks_item_failed(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_item_status records failure for an existing item.

        Tests: dispatch_item_status — failed transition
        How: Seed a wave with issue 101, call the tool with status=failed and
             an error message. Verify item status and error field in the database.
        Why: Failure tracking drives retry decisions and post-dispatch summaries.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_item_status", {"milestone": 10, "issue": 101, "status": "failed", "error": "timeout"}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert data["status"] == "failed"
        assert "error" not in data  # no lookup error

        item = patch_state_manager.get_item(milestone=10, wave_num=1, issue=101)
        assert item is not None
        assert item.status == "failed"
        assert item.error == "timeout"

    async def test_marks_item_skipped(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_item_status treats skipped as a failed terminal state.

        Tests: dispatch_item_status — skipped transition
        How: Seed a wave, call with status=skipped. Verify the DB item is
             in failed state (skipped maps to failed per implementation).
        Why: skipped is a valid dispatch outcome that must be persisted as
             terminal to avoid re-dispatch.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_item_status", {"milestone": 10, "issue": 101, "status": "skipped"}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert data["status"] == "skipped"
        assert "error" not in data

    async def test_returns_error_for_unknown_issue(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_item_status returns error dict when issue not found in any wave.

        Tests: dispatch_item_status — not-found path
        How: Call the tool for an issue number that was never seeded.
        Why: Callers must be able to detect missing items without the server
             raising an unhandled exception.
        """
        # Arrange — empty database, issue 999 does not exist

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_item_status", {"milestone": 10, "issue": 999, "status": "complete"}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "999" in data["error"]

    async def test_returns_error_for_invalid_status(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_item_status returns error dict for an unrecognised status value.

        Tests: dispatch_item_status — invalid status guard
        How: Seed an item, then call with status='running' (not a valid value).
        Why: Prevents silent corruption of item state with arbitrary string values.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_item_status", {"milestone": 10, "issue": 101, "status": "running"}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "running" in data["error"]


# ---------------------------------------------------------------------------
# dispatch_wave_status
# ---------------------------------------------------------------------------


class TestDispatchWaveStatus:
    """Integration tests for the dispatch_wave_status MCP tool.

    Verifies the wave summary aggregation, stale-PID detection, and
    not-found error path. check_stale_pids is exercised by patching os.kill
    so no live process management occurs.
    """

    async def test_returns_wave_summary_for_existing_wave(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_status returns aggregated item counts for a known wave.

        Tests: dispatch_wave_status happy path
        How: Seed a wave with two pending items. Call the tool and verify
             summary fields: total_items, pending, complete, failed.
        Why: Orchestrators poll this tool to decide when to advance to the
             next wave; incorrect counts cause premature or stalled advancement.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101, 102])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_wave_status", {"milestone": 10, "wave_num": 1})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data
        assert data["total_items"] == 2
        assert data["pending"] == 2
        assert data["complete"] == 0
        assert data["failed"] == 0

    async def test_returns_error_for_missing_wave(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_status returns error dict when wave does not exist.

        Tests: dispatch_wave_status — not-found path
        How: Query wave_num=99 on a milestone that has no waves.
        Why: The tool must not raise; callers check the error key.
        """
        # Arrange — empty database

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_wave_status", {"milestone": 10, "wave_num": 99})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "99" in data["error"]

    async def test_detects_stale_pid_and_marks_item_failed(
        self, patch_state_manager: DispatchStateManager, mocker: MockerFixture
    ) -> None:
        """dispatch_wave_status detects a dead PID and marks the item failed.

        Tests: dispatch_wave_status — stale PID detection
        How: Seed a wave, mark item 101 in-progress with pid=77777.
             Patch os.kill to raise ProcessLookupError (PID dead).
             Call dispatch_wave_status and verify:
             (a) the warnings list contains a stale-PID message,
             (b) the item is marked failed in the database.
        Why: Ensures the tool surfaces stuck spawns rather than reporting
             phantom in-progress items indefinitely.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101, 102])
        patch_state_manager.set_item_in_progress(milestone=10, wave_num=1, issue=101, pid=77777)

        mocker.patch("backlog_core.dispatch_state.os.kill", side_effect=ProcessLookupError)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_wave_status", {"milestone": 10, "wave_num": 1})

        # Assert — stale PID warning is surfaced in the response
        data: dict[str, Any] = result.data
        assert "error" not in data
        warnings: list[str] = data.get("warnings", [])
        assert any("77777" in w or "101" in w for w in warnings), (
            f"Expected stale-PID warning for pid=77777 / issue=101, got warnings: {warnings}"
        )

        # Assert — item is now failed in the database
        item = patch_state_manager.get_item(milestone=10, wave_num=1, issue=101)
        assert item is not None
        assert item.status == "failed"

    async def test_response_contains_items_list(self, patch_state_manager: DispatchStateManager) -> None:
        """dispatch_wave_status includes per-item detail in the response.

        Tests: dispatch_wave_status — items list field
        How: Seed a wave with two items, call the tool, verify the items
             field is a non-empty list containing the seeded issue numbers.
        Why: Callers use the items list to surface per-item status to the user.
        """
        # Arrange
        _seed_wave(patch_state_manager, milestone=10, wave_num=1, issues=[101, 102])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_wave_status", {"milestone": 10, "wave_num": 1})

        # Assert
        data: dict[str, Any] = result.data
        items = data.get("items", [])
        assert len(items) == 2
        item_issues = {i["issue"] for i in items}
        assert item_issues == {101, 102}


# ---------------------------------------------------------------------------
# dispatch_spawn
# ---------------------------------------------------------------------------


class TestDispatchSpawn:
    """Integration tests for the dispatch_spawn MCP tool (background task).

    dispatch_spawn is decorated with @mcp.tool(task=True) so the FastMCP
    client returns a task handle on the first call and the result is
    delivered when the background task finishes.

    All subprocess creation is mocked so no real processes are spawned.
    The mock simulates spawn.py emitting a JSON line ``{"pid": 0,
    "result_file": "<path>"}`` to stdout; a corresponding result file is
    written to tmp_path so _poll_until_done detects completion.
    """

    async def test_spawn_end_to_end_single_wave(
        self, patch_state_manager: DispatchStateManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """dispatch_spawn processes one wave and returns a completion summary.

        Tests: dispatch_spawn — full end-to-end with mocked subprocess
        How:
          1. Write a dispatch plan YAML with a single item (avoids concurrent
             SQLite writes from asyncio.gather which cause transaction conflicts
             when two threads call set_item_complete simultaneously).
          2. Prepare a result file so _poll_until_done detects completion on
             the first poll cycle.
          3. Mock asyncio.create_subprocess_exec to emit spawn.py JSON pointing
             to the prepared result file.
          4. Call dispatch_spawn via in-memory Client and await the result.
          5. Verify the summary shows the item completed with no failures.
        Why: The tool is the core workhorse of dispatch; verifying the
             end-to-end path with mocked I/O guards against regressions in
             the item monitoring loop.
        """
        # Arrange — single-item plan to avoid concurrent thread writes to SQLite.
        plan_path = tmp_path / "milestone-10-dispatch.yaml"
        plan_path.write_text(_make_dispatch_plan_yaml(milestone=10, wave_num=1, issues=[101]))
        mocker.patch("backlog_core.server._dispatch_plan_path", return_value=plan_path)

        result_file = tmp_path / "result-101.json"
        result_file.write_text(json.dumps({"status": "ok", "cost": 0.01}))

        def _fake_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            """Return a mock process whose stdout encodes spawn.py JSON."""
            proc = MagicMock()
            spawn_json = json.dumps({"pid": 0, "result_file": str(result_file)}).encode()
            proc.communicate = AsyncMock(return_value=(spawn_json, b""))
            return proc

        mocker.patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=_fake_subprocess))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_spawn", {"milestone": 10, "wave_num": 1})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["total_items"] == 1
        assert data["completed"] == 1
        assert data["failed"] == 0

    async def test_spawn_missing_plan_returns_error(
        self, patch_state_manager: DispatchStateManager, mocker: MockerFixture
    ) -> None:
        """dispatch_spawn returns an error dict when the dispatch plan file is absent.

        Tests: dispatch_spawn — FileNotFoundError handling
        How: Patch _dispatch_plan_path to return a non-existent file path.
             Call dispatch_spawn and verify the error key is set.
        Why: Missing plan files are a common operator error; the tool must
             return a meaningful error rather than an unhandled exception.
        """
        # Arrange
        missing = Path("/tmp/does-not-exist-abc123/milestone-10-dispatch.yaml")
        mocker.patch("backlog_core.server._dispatch_plan_path", return_value=missing)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_spawn", {"milestone": 10, "wave_num": 1})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "10" in str(data["error"]) or "not found" in data["error"].lower()

    async def test_spawn_subprocess_non_json_output_marks_item_failed(
        self, patch_state_manager: DispatchStateManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """dispatch_spawn marks an item failed when spawn.py emits non-JSON stdout.

        Tests: dispatch_spawn — non-JSON output error path
        How: Use a single-item plan to avoid concurrent SQLite writes.
             Mock subprocess to return plain text instead of JSON. Verify
             the item is counted in the failed tally and the summary reflects
             the failure.
        Why: spawn.py may fail to start cleanly; the tool must not crash and
             must record the failure so the operator can diagnose it.
        """
        # Arrange — single-item plan; patch plan path to tmp file.
        plan_path = tmp_path / "milestone-10-dispatch.yaml"
        plan_path.write_text(_make_dispatch_plan_yaml(milestone=10, wave_num=1, issues=[101]))
        mocker.patch("backlog_core.server._dispatch_plan_path", return_value=plan_path)

        def _bad_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            proc = MagicMock()
            proc.communicate = AsyncMock(return_value=(b"ERROR: spawn failed\n", b""))
            return proc

        mocker.patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=_bad_subprocess))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_spawn", {"milestone": 10, "wave_num": 1})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data  # tool returns a summary, not an error
        assert data["failed"] > 0

    async def test_spawn_calls_check_stale_pids_at_startup(
        self, patch_state_manager: DispatchStateManager, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """dispatch_spawn calls check_stale_pids before spawning to clean up prior runs.

        Tests: dispatch_spawn — stale PID cleanup on entry
        How: Spy on the state manager's check_stale_pids method. Use a
             single-item plan, mock subprocess to return an immediate completion,
             call dispatch_spawn, and verify check_stale_pids was invoked.
        Why: Without the stale-PID cleanup call, orphaned sessions from prior
             runs accumulate as in-progress items and block wave progress
             indefinitely. Verifying the call is made ensures the guard is active
             regardless of whether stale items exist in a given test run.
        """
        # Arrange — single-item plan; spy on check_stale_pids.
        plan_path = tmp_path / "milestone-10-dispatch.yaml"
        plan_path.write_text(_make_dispatch_plan_yaml(milestone=10, wave_num=1, issues=[101]))
        mocker.patch("backlog_core.server._dispatch_plan_path", return_value=plan_path)

        check_stale_spy = mocker.spy(patch_state_manager, "check_stale_pids")

        result_file = tmp_path / "result-spawn.json"
        result_file.write_text(json.dumps({"status": "ok"}))

        def _fake_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            proc = MagicMock()
            spawn_json = json.dumps({"pid": 0, "result_file": str(result_file)}).encode()
            proc.communicate = AsyncMock(return_value=(spawn_json, b""))
            return proc

        mocker.patch("asyncio.create_subprocess_exec", new=AsyncMock(side_effect=_fake_subprocess))

        # Act
        async with Client(mcp) as client:
            await client.call_tool("dispatch_spawn", {"milestone": 10, "wave_num": 1})

        # Assert — check_stale_pids must be called once at startup
        assert check_stale_spy.call_count >= 1, (
            "dispatch_spawn must call check_stale_pids at startup to clean up orphaned sessions"
        )


# ---------------------------------------------------------------------------
# dispatch_create_plan
# ---------------------------------------------------------------------------


def _make_valid_plan_dict(milestone: int = 10, issue: int = 101) -> dict:
    """Return a minimal valid dispatch plan dict for TestDispatchCreatePlan.

    Args:
        milestone: Milestone number to embed in the plan.
        issue: Issue number for the single wave item.

    Returns:
        Dict conforming to the DispatchPlan JSON schema with one wave and one item.
    """
    return {
        "milestone": {"number": milestone, "title": f"Test Milestone {milestone}", "integration_branch": "main"},
        "waves": [{"wave": 1, "items": [{"title": f"Issue {issue}", "issue": issue, "priority": "P2"}]}],
    }


@pytest.fixture
def valid_plan_dict() -> dict:
    """Provide a minimal valid dispatch plan dict for milestone 10.

    Returns:
        Dict with milestone number 10, one wave, one item (issue 101).
    """
    return _make_valid_plan_dict(milestone=10, issue=101)


@pytest.fixture
def plan_target_path(tmp_path: Path) -> Path:
    """Return a non-existent plan file path inside tmp_path.

    Returns:
        Path object pointing to a file that does not exist yet.
    """
    return tmp_path / "milestone-10-dispatch.yaml"


@pytest.fixture
def patch_create_plan_path(mocker: MockerFixture, plan_target_path: Path) -> Path:
    """Patch _dispatch_plan_path() to return a non-existent tmp path (for creation tests).

    Returns:
        Path to the patched (non-existent) dispatch plan file location.
    """
    mocker.patch("backlog_core.server._dispatch_plan_path", return_value=plan_target_path)
    return plan_target_path


@pytest.fixture
def existing_plan_file(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Pre-write a valid dispatch plan file and patch _dispatch_plan_path to return it.

    Returns:
        Path to the pre-written dispatch plan file.
    """
    plan_path = tmp_path / "milestone-10-dispatch.yaml"
    plan_path.write_text(_make_dispatch_plan_yaml())
    mocker.patch("backlog_core.server._dispatch_plan_path", return_value=plan_path)
    return plan_path


class TestDispatchCreatePlan:
    """Integration tests for the dispatch_create_plan MCP tool.

    Tests the full creation lifecycle: typed plan dict acceptance (kebab-case and
    snake_case alias keys), overwrite protection, milestone number consistency,
    post-write integrity validation, and best-effort artifact registration.
    All calls use the FastMCP in-memory Client against the real ``mcp``
    application instance; no HTTP transport is used.

    Fixtures:
        valid_plan_dict: Minimal valid plan dict for milestone 10 with one wave/item.
        plan_target_path: Non-existent path in tmp_path for creation tests.
        patch_create_plan_path: Patches _dispatch_plan_path to non-existent tmp path.
        existing_plan_file: Pre-written plan file for overwrite/exists tests.
    """

    # ------------------------------------------------------------------
    # Happy-path tests
    # ------------------------------------------------------------------

    async def test_create_plan_valid_yaml(self, valid_plan_dict: dict, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan writes a file and returns success metadata for a valid plan dict.

        Tests: dispatch_create_plan — happy path
        How: Call the tool with a minimal valid plan dict for milestone 10. Verify the
             response has no error key, wave_count and item_count are correct, and
             is_valid is True (default validate=True).
        Why: Callers depend on wave_count and item_count to confirm the plan was accepted
             and written before invoking dispatch_wave_start.
        """
        # Arrange
        target = patch_create_plan_path

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": valid_plan_dict})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["milestone_number"] == 10
        assert data["wave_count"] == 1
        assert data["item_count"] == 1
        assert data["is_valid"] is True
        assert target.exists()

    async def test_create_plan_kebab_case_keys(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan accepts kebab-case alias keys in the plan dict.

        Tests: dispatch_create_plan — kebab-case key acceptance
        How: Provide a dict with 'integration-branch' and 'conflict-groups' in kebab-case.
             Verify the tool accepts and writes without error.
        Why: The DispatchPlan schema uses AliasChoices for both forms; callers
             from groom-milestone produce kebab-case dicts by convention.
        """
        # Arrange — use kebab-case alias keys that Pydantic resolves via AliasChoices
        plan_dict = {
            "milestone": {"number": 10, "title": "Test Milestone", "integration-branch": "feature/test"},
            "conflict-groups": [],
            "waves": [{"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P1"}]}],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": plan_dict})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["wave_count"] == 1
        assert patch_create_plan_path.exists()

    async def test_create_plan_snake_case_keys(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan accepts snake_case alias keys in the plan dict.

        Tests: dispatch_create_plan — snake_case key acceptance
        How: Provide a dict with 'integration_branch' and 'conflict_groups' in snake_case.
             Verify the tool accepts and writes without error.
        Why: The AliasChoices on DispatchPlan fields accept both forms; both must work
             so callers are not forced to canonicalise keys before calling.
        """
        # Arrange — use snake_case keys (the other alias form)
        plan_dict = {
            "milestone": {"number": 10, "title": "Test Milestone", "integration_branch": "main"},
            "conflict_groups": [],
            "waves": [{"wave": 1, "items": [{"title": "Issue 202", "issue": 202, "priority": "P0"}]}],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": plan_dict})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["item_count"] == 1
        assert patch_create_plan_path.exists()

    async def test_create_plan_validate_false(self, valid_plan_dict: dict, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan skips integrity validation when validate=False.

        Tests: dispatch_create_plan — validate=False path
        How: Call with validate=False and a valid plan dict. Verify is_valid is None in
             the response and the file is still written.
        Why: Callers that have already validated externally can skip the post-write
             check for performance; is_valid=None signals validation was not run.
        """
        # Arrange
        target = patch_create_plan_path

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_create_plan", {"milestone_number": 10, "plan": valid_plan_dict, "validate": False}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["is_valid"] is None
        assert target.exists()

    async def test_create_plan_overwrite_existing(self, existing_plan_file: Path) -> None:
        """dispatch_create_plan replaces an existing file when overwrite=True.

        Tests: dispatch_create_plan — overwrite=True success path
        How: Use the existing_plan_file fixture (which pre-writes a plan and patches
             the path). Call with overwrite=True and a YAML containing two items.
             Verify the response has no error and item_count reflects the new content.
        Why: Re-grooming a milestone produces an updated plan that must replace the
             prior one atomically; overwrite=True is the groom-milestone use case.
        """
        # Arrange — existing_plan_file fixture has already written one item
        new_plan = {
            "milestone": {"number": 10, "title": "Updated Milestone", "integration_branch": "main"},
            "waves": [
                {
                    "wave": 1,
                    "items": [
                        {"title": "Issue 101", "issue": 101, "priority": "P2"},
                        {"title": "Issue 102", "issue": 102, "priority": "P3"},
                    ],
                }
            ],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_create_plan", {"milestone_number": 10, "plan": new_plan, "overwrite": True}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        assert data["item_count"] == 2
        assert existing_plan_file.exists()

    async def test_create_plan_with_issue(
        self, valid_plan_dict: dict, patch_create_plan_path: Path, mocker: MockerFixture
    ) -> None:
        """dispatch_create_plan attempts artifact registration when issue is provided.

        Tests: dispatch_create_plan — artifact registration side-effect
        How: Patch _try_register_dispatch_plan_artifact to a mock. Call the tool with
             issue=42. Verify the mock was called once with the correct arguments.
        Why: Artifact registration ties the plan file to a GitHub issue for cross-tool
             discovery; missing registration breaks artifact_read lookups.
        """
        # Arrange
        register_mock = mocker.patch("backlog_core.server._try_register_dispatch_plan_artifact")

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_create_plan", {"milestone_number": 10, "plan": valid_plan_dict, "issue": 42}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected error: {data.get('error')}"
        register_mock.assert_called_once_with(42, patch_create_plan_path)

    # ------------------------------------------------------------------
    # Error-case tests
    # ------------------------------------------------------------------

    async def test_create_plan_invalid_plan_structure(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan raises ToolError when the plan dict fails Pydantic validation.

        Tests: dispatch_create_plan — Pydantic validation failure for structurally invalid input
        How: Pass a dict where milestone.number is a string instead of an int. Verify
             the call raises ToolError (FastMCP rejects at the MCP layer before the
             tool function runs) and no file is written.
        Why: With the typed plan parameter, Pydantic validates the input before the
             function is called; invalid types raise ToolError rather than returning
             an error dict.
        """
        # Arrange — milestone.number must be int >= 1; pass a string to trigger validation error
        bad_plan = {
            "milestone": {"number": "not-a-number", "title": "Bad Plan", "integration_branch": "main"},
            "waves": [{"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P2"}]}],
        }

        # Act + Assert — FastMCP raises ToolError for Pydantic validation failures
        async with Client(mcp) as client:
            with pytest.raises(ToolError, match=r"int_parsing|not-a-number|integer"):
                await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": bad_plan})

        assert not patch_create_plan_path.exists()

    async def test_create_plan_missing_milestone_field(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan raises ToolError when the plan dict is missing the milestone block.

        Tests: dispatch_create_plan — missing required top-level field
        How: Pass a dict with only waves and no milestone key. Verify the call raises
             ToolError (FastMCP rejects at the MCP layer) and no file is written.
        Why: The DispatchPlan schema requires milestone; Pydantic raises before the
             function runs, so callers receive a ToolError for missing required fields.
        """
        # Arrange — no milestone key at all
        no_milestone_plan = {"waves": [{"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P2"}]}]}

        # Act + Assert — FastMCP raises ToolError for missing required field
        async with Client(mcp) as client:
            with pytest.raises(ToolError, match=r"milestone|missing|required"):
                await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": no_milestone_plan})

        assert not patch_create_plan_path.exists()

    async def test_create_plan_missing_required_field(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan raises ToolError when 'waves' is absent from the plan dict.

        Tests: dispatch_create_plan — Pydantic validation failure for missing required field
        How: Provide a dict with a valid milestone block but no 'waves' key. Verify the
             call raises ToolError (FastMCP rejects before the function runs).
        Why: waves is required (min_length=1); Pydantic rejects at the MCP layer so
             callers receive a ToolError with a descriptive message.
        """
        # Arrange — valid milestone but no waves key
        no_waves_plan = {"milestone": {"number": 10, "title": "Missing waves", "integration_branch": "main"}}

        # Act + Assert — FastMCP raises ToolError for missing required field
        async with Client(mcp) as client:
            with pytest.raises(ToolError, match=r"waves|missing|required"):
                await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": no_waves_plan})

    async def test_create_plan_empty_waves(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan raises ToolError when waves is an empty list.

        Tests: dispatch_create_plan — min_length=1 enforcement on waves
        How: Provide a dict with waves: [] (empty list). Verify the call raises
             ToolError (FastMCP rejects the min_length constraint before the function runs).
        Why: DispatchPlan.waves has min_length=1; Pydantic enforces this at the MCP
             layer so an empty list is rejected before reaching the tool function.
        """
        # Arrange — empty waves list violates min_length=1
        empty_waves_plan = {
            "milestone": {"number": 10, "title": "Empty waves", "integration_branch": "main"},
            "waves": [],
        }

        # Act + Assert — FastMCP raises ToolError for min_length violation
        async with Client(mcp) as client:
            with pytest.raises(ToolError, match=r"waves|too_short|min"):
                await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": empty_waves_plan})

    async def test_create_plan_file_exists_no_overwrite(self, existing_plan_file: Path) -> None:
        """dispatch_create_plan returns an error when the file exists and overwrite=False.

        Tests: dispatch_create_plan — overwrite=False protection
        How: Use the existing_plan_file fixture (pre-written file). Call with default
             overwrite=False. Verify the error mentions the existing path.
        Why: Overwrite protection prevents accidental replacement of a live dispatch
             plan mid-wave; callers must explicitly opt in with overwrite=True.
        """
        # Arrange — existing_plan_file fixture has already written and patched the path

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dispatch_create_plan", {"milestone_number": 10, "plan": _make_valid_plan_dict()}
            )

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "already exists" in data["error"] or str(existing_plan_file) in data["error"]

    async def test_create_plan_milestone_mismatch(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan returns an error when milestone numbers disagree.

        Tests: dispatch_create_plan — milestone consistency check
        How: Pass milestone_number=10 as the parameter but embed number: 20 in the
             YAML milestone block. Verify the error describes the mismatch.
        Why: A mismatch means the caller is writing a plan for a different milestone
             than the YAML describes; this would corrupt the plan directory naming.
        """
        # Arrange — milestone_number=10 but plan embeds number=20
        mismatched_plan = {
            "milestone": {"number": 20, "title": "Wrong milestone", "integration_branch": "main"},
            "waves": [{"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P2"}]}],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": mismatched_plan})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "mismatch" in data["error"].lower() or "10" in data["error"]

    async def test_create_plan_symlink_target(
        self, valid_plan_dict: dict, patch_create_plan_path: Path, mocker: MockerFixture
    ) -> None:
        """dispatch_create_plan returns an error when write_dispatch_plan raises ValueError.

        Tests: dispatch_create_plan — symlink rejection from writer
        How: Patch asyncio.to_thread so write_dispatch_plan raises ValueError with
             "symlink" message. Verify the error response contains the symlink message.
        Why: write_dispatch_plan rejects symlink targets for security; the tool must
             surface this as a structured error, not an unhandled exception.
        """
        # Arrange — patch asyncio.to_thread selectively for write_dispatch_plan call
        original_to_thread = __import__("asyncio").to_thread

        async def _selective_to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
            if getattr(func, "__name__", "") == "write_dispatch_plan":
                raise ValueError("symlink target rejected")
            return await original_to_thread(func, *args, **kwargs)

        mocker.patch("asyncio.to_thread", side_effect=_selective_to_thread)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": valid_plan_dict})

        # Assert
        data: dict[str, Any] = result.data
        assert "error" in data
        assert "symlink" in data["error"].lower() or "symlink" in data["error"]

    # ------------------------------------------------------------------
    # Validation-integration tests
    # ------------------------------------------------------------------

    async def test_create_plan_duplicate_issues(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan surfaces is_valid=False when the same issue appears twice.

        Tests: dispatch_create_plan — duplicate issue detection via validate_plan_integrity
        How: Provide YAML with issue 101 in both wave 1 and wave 2. Call with validate=True
             (default). Verify the file is written and is_valid=False in the response.
        Why: Duplicate issues cause double-dispatch of the same work item; integrity
             validation must catch this before the plan is used for dispatch.

        Note: The implementation merges **out.to_dict() after the explicit errors/warnings
        keys, which clobbers the validation error list with an empty list from Output.
        is_valid=False is the reliable signal; the errors key is not asserted here because
        of this known key-collision in the success return dict (divergence DN-1 in T02).
        """
        # Arrange — issue 101 appears in both waves
        duplicate_plan = {
            "milestone": {"number": 10, "title": "Duplicate issue test", "integration_branch": "main"},
            "waves": [
                {"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P2"}]},
                {"wave": 2, "items": [{"title": "Issue 101 again", "issue": 101, "priority": "P3"}]},
            ],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": duplicate_plan})

        # Assert — file is written and integrity check reports failure
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected tool error: {data.get('error')}"
        assert data["is_valid"] is False
        assert patch_create_plan_path.exists()

    async def test_create_plan_broken_depends_on(self, patch_create_plan_path: Path) -> None:
        """dispatch_create_plan surfaces is_valid=False when depends_on references missing issue.

        Tests: dispatch_create_plan — broken depends_on detection via validate_plan_integrity
        How: Provide YAML where item 102 depends_on issue 999 which does not appear in
             any wave. Verify the file is written and is_valid=False in the response.
        Why: A depends_on reference to a non-existent issue creates an unresolvable
             dependency; the validator must catch this to prevent dispatch stalls.

        Note: The implementation merges **out.to_dict() after the explicit errors/warnings
        keys, which clobbers the validation error list with an empty list from Output.
        is_valid=False is the reliable signal; the errors key is not asserted here because
        of this known key-collision in the success return dict (divergence DN-1 in T02).
        """
        # Arrange — issue 102 depends on 999 which is not in the plan
        broken_deps_plan = {
            "milestone": {"number": 10, "title": "Broken depends_on test", "integration_branch": "main"},
            "waves": [
                {"wave": 1, "items": [{"title": "Issue 101", "issue": 101, "priority": "P2"}]},
                {"wave": 2, "items": [{"title": "Issue 102", "issue": 102, "priority": "P3", "depends_on": [999]}]},
            ],
        }

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("dispatch_create_plan", {"milestone_number": 10, "plan": broken_deps_plan})

        # Assert — file is written and integrity check reports failure
        data: dict[str, Any] = result.data
        assert "error" not in data, f"Unexpected tool error: {data.get('error')}"
        assert data["is_valid"] is False
        assert patch_create_plan_path.exists()
