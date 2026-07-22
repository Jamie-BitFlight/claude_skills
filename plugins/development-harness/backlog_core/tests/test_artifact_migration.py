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
