"""Tests for the best-effort fallback migration path in ``_migrate_one``.

Covers Category A (YAML frontmatter with non-standard task lists) and
Category B (pure markdown, no frontmatter) files that ``load_plan`` cannot
parse into the canonical schema.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from sam_schema.cli import _migrate_one, _migrate_one_fallback, app
from typer.testing import CliRunner

runner = CliRunner()

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
_NONSTANDARD_FM: Path = FIXTURES_DIR / "nonstandard_frontmatter_tasks.md"
_PURE_MD: Path = FIXTURES_DIR / "pure_markdown_checklist.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a plain dict.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dict.
    """
    y = YAML()
    result = y.load(path.read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def _make_nonstandard_plan_dir(tmp_path: Path) -> Path:
    """Create a plan directory containing one Category A file.

    Args:
        tmp_path: pytest tmp_path fixture value.

    Returns:
        Path to the created plan directory.
    """
    d = tmp_path / "plan"
    d.mkdir()
    content = _NONSTANDARD_FM.read_text(encoding="utf-8")
    (d / "tasks-6-enhance-skill-research.md").write_text(content, encoding="utf-8")
    return d


def _make_pure_markdown_plan_dir(tmp_path: Path) -> Path:
    """Create a plan directory containing one Category B file.

    Args:
        tmp_path: pytest tmp_path fixture value.

    Returns:
        Path to the created plan directory.
    """
    d = tmp_path / "plan"
    d.mkdir()
    content = _PURE_MD.read_text(encoding="utf-8")
    (d / "tasks-2-complete-ty-skill.md").write_text(content, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# _migrate_one_fallback — unit-level tests
# ---------------------------------------------------------------------------


def test_migrate_one_fallback_writes_yaml_for_nonstandard_frontmatter(tmp_path: Path) -> None:
    """_migrate_one_fallback writes a valid YAML file for Category A (non-standard frontmatter tasks).

    Tests: Fallback writes output for YAML-frontmatter files with non-canonical task schemas.
    How: Copy the nonstandard_frontmatter_tasks fixture to tmp_path as tasks-6-enhance-skill-research.md,
         call _migrate_one_fallback, assert P006-enhance-skill-research.yaml is created.
    Why: Category A files have frontmatter but task lists that load_plan rejects.
         The fallback must produce a .yaml file so migration reports zero errors.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-6-enhance-skill-research.md"
    src.write_text(_NONSTANDARD_FM.read_text(encoding="utf-8"), encoding="utf-8")

    output, source_format = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    assert output.name == "P006-enhance-skill-research.yaml"
    assert output.exists()
    assert source_format == "fallback-preservation"


def test_migrate_one_fallback_preserves_raw_content_in_context_body(tmp_path: Path) -> None:
    """_migrate_one_fallback stores the complete original content in context.body.

    Tests: No data loss — full original markdown is preserved.
    How: Write a file with known unique content, run fallback, load the output YAML
         and verify context.body contains that unique string.
    Why: The fallback must guarantee zero data loss even when the task schema is unknown.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    unique_marker = "UNIQUE-CANARY-STRING-XYZ-987"
    src = plan_dir / "tasks-3-data-preservation.md"
    src.write_text(f"# Data Preservation Test\n\n**Issue**: #42\n\n{unique_marker}\n", encoding="utf-8")

    output, _ = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    data = _load_yaml(output)
    assert "context" in data
    assert unique_marker in data["context"]["body"]


def test_migrate_one_fallback_extracts_goal_from_heading(tmp_path: Path) -> None:
    """_migrate_one_fallback sets goal from the first # heading.

    Tests: Goal extraction from markdown heading.
    How: Write a file with a known # heading, run fallback, check the goal field in output YAML.
    Why: goal is required for the output to be useful to consumers.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-10-goal-extraction.md"
    src.write_text("# My Specific Goal Title\n\nSome body content.\n", encoding="utf-8")

    output, _ = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    data = _load_yaml(output)
    assert data["goal"] == "My Specific Goal Title"


def test_migrate_one_fallback_extracts_issue_from_bold_field(tmp_path: Path) -> None:
    """_migrate_one_fallback extracts issue number from **Issue**: #N markdown pattern.

    Tests: Issue extraction from bold markdown field.
    How: Write a file with **Issue**: #99, run fallback, check the issue field in output YAML.
    Why: Issue number links the migrated plan back to the GitHub issue for traceability.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-11-issue-extraction.md"
    src.write_text("# Title\n\n**Issue**: #99\n\nContent.\n", encoding="utf-8")

    output, _ = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    data = _load_yaml(output)
    assert data.get("issue") == 99


def test_migrate_one_fallback_sets_status_complete_and_empty_tasks(tmp_path: Path) -> None:
    """_migrate_one_fallback sets status=complete and tasks=[].

    Tests: Output schema correctness for non-parseable plans.
    How: Run fallback on any non-standard file, check status and tasks fields.
    Why: Fallback-migrated plans are old completed plans; tasks=[] signals the content
         lives in context.body rather than the canonical task list.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-12-schema-check.md"
    src.write_text("# Schema Check\n\nSome content.\n", encoding="utf-8")

    output, _ = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    data = _load_yaml(output)
    assert data["status"] == "complete"
    assert data["tasks"] == []


def test_migrate_one_fallback_dry_run_returns_none_and_prints_preview(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """_migrate_one_fallback dry_run=True returns (None, 'fallback-preservation') and prints preview.

    Tests: Dry-run mode of the fallback path.
    How: Run _migrate_one_fallback with dry_run=True, assert return value and no file written.
    Why: dry_run must be non-destructive so callers can preview before committing.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-13-dry-run.md"
    src.write_text("# Dry Run Test\n\nContent.\n", encoding="utf-8")

    output, source_format = _migrate_one_fallback(src, dry_run=True)

    assert output is None
    assert source_format == "fallback-preservation"
    expected_yaml = plan_dir / "P013-dry-run.yaml"
    assert not expected_yaml.exists()


def test_migrate_one_fallback_collision_raises_file_exists_error(tmp_path: Path) -> None:
    """_migrate_one_fallback raises FileExistsError when the canonical target already exists.

    Tests: Collision guard in the fallback path (non-dry-run).
    How: Pre-create P014-collision.yaml, call _migrate_one_fallback on tasks-14-collision.md.
    Why: The fallback collision guard must behave identically to the canonical path to
         prevent silent overwrites of already-migrated files.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-14-collision.md"
    src.write_text("# Collision\n\nContent.\n", encoding="utf-8")
    existing = plan_dir / "P014-collision.yaml"
    existing.write_text("sentinel: true\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _migrate_one_fallback(src, dry_run=False)

    assert existing.read_text(encoding="utf-8") == "sentinel: true\n"


def test_migrate_one_fallback_records_source_file_in_context(tmp_path: Path) -> None:
    """_migrate_one_fallback stores the original filename in context.source_file.

    Tests: Traceability metadata in fallback output.
    How: Run fallback on a file with a known name, check context.source_file in output YAML.
    Why: Consumers need to know which original file was preserved in context.body.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    src = plan_dir / "tasks-15-traceability.md"
    src.write_text("# Traceability\n\nContent.\n", encoding="utf-8")

    output, _ = _migrate_one_fallback(src, dry_run=False)

    assert output is not None
    data = _load_yaml(output)
    assert data["context"]["source_file"] == "tasks-15-traceability.md"


# ---------------------------------------------------------------------------
# _migrate_one — integration with fallback
# ---------------------------------------------------------------------------


def test_migrate_one_falls_back_when_load_plan_fails(tmp_path: Path) -> None:
    """_migrate_one calls the fallback when load_plan raises any exception.

    Tests: Fallback integration in _migrate_one.
    How: Provide a file that load_plan cannot parse (non-standard task_exports schema),
         call _migrate_one, verify a .yaml output is written with source_format='fallback-preservation'.
    Why: _migrate_one must never raise for parseable-content files — it must always produce output.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    content = _NONSTANDARD_FM.read_text(encoding="utf-8")
    src = plan_dir / "tasks-6-nonstandard.md"
    src.write_text(content, encoding="utf-8")

    output, source_format = _migrate_one(src, dry_run=False)

    assert output is not None
    assert output.name == "P006-nonstandard.yaml"
    assert output.exists()
    assert source_format == "fallback-preservation"
    data = _load_yaml(output)
    assert "context" in data
    assert "body" in data["context"]


def test_migrate_one_falls_back_for_pure_markdown_no_frontmatter(tmp_path: Path) -> None:
    """_migrate_one uses the fallback for Category B files (pure markdown, no frontmatter).

    Tests: Fallback activation for pure markdown files with no parseable YAML structure.
    How: Provide the pure_markdown_checklist fixture, call _migrate_one, verify output.
    Why: Pure markdown files with checklist tasks are a common legacy format that load_plan rejects.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    content = _PURE_MD.read_text(encoding="utf-8")
    src = plan_dir / "tasks-2-complete-ty-skill.md"
    src.write_text(content, encoding="utf-8")

    output, source_format = _migrate_one(src, dry_run=False)

    assert output is not None
    assert output.exists()
    assert source_format == "fallback-preservation"
    data = _load_yaml(output)
    assert data["tasks"] == []
    assert "checklist" in data["context"]["body"] or "- [" in data["context"]["body"]


# ---------------------------------------------------------------------------
# sam migrate --all with non-parseable files
# ---------------------------------------------------------------------------


def test_migrate_all_migrates_nonstandard_frontmatter_files(tmp_path: Path) -> None:
    """--all successfully migrates Category A files (non-standard frontmatter task lists).

    Tests: Zero errors when migrating files with task_exports or other non-canonical schemas.
    How: Place nonstandard_frontmatter fixture, run sam migrate --all --skip-sync,
         assert output yaml exists and exit code is 0.
    Why: The 10 error files in the original run were Category A/B — after this fix, zero errors.
    """
    plan_dir = _make_nonstandard_plan_dir(tmp_path)

    result = runner.invoke(app, ["migrate", "--all", "--skip-sync", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.output
    yaml_files = list(plan_dir.glob("*.yaml"))
    assert len(yaml_files) == 1
    assert yaml_files[0].name == "P006-enhance-skill-research.yaml"


def test_migrate_all_migrates_pure_markdown_files(tmp_path: Path) -> None:
    """--all successfully migrates Category B files (pure markdown, no frontmatter).

    Tests: Zero errors when migrating pure markdown files with checklist tasks.
    How: Place pure_markdown_checklist fixture, run sam migrate --all --skip-sync,
         assert output yaml exists.
    Why: Pure markdown files are the second common category that load_plan previously rejected.
    """
    plan_dir = _make_pure_markdown_plan_dir(tmp_path)

    result = runner.invoke(app, ["migrate", "--all", "--skip-sync", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.output
    yaml_files = list(plan_dir.glob("*.yaml"))
    assert len(yaml_files) == 1


def test_migrate_all_preserves_content_for_fallback_migrated_files(tmp_path: Path) -> None:
    """--all preserves all original content in context.body for fallback-migrated files.

    Tests: No data loss in bulk migration of non-parseable files.
    How: Place a file with a unique marker, run --all, load the output YAML, check context.body.
    Why: Consumers must be able to access original content after migration.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    unique_marker = "BULK-MIGRATE-CANARY-ABC-456"
    src = plan_dir / "tasks-7-data-check.md"
    src.write_text(f"# Data Check\n\n**Issue**: #7\n\n{unique_marker}\n", encoding="utf-8")

    result = runner.invoke(app, ["migrate", "--all", "--skip-sync", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.output
    output = plan_dir / "P007-data-check.yaml"
    assert output.exists()
    data = _load_yaml(output)
    assert unique_marker in data["context"]["body"]


def test_migrate_all_dry_run_shows_fallback_files_as_would_migrate(tmp_path: Path) -> None:
    """--all --dry-run reports fallback-path files as 'Would migrate' without writing.

    Tests: dry_run integration for fallback files.
    How: Place nonstandard file, run --all --dry-run, assert 'Would migrate' in output, no .yaml written.
    Why: Dry-run must include fallback files in the preview count.
    """
    plan_dir = _make_nonstandard_plan_dir(tmp_path)
    original_files = set(plan_dir.iterdir())

    result = runner.invoke(app, ["migrate", "--all", "--dry-run", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.output
    assert "Would migrate" in result.output
    assert set(plan_dir.iterdir()) == original_files


def test_migrate_all_mixed_standard_and_fallback_files(tmp_path: Path) -> None:
    """--all migrates a mix of canonical and fallback files in a single run.

    Tests: Coexistence of canonical-parseable and fallback files in one migration.
    How: Place one legacy_markdown.md (canonical) and one nonstandard_frontmatter_tasks.md
         (fallback) in the same plan dir. Run --all. Assert both produce .yaml files.
    Why: Real plan directories contain mixed file types; the loop must handle both.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    legacy_content = (FIXTURES_DIR / "legacy_markdown.md").read_text(encoding="utf-8")
    (plan_dir / "tasks-1-canonical.md").write_text(legacy_content, encoding="utf-8")

    nonstandard_content = _NONSTANDARD_FM.read_text(encoding="utf-8")
    (plan_dir / "tasks-6-nonstandard.md").write_text(nonstandard_content, encoding="utf-8")

    result = runner.invoke(app, ["migrate", "--all", "--skip-sync", "--plan-dir", str(plan_dir)])

    assert result.exit_code == 0, result.output
    yaml_files = {p.name for p in plan_dir.glob("*.yaml")}
    assert "P001-canonical.yaml" in yaml_files
    assert "P006-nonstandard.yaml" in yaml_files
    assert "Migration complete" in result.output
