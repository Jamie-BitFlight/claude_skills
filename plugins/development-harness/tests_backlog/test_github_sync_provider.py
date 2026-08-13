from __future__ import annotations

from pathlib import Path
from typing import Protocol
from unittest.mock import MagicMock

import pytest
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ArtifactManifest,
    BacklogError,
    BacklogItem,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    ProviderPatch,
    ReconcileRequest,
    ReconcileScope,
    UnsupportedCapabilityError,
)
from sam_schema.core.artifact_registry_client import ArtifactRegistryClient, PlanIndexUnavailableError
from sam_schema.core.plan_id_index import PlanIndexEntry, _serialize_index_yaml


class _RemoteArtifactProviderFakeSpec(Protocol):
    def store_artifact_content(self, owner: int, artifact_type: str, path: str, content: str) -> None: ...

    def read_artifact_content_from_remote(self, owner: int, artifact_type: str, path: str) -> str | None: ...

    def list_artifact_content_from_remote(self, owner: int, artifact_type: str, path_prefix: str) -> dict[str, str]: ...


def _issue(number: int, revision: str = "rev-1") -> dict[str, object]:
    return {
        "id": f"node-{number}",
        "number": number,
        "title": f"Issue {number}",
        "body": "body",
        "state": "OPEN",
        "labels": [{"id": "label-1", "name": "feature"}],
        "updatedAt": revision,
        "createdAt": "2026-08-12T00:00:00Z",
        "milestone": None,
        "assignees": [],
    }


def test_github_sync_provider_normalizes_bounded_snapshot() -> None:
    # Given: a GitHub backend returning a GraphQL issue page
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue(1)])

    # When: reconciliation fetches an initial snapshot
    snapshot = backend._fetch_snapshot(ReconcileRequest(scope=ReconcileScope.INITIAL))

    # Then: the normalized provider item retains body, labels, and revision
    assert snapshot.items[0].reference == "#1"
    assert snapshot.items[0].labels == ["feature"]
    assert snapshot.items[0].revision == "rev-1"
    assert backend._fetch_issues_graphql.call_args.kwargs["first"] == 100


def test_github_sync_provider_forwards_label_scope_to_snapshot_query() -> None:
    # Given: an initial reconciliation restricted to one label
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue(1)])

    # When: the adapter fetches the provider snapshot
    backend._fetch_snapshot(ReconcileRequest(scope=ReconcileScope.INITIAL, label="review"))

    # Then: the existing GraphQL query receives only the requested label
    assert backend._fetch_issues_graphql.call_args.kwargs["labels"] == ["review"]


def test_github_sync_provider_reports_conflict_without_mutation() -> None:
    # Given: a preflight revision that differs from the patch expectation
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._graphql_request = MagicMock(return_value={"repository": {"i0": _issue(1, revision="rev-2")}})
    backend._update_issues_graphql_batch = MagicMock()
    patch = ProviderPatch(provider_id="node-1", reference="#1", expected_revision="rev-1", body="updated")

    # When: the patch is applied
    result = backend._apply_patches([patch])

    # Then: the provider body mutation is skipped and the conflict is surfaced
    assert result[0].status == "conflict"
    backend._update_issues_graphql_batch.assert_not_called()


def test_github_sync_provider_targeted_fetch_uses_alias_batch_and_emits_tombstone() -> None:
    # Given: one existing and one deleted linked reference
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issue_graphql = MagicMock()
    backend._fetch_issues_graphql = MagicMock()
    backend._graphql_request = MagicMock(return_value={"repository": {"i0": _issue(1), "i1": None}})

    # When: reconciliation asks only for those linked references
    snapshot = backend._fetch_snapshot(ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#1", "#2"]))

    # Then: one bounded alias query replaces per-issue reads and preserves the deletion explicitly
    assert [item.exists for item in snapshot.items] == [True, False]
    assert snapshot.items[1].reference == "#2"
    backend._fetch_issue_graphql.assert_not_called()
    backend._fetch_issues_graphql.assert_not_called()
    assert "i0: issue(number: $number0)" in backend._graphql_request.call_args.args[1]


def test_github_sync_provider_bounds_targeted_aliases_to_one_hundred() -> None:
    # Given: 101 targeted references and a response derived from each bounded request
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")

    def targeted_response(_repo: object, _query: str, variables: dict[str, object]) -> dict[str, object]:
        numbers = [value for key, value in variables.items() if key.startswith("number") and isinstance(value, int)]
        return {"repository": {f"i{index}": _issue(number) for index, number in enumerate(numbers)}}

    backend._graphql_request = MagicMock(side_effect=targeted_response)

    # When: all references are resolved
    resolved = backend._fetch_targeted_issues(repository, "owner", "repo", [f"#{number}" for number in range(1, 102)])

    # Then: no aliased GraphQL request exceeds the documented page bound
    assert len(resolved) == 101
    assert [
        len([key for key in call.args[2] if key.startswith("number")])
        for call in backend._graphql_request.call_args_list
    ] == [100, 1]


def test_github_sync_provider_rejects_body_change_without_mutation() -> None:
    # Given: a body patch whose current provider revision matches
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issue_graphql = MagicMock()
    backend._fetch_issues_graphql = MagicMock()
    backend._graphql_request = MagicMock(return_value={"repository": {"i0": _issue(1)}})
    backend._update_issues_graphql_batch = MagicMock()
    patch = ProviderPatch(provider_id="node-1", reference="#1", expected_revision="rev-1", body="updated")

    # When: the adapter classifies the unsafe body change
    results = backend._apply_patches([patch])

    # Then: no conditional GitHub mutation exists, so the observed revision is a conflict
    assert results[0].status == "conflict"
    assert results[0].revision == "rev-1"
    backend._update_issues_graphql_batch.assert_not_called()
    backend._fetch_issue_graphql.assert_not_called()
    backend._fetch_issues_graphql.assert_not_called()


def test_github_sync_provider_omits_matching_patch_body() -> None:
    # Given: a patch body that already matches the revision-preflight body
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._graphql_request = MagicMock(return_value={"repository": {"i0": _issue(1)}})
    backend._update_issues_graphql_batch = MagicMock()
    patch = ProviderPatch(provider_id="node-1", reference="#1", expected_revision="rev-1", body="body")

    # When: patch application reaches the preflight equality check
    results = backend._apply_patches([patch])

    # Then: no mutation is sent and the existing revision is returned as applied
    assert results[0].status == "applied"
    assert results[0].revision == "rev-1"
    backend._update_issues_graphql_batch.assert_not_called()


def test_github_backend_reconcile_owns_snapshot_cache_and_engine(tmp_path: Path) -> None:
    # Given: a remote-only issue and an injected private file cache
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache)
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    remote_issue = _issue(1)
    remote_issue["body"] = backend.render_issue_body(BacklogItem())
    backend._fetch_issues_graphql = MagicMock(return_value=[remote_issue])

    # When: callers invoke the backend's one reconciliation capability
    result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))

    # Then: the pure engine result and durable cache mutation are both completed internally
    assert result.fetched_items == 1
    assert result.local_updates == 1
    assert result.changed_references == ["#1"]
    assert not hasattr(backend, "fetch_snapshot")
    assert not hasattr(backend, "apply_patches")
    assert cache._work_item_snapshots()[0][1].metadata.sync_fingerprint


def test_github_content_provider_fails_closed_on_plan_creation(tmp_path: Path) -> None:
    # Given: a reachable provider and a new logical plan identity
    artifact_provider = MagicMock()
    remote_content: dict[tuple[int, str, str], str] = {}
    artifact_provider.get_manifest.side_effect = lambda owner: ArtifactManifest(issue_number=owner)
    artifact_provider.read_local_artifact_content.return_value = None
    artifact_provider.store_artifact_content.side_effect = lambda owner, artifact_type, path, content: (
        remote_content.__setitem__((owner, artifact_type, path), content)
    )
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: (
        remote_content.get((owner, artifact_type, path))
    )
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")

    # When: a new plan is requested without a provider CAS revision
    with pytest.raises(UnsupportedCapabilityError):
        backend.put_content(ContentWrite(reference=reference, content="v1", owner_reference="#1"))

    # Then: no Gist content or index mutation is reported or performed
    assert remote_content == {}


def test_github_content_provider_keeps_linked_plans_separate_by_plan_id(tmp_path: Path) -> None:
    # Given: two existing logical plans linked to the same GitHub issue
    artifact_provider = MagicMock()
    remote_content: dict[tuple[int, str, str], str] = {}
    artifact_provider.get_manifest.side_effect = lambda owner: ArtifactManifest(issue_number=owner)
    artifact_provider.store_artifact_content.side_effect = lambda owner, artifact_type, path, content: (
        remote_content.__setitem__((owner, artifact_type, path), content)
    )
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: (
        remote_content.get((owner, artifact_type, path))
    )
    remote_content[2531, "plan-index", "sam-plan/plan-index.yaml"] = _serialize_index_yaml([
        PlanIndexEntry(plan_id="Pfirst", issue=42, slug="first", created_at="2026-08-12T00:00:00Z"),
        PlanIndexEntry(plan_id="Psecond", issue=42, slug="second", created_at="2026-08-12T00:00:00Z"),
    ])
    remote_content[42, "task-plan", "sam-plan/task-plan-issue-42-plan-Pfirst.yaml"] = "first"
    remote_content[42, "task-plan", "sam-plan/task-plan-issue-42-plan-Psecond.yaml"] = "second"
    first = ContentRef(kind=ContentKind.PLAN, name="Pfirst")
    second = ContentRef(kind=ContentKind.PLAN, name="Psecond")

    # When: both plans are fetched through a fresh backend
    fresh_backend = GitHubBackend(cache=FileCache(tmp_path / "fresh"), artifact_provider=artifact_provider)
    fresh_backend.try_get_github = MagicMock(return_value=MagicMock())
    records = fresh_backend.list_content(ContentQuery(kind=ContentKind.PLAN, owner_reference="#42"))

    # Then: each logical ID has an independent Gist and manifest identity
    assert [(record.reference, record.content) for record in records] == [(first, "first"), (second, "second")]
    assert remote_content[42, "task-plan", "sam-plan/task-plan-issue-42-plan-Pfirst.yaml"] == "first"
    assert remote_content[42, "task-plan", "sam-plan/task-plan-issue-42-plan-Psecond.yaml"] == "second"


def test_github_content_provider_reads_legacy_linked_plan_path(tmp_path: Path) -> None:
    # Given: a plan index entry and the issue-only path written before plan-specific storage
    reference = ContentRef(kind=ContentKind.PLAN, name="Plegacy")
    index = _serialize_index_yaml([
        PlanIndexEntry(plan_id="Plegacy", issue=42, slug="legacy", created_at="2026-08-12T00:00:00Z")
    ])
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: {
        (2531, "plan-index", "sam-plan/plan-index.yaml"): index,
        (42, "task-plan", "sam-plan/task-plan-issue-42.yaml"): "legacy content",
    }.get((owner, artifact_type, path))
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: the indexed legacy plan is fetched
    record = backend.get_content(reference)

    # Then: only the remote legacy identity supplies its content
    assert record.content == "legacy content"
    artifact_provider.read_local_artifact_content.assert_not_called()


def test_github_content_provider_discovers_remote_plans_with_empty_cache(tmp_path: Path) -> None:
    # Given: a provider-native index and plan while the private file cache is empty
    artifact_provider = MagicMock()
    artifact_provider.get_manifest.side_effect = lambda owner: ArtifactManifest(issue_number=owner)
    artifact_provider.read_local_artifact_content.return_value = None
    index = _serialize_index_yaml([
        PlanIndexEntry(plan_id="Premote", issue=None, slug="remote-plan", created_at="2026-08-12T00:00:00Z")
    ])
    remote_content = {
        (2531, "plan-index", "sam-plan/plan-index.yaml"): index,
        (2531, "plan", "sam-plan/unlinked/Premote.yaml"): "remote body",
    }
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: (
        remote_content.get((owner, artifact_type, path))
    )
    cache = FileCache(tmp_path)
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: bounded plan discovery runs online
    listed = backend.list_content(ContentQuery(kind=ContentKind.PLAN, owner_reference="", limit=1))

    # Then: the remote index is authoritative and refreshes the private cache
    assert [(record.reference.name, record.content) for record in listed] == [("Premote", "remote body")]
    assert cache.get_content(ContentRef(kind=ContentKind.PLAN, name="Premote")).content == "remote body"


def test_github_content_provider_round_trips_dispatch_content_without_sam_plan_index(tmp_path: Path) -> None:
    # Given: an online provider with no cached content.
    remote_content: dict[tuple[int, str, str], str] = {}
    artifact_provider = MagicMock(spec=_RemoteArtifactProviderFakeSpec)
    artifact_provider.store_artifact_content.side_effect = lambda owner, artifact_type, path, content: (
        remote_content.__setitem__((owner, artifact_type, path), content)
    )
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: (
        remote_content.get((owner, artifact_type, path))
    )
    artifact_provider.list_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path_prefix: {
        path: content
        for (stored_owner, stored_type, path), content in remote_content.items()
        if (stored_owner, stored_type) == (owner, artifact_type) and path.startswith(path_prefix)
    }
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-10")
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: a dispatch plan is created, preserved, reassigned, and unlinked.
    created = backend.put_content(
        ContentWrite(reference=reference, content='{"milestone":{"number":10}}', owner_reference="#1")
    )
    preserved = backend.put_content(
        ContentWrite(
            reference=reference,
            content='{"milestone":{"number":10},"state":"draft"}',
            expected_revision=created.revision,
        )
    )
    reassigned = backend.put_content(
        ContentWrite(
            reference=reference,
            content='{"milestone":{"number":10},"state":"ready"}',
            owner_reference="#2",
            expected_revision=preserved.revision,
        )
    )
    written = backend.put_content(
        ContentWrite(
            reference=reference,
            content='{"milestone":{"number":10},"state":"final"}',
            owner_reference="",
            expected_revision=reassigned.revision,
        )
    )
    other_reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-11")
    other = backend.put_content(
        ContentWrite(reference=other_reference, content='{"milestone":{"number":11}}', owner_reference="#3")
    )
    fresh_backend = GitHubBackend(cache=FileCache(tmp_path / "fresh"), artifact_provider=artifact_provider)
    fresh_backend.try_get_github = MagicMock(return_value=MagicMock())
    dispatch_records = fresh_backend.list_content(ContentQuery(kind=ContentKind.DISPATCH_PLAN))
    unowned_dispatch_records = fresh_backend.list_content(
        ContentQuery(kind=ContentKind.DISPATCH_PLAN, owner_reference="")
    )
    owned_dispatch_records = fresh_backend.list_content(
        ContentQuery(kind=ContentKind.DISPATCH_PLAN, owner_reference="#3")
    )
    sam_records = fresh_backend.list_content(ContentQuery(kind=ContentKind.PLAN))

    # Then: dispatch content round-trips independently and SAM discovery stays empty.
    assert [
        created.owner_reference,
        preserved.owner_reference,
        reassigned.owner_reference,
        written.owner_reference,
    ] == ["#1", "#1", "#2", ""]
    assert written.reference == reference
    assert [(record.reference, record.content) for record in dispatch_records] == [
        (reference, '{"milestone":{"number":10},"state":"final"}'),
        (other_reference, '{"milestone":{"number":11}}'),
    ]
    assert unowned_dispatch_records == [written]
    assert owned_dispatch_records == [other]
    assert sam_records == []


def test_github_content_provider_reads_legacy_name_only_dispatch_index(tmp_path: Path) -> None:
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-10")
    remote_content = {
        (2531, "dispatch-plan-index", "dispatch-plan/index.json"): '["dispatch-milestone-10"]',
        (2531, "dispatch-plan", "dispatch-plan/dispatch-milestone-10.json"): "legacy",
    }
    artifact_provider = MagicMock(spec=_RemoteArtifactProviderFakeSpec)
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda owner, artifact_type, path: (
        remote_content.get((owner, artifact_type, path))
    )
    artifact_provider.list_artifact_content_from_remote.return_value = {}
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    records = backend.list_content(ContentQuery(kind=ContentKind.DISPATCH_PLAN, owner_reference=""))

    assert [(record.reference, record.owner_reference, record.content) for record in records] == [
        (reference, "", "legacy")
    ]


def test_artifact_registry_client_plan_read_never_uses_local_artifact_storage() -> None:
    # Given: a remote miss and a local file that must not participate in GitHub plan reads
    provider = MagicMock()
    provider.read_artifact_content_from_remote.return_value = None
    provider.read_local_artifact_content.return_value = "wrong local plan"
    client = ArtifactRegistryClient(provider)

    # When: the plan is absent from its configured remote provider
    content = client.read(42)

    # Then: the client reports the miss without accessing arbitrary local artifact storage
    assert content is None
    provider.read_local_artifact_content.assert_not_called()


def test_artifact_registry_client_index_read_never_uses_local_artifact_storage() -> None:
    # Given: a remote index miss and a local file that must not participate in GitHub index reads
    provider = MagicMock()
    provider.read_artifact_content_from_remote.return_value = None
    provider.read_local_artifact_content.return_value = "wrong local index"
    client = ArtifactRegistryClient(provider)

    # When: the index is absent from its configured remote provider
    content = client.read_index(2531)

    # Then: the client reports the miss without accessing arbitrary local artifact storage
    assert content is None
    provider.read_local_artifact_content.assert_not_called()


def test_artifact_registry_client_index_read_raises_when_remote_is_unavailable() -> None:
    # Given: the configured remote provider cannot read the index
    provider = MagicMock()
    provider.read_artifact_content_from_remote.side_effect = BacklogError("offline")
    client = ArtifactRegistryClient(provider)

    # When: the plan index is read
    with pytest.raises(PlanIndexUnavailableError):
        client.read_index(2531)

    # Then: the failure remains distinct from a confirmed missing index
    provider.read_local_artifact_content.assert_not_called()


def test_github_content_provider_reads_cached_plan_while_github_is_offline(tmp_path: Path) -> None:
    # Given: a cached plan and an unreachable GitHub provider
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="Pcached")
    cache.cache_content(
        ContentRecord(reference=reference, owner_reference="#42", content="cached plan", revision="cached-revision")
    )
    artifact_provider = MagicMock()
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=None)

    # When: the plan is requested while the configured provider is unavailable
    cached = backend.get_content(reference)

    # Then: the provider-owned FileCache serves an explicitly stale copy without any artifact filesystem access
    assert (cached.content, cached.stale) == ("cached plan", True)
    artifact_provider.read_local_artifact_content.assert_not_called()


def test_github_plan_list_uses_stale_cache_when_index_is_unavailable(tmp_path: Path) -> None:
    # Given: cached plan content and an online GitHub API with an unavailable plan index
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="Pcached")
    cache.cache_content(ContentRecord(reference=reference, owner_reference="#42", content="cached plan"))
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.side_effect = BacklogError("offline index")
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: plan discovery cannot read its authoritative index
    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN))

    # Then: the existing cache is returned as stale and no empty index is stored
    assert [(record.reference, record.content, record.stale) for record in records] == [
        (reference, "cached plan", True)
    ]
    artifact_provider.store_artifact_content.assert_not_called()


def test_github_plan_get_uses_stale_cache_when_index_is_unavailable(tmp_path: Path) -> None:
    # Given: cached plan content and an online GitHub API with an unavailable plan index
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="Pcached")
    cache.cache_content(ContentRecord(reference=reference, owner_reference="#42", content="cached plan"))
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.side_effect = BacklogError("offline index")
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: a plan read cannot read its authoritative index
    record = backend.get_content(reference)

    # Then: the existing cache is returned as stale and no empty index is stored
    assert (record.reference, record.content, record.stale) == (reference, "cached plan", True)
    artifact_provider.store_artifact_content.assert_not_called()


def test_github_plan_put_queues_when_index_is_unavailable(tmp_path: Path) -> None:
    # Given: an online GitHub API with an unavailable authoritative plan index
    cache = FileCache(tmp_path)
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.side_effect = BacklogError("offline index")
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())
    request = ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="Pnew"), content="new plan")

    # When: a plan write cannot read its authoritative index
    record = backend.put_content(request)

    # Then: the mutation is queued without storing a replacement empty index
    assert record.pending is True
    assert len(cache.pending_mutations()) == 1
    artifact_provider.store_artifact_content.assert_not_called()


@pytest.mark.parametrize("operation", ["list", "get", "put"])
def test_github_plan_content_outage_uses_provider_cache(tmp_path: Path, operation: str) -> None:
    # Given: a readable plan index, a failed plan-content Gist read, and a stale cached record
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="Pcached")
    cache.cache_content(ContentRecord(reference=reference, owner_reference="#42", content="cached plan"))
    index = _serialize_index_yaml([
        PlanIndexEntry(plan_id="Pcached", issue=42, slug="cached", created_at="2026-08-12T00:00:00Z")
    ])
    artifact_provider = MagicMock()

    def read_remote(owner: int, artifact_type: str, path: str) -> str | None:
        if (owner, artifact_type, path) == (2531, "plan-index", "sam-plan/plan-index.yaml"):
            return index
        raise BacklogError("plan gist unavailable")

    artifact_provider.read_artifact_content_from_remote.side_effect = read_remote
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: plan discovery, read, or write reaches the unavailable Gist content
    match operation:
        case "list":
            result = backend.list_content(ContentQuery(kind=ContentKind.PLAN))
            assert [(record.content, record.stale) for record in result] == [("cached plan", True)]
        case "get":
            result = backend.get_content(reference)
            assert (result.content, result.stale) == ("cached plan", True)
        case "put":
            result = backend.put_content(ContentWrite(reference=reference, content="queued plan"))
            assert result.pending is True
            assert len(cache.pending_mutations()) == 1
        case unreachable:
            pytest.fail(f"unexpected operation: {unreachable}")


@pytest.mark.parametrize("operation", ["list", "get", "put"])
def test_github_dispatch_content_outage_uses_provider_cache(tmp_path: Path, operation: str) -> None:
    # Given: a readable dispatch index, a failed dispatch-content Gist read, and a stale cached record
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-cached")
    cache.cache_content(ContentRecord(reference=reference, content='{"state":"cached"}'))
    artifact_provider = MagicMock()

    def read_remote(owner: int, artifact_type: str, path: str) -> str:
        if (owner, artifact_type, path) == (2531, "dispatch-plan-index", "dispatch-plan/index.json"):
            return '{"version":1,"entries":[{"name":"dispatch-cached","owner_reference":""}]}'
        raise BacklogError("dispatch gist unavailable")

    artifact_provider.read_artifact_content_from_remote.side_effect = read_remote
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: dispatch discovery, read, or write reaches the unavailable Gist content
    match operation:
        case "list":
            result = backend.list_content(ContentQuery(kind=ContentKind.DISPATCH_PLAN))
            assert [(record.content, record.stale) for record in result] == [('{"state":"cached"}', True)]
        case "get":
            result = backend.get_content(reference)
            assert (result.content, result.stale) == ('{"state":"cached"}', True)
        case "put":
            result = backend.put_content(ContentWrite(reference=reference, content='{"state":"queued"}'))
            assert result.pending is True
            assert len(cache.pending_mutations()) == 1
        case unreachable:
            pytest.fail(f"unexpected operation: {unreachable}")


def test_github_content_provider_distinguishes_online_not_found_from_offline_cache_miss(tmp_path: Path) -> None:
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.return_value = None
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    reference = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="test", name="missing")

    backend.try_get_github = MagicMock(return_value=None)
    with pytest.raises(ContentUnavailableError) as offline:
        backend.get_content(reference)
    assert type(offline.value) is ContentUnavailableError

    backend.try_get_github = MagicMock(return_value=MagicMock())
    with pytest.raises(ContentNotFoundError):
        backend.get_content(reference)


def test_github_content_provider_queues_offline_write_and_returns_stale_cache(tmp_path: Path) -> None:
    # Given: one cached artifact and an unreachable GitHub provider
    cache = FileCache(tmp_path)
    artifact_provider = MagicMock()
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=None)
    reference = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="research", name="same/id")

    # When: a write is accepted offline and then read
    queued = backend.put_content(ContentWrite(reference=reference, content="offline"))
    stale = backend.get_content(reference)

    # Then: the mutation is durable, pending, and the cached read is explicitly stale
    assert queued.pending is True
    assert stale.stale is True
    assert len(cache.pending_mutations()) == 1
    artifact_provider.store_artifact_content.assert_not_called()


def test_github_content_provider_keeps_complete_artifact_identity(tmp_path: Path) -> None:
    # Given: equal artifact IDs under different owners and types
    artifact_provider = MagicMock()
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=MagicMock())
    references = [
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="design", name="same/id"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#2", artifact_type="design", name="same/id"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="test", name="same/id"),
    ]

    # When: all three records are written and listed through the logical content API
    for index, reference in enumerate(references):
        backend.put_content(ContentWrite(reference=reference, content=f"content-{index}"))
    listed = backend.list_content(ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, owner_reference="#1"))

    # Then: owner, type, and ID remain distinct and discovery is owner-bounded
    assert [record.reference for record in listed] == [references[0], references[2]]
    stored_paths = [call.args[2] for call in artifact_provider.store_artifact_content.call_args_list]
    assert stored_paths == ["design/same/id", "design/same/id", "test/same/id"]


def test_github_content_provider_partial_replay_acknowledges_only_applied_writes(tmp_path: Path) -> None:
    # Given: two durable offline writes and a provider that fails on the second mutation
    cache = FileCache(tmp_path)
    artifact_provider = MagicMock()
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    backend.try_get_github = MagicMock(return_value=None)
    references = [
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace=f"#{number}", artifact_type="test", name="report")
        for number in (1, 2)
    ]
    for reference in references:
        backend.put_content(ContentWrite(reference=reference, content=reference.namespace))
    artifact_provider.store_artifact_content.side_effect = [None, BacklogError("provider failed")]
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: reconnect discovery replays the durable queue
    backend.list_content(ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, owner_reference="#1"))

    # Then: the applied prefix is acknowledged and the failed suffix remains durable
    assert [mutation.write.reference for mutation in cache.pending_mutations()] == [references[1]]
    assert cache.get_content(references[0]).pending is False
    assert cache.get_content(references[1]).pending is True


def test_github_content_provider_replay_preserves_concurrent_remote_revision(tmp_path: Path) -> None:
    # Given: an offline artifact edit based on a revision that the remote later supersedes
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="test", name="report")
    remote = {"content": "revision-one"}
    artifact_provider = MagicMock()
    artifact_provider.read_artifact_content_from_remote.side_effect = lambda *_args: remote["content"]
    artifact_provider.store_artifact_content.side_effect = lambda *_args: remote.__setitem__("content", _args[-1])
    backend = GitHubBackend(cache=cache, artifact_provider=artifact_provider)
    initial = ContentRecord(
        reference=reference,
        owner_reference="#1",
        content=remote["content"],
        revision=GitHubBackend._content_revision(remote["content"]),
    )
    cache.cache_content(initial)
    backend.try_get_github = MagicMock(return_value=None)
    backend.put_content(ContentWrite(reference=reference, content="queued", expected_revision=initial.revision))
    remote["content"] = "revision-two"
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: reconnect reads the authoritative remote content before replay
    current = backend.get_content(reference)

    # Then: the remote wins and the conflicting queued mutation remains available for retry or diagnosis
    assert current.content == "revision-two"
    assert remote["content"] == "revision-two"
    assert [mutation.write.content for mutation in cache.pending_mutations()] == ["queued"]
    artifact_provider.store_artifact_content.assert_not_called()


def test_github_plan_replay_coalesces_sequential_offline_writes(tmp_path: Path) -> None:
    # Given: an existing plan edited twice while the provider is offline
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="P42")
    initial = ContentRecord(reference=reference, content="original", revision="rev-1")
    cache.cache_content(initial)
    remote = initial
    writes: list[ContentWrite] = []

    def put(request: ContentWrite) -> ContentRecord:
        nonlocal remote
        if request.expected_revision != remote.revision:
            raise ContentConflictError("Content revision no longer matches")
        writes.append(request)
        remote = ContentRecord(reference=reference, content=request.content, revision=f"rev-{len(writes) + 1}")
        return remote

    plan_persistence = MagicMock()
    plan_persistence.put.side_effect = put
    plan_persistence.get.side_effect = lambda _reference: remote
    backend = GitHubBackend(cache=cache, plan_persistence=plan_persistence)
    backend.try_get_github = MagicMock(return_value=None)
    backend.put_content(ContentWrite(reference=reference, content="first", expected_revision="rev-1"))
    backend.put_content(ContentWrite(reference=reference, content="latest", expected_revision="rev-1"))
    backend.try_get_github = MagicMock(return_value=MagicMock())

    # When: the provider reconnects and replays its durable queue
    replayed = backend.get_content(reference)

    # Then: the latest edit applies once against the original provider revision
    assert [write.content for write in writes] == ["latest"]
    assert replayed.content == "latest"
    assert cache.pending_mutations() == []
