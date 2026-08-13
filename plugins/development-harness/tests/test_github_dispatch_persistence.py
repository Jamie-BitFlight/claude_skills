from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_provider import GitHubGistArtifactProvider, ItemId
from backlog_core.backends.github_backend import _GitHubDispatchPersistence
from backlog_core.models import (
    ArtifactManifest,
    ContentKind,
    ContentQuery,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)


class _RemoteGistProvider:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.before_next_store: _GitHubDispatchPersistence | None = None
        self.unavailable = False
        self.store_paths: list[str] = []

    def store_artifact_content(self, item_id: ItemId, artifact_type: str, path: str, content: str) -> None:
        self.store_paths.append(path)
        if self.before_next_store is not None:
            persistence = self.before_next_store
            self.before_next_store = None
            persistence.put(
                ContentWrite(
                    reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-2"),
                    owner_reference="#2",
                    content='{"milestone":2}',
                )
            )
        self.files[path.replace("/", "--")] = content

    def get_manifest(self, item_id: ItemId) -> ArtifactManifest:
        raise NotImplementedError

    def set_manifest(self, item_id: ItemId, manifest: ArtifactManifest) -> None:
        raise NotImplementedError

    def read_artifact_content(self, path: str) -> str:
        raise NotImplementedError

    def read_artifact_content_from_remote(self, item_id: ItemId, artifact_type: str, path: str) -> str | None:
        return self.files.get(path.replace("/", "--"))

    def read_local_artifact_content(self, path: str) -> str | None:
        raise NotImplementedError

    def list_artifact_content_from_remote(
        self, item_id: ItemId, artifact_type: str, path_prefix: str
    ) -> dict[str, str]:
        if self.unavailable:
            raise ContentUnavailableError("remote unavailable")
        filename_prefix = path_prefix.replace("/", "--")
        return {filename: content for filename, content in self.files.items() if filename.startswith(filename_prefix)}


def test_overlapping_dispatch_plan_inserts_remain_discoverable() -> None:
    provider = _RemoteGistProvider()
    first = _GitHubDispatchPersistence(provider)
    second = _GitHubDispatchPersistence(provider)
    provider.before_next_store = second

    first.put(
        ContentWrite(
            reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-1"),
            owner_reference="#1",
            content='{"milestone":1}',
        )
    )

    records = first.list(ContentQuery(kind=ContentKind.DISPATCH_PLAN))

    assert {(record.reference.name, record.owner_reference, record.content) for record in records} == {
        ("dispatch-milestone-1", "#1", '{"milestone":1}'),
        ("dispatch-milestone-2", "#2", '{"milestone":2}'),
    }
    assert "dispatch-plan/index.json" not in provider.store_paths


def test_legacy_shared_index_entries_remain_discoverable() -> None:
    provider = _RemoteGistProvider()
    provider.files["dispatch-plan--legacy.json"] = '{"milestone":9}'
    provider.files["dispatch-plan--index.json"] = '{"version":1,"entries":[{"name":"legacy","owner_reference":"#9"}]}'
    persistence = _GitHubDispatchPersistence(provider)

    record = persistence.get(ContentRef(kind=ContentKind.DISPATCH_PLAN, name="legacy"))

    assert (record.owner_reference, record.content) == ("#9", '{"milestone":9}')


def test_current_envelopes_do_not_hide_distinct_legacy_index_entries() -> None:
    provider = _RemoteGistProvider()
    provider.files["dispatch-plan--current.json"] = _GitHubDispatchPersistence._serialize_envelope(
        "current", "#1", '{"milestone":1}'
    )
    provider.files["dispatch-plan--legacy.json"] = '{"milestone":9}'
    provider.files["dispatch-plan--index.json"] = '{"version":1,"entries":[{"name":"legacy","owner_reference":"#9"}]}'
    persistence = _GitHubDispatchPersistence(provider)

    records = persistence.list(ContentQuery(kind=ContentKind.DISPATCH_PLAN))

    assert {(record.reference.name, record.owner_reference, record.content) for record in records} == {
        ("current", "#1", '{"milestone":1}'),
        ("legacy", "#9", '{"milestone":9}'),
    }


def test_dispatch_name_round_trips_when_gist_filename_is_lossy() -> None:
    provider = _RemoteGistProvider()
    persistence = _GitHubDispatchPersistence(provider)
    name = "dispatch/a--b"

    persistence.put(
        ContentWrite(
            reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name=name),
            owner_reference="#1",
            content='{"milestone":1}',
        )
    )

    record = persistence.get(ContentRef(kind=ContentKind.DISPATCH_PLAN, name=name))

    assert record.reference.name == name


def test_unavailable_dispatch_enumeration_does_not_write_an_empty_index() -> None:
    provider = _RemoteGistProvider()
    provider.unavailable = True
    persistence = _GitHubDispatchPersistence(provider)

    with pytest.raises(ContentUnavailableError, match="remote unavailable"):
        persistence.put(
            ContentWrite(
                reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-1"),
                content='{"milestone":1}',
            )
        )

    assert provider.store_paths == []


def test_github_gist_provider_lists_matching_gist_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    provider = GitHubGistArtifactProvider(repo="owner/repo", root_worktree=tmp_path)
    gist = MagicMock()
    gist.files = {
        "dispatch-plan--one.json": SimpleNamespace(content="one"),
        "dispatch-plan--two.json": SimpleNamespace(content="two"),
        "sam-plan--other.yaml": SimpleNamespace(content="other"),
    }
    monkeypatch.setattr(provider, "_get_gist", lambda item_id, body: gist)
    monkeypatch.setattr("backlog_core.artifact_provider.get_github", lambda repo: MagicMock())
    monkeypatch.setattr("backlog_core.artifact_provider._fetch_issue_graphql", lambda *args: {"body": ""})

    files = provider.list_artifact_content_from_remote(42, "dispatch-plan", "dispatch-plan/")

    assert files == {"dispatch-plan--one.json": "one", "dispatch-plan--two.json": "two"}
