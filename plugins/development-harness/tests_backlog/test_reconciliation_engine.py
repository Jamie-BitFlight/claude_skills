from __future__ import annotations

from pathlib import Path

import backlog_core.models as _models
import pytest
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BacklogItem,
    BacklogItemMetadata,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
)
from backlog_core.reconciliation import reconcile_backlog, synchronized_fingerprint
from backlog_core.yaml_io import load_item, save_item


@pytest.fixture
def backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "backlog"
    directory.mkdir()
    monkeypatch.setattr(
        _models, "_config", _models.BacklogConfig(repo_root=tmp_path, backlog_dir=directory, default_repo="")
    )
    return directory


class InMemorySyncProvider:
    def __init__(self, item: ProviderItem) -> None:
        self.item = item
        self.patches: list[ProviderPatch] = []

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        return ProviderSnapshot(items=[self.item], sync_started_at="2026-08-12T00:00:00Z", pages_fetched=1)

    def apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        self.patches.extend(patches)
        self.item = self.item.model_copy(update={"body": patches[0].body, "revision": "rev-2"})
        return [
            PatchResult(
                provider_id=patches[0].provider_id, reference=patches[0].reference, status="applied", revision="rev-2"
            )
        ]


def _linked_item(description: str) -> BacklogItem:
    return BacklogItem(
        title="Example",
        description=description,
        metadata=BacklogItemMetadata(
            source="test", added="2026-08-12", priority="P1", item_type="Feature", status="open", issue="#1"
        ),
    )


def _provider_item(body: str, state: str = "OPEN", exists: bool = True) -> ProviderItem:
    return ProviderItem(
        provider_id="node-1",
        reference="#1",
        title="Example",
        body=body,
        state=state,
        labels=["feature"],
        revision="rev-1",
        exists=exists,
    )


def test_reconcile_backlog_skips_equal_rendered_body(backlog_dir) -> None:
    # Given: a linked local item with a durable fingerprint matching the provider body
    local = _linked_item("unchanged")
    local.metadata.sync_fingerprint = synchronized_fingerprint(local)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(local)))

    # When: reconciliation observes the matching snapshot
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: it establishes no provider mutation
    assert result.no_ops == 1
    assert provider.patches == []


def test_reconcile_backlog_patches_local_content_change(backlog_dir) -> None:
    # Given: a linked item whose local content changed after its checkpoint
    baseline = _linked_item("before")
    local = _linked_item("after")
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(baseline)))

    # When: reconciliation runs against the in-memory provider
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: exactly one optimistic body patch and checkpoint are durable
    saved = load_item(path)
    assert result.provider_patches == 1
    assert provider.patches[0].expected_revision == "rev-1"
    assert saved.metadata.sync_fingerprint == synchronized_fingerprint(saved)


def test_reconcile_backlog_pulls_remote_content_change(backlog_dir) -> None:
    # Given: an unchanged local item and a provider body changed from its checkpoint
    baseline = _linked_item("before")
    local = _linked_item("before")
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(_linked_item("after"))))

    # When: reconciliation observes the remote-only change
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: the local cache is updated without a provider mutation
    assert load_item(path).description == "after"
    assert result.provider_patches == 0


def test_reconcile_backlog_bootstrap_merges_without_losing_local_content(backlog_dir) -> None:
    # Given: a linked local item with no fingerprint and an equivalent provider body
    local = _linked_item("local")
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(_linked_item("local"))))

    # When: reconciliation establishes the first checkpoint
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: local content remains and no needless patch is made
    assert load_item(path).description == "local"
    assert result.no_ops == 1


def test_reconcile_backlog_merges_concurrent_content_changes(backlog_dir) -> None:
    # Given: local and provider bodies both changed after the same checkpoint
    baseline = _linked_item("before")
    local = _linked_item("local")
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(_linked_item("remote"))))

    # When: reconciliation applies the existing entry-aware merge seam
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: the merged body retains the local description and is patched once
    assert result.provider_patches == 1
    assert "local" in provider.patches[0].body


def test_reconcile_backlog_force_replaces_local_content(backlog_dir) -> None:
    # Given: a local edit and a newer provider body
    baseline = _linked_item("before")
    local = _linked_item("local")
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(_linked_item("remote"))))

    # When: a force pull is requested
    reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"], force=True))

    # Then: provider content replaces synchronized local content
    assert load_item(path).description == "remote"


def test_reconcile_backlog_preserves_file_when_provider_tombstones_link(backlog_dir) -> None:
    # Given: a linked local item and a conclusive provider tombstone
    local = _linked_item("local")
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item("", exists=False))

    # When: reconciliation receives the tombstone
    result = reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#1"]))

    # Then: the local record remains but becomes local-only
    assert path.exists()
    assert load_item(path).metadata.issue == ""
    assert result.deleted_provider_items == 1


def test_reconcile_backlog_keeps_remote_closed_state_while_patching_body(backlog_dir) -> None:
    # Given: a local content edit against a remotely closed item
    baseline = _linked_item("before")
    local = _linked_item("after")
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    path = backlog_dir / "p1-example.yaml"
    save_item(local, path)
    provider = InMemorySyncProvider(_provider_item(render_issue_body(baseline), state="CLOSED"))

    # When: reconciliation applies the local body change
    reconcile_backlog(provider, ReconcileRequest(scope=ReconcileScope.LINKED, references=["#1"]))

    # Then: the body patch does not reopen the locally persisted provider state
    assert load_item(path).metadata.status == "closed"
    assert provider.patches[0].body.endswith("after\n")
