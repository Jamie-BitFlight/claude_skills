"""Backend abstraction for artifact manifest storage.

Defines the ``ArtifactBackend`` protocol and the ``GitHubGistArtifactProvider``
implementation that stores manifest data in GitHub Gists linked from Issue bodies.

The manifest is stored as a JSON file (``manifest.json``) in a private Gist.
The Gist is linked to the issue body via an HTML comment sentinel::

    <!-- artifact-gist:{gist_id} -->

Legacy issues using the inline markdown table format are lazily migrated to
Gist storage on first read — the old section is replaced with the sentinel.

Artifact file content (research, plan documents, etc.) is stored as additional
files in the same Gist, with ``/`` in the path replaced by ``--`` to form a
valid Gist filename.

Parse/render helpers for the legacy inline format are in
:mod:`backlog_core.artifact_registry`.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias, cast, runtime_checkable

from github import Auth, Github, GithubException, InputFileContent

from .artifact_provider_local import LocalFilesystemArtifactProvider
from .artifact_registry import parse_manifest_section, render_manifest_section, replace_manifest_in_body
from .gh_client import _fetch_issue_graphql, _update_issue_graphql, get_github
from .gitlab_client import (
    gitlab_create_issue_note,
    gitlab_create_snippet,
    gitlab_get_snippet,
    gitlab_list_issue_notes,
    gitlab_update_snippet,
)
from .linear_client import linear_create_attachment, linear_get_attachments
from .models import ArtifactManifest, BacklogError

#: Type alias for a backlog item identifier.
#: GitHub and GitLab backends use a positive integer IID; the beads backend
#: uses a nanoid string (e.g. ``"bd-a3f8"``); Linear uses a UUID string.
ItemId: TypeAlias = str | int

# dh_paths lives one level above backlog_core (at plugin root).
_plugin_root = Path(__file__).parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import dh_paths as _dh_paths

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from github.AuthenticatedUser import AuthenticatedUser
    from github.Gist import Gist

# Re-export so callers that imported these from artifact_provider continue to work.
__all__ = [
    "ArtifactBackend",
    "BackendName",
    "GitHubArtifactProvider",
    "GitHubGistArtifactProvider",
    "GitLabArtifactProvider",
    "LinearArtifactProvider",
    "LocalFilesystemArtifactProvider",
    "create_artifact_provider",
    "parse_manifest_section",
    "render_manifest_section",
    "replace_manifest_in_body",
]


class BackendName(StrEnum):
    """Canonical identifiers for pluggable artifact storage backends."""

    github = "github"
    linear = "linear"
    gitlab = "gitlab"
    beads = "beads"
    local = "local"
    sqlite = "sqlite"
    memory = "memory"


# ---------------------------------------------------------------------------
# Artifact content comment constants
# ---------------------------------------------------------------------------

#: Maximum GitHub comment body size in characters.
_GITHUB_COMMENT_MAX_CHARS = 65_536

#: Regex matching the opening tag of an artifact content comment block.
#: Captures ``type`` and ``path`` groups.
_ARTIFACT_CONTENT_TAG_RE = re.compile(r"<!-- artifact-content:type=(?P<type>[^:]+):path=(?P<path>[^ >]+) -->")

#: Closing tag for artifact content comment blocks.
_ARTIFACT_CONTENT_END_TAG = "<!-- /artifact-content -->"

#: Regex matching the complete artifact content block including delimiters.
_ARTIFACT_CONTENT_BLOCK_RE = re.compile(
    r"<!-- artifact-content:type=[^:]+:path=[^ >]+ -->.*?<!-- /artifact-content -->", re.DOTALL
)

#: Regex matching the Gist sentinel comment that links an issue to its Gist.
#: Captures the ``gist_id`` group (hex string).
_GIST_SENTINEL_RE = re.compile(r"<!-- artifact-gist:(?P<gist_id>[0-9a-f]+) -->")

#: HTTP status code returned by the GitHub Gist API when the token lacks the
#: ``gist`` OAuth scope.
_GIST_FORBIDDEN_STATUS = 403


def _make_github_client() -> Github:
    """Create a PyGithub :class:`~github.Github` client from ``GITHUB_TOKEN``.

    Returns:
        Authenticated ``Github`` client instance.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    return Github(auth=Auth.Token(token))


def _require_int_item_id(cls_name: str, item_id: ItemId) -> int:
    """Raise ``TypeError`` when *item_id* is a string.

    GitHub and GitLab providers require a positive integer item ID.  String
    identifiers (beads nanoid ``"bd-a3f8"``) are only valid for
    ``BeadsArtifactProvider``.  Linear UUID strings must NOT pass through
    this helper — ``LinearArtifactProvider`` accepts strings natively and
    does not call this function.

    Args:
        cls_name: Name of the calling provider class, used in the error message.
        item_id: The value passed by the caller — rejected when it is a ``str``.

    Returns:
        The validated integer item ID.

    Raises:
        TypeError: When *item_id* is a ``str`` instance.
    """
    if isinstance(item_id, str):
        msg = (
            f"{cls_name} requires an integer item ID, got {item_id!r}. "
            "Use BeadsArtifactProvider for string (beads) item identifiers."
        )
        raise TypeError(msg)
    return item_id


# ---------------------------------------------------------------------------
# Artifact content comment helpers
# ---------------------------------------------------------------------------


def _build_artifact_content_comment(artifact_type: str, path: str, content: str) -> str:
    """Build a structured GitHub comment body for storing artifact content.

    The comment uses HTML comment delimiters for programmatic identification
    and a ``<details>`` block to keep the issue visually uncluttered.

    If *content* exceeds ``_GITHUB_COMMENT_MAX_CHARS`` it is truncated and a
    warning notice is appended.

    Args:
        artifact_type: Artifact type string, e.g. ``"research"``.
        path: Repo-relative path used as the comment identifier.
        content: Full artifact content to embed.

    Returns:
        Complete comment body string ready for ``create_comment`` or
        ``comment.edit()``.
    """
    opening_tag = f"<!-- artifact-content:type={artifact_type}:path={path} -->"
    summary = f"Artifact: {artifact_type} — {path}"
    # Build the wrapper without content to measure fixed overhead.

    def _assemble(inner: str) -> str:
        return (
            f"{opening_tag}\n"
            "<details>\n"
            f"<summary>{summary}</summary>\n\n"
            f"{inner}\n\n"
            "</details>\n"
            f"{_ARTIFACT_CONTENT_END_TAG}"
        )

    # Truncation notice added when content is cut — measure it first so the
    # final assembled string stays within the GitHub limit.
    notice = f"\n\n<!-- WARNING: content truncated — original length {len(content)} chars exceeded GitHub limit -->"
    overhead = len(_assemble("")) + len(notice)
    max_content = _GITHUB_COMMENT_MAX_CHARS - overhead

    if len(content) > max_content:
        return _assemble(content[:max_content] + notice)
    return _assemble(content)


def _extract_content_from_comment(comment_body: str) -> str:
    """Extract the raw content from an artifact content comment body.

    Parses the ``<details>`` block between the opening tag and closing
    delimiter and returns the inner content (between the ``</summary>`` close
    and the ``</details>`` open).

    Args:
        comment_body: Full GitHub comment body as returned by PyGithub.

    Returns:
        Extracted content string, or the full comment body when the expected
        structure is not found.
    """
    # Find content between </summary> and </details>
    summary_end = comment_body.find("</summary>")
    details_end = comment_body.rfind("</details>")
    if summary_end == -1 or details_end == -1:
        return comment_body
    # Skip the </summary> tag and surrounding blank lines.
    raw = comment_body[summary_end + len("</summary>") : details_end]
    return raw.strip()


def _sanitize_gist_filename(path: str) -> str:
    """Convert a repo-relative artifact path to a valid Gist filename.

    Gist filenames may not contain ``/``.  Slashes are replaced with ``--``
    so the path can be reconstructed unambiguously.

    Args:
        path: Repo-relative path such as ``plan/architect-foo.md``.

    Returns:
        Gist-safe filename such as ``plan--architect-foo.md``.
    """
    return path.replace("/", "--")


def _replace_old_manifest_with_sentinel(body: str, sentinel: str) -> str:
    """Replace an inline manifest block with a Gist sentinel comment.

    When the legacy ``<!-- artifact-manifest:begin/end -->`` block is found it
    is replaced in-place.  When absent the sentinel is appended to the body.

    Args:
        body: Current GitHub Issue body text.
        sentinel: Sentinel string, e.g. ``<!-- artifact-gist:abc123 -->``.

    Returns:
        Updated body with the sentinel inserted.
    """
    old_match = re.search(r"<!-- artifact-manifest:begin -->.*?<!-- artifact-manifest:end -->", body, re.DOTALL)
    if old_match:
        return body[: old_match.start()] + sentinel + body[old_match.end() :]
    return body.rstrip() + f"\n\n{sentinel}"


# ---------------------------------------------------------------------------
# ArtifactBackend Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ArtifactBackend(Protocol):
    """Protocol defining the storage contract for artifact manifest backends.

    Implementations store and retrieve ``ArtifactManifest`` objects from a
    backend (GitHub Issue body, database, local file, etc.) and serve
    artifact file content for MCP consumers.

    All methods are synchronous.  The MCP tool layer wraps calls in
    ``asyncio.to_thread()`` when needed.
    """

    def get_manifest(self, item_id: ItemId) -> ArtifactManifest:
        """Retrieve the artifact manifest for *item_id*.

        Args:
            item_id: Backlog item identifier — positive integer for GitHub/GitLab
                backends, UUID string for Linear, or beads nanoid string
                (e.g. ``"bd-a3f8"``) for the beads backend.

        Returns:
            ``ArtifactManifest`` for the item.  Returns an empty manifest
            (no artifacts) when the item has no manifest section — this is
            not an error.
        """
        ...

    def set_manifest(self, item_id: ItemId, manifest: ArtifactManifest) -> None:
        """Persist *manifest* for *item_id*.

        Replaces any existing manifest section; creates one if absent.

        Args:
            item_id: Backlog item identifier — positive integer for GitHub/GitLab
                backends, UUID string for Linear, or beads nanoid string
                (e.g. ``"bd-a3f8"``) for the beads backend.
            manifest: Updated manifest to persist.
        """
        ...

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree.

        Args:
            path: Repo-relative path to the artifact file (e.g.
                ``plan/architect-foo.md`` or ``research/findings.md``).
                Must not escape the repository root.

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* fails the safety checks (path traversal
                detected — path resolves outside the repository root).
            FileNotFoundError: When the file does not exist in the root
                worktree (cache miss — the artifact is registered but not yet
                committed or was deleted).
        """
        ...

    def store_artifact_content(self, item_id: ItemId, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a GitHub issue comment.

        Creates a structured collapsible comment identified by
        ``artifact-content:type={artifact_type}:path={path}``.  When a
        comment with the same type and path already exists it is edited
        in-place rather than duplicated.

        If *content* exceeds the GitHub comment size limit
        (``_GITHUB_COMMENT_MAX_CHARS``), it is truncated and a warning
        notice is appended.

        Args:
            item_id: Backlog item identifier — positive integer for GitHub backends
                or beads nanoid string for the beads backend.
            artifact_type: Artifact type string, e.g. ``"research"``.
            path: Repo-relative path used as the comment identifier.
            content: Full artifact content to store.
        """
        ...

    def read_artifact_content_from_remote(self, item_id: ItemId, artifact_type: str, path: str) -> str | None:
        """Search item comments for stored artifact content.

        Scans the item's comments for an artifact content block whose
        ``type`` and ``path`` match the given arguments.

        Args:
            item_id: Backlog item identifier — positive integer for GitHub backends
                or beads nanoid string for the beads backend.
            artifact_type: Artifact type string to match.
            path: Repo-relative path to match.

        Returns:
            The stored content string when found, or ``None`` when no
            matching comment exists.
        """
        ...

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content from the local filesystem without raising on missing file.

        Applies the same path safety checks as :meth:`read_artifact_content`
        but returns ``None`` when the file does not exist, rather than
        raising ``FileNotFoundError``.  Used by ``artifact_register`` to
        auto-upload local file content to GitHub when the caller does not
        supply explicit content.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not exist.

        Raises:
            ValueError: When *path* fails the safety checks (path traversal).
        """
        ...


# ---------------------------------------------------------------------------
# GitHubArtifactProvider
# ---------------------------------------------------------------------------


class GitHubGistArtifactProvider:
    """GitHub Gist-backed implementation of :class:`ArtifactBackend`.

    Stores the artifact manifest as a JSON file inside a private GitHub Gist.
    The Gist is linked to the issue body via an HTML comment sentinel
    ``<!-- artifact-gist:{gist_id} -->``.

    Artifact file content (research, plan documents, etc.) is stored as
    additional files in the same Gist with ``/`` replaced by ``--`` in the
    filename.

    No new credentials are required beyond ``GITHUB_TOKEN``.  The token must
    have the ``gist`` OAuth scope; a 403 response from ``create_gist`` raises
    :class:`~backlog_core.models.BacklogError` with a link to the settings
    page where the scope can be granted.

    Legacy issues using the inline ``<!-- artifact-manifest:begin/end -->``
    format are lazily migrated to Gist storage on first :meth:`get_manifest`
    call.

    Args:
        repo: GitHub repository slug in ``owner/name`` format.
        root_worktree: Absolute path to the DH state root directory.  Defaults
            to ``dh_paths.state_root()`` when not provided.

    Example::

        provider = GitHubGistArtifactProvider(repo="owner/myrepo")
        manifest = provider.get_manifest(965)
        print(manifest.artifacts)
    """

    def __init__(self, repo: str, root_worktree: Path | None = None) -> None:
        """Initialise provider with GitHub repository slug and state root path.

        Args:
            repo: ``owner/name`` repository slug.
            root_worktree: Absolute path to the DH state root for this project.
                When ``None``, resolved via :func:`dh_paths.state_root` (the
                ``~/.dh/projects/{slug}/`` directory).
        """
        self._repo = repo
        self._root_worktree = root_worktree if root_worktree is not None else _dh_paths.state_root()
        self._gist_cache: dict[int, Gist] = {}

    # ------------------------------------------------------------------
    # ArtifactBackend implementation
    # ------------------------------------------------------------------

    def get_manifest(self, item_id: ItemId) -> ArtifactManifest:
        """Retrieve the artifact manifest for *item_id*.

        Fetches the issue body via GraphQL and checks for a Gist sentinel
        comment.  If found, loads ``manifest.json`` from the Gist.  Legacy
        issues with an inline manifest section are lazily migrated — the
        inline block is replaced with a Gist sentinel on first access.
        Returns an empty manifest when no manifest data is present.

        Args:
            item_id: GitHub Issue number (positive integer).

        Returns:
            Parsed ``ArtifactManifest``.  Empty when no manifest is stored.

        Raises:
            backlog_core.models.GitHubUnavailableError: When ``GITHUB_TOKEN``
                is not set.
            backlog_core.models.BacklogError: On GraphQL API or gist-scope
                failures.
        """
        item_id = _require_int_item_id("GitHubGistArtifactProvider", item_id)
        try:
            repo = get_github(self._repo)
            owner, repo_name = self._repo.split("/", 1)
            issue = _fetch_issue_graphql(repo, owner, repo_name, item_id)
            body = issue.get("body") or ""

            # Current format: Gist-backed manifest.
            gist = self._get_gist(item_id, body)
            if gist is not None:
                gist_file = gist.files.get("manifest.json")
                if gist_file is not None:
                    return ArtifactManifest.model_validate_json(gist_file.content)
                return ArtifactManifest(issue_number=item_id)

            # Legacy inline manifest — lazy migration to Gist storage.
            if "<!-- artifact-manifest:begin -->" in body:
                manifest = parse_manifest_section(body, item_id)
                manifest_json = manifest.model_dump_json(by_alias=True)
                self._create_and_link_gist(
                    item_id, issue["id"], body, {"manifest.json": InputFileContent(manifest_json)}
                )
                return manifest

            return ArtifactManifest(issue_number=item_id)
        except GithubException as exc:
            msg = f"GitHub API error retrieving artifact manifest for item #{item_id}: {exc}"
            raise BacklogError(msg) from exc

    def set_manifest(self, item_id: ItemId, manifest: ArtifactManifest) -> None:
        """Persist *manifest* by writing it to the linked Gist.

        If no Gist exists yet, one is created and the issue body is updated
        with a sentinel comment ``<!-- artifact-gist:{gist_id} -->``.

        Args:
            item_id: GitHub Issue number (positive integer).
            manifest: Updated manifest to persist.

        Raises:
            backlog_core.models.GitHubUnavailableError: When ``GITHUB_TOKEN``
                is not set.
            backlog_core.models.BacklogError: On GraphQL API or gist-scope
                failures.
        """
        item_id = _require_int_item_id("GitHubGistArtifactProvider", item_id)
        try:
            repo = get_github(self._repo)
            owner, repo_name = self._repo.split("/", 1)
            issue = _fetch_issue_graphql(repo, owner, repo_name, item_id)
            body = issue.get("body") or ""

            # Stamp last_updated before serialising.
            manifest = manifest.model_copy(update={"last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
            manifest_json = manifest.model_dump_json(by_alias=True)

            gist = self._get_gist(item_id, body)
            if gist is not None:
                gist.edit(files={"manifest.json": InputFileContent(manifest_json)})
                return

            self._create_and_link_gist(item_id, issue["id"], body, {"manifest.json": InputFileContent(manifest_json)})
        except GithubException as exc:
            msg = f"GitHub API error persisting artifact manifest for item #{item_id}: {exc}"
            raise BacklogError(msg) from exc

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree filesystem.

        Validates that *path* resolves to a location inside the repository
        root (path traversal prevention via ``Path.resolve()``).  No
        directory prefix restriction is applied — any repo-relative path is
        accessible, including ``plan/``, ``research/``, and others.

        Args:
            path: Repo-relative path to the artifact file, e.g.
                ``plan/architect-foo.md`` or ``research/findings.md``.

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* resolves outside the repository root
                (path traversal detected).
            FileNotFoundError: When the resolved file does not exist.
        """
        self._validate_artifact_path(path)
        resolved = (self._root_worktree / path).resolve()
        return resolved.read_text(encoding="utf-8")

    def store_artifact_content(self, item_id: ItemId, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a file in the linked Gist.

        The artifact *path* is sanitised for use as a Gist filename by
        replacing ``/`` with ``--``.  If no Gist exists yet it is created and
        linked to the issue body before the file is added.

        Args:
            item_id: GitHub Issue number (positive integer).
            artifact_type: Artifact type string (e.g. ``"research"``).
                Not used in the Gist filename — *path* is the unique key.
            path: Repo-relative artifact path, e.g. ``plan/architect-foo.md``.
            content: Full artifact content to store.
        """
        item_id = _require_int_item_id("GitHubGistArtifactProvider", item_id)
        repo = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        issue = _fetch_issue_graphql(repo, owner, repo_name, item_id)
        body = issue.get("body") or ""

        gist = self._get_gist(item_id, body)
        if gist is None:
            gist = self._create_and_link_gist(item_id, issue["id"], body, {"manifest.json": InputFileContent("{}")})

        filename = _sanitize_gist_filename(path)
        gist.edit(files={filename: InputFileContent(content)})

    def read_artifact_content_from_remote(self, item_id: ItemId, artifact_type: str, path: str) -> str | None:
        """Read artifact content from the linked Gist.

        Sanitises *path* to a Gist filename and looks it up in the Gist file
        dictionary.  Returns ``None`` when no Gist is linked or the file is
        absent.

        Args:
            item_id: GitHub Issue number (positive integer).
            artifact_type: Artifact type string (not used for lookup — *path*
                is the unique key in the Gist).
            path: Repo-relative artifact path, e.g. ``plan/architect-foo.md``.

        Returns:
            Stored content string, or ``None`` when not found.
        """
        item_id = _require_int_item_id("GitHubGistArtifactProvider", item_id)
        repo = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        issue = _fetch_issue_graphql(repo, owner, repo_name, item_id)
        body = issue.get("body") or ""

        gist = self._get_gist(item_id, body)
        if gist is None:
            return None

        filename = _sanitize_gist_filename(path)
        gist_file = gist.files.get(filename)
        if gist_file is None:
            return None
        return gist_file.content

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content from the local filesystem.

        Validates the path for traversal attacks, then returns the file
        content or ``None`` when the file does not exist.  Does not require
        the path to start with ``plan/`` — this method supports auto-upload
        of any registered artifact whose local file is present.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not exist.

        Raises:
            ValueError: When *path* contains ``..`` components or resolves
                outside the repository root.
        """
        # Traversal check only — no plan/ prefix restriction here since
        # artifact types like "research" may live outside plan/.
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None
        if not candidate.exists():
            return None
        return candidate.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Path safety helpers
    # ------------------------------------------------------------------

    def _validate_artifact_path(self, path: str) -> None:
        """Raise ``ValueError`` when *path* fails the path traversal check.

        The resolved absolute path must be a descendant of
        ``self._root_worktree``.  No directory prefix restriction is applied —
        any repo-relative path (``plan/``, ``research/``, etc.) is permitted
        as long as it stays inside the repository root.

        Args:
            path: Repo-relative path string as provided by the caller.

        Raises:
            ValueError: When the resolved path escapes the repository root.
        """
        # Resolve the candidate path and check it stays under root_worktree.
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None

    def _get_gist(self, item_id: int, body: str) -> Gist | None:
        """Load the Gist for *item_id* from the cache or sentinel in *body*.

        Args:
            item_id: GitHub Issue number (positive integer).
            body: Current GitHub Issue body text to search for the sentinel.

        Returns:
            The Gist object, or ``None`` when no Gist is linked to this issue.
        """
        if item_id in self._gist_cache:
            return self._gist_cache[item_id]
        match = _GIST_SENTINEL_RE.search(body)
        if match:
            gh = _make_github_client()
            gist = gh.get_gist(match.group("gist_id"))
            self._gist_cache[item_id] = gist
            return gist
        return None

    def _create_and_link_gist(
        self, item_id: int, issue_id: str, body: str, initial_files: dict[str, InputFileContent]
    ) -> Gist:
        """Create a new private Gist, cache it, and write the sentinel to the issue.

        The sentinel ``<!-- artifact-gist:{gist_id} -->`` is written into the
        issue body — replacing the legacy inline manifest block when present or
        appending otherwise — via a GraphQL ``updateIssue`` mutation.

        Args:
            item_id: GitHub Issue number (used for the Gist description
                and instance cache key).
            issue_id: GitHub GraphQL node ID for the issue (used by
                :func:`_update_issue_graphql`).
            body: Current issue body text (used to detect legacy manifest
                blocks and build the updated body).
            initial_files: Initial Gist file set passed directly to
                ``create_gist``.

        Returns:
            The created Gist object.

        Raises:
            backlog_core.models.BacklogError: When the token is missing the
                ``gist`` OAuth scope (HTTP 403 from the Gist API).
            github.GithubException: On other GitHub API failures.
        """
        gh = _make_github_client()
        user = cast("AuthenticatedUser", gh.get_user())
        try:
            gist = user.create_gist(public=False, files=initial_files, description=f"artifact-manifest-item-{item_id}")
        except GithubException as exc:
            if exc.status == _GIST_FORBIDDEN_STATUS:
                msg = "GitHub token missing 'gist' scope — grant it at https://github.com/settings/tokens"
                raise BacklogError(msg) from exc
            raise
        self._gist_cache[item_id] = gist
        sentinel = f"<!-- artifact-gist:{gist.id} -->"
        new_body = _replace_old_manifest_with_sentinel(body, sentinel)
        repo = get_github(self._repo)
        _update_issue_graphql(repo, issue_id, body=new_body)
        return gist


GitHubArtifactProvider = GitHubGistArtifactProvider  # backward-compat alias


# ---------------------------------------------------------------------------
# LinearArtifactProvider
# ---------------------------------------------------------------------------

#: Maximum recommended manifest JSON size for Linear attachment metadata.
_LINEAR_MANIFEST_WARN_CHARS = 10_000


class LinearArtifactProvider:
    """Linear Attachments-backed implementation of :class:`ArtifactBackend`.

    Stores the artifact manifest and artifact file content as Linear
    Attachments on the issue, using the ``dh://`` URL scheme as an
    idempotency key.

    **Issue ID vs issue number**: Linear issue IDs are UUIDs.
    :func:`~backlog_core.linear_client.linear_get_attachments` and
    :func:`~backlog_core.linear_client.linear_create_attachment` accept
    ``issue_id: str``.  This provider passes ``str(issue_number)`` as the
    ``issue_id``.  This works when the ``issue_number`` stored in the backlog
    matches the Linear UUID for that issue.  Callers must ensure the
    ``issue_number`` field on their backlog items contains the Linear UUID,
    not the short human-readable sequence number.

    Args:
        api_key: Linear personal API key.  Must not be empty.
        team_id: Linear team identifier (UUID).  Stored for future use by
            team-scoped queries.
        root_worktree: Absolute path to the DH state root directory.
            Defaults to ``dh_paths.state_root()`` when not provided.

    Raises:
        ValueError: When *api_key* is empty.

    Example::

        provider = LinearArtifactProvider(api_key=os.environ["LINEAR_API_KEY"], team_id="team-uuid")
        manifest = provider.get_manifest("issue-uuid")
    """

    def __init__(self, api_key: str, team_id: str, root_worktree: Path | None = None) -> None:
        """Initialise provider with Linear credentials and state root path.

        Args:
            api_key: Linear personal API key.  Must not be empty.
            team_id: Linear team identifier (UUID).
            root_worktree: Absolute path to the DH state root for this
                project.  When ``None``, resolved via
                :func:`dh_paths.state_root`.

        Raises:
            ValueError: When *api_key* is empty.
        """
        if not api_key:
            msg = "LINEAR_API_KEY must not be empty"
            raise ValueError(msg)
        self._api_key = api_key
        self._team_id = team_id
        self._root_worktree = root_worktree or Path(_dh_paths.state_root())

    # ------------------------------------------------------------------
    # ArtifactBackend implementation
    # ------------------------------------------------------------------

    def get_manifest(self, item_id: ItemId) -> ArtifactManifest:
        """Retrieve the artifact manifest for *item_id*.

        Fetches all Linear attachments for the issue and looks for one
        whose URL matches ``dh://artifact-manifest/{item_id}``.
        Parses ``metadata["manifest_json"]`` and returns the result.
        Returns an empty manifest when no matching attachment exists.

        Args:
            item_id: Issue identifier — Linear issue UUID (string) or
                integer coerced to string via ``str(item_id)``.

        Returns:
            Parsed ``ArtifactManifest``.  Empty when no manifest attachment
            is stored.

        Raises:
            backlog_core.models.BacklogError: On Linear API failures.
        """
        target_url = f"dh://artifact-manifest/{item_id}"
        nodes = linear_get_attachments(self._api_key, str(item_id))
        for node in nodes:
            if node.get("url") == target_url:
                raw_metadata = node.get("metadata")
                if isinstance(raw_metadata, dict):
                    metadata = cast("dict[str, object]", raw_metadata)
                    manifest_json = metadata.get("manifest_json")
                    if isinstance(manifest_json, str):
                        return ArtifactManifest.model_validate_json(manifest_json)
        return ArtifactManifest(issue_number=item_id)

    def set_manifest(self, item_id: ItemId, manifest: ArtifactManifest) -> None:
        """Persist *manifest* as a Linear attachment on *item_id*.

        Serialises the manifest to JSON and creates (or upserts) a Linear
        attachment with URL ``dh://artifact-manifest/{item_id}``.
        Linear treats the same URL on the same issue as idempotent — the
        existing attachment is updated rather than duplicated.

        Logs a warning when the serialised manifest exceeds
        ``_LINEAR_MANIFEST_WARN_CHARS`` characters, as Linear attachment
        metadata has undocumented size limits.

        Args:
            item_id: Issue identifier — Linear issue UUID (string) or
                integer coerced to string via ``str(item_id)``.
            manifest: Updated manifest to persist.

        Raises:
            backlog_core.models.BacklogError: On Linear API failures.
        """
        manifest_json = manifest.model_dump_json(by_alias=True)
        if len(manifest_json) > _LINEAR_MANIFEST_WARN_CHARS:
            logger.warning("Linear manifest exceeds 10K chars; truncation risk (size=%d)", len(manifest_json))
        linear_create_attachment(
            self._api_key,
            str(item_id),
            url=f"dh://artifact-manifest/{item_id}",
            title="DH Artifact Manifest",
            metadata={"manifest_json": manifest_json},
        )

    def store_artifact_content(self, item_id: ItemId, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a Linear attachment on *item_id*.

        Creates (or upserts) a Linear attachment using the URL scheme
        ``dh://artifact-content/{item_id}/{artifact_type}/{safe_path}``
        where ``safe_path`` has ``/`` replaced with ``--``.

        Args:
            item_id: Issue identifier — Linear issue UUID (string) or
                integer coerced to string via ``str(item_id)``.
            artifact_type: Artifact type string, e.g. ``"research"``.
            path: Repo-relative artifact path, e.g.
                ``plan/architect-foo.md``.
            content: Full artifact content to store.

        Raises:
            backlog_core.models.BacklogError: On Linear API failures.
        """
        safe_path = path.replace("/", "--")
        url = f"dh://artifact-content/{item_id}/{artifact_type}/{safe_path}"
        linear_create_attachment(
            self._api_key,
            str(item_id),
            url=url,
            title=f"DH Artifact: {artifact_type}/{path}",
            metadata={"content": content},
        )

    def read_artifact_content_from_remote(self, item_id: ItemId, artifact_type: str, path: str) -> str | None:
        """Read artifact content from a Linear attachment.

        Sanitises *path* to the ``dh://`` URL form and scans all
        attachments for the issue looking for a match.  Returns the
        ``metadata["content"]`` value when found.

        Args:
            item_id: Issue identifier — Linear issue UUID (string) or
                integer coerced to string via ``str(item_id)``.
            artifact_type: Artifact type string to match.
            path: Repo-relative artifact path to match.

        Returns:
            Stored content string, or ``None`` when no matching attachment
            exists.

        Raises:
            backlog_core.models.BacklogError: On Linear API failures.
        """
        safe_path = path.replace("/", "--")
        target_url = f"dh://artifact-content/{item_id}/{artifact_type}/{safe_path}"
        nodes = linear_get_attachments(self._api_key, str(item_id))
        for node in nodes:
            if node.get("url") == target_url:
                raw_metadata = node.get("metadata")
                if isinstance(raw_metadata, dict):
                    metadata = cast("dict[str, object]", raw_metadata)
                    content = metadata.get("content")
                    if isinstance(content, str):
                        return content
        return None

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree filesystem.

        Validates that *path* resolves to a location inside the repository
        root (path traversal prevention via ``Path.resolve()``).

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* resolves outside the repository root
                (path traversal detected).
            FileNotFoundError: When the resolved file does not exist.
        """
        self._validate_artifact_path(path)
        resolved = (self._root_worktree / path).resolve()
        return resolved.read_text(encoding="utf-8")

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content from the local filesystem.

        Validates the path for traversal attacks, then returns the file
        content or ``None`` when the file does not exist.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not
            exist.

        Raises:
            ValueError: When *path* contains ``..`` components or resolves
                outside the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None
        if not candidate.exists():
            return None
        return candidate.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Path safety helpers
    # ------------------------------------------------------------------

    def _validate_artifact_path(self, path: str) -> None:
        """Raise ``ValueError`` when *path* fails the path traversal check.

        Args:
            path: Repo-relative path string as provided by the caller.

        Raises:
            ValueError: When the resolved path escapes the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None


# ---------------------------------------------------------------------------
# GitLabArtifactProvider
# ---------------------------------------------------------------------------

#: Regex matching the snippet sentinel comment that links an issue to its snippet.
#: Captures the ``snippet_id`` group (integer).
_SNIPPET_SENTINEL_RE = re.compile(r"<!-- artifact-snippet:(?P<snippet_id>\d+) -->")


class GitLabArtifactProvider:
    """GitLab Snippets-backed implementation of :class:`ArtifactBackend`.

    Stores the artifact manifest as a JSON file inside a private GitLab project
    snippet.  The snippet is linked to the issue via a note (comment) containing
    the sentinel ``<!-- artifact-snippet:{snippet_id} -->``.

    Artifact file content (research, plan documents, etc.) is stored as
    additional files in the same snippet with ``/`` replaced by ``--`` in the
    filename and ``.txt`` appended.

    Args:
        project_id: GitLab project ID (integer).
        private_token: GitLab personal access token.  Must not be empty.
        gitlab_url: GitLab instance base URL.  Defaults to ``https://gitlab.com``.
        root_worktree: Absolute path to the DH state root directory.  Defaults
            to ``dh_paths.state_root()`` when not provided.

    Raises:
        ValueError: When *private_token* is empty.

    Example::

        provider = GitLabArtifactProvider(project_id=42, private_token=os.environ["GITLAB_TOKEN"])
        manifest = provider.get_manifest(965)
        print(manifest.artifacts)
    """

    def __init__(
        self,
        project_id: int,
        private_token: str,
        gitlab_url: str = "https://gitlab.com",
        root_worktree: Path | None = None,
    ) -> None:
        """Initialise provider with GitLab credentials and state root path.

        Args:
            project_id: GitLab project ID (integer).
            private_token: GitLab personal access token.  Must not be empty.
            gitlab_url: GitLab instance base URL.
            root_worktree: Absolute path to the DH state root for this project.
                When ``None``, resolved via :func:`dh_paths.state_root`.

        Raises:
            ValueError: When *private_token* is empty.
        """
        if not private_token:
            msg = "GITLAB_TOKEN must not be empty"
            raise ValueError(msg)
        self._project_id = project_id
        self._private_token = private_token
        self._gitlab_url = gitlab_url.rstrip("/")
        self._root_worktree = root_worktree or Path(_dh_paths.state_root())
        self._snippet_cache: dict[int, int] = {}

    # ------------------------------------------------------------------
    # ArtifactBackend implementation
    # ------------------------------------------------------------------

    def get_manifest(self, item_id: ItemId) -> ArtifactManifest:
        """Retrieve the artifact manifest for *item_id*.

        Lists issue notes and scans for a snippet sentinel comment.  If found,
        loads ``manifest.json`` from the linked snippet.  Returns an empty
        manifest when no manifest data is present.

        Args:
            item_id: GitLab issue IID (positive integer).

        Returns:
            Parsed ``ArtifactManifest``.  Empty when no manifest is stored.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        item_id = _require_int_item_id("GitLabArtifactProvider", item_id)
        snippet_id = self._get_snippet_id_from_notes(item_id)
        if snippet_id is None:
            return ArtifactManifest(issue_number=item_id)

        self._snippet_cache[item_id] = snippet_id
        snippet = gitlab_get_snippet(self._project_id, snippet_id, self._private_token, self._gitlab_url)
        manifest_json = snippet["files_content"].get("manifest.json")
        if manifest_json is None:
            return ArtifactManifest(issue_number=item_id)
        return ArtifactManifest.model_validate_json(manifest_json)

    def set_manifest(self, item_id: ItemId, manifest: ArtifactManifest) -> None:
        """Persist *manifest* by writing it to the linked snippet.

        If no snippet exists yet, one is created and a sentinel note is posted
        on the issue.

        Args:
            item_id: GitLab issue IID (positive integer).
            manifest: Updated manifest to persist.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        item_id = _require_int_item_id("GitLabArtifactProvider", item_id)
        manifest_json = manifest.model_dump_json(by_alias=True)
        snippet_id = self._get_or_create_snippet(item_id)
        gitlab_update_snippet(
            self._project_id,
            snippet_id,
            self._private_token,
            self._gitlab_url,
            files=[{"action": "update", "file_path": "manifest.json", "content": manifest_json}],
        )

    def store_artifact_content(self, item_id: ItemId, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a file in the linked snippet.

        The artifact *path* is sanitised for use as a snippet filename by
        replacing ``/`` with ``--`` and appending ``.txt``.  If no snippet
        exists yet it is created and linked to the issue before the file is
        added.

        Args:
            item_id: GitLab issue IID (positive integer).
            artifact_type: Artifact type string (e.g. ``"research"``).
                Not used in the snippet filename — *path* is the unique key.
            path: Repo-relative artifact path, e.g. ``plan/architect-foo.md``.
            content: Full artifact content to store.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        item_id = _require_int_item_id("GitLabArtifactProvider", item_id)
        safe_path = path.replace("/", "--") + ".txt"
        snippet_id = self._get_or_create_snippet(item_id)
        # Attempt update; if the file does not yet exist, create it instead.
        try:
            gitlab_update_snippet(
                self._project_id,
                snippet_id,
                self._private_token,
                self._gitlab_url,
                files=[{"action": "update", "file_path": safe_path, "content": content}],
            )
        except BacklogError:
            gitlab_update_snippet(
                self._project_id,
                snippet_id,
                self._private_token,
                self._gitlab_url,
                files=[{"action": "create", "file_path": safe_path, "content": content}],
            )

    def read_artifact_content_from_remote(self, item_id: ItemId, artifact_type: str, path: str) -> str | None:
        """Read artifact content from the linked snippet.

        Sanitises *path* to the snippet filename form and looks it up in the
        snippet file dictionary.  Returns ``None`` when no snippet is linked or
        the file is absent.

        Args:
            item_id: GitLab issue IID (positive integer).
            artifact_type: Artifact type string (not used for lookup — *path*
                is the unique key in the snippet).
            path: Repo-relative artifact path, e.g. ``plan/architect-foo.md``.

        Returns:
            Stored content string, or ``None`` when not found.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        item_id = _require_int_item_id("GitLabArtifactProvider", item_id)
        safe_path = path.replace("/", "--") + ".txt"
        snippet_id = self._get_snippet_id_from_notes(item_id)
        if snippet_id is None:
            return None
        snippet = gitlab_get_snippet(self._project_id, snippet_id, self._private_token, self._gitlab_url)
        return snippet["files_content"].get(safe_path)

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree filesystem.

        Validates that *path* resolves to a location inside the repository
        root (path traversal prevention via ``Path.resolve()``).

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* resolves outside the repository root
                (path traversal detected).
            FileNotFoundError: When the resolved file does not exist.
        """
        self._validate_artifact_path(path)
        resolved = (self._root_worktree / path).resolve()
        return resolved.read_text(encoding="utf-8")

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content from the local filesystem.

        Validates the path for traversal attacks, then returns the file
        content or ``None`` when the file does not exist.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not exist.

        Raises:
            ValueError: When *path* contains ``..`` components or resolves
                outside the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None
        if not candidate.exists():
            return None
        return candidate.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Path safety helpers
    # ------------------------------------------------------------------

    def _validate_artifact_path(self, path: str) -> None:
        """Raise ``ValueError`` when *path* fails the path traversal check.

        Args:
            path: Repo-relative path string as provided by the caller.

        Raises:
            ValueError: When the resolved path escapes the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None

    # ------------------------------------------------------------------
    # Snippet linkage helpers
    # ------------------------------------------------------------------

    def _get_snippet_id_from_notes(self, item_id: int) -> int | None:
        """Scan issue notes for the snippet sentinel and return the snippet ID.

        Args:
            item_id: GitLab issue IID (positive integer).

        Returns:
            Integer snippet ID when found, or ``None`` when no sentinel note
            exists.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        if item_id in self._snippet_cache:
            return self._snippet_cache[item_id]
        notes = gitlab_list_issue_notes(self._project_id, item_id, self._private_token, self._gitlab_url)
        for note in notes:
            body = note.get("body") or ""
            match = _SNIPPET_SENTINEL_RE.search(body)
            if match:
                snippet_id = int(match.group("snippet_id"))
                self._snippet_cache[item_id] = snippet_id
                return snippet_id
        return None

    def _get_or_create_snippet(self, item_id: int) -> int:
        """Return the snippet ID for *item_id*, creating one if absent.

        Checks the in-memory cache first, then scans issue notes.  When no
        snippet exists, creates a new private snippet with an empty
        ``manifest.json`` and posts a sentinel note on the issue.

        Args:
            item_id: GitLab issue IID (positive integer).

        Returns:
            Integer snippet ID.

        Raises:
            backlog_core.models.BacklogError: On GitLab API failures.
        """
        cached = self._get_snippet_id_from_notes(item_id)
        if cached is not None:
            return cached

        result = gitlab_create_snippet(
            self._project_id,
            self._private_token,
            self._gitlab_url,
            title=f"dh-artifact-manifest-item-{item_id}",
            files=[{"file_path": "manifest.json", "content": "{}"}],
            visibility="private",
        )
        snippet_id: int = result["id"]
        self._snippet_cache[item_id] = snippet_id

        sentinel = f"<!-- artifact-snippet:{snippet_id} -->"
        gitlab_create_issue_note(self._project_id, item_id, self._private_token, self._gitlab_url, body=sentinel)
        return snippet_id


def create_artifact_provider(
    backend_name: str | None = None, repo: str | None = None, root_worktree: Path | None = None
) -> ArtifactBackend:
    """Create an ArtifactBackend provider based on backend config.

    Args:
        backend_name: Override backend name. When None, reads BACKLOG_BACKEND env var,
            then falls back to ``github``.
        repo: GitHub repo slug (``owner/name``). Required for GitHub backend.
        root_worktree: Local filesystem root for artifact content reads.

    Returns:
        Configured ArtifactBackend provider instance.

    Raises:
        BacklogError: For non-remote backends (sqlite, memory) or missing credentials.
    """
    resolved = backend_name or os.environ.get("BACKLOG_BACKEND") or "github"
    if resolved in {BackendName.github, "github"}:
        if not repo:
            msg = "GitHub artifact backend requires repo (owner/name)"
            raise BacklogError(msg)
        return GitHubGistArtifactProvider(repo=repo, root_worktree=root_worktree)
    if resolved in {BackendName.linear, "linear"}:
        api_key = os.environ.get("LINEAR_API_KEY", "")
        team_id = os.environ.get("LINEAR_TEAM_ID", "")
        if not api_key:
            msg = "LINEAR_API_KEY env var is required for Linear backend"
            raise BacklogError(msg)
        return LinearArtifactProvider(api_key=api_key, team_id=team_id, root_worktree=root_worktree)
    if resolved in {BackendName.gitlab, "gitlab"}:
        private_token = os.environ.get("GITLAB_TOKEN", "")
        project_id_str = os.environ.get("GITLAB_PROJECT_ID", "")
        gitlab_url = os.environ.get("GITLAB_URL", "https://gitlab.com")
        if not private_token:
            msg = "GITLAB_TOKEN env var is required for GitLab backend"
            raise BacklogError(msg)
        if not project_id_str:
            msg = "GITLAB_PROJECT_ID env var is required for GitLab backend"
            raise BacklogError(msg)
        return GitLabArtifactProvider(
            project_id=int(project_id_str),
            private_token=private_token,
            gitlab_url=gitlab_url,
            root_worktree=root_worktree,
        )
    if resolved in {BackendName.beads, "beads"}:
        from .backends.beads_artifact_provider import BeadsArtifactProvider  # noqa: PLC0415

        return BeadsArtifactProvider()
    if resolved in {BackendName.local, "local"}:
        return LocalFilesystemArtifactProvider(
            root_worktree=root_worktree or _dh_paths.git_project_root(), manifest_dir=None
        )
    if resolved in {BackendName.sqlite, BackendName.memory, "sqlite", "memory"}:
        msg = f"Backend '{resolved}' does not support artifact storage. Use github, linear, or gitlab."
        raise BacklogError(msg)
    msg = f"Unknown artifact backend: '{resolved}'"
    raise BacklogError(msg)
