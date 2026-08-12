"""SAM task storage composed over the configured content capability."""

from __future__ import annotations

import json
from collections.abc import Sequence

from backlog_core.backend_types import ContentProvider
from backlog_core.models import ContentKind, ContentQuery, ContentRef, ContentWrite
from pydantic import TypeAdapter

from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.models import PlanState, Task
from sam_schema.core.task_backend_types import PlanData

_PLAN_DATA_ADAPTER = TypeAdapter(PlanData)
_PLAN_DATA_ADAPTER.rebuild(_types_namespace={"PlanState": PlanState})
_CONTENT_PAGE_SIZE = 100


class ContentTaskProvider(InMemoryTaskProvider):
    """Persist the established in-memory task behavior through ContentProvider."""

    def __init__(self, provider: ContentProvider) -> None:
        """Load current logical plans from the configured provider."""
        super().__init__()
        self._provider = provider
        offset = 0
        while True:
            records = provider.list_content(
                ContentQuery(kind=ContentKind.PLAN, offset=offset, limit=_CONTENT_PAGE_SIZE)
            )
            for record in records:
                plan = _PLAN_DATA_ADAPTER.validate_json(record.content)
                self._plans[plan["plan_id"]] = plan
            if len(records) < _CONTENT_PAGE_SIZE:
                break
            offset += len(records)

    def _flush(self, plan_id: str, owner_reference: str | None = None) -> None:
        self._provider.put_content(
            ContentWrite(
                reference=ContentRef(kind=ContentKind.PLAN, name=plan_id),
                content=json.dumps(self._plans[plan_id], separators=(",", ":"), default=str),
                owner_reference=owner_reference,
            )
        )

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
        """Create and persist a plan.

        Returns:
            The created plan.
        """
        plan = super().create_plan(
            slug, goal, tasks, context=context, issue=issue, acceptance_criteria=acceptance_criteria
        )
        self._flush(plan["plan_id"], f"#{issue}" if issue is not None else "")
        return plan

    def set_owner(self, plan_id: str, owner_reference: str) -> None:
        """Atomically reassign plan ownership."""
        self._flush(plan_id, owner_reference)

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
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
            self._flush(plan_id)
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
