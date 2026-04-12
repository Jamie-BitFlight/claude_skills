"""MCP-layer tests for the 3 consolidated SAM tools.

Covers sam_task, sam_plan, and sam_active_task through the FastMCP in-memory
transport against InMemoryTaskProvider and InMemoryContextBackend.  No
filesystem I/O — all state lives in memory for the duration of each test.

asyncio_mode = "auto" is set in pyproject.toml — no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend
from sam_schema.core.context_config import ContextConfig, reset_context_config, set_context_config
from sam_schema.core.task_config import TaskConfig, set_task_config
from sam_schema.server import mcp

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# YAML for sam_plan(action="create") tests — uses "id:" key for InMemoryTaskProvider.
_TWO_TASK_YAML = (
    "tasks:\n"
    "  - id: T01\n"
    "    title: First task\n"
    "    status: not-started\n"
    "    agent: test-agent\n"
    "    dependencies: []\n"
    "    priority: 1\n"
    "    complexity: low\n"
    "  - id: T02\n"
    "    title: Second task\n"
    "    status: not-started\n"
    "    agent: test-agent\n"
    "    dependencies: [T01]\n"
    "    priority: 2\n"
    "    complexity: medium\n"
)

_SINGLE_TASK_YAML = (
    "tasks:\n"
    "  - id: T01\n"
    "    title: Only task\n"
    "    status: not-started\n"
    "    agent: test-agent\n"
    "    dependencies: []\n"
    "    priority: 1\n"
    "    complexity: low\n"
)


from tests_sam.conftest import make_task_def as _task_def

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_backend() -> InMemoryTaskProvider:
    """Fresh in-memory task backend — function scope, no filesystem."""
    return InMemoryTaskProvider()


@pytest.fixture
def ctx_backend() -> InMemoryContextBackend:
    """Fresh in-memory context backend — function scope, no filesystem."""
    return InMemoryContextBackend()


@pytest.fixture(autouse=True)
def configured_backends(
    task_backend: InMemoryTaskProvider, ctx_backend: InMemoryContextBackend
) -> Generator[None, None, None]:
    """Inject memory backends into the module-level singletons.

    Runs before every test in this module (autouse=True, function scope).
    Teardown resets context config and replaces task config with a fresh
    memory backend to prevent state leakage if a test fails mid-execution.
    """
    set_task_config(TaskConfig(backend=task_backend))
    set_context_config(ContextConfig(backend=ctx_backend))
    yield
    reset_context_config()
    # Replace task config with a fresh empty backend so any test that leaks
    # state into the module-level singleton cannot affect downstream modules.
    set_task_config(TaskConfig(backend=InMemoryTaskProvider()))


@pytest.fixture
async def client() -> AsyncGenerator[Client, None]:
    """In-memory MCP client connected to the configured SAM server."""
    async with Client(mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Server metadata
# ---------------------------------------------------------------------------


async def test_server_exposes_consolidated_tools(client: Client) -> None:
    """Server registers the 3 consolidated tools via the MCP protocol.

    Tests: Tool registration completeness.
    How: Call list_tools() via in-memory Client; check for new tool names.
    Why: Catches decorator or import errors that silently drop a tool.
    """
    # Arrange + Act
    tools = await client.list_tools()

    # Assert
    tool_names = {t.name for t in tools}
    assert "sam_task" in tool_names
    assert "sam_plan" in tool_names
    assert "sam_active_task" in tool_names


# ===========================================================================
# sam_task — action=read
# ===========================================================================


async def test_sam_task_read_returns_task_assignment(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=read returns a TaskAssignment dict with plan context and task fields.

    Tests: sam_task read happy path through the MCP protocol.
    How: Create a plan directly on the memory backend; call sam_task read.
    Why: Verifies MCP schema validation and JSON round-trip of a nested TaskAssignment.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}})

    # Assert
    data = result.data
    assert "task" in data
    assert data["task"]["id"] == "T01"
    assert data["task"]["status"] == "not-started"
    assert "error" not in data


async def test_sam_task_read_missing_task_raises_tool_error(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=read raises ToolError for a nonexistent task ID.

    Tests: sam_task read error path.
    How: Request T99 which does not exist in a plan that does.
    Why: FastMCP converts unhandled TaskNotFoundError to ToolError.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act / Assert
    with pytest.raises(ToolError, match="T99"):
        await client.call_tool("sam_task", {"plan": plan_id, "task": "T99", "config": {"action": "read"}})


async def test_sam_task_read_missing_plan_raises_tool_error(client: Client) -> None:
    """sam_task action=read raises ToolError for a nonexistent plan address.

    Tests: sam_task read error path when the plan itself is absent.
    How: Request P99 against an empty backend.
    Why: Verifies PlanNotFoundError surfaces as ToolError through MCP.
    """
    # Arrange — backend is empty (no plans created)

    # Act / Assert
    with pytest.raises(ToolError):
        await client.call_tool("sam_task", {"plan": "P99", "task": "T01", "config": {"action": "read"}})


# ===========================================================================
# sam_task — action=claim
# ===========================================================================


async def test_sam_task_claim_transitions_to_in_progress(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=claim returns claimed=true and task_id for a not-started task.

    Tests: sam_task claim happy path.
    How: Create plan with not-started T01; claim it via MCP.
    Why: Claim is the primary write operation that prevents duplicate dispatch.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "claim"}})

    # Assert
    data = result.data
    assert data["claimed"] is True
    assert data["task_id"] == "T01"
    assert "started" in data


async def test_sam_task_claim_double_claim_returns_claimed_false(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_task action=claim second call on in-progress task returns claimed=false.

    Tests: sam_task claim double-claim guard.
    How: Claim T01 twice; second call must return claimed=false without raising.
    Why: Duplicate dispatch prevention must work through the MCP protocol.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]
    await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "claim"}})

    # Act
    result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "claim"}})

    # Assert
    data = result.data
    assert data["claimed"] is False
    assert "error" in data
    assert "in-progress" in data["error"]


async def test_sam_task_claim_complete_task_returns_claimed_false(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_task action=claim returns claimed=false for a task already in a terminal state.

    Tests: sam_task claim guard against terminal-status tasks.
    How: Create plan with T01 pre-set to complete; attempt claim.
    Why: Completed tasks must not be re-claimed — confirms guard fires for all non-not-started states.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def(status="complete")])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "claim"}})

    # Assert
    assert result.data["claimed"] is False
    assert "complete" in result.data["error"]


# ===========================================================================
# sam_task — action=state
# ===========================================================================


async def test_sam_task_state_updates_task_status(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=state transitions task to the requested status.

    Tests: sam_task state happy path.
    How: Create plan; transition T01 to in-progress via state action.
    Why: Status mutation is the primary write operation in the task workflow.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool(
        "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "state", "status": "in-progress"}}
    )

    # Assert
    data = result.data
    assert data["id"] == "T01"
    assert data["status"] == "in-progress"


async def test_sam_task_state_complete_sets_status(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=state accepts 'complete' as a valid status.

    Tests: sam_task state with terminal status value.
    How: Transition T01 directly to complete.
    Why: Agents use state to mark tasks done after verification steps pass.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool(
        "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "state", "status": "complete"}}
    )

    # Assert
    assert result.data["status"] == "complete"


async def test_sam_task_state_invalid_status_raises_tool_error(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_task action=state raises ToolError for an unrecognised status string.

    Tests: sam_task state input validation.
    How: Pass 'not-a-valid-status' which is not in _VALID_STATUSES.
    Why: FastMCP converts unhandled TaskValidationError to ToolError.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act / Assert
    with pytest.raises(ToolError):
        await client.call_tool(
            "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "state", "status": "not-a-valid-status"}}
        )


# ===========================================================================
# sam_task — action=update
# ===========================================================================


async def test_sam_task_update_set_fields_patches_task(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_task action=update with set_fields_json patches the named task fields.

    Tests: sam_task update set_fields_json path.
    How: Create plan; patch title via set_fields_json; re-read to verify.
    Why: Agents patch task fields mid-execution to record divergence notes.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool(
        "sam_task",
        {
            "plan": plan_id,
            "task": "T01",
            "config": {"action": "update", "set_fields_json": '{"title": "Updated title"}'},
        },
    )

    # Assert
    assert result.data["updated"] is True
    assert result.data["address"] == f"{plan_id}/T01"

    # Verify the change persisted (round-trip)
    read_result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}})
    assert read_result.data["task"]["title"] == "Updated title"


async def test_sam_task_update_append_section_stores_content(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_task action=update with append_section adds a named section to context_notes.

    Tests: sam_task update append_section path.
    How: Append a section; verify updated=true is returned.
    Why: start-task skill appends progress sections to task bodies during execution.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool(
        "sam_task",
        {
            "plan": plan_id,
            "task": "T01",
            "config": {"action": "update", "append_section": "Progress Notes", "section_content": "Work in progress."},
        },
    )

    # Assert
    assert result.data["updated"] is True
    assert result.data["address"] == f"{plan_id}/T01"


async def test_sam_task_update_invalid_json_raises_tool_error(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_task action=update raises ToolError when set_fields_json is not valid JSON.

    Tests: sam_task update input validation for malformed JSON.
    How: Pass 'not-json' as set_fields_json.
    Why: json.loads raises ValueError which FastMCP wraps as ToolError.
    """
    # Arrange
    plan_data = task_backend.create_plan("test-plan", "Test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act / Assert
    with pytest.raises(ToolError):
        await client.call_tool(
            "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "update", "set_fields_json": "not-json"}}
        )


# ===========================================================================
# sam_plan — action=create
# ===========================================================================


async def test_sam_plan_create_returns_plan_number_and_task_count(client: Client) -> None:
    """sam_plan action=create returns plan_id and task_count on success.

    Tests: sam_plan create happy path.
    How: Pass two-task YAML string; verify the return shape.
    Why: plan_id is used by subsequent tool calls; task_count confirms parsing.
    """
    import re

    # Act
    result = await client.call_tool(
        "sam_plan",
        {"config": {"action": "create", "slug": "new-plan", "goal": "Build something", "tasks_yaml": _TWO_TASK_YAML}},
    )

    # Assert
    data = result.data
    assert re.match(r"^P[0-9a-f]{8}$", data["plan_id"]), f"Expected UUID plan_id, got: {data['plan_id']!r}"
    assert data["task_count"] == 2


async def test_sam_plan_create_sets_plan_goal(client: Client) -> None:
    """sam_plan action=create stores the goal and makes it readable via plan read.

    Tests: sam_plan create → read round-trip for the goal field.
    How: Create plan with known goal; read back and verify goal field.
    Why: Goal field drives agent decision-making in the task-worker.
    """
    # Act
    create_result = await client.call_tool(
        "sam_plan",
        {
            "config": {
                "action": "create",
                "slug": "goal-plan",
                "goal": "Specific goal string",
                "tasks_yaml": _SINGLE_TASK_YAML,
            }
        },
    )
    plan_id = create_result.data["plan_id"]

    read_result = await client.call_tool("sam_plan", {"config": {"action": "read"}, "plan": plan_id})

    # Assert
    assert read_result.data.get("goal") == "Specific goal string"


async def test_sam_plan_create_invalid_yaml_raises_tool_error(client: Client) -> None:
    """sam_plan action=create raises ToolError when tasks_yaml lacks a 'tasks' key.

    Tests: sam_plan create YAML validation.
    How: Pass YAML with no 'tasks' top-level key.
    Why: The server validates the parsed YAML structure before calling the backend.
    """
    # Act / Assert
    with pytest.raises(ToolError):
        await client.call_tool(
            "sam_plan",
            {
                "config": {
                    "action": "create",
                    "slug": "bad",
                    "goal": "Bad plan",
                    "tasks_yaml": "not_tasks: true\nother: value",
                }
            },
        )


# ===========================================================================
# sam_plan — action=read
# ===========================================================================


async def test_sam_plan_read_returns_plan_fields(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_plan action=read returns Plan model fields for an existing plan.

    Tests: sam_plan read happy path.
    How: Create plan directly on backend; read via MCP.
    Why: Plan read is used by orchestrators to load goal/context before dispatch.
    """
    # Arrange
    plan_data = task_backend.create_plan("read-plan", "Read test goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "read"}, "plan": plan_id})

    # Assert
    data = result.data
    assert data["feature"] == "read-plan"
    assert "task" not in data  # plan-only read, no nested task object


async def test_sam_plan_read_missing_plan_raises_tool_error(client: Client) -> None:
    """sam_plan action=read raises ToolError for a nonexistent plan address.

    Tests: sam_plan read error path.
    How: Request P999 against an empty backend.
    Why: PlanNotFoundError must surface as ToolError through MCP.
    """
    # Arrange — backend is empty

    # Act / Assert
    with pytest.raises(ToolError):
        await client.call_tool("sam_plan", {"config": {"action": "read"}, "plan": "P999"})


async def test_sam_plan_read_without_plan_param_raises_tool_error(client: Client) -> None:
    """sam_plan action=read raises ToolError when the 'plan' parameter is omitted.

    Tests: sam_plan required-param validation for read action.
    How: Omit 'plan' parameter entirely.
    Why: Server must reject required-param absence with a descriptive error message.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="requires the 'plan' parameter"):
        await client.call_tool("sam_plan", {"config": {"action": "read"}})


# ===========================================================================
# sam_plan — action=list
# ===========================================================================


async def test_sam_plan_list_empty_backend_returns_zero_items(client: Client) -> None:
    """sam_plan action=list returns empty items list when no plans exist.

    Tests: sam_plan list zero-results path.
    How: Call list on an empty backend.
    Why: Callers must handle empty results without errors.
    """
    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "list"}})

    # Assert
    data = result.data
    assert data["count"] == 0
    assert data["items"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["has_more"] is False


async def test_sam_plan_list_returns_all_plans_with_summary_fields(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_plan action=list returns all plans with required summary fields.

    Tests: sam_plan list happy path and item shape.
    How: Create two plans; call list; check count, features, and item keys.
    Why: Orchestrators depend on list to find plans for dispatch.
    """
    # Arrange
    task_backend.create_plan("alpha", "Alpha goal", [_task_def("T01")])
    task_backend.create_plan("beta", "Beta goal", [_task_def("T01")])

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "list"}})

    # Assert
    data = result.data
    assert data["count"] == 2
    assert data["pagination"]["total"] == 2
    features = {item["feature"] for item in data["items"]}
    assert features == {"alpha", "beta"}
    item = data["items"][0]
    assert "feature" in item
    assert "goal" in item
    assert "task_count" in item


async def test_sam_plan_list_search_filters_by_feature_substring(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_plan action=list with search filters plans by feature name substring.

    Tests: sam_plan list search path.
    How: Create two plans; search for 'alpha'; expect only alpha-feature to match.
    Why: Search is how orchestrators locate the right plan by name.
    """
    # Arrange
    task_backend.create_plan("alpha-feature", "Do alpha work", [_task_def("T01")])
    task_backend.create_plan("beta-feature", "Do beta work", [_task_def("T01")])

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "list", "search": "alpha"}})

    # Assert
    data = result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == "alpha-feature"


async def test_sam_plan_list_pagination_offset_and_limit(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_plan action=list with offset and limit returns the correct page of results.

    Tests: sam_plan list explicit pagination.
    How: Create 3 plans; request page 2 (offset=1, limit=1); verify next_call hint.
    Why: Token-budget pagination must work through the MCP protocol.
    """
    # Arrange
    task_backend.create_plan("first", "First goal", [_task_def("T01")])
    task_backend.create_plan("second", "Second goal", [_task_def("T01")])
    task_backend.create_plan("third", "Third goal", [_task_def("T01")])

    # Get all to determine insertion order
    all_result = await client.call_tool("sam_plan", {"config": {"action": "list"}})
    all_features = [item["feature"] for item in all_result.data["items"]]

    # Act — page 2
    page_result = await client.call_tool("sam_plan", {"config": {"action": "list", "offset": 1, "limit": 1}})

    # Assert
    data = page_result.data
    assert data["count"] == 1
    assert data["items"][0]["feature"] == all_features[1]
    assert data["pagination"]["has_more"] is True
    assert "next_call" in data


# ===========================================================================
# sam_plan — action=status
# ===========================================================================


async def test_sam_plan_status_returns_progress_summary(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_plan action=status returns a task count summary including completion_pct.

    Tests: sam_plan status happy path.
    How: Create plan with 1 complete + 1 not-started task; check summary fields.
    Why: Orchestrators use status to decide when to close a plan.
    """
    # Arrange
    plan_data = task_backend.create_plan(
        "progress-plan", "Progress goal", [_task_def("T01", status="complete"), _task_def("T02")]
    )
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "status"}, "plan": plan_id})

    # Assert
    data = result.data
    assert data["total_tasks"] == 2
    assert "by_status" in data
    assert "completion_pct" in data
    assert data["has_cycles"] is False
    assert data["completion_pct"] == pytest.approx(50.0)


async def test_sam_plan_status_missing_plan_raises_tool_error(client: Client) -> None:
    """sam_plan action=status raises ToolError when the 'plan' parameter is omitted.

    Tests: sam_plan required-param validation for status action.
    How: Omit 'plan' parameter.
    Why: Consistent error message for missing required params across all plan actions.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="requires the 'plan' parameter"):
        await client.call_tool("sam_plan", {"config": {"action": "status"}})


# ===========================================================================
# sam_plan — action=ready
# ===========================================================================


async def test_sam_plan_ready_returns_tasks_with_satisfied_deps(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_plan action=ready returns tasks whose dependencies are all in terminal status.

    Tests: sam_plan ready happy path.
    How: T01 complete, T02 depends on T01 — T02 should appear in ready list.
    Why: Orchestrators call ready to discover which tasks can be dispatched next.
    """
    # Arrange
    plan_data = task_backend.create_plan(
        "ready-plan", "Ready goal", [_task_def("T01", status="complete"), _task_def("T02", deps=["T01"])]
    )
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "ready"}, "plan": plan_id})

    # Assert
    data = result.data
    assert data["count"] == 1
    assert data["ready_tasks"][0]["id"] == "T02"


async def test_sam_plan_ready_full_returns_complete_task_fields(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_plan action=ready with full=True returns the complete Task model dump.

    Tests: sam_plan ready full=True path.
    How: Create plan with one ready task; call ready with full=True.
    Why: full=True is needed when agents require all task fields, not just the 7-field manifest.
    """
    # Arrange
    plan_data = task_backend.create_plan("full-plan", "Full goal", [_task_def("T01")])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool("sam_plan", {"config": {"action": "ready", "full": True}, "plan": plan_id})

    # Assert
    data = result.data
    assert data["count"] == 1
    task = data["ready_tasks"][0]
    # Full model contains more than the compact 7-field manifest
    assert "id" in task
    assert "title" in task
    assert "status" in task
    assert "dependencies" in task


async def test_sam_plan_ready_missing_plan_raises_tool_error(client: Client) -> None:
    """sam_plan action=ready raises ToolError when the 'plan' parameter is omitted.

    Tests: sam_plan required-param validation for ready action.
    How: Omit 'plan' parameter.
    Why: Consistent server-side required-param enforcement across all plan actions.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="requires the 'plan' parameter"):
        await client.call_tool("sam_plan", {"config": {"action": "ready"}})


# ===========================================================================
# sam_plan — action=update
# ===========================================================================


async def test_sam_plan_update_sets_context_field(client: Client, task_backend: InMemoryTaskProvider) -> None:
    """sam_plan action=update sets the plan-level context field.

    Tests: sam_plan update context path.
    How: Create plan; set context via update; verify updated=true.
    Why: Context is set by the context-gathering agent after discovery.
    """
    # Arrange
    plan_data = task_backend.create_plan("update-plan", "Update goal", [_task_def()])
    plan_id = plan_data["plan_id"]

    # Act
    result = await client.call_tool(
        "sam_plan", {"config": {"action": "update", "context": "New context text"}, "plan": plan_id}
    )

    # Assert
    assert result.data["updated"] is True
    assert result.data["address"] == plan_id


async def test_sam_plan_update_missing_plan_raises_tool_error(client: Client) -> None:
    """sam_plan action=update raises ToolError when the 'plan' parameter is omitted.

    Tests: sam_plan required-param validation for update action.
    How: Omit 'plan' parameter.
    Why: Server must reject plan-mutating operations without a plan address.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="requires the 'plan' parameter"):
        await client.call_tool("sam_plan", {"config": {"action": "update", "context": "ctx"}})


# ===========================================================================
# sam_active_task — action=get
# ===========================================================================


async def test_sam_active_task_get_returns_null_when_not_set(client: Client) -> None:
    """sam_active_task action=get returns active_task=null when no context is stored.

    Tests: sam_active_task get empty state.
    How: Call get with no prior set on a fresh context backend.
    Why: Agents must handle the null case without an error before calling set.
    """
    # Act
    result = await client.call_tool("sam_active_task", {"config": {"action": "get"}})

    # Assert
    assert result.data["active_task"] is None


# ===========================================================================
# sam_active_task — action=set
# ===========================================================================


async def test_sam_active_task_set_stores_plan_and_task(client: Client) -> None:
    """sam_active_task action=set stores the plan/task address and returns the context.

    Tests: sam_active_task set happy path.
    How: Set plan=P1, task=T01; verify the returned context contains task_id.
    Why: set is the primary write operation for session-to-task binding.
    """
    # Act
    result = await client.call_tool("sam_active_task", {"config": {"action": "set", "plan": "P1", "task": "T01"}})

    # Assert
    data = result.data
    assert "active_task" in data
    ctx = data["active_task"]
    assert ctx["task_id"] == "T01"


async def test_sam_active_task_set_with_explicit_session_id(client: Client) -> None:
    """sam_active_task action=set with explicit session_id stores to the named session.

    Tests: sam_active_task set with session_id parameter.
    How: Set with session_id='test-session'; verify session_id in returned context.
    Why: Explicit session IDs enable multi-agent isolation in worktree deployments.
    """
    # Act
    result = await client.call_tool(
        "sam_active_task", {"config": {"action": "set", "plan": "P10", "task": "T05"}, "session_id": "test-session-xyz"}
    )

    # Assert
    ctx = result.data["active_task"]
    assert ctx["session_id"] == "test-session-xyz"
    assert ctx["task_id"] == "T05"


async def test_sam_active_task_get_after_set_returns_stored_context(client: Client) -> None:
    """sam_active_task action=get returns the context written by a prior set call.

    Tests: sam_active_task set → get round-trip.
    How: Set plan=P5 task=T03; get; verify task_id matches.
    Why: Round-trip fidelity ensures agents can recover their active task after session resume.
    """
    # Arrange
    await client.call_tool("sam_active_task", {"config": {"action": "set", "plan": "P5", "task": "T03"}})

    # Act
    result = await client.call_tool("sam_active_task", {"config": {"action": "get"}})

    # Assert
    ctx = result.data["active_task"]
    assert ctx is not None
    assert ctx["task_id"] == "T03"


# ===========================================================================
# sam_active_task — action=clear
# ===========================================================================


async def test_sam_active_task_clear_removes_context(client: Client) -> None:
    """sam_active_task action=clear removes the stored context; subsequent get returns null.

    Tests: sam_active_task clear happy path.
    How: Set context; clear it; verify get returns null.
    Why: Agents call clear on task completion to free the session slot.
    """
    # Arrange
    await client.call_tool("sam_active_task", {"config": {"action": "set", "plan": "P1", "task": "T01"}})

    # Act
    clear_result = await client.call_tool("sam_active_task", {"config": {"action": "clear"}})

    # Assert
    assert clear_result.data["cleared"] is True

    get_result = await client.call_tool("sam_active_task", {"config": {"action": "get"}})
    assert get_result.data["active_task"] is None


async def test_sam_active_task_clear_nonexistent_returns_false(client: Client) -> None:
    """sam_active_task action=clear returns cleared=false when no context exists.

    Tests: sam_active_task clear idempotency on empty state.
    How: Call clear without prior set.
    Why: Idempotent clear prevents errors in cleanup-on-failure handlers.
    """
    # Act
    result = await client.call_tool("sam_active_task", {"config": {"action": "clear"}})

    # Assert
    assert result.data["cleared"] is False


# ===========================================================================
# sam_active_task — action=update
# ===========================================================================


async def test_sam_active_task_update_without_active_raises_tool_error(client: Client) -> None:
    """sam_active_task action=update raises ToolError when no active task is set.

    Tests: sam_active_task update guard for absent context.
    How: Call update with no prior set.
    Why: ToolError with descriptive message directs agents to call set first.
    """
    # Act / Assert
    with pytest.raises(ToolError, match="no active task set"):
        await client.call_tool(
            "sam_active_task", {"config": {"action": "update", "set_fields_json": '{"priority": 1}'}}
        )


async def test_sam_active_task_update_patches_task_via_active_context(
    client: Client, task_backend: InMemoryTaskProvider
) -> None:
    """sam_active_task action=update patches fields on the currently active task.

    Tests: sam_active_task update happy path with memory backends.
    How: Create plan; set active context to P1/T01; update title via active context;
         read back via sam_task to verify the patch was applied.
    Why: active-task update is the write path for agents that do not want to
         re-specify plan/task on every call.
    """
    # Arrange
    plan_data = task_backend.create_plan("active-plan", "Active goal", [_task_def("T01")])
    plan_id = plan_data["plan_id"]
    await client.call_tool("sam_active_task", {"config": {"action": "set", "plan": plan_id, "task": "T01"}})

    # Act
    result = await client.call_tool(
        "sam_active_task",
        {"config": {"action": "update", "set_fields_json": '{"title": "Updated via active context"}'}},
    )

    # Assert
    assert result.data["updated"] is True

    # Verify patch persisted through sam_task read
    read_result = await client.call_tool("sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}})
    assert read_result.data["task"]["title"] == "Updated via active context"


# ===========================================================================
# sam_active_task — session isolation
# ===========================================================================


async def test_sam_active_task_different_sessions_are_isolated(client: Client) -> None:
    """sam_active_task stores separate contexts for different session_ids.

    Tests: sam_active_task session isolation.
    How: Set P1/T01 for session-a and P2/T02 for session-b; get each separately.
    Why: Parallel agents in a swarm each have their own session binding.
    """
    # Arrange
    await client.call_tool(
        "sam_active_task", {"config": {"action": "set", "plan": "P1", "task": "T01"}, "session_id": "session-a"}
    )
    await client.call_tool(
        "sam_active_task", {"config": {"action": "set", "plan": "P2", "task": "T02"}, "session_id": "session-b"}
    )

    # Act
    result_a = await client.call_tool("sam_active_task", {"config": {"action": "get"}, "session_id": "session-a"})
    result_b = await client.call_tool("sam_active_task", {"config": {"action": "get"}, "session_id": "session-b"})

    # Assert
    assert result_a.data["active_task"]["task_id"] == "T01"
    assert result_b.data["active_task"]["task_id"] == "T02"


async def test_sam_active_task_omitting_session_id_uses_default_sentinel(client: Client) -> None:
    """sam_active_task without session_id uses the _default sentinel key internally.

    Tests: sam_active_task default session isolation from explicit sessions.
    How: Set with no session_id; get with no session_id; verify context retrieved.
    Why: Single-agent workflows omit session_id — the _default sentinel must work.
    """
    # Arrange
    await client.call_tool("sam_active_task", {"config": {"action": "set", "plan": "P1", "task": "T01"}})

    # Act
    result = await client.call_tool("sam_active_task", {"config": {"action": "get"}})

    # Assert
    ctx = result.data["active_task"]
    assert ctx is not None
    assert ctx["task_id"] == "T01"
