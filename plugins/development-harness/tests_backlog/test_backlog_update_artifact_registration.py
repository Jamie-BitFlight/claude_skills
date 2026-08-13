from __future__ import annotations

from unittest.mock import MagicMock, patch

from backlog_core.backend_types import BacklogConfig, WorkItemBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogItem, BacklogItemMetadata, ContentKind, ContentQuery
from backlog_core.operations import update_item


def _make_item(issue: str = "#42") -> BacklogItem:
    return BacklogItem(
        title="Test Feature",
        reference="test-feature",
        description="Test item",
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", issue=issue, topic="test-feature"
        ),
    )


def test_update_item_plan_persists_association_without_manifest_write() -> None:
    item = _make_item()
    provider = InMemoryBackend()
    provider.put_work_item(item)
    provider.put_content = MagicMock(side_effect=AssertionError("plan update wrote an artifact manifest"))

    with (
        patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)),
        patch("backlog_core.operations.try_get_github", return_value=None),
    ):
        result = update_item(selector=item.title, plan="plan/tasks-1-foo.yaml")

    assert result["plan"] == "plan/tasks-1-foo.yaml"
    assert provider.get_work_item(item.reference).metadata.plan == "plan/tasks-1-foo.yaml"
    provider.put_content.assert_not_called()
    assert provider.list_content(ContentQuery(kind=ContentKind.ARTIFACT_MANIFEST)) == []


def test_update_item_plan_succeeds_without_artifact_capability() -> None:
    item = _make_item()
    provider = MagicMock(spec=WorkItemBackend)
    provider.issue_id_type = "integer"
    provider.list_work_items.return_value = [item]
    provider.get_work_item.return_value = item
    provider.try_get_github.return_value = None

    with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
        result = update_item(selector=item.title, plan="plan/tasks-2-bar.yaml")

    assert result["plan"] == "plan/tasks-2-bar.yaml"
    assert item.metadata.plan == "plan/tasks-2-bar.yaml"
    provider.put_work_item.assert_called_once_with(item)
