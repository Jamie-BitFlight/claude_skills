from __future__ import annotations

import pytest
from backlog_core.backends.memory_backend import InMemoryBackend

from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.backends.memory import InMemoryTaskProvider


def test_in_memory_provider_preserves_structured_acceptance_criteria_update() -> None:
    # Given: a plan in the in-memory task provider.
    provider = InMemoryTaskProvider()
    plan = provider.create_plan("structured-criteria", "preserve structured criteria", [])
    criteria = [{"criterion_id": "AC-1", "check_command": "uv run pytest", "expected_final": "pass"}]

    # When: structured acceptance criteria are updated through the plan field seam.
    provider.update_plan_fields(plan["plan_id"], set_fields={"acceptance_criteria_structured": criteria})

    # Then: reading the plan returns the updated criteria unchanged.
    assert provider.read_plan(plan["plan_id"])["acceptance_criteria_structured"] == criteria


@pytest.mark.parametrize("field_name", ["acceptance_criteria_structured", "acceptance-criteria-structured"])
def test_content_provider_persists_structured_acceptance_criteria_update(field_name: str) -> None:
    # Given: a plan persisted through the configured content provider.
    content = InMemoryBackend()
    provider = ContentTaskProvider(content)
    plan = provider.create_plan("structured-criteria", "persist structured criteria", [])
    criteria = [{"criterion_id": "AC-1", "check_command": "uv run pytest", "expected_final": "pass"}]

    # When: structured acceptance criteria are updated and the task provider is reconstructed.
    provider.update_plan_fields(plan["plan_id"], set_fields={field_name: criteria})
    reloaded = ContentTaskProvider(content)

    # Then: reading through the configured provider returns the persisted criteria unchanged.
    assert reloaded.read_plan(plan["plan_id"])["acceptance_criteria_structured"] == criteria
