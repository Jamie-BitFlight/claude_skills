"""Fetch-only reconciliation must still advance the snapshot checkpoint.

PR #3573 review Finding 2 (P2): a never-synced cache carrying a divergent
queued local mutation, reconciled fetch-only (``ReconcileRequest.
apply_local_patches=False`` — used by the implicit cold-cache read-through in
``operations.list_items`` so a plain ``backlog_list`` call never replays a
queued edit to GitHub), supplies no ``PatchResult`` for that mutation's
provider patch. Before the fix, ``finalize_reconciliation`` counted the
intentionally skipped patch as a failure, so ``_advance_snapshot_checkpoint``
refused to persist the checkpoint even though the snapshot fetch and cache
write both completed cleanly — ``has_synced_snapshot()`` stayed False
forever, and every subsequent default list performed another full GitHub
fetch.

These tests drive the real ``_GitHubReconciliation.reconcile()`` against a
real ``FileCache`` (temp-directory backed) and a minimal fake
``_ReconcileProvider``, rather than a stub of ``reconcile()`` itself, so the
assertions exercise the exact ``finalize_reconciliation`` /
``_advance_snapshot_checkpoint`` interaction the finding identifies.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from backlog_core.backends.github_work_items import _GitHubReconciliation
from backlog_core.file_cache import FileCache
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BacklogItem,
    PatchResult,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
)

if TYPE_CHECKING:
    from backlog_core.models import ProviderPatch

_PatchStatus = Literal["applied", "conflict", "error"]

_ISSUE_REFERENCE = "#1"
_SHARED_TITLE = "Same Title"


class _FakeReconcileProvider:
    """Minimal ``_ReconcileProvider`` stand-in recording every patch-apply call."""

    def __init__(self, snapshot: ProviderSnapshot, *, patch_status: _PatchStatus = "applied") -> None:
        self._snapshot = snapshot
        self._patch_status = patch_status
        self.apply_patches_calls: list[list[ProviderPatch]] = []

    def _fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Return the fixed snapshot regardless of the request (test double)."""
        del request
        return self._snapshot

    def _apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        self.apply_patches_calls.append(patches)
        return [
            PatchResult(
                provider_id=patch.provider_id, reference=patch.reference, status=self._patch_status, revision="rev-2"
            )
            for patch in patches
        ]


def _provider_snapshot() -> ProviderSnapshot:
    """One provider item whose body differs from the queued local edit's description."""
    remote_source = BacklogItem(
        title=_SHARED_TITLE, description="Provider description", issue=_ISSUE_REFERENCE, section="P1"
    )
    body = render_issue_body(remote_source)
    item = ProviderItem(
        provider_id="PVT_1",
        reference=_ISSUE_REFERENCE,
        title=_SHARED_TITLE,
        body=body,
        state="OPEN",
        labels=[],
        revision="rev-1",
    )
    return ProviderSnapshot(items=[item], sync_started_at="2026-01-01T00:00:00+00:00", pages_fetched=1)


def _queue_divergent_local_mutation(cache: FileCache) -> None:
    """Queue a local edit for #1 whose description diverges from the provider's.

    Same title as the provider item (see ``_provider_snapshot``) so
    ``reconcile_backlog`` takes the ordinary patch branch, not the
    title-conflict branch — conflicts independently block the checkpoint
    (``_advance_snapshot_checkpoint`` requires ``conflicts == 0``), so a title
    mismatch here would not isolate the behaviour this test targets.
    """
    local_item = BacklogItem(title=_SHARED_TITLE, description="Local description", issue=_ISSUE_REFERENCE, section="P1")
    cache._queue_work_item("1", local_item)


class TestFetchOnlyReconcileAdvancesTheCheckpoint:
    """A fetch-only reconcile that skips a divergent patch still counts as synced."""

    def test_checkpoint_persists_and_the_mutation_stays_unapplied(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        _queue_divergent_local_mutation(cache)
        provider = _FakeReconcileProvider(_provider_snapshot())
        reconciliation = _GitHubReconciliation(cache, provider)

        assert reconciliation.has_synced_snapshot() is False

        result = reconciliation.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=False))

        # The provider was never asked to push the queued edit.
        assert provider.apply_patches_calls == []
        # The skipped patch is accounted for, but not as a failure.
        assert result.skipped_patches == 1
        assert result.failures == 0
        # The checkpoint durably advanced despite the skipped patch.
        assert reconciliation.has_synced_snapshot() is True
        # The queued mutation is still pending -- never silently acknowledged.
        pending = cache._pending_work_item_mutations()
        assert len(pending) == 1
        assert pending[0].item.reference == _ISSUE_REFERENCE

    def test_a_second_fetch_only_call_does_not_repeat_the_full_fetch(self, tmp_path: Path) -> None:
        """Regression guard for the reported symptom: once the checkpoint has
        advanced, ``has_synced_snapshot()`` must not flip back to False on a
        second fetch-only pass over the same still-unresolved mutation."""
        cache = FileCache(tmp_path)
        _queue_divergent_local_mutation(cache)
        provider = _FakeReconcileProvider(_provider_snapshot())
        reconciliation = _GitHubReconciliation(cache, provider)

        reconciliation.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=False))
        assert reconciliation.has_synced_snapshot() is True

        reconciliation.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, apply_local_patches=False))

        assert reconciliation.has_synced_snapshot() is True


class TestFinalizeReconciliationStillDistinguishesFailureFromSkip:
    """A genuinely failed patch (attempted, no usable outcome) must still block
    the checkpoint -- the fix must not broaden into "always advance"."""

    def test_an_applied_patches_run_still_advances_and_acknowledges(self, tmp_path: Path) -> None:
        """Baseline: the ordinary apply_local_patches=True path is unaffected."""
        cache = FileCache(tmp_path)
        _queue_divergent_local_mutation(cache)
        provider = _FakeReconcileProvider(_provider_snapshot(), patch_status="applied")
        reconciliation = _GitHubReconciliation(cache, provider)

        result = reconciliation.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=True))

        assert len(provider.apply_patches_calls) == 1
        assert result.skipped_patches == 0
        assert result.failures == 0
        assert reconciliation.has_synced_snapshot() is True
        assert cache._pending_work_item_mutations() == []

    def test_a_genuine_patch_error_still_blocks_the_checkpoint(self, tmp_path: Path) -> None:
        """A patch that was attempted and errored is a real failure, not a skip."""
        cache = FileCache(tmp_path)
        _queue_divergent_local_mutation(cache)
        provider = _FakeReconcileProvider(_provider_snapshot(), patch_status="error")
        reconciliation = _GitHubReconciliation(cache, provider)

        result = reconciliation.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=True))

        assert len(provider.apply_patches_calls) == 1
        assert result.skipped_patches == 0
        assert result.failures == 1
        assert reconciliation.has_synced_snapshot() is False
