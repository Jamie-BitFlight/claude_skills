from __future__ import annotations

import pytest
from backlog_core.backend_protocol import (
    ContentConflictError,
    ContentProvider,
    ContentProviderError,
    ContentUnavailableError,
    SyncProvider,
    UnsupportedCapabilityError,
)
from backlog_core.models import (
    BacklogItemMetadata,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
    PatchResult,
    ProviderItem,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
)
from pydantic import ValidationError


class _InMemorySyncProvider:
    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        return ReconcileResult()


class _RetiredTransportProvider:
    def fetch_snapshot(self, request: ReconcileRequest) -> object:
        return object()

    def apply_patches(self, patches: list[object]) -> list[object]:
        return []


class _InMemoryContentProvider:
    def list_content(self, query: ContentQuery) -> list[ContentRecord]:
        return []

    def get_content(self, reference: ContentRef) -> ContentRecord:
        return ContentRecord(reference=reference, content="")

    def put_content(self, request: ContentWrite) -> ContentRecord:
        return ContentRecord(
            reference=request.reference, content=request.content, owner_reference=request.owner_reference or ""
        )


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

    # Then: the single reconciliation method is required
    assert supported is True


def test_retired_transport_surface_does_not_satisfy_sync_protocol() -> None:
    assert isinstance(_RetiredTransportProvider(), SyncProvider) is False


def test_reconcile_result_exposes_offline_state() -> None:
    # Given: a reconciliation that performed no work
    result = ReconcileResult()

    # When: its additive offline result fields are inspected
    offline_state = (result.stale, result.unavailable_references, result.pending_mutations)

    # Then: callers can distinguish cached absence from an authoritative empty result
    assert offline_state == (False, [], 0)


def test_content_ref_preserves_plan_identity_without_owner() -> None:
    # Given: a logical plan ID
    reference = ContentRef(kind=ContentKind.PLAN, name="P123-plan")

    # When: it crosses the content boundary
    identity = (reference.kind, reference.namespace, reference.artifact_type, reference.name)

    # Then: the immutable identity excludes the mutable owner
    assert identity == (ContentKind.PLAN, "", "", "P123-plan")


@pytest.mark.parametrize(
    ("reference", "reason"),
    [
        (
            ContentRef.model_construct(kind=ContentKind.PLAN, namespace="item-1", artifact_type="", name="P1"),
            "plan namespace",
        ),
        (
            ContentRef.model_construct(kind=ContentKind.PLAN, namespace="", artifact_type="task", name="P1"),
            "plan artifact type",
        ),
        (
            ContentRef.model_construct(
                kind=ContentKind.ARTIFACT_MANIFEST, namespace="", artifact_type="", name="manifest"
            ),
            "manifest owner",
        ),
        (
            ContentRef.model_construct(
                kind=ContentKind.ARTIFACT_MANIFEST, namespace="item-1", artifact_type="", name="other"
            ),
            "manifest canonical name",
        ),
        (
            ContentRef.model_construct(
                kind=ContentKind.ARTIFACT_CONTENT, namespace="", artifact_type="report", name="id"
            ),
            "content owner",
        ),
        (
            ContentRef.model_construct(
                kind=ContentKind.ARTIFACT_CONTENT, namespace="item-1", artifact_type="", name="id"
            ),
            "content type",
        ),
    ],
)
def test_content_ref_rejects_kind_specific_invalid_identity(reference: ContentRef, reason: str) -> None:
    # Given: an identity that violates its content-kind contract
    # When / Then: validation rejects it at the boundary
    with pytest.raises(ValidationError, match=reason):
        ContentRef.model_validate(reference)


def test_content_ref_preserves_artifact_owner_type_and_id() -> None:
    # Given: content stored for one owning item and type
    reference = ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace="item-7", artifact_type="research", name="artifact-42"
    )

    # When: its storage identity is constructed
    identity = (reference.kind, reference.namespace, reference.artifact_type, reference.name)

    # Then: all identity coordinates are retained
    assert identity == (ContentKind.ARTIFACT_CONTENT, "item-7", "research", "artifact-42")


def test_content_ref_accepts_owner_scoped_manifest() -> None:
    # Given: the canonical artifact manifest address
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="item-7", name="manifest")

    # When: it crosses the typed content boundary
    identity = (reference.kind, reference.namespace, reference.artifact_type, reference.name)

    # Then: its owner and canonical name form a valid manifest identity
    assert identity == (ContentKind.ARTIFACT_MANIFEST, "item-7", "", "manifest")


def test_artifact_content_identity_distinguishes_owner_and_type() -> None:
    # Given: artifact records that share an artifact ID
    references = [
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="item-7", artifact_type="research", name="artifact-42"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="item-8", artifact_type="research", name="artifact-42"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="item-7", artifact_type="plan", name="artifact-42"),
    ]

    # When: their complete content identities become storage keys
    identities = {
        (reference.kind, reference.namespace, reference.artifact_type, reference.name) for reference in references
    }

    # Then: neither owner nor artifact type can collide
    assert len(identities) == 3


def test_content_write_distinguishes_plan_owner_preserve_reassign_and_unlink() -> None:
    # Given: a plan with a stable content identity
    reference = ContentRef(kind=ContentKind.PLAN, name="P123-plan")

    # When: its owner is omitted, assigned, or explicitly cleared
    writes = [
        ContentWrite(reference=reference, content="body"),
        ContentWrite(reference=reference, content="body", owner_reference="item-9"),
        ContentWrite(reference=reference, content="body", owner_reference=""),
    ]

    # Then: None preserves while strings reassign or unlink
    assert [write.owner_reference for write in writes] == [None, "item-9", ""]


def test_content_write_rejects_conflicting_artifact_owner() -> None:
    # Given: an artifact whose owner is part of immutable identity
    reference = ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace="item-7", artifact_type="research", name="artifact-42"
    )

    # When / Then: reassignment to another owner is rejected
    with pytest.raises(ValidationError, match="owner_reference"):
        ContentWrite(reference=reference, content="body", owner_reference="item-8")


def test_in_memory_content_provider_satisfies_optional_content_protocol() -> None:
    # Given: the minimal three-operation content capability
    provider = _InMemoryContentProvider()

    # When: callers inspect the optional runtime-checkable seam
    supported = isinstance(provider, ContentProvider)

    # Then: the typed content methods establish the capability
    assert supported is True


def test_content_capability_errors_have_one_explicit_base_type() -> None:
    # Given: the public capability error cases
    errors = [ContentUnavailableError(), ContentConflictError(), UnsupportedCapabilityError()]

    # When: callers handle a content-capability failure
    supported = [isinstance(error, ContentProviderError) for error in errors]

    # Then: every case can be handled without selecting a fallback provider
    assert supported == [True, True, True]
