from __future__ import annotations

from base64 import b64encode
from pathlib import Path
from types import SimpleNamespace
from typing import TypeAlias
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_manifest_store import publish_artifact
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.github_contents import _GitHubContentsStore
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


class _Repository:
    def __init__(self) -> None:
        self.default_branch = "main"
        self.files: dict[str, _File] = {}
        self.create_race = False
        self.conflict_update = False
        self.branch_contention = 0
        self.tree_truncated = False
        self.branches: list[str] = []
        self.foreign_revision = 0
        self.mutate_after_tree = False
        self.advance_after_write = False
        self._blobs: dict[str, str] = {}
        self._next_sha = 0

    def get_contents(self, path: str, ref: str) -> _File:
        self.branches.append(ref)
        try:
            return self.files[path]
        except KeyError as exc:
            raise GithubException(404, {"message": "Not Found"}, {}) from exc

    def create_file(self, path: str, message: str, content: str, branch: str) -> dict[str, object]:
        self.branches.append(branch)
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
        snapshot = dict(self.files.items())
        self._blobs = {file.sha: file.content for file in snapshot.values()}
        if self.mutate_after_tree:
            path, file = next(iter(self.files.items()))
            self.files[path] = _File(content=file.content.replace("body", "moved"), sha="sha-moved")
        return _Tree(
            tree=[_TreeEntry(path=path, sha=file.sha) for path, file in snapshot.items()], truncated=self.tree_truncated
        )

    def get_git_blob(self, sha: str) -> SimpleNamespace:
        return SimpleNamespace(content=b64encode(self._blobs[sha].encode()).decode())

    def _sha(self) -> str:
        self._next_sha += 1
        return f"sha-{self._next_sha}"


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
    assert set(repository.branches) == {"main"}


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
    repository.get_git_blob = MagicMock(return_value=SimpleNamespace(content="not-base64!"))

    with pytest.raises(ContentUnavailableError, match="envelope"):
        store.list(ContentQuery(kind=ContentKind.PLAN))


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


def test_two_plans_for_one_owner_remain_distinct(store: _GitHubContentsStore) -> None:
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), owner_reference="#1", content="one"))
    store.put(ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P2"), owner_reference="#1", content="two"))

    records = store.list(ContentQuery(kind=ContentKind.PLAN, owner_reference="#1"))

    assert [(record.reference.name, record.content) for record in records] == [("P1", "one"), ("P2", "two")]


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
