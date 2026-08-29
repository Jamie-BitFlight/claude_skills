from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from backlog_core.backends.github_content_migration import _GitHubContentCache, _GitHubContentMigration
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
    UnsupportedCapabilityError,
)

if TYPE_CHECKING:
    from github.Repository import Repository
    from pytest_mock import MockerFixture


class _FakeLegacyStore:
    """Minimal _PlanPersistence/_ContentPersistence double backed by a single record."""

    def __init__(self, record: ContentRecord | None) -> None:
        self._record = record

    def get(self, reference: ContentRef) -> ContentRecord:
        if self._record is None:
            raise ContentNotFoundError(f"missing: {reference.model_dump_json()}")
        return self._record

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        return [self._record] if self._record else []

    def put(self, request: object) -> ContentRecord:
        raise NotImplementedError


class _EmptyContentsStore:
    """Contents API double that never has the reference, forcing legacy fallback."""

    def get(self, reference: ContentRef) -> ContentRecord:
        raise ContentNotFoundError(f"not in contents api: {reference.model_dump_json()}")

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        return []

    def put(self, request: object) -> ContentRecord:
        raise NotImplementedError


def test_read_legacy_resolves_plan_persistence_at_call_time_not_construction_time(mocker: MockerFixture) -> None:
    """A plan_persistence swap after construction must take effect on the next read.

    Regression test for a Codex review finding on PR 2894: _GitHubContentMigration
    previously captured plan_persistence/dispatch_persistence/artifact_provider by
    value at construction, so replacing backend._plan_persistence after
    construction (a documented substitutable seam) had no effect on subsequent
    reads. All four dependencies are now resolver callables, matching the
    contents resolver's existing pattern.
    """
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    original = _FakeLegacyStore(ContentRecord(reference=reference, content="original", revision="r1"))
    replacement = _FakeLegacyStore(ContentRecord(reference=reference, content="replacement", revision="r2"))
    container: dict[str, Any] = {"plan_persistence": original}

    migration = _GitHubContentMigration(
        contents=_EmptyContentsStore,
        plan_persistence=lambda: container["plan_persistence"],
        dispatch_persistence=lambda: original,
        artifact_provider=mocker.MagicMock,
    )

    assert migration.read(reference).content == "original"

    container["plan_persistence"] = replacement

    assert migration.read(reference).content == "replacement"


def test_with_legacy_content_resolves_dispatch_persistence_at_call_time(mocker: MockerFixture) -> None:
    """The list-side legacy fallback must also resolve dispatch_persistence live."""
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="D1")
    original = _FakeLegacyStore(ContentRecord(reference=reference, content="original", revision="r1"))
    replacement = _FakeLegacyStore(ContentRecord(reference=reference, content="replacement", revision="r2"))
    container: dict[str, Any] = {"dispatch_persistence": original}

    migration = _GitHubContentMigration(
        contents=_EmptyContentsStore,
        plan_persistence=lambda: original,
        dispatch_persistence=lambda: container["dispatch_persistence"],
        artifact_provider=mocker.MagicMock,
    )

    query = ContentQuery(kind=ContentKind.DISPATCH_PLAN)
    [record] = migration.list_online(query)
    assert record.content == "original"

    container["dispatch_persistence"] = replacement

    [record] = migration.list_online(query)
    assert record.content == "replacement"


def test_read_legacy_resolves_artifact_provider_at_call_time(mocker: MockerFixture) -> None:
    """The artifact-manifest legacy path must also resolve artifact_provider live."""
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="1", name="manifest")

    class _FakeArtifactProvider:
        def __init__(self, body: str) -> None:
            self._body = body

        def get_manifest(self, issue_number: int) -> object:
            body = self._body

            class _Manifest:
                def model_dump_json(self, *, by_alias: bool = False) -> str:
                    return body

            return _Manifest()

    container: dict[str, Any] = {"provider": _FakeArtifactProvider("original")}
    migration = _GitHubContentMigration(
        contents=_EmptyContentsStore,
        plan_persistence=mocker.MagicMock,
        dispatch_persistence=mocker.MagicMock,
        artifact_provider=lambda: container["provider"],
    )

    assert migration.read(reference).content == "original"

    container["provider"] = _FakeArtifactProvider("replacement")

    assert migration.read(reference).content == "replacement"


class _UnresolvablyFailingProvider:
    """_OnlineContent double whose write always raises a non-retryable error."""

    def __init__(self, error: BaseException) -> None:
        self._error = error
        self.write_calls = 0

    def try_get_github(self, repo: str = "") -> Repository | None:
        return None

    def _list_online_content(self, query: ContentQuery) -> list[ContentRecord]:
        raise NotImplementedError

    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord:
        raise NotImplementedError

    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        self.write_calls += 1
        raise self._error


@pytest.mark.parametrize(
    "error",
    [
        ContentConflictError("Content revision no longer matches"),
        UnsupportedCapabilityError("Content reference is provider-private"),
    ],
)
def test_replay_pending_discards_mutation_that_can_never_land(
    tmp_path: Path, error: ContentConflictError | UnsupportedCapabilityError
) -> None:
    """Regression test for the pending-queue leak in _GitHubContentCache.replay_pending.

    A ContentConflictError/UnsupportedCapabilityError means the queued write's
    precondition is permanently violated -- retrying it on every future replay
    can never succeed. The sane target behavior is to discard the mutation
    (with its failure surfaced) rather than leave it silently stuck forever.
    This assertion is expected to fail (RED) against the current bare
    `except (...): continue`, which neither acknowledges nor discards it.
    """
    # Given: one durably queued write whose replay will always raise a
    # non-retryable error
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    cache.queue_write(
        ContentRecord(reference=reference, content="", revision=""),
        ContentWrite(reference=reference, content="queued content", expected_revision="stale-rev"),
    )
    provider = _UnresolvablyFailingProvider(error)
    content_cache = _GitHubContentCache(cache=cache, provider=provider)

    # When: reconciliation replays the durable queue
    content_cache.replay_pending()

    # Then: the unresolvable mutation is discarded, not left to retry forever
    # -- but retained (with its failure surfaced) in the rejected bucket
    # rather than lost outright.
    assert provider.write_calls == 1
    assert cache.pending_mutations() == []
    [rejected] = cache.rejected_mutations()
    assert rejected.write.content == "queued content"
    assert rejected.reason


class _OnlineProviderWithReadableContent:
    """_OnlineContent double that is reachable and whose read always succeeds.

    Its write always raises a non-retryable error, so a pending mutation
    replayed against it is rejected rather than retried.
    """

    def __init__(self, error: BaseException, read_record: ContentRecord) -> None:
        self._error = error
        self._read_record = read_record

    def try_get_github(self, repo: str = "") -> Repository | None:
        return cast("Repository", object())

    def _list_online_content(self, query: ContentQuery) -> list[ContentRecord]:
        raise NotImplementedError

    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord:
        return self._read_record

    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        raise self._error


def test_get_content_surfaces_a_rejection_discovered_during_this_same_call(tmp_path: Path) -> None:
    """A conflict discovered by replay_pending() inside get_content() must not vanish.

    Regression test for a review finding on PR #3306: get_content() calls
    replay_pending() as its first step whenever GitHub is reachable. If that
    replay rejects the reference's pending mutation, the reference is no
    longer "pending" (FileCache._is_pending treats a rejected reference as
    not-pending by design), so get_content() falls through to the online-read
    success branch -- which previously returned the freshly read provider
    record directly instead of routing it through FileCache.get_content(),
    the only place conflict_reason is derived. The caller who triggers the
    very replay that discovers the conflict never saw it.
    """
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    cache.queue_write(
        ContentRecord(reference=reference, content="", revision=""),
        ContentWrite(reference=reference, content="queued content", expected_revision="stale-rev"),
    )
    fresh_record = ContentRecord(reference=reference, content="remote content", revision="remote-rev")
    provider = _OnlineProviderWithReadableContent(
        ContentConflictError("Content revision no longer matches"), fresh_record
    )
    content_cache = _GitHubContentCache(cache=cache, provider=provider)

    result = content_cache.get_content(reference)

    assert result.content == "remote content"
    assert result.conflict_reason


class _OnlineProviderWithListableContent:
    """_OnlineContent double that is reachable and whose list always succeeds.

    Its write always raises a non-retryable error, so a pending mutation
    replayed against it is rejected rather than retried.
    """

    def __init__(self, error: BaseException, list_records: list[ContentRecord]) -> None:
        self._error = error
        self._list_records = list_records

    def try_get_github(self, repo: str = "") -> Repository | None:
        return cast("Repository", object())

    def _list_online_content(self, query: ContentQuery) -> list[ContentRecord]:
        return self._list_records

    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord:
        raise NotImplementedError

    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        raise self._error


def test_list_content_surfaces_a_rejection_discovered_during_this_same_call(tmp_path: Path) -> None:
    """list_content()'s online branch must also surface a conflict_reason.

    Regression test for a review finding on PR #3306: ContentTaskProvider
    loads plans through list_content(), not get_content(). The online branch
    of list_content() returned raw provider records directly (no pending or
    conflict_reason derivation at all), so a rejection replay_pending()
    discovers as the first step of this same call was invisible to any
    list-based consumer, exactly like the get_content() gap fixed above.
    """
    cache = FileCache(tmp_path)
    reference = ContentRef(kind=ContentKind.PLAN, name="P1")
    cache.queue_write(
        ContentRecord(reference=reference, content="", revision=""),
        ContentWrite(reference=reference, content="queued content", expected_revision="stale-rev"),
    )
    fresh_record = ContentRecord(reference=reference, content="remote content", revision="remote-rev")
    provider = _OnlineProviderWithListableContent(
        ContentConflictError("Content revision no longer matches"), [fresh_record]
    )
    content_cache = _GitHubContentCache(cache=cache, provider=provider)

    [result] = content_cache.list_content(ContentQuery(kind=ContentKind.PLAN))

    assert result.content == "remote content"
    assert result.conflict_reason
