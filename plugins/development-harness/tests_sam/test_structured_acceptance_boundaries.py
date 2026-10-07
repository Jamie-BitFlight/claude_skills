from __future__ import annotations

import json
from typing import TYPE_CHECKING

from backlog_core.backend_protocol import get_config
from backlog_core.backend_types import ContentProvider
from sam_schema.cli import app
from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition
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
    plan = content_backend.create_plan(
        "structured-update", "persist structured criteria", [], acceptance_criteria="Keep this prose."
    )
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
    assert ContentTaskProvider(provider).read_plan(plan["plan_id"])["acceptance_criteria"] == "Keep this prose."


def test_mcp_create_persists_task_scalar_variants(content_backend: ContentTaskProvider) -> None:
    tasks = [
        TaskDefinition(
            id=f"T{priority}",
            title=f"Task {priority}",
            status="not-started",
            agent="agent",
            priority=priority,
            complexity=complexity,
            issue_classification=classification,
            analysis_method=method,
        )
        for priority, complexity, classification, method in [
            (1, "low", "procedural", "none"),
            (2, "medium", "defect", "5-whys"),
            (3, "high", "recurring-pattern", "none"),
            (4, "low", "procedural", "5-whys"),
            (5, "medium", "defect", "none"),
        ]
    ]
    result = sam_plan(config=CreatePlanConfig(slug="scalar-variants", goal="persist scalar variants", tasks=tasks))

    assert isinstance(result, CreatePlanResult)
    provider = get_config().backend
    assert isinstance(provider, ContentProvider)
    persisted = ContentTaskProvider(provider).read_plan(result.plan_id)["tasks"]
    assert [task["priority"] for task in persisted] == [1, 2, 3, 4, 5]
    assert [task["complexity"] for task in persisted] == ["low", "medium", "high", "low", "medium"]
    assert [task["issue_classification"] for task in persisted] == [
        "procedural",
        "defect",
        "recurring-pattern",
        "procedural",
        "defect",
    ]
    assert [task["analysis_method"] for task in persisted] == ["none", "5-whys", "none", "5-whys", "none"]


def test_cli_update_rejects_incomplete_structured_criterion_without_persisting(
    content_backend: ContentTaskProvider,
) -> None:
    plan = content_backend.create_plan("structured-rejection", "reject incomplete criteria", [])

    result = CliRunner().invoke(
        app,
        [
            "plan",
            "update",
            "--plan-address",
            plan["plan_id"],
            "--acceptance-criteria-structured-json",
            json.dumps([{"criterion-id": "AC-1"}], separators=(",", ":")),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code != 0
    provider = get_config().backend
    assert isinstance(provider, ContentProvider)
    assert "acceptance_criteria_structured" not in ContentTaskProvider(provider).read_plan(plan["plan_id"])
