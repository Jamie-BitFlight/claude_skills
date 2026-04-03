"""Tests for artifact content storage and retrieval via GitHub issue comments.

Covers:
- _build_artifact_content_comment: structure, truncation
- _extract_content_from_comment: happy path, malformed input
- GitHubArtifactProvider.store_artifact_content: create new, update existing
- GitHubArtifactProvider.read_artifact_content_from_github: found, not found
- artifact_register MCP tool: with content (tier 1), auto-read local file (tier 2), no content/no file (tier 3)
- artifact_read MCP tool: GitHub-first, filesystem fallback, neither available

All GitHub API calls are mocked at the ``_graphql_request`` boundary
(``backlog_core.gh_client._graphql_request``) using fixture factories from
``tests.graphql_factories``.  No PyGithub REST mocks remain in this file.
"""

from __future__ import annotations

import json
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
from fastmcp.client import Client
from graphql_factories import (
    make_add_comment_response,
    make_issue_by_number_response,
    make_issue_comment_node,
    make_issue_comments_response,
    make_issue_node,
    make_update_comment_response,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result.

    Tests: FastMCP tool invocation via in-memory transport.
    How: Opens a Client connected to the mcp server, calls tool, parses JSON.
    Why: Ensures MCP tool wrappers behave correctly end-to-end without HTTP.
    """
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


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


def test_store_artifact_content_creates_new_comment_when_none_exists(tmp_path: Path) -> None:
    """Verify a new comment is created via _add_comment_graphql when no match exists.

    Tests: GitHubArtifactProvider.store_artifact_content — create path.
    How: Mock _graphql_request with issue fetch + empty comments + add-comment responses.
         Assert _graphql_request is called with the ADD_COMMENT mutation pattern.
    Why: When no existing comment matches type+path, a new comment must be created.
    """
    # Arrange
    mock_repo = _make_mock_repo()
    issue_node = make_issue_node(number=42, id="I_42")
    responses = [
        make_issue_by_number_response(issue_node),  # _fetch_issue_graphql
        make_issue_comments_response([]),  # _fetch_issue_comments_graphql (page 1, no more)
        make_add_comment_response(),  # _add_comment_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=mock_repo),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
    ):
        # Act
        provider.store_artifact_content(42, "research", "plan/foo.md", "# Content")

    # Assert — third call is the addComment mutation
    assert mock_gql.call_count == 3
    last_call_args = mock_gql.call_args_list[2]
    mutation_str: str = last_call_args[0][1]
    assert "addComment" in mutation_str
    variables: dict = last_call_args[0][2]
    assert "# Content" in variables["body"]
    assert "artifact-content:type=research:path=plan/foo.md" in variables["body"]


def test_store_artifact_content_updates_existing_comment_in_place(tmp_path: Path) -> None:
    """Verify an existing matching comment is updated in-place via _update_issue_comment_graphql.

    Tests: GitHubArtifactProvider.store_artifact_content — update path.
    How: Mock _graphql_request with issue fetch + comment list containing matching comment.
         Assert _graphql_request is called with updateIssueComment mutation.
    Why: Prevents duplicate comments — existing comments must be edited, not duplicated.
    """
    # Arrange
    existing_body = _build_artifact_content_comment("research", "plan/foo.md", "old content")
    existing_comment = make_issue_comment_node(comment_id="IC_existing", body=existing_body)
    issue_node = make_issue_node(number=42, id="I_42")
    responses = [
        make_issue_by_number_response(issue_node),  # _fetch_issue_graphql
        make_issue_comments_response([existing_comment]),  # _fetch_issue_comments_graphql
        make_update_comment_response(comment_id="IC_existing"),  # _update_issue_comment_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
    ):
        # Act
        provider.store_artifact_content(42, "research", "plan/foo.md", "new content")

    # Assert — third call is the updateIssueComment mutation
    assert mock_gql.call_count == 3
    last_call_args = mock_gql.call_args_list[2]
    mutation_str: str = last_call_args[0][1]
    assert "updateIssueComment" in mutation_str
    variables: dict = last_call_args[0][2]
    assert variables["id"] == "IC_existing"
    assert "new content" in variables["body"]


def test_store_artifact_content_does_not_update_comment_with_different_path(tmp_path: Path) -> None:
    """Verify a comment with the same type but different path triggers creation, not update.

    Tests: GitHubArtifactProvider.store_artifact_content — path mismatch.
    How: Place existing comment for plan/other.md, store for plan/foo.md.
         Assert addComment is called (not updateIssueComment).
    Why: Comments are identified by type AND path — partial match must not edit wrong comment.
    """
    # Arrange
    existing_body = _build_artifact_content_comment("research", "plan/other.md", "old content")
    existing_comment = make_issue_comment_node(comment_id="IC_other", body=existing_body)
    issue_node = make_issue_node(number=42, id="I_42")
    responses = [
        make_issue_by_number_response(issue_node),
        make_issue_comments_response([existing_comment]),
        make_add_comment_response(),  # new comment created, not edit
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses) as mock_gql,
    ):
        # Act
        provider.store_artifact_content(42, "research", "plan/foo.md", "new content")

    # Assert — addComment called, not updateIssueComment
    assert mock_gql.call_count == 3
    last_call_args = mock_gql.call_args_list[2]
    mutation_str: str = last_call_args[0][1]
    assert "addComment" in mutation_str
    assert "updateIssueComment" not in mutation_str


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.read_artifact_content_from_github
# ---------------------------------------------------------------------------


def test_read_artifact_content_from_github_returns_content_when_found(tmp_path: Path) -> None:
    """Verify stored content is returned when a matching comment is found.

    Tests: GitHubArtifactProvider.read_artifact_content_from_github — found path.
    How: Mock _graphql_request with comment list containing a matching comment body.
    Why: The primary read path must recover content stored by store_artifact_content.
    """
    # Arrange
    stored_content = "# Research findings\n\nImportant data."
    comment_body = _build_artifact_content_comment("research", "plan/foo.md", stored_content)
    matching_comment = make_issue_comment_node(comment_id="IC_match", body=comment_body)
    responses = [
        make_issue_comments_response([matching_comment])  # _fetch_issue_comments_graphql
    ]
    provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=tmp_path)

    with (
        patch("backlog_core.artifact_provider.get_github", return_value=_make_mock_repo()),
        patch("backlog_core.gh_client._graphql_request", side_effect=responses),
    ):
        # Act
        result = provider.read_artifact_content_from_github(42, "research", "plan/foo.md")

    # Assert
    assert result is not None
    assert "# Research findings" in result
    assert "Important data." in result


def test_read_artifact_content_from_github_returns_none_when_not_found(tmp_path: Path) -> None:
    """Verify None is returned when no matching comment exists.

    Tests: GitHubArtifactProvider.read_artifact_content_from_github — not-found path.
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
        result = provider.read_artifact_content_from_github(42, "research", "plan/foo.md")

    # Assert
    assert result is None


def test_read_artifact_content_from_github_ignores_wrong_type(tmp_path: Path) -> None:
    """Verify a comment with the same path but different type is not returned.

    Tests: GitHubArtifactProvider.read_artifact_content_from_github — type mismatch.
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
        result = provider.read_artifact_content_from_github(42, "research", "plan/foo.md")

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
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, path="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register", {"issue_number": 42, "artifact_type": "research", "path": "plan/r.md"}
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
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, path="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register",
            {"issue_number": 42, "artifact_type": "research", "path": "plan/r.md", "content": "# Research content"},
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
            update={"artifacts": [ArtifactEntry(artifact_type=ArtifactType.RESEARCH, path="plan/r.md")]}
        )
        # Act
        result = await _call(
            "artifact_register", {"issue_number": 42, "artifact_type": "research", "path": "plan/r.md"}
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
        "artifact_register", {"issue_number": 42, "artifact_type": "not-a-real-type", "path": "plan/foo.md"}
    )

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# artifact_read MCP tool — GitHub-first, filesystem fallback
# ---------------------------------------------------------------------------


async def test_artifact_read_returns_github_content_when_available() -> None:
    """Verify artifact_read returns content from GitHub when present.

    Tests: artifact_read MCP tool — GitHub-first path.
    How: Mock provider with read_artifact_content_from_github returning content.
    Why: GitHub-stored content takes precedence over filesystem for worktree isolation.
    """
    # Arrange
    entry = ArtifactEntry(artifact_type=ArtifactType.RESEARCH, path="plan/r.md", status=ArtifactStatus.CURRENT)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[entry])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.read_artifact_content_from_github.return_value = "# From GitHub"

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.get_by_type.return_value = [entry]
        # Act
        result = await _call("artifact_read", {"issue_number": 42, "artifact_type": "research"})

    # Assert
    assert result.get("error") is None
    assert result["content"] == "# From GitHub"
    mock_provider.read_artifact_content.assert_not_called()


async def test_artifact_read_falls_back_to_filesystem_when_github_returns_none(tmp_path: Path) -> None:
    """Verify artifact_read falls back to filesystem when GitHub returns no content.

    Tests: artifact_read MCP tool — filesystem fallback.
    How: Mock read_artifact_content_from_github to return None, read_artifact_content for file.
    Why: Artifacts not stored as comments must still be readable from local disk.
    """
    # Arrange
    entry = ArtifactEntry(artifact_type=ArtifactType.RESEARCH, path="plan/r.md", status=ArtifactStatus.CURRENT)
    mock_manifest = ArtifactManifest(issue_number=42, artifacts=[entry])
    mock_provider = MagicMock()
    mock_provider.get_manifest.return_value = mock_manifest
    mock_provider.read_artifact_content_from_github.return_value = None
    mock_provider.read_artifact_content.return_value = "# From filesystem"

    with (
        patch("backlog_core.server._get_artifact_provider", return_value=mock_provider),
        patch("backlog_core.server._artifact_registry") as mock_registry,
    ):
        mock_registry.get_by_type.return_value = [entry]
        # Act
        result = await _call("artifact_read", {"issue_number": 42, "artifact_type": "research"})

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
        result = await _call("artifact_read", {"issue_number": 42, "artifact_type": "research"})

    # Assert
    assert "error" in result


async def test_artifact_read_returns_error_for_invalid_type() -> None:
    """Verify artifact_read returns an error for unknown artifact types.

    Tests: artifact_read MCP tool — invalid type validation.
    How: Pass artifact_type not in ArtifactType enum.
    Why: Input validation must reject invalid types before touching GitHub.
    """
    # Arrange / Act
    result = await _call("artifact_read", {"issue_number": 42, "artifact_type": "not-real"})

    # Assert
    assert "error" in result
