"""InMemoryTaskProvider — in-memory TaskBackend implementation for testing.

Pure-Python implementation that stores all state in plain dicts and lists.
No filesystem access, no external dependencies. Designed as a test double
for conformance testing and unit testing of code that depends on TaskBackend.

Mirrors the pattern from backlog_core/backends/memory_backend.py.

Usage::

    from sam_schema.core.backends.memory import InMemoryTaskProvider
    from sam_schema.core.task_backend import TaskBackend

    backend = InMemoryTaskProvider()
    assert isinstance(backend, TaskBackend)
"""

from __future__ import annotations

import copy
import uuid
from typing import TYPE_CHECKING, Any, cast

from sam_schema.core.backends._utils import _now_iso, validate_appended_task
from sam_schema.core.dependencies import TERMINAL_STATUSES as _TERMINAL_STATUSES
from sam_schema.core.exceptions import (
    DocumentNotFoundError,
    PlanExistsError,
    PlanNotFoundError,
    TaskNotFoundError,
    TaskValidationError,
)
from sam_schema.core.models import PlanState, Task
from sam_schema.core.query import _new_plan_id

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.task_backend_types import (
        DocumentData,
        DocumentHandle,
        PlanData,
        PlanSummary,
        TaskData,
        TaskDefinitionDict,
    )

__all__ = ["InMemoryTaskProvider"]

# All valid TaskStatus values.
_VALID_STATUSES: frozenset[str] = frozenset({
    "not-started",
    "in-progress",
    "complete",
    "blocked",
    "deferred",
    "skipped",
})


def _task_def_to_task_data(task_def: TaskDefinitionDict) -> TaskData:
    """Convert a TaskDefinitionDict input TypedDict to a TaskData output TypedDict.

    Applies defaults for all optional fields absent from the input.

    Args:
        task_def: Input task definition from create_plan.

    Returns:
        TaskData dict with all required fields set and optional fields
        populated from the input where non-empty.
    """
    data: TaskData = {
        "id": task_def["id"],
        "title": task_def["title"],
        "status": task_def.get("status", "not-started"),
        "agent": task_def.get("agent"),
        "dependencies": list(task_def.get("dependencies", [])),
        "blocked_by": list(task_def.get("blocked_by", [])),
        "parallelize_with": list(task_def.get("parallelize_with", [])),
        "priority": task_def.get("priority", 3),
        "complexity": task_def.get("complexity", "medium"),
        "skills": list(task_def.get("skills", [])),
        "created": task_def.get("created") or _now_iso(),
        "started": task_def.get("started"),
        "completed": task_def.get("completed"),
        "last_activity": task_def.get("last_activity"),
        "body": task_def.get("body", ""),
        "description": task_def.get("description", ""),
    }
    # Optional content fields: include only when non-empty.
    for opt_field in (
        "objective",
        "requirements",
        "constraints",
        "expected_outputs",
        "acceptance_criteria",
        "verification_steps",
        "context_notes",
        "handoff",
    ):
        val = task_def.get(opt_field, "")  # type: ignore[literal-required]
        if val:
            data[opt_field] = val  # type: ignore[literal-required]

    # Analytical metadata.
    data["analysis_method"] = task_def.get("analysis_method", "none")  # type: ignore[typeddict-item]
    data["divergence_notes"] = task_def.get("divergence_notes", 0)  # type: ignore[typeddict-item]
    data["accuracy_risk"] = task_def.get("accuracy_risk", "low")  # type: ignore[typeddict-item]
    reason = task_def.get("reason", "")
    if reason:
        data["reason"] = reason  # type: ignore[typeddict-item]

    # Bookend fields.
    if task_def.get("is_bookend"):
        data["is_bookend"] = cast("bool", task_def["is_bookend"])  # type: ignore[typeddict-item]
    if task_def.get("bookend_type") is not None:
        data["bookend_type"] = cast("str | None", task_def["bookend_type"])  # type: ignore[typeddict-item]
    if task_def.get("issue_classification") is not None:
        data["issue_classification"] = cast("str | None", task_def["issue_classification"])  # type: ignore[typeddict-item]
    if task_def.get("github_issue") is not None:
        data["github_issue"] = cast("int | None", task_def["github_issue"])  # type: ignore[typeddict-item]

    return data


def _has_cycle(tasks: list[TaskData]) -> bool:
    """Detect dependency cycles in a task list using iterative DFS.

    Args:
        tasks: All tasks in the plan.

    Returns:
        True if at least one cycle exists, False otherwise.
    """
    # Build adjacency list: task_id -> list of dep_ids present in the plan.
    by_deps: dict[str, list[str]] = {t["id"]: list(t["dependencies"]) for t in tasks}
    all_ids: set[str] = set(by_deps)

    # Three-colour DFS: 0=unvisited, 1=in-stack, 2=done.
    colour: dict[str, int] = dict.fromkeys(all_ids, 0)

    def _dfs(start: str) -> bool:
        stack: list[tuple[str, int]] = [(start, 0)]
        in_stack: set[str] = set()
        while stack:
            node, idx = stack[-1]
            if idx == 0:
                colour[node] = 1
                in_stack.add(node)
            deps = by_deps.get(node, [])
            found_next = False
            while idx < len(deps):
                dep_id = deps[idx]
                idx += 1
                if dep_id not in all_ids:
                    continue
                if colour[dep_id] == 1:
                    return True
                if colour[dep_id] == 0:
                    stack[-1] = (node, idx)
                    stack.append((dep_id, 0))
                    found_next = True
                    break
            if not found_next:
                colour[node] = 2
                in_stack.discard(node)
                stack.pop()
        return False

    return any(_dfs(tid) for tid in all_ids if colour[tid] == 0)


class InMemoryTaskProvider:
    """In-memory TaskBackend for use in tests.

    All state lives in plain Python dicts. Every method is synchronous and
    has no side effects outside this instance. No filesystem access and no
    external dependencies.

    Plan IDs are auto-assigned as ``P`` + first 8 hex chars of a UUID4
    (e.g. ``Pa1b2c3d4``) for every new plan, regardless of whether an
    ``issue`` is provided. The ``issue`` value is stored in plan metadata
    but does not influence the plan ID.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        # plan_id -> PlanData (deep copies stored to prevent aliasing)
        self._plans: dict[str, PlanData] = {}
        # content_ref -> DocumentData
        self._documents: dict[str, DocumentData] = {}

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def create_plan(
        self,
        slug: str,
        goal: str,
        tasks: Sequence[Task],
        *,
        context: str | None = None,
        issue: int | None = None,
        acceptance_criteria: str | None = None,
    ) -> PlanData:
        """Create a new plan with an auto-assigned or issue-derived plan_id.

        Args:
            slug: Human-readable identifier slug for the plan.
            goal: One-sentence goal statement.
            tasks: Ordered list of validated Task models.
            context: Optional plan-level context narrative.
            issue: Optional GitHub issue number. When provided, the plan_id
                is ``P{issue}``; otherwise an auto-incremented ID is used.
            acceptance_criteria: Optional plan-level acceptance criteria markdown.

        Returns:
            PlanData with the assigned plan_id.

        Raises:
            PlanExistsError: When the resolved plan_id already exists.
            TaskValidationError: When any task definition is missing required fields.
        """
        plan_id = _new_plan_id()

        if plan_id in self._plans:
            raise PlanExistsError(plan_id)

        task_data_list: list[TaskData] = []
        for idx, task in enumerate(tasks):
            if not task.id:
                raise TaskValidationError(idx, "Task 'id' is required")
            if not task.title:
                raise TaskValidationError(idx, "Task 'title' is required")
            task_data_list.append(_task_def_to_task_data(cast("TaskDefinitionDict", task.model_dump(by_alias=False))))

        plan_data: PlanData = {
            "plan_id": plan_id,
            "feature": slug,
            "version": "1.0.0",
            "description": "",
            "goal": goal,
            "context": context or "",
            "acceptance_criteria": acceptance_criteria or "",
            "issue": str(issue) if issue is not None else None,
            "tasks": task_data_list,
            "source_path": None,
            "state": PlanState.DRAFTING if not tasks else PlanState.READY,
        }
        self._plans[plan_id] = copy.deepcopy(plan_data)
        return copy.deepcopy(plan_data)

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by its plan_id.

        Args:
            plan_id: Backend-assigned plan identifier (e.g. ``'P1'``).

        Returns:
            PlanData containing the full plan with all tasks.

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        return copy.deepcopy(self._plans[plan_id])

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """Return lightweight summaries for all plans, optionally filtered.

        Args:
            search: Optional substring to filter by feature name or goal.
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return. None means no limit.

        Returns:
            List of PlanSummary TypedDicts ordered by insertion order.
        """
        summaries: list[PlanSummary] = []
        for plan in self._plans.values():
            if search is not None:
                text = f"{plan['feature']} {plan['goal']} {plan['description']}"
                if search.lower() not in text.lower():
                    continue
            summary: PlanSummary = {
                "plan_id": plan["plan_id"],
                "feature": plan["feature"],
                "goal": plan["goal"],
                "description": plan["description"],
                "task_count": len(plan["tasks"]),
                "source_path": plan["source_path"],
            }
            if plan.get("issue") is not None:
                summary["issue"] = plan["issue"]
            if plan.get("backend_ref") is not None:
                summary["backend_ref"] = plan["backend_ref"]
            summaries.append(summary)

        paginated = summaries[offset:]
        if limit is not None:
            paginated = paginated[:limit]
        return paginated

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level fields on a plan.

        Args:
            plan_id: Backend-assigned plan identifier.
            context: When provided, replaces the plan context narrative.
            set_fields: Optional mapping of field names to new values.

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        plan = self._plans[plan_id]
        if context is not None:
            plan["context"] = context
        if set_fields:
            for key, value in set_fields.items():
                cast("dict[str, object]", plan)[key] = value

    # ------------------------------------------------------------------
    # Task access
    # ------------------------------------------------------------------

    def _find_task(self, plan_id: str, task_id: str) -> TaskData:
        """Find a task within a plan, returning a direct reference to stored state.

        Modifications to the returned dict affect stored state. For read-only
        operations, callers should deep-copy the result.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier to locate.

        Returns:
            TaskData dict (direct reference into stored state).

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        for task in self._plans[plan_id]["tasks"]:
            if task["id"] == task_id:
                return task
        raise TaskNotFoundError(plan_id, task_id)

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task from a plan.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan (e.g. ``'T02'``).

        Returns:
            TaskData containing full task state.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
        """
        return copy.deepcopy(self._find_task(plan_id, task_id))

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Attempt to claim a task by transitioning it from not-started to in-progress.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.

        Returns:
            True if the task was not-started and is now in-progress.
            False if the task was in any other status.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
        """
        task = self._find_task(plan_id, task_id)
        if task["status"] != "not-started":
            return False
        task["status"] = "in-progress"
        task["started"] = _now_iso()
        return True

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update the status of a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            status: New status string. Must be a valid TaskStatus value.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
            TaskValidationError: When status is not a valid TaskStatus value.
        """
        if status not in _VALID_STATUSES:
            raise TaskValidationError(0, f"Invalid status value: {status!r}")
        task = self._find_task(plan_id, task_id)
        task["status"] = status
        if status == "complete" and not task.get("completed"):
            task["completed"] = _now_iso()
        elif status == "in-progress" and not task.get("started"):
            task["started"] = _now_iso()

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Set one or more scalar fields on a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            fields: Mapping of field names to new values.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
        """
        task = self._find_task(plan_id, task_id)
        for key, value in fields.items():
            cast("dict[str, object]", task)[key] = value

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace the stored task with the provided Task model.

        Converts the Task model to a TaskData dict and substitutes the matching
        task entry by index in the plan's task list.

        Args:
            plan_id: Backend-assigned plan identifier.
            task: Fully-validated Task model whose ``id`` identifies the target
                task within the plan.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When ``task.id`` is not in the plan.
        """
        from sam_schema.core.backends.local_yaml import _task_to_task_data  # noqa: PLC0415

        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        tasks = self._plans[plan_id]["tasks"]
        for idx, stored in enumerate(tasks):
            if stored["id"] == task.id:
                tasks[idx] = _task_to_task_data(task)
                return
        raise TaskNotFoundError(plan_id, task.id)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append markdown content to a named section stored in ``context_notes``.

        Section content accumulates in the ``context_notes`` field to match
        ``LocalYamlTaskProvider`` behaviour, which uses the same field
        because the yaml_writer does not support direct writes to ``body``.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            section_name: Markdown heading name for the section (without ``##``).
            content: Markdown content to append to the section.

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskNotFoundError: When task_id is not in the plan.
        """
        task = self._find_task(plan_id, task_id)
        heading = f"## {section_name}"
        existing = task.get("context_notes", "")  # type: ignore[typeddict-item]
        if heading in existing:
            new_context = f"{existing}\n{content}"
        else:
            separator = "\n" if existing else ""
            new_context = f"{existing}{separator}{heading}\n\n{content}"
        task["context_notes"] = new_context  # type: ignore[typeddict-item]

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a single validated Task to an existing plan.

        Duplicate-ID check via ``validate_appended_task``; see ADR-1770-1 for the
        single-writer contract (callers must serialise writes to the same plan).

        Args:
            plan_id: Backend-assigned plan identifier.
            task: Validated Task model to append.

        Returns:
            Dict with ``appended`` (True) and ``task_id`` (the appended task's ID).

        Raises:
            PlanNotFoundError: When plan_id is not known.
            TaskValidationError: When the task ID already exists in the plan.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)

        existing_ids = {t["id"] for t in self._plans[plan_id]["tasks"]}
        validate_appended_task(task, existing_ids, plan_id)

        task_data = _task_def_to_task_data(cast("TaskDefinitionDict", task.model_dump(by_alias=False)))
        self._plans[plan_id]["tasks"].append(task_data)

        return {"appended": True, "task_id": task.id}

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Finalize a drafting plan, transitioning its state to 'ready'.

        Clears the drafting marker set during create_plan. See ADR-1770-1 for the
        single-writer contract (callers must serialise writes to the same plan).

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            Dict with ``finalized`` (True) and ``state`` ('ready').

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        # No-op guard: already ready — skip write, return early.
        if self._plans[plan_id].get("state") == PlanState.READY:
            return {"finalized": True, "state": PlanState.READY}
        self._plans[plan_id]["state"] = PlanState.READY
        return {"finalized": True, "state": PlanState.READY}

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return all tasks that are ready for dispatch.

        A task is ready when its status is ``not-started`` and all dependency
        tasks are in a terminal status (complete, deferred, or skipped).
        Dependencies referencing absent task IDs are treated as unsatisfied.

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            List of TaskData for tasks ready to be claimed.

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        tasks = self._plans[plan_id]["tasks"]
        status_by_id: dict[str, str] = {t["id"]: t["status"] for t in tasks}

        ready: list[TaskData] = []
        for task in tasks:
            if task["status"] != "not-started":
                continue
            if all(status_by_id.get(dep_id, "") in _TERMINAL_STATUSES for dep_id in task["dependencies"]):
                ready.append(copy.deepcopy(task))

        return ready

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return a summary dict of task status counts for a plan.

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            Dict with keys: ``feature``, ``total_tasks``, ``by_status``,
            ``ready_tasks``, ``blocked_tasks``, ``completion_pct``, ``has_cycles``.

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)
        plan = self._plans[plan_id]
        tasks = plan["tasks"]
        status_by_id: dict[str, str] = {t["id"]: t["status"] for t in tasks}

        by_status: dict[str, int] = {}
        for task in tasks:
            s = task["status"]
            by_status[s] = by_status.get(s, 0) + 1

        ready_task_ids: list[str] = []
        blocked_tasks: list[dict[str, list[str]]] = []
        for task in tasks:
            if task["status"] != "not-started":
                continue
            unsatisfied = [d for d in task["dependencies"] if status_by_id.get(d, "") not in _TERMINAL_STATUSES]
            if unsatisfied:
                blocked_tasks.append({task["id"]: unsatisfied})
            else:
                ready_task_ids.append(task["id"])

        total = len(tasks)
        complete_count = by_status.get("complete", 0)
        completion_pct = (complete_count / total * 100.0) if total > 0 else 0.0

        return {
            "feature": plan["feature"],
            "total_tasks": total,
            "by_status": by_status,
            "ready_tasks": ready_task_ids,
            "blocked_tasks": blocked_tasks,
            "completion_pct": completion_pct,
            "has_cycles": _has_cycle(tasks),
            "state": plan.get("state", PlanState.READY),
        }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Store a document and return an opaque retrieval handle.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Optional task identifier. None for plan-level documents.
            stage: Pipeline stage name (e.g. ``'architect'``).
            doc_type: Document type discriminator (e.g. ``'spec'``).
            title: Human-readable document title.
            content: Raw document content.
            fmt: Format hint. Defaults to ``'md'``.

        Returns:
            DocumentHandle with a ``mem://`` scheme content_ref.

        Raises:
            PlanNotFoundError: When plan_id is not known.
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id)

        ref_suffix = uuid.uuid4().hex[:8]
        owner_slug = task_id if task_id is not None else "plan"
        content_ref = f"mem://{plan_id}/{owner_slug}/{stage}/{doc_type}/{ref_suffix}"
        owner_type = "task" if task_id is not None else "plan"
        owner_id = task_id if task_id is not None else plan_id

        doc_data: DocumentData = {
            "content_ref": content_ref,
            "title": title,
            "content": content,
            "fmt": fmt,
            "version": None,
            "owner_type": owner_type,
            "owner_id": owner_id,
            "stage": stage,
            "doc_type": doc_type,
        }
        self._documents[content_ref] = doc_data

        handle: DocumentHandle = {
            "content_ref": content_ref,
            "owner_type": owner_type,
            "owner_id": owner_id,
            "stage": stage,
            "doc_type": doc_type,
            "title": title,
            "fmt": fmt,
        }
        return handle

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a document by its handle.

        Args:
            handle: DocumentHandle returned from a prior :meth:`store_document` call.
                The ``content_ref`` field is the primary lookup key.

        Returns:
            DocumentData with full document content.

        Raises:
            DocumentNotFoundError: When the content_ref is not found.
        """
        content_ref = handle["content_ref"]
        doc = self._documents.get(content_ref)
        if doc is None:
            raise DocumentNotFoundError(content_ref)
        return copy.deepcopy(doc)
