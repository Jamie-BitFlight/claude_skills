"""Regression tests for artifact migration's lower-level backlog lookup."""

from __future__ import annotations

from pathlib import Path

from backlog_core import artifact_migration
from backlog_core.models import BacklogItem


def test_migration_backlog_items_maps_issue_to_number(monkeypatch) -> None:
    """Migration lookup retains the issue field under the expected number key."""
    item = BacklogItem(title="Cache sync", issue="42", plan="plan/P42-cache-sync.yaml")
    monkeypatch.setattr(artifact_migration, "parse_backlog", lambda: [item])

    assert artifact_migration._migration_backlog_items() == [
        {"title": "Cache sync", "plan": "plan/P42-cache-sync.yaml", "number": "42"}
    ]


def test_migration_slug_fallback_uses_local_backlog_items(monkeypatch, tmp_path: Path) -> None:
    """Migration resolves an issue from the filename when frontmatter lacks one."""
    item = BacklogItem(title="Cache sync", issue="42", plan="plan/P42-cache-sync.yaml")
    monkeypatch.setattr(artifact_migration, "parse_backlog", lambda: [item])
    artifact = tmp_path / "feature-context-cache-sync.md"
    artifact.write_text("# Cache sync\n", encoding="utf-8")

    assert artifact_migration._migrate_resolve_issue(artifact, artifact_migration._migration_backlog_items()) == 42


def test_migrate_dry_run_uses_plan_relative_paths_outside_repo(monkeypatch, tmp_path: Path) -> None:
    """Dry-run discovers state-plan artifacts stored outside the repository."""
    repo_root = tmp_path / "repo"
    state_plan_dir = tmp_path / "state" / "plan"
    codebase_dir = state_plan_dir / "codebase"
    repo_root.mkdir()
    codebase_dir.mkdir(parents=True)
    (state_plan_dir / "P42-state-plan.yaml").write_text("issue: 42\n", encoding="utf-8")
    (codebase_dir / "architecture.md").write_text("---\nissue: 42\n---\n", encoding="utf-8")
    monkeypatch.setattr(artifact_migration.dh_paths, "plan_dir", lambda _repo_root: state_plan_dir)
    monkeypatch.setattr(artifact_migration._models, "get_repo_root", lambda: repo_root)

    result = artifact_migration.migrate_dry_run(42)

    assert result["would_register"] == 2
    assert sorted([detail["path"] for detail in result["details"]]) == sorted([
        "plan/codebase/architecture.md",
        "plan/P42-state-plan.yaml",
    ])
