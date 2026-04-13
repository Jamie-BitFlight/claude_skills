"""TaskBackend Protocol — implementation-agnostic abstraction for SAM plan storage.

This module defines the TaskBackend Protocol. All provider implementations
(LocalYamlTaskProvider, GitHubTaskProvider, InMemoryTaskProvider) must satisfy
this Protocol. The query layer depends on this interface; storage-specific
implementations live in ``sam_schema.core.backends``.

All protocol methods are synchronous. The MCP layer wraps calls in
``asyncio.to_thread()`` when needed — matching the pattern established in
``backlog_core.backend_protocol``.

Dependency direction (must remain acyclic):
    task_backend_types <- task_backend
    task_backend is imported by: task_config, query layer, server
    task_backend does NOT import from: backends, yaml_reader, yaml_writer, query
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.models import Task
    from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

__all__ = ["TaskBackend"]


@runtime_checkable
class TaskBackend(Protocol):
    """Protocol defining the backend contract for SAM plan and task storage.

    All methods are synchronous. The MCP layer wraps calls in
    ``asyncio.to_thread()`` when needed.

    Method groups:
    - **Plan lifecycle**: create_plan, read_plan, list_plans, update_plan_fields
    - **Task access**: read_task, claim_task, update_task_status,
      update_task_fields, append_task_section, get_ready_tasks, get_plan_status
    - **Documents**: store_document, read_document
    """

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
        """Create a new plan with the given slug and task definitions.

        Args:
            slug: Human-readable identifier slug for the plan.
            goal: One-sentence goal statement for the plan.
            tasks: Ordered sequence of validated Task models to create.
            context: Optional plan-level context narrative.
            issue: Optional GitHub issue number to associate with this plan.
            acceptance_criteria: Optional plan-level acceptance criteria markdown.

        Returns:
            PlanData containing the created plan with backend-assigned plan_id.

        Raises:
            PlanExistsError: When a plan with the resolved plan_id already exists.
            TaskValidationError: When any task definition fails schema validation.
        """
        ...

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by its backend-assigned identifier.

        Args:
            plan_id: Backend-assigned plan identifier (e.g. ``"P912"``).

        Returns:
            PlanData containing the full plan with all tasks.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
        """
        ...

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """Return lightweight summaries for all plans, optionally filtered.

        Args:
            search: Optional substring to filter plan feature names or goals.
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return. None means no limit.

        Returns:
            List of PlanSummary TypedDicts, ordered by plan_id.
        """
        ...

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level fields on a plan.

        Args:
            plan_id: Backend-assigned plan identifier.
            context: When provided, replaces the plan context narrative.
            set_fields: Optional mapping of field names to new values.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
        """
        ...

    # ------------------------------------------------------------------
    # Task access
    # ------------------------------------------------------------------

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task from a plan.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan (e.g. ``"T02"``).

        Returns:
            TaskData containing full task state.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        ...

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Attempt to claim a task for execution.

        Implements a read-check-write pattern: only transitions a task from
        ``not-started`` to ``in-progress``. Concurrent claims from multiple
        callers result in exactly one succeeding (returns True) and the rest
        returning False.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.

        Returns:
            True if the claim succeeded (status was not-started and is now
            in-progress). False if the task was already in-progress, complete,
            or otherwise not claimable.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        ...

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update the status of a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            status: New status string. Must be a valid
                :class:`~sam_schema.core.models.TaskStatus` value.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When task_id does not exist within the plan.
            TaskValidationError: When status is not a valid TaskStatus value.
        """
        ...

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Set one or more scalar fields on a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            fields: Mapping of field names to new values. Only the listed
                fields are modified; unlisted fields are preserved.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        ...

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace the stored task with the provided Task model.

        Serializes the full Task model to the backend's native storage format
        and writes it atomically, replacing all fields of the existing task
        entry.  Fields not present on the Task model are not preserved.

        Args:
            plan_id: Backend-assigned plan identifier.
            task: Fully-validated Task model whose ``id`` identifies the target
                task within the plan.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When ``task.id`` does not exist within the plan.
        """
        ...

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append markdown content to a named section of a task body.

        If the section does not exist, it is created. If it already exists,
        the content is appended below the existing section content.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            section_name: Markdown heading name for the section (without ``##``).
            content: Markdown content to append to the section.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        ...

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a single task to an existing plan.

        **Concurrency — single-writer assumption**: ``TaskBackend.append_task`` is NOT
        required to be atomic under concurrent writers. Callers MUST serialize writes to
        the same plan. Behavior under concurrent writes is undefined — backends are not
        required to detect, reject, or recover from it. See ADR-1770-1.

        Args:
            plan_id: Plan identifier returned by create_plan.
            task: Validated Task model to append. The caller (server layer) is
                responsible for validation via Pydantic before calling this method.
                Backends use ``task.model_dump()`` for format-specific serialization.

        Returns:
            Dict with append result: ``{"appended": True, "task_id": task.id}``.

        Raises:
            PlanNotFoundError: If plan_id does not exist.
            TaskValidationError: If the task ID duplicates an existing task in the plan.
        """
        ...

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Transition a plan from drafting state to ready state.

        **Concurrency — single-writer assumption**: ``TaskBackend.finalize_plan`` is NOT
        required to be atomic under concurrent writers. Callers MUST serialize writes to
        the same plan. Behavior under concurrent writes is undefined — backends are not
        required to detect, reject, or recover from it. See #1770 / ADR-1770-1.

        After finalize, the plan transitions from ``state="drafting"`` to
        ``state="ready"`` and becomes available for execution via
        ``sam_plan(action='ready')`` and ``/dh:implement-feature``. See #1770.

        Args:
            plan_id: Plan identifier.

        Returns:
            Dict with finalized=True and the new state.

        Raises:
            PlanNotFoundError: If plan_id does not exist.
        """
        ...

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return all tasks that are ready for dispatch.

        A task is ready when its status is ``not-started`` and all of its
        dependency tasks have status ``complete``. The dependency graph
        evaluation is performed in the query layer, not the backend.

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            List of TaskData for tasks ready to be claimed.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
        """
        ...

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return a summary dict of task status counts for a plan.

        The returned dict contains at minimum:
        - ``"feature"``: str — plan feature name
        - ``"total_tasks"``: int — total task count
        - ``"by_status"``: dict[str, int] — count per status value
        - ``"ready_tasks"``: list[str] — IDs of ready-to-dispatch tasks
        - ``"blocked_tasks"``: list[dict[str, list[str]]] — each entry maps a
          task ID to the list of unresolved dependency IDs
        - ``"completion_pct"``: float — percentage of tasks with status complete
        - ``"has_cycles"``: bool — True if the dependency graph contains a cycle

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            Status summary dict.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
        """
        ...

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Persist a document and return an opaque retrieval handle.

        Documents are associated with a plan (and optionally a task). The
        backend assigns a ``content_ref`` that is stored in the
        :class:`DocumentHandle`. Pass this handle to
        :meth:`read_document` to retrieve the content later.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Optional task identifier. None for plan-level documents.
            stage: Pipeline stage name (e.g. ``"architect"``, ``"feature-context"``).
            doc_type: Document type discriminator (e.g. ``"spec"``, ``"context"``).
            title: Human-readable document title.
            content: Raw document content.
            fmt: Format hint (e.g. ``"md"``, ``"yaml"``). Defaults to ``"md"``.

        Returns:
            DocumentHandle with backend-specific content_ref and metadata.

        Raises:
            PlanNotFoundError: When plan_id does not resolve to a known plan.
        """
        ...

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a document by its handle.

        Args:
            handle: DocumentHandle returned from a prior :meth:`store_document`
                call. The ``content_ref`` field is the primary lookup key.

        Returns:
            DocumentData containing the full document content and metadata.

        Raises:
            DocumentNotFoundError: When the content_ref in the handle cannot
                be resolved to a stored document.
        """
        ...
