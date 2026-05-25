"""LocalYamlTaskProvider — TaskBackend implementation wrapping existing YAML I/O.

Wraps the existing YAML I/O stack (yaml_reader.py, yaml_writer.py, query.py)
behind the TaskBackend Protocol. This is the default backend preserving all
current single-machine behavior without modifying the underlying modules.

All plan/task operations delegate to the query layer. Document operations
write to ``plan_dir/{plan_id}/documents/`` on the local filesystem.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sam_schema.core import query
from sam_schema.core.addressing import AddressingError, resolve_plan_address
from sam_schema.core.backends._utils import validate_appended_task
from sam_schema.core.exceptions import (
    DocumentNotFoundError,
    PlanExistsError,
    PlanNotFoundError,
    TaskNotFoundError,
    TaskValidationError,
)
from sam_schema.core.models import Plan, PlanState, Task, TaskStatus
from sam_schema.readers.detect import FormatDetectionError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

__all__ = ["LocalYamlTaskProvider"]

# Extract plan_id from a plan file stem.
# Matches both legacy numeric IDs (e.g. "P912" from "P912-migrate-...")
# and UUID-derived hex IDs (e.g. "Pa1b2c3d4" from "Pa1b2c3d4-migrate-...").
_P_STEM_RE = re.compile(r"^(P[0-9a-f]+)-", re.IGNORECASE)
_TASKS_STEM_RE = re.compile(r"^tasks-(\d+)-")
_TASK_VALIDATION_RE = re.compile(r"Task at index (\d+) failed validation: (.+)", re.DOTALL)


def _plan_id_from_path(path: Path) -> str:
    """Extract the plan_id string (e.g. 'P912') from a plan file path.

    Args:
        path: Path to the plan file or directory.

    Returns:
        Plan identifier string derived from the file stem.
    """
    stem = path.stem
    m = _P_STEM_RE.match(stem)
    if m:
        return m.group(1)
    m2 = _TASKS_STEM_RE.match(stem)
    if m2:
        return f"P{m2.group(1)}"
    return stem


def _populate_task_content_fields(data: TaskData, task: Task) -> None:
    """Populate optional markdown content fields on a TaskData dict in-place.

    Adds fields only when non-empty, keeping the dict compact.

    Args:
        data: TaskData dict to populate (modified in place).
        task: Source Task model.
    """
    if task.objective:
        data["objective"] = task.objective
    if task.requirements:
        data["requirements"] = task.requirements
    if task.constraints:
        data["constraints"] = task.constraints
    if task.expected_outputs:
        data["expected_outputs"] = task.expected_outputs
    if task.acceptance_criteria:
        data["acceptance_criteria"] = task.acceptance_criteria
    if task.verification_steps:
        data["verification_steps"] = task.verification_steps
    if task.context_notes:
        data["context_notes"] = task.context_notes
    if task.handoff:
        data["handoff"] = task.handoff


def _task_to_task_data(task: Task) -> TaskData:
    """Convert a Task Pydantic model to a TaskData TypedDict.

    Args:
        task: Task model to convert.

    Returns:
        TaskData dict with all required fields and any non-empty optional fields.
    """
    data: TaskData = {
        "id": task.id,
        "title": task.title,
        "status": str(task.status),
        "agent": task.agent,
        "dependencies": list(task.dependencies),
        "blocked_by": list(task.blocked_by),
        "parallelize_with": list(task.parallelize_with),
        "priority": int(task.priority),
        "complexity": str(task.complexity),
        "skills": list(task.skills),
        "created": task.created.isoformat() if task.created else None,
        "started": task.started.isoformat() if task.started else None,
        "completed": task.completed.isoformat() if task.completed else None,
        "last_activity": task.last_activity.isoformat() if task.last_activity else None,
        "body": task.body,
        "description": task.description,
    }
    _populate_task_content_fields(data, task)
    if task.issue_classification is not None:
        data["issue_classification"] = str(task.issue_classification)
    data["analysis_method"] = str(task.analysis_method)
    data["divergence_notes"] = task.divergence_notes
    data["accuracy_risk"] = task.accuracy_risk
    if task.reason:
        data["reason"] = task.reason
    if task.is_bookend:
        data["is_bookend"] = task.is_bookend
    if task.bookend_type is not None:
        data["bookend_type"] = str(task.bookend_type)
    if task.github_issue is not None:
        data["github_issue"] = task.github_issue
    return data


def _plan_to_plan_data(plan: Plan, plan_id: str) -> PlanData:
    """Convert a Plan Pydantic model to a PlanData TypedDict.

    Args:
        plan: Plan model to convert.
        plan_id: Backend-assigned plan identifier (e.g. 'P912').

    Returns:
        PlanData dict with all required fields populated.
    """
    data: PlanData = {
        "plan_id": plan_id,
        "feature": plan.feature,
        "version": plan.version,
        "description": plan.description,
        "goal": plan.goal or "",
        "context": plan.context or "",
        "acceptance_criteria": plan.acceptance_criteria or "",
        "issue": plan.issue,
        "tasks": [_task_to_task_data(t) for t in plan.tasks],
        "source_path": str(plan.source_path) if plan.source_path else None,
    }
    if plan.architecture is not None:
        data["architecture"] = plan.architecture
    if plan.feature_context is not None:
        data["feature_context"] = plan.feature_context
    if plan.codebase_patterns is not None:
        data["codebase_patterns"] = plan.codebase_patterns
    if plan.backend_ref is not None:
        data["backend_ref"] = plan.backend_ref
    data["state"] = plan.state
    data["autonomy"] = plan.autonomy
    if plan.acceptance_criteria_structured:
        data["acceptance_criteria_structured"] = [c.model_dump() for c in plan.acceptance_criteria_structured]
    return data


class LocalYamlTaskProvider:
    """TaskBackend implementation wrapping the existing YAML I/O stack.

    All plan and task operations delegate to query.py, which in turn calls
    yaml_reader.py and yaml_writer.py. Document operations write to the
    local filesystem under ``plan_dir/{plan_id}/documents/``.

    This is the default backend that preserves existing single-machine behavior.

    Args:
        plan_dir: Root directory for plan YAML files. Defaults to
            ``dh_paths.plan_dir()`` when not provided.
    """

    def __init__(self, plan_dir: Path | None = None) -> None:
        """Initialize with an optional plan directory.

        Args:
            plan_dir: Root directory for plan YAML files. When None,
                resolves via ``dh_paths.plan_dir()``.

        Raises:
            RuntimeError: If plan_dir is None and dh_paths is not importable.
        """
        if plan_dir is None:
            import dh_paths  # noqa: PLC0415

            plan_dir = dh_paths.plan_dir()
        self._plan_dir: Path = plan_dir
        # Per-plan task-ID cache — avoids repeated YAML parse+deserialize when
        # calling append_task multiple times on the same plan in sequence.
        # Keyed by plan_id (str); invalidated on finalize_plan.
        self._task_id_cache: dict[str, set[str]] = {}

    def _resolve_path(self, plan_id: str) -> Path:
        """Resolve a plan_id to its filesystem path.

        Args:
            plan_id: Backend-assigned plan identifier (e.g. 'P912').

        Returns:
            Path to the plan file or directory.

        Raises:
            PlanNotFoundError: When the plan_id cannot be resolved.
        """
        try:
            return resolve_plan_address(plan_id, self._plan_dir)
        except (AddressingError, FileNotFoundError) as exc:
            raise PlanNotFoundError(plan_id) from exc

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
        """Create a new plan and write it to disk as a YAML file.

        Delegates to ``query.create_plan()``. The ``acceptance_criteria``
        parameter is accepted for Protocol compatibility but is not written
        by the underlying query layer; use ``update_plan_fields()`` after
        creation to set it.

        Args:
            slug: Human-readable identifier slug for the plan.
            goal: One-sentence goal statement.
            tasks: Ordered list of validated Task models.
            context: Optional plan-level context narrative.
            issue: Optional GitHub issue number.
            acceptance_criteria: Accepted but not written by this backend.
                Use ``update_plan_fields()`` post-creation to set it.

        Returns:
            PlanData with backend-assigned plan_id.

        Raises:
            PlanExistsError: When a plan with the resolved plan_id already exists.
            TaskValidationError: When any task definition fails validation.
        """
        task_dicts: list[dict[str, Any]] = [t.model_dump(by_alias=False, exclude_none=True) for t in tasks]
        try:
            plan = query.create_plan(
                slug=slug, goal=goal, tasks=task_dicts, plan_dir=self._plan_dir, context=context, issue=issue
            )
        except ValueError as exc:
            msg = str(exc)
            if "already exists" in msg:
                plan_number = str(issue) if issue is not None else slug
                raise PlanExistsError(f"P{plan_number}") from exc
            m = _TASK_VALIDATION_RE.search(msg)
            if m:
                raise TaskValidationError(int(m.group(1)), m.group(2)) from exc
            raise TaskValidationError(0, msg) from exc

        if not tasks:
            from sam_schema.writers.yaml_writer import write_plan  # noqa: PLC0415

            plan = plan.model_copy(update={"state": PlanState.DRAFTING})
            if plan.source_path is not None:
                write_plan(plan, plan.source_path, force_single=True)

        plan_id = _plan_id_from_path(plan.source_path) if plan.source_path else slug
        return _plan_to_plan_data(plan, plan_id)

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by its backend-assigned identifier.

        Args:
            plan_id: Backend-assigned plan identifier (e.g. 'P912').

        Returns:
            PlanData containing the full plan with all tasks.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
        """
        path = self._resolve_path(plan_id)
        try:
            result = query.load_plan(path)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc
        # Prefer the plan_id stored in the record; fall back to filename-derived
        # value for backwards compatibility with pre-existing files.
        effective_plan_id = result.plan.plan_id or _plan_id_from_path(path)
        return _plan_to_plan_data(result.plan, effective_plan_id)

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """Return lightweight summaries for all plans, optionally filtered.

        Args:
            search: Optional substring to filter by feature name or goal.
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return. None means no limit.

        Returns:
            List of PlanSummary TypedDicts ordered by filename.
        """
        if not self._plan_dir.exists():
            return []

        candidates = sorted(c for c in self._plan_dir.iterdir() if c.suffix in {".yaml", ".md"} or c.is_dir())
        summaries: list[PlanSummary] = []
        for candidate in candidates:
            try:
                result = query.load_plan(candidate)
                plan = result.plan
                if search is not None:
                    text = f"{plan.feature} {plan.goal or ''} {plan.description}"
                    if search.lower() not in text.lower():
                        continue
                # Prefer the plan_id stored in the record; fall back to filename-derived
                # value for backwards compatibility with pre-existing files.
                plan_id = plan.plan_id or _plan_id_from_path(candidate)
                summary: PlanSummary = {
                    "plan_id": plan_id,
                    "feature": plan.feature,
                    "goal": plan.goal or "",
                    "description": plan.description,
                    "task_count": len(plan.tasks),
                    "source_path": str(plan.source_path or candidate),
                }
                if plan.issue is not None:
                    summary["issue"] = plan.issue
                if plan.backend_ref is not None:
                    summary["backend_ref"] = plan.backend_ref
                summaries.append(summary)
            except (FileNotFoundError, FormatDetectionError, ValueError, TypeError):
                continue

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
            PlanNotFoundError: When plan_id cannot be resolved.
        """
        path = self._resolve_path(plan_id)
        try:
            query.update_plan_fields(path, context=context, set_fields=set_fields)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc

    # ------------------------------------------------------------------
    # Task access
    # ------------------------------------------------------------------

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task from a plan.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan (e.g. 'T02').

        Returns:
            TaskData containing full task state.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        plan_data = self.read_plan(plan_id)
        for task_data in plan_data["tasks"]:
            if task_data["id"] == task_id:
                return task_data
        raise TaskNotFoundError(plan_id, task_id)

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Attempt to claim a task by transitioning it to in-progress.

        Returns True if the task was in not-started status and is now
        in-progress. Returns False if the task was already claimed,
        complete, or otherwise not claimable.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.

        Returns:
            True if claim succeeded, False if not claimable.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        path = self._resolve_path(plan_id)
        try:
            query.claim_task(path, task_id)
        except ValueError:
            # Task is not in not-started status — already claimed or terminal.
            return False
        except KeyError as exc:
            raise TaskNotFoundError(plan_id, task_id) from exc
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc
        return True

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update the status of a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            status: New status string (must be a valid TaskStatus value).

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When task_id does not exist within the plan.
            TaskValidationError: When status is not a valid TaskStatus value.
        """
        try:
            task_status = TaskStatus(status)
        except ValueError as exc:
            raise TaskValidationError(0, f"Invalid status value: {status!r}") from exc
        path = self._resolve_path(plan_id)
        try:
            query.update_status(path, task_id, task_status)
        except KeyError as exc:
            raise TaskNotFoundError(plan_id, task_id) from exc
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Set one or more scalar fields on a task.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            fields: Mapping of field names to new values.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        path = self._resolve_path(plan_id)
        try:
            query.update_plan_fields(path, task_id=task_id, set_fields=fields)
        except KeyError as exc:
            raise TaskNotFoundError(plan_id, task_id) from exc
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace the stored task with the provided Task model.

        Loads the full plan, substitutes the matching task in the task list,
        then writes the plan back using ``write_plan``.  This preserves all
        native YAML types (list fields serialise as sequences, not repr strings)
        and handles fields like ``body`` that the field-level update path does
        not support.

        Args:
            plan_id: Backend-assigned plan identifier.
            task: Fully-validated Task model whose ``id`` identifies the target
                task within the plan.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When ``task.id`` does not exist within the plan.
        """
        from sam_schema.writers.yaml_writer import write_plan  # noqa: PLC0415

        path = self._resolve_path(plan_id)
        try:
            result = query.load_plan(path)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc

        plan = result.plan
        task_ids = [t.id for t in plan.tasks]
        if task.id not in task_ids:
            raise TaskNotFoundError(plan_id, task.id)

        updated_tasks = [task if t.id == task.id else t for t in plan.tasks]
        updated_plan = plan.model_copy(update={"tasks": updated_tasks})
        write_plan(updated_plan, path, force_single=True)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append markdown content to a named section of a task's context_notes.

        Reads the current ``context_notes`` field. If the ``## {section_name}``
        heading is absent, prepends it before the content; if the heading already
        exists, appends only the content. Writes back via ``update_plan_fields``.

        Note: Content is stored in ``task["context_notes"]``, not ``task["body"]``.
        The yaml_writer does not support direct writes to the body field.
        See #1492 for the cross-backend divergence: GitHubTaskProvider writes to
        ``body``; this backend writes to ``context_notes``.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            section_name: Markdown heading name for the section (without ``##``).
            content: Markdown content to append.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
            TaskNotFoundError: When task_id does not exist within the plan.
        """
        # Read current context_notes first (validates plan/task exist via read_task).
        # append_task_section accumulates section content in the context_notes field —
        # the yaml_writer does not support direct writes to the body field.
        current_task = self.read_task(plan_id, task_id)
        heading = f"## {section_name}"
        existing = current_task.get("context_notes", "")
        if heading in existing:
            new_context = f"{existing}\n{content}"
        else:
            separator = "\n" if existing else ""
            new_context = f"{existing}{separator}{heading}\n\n{content}"

        path = self._resolve_path(plan_id)
        try:
            query.update_plan_fields(path, task_id=task_id, set_fields={"context-notes": new_context})
        except KeyError as exc:
            raise TaskNotFoundError(plan_id, task_id) from exc
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a single validated Task to an existing plan.

        Duplicate-ID check via ``validate_appended_task``; see ADR-1770-1 for the
        single-writer contract (callers must serialise writes to the same plan).

        Args:
            plan_id: Plan identifier.
            task: Validated Task model to append.

        Returns:
            ``{"appended": True, "task_id": task.id}``

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved to a file.
            TaskValidationError: When the task ID already exists in the plan.
        """
        from sam_schema.writers.yaml_writer import write_plan  # noqa: PLC0415

        path = self._resolve_path(plan_id)
        result = query.load_plan(path)
        plan = result.plan

        # Use cache on subsequent calls; populate from plan on first call.
        if plan_id not in self._task_id_cache:
            self._task_id_cache[plan_id] = {t.id for t in plan.tasks}

        validate_appended_task(task, self._task_id_cache[plan_id], plan_id)
        self._task_id_cache[plan_id].add(task.id)

        new_tasks = [*plan.tasks, task]
        updated_plan = plan.model_copy(update={"tasks": new_tasks})
        write_plan(updated_plan, path, force_single=True)

        return {"appended": True, "task_id": task.id}

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Finalize a drafting plan by setting its state to ready.

        Loads the plan, sets ``state="ready"``, writes back via ``write_plan``.
        See ADR-1770-1 for the single-writer contract (callers must serialise
        writes to the same plan).

        Args:
            plan_id: Plan identifier.

        Returns:
            ``{"finalized": True, "state": "ready"}``

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved to a file.
        """
        from sam_schema.writers.yaml_writer import write_plan  # noqa: PLC0415

        path = self._resolve_path(plan_id)
        result = query.load_plan(path)
        plan = result.plan

        # No-op guard: already ready — skip write, return early.
        if plan.state == PlanState.READY:
            return {"finalized": True, "state": PlanState.READY}

        updated_plan = plan.model_copy(update={"state": PlanState.READY})
        write_plan(updated_plan, path, force_single=True)
        # Invalidate task-ID cache so subsequent appends read fresh state.
        self._task_id_cache.pop(plan_id, None)

        return {"finalized": True, "state": PlanState.READY}

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return all tasks that are ready for dispatch.

        A task is ready when its status is not-started and all dependency
        tasks have status complete.

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            List of TaskData for tasks ready to be claimed.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
        """
        path = self._resolve_path(plan_id)
        try:
            tasks = query.get_ready_tasks(path)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc
        return [_task_to_task_data(t) for t in tasks]

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return a summary dict of task status counts for a plan.

        Args:
            plan_id: Backend-assigned plan identifier.

        Returns:
            Dict with feature, total_tasks, by_status, ready_tasks,
            blocked_tasks, completion_pct, and has_cycles.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
        """
        path = self._resolve_path(plan_id)
        try:
            result = query.load_plan(path)
            status = query.get_plan_status(path)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(plan_id) from exc
        return {
            "feature": status.feature,
            "total_tasks": status.total_tasks,
            "by_status": dict(status.by_status),
            "ready_tasks": list(status.ready_tasks),
            "blocked_tasks": list(status.blocked_tasks),
            "completion_pct": status.completion_pct,
            "has_cycles": status.has_cycles,
            "state": result.plan.state,
        }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Persist a document under ``plan_dir/{plan_id}/documents/``.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Optional task identifier. None for plan-level documents.
            stage: Pipeline stage name (e.g. 'architect').
            doc_type: Document type discriminator (e.g. 'spec').
            title: Human-readable document title.
            content: Raw document content.
            fmt: Format hint (e.g. 'md', 'yaml'). Defaults to 'md'.

        Returns:
            DocumentHandle with filesystem content_ref.

        Raises:
            PlanNotFoundError: When plan_id cannot be resolved.
        """
        self._resolve_path(plan_id)  # Validate plan exists before writing.

        doc_dir = self._plan_dir / plan_id / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)

        owner_type = "task" if task_id is not None else "plan"
        owner_id = task_id if task_id is not None else plan_id
        file_name = f"{task_id}-{stage}-{doc_type}.{fmt}" if task_id is not None else f"{stage}-{doc_type}.{fmt}"
        doc_path = doc_dir / file_name
        doc_path.write_text(content, encoding="utf-8")

        handle: DocumentHandle = {
            "content_ref": str(doc_path),
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
            handle: DocumentHandle returned from a prior ``store_document`` call.
                The ``content_ref`` field is the filesystem path.

        Returns:
            DocumentData with full document content.

        Raises:
            DocumentNotFoundError: When the content_ref path does not exist.
        """
        doc_path = Path(handle["content_ref"])
        try:
            content = doc_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise DocumentNotFoundError(handle["content_ref"]) from None
        doc_data: DocumentData = {
            "content_ref": handle["content_ref"],
            "title": handle["title"],
            "content": content,
            "fmt": handle["fmt"],
            "version": handle.get("version"),
            "owner_type": handle["owner_type"],
            "owner_id": handle["owner_id"],
            "stage": handle["stage"],
            "doc_type": handle["doc_type"],
        }
        return doc_data
