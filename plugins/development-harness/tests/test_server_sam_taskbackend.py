"""Tests — SAM server routes all tools through TaskBackend via sam_task / sam_plan.

Test groups:
    1. Backend routing — each tool calls the expected TaskBackend method
       (not query / yaml_reader / yaml_writer) via get_task_config().backend
    2. Exception handling — PlanNotFoundError / TaskNotFoundError from the backend
       propagate as fastmcp.exceptions.ToolError (MCP isError=true), not {"error": "..."} dicts
    3. Module initialisation — server.py source contains set_task_config and
       create_task_backend at module level (not inside a function)
    4. Structural — server.py source has no direct query / yaml_reader / yaml_writer
       imports after the refactor

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set in pyproject.toml.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastmcp.exceptions import ToolError
from pytest_mock import MockerFixture  # noqa: F401 — available for future use
from sam_schema.core.exceptions import PlanNotFoundError, TaskNotFoundError
from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
from sam_schema.server import mcp

from tests.helpers import call_mcp_tool

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

# ---------------------------------------------------------------------------
# Shared call helper
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Canonical minimal return values for the mock backend
# ---------------------------------------------------------------------------

_PLAN_DATA: dict = {
    "plan_id": "P1",
    "feature": "test-feature",
    "version": "1",
    "description": "test description",
    "goal": "test goal",
    "context": "",
    "acceptance_criteria": "",
    "issue": None,
    "tasks": [],
    "source_path": None,
}

_TASK_DATA: dict = {
    "id": "T1",
    "title": "test task",
    "status": "not-started",
    "agent": "test-agent",
    "dependencies": [],
    "blocked_by": [],
    "parallelize_with": [],
    "priority": 2,
    "complexity": "low",
    "skills": [],
    "created": None,
    "started": None,
    "completed": None,
    "last_activity": None,
    "body": "",
    "description": "",
}

_STATUS_DATA: dict = {
    "feature": "test-feature",
    "total_tasks": 0,
    "by_status": {},
    "ready_tasks": [],
    "blocked_tasks": [],
    "completion_pct": 0.0,
    "has_cycles": False,
}

_PLAN_SUMMARY: dict = {
    "plan_id": "P1",
    "feature": "test-feature",
    "goal": "test goal",
    "description": "",
    "task_count": 0,
    "source_path": "/tmp/P001-test.yaml",
}

_MINIMAL_TASKS_LIST = [
    {
        "id": "T1",
        "title": "Do something",
        "status": "not-started",
        "agent": "test-agent",
        "dependencies": [],
        "priority": 2,
        "complexity": "low",
    }
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backend_mock() -> Generator[MagicMock, None, None]:
    """Inject a MagicMock TaskBackend via set_task_config for test isolation.

    Configures default return values for all Protocol methods so tool code
    can reach the assertion point without crashing after T04. Calls
    reset_task_config() in teardown to prevent cross-test contamination.

    Yields:
        Configured MagicMock satisfying the TaskBackend Protocol surface.
    """
    mock_backend = MagicMock()
    mock_backend.read_plan.return_value = _PLAN_DATA
    mock_backend.read_task.return_value = _TASK_DATA
    mock_backend.get_ready_tasks.return_value = []
    mock_backend.get_plan_status.return_value = _STATUS_DATA
    mock_backend.list_plans.return_value = [_PLAN_SUMMARY]
    mock_backend.create_plan.return_value = {**_PLAN_DATA, "source_path": "/tmp/P001-test-slug.yaml"}
    mock_backend.claim_task.return_value = True
    mock_backend.update_task_status.return_value = None
    mock_backend.update_plan_fields.return_value = None
    mock_backend.update_task_fields.return_value = None
    mock_backend.append_task_section.return_value = None

    set_task_config(TaskConfig(backend=mock_backend))
    yield mock_backend
    reset_task_config()


# ---------------------------------------------------------------------------
# Group 1: Backend routing — each tool calls the expected TaskBackend method
# ---------------------------------------------------------------------------


async def test_sam_read_plan_only_routes_through_backend_read_plan(backend_mock: MagicMock) -> None:
    """sam_plan action=read calls backend.read_plan for a plan-only read.

    sam_plan(config={action: read}, plan='P1') must resolve to backend.read_plan('P1').

    Arrange: inject mock backend via set_task_config with default plan data.
    Act: call sam_plan with action=read, plan='P1'.
    Assert: backend.read_plan was called exactly once with plan_id 'P1'.
    """
    # Act
    await _call("sam_plan", {"config": {"action": "read"}, "plan": "P1"})

    # Assert
    backend_mock.read_plan.assert_called_once_with("P1")


async def test_sam_read_with_task_routes_through_backend_read_task(backend_mock: MagicMock) -> None:
    """sam_task action=read calls backend.read_task for a task read.

    sam_task(plan='P1', task='T1', config={action: read}) must delegate to
    backend.read_task('P1', 'T1') to retrieve the task with its plan context.

    Arrange: inject mock backend with task data return value.
    Act: call sam_task with plan='P1', task='T1', action=read.
    Assert: backend.read_task called once with ('P1', 'T1').
    """
    # Act
    await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "read"}})

    # Assert
    backend_mock.read_task.assert_called_once_with("P1", "T1")


async def test_sam_read_with_task_returns_task_assignment_envelope(backend_mock: MagicMock) -> None:
    """sam_task action=read returns TaskAssignment envelope including plan_goal and task fields.

    sam_task(plan='P1', task='T1', config={action: read}) must return a dict
    containing plan-level envelope fields (plan-goal, plan-number) alongside the nested
    task object — matching the TaskAssignment serialization shape.

    Arrange: inject mock backend; _PLAN_DATA has goal='test goal', feature='test-feature'.
    Act: call sam_task with plan='P1', task='T1', action=read.
    Assert: response contains 'plan-goal' (by_alias serialization) and 'task' keys,
            with plan-goal matching the plan data value.
    """
    # Act
    response = await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "read"}})

    # Assert
    assert "plan-goal" in response, f"Expected 'plan-goal' in response, got keys: {sorted(response.keys())}"
    assert "task" in response, f"Expected 'task' in response, got keys: {sorted(response.keys())}"
    assert response["plan-goal"] == "test goal"
    assert response["task"]["id"] == "T1"


async def test_sam_state_routes_through_backend_update_task_status(backend_mock: MagicMock) -> None:
    """sam_task action=state calls backend.update_task_status.

    sam_task(plan, task, config={action: state, status: complete}) must delegate to
    backend.update_task_status(plan_id, task_id, status_str).

    Arrange: inject mock backend via set_task_config.
    Act: call sam_task with plan='P1', task='T1', config action=state status=complete.
    Assert: backend.update_task_status called with ('P1', 'T1', 'complete').
    """
    # Act
    await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "state", "status": "complete"}})

    # Assert
    backend_mock.update_task_status.assert_called_once_with("P1", "T1", "complete")


async def test_sam_ready_routes_through_backend_get_ready_tasks(backend_mock: MagicMock) -> None:
    """sam_plan action=ready calls backend.get_ready_tasks.

    The list of dispatch-ready tasks is fetched via the backend Protocol,
    enabling non-filesystem backends (memory, GitHub) to implement it.

    Arrange: inject mock backend; configure get_ready_tasks to return [].
    Act: call sam_plan with action=ready, plan='P1'.
    Assert: backend.get_ready_tasks called exactly once with 'P1'.
    """
    # Act
    await _call("sam_plan", {"config": {"action": "ready"}, "plan": "P1"})

    # Assert
    backend_mock.get_ready_tasks.assert_called_once_with("P1")


async def test_sam_status_routes_through_backend_get_plan_status(backend_mock: MagicMock) -> None:
    """sam_plan action=status calls backend.get_plan_status.

    Plan-level progress summaries come from the backend Protocol rather than
    direct YAML reads, enabling in-memory and remote backends.

    Arrange: inject mock backend; configure get_plan_status return value.
    Act: call sam_plan with action=status, plan='P1'.
    Assert: backend.get_plan_status called once with 'P1'.
    """
    # Act
    await _call("sam_plan", {"config": {"action": "status"}, "plan": "P1"})

    # Assert
    backend_mock.get_plan_status.assert_called_once_with("P1")


async def test_sam_status_merges_autonomy_from_read_plan(backend_mock: MagicMock) -> None:
    """sam_plan action=status merges autonomy field from backend.read_plan into the response.

    Arrange: configure backend.read_plan to return _PLAN_DATA with autonomy='per_task'.
    Act: call sam_plan with action=status, plan='P1'.
    Assert: result['autonomy'] == 'per_task'; backend.read_plan called once with 'P1'.
    """
    # Arrange — override read_plan to return a plan dict with explicit autonomy
    backend_mock.read_plan.return_value = {**_PLAN_DATA, "autonomy": "per_task"}

    # Act
    result = await _call("sam_plan", {"config": {"action": "status"}, "plan": "P1"})

    # Assert — autonomy value surfaced from read_plan merge
    assert "autonomy" in result, f"Expected 'autonomy' key in status result, got keys: {sorted(result.keys())}"
    assert result["autonomy"] == "per_task"
    backend_mock.read_plan.assert_called_once_with("P1")


async def test_sam_status_autonomy_fallback_when_absent_in_read_plan(backend_mock: MagicMock) -> None:
    """sam_plan action=status returns autonomy='full_auto' when read_plan dict lacks the key.

    Arrange: backend.read_plan returns _PLAN_DATA which does NOT contain 'autonomy'.
    Act: call sam_plan with action=status, plan='P1'.
    Assert: result['autonomy'] == 'full_auto' (the .get() fallback path).
    """
    # Arrange — _PLAN_DATA has no 'autonomy' key; verify the baseline assumption
    assert "autonomy" not in _PLAN_DATA, (
        "_PLAN_DATA must not contain 'autonomy' for this test to exercise the fallback path. "
        "Remove 'autonomy' from _PLAN_DATA or update this test."
    )

    # Act (backend_mock.read_plan already returns _PLAN_DATA by default from fixture)
    result = await _call("sam_plan", {"config": {"action": "status"}, "plan": "P1"})

    # Assert — fallback to 'full_auto' when key is absent
    assert "autonomy" in result, f"Expected 'autonomy' key in status result, got keys: {sorted(result.keys())}"
    assert result["autonomy"] == "full_auto"


async def test_sam_list_routes_through_backend_list_plans(backend_mock: MagicMock) -> None:
    """sam_plan action=list calls backend.list_plans.

    Plan enumeration is delegated to the backend, which handles search,
    pagination, and filesystem (or remote) access internally.

    Arrange: inject mock backend; configure list_plans to return a summary list.
    Act: call sam_plan with action=list.
    Assert: backend.list_plans called at least once.
    """
    # Act
    await _call("sam_plan", {"config": {"action": "list"}})

    # Assert
    backend_mock.list_plans.assert_called_once()


async def test_sam_create_routes_through_backend_create_plan(backend_mock: MagicMock) -> None:
    """sam_plan action=create calls backend.create_plan.

    Plan creation is mediated through the TaskBackend Protocol.
    The YAML parsing of tasks_yaml (user input) may remain in the tool, but
    the actual plan write goes through backend.create_plan.

    Arrange: inject mock backend; configure create_plan return value.
    Act: call sam_plan with action=create, slug='test-slug', goal='test goal', valid tasks_yaml.
    Assert: backend.create_plan called once; slug argument is 'test-slug'.
    """
    # Act
    await _call(
        "sam_plan",
        {"config": {"action": "create", "slug": "test-slug", "goal": "test goal", "tasks": _MINIMAL_TASKS_LIST}},
    )

    # Assert
    backend_mock.create_plan.assert_called_once()
    call_args = backend_mock.create_plan.call_args
    # Accept both positional and keyword slug argument
    slug_value = call_args.kwargs.get("slug") if call_args.kwargs else None
    if slug_value is None and call_args.args:
        slug_value = call_args.args[0]
    assert slug_value == "test-slug"


async def test_sam_update_plan_fields_routes_through_backend_update_plan_fields(backend_mock: MagicMock) -> None:
    """sam_plan action=update calls backend.update_plan_fields.

    Plan context and field updates go through the backend Protocol.

    Arrange: inject mock backend via set_task_config.
    Act: call sam_plan with action=update, plan='P1', context='new context'.
    Assert: backend.update_plan_fields called once.
    """
    # Act
    await _call("sam_plan", {"config": {"action": "update", "context": "new context"}, "plan": "P1"})

    # Assert
    backend_mock.update_plan_fields.assert_called_once()


async def test_sam_update_task_fields_routes_through_backend_update_task(backend_mock: MagicMock) -> None:
    """sam_task action=update with set_fields_json calls backend.update_task.

    Task scalar field updates (e.g. agent) go through backend.update_task
    (full Task model write) rather than backend.update_task_fields (field-level patch).

    Arrange: inject mock backend via set_task_config.
    Act: call sam_task with plan='P1', task='T1', action=update, set_fields_json for agent field.
    Assert: backend.update_task called once; backend.update_task_fields NOT called.
    """
    # Arrange
    backend_mock.update_task.return_value = None

    # Act
    await _call(
        "sam_task",
        {"plan": "P1", "task": "T1", "config": {"action": "update", "set_fields_json": {"agent": "new-agent"}}},
    )

    # Assert
    backend_mock.update_task.assert_called_once()
    backend_mock.update_task_fields.assert_not_called()


async def test_sam_update_append_section_routes_through_backend_append_task_section(backend_mock: MagicMock) -> None:
    """sam_task action=update with append_section calls backend.append_task_section.

    Appending a markdown section to a task body goes through
    backend.append_task_section.

    Arrange: inject mock backend via set_task_config.
    Act: call sam_task with plan='P1', task='T1', action=update, append_section and content.
    Assert: backend.append_task_section called once.
    """
    # Act
    await _call(
        "sam_task",
        {
            "plan": "P1",
            "task": "T1",
            "config": {"action": "update", "append_section": "Work Log", "section_content": "Completed the refactor."},
        },
    )

    # Assert
    backend_mock.append_task_section.assert_called_once()


async def test_sam_claim_routes_through_backend_claim_task(backend_mock: MagicMock) -> None:
    """sam_task action=claim calls backend.claim_task.

    Task claiming is mediated through the backend Protocol,
    enabling atomic claim semantics in non-filesystem backends.

    Arrange: inject mock backend; configure claim_task to return True.
    Act: call sam_task with plan='P1', task='T1', action=claim.
    Assert: backend.claim_task called once with ('P1', 'T1').
    """
    # Act
    await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "claim"}})

    # Assert
    backend_mock.claim_task.assert_called_once_with("P1", "T1")


# ---------------------------------------------------------------------------
# Group 2: Exception handling — SAM exceptions propagate as MCP ToolError
# ---------------------------------------------------------------------------


async def test_sam_read_raises_tool_error_when_backend_raises_plan_not_found(backend_mock: MagicMock) -> None:
    """sam_plan action=read raises ToolError when backend raises PlanNotFoundError.

    FastMCP converts unhandled tool exceptions to isError=true MCP responses,
    which the client surfaces as ToolError. The error message must include the
    plan_id so callers can identify which plan was missing.

    Arrange: configure backend.read_plan to raise PlanNotFoundError("P999").
    Act: call sam_plan with action=read, plan='P999'.
    Assert: ToolError is raised containing "Plan not found" and "P999".
    """
    # Arrange
    backend_mock.read_plan.side_effect = PlanNotFoundError("P999")

    # Act / Assert
    with pytest.raises(ToolError) as exc_info:
        await _call("sam_plan", {"config": {"action": "read"}, "plan": "P999"})
    assert "Plan not found" in str(exc_info.value)
    assert "P999" in str(exc_info.value)


async def test_sam_state_raises_tool_error_when_backend_raises_task_not_found(backend_mock: MagicMock) -> None:
    """sam_task action=state raises ToolError when backend raises TaskNotFoundError.

    FastMCP converts unhandled tool exceptions to isError=true MCP responses,
    which the client surfaces as ToolError. The error message must reference
    the missing task_id.

    Arrange: configure backend.update_task_status to raise TaskNotFoundError("P1", "T999").
    Act: call sam_task with plan='P1', task='T999', action=state, status='complete'.
    Assert: ToolError is raised containing "T999".
    """
    # Arrange
    backend_mock.update_task_status.side_effect = TaskNotFoundError("P1", "T999")

    # Act / Assert
    with pytest.raises(ToolError) as exc_info:
        await _call("sam_task", {"plan": "P1", "task": "T999", "config": {"action": "state", "status": "complete"}})
    assert "T999" in str(exc_info.value)


async def test_sam_claim_raises_tool_error_when_backend_raises_plan_not_found(backend_mock: MagicMock) -> None:
    """sam_task action=claim raises ToolError when backend.claim_task raises PlanNotFoundError.

    FastMCP converts unhandled tool exceptions to isError=true MCP responses,
    which the client surfaces as ToolError. MCP clients must use the isError
    flag (not dict key inspection) to detect tool failures.

    Arrange: configure backend.claim_task to raise PlanNotFoundError("P999").
    Act: call sam_task with plan='P999', task='T1', action=claim.
    Assert: ToolError is raised containing "P999".
    """
    # Arrange
    backend_mock.claim_task.side_effect = PlanNotFoundError("P999")

    # Act / Assert
    with pytest.raises(ToolError) as exc_info:
        await _call("sam_task", {"plan": "P999", "task": "T1", "config": {"action": "claim"}})
    assert "P999" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Group 3: Module initialisation — set_task_config called at module level
# ---------------------------------------------------------------------------


def test_server_module_source_calls_set_task_config() -> None:
    """server.py source contains a call to set_task_config.

    After T04, the module must call set_task_config(TaskConfig(backend=...))
    at import time so that get_task_config() succeeds without manual setup.
    This structural check ensures the initialisation is present in the source.

    Why: Without module-level initialisation, a fresh import leaves
    get_task_config() raising RuntimeError, breaking all 8 MCP tools.
    """
    import sam_schema.server as server_module

    source = inspect.getsource(server_module)
    assert "set_task_config" in source


def test_server_module_source_calls_create_task_backend() -> None:
    """server.py source contains a call to create_task_backend.

    After T04, the backend instance must be obtained via the factory function
    create_task_backend(), which honours the TASKBACKEND env var and
    taskbackend.toml, rather than directly constructing LocalYamlTaskProvider.

    Why: Direct construction bypasses backend selection, breaking env-based
    backend switching used in tests and CI.
    """
    import sam_schema.server as server_module

    source = inspect.getsource(server_module)
    assert "create_task_backend" in source


# ---------------------------------------------------------------------------
# Group 4: Structural — no direct query / yaml_reader / yaml_writer imports
# ---------------------------------------------------------------------------


def test_server_has_no_direct_query_import() -> None:
    """server.py must not import from sam_schema.core.query after T04.

    After T04, all operations previously performed by query.* functions are
    delegated to the TaskBackend Protocol. Any remaining direct query import
    is a regression that indicates the tool still bypasses the backend.

    Check: neither 'from sam_schema.core.query import' nor
    'from sam_schema.core import query' appear in server.py import lines.
    """
    import sam_schema.server as server_module

    source = inspect.getsource(server_module)
    import_lines = [line for line in source.splitlines() if line.strip().startswith(("from ", "import "))]
    import_block = "\n".join(import_lines)

    assert "from sam_schema.core.query import" not in import_block
    assert "from sam_schema.core import query" not in import_block


def test_server_has_no_yaml_reader_import() -> None:
    """server.py must not import yaml_reader after T04.

    yaml_reader is an internal module of the YAML I/O stack encapsulated inside
    LocalYamlTaskProvider. A direct import in server.py indicates the tool is
    reading YAML files outside the backend abstraction.

    Check: the string 'yaml_reader' does not appear anywhere in server.py source.
    """
    import sam_schema.server as server_module

    source = inspect.getsource(server_module)
    assert "yaml_reader" not in source


def test_server_has_no_yaml_writer_import() -> None:
    """server.py must not import yaml_writer after T04.

    yaml_writer is an internal module of the YAML I/O stack encapsulated inside
    LocalYamlTaskProvider. A direct import in server.py indicates the tool is
    writing YAML files outside the backend abstraction.

    Check: the string 'yaml_writer' does not appear anywhere in server.py source.
    """
    import sam_schema.server as server_module

    source = inspect.getsource(server_module)
    assert "yaml_writer" not in source


# ---------------------------------------------------------------------------
# Regression: list fields in set_fields_json must reach backend as list[str]
# ---------------------------------------------------------------------------


async def test_sam_update_set_fields_json_list_value_passes_list_to_backend(backend_mock: MagicMock) -> None:
    """sam_task action=update preserves list values in set_fields_json as list[str] to backend.

    Regression guard for the bug where str(["T01", "T02", "T03"]) produced the
    Python repr string "['T01', 'T02', 'T03']" instead of a list.

    sam_task calls backend.update_task with a fully-validated Task model. The Task
    model's dependencies field must carry a list[str], not a string repr of a list.

    Arrange: inject mock backend via set_task_config.
    Act: call sam_task with plan='P1', task='T1', action=update, set_fields_json containing a
         list-valued field: {"dependencies": ["T01", "T02", "T03"]}.
    Assert: backend.update_task was called once with a Task whose dependencies
            is the list ["T01", "T02", "T03"], not a string repr of it.
    """
    # Arrange
    backend_mock.update_task.return_value = None
    fields = {"dependencies": ["T01", "T02", "T03"]}

    # Act
    await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "update", "set_fields_json": fields}})

    # Assert: update_task called, update_task_fields NOT called
    backend_mock.update_task.assert_called_once()
    backend_mock.update_task_fields.assert_not_called()

    call_args = backend_mock.update_task.call_args
    # update_task(plan_id, task) — task is 2nd positional arg
    task_passed = call_args.args[1] if call_args.args and len(call_args.args) >= 2 else call_args.kwargs.get("task")

    assert task_passed is not None, "Expected task argument in backend.update_task call"
    deps = task_passed.dependencies
    assert isinstance(deps, list), (
        f"Expected list for 'dependencies' but got {type(deps).__name__!r}: {deps!r}\n"
        "This is the str() coercion bug — set_fields_json must preserve list values."
    )
    assert deps == ["T01", "T02", "T03"], f"Expected ['T01', 'T02', 'T03'] but got: {deps!r}"


# ---------------------------------------------------------------------------
# update_task round-trip: list fields preserved; server routes through update_task
# ---------------------------------------------------------------------------


def test_update_task_round_trips_list_fields_without_coercion(tmp_path: Path) -> None:
    """update_task preserves list[str] fields as lists, not Python repr strings.

    Regression guard: LocalYamlTaskProvider.update_task must write dependencies
    as a YAML sequence, not as str(["T01", "T02"]) which would produce the
    Python repr string.

    Arrange: create a plan with one task; call LocalYamlTaskProvider.update_task
             with a Task model whose dependencies=["T01", "T02"].
    Act: read the raw YAML file back after the write.
    Assert: dependencies is a list of strings in the stored YAML, not a string repr.
    """
    from pathlib import Path as _Path

    from ruamel.yaml import YAML
    from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.models import Complexity, Priority, Task as _Task
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
    from sam_schema.server import sam_plan

    # Arrange: create plan via LocalYamlTaskProvider so the file is real YAML
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(
        id="T01", title="Task One", status="not-started", agent="a", priority=Priority.HIGH, complexity=Complexity.LOW
    )
    backend = LocalYamlTaskProvider(p_dir)
    set_task_config(TaskConfig(backend=backend))
    try:
        result = sam_plan(
            config=CreatePlanConfig(slug="roundtrip", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
        )
        assert "error" not in result, f"sam_create failed: {result}"
        plan_id = result["plan_id"]
        plan_path = _Path(p_dir) / f"{plan_id}-roundtrip.yaml"

        # Act: update task with a Task model that has non-empty dependencies
        task_data = backend.read_task(plan_id, "T01")
        updated_task = _Task.model_validate({**task_data, "dependencies": ["T01", "T02"]})
        backend.update_task(plan_id, updated_task)

        # Assert: read the raw YAML file — dependencies must be a sequence, not a string
        yaml = YAML()
        loaded = yaml.load(plan_path)
        # Navigate to the task in the loaded structure
        tasks_raw = loaded.get("tasks") or loaded.get("task") or []
        if not isinstance(tasks_raw, list):
            tasks_raw = [tasks_raw]
        t01 = next((t for t in tasks_raw if t.get("task") == "T01" or t.get("id") == "T01"), None)
        assert t01 is not None, f"Could not find T01 in raw YAML: {dict(loaded)}"
        deps_raw = t01.get("dependencies", [])
        assert isinstance(deps_raw, list), (
            f"Expected list for 'dependencies' in YAML but got {type(deps_raw).__name__!r}: {deps_raw!r}\n"
            "This is the str() coercion bug — update_task must write YAML sequences."
        )
        assert list(deps_raw) == ["T01", "T02"], f"Expected ['T01', 'T02'] but got: {list(deps_raw)!r}"
    finally:
        reset_task_config()


async def test_sam_update_set_fields_json_writes_via_update_task(backend_mock: MagicMock) -> None:
    """sam_task action=update routes through backend.update_task, not field-level setters.

    sam_task with action=update and set_fields_json must call
    backend.update_task(plan_id, validated_task) with a full Task model —
    NOT backend.update_task_fields(plan_id, task_id, field_dict).

    Arrange: inject mock backend; configure update_task return value.
    Act: call sam_task with plan='P1', task='T1', action=update, set_fields_json containing
         a list-valued dependencies field.
    Assert: backend.update_task was called once; backend.update_task_fields
            was NOT called.
    """
    # Arrange
    backend_mock.update_task.return_value = None
    fields = {"dependencies": ["T01", "T02"]}

    # Act
    await _call("sam_task", {"plan": "P1", "task": "T1", "config": {"action": "update", "set_fields_json": fields}})

    # Assert: update_task called, update_task_fields NOT called
    backend_mock.update_task.assert_called_once()
    backend_mock.update_task_fields.assert_not_called()


# ---------------------------------------------------------------------------
# Regression #1528: kebab-case field merge and list[Model] YAML serialization
# ---------------------------------------------------------------------------


def test_validated_task_patch_kebab_case_fields_survive_merge(tmp_path: Path) -> None:
    """_validated_task_patch correctly merges kebab-case patch fields without key duplication.

    Regression guard for Fix 1 in #1528: model_dump() without by_alias=True produced
    snake_case keys. Merging that with raw_fields (kebab-case) created both
    'parallelize_with' and 'parallelize-with' in the merged dict, causing
    Task.model_validate to ignore the patched value.

    With the fix, model_dump(by_alias=True, mode='json') emits kebab-case keys on both
    sides of the merge, so the kebab-case raw_fields value wins cleanly.

    Arrange: create a plan with one task that has parallelize_with=[]; call
             _validated_task_patch directly with raw_fields using the kebab-case key.
    Act: pass raw_fields={"parallelize-with": ["T01", "T02"]} to _validated_task_patch.
    Assert:
        1. returned Task.parallelize_with == ["T01", "T02"]
        2. model_dump() produces a single key for the field (no duplication)
    """
    from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.models import Complexity, Priority
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
    from sam_schema.server import _validated_task_patch, sam_plan  # type: ignore[attr-defined]

    # Arrange: create a plan with a task that has no parallelize_with entries
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(
        id="T01", title="Task One", status="not-started", agent="a", priority=Priority.HIGH, complexity=Complexity.LOW
    )
    backend = LocalYamlTaskProvider(p_dir)
    set_task_config(TaskConfig(backend=backend))
    try:
        result = sam_plan(
            config=CreatePlanConfig(slug="kebabmerge", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
        )
        assert "error" not in result, f"sam_plan create failed: {result}"
        plan_id = result["plan_id"]

        # Act: patch parallelize-with using the MCP wire (kebab-case) key
        raw_fields: dict = {"parallelize-with": ["T01", "T02"]}
        patched_task = _validated_task_patch(backend, plan_id, "T01", raw_fields)

        # Assert 1: field value is correct
        assert patched_task.parallelize_with == ["T01", "T02"], (
            f"Expected ['T01', 'T02'] but got {patched_task.parallelize_with!r}.\n"
            "This is the kebab/snake key collision bug from #1528 Fix 1."
        )

        # Assert 2: model_dump produces exactly one key for the parallelize field — no duplication
        dumped = patched_task.model_dump()
        assert "parallelize_with" in dumped, "Expected 'parallelize_with' snake_case key in model_dump()"
        assert "parallelize-with" not in dumped, (
            "Unexpected 'parallelize-with' key found in model_dump() — "
            "this means both snake and kebab keys survived the merge."
        )
    finally:
        reset_task_config()


def test_sam_update_kebab_case_field_roundtrips_through_yaml(tmp_path: Path) -> None:
    """sam_task action=update with a kebab-case field persists the value correctly in YAML.

    Integration regression guard for Fix 1 in #1528: after patching parallelize-with
    via the MCP sam_task update action, the stored YAML must contain a proper sequence,
    not a repr string or an empty list.

    Arrange: create a plan with one task via LocalYamlTaskProvider.
    Act: call sam_task update with set_fields_json={"parallelize-with": ["T01", "T02"]}.
    Assert: raw YAML file contains parallelize-with as a list, not a repr string.
    """
    import asyncio
    from pathlib import Path as _Path

    from ruamel.yaml import YAML
    from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.models import Complexity, Priority
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
    from sam_schema.server import sam_plan

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(
        id="T01", title="Task One", status="not-started", agent="a", priority=Priority.HIGH, complexity=Complexity.LOW
    )
    backend = LocalYamlTaskProvider(p_dir)
    set_task_config(TaskConfig(backend=backend))
    try:
        result = sam_plan(
            config=CreatePlanConfig(slug="kebabint", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
        )
        assert "error" not in result, f"sam_plan create failed: {result}"
        plan_id = result["plan_id"]

        # Act: update via the MCP handler using the kebab-case wire key
        update_result = asyncio.run(
            _call(
                "sam_task",
                {
                    "plan": plan_id,
                    "task": "T01",
                    "config": {"action": "update", "set_fields_json": {"parallelize-with": ["T01", "T02"]}},
                },
            )
        )
        assert "error" not in update_result, f"sam_task update failed: {update_result}"

        # Assert: read raw YAML back and verify parallelize-with is a list
        plan_yaml_files = list(_Path(p_dir).glob(f"{plan_id}-*.yaml"))
        assert plan_yaml_files, f"No YAML file found for plan {plan_id} in {p_dir}"
        yaml = YAML()
        loaded = yaml.load(plan_yaml_files[0])
        tasks_raw = loaded.get("tasks") or []
        t01 = next((t for t in tasks_raw if t.get("task") == "T01" or t.get("id") == "T01"), None)
        assert t01 is not None, f"T01 not found in raw YAML. Keys: {list(loaded.keys())}"
        pw_raw = t01.get("parallelize-with", t01.get("parallelize_with", []))
        assert isinstance(pw_raw, list), (
            f"Expected list for 'parallelize-with' in YAML but got {type(pw_raw).__name__!r}: {pw_raw!r}\n"
            "Fix 1 in #1528 should have prevented the kebab/snake merge collision."
        )
        assert list(pw_raw) == ["T01", "T02"], f"Expected ['T01', 'T02'] but got: {list(pw_raw)!r}"
    finally:
        reset_task_config()


def test_sam_plan_update_serializes_list_model_fields_as_dicts(tmp_path: Path) -> None:
    """sam_plan update with acceptance-criteria-structured stores plain dicts, not model reprs.

    Regression guard for Fix 2 in #1528: model_dump(by_alias=True) without mode='json'
    returns AcceptanceCriterion instances for list[AcceptanceCriterion] fields.
    ruamel.yaml serializes those as Python repr strings. mode='json' ensures the values
    are JSON-native dicts before passing to the backend.

    Arrange: create a plan; update it with a structured acceptance criterion via MCP.
    Act: read the plan back via backend.read_plan.
    Assert: acceptance-criteria-structured is a list of dicts, not model reprs.
    """
    import asyncio

    from sam_schema.core.action_models import CreatePlanConfig
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
    from sam_schema.server import sam_plan

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    backend = LocalYamlTaskProvider(p_dir)
    set_task_config(TaskConfig(backend=backend))
    try:
        result = sam_plan(config=CreatePlanConfig(slug="acstest", goal="Goal", tasks=[]), plan_dir=str(p_dir))
        assert "error" not in result, f"sam_plan create failed: {result}"
        plan_id = result["plan_id"]

        # Act: update the plan with a structured acceptance criterion via MCP call
        # Using _call (MCP handler) so the discriminated-union config deserialization runs
        ac_value = [
            {
                "criterion-id": "AC01",
                "description": "The thing works",
                "check-command": "echo ok",
                "expected-baseline": "any",
                "expected-final": "pass",
            }
        ]
        update_result = asyncio.run(
            _call(
                "sam_plan",
                {
                    "plan": plan_id,
                    "plan_dir": str(p_dir),
                    "config": {"action": "update", "set_fields_json": {"acceptance-criteria-structured": ac_value}},
                },
            )
        )
        assert "error" not in update_result, f"sam_plan update failed: {update_result}"

        # Assert: read the plan back — acceptance_criteria_structured must be list of dicts
        plan_data = backend.read_plan(plan_id)
        acs = plan_data.get("acceptance-criteria-structured") or plan_data.get("acceptance_criteria_structured") or []
        assert isinstance(acs, list), f"Expected list but got {type(acs).__name__!r}: {acs!r}"
        assert len(acs) == 1, f"Expected 1 criterion but got {len(acs)}: {acs!r}"
        first = acs[0]
        assert isinstance(first, dict), (
            f"Expected dict for criterion but got {type(first).__name__!r}: {first!r}\n"
            "This is the model_dump without mode='json' bug from #1528 Fix 2 — "
            "AcceptanceCriterion instances must be serialized to dicts."
        )
        criterion_id = first.get("criterion-id") or first.get("criterion_id")
        assert criterion_id == "AC01", f"Expected criterion-id 'AC01' but got: {criterion_id!r}"
    finally:
        reset_task_config()


def test_sam_plan_update_list_field_no_repr_in_yaml(tmp_path: Path) -> None:
    """sam_plan update does not write AcceptanceCriterion repr strings to YAML.

    Regression guard for Fix 2 in #1528: raw YAML must not contain the class name
    'AcceptanceCriterion' anywhere — that would mean Pydantic model instances were
    passed to ruamel.yaml instead of plain dicts.

    Arrange: create a plan; update acceptance-criteria-structured via MCP.
    Act: read the raw YAML file.
    Assert: 'AcceptanceCriterion' does not appear anywhere in the YAML content.
    """
    import asyncio
    from pathlib import Path as _Path

    from sam_schema.core.action_models import CreatePlanConfig
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
    from sam_schema.server import sam_plan

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    backend = LocalYamlTaskProvider(p_dir)
    set_task_config(TaskConfig(backend=backend))
    try:
        result = sam_plan(config=CreatePlanConfig(slug="noreprtest", goal="Goal", tasks=[]), plan_dir=str(p_dir))
        assert "error" not in result, f"sam_plan create failed: {result}"
        plan_id = result["plan_id"]

        # Act: update the plan with a structured acceptance criterion via MCP call
        ac_value = [
            {
                "criterion-id": "AC01",
                "description": "No repr allowed",
                "check-command": "echo pass",
                "expected-baseline": "any",
                "expected-final": "pass",
            }
        ]
        update_result = asyncio.run(
            _call(
                "sam_plan",
                {
                    "plan": plan_id,
                    "plan_dir": str(p_dir),
                    "config": {"action": "update", "set_fields_json": {"acceptance-criteria-structured": ac_value}},
                },
            )
        )
        assert "error" not in update_result, f"sam_plan update failed: {update_result}"

        # Assert: raw YAML must not contain the Pydantic class name
        plan_yaml_files = list(_Path(p_dir).glob(f"{plan_id}-*.yaml"))
        assert plan_yaml_files, f"No YAML file found for plan {plan_id} in {p_dir}"
        raw_content = plan_yaml_files[0].read_text()
        assert "AcceptanceCriterion" not in raw_content, (
            "Found 'AcceptanceCriterion' in raw YAML — Pydantic model instances were "
            "serialized as repr strings instead of dicts.\n"
            "This is the model_dump without mode='json' bug from #1528 Fix 2.\n"
            f"YAML content snippet: {raw_content[:500]!r}"
        )
    finally:
        reset_task_config()


# ---------------------------------------------------------------------------
# sam_active_task: set→get round-trip with parent_issue_number
# ---------------------------------------------------------------------------


async def test_sam_active_task_set_get_round_trip_persists_parent_issue_number(backend_mock: MagicMock) -> None:
    """sam_active_task set→get round-trip persists parent_issue_number.

    SetActiveTaskConfig gained parent_issue_number to thread it into the
    context backend so the SubagentStop hook can link sub-issues.  Verify
    that a value set via action='set' is returned by action='get'.

    Arrange: inject in-memory context backend; inject mock task backend.
    Act 1: sam_active_task(action='set', plan='P1', task='T1', parent_issue_number=42).
    Act 2: sam_active_task(action='get').
    Assert: get response includes parent_issue_number=42.
    """
    from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend
    from sam_schema.core.context_config import ContextConfig, reset_context_config, set_context_config

    ctx_backend = InMemoryContextBackend()
    set_context_config(ContextConfig(backend=ctx_backend))
    try:
        # Act 1 — set with parent_issue_number
        await _call(
            "sam_active_task", {"config": {"action": "set", "plan": "P1", "task": "T1", "parent_issue_number": 42}}
        )

        # Act 2 — get and verify round-trip
        result = await _call("sam_active_task", {"config": {"action": "get"}})
        active_task = result.get("active_task") or {}
        assert active_task.get("parent_issue_number") == 42
    finally:
        reset_context_config()


# ---------------------------------------------------------------------------
# Plan-level set_fields_json validation (fix #1512)
# ---------------------------------------------------------------------------


async def test_sam_plan_update_set_fields_json_invalid_enum_raises_tool_error(backend_mock: MagicMock) -> None:
    """sam_plan action=update with set_fields_json validates fields through Plan model.

    Plan-level set_fields_json must route through Plan.model_validate, not cast().
    Passing an invalid enum value for `state` must raise ToolError, not silently
    accept the invalid value.

    Arrange: inject mock backend.
    Act: call sam_plan with action=update, plan='P1', set_fields_json containing
         an invalid PlanState enum value.
    Assert: ToolError is raised (pydantic.ValidationError propagates as ToolError).
    """
    with pytest.raises(ToolError):
        await _call(
            "sam_plan", {"config": {"action": "update", "set_fields_json": '{"state": "invalid-value"}'}, "plan": "P1"}
        )
    backend_mock.update_plan_fields.assert_not_called()


async def test_sam_plan_update_set_fields_json_valid_value_succeeds(backend_mock: MagicMock) -> None:
    """sam_plan action=update with valid set_fields_json passes validation and calls backend.

    Arrange: inject mock backend.
    Act: call sam_plan with action=update, plan='P1', set_fields_json with a valid goal string.
    Assert: backend.update_plan_fields is called; no ToolError raised.
    """
    result = await _call(
        "sam_plan", {"config": {"action": "update", "set_fields_json": {"goal": "new goal"}}, "plan": "P1"}
    )
    assert result.get("updated") is True
    backend_mock.update_plan_fields.assert_called_once_with("P1", context=None, set_fields={"goal": "new goal"})
