"""Focused tests for shared action-boundary models."""

from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel, ValidationError

from sam_schema.cli_inputs import CreatePlanInput
from sam_schema.core import action_models
from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition, UpdatePlanConfig


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


# ---------------------------------------------------------------------------
# Closed-object contract on every action config (#3162)
# ---------------------------------------------------------------------------


def _action_config_models() -> list[type[BaseModel]]:
    """Return every concrete action-config model exposed on the SAM tool surface."""
    base = action_models._ActionConfigBase
    return [
        member
        for _, member in inspect.getmembers(action_models, inspect.isclass)
        if issubclass(member, base) and member is not base
    ]


def test_plan_update_config_rejects_parameters_that_do_not_exist() -> None:
    """A plan-level section append was instructed for months and silently wrote nothing.

    ``plan_slug``, ``section`` and ``content`` are not ``UpdatePlanConfig`` fields. While
    the config accepted unknown keys the call returned success having applied no patch,
    so the agent's output was lost with no signal at the call site (#3162).
    """
    with pytest.raises(ValidationError, match="plan_slug"):
        UpdatePlanConfig.model_validate({
            "action": "update",
            "plan_slug": "auth-system",
            "section": "Findings",
            "content": "Research output",
        })


@pytest.mark.parametrize("model", _action_config_models(), ids=lambda m: m.__name__)
def test_action_config_schema_advertises_a_closed_object(model: type[BaseModel]) -> None:
    """Each config branch must publish ``additionalProperties: false``.

    The enclosing tool schema already closes its top level, but a calling agent reads the
    branch schema to learn which keys exist. A branch that advertises nothing invites the
    invented parameter and then discards it.
    """
    assert model.model_json_schema().get("additionalProperties") is False, (
        f"{model.__name__} does not advertise a closed object, so an unknown key on this "
        "action is neither rejected nor visible as invalid in the published schema."
    )


def test_cli_create_plan_passes_no_keys_the_config_forbids() -> None:
    """``plan create`` re-validates its own dump, so a stray key would break the CLI.

    ``sam_plan.create`` builds the action config from ``CreatePlanInput.to_config()``'s
    dump plus ``owner_reference``. Closing the model turns any key outside the field set
    into a hard CLI failure, so the round trip is asserted directly.
    """
    config = CreatePlanInput(slug="auth-system", goal="Ship auth", tasks=[], context=None, issue=None).to_config()

    payload = {**config.model_dump(), "owner_reference": None}

    assert set(payload) <= set(CreatePlanConfig.model_fields), (
        "plan create would pass keys the closed config rejects: "
        f"{sorted(set(payload) - set(CreatePlanConfig.model_fields))}"
    )
    assert CreatePlanConfig.model_validate(payload).slug == "auth-system"
