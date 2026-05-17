"""Integration tests for _get_artifact_provider fallback chain.

Covers seven named scenarios from architect §8 Testing Architecture and
four warning-merge tests (one per artifact MCP tool).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import backlog_core.server as _server
import pytest
from backlog_core.artifact_provider import ArtifactBackend
from backlog_core.artifact_provider_local import LocalFilesystemArtifactProvider
from backlog_core.backends.bd_runner import BdRunner
from backlog_core.backends.beads_artifact_provider import BeadsArtifactProvider
from backlog_core.models import BacklogError, GitHubUnavailableError

from tests.helpers import call_mcp_tool

if TYPE_CHECKING:
    from pathlib import Path

_EXPECTED_WARNING = "Artifacts stored in local filesystem provider. Remote sync unavailable."

# ---------------------------------------------------------------------------
# Exception-raising helpers — avoid lambda-based raise anti-pattern
# ---------------------------------------------------------------------------


def _raise_github_unavailable(**_kw: object) -> None:
    """Raise GitHubUnavailableError; used as a create_artifact_provider replacement."""
    raise GitHubUnavailableError("no token")


def _raise_backlog_error(**_kw: object) -> None:
    """Raise BacklogError; used as a create_artifact_provider replacement."""
    raise BacklogError("connection refused")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset _get_artifact_provider singleton globals before every test."""
    monkeypatch.setattr(_server, "_artifact_provider", None)
    monkeypatch.setattr(_server, "_artifact_provider_warning", None)


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect DH_STATE_HOME to tmp_path; return a fake repo root directory."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


@pytest.fixture
def active_fallback(isolated_state: Path, monkeypatch: pytest.MonkeyPatch) -> LocalFilesystemArtifactProvider:
    """Pre-populate singleton with a local provider and warning for warning-merge tests."""
    manifest_dir = isolated_state.parent / "artifacts"
    manifest_dir.mkdir(exist_ok=True)
    provider = LocalFilesystemArtifactProvider(root_worktree=isolated_state, manifest_dir=manifest_dir)
    monkeypatch.setattr(_server, "_artifact_provider", provider)
    monkeypatch.setattr(_server, "_artifact_provider_warning", _EXPECTED_WARNING)
    return provider


# ---------------------------------------------------------------------------
# In-process MCP call helper
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Invoke a backlog MCP tool in-process and return the parsed JSON response.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(_server.mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Seven fallback-chain scenario tests
# ---------------------------------------------------------------------------


class TestFallbackChain:
    """Named scenarios from architect §8 Testing Architecture."""

    def test_no_repo_configured_uses_local_provider(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no default repo is configured the local provider is returned."""
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "")
        monkeypatch.setattr(_server._dh_paths, "git_project_root", lambda: isolated_state)

        provider = _server._get_artifact_provider()

        assert isinstance(provider, LocalFilesystemArtifactProvider)
        assert _server._artifact_provider_warning == _EXPECTED_WARNING

    def test_remote_provider_returned_when_create_succeeds(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When create_artifact_provider succeeds its result is returned with no warning."""
        mock_remote: ArtifactBackend = MagicMock(spec=ArtifactBackend)
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", lambda **kw: mock_remote)

        provider = _server._get_artifact_provider()

        assert provider is mock_remote
        assert _server._artifact_provider_warning is None

    def test_github_unavailable_error_falls_back_to_local(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GitHubUnavailableError from create_artifact_provider triggers local fallback."""
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", _raise_github_unavailable)
        monkeypatch.setattr(_server._dh_paths, "git_project_root", lambda: isolated_state)

        provider = _server._get_artifact_provider()

        assert isinstance(provider, LocalFilesystemArtifactProvider)
        assert _server._artifact_provider_warning == _EXPECTED_WARNING

    def test_backlog_error_falls_back_to_local(self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """BacklogError from create_artifact_provider triggers local fallback."""
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", _raise_backlog_error)
        monkeypatch.setattr(_server._dh_paths, "git_project_root", lambda: isolated_state)

        provider = _server._get_artifact_provider()

        assert isinstance(provider, LocalFilesystemArtifactProvider)
        assert _server._artifact_provider_warning == _EXPECTED_WARNING

    def test_local_provider_return_value_sets_warning(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When create_artifact_provider returns a LocalFilesystemArtifactProvider the warning is set."""
        local_provider = LocalFilesystemArtifactProvider(root_worktree=isolated_state)
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", lambda **kw: local_provider)

        provider = _server._get_artifact_provider()

        assert provider is local_provider
        assert isinstance(provider, LocalFilesystemArtifactProvider)
        assert _server._artifact_provider_warning == _EXPECTED_WARNING

    def test_explicit_local_backend_env_var_selects_local_provider(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BACKLOG_BACKEND=local selects the local provider directly without raising or falling back."""
        monkeypatch.setenv("BACKLOG_BACKEND", "local")
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server._dh_paths, "git_project_root", lambda: isolated_state)

        provider = _server._get_artifact_provider()

        assert isinstance(provider, LocalFilesystemArtifactProvider)
        assert _server._artifact_provider_warning == _EXPECTED_WARNING

    def test_singleton_cached_after_first_call(self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Subsequent calls return the identical cached instance."""
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", lambda **kw: MagicMock(spec=ArtifactBackend))

        first = _server._get_artifact_provider()
        second = _server._get_artifact_provider()

        assert first is second

    def test_create_provider_called_exactly_once_per_session(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_artifact_provider is invoked exactly once regardless of call count."""
        call_count = 0

        def _counting_create(**kw: object) -> ArtifactBackend:
            nonlocal call_count
            call_count += 1
            return MagicMock(spec=ArtifactBackend)

        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", _counting_create)

        _server._get_artifact_provider()
        _server._get_artifact_provider()
        _server._get_artifact_provider()

        assert call_count == 1

    def test_beads_provider_returned_without_local_warning(
        self, isolated_state: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BeadsArtifactProvider from create_artifact_provider sets no local-provider warning.

        The warning is set only when the provider is a LocalFilesystemArtifactProvider.
        BeadsArtifactProvider is a remote-capable provider; no fallback warning applies.
        """
        mock_runner = MagicMock(spec=BdRunner)
        beads_provider = BeadsArtifactProvider(runner=mock_runner)
        monkeypatch.setattr(_server._models, "get_default_repo", lambda: "owner/repo")
        monkeypatch.setattr(_server._models, "get_repo_root", lambda: isolated_state)
        monkeypatch.setattr(_server, "create_artifact_provider", lambda **kw: beads_provider)

        provider = _server._get_artifact_provider()

        assert provider is beads_provider
        assert isinstance(provider, BeadsArtifactProvider)
        assert _server._artifact_provider_warning is None


# ---------------------------------------------------------------------------
# Warning-merge tests — one per artifact MCP tool
# ---------------------------------------------------------------------------


async def test_warning_surfaces_in_artifact_register_response(active_fallback: LocalFilesystemArtifactProvider) -> None:
    """artifact_register response warnings list contains the local-provider warning."""
    result = await _call(
        "artifact_register",
        {
            "issue_number": 9999,
            "artifact_type": "research",
            "artifact_id": "research-fallback-warning-test",
            "content": "test content for warning merge test",
        },
    )
    assert _EXPECTED_WARNING in result.get("warnings", [])


async def test_warning_surfaces_in_artifact_list_response(active_fallback: LocalFilesystemArtifactProvider) -> None:
    """artifact_list response warnings list contains the local-provider warning."""
    result = await _call("artifact_list", {"issue_number": 9999})
    assert _EXPECTED_WARNING in result.get("warnings", [])


async def test_warning_surfaces_in_artifact_get_response(active_fallback: LocalFilesystemArtifactProvider) -> None:
    """artifact_get response warnings list contains the local-provider warning."""
    result = await _call("artifact_get", {"issue_number": 9999, "artifact_type": "research"})
    assert _EXPECTED_WARNING in result.get("warnings", [])


async def test_warning_surfaces_in_artifact_read_response(active_fallback: LocalFilesystemArtifactProvider) -> None:
    """artifact_read response warnings list contains the local-provider warning."""
    result = await _call("artifact_read", {"issue_number": 9999, "artifact_type": "research"})
    assert _EXPECTED_WARNING in result.get("warnings", [])
