"""Focused tests for typed CLI input adapters."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sam_schema.cli_inputs import (
    AppendTaskInput,
    CreatePlanInput,
    PlanUpdateFields,
    PlanUpdateInput,
    TaskUpdateFields,
    TaskUpdateInput,
)
from sam_schema.core.action_models import TaskDefinition


def task() -> TaskDefinition:
    """Build the smallest valid task input."""
    return TaskDefinition(id="T1", title="Implement")


def test_create_and_append_adapters_validate_immediately() -> None:
    """Create and append adapters construct canonical action inputs."""
    create = CreatePlanInput(slug="cli", goal="Typed boundary", tasks=[task()])
    append = AppendTaskInput(plan_address="P1", task=task())

    assert create.to_config().tasks[0].id == "T1"
    assert append.to_config().task.title == "Implement"

    with pytest.raises(ValidationError):
        CreatePlanInput.model_validate({"slug": "cli", "goal": "x", "unexpected": True})


def test_update_fields_are_explicit_and_aliased() -> None:
    """Supported fields serialize without arbitrary key/value passthrough."""
    fields = TaskUpdateFields.model_validate({"status": "complete", "blocked-by": ["T0"]})
    plan_fields = PlanUpdateFields.model_validate({"acceptance-criteria": "ship it"})

    assert fields.as_operation_fields() == {"status": "complete", "blocked-by": ["T0"]}
    assert plan_fields.as_operation_fields() == {"acceptance-criteria": "ship it"}
    with pytest.raises(ValidationError):
        TaskUpdateFields.model_validate({"not_supported": "value"})


def test_update_adapters_reject_incomplete_sections_and_empty_patches() -> None:
    """Section appends and field updates have complete, non-empty shapes."""
    with pytest.raises(ValidationError, match="at least one task update field"):
        TaskUpdateFields.model_validate({})
    with pytest.raises(ValidationError, match="provided together"):
        TaskUpdateInput(
            plan_address="P1",
            task_id="T1",
            fields=TaskUpdateFields.model_validate({"status": "complete"}),
            append_section="Notes",
        )
    with pytest.raises(ValidationError, match="at least one plan update field"):
        PlanUpdateInput(plan_address="P1")


def test_completed_and_last_activity_reject_non_iso_datetime_strings() -> None:
    """`completed`/`last-activity` are deliberately `str` fields (click's DateTime type
    rejects UTC-offset ISO-8601 strings), but that must not mean any string is accepted.
    """
    with pytest.raises(ValidationError):
        TaskUpdateFields(completed="not-a-date")
    with pytest.raises(ValidationError):
        TaskUpdateFields(last_activity="not-a-date")


def test_completed_and_last_activity_accept_iso_datetime_strings_and_stay_strings() -> None:
    """Naive and UTC-offset ISO-8601 strings are both valid and round-trip as strings, not datetimes."""
    naive = TaskUpdateFields(completed="2026-08-29T12:00:00")
    offset = TaskUpdateFields(last_activity="2026-08-29T12:00:00+00:00")

    assert naive.as_operation_fields() == {"completed": "2026-08-29T12:00:00"}
    assert isinstance(naive.completed, str)
    assert offset.as_operation_fields() == {"last-activity": "2026-08-29T12:00:00+00:00"}
    assert isinstance(offset.last_activity, str)
