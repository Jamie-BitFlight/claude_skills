"""Focused tests for shared action-boundary models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition


def test_create_plan_schema_describes_provider_neutral_identity() -> None:
    properties = CreatePlanConfig.model_json_schema()["properties"]

    assert properties["slug"]["description"] == (
        "Logical feature slug stored as the plan's feature identifier (e.g., 'auth-system')."
    )
    assert properties["issue"]["description"] == (
        "Legacy numeric owner alias. Stores the number in plan metadata and associates persisted plan content "
        "with owner reference '#<issue>'. Prefer owner_reference for provider-native identifiers."
    )


def test_task_definition_rejects_unknown_fields() -> None:
    """Unknown task fields fail instead of being silently discarded."""
    with pytest.raises(ValidationError, match="unknown"):
        TaskDefinition.model_validate({"id": "T1", "title": "Implement", "unknown": "unexpected"})


def test_task_definition_retains_required_field_validation() -> None:
    """The title remains required for task authoring."""
    with pytest.raises(ValidationError, match="title"):
        TaskDefinition.model_validate({"id": "T1"})


def test_task_definition_accepts_valid_aliases_and_defaults() -> None:
    """Valid task input keeps aliases and the default status contract."""
    task = TaskDefinition.model_validate({"task": "T1", "title": "Implement", "blocked-by": ["T0"]})

    assert task.id == "T1"
    assert task.status == "not-started"
    assert task.blocked_by == ["T0"]


def test_task_definition_rejects_invalid_values() -> None:
    """Invalid enum and range values fail at the shared boundary."""
    with pytest.raises(ValidationError):
        TaskDefinition.model_validate({"id": "T1", "title": "Implement", "status": "invented"})
    with pytest.raises(ValidationError):
        TaskDefinition.model_validate({"id": "T1", "title": "Implement", "priority": 9})


@pytest.mark.parametrize("valid_id", ["T10a", "T10a/T10b", "P1/T3", "P1/T10a"])
def test_task_definition_accepts_canonical_id_suffix_and_compound_forms(valid_id: str) -> None:
    """Letter-suffixed (T10a) and slash-separated compound (T10a/T10b) IDs are accepted.

    Regression test: TaskDefinition.id previously overrode Task's pattern with a
    narrower regex than TASK_ID_PATTERN, rejecting these documented-valid forms
    before the request reached the backend.
    """
    task = TaskDefinition.model_validate({"id": valid_id, "title": "Implement"})
    assert task.id == valid_id


def test_task_definition_rejects_id_not_matching_task_id_pattern() -> None:
    """An ID outside TASK_ID_PATTERN is still rejected after widening to the canonical pattern."""
    with pytest.raises(ValidationError, match="id"):
        TaskDefinition.model_validate({"id": "invalid-id", "title": "Implement"})
