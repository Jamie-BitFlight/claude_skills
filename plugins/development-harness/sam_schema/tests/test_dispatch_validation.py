"""Focused validation tests for the provider-neutral dispatch CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

_plugin_root = Path(__file__).resolve().parents[2]
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

from sam_schema import dispatch

runner = CliRunner()


def test_plan_item_accepts_complete_supported_item_fields() -> None:
    item = dispatch._parse_plan_item(
        "wave=2;issue=101;title=Feature;priority=P2;conflict_group=3;depends_on=7,8;status=complete;parallel=false"
    )

    assert item.model_dump() == {
        "wave": 2,
        "issue": 101,
        "title": "Feature",
        "priority": "P2",
        "conflict_group": 3,
        "depends_on": [7, 8],
        "status": "complete",
        "parallel": False,
    }


def test_plan_item_rejects_non_positive_dependency_and_conflict_ids() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        dispatch._parse_plan_item("wave=1;issue=101;title=Feature;depends_on=0")
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        dispatch._parse_plan_item("wave=1;issue=101;title=Feature;conflict_group=0")


def test_create_plan_rejects_empty_integration_branch_without_operation_call(monkeypatch: pytest.MonkeyPatch) -> None:
    operation = Mock()
    monkeypatch.setattr(dispatch.operations, "dispatch_create_plan", operation)

    result = runner.invoke(
        dispatch.app,
        [
            "create-plan",
            "--milestone-number",
            "1",
            "--milestone-title",
            "Milestone",
            "--integration-branch",
            "",
            "--wave-item",
            "wave=1;issue=101;title=Feature",
        ],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "integration branch must not be empty" in result.stderr
    operation.assert_not_called()


def test_create_plan_forwards_all_supported_dispatch_plan_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    operation = Mock(return_value={"created": True})
    monkeypatch.setattr(dispatch.operations, "dispatch_create_plan", operation)

    result = runner.invoke(
        dispatch.app,
        [
            "create-plan",
            "--milestone-number",
            "1",
            "--milestone-title",
            "Milestone",
            "--integration-branch",
            "main",
            "--wave-item",
            "wave=1;issue=101;title=Feature;priority=P1;conflict_group=3;depends_on=7;status=complete;parallel=false",
            "--conflict-group",
            "group_id=3;reason=shared files;items=101,102",
            "--pre-merge",
            "uv run ruff check",
            "--post-merge",
            "uv run pytest",
        ],
    )

    assert result.exit_code == 0, result.stderr
    operation.assert_called_once_with(
        milestone_number=1,
        plan={
            "milestone": {"number": 1, "title": "Milestone", "integration_branch": "main"},
            "conflict_groups": [{"group_id": 3, "reason": "shared files", "items": ["101", "102"]}],
            "waves": [
                {
                    "wave": 1,
                    "parallel": False,
                    "items": [
                        {
                            "title": "Feature",
                            "issue": 101,
                            "priority": "P1",
                            "conflict_group": 3,
                            "depends_on": [7],
                            "status": "complete",
                        }
                    ],
                }
            ],
            "quality_gates": {"pre_merge": ["uv run ruff check"], "post_merge": ["uv run pytest"]},
        },
        overwrite=False,
        validate=True,
        issue=None,
    )


def test_conflict_group_rejects_empty_branch_and_missing_items() -> None:
    with pytest.raises(ValueError, match=r"conflict groups.*items"):
        dispatch._parse_conflict_group("group_id=1;reason=shared;items=")
    with pytest.raises(ValueError, match="at least 2"):
        dispatch._parse_conflict_group("group_id=1;reason=shared;items=101")
    with pytest.raises(ValueError, match="unknown conflict-group field"):
        dispatch._parse_conflict_group("group_id=1;reason=shared;items=101,102;unexpected=x")
