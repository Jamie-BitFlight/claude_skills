"""BeadsTaskProvider and BeadsContextBackend — beads (bd CLI) backend for SAM.

Both classes are co-located in this module (per architect doc §4.5) and share
a single BdRunner instance when instantiated together.

Index strategy (Path B)
-----------------------
The ``bd remember`` key-value store serves as a bidirectional index mapping
SAM plan/task IDs to beads epic/issue IDs.  This avoids any modification to
``beads_models.py`` (owned by T05) and does not rely on issue metadata fields.

Keys:
- ``dh.plan-index.{plan_id}``         → beads epic ID (plain string)
- ``dh.task-index.{plan_id}.{task_id}`` → JSON
  ``{"bd_id":"bd-xxx","is_bookend":false,"bookend_type":null}``
- ``dh.active-task.{session_id}``     → JSON-encoded ActiveTaskContext
  (written by BeadsContextBackend)

Document storage
----------------
Documents are embedded in beads issue notes using HTML-comment delimiters::

    <!-- doc:{content_ref} -->
    <!-- title: {title} | fmt: {fmt} -->
    {content}
    <!-- /doc:{content_ref} -->

The ``content_ref`` uses a ``bd://`` URI scheme:
``bd://{plan_id}/{owner_id}/{stage}/{doc_type}/{ref_suffix}``
"""

from __future__ import annotations

import contextlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import dh_paths
from backlog_core.backends.bd_runner import BdInvocationError, BdJsonDecodeError, BdNotInstalledError, BdRunner
from backlog_core.backends.beads_models import (
    BeadsIssueRaw,
    BeadsStatus,
    parse_issue,
    parse_issue_list,
    parse_ready_list,
)
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from sam_schema.core.backends._utils import _now_iso, validate_appended_task
from sam_schema.core.dependencies import SUCCESSFUL_STATUSES as _SUCCESSFUL_STATUSES
from sam_schema.core.exceptions import (
    DocumentNotFoundError,
    PlanExistsError,
    PlanNotFoundError,
    TaskNotFoundError,
    TaskValidationError,
)
from sam_schema.core.models import ActiveTaskContext, PlanState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.models import Task
    from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

__all__ = ["BeadsContextBackend", "BeadsTaskProvider"]


# ---------------------------------------------------------------------------
# bd remember index key prefixes
# ---------------------------------------------------------------------------

_PLAN_IDX_PREFIX: Final[str] = "dh.plan-index."
_TASK_IDX_PREFIX: Final[str] = "dh.task-index."
_CTX_PREFIX: Final[str] = "dh.active-task."


# ---------------------------------------------------------------------------
# Local boundary model — bd remember --list --json output
# ---------------------------------------------------------------------------


class _RememberEntry(BaseModel):
    """Single entry from ``bd memories --json`` output.

    Attributes:
        key: Remember store key.
        value: Stored value string.
    """

    model_config = ConfigDict(strict=False, extra="ignore")
    key: str
    value: str


_REMEMBER_LIST_ADAPTER: TypeAdapter[list[_RememberEntry]] = TypeAdapter(list[_RememberEntry])


# ---------------------------------------------------------------------------
# Status mappers
# ---------------------------------------------------------------------------

_VALID_STATUSES: frozenset[str] = frozenset({
    "not-started",
    "in-progress",
    "complete",
    "blocked",
    "deferred",
    "skipped",
    "failed",
})

#: Length of a bare ``["update", id]`` argv slice — used to detect when optional
#: field flags have been appended before calling the bd runner.
_UPDATE_BASE_LEN: Final[int] = 2

#: Minimum number of path segments in a ``bd://`` URI (plan_id + owner_id).
_BD_URI_MIN_PARTS: Final[int] = 2


def _beads_to_task_status(s: BeadsStatus) -> str:
    """Map a BeadsStatus to a SAM TaskStatus string.

    HOOKED is the atomic claim status written by ``bd claim``; it surfaces
    as ``in-progress`` from SAM's perspective.

    Args:
        s: BeadsStatus enum value.

    Returns:
        SAM-compatible status string.
    """
    match s:
        case BeadsStatus.OPEN:
            return "not-started"
        case BeadsStatus.IN_PROGRESS | BeadsStatus.HOOKED:
            return "in-progress"
        case BeadsStatus.CLOSED:
            return "complete"
        case BeadsStatus.BLOCKED:
            return "blocked"
        case BeadsStatus.DEFERRED | BeadsStatus.PINNED:
            return "deferred"
        case _:
            return "not-started"


def _task_to_beads_status(s: str) -> str:
    """Map a SAM TaskStatus string to a bd-compatible status value.

    Used on the write path only (``bd update --status``).  The claim path
    uses ``bd claim`` directly and never routes through this function.

    Args:
        s: SAM TaskStatus string.

    Returns:
        bd status string accepted by ``bd update --status <value>``.
    """
    match s:
        case "not-started":
            return "open"
        case "in-progress":
            return "in_progress"
        case "complete":
            return "closed"
        case "blocked" | "failed":
            # beads has no FAILED status; map failed to blocked for visibility
            return "blocked"
        case "deferred" | "skipped":
            return "deferred"
        case _:
            return "open"


# ---------------------------------------------------------------------------
# Shared TaskData builder
# ---------------------------------------------------------------------------


def _issue_to_task_data(issue: BeadsIssueRaw, task_id: str, plan_id: str) -> TaskData:
    """Build a minimal TaskData from a BeadsIssueRaw instance.

    Only fields derivable from the bd issue are populated.  Rich content
    (requirements, acceptance criteria, verification steps) comes from the
    SAM plan YAML and is not available from beads alone.

    Args:
        issue: Parsed BeadsIssueRaw instance.
        task_id: SAM task identifier (e.g. ``'T01'``).
        plan_id: SAM plan identifier (e.g. ``'Pabc123'``).

    Returns:
        Minimal TaskData dict with status, title, id, and timestamps.
    """
    data: TaskData = {
        "id": task_id,
        "title": issue.title,
        "status": _beads_to_task_status(issue.status),
        "agent": None,
        "dependencies": [],
        "blocked_by": [],
        "parallelize_with": [],
        "priority": 3,
        "complexity": "medium",
        "skills": [],
        "created": issue.created_at or _now_iso(),
        "started": None,
        "completed": issue.closed_at or None,
        "last_activity": issue.updated_at or None,
        "body": issue.notes or "",
        "description": issue.description or "",
        "analysis_method": "none",
        "divergence_notes": 0,
        "accuracy_risk": "low",
    }
    return data


def _build_plan_data(plan_id: str, epic: BeadsIssueRaw, task_data_list: list[TaskData]) -> PlanData:
    """Build a PlanData dict from a beads epic and task list.

    Args:
        plan_id: SAM plan identifier.
        epic: Parsed BeadsIssueRaw for the plan's epic.
        task_data_list: List of TaskData dicts for the plan's tasks.

    Returns:
        PlanData TypedDict populated from the epic fields.
    """
    plan_data: PlanData = {
        "plan_id": plan_id,
        "feature": epic.title,
        "version": "1.0.0",
        "description": epic.description or "",
        "goal": epic.description or "",
        "context": "",
        "acceptance_criteria": "",
        "issue": None,
        "tasks": task_data_list,
        "source_path": None,
        "state": PlanState.READY,
        "backend_ref": epic.id,
    }
    return plan_data


# ---------------------------------------------------------------------------
# BeadsTaskProvider
# ---------------------------------------------------------------------------


class BeadsTaskProvider:
    """TaskBackend implementation routing SAM plan/task operations to the bd CLI.

    Plans map to beads epics (``--type epic``).  Tasks map to child issues
    with ``--parent <epic_id>`` links.  The ``bd remember`` key-value store
    holds a bidirectional index — see module docstring for the key schema.

    All methods are synchronous.  The MCP server wraps calls in
    ``asyncio.to_thread()`` as needed.

    Parameters
    ----------
    runner:
        Optional pre-constructed :class:`~backlog_core.backends.bd_runner.BdRunner`.
        When absent, a default ``BdRunner()`` is created (lazy — no subprocess
        at init time).
    """

    def __init__(self, runner: BdRunner | None = None) -> None:
        """Store the runner.  No filesystem or subprocess activity at init."""
        self._runner = runner or BdRunner()

    # ------------------------------------------------------------------
    # bd remember index helpers
    # ------------------------------------------------------------------

    def _remember_set(self, key: str, value: str) -> None:
        """Store a key→value pair in bd remember.

        Args:
            key: Remember store key.
            value: String value to store.
        """
        self._runner.run_text(["remember", value, "--key", key])

    def _remember_get(self, key: str) -> str | None:
        """Retrieve a value from bd remember, or None if absent.

        Args:
            key: Remember store key.

        Returns:
            Stored value string, or None if the key does not exist or bd errors.
        """
        try:
            return self._runner.run_text(["recall", key]).strip() or None
        except BdInvocationError:
            return None

    def _remember_forget(self, key: str) -> None:
        """Delete a key from bd remember.  No-op when the key is absent.

        Args:
            key: Remember store key to delete.
        """
        with contextlib.suppress(BdInvocationError):
            self._runner.run_text(["forget", key])

    def _remember_list(self) -> list[_RememberEntry]:
        """Return all entries from ``bd memories --json``.

        ``bd memories --json`` returns a flat dict ``{key: value, ..., "schema_version": 1}``.
        This method converts that dict into a list of :class:`_RememberEntry` instances,
        excluding the ``schema_version`` metadata field.

        Returns:
            Parsed list of _RememberEntry instances, or empty list on failure.
        """
        try:
            raw = self._runner.run_json(["memories", "--json"])
            if not isinstance(raw, dict):
                return []
            entries_data = [{"key": k, "value": str(v)} for k, v in raw.items() if k != "schema_version"]
            return _REMEMBER_LIST_ADAPTER.validate_python(entries_data)
        except (BdNotInstalledError, BdInvocationError, BdJsonDecodeError, ValidationError):
            return []

    def _write_plan_index(self, plan_id: str, epic_id: str) -> None:
        """Write plan_id → epic_id into bd remember.

        Args:
            plan_id: SAM plan identifier.
            epic_id: Beads epic issue ID (e.g. ``'bd-a1b2'``).
        """
        self._remember_set(f"{_PLAN_IDX_PREFIX}{plan_id}", epic_id)

    def _epic_id_for_plan(self, plan_id: str) -> str:
        """Look up the beads epic ID for a SAM plan.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            Beads epic ID string.

        Raises:
            PlanNotFoundError: When no epic is registered for plan_id.
        """
        epic_id = self._remember_get(f"{_PLAN_IDX_PREFIX}{plan_id}")
        if not epic_id:
            raise PlanNotFoundError(plan_id)
        return epic_id

    def _write_task_index(
        self, plan_id: str, task_id: str, bd_id: str, *, is_bookend: bool = False, bookend_type: str | None = None
    ) -> None:
        """Write task metadata into bd remember for later lookup.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier (e.g. ``'T01'``).
            bd_id: Beads issue ID for this task (e.g. ``'bd-x9y8'``).
            is_bookend: Whether this task is a bookend task.
            bookend_type: ``'t0-baseline'`` | ``'tn-verification'`` | None.
        """
        payload = json.dumps({"bd_id": bd_id, "is_bookend": is_bookend, "bookend_type": bookend_type})
        self._remember_set(f"{_TASK_IDX_PREFIX}{plan_id}.{task_id}", payload)

    def _task_index(self, plan_id: str) -> dict[str, dict[str, Any]]:
        """Read the full task index for a plan from bd remember.

        Scans all remember entries with the prefix
        ``dh.task-index.{plan_id}.`` and parses each value as JSON.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            Dict mapping task_id → ``{bd_id, is_bookend, bookend_type}``.
        """
        prefix = f"{_TASK_IDX_PREFIX}{plan_id}."
        result: dict[str, dict[str, Any]] = {}
        for entry in self._remember_list():
            if not entry.key.startswith(prefix):
                continue
            task_id = entry.key[len(prefix) :]
            try:
                parsed = json.loads(entry.value)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict) and "bd_id" in parsed:
                result[task_id] = parsed
        return result

    def _bd_id_for_task(self, plan_id: str, task_id: str) -> tuple[str, bool, str | None]:
        """Look up (bd_id, is_bookend, bookend_type) for a SAM task.

        Uses a single bd recall on the hot path. The plan-existence check is
        deferred to the error path to preserve PlanNotFoundError vs
        TaskNotFoundError distinction without paying for two bd recall calls on
        every successful lookup.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier.

        Returns:
            Tuple of ``(bd_id, is_bookend, bookend_type)``.

        Raises:
            PlanNotFoundError: When no epic is registered for plan_id.
            TaskNotFoundError: When task_id is not in the task index.
        """
        raw = self._remember_get(f"{_TASK_IDX_PREFIX}{plan_id}.{task_id}")
        if raw:
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                raise TaskNotFoundError(plan_id, task_id) from exc
            if not isinstance(parsed, dict) or "bd_id" not in parsed:
                raise TaskNotFoundError(plan_id, task_id)
            return parsed["bd_id"], bool(parsed.get("is_bookend", False)), parsed.get("bookend_type")

        # Task key absent: distinguish missing-plan from missing-task (1 additional
        # recall on the error path only). Contract: PlanNotFoundError when the plan
        # does not exist; TaskNotFoundError when the plan exists but task is absent.
        self._epic_id_for_plan(plan_id)  # raises PlanNotFoundError if plan absent
        raise TaskNotFoundError(plan_id, task_id)

    def _create_task_issue(self, task: Task, epic_id: str) -> BeadsIssueRaw:
        """Create a child bd issue for a SAM task.

        Args:
            task: Validated Task model.
            epic_id: Beads epic ID to use as parent.

        Returns:
            Parsed BeadsIssueRaw for the newly created issue.
        """
        argv = ["create", "--type", "task", "--title", task.title, "--parent", epic_id]
        if task.description:
            argv += ["--description", task.description]
        if task.priority is not None:
            argv += ["--priority", str(int(task.priority))]
        return parse_issue(self._runner.run_json(argv))

    def _wire_task_dependencies(self, plan_id: str, task: Task, bd_issue_id: str) -> None:
        """Wire beads dependency links from a task to already-created tasks in the index.

        Iterates ``task.dependencies`` and calls ``bd dep add`` for each dep
        already registered in the remember index.  Errors are suppressed because
        dependency issues may not yet exist when tasks are created in series.

        Args:
            plan_id: SAM plan identifier.
            task: Validated Task model containing dependency IDs.
            bd_issue_id: Beads issue ID for the task being wired.
        """
        for dep_id in task.dependencies:
            dep_raw = self._remember_get(f"{_TASK_IDX_PREFIX}{plan_id}.{dep_id}")
            if not dep_raw:
                continue
            try:
                dep_parsed = json.loads(dep_raw)
            except (json.JSONDecodeError, ValueError):
                continue
            dep_bd_id = dep_parsed.get("bd_id", "")
            if dep_bd_id:
                with contextlib.suppress(BdInvocationError):
                    self._runner.run_text(["dep", "add", bd_issue_id, dep_bd_id])

    def _create_and_index_tasks(self, plan_id: str, tasks: Sequence[Task], epic_id: str) -> list[TaskData]:
        """Create child bd issues for each task and populate the remember index.

        Validates task IDs and titles, calls :meth:`_create_task_issue`,
        registers each task in the remember index, and wires dependency links.

        Args:
            plan_id: SAM plan identifier.
            tasks: Ordered validated Task models.
            epic_id: Beads epic ID to use as parent for all child issues.

        Returns:
            List of minimal TaskData dicts for each created task.

        Raises:
            TaskValidationError: When a task definition is invalid or a duplicate.
        """
        task_data_list: list[TaskData] = []
        existing_ids: set[str] = set()
        for idx, task in enumerate(tasks):
            if not task.id:
                raise TaskValidationError(idx, "Task 'id' is required")
            if not task.title:
                raise TaskValidationError(idx, "Task 'title' is required")
            validate_appended_task(task, existing_ids, plan_id)
            existing_ids.add(task.id)
            bd_issue = self._create_task_issue(task, epic_id)
            self._write_task_index(
                plan_id,
                task.id,
                bd_issue.id,
                is_bookend=task.is_bookend,
                bookend_type=str(task.bookend_type) if task.bookend_type is not None else None,
            )
            self._wire_task_dependencies(plan_id, task, bd_issue.id)
            td = _issue_to_task_data(bd_issue, task.id, plan_id)
            if task.is_bookend:
                td["is_bookend"] = task.is_bookend
            if task.bookend_type is not None:
                td["bookend_type"] = str(task.bookend_type)
            task_data_list.append(td)
        return task_data_list

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
        """Create a beads epic for the plan and child issues for each task.

        Plan ID is auto-assigned via :func:`~sam_schema.core.query._new_plan_id`.
        The epic is created with type ``epic``; each task becomes a child issue
        with ``--parent <epic_id>``.

        Args:
            slug: Human-readable identifier slug used as the epic title.
            goal: Plan goal statement stored in the epic description.
            tasks: Ordered validated Task models to create as child issues.
            context: Optional context narrative appended to epic description.
            issue: Optional GitHub issue number stored in plan metadata only.
            acceptance_criteria: Optional plan-level acceptance criteria text.

        Returns:
            PlanData with the backend-assigned plan_id.

        Raises:
            PlanExistsError: When the generated plan_id already has an index entry.
            TaskValidationError: When any task definition is invalid.
        """
        from sam_schema.core.query import _new_plan_id  # noqa: PLC0415

        plan_id = _new_plan_id()

        existing = self._remember_get(f"{_PLAN_IDX_PREFIX}{plan_id}")
        if existing:
            raise PlanExistsError(plan_id)

        # Build epic description
        desc_lines = [goal]
        if context:
            desc_lines.append(f"\n\nContext: {context}")
        if acceptance_criteria:
            desc_lines.append(f"\n\nAcceptance Criteria:\n{acceptance_criteria}")
        epic_description = "".join(desc_lines)

        # Create the plan epic
        epic_raw = self._runner.run_json([
            "create",
            "--type",
            "epic",
            "--title",
            slug,
            "--description",
            epic_description,
            "--priority",
            "2",
        ])
        epic = parse_issue(epic_raw)
        self._write_plan_index(plan_id, epic.id)

        # Create task issues and register in index
        task_data_list = self._create_and_index_tasks(plan_id, tasks, epic.id)

        plan_data: PlanData = {
            "plan_id": plan_id,
            "feature": slug,
            "version": "1.0.0",
            "description": goal,
            "goal": goal,
            "context": context or "",
            "acceptance_criteria": acceptance_criteria or "",
            "issue": str(issue) if issue is not None else None,
            "tasks": task_data_list,
            "source_path": None,
            "state": PlanState.DRAFTING if not tasks else PlanState.READY,
            "backend_ref": epic.id,
        }
        return plan_data

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by fetching the epic and its registered child task issues.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            PlanData reconstructed from the beads epic and its children.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic in the index.
        """
        epic_id = self._epic_id_for_plan(plan_id)
        epic = parse_issue(self._runner.run_json(["show", epic_id]))

        task_index = self._task_index(plan_id)
        task_data_list: list[TaskData] = []

        # Batch fetch: replace N individual bd show calls with a single
        # bd list --parent <epic_id>. Falls back to per-task shows when the
        # --parent flag is unsupported or the response fails to parse.
        children_by_bd_id: dict[str, BeadsIssueRaw] = {}
        try:
            raw_children = self._runner.run_json(["list", "--parent", epic_id])
            children_by_bd_id = {issue.id: issue for issue in parse_issue_list(raw_children)}
        except BdNotInstalledError:
            raise
        except (BdInvocationError, BdJsonDecodeError, ValidationError):
            # bd list --parent unsupported, non-JSON output, or invalid JSON — fall back to per-task shows.
            for task_id, meta in task_index.items():
                bd_id = meta["bd_id"]
                try:
                    issue = parse_issue(self._runner.run_json(["show", bd_id]))
                    td = _issue_to_task_data(issue, task_id, plan_id)
                    if meta.get("is_bookend"):
                        td["is_bookend"] = meta["is_bookend"]
                    if meta.get("bookend_type") is not None:
                        td["bookend_type"] = meta["bookend_type"]
                    task_data_list.append(td)
                except BdNotInstalledError:
                    raise
                except BdInvocationError:
                    continue  # individual issue inaccessible; skip rather than fail whole plan
            return _build_plan_data(plan_id, epic, task_data_list)

        # Happy path: join batch result against task index for task_id mapping
        # and bookend metadata. Issues absent from the batch result are skipped —
        # this matches the defensive posture of the original per-task show loop
        # (bd issues deleted in bd but surviving in the remember index are dropped).
        for task_id, meta in task_index.items():
            bd_id = meta["bd_id"]
            if (issue := children_by_bd_id.get(bd_id)) is None:
                continue  # issue deleted in bd but index entry survives; skip
            td = _issue_to_task_data(issue, task_id, plan_id)
            if meta.get("is_bookend"):
                td["is_bookend"] = meta["is_bookend"]
            if meta.get("bookend_type") is not None:
                td["bookend_type"] = meta["bookend_type"]
            task_data_list.append(td)

        return _build_plan_data(plan_id, epic, task_data_list)

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """Return plan summaries by scanning bd remember for plan index entries.

        Calls bd memories exactly once and partitions entries in memory to count
        tasks per plan without a separate bd recall per plan.

        Args:
            search: Optional substring filter on feature name or goal.
            offset: Number of results to skip (for pagination).
            limit: Maximum results to return; None means no limit.

        Returns:
            List of PlanSummary TypedDicts.
        """
        all_entries = self._remember_list()

        # Partition entries into plan-index entries and task count by plan_id.
        # Task key format: dh.task-index.{plan_id}.{task_id}
        # Plan_id contains no dots (it is a nanoid-prefixed slug), so the first
        # dot after the prefix unambiguously separates plan_id from task_id.
        plan_entries: dict[str, str] = {}  # plan_id -> epic_id
        task_counts: dict[str, int] = {}  # plan_id -> task count

        for entry in all_entries:
            if entry.key.startswith(_PLAN_IDX_PREFIX):
                plan_id = entry.key[len(_PLAN_IDX_PREFIX) :]
                plan_entries[plan_id] = entry.value.strip()
            elif entry.key.startswith(_TASK_IDX_PREFIX):
                # Extract plan_id from dh.task-index.{plan_id}.{task_id}
                remainder = entry.key[len(_TASK_IDX_PREFIX) :]
                dot_idx = remainder.find(".")
                if dot_idx == -1:
                    continue  # malformed key; skip
                plan_id = remainder[:dot_idx]
                task_counts[plan_id] = task_counts.get(plan_id, 0) + 1

        summaries: list[PlanSummary] = []
        for plan_id, epic_id in plan_entries.items():
            if not epic_id:
                continue

            try:
                epic = parse_issue(self._runner.run_json(["show", epic_id]))
            except BdInvocationError:
                continue

            feature = epic.title
            goal = epic.description or ""

            if search is not None and search.lower() not in f"{feature} {goal}".lower():
                continue

            summary: PlanSummary = {
                "plan_id": plan_id,
                "feature": feature,
                "goal": goal,
                "description": goal,
                "task_count": task_counts.get(plan_id, 0),
                "source_path": None,
                "backend_ref": epic_id,
            }
            summaries.append(summary)

        paginated = summaries[offset:]
        if limit is not None:
            paginated = paginated[:limit]
        return paginated

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level fields on the beads epic for a plan.

        Supported ``set_fields`` keys: ``title``, ``feature``, ``description``.
        Unknown keys are silently ignored.

        Args:
            plan_id: SAM plan identifier.
            context: When provided, appended to the epic notes as context.
            set_fields: Optional field map with new values.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
        """
        epic_id = self._epic_id_for_plan(plan_id)
        argv = ["update", epic_id]

        if context is not None:
            argv += ["--notes", f"Context:\n{context}"]
        if set_fields:
            if "description" in set_fields:
                argv += ["--description", str(set_fields["description"])]
            new_title = set_fields.get("title") or set_fields.get("feature")
            if new_title:
                argv += ["--title", str(new_title)]

        if len(argv) > _UPDATE_BASE_LEN:
            self._runner.run_text(argv)

    # ------------------------------------------------------------------
    # Task access
    # ------------------------------------------------------------------

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task by fetching the corresponding bd issue.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier (e.g. ``'T02'``).

        Returns:
            TaskData derived from the bd issue.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is not in the plan task index.
        """
        bd_id, is_bookend, bookend_type = self._bd_id_for_task(plan_id, task_id)
        issue = parse_issue(self._runner.run_json(["show", bd_id]))
        td = _issue_to_task_data(issue, task_id, plan_id)
        if is_bookend:
            td["is_bookend"] = is_bookend
        if bookend_type is not None:
            td["bookend_type"] = bookend_type
        return td

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Attempt to claim a task using ``bd claim``.

        ``bd claim`` is the atomic primitive.  It transitions the issue from
        ``open`` to ``hooked``.  If the issue is already claimed or closed,
        bd exits non-zero and :exc:`BdInvocationError` is raised — in which
        case this method returns False.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier.

        Returns:
            True if the claim succeeded, False if already claimed or not claimable.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is not in the plan task index.
        """
        bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task_id)
        try:
            self._runner.run_json(["claim", bd_id])
        except BdInvocationError:
            return False
        else:
            return True

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update the status of a task via ``bd update --status``.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier.
            status: New status string; must be a valid TaskStatus value.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is not in the plan task index.
            TaskValidationError: When status is not a valid TaskStatus value.
        """
        if status not in _VALID_STATUSES:
            raise TaskValidationError(0, f"Invalid status value: {status!r}")
        bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task_id)
        self._runner.run_text(["update", bd_id, "--status", _task_to_beads_status(status)])

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update one or more scalar fields on a task via ``bd update``.

        Supported keys: ``title``, ``description``, ``priority``, ``notes``,
        ``body``.  Unknown keys are silently ignored.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier.
            fields: Mapping of field names to new values.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is not in the plan task index.
        """
        bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task_id)
        argv: list[str] = ["update", bd_id]
        if "title" in fields:
            argv += ["--title", str(fields["title"])]
        if "description" in fields:
            argv += ["--description", str(fields["description"])]
        if "priority" in fields:
            prio_raw = fields["priority"]
            if isinstance(prio_raw, (int, str)):
                argv += ["--priority", str(int(prio_raw))]
        notes_val = fields.get("notes") or fields.get("body")
        if notes_val is not None:
            argv += ["--notes", str(notes_val)]
        if len(argv) > _UPDATE_BASE_LEN:
            self._runner.run_text(argv)

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace a task's fields by serializing the Task model to bd update.

        Args:
            plan_id: SAM plan identifier.
            task: Validated Task model whose ``id`` identifies the target task.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task.id is not in the plan task index.
        """
        bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task.id)
        argv: list[str] = ["update", bd_id, "--title", task.title]
        if task.description:
            argv += ["--description", task.description]
        if task.priority is not None:
            argv += ["--priority", str(int(task.priority))]
        argv += ["--status", _task_to_beads_status(str(task.status))]
        self._runner.run_text(argv)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append markdown content under a named heading in the task notes.

        Fetches the current bd issue notes, appends the section, and writes
        back via ``bd update --notes``.  Follows the same append semantics as
        LocalYamlTaskProvider: if the heading already exists, content is appended
        at the end of the field; otherwise the heading is emitted first.

        Args:
            plan_id: SAM plan identifier.
            task_id: SAM task identifier.
            section_name: Heading label (without ``##``).
            content: Markdown content to append.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is not in the plan task index.
        """
        bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task_id)
        issue = parse_issue(self._runner.run_json(["show", bd_id]))
        existing = issue.notes or ""
        heading = f"## {section_name}"
        if heading in existing:
            new_notes = f"{existing}\n{content}"
        else:
            separator = "\n" if existing else ""
            new_notes = f"{existing}{separator}{heading}\n\n{content}"
        self._runner.run_text(["update", bd_id, "--notes", new_notes])

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a single validated Task to an existing plan.

        Creates a new child issue under the plan epic and registers it in
        the task index via bd remember.

        Single-writer assumption applies (ADR-1770-1): callers must serialize
        writes to the same plan.

        Args:
            plan_id: SAM plan identifier.
            task: Validated Task model to append.

        Returns:
            Dict with ``appended`` (True) and ``task_id`` (the task's ID).

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskValidationError: When the task ID already exists in the plan.
        """
        epic_id = self._epic_id_for_plan(plan_id)
        existing_ids = set(self._task_index(plan_id).keys())
        validate_appended_task(task, existing_ids, plan_id)

        bd_issue = self._create_task_issue(task, epic_id)
        self._write_task_index(
            plan_id,
            task.id,
            bd_issue.id,
            is_bookend=task.is_bookend,
            bookend_type=str(task.bookend_type) if task.bookend_type is not None else None,
        )
        return {"appended": True, "task_id": task.id}

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Finalize a drafting plan.

        Beads issues are live after creation, so this is a no-op on the
        backend.  The method validates the plan exists and returns the ready
        state.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            Dict with ``finalized`` (True) and ``state`` (``'ready'``).

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
        """
        self._epic_id_for_plan(plan_id)  # validate plan exists
        return {"finalized": True, "state": PlanState.READY}

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return tasks ready for dispatch (not-started, all deps satisfied).

        Attempts ``bd ready --parent <epic_id>`` first.  If bd does not support
        the ``--parent`` flag, falls back to manual dependency evaluation using
        the task index statuses.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            List of TaskData for tasks ready to be claimed.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
        """
        epic_id = self._epic_id_for_plan(plan_id)
        task_index = self._task_index(plan_id)

        # Fetch all non-bookend task data
        status_by_task_id: dict[str, str] = {}
        task_data_by_id: dict[str, TaskData] = {}
        for task_id, meta in task_index.items():
            if meta.get("is_bookend"):
                continue
            bd_id = meta["bd_id"]
            try:
                issue = parse_issue(self._runner.run_json(["show", bd_id]))
                td = _issue_to_task_data(issue, task_id, plan_id)
                status_by_task_id[task_id] = td["status"]
                task_data_by_id[task_id] = td
            except BdInvocationError:
                continue

        # Attempt bd ready --parent for native ready list
        ready_ids: set[str] = set()
        bd_id_to_task_id: dict[str, str] = {meta["bd_id"]: tid for tid, meta in task_index.items()}
        try:
            raw_ready = self._runner.run_json(["ready", "--parent", epic_id])
            ready_issues = parse_ready_list(raw_ready)
            for rissue in ready_issues:
                mapped_tid = bd_id_to_task_id.get(rissue.id)
                if mapped_tid and not task_index[mapped_tid].get("is_bookend"):
                    ready_ids.add(mapped_tid)
        except BdInvocationError:
            # Fall back to local dependency evaluation
            for task_id, td in task_data_by_id.items():
                if td["status"] != "not-started":
                    continue
                if all(status_by_task_id.get(dep_id, "") in _SUCCESSFUL_STATUSES for dep_id in td["dependencies"]):
                    ready_ids.add(task_id)

        return [task_data_by_id[tid] for tid in ready_ids if tid in task_data_by_id]

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return a summary dict of task status counts for a plan.

        Args:
            plan_id: SAM plan identifier.

        Returns:
            Dict with keys: ``feature``, ``total_tasks``, ``by_status``,
            ``ready_tasks``, ``blocked_tasks``, ``completion_pct``,
            ``has_cycles``, ``state``.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
        """
        plan_data = self.read_plan(plan_id)
        tasks = plan_data["tasks"]
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
            unsatisfied = [d for d in task["dependencies"] if status_by_id.get(d, "") not in _SUCCESSFUL_STATUSES]
            if unsatisfied:
                blocked_tasks.append({task["id"]: unsatisfied})
            else:
                ready_task_ids.append(task["id"])

        total = len(tasks)
        complete_count = by_status.get("complete", 0)
        completion_pct = (complete_count / total * 100.0) if total > 0 else 0.0

        return {
            "feature": plan_data["feature"],
            "total_tasks": total,
            "by_status": by_status,
            "ready_tasks": ready_task_ids,
            "blocked_tasks": blocked_tasks,
            "completion_pct": completion_pct,
            "has_cycles": False,  # beads enforces DAG constraints server-side
            "state": plan_data.get("state", PlanState.READY),
        }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Persist a document in bd issue notes and return a retrieval handle.

        Documents are stored in the notes field of the epic (plan-level) or
        task issue (task-level) using HTML-comment delimiters.  The
        ``content_ref`` uses a ``bd://`` URI scheme to encode retrieval
        coordinates.

        Args:
            plan_id: SAM plan identifier.
            task_id: Optional task identifier. None for plan-level documents.
            stage: Pipeline stage name (e.g. ``'architect'``).
            doc_type: Document type discriminator (e.g. ``'spec'``).
            title: Human-readable document title.
            content: Raw document content.
            fmt: Format hint. Defaults to ``'md'``.

        Returns:
            DocumentHandle with a ``bd://`` scheme content_ref.

        Raises:
            PlanNotFoundError: When plan_id has no registered epic.
            TaskNotFoundError: When task_id is provided but not in the index.
        """
        if task_id is not None:
            bd_id, _is_bookend, _bookend_type = self._bd_id_for_task(plan_id, task_id)
            owner_type = "task"
            owner_id = task_id
        else:
            bd_id = self._epic_id_for_plan(plan_id)
            owner_type = "plan"
            owner_id = plan_id

        ref_suffix = uuid.uuid4().hex[:8]
        content_ref = f"bd://{plan_id}/{owner_id}/{stage}/{doc_type}/{ref_suffix}"

        issue = parse_issue(self._runner.run_json(["show", bd_id]))
        existing_notes = issue.notes or ""
        doc_block = (
            f"\n<!-- doc:{content_ref} -->\n"
            f"<!-- title: {title} | fmt: {fmt} -->\n"
            f"{content}\n"
            f"<!-- /doc:{content_ref} -->\n"
        )
        self._runner.run_text(["update", bd_id, "--notes", existing_notes + doc_block])

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

    def _extract_doc_from_notes(self, notes: str, content_ref: str) -> str:
        """Extract doc content delimited by HTML-comment markers from issue notes.

        Args:
            notes: Full notes field of a bd issue.
            content_ref: The ``bd://`` URI identifying the document block.

        Returns:
            Extracted and cleaned document content string.

        Raises:
            DocumentNotFoundError: When the markers are absent or malformed.
        """
        start_marker = f"<!-- doc:{content_ref} -->"
        end_marker = f"<!-- /doc:{content_ref} -->"
        start_idx = notes.find(start_marker)
        if start_idx == -1:
            raise DocumentNotFoundError(content_ref)
        end_idx = notes.find(end_marker, start_idx)
        if end_idx == -1:
            raise DocumentNotFoundError(content_ref)
        inner = notes[start_idx + len(start_marker) : end_idx].strip()
        cleaned_lines = [
            line for line in inner.splitlines() if not (line.startswith("<!-- title:") and line.endswith("-->"))
        ]
        return "\n".join(cleaned_lines).strip()

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a document from bd issue notes by its handle.

        Parses the ``<!-- doc:{ref} --> ... <!-- /doc:{ref} -->`` delimiters
        written by :meth:`store_document`.

        Args:
            handle: DocumentHandle returned from a prior :meth:`store_document` call.

        Returns:
            DocumentData with full document content and metadata.

        Raises:
            DocumentNotFoundError: When the content_ref cannot be resolved.
        """
        content_ref = handle["content_ref"]
        if not content_ref.startswith("bd://"):
            raise DocumentNotFoundError(content_ref)

        # bd://{plan_id}/{owner_id}/{stage}/{doc_type}/{ref_suffix}
        uri_parts = content_ref[len("bd://") :].split("/")
        if len(uri_parts) < _BD_URI_MIN_PARTS:
            raise DocumentNotFoundError(content_ref)

        plan_id = uri_parts[0]
        owner_id = uri_parts[1]

        try:
            if owner_id == plan_id:
                bd_id = self._epic_id_for_plan(plan_id)
            else:
                bd_id = self._bd_id_for_task(plan_id, owner_id)[0]
        except (PlanNotFoundError, TaskNotFoundError) as exc:
            raise DocumentNotFoundError(content_ref) from exc

        issue = parse_issue(self._runner.run_json(["show", bd_id]))
        doc_content = self._extract_doc_from_notes(issue.notes or "", content_ref)

        doc_data: DocumentData = {
            "content_ref": content_ref,
            "title": handle["title"],
            "content": doc_content,
            "fmt": handle["fmt"],
            "version": None,
            "owner_type": handle["owner_type"],
            "owner_id": handle["owner_id"],
            "stage": handle["stage"],
            "doc_type": handle["doc_type"],
        }
        return doc_data


# ---------------------------------------------------------------------------
# BeadsContextBackend
# ---------------------------------------------------------------------------


class BeadsContextBackend:
    """ContextBackend persisting active-task context via bd remember.

    Context is stored under the key ``dh.active-task.{session_id}`` as a
    JSON-encoded :class:`~sam_schema.core.models.ActiveTaskContext`.

    Parameters
    ----------
    runner:
        Optional pre-constructed :class:`~backlog_core.backends.bd_runner.BdRunner`.
        When absent, a default ``BdRunner()`` is created (lazy — no subprocess
        at init time).
    """

    def __init__(self, runner: BdRunner | None = None) -> None:
        """Store the runner.  No filesystem or subprocess activity at init."""
        self._runner = runner or BdRunner()

    def _ctx_key(self, session_id: str) -> str:
        """Return the bd remember key for a session's active task context.

        Args:
            session_id: Claude Code session identifier.

        Returns:
            Full remember store key string.
        """
        return f"{_CTX_PREFIX}{session_id}"

    def get_active_task(self, session_id: str) -> ActiveTaskContext | None:
        """Retrieve the active task context for a session from bd remember.

        Args:
            session_id: Claude Code session identifier.

        Returns:
            :class:`~sam_schema.core.models.ActiveTaskContext` if found, otherwise None.
        """
        try:
            raw = self._runner.run_text(["recall", self._ctx_key(session_id)]).strip()
        except BdInvocationError:
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return ActiveTaskContext.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return None

    def set_active_task(
        self, session_id: str, plan: str, task: str, plan_dir: str, parent_issue_number: str | int | None = None
    ) -> ActiveTaskContext:
        """Store active task context as JSON in bd remember.

        Args:
            session_id: Claude Code session identifier.
            plan: Plan address (e.g. ``'Pa1b2c3d4'`` or a slug).
            task: Task ID within the plan (e.g. ``'T3'``).
            plan_dir: Sentinel ``'plan'`` or an absolute path string.
            parent_issue_number: Optional parent story issue number or beads ID.

        Returns:
            The stored :class:`~sam_schema.core.models.ActiveTaskContext` instance.
        """
        task_file_path = _resolve_task_file_path(plan, plan_dir)
        context = ActiveTaskContext(
            task_file_path=task_file_path,
            task_id=task,
            parent_issue_number=parent_issue_number,
            session_id=session_id,
            started_at=datetime.now(tz=UTC).isoformat(),
        )
        payload = json.dumps(context.model_dump(exclude_none=False))
        self._runner.run_text(["remember", payload, "--key", self._ctx_key(session_id)])
        return context

    def clear_active_task(self, session_id: str) -> bool:
        """Remove the active task context for a session from bd remember.

        Args:
            session_id: Claude Code session identifier.

        Returns:
            True if context existed and was removed, False otherwise.
        """
        key = self._ctx_key(session_id)
        existing: str | None = None
        with contextlib.suppress(BdInvocationError):
            existing = self._runner.run_text(["recall", key]).strip() or None
        if not existing:
            return False
        try:
            self._runner.run_text(["forget", key])
        except BdInvocationError:
            return False
        else:
            return True

    def list_active_tasks(self) -> list[ActiveTaskContext]:
        """Return all active task contexts stored in bd remember.

        Scans all remember entries for the ``dh.active-task.`` prefix and
        parses each value as an :class:`~sam_schema.core.models.ActiveTaskContext`.

        Returns:
            List of parsed ActiveTaskContext instances.
        """
        results: list[ActiveTaskContext] = []
        try:
            raw = self._runner.run_json(["memories", "--json"])
            if not isinstance(raw, dict):
                return results
            entries_data = [{"key": k, "value": str(v)} for k, v in raw.items() if k != "schema_version"]
            entries = _REMEMBER_LIST_ADAPTER.validate_python(entries_data)
        except (BdNotInstalledError, BdInvocationError, BdJsonDecodeError, ValidationError):
            return results

        for entry in entries:
            if not entry.key.startswith(_CTX_PREFIX):
                continue
            try:
                data = json.loads(entry.value)
                results.append(ActiveTaskContext.model_validate(data))
            except (json.JSONDecodeError, ValueError):
                continue
        return results


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _resolve_task_file_path(plan: str, plan_dir: str) -> str:
    """Resolve the plan YAML file path (mirrors LocalContextBackend pattern).

    Args:
        plan: Plan address (e.g. ``'Pa1b2c3d4'`` or a slug).
        plan_dir: Sentinel ``'plan'`` or an absolute path string.

    Returns:
        Absolute path string to the plan YAML file.
    """
    base: Path = dh_paths.plan_dir() if plan_dir == "plan" else Path(plan_dir)
    return str(base / f"{plan}.yaml")
