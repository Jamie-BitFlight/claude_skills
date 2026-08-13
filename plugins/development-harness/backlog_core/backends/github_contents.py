"""GitHub Contents API persistence for versioned logical backlog content."""

from __future__ import annotations

import json
from base64 import b64decode
from binascii import Error as Base64Error
from collections.abc import Callable, Mapping, Sequence as SequenceABC, Sequence as SequenceType
from typing import Protocol, TypeAlias, runtime_checkable
from urllib.parse import quote

from github import GithubException

from backlog_core.models import (
    ContentConflictError,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)

_ROOT = ".dh/content/v1"
_VERSION = 1
_NOT_FOUND = 404
_CONFLICT_STATUSES = frozenset({409, 422})
_MAX_CONTENT_BYTES = 1_000_000
_WRITE_ATTEMPTS = 3
ContentRecords: TypeAlias = list[ContentRecord]


class _GitHubContentIntegrityError(ContentUnavailableError):
    pass


@runtime_checkable
class _ContentsFile(Protocol):
    @property
    def decoded_content(self) -> bytes: ...

    @property
    def sha(self) -> str: ...


class _GitTreeEntry(Protocol):
    @property
    def path(self) -> str: ...

    @property
    def type(self) -> str: ...

    @property
    def sha(self) -> str: ...


class _GitTree(Protocol):
    @property
    def tree(self) -> SequenceType[_GitTreeEntry]: ...

    @property
    def truncated(self) -> bool: ...


class _GitBlob(Protocol):
    @property
    def content(self) -> str: ...


class _ContentsRepository(Protocol):
    @property
    def default_branch(self) -> str: ...

    def get_contents(self, path: str, ref: str) -> _ContentsFile | SequenceType[_ContentsFile]: ...
    def create_file(self, path: str, message: str, content: str, branch: str) -> Mapping[str, object]: ...
    def update_file(self, path: str, message: str, content: str, sha: str, branch: str) -> Mapping[str, object]: ...
    def get_git_tree(self, sha: str, recursive: bool) -> _GitTree: ...
    def get_git_blob(self, sha: str) -> _GitBlob: ...


class _GitHubContentsStore:
    def __init__(self, repository: Callable[[], _ContentsRepository]) -> None:
        self._repository = repository

    def list(self, query: ContentQuery) -> SequenceType[ContentRecord]:
        repository = self._repository()
        try:
            tree = repository.get_git_tree(repository.default_branch, recursive=True)
        except GithubException as exc:
            raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc
        if tree.truncated:
            raise _GitHubContentIntegrityError("GitHub content discovery tree was truncated")
        records = [
            self._from_blob(repository, entry.path, entry.sha)
            for entry in tree.tree
            if entry.type == "blob" and entry.path.startswith(self._kind_prefix(query.kind.value))
        ]
        filtered = [
            record
            for record in records
            if (query.owner_reference is None or record.owner_reference == query.owner_reference)
            and query.search.casefold() in record.reference.name.casefold()
        ]
        filtered.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return filtered[query.offset : query.offset + query.limit]

    def list_content(self, query: ContentQuery) -> ContentRecords:
        return list(self.list(query))

    def get(self, reference: ContentRef) -> ContentRecord:
        repository = self._repository()
        return self._get(repository, self._path(reference), repository.default_branch)

    def get_content(self, reference: ContentRef) -> ContentRecord:
        return self.get(reference)

    def put(self, request: ContentWrite) -> ContentRecord:
        repository = self._repository()
        branch = repository.default_branch
        path = self._path(request.reference)
        for _ in range(_WRITE_ATTEMPTS):
            current = self._existing(repository, path, branch)
            record = self._record_for_write(request, current)
            if current == record:
                return current
            envelope = self._serialize(record)
            if len(envelope.encode()) > _MAX_CONTENT_BYTES:
                raise ContentUnavailableError("GitHub content exceeds the 1 MB Contents API limit")
            try:
                if current is None:
                    response = repository.create_file(path, f"Store {request.reference.kind}", envelope, branch=branch)
                else:
                    response = repository.update_file(
                        path, f"Store {request.reference.kind}", envelope, current.revision, branch=branch
                    )
            except GithubException as exc:
                if exc.status not in _CONFLICT_STATUSES:
                    raise ContentUnavailableError(f"GitHub content write failed: {exc}") from exc
                observed = self._existing(repository, path, branch)
                if current is None:
                    if observed is not None:
                        raise ContentConflictError("Content already exists") from exc
                elif observed is None or observed.revision != current.revision:
                    raise ContentConflictError("Content revision no longer matches") from exc
            else:
                written = response.get("content")
                if not isinstance(written, _ContentsFile):
                    raise ContentUnavailableError("GitHub content write response was invalid")
                return self._parse(path, envelope.encode(), written.sha)
        raise ContentUnavailableError("GitHub content write could not advance the selected branch")

    def put_content(self, request: ContentWrite) -> ContentRecord:
        return self.put(request)

    def _existing(self, repository: _ContentsRepository, path: str, branch: str) -> ContentRecord | None:
        try:
            return self._get(repository, path, branch)
        except ContentNotFoundError:
            return None

    @staticmethod
    def _record_for_write(request: ContentWrite, current: ContentRecord | None) -> ContentRecord:
        owner_reference = (
            request.owner_reference
            if request.owner_reference is not None
            else (current.owner_reference if current is not None else request.reference.namespace)
        )
        if request.create_only and current is not None:
            raise ContentConflictError("Content already exists")
        if request.expected_revision and (current is None or current.revision != request.expected_revision):
            raise ContentConflictError("Content revision no longer matches")
        if current is not None and current.content == request.content and current.owner_reference == owner_reference:
            return current
        return ContentRecord(reference=request.reference, owner_reference=owner_reference, content=request.content)

    @staticmethod
    def _kind_prefix(kind: object) -> str:
        return f"{_ROOT}/{_segment(str(kind))}/"

    @staticmethod
    def _path(reference: ContentRef) -> str:
        return "/".join((
            _ROOT,
            _segment(reference.kind.value),
            _segment(reference.namespace),
            _segment(reference.artifact_type),
            _segment(reference.name),
        ))

    def _get(self, repository: _ContentsRepository, path: str, branch: str) -> ContentRecord:
        try:
            file = repository.get_contents(path, ref=branch)
        except GithubException as exc:
            if exc.status == _NOT_FOUND:
                raise ContentNotFoundError(f"Content was not found: {path}") from exc
            raise ContentUnavailableError(f"GitHub content read failed: {exc}") from exc
        if isinstance(file, SequenceABC):
            raise _GitHubContentIntegrityError(f"GitHub content path is not a file: {path}")
        return self._parse(path, file.decoded_content, file.sha)

    def _from_blob(self, repository: _ContentsRepository, path: str, sha: str) -> ContentRecord:
        try:
            encoded = repository.get_git_blob(sha).content
        except GithubException as exc:
            raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc
        try:
            content = b64decode(encoded, validate=True)
        except (Base64Error, ValueError) as exc:
            raise _GitHubContentIntegrityError(f"GitHub content envelope is invalid: {path}") from exc
        return self._parse(path, content, sha)

    def _parse(self, path: str, content: bytes, revision: str) -> ContentRecord:
        try:
            data = json.loads(content.decode())
            record = ContentRecord.model_validate(data)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _GitHubContentIntegrityError(f"GitHub content envelope is invalid: {path}") from exc
        if data.get("version") != _VERSION or self._path(record.reference) != path:
            raise _GitHubContentIntegrityError(f"GitHub content envelope is invalid: {path}")
        return record.model_copy(update={"revision": revision})

    @staticmethod
    def _serialize(record: ContentRecord) -> str:
        return json.dumps(
            {
                "version": _VERSION,
                **record.model_dump(mode="json", include={"reference", "owner_reference", "content"}),
            },
            separators=(",", ":"),
        )


def _segment(value: str) -> str:
    return "~" if not value else f"_{quote(value, safe='')}"
