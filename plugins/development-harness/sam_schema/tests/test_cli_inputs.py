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
