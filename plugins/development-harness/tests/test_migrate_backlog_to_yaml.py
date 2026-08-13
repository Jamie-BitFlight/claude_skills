"""CLI-level tests for migrate_backlog_to_yaml.py.

migrate_backlog_to_yaml is invoked exclusively by AI agents via subprocess,
so its ``main`` command emits a single compact JSON object on stdout for
every action (--dry-run, --confirm, --cleanup, or no flag). These tests
parse that JSON and assert on structured fields.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: add the harness package to sys.path so the script under test
# can be imported directly in the test environment.
# ---------------------------------------------------------------------------
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

from scripts.migrate_backlog_to_yaml import MigrationReport, app, run_cleanup, run_dry_run, run_migration
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Callable

runner = CliRunner()

_VALID_ITEM_MD = """\
---
name: Test migration item
description: A test item for migration.
metadata:
  source: test-session
  added: '2026-01-15'
  priority: P1
  type: Feature
  status: open
  issue: '#42'
---

## Context

Some context content.
"""


def _write_item(backlog_dir: Path, name: str = "item1.md") -> Path:
    """Write a valid backlog .md fixture into *backlog_dir*.

    Returns:
        Path to the written file.
    """
    backlog_dir.mkdir(parents=True, exist_ok=True)
    path = backlog_dir / name
    path.write_text(_VALID_ITEM_MD, encoding="utf-8")
    return path


def test_migration_script_uses_no_yaml_codec_directly() -> None:
    module_path = sys.modules["scripts.migrate_backlog_to_yaml"].__file__
    assert module_path is not None
    source = Path(module_path).read_text(encoding="utf-8")
    imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    called_names = {
        node.func.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "backlog_core.yaml_io" not in imports
    assert "ruamel.yaml" not in imports
    assert "YAML" not in called_names


# ---------------------------------------------------------------------------
# main command — no action flag
# ---------------------------------------------------------------------------


def test_main_no_flag_exits_0_with_no_action_status(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--backlog-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "no_action"


def test_main_missing_backlog_dir_errors(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = runner.invoke(app, ["--backlog-dir", str(missing), "--dry-run"])

    assert result.exit_code == 1
    assert "does not exist" in result.output.lower() or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# main command — --dry-run
# ---------------------------------------------------------------------------


def test_main_dry_run_reports_verified_item_and_makes_no_changes(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    item_path = _write_item(backlog_dir)

    result = runner.invoke(app, ["--backlog-dir", str(backlog_dir), "--dry-run"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["total_found"] == 1
    assert payload["migrated"] == 1
    assert payload["error_count"] == 0
    assert payload["results"] == [
        {"file": "item1.md", "status": "verified", "sections": 1, "section_keys": ["context"]}
    ]
    # No filesystem changes on a dry run.
    assert item_path.exists()
    assert not item_path.with_suffix(".yaml").exists()


def test_main_dry_run_skips_file_without_frontmatter(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True)
    (backlog_dir / "README.md").write_text("# Not a backlog item\n", encoding="utf-8")

    result = runner.invoke(app, ["--backlog-dir", str(backlog_dir), "--dry-run"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["skipped_no_frontmatter"] == 1
    assert payload["results"] == [{"file": "README.md", "status": "skipped_no_frontmatter"}]


# ---------------------------------------------------------------------------
# main command — --confirm
# ---------------------------------------------------------------------------


def test_main_confirm_migrates_and_renames_original(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    item_path = _write_item(backlog_dir)

    result = runner.invoke(app, ["--backlog-dir", str(backlog_dir), "--confirm"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["dry_run"] is False
    assert payload["migrated"] == 1
    assert payload["results"] == [{"file": "item1.md", "status": "migrated"}]

    assert not item_path.exists()
    assert item_path.with_suffix(".md.bak").exists()
    assert item_path.with_suffix(".yaml").exists()


def test_main_confirm_skips_already_converted(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    item_path = _write_item(backlog_dir)
    item_path.with_suffix(".yaml").write_text("name: already there\n", encoding="utf-8")

    result = runner.invoke(app, ["--backlog-dir", str(backlog_dir), "--confirm"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["skipped_already_converted"] == 1
    assert payload["results"] == [{"file": "item1.md", "status": "skipped_yaml_exists"}]


# ---------------------------------------------------------------------------
# main command — --cleanup
# ---------------------------------------------------------------------------


def test_main_cleanup_removes_bak_files(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True)
    (backlog_dir / "item1.md.bak").write_text("stale", encoding="utf-8")

    result = runner.invoke(app, ["--backlog-dir", str(backlog_dir), "--cleanup"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "cleanup"
    assert payload["removed"] == ["item1.md.bak"]
    assert payload["removed_count"] == 1
    assert not (backlog_dir / "item1.md.bak").exists()


# ---------------------------------------------------------------------------
# run_cleanup — direct unit coverage of the return-value contract
# ---------------------------------------------------------------------------


def test_run_cleanup_returns_removed_names(tmp_path: Path) -> None:
    (tmp_path / "a.md.bak").write_text("a", encoding="utf-8")
    (tmp_path / "b.md.bak").write_text("b", encoding="utf-8")

    removed = run_cleanup(tmp_path)

    assert removed == ["a.md.bak", "b.md.bak"]
    assert not (tmp_path / "a.md.bak").exists()
    assert not (tmp_path / "b.md.bak").exists()


# ---------------------------------------------------------------------------
# run_dry_run / run_migration — direct unit coverage of MigrationReport.results
# ---------------------------------------------------------------------------


def test_run_dry_run_on_missing_dir_returns_empty_report(tmp_path: Path) -> None:
    report = run_dry_run(tmp_path / "does-not-exist")

    assert report.total_found == 0
    assert report.results == []


def test_run_migration_on_missing_dir_returns_empty_report(tmp_path: Path) -> None:
    report = run_migration(tmp_path / "does-not-exist")

    assert report.total_found == 0
    assert report.results == []


@pytest.mark.parametrize("runner_fn", [run_dry_run, run_migration])
def test_run_functions_record_skipped_bak_exists_status(
    tmp_path: Path, runner_fn: Callable[[Path], MigrationReport]
) -> None:
    # A .md.bak counterpart already exists — both run_dry_run and run_migration
    # should record a skip, not attempt to process the file.
    item_path = _write_item(tmp_path)
    item_path.with_suffix(".md.bak").write_text("stale backup", encoding="utf-8")

    report = runner_fn(tmp_path)

    assert report.results == [{"file": "item1.md", "status": "skipped_bak_exists"}]
