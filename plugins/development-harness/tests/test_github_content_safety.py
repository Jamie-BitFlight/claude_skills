from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from backlog_core.backends.github_backend import GitHubBackend, _GitHubPlanPersistence
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ContentConflictError,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
    UnsupportedCapabilityError,
)


def _plan_persistence(current: ContentRecord | None) -> tuple[_GitHubPlanPersistence, MagicMock, MagicMock, MagicMock]:
    persistence = _GitHubPlanPersistence.__new__(_GitHubPlanPersistence)
    persistence._entries = MagicMock(return_value=[SimpleNamespace(plan_id=current.reference.name)] if current else [])
    persistence._record = MagicMock(return_value=current)
    persistence._provider = MagicMock()
    persistence._client = MagicMock()
    persistence._index = MagicMock()
    persistence._sentinel_issue = 1
    return persistence, persistence._provider, persistence._client, persistence._index


def test_plan_update_with_expected_revision_fails_closed_without_gist_mutation() -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    current = ContentRecord(reference=reference, content="before", revision="current")
    persistence, provider, client, index = _plan_persistence(current)

    with pytest.raises(ContentConflictError, match="revision"):
        persistence.put(ContentWrite(reference=reference, content="after", expected_revision="current"))

    provider.store_artifact_content.assert_not_called()
    client.store.assert_not_called()
    index.register.assert_not_called()


def test_plan_noop_with_expected_revision_does_not_mutate_gist() -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    current = ContentRecord(reference=reference, content="unchanged", revision="current")
    persistence, provider, client, index = _plan_persistence(current)

    record = persistence.put(ContentWrite(reference=reference, content="unchanged", expected_revision="stale"))

    assert record == current
    provider.store_artifact_content.assert_not_called()
    client.store.assert_not_called()
    index.register.assert_not_called()


def test_missing_plan_with_expected_revision_fails_closed() -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    persistence, provider, client, index = _plan_persistence(None)

    with pytest.raises(ContentConflictError, match="revision"):
        persistence.put(ContentWrite(reference=reference, content="new", expected_revision="prior"))

    provider.store_artifact_content.assert_not_called()
    client.store.assert_not_called()
    index.register.assert_not_called()


def test_plan_creation_fails_closed_without_gist_mutation() -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    persistence, provider, client, index = _plan_persistence(None)

    with pytest.raises(UnsupportedCapabilityError):
        persistence.put(ContentWrite(reference=reference, content="new"))

    provider.store_artifact_content.assert_not_called()
    client.store.assert_not_called()
    index.register.assert_not_called()


def test_revisionless_plan_update_fails_closed_without_gist_mutation() -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    current = ContentRecord(reference=reference, content="before", revision="current")
    persistence, provider, client, index = _plan_persistence(current)

    with pytest.raises(UnsupportedCapabilityError):
        persistence.put(ContentWrite(reference=reference, content="after"))

    provider.store_artifact_content.assert_not_called()
    client.store.assert_not_called()
    index.register.assert_not_called()


class _UnavailablePlanPersistence:
    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        raise OSError("GitHub unavailable")

    def get(self, reference: ContentRef) -> ContentRecord:
        raise OSError("GitHub unavailable")

    def put(self, request: ContentWrite) -> ContentRecord:
        raise OSError("GitHub unavailable")


def _offline_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[GitHubBackend, ContentRef, ContentRecord]:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    cached = ContentRecord(reference=reference, content="cached", revision="current")
    cache = FileCache(tmp_path / "github-cache")
    cache.cache_content(cached)
    cache.queue_write(cached, ContentWrite(reference=reference, content="pending", expected_revision="current"))
    backend = GitHubBackend(cache=cache, plan_persistence=_UnavailablePlanPersistence())
    monkeypatch.setattr(backend, "try_get_github", MagicMock)
    return backend, reference, cached


def test_replay_oserror_keeps_pending_mutation_and_list_returns_stale_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, reference, _ = _offline_backend(tmp_path, monkeypatch)

    records = backend.list_content(ContentQuery(kind=ContentKind.PLAN))

    assert [(record.reference, record.content, record.stale) for record in records] == [(reference, "pending", True)]
    assert len(backend._cache.pending_mutations()) == 1


def test_replay_oserror_keeps_pending_mutation_and_get_returns_stale_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, reference, _ = _offline_backend(tmp_path, monkeypatch)

    record = backend.get_content(reference)

    assert (record.content, record.stale) == ("pending", True)
    assert len(backend._cache.pending_mutations()) == 1


def test_replay_oserror_keeps_pending_mutation_and_put_queues_latest_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, reference, _ = _offline_backend(tmp_path, monkeypatch)

    record = backend.put_content(ContentWrite(reference=reference, content="latest", expected_revision="current"))

    assert (record.content, record.pending) == ("latest", True)
    pending = backend._cache.pending_mutations()
    assert len(pending) == 1
    assert pending[0].write.content == "latest"


def test_replay_conflict_keeps_pending_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    cached = ContentRecord(reference=reference, content="cached", revision="current")
    cache = FileCache(tmp_path / "github-cache")
    cache.cache_content(cached)
    cache.queue_write(cached, ContentWrite(reference=reference, content="pending", expected_revision="current"))
    backend = GitHubBackend(cache=cache, plan_persistence=_UnavailablePlanPersistence())
    monkeypatch.setattr(backend, "try_get_github", MagicMock)
    monkeypatch.setattr(
        backend,
        "_write_online_content",
        lambda request, cached: (_ for _ in ()).throw(ContentConflictError("conflict")),
    )

    backend._replay_pending_content()

    assert len(backend._cache.pending_mutations()) == 1
