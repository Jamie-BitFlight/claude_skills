from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock

from backlog_core.backends.github_content_migration import _GitHubContentMigration
from backlog_core.models import ContentKind, ContentNotFoundError, ContentQuery, ContentRecord, ContentRef


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


def test_read_legacy_resolves_plan_persistence_at_call_time_not_construction_time() -> None:
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
        artifact_provider=MagicMock,
    )

    assert migration.read(reference).content == "original"

    container["plan_persistence"] = replacement

    assert migration.read(reference).content == "replacement"


def test_with_legacy_content_resolves_dispatch_persistence_at_call_time() -> None:
    """The list-side legacy fallback must also resolve dispatch_persistence live."""
    reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name="D1")
    original = _FakeLegacyStore(ContentRecord(reference=reference, content="original", revision="r1"))
    replacement = _FakeLegacyStore(ContentRecord(reference=reference, content="replacement", revision="r2"))
    container: dict[str, Any] = {"dispatch_persistence": original}

    migration = _GitHubContentMigration(
        contents=_EmptyContentsStore,
        plan_persistence=lambda: original,
        dispatch_persistence=lambda: container["dispatch_persistence"],
        artifact_provider=MagicMock,
    )

    query = ContentQuery(kind=ContentKind.DISPATCH_PLAN)
    [record] = migration.list_online(query)
    assert record.content == "original"

    container["dispatch_persistence"] = replacement

    [record] = migration.list_online(query)
    assert record.content == "replacement"


def test_read_legacy_resolves_artifact_provider_at_call_time() -> None:
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
        plan_persistence=MagicMock,
        dispatch_persistence=MagicMock,
        artifact_provider=lambda: container["provider"],
    )

    assert migration.read(reference).content == "original"

    container["provider"] = _FakeArtifactProvider("replacement")

    assert migration.read(reference).content == "replacement"
