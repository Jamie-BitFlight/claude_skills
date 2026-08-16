from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from backlog_core.backends.github_backend import GitHubBackend, _GitHubPlanPersistence
from backlog_core.backends.github_contents import _GitHubContentIntegrityError
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ArtifactManifest,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
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


def test_online_artifact_content_write_routes_to_contents_before_gist_store(tmp_path: Path) -> None:
    reference = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="research", name="note")
    provider = MagicMock()
    contents = MagicMock()
    contents.put.return_value = ContentRecord(reference=reference, content="after", revision="sha")
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=provider, contents=contents)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    assert backend.put_content(ContentWrite(reference=reference, content="after")).revision == "sha"

    contents.put.assert_called_once()
    provider.store_artifact_content.assert_not_called()
    provider.set_manifest.assert_not_called()


def test_online_artifact_manifest_write_routes_to_contents_before_gist_store(tmp_path: Path) -> None:
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="#1", name="manifest")
    provider = MagicMock()
    contents = MagicMock()
    contents.put.return_value = ContentRecord(reference=reference, content="{}", revision="sha")
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=provider, contents=contents)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    backend.put_content(
        ContentWrite(
            reference=reference, content=ArtifactManifest(issue_number=1, last_updated="new").model_dump_json()
        )
    )

    contents.put.assert_called_once()
    provider.store_artifact_content.assert_not_called()
    provider.set_manifest.assert_not_called()


def test_online_artifact_read_remains_available(tmp_path: Path) -> None:
    reference = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="#1", artifact_type="research", name="note")
    provider = MagicMock()
    contents = MagicMock()
    contents.get.return_value = ContentRecord(reference=reference, content="stored", revision="sha")
    backend = GitHubBackend(cache=FileCache(tmp_path), artifact_provider=provider, contents=contents)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    record = backend.get_content(reference)

    assert (record.content, record.pending, record.stale) == ("stored", False, False)
    contents.get.assert_called_once_with(reference)
    provider.store_artifact_content.assert_not_called()


def test_pending_artifact_manifest_write_is_not_clobbered_by_empty_legacy_read(tmp_path: Path) -> None:
    """A queued manifest write that cannot land yet must stay visible to readers.

    Regression test for backlog item #2899: ``artifact_register`` reported
    success but the artifact was invisible to ``artifact_list``/``artifact_get``
    immediately after. Root cause -- ``GitHubGistArtifactProvider.get_manifest``
    (the legacy fallback ``read_legacy`` uses for ``ARTIFACT_MANIFEST``) never
    raises ``ContentNotFoundError`` for an item with no manifest data yet; it
    returns a valid, empty manifest instead. Before the fix, ``get_content``
    trusted that empty read as authoritative and cached it over the top of the
    still-pending queued write (e.g. one blocked by a branch-protection ruleset
    that rejects direct Contents API commits), erasing the just-registered
    artifact from view.
    """
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="1", name="manifest")
    base = ContentRecord(reference=reference, content="", revision="")
    manifest_with_entry = '{"issue_number":1,"artifacts":[{"artifact_type":"feature-context","artifact_id":"x.md"}]}'
    cache = FileCache(tmp_path / "github-cache")
    cache.queue_write(base, ContentWrite(reference=reference, content=manifest_with_entry, create_only=True))

    contents = MagicMock()
    contents.get.side_effect = ContentNotFoundError("not in contents api")
    provider = MagicMock()
    provider.get_manifest.return_value = ArtifactManifest(issue_number=1)
    backend = GitHubBackend(cache=cache, artifact_provider=provider, contents=contents)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    record = backend.get_content(reference)

    assert (record.content, record.pending) == (manifest_with_entry, True)
    provider.get_manifest.assert_called()
    assert len(backend._cache.pending_mutations()) == 1


def test_pending_write_still_surfaces_integrity_error_on_underlying_reference(tmp_path: Path) -> None:
    """A stuck pending write must not mask a genuine remote integrity error.

    Regression test for a visibility gap introduced by the pending-guard fix
    above: routing straight to the stale cache once ``cached.pending`` is
    True skips ``_read_online_content`` entirely, so a real
    ``_GitHubContentIntegrityError`` on that same reference (e.g. a truncated
    or malformed Contents API blob) never runs and is silently withheld from
    every ``get_content`` caller for as long as the write stays stuck.
    """
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="1", name="manifest")
    base = ContentRecord(reference=reference, content="", revision="")
    cache = FileCache(tmp_path / "github-cache")
    cache.queue_write(base, ContentWrite(reference=reference, content="queued", create_only=True))

    contents = MagicMock()
    contents.get.side_effect = _GitHubContentIntegrityError("corrupt blob")
    provider = MagicMock()
    provider.get_manifest.return_value = ArtifactManifest(issue_number=1)
    backend = GitHubBackend(cache=cache, artifact_provider=provider, contents=contents)
    backend.try_get_github = MagicMock(return_value=MagicMock())

    with pytest.raises(_GitHubContentIntegrityError):
        backend.get_content(reference)


def test_fresh_online_write_discards_stale_pending_mutation_for_same_reference(tmp_path: Path) -> None:
    """A landed direct write must dequeue any stale pending write for its reference.

    Regression test: ``put_content``'s online-write success path previously
    never touched ``state.pending``, so a queued create-only write that lost
    its first replay attempt (e.g. against a legacy record) stayed queued
    forever. Using a persistence double that -- unlike the real
    ``_GitHubContentsStore`` -- performs no create-only/revision
    self-validation on ``put`` isolates the offline-mutation-cache contract
    itself: on the *next* replay this stale write would silently land and
    clobber content that a fresh, unconditional write had already
    superseded, unless the cache dequeues it as soon as that fresh write
    lands.
    """

    class _NaiveContentsStore:
        """Minimal, non-validating ``_ContentPersistence`` double.

        The `_ContentPersistence` Protocol's ``put`` contract does not itself
        require create-only/revision validation -- only the concrete
        production `_GitHubContentsStore` happens to add it. This double
        omits that defense-in-depth deliberately, to prove the offline cache
        contract stays safe without relying on it.
        """

        def __init__(self) -> None:
            self._record: ContentRecord | None = None

        def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
            return [self._record] if self._record is not None else []

        def get(self, reference: ContentRef) -> ContentRecord:
            if self._record is None:
                raise ContentNotFoundError(str(reference))
            return self._record

        def put(self, request: ContentWrite) -> ContentRecord:
            self._record = ContentRecord(reference=request.reference, content=request.content, revision="rev")
            return self._record

    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="1", name="manifest")
    cache = FileCache(tmp_path / "github-cache")
    provider = MagicMock()
    provider.get_manifest.return_value = ArtifactManifest(issue_number=1)
    naive_store = _NaiveContentsStore()
    backend = GitHubBackend(cache=cache, artifact_provider=provider, contents=naive_store)

    backend.try_get_github = MagicMock(return_value=None)
    backend.put_content(ContentWrite(reference=reference, content="A", create_only=True))
    assert len(backend._cache.pending_mutations()) == 1

    backend.try_get_github = MagicMock(return_value=MagicMock())
    written = backend.put_content(ContentWrite(reference=reference, content="B"))

    assert written.content == "B"
    assert backend._cache.pending_mutations() == []

    record = backend.get_content(reference)

    assert record.content == "B"


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
    backend = GitHubBackend(
        cache=cache, plan_persistence=_UnavailablePlanPersistence(), contents=_UnavailablePlanPersistence()
    )
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


def test_replay_conflict_continues_to_later_mutation_and_acknowledges_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_reference = ContentRef(kind=ContentKind.PLAN, name="P123")
    later_reference = ContentRef(kind=ContentKind.PLAN, name="P456")
    cache = FileCache(tmp_path / "github-cache")
    for reference in (first_reference, later_reference):
        cached = ContentRecord(reference=reference, content="cached", revision="current")
        cache.cache_content(cached)
        cache.queue_write(cached, ContentWrite(reference=reference, content="pending", expected_revision="current"))
    backend = GitHubBackend(cache=cache, plan_persistence=_UnavailablePlanPersistence())
    monkeypatch.setattr(backend, "try_get_github", MagicMock)
    writes = MagicMock()

    def write(request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        if request.reference == first_reference:
            raise ContentConflictError("conflict")
        return ContentRecord(
            reference=request.reference,
            content=request.content,
            revision=GitHubBackend._content_revision(request.content),
        )

    writes.side_effect = write
    monkeypatch.setattr(backend, "_write_online_content", writes)
    acknowledge = MagicMock(side_effect=cache.acknowledge_replay)
    monkeypatch.setattr(cache, "acknowledge_replay", acknowledge)

    backend._replay_pending_content()
    backend._replay_pending_content()

    assert [mutation.write.reference for mutation in cache.pending_mutations()] == [first_reference]
    assert [call.args[0].reference for call in writes.call_args_list] == [
        first_reference,
        later_reference,
        first_reference,
    ]
    assert acknowledge.call_count == 1
    assert [entry.record.reference for entry in acknowledge.call_args.args[0]] == [later_reference]
    assert cache.get_content(later_reference).pending is False
