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

    The file is named ``P001-auth-system.yaml`` so address ``P1`` resolves
    to it via numeric match, and ``auth-system`` resolves via slug match.

    Returns:
        Path to a ``plan/`` directory with one plan file.
    """
    d = tmp_path / "plan"
    d.mkdir()
    content = _PURE_YAML_SINGLE.read_text(encoding="utf-8")
    (d / "P001-auth-system.yaml").write_text(content, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# sam --help
# ---------------------------------------------------------------------------


def test_help_shows_all_commands() -> None:
    """--help output lists the grouped command domains."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("plan", "backlog", "dispatch", "artifact", "active-task"):
        assert cmd in result.stdout


def test_append_task_uses_typed_options(plan_dir: Path) -> None:
    """append-task uses named typed task fields."""
    result = runner.invoke(
        app,
        [
            "plan",
            "append-task",
            "--plan-address",
            "P1",
            "--plan-dir",
            str(plan_dir),
            "--task-id",
            "T4",
            "--task-title",
            "Legacy task",
            "--task-status",
            "not-started",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"appended": True, "task_id": "T4"}


def test_append_task_stdin_carries_fields_absent_from_typed_options(plan_dir: Path) -> None:
    """append-task --stdin persists skills and body, which the scalar options cannot carry.

    Tests: structured stdin input path restores full-fidelity task authoring.
    How: Pipe a YAML task mapping with skills/body via --stdin, read the task back.
    Why: The scalar typed options omit acceptance criteria, verification steps, handoff,
        body, and skills entirely -- --stdin is the documented (AGENTS.md) large-plan
        append path and must round-trip those fields.
    """
    task_yaml = (
        "task: T4\n"
        "title: Rich task\n"
        "status: not-started\n"
        "skills:\n"
        "  - python-engineering:python3-cli\n"
        "body: |\n"
        "  ## Objective\n"
        "  Do the thing.\n"
    )
    result = runner.invoke(
        app, ["plan", "append-task", "--plan-address", "P1", "--plan-dir", str(plan_dir), "--stdin"], input=task_yaml
    )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == {"appended": True, "task_id": "T4"}

    read_result = runner.invoke(app, ["plan", "read", "--address", "P1/T4", "--plan-dir", str(plan_dir)])
    task = json.loads(read_result.stdout)["task"]
    assert task["skills"] == ["python-engineering:python3-cli"]
    assert task["body"] == "## Objective\nDo the thing.\n"


def test_append_task_stdin_combined_with_typed_option_is_rejected(plan_dir: Path) -> None:
    """append-task rejects --stdin combined with a scalar typed task option.

    Tests: mixed structured/scalar input is a clear caller error, not silently merged.
    How: Pass --stdin together with --task-id, expect a parser-level rejection.
    Why: Ambiguous precedence between the two input paths must not be resolved silently.
    """
    result = runner.invoke(
        app,
        ["plan", "append-task", "--plan-address", "P1", "--plan-dir", str(plan_dir), "--stdin", "--task-id", "T4"],
        input="task: T4\ntitle: x\n",
    )
    assert result.exit_code != 0
    assert result.stdout == ""
    assert "--stdin" in result.stderr


def test_sam_task_create_accepts_and_forwards_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """sam-task-create accepts --repo and forwards it to operations."""
    captured: dict[str, object] = {}

    def fake_create(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"issue_number": 42, "title": "T1", "url": "", "messages": [], "warnings": [], "errors": []}

    monkeypatch.setattr("sam_schema.sam_plan.operations.create_sam_task", fake_create)
    result = runner.invoke(
        app,
        [
            "plan",
            "sam-task-create",
            "--parent-issue-number",
            "480",
            "--task-id",
            "T1",
            "--feature",
            "f",
            "--task-type",
            "implementation",
            "--agent",
            "a",
            "--priority",
            "1",
            "--description",
            "d",
            "--skill",
            "python",
            "--repo",
            "acme/project",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["repo"] == "acme/project"


def test_sam_task_create_without_skill_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """sam-task-create omitting --skill forwards an empty skills list, not a CLI error.

    Tests: --skill is optional (not required=True at the CLI boundary).
    How: Invoke sam-task-create with no --skill option, monkeypatch operations.create_sam_task.
    Why: SamTask.skills defaults to an empty list -- tasks for the direct dh:task-worker
        fallback intentionally carry no specialist skill and must not be blocked.
    """
    captured: dict[str, object] = {}

    def fake_create(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"issue_number": 42, "title": "T1", "url": "", "messages": [], "warnings": [], "errors": []}

    monkeypatch.setattr("sam_schema.sam_plan.operations.create_sam_task", fake_create)
    result = runner.invoke(
        app,
        [
            "plan",
            "sam-task-create",
            "--parent-issue-number",
            "480",
            "--task-id",
            "T1",
            "--feature",
            "f",
            "--task-type",
            "implementation",
            "--agent",
            "a",
            "--priority",
            "1",
            "--description",
            "d",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["skills"] == []


def test_sam_task_status_accepts_and_forwards_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """sam-task-status accepts --repo and forwards it to operations."""
    captured: dict[str, object] = {}

    def fake_update(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "updated": True,
            "issue_number": 101,
            "new_status": "complete",
            "messages": [],
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr("sam_schema.sam_plan.operations.update_sam_task_status", fake_update)
    result = runner.invoke(
        app, ["plan", "sam-task-status", "--issue-number", "101", "--new-status", "complete", "--repo", "acme/project"]
    )

    assert result.exit_code == 0, result.stdout
    assert captured["repo"] == "acme/project"


# ---------------------------------------------------------------------------
# sam list
# ---------------------------------------------------------------------------


def test_list_returns_json_with_items_count_total(plan_dir: Path) -> None:
    """List returns a JSON envelope with items, count, and total."""
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # list_plans returns an envelope {"items": [...], "count": N, "total": N}.
    assert isinstance(data, dict)
    assert "items" in data
    assert "count" in data
    assert "total" in data
    assert len(data["items"]) >= 1


def test_list_items_contain_expected_fields(plan_dir: Path) -> None:
    """Each item in list output has feature, goal, task_count, and plan_ref fields."""
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    items = data["items"]
    assert len(items) >= 1
    item = items[0]
    assert "feature" in item
    assert "task_count" in item
    assert "plan_ref" in item


def test_list_search_filters_by_feature_name(plan_dir: Path) -> None:
    """List --search auth-system returns only matching plans."""
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir), "--search", "auth-system"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
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
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir), "--search", "zzz-no-match-zzz"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert data["items"] == []


def test_list_offset_and_limit_paginate_results(plan_dir: Path) -> None:
    """List --offset 0 --limit 1 returns at most one item."""
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir), "--offset", "0", "--limit", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    items = data["items"]
    assert len(items) <= 1


def test_list_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """List with non-existent plan_dir exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(missing)])
    assert result.exit_code == 1
    assert not result.stdout
    assert "Error:" in result.stderr


# ---------------------------------------------------------------------------
# sam read
# ---------------------------------------------------------------------------


def test_read_returns_task_assignment_json_with_task_address(plan_dir: Path) -> None:
    """Read P1/T1 returns TaskAssignment JSON with plan context + nested task."""
    result = runner.invoke(app, ["plan", "read", "--address", "P1/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # TaskAssignment wraps the task inside a "task" field.
    assert "task" in data
    assert data["task"]["id"] == "T1"
    assert data["task"]["status"] == "complete"


def test_read_task_assignment_includes_plan_fields(plan_dir: Path) -> None:
    """Read P1/T1 returns plan-level fields alongside the task."""
    result = runner.invoke(app, ["plan", "read", "--address", "P1/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Plan-level fields are present at top level (may be None if not set in fixture).
    assert "task" in data
    # plan_number and plan_slug are derived from filename when source_path is set.
    # They may be absent (excluded by exclude_none) if the fixture has no source_path stem.


def test_read_uses_slug_address(plan_dir: Path) -> None:
    """Read Pauth-system/T2 resolves via slug match and returns TaskAssignment."""
    result = runner.invoke(app, ["plan", "read", "--address", "Pauth-system/T2", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["task"]["id"] == "T2"


def test_read_invalid_address_exits_with_code_1(plan_dir: Path) -> None:
    """Read with completely invalid address exits 1 with error message."""
    result = runner.invoke(app, ["plan", "read", "--address", "INVALID", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1
    assert not result.stdout
    assert "Error:" in result.stderr


def test_read_plan_only_address_returns_plan_json(plan_dir: Path) -> None:
    """Read P1 (no task part) returns ReadResult JSON — plan is nested under 'plan' key."""
    result = runner.invoke(app, ["plan", "read", "--address", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # read_plan returns a ReadResult with .plan, .gaps, .source_format, .source_path.
    # The plan fields are nested under the "plan" key.
    assert "plan" in data
    assert "task" not in data
    assert "feature" in data["plan"]


def test_read_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Read P99/T1 (no matching plan number) exits 1."""
    result = runner.invoke(app, ["plan", "read", "--address", "P99/T1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_read_nonexistent_task_exits_with_code_1(plan_dir: Path) -> None:
    """Read P1/T99 (task not in plan) exits 1."""
    result = runner.invoke(app, ["plan", "read", "--address", "P1/T99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_read_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """Read with a plan_dir that does not exist exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["plan", "read", "--address", "P1/T1", "--plan-dir", str(missing)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam status
# ---------------------------------------------------------------------------


def test_status_returns_json_summary(plan_dir: Path) -> None:
    """Status P1 returns JSON with feature, total_tasks, and by_status."""
    result = runner.invoke(app, ["plan", "status", "--plan-address", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["feature"] == "auth-system"
    assert "total_tasks" in data
    assert "by_status" in data
    assert "completion_pct" in data
    assert "ready_tasks" in data


def test_status_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Status P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["plan", "status", "--plan-address", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


def test_status_missing_plan_dir_exits_with_code_1(tmp_path: Path) -> None:
    """Status with non-existent plan_dir exits 1."""
    missing = tmp_path / "no-such-dir"
    result = runner.invoke(app, ["plan", "status", "--plan-address", "P1", "--plan-dir", str(missing)])
    assert result.exit_code == 1


def test_status_all_skips_structurally_malformed_plan(plan_dir: Path) -> None:
    """Status --all warns and skips a plan whose top level is not a YAML mapping.

    Tests: warn-and-skip resilience against a TypeError-raising candidate.
    How: Add a bare-list YAML file (raises TypeError in the reader, not ValueError)
        alongside the valid fixture plan, then request --all.
    Why: A single malformed plan must not abort the rest of the listing.
    """
    (plan_dir / "P002-bad.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")

    result = runner.invoke(app, ["plan", "status", "--all", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["feature"] == "auth-system"
    assert "Warning: skipping" in result.stderr


# ---------------------------------------------------------------------------
# sam ready
# ---------------------------------------------------------------------------


def test_ready_returns_json_list(plan_dir: Path) -> None:
    """Ready P1 returns a JSON envelope with ready_tasks (may be empty or contain tasks)."""
    result = runner.invoke(app, ["plan", "ready", "--plan-address", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "ready_tasks" in data


def test_ready_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Ready P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["plan", "ready", "--plan-address", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam state
# ---------------------------------------------------------------------------


def test_state_updates_task_status_and_prints_confirmation(plan_dir: Path) -> None:
    """State P1/T3 in-progress updates status and prints old -> new."""
    result = runner.invoke(
        app, ["plan", "state", "--address", "P1/T3", "--new-status", "in-progress", "--plan-dir", str(plan_dir)]
    )
    assert result.exit_code == 0
    assert "T3" in result.stdout
    assert "in-progress" in result.stdout


def test_state_invalid_status_value_is_rejected_by_typer(plan_dir: Path) -> None:
    """State rejects an invalid typed status before execution."""
    result = runner.invoke(
        app, ["plan", "state", "--address", "P1/T1", "--new-status", "bananas", "--plan-dir", str(plan_dir)]
    )
    assert result.exit_code == 2
    assert "Error" in result.stderr


def test_state_missing_task_component_exits_with_code_1(plan_dir: Path) -> None:
    """State P1 (no task) exits 1."""
    result = runner.invoke(
        app, ["plan", "state", "--address", "P1", "--new-status", "complete", "--plan-dir", str(plan_dir)]
    )
    assert result.exit_code == 1


def test_state_nonexistent_task_exits_with_code_1(plan_dir: Path) -> None:
    """State P1/T99 (task not in plan) exits 1."""
    result = runner.invoke(
        app, ["plan", "state", "--address", "P1/T99", "--new-status", "complete", "--plan-dir", str(plan_dir)]
    )
    assert result.exit_code == 1


def test_state_output_shows_old_and_new_status(plan_dir: Path) -> None:
    """State P1/T3 complete shows both old and new status in output."""
    result = runner.invoke(
        app, ["plan", "state", "--address", "P1/T3", "--new-status", "complete", "--plan-dir", str(plan_dir)]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {"id": "T3", "status": "complete"}


# ---------------------------------------------------------------------------
# sam migrate
# ---------------------------------------------------------------------------


def test_migrate_nonexistent_plan_exits_with_code_1(plan_dir: Path) -> None:
    """Migrate P99 exits 1 when no matching plan exists."""
    result = runner.invoke(app, ["plan", "migrate", "--plan-address", "P99", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam validate
# ---------------------------------------------------------------------------


def test_validate_canonical_plan_reports_valid(plan_dir: Path) -> None:
    """Validate P1 on a canonical YAML plan reports no errors or warnings."""
    result = runner.invoke(app, ["plan", "validate", "--address", "P1", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["valid"] is True
    assert data["errors"] == []
    assert data["warnings"] == []


def test_validate_structurally_malformed_plan_reports_invalid_instead_of_crashing(tmp_path: Path) -> None:
    """Validate on a plan whose top level is not a mapping returns valid:false, not a traceback.

    Tests: TypeError from the reader is converted into the JSON validation contract.
    How: Write a bare-list YAML file (not a mapping) and validate it.
    Why: Callers of ``sam plan validate`` parse JSON on stdout -- an uncaught traceback
        breaks that contract for the exact malformed-plan case validate exists to detect.
    """
    d = tmp_path / "plan"
    d.mkdir()
    (d / "P001-bad.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")

    result = runner.invoke(app, ["plan", "validate", "--address", "P1", "--plan-dir", str(d)])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    assert data["errors"]
    assert data["warnings"] == []


def test_removed_cli_forms_are_rejected() -> None:
    """Flat paths, positional data, and removed flags fail at the parser boundary."""
    for args in (
        ["append-task", "P1"],
        ["plan", "read", "P1/T1"],
        ["plan", "append-task", "--plan-address", "P1", "--task-id", "T1", "--task-title", "x", "--task-json", "{}"],
        ["plan", "read", "--address", "P1", "--format", "json"],
        ["plan", "read", "--address", "P1", "--unknown-option"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code != 0
        assert not result.stdout
        assert result.stderr


def test_success_output_is_compact_json(plan_dir: Path) -> None:
    """Successful plan commands emit compact JSON on stdout."""
    result = runner.invoke(app, ["plan", "list", "--plan-dir", str(plan_dir)])
    assert result.exit_code == 0
    json.loads(result.stdout)
    assert '": "' not in result.stdout
    assert '", "' not in result.stdout
