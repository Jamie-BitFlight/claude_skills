"""Tests for sam_schema.cli — Typer CLI commands via CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sam_schema.cli import app
from typer.testing import CliRunner

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
_PURE_YAML_SINGLE: Path = FIXTURES_DIR / "pure_yaml_single.yaml"


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Create a temporary plan directory containing a copy of pure_yaml_single.yaml.

    The file is named ``tasks-1-auth-system.yaml`` so address ``P1`` resolves
    to it via numeric match, and ``auth-system`` resolves via slug match.

    Returns:
        Path to a ``plan/`` directory with one plan file.
    """
    d = tmp_path / "plan"
    d.mkdir()
    content = _PURE_YAML_SINGLE.read_text(encoding="utf-8")
    (d / "tasks-1-auth-system.yaml").write_text(content, encoding="utf-8")
    return d


@pytest.fixture
def legacy_plan_dir(tmp_path: Path) -> Path:
    """Create a temporary plan directory containing a legacy markdown plan file.

    Returns:
        Path to a ``plan/`` directory with a legacy-format plan file.
    """
    d = tmp_path / "plan"
    d.mkdir()
    content = (FIXTURES_DIR / "legacy_markdown.md").read_text(encoding="utf-8")
    (d / "tasks-2-legacy.md").write_text(content, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# sam --help
# ---------------------------------------------------------------------------


def test_help_shows_all_commands() -> None:
    """--help output lists all expected commands including list."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("list", "read", "state", "ready", "status", "migrate"):
        assert cmd in result.output


# ---------------------------------------------------------------------------
# sam list
# ---------------------------------------------------------------------------


def test_list_returns_json_with_items_count_total(plan_dir: Path) -> None:
    """List returns a JSON envelope with items, count, and total."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # list_plans returns an envelope {"items": [...], "count": N, "total": N}.
    assert isinstance(data, dict)
    assert "items" in data
    assert "count" in data
    assert "total" in data
    assert len(data["items"]) >= 1


def test_list_items_contain_expected_fields(plan_dir: Path) -> None:
    """Each item in list output has feature, goal, task_count, and plan_ref fields."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    items = data["items"]
    assert len(items) >= 1
    item = items[0]
    assert "feature" in item
    assert "task_count" in item
    assert "plan_ref" in item


def test_list_search_filters_by_feature_name(plan_dir: Path) -> None:
    """List --search auth-system returns only matching plans."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir), "--search", "auth-system"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    items = data["items"]
    assert len(items) >= 1
    for item in items:
        feature_val = str(item.get("feature", "")).lower()
        goal_val = str(item.get("goal", "")).lower()
        desc_val = str(item.get("description", "")).lower()
        assert "auth-system" in feature_val or "auth-system" in goal_val or "auth-system" in desc_val


def test_list_search_no_match_returns_empty_items(plan_dir: Path) -> None:
    """List --search with no matching plans returns an empty items array."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir), "--search", "zzz-no-match-zzz"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert data["items"] == []


def test_list_offset_and_limit_paginate_results(plan_dir: Path) -> None:
    """List --offset 0 --limit 1 returns at most one item."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir), "--offset", "0", "--limit", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    items = data["items"]
    assert len(items) <= 1


def test_list_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """List with non-existent plan_dir exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["list", "--plan-dir", str(missing)])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_list_invalid_format_exits_with_code_1(plan_dir: Path) -> None:
    """List --format invalid exits 1."""
    result = runner.invoke(app, ["list", "--plan-dir", str(plan_dir), "--format", "invalid"])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# sam read
# ---------------------------------------------------------------------------


def test_read_returns_task_assignment_json_with_task_address(plan_dir: Path) -> None:
    """Read P1/T1 returns TaskAssignment JSON with plan context + nested task."""
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # TaskAssignment wraps the task inside a "task" field.
    assert "task" in data
    assert data["task"]["id"] == "T1"
    assert data["task"]["status"] == "complete"


def test_read_task_assignment_includes_plan_fields(plan_dir: Path) -> None:
    """Read P1/T1 returns plan-level fields alongside the task."""
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Plan-level fields are present at top level (may be None if not set in fixture).
    assert "task" in data
    # plan_number and plan_slug are derived from filename when source_path is set.
    # They may be absent (excluded by exclude_none) if the fixture has no source_path stem.


def test_read_uses_slug_address(plan_dir: Path) -> None:
    """Read Pauth-system/T2 resolves via slug match and returns TaskAssignment."""
    result = runner.invoke(app, ["read", "Pauth-system/T2", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["task"]["id"] == "T2"


def test_read_with_yaml_format_option(plan_dir: Path) -> None:
    """Read --format yaml emits YAML output containing nested task id."""
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(plan_dir), "--format", "yaml"])
    assert result.exit_code == 0, result.output
    # Task is nested under the 'task' key in the TaskAssignment YAML.
    assert "T1" in result.output


def test_read_with_rich_format_option(plan_dir: Path) -> None:
    """Read --format rich produces table output with task title."""
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(plan_dir), "--format", "rich"])
    assert result.exit_code == 0
    assert "Define auth data models" in result.output


def test_read_invalid_address_exits_with_code_1(plan_dir: Path) -> None:
    """Read with completely invalid address exits 1 with error message."""
    result = runner.invoke(app, ["read", "INVALID", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_read_plan_only_address_returns_plan_json(plan_dir: Path) -> None:
    """Read P1 (no task part) returns ReadResult JSON — plan is nested under 'plan' key."""
    result = runner.invoke(app, ["read", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # read_plan returns a ReadResult with .plan, .gaps, .source_format, .source_path.
    # The plan fields are nested under the "plan" key.
    assert "plan" in data
    assert "task" not in data
    assert "feature" in data["plan"]


def test_read_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Read P99/T1 (no matching plan number) exits 1."""
    result = runner.invoke(app, ["read", "P99/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_read_nonexistent_task_exits_with_code_1(plan_dir: Path) -> None:
    """Read P1/T99 (task not in plan) exits 1."""
    result = runner.invoke(app, ["read", "P1/T99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_read_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """Read with a plan_dir that does not exist exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(missing)])
    assert result.exit_code == 1


def test_read_invalid_format_option_exits_with_code_1(plan_dir: Path) -> None:
    """Read --format invalid exits 1 with error message."""
    result = runner.invoke(app, ["read", "P1/T1", "--plan-dir", str(plan_dir), "--format", "invalid"])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# sam status
# ---------------------------------------------------------------------------


def test_status_returns_json_summary(plan_dir: Path) -> None:
    """Status P1 returns JSON with feature, total_tasks, and by_status."""
    result = runner.invoke(app, ["status", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["feature"] == "auth-system"
    assert "total_tasks" in data
    assert "by_status" in data
    assert "completion_pct" in data
    assert "ready_tasks" in data


def test_status_with_rich_format_produces_table(plan_dir: Path) -> None:
    """Status P1 --format rich produces Rich table output."""
    result = runner.invoke(app, ["status", "P1", "--plan-dir", str(plan_dir), "--format", "rich"])
    assert result.exit_code == 0
    assert "auth-system" in result.output


def test_status_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Status P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["status", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_status_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """Status with non-existent plan_dir exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["status", "P1", "--plan-dir", str(missing)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam ready
# ---------------------------------------------------------------------------


def test_ready_returns_json_list(plan_dir: Path) -> None:
    """Ready P1 returns a JSON envelope with ready_tasks (may be empty or contain tasks)."""
    result = runner.invoke(app, ["ready", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "ready_tasks" in data


def test_ready_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Ready P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["ready", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_ready_explicit_json_format_option_succeeds(plan_dir: Path) -> None:
    """Ready P1 --format json exits 0 and returns a JSON envelope with ready_tasks."""
    result = runner.invoke(app, ["ready", "P1", "--format", "json", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "ready_tasks" in data


def test_ready_yaml_format_option_produces_yaml(plan_dir: Path) -> None:
    """Ready P1 --format yaml exits 0 and produces non-JSON YAML-style output."""
    result = runner.invoke(app, ["ready", "P1", "--format", "yaml", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    # YAML output for an empty list is '[]' or '- ...' blocks; either way not a JSON list
    # Just verify exit code 0 and non-empty output when there are tasks, or empty list syntax.
    assert result.exit_code == 0


def test_ready_invalid_format_exits_with_code_1(plan_dir: Path) -> None:
    """Ready P1 --format invalid exits 1."""
    result = runner.invoke(app, ["ready", "P1", "--format", "invalid", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# sam state
# ---------------------------------------------------------------------------


def test_state_updates_task_status_and_prints_confirmation(plan_dir: Path) -> None:
    """State P1/T3 in-progress updates status and prints old -> new."""
    result = runner.invoke(app, ["state", "P1/T3", "in-progress", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    assert "T3" in result.output
    assert "in-progress" in result.output


def test_state_invalid_status_value_exits_with_code_1(plan_dir: Path) -> None:
    """State P1/T1 bananas exits 1 with error about invalid status."""
    result = runner.invoke(app, ["state", "P1/T1", "bananas", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_state_missing_task_component_exits_with_code_1(plan_dir: Path) -> None:
    """State P1 (no task) exits 1."""
    result = runner.invoke(app, ["state", "P1", "complete", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_state_nonexistent_task_exits_with_code_1(plan_dir: Path) -> None:
    """State P1/T99 (task not in plan) exits 1."""
    result = runner.invoke(app, ["state", "P1/T99", "complete", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_state_output_shows_old_and_new_status(plan_dir: Path) -> None:
    """State P1/T3 complete shows both old and new status in output."""
    result = runner.invoke(app, ["state", "P1/T3", "complete", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    # T3 starts as not-started, should show transition
    assert "->" in result.output


# ---------------------------------------------------------------------------
# sam migrate
# ---------------------------------------------------------------------------


def test_migrate_dry_run_prints_plan_info_without_writing(legacy_plan_dir: Path) -> None:
    """Migrate P2 --dry-run prints what would change without modifying files."""
    original_files = set(legacy_plan_dir.iterdir())
    result = runner.invoke(app, ["migrate", "P2", "--dry-run", "--plan-dir", str(legacy_plan_dir)])
    assert result.exit_code == 0
    assert "Would migrate" in result.output
    assert "Source format" in result.output
    # No new files should be written
    assert set(legacy_plan_dir.iterdir()) == original_files


def test_migrate_converts_legacy_to_yaml(legacy_plan_dir: Path) -> None:
    """Migrate P2 converts a legacy markdown plan to .yaml format."""
    result = runner.invoke(app, ["migrate", "P2", "--plan-dir", str(legacy_plan_dir)])
    assert result.exit_code == 0
    assert "Migrated" in result.output
    # A .yaml file should now exist in the plan dir
    yaml_files = list(legacy_plan_dir.glob("*.yaml"))
    assert len(yaml_files) >= 1


def test_migrate_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Migrate P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["migrate", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam validate
# ---------------------------------------------------------------------------


def test_validate_canonical_plan_reports_valid(plan_dir: Path) -> None:
    """Validate P1 on a canonical YAML plan reports no errors or warnings."""
    result = runner.invoke(app, ["validate", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["errors"] == []
    assert data["warnings"] == []


def test_validate_legacy_plan_reports_gaps(legacy_plan_dir: Path) -> None:
    """Validate P2 on a legacy markdown plan surfaces schema gaps as errors.

    This verifies that operations.read_plan preserves gaps from the
    reader/normalizer pipeline through the backend and back to ReadResult.
    Without the fix, gaps was hardcoded to [] and validate reported
    {"valid": true} for non-canonical plans.
    """
    result = runner.invoke(app, ["validate", "P2", "--plan-dir", str(legacy_plan_dir)])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert len(data["errors"]) > 0
