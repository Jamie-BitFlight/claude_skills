"""Content migration orchestration for the GitHub backend.

Two collaborators split the logical-content lane along the only boundary that
matters at runtime — whether GitHub itself has to be reachable:

``_GitHubContentMigration``
    Resolves reads, writes, and discovery across the authoritative Contents API
    store and the legacy Gist-backed stores, and performs the one-shot migration
    compare-and-swap that promotes legacy content into the Contents API on its
    first conditional write.

``_GitHubContentCache``
    Owns the offline policy around those provider calls: online probing,
    durable queueing, replay of queued mutations, stale fallback reads, and
    caching of authoritative results.

The cache collaborator reaches the provider through the ``_OnlineContent``
Protocol rather than holding ``_GitHubContentMigration`` directly, so
:class:`GitHubBackend` stays the single composition root that wires the two
together and remains the seam callers substitute.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, assert_never

from backlog_core.backends._github_work_item_versions import is_work_item_head_ref
from backlog_core.backends.github_content_stores import (
    _content_revision,
    _ContentPersistence,
    _list_all_content,
    _owner_number,
)
from backlog_core.backends.github_contents import _GitHubContentIntegrityError
from backlog_core.file_cache import ReplayAcknowledgement
from backlog_core.models import (
    BacklogError,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    UnsupportedCapabilityError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from github.Repository import Repository

    from backlog_core.artifact_provider import ArtifactBackend
    from backlog_core.file_cache import FileCache


class _PlanPersistence(Protocol):
    """Structural surface of the legacy plan-index content store."""

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]: ...
    def get(self, reference: ContentRef) -> ContentRecord: ...
    def put(self, request: ContentWrite) -> ContentRecord: ...


class _OnlineContent(Protocol):
    """Provider-side content operations the offline policy depends on.

    :class:`GitHubBackend` satisfies this Protocol structurally, so every call
    resolves against the live backend attribute at call time instead of a
    reference captured during construction.
    """

    def try_get_github(self, repo: str = "") -> Repository | None: ...
    def _list_online_content(self, query: ContentQuery) -> list[ContentRecord]: ...
    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord: ...
    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord: ...


class _GitHubContentMigration:
    """Resolve logical content across the Contents API and the legacy stores."""

    def __init__(
        self,
        contents: Callable[[], _ContentPersistence],
        plan_persistence: Callable[[], _PlanPersistence],
        dispatch_persistence: Callable[[], _ContentPersistence],
        artifact_provider: Callable[[], ArtifactBackend],
    ) -> None:
        """Compose the stores that back logical GitHub content.

        Args:
            contents: Resolver for the authoritative Contents API store.
            plan_persistence: Resolver for the legacy plan-index store.
            dispatch_persistence: Resolver for the legacy dispatch-plan store.
            artifact_provider: Resolver for the Gist persistence adapter backing
                legacy artifacts.

        All four are kept as callables, not captured values, so a store
        substituted on the composing backend after construction (e.g.
        ``backend._plan_persistence = ...``) takes effect for calls made
        after the substitution -- matching the substitutable backend-instance
        seam documented in ARCHITECTURE.md.
        """
        self._contents = contents
        self._plan_persistence = plan_persistence
        self._dispatch_persistence = dispatch_persistence
        self._artifact_provider = artifact_provider

    def list_online(self, query: ContentQuery) -> list[ContentRecord]:
        """Enumerate authoritative content for a query, merged with legacy records.

        Returns:
            Every discoverable record, excluding provider-private work-item heads.
        """
        records = _list_all_content(self._contents(), query)
        records = [record for record in records if not is_work_item_head_ref(record.reference)]
        return self._with_legacy_content(query, records)

    def read(self, reference: ContentRef) -> ContentRecord:
        """Read authoritative content, falling back to the legacy stores.

        Returns:
            The resolved content record.
        """
        try:
            return self._contents().get(reference)
        except ContentNotFoundError:
            pass
        return self.read_legacy(reference)

    def read_legacy(self, reference: ContentRef) -> ContentRecord:
        """Read one content record from the stores that predate the Contents API.

        Returns:
            The legacy content record.

        Raises:
            ContentNotFoundError: If no legacy store holds the reference.
        """
        match reference.kind:
            case ContentKind.PLAN:
                return self._plan_persistence().get(reference)
            case ContentKind.DISPATCH_PLAN:
                return self._dispatch_persistence().get(reference)
            case ContentKind.ARTIFACT_MANIFEST:
                manifest = self._artifact_provider().get_manifest(_owner_number(reference.namespace))
                content = manifest.model_dump_json(by_alias=True)
            case ContentKind.ARTIFACT_CONTENT:
                content = self._artifact_provider().read_artifact_content_from_remote(
                    _owner_number(reference.namespace),
                    reference.artifact_type,
                    f"{reference.artifact_type}/{reference.name}",
                )
        if content is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return ContentRecord(
            reference=reference,
            owner_reference=reference.namespace,
            content=content,
            revision=_content_revision(content),
        )

    def write(self, request: ContentWrite) -> ContentRecord:
        """Write content, migrating a legacy record into the Contents API when needed.

        An unconditional write goes straight to the Contents API. A conditional
        write whose reference is absent there validates the caller's expectation
        against the legacy record first, then republishes it as a create so the
        Contents API becomes authoritative without dropping the compare-and-swap.

        Returns:
            The written content record.

        Raises:
            ContentConflictError: If the caller's create-only or revision
                expectation no longer holds against the legacy record.
        """
        if not request.expected_revision and not request.create_only:
            return self._contents().put(request)
        try:
            self._contents().get(request.reference)
        except ContentNotFoundError as exc:
            try:
                legacy = self.read_legacy(request.reference)
            except ContentNotFoundError:
                return self._contents().put(request)
            if request.create_only:
                raise ContentConflictError("Content already exists") from exc
            if legacy.revision != request.expected_revision:
                raise ContentConflictError("Content revision no longer matches") from exc
            return self._contents().put(
                request.model_copy(
                    update={
                        "owner_reference": (
                            request.owner_reference if request.owner_reference is not None else legacy.owner_reference
                        ),
                        "expected_revision": "",
                        "create_only": True,
                    }
                )
            )
        return self._contents().put(request)

    def _with_legacy_content(self, query: ContentQuery, current: list[ContentRecord]) -> list[ContentRecord]:
        try:
            match query.kind:
                case ContentKind.PLAN:
                    legacy = _list_all_content(self._plan_persistence(), query)
                case ContentKind.DISPATCH_PLAN:
                    legacy = _list_all_content(self._dispatch_persistence(), query)
                case ContentKind.ARTIFACT_MANIFEST | ContentKind.ARTIFACT_CONTENT:
                    legacy = []
                case unreachable:
                    assert_never(unreachable)
        except (BacklogError, ContentUnavailableError, OSError):
            if current:
                return current
            raise
        current_references = {record.reference.model_dump_json() for record in current}
        records = [
            *current,
            *(record for record in legacy if record.reference.model_dump_json() not in current_references),
        ]
        records.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return records


class _GitHubContentCache:
    """Apply offline, replay, and staleness policy around provider content calls."""

    def __init__(self, cache: FileCache, provider: _OnlineContent) -> None:
        """Bind the durable cache to the provider seam it guards.

        Args:
            cache: Provider-private durable cache.
            provider: Online content operations, resolved at call time.
        """
        self._cache = cache
        self._provider = provider

    def list_content(self, query: ContentQuery) -> list[ContentRecord]:
        """Return a bounded discovery page, falling back to stale cached records.

        Returns:
            The requested page of content records.
        """
        online = self._provider.try_get_github() is not None
        if online:
            self.replay_pending()
            try:
                records = self._provider._list_online_content(query)
            except _GitHubContentIntegrityError:
                raise
            except (BacklogError, ContentUnavailableError, OSError):
                online = False
            else:
                for record in records:
                    self._cache.cache_content(record)
                return records[query.offset : query.offset + query.limit]
        records = [
            record.model_copy(update={"stale": not online})
            for record in self._cache._load_state().records
            if record.reference.kind == query.kind
            and not is_work_item_head_ref(record.reference)
            and (query.owner_reference is None or record.owner_reference == query.owner_reference)
            and query.search.casefold() in record.reference.name.casefold()
        ]
        records.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return records[query.offset : query.offset + query.limit]

    def get_content(self, reference: ContentRef) -> ContentRecord:
        """Read authoritative content or an explicitly stale cached copy.

        A reference whose queued write is still pending after
        :meth:`replay_pending` (e.g. blocked by a branch-protection ruleset
        that rejects direct Contents API commits) is served from the cache
        instead of being re-read online. Some legacy fallback readers (the
        artifact-manifest Gist reader in particular) never raise
        ``ContentNotFoundError`` for a reference with no remote data yet —
        they return an empty-but-valid record instead — so a successful
        online read cannot be trusted to mean "this write landed". Trusting
        it anyway would silently overwrite the cache with that empty record,
        discarding the caller's own unacknowledged write.

        Returns:
            The provider or cached logical content record.

        Raises:
            UnsupportedCapabilityError: If the reference is provider-private.
        """
        if is_work_item_head_ref(reference):
            raise UnsupportedCapabilityError("Content reference is provider-private")
        if self._provider.try_get_github() is None:
            return self._cache.get_content(reference, stale=True)
        self.replay_pending()
        cached = self.cached_content(reference)
        if cached is not None and cached.pending:
            return self._cache.get_content(reference, stale=True)
        try:
            record = self._provider._read_online_content(reference, cached)
        except ContentNotFoundError:
            raise
        except _GitHubContentIntegrityError:
            raise
        except (BacklogError, ContentUnavailableError, OSError):
            return self._cache.get_content(reference, stale=True)
        self._cache.cache_content(record)
        return record

    def put_content(self, request: ContentWrite) -> ContentRecord:
        """Write content, durably queueing it while GitHub is offline.

        Returns:
            The applied or pending logical content record.

        Raises:
            UnsupportedCapabilityError: If the reference is provider-private.
            ContentConflictError: If a queued write violates the caller's
                create-only or revision expectation against the cached record.
        """
        if is_work_item_head_ref(request.reference):
            raise UnsupportedCapabilityError("Content reference is provider-private")
        cached = self.cached_content(request.reference)
        if self._provider.try_get_github() is None:
            if request.create_only and cached is not None:
                raise ContentConflictError("Content already exists")
            if request.expected_revision and (cached is None or cached.revision != request.expected_revision):
                raise ContentConflictError("Content revision no longer matches")
            self._cache.queue_write(self._queue_base(request, cached), request)
            return self._cache.get_content(request.reference)
        self.replay_pending()
        cached = self.cached_content(request.reference)
        try:
            record = self._provider._write_online_content(request, cached)
        except ContentNotFoundError:
            raise
        except _GitHubContentIntegrityError:
            raise
        except (BacklogError, ContentUnavailableError, OSError):
            self._cache.queue_write(self._queue_base(request, cached), request)
            return self._cache.get_content(request.reference)
        self._cache.cache_content(record)
        return record

    def replay_pending(self) -> None:
        """Replay durably queued writes, acknowledging only the ones that land."""
        acknowledgements: list[ReplayAcknowledgement] = []
        for mutation in self._cache.pending_mutations():
            cached = self.cached_content(mutation.write.reference)
            try:
                record = self._provider._write_online_content(mutation.write, cached)
            except (ContentConflictError, UnsupportedCapabilityError):
                continue
            except (BacklogError, ContentUnavailableError, OSError):
                break
            acknowledgements.append(
                ReplayAcknowledgement(
                    idempotency_key=mutation.idempotency_key,
                    record=record,
                    fingerprint=_content_revision(record.content),
                )
            )
        if acknowledgements:
            self._cache.acknowledge_replay(acknowledgements)

    def cached_content(self, reference: ContentRef) -> ContentRecord | None:
        """Return the cached record for a reference when one is available.

        Returns:
            The cached record, or None when the cache holds no entry.
        """
        try:
            return self._cache.get_content(reference)
        except ContentUnavailableError:
            return None

    @staticmethod
    def _queue_base(request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        return cached or ContentRecord(
            reference=request.reference,
            owner_reference=request.reference.namespace,
            content="",
            revision=request.expected_revision,
        )
