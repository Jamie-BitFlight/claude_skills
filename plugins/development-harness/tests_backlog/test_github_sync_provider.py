from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ArtifactManifest,
    BacklogError,
    BacklogItem,
    ContentKind,
    ContentQuery,
    ContentRef,
    ContentWrite,
    ProviderPatch,
    ReconcileRequest,
    ReconcileScope,
)
from sam_schema.core.plan_id_index import PlanIndexEntry, _serialize_index_yaml


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


def test_github_sync_provider_batches_preflight_and_mutations_without_per_item_fetches() -> None:
    # Given: 26 body patches whose current provider revisions match
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issue_graphql = MagicMock()
    backend._fetch_issues_graphql = MagicMock()
    backend._graphql_request = MagicMock(
        return_value={"repository": {f"i{index}": _issue(index + 1) for index in range(26)}}
    )
    backend._update_issues_graphql_batch = MagicMock()
    patches = [
        ProviderPatch(provider_id=f"node-{number}", reference=f"#{number}", expected_revision="rev-1", body="updated")
        for number in range(1, 27)
    ]

    # When: the adapter preflights then applies every patch
    results = backend._apply_patches(patches)

    # Then: targeted aliases avoid N+1 reads and body mutations never exceed GitHub's 25-item batch limit
    assert [result.status for result in results] == ["applied"] * 26
    assert [len(call.args[1]) for call in backend._update_issues_graphql_batch.call_args_list] == [25, 1]
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
    assert result.file_paths["#1"].endswith("issues/1.yaml")
    assert not hasattr(backend, "fetch_snapshot")
    assert not hasattr(backend, "apply_patches")
    assert cache._load_item_snapshot(Path("issues/1.yaml")).metadata.sync_fingerprint


def test_github_content_provider_preserves_plan_identity_while_reassigning_owner(tmp_path: Path) -> None:
    # Given: a reachable provider and one stable logical plan identity
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

    # When: the plan is created, preserved, reassigned, then unlinked
    created = backend.put_content(ContentWrite(reference=reference, content="v1", owner_reference="#1"))
    preserved = backend.put_content(ContentWrite(reference=reference, content="v2", expected_revision=created.revision))
    reassigned = backend.put_content(
        ContentWrite(reference=reference, content="v3", owner_reference="#2", expected_revision=preserved.revision)
    )
    unlinked = backend.put_content(
        ContentWrite(reference=reference, content="v4", owner_reference="", expected_revision=reassigned.revision)
    )

    # Then: ownership changes without changing the plan's kind/name identity
    assert [
        created.owner_reference,
        preserved.owner_reference,
        reassigned.owner_reference,
        unlinked.owner_reference,
    ] == ["#1", "#1", "#2", ""]
    assert unlinked.reference == reference
    assert remote_content[2531, "plan", "sam-plan/unlinked/P1.yaml"] == "v4"


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
