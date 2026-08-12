from __future__ import annotations

import pytest
from backlog_core.backend_protocol import SyncProvider
from backlog_core.models import (
    BacklogItemMetadata,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
)
from pydantic import ValidationError


class _InMemorySyncProvider:
    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        return ProviderSnapshot(items=[], sync_started_at="2026-08-12T00:00:00Z")

    def apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        return []


def test_sync_fingerprint_defaults_to_empty_checkpoint() -> None:
    # Given: metadata for an item that has never been reconciled
    metadata = BacklogItemMetadata()

    # When: the persisted model is serialized
    serialized = metadata.model_dump()

    # Then: the empty fingerprint establishes bootstrap semantics
    assert serialized["sync_fingerprint"] == ""


def test_provider_item_accepts_a_tombstone() -> None:
    # Given: a targeted provider lookup confirms the linked item is absent
    tombstone = ProviderItem(
        provider_id="node-1",
        reference="#1",
        title="Deleted item",
        body="",
        state="CLOSED",
        labels=[],
        revision="rev-1",
        exists=False,
    )

    # When: the normalized provider item is inspected
    exists = tombstone.exists

    # Then: absence is preserved explicitly rather than inferred from omission
    assert exists is False


def test_reconcile_request_parses_each_scope() -> None:
    # Given: every supported reconciliation scope
    raw_scopes = ["initial", "incremental", "linked", "targeted"]

    # When: each scope enters the typed boundary
    requests = [ReconcileRequest(scope=scope) for scope in raw_scopes]

    # Then: each value is represented by the closed scope set
    assert [request.scope for request in requests] == list(ReconcileScope)


def test_reconcile_request_rejects_unknown_scope() -> None:
    # Given: an unsupported reconciliation scope
    # When / Then: Pydantic rejects it at the boundary
    with pytest.raises(ValidationError):
        ReconcileRequest(scope="all")


def test_patch_result_rejects_unknown_status() -> None:
    # Given: a provider patch result outside the defined outcome set
    # When / Then: Pydantic rejects it at the boundary
    with pytest.raises(ValidationError):
        PatchResult.model_validate({"provider_id": "node-1", "reference": "#1", "status": "skipped"})


def test_in_memory_provider_satisfies_optional_sync_protocol() -> None:
    # Given: the minimal in-memory provider adapter
    provider = _InMemorySyncProvider()

    # When: callers inspect the optional runtime-checkable seam
    supported = isinstance(provider, SyncProvider)

    # Then: only the two reconciliation methods are required
    assert supported is True
