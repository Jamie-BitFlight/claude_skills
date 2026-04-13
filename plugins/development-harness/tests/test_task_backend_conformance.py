"""Protocol conformance tests for all TaskBackend implementations.

Parametrized over every concrete backend so a single test class validates
the full contract. Adding a new backend requires only a new fixture parameter.

Coverage targets:
- Plan lifecycle (create, read, list, update fields)
- Task access (read, claim, update status/fields, append section)
- Ready-task dependency resolution
- Plan status aggregation
- Document store/retrieve round-trip
- Error paths (not-found, duplicate, invalid status)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from sam_schema.core.action_models import TaskDefinition
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.exceptions import DocumentNotFoundError, PlanNotFoundError, TaskNotFoundError, TaskValidationError
from sam_schema.core.task_backend import TaskBackend

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_def(
    task_id: str,
    title: str,
    status: str = "not-started",
    dependencies: list[str] | None = None,
    agent: str | None = None,
    priority: int = 1,
    complexity: str = "low",
    skills: list[str] | None = None,
    body: str = "",
    description: str = "",
) -> TaskDefinition:
    """Construct a minimal TaskDefinition for test data.

    Uses model_validate to accept raw test values (int priority, str complexity)
    without triggering ty type errors on enum fields.

    All parameters have sensible defaults so callers only need to supply
    the fields relevant to the test under execution.
    """
    return TaskDefinition.model_validate({
        "id": task_id,
        "title": title,
        "status": status,
        "priority": priority,
        "complexity": complexity,
        "body": body,
        "description": description,
        "dependencies": dependencies or [],
        "agent": agent,
        "skills": skills or [],
    })


# ---------------------------------------------------------------------------
# Parametrized backend fixture
# ---------------------------------------------------------------------------


@pytest.fixture(params=["local_yaml", "memory"])
def backend(request: pytest.FixtureRequest, tmp_path: Path) -> TaskBackend:
    """Provide a fresh TaskBackend instance for each parametrized variant.

    ``local_yaml`` uses a temporary directory so tests do not pollute the
    real plan store.  ``memory`` creates a new in-memory instance with no
    shared state.
    """
    match request.param:
        case "local_yaml":
            return LocalYamlTaskProvider(plan_dir=tmp_path)
        case "memory":
            return InMemoryTaskProvider()
        case _:
            msg = f"Unknown backend parameter: {request.param!r}"
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Conformance test class
# ---------------------------------------------------------------------------


class TestTaskBackendConformance:
    """Validates that every TaskBackend implementation honours the Protocol contract."""

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def test_create_and_read_plan(self, backend: TaskBackend) -> None:
        """Creating a plan and reading it back should return matching data."""
        # Arrange
        tasks = [_make_task_def("T01", "First task")]

        # Act
        created = backend.create_plan("my-slug", "Do the thing", tasks, context="some context")
        plan_id = created["plan_id"]
        read_back = backend.read_plan(plan_id)

        # Assert
        assert read_back["plan_id"] == plan_id
        assert read_back["goal"] == "Do the thing"
        assert len(read_back["tasks"]) == 1
        assert read_back["tasks"][0]["id"] == "T01"
        assert read_back["tasks"][0]["title"] == "First task"

    def test_create_plan_duplicate_raises(self, backend: TaskBackend) -> None:
        """Creating two plans with the same issue number assigns distinct UUID plan IDs.

        With UUID-derived IDs, the issue number is stored in metadata only and does not
        constrain plan_id uniqueness. Each create call generates a new UUID plan_id.
        """
        import re

        # Arrange
        tasks = [_make_task_def("T01", "Task")]

        # Act — two plans for the same issue succeed (UUID IDs are collision-resistant)
        plan_a = backend.create_plan("slug-a", "Goal A", tasks, issue=9001)
        plan_b = backend.create_plan("slug-b", "Goal B", tasks, issue=9001)

        # Assert — each plan gets a unique UUID plan_id
        assert re.match(r"^P[0-9a-f]{8}$", plan_a["plan_id"]), f"Expected UUID plan_id, got: {plan_a['plan_id']!r}"
        assert re.match(r"^P[0-9a-f]{8}$", plan_b["plan_id"]), f"Expected UUID plan_id, got: {plan_b['plan_id']!r}"
        assert plan_a["plan_id"] != plan_b["plan_id"], "Two create calls must produce distinct plan IDs"

    def test_read_nonexistent_plan_raises(self, backend: TaskBackend) -> None:
        """Reading a plan that does not exist should raise PlanNotFoundError."""
        with pytest.raises(PlanNotFoundError):
            backend.read_plan("P99999")

    def test_list_plans_empty(self, backend: TaskBackend) -> None:
        """Listing plans when none have been created should return an empty list."""
        result = backend.list_plans()
        assert result == []

    def test_list_plans_with_search(self, backend: TaskBackend) -> None:
        """Search filter should return only plans whose feature/goal contains the term."""
        # Arrange
        backend.create_plan("apple-feature", "Build apple UI", [_make_task_def("T01", "Task")])
        backend.create_plan("banana-feature", "Build banana API", [_make_task_def("T01", "Task")])

        # Act
        results = backend.list_plans(search="apple")

        # Assert — only the first plan matches
        assert len(results) == 1
        assert "apple" in results[0]["feature"].lower() or "apple" in results[0]["goal"].lower()

    # ------------------------------------------------------------------
    # Task access
    # ------------------------------------------------------------------

    def test_read_task(self, backend: TaskBackend) -> None:
        """Reading an existing task should return its full data."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "My task", agent="bot")])
        plan_id = created["plan_id"]

        # Act
        task = backend.read_task(plan_id, "T01")

        # Assert
        assert task["id"] == "T01"
        assert task["title"] == "My task"

    def test_read_nonexistent_task_raises(self, backend: TaskBackend) -> None:
        """Reading a task ID that does not exist should raise TaskNotFoundError."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act / Assert
        with pytest.raises(TaskNotFoundError):
            backend.read_task(plan_id, "T99")

    def test_claim_task_success(self, backend: TaskBackend) -> None:
        """Claiming a not-started task should return True and update status."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act
        result = backend.claim_task(plan_id, "T01")

        # Assert
        assert result is True
        task = backend.read_task(plan_id, "T01")
        assert task["status"] == "in-progress"

    def test_claim_task_already_claimed_returns_false(self, backend: TaskBackend) -> None:
        """Claiming a task that is already in-progress should return False."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]
        backend.claim_task(plan_id, "T01")  # First claim succeeds

        # Act
        result = backend.claim_task(plan_id, "T01")

        # Assert
        assert result is False

    def test_claim_task_terminal_state_returns_false(self, backend: TaskBackend) -> None:
        """Claiming a task with a terminal status (complete) should return False."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]
        backend.update_task_status(plan_id, "T01", "complete")

        # Act
        result = backend.claim_task(plan_id, "T01")

        # Assert
        assert result is False

    def test_update_task_status(self, backend: TaskBackend) -> None:
        """Updating a task's status should persist and be visible on read."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act
        backend.update_task_status(plan_id, "T01", "complete")

        # Assert
        task = backend.read_task(plan_id, "T01")
        assert task["status"] == "complete"

    def test_update_task_status_invalid_raises(self, backend: TaskBackend) -> None:
        """Updating a task with an invalid status value should raise TaskValidationError."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act / Assert
        with pytest.raises(TaskValidationError):
            backend.update_task_status(plan_id, "T01", "not-a-real-status")

    def test_update_task_fields(self, backend: TaskBackend) -> None:
        """Updating task fields should persist the new values."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act
        backend.update_task_fields(plan_id, "T01", {"priority": 5, "complexity": "high"})

        # Assert
        task = backend.read_task(plan_id, "T01")
        assert task["priority"] == 5
        assert task["complexity"] == "high"

    def test_update_plan_fields(self, backend: TaskBackend) -> None:
        """Updating plan-level context should persist on subsequent reads."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act
        backend.update_plan_fields(plan_id, context="Updated context narrative")

        # Assert
        plan = backend.read_plan(plan_id)
        assert "Updated context narrative" in plan["context"]

    def test_append_task_section(self, backend: TaskBackend) -> None:
        """Appending to a named YAML field should persist the content on read_task.

        Uses ``context_notes`` as the section name — a concrete TaskData field
        that LocalYamlTaskProvider maps to the ``context_notes`` YAML key.
        InMemoryTaskProvider writes to the same field by name.
        """
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act — use a known TaskData field name as the section identifier
        backend.append_task_section(plan_id, "T01", "context_notes", "Found something important.")

        # Assert
        task = backend.read_task(plan_id, "T01")
        context_notes = task.get("context_notes", "")
        assert "Found something important." in context_notes

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def test_get_ready_tasks_no_deps(self, backend: TaskBackend) -> None:
        """Tasks with no dependencies and not-started status should be ready."""
        # Arrange
        tasks = [_make_task_def("T01", "Task 1"), _make_task_def("T02", "Task 2")]
        created = backend.create_plan("my-plan", "Goal", tasks)
        plan_id = created["plan_id"]

        # Act
        ready = backend.get_ready_tasks(plan_id)

        # Assert
        ready_ids = {t["id"] for t in ready}
        assert "T01" in ready_ids
        assert "T02" in ready_ids

    def test_get_ready_tasks_with_deps(self, backend: TaskBackend) -> None:
        """A task whose dependency is complete should appear in ready tasks."""
        # Arrange
        tasks = [_make_task_def("T01", "First task"), _make_task_def("T02", "Second task", dependencies=["T01"])]
        created = backend.create_plan("my-plan", "Goal", tasks)
        plan_id = created["plan_id"]
        backend.update_task_status(plan_id, "T01", "complete")

        # Act
        ready = backend.get_ready_tasks(plan_id)

        # Assert — T01 is complete so T02 is now ready; T01 itself is not not-started
        ready_ids = {t["id"] for t in ready}
        assert "T02" in ready_ids
        assert "T01" not in ready_ids

    def test_get_ready_tasks_blocked(self, backend: TaskBackend) -> None:
        """A task whose dependency is not complete should NOT appear in ready tasks."""
        # Arrange
        tasks = [_make_task_def("T01", "First task"), _make_task_def("T02", "Second task", dependencies=["T01"])]
        created = backend.create_plan("my-plan", "Goal", tasks)
        plan_id = created["plan_id"]
        # T01 is not-started (not complete) so T02 is blocked

        # Act
        ready = backend.get_ready_tasks(plan_id)

        # Assert — T01 is ready (no deps); T02 is blocked
        ready_ids = {t["id"] for t in ready}
        assert "T01" in ready_ids
        assert "T02" not in ready_ids

    # ------------------------------------------------------------------
    # Plan status
    # ------------------------------------------------------------------

    def test_get_plan_status(self, backend: TaskBackend) -> None:
        """Plan status should report correct counts, ready/blocked lists, and percentage."""
        # Arrange
        tasks = [
            _make_task_def("T01", "Task 1"),
            _make_task_def("T02", "Task 2"),
            _make_task_def("T03", "Task 3", dependencies=["T01"]),
        ]
        created = backend.create_plan("my-plan", "Goal", tasks)
        plan_id = created["plan_id"]
        backend.update_task_status(plan_id, "T01", "complete")

        # Act
        status = backend.get_plan_status(plan_id)

        # Assert
        assert status["total_tasks"] == 3
        by_status = cast("dict[str, int]", status["by_status"])
        assert isinstance(by_status, dict)
        assert by_status.get("complete") == 1
        assert by_status.get("not-started") == 2

        ready_tasks = status["ready_tasks"]
        assert isinstance(ready_tasks, list)
        # T02 (no deps) and T03 (dep T01 is complete) are both ready
        assert "T02" in ready_tasks
        assert "T03" in ready_tasks

        assert isinstance(status["completion_pct"], float)
        assert status["has_cycles"] is False

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def test_store_and_read_document(self, backend: TaskBackend) -> None:
        """Storing a document and reading it back via the handle should round-trip."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]

        # Act
        handle = backend.store_document(
            plan_id=plan_id,
            task_id="T01",
            stage="architect",
            doc_type="spec",
            title="Architecture Spec",
            content="# Architecture\n\nDetails here.",
            fmt="md",
        )
        doc = backend.read_document(handle)

        # Assert
        assert doc["content"] == "# Architecture\n\nDetails here."
        assert doc["title"] == "Architecture Spec"
        assert doc["stage"] == "architect"
        assert doc["doc_type"] == "spec"
        assert doc["fmt"] == "md"
        assert doc["owner_type"] == "task"
        assert doc["owner_id"] == "T01"

    def test_read_document_missing_handle_raises(self, backend: TaskBackend) -> None:
        """Reading a document with an unknown content_ref should raise DocumentNotFoundError."""
        # Arrange
        created = backend.create_plan("my-plan", "Goal", [_make_task_def("T01", "Task")])
        plan_id = created["plan_id"]
        # Store a document to get a valid handle shape, then corrupt it
        handle = backend.store_document(
            plan_id=plan_id, task_id=None, stage="context", doc_type="notes", title="Notes", content="content"
        )
        bad_handle = {**handle, "content_ref": "nonexistent://fake-ref"}

        # Act / Assert
        with pytest.raises(DocumentNotFoundError):
            backend.read_document(bad_handle)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # plan_id durability
    # ------------------------------------------------------------------

    def test_plan_id_stored_in_record(self, backend: TaskBackend) -> None:
        """plan_id must be stored in the plan record itself, not only in the filename.

        Reading a plan back must return the same plan_id regardless of how the
        backend resolves the record — the ID must survive round-trips without
        depending on the filename or path.
        """
        # Arrange
        tasks = [_make_task_def("T01", "Task")]

        # Act
        created = backend.create_plan("my-slug", "Do the thing", tasks)
        plan_id = created["plan_id"]
        read_back = backend.read_plan(plan_id)

        # Assert — plan_id is present in the stored record, not derived at read time
        assert read_back["plan_id"] == plan_id

    def test_plan_id_preserved_in_list(self, backend: TaskBackend) -> None:
        """list_plans must return the stored plan_id for each plan."""
        # Arrange
        tasks = [_make_task_def("T01", "Task")]
        created = backend.create_plan("my-slug", "Do the thing", tasks)
        plan_id = created["plan_id"]

        # Act
        summaries = backend.list_plans()

        # Assert — the summary contains the same plan_id that was assigned at create time
        assert len(summaries) == 1
        assert summaries[0]["plan_id"] == plan_id

    # ------------------------------------------------------------------
    # Protocol structural check
    # ------------------------------------------------------------------

    def test_isinstance_check(self, backend: TaskBackend) -> None:
        """Backend instance should satisfy the runtime-checkable TaskBackend Protocol."""
        assert isinstance(backend, TaskBackend)

    # ------------------------------------------------------------------
    # append_task — #1770 RED-PHASE conformance case
    # ------------------------------------------------------------------
    # These tests FAIL in the red phase with:
    #   AttributeError: object has no attribute 'append_task'
    # or NotImplementedError if the Protocol stub is added without implementation.
    # The green phase implements append_task on all three backends and these
    # tests must pass for ALL parametrized variants.
    # ------------------------------------------------------------------

    def test_append_task_adds_task_to_plan(self, backend: TaskBackend) -> None:
        """append_task adds a single task to a plan with empty task list.

        AC #2/#5: TaskBackend.append_task must append a single task to the plan
        and make it visible on the subsequent read_plan call.

        Arrange: create a plan with zero tasks.
        Act: call backend.append_task with a TaskDefinitionDict for T01.
        Assert: read_plan returns a plan with exactly one task; task fields match.
        """
        # Arrange
        created = backend.create_plan("my-slug", "Do the thing", [])
        plan_id = created["plan_id"]

        task_def = _make_task_def("T01", "First appended task")

        # Act
        backend.append_task(plan_id, task_def)

        # Assert
        plan = backend.read_plan(plan_id)
        assert len(plan["tasks"]) == 1
        assert plan["tasks"][0]["id"] == "T01"
        assert plan["tasks"][0]["title"] == "First appended task"

    def test_append_task_preserves_existing_tasks(self, backend: TaskBackend) -> None:
        """append_task adds a task without disturbing existing tasks.

        AC #3/#5: appending to a plan with existing tasks must not overwrite or
        reorder the existing task list.

        Arrange: create a plan with one task (T01); append a second task (T02).
        Act: call backend.append_task(plan_id, T02_def).
        Assert: read_plan returns two tasks in insertion order: T01 then T02.
        """
        # Arrange
        created = backend.create_plan("two-task-plan", "Two tasks", [_make_task_def("T01", "Original task")])
        plan_id = created["plan_id"]

        # Act
        backend.append_task(plan_id, _make_task_def("T02", "Appended task"))

        # Assert
        plan = backend.read_plan(plan_id)
        assert len(plan["tasks"]) == 2
        assert plan["tasks"][0]["id"] == "T01"
        assert plan["tasks"][1]["id"] == "T02"

    def test_append_task_plan_not_found_raises(self, backend: TaskBackend) -> None:
        """append_task raises PlanNotFoundError when plan_id does not exist.

        AC #6: each backend must raise PlanNotFoundError (not a silent no-op)
        when append_task is called for an unknown plan_id.

        Arrange: backend has no plans.
        Act: call backend.append_task with plan_id 'P99999'.
        Assert: PlanNotFoundError is raised containing 'P99999'.
        """
        # Arrange — backend starts empty; no plans exist

        # Act / Assert
        with pytest.raises(PlanNotFoundError):
            backend.append_task("P99999", _make_task_def("T01", "Task"))

    def test_append_task_duplicate_task_id_raises(self, backend: TaskBackend) -> None:
        """append_task raises an error when a duplicate task ID is appended.

        AC #6: each backend must raise TaskValidationError when a task with an
        already-existing ID is appended.

        Arrange: create a plan with T01; append T01 again.
        Act: second append_task call with the same task ID.
        Assert: TaskValidationError is raised.
        """
        from sam_schema.core.exceptions import TaskValidationError

        # Arrange
        created = backend.create_plan("dup-plan", "Goal", [_make_task_def("T01", "Original")])
        plan_id = created["plan_id"]

        # Act / Assert — appending a duplicate ID must be rejected
        with pytest.raises(TaskValidationError):
            backend.append_task(plan_id, _make_task_def("T01", "Duplicate"))

    def test_append_multiple_tasks_preserves_order(self, backend: TaskBackend) -> None:
        """N sequential append_task calls preserve insertion order.

        AC #3: after N sequential append_task calls, read_plan must return tasks
        in the same order they were appended.

        Arrange: create empty plan; append T01..T05 sequentially.
        Act: read plan.
        Assert: tasks are ordered T01, T02, T03, T04, T05.
        """
        # Arrange
        created = backend.create_plan("ordered-plan", "Order test", [])
        plan_id = created["plan_id"]

        # Act
        for i in range(1, 6):
            backend.append_task(plan_id, _make_task_def(f"T{i:02d}", f"Task {i}"))

        # Assert
        plan = backend.read_plan(plan_id)
        assert len(plan["tasks"]) == 5
        task_ids = [t["id"] for t in plan["tasks"]]
        assert task_ids == ["T01", "T02", "T03", "T04", "T05"], f"Expected ordered IDs T01..T05, got: {task_ids}"
