"""Tests for artifact content storage and retrieval via GitHub issue comments.

Covers:
- _build_artifact_content_comment: structure, truncation
- _extract_content_from_comment: happy path, malformed input
- GitHubArtifactProvider.store_artifact_content: create new, update existing
- GitHubArtifactProvider.read_artifact_content_from_remote: found, not found
- artifact_register MCP tool: with content (tier 1), auto-read local file (tier 2), no content/no file (tier 3)
- artifact_read MCP tool: GitHub-first, filesystem fallback, neither available

All GitHub API calls are mocked at the ``_graphql_request`` boundary
(``backlog_core.gh_client._graphql_request``) using fixture factories from
``tests.graphql_factories``.  No PyGithub REST mocks remain in this file.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure graphql_factories is importable regardless of pytest invocation path.
_tests_dir = Path(__file__).parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from backlog_core.artifact_provider import (
    _GITHUB_COMMENT_MAX_CHARS,
    GitHubArtifactProvider,
    _build_artifact_content_comment,
    _extract_content_from_comment,
)
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType
from backlog_core.server import mcp
from graphql_factories import (
    make_issue_by_number_response,
    make_issue_comment_node,
    make_issue_comments_response,
    make_issue_node,
    make_update_issue_response,
)

from tests.helpers import call_mcp_tool

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


def _make_mock_repo() -> MagicMock:
    """Return a minimal MagicMock suitable as a PyGithub Repository object.

    Returns:
        MagicMock with no pre-configured attributes — _graphql_request is
        mocked at the module level, so the repo object is only passed through.
    """
    return MagicMock()


# ---------------------------------------------------------------------------
# _build_artifact_content_comment
# ---------------------------------------------------------------------------


def test_build_artifact_content_comment_contains_opening_tag() -> None:
    """Verify the opening artifact-content HTML comment tag is present.

    Tests: _build_artifact_content_comment structure.
    How: Build a comment and check for the opening marker string.
    Why: The tag is used by the search logic to identify matching comments.
    """
    # Arrange
    artifact_type = "research"
    path = "plan/research-foo.md"
    content = "Some content"

    # Act
    result = _build_artifact_content_comment(artifact_type, path, content)

    # Assert
    assert "<!-- artifact-content:type=research:path=plan/research-foo.md -->" in result


def test_build_artifact_content_comment_contains_closing_tag() -> None:
    """Verify the closing artifact-content HTML comment tag is present.

    Tests: _build_artifact_content_comment structure.
    How: Build a comment and check for the closing delimiter.
    Why: The closing tag bounds the extractable content block.
    """
    # Arrange / Act
    result = _build_artifact_content_comment("research", "plan/foo.md", "content")

    # Assert
    assert "<!-- /artifact-content -->" in result


def test_build_artifact_content_comment_contains_details_block() -> None:
    """Verify the comment wraps content in an HTML details/summary block.

    Tests: _build_artifact_content_comment structure.
    How: Check for <details> and <summary> HTML elements.
    Why: Keeps GitHub issues visually uncluttered while storing machine-parseable content.
    """
    # Arrange / Act
    result = _build_artifact_content_comment("architect", "plan/arch.md", "# Architecture")

    # Assert
    assert "<details>" in result
    assert "</details>" in result
    assert "<summary>" in result


def test_build_artifact_content_comment_embeds_content() -> None:
    """Verify the artifact content is embedded verbatim in the comment.

    Tests: _build_artifact_content_comment content embedding.
    How: Build comment and assert content string appears in result.
    Why: The stored content must be retrievable by _extract_content_from_comment.
    """
    # Arrange
    content = "This is the artifact body text."

    # Act
    result = _build_artifact_content_comment("feature-context", "plan/fc.md", content)

    # Assert
    assert content in result


def test_build_artifact_content_comment_truncates_oversized_content() -> None:
    """Verify oversized content is truncated to stay within GitHub's limit.

    Tests: _build_artifact_content_comment truncation.
    How: Pass content larger than _GITHUB_COMMENT_MAX_CHARS and verify result fits.
    Why: GitHub rejects comments exceeding 65536 characters.
    """
    # Arrange — content large enough to exceed the GitHub limit
    oversized = "x" * (_GITHUB_COMMENT_MAX_CHARS + 1000)

    # Act
    result = _build_artifact_content_comment("research", "plan/big.md", oversized)

    # Assert — result must be within the limit
    assert len(result) <= _GITHUB_COMMENT_MAX_CHARS
    assert "WARNING: content truncated" in result


def test_build_artifact_content_comment_does_not_truncate_within_limit() -> None:
    """Verify content within the size limit is stored unmodified.

    Tests: _build_artifact_content_comment no-truncation path.
    How: Pass small content and verify no WARNING marker appears.
    Why: Normal-sized artifacts should round-trip without modification.
    """
    # Arrange — content well within limit
    content = "Small content"

    # Act
    result = _build_artifact_content_comment("research", "plan/small.md", content)

    # Assert — no truncation warning
    assert "WARNING" not in result
    assert content in result


# ---------------------------------------------------------------------------
# _extract_content_from_comment
# ---------------------------------------------------------------------------


def test_extract_content_from_comment_returns_inner_content() -> None:
    """Verify inner content is extracted from a well-formed comment body.

    Tests: _extract_content_from_comment happy path.
    How: Build a comment body with standard structure, extract, verify content present.
    Why: Round-trip correctness — stored content must be recoverable.
    """
    # Arrange
    comment_body = (
        "<!-- artifact-content:type=research:path=plan/foo.md -->\n"
        "<details>\n"
        "<summary>Artifact: research — plan/foo.md</summary>\n\n"
        "# Research findings\n\nSome text here.\n\n"
        "</details>\n"
        "<!-- /artifact-content -->"
    )

    # Act
    result = _extract_content_from_comment(comment_body)

    # Assert
    assert "# Research findings" in result
    assert "Some text here." in result


def test_extract_content_from_comment_strips_surrounding_whitespace() -> None:
    """Verify extracted content has surrounding whitespace stripped.

    Tests: _extract_content_from_comment whitespace handling.
    How: Embed content with leading/trailing spaces, check result is stripped.
    Why: Whitespace normalisation prevents spurious diffs in callers.
    """
    # Arrange
    comment_body = (
        "<!-- artifact-content:type=research:path=plan/foo.md -->\n"
        "<details>\n"
        "<summary>summary</summary>\n\n"
        "  actual content  \n\n"
        "</details>\n"
        "<!-- /artifact-content -->"
    )

    # Act
    result = _extract_content_from_comment(comment_body)

    # Assert
    assert result == "actual content"


def test_extract_content_from_comment_returns_full_body_when_malformed() -> None:
    """Verify malformed comments return the full body rather than raising.

    Tests: _extract_content_from_comment fallback on missing </summary> or </details>.
    How: Pass a body without the expected HTML structure, verify identity return.
    Why: Graceful degradation — callers can inspect the raw body instead of crashing.
    """
    # Arrange — no </summary> or </details> tags
    malformed = "<!-- artifact-content:type=x:path=y -->\nsome raw text\n<!-- /artifact-content -->"

    # Act
    result = _extract_content_from_comment(malformed)

    # Assert — returns the full body rather than raising
    assert result == malformed


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.store_artifact_content
# ---------------------------------------------------------------------------


def test_store_artifact_content_creates_new_gist_when_none_exists(tmp_path: Path) -> None:
    """Verify a new Gist is created and linked when no Gist sentinel exists in the issue body.

    Tests: GitHubGistArtifactProvider.store_artifact_content — create path.
    How: Mock _graphql_request with issue-fetch (no sentinel in body) + update-issue responses.
         Mock _make_github_client so create_gist returns a fake Gist.
         Assert gist.edit() is called with the sanitised filename and content.
    Why: When no Gist is linked to the issue, a new Gist must be created and its ID
         written into the issue body as a sentinel comment.
    """
    # Arrange — issue body has no sentinel, so a new Gist will be created.
    mock_repo = _make_mock_repo()
    issue_node = make_issue_node(number=42, id="I_42", body="No sentinel here.")
    mock_gist = MagicMock()
    mock_gist.id = "abc123deadbeef00"
    mock_gh_client = MagicMock()
    mock_gh_client.get_user.return_value.create_gist.return_value = mock_gist

    responses = [
        make_issue_by_number_response(issue_node),  # _fetch_issue_graphql
        make_update_issue_response(),  # _update_issue_graphql (writes sentinel)
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=mock_repo),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
        patch("backlog_core.artifact_provider._make_github_client", return_value=mock_gh_client),
    ):
        # Act
        provider.store_artifact_content(42, "research", "plan/foo.md", "# Content")

    # Assert — exactly 2 _graphql_request calls: fetch issue + update issue body with sentinel
    assert mock_gql.call_count == 2
    # Gist edit called with sanitised filename (/ → --) and correct content
    mock_gist.edit.assert_called_once()
    edit_files_arg: dict = mock_gist.edit.call_args[1].get("files") or mock_gist.edit.call_args[0][0]
    assert "plan--foo.md" in edit_files_arg
    assert "# Content" in edit_files_arg["plan--foo.md"]._InputFileContent__content


def test_store_artifact_content_updates_existing_gist_file_in_place(tmp_path: Path) -> None:
    """Verify an existing Gist file is edited in-place when a Gist sentinel exists.

    Tests: GitHubGistArtifactProvider.store_artifact_content — update path.
    How: Issue body contains a Gist sentinel; mock _make_github_client so get_gist()
         returns a pre-existing Gist mock. Assert gist.edit() is called with new content.
    Why: When a Gist is already linked, only one _graphql_request call (fetch) is needed
         and the Gist file is updated via gist.edit() — no new Gist is created.
    """
    # Arrange — issue body contains the Gist sentinel.
    gist_id = "1234abc5def6cafe"
    issue_body = f"Some existing body.\n\n<!-- artifact-gist:{gist_id} -->"
    issue_node = make_issue_node(number=42, id="I_42", body=issue_body)

    mock_gist = MagicMock()
    mock_gist.id = gist_id
    mock_gh_client = MagicMock()
    mock_gh_client.get_gist.return_value = mock_gist

    responses = [
        make_issue_by_number_response(issue_node)  # _fetch_issue_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
        patch("backlog_core.artifact_provider._make_github_client", return_value=mock_gh_client),
    ):
        # Act
        provider.store_artifact_content(42, "research", "plan/foo.md", "new content")

    # Assert — exactly 1 _graphql_request call (fetch issue); gist.edit() writes content
    assert mock_gql.call_count == 1
    mock_gist.edit.assert_called_once()
    edit_files_arg: dict = mock_gist.edit.call_args[1].get("files") or mock_gist.edit.call_args[0][0]
    assert "plan--foo.md" in edit_files_arg
    assert "new content" in edit_files_arg["plan--foo.md"]._InputFileContent__content


def test_store_artifact_content_writes_only_target_path_not_other_paths(tmp_path: Path) -> None:
    """Verify that storing to plan/foo.md writes only plan--foo.md, leaving plan--other.md untouched.

    Tests: GitHubGistArtifactProvider.store_artifact_content — path isolation.
    How: Existing Gist already has plan--other.md; store to plan/foo.md.
         Assert gist.edit() receives plan--foo.md (not plan--other.md) as the key.
    Why: Gist filenames are derived from path — each path maps to exactly one Gist file.
         Writing to plan/foo.md must not overwrite plan--other.md in the same Gist.
    """
    # Arrange — Gist sentinel in issue body; Gist has a pre-existing file for another path.
    gist_id = "dead456beef0cafe"
    issue_body = f"Description.\n\n<!-- artifact-gist:{gist_id} -->"
    issue_node = make_issue_node(number=42, id="I_42", body=issue_body)

    mock_gist = MagicMock()
    mock_gist.id = gist_id
    mock_gh_client = MagicMock()
    mock_gh_client.get_gist.return_value = mock_gist

    responses = [
        make_issue_by_number_response(issue_node)  # _fetch_issue_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
        patch("backlog_core.artifact_provider._make_github_client", return_value=mock_gh_client),
    ):
        # Act — store content for plan/foo.md (not plan/other.md)
        provider.store_artifact_content(42, "research", "plan/foo.md", "new content")

    # Assert — gist.edit() received plan--foo.md, not plan--other.md
    assert mock_gql.call_count == 1
    mock_gist.edit.assert_called_once()
    edit_files_arg: dict = mock_gist.edit.call_args[1].get("files") or mock_gist.edit.call_args[0][0]
    assert "plan--foo.md" in edit_files_arg
    assert "plan--other.md" not in edit_files_arg


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.read_artifact_content_from_remote
# ---------------------------------------------------------------------------


def test_read_artifact_content_from_remote_returns_content_when_found(tmp_path: Path) -> None:
    """Verify stored content is returned when the Gist file matching the path is found.

    Tests: GitHubGistArtifactProvider.read_artifact_content_from_remote — found path.
    How: Issue body contains a Gist sentinel; mock _make_github_client so get_gist()
         returns a Gist whose files dict contains the sanitised filename.
    Why: The primary read path must recover content stored by store_artifact_content.
    """
    # Arrange — issue body has Gist sentinel; Gist has the content file.
    gist_id = "f0a1b2c3d4e5f6a7"
    stored_content = "# Research findings\n\nImportant data."
    issue_body = f"Issue description.\n\n<!-- artifact-gist:{gist_id} -->"
    issue_node = make_issue_node(number=42, id="I_42", body=issue_body)

    mock_gist_file = MagicMock()
    mock_gist_file.content = stored_content
    mock_gist = MagicMock()
    mock_gist.files = {"plan--foo.md": mock_gist_file}
    mock_gh_client = MagicMock()
    mock_gh_client.get_gist.return_value = mock_gist

    responses = [
        make_issue_by_number_response(issue_node)  # _fetch_issue_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses),
        patch("backlog_core.artifact_provider._make_github_client", return_value=mock_gh_client),
    ):
        # Act
        result = provider.read_artifact_content_from_remote(42, "research", "plan/foo.md")

    # Assert
    assert result is not None
    assert "# Research findings" in result
    assert "Important data." in result


def test_read_artifact_content_from_remote_returns_none_when_not_found(tmp_path: Path) -> None:
    """Verify None is returned when no matching comment exists.

    Tests: GitHubArtifactProvider.read_artifact_content_from_remote — not-found path.
    How: Mock _graphql_request with empty comment list.
    Why: Callers must be able to detect absence and fall back to filesystem.
    """
    # Arrange — no comments at all
    responses = [
        make_issue_comments_response([])  # _fetch_issue_comments_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses),
    ):
        # Act
        result = provider.read_artifact_content_from_remote(42, "research", "plan/foo.md")

    # Assert
    assert result is None


def test_read_artifact_content_from_remote_ignores_wrong_type(tmp_path: Path) -> None:
    """Verify a comment with the same path but different type is not returned.

    Tests: GitHubArtifactProvider.read_artifact_content_from_remote — type mismatch.
    How: Provide comment for artifact_type="architect", request "research".
    Why: Type filtering is required — different artifacts may share paths.
    """
    # Arrange — comment exists but for a different type
    comment_body = _build_artifact_content_comment("architect", "plan/foo.md", "some content")
    wrong_type_comment = make_issue_comment_node(body=comment_body)
    responses = [
        make_issue_comments_response([wrong_type_comment])  # _fetch_issue_comments_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses),
    ):
        # Act
        result = provider.read_artifact_content_from_remote(42, "research", "plan/foo.md")

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# artifact_register MCP tool — content parameter
# ---------------------------------------------------------------------------


async def test_artifact_register_without_content_and_no_local_file_registers_manifest_only() -> None:
    """Verify artifact_register emits a warning when content and local file are both absent.

    Tests: artifact_register MCP tool — tier 3 (manifest-only).
    How: Mock provider with no local file, call tool without content param.
    Why: Callers need a warning signal to detect missing content — not a silent no-op.
    """
    # Arrange — no explicit content and no local file (tier 3: manifest-only)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.set_manifest.return_value = None
    mock_provider.read_local_artifact_content.return_value = None  # no local file

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.register.return_value = mock_manifest.model_copy(
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register", {"item_id": 42, "artifact_type": "research", "artifact_id": "plan/r.md"}
        )

    # Assert
    assert result.get("error") is None
    assert result["registered"] is True
    assert result["content_stored"] is False
    mock_provider.store_artifact_content.assert_not_called()
    # A warning must be emitted so callers can detect the missing content
    assert any("no local file" in w.lower() or "manifest entry" in w.lower() for w in result.get("warnings", []))


async def test_artifact_register_with_content_stores_to_github() -> None:
    """Verify artifact_register stores explicit content to GitHub.

    Tests: artifact_register MCP tool — tier 1 (explicit content).
    How: Pass content parameter, verify store_artifact_content called correctly.
    Why: Explicit content upload is the primary storage path for agent-produced artifacts.
    """
    # Arrange
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.set_manifest.return_value = None
    mock_provider.store_artifact_content.return_value = None

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.register.return_value = mock_manifest.model_copy(
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register",
            {"item_id": 42, "artifact_type": "research", "artifact_id": "plan/r.md", "content": "# Research content"},
        )

    # Assert
    assert result.get("error") is None
    assert result["registered"] is True
    assert result["content_stored"] is True
    mock_provider.store_artifact_content.assert_called_once_with(42, "research", "plan/r.md", "# Research content")


async def test_artifact_register_without_content_reads_local_file_and_uploads() -> None:
    """Verify artifact_register auto-reads local file content and uploads when no explicit content given.

    Tests: artifact_register MCP tool — tier 2 (auto-read from filesystem).
    How: Mock read_local_artifact_content to return file content, verify upload called.
    Why: Agents should not need to explicitly pass file content when it already exists on disk.
    """
    # Arrange — no explicit content but local file exists (tier 2: auto-read from filesystem)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.set_manifest.return_value = None
    mock_provider.read_local_artifact_content.return_value = "# File content read automatically"
    mock_provider.store_artifact_content.return_value = None

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.register.return_value = mock_manifest.model_copy(
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register", {"item_id": 42, "artifact_type": "research", "artifact_id": "plan/r.md"}
        )

    # Assert
    assert result.get("error") is None
    assert result["registered"] is True
    assert result["content_stored"] is True
    mock_provider.read_local_artifact_content.assert_called_once_with("plan/r.md")
    mock_provider.store_artifact_content.assert_called_once_with(
        42, "research", "plan/r.md", "# File content read automatically"
    )


async def test_artifact_register_with_invalid_type_returns_error() -> None:
    """Verify artifact_register returns an error for unknown artifact types.

    Tests: artifact_register MCP tool — invalid type validation.
    How: Pass artifact_type not in ArtifactType enum, verify error key present.
    Why: Input validation must reject garbage types before touching GitHub.
    """
    # Arrange / Act
    result = await _call(
        "artifact_register", {"item_id": 42, "artifact_type": "not-a-real-type", "artifact_id": "plan/foo.md"}
    )

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# artifact_read MCP tool — GitHub-first, filesystem fallback
# ---------------------------------------------------------------------------


async def test_artifact_read_returns_github_content_when_available() -> None:
    """Verify artifact_read returns content from GitHub when present.

    Tests: artifact_read MCP tool — GitHub-first path.
    How: Mock provider with read_artifact_content_from_remote returning content.
    Why: GitHub-stored content takes precedence over filesystem for worktree isolation.
    """
    # Arrange
    entry = ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="plan/r.md", status=ArtifactStatus.CURRENT)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[entry])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.read_artifact_content_from_remote.return_value = "# From GitHub"

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.get_by_type.return_value = [entry]
        # Act
        result = await _call("artifact_read", {"item_id": 42, "artifact_type": "research"})

    # Assert
    assert result.get("error") is None
    assert result["content"] == "# From GitHub"
    mock_provider.read_artifact_content.assert_not_called()


async def test_artifact_read_falls_back_to_filesystem_when_github_returns_none(tmp_path: Path) -> None:
    """Verify artifact_read falls back to filesystem when GitHub returns no content.

    Tests: artifact_read MCP tool — filesystem fallback.
    How: Mock read_artifact_content_from_remote to return None, read_artifact_content for file.
    Why: Artifacts not stored as comments must still be readable from local disk.
    """
    # Arrange
    entry = ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="plan/r.md", status=ArtifactStatus.CURRENT)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[entry])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.read_artifact_content_from_remote.return_value = None
    mock_provider.read_artifact_content.return_value = "# From filesystem"

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.get_by_type.return_value = [entry]
        # Act
        result = await _call("artifact_read", {"item_id": 42, "artifact_type": "research"})

    # Assert
    assert result.get("error") is None
    assert result["content"] == "# From filesystem"
    mock_provider.read_artifact_content.assert_called_once_with("plan/r.md")


async def test_artifact_read_returns_error_when_type_not_found() -> None:
    """Verify artifact_read returns an error when no artifact of the requested type exists.

    Tests: artifact_read MCP tool — missing artifact type.
    How: Mock registry with empty list for the requested type.
    Why: Callers must distinguish between missing artifacts and API failures.
    """
    # Arrange
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.get_by_type.return_value = []
        # Act
        result = await _call("artifact_read", {"item_id": 42, "artifact_type": "research"})

    # Assert
    assert "error" in result


async def test_artifact_read_returns_error_for_invalid_type() -> None:
    """Verify artifact_read returns an error for unknown artifact types.

    Tests: artifact_read MCP tool — invalid type validation.
    How: Pass artifact_type not in ArtifactType enum.
    Why: Input validation must reject invalid types before touching GitHub.
    """
    # Arrange / Act
    result = await _call("artifact_read", {"item_id": 42, "artifact_type": "not-real"})

    # Assert
    assert "error" in result


async def test_artifact_read_multi_entry_returns_most_recent_and_warns() -> None:
    """When multiple entries of the same type exist, artifact_read returns the most recent.

    Tests: artifact_read MCP tool — multi-entry selection + warning.
    How: Mock registry with two entries; older has earlier created_at, newer has later created_at.
    Why: Silent first-entry selection is a data-loss bug in multi-agent scenarios (#1482).
    """
    # Arrange: two research entries — newer registered second with a later timestamp
    older_entry = ArtifactEntry(
        artifact_type=ArtifactType.RESEARCH,
        artifact_id="plan/r-old.md",
        status=ArtifactStatus.CURRENT,
        created_at="2026-01-01T10:00:00Z",
    )
    newer_entry = ArtifactEntry(
        artifact_type=ArtifactType.RESEARCH,
        artifact_id="plan/r-new.md",
        status=ArtifactStatus.CURRENT,
        created_at="2026-06-01T10:00:00Z",
    )
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[older_entry, newer_entry])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.read_artifact_content_from_remote.return_value = "# Newer content"

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        # Registry returns insertion-order list (older first)
        mock_registry.get_by_type.return_value = [older_entry, newer_entry]
        # Act
        result = await _call("artifact_read", {"item_id": 42, "artifact_type": "research"})

    # Assert: most recent returned
    assert result.get("error") is None
    assert result["path"] == "plan/r-new.md"
    assert result["content"] == "# Newer content"
    # Assert: warning lists the skipped older entry
    warnings = result.get("warnings", [])
    assert len(warnings) == 1
    assert "plan/r-old.md" in warnings[0]
    assert "2" in warnings[0]  # "Multiple … found (2)"
