"""Current server backend must not reintroduce the retired local-plan route."""

from __future__ import annotations

from pathlib import Path

import pytest
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.exceptions import PlanNotFoundError
from sam_schema.core.models import Task, TaskStatus
from sam_schema.server_backend import get_backend


def _create_local_only_plan(plan_dir: Path, slug: str, tasks: list[Task]) -> str:
    """Write a local-only legacy plan for the retired-route guard."""
    local = LocalYamlTaskProvider(plan_dir)
    plan_data = local.create_plan(
        slug=slug, goal=f"Legacy local plan: {slug}", tasks=tasks, context="Legacy local plan", issue=None
    )
    return plan_data["plan_id"]


def test_server_backend_does_not_fallback_to_local_plan(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    plan_id = _create_local_only_plan(
        plan_dir, "warning-plan", [Task(id="T1", title="Task", status=TaskStatus.NOT_STARTED)]
    )

    backend = get_backend(str(plan_dir))

    assert isinstance(backend, ContentTaskProvider)
    with pytest.raises(PlanNotFoundError):
        backend.read_plan(plan_id)
