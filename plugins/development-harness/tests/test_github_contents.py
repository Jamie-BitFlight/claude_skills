from __future__ import annotations

from pathlib import Path
from typing import TypeAlias
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_manifest_store import publish_artifact
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.github_contents import _CONTENT_BRANCH, _GitHubContentsStore
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ArtifactEntry,
    ArtifactManifest,
    ArtifactType,
    ContentConflictError,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    UnsupportedCapabilityError,
)
from github import GithubException
from pydantic import BaseModel

ContentRecords: TypeAlias = list[ContentRecord]


class _File(BaseModel):
    content: str
    sha: str

    @property
    def decoded_content(self) -> bytes:
        return self.content.encode()


class _TreeEntry(BaseModel):
    path: str
    sha: str
    type: str = "blob"


class _Tree(BaseModel):
    tree: list[_TreeEntry]
    truncated: bool = False


class _FakeRequester:
    """Simulates PyGithub's requester.graphql_query for the aliased blob-batch query.

    Only understands the shape _fetch_blobs_graphql actually sends ($sha0,
    $sha1, ... variables aliased b0, b1, ...) -- not a general GraphQL engine.
    """

    def __init__(self, repository: _Repository) -> None:
        self._repository = repository
        self.call_count = 0
        self.override: dict[str, object] | None = None

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        self.call_count += 1
        if self.override is not None:
            return {}, self.override
        sha_keys = sorted((key for key in variables if key.startswith("sha")), key=lambda key: int(key[3:]))
        repository_data: dict[str, object] = {}
        for index, key in enumerate(sha_keys):
            sha = str(variables[key])
            self._repository.blob_requests.append(sha)
            content = self._repository._blobs.get(sha)
            repository_data[f"b{index}"] = None if content is None else {"text": content, "isBinary": False}
        return {}, {"data": {"repository": repository_data}}


class _Repository:
    def __init__(self) -> None:
        self.default_branch = "main"
        self.full_name = "owner/repo"
        self.files: dict[str, _File] = {}
        self.create_race = False
        self.conflict_update = False
        self.branch_contention = 0
        self.tree_truncated = False
        self.branches: list[str] = []
        self.foreign_revision = 0
        self.mutate_after_tree = False
        self.advance_after_write = False
        self.blob_requests: list[str] = []
        self._blobs: dict[str, str] = {}
        self._next_sha = 0
        self.requester = _FakeRequester(self)
        self.existing_branches: set[str] = {"main"}
        self.branch_create_conflict = False
        self.branch_create_false_conflict = False
        self.branch_create_false_conflict_status = 422
        self.branch_lookup_calls: list[str] = []
        self.tree_shas: list[str] = []

    def _require_branch(self, branch: str) -> None:
        """Reject an operation against a branch this fake never created.

        Mirrors real GitHub: content and tree operations against a
        nonexistent ref fail. Without this check, the fake accepted content
        operations against any branch string regardless of
        ``existing_branches``, which would mask a false-positive
        ``_GitHubContentsStore._branch_ready`` bootstrap (see
        ``test_content_branch_creation_false_conflict_fails_closed``).
        """
        if branch not in self.existing_branches:
            raise GithubException(404, {"message": f"Branch not found: {branch}"}, {})

    def get_contents(self, path: str, ref: str) -> _File:
        self.branches.append(ref)
        self._require_branch(ref)
        try:
            return self.files[path]
        except KeyError as exc:
            raise GithubException(404, {"message": "Not Found"}, {}) from exc

    def create_file(self, path: str, message: str, content: str, branch: str) -> dict[str, object]:
        self.branches.append(branch)
        self._require_branch(branch)
        if self.branch_contention:
            self.branch_contention -= 1
            raise GithubException(409, {"message": "branch moved"}, {})
        if self.create_race:
            self.create_race = False
            self.files[path] = _File(
                content='{"version":1,"reference":{"kind":"plan","namespace":"","artifact_type":"","name":"P1"},"owner_reference":"","content":"foreign"}',
                sha="sha-other",
            )
            raise GithubException(422, {"message": "already exists"}, {})
        if path in self.files:
            raise GithubException(422, {"message": "already exists"}, {})
        written = _File(content=content, sha=self._sha())
        self.files[path] = written
        if self.advance_after_write:
            self.files[path] = _File(content=content.replace("first", "second"), sha=self._sha())
        return {"content": written}

    def update_file(self, path: str, message: str, content: str, sha: str, branch: str) -> dict[str, object]:
        self.branches.append(branch)
        self._require_branch(branch)
        if self.branch_contention:
            self.branch_contention -= 1
            raise GithubException(409, {"message": "branch moved"}, {})
        if self.conflict_update:
            self.foreign_revision += 1
            self.files[path] = _File(content=self.files[path].content, sha=f"sha-other-{self.foreign_revision}")
            raise GithubException(409, {"message": "conflict"}, {})
        if self.files[path].sha != sha:
            raise GithubException(409, {"message": "conflict"}, {})
        written = _File(content=content, sha=self._sha())
        self.files[path] = written
        if self.advance_after_write:
            self.files[path] = _File(content=content.replace("first", "second"), sha=self._sha())
        return {"content": written}

    def get_git_tree(self, sha: str, recursive: bool) -> _Tree:
        self.tree_shas.append(sha)
        self._require_branch(sha)
        snapshot = dict(self.files.items())
        self._blobs = {file.sha: file.content for file in snapshot.values()}
        if self.mutate_after_tree:
            path, file = next(iter(self.files.items()))
            self.files[path] = _File(content=file.content.replace("body", "moved"), sha="sha-moved")
        return _Tree(
            tree=[_TreeEntry(path=path, sha=file.sha) for path, file in snapshot.items()], truncated=self.tree_truncated
        )

    def _sha(self) -> str:
        self._next_sha += 1
        return f"sha-{self._next_sha}"

    def get_branch(self, branch: str) -> _FakeBranch:
        self.branch_lookup_calls.append(branch)
        if branch not in self.existing_branches:
            raise GithubException(404, {"message": "Branch not found"}, {})
        return _FakeBranch(commit=_FakeCommit(sha="base-sha"))

    def create_git_ref(self, ref: str, sha: str) -> None:
        name = ref.removeprefix("refs/heads/")
        if self.branch_create_false_conflict:
            # A conflict status that does NOT correspond to a real,
            # pre-existing branch -- e.g. a transient ref-lock, a
            # secondary-rate-limit response surfaced as 422, or an
            # undocumented 409. The branch is deliberately left absent from
            # existing_branches so re-verification (Finding 1 fix) fails.
            raise GithubException(self.branch_create_false_conflict_status, {"message": "conflict"}, {})
        if self.branch_create_conflict:
            # Simulates a concurrent bootstrapper winning the race: the
            # branch genuinely exists by the time we ask, even though our
            # own create_git_ref call still reports 422.
            self.existing_branches.add(name)
            raise GithubException(422, {"message": "Reference already exists"}, {})
        self.existing_branches.add(name)


class _FakeCommit(BaseModel):
    sha: str


class _FakeBranch(BaseModel):
    commit: _FakeCommit


class _PagedContent:
    def __init__(self, records: ContentRecords) -> None:
        self.records = records

    def list(self, query: ContentQuery) -> ContentRecords:
        return self.records[query.offset : query.offset + query.limit]

    def get(self, reference: ContentRef) -> ContentRecord:
        raise NotImplementedError

    def put(self, request: ContentWrite) -> ContentRecord:
        raise NotImplementedError


@pytest.fixture
def repository() -> _Repository:
    return _Repository()


@pytest.fixture
def store(repository: _Repository) -> _GitHubContentsStore:
    return _GitHubContentsStore(lambda: repository)


def test_round_trip_uses_compact_lossless_envelope(store: _GitHubContentsStore, repository: _Repository) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P/one%two")

    created = store.put(ContentWrite(reference=reference, owner_reference="#7", content="body"))

    assert created.revision == "sha-1"
    path, stored = next(iter(repository.files.items()))
    assert path.startswith(".dh/content/v1/")
    assert (
        stored.content
        == '{"version":1,"reference":{"kind":"plan","namespace":"","artifact_type":"","name":"P/one%two"},"owner_reference":"#7","content":"body"}'
    )
    assert store.get(reference) == created
    assert set(repository.branches) == {_CONTENT_BRANCH}


def test_stale_update_raises_conflict(store: _GitHubContentsStore, repository: _Repository) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    store.put(ContentWrite(reference=reference, content="before"))
    repository.conflict_update = True

    with pytest.raises(ContentConflictError):
        store.put(ContentWrite(reference=reference, content="after", expected_revision="sha-1"))


def test_create_race_raises_conflict(store: _GitHubContentsStore, repository: _Repository) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    repository.create_race = True

    with pytest.raises(ContentConflictError):
        store.put(ContentWrite(reference=reference, content="body", create_only=True))


def test_create_only_conflicts_even_when_content_is_identical(store: _GitHubContentsStore) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    store.put(ContentWrite(reference=reference, content="body"))

    with pytest.raises(ContentConflictError):
        store.put(ContentWrite(reference=reference, content="body", create_only=True))


def test_branch_head_contention_retries_when_target_is_unchanged(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    repository.branch_contention = 1

    record = store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))

    assert record.content == "body"


def test_success_returns_exact_written_blob_when_path_advances(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    repository.advance_after_write = True

    written = store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="first"))

    assert (written.content, written.revision) == ("first", "sha-1")
    assert next(iter(repository.files.values())).sha == "sha-2"


def test_paths_remain_distinct_for_ambiguous_characters(store: _GitHubContentsStore, repository: _Repository) -> None:
    names = ["a/b", "a--b", "%2F", "☃"]
    for name in names:
        store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name=name), content=name))

    assert [record.reference.name for record in store.list(ContentQuery(kind=ContentKind.PLAN))] == sorted(names)


def test_truncated_tree_fails_closed(store: _GitHubContentsStore, repository: _Repository) -> None:
    repository.tree_truncated = True

    with pytest.raises(ContentUnavailableError, match="truncated"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


def test_list_reads_one_resolved_tree_snapshot(store: _GitHubContentsStore, repository: _Repository) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    repository.mutate_after_tree = True

    records = store.list(ContentQuery(kind=ContentKind.PLAN))

    assert [(record.content, record.revision) for record in records] == [("body", "sha-1")]


def test_contents_api_size_limit_fails_closed(store: _GitHubContentsStore) -> None:
    with pytest.raises(ContentUnavailableError, match="1 MB"):
        store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="x" * 1_000_000))


def test_malformed_native_content_does_not_fall_back_to_legacy(
    tmp_path: Path, store: _GitHubContentsStore, repository: _Repository
) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    repository.files[store._path(reference)] = _File(content="not-json", sha="sha-malformed")
    legacy = MagicMock()
    cache = FileCache(tmp_path)
    cache.cache_content(ContentRecord(reference=reference, content="cached"))
    backend = GitHubBackend(cache=cache, artifact_provider=MagicMock(), plan_persistence=legacy, contents=store)
    backend._cache.cache_content = MagicMock()
    backend.try_get_github = MagicMock(return_value=MagicMock())

    with pytest.raises(ContentUnavailableError, match="envelope"):
        store.get(reference)
    with pytest.raises(ContentUnavailableError):
        backend.get_content(reference)
    with pytest.raises(ContentUnavailableError):
        backend.list_content(ContentQuery(kind=ContentKind.PLAN))
    legacy.get.assert_not_called()


def test_malformed_native_blob_fails_closed(store: _GitHubContentsStore, repository: _Repository) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    repository.requester.override = {"data": {"repository": {"b0": {"text": "not-json", "isBinary": False}}}}

    with pytest.raises(ContentUnavailableError, match="envelope"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


def test_binary_native_blob_fails_closed(store: _GitHubContentsStore, repository: _Repository) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    repository.requester.override = {"data": {"repository": {"b0": {"text": None, "isBinary": True}}}}

    with pytest.raises(ContentUnavailableError, match="invalid or missing"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


def test_missing_native_blob_fails_closed(store: _GitHubContentsStore, repository: _Repository) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    repository.requester.override = {"data": {"repository": {"b0": None}}}

    with pytest.raises(ContentUnavailableError, match="invalid or missing"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


def test_blob_batch_graphql_transport_failure_fails_closed(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    repository.requester.override = {"errors": [{"message": "rate limited"}]}

    with pytest.raises(ContentUnavailableError, match="discovery failed"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


def test_get_many_fetches_only_requested_blobs(store: _GitHubContentsStore, repository: _Repository) -> None:
    requested = ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="_dh-work-item-head-v1", name="head"
    )
    unrelated = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="report", name="report")
    store.put(ContentWrite(reference=requested, content="head"))
    store.put(ContentWrite(reference=unrelated, content="artifact"))

    [record] = store.get_many([requested])

    assert record.reference == requested
    assert repository.blob_requests == ["sha-1"]


def test_backend_hides_private_work_item_heads_from_artifact_listing(
    tmp_path: Path, store: _GitHubContentsStore
) -> None:
    head = ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="_dh-work-item-head-v1", name="head"
    )
    artifact = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="test", name="report")
    store.put(ContentWrite(reference=head, content="private"))
    store.put(ContentWrite(reference=artifact, content="public"))
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=MagicMock(), contents=store)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    records = backend.list_content(ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, owner_reference="#1"))

    assert [(record.reference, record.content) for record in records] == [(artifact, "public")]

    with pytest.raises(UnsupportedCapabilityError, match="provider-private"):
        backend.get_content(head)
    with pytest.raises(UnsupportedCapabilityError, match="provider-private"):
        backend.put_content(ContentWrite(reference=head, content="replacement"))

    backend._cache.cache_content(ContentRecord(reference=head, content="private"))
    backend.try_get_github = MagicMock(return_value=None)
    records = backend.list_content(ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, owner_reference="#1"))

    assert [(record.reference, record.content) for record in records] == [(artifact, "public")]


def test_two_plans_for_one_owner_remain_distinct(store: _GitHubContentsStore) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), owner_reference="#1", content="one"))
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P2"), owner_reference="#1", content="two"))

    records = store.list(ContentQuery(kind=ContentKind.PLAN, owner_reference="#1"))

    assert [(record.reference.name, record.content) for record in records] == [("P1", "one"), ("P2", "two")]


def test_content_branch_is_bootstrapped_from_default_branch_when_missing(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    assert _CONTENT_BRANCH not in repository.existing_branches

    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))

    assert _CONTENT_BRANCH in repository.existing_branches
    assert repository.branch_lookup_calls == [_CONTENT_BRANCH, "main"]
    assert set(repository.branches) == {_CONTENT_BRANCH}


def test_content_branch_creation_race_is_idempotent(store: _GitHubContentsStore, repository: _Repository) -> None:
    # Simulates a concurrent bootstrapper winning the create-branch race: our
    # lookup observes the branch missing, but by the time we attempt to
    # create it, GitHub already has it (422 "Reference already exists").
    repository.branch_create_conflict = True

    record = store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))

    assert record.content == "body"
    assert set(repository.branches) == {_CONTENT_BRANCH}


def test_content_branch_creation_false_conflict_fails_closed(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    """A 422 from create_git_ref that is NOT a genuine 'already exists' --
    e.g. a transient ref-lock or a secondary-rate-limit response surfaced as
    422 -- must not be silently accepted as 'branch is ready'. Regression
    guard for Finding 1: pre-fix, _content_branch fell through to
    self._branch_ready = True without verifying the branch actually exists.
    """
    repository.branch_create_false_conflict = True

    with pytest.raises(ContentUnavailableError, match="branch"):
        store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))

    assert _CONTENT_BRANCH not in repository.existing_branches


def test_content_branch_creation_undocumented_conflict_status_fails_closed(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    """create_git_ref's documented 'already exists' status is 422, not 409.

    A 409 must surface as an error rather than being tolerated as a
    successful race -- regression guard for the _CONFLICT_STATUSES /
    _REF_ALREADY_EXISTS conflation fixed for Finding 3 (create_git_ref's
    'ref already exists' now has a distinct constant from the content-write
    conflict statuses).
    """
    repository.branch_create_false_conflict = True
    repository.branch_create_false_conflict_status = 409

    with pytest.raises(ContentUnavailableError, match="branch"):
        store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))


def test_fake_repository_rejects_content_ops_against_unbootstrapped_branch(repository: _Repository) -> None:
    """Regression guard for the test double itself (Finding 2): if
    _content_branch ever again marked _branch_ready=True without the branch
    actually existing, the fake must fail the same way real GitHub would --
    not silently accept content operations against a nonexistent ref.
    """
    assert _CONTENT_BRANCH not in repository.existing_branches

    with pytest.raises(GithubException):
        repository.get_contents("any/path", ref=_CONTENT_BRANCH)


def test_store_never_targets_the_repository_default_branch_for_content(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    repository.default_branch = "totally-different-default"
    repository.existing_branches = {"totally-different-default"}

    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="body"))
    store.list(ContentQuery(kind=ContentKind.PLAN))

    assert "totally-different-default" not in repository.branches
    assert "totally-different-default" not in repository.tree_shas
    assert set(repository.branches) == {_CONTENT_BRANCH}
    assert set(repository.tree_shas) == {_CONTENT_BRANCH}


def test_publish_keeps_body_when_manifest_update_conflicts(
    store: _GitHubContentsStore, repository: _Repository
) -> None:
    manifest = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="#1", name="manifest")
    entry = ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="report.md")
    store.put(ContentWrite(reference=manifest, content=ArtifactManifest(issue_number="#1").model_dump_json()))
    repository.conflict_update = True

    with pytest.raises(ContentConflictError):
        publish_artifact(store, manifest, "#1", entry, "body")

    assert any('"content":"body"' in file.content for file in repository.files.values())


def test_dispatch_create_update_and_list_preserve_exact_identity(store: _GitHubContentsStore) -> None:
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch/a--b")
    created = store.put(ContentWrite(reference=reference, owner_reference="#1", content="before"))
    updated = store.put(
        ContentWrite(reference=reference, owner_reference="#1", content="after", expected_revision=created.revision)
    )

    assert updated.revision == "sha-2"
    assert [
        (record.reference.name, record.content) for record in store.list(ContentQuery(kind=ContentKind.DISPATCH_PLAN))
    ] == [("dispatch/a--b", "after")]


def test_backend_prefers_v1_content_and_falls_back_to_legacy(tmp_path: Path, store: _GitHubContentsStore) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    legacy = MagicMock()
    legacy_record = store.put(ContentWrite(reference=reference, content="current"))
    legacy.get.return_value = legacy_record.model_copy(update={"content": "legacy"})
    backend = GitHubBackend(
        cache=FileCache(tmp_path), artifact_provider=MagicMock(), plan_persistence=legacy, contents=store
    )
    backend.try_get_github = MagicMock(return_value=MagicMock())

    assert backend.get_content(reference).content == "current"
    legacy.get.assert_not_called()

    missing = ContentRef(kind=ContentKind.PLAN, name="P2")
    assert backend.get_content(missing).content == "legacy"
    legacy.get.assert_called_once_with(missing)


def test_backend_migrates_validated_legacy_revision_on_first_write(tmp_path: Path, store: _GitHubContentsStore) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    legacy = MagicMock()
    legacy.get.return_value = ContentRecord(
        reference=reference, owner_reference="#7", content="legacy", revision="legacy-revision"
    )
    backend = GitHubBackend(cache=FileCache(tmp_path), plan_persistence=legacy, contents=store)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    migrated = backend.put_content(
        ContentWrite(reference=reference, content="native", expected_revision="legacy-revision")
    )

    assert (migrated.content, migrated.owner_reference, store.get(reference).content) == ("native", "#7", "native")

    missing = ContentRef(kind=ContentKind.PLAN, name="P2")
    legacy.get.return_value = ContentRecord(reference=missing, content="legacy", revision="current")
    with pytest.raises(ContentConflictError):
        backend.put_content(ContentWrite(reference=missing, content="native", expected_revision="stale"))

    with pytest.raises(ContentConflictError, match="already exists"):
        backend.put_content(ContentWrite(reference=missing, content="replacement", create_only=True))


def test_backend_native_pagination_fetches_each_blob_once(
    tmp_path: Path, store: _GitHubContentsStore, repository: _Repository
) -> None:
    for number in range(101):
        store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name=f"P{number:03}"), content="body"))
    backend = GitHubBackend(cache=FileCache(tmp_path), plan_persistence=MagicMock(), contents=store)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN, offset=100, limit=1))

    assert [record.reference.name for record in records] == ["P100"]
    assert len(repository.blob_requests) == 101
    # Regression guard for the N+1 fix: 101 blobs must reach the server as 5
    # batched GraphQL requests (ceil(101/_BLOB_BATCH_SIZE)=ceil(101/25)), not
    # 101 individual round trips.
    assert repository.requester.call_count == 5


def test_backend_lists_native_content_when_legacy_migration_is_unavailable(
    tmp_path: Path, store: _GitHubContentsStore
) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    store.put(ContentWrite(reference=reference, content="current"))
    legacy = MagicMock()
    legacy.list.side_effect = OSError("legacy unavailable")
    backend = GitHubBackend(
        cache=FileCache(tmp_path), artifact_provider=MagicMock(), plan_persistence=legacy, contents=store
    )
    backend.try_get_github = MagicMock(return_value=MagicMock())

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN))

    assert [(record.reference, record.content, record.stale) for record in records] == [(reference, "current", False)]


def _records(start: int, stop: int, content_prefix: str) -> list[ContentRecord]:
    return [
        ContentRecord(
            reference=ContentRef(kind=ContentKind.PLAN, name=f"P{number:03}"), content=f"{content_prefix}{number}"
        )
        for number in range(start, stop)
    ]


def _paged_backend(tmp_path: Path, native: list[ContentRecord], legacy: list[ContentRecord]) -> GitHubBackend:
    backend = GitHubBackend(
        cache=FileCache(tmp_path),
        artifact_provider=MagicMock(),
        plan_persistence=_PagedContent(legacy),
        contents=_PagedContent(native),
    )
    backend._cache.cache_content = MagicMock()
    backend.try_get_github = MagicMock(return_value=MagicMock())
    return backend


def test_backend_lists_native_records_past_the_first_page(tmp_path: Path) -> None:
    backend = _paged_backend(tmp_path, _records(0, 101, "native-"), [])

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN, offset=100, limit=1))

    assert [(record.reference.name, record.content) for record in records] == [("P100", "native-100")]


def test_backend_lists_legacy_records_past_the_first_page(tmp_path: Path) -> None:
    backend = _paged_backend(tmp_path, [], _records(0, 101, "legacy-"))

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN, offset=100, limit=1))

    assert [(record.reference.name, record.content) for record in records] == [("P100", "legacy-100")]


def test_backend_merges_native_first_before_applying_offset(tmp_path: Path) -> None:
    native = _records(0, 101, "native-")
    legacy = [*_records(100, 101, "legacy-"), *_records(101, 201, "legacy-")]
    backend = _paged_backend(tmp_path, native, legacy)

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN, offset=100, limit=2))

    assert [(record.reference.name, record.content) for record in records] == [
        ("P100", "native-100"),
        ("P101", "legacy-101"),
    ]
