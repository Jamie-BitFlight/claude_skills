"""In-memory MCP protocol tests for sam_schema.server.

Tests each tool through the real FastMCP in-memory transport — the same protocol
path that Claude Code agents use. Verifies MCP schema validation, serialization,
and tool dispatch rather than calling tool functions directly.

Uses Client(mcp) per FastMCP v3 testing.md primary test pattern.
asyncio_mode = "auto" is set in pyproject.toml — no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastmcp.client import Client
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.server import mcp
from sam_schema.writers.yaml_writer import write_plan

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_task(task_id: str, status: TaskStatus = TaskStatus.NOT_STARTED, dependencies: list[str] | None = None) -> Task:
    """Return a minimal Task for test use."""
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=status,
        dependencies=dependencies or [],
        priority=Priority.MEDIUM,
        complexity=Complexity.MEDIUM,
    )


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
    """Server exposes exactly the seven documented tools via the MCP protocol.

    Tests: tool registration completeness through the MCP protocol.
    How: Call list_tools() via in-memory Client.
    Why: Catches decorator or import errors that would remove a tool silently.
    """
    # Arrange + Act
    async with Client(mcp) as client:
        tools = await client.list_tools()

    # Assert
    tool_names = {t.name for t in tools}
    assert tool_names == {"sam_read", "sam_state", "sam_ready", "sam_status", "sam_create", "sam_update", "sam_claim"}


def test_server_instructions_are_set() -> None:
    """Server exposes non-empty instructions to MCP clients.

    Tests: FastMCP instructions parameter is present.
    How: Inspect mcp.instructions directly (set at construction time).
    Why: Client discovery depends on instructions to route tool selection.
    """
    assert mcp.instructions
    assert len(mcp.instructions) > 20


# ---------------------------------------------------------------------------
# sam_read via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_read_existing_task_returns_task_assignment(plan_dir: Path) -> None:
    """sam_read called via MCP returns TaskAssignment dict for existing task.

    Tests: sam_read MCP protocol happy path.
    How: Call via Client.call_tool with serialized string arguments.
    Why: Verifies MCP schema validation and JSON round-trip — not just direct function call.
    """
    # Arrange
    plan_dir_str = str(plan_dir)

    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_read", {"plan": "P1", "task": "T1", "plan_dir": plan_dir_str})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert "task" in data
    assert data["task"]["id"] == "T1"
    assert data["task"]["status"] == "complete"


async def test_mcp_sam_read_plan_only_returns_plan_fields(plan_dir: Path) -> None:
    """sam_read without task param returns Plan fields via MCP protocol.

    Tests: sam_read plan-only path through MCP.
    How: Omit task parameter in call_tool arguments.
    Why: Validates optional parameter handling through the protocol layer.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_read", {"plan": "P1", "plan_dir": str(plan_dir)})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert "feature" in data
    assert "task" not in data


async def test_mcp_sam_read_missing_task_returns_error_dict(plan_dir: Path) -> None:
    """sam_read returns error dict for a non-existent task via MCP protocol.

    Tests: sam_read MCP error path — tool does not raise, returns dict.
    How: Request T99 which does not exist.
    Why: MCP clients receive error dicts, not protocol-level exceptions.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_read", {"plan": "P1", "task": "T99", "plan_dir": str(plan_dir)})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" in data


# ---------------------------------------------------------------------------
# sam_state via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_state_transitions_task_status(plan_dir: Path) -> None:
    """sam_state updates task status and returns updated fields via MCP.

    Tests: sam_state MCP protocol happy path.
    How: Transition T2 to in-progress via call_tool.
    Why: Status mutation is the primary write operation in the workflow.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_state", {"plan": "P1", "task": "T2", "status": "in-progress", "plan_dir": str(plan_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["status"] == "in-progress"


async def test_mcp_sam_state_invalid_status_returns_error_dict(plan_dir: Path) -> None:
    """sam_state returns error dict for unrecognized status via MCP protocol.

    Tests: sam_state input validation through MCP.
    How: Pass 'garbage-status' as the status value.
    Why: Protocol-level call confirms tool handles bad input without raising.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool(
            "sam_state", {"plan": "P1", "task": "T2", "status": "garbage-status", "plan_dir": str(plan_dir)}
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" in data


# ---------------------------------------------------------------------------
# sam_ready via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_ready_returns_ready_tasks(plan_dir: Path) -> None:
    """sam_ready returns ready task list via MCP protocol.

    Tests: sam_ready MCP protocol happy path.
    How: T1 is complete, T2 depends on T1 — T2 should be ready.
    Why: Agents call sam_ready to find the next task to dispatch.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_ready", {"plan": "P1", "plan_dir": str(plan_dir)})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["count"] == 1
    assert data["ready_tasks"][0]["id"] == "T2"


# ---------------------------------------------------------------------------
# sam_status via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_status_returns_plan_summary(plan_dir: Path) -> None:
    """sam_status returns plan summary dict via MCP protocol.

    Tests: sam_status MCP protocol happy path.
    How: Call sam_status on two-task plan (T1 complete, T2 not-started).
    Why: Verifies all required summary fields survive JSON serialization.
    """
    # Act
    async with Client(mcp) as client:
        result = await client.call_tool("sam_status", {"plan": "P1", "plan_dir": str(plan_dir)})

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
# sam_create via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_create_creates_plan_file(tmp_path: Path) -> None:
    """sam_create creates a plan file and returns metadata via MCP protocol.

    Tests: sam_create MCP protocol happy path.
    How: Pass valid tasks_yaml string via call_tool.
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
            "sam_create",
            {"slug": "mcp-create", "goal": "MCP create goal", "tasks_yaml": tasks_yaml, "plan_dir": str(p_dir)},
        )

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert "error" not in data
    assert data["task_count"] == 1
    assert data["plan_number"] == 1


# ---------------------------------------------------------------------------
# sam_claim via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_claim_returns_claimed_true(tmp_path: Path) -> None:
    """sam_claim transitions a not-started task to in-progress via MCP protocol.

    Tests: sam_claim MCP protocol happy path.
    How: Create plan via sam_create, then sam_claim T01 via call_tool.
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
            "sam_create", {"slug": "claim-mcp", "goal": "Claim goal", "tasks_yaml": tasks_yaml, "plan_dir": str(p_dir)}
        )
        plan_number = create_result.data["plan_number"]

        # Act
        result = await client.call_tool("sam_claim", {"plan": f"P{plan_number}", "task": "T01", "plan_dir": str(p_dir)})

    # Assert
    data = result.data
    assert isinstance(data, dict)
    assert data.get("claimed") is True
    assert data.get("task_id") == "T01"
    assert "started" in data


async def test_mcp_sam_claim_double_claim_returns_claimed_false(tmp_path: Path) -> None:
    """sam_claim second call on in-progress task returns claimed=false via MCP.

    Tests: sam_claim double-claim guard through MCP protocol.
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
            "sam_create", {"slug": "double-claim-mcp", "goal": "Goal", "tasks_yaml": tasks_yaml, "plan_dir": str(p_dir)}
        )
        plan_number = create_result.data["plan_number"]
        plan_addr = f"P{plan_number}"

        first = await client.call_tool("sam_claim", {"plan": plan_addr, "task": "T01", "plan_dir": str(p_dir)})
        assert first.data.get("claimed") is True

        # Act
        second = await client.call_tool("sam_claim", {"plan": plan_addr, "task": "T01", "plan_dir": str(p_dir)})

    # Assert
    assert second.data.get("claimed") is False
    assert "error" in second.data


# ---------------------------------------------------------------------------
# sam_update via MCP protocol
# ---------------------------------------------------------------------------


async def test_mcp_sam_update_sets_context(tmp_path: Path) -> None:
    """sam_update sets plan context field via MCP protocol.

    Tests: sam_update context path through MCP.
    How: Create plan, call sam_update with context, verify via sam_read.
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
            "sam_create",
            {"slug": "update-mcp", "goal": "Update goal", "tasks_yaml": tasks_yaml, "plan_dir": str(p_dir)},
        )
        plan_number = create_result.data["plan_number"]
        plan_addr = f"P{plan_number}"

        # Act
        update_result = await client.call_tool(
            "sam_update", {"address": plan_addr, "plan_dir": str(p_dir), "context": "MCP context text."}
        )

        # Verify via sam_read
        read_result = await client.call_tool("sam_read", {"plan": plan_addr, "task": "T01", "plan_dir": str(p_dir)})

    # Assert
    assert update_result.data.get("updated") is True
    assert read_result.data.get("plan-context") == "MCP context text."
