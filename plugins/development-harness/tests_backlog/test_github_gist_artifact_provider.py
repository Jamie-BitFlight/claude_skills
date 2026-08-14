"""Tests for GitHubGistArtifactProvider — gist creation, naming, migration, error handling.

Tests:
- Gist creation with public=False
- File naming: path sanitization (/ → --)
- Lazy migration from HTML manifest delimiters to gist
- Gist scope 403 error handling
- Gist caching per issue_number
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_provider import GitHubGistArtifactProvider
from backlog_core.models import BacklogError
from github import GithubException
from github.AuthenticatedUser import AuthenticatedUser

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Provide a temporary directory acting as the root worktree.

    Tests: Filesystem root for provider under test.
    How: Create plan/ inside tmp_path.
    Why: Provider validates artifact paths against this root.
    """
    (tmp_path / "plan").mkdir()
    return tmp_path


def _make_graphql_return(body: str = "", issue_id: str = "I_node_id") -> tuple[dict, dict]:
    """Build a graphql_query return value wrapping the given issue body."""
    return (
        {},
        {
            "data": {
                "repository": {
                    "issue": {
                        "id": issue_id,
                        "number": 1,
                        "title": "",
                        "state": "OPEN",
                        "body": body,
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-01T00:00:00Z",
                        "labels": {"nodes": []},
                        "milestone": None,
                        "assignees": {"nodes": []},
                    }
                }
            }
        },
    )


@pytest.fixture
def mock_github_repo(mocker: MockerFixture) -> MagicMock:
    """Patch get_github and return a mock repo with a pre-configured graphql_query.

    Tests: GitHub API boundary — no real HTTP calls.
    How: Patch backlog_core.artifact_provider.get_github; configure graphql_query
         to return a valid 2-tuple.
    Why: Provider uses _fetch_issue_graphql / _update_issue_graphql which unpack
         (headers, data) from repo.requester.graphql_query. The owner/repo split
         reads repo.full_name (the established gh_client.py convention), which
         must be configured for the same reason.
    """
    mock = mocker.patch("backlog_core.artifact_provider.get_github")
    repo = MagicMock()
    repo.full_name = "owner/repo"
    repo.requester.graphql_query.return_value = _make_graphql_return()
    mock.return_value = repo
    return repo


@pytest.fixture
def mock_gist_user(mocker: MockerFixture) -> MagicMock:
    """Patch _make_github_client so gist creation uses a mock user.

    Tests: GitHub user/gist creation mocking.
    How: Patch backlog_core.artifact_provider._make_github_client; set up
         get_user().create_gist() to return a mock gist.
    Why: _create_and_link_gist calls _make_github_client() to reach create_gist.
    """
    mock_client_fn = mocker.patch("backlog_core.artifact_provider._make_github_client")
    mock_gh = MagicMock()
    mock_gist = MagicMock()
    mock_gist.id = "abc123"
    mock_user = MagicMock(spec=AuthenticatedUser)
    mock_user.create_gist.return_value = mock_gist
    mock_gh.get_user.return_value = mock_user
    mock_client_fn.return_value = mock_gh
    return mock_gh


@pytest.fixture
def provider(worktree: Path, mock_github_repo: MagicMock) -> GitHubGistArtifactProvider:
    """Return a GitHubGistArtifactProvider for testing.

    Tests: Provider instance configured with a tmp worktree.
    How: Construct with owner/test-repo and the tmp_path worktree.
    Why: Combines mocked GitHub and real filesystem.
    """
    return GitHubGistArtifactProvider(repo="owner/test-repo", root_worktree=worktree)


# ---------------------------------------------------------------------------
# Gist creation: public=False
# ---------------------------------------------------------------------------


class TestGistCreatedPrivate:
    """Gist is always created with public=False."""

    def test_create_gist_called_with_public_false(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """set_manifest on a fresh issue creates a private gist.

        Tests: Gist privacy — create_gist must receive public=False.
        How: Call set_manifest with an empty manifest; inspect the create_gist call.
        Why: All DH manifests are private; leaking issue metadata via public gist is
             a security concern.
        """
        from backlog_core.models import ArtifactManifest

        # Arrange
        manifest = ArtifactManifest(issue_number=1)

        # Act
        provider.set_manifest(1, manifest)

        # Assert
        mock_gist_user.get_user.return_value.create_gist.assert_called_once()
        call_kwargs = mock_gist_user.get_user.return_value.create_gist.call_args
        assert call_kwargs.kwargs.get("public") is False or call_kwargs.args[0] is False


# ---------------------------------------------------------------------------
# File naming: path sanitization
# ---------------------------------------------------------------------------


class TestGistFilenaming:
    """Artifact paths are sanitized for use as Gist filenames."""

    def test_slash_replaced_with_double_dash(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """store_artifact_content sanitizes / to -- in the gist filename.

        Tests: _sanitize_gist_filename applied during store_artifact_content.
        How: Call store_artifact_content with plan/architect-foo.md; inspect gist.edit.
        Why: Gist filenames may not contain /; -- is the canonical replacement.
        """
        # Arrange — gist already linked via sentinel
        mock_gist = MagicMock()
        mock_gist.id = "abc123"
        mock_gist.files = {}
        mock_gist_user.get_gist.return_value = mock_gist
        mock_github_repo.requester.graphql_query.return_value = _make_graphql_return(
            body="<!-- artifact-gist:abc123 -->"
        )

        # Act
        provider.store_artifact_content(1, "architect", "plan/architect-foo.md", "# content")

        # Assert
        mock_gist.edit.assert_called_once()
        call_kwargs = mock_gist.edit.call_args
        files_arg: dict = call_kwargs.kwargs.get("files") or call_kwargs.args[0]
        assert "plan--architect-foo.md" in files_arg

    def test_multiple_slashes_all_replaced(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """All / characters in a path are replaced with --.

        Tests: _sanitize_gist_filename handles nested paths.
        How: Call store_artifact_content with research/sub/findings.md.
        Why: Nested paths like research/sub/findings.md should map to
             research--sub--findings.md unambiguously.
        """
        mock_gist = MagicMock()
        mock_gist.id = "def456"
        mock_gist.files = {}
        mock_gist_user.get_gist.return_value = mock_gist
        mock_github_repo.requester.graphql_query.return_value = _make_graphql_return(
            body="<!-- artifact-gist:def456 -->"
        )

        provider.store_artifact_content(1, "research", "research/sub/findings.md", "content")

        call_kwargs = mock_gist.edit.call_args
        files_arg: dict = call_kwargs.kwargs.get("files") or call_kwargs.args[0]
        assert "research--sub--findings.md" in files_arg


# ---------------------------------------------------------------------------
# Lazy migration from HTML manifest delimiters
# ---------------------------------------------------------------------------


class TestLazyMigration:
    """Legacy inline manifest blocks are lazily migrated to Gist storage."""

    def test_get_manifest_migrates_legacy_inline_block(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """get_manifest detects the legacy inline block and migrates to a Gist.

        Tests: Lazy migration path in get_manifest.
        How: Set graphql_query to return a body containing
             <!-- artifact-manifest:begin --> ... <!-- artifact-manifest:end -->.
             Assert create_gist is called and set_manifest writes a sentinel.
        Why: Issues created before the Gist migration keep the old inline format;
             first access should transparently migrate them.
        """
        # Arrange — build legacy inline manifest
        from backlog_core.artifact_registry import ArtifactRegistry, render_manifest_section
        from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactType

        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=1)
        entry = ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, artifact_id="plan/architect-test.md")
        manifest = registry.register(manifest, entry)
        legacy_body = render_manifest_section(manifest)

        mock_github_repo.requester.graphql_query.return_value = _make_graphql_return(body=legacy_body)

        # Act
        result = provider.get_manifest(1)

        # Assert — create_gist was called (migration occurred)
        mock_gist_user.get_user.return_value.create_gist.assert_called_once()
        # Returned manifest contains the migrated artifact
        assert len(result.artifacts) == 1


# ---------------------------------------------------------------------------
# 403 gist-scope error handling
# ---------------------------------------------------------------------------


class TestGistScopeError:
    """A 403 from create_gist is surfaced as BacklogError."""

    def test_403_from_create_gist_raises_backlog_error(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """set_manifest raises BacklogError when token lacks gist scope.

        Tests: 403 → BacklogError with helpful message.
        How: Mock create_gist to raise GithubException(status=403); call set_manifest.
        Why: The gist OAuth scope is separate from repo scope; users need a clear
             error message pointing them to the GitHub settings page.
        """
        from backlog_core.models import ArtifactManifest

        # Arrange
        exc = GithubException(status=403, data={"message": "Forbidden"}, headers={})
        mock_gist_user.get_user.return_value.create_gist.side_effect = exc

        manifest = ArtifactManifest(issue_number=1)

        # Act / Assert
        with pytest.raises(BacklogError, match="gist"):
            provider.set_manifest(1, manifest)


# ---------------------------------------------------------------------------
# Gist caching per issue_number
# ---------------------------------------------------------------------------


class TestGistCaching:
    """Gists are cached per issue_number to avoid repeated API calls."""

    def test_gist_loaded_once_per_issue_across_calls(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """_get_gist uses the in-memory cache on subsequent calls.

        Tests: _gist_cache prevents repeated get_gist API calls.
        How: Issue body contains sentinel; call get_manifest twice; assert
             get_gist called at most once.
        Why: Each get_gist call costs an API round-trip; caching is required
             for performance in multi-artifact workflows.
        """
        mock_gist = MagicMock()
        mock_gist.id = "abc123"
        manifest_file = MagicMock()
        manifest_file.content = '{"artifacts": [], "issue_number": 1, "last-updated": ""}'
        mock_gist.files = {"manifest.json": manifest_file}
        mock_gist_user.get_gist.return_value = mock_gist

        mock_github_repo.requester.graphql_query.return_value = _make_graphql_return(
            body="<!-- artifact-gist:abc123 -->"
        )

        # Act — call twice
        provider.get_manifest(1)
        provider.get_manifest(1)

        # Assert — get_gist called once (second served from cache)
        mock_gist_user.get_gist.assert_called_once_with("abc123")

    def test_gist_cache_is_per_issue(
        self, provider: GitHubGistArtifactProvider, mock_github_repo: MagicMock, mock_gist_user: MagicMock
    ) -> None:
        """Different issue numbers get separate cache entries.

        Tests: _gist_cache keyed by issue_number.
        How: Call get_manifest for issue 1 and issue 2; assert get_gist called twice
             (once per distinct issue).
        Why: Cache must be per-issue, not global, to avoid cross-contamination.
        """
        manifest_json = '{"artifacts": [], "issue_number": 0, "last-updated": ""}'
        mock_gist_1 = MagicMock()
        mock_gist_1.id = "aaa111"
        file_1 = MagicMock()
        file_1.content = manifest_json
        mock_gist_1.files = {"manifest.json": file_1}

        mock_gist_2 = MagicMock()
        mock_gist_2.id = "bbb222"
        file_2 = MagicMock()
        file_2.content = manifest_json
        mock_gist_2.files = {"manifest.json": file_2}

        mock_gist_user.get_gist.side_effect = lambda gid: mock_gist_1 if gid == "aaa111" else mock_gist_2

        def _graphql_side_effect(query: str, variables: dict) -> tuple[dict, dict]:
            issue_num = variables.get("number", 1)
            body = "<!-- artifact-gist:aaa111 -->" if issue_num == 1 else "<!-- artifact-gist:bbb222 -->"
            return _make_graphql_return(body=body)

        mock_github_repo.requester.graphql_query.side_effect = _graphql_side_effect

        # Act
        provider.get_manifest(1)
        provider.get_manifest(2)

        # Assert — two distinct get_gist calls
        assert mock_gist_user.get_gist.call_count == 2
