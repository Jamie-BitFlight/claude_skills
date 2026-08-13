"""SAM task storage composed over the configured content capability."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from backlog_core.backend_types import ContentProvider
from backlog_core.models import ContentConflictError, ContentKind, ContentQuery, ContentRef, ContentWrite
from pydantic import TypeAdapter, ValidationError
from ruamel.yaml import YAML

from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.models import AcceptanceCriterion, PlanState, Task
from sam_schema.core.task_backend_types import PlanData, PlanUpdateValue
from sam_schema.readers.detect import FormatType
from sam_schema.readers.normalize import normalize_plan

_PLAN_DATA_ADAPTER = TypeAdapter(PlanData)
_PLAN_DATA_ADAPTER.rebuild(_types_namespace={"PlanState": PlanState})
_CONTENT_PAGE_SIZE = 100
_LEGACY_PLAN_YAML = YAML(typ="safe")


def parse_plan_content(content: str, record_name: str) -> PlanData:
    """Normalize canonical JSON or legacy provider YAML into plan data.

    Returns:
        The normalized plan payload.
    """
    try:
        return _PLAN_DATA_ADAPTER.validate_json(content)
    except ValidationError as exc:
        if not any(error["type"] == "json_invalid" for error in exc.errors()):
            raise

    raw_plan = _LEGACY_PLAN_YAML.load(content)
    if not isinstance(raw_plan, dict) or not isinstance(raw_tasks := raw_plan.get("tasks", []), list):
        return _PLAN_DATA_ADAPTER.validate_python(raw_plan)

    result = normalize_plan(raw_plan, raw_tasks, FormatType.PURE_YAML, Path(record_name))
    plan_data = result.plan.model_dump(mode="json")
    plan_data.update(
        goal=result.plan.goal or "",
        context=result.plan.context or "",
        acceptance_criteria=result.plan.acceptance_criteria or "",
        source_path=None,
    )
    return _PLAN_DATA_ADAPTER.validate_python(plan_data)


class ContentTaskProvider(InMemoryTaskProvider):
    """Persist the established in-memory task behavior through ContentProvider."""

    def __init__(self, provider: ContentProvider) -> None:
        """Load current logical plans from the configured provider."""
        super().__init__()
        self._provider = provider
        self._revisions: dict[str, str] = {}
        offset = 0
        while True:
            records = provider.list_content(
                ContentQuery(kind=ContentKind.PLAN, offset=offset, limit=_CONTENT_PAGE_SIZE)
            )
            for record in records:
                plan = parse_plan_content(record.content, record.reference.name)
                self._plans[plan["plan_id"]] = plan
                self._revisions[plan["plan_id"]] = record.revision
            if len(records) < _CONTENT_PAGE_SIZE:
                break
            offset += len(records)

    def _flush(self, plan_id: str, owner_reference: str | None = None) -> None:
        record = self._provider.put_content(
            ContentWrite(
                reference=ContentRef(kind=ContentKind.PLAN, name=plan_id),
                content=json.dumps(self._plans[plan_id], separators=(",", ":"), default=str),
                owner_reference=owner_reference,
                expected_revision=self._revisions.get(plan_id, ""),
            )
        )
        self._revisions[plan_id] = record.revision

    def _refresh(self, plan_id: str) -> None:
        record = self._provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan_id))
        self._plans[plan_id] = parse_plan_content(record.content, record.reference.name)
        self._revisions[plan_id] = record.revision

    def create_plan(
        self,
        slug: str,
        goal: str,
        tasks: Sequence[Task],
        *,
        context: str | None = None,
        issue: int | None = None,
        acceptance_criteria: str | None = None,
        acceptance_criteria_structured: Sequence[AcceptanceCriterion] | None = None,
    ) -> PlanData:
        """Create and persist a plan.

        Returns:
            The created plan.
        """
        plan = super().create_plan(
            slug,
            goal,
            tasks,
            context=context,
            issue=issue,
            acceptance_criteria=acceptance_criteria,
            acceptance_criteria_structured=acceptance_criteria_structured,
        )
        self._flush(plan["plan_id"], f"#{issue}" if issue is not None else "")
        return plan

    def set_owner(self, plan_id: str, owner_reference: str) -> None:
        """Atomically reassign plan ownership."""
        self._flush(plan_id, owner_reference)

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, PlanUpdateValue] | None = None
    ) -> None:
        """Update and persist plan fields."""
        super().update_plan_fields(plan_id, context=context, set_fields=set_fields)
        self._flush(plan_id)

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Claim and persist a task.

        Returns:
            Whether the task was claimed.
        """
        claimed = super().claim_task(plan_id, task_id)
        if claimed:
            try:
                self._flush(plan_id)
            except ContentConflictError:
                self._refresh(plan_id)
                return False
        return claimed

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update and persist task status."""
        super().update_task_status(plan_id, task_id, status)
        self._flush(plan_id)

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update and persist task fields."""
        super().update_task_fields(plan_id, task_id, fields)
        self._flush(plan_id)

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace and persist a task."""
        super().update_task(plan_id, task)
        self._flush(plan_id)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append and persist a task section."""
        super().append_task_section(plan_id, task_id, section_name, content)
        self._flush(plan_id)

    def append_task(self, plan_id: str, task: Task) -> dict[str, object]:
        """Append and persist a task.

        Returns:
            The append operation result.
        """
        result = super().append_task(plan_id, task)
        self._flush(plan_id)
        return result

    def finalize_plan(self, plan_id: str) -> dict[str, object]:
        """Finalize and persist a plan.

        Returns:
            The finalization result.
        """
        result = super().finalize_plan(plan_id)
        self._flush(plan_id)
        return result
