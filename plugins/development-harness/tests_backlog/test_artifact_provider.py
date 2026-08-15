"""Tests for backlog_core.artifact_provider — GitHubArtifactProvider and MCP tools.

Tests: GitHubArtifactProvider with mocked GitHub API, path safety, and FastMCP
       in-memory integration tests for all four artifact MCP tools.
       Also covers: multi-provider protocol compliance, create_artifact_provider factory.

Strategy:
    - GitHubArtifactProvider tests use pytest-mock to stub PyGithub's get_github()
      and the issue object. No real network calls are made.
    - MCP tool integration tests use the FastMCP in-memory client to call tools
      through the full request/response pipeline, with an injected mock provider
      via monkeypatching the server module's _get_artifact_provider() function.
    - Security tests verify path traversal and non-plan path rejection.
    - All tests follow AAA and are independently isolated with function-scoped fixtures.
    - TestArtifactBackendProtocol is parametrized over github, linear, and gitlab
      providers so protocol compliance is verified for all three.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_provider import (
    ArtifactBackend,
    GitHubArtifactProvider,
    GitHubGistArtifactProvider,
    GitLabArtifactProvider,
    LinearArtifactProvider,
    create_artifact_provider,
)
from backlog_core.artifact_registry import ArtifactRegistry, render_manifest_section
from backlog_core.models import (
    ArtifactEntry,
    ArtifactManifest,
    ArtifactStatus,
    ArtifactType,
    BacklogError,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentRecord,
    ContentRef,
    ContentWrite,
)
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

    Tests: A filesystem root containing plan/ directory
    How: Create tmp_path/plan/ for tests that read from the plan/ directory.
    Why: GitHubArtifactProvider validates paths against root_worktree; tests
         need real filesystem paths for read_artifact_content.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    return tmp_path


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> MagicMock:
    """Return a MagicMock replacing get_github() at the provider level.

    Tests: GitHub API boundary mocking
    How: Patch backlog_core.artifact_provider.get_github and return a mock repo
         with requester.graphql_query pre-configured to return a valid 2-tuple.
    Why: Provider tests must not make real HTTP calls. The artifact_provider calls
         _fetch_issue_graphql (query) and _update_issue_graphql (mutation), both of
         which unpack repo.requester.graphql_query() as (headers, response). A bare
         MagicMock() unpacks to 0 values and raises ValueError. Likewise, the owner/
         repo split reads repo.full_name (the established gh_client.py convention),
         which must be configured for the same reason.
    """
    mock = mocker.patch("backlog_core.artifact_provider.get_github")
    repo = MagicMock()
    repo.full_name = "owner/repo"
    repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "issue": {
                        "id": "I_test_node_id",
                        "number": 0,
                        "title": "",
                        "state": "OPEN",
                        "body": "",
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
    mock.return_value = repo
    return repo


@pytest.fixture
def mock_issue(mock_repo: MagicMock) -> MagicMock:
    """Return a MagicMock for a GitHub Issue with empty body.

    Tests: Minimal issue mock for provider tests
    How: Configure mock_repo.get_issue() to return a mock issue with body="".
    Why: Most provider tests start from a clean-slate issue body.
    """
    issue = MagicMock()
    issue.body = ""
    mock_repo.get_issue.return_value = issue
    return issue


@pytest.fixture
def provider(worktree: Path, mock_repo: MagicMock) -> GitHubArtifactProvider:
    """Return a GitHubArtifactProvider pointed at a test repo and tmp worktree.

    Tests: Provider instance with test configuration
    How: Construct with owner/test-repo slug and the tmp worktree path.
    Why: Combines mocked GitHub and real filesystem for isolation.
    """
    return GitHubArtifactProvider(repo="owner/test-repo", root_worktree=worktree)


@pytest.fixture
def registry() -> ArtifactRegistry:
    """Return a fresh ArtifactRegistry instance for helper use.

    Tests: Registry used alongside provider in integration setups
    How: Construct with no arguments.
    Why: Some provider fixtures need to build manifests to embed in mock bodies.
    """
    return ArtifactRegistry()


# ---------------------------------------------------------------------------
# Multi-provider fixture: parametrized over github, linear, gitlab
# ---------------------------------------------------------------------------


def _make_mock_github_provider(worktree: Path, mocker: MockerFixture) -> ArtifactBackend:
    """Construct a mocked GitHubGistArtifactProvider for protocol testing."""
    mock = mocker.patch("backlog_core.artifact_provider.get_github")
    repo = MagicMock()
    repo.full_name = "owner/test-repo"
    repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "issue": {
                        "id": "I_node_id",
                        "number": 1,
                        "title": "",
                        "state": "OPEN",
                        "body": "",
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
    mock.return_value = repo
    return GitHubGistArtifactProvider(repo="owner/test-repo", root_worktree=worktree)


def _make_mock_linear_provider(worktree: Path, mocker: MockerFixture) -> ArtifactBackend:
    """Construct a mocked LinearArtifactProvider for protocol testing."""
    mocker.patch("backlog_core.artifact_provider.linear_get_attachments", return_value=[])
    mocker.patch(
        "backlog_core.artifact_provider.linear_create_attachment",
        return_value={"id": "a1", "url": "dh://artifact-manifest/1", "title": "DH"},
    )
    return LinearArtifactProvider(api_key="test-key", team_id="team-uuid", root_worktree=worktree)


def _make_mock_gitlab_provider(worktree: Path, mocker: MockerFixture) -> ArtifactBackend:
    """Construct a mocked GitLabArtifactProvider for protocol testing."""
    mocker.patch("backlog_core.artifact_provider.gitlab_list_issue_notes", return_value=[])
    mocker.patch(
        "backlog_core.artifact_provider.gitlab_create_snippet", return_value={"id": 42, "title": "t", "web_url": "u"}
    )
    mocker.patch("backlog_core.artifact_provider.gitlab_update_snippet", return_value={"id": 42})
    mocker.patch(
        "backlog_core.artifact_provider.gitlab_create_issue_note",
        return_value={"id": 1, "body": "<!-- artifact-snippet:42 -->"},
    )
    return GitLabArtifactProvider(project_id=1, private_token="test-token", root_worktree=worktree)


_PROVIDER_FACTORIES = {
    "github": _make_mock_github_provider,
    "linear": _make_mock_linear_provider,
    "gitlab": _make_mock_gitlab_provider,
}


@pytest.fixture(params=["github", "linear", "gitlab"])
def any_provider(request: pytest.FixtureRequest, tmp_path: Path, mocker: MockerFixture) -> ArtifactBackend:
    """Parametrized fixture that yields a mocked provider for each backend.

    Tests: Protocol compliance across all three provider implementations.
    How: Uses _PROVIDER_FACTORIES to construct each provider with mocked APIs.
    Why: TestArtifactBackendProtocol should verify all providers, not only GitHub.
    """
    factory = _PROVIDER_FACTORIES[request.param]
    (tmp_path / "plan").mkdir(exist_ok=True)
    return factory(tmp_path, mocker)


# ---------------------------------------------------------------------------
# ArtifactBackend Protocol compliance
# ---------------------------------------------------------------------------


class TestArtifactBackendProtocol:
    """Verify all three providers satisfy the ArtifactBackend Protocol.

    Tests: Runtime checkable protocol compliance for github, linear, and gitlab.
    Strategy: Use isinstance() check — requires @runtime_checkable decorator.
    """

    def test_provider_satisfies_artifact_backend_protocol(self, any_provider: ArtifactBackend) -> None:
        """Each provider is an instance of ArtifactBackend protocol.

        Tests: Protocol compliance via isinstance check (parametrized).
        How: Receive provider from the any_provider fixture; assert isinstance.
        Why: Protocol compliance ensures providers can be used interchangeably.
        """
        # Arrange: any_provider fixture provides a mocked provider instance

        # Act / Assert
        assert isinstance(any_provider, ArtifactBackend)

    def test_provider_has_all_required_methods(self, any_provider: ArtifactBackend) -> None:
        """Each provider exposes all required ArtifactBackend methods.

        Tests: Method presence without invocation.
        How: Use hasattr checks against all Protocol method names.
        Why: A provider missing any method fails at call-site with AttributeError —
             catching this at the protocol level gives a clearer failure.
        """
        # Arrange
        required_methods = [
            "get_manifest",
            "set_manifest",
            "read_artifact_content",
            "store_artifact_content",
            "read_artifact_content_from_remote",
            "read_local_artifact_content",
        ]

        # Act / Assert
        for method_name in required_methods:
            assert hasattr(any_provider, method_name), f"Provider missing method: {method_name}"

    # Keep the existing single-provider test as a named regression test.
    def test_github_provider_satisfies_artifact_backend_protocol(self, worktree: Path, mock_repo: MagicMock) -> None:
        """GitHubArtifactProvider (alias) is an instance of ArtifactBackend protocol.

        Tests: Backward-compat alias GitHubArtifactProvider remains protocol-compliant.
        How: Construct provider; assert isinstance(provider, ArtifactBackend).
        Why: Consumer code may still reference GitHubArtifactProvider by name.
        """
        # Arrange / Act
        prov = GitHubArtifactProvider(repo="owner/repo", root_worktree=worktree)

        # Assert
        assert isinstance(prov, ArtifactBackend)


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.get_manifest tests
# ---------------------------------------------------------------------------


class TestGitHubArtifactProviderGetManifest:
    """Unit tests for GitHubArtifactProvider.get_manifest.

    Tests: Manifest retrieval from mocked GitHub Issue body.
    Strategy: Tests vary the issue body to exercise absent-section and present-section paths.
    """

    def test_returns_empty_manifest_when_issue_body_is_empty(
        self, provider: GitHubArtifactProvider, mock_issue: MagicMock, mock_repo: MagicMock
    ) -> None:
        """get_manifest returns empty manifest when the issue body is empty.

        Tests: No manifest section present in issue body (cache miss scenario)
        How: Set issue.body = ""; call get_manifest; assert artifacts == [].
        Why: An issue with no prior artifact registrations must return an empty
             manifest, not raise an exception.
        """
        # Arrange
        mock_issue.body = ""
        mock_repo.get_issue.return_value = mock_issue

        # Act
        manifest = provider.get_manifest(965)

        # Assert
        assert manifest.issue_number == 965
        assert manifest.artifacts == []

    def test_returns_empty_manifest_when_issue_body_is_none(
        self, provider: GitHubArtifactProvider, mock_issue: MagicMock, mock_repo: MagicMock
    ) -> None:
        """get_manifest handles None issue body gracefully.

        Tests: GitHub issues with null body field
        How: Set issue.body = None; call get_manifest.
        Why: PyGithub returns None for issues with no body text.
        """
        # Arrange
        mock_issue.body = None
        mock_repo.get_issue.return_value = mock_issue

        # Act
        manifest = provider.get_manifest(100)

        # Assert
        assert manifest.artifacts == []

    def test_returns_parsed_manifest_when_section_present(
        self,
        provider: GitHubArtifactProvider,
        mock_issue: MagicMock,
        mock_repo: MagicMock,
        registry: ArtifactRegistry,
        mocker: MockerFixture,
    ) -> None:
        """get_manifest parses and returns the artifact manifest from the issue body.

        Tests: Manifest section parsing via get_manifest
        How: Pre-populate graphql_query mock to return a rendered manifest as body;
             call get_manifest; assert the returned manifest contains the expected entry.
        Why: Provider uses GraphQL (_fetch_issue_graphql) to retrieve the issue body.
             The graphql_query mock must return the body in the nested response shape.
             The legacy inline format triggers lazy migration via _create_and_link_gist,
             which calls _make_github_client — must be mocked.
        """
        # Arrange — mock gist creation for the lazy migration path
        mock_gh_client = mocker.patch("backlog_core.artifact_provider._make_github_client")
        mock_gist = MagicMock()
        mock_gist.id = "abc123deadbeef"
        mock_user = MagicMock(spec=AuthenticatedUser)
        mock_user.create_gist.return_value = mock_gist
        mock_gh_client.return_value.get_user.return_value = mock_user

        # Arrange — build a body with one registered artifact
        manifest = ArtifactManifest(issue_number=965)
        entry = ArtifactEntry(
            artifact_type=ArtifactType.ARCHITECT,
            artifact_id="plan/architect-foo.md",
            status=ArtifactStatus.CURRENT,
            agent="architect-agent",
            created_at="2026-03-21T10:00:00Z",
        )
        manifest = registry.register(manifest, entry)
        rendered = render_manifest_section(manifest)

        # Override graphql_query to return the rendered manifest as the issue body
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_test_node_id",
                            "number": 965,
                            "title": "Test Issue",
                            "state": "OPEN",
                            "body": rendered,
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

        # Act
        result = provider.get_manifest(965)

        # Assert
        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.ARCHITECT
        assert result.artifacts[0].artifact_id == "plan/architect-foo.md"


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.set_manifest tests
# ---------------------------------------------------------------------------


class TestGitHubArtifactProviderSetManifest:
    """Unit tests for GitHubArtifactProvider.set_manifest.

    Tests: Manifest persistence via issue.edit(), no-op when body unchanged.
    """

    def test_set_manifest_calls_issue_edit_when_body_changes(
        self,
        provider: GitHubArtifactProvider,
        mock_issue: MagicMock,
        mock_repo: MagicMock,
        registry: ArtifactRegistry,
        mocker: MockerFixture,
    ) -> None:
        """set_manifest issues a GraphQL mutation when the body content changes.

        Tests: GitHub issue body update triggered by set_manifest
        How: graphql_query mock returns empty body; set_manifest with one entry;
             assert graphql_query was called twice (fetch + mutation) and the
             mutation variables contain the gist sentinel.
        Why: set_manifest uses GraphQL (_update_issue_graphql) to persist the sentinel
             after creating/updating the Gist. The mutation carries the new body with
             <!-- artifact-gist:{id} --> in its variables dict.
        """
        # Arrange — patch _make_github_client so gist creation succeeds
        mock_gh_client = mocker.patch("backlog_core.artifact_provider._make_github_client")
        mock_gist = MagicMock()
        mock_gist.id = "abc123deadbeef"
        mock_user = MagicMock(spec=AuthenticatedUser)
        mock_user.create_gist.return_value = mock_gist
        mock_gh_client.return_value.get_user.return_value = mock_user
        # graphql_query fixture returns empty body (set in mock_repo fixture)
        manifest = ArtifactManifest(issue_number=965)
        entry = ArtifactEntry(artifact_type=ArtifactType.FEATURE_CONTEXT, artifact_id="plan/feature-context-foo.md")
        manifest = registry.register(manifest, entry)

        # Act
        provider.set_manifest(965, manifest)

        # Assert — graphql_query called at least twice: fetch + mutation
        assert mock_repo.requester.graphql_query.call_count >= 2
        # Find the mutation call (contains 'updateIssue')
        mutation_calls = [
            call for call in mock_repo.requester.graphql_query.call_args_list if "updateIssue" in call[0][0]
        ]
        assert len(mutation_calls) >= 1, "Expected at least one updateIssue mutation call"
        mutation_variables: dict[str, Any] = mutation_calls[0][0][1]
        assert "body" in mutation_variables
        # The implementation now writes a Gist sentinel, not the legacy inline manifest
        assert "<!-- artifact-gist:" in mutation_variables["body"]

    def test_set_manifest_skips_edit_when_body_unchanged(
        self, provider: GitHubArtifactProvider, mock_repo: MagicMock
    ) -> None:
        """set_manifest calls gist.edit() but skips updateIssue when sentinel is already in body.

        Tests: When the issue body already carries the gist sentinel, set_manifest updates
               the Gist content via gist.edit() but does NOT issue a GraphQL updateIssue
               mutation (the issue body does not need to change).
        How: Pre-populate provider._gist_cache with a mock Gist and configure graphql_query
             to return a body containing the sentinel. Call set_manifest once. Assert
             gist.edit() is called but no updateIssue mutation is issued.
        Why: _get_gist() checks _gist_cache first (before calling _make_github_client).
             Pre-seeding the cache and body avoids all live API calls while exercising the
             correct code path. The previous implementation called _make_github_client()
             (which uses GITHUB_TOKEN) when the sentinel was absent, hitting the real API
             under CI conditions with a live token.
        """
        # Arrange — a hex gist_id matching _GIST_SENTINEL_RE: r"<!-- artifact-gist:(?P<gist_id>[0-9a-f]+) -->"
        gist_id = "abc123def456abcd"
        sentinel_body = f"Issue description.\n<!-- artifact-gist:{gist_id} -->"

        mock_gist = MagicMock()
        # Pre-seed the cache: _get_gist checks this before calling _make_github_client
        provider._gist_cache[965] = mock_gist

        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_test_node_id",
                            "number": 965,
                            "title": "",
                            "state": "OPEN",
                            "body": sentinel_body,
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

        manifest = ArtifactManifest(issue_number=965)

        # Act
        provider.set_manifest(965, manifest)

        # Assert — gist.edit() was called with the serialised manifest JSON
        mock_gist.edit.assert_called_once()
        call_files: dict[str, Any] = mock_gist.edit.call_args.kwargs["files"]
        assert "manifest.json" in call_files

        # The issue body did not change (sentinel was already present) — no updateIssue mutation
        mutation_calls = [
            call for call in mock_repo.requester.graphql_query.call_args_list if "updateIssue" in call[0][0]
        ]
        assert mutation_calls == [], "updateIssue mutation must not fire when sentinel is already in body"


# ---------------------------------------------------------------------------
# GitHubArtifactProvider.read_artifact_content tests
# ---------------------------------------------------------------------------


class TestGitHubArtifactProviderReadArtifactContent:
    """Unit tests for GitHubArtifactProvider.read_artifact_content.

    Tests: Successful read from plan/ and other directories, path traversal
           rejection, and FileNotFoundError on missing file (cache miss).
    Strategy: Uses real tmp_path filesystem. No GitHub mocking needed for read.
    """

    def test_reads_valid_plan_file_content(self, provider: GitHubArtifactProvider, worktree: Path) -> None:
        """read_artifact_content returns file content for a valid plan/ path.

        Tests: Happy-path file read from plan/ directory
        How: Write a test file to plan/; call read_artifact_content; assert content.
        Why: Verifies the basic read path works end-to-end.
        """
        # Arrange
        plan_file = worktree / "plan" / "architect-test.md"
        plan_file.write_text("# Architecture\n\nContent here.", encoding="utf-8")

        # Act
        content = provider.read_artifact_content("plan/architect-test.md")

        # Assert
        assert "# Architecture" in content
        assert "Content here." in content

    def test_rejects_path_traversal_with_dotdot(self, provider: GitHubArtifactProvider) -> None:
        """read_artifact_content rejects paths that escape the repository root.

        Tests: Path traversal rejection (architect spec 7.3 scenario 6)
        How: Pass ../../../etc/passwd as path; assert ValueError raised with
             "path traversal" in the message.
        Why: Critical security requirement — must prevent arbitrary file reads.
        """
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="traversal"):
            provider.read_artifact_content("../../../etc/passwd")

    def test_reads_research_path_outside_plan_directory(self, provider: GitHubArtifactProvider, worktree: Path) -> None:
        """read_artifact_content reads files outside plan/ (e.g. research/).

        Tests: Removal of plan/ prefix restriction — any repo-relative path allowed
        How: Write a file to research/; call read_artifact_content; assert content returned.
        Why: Research artifacts live under research/, not plan/. The path traversal
             protection (resolve + relative_to) is the real security boundary.
        """
        # Arrange
        research_dir = worktree / "research"
        research_dir.mkdir()
        research_file = research_dir / "findings.md"
        research_file.write_text("# Research Findings\n\nContent.", encoding="utf-8")

        # Act
        content = provider.read_artifact_content("research/findings.md")

        # Assert
        assert "# Research Findings" in content

    def test_rejects_plan_path_with_embedded_traversal(self, provider: GitHubArtifactProvider) -> None:
        """read_artifact_content rejects plan/ paths that traverse outside root via resolve.

        Tests: Path traversal via plan/../.. pattern
        How: Pass plan/../../etc/shadow; assert ValueError raised.
        Why: A path starting with plan/ could still escape via resolve() — must be caught.
        """
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="traversal"):
            provider.read_artifact_content("plan/../../etc/shadow")

    def test_raises_file_not_found_for_registered_but_missing_file(self, provider: GitHubArtifactProvider) -> None:
        """read_artifact_content raises FileNotFoundError when file does not exist.

        Tests: Cache miss — artifact registered but file not on disk (architect spec 7.3 scenario 8)
        How: Pass a valid plan/ path that does not exist in tmp_path; assert FileNotFoundError.
        Why: Registered artifacts may not yet be committed in all worktrees; the error
             gives consumers a clear signal to fall back to filesystem access.
        """
        # Arrange / Act / Assert
        with pytest.raises(FileNotFoundError):
            provider.read_artifact_content("plan/does-not-exist.md")

    def test_reads_path_with_plan_substring_not_at_start(
        self, provider: GitHubArtifactProvider, worktree: Path
    ) -> None:
        """read_artifact_content reads paths where 'plan' appears but is not a prefix.

        Tests: No plan/ prefix restriction — 'myplan/...' is now a valid repo-relative path
        How: Write a file to myplan/; call read_artifact_content; assert content returned.
        Why: The old plan/ check was artificial; path traversal protection is the real guard.
        """
        # Arrange
        myplan_dir = worktree / "myplan"
        myplan_dir.mkdir()
        myplan_file = myplan_dir / "architect.md"
        myplan_file.write_text("# My Plan\n\nContent.", encoding="utf-8")

        # Act
        content = provider.read_artifact_content("myplan/architect.md")

        # Assert
        assert "# My Plan" in content


# ---------------------------------------------------------------------------
# MCP tool integration tests
# ---------------------------------------------------------------------------

# The integration tests use FastMCP's in-memory transport. The server module
# resolves the artifact provider via the _get_artifact_provider() function. Tests
# inject a MockArtifactBackend via monkeypatch to avoid real GitHub calls while
# testing the full tool request/response pipeline.


class _InMemoryArtifactBackend:
    """Minimal in-memory ContentProvider double for MCP integration tests.

    Implements the ``get_content``/``put_content`` surface that
    ``backlog_core.server`` calls through ``_get_artifact_provider()`` —
    ``ContentKind.ARTIFACT_MANIFEST`` resolves to a manifest keyed by
    issue_number; ``ContentKind.ARTIFACT_CONTENT`` resolves to file content
    keyed by the artifact's repo-relative path (``ContentRef.name``), matching
    the ``artifact_content_reference()`` scheme in
    ``backlog_core.artifact_manifest_store`` for entries with no
    ``content_revision`` (the tests never set one).
    """

    def __init__(self) -> None:
        """Initialise with empty storage."""
        self._manifests: dict[int, ArtifactManifest] = {}
        self._files: dict[str, str] = {}
        self._revisions: dict[str, str] = {}

    @staticmethod
    def _revision_key(reference: ContentRef) -> str:
        """Canonical CAS key for a reference, matching the get/put storage split.

        Args:
            reference: Logical content identity to key revisions by.

        Returns:
            "manifest:{issue_number}" for ARTIFACT_MANIFEST, "content:{path}" otherwise.
        """
        if reference.kind == ContentKind.ARTIFACT_MANIFEST:
            return f"manifest:{reference.namespace}"
        return f"content:{reference.name}"

    def get_manifest(self, issue_number: int) -> ArtifactManifest:
        """Return stored manifest or empty manifest.

        Args:
            issue_number: GitHub issue number.

        Returns:
            Stored or new empty ArtifactManifest.
        """
        return self._manifests.get(issue_number, ArtifactManifest(issue_number=issue_number))

    def set_manifest(self, issue_number: int, manifest: ArtifactManifest) -> None:
        """Store the manifest, stamping a fresh revision like a real put_content would.

        Args:
            issue_number: GitHub issue number.
            manifest: Manifest to store.
        """
        self._manifests[issue_number] = manifest
        self._revisions[f"manifest:{issue_number}"] = uuid.uuid4().hex

    def add_file(self, path: str, content: str) -> None:
        """Register in-memory file content, stamping a fresh revision like a real put_content would.

        Args:
            path: Path to register.
            content: File content string.
        """
        self._files[path] = content
        self._revisions[f"content:{path}"] = uuid.uuid4().hex

    def get_content(self, reference: ContentRef) -> ContentRecord:
        """Resolve a manifest or artifact-content record by logical reference.

        Args:
            reference: Logical content identity requested by the server.

        Returns:
            The matching ContentRecord.

        Raises:
            ContentNotFoundError: When no manifest or file is registered for
                the requested reference — mirrors the real ContentProvider
                contract (see ``backlog_core.backends.memory_backend.InMemoryBackend``),
                and propagates as ``fastmcp.exceptions.ToolError`` since
                ``ContentNotFoundError`` is not a ``BacklogError``.
        """
        if reference.kind == ContentKind.ARTIFACT_MANIFEST:
            manifest = self._manifests.get(int(reference.namespace))
            if manifest is None:
                raise ContentNotFoundError(f"No manifest registered for issue {reference.namespace}")
            return ContentRecord(
                reference=reference,
                owner_reference=reference.namespace,
                content=manifest.model_dump_json(),
                revision=self._revisions[self._revision_key(reference)],
            )
        content = self._files.get(reference.name)
        if content is None:
            raise ContentNotFoundError(f"File not found in test backend: {reference.name}")
        return ContentRecord(
            reference=reference,
            owner_reference=reference.namespace,
            content=content,
            revision=self._revisions[self._revision_key(reference)],
        )

    def put_content(self, request: ContentWrite) -> ContentRecord:
        """Persist a manifest or artifact-content record by logical reference, enforcing CAS.

        Mirrors ``backlog_core.backends.memory_backend.InMemoryBackend.put_content``'s
        revision-safe update contract: a ``create_only`` write against an existing
        record, or a write whose ``expected_revision`` no longer matches the stored
        revision, is rejected rather than silently overwriting.

        Args:
            request: Logical content write issued by the server.

        Returns:
            The persisted ContentRecord, stamped with a fresh revision.

        Raises:
            ContentConflictError: When the reference kind is unsupported, when
                ``create_only`` targets an existing record, or when
                ``expected_revision`` no longer matches the stored revision.
        """
        reference = request.reference
        key = self._revision_key(reference)
        current_revision = self._revisions.get(key, "")
        if request.create_only and key in self._revisions:
            raise ContentConflictError(f"Content already exists: {key}")
        if request.expected_revision and request.expected_revision != current_revision:
            raise ContentConflictError(f"Content revision no longer matches: {key}")
        new_revision = uuid.uuid4().hex
        if reference.kind == ContentKind.ARTIFACT_MANIFEST:
            self._manifests[int(reference.namespace)] = ArtifactManifest.model_validate_json(request.content)
            self._revisions[key] = new_revision
        elif reference.kind == ContentKind.ARTIFACT_CONTENT:
            self._files[reference.name] = request.content
            self._revisions[key] = new_revision
        else:
            raise ContentConflictError(f"Unsupported content kind for test backend: {reference.kind}")
        return ContentRecord(
            reference=reference, owner_reference=reference.namespace, content=request.content, revision=new_revision
        )


@pytest.fixture
def in_memory_backend() -> _InMemoryArtifactBackend:
    """Return a fresh in-memory artifact backend.

    Tests: MCP tool integration with isolated in-memory storage
    How: Construct fresh instance with empty manifests and files.
    Why: Enables MCP tool tests without GitHub API or filesystem.
    """
    return _InMemoryArtifactBackend()


@pytest.fixture
def patched_mcp_server(monkeypatch: pytest.MonkeyPatch, in_memory_backend: _InMemoryArtifactBackend) -> Any:
    """Patch the backlog MCP server to use the in-memory backend.

    Tests: MCP tool integration setup
    How: Monkeypatch _get_artifact_provider in server module.
    Why: MCP tools call _get_artifact_provider(); patching it ensures all tool
         calls use the in-memory backend throughout each test.

    Returns:
        The FastMCP server instance for use with Client.
    """
    import backlog_core.server as server_module

    monkeypatch.setattr(server_module, "_get_artifact_provider", lambda: in_memory_backend)
    return server_module.mcp


class TestMCPToolArtifactRegister:
    """Integration tests for the artifact_register MCP tool.

    Tests: Full request/response pipeline for artifact_register via in-memory transport.
    Strategy: Uses FastMCP Client with in-memory backend. Verifies idempotency,
              action field values, and error responses for invalid input.
    """

    async def test_artifact_register_adds_new_entry(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_register tool adds a new entry and returns action='added'.

        Tests: First registration of an artifact type
        How: Call artifact_register via FastMCP client; assert action='added'.
        Why: Verifies the MCP tool successfully delegates to registry and provider.
        """
        from fastmcp.client import Client

        # Arrange / Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool(
                "artifact_register",
                {
                    "item_id": 965,
                    "artifact_type": "feature-context",
                    "artifact_id": "plan/feature-context-foo.md",
                    "content": "# Feature Context\n\nFoo.",
                    "status": "current",
                    "agent": "feature-researcher",
                },
            )

        # Assert
        data = result.data
        assert data["registered"] is True
        assert data["action"] == "added"
        assert data["artifact_count"] == 1

    async def test_artifact_register_idempotent_returns_updated(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_register is idempotent: re-registering same type+path returns action='updated'.

        Tests: Idempotency via MCP tool (architect spec 7.3 scenario 2)
        How: Register same artifact twice; assert second call returns action='updated'
             and artifact_count is still 1.
        Why: The MCP tool must surface idempotent upsert to callers.
        """
        from fastmcp.client import Client

        # Arrange
        async with Client(patched_mcp_server) as client:
            await client.call_tool(
                "artifact_register",
                {
                    "item_id": 965,
                    "artifact_type": "architect",
                    "artifact_id": "plan/architect-foo.md",
                    "content": "# Architect Spec\n\nDraft.",
                    "status": "draft",
                    "agent": "agent",
                },
            )

            # Act — register same artifact_id again
            result = await client.call_tool(
                "artifact_register",
                {
                    "item_id": 965,
                    "artifact_type": "architect",
                    "artifact_id": "plan/architect-foo.md",
                    "content": "# Architect Spec\n\nCurrent.",
                    "status": "current",
                    "agent": "updated-agent",
                },
            )

        # Assert
        data = result.data
        assert data["registered"] is True
        assert data["action"] == "updated"
        assert data["artifact_count"] == 1  # Still one entry

    async def test_artifact_register_invalid_type_returns_error(self, patched_mcp_server: Any) -> None:
        """artifact_register returns error dict for an unknown artifact_type value.

        Tests: Input validation error handling in artifact_register
        How: Pass an unknown artifact type string; assert 'error' key in response.
        Why: Callers must receive an informative error, not an unhandled exception.
        """
        from fastmcp.client import Client

        # Arrange / Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool(
                "artifact_register",
                {
                    "item_id": 100,
                    "artifact_type": "not-a-real-type",
                    "artifact_id": "plan/something.md",
                    "content": "irrelevant — invalid type is rejected before content is used",
                },
            )

        # Assert
        assert "error" in result.data

    async def test_artifact_register_invalid_status_returns_error(self, patched_mcp_server: Any) -> None:
        """artifact_register returns error dict for an unknown status value.

        Tests: Status value validation in artifact_register
        How: Pass an unknown status string; assert 'error' key in response.
        Why: Invalid status values must produce an error, not silently default.
        """
        from fastmcp.client import Client

        # Arrange / Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool(
                "artifact_register",
                {
                    "item_id": 100,
                    "artifact_type": "architect",
                    "artifact_id": "plan/architect-foo.md",
                    "content": "irrelevant — invalid status is rejected before content is used",
                    "status": "not-a-real-status",
                },
            )

        # Assert
        assert "error" in result.data


class TestMCPToolArtifactList:
    """Integration tests for the artifact_list MCP tool.

    Tests: Listing all artifacts, filtered listing, empty manifest.
    """

    async def test_artifact_list_returns_all_entries_when_no_filter(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_list returns all registered artifacts when no type filter is applied.

        Tests: Unfiltered artifact_list response
        How: Register two entries of different types; list without filter; assert count=2.
        Why: Consumers need to enumerate all artifacts for a given issue.
        """
        from fastmcp.client import Client

        # Arrange — populate backend with two entries
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=965)
        manifest = registry.register(
            manifest,
            ArtifactEntry(artifact_type=ArtifactType.FEATURE_CONTEXT, artifact_id="plan/feature-context-foo.md"),
        )
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, artifact_id="plan/architect-foo.md")
        )
        in_memory_backend.set_manifest(965, manifest)

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_list", {"item_id": 965})

        # Assert
        data = result.data
        assert data["count"] == 2
        assert len(data["artifacts"]) == 2

    async def test_artifact_list_filters_by_type(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_list returns only entries matching the artifact_type filter.

        Tests: Type-filtered listing
        How: Register two entries; list with type filter; assert count=1.
        Why: Callers often need only one artifact type (e.g., just the architect spec).
        """
        from fastmcp.client import Client

        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=10)
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, artifact_id="plan/architect-test.md")
        )
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.TASK_PLAN, artifact_id="plan/tasks-1-test.yaml")
        )
        in_memory_backend.set_manifest(10, manifest)

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_list", {"item_id": 10, "artifact_type": "architect"})

        # Assert
        data = result.data
        assert data["count"] == 1
        assert data["artifacts"][0]["artifact_type"] == "architect"

    async def test_artifact_list_returns_empty_for_issue_with_no_manifest(self, patched_mcp_server: Any) -> None:
        """artifact_list returns empty artifacts list when the issue has no manifest.

        Tests: Empty list response — not an error
        How: Call artifact_list on an issue number with no registered artifacts.
        Why: Consumers fall back to filesystem paths when list returns empty.
        """
        from fastmcp.client import Client

        # Arrange — issue 999 has no manifest in in_memory_backend

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_list", {"item_id": 999})

        # Assert
        data = result.data
        assert data["count"] == 0
        assert data["artifacts"] == []
        assert "error" not in data


class TestMCPToolArtifactGet:
    """Integration tests for the artifact_get MCP tool.

    Tests: Successful retrieval by type, error on absent type.
    """

    async def test_artifact_get_returns_entries_for_existing_type(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_get returns artifact entries for an existing type.

        Tests: Successful artifact_get response
        How: Register architect entry; call artifact_get for architect; assert entry returned.
        Why: Verifies the get-by-type delegation through the full MCP pipeline.
        """
        from fastmcp.client import Client

        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=50)
        manifest = registry.register(
            manifest,
            ArtifactEntry(
                artifact_type=ArtifactType.ARCHITECT, artifact_id="plan/architect-bar.md", agent="spec-agent"
            ),
        )
        in_memory_backend.set_manifest(50, manifest)

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_get", {"item_id": 50, "artifact_type": "architect"})

        # Assert
        data = result.data
        assert data["count"] == 1
        assert data["artifacts"][0]["artifact_id"] == "plan/architect-bar.md"

    async def test_artifact_get_returns_error_for_absent_type(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_get returns an error when the requested type is not registered.

        Tests: Type-not-found error path in artifact_get
        How: Call artifact_get for task-plan on issue with only architect entry.
        Why: Callers need a clear error signal when an artifact type is absent.
        """
        from fastmcp.client import Client

        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=51)
        manifest = registry.register(
            manifest, ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, artifact_id="plan/architect-baz.md")
        )
        in_memory_backend.set_manifest(51, manifest)

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_get", {"item_id": 51, "artifact_type": "task-plan"})

        # Assert
        assert "error" in result.data


class TestMCPToolArtifactRead:
    """Integration tests for the artifact_read MCP tool.

    Tests: Content retrieval, type-not-found error, cache-miss FileNotFoundError.
    """

    async def test_artifact_read_returns_file_content(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_read returns the file content for a registered and present artifact.

        Tests: Full read pipeline through artifact_read MCP tool
        How: Register artifact in manifest; add file to backend; call artifact_read;
             assert content returned.
        Why: Verifies the complete path from manifest lookup through file read.
        """
        from fastmcp.client import Client

        # Arrange
        registry = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=200)
        entry = ArtifactEntry(
            artifact_type=ArtifactType.FEATURE_CONTEXT,
            artifact_id="plan/feature-context-test.md",
            status=ArtifactStatus.CURRENT,
        )
        manifest = registry.register(manifest, entry)
        in_memory_backend.set_manifest(200, manifest)
        in_memory_backend.add_file("plan/feature-context-test.md", "# Feature Context\n\nTest content.")

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_read", {"item_id": 200, "artifact_type": "feature-context"})

        # Assert
        data = result.data
        assert "content" in data
        assert "# Feature Context" in data["content"]
        assert data["path"] == "plan/feature-context-test.md"  # ArtifactContent.path maps to ArtifactEntry.artifact_id

    async def test_artifact_read_returns_error_when_type_not_registered(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_read returns an error when the artifact type has no entry.

        Tests: Type-not-found path in artifact_read
        How: Call artifact_read on an issue with no registered artifacts.
        Why: Callers must receive an error when requesting an unregistered artifact.
        """
        from fastmcp.client import Client

        # Arrange — issue 300 has an empty manifest

        # Act
        async with Client(patched_mcp_server) as client:
            result = await client.call_tool("artifact_read", {"item_id": 300, "artifact_type": "architect"})

        # Assert
        assert "error" in result.data

    async def test_artifact_read_raises_tool_error_on_file_not_found(
        self, patched_mcp_server: Any, in_memory_backend: _InMemoryArtifactBackend
    ) -> None:
        """artifact_read raises ToolError when artifact is registered but file is missing.

        Tests: Cache miss — file not present in worktree (architect spec 7.3 scenario 8)
        How: Register artifact in manifest but do NOT add file to backend;
             call artifact_read; assert ToolError is raised (ContentNotFoundError is
             not caught by the tool's error handling and propagates as ToolError).
        Why: The registered artifact may not yet be committed in the current worktree.
             FastMCP surfaces unhandled exceptions as ToolError to the caller.

        Note: The server's artifact_read catches ValueError, KeyError, and BacklogError.
              ContentNotFoundError is a ContentProviderError, not a BacklogError, so it
              is not caught. This is the actual server contract — callers must handle
              ToolError for cache-miss scenarios. This test documents the existing
              behaviour as a specification test.
        """
        from fastmcp.client import Client
        from fastmcp.exceptions import ToolError

        # Arrange — manifest has entry but file is not in backend._files
        reg = ArtifactRegistry()
        manifest = ArtifactManifest(issue_number=400)
        manifest = reg.register(
            manifest,
            ArtifactEntry(
                artifact_type=ArtifactType.TASK_PLAN,
                artifact_id="plan/tasks-1-missing.yaml",
                status=ArtifactStatus.CURRENT,
            ),
        )
        in_memory_backend.set_manifest(400, manifest)
        # Intentionally NOT calling in_memory_backend.add_file(...)

        # Act / Assert — FileNotFoundError propagates as ToolError
        with pytest.raises(ToolError):
            async with Client(patched_mcp_server) as client:
                await client.call_tool("artifact_read", {"item_id": 400, "artifact_type": "task-plan"})


# ---------------------------------------------------------------------------
# create_artifact_provider factory tests
# ---------------------------------------------------------------------------


class TestCreateArtifactProviderFactory:
    """Unit tests for the create_artifact_provider() factory function.

    Tests: Provider selection, credential reading from env vars, unsupported
           backend rejection, BACKLOG_BACKEND env var fallback.
    """

    def test_github_backend_returns_github_gist_provider(self, tmp_path: Path) -> None:
        """create_artifact_provider returns GitHubGistArtifactProvider for backend_name="github".

        Tests: Factory produces correct type for GitHub backend.
        How: Call with backend_name="github", repo="owner/repo"; assert isinstance.
        Why: Consumer code relies on factory to select the correct implementation.
        """
        # Arrange / Act
        provider = create_artifact_provider(backend_name="github", repo="owner/repo", root_worktree=tmp_path)

        # Assert
        assert isinstance(provider, GitHubGistArtifactProvider)

    def test_linear_backend_returns_linear_provider(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_artifact_provider returns LinearArtifactProvider for backend_name="linear".

        Tests: Factory produces correct type for Linear backend.
        How: Set LINEAR_API_KEY and LINEAR_TEAM_ID env vars; call with backend_name="linear".
        Why: Linear backend requires env vars; factory must read and inject them.
        """
        # Arrange
        monkeypatch.setenv("LINEAR_API_KEY", "test-linear-key")
        monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid")

        # Act
        provider = create_artifact_provider(backend_name="linear", root_worktree=tmp_path)

        # Assert
        assert isinstance(provider, LinearArtifactProvider)

    def test_gitlab_backend_returns_gitlab_provider(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_artifact_provider returns GitLabArtifactProvider for backend_name="gitlab".

        Tests: Factory produces correct type for GitLab backend.
        How: Set GITLAB_TOKEN and GITLAB_PROJECT_ID env vars; call with backend_name="gitlab".
        Why: GitLab backend requires env vars; factory must read and inject them.
        """
        # Arrange
        monkeypatch.setenv("GITLAB_TOKEN", "test-gitlab-token")
        monkeypatch.setenv("GITLAB_PROJECT_ID", "123")

        # Act
        provider = create_artifact_provider(backend_name="gitlab", root_worktree=tmp_path)

        # Assert
        assert isinstance(provider, GitLabArtifactProvider)

    def test_sqlite_backend_raises_backlog_error(self, tmp_path: Path) -> None:
        """create_artifact_provider raises BacklogError for backend_name="sqlite".

        Tests: Non-remote backends are rejected with a clear error.
        How: Call with backend_name="sqlite"; assert BacklogError raised.
        Why: SQLite does not support remote artifact storage; the error message
             guides users to select a supported backend.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="sqlite"):
            create_artifact_provider(backend_name="sqlite")

    def test_memory_backend_raises_backlog_error(self, tmp_path: Path) -> None:
        """create_artifact_provider raises BacklogError for backend_name="memory".

        Tests: In-memory backend is rejected with a clear error.
        How: Call with backend_name="memory"; assert BacklogError raised.
        Why: Memory backend has no persistence; artifact storage requires persistence.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="memory"):
            create_artifact_provider(backend_name="memory")

    def test_unknown_backend_raises_backlog_error(self) -> None:
        """create_artifact_provider raises BacklogError for an unrecognised backend name.

        Tests: Unknown backend names are rejected with a descriptive error.
        How: Call with backend_name="redis"; assert BacklogError raised.
        Why: Silent failures from unknown names would be hard to debug.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="Unknown"):
            create_artifact_provider(backend_name="redis")

    def test_reads_backlog_backend_env_var_when_backend_name_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_artifact_provider reads BACKLOG_BACKEND env var when backend_name is None.

        Tests: Env var fallback — backend_name=None → read BACKLOG_BACKEND.
        How: Set BACKLOG_BACKEND=github; call with backend_name=None; assert GitHub provider.
        Why: Callers omit backend_name when the backend should be determined from config.
        """
        # Arrange
        monkeypatch.setenv("BACKLOG_BACKEND", "github")

        # Act
        provider = create_artifact_provider(backend_name=None, repo="owner/repo", root_worktree=tmp_path)

        # Assert
        assert isinstance(provider, GitHubGistArtifactProvider)

    def test_defaults_to_github_when_no_backend_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_artifact_provider defaults to GitHub when BACKLOG_BACKEND is not set.

        Tests: Default backend selection when neither argument nor env var is set.
        How: Unset BACKLOG_BACKEND; call with backend_name=None and repo; assert GitHub provider.
        Why: Existing deployments rely on GitHub as the default; no configuration change needed.
        """
        # Arrange
        monkeypatch.delenv("BACKLOG_BACKEND", raising=False)

        # Act
        provider = create_artifact_provider(backend_name=None, repo="owner/repo", root_worktree=tmp_path)

        # Assert
        assert isinstance(provider, GitHubGistArtifactProvider)

    def test_linear_backend_missing_api_key_raises_backlog_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_artifact_provider raises BacklogError when LINEAR_API_KEY is not set.

        Tests: Missing credential detection for Linear backend.
        How: Ensure LINEAR_API_KEY is unset; call with backend_name="linear".
        Why: Clear error at factory time prevents confusing failures deep inside provider methods.
        """
        # Arrange
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)

        # Act / Assert
        with pytest.raises(BacklogError, match="LINEAR_API_KEY"):
            create_artifact_provider(backend_name="linear", root_worktree=tmp_path)

    def test_gitlab_backend_missing_token_raises_backlog_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_artifact_provider raises BacklogError when GITLAB_TOKEN is not set.

        Tests: Missing credential detection for GitLab backend.
        How: Ensure GITLAB_TOKEN is unset; call with backend_name="gitlab".
        Why: Clear error at factory time prevents confusing failures deep inside provider methods.
        """
        # Arrange
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)

        # Act / Assert
        with pytest.raises(BacklogError, match="GITLAB_TOKEN"):
            create_artifact_provider(backend_name="gitlab", root_worktree=tmp_path)

    def test_gitlab_backend_missing_project_id_raises_backlog_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_artifact_provider raises BacklogError when GITLAB_PROJECT_ID is not set.

        Tests: Missing project ID detection for GitLab backend.
        How: Set GITLAB_TOKEN but unset GITLAB_PROJECT_ID; call with backend_name="gitlab".
        Why: GITLAB_PROJECT_ID is required to route API calls to the correct project.
        """
        # Arrange
        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.delenv("GITLAB_PROJECT_ID", raising=False)

        # Act / Assert
        with pytest.raises(BacklogError, match="GITLAB_PROJECT_ID"):
            create_artifact_provider(backend_name="gitlab", root_worktree=tmp_path)
