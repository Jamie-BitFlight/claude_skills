"""SAM task storage composed over the configured content capability."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar

from backlog_core.backend_types import ContentProvider
from backlog_core.models import (
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentProviderError,
    ContentQuery,
    ContentRef,
    ContentWrite,
)
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
_MutationResult = TypeVar("_MutationResult")


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

    def _mutate(
        self, mutation: Callable[[], tuple[str | None, _MutationResult]], *, owner_reference: str | None = None
    ) -> _MutationResult:
        plans_before = copy.deepcopy(self._plans)
        revisions_before = self._revisions.copy()
        plan_id, result = mutation()
        if plan_id is None:
            return result
        try:
            self._flush(plan_id, owner_reference)
        except ContentProviderError:
            try:
                self._refresh(plan_id)
            except ContentNotFoundError:
                self._plans.pop(plan_id, None)
                self._revisions.pop(plan_id, None)
            except ContentProviderError:
                self._plans = plans_before
                self._revisions = revisions_before
            raise
        return result

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
        owner_reference: str | None = None,
        acceptance_criteria: str | None = None,
        acceptance_criteria_structured: Sequence[AcceptanceCriterion] | None = None,
    ) -> PlanData:
        """Create and persist a plan.

        Returns:
            The created plan.
        """

        def create() -> tuple[str, PlanData]:
            plan = super(ContentTaskProvider, self).create_plan(
                slug,
                goal,
                tasks,
                context=context,
                issue=issue,
                owner_reference=owner_reference,
                acceptance_criteria=acceptance_criteria,
                acceptance_criteria_structured=acceptance_criteria_structured,
            )
            return plan["plan_id"], plan

        return self._mutate(
            create,
            owner_reference=owner_reference
            if owner_reference is not None
            else f"#{issue}"
            if issue is not None
            else "",
        )

    def set_owner(self, plan_id: str, owner_reference: str) -> None:
        """Atomically reassign plan ownership."""
        self._mutate(lambda: (plan_id, None), owner_reference=owner_reference)

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, PlanUpdateValue] | None = None
    ) -> None:
        """Update and persist plan fields."""
        self._mutate(
            lambda: (
                plan_id,
                super(ContentTaskProvider, self).update_plan_fields(plan_id, context=context, set_fields=set_fields),
            )
        )

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Claim and persist a task.

        Returns:
            Whether the task was claimed.
        """
        try:
            return self._mutate(
                lambda: (
                    plan_id if (claimed := super(ContentTaskProvider, self).claim_task(plan_id, task_id)) else None,
                    claimed,
                )
            )
        except ContentConflictError:
            return False

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update and persist task status."""
        self._mutate(lambda: (plan_id, super(ContentTaskProvider, self).update_task_status(plan_id, task_id, status)))

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update and persist task fields."""
        self._mutate(lambda: (plan_id, super(ContentTaskProvider, self).update_task_fields(plan_id, task_id, fields)))

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace and persist a task."""
        self._mutate(lambda: (plan_id, super(ContentTaskProvider, self).update_task(plan_id, task)))

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append and persist a task section."""
        self._mutate(
            lambda: (
                plan_id,
                super(ContentTaskProvider, self).append_task_section(plan_id, task_id, section_name, content),
            )
        )

    def append_task(self, plan_id: str, task: Task) -> dict[str, object]:
        """Append and persist a task.

        Returns:
            The append operation result.
        """
        return self._mutate(lambda: (plan_id, super(ContentTaskProvider, self).append_task(plan_id, task)))

    def finalize_plan(self, plan_id: str) -> dict[str, object]:
        """Finalize and persist a plan.

        Returns:
            The finalization result.
        """
        return self._mutate(lambda: (plan_id, super(ContentTaskProvider, self).finalize_plan(plan_id)))
