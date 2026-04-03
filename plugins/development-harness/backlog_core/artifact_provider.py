"""Backend abstraction for artifact manifest storage.

Defines the ``ArtifactBackend`` protocol and the ``GitHubArtifactProvider``
implementation that stores manifest data in GitHub Issue bodies.

The manifest is stored as a markdown table delimited by HTML comment markers
inside the issue body, making it human-readable when browsing GitHub and
machine-parseable by the MCP tools.

Manifest section format in issue body::

    ## Artifact Manifest

    <!-- artifact-manifest:begin -->
    | Type | Path | Status | Agent | Created |
    |------|------|--------|-------|---------|
    | feature-context | plan/feature-context-foo.md | current | feature-researcher | 2026-03-21T10:00:00Z |
    <!-- artifact-manifest:end -->

Artifact content comments in issue comments::

    <!-- artifact-content:type=research:path=research/artifact.md -->
    <details>
    <summary>Artifact: research — research/artifact.md</summary>

    {content here}

    </details>
    <!-- /artifact-content -->

Parse/render helpers are consolidated in :mod:`backlog_core.artifact_registry`.
This module imports them from there.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .artifact_registry import parse_manifest_section, render_manifest_section, replace_manifest_in_body
from .gh_client import (
    _add_comment_graphql,
    _fetch_issue_comments_graphql,
    _fetch_issue_graphql,
    _update_issue_comment_graphql,
    _update_issue_graphql,
    get_github,
)

# dh_paths lives one level above backlog_core (at plugin root).
_plugin_root = Path(__file__).parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import dh_paths as _dh_paths

if TYPE_CHECKING:
    from .models import ArtifactManifest

# Re-export so callers that imported these from artifact_provider continue to work.
__all__ = [
    "ArtifactBackend",
    "GitHubArtifactProvider",
    "parse_manifest_section",
    "render_manifest_section",
    "replace_manifest_in_body",
]


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

    def get_manifest(self, issue_number: int) -> ArtifactManifest:
        """Retrieve the artifact manifest for *issue_number*.

        Args:
            issue_number: GitHub Issue number (positive integer).

        Returns:
            ``ArtifactManifest`` for the issue.  Returns an empty manifest
            (no artifacts) when the issue has no manifest section — this is
            not an error.
        """
        ...

    def set_manifest(self, issue_number: int, manifest: ArtifactManifest) -> None:
        """Persist *manifest* for *issue_number*.

        Replaces any existing manifest section; creates one if absent.

        Args:
            issue_number: GitHub Issue number (positive integer).
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

    def store_artifact_content(self, issue_number: int, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a GitHub issue comment.

        Creates a structured collapsible comment identified by
        ``artifact-content:type={artifact_type}:path={path}``.  When a
        comment with the same type and path already exists it is edited
        in-place rather than duplicated.

        If *content* exceeds the GitHub comment size limit
        (``_GITHUB_COMMENT_MAX_CHARS``), it is truncated and a warning
        notice is appended.

        Args:
            issue_number: GitHub Issue number (positive integer).
            artifact_type: Artifact type string, e.g. ``"research"``.
            path: Repo-relative path used as the comment identifier.
            content: Full artifact content to store.
        """
        ...

    def read_artifact_content_from_github(self, issue_number: int, artifact_type: str, path: str) -> str | None:
        """Search issue comments for stored artifact content.

        Scans the issue's comments for an artifact content block whose
        ``type`` and ``path`` match the given arguments.

        Args:
            issue_number: GitHub Issue number (positive integer).
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


class GitHubArtifactProvider:
    """GitHub-backed implementation of :class:`ArtifactBackend`.

    Reads and writes the artifact manifest section inside GitHub Issue bodies
    using the existing PyGithub + GraphQL helpers from ``backlog_core.gh_client``.
    No new credentials are required — the same ``GITHUB_TOKEN`` used by other
    backlog operations is reused.

    Artifact file content is served from the DH state root
    (``~/.dh/projects/{slug}/``).  Artifact paths stored in the manifest are
    relative to this state root rather than the git project root.  Worktree-
    isolated agents access content via the ``artifact_read`` MCP tool rather
    than the filesystem.

    Args:
        repo: GitHub repository slug in ``owner/name`` format.
        root_worktree: Absolute path to the state root directory.  Defaults
            to ``dh_paths.state_root()`` when not provided.

    Example::

        provider = GitHubArtifactProvider(repo="owner/myrepo")
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

    # ------------------------------------------------------------------
    # ArtifactBackend implementation
    # ------------------------------------------------------------------

    def get_manifest(self, issue_number: int) -> ArtifactManifest:
        """Retrieve the artifact manifest from the GitHub Issue body.

        Fetches the issue body via GraphQL, then extracts and parses
        the ``<!-- artifact-manifest:begin/end -->`` section.  Returns an
        empty manifest when the section is absent.

        Args:
            issue_number: GitHub Issue number (positive integer).

        Returns:
            Parsed ``ArtifactManifest``.  Empty (no artifacts) when the
            issue body contains no manifest section.

        Raises:
            backlog_core.models.GitHubUnavailableError: When ``GITHUB_TOKEN``
                is not set.
            backlog_core.models.BacklogError: On GraphQL API failures.
        """
        repo_obj = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        issue = _fetch_issue_graphql(repo_obj, owner, repo_name, issue_number)
        body = issue.get("body") or ""
        return parse_manifest_section(body, issue_number)

    def set_manifest(self, issue_number: int, manifest: ArtifactManifest) -> None:
        """Persist the manifest by updating the GitHub Issue body.

        Renders the manifest as a markdown table, then replaces the existing
        manifest section in the issue body (or appends it if absent) via a
        GraphQL ``updateIssue`` mutation.

        Args:
            issue_number: GitHub Issue number (positive integer).
            manifest: Updated manifest to persist.

        Raises:
            backlog_core.models.GitHubUnavailableError: When ``GITHUB_TOKEN``
                is not set.
            backlog_core.models.BacklogError: On GraphQL API failures.
        """
        repo_obj = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        issue = _fetch_issue_graphql(repo_obj, owner, repo_name, issue_number)
        current_body = issue.get("body") or ""

        # Stamp last_updated before rendering
        manifest = manifest.model_copy(update={"last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
        rendered = render_manifest_section(manifest)
        new_body = replace_manifest_in_body(current_body, rendered)

        if new_body != current_body:
            _update_issue_graphql(repo_obj, issue["id"], body=new_body)

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

    def store_artifact_content(self, issue_number: int, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a GitHub issue comment.

        Creates or updates a collapsible comment identified by the
        ``<!-- artifact-content:type=...:path=... -->`` markers.  If a
        matching comment already exists it is edited in-place via GraphQL
        ``updateIssueComment`` mutation.

        Content exceeding ``_GITHUB_COMMENT_MAX_CHARS`` is truncated with a
        warning notice appended so the comment stays within GitHub's limit.

        Args:
            issue_number: GitHub Issue number (positive integer).
            artifact_type: Artifact type string, e.g. ``"research"``.
            path: Repo-relative path used as the comment identifier.
            content: Full artifact content to store.
        """
        repo_obj = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        issue = _fetch_issue_graphql(repo_obj, owner, repo_name, issue_number)
        comment_body = _build_artifact_content_comment(artifact_type, path, content)

        # Search for an existing comment to update in-place via GraphQL.
        comments = _fetch_issue_comments_graphql(repo_obj, owner, repo_name, issue_number)
        for comment in comments:
            tag_match = _ARTIFACT_CONTENT_TAG_RE.match(comment.get("body") or "")
            if tag_match and tag_match.group("type") == artifact_type and tag_match.group("path") == path:
                _update_issue_comment_graphql(repo_obj, comment["id"], comment_body)
                return

        _add_comment_graphql(repo_obj, issue["id"], comment_body)

    def read_artifact_content_from_github(self, issue_number: int, artifact_type: str, path: str) -> str | None:
        """Search issue comments for stored artifact content.

        Scans the issue's comments via GraphQL for an artifact content block
        whose ``type`` and ``path`` match the given arguments.

        Args:
            issue_number: GitHub Issue number (positive integer).
            artifact_type: Artifact type string to match.
            path: Repo-relative path to match.

        Returns:
            The stored content string when found, or ``None`` when no
            matching comment exists.
        """
        repo_obj = get_github(self._repo)
        owner, repo_name = self._repo.split("/", 1)
        comments = _fetch_issue_comments_graphql(repo_obj, owner, repo_name, issue_number)

        for comment in comments:
            body = comment.get("body") or ""
            tag_match = _ARTIFACT_CONTENT_TAG_RE.match(body)
            if tag_match and tag_match.group("type") == artifact_type and tag_match.group("path") == path:
                return _extract_content_from_comment(body)

        return None

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
            raise ValueError(f"Path traversal detected: {path!r} resolves outside the repository root.") from None
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
            raise ValueError(f"Path traversal detected: {path!r} resolves outside the repository root.") from None
