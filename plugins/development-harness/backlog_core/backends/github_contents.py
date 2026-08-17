"""GitHub Contents API persistence for versioned logical backlog content."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence as SequenceABC, Sequence as SequenceType
from typing import Protocol, TypeAlias, runtime_checkable
from urllib.parse import quote

from github import GithubException

from backlog_core import gh_client
from backlog_core.models import (
    BacklogError,
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
# create_git_ref's documented "Reference already exists" status. Distinct
# from _CONFLICT_STATUSES on purpose: content-write conflicts (create_file /
# update_file) have a revision to re-read and diff, so 409 and 422 both
# route through the same retry-on-current-state logic in put(). A ref
# conflict has no revision -- only re-reading whether the branch now exists
# tells us if the 422 corresponded to a genuine race or an unrelated
# failure (see _content_branch). Treating an undocumented 409 the same way
# would silently accept a failure that never actually created the branch.
_REF_ALREADY_EXISTS = 422
_MAX_CONTENT_BYTES = 1_000_000
_WRITE_ATTEMPTS = 3
# Dedicated, unprotected branch for all .dh/content/v1/ record reads and writes.
# The repository's default branch typically carries a ruleset requiring PR +
# status checks, which permanently rejects direct Contents API commits (409,
# "N of N required status checks are expected") -- a policy failure, not a
# transient conflict. GitHub's "~DEFAULT_BRANCH" ruleset condition only
# matches the branch actually configured as default, so a differently named
# branch sits entirely outside that ruleset's scope. Bootstrapped from the
# default branch HEAD on first use per store instance; see _content_branch.
_CONTENT_BRANCH = "dh-content"
# Bounded aliased GraphQL batch size for blob fetches, matching the
# gh_client._BATCH_CHUNK_SIZE precedent for batches that carry full text
# bodies (not just small metadata fields like _TARGET_BATCH_SIZE=100's
# issue-node batches) -- content records can be up to _MAX_CONTENT_BYTES
# each, so a smaller chunk keeps a single GraphQL response bounded.
_BLOB_BATCH_SIZE = 25
ContentRecords: TypeAlias = list[ContentRecord]


class _GitHubContentIntegrityError(ContentUnavailableError):
    pass


# PyGithub (>=2.9.0) is PEP 561-compliant and ships real, correctly-typed
# classes for every one of these -- github.ContentFile.ContentFile,
# github.Commit.Commit, github.Branch.Branch, github.GitTree.GitTree, and
# github.GitTreeElement.GitTreeElement each declare concrete typed
# properties (verified via inspect.signature against the installed
# package). These five Protocols do NOT exist to compensate for missing
# PyGithub stubs. They exist because the real classes have private,
# requester-bound constructors that only PyGithub itself can call, so the
# lightweight fakes in tests/test_github_contents.py (_File, _FakeCommit,
# _FakeBranch, _TreeEntry, _Tree -- plain Pydantic models) cannot subclass
# or otherwise become nominal instances of them. `ty` proves this: swapping
# any one of these Protocols for its real-class equivalent makes
# `_GitHubContentsStore(lambda: repository)` in the test fixture fail
# `invalid-argument-type` because the fake's return value is not
# assignable to the concrete class. `_ContentsFile` is additionally
# `@runtime_checkable` because `put()` isinstance-checks the write
# response against it -- a real `isinstance(x, ContentFile)` check would
# also reject every test double at runtime, not just at type-check time.
@runtime_checkable
class _ContentsFile(Protocol):
    @property
    def decoded_content(self) -> bytes: ...

    @property
    def sha(self) -> str: ...


class _Commit(Protocol):
    @property
    def sha(self) -> str: ...


class _Branch(Protocol):
    @property
    def commit(self) -> _Commit: ...


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


class _Requester(Protocol):
    def graphql_query(
        self, query: str, variables: dict[str, object]
    ) -> tuple[dict[str, object], dict[str, object]]: ...


class _ContentsRepository(Protocol):
    @property
    def default_branch(self) -> str: ...

    @property
    def full_name(self) -> str: ...

    @property
    def requester(self) -> _Requester: ...

    def get_contents(self, path: str, ref: str) -> _ContentsFile | SequenceType[_ContentsFile]: ...
    def create_file(self, path: str, message: str, content: str, branch: str) -> Mapping[str, object]: ...
    def update_file(self, path: str, message: str, content: str, sha: str, branch: str) -> Mapping[str, object]: ...
    def get_git_tree(self, sha: str, recursive: bool) -> _GitTree: ...
    def get_branch(self, branch: str) -> _Branch: ...
    def create_git_ref(self, ref: str, sha: str) -> object: ...


class _GitHubContentsStore:
    def __init__(self, repository: Callable[[], _ContentsRepository]) -> None:
        self._repository = repository
        self._branch_ready = False

    def _content_branch(self, repository: _ContentsRepository) -> str:
        """Return the dedicated content branch, bootstrapping it if missing.

        Checked and created at most once per store instance: subsequent
        calls return the cached name without another round trip. Creation
        races against a concurrent bootstrapper are resolved by re-reading
        actual branch state after a ``422`` ("Reference already exists")
        from ``create_git_ref`` -- mirroring ``put()``'s ``_existing()``
        re-read on a write conflict -- rather than assuming the conflict
        proves the branch exists.

        Args:
            repository: The resolved PyGithub repository.

        Returns:
            The dedicated content branch name (``_CONTENT_BRANCH``).

        Raises:
            ContentUnavailableError: If branch existence cannot be
                determined, if branch creation fails for a reason other
                than the branch already existing, or if a reported
                "already exists" conflict cannot be confirmed by
                re-reading the branch afterward.
        """
        if self._branch_ready:
            return _CONTENT_BRANCH
        try:
            repository.get_branch(_CONTENT_BRANCH)
        except GithubException as exc:
            if exc.status != _NOT_FOUND:
                raise ContentUnavailableError(f"GitHub content branch lookup failed: {exc}") from exc
            try:
                base = repository.get_branch(repository.default_branch)
                repository.create_git_ref(ref=f"refs/heads/{_CONTENT_BRANCH}", sha=base.commit.sha)
            except GithubException as create_exc:
                if create_exc.status != _REF_ALREADY_EXISTS:
                    raise ContentUnavailableError(
                        f"GitHub content branch creation failed: {create_exc}"
                    ) from create_exc
                self._verify_branch_exists_after_conflict(repository, create_exc)
        self._branch_ready = True
        return _CONTENT_BRANCH

    @staticmethod
    def _verify_branch_exists_after_conflict(repository: _ContentsRepository, create_exc: GithubException) -> None:
        """Confirm the content branch actually exists after a reported ref conflict.

        A ``422`` from ``create_git_ref`` is not proof the branch exists --
        it could be a transient ref-lock or another failure GitHub happens
        to surface as ``422``. Re-reading the branch is the only way to
        distinguish a genuine concurrent-bootstrap race from a failure that
        never created the branch at all.

        Args:
            repository: The resolved PyGithub repository.
            create_exc: The ``GithubException`` raised by ``create_git_ref``.

        Raises:
            ContentUnavailableError: If the branch still cannot be found,
                meaning the reported conflict did not correspond to a
                genuine pre-existing branch.
        """
        try:
            repository.get_branch(_CONTENT_BRANCH)
        except GithubException as verify_exc:
            raise ContentUnavailableError(
                f"GitHub content branch creation reported a conflict ({create_exc}) but the "
                f"branch could not be confirmed to exist: {verify_exc}"
            ) from verify_exc

    def list(self, query: ContentQuery) -> SequenceType[ContentRecord]:
        records = self.list_all(query)
        return records[query.offset : query.offset + query.limit]

    def list_all(self, query: ContentQuery) -> ContentRecords:
        repository = self._repository()
        branch = self._content_branch(repository)
        try:
            tree = repository.get_git_tree(branch, recursive=True)
        except GithubException as exc:
            raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc
        if tree.truncated:
            raise _GitHubContentIntegrityError("GitHub content discovery tree was truncated")
        matching = [
            entry
            for entry in tree.tree
            if entry.type == "blob" and entry.path.startswith(self._kind_prefix(query.kind.value))
        ]
        blobs = self._fetch_blobs_graphql(repository, [entry.sha for entry in matching])
        records = [self._parse(entry.path, blobs[entry.sha], entry.sha) for entry in matching]
        filtered = [
            record
            for record in records
            if (query.owner_reference is None or record.owner_reference == query.owner_reference)
            and query.search.casefold() in record.reference.name.casefold()
        ]
        filtered.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return filtered

    def list_content(self, query: ContentQuery) -> ContentRecords:
        return list(self.list(query))

    def get_many(self, references: SequenceType[ContentRef]) -> ContentRecords:
        if not references:
            return []
        repository = self._repository()
        branch = self._content_branch(repository)
        try:
            tree = repository.get_git_tree(branch, recursive=True)
        except GithubException as exc:
            raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc
        if tree.truncated:
            raise _GitHubContentIntegrityError("GitHub content discovery tree was truncated")
        paths = {self._path(reference) for reference in references}
        matching = [entry for entry in tree.tree if entry.type == "blob" and entry.path in paths]
        blobs = self._fetch_blobs_graphql(repository, [entry.sha for entry in matching])
        return [self._parse(entry.path, blobs[entry.sha], entry.sha) for entry in matching]

    def get(self, reference: ContentRef) -> ContentRecord:
        repository = self._repository()
        return self._get(repository, self._path(reference), self._content_branch(repository))

    def get_content(self, reference: ContentRef) -> ContentRecord:
        return self.get(reference)

    def put(self, request: ContentWrite) -> ContentRecord:
        repository = self._repository()
        branch = self._content_branch(repository)
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

    def _fetch_blobs_graphql(self, repository: _ContentsRepository, shas: SequenceType[str]) -> dict[str, bytes]:
        """Fetch blob content for every sha in one bounded aliased GraphQL request per chunk.

        Replaces one get_git_blob REST call per blob (N+1 against the tree
        listing) with _BLOB_BATCH_SIZE blobs per GraphQL round trip, mirroring
        _GitHubBackend._fetch_targeted_issues's bounded aliased-query pattern.
        GraphQL's Blob.text returns already-decoded UTF8 content directly (no
        base64 step, unlike the REST get_git_blob response).

        Returns:
            Mapping of blob sha to its decoded content bytes.

        Raises:
            ContentUnavailableError: On GraphQL transport failure.
            _GitHubContentIntegrityError: If a requested blob is missing,
                binary, or otherwise not decodable text.
        """
        unique_shas = list(dict.fromkeys(shas))
        if not unique_shas:
            return {}
        owner, repo_name = repository.full_name.split("/", 1)
        blobs: dict[str, bytes] = {}
        for offset in range(0, len(unique_shas), _BLOB_BATCH_SIZE):
            chunk = unique_shas[offset : offset + _BLOB_BATCH_SIZE]
            declarations = ", ".join(f"$sha{index}: GitObjectID!" for index in range(len(chunk)))
            aliases = "\n".join(
                f"      b{index}: object(oid: $sha{index}) {{ ... on Blob {{ text isBinary }} }}"
                for index in range(len(chunk))
            )
            query = (
                f"query BlobBatch($owner: String!, $repo: String!, {declarations}) {{\n"
                f"  repository(owner: $owner, name: $repo) {{\n{aliases}\n  }}\n}}"
            )
            variables: dict[str, object] = {"owner": owner, "repo": repo_name}
            variables.update({f"sha{index}": sha for index, sha in enumerate(chunk)})
            try:
                data = gh_client._graphql_request(repository, query, variables)
            except BacklogError as exc:
                raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc
            repository_data = data.get("repository")
            if not isinstance(repository_data, dict):
                raise ContentUnavailableError("GraphQL blob batch response omitted repository data")
            for index, sha in enumerate(chunk):
                alias = f"b{index}"
                node = repository_data.get(alias)
                if (
                    not isinstance(node, dict)
                    or node.get("isBinary") is not False
                    or not isinstance(node.get("text"), str)
                ):
                    raise _GitHubContentIntegrityError(f"GitHub content blob is invalid or missing: {sha}")
                blobs[sha] = node["text"].encode()
        return blobs

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
