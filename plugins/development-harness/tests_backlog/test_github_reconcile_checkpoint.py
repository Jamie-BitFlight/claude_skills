from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from backlog_core.backends import github_work_items
from backlog_core.backends._github_work_item_versions import root_revision
from backlog_core.backends.github_backend import GitHubBackend, _GitHubPlanPersistence
from backlog_core.file_cache import FileCache, _ProviderSnapshotCheckpoint
from backlog_core.file_cache_state import _CacheState, _RejectedWorkItemMutation
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    ContentKind,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
)
from backlog_core.reconciliation import ReconcilePlan, synchronized_fingerprint
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


def test_github_reconcile_result_counts_dead_lettered_work_item_rejections(tmp_path: Path) -> None:
    # Given: a cache with one dead-lettered work-item mutation (e.g. from a
    # key/content mismatch caught on load -- see _verify_queue_keys) and no
    # content-side rejections
    cache = FileCache(tmp_path)
    forged_item = BacklogItem(title="Forged entry")
    cache._state._save(
        _CacheState(
            rejected_work_items=[
                _RejectedWorkItemMutation(
                    idempotency_key="stale-key", key="#1", item=forged_item, reason="test fixture"
                )
            ]
        )
    )
    backend = GitHubBackend(cache=cache)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(items=[], sync_started_at="2026-08-12T01:00:00Z", pages_fetched=1)
    )

    # When: reconcile runs
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))

    # Then: the work-item rejection is counted, not just the content-side one
    # (reconcile() previously summed only cache.rejected_mutations(), missing
    # _rejected_work_item_mutations() entirely)
    assert result.rejected_mutations == 1


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
    repository = MagicMock(full_name="owner/repo")
    observed_issue: dict[str, object] = {
        "id": "node-1",
        "number": 1,
        "title": "Issue 1",
        "body": backend.render_issue_body(baseline),
        "state": "OPEN",
        "labels": [{"id": "label-1", "name": "feature"}],
        "updatedAt": "rev-1",
        "createdAt": "2026-08-12T00:00:00Z",
        "milestone": None,
        "assignees": [],
    }
    backend.get_github = MagicMock(return_value=repository)
    backend._contents = MagicMock()
    backend._contents.get.side_effect = ContentNotFoundError("head missing")
    backend._graphql_request = MagicMock(return_value={"repository": {"i0": observed_issue}})
    backend._update_issues_graphql_batch = MagicMock()

    # When: the provider reports the patch conflict
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL))

    # Then: the body remains unwritten, the conflict is reported, and the prior global watermark remains durable
    assert result.conflicts == 1
    assert result.patch_results[0].revision == root_revision("#1", "node-1", str(observed_issue["body"]))
    backend._update_issues_graphql_batch.assert_not_called()
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


def test_reconcile_does_not_acknowledge_pending_mutation_when_unlink_snapshot_save_fails(tmp_path: Path) -> None:
    """A GitHub-deleted issue produces an unlink CacheAction whose ``record.item``

    has ``metadata.issue`` already cleared to ``""`` (see ``_plan_item``'s
    unlinked-copy construction). If the acknowledgement guard in
    ``github_work_items.reconcile`` keys ``failed_cache_references`` off
    ``action.record.item.metadata.issue`` it collects ``""`` instead of the
    real reference, so a failed unlink write never blocks acknowledgement and
    the still-pending local mutation is wrongly dropped. Fails (RED) against
    the unfixed guard.
    """
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    local = BacklogItem(title="Issue 1", description="local body")
    local.metadata.issue = "#1"
    backend.put_work_item(local)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body="",
                    state="OPEN",
                    labels=[],
                    revision="rev-1",
                    exists=False,
                )
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    cache._save_work_item_snapshot = MagicMock(side_effect=OSError("disk full"))

    # When: reconciliation processes the unlink action and its cache write fails
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: the pending mutation must remain queued -- it was never durably unlinked
    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert [mutation.item.metadata.issue for mutation in pending] == ["#1"], (
        "Mutation was acknowledged despite the unlink cache write failing"
    )


def test_github_reconcile_retains_mutation_queued_after_plan_construction(tmp_path: Path) -> None:
    # Given: a queued body change whose provider patch will succeed
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    planned = baseline.model_copy(update={"description": "planned body"})
    backend.put_work_item(planned)
    planned_mutation = cache._pending_work_item_mutations()[0]
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body=backend.render_issue_body(baseline),
                    state="OPEN",
                    labels=[],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    newer = planned.model_copy(update={"description": "newer body"})

    def queue_newer_mutation(_patches: list[ProviderPatch]) -> list[PatchResult]:
        backend.put_work_item(newer)
        return [PatchResult(provider_id="node-1", reference="#1", status="applied", revision="rev-2")]

    backend._apply_patches = MagicMock(side_effect=queue_newer_mutation)

    # When: a newer same-reference, same-title mutation is queued after planning
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: only the planned mutation is acknowledged; the newer body change remains durable
    pending = cache._pending_work_item_mutations()
    assert [mutation.item.description for mutation in pending] == ["newer body"]
    assert pending[0].idempotency_key != planned_mutation.idempotency_key


def test_github_reconcile_overlays_queued_work_item_by_stable_reference(tmp_path: Path) -> None:
    # Given: a cached snapshot whose storage path differs from its logical GitHub reference
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    snapshot = BacklogItem(title="Issue 1", reference="#1", description="cached body")
    snapshot.metadata.issue = "#1"
    snapshot.metadata.sync_fingerprint = synchronized_fingerprint(snapshot)
    cache._save_item_snapshot(snapshot, Path("legacy/issue-1.yaml"))
    queued = snapshot.model_copy(update={"description": "queued body"})
    backend.put_work_item(queued)

    # When: reconciliation loads its logical cache records
    records = backend._load_reconcile_records()

    # Then: the queued content replaces the storage-keyed snapshot without duplicating the logical record
    assert [(record.key, record.item.reference, record.item.description) for record in records] == [
        ("legacy/issue-1.yaml", "#1", "queued body")
    ]


def test_github_reconcile_acknowledges_successful_queue_despite_independent_conflict(tmp_path: Path) -> None:
    # Given: an offline title conflict and an independent queued body update
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    conflict = BacklogItem(title="Issue 1", reference="#1", description="provider body")
    conflict.metadata.issue = "#1"
    conflict.metadata.sync_fingerprint = synchronized_fingerprint(conflict)
    backend.put_work_item(conflict.model_copy(update={"title": "Renamed offline"}))
    noop = BacklogItem(title="Issue 2", reference="#2", description="provider body")
    noop.metadata.issue = "#2"
    noop.metadata.sync_fingerprint = synchronized_fingerprint(noop)
    backend.put_work_item(noop)
    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Issue 1",
                    body=backend.render_issue_body(conflict),
                    state="OPEN",
                    labels=[],
                    revision="rev-1",
                ),
                ProviderItem(
                    provider_id="node-2",
                    reference="#2",
                    title="Issue 2",
                    body=backend.render_issue_body(noop),
                    state="OPEN",
                    labels=[],
                    revision="rev-1",
                ),
            ],
            sync_started_at="2026-08-12T02:00:00Z",
            pages_fetched=1,
        )
    )
    backend._apply_patches = MagicMock(
        return_value=[
            PatchResult(provider_id="node-1", reference="#1", status="applied", revision="rev-2"),
            PatchResult(provider_id="node-2", reference="#2", status="applied", revision="rev-2"),
        ]
    )

    # When: reconnect reconciliation sees both records in the same snapshot
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1", "#2"]))

    # Then: the conflict remains durable while the independently successful update is acknowledged
    assert result.conflicts == 1
    assert result.failures == 0
    assert result.provider_patches == 2
    assert [mutation.key for mutation in cache._pending_work_item_mutations()] == ["#1"]


def test_github_queued_title_rename_survives_reconnect(tmp_path: Path) -> None:
    # Given: an offline queued rename that GitHub's body-only patch path cannot represent
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    renamed = baseline.model_copy(update={"title": "Renamed offline"})
    backend.put_work_item(renamed)
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

    # When: the provider reconnects without a lossless title mutation path
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: the rename remains durably queued instead of being acknowledged as synchronized
    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert result.conflicts == 1
    assert [mutation.item.title for mutation in pending] == ["Renamed offline"]
    assert backend._apply_patches.call_args.args[0][0].body


def _leak_a_baseline(title: str = "Issue 1", description: str = "provider body") -> BacklogItem:
    """Return a baseline shaped the way ``_checkpoint`` would persist it.

    ``_checkpoint`` (reconciliation.py) always receives a ``_compose``d
    candidate, whose ``metadata.status`` is always ``provider.state.lower()``
    -- never the empty string a bare ``BacklogItem()`` carries. The
    ``_merged_title`` probe recomputes ``synchronized_fingerprint`` -- which
    hashes ``metadata.status`` -- against this baseline's stored fingerprint,
    so a baseline built with ``status == ""`` can never match the probe's
    projection (whose status is always the real provider state). Every probe
    call would then silently fall through to the safe ``local.title`` answer,
    passing regardless of whether ``_merged_title`` actually works. Setting
    ``status`` explicitly here is what makes these 5 tests a real exercise of
    the merge logic instead of false-confidence passes.
    """
    baseline = BacklogItem(title=title, description=description)
    baseline.metadata.issue = "#1"
    baseline.metadata.status = "open"
    baseline.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    return baseline


def _leak_a_snapshot(backend: GitHubBackend, *, title: str, body_item: BacklogItem) -> ProviderSnapshot:
    return ProviderSnapshot(
        items=[
            ProviderItem(
                provider_id="node-1",
                reference="#1",
                title=title,
                body=backend.render_issue_body(body_item),
                state="OPEN",
                labels=[],
                revision="rev-1",
            )
        ],
        sync_started_at="2026-08-12T02:00:00Z",
        pages_fetched=1,
    )


def _leak_a_applied_patches() -> MagicMock:
    return MagicMock(
        return_value=[PatchResult(provider_id="node-1", reference="#1", status="applied", revision="rev-2")]
    )


def test_github_reconcile_accepts_remote_rename_when_local_only_edited_body(tmp_path: Path) -> None:
    """Remote renamed the title; local only edited the body. The fix's whole point:

    this must NOT be treated as a title conflict. Fails (RED) without the
    ``_merged_title`` fix, which would otherwise fall back to ``local.title``
    and discard the remote rename as a spurious conflict.
    """
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = _leak_a_baseline()
    local = baseline.model_copy(update={"description": "local body"})
    backend.put_work_item(local)
    backend._fetch_snapshot = MagicMock(
        return_value=_leak_a_snapshot(backend, title="Renamed on GitHub", body_item=baseline)
    )
    backend._apply_patches = _leak_a_applied_patches()

    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    assert result.conflicts == 0


def test_github_reconcile_retains_local_rename_when_remote_title_unchanged(tmp_path: Path) -> None:
    """DATA LOSS GUARD: local renamed the title offline; remote is unchanged.

    The offline rename must surface as a conflict and be retained, never
    silently overwritten by the provider's stale title. Must stay correct
    forever.
    """
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = _leak_a_baseline()
    renamed = baseline.model_copy(update={"title": "Renamed offline"})
    backend.put_work_item(renamed)
    backend._fetch_snapshot = MagicMock(return_value=_leak_a_snapshot(backend, title="Issue 1", body_item=baseline))
    backend._apply_patches = _leak_a_applied_patches()

    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert result.conflicts == 1, "DATA LOSS: offline rename silently accepted the provider title"
    assert [mutation.item.title for mutation in pending] == ["Renamed offline"]


def test_github_reconcile_conflicts_when_remote_renamed_and_remote_body_changed(tmp_path: Path) -> None:
    """Remote renamed the title AND the remote body changed in the same snapshot.

    Documented, deliberate fallback ceiling: the merge probe can only prove a
    remote-only rename by reproducing the baseline fingerprint with local's
    title substituted in, which requires every other field (including body)
    to match the baseline exactly. A concurrent remote body change breaks
    that substitution, so this falls back to ``local.title`` and surfaces as
    a conflict -- safe, just not optimized. Do not "fix" this without
    re-reading the design rationale in reconciliation.py's ``_merged_title``.
    """
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = _leak_a_baseline()
    remote_body_item = baseline.model_copy(update={"description": "remote body moved on"})
    local = baseline.model_copy(update={"description": "local body"})
    backend.put_work_item(local)
    backend._fetch_snapshot = MagicMock(
        return_value=_leak_a_snapshot(backend, title="Renamed on GitHub", body_item=remote_body_item)
    )
    backend._apply_patches = _leak_a_applied_patches()

    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    assert result.conflicts == 1


def test_github_reconcile_retains_local_rename_when_remote_body_also_changed(tmp_path: Path) -> None:
    """DATA LOSS GUARD: local renamed offline while the remote body also moved on."""
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = _leak_a_baseline()
    remote_body_item = baseline.model_copy(update={"description": "remote body moved on"})
    renamed = baseline.model_copy(update={"title": "Renamed offline"})
    backend.put_work_item(renamed)
    backend._fetch_snapshot = MagicMock(
        return_value=_leak_a_snapshot(backend, title="Issue 1", body_item=remote_body_item)
    )
    backend._apply_patches = _leak_a_applied_patches()

    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert result.conflicts == 1
    assert [mutation.item.title for mutation in pending] == ["Renamed offline"]


def test_github_reconcile_retains_local_rename_when_both_sides_renamed_differently(tmp_path: Path) -> None:
    """DATA LOSS GUARD: local renamed offline AND remote renamed differently."""
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = _leak_a_baseline()
    renamed = baseline.model_copy(update={"title": "Renamed offline"})
    backend.put_work_item(renamed)
    backend._fetch_snapshot = MagicMock(
        return_value=_leak_a_snapshot(backend, title="Renamed on GitHub", body_item=baseline)
    )
    backend._apply_patches = _leak_a_applied_patches()

    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    pending = FileCache(tmp_path)._pending_work_item_mutations()
    assert result.conflicts == 1, "DATA LOSS: concurrent rename resolved to the provider title"
    assert [mutation.item.title for mutation in pending] == ["Renamed offline"]


def test_github_work_item_ack_ignores_stable_reference_when_title_drifted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a queued body-only edit whose patch will land successfully, while
    # GitHub's title has drifted for reasons unrelated to the queued change
    # (e.g. renamed by someone else after the item was queued locally).
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    baseline = BacklogItem(title="Issue 1", description="provider body")
    baseline.metadata.issue = "#1"
    baseline.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local = baseline.model_copy(update={"description": "local body"})
    backend.put_work_item(local)  # frozen queued title: "Issue 1"

    backend._fetch_snapshot = MagicMock(
        return_value=ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="node-1",
                    reference="#1",
                    title="Renamed on GitHub",
                    body=backend.render_issue_body(baseline),
                    state="OPEN",
                    labels=[],
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

    # The pure reconcile engine has its own, separate title-conflict gate
    # (reconciliation.py's `candidate.title != provider.title` check) that
    # would otherwise co-fire alongside the acknowledgement guard under test
    # and mask which one is responsible for the stuck entry. Substituting a
    # clean patch-only plan isolates the acknowledgement guard itself.
    def isolated_plan(records: object, snapshot: ProviderSnapshot, request: ReconcileRequest) -> ReconcilePlan:
        return ReconcilePlan(
            provider_patches=[
                ProviderPatch(provider_id="node-1", reference="#1", expected_revision="rev-1", body="patched body")
            ],
            result=ReconcileResult(fetched_pages=snapshot.pages_fetched, fetched_items=len(snapshot.items)),
            snapshot_checkpoint=snapshot.sync_started_at,
        )

    monkeypatch.setattr(github_work_items, "reconcile_backlog", isolated_plan)

    # When: reconciliation applies the patch against a GitHub snapshot whose
    # title no longer matches what was frozen at queue time
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1"]))

    # Then: the mutation should be acknowledged -- it shares the same stable
    # reference ("#1") and its patch landed -- but the frozen-title equality
    # guard in `_acknowledge_work_items` (github_work_items.py) can never
    # match a title that changed after the item was queued, so the mutation
    # leaks in `pending_work_items` forever. This pins the sane target
    # behavior (acknowledge by stable reference, not title text) and is
    # expected to fail (RED) against the current guard.
    assert FileCache(tmp_path)._pending_work_item_mutations() == []


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
