"""Focused tests for shared action-boundary models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sam_schema.core.action_models import TaskDefinition


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
