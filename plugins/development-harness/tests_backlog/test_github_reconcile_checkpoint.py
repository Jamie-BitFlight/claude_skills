from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from backlog_core.backends.github_backend import GitHubBackend, _GitHubPlanPersistence
from backlog_core.file_cache import FileCache, _ProviderSnapshotCheckpoint
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    PatchResult,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
)
from backlog_core.reconciliation import synchronized_fingerprint
from sam_schema.core.plan_id_index import PlanIndexEntry


def test_github_reconcile_initial_establishes_durable_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a complete initial provider snapshot and an empty provider-owned cache
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(items=[], sync_started_at="2026-08-12T01:00:00Z", pages_fetched=1)
    )

    # When: the initial reconciliation completes successfully
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))

    # Then: the global snapshot watermark survives reopening the cache
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == _ProviderSnapshotCheckpoint(
        watermark="2026-08-12T01:00:00Z"
    )


def test_github_reconcile_empty_incremental_normalizes_to_initial(tmp_path: Path) -> None:
    # Given: a provider-owned cache without a durable snapshot watermark
    backend = GitHubBackend(cache=FileCache(tmp_path))
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(items=[], sync_started_at="2026-08-12T01:00:00Z", pages_fetched=1)
    )

    # When: startup requests incremental reconciliation without a since value
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: the provider privately fetches a complete initial snapshot
    effective_request = backend._fetch_snapshot.call_args.args[0]
    assert effective_request.scope is ReconcileScope.INITIAL
    assert effective_request.since == ""


def test_github_reconcile_incremental_uses_durable_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a provider-owned cache with a prior global snapshot watermark
    cache = FileCache(tmp_path)
    cache._set_snapshot_checkpoint(_ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z"))
    backend = GitHubBackend(cache=cache)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(items=[], sync_started_at="2026-08-12T02:00:00Z", pages_fetched=1)
    )

    # When: an incremental caller omits its since value
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: the backend supplies the durable watermark to its private snapshot adapter
    assert backend._fetch_snapshot.call_args.args[0].since == "2026-08-12T01:00:00Z"
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == _ProviderSnapshotCheckpoint(
        watermark="2026-08-12T02:00:00Z"
    )


def test_github_reconcile_fetch_failure_preserves_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a prior global watermark and a provider fetch that fails before returning a complete snapshot
    cache = FileCache(tmp_path)
    old_checkpoint = _ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z")
    cache._set_snapshot_checkpoint(old_checkpoint)
    backend = GitHubBackend(cache=cache)
    backend._fetch_snapshot = MagicMock(side_effect=BacklogError("partial snapshot"))

    # When: incremental reconciliation attempts the incomplete fetch
    with pytest.raises(BacklogError, match="partial snapshot"):
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: no partial observation advances the durable watermark
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == old_checkpoint


def test_github_reconcile_patch_failure_preserves_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a local-only body change that requires a provider patch
    cache = FileCache(tmp_path)
    old_checkpoint = _ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z")
    cache._set_snapshot_checkpoint(old_checkpoint)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.updated_at = "rev-1"
    local = baseline.model_copy(deep=True)
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local.description = "local body"
    cache._save_item_snapshot(local, Path("issues/1.yaml"))
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body=backend.render_issue_body(baseline),
                    state="OPEN",
                    labels=["feature"],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    backend._apply_patches = MagicMock(
        return_value=[PatchResult(provider_id="node-1", reference="#1", status="error", message="provider failed")]
    )

    # When: the provider rejects the required patch
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: the failure is reported and the prior global watermark remains durable
    assert result.failures == 1
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == old_checkpoint


def test_github_reconcile_conflict_preserves_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a local-only body change whose provider patch conflicts
    cache = FileCache(tmp_path)
    old_checkpoint = _ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z")
    cache._set_snapshot_checkpoint(old_checkpoint)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.updated_at = "rev-1"
    local = baseline.model_copy(deep=True)
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local.description = "local body"
    cache._save_item_snapshot(local, Path("issues/1.yaml"))
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body=backend.render_issue_body(baseline),
                    state="OPEN",
                    labels=["feature"],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    backend._apply_patches = MagicMock(
        return_value=[PatchResult(provider_id="node-1", reference="#1", status="conflict", message="stale")]
    )

    # When: the provider reports the patch conflict
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: the conflict is reported and the prior global watermark remains durable
    assert result.conflicts == 1
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == old_checkpoint


def test_github_reconcile_dry_run_preserves_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a prior global watermark and a newer complete provider snapshot
    cache = FileCache(tmp_path)
    old_checkpoint = _ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z")
    cache._set_snapshot_checkpoint(old_checkpoint)
    backend = GitHubBackend(cache=cache)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(items=[], sync_started_at="2026-08-12T02:00:00Z", pages_fetched=1)
    )

    # When: incremental reconciliation is explicitly a dry run
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, dry_run=True))

    # Then: observation alone does not advance durable state
    assert FileCache(tmp_path)._get_snapshot_checkpoint() == old_checkpoint


def _offline_work_item_backend(tmp_path: Path) -> GitHubBackend:
    # Given: a local edit queued before GitHub becomes unavailable
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local = baseline.model_copy(deep=True)
    local.description = "local body"
    backend.put_work_item(local)
    backend._fetch_snapshot = MagicMock(side_effect=BacklogError("offline"))
    return backend


def test_github_work_item_intent_survives_offline_reconcile(tmp_path: Path) -> None:
    backend = _offline_work_item_backend(tmp_path)

    # When: offline reconciliation cannot fetch its provider snapshot
    with pytest.raises(BacklogError, match="offline"):
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: the provider-owned cache retains the durable mutation
    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert len(pending) == 1
    assert pending[0].item.description == "local body"


def test_github_work_item_intent_replays_once_after_reconnect(tmp_path: Path) -> None:
    # Given: a durable work-item mutation retained after an offline attempt
    backend = _offline_work_item_backend(tmp_path)
    with pytest.raises(BacklogError, match="offline"):
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body=backend.render_issue_body(baseline),
                    state="OPEN",
                    labels=["feature"],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    backend._apply_patches = MagicMock(
        return_value=[PatchResult(provider_id="node-1", reference="#1", status="applied", revision="rev-2")]
    )

    # When: the durable intent is retried against a complete provider snapshot
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: the provider acknowledges one patch and the durable intent is removed
    assert result.provider_patches == 1
    assert FileCache(tmp_path)._pending_work_item_mutations() == []
    assert backend._apply_patches.call_count == 1


def test_github_plan_discovery_lists_all_owners_when_owner_is_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: linked and unlinked plans in the provider-native index
    entries = [
        PlanIndexEntry(plan_id="Powned", issue=1, slug="owned", created_at=""),
        PlanIndexEntry(plan_id="Punowned", issue=None, slug="unowned", created_at=""),
    ]
    persistence = object.__new__(_GitHubPlanPersistence)
    monkeypatch.setattr(_GitHubPlanPersistence, "_entries", lambda _self: entries)
    monkeypatch.setattr(
        _GitHubPlanPersistence,
        "_record",
        lambda _self, entry: ContentRecord(
            reference=ContentRef(kind=ContentKind.PLAN, name=entry.plan_id),
            owner_reference=f"#{entry.issue}" if entry.issue is not None else "",
            content=entry.plan_id,
        ),
    )

    # When: discovery omits the owner filter and requests the second bounded record
    listed = persistence.list(ContentQuery(kind=ContentKind.PLAN, owner_reference=None, offset=1, limit=1))

    # Then: all owners participate before pagination is applied
    assert [record.reference.name for record in listed] == ["Punowned"]
