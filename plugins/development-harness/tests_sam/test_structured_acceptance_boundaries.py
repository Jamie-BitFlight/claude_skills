from __future__ import annotations

import json
from typing import TYPE_CHECKING

from backlog_core.backend_protocol import get_config
from backlog_core.backend_types import ContentProvider
from sam_schema.cli import app
from sam_schema.core.action_models import CreatePlanConfig
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.models import CreatePlanResult
from sam_schema.server import sam_plan
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path


def test_mcp_create_persists_structured_acceptance_criteria(
    tmp_path: Path, content_backend: ContentTaskProvider
) -> None:
    # Given: an MCP create payload using the public kebab-case field.
    criteria = [{"criterion-id": "AC-1", "check-command": "uv run pytest", "expected-final": "pass"}]
    config = CreatePlanConfig.model_validate({
        "slug": "structured-create",
        "goal": "persist structured criteria",
        "tasks": [],
        "acceptance-criteria-structured": criteria,
    })

    # When: the consolidated MCP plan tool creates the plan.
    result = sam_plan(config=config, plan_dir=str(tmp_path))

    # Then: provider readback contains the normalized structured criteria.
    assert isinstance(result, CreatePlanResult)
    provider = get_config().backend
    assert isinstance(provider, ContentProvider)
    assert ContentTaskProvider(provider).read_plan(result.plan_id)["acceptance_criteria_structured"] == [
        {
            "criterion_id": "AC-1",
            "description": "",
            "check_command": "uv run pytest",
            "expected_baseline": "any",
            "expected_final": "pass",
        }
    ]


def test_cli_update_persists_structured_acceptance_criteria(content_backend: ContentTaskProvider) -> None:
    # Given: an existing provider plan and a compact JSON criteria payload.
    plan = content_backend.create_plan("structured-update", "persist structured criteria", [])
    criteria = [{"criterion-id": "AC-2", "check-command": "uv run ty check .", "expected-final": "pass"}]

    # When: the grouped CLI update applies the structured criteria field.
    result = CliRunner().invoke(
        app,
        [
            "plan",
            "update",
            "--plan-address",
            plan["plan_id"],
            "--acceptance-criteria-structured-json",
            json.dumps(criteria, separators=(",", ":")),
        ],
        env={"NO_COLOR": "1"},
    )

    # Then: the command succeeds and provider readback contains normalized criteria.
    assert result.exit_code == 0, result.stdout
    provider = get_config().backend
    assert isinstance(provider, ContentProvider)
    assert ContentTaskProvider(provider).read_plan(plan["plan_id"])["acceptance_criteria_structured"] == [
        {
            "criterion_id": "AC-2",
            "description": "",
            "check_command": "uv run ty check .",
            "expected_baseline": "any",
            "expected_final": "pass",
        }
    ]
