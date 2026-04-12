"""In-memory MCP protocol tests for sam_schema.server.

Tests each tool through the real FastMCP in-memory transport — the same protocol
path that Claude Code agents use. Verifies MCP schema validation, serialization,
and tool dispatch rather than calling tool functions directly.

Uses Client(mcp) per FastMCP v3 testing.md primary test pattern.
asyncio_mode = "auto" is set in pyproject.toml — no @pytest.mark.asyncio needed.

T07: Rewrites all sam_read/sam_state/sam_ready/sam_status/sam_create/sam_update/sam_claim
MCP tests to call sam_task/sam_plan with the new consolidated config dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError
from sam_schema.core.models import Plan, TaskStatus
from sam_schema.server import mcp
from sam_schema.writers.yaml_writer import write_plan

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers (shared — see conftest.py)
# ---------------------------------------------------------------------------

from tests_sam.conftest import make_task

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Write a two-task plan file and return the plan directory path.

    Directory layout::

        tmp_path/
        └── plan/
            └── tasks-1-mcp-test.yaml   (T1 complete, T2 depends on T1)

    Returns:
        Path to the plan directory (``tmp_path/plan``).
    """
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="mcp-test", version="1.0", goal="MCP test goal", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-mcp-test.yaml", force_single=True)
    return p_dir


# ---------------------------------------------------------------------------
# Server metadata
# ---------------------------------------------------------------------------


async def test_server_lists_expected_tools() -> None:
    """Server exposes exactly the three documented tools via the MCP protocol.

    Tests: tool registration completeness through the MCP protocol.
    How: Call list_tools() via in-memory Client.
    Why: Catches decorator or import errors that would remove a tool silently.
    """
    # Arrange + Act
    async with Client(mcp) as client:
        tools = await client.list_tools()

    # Assert
    tool_names = {t.name for t in tools}
    assert tool_names == {"sam_plan", "sam_task", "sam_active_task"}


def test_server_instructions_are_set() -> None:
    """Server exposes non-empty instructions to MCP clients.

    Tests: FastMCP instructions parameter is present.
    How: Inspect mcp.instructions directly (set at construction time).
    Why: Client discovery depends on instructions to route tool selection.
    """
    assert mcp.instructions
    assert len(mcp.instructions) > 20


# ---------------------------------------------------------------------------
# sam_task read via MCP protocol (replaces sam_read tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_read_existing_task_returns_task_assignment(plan_dir: Path) -> None:
    """sam_task read called via MCP returns TaskAssignment dict for existing task.

    Tests: sam_task read MCP protocol happy path.
    How: Call via Client.call_tool with config={"action": "read"}.
    Why: Verifies MCP schema validation and JSON round-trip — not just direct function call.
    """
    # Arrange
    plan_dir_str = str(plan_dir)

    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_task", {"plan": "P1", "task": "T1", "config": {"action": "read"}, "plan_dir": plan_dir_str}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert "task" in data
    assert data["task"]["id"] == "T1"
    assert data["task"]["status"] == "complete"


async def test_mcp_sam_read_plan_only_returns_plan_fields(plan_dir: Path) -> None:
    """sam_plan read without task param returns Plan fields via MCP protocol.

    Tests: sam_plan read plan-only path through MCP.
    How: Call sam_plan with config={"action": "read"} and plan param.
    Why: Validates optional parameter handling through the protocol layer.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "read"}, "plan": "P1", "plan_dir": str(plan_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert "feature" in data
    assert "task" not in data


async def test_mcp_sam_read_missing_task_returns_error_dict(plan_dir: Path) -> None:
    """sam_task read raises ToolError for a non-existent task via MCP protocol.

    Tests: sam_task read MCP error path.
    How: Request T99 which does not exist.
    Why: FastMCP converts unhandled TaskNotFoundError to isError=true, which
         the client surfaces as ToolError. The error message includes the task ID.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="T99"):
        async with Client(mcp) as client:
            await client.call_tool(
                "sam_task", {"plan": "P1", "task": "T99", "config": {"action": "read"}, "plan_dir": str(plan_dir)}
            )


# ---------------------------------------------------------------------------
# sam_task state via MCP protocol (replaces sam_state tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_state_transitions_task_status(plan_dir: Path) -> None:
    """sam_task state updates task status and returns updated fields via MCP.

    Tests: sam_task state MCP protocol happy path.
    How: Transition T2 to in-progress via call_tool with config={"action": "state", ...}.
    Why: Status mutation is the primary write operation in the workflow.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_task",
            {
                "plan": "P1",
                "task": "T2",
                "config": {"action": "state", "status": "in-progress"},
                "plan_dir": str(plan_dir),
            },
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["status"] == "in-progress"


async def test_mcp_sam_state_invalid_status_returns_error_dict(plan_dir: Path) -> None:
    """sam_task state raises ToolError for unrecognized status via MCP protocol.

    Tests: sam_task state input validation through MCP.
    How: Pass 'garbage-status' as the status value.
    Why: FastMCP converts unhandled TaskValidationError to isError=true, which
         the client surfaces as ToolError.
    """
    # Act / Assert
    with pytest.raises(ToolError):
        async with Client(mcp) as client:
            await client.call_tool(
                "sam_task",
                {
                    "plan": "P1",
                    "task": "T2",
                    "config": {"action": "state", "status": "garbage-status"},
                    "plan_dir": str(plan_dir),
                },
            )


# ---------------------------------------------------------------------------
# sam_plan ready via MCP protocol (replaces sam_ready tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_ready_returns_ready_tasks(plan_dir: Path) -> None:
    """sam_plan ready returns ready task list via MCP protocol.

    Tests: sam_plan ready MCP protocol happy path.
    How: T1 is complete, T2 depends on T1 — T2 should be ready.
    Why: Agents call sam_plan ready to find the next task to dispatch.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "ready"}, "plan": "P1", "plan_dir": str(plan_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["count"] == 1
    assert data["ready_tasks"][0]["id"] == "T2"


# ---------------------------------------------------------------------------
# sam_plan status via MCP protocol (replaces sam_status tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_status_returns_plan_summary(plan_dir: Path) -> None:
    """sam_plan status returns plan summary dict via MCP protocol.

    Tests: sam_plan status MCP protocol happy path.
    How: Call sam_plan status on two-task plan (T1 complete, T2 not-started).
    Why: Verifies all required summary fields survive JSON serialization.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "status"}, "plan": "P1", "plan_dir": str(plan_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["total_tasks"] == 2
    assert "by_status" in data
    assert "completion_pct" in data
    assert "has_cycles" in data
    assert data["has_cycles"] is False


# ---------------------------------------------------------------------------
# sam_plan create via MCP protocol (replaces sam_create tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_create_creates_plan_file(tmp_path: Path) -> None:
    """sam_plan create creates a plan file and returns metadata via MCP protocol.

    Tests: sam_plan create MCP protocol happy path.
    How: Pass valid tasks_yaml string via call_tool with config={"action": "create", ...}.
    Why: Verifies YAML string argument passes MCP serialization unchanged.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: MCP test task\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )

    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan",
            {
                "config": {
                    "action": "create",
                    "slug": "mcp-create",
                    "goal": "MCP create goal",
                    "tasks_yaml": tasks_yaml,
                },
                "plan_dir": str(p_dir),
            },
        )

    # Assert
    data = result.data
    import re

    assert isinstance(data, dict)
    assert "error" not in data
    assert data["task_count"] == 1
    assert re.match(r"^P[0-9a-f]{8}$", data["plan_id"]), f"Expected UUID plan_id, got: {data['plan_id']!r}"


# ---------------------------------------------------------------------------
# sam_task claim via MCP protocol (replaces sam_claim tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_claim_returns_claimed_true(tmp_path: Path) -> None:
    """sam_task claim transitions a not-started task to in-progress via MCP protocol.

    Tests: sam_task claim MCP protocol happy path.
    How: Create plan via sam_plan create, then sam_task claim T01 via call_tool.
    Why: Verifies claim guard and return shape through the full protocol path.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Claim test task\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )

    async with Client(mcp) as client:
        create_result = await client.call_tool(
            "sam_plan",
            {
                "config": {"action": "create", "slug": "claim-mcp", "goal": "Claim goal", "tasks_yaml": tasks_yaml},
                "plan_dir": str(p_dir),
            },
        )
        plan_id = create_result.data["plan_id"]

        # Act
        result = await client.call_tool(
            "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "claim"}, "plan_dir": str(p_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert data.get("claimed") is True
    assert data.get("task_id") == "T01"
    assert "started" in data


async def test_mcp_sam_claim_double_claim_returns_claimed_false(tmp_path: Path) -> None:
    """sam_task claim second call on in-progress task returns claimed=false via MCP.

    Tests: sam_task claim double-claim guard through MCP protocol.
    How: Claim T01 twice; second call must return claimed=false without raising.
    Why: Duplicate dispatch prevention must work through the real protocol path.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Double claim task\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )

    async with Client(mcp) as client:
        create_result = await client.call_tool(
            "sam_plan",
            {
                "config": {"action": "create", "slug": "double-claim-mcp", "goal": "Goal", "tasks_yaml": tasks_yaml},
                "plan_dir": str(p_dir),
            },
        )
        plan_addr = create_result.data["plan_id"]

        first = await client.call_tool(
            "sam_task", {"plan": plan_addr, "task": "T01", "config": {"action": "claim"}, "plan_dir": str(p_dir)}
        )
        assert first.data.get("claimed") is True

        # Act
        second = await client.call_tool(
            "sam_task", {"plan": plan_addr, "task": "T01", "config": {"action": "claim"}, "plan_dir": str(p_dir)}
        )

    # Assert
    assert second.data.get("claimed") is False
    assert "error" in second.data


# ---------------------------------------------------------------------------
# sam_plan update / sam_task update via MCP protocol (replaces sam_update tests)
# ---------------------------------------------------------------------------


async def test_mcp_sam_update_sets_context(tmp_path: Path) -> None:
    """sam_plan update sets plan context field via MCP protocol.

    Tests: sam_plan update context path through MCP.
    How: Create plan, call sam_plan update with context, verify via sam_task read.
    Why: Confirms string fields survive MCP JSON round-trip intact.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Update test\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )

    async with Client(mcp) as client:
        create_result = await client.call_tool(
            "sam_plan",
            {
                "config": {"action": "create", "slug": "update-mcp", "goal": "Update goal", "tasks_yaml": tasks_yaml},
                "plan_dir": str(p_dir),
            },
        )
        plan_addr = create_result.data["plan_id"]

        # Act
        update_result = await client.call_tool(
            "sam_plan",
            {"config": {"action": "update", "context": "MCP context text."}, "plan": plan_addr, "plan_dir": str(p_dir)},
        )

        # Verify via sam_task read
        read_result = await client.call_tool(
            "sam_task", {"plan": plan_addr, "task": "T01", "config": {"action": "read"}, "plan_dir": str(p_dir)}
        )

    # Assert
    assert update_result.data.get("updated") is True
    assert read_result.data.get("plan-context") == "MCP context text."


# ---------------------------------------------------------------------------
# sam_plan list via MCP protocol (replaces sam_list tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def multi_plan_dir(tmp_path: Path) -> Path:
    """Write three plan files in a plan directory and return its path.

    Directory layout::

        tmp_path/
        └── plan/
            ├── tasks-1-alpha-feature.yaml   (goal: "Implement alpha")
            ├── tasks-2-beta-feature.yaml    (goal: "Implement beta")
            └── tasks-3-gamma-search.yaml    (goal: "Search integration")

    Returns:
        Path to the plan directory (``tmp_path/plan``).
    """
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    for plan_num, feature, goal in [
        (1, "alpha-feature", "Implement alpha"),
        (2, "beta-feature", "Implement beta"),
        (3, "gamma-search", "Search integration"),
    ]:
        tasks = [make_task("T1")]
        plan = Plan(feature=feature, version="1.0", goal=goal, tasks=tasks)
        write_plan(plan, p_dir / f"tasks-{plan_num}-{feature}.yaml", force_single=True)

    return p_dir


async def test_sam_list_returns_all_plans_with_response_shape(multi_plan_dir: Path) -> None:
    """sam_plan list returns all plans with expected response keys via MCP protocol.

    Tests: sam_plan list happy path — no filters, no explicit limit.
    How: Call sam_plan with config={"action": "list"}; verify shape and count.
    Why: Confirms tool registration, return shape, and pagination object presence.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_plan", {"config": {"action": "list"}, "plan_dir": str(multi_plan_dir)})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "errors" not in data or data["errors"] == []
    assert "items" in data
    assert "count" in data
    assert "pagination" in data
    assert "messages" in data
    assert "warnings" in data
    assert data["count"] == 3
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["has_more"] is False
    assert data["pagination"]["offset"] == 0


async def test_sam_list_search_filters_by_feature_substring(multi_plan_dir: Path) -> None:
    """sam_plan list search parameter filters plans by feature name substring.

    Tests: search across feature field (case-insensitive).
    How: Pass search="alpha"; only alpha-feature plan should match.
    Why: Core search requirement — single field match.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "search": "alpha"}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == "alpha-feature"
    assert data["pagination"]["total"] == 1


async def test_sam_list_search_filters_by_goal_substring(multi_plan_dir: Path) -> None:
    """sam_plan list search parameter filters plans by goal substring.

    Tests: search across goal field (case-insensitive).
    How: Pass search="search"; only gamma-search plan (goal="Search integration") matches.
    Why: Confirms multi-field search includes goal.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "search": "search"}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == "gamma-search"


async def test_sam_list_search_case_insensitive(multi_plan_dir: Path) -> None:
    """sam_plan list search is case-insensitive.

    Tests: uppercase search term matches lowercase field values.
    How: Pass search="BETA"; beta-feature plan should match.
    Why: Case-insensitive matching is a stated requirement.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "search": "BETA"}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == "beta-feature"


async def test_sam_list_search_no_match_returns_empty_items(multi_plan_dir: Path) -> None:
    """sam_plan list search with no matches returns empty items list with total=0.

    Tests: sam_plan list search zero-results path.
    How: Pass search="zzznotfound"; no plan should match.
    Why: Callers must handle empty results without errors.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "search": "zzznotfound"}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = result.data
    assert data["count"] == 0
    assert data["items"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


async def test_sam_list_offset_and_limit_returns_correct_page(multi_plan_dir: Path) -> None:
    """sam_plan list offset and limit return the requested page of results.

    Tests: explicit pagination — offset=1, limit=1 returns second item only.
    How: Call with offset=1, limit=1 on three-plan directory.
    Why: Callers must be able to page through results deterministically.
    """
    # Arrange — get all items first to know sort order
    async with Client(mcp) as client:
        all_result = await client.call_tool("sam_plan", {"config": {"action": "list"}, "plan_dir": str(multi_plan_dir)})
        all_features = [item["feature"] for item in all_result.data["items"]]

        # Act — page 2 (offset=1, limit=1)
        page_result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "offset": 1, "limit": 1}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = page_result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == all_features[1]
    assert data["pagination"]["offset"] == 1
    assert data["pagination"]["limit"] == 1
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["has_more"] is True
    assert "next_call" in data


async def test_sam_list_has_more_true_includes_next_call_hint(multi_plan_dir: Path) -> None:
    """sam_plan list includes next_call hint when has_more is true.

    Tests: next_call field present and non-empty when pagination continues.
    How: Request limit=1 on three-plan directory — must have more.
    Why: Callers use next_call to construct the follow-up request.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list", "limit": 1}, "plan_dir": str(multi_plan_dir)}
        )

    # Assert
    data = result.data
    assert data["pagination"]["has_more"] is True
    assert "next_call" in data
    assert "sam_plan" in data["next_call"]
    assert "offset=1" in data["next_call"]


async def test_sam_list_nonexistent_plan_dir_returns_error(tmp_path: Path) -> None:
    """sam_plan list with non-existent plan_dir returns an empty result, not a raise.

    Tests: sam_plan list error path for missing directory.
    How: Pass plan_dir pointing to a path that does not exist.
    Why: LocalYamlTaskProvider.list_plans returns [] when plan_dir does not exist.
         sam_plan list wraps this as an empty paginated response with count=0.
         No errors are added because the backend treats a missing dir as empty.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_plan", {"config": {"action": "list"}, "plan_dir": str(tmp_path / "nonexistent")}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert data["count"] == 0
    assert data["items"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


async def test_sam_list_items_include_required_summary_fields(multi_plan_dir: Path) -> None:
    """sam_plan list items contain feature, goal, description, task_count, and path.

    Tests: item shape completeness.
    How: Call sam_plan list with no filters, inspect first item keys.
    Why: Callers depend on these fields to route plan selection decisions.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_plan", {"config": {"action": "list"}, "plan_dir": str(multi_plan_dir)})

    # Assert
    item = result.data["items"][0]
    assert "feature" in item
    assert "goal" in item
    assert "description" in item
    assert "task_count" in item
    assert item["task_count"] == 1


async def test_sam_list_items_include_plan_ref(multi_plan_dir: Path) -> None:
    """sam_plan list items include plan_ref with correct P-format when no issue is set.

    Tests: plan_ref field in list response — global composite identifier (PR #1725).
    How: Call sam_plan list; verify each item has plan_ref matching 'P<digits>' pattern.
    Why: Callers need plan_ref to construct globally unique plan addresses without issue scope.
    """
    import re

    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_plan", {"config": {"action": "list"}, "plan_dir": str(multi_plan_dir)})

    # Assert — all items have plan_ref present and matching P-format (no issue in fixture)
    # Plans in this fixture used tasks-{N}-{slug} naming (legacy format), so plan_id is the
    # filename stem's P-prefix portion. Legacy files expose their plan_id from the file stem.
    items = result.data["items"]
    assert len(items) > 0
    for item in items:
        assert "plan_ref" in item
        plan_ref = item["plan_ref"]
        assert plan_ref is not None
        assert re.match(r"^P[0-9a-f\d]+", plan_ref), f"Expected P-format plan_ref, got: {plan_ref!r}"
