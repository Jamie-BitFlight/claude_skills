"""Content persistence vocabulary and legacy GitHub content stores.

This module owns the persistence-shaped collaborators that :class:`GitHubBackend`
composes for logical content:

- the structural Protocols every content store satisfies (``list``/``get``/``put``),
- the shared revision, owner-reference, and full-page enumeration helpers,
- the pre-Contents-API stores (``_GitHubPlanPersistence``,
  ``_GitHubDispatchPersistence``) that remain readable so historical Gist-backed
  plans and dispatch plans keep resolving after the Contents API became the
  authoritative writer.

No reconciliation, cache, or GitHub API composition logic lives here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sam_schema.core.artifact_registry_client import (
    ArtifactRegistryClient,
    PlanContentUnavailableError,
    PlanIndexUnavailableError,
)
from sam_schema.core.exceptions import ArtifactWriteError, PlanIndexError
from sam_schema.core.plan_id_index import PlanIndexEntry, create_plan_id_index

from backlog_core.artifact_provider import ArtifactBackend
from backlog_core.backends.github_contents import _GitHubContentsStore
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
    parse_issue_number,
)

_CONTENT_PAGE_SIZE = 100

# Resolved once at import so a test double substituted for the module-level
# ``_GitHubContentsStore`` name elsewhere never changes the native-store
# detection that selects whole-tree enumeration over paged listing.
_NativeContentsStore = _GitHubContentsStore


class _ContentPersistence(Protocol):
    """Structural surface every logical content store satisfies."""

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]: ...
    def get(self, reference: ContentRef) -> ContentRecord: ...
    def put(self, request: ContentWrite) -> ContentRecord: ...


@runtime_checkable
class _RemoteArtifactContentLister(Protocol):
    def list_artifact_content_from_remote(
        self, item_id: int, artifact_type: str, path_prefix: str
    ) -> dict[str, str]: ...


def _content_revision(content: str) -> str:
    """Return the content-addressed revision for a logical content body.

    Returns:
        Hex SHA-256 digest of the UTF-8 encoded content.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def _owner_number(reference: str) -> int:
    """Resolve a GitHub owner reference (``#123``) to its issue number.

    Returns:
        The parsed issue number.

    Raises:
        ContentUnavailableError: If the reference is not a GitHub issue reference.
    """
    number = parse_issue_number(reference)
    if number is None:
        raise ContentUnavailableError(f"Invalid GitHub owner reference: {reference!r}")
    return number


def _list_all_content(persistence: _ContentPersistence, query: ContentQuery) -> list[ContentRecord]:
    """Enumerate every record a content store exposes for one query.

    Native Contents stores enumerate the whole tree in one call; every other
    store is drained page by page so callers never observe a partial listing.

    Returns:
        All matching records, ignoring the query's offset and limit window.
    """
    if isinstance(persistence, _NativeContentsStore):
        return persistence.list_all(query)
    records: list[ContentRecord] = []
    offset = 0
    while True:
        page = list(persistence.list(query.model_copy(update={"offset": offset, "limit": _CONTENT_PAGE_SIZE})))
        records.extend(page)
        if len(page) < _CONTENT_PAGE_SIZE:
            return records
        offset += len(page)


@dataclass(frozen=True, slots=True)
class _DispatchIndexEntry:
    name: str
    owner_reference: str
    legacy: bool = False


class _GitHubPlanPersistence:
    def __init__(self, provider: ArtifactBackend) -> None:
        client = ArtifactRegistryClient(provider)
        self._index = create_plan_id_index(client)
        self._sentinel_issue = self._index._sentinel_issue
        self._client = client
        self._provider = provider

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        entries = [
            entry
            for entry in self._entries()
            if (query.owner_reference is None or self._owner(entry) == query.owner_reference)
            and query.search.casefold() in f"{entry.plan_id} {entry.slug}".casefold()
        ]
        return [self._record(entry) for entry in entries[query.offset : query.offset + query.limit]]

    def get(self, reference: ContentRef) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.plan_id == reference.name), None)
        if entry is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return self._record(entry)

    def put(self, request: ContentWrite) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.plan_id == request.reference.name), None)
        current = self._record(entry) if entry is not None else None
        owner = (
            request.owner_reference
            if request.owner_reference is not None
            else current.owner_reference
            if current is not None
            else ""
        )
        if current is not None and current.content == request.content and current.owner_reference == owner:
            return current
        if request.expected_revision:
            raise ContentConflictError("Content revision no longer matches")
        raise UnsupportedCapabilityError("GitHub plan writes require a compare-and-swap revision")

    def _entries(self) -> Sequence[PlanIndexEntry]:
        try:
            return self._index.list_all()
        except PlanIndexUnavailableError as exc:
            raise BacklogError(str(exc)) from exc
        except (ArtifactWriteError, PlanIndexError) as exc:
            raise BacklogError(str(exc)) from exc

    def _record(self, entry: PlanIndexEntry) -> ContentRecord:
        try:
            content = (
                self._client.read(entry.issue, plan_id=entry.plan_id)
                if entry.issue is not None
                else self._provider.read_artifact_content_from_remote(
                    self._sentinel_issue, "plan", self._unlinked_path(entry.plan_id)
                )
            )
        except PlanContentUnavailableError as exc:
            raise BacklogError(str(exc)) from exc
        reference = ContentRef(kind=ContentKind.PLAN, name=entry.plan_id)
        if content is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return ContentRecord(
            reference=reference,
            owner_reference=self._owner(entry),
            content=content,
            revision=_content_revision(content),
        )

    @staticmethod
    def _owner(entry: PlanIndexEntry) -> str:
        return f"#{entry.issue}" if entry.issue is not None else ""

    @staticmethod
    def _unlinked_path(plan_id: str) -> str:
        return f"sam-plan/unlinked/{plan_id}.yaml"


class _GitHubDispatchPersistence:
    _CONTENT_TYPE = "dispatch-plan"
    _INDEX_TYPE = "dispatch-plan-index"
    _INDEX_PATH = "dispatch-plan/index.json"
    _ENVELOPE_VERSION_KEY = "dispatch-content-version"

    def __init__(self, provider: ArtifactBackend) -> None:
        self._provider = provider
        self._sentinel_issue = create_plan_id_index(ArtifactRegistryClient(provider))._sentinel_issue

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        entries = [
            entry
            for entry in self._entries()
            if (query.owner_reference is None or entry.owner_reference == query.owner_reference)
            and query.search.casefold() in entry.name.casefold()
        ]
        records = [self._record(entry) for entry in entries]
        return records[query.offset : query.offset + query.limit]

    def get(self, reference: ContentRef) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.name == reference.name), None)
        if entry is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return self._record(entry)

    def put(self, request: ContentWrite) -> ContentRecord:
        entries = self._entries()
        entry = next((entry for entry in entries if entry.name == request.reference.name), None)
        current = self._record(entry) if entry is not None else None
        owner_reference = (
            request.owner_reference if request.owner_reference is not None else current and current.owner_reference
        )
        if current is not None and current.content == request.content and current.owner_reference == owner_reference:
            return current
        raise UnsupportedCapabilityError("GitHub dispatch writes are not supported")

    def _record(self, entry: _DispatchIndexEntry) -> ContentRecord:
        stored_content = self._provider.read_artifact_content_from_remote(
            self._sentinel_issue, self._CONTENT_TYPE, self._content_path(entry.name)
        )
        if stored_content is None:
            reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name=entry.name)
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        envelope = self._parse_envelope(stored_content)
        if entry.legacy:
            content = stored_content
        else:
            if envelope is None:
                raise ContentUnavailableError("Dispatch content envelope is invalid")
            content = envelope[2]
        return ContentRecord(
            reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name=entry.name),
            owner_reference=entry.owner_reference,
            content=content,
            revision=_content_revision(content),
        )

    def _entries(self) -> Sequence[_DispatchIndexEntry]:
        provider = self._provider
        if not isinstance(provider, _RemoteArtifactContentLister):
            raise ContentUnavailableError("GitHub artifact provider cannot enumerate dispatch plans")
        current_entries: list[_DispatchIndexEntry] = []
        for stored_content in provider.list_artifact_content_from_remote(
            self._sentinel_issue, self._CONTENT_TYPE, "dispatch-plan/"
        ).values():
            envelope = self._parse_envelope(stored_content)
            if envelope is not None:
                current_entries.append(_DispatchIndexEntry(name=envelope[0], owner_reference=envelope[1]))

        current_names = {entry.name for entry in current_entries}
        return [*current_entries, *(entry for entry in self._legacy_entries() if entry.name not in current_names)]

    def _legacy_entries(self) -> Sequence[_DispatchIndexEntry]:
        content = self._provider.read_artifact_content_from_remote(
            self._sentinel_issue, self._INDEX_TYPE, self._INDEX_PATH
        )
        if content is None:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ContentUnavailableError("Dispatch content index is invalid") from exc
        if isinstance(data, list) and all(isinstance(name, str) for name in data):
            return [_DispatchIndexEntry(name=name, owner_reference="", legacy=True) for name in data]
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ContentUnavailableError("Dispatch content index is invalid")
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise ContentUnavailableError("Dispatch content index is invalid")
        entries: list[_DispatchIndexEntry] = []
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise ContentUnavailableError("Dispatch content index is invalid")
            name = raw_entry.get("name")
            owner_reference = raw_entry.get("owner_reference")
            if not isinstance(name, str) or not isinstance(owner_reference, str):
                raise ContentUnavailableError("Dispatch content index is invalid")
            entries.append(_DispatchIndexEntry(name=name, owner_reference=owner_reference, legacy=True))
        return entries

    @classmethod
    def _serialize_envelope(cls, name: str, owner_reference: str, content: str) -> str:
        return json.dumps(
            {cls._ENVELOPE_VERSION_KEY: 1, "name": name, "owner_reference": owner_reference, "content": content},
            separators=(",", ":"),
        )

    @classmethod
    def _parse_envelope(cls, stored_content: str) -> tuple[str, str, str] | None:
        try:
            data = json.loads(stored_content)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict) or cls._ENVELOPE_VERSION_KEY not in data:
            return None
        if data[cls._ENVELOPE_VERSION_KEY] != 1:
            raise ContentUnavailableError("Dispatch content envelope is invalid")
        name = data.get("name")
        owner_reference = data.get("owner_reference")
        content = data.get("content")
        if not isinstance(name, str) or not isinstance(owner_reference, str) or not isinstance(content, str):
            raise ContentUnavailableError("Dispatch content envelope is invalid")
        return name, owner_reference, content

    @staticmethod
    def _content_path(name: str) -> str:
        return f"dispatch-plan/{name}.json"
