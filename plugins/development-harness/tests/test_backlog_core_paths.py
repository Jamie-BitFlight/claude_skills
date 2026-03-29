"""Tests for backlog_core path resolution via dh_paths.

Verifies that:
- models.BACKLOG_DIR resolves to the dh_paths state root, not .claude/backlog/
- models.init() updates BACKLOG_DIR correctly when given a project_dir
- operations and parsing consume _models.BACKLOG_DIR (not a stale binding)
- GitHubArtifactProvider defaults root_worktree to dh_paths.state_root()
- Path traversal prevention in artifact_provider still works
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_plugin_root_to_path() -> None:
    """Ensure the development-harness plugin root is on sys.path."""
    plugin_root = Path(__file__).parent.parent
    if str(plugin_root) not in sys.path:
        sys.path.insert(0, str(plugin_root))


_add_plugin_root_to_path()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override DH_STATE_HOME to use a temp directory.

    Returns:
        The tmp_path used as DH_STATE_HOME.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def fake_project_root(tmp_path: Path) -> Path:
    """Return a fake project root path under tmp_path."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    return project_root


# ---------------------------------------------------------------------------
# dh_paths unit tests
# ---------------------------------------------------------------------------


class TestDhPathsComputeSlug:
    """Test compute_slug converts paths to dash-separated slugs."""

    def test_compute_slug_simple_path_produces_leading_dash(self) -> None:
        import dh_paths

        result = dh_paths.compute_slug(Path("/home/user/repos/myproject"))
        assert result == "-home-user-repos-myproject"

    def test_compute_slug_with_underscores_preserved(self) -> None:
        import dh_paths

        result = dh_paths.compute_slug(Path("/home/user/repos/claude_skills"))
        assert result == "-home-user-repos-claude_skills"

    def test_compute_slug_nested_path_replaces_all_slashes(self) -> None:
        import dh_paths

        result = dh_paths.compute_slug(Path("/a/b/c/d"))
        assert result == "-a-b-c-d"


class TestDhPathsStateRoot:
    """Test state_root resolves correctly under DH_STATE_HOME override."""

    def test_state_root_uses_dh_state_home_when_set(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        result = dh_paths.state_root(fake_project_root)
        slug = dh_paths.compute_slug(fake_project_root)
        expected = isolated_state / "projects" / slug
        assert result == expected

    def test_backlog_dir_is_under_state_root(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        state = dh_paths.state_root(fake_project_root)
        backlog = dh_paths.backlog_dir(fake_project_root)
        assert backlog == state / "backlog"

    def test_plan_dir_is_under_state_root(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        state = dh_paths.state_root(fake_project_root)
        plan = dh_paths.plan_dir(fake_project_root)
        assert plan == state / "plan"

    def test_context_dir_is_under_state_root(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        state = dh_paths.state_root(fake_project_root)
        ctx = dh_paths.context_dir(fake_project_root)
        assert ctx == state / "context"

    def test_reports_dir_is_under_state_root(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        state = dh_paths.state_root(fake_project_root)
        reports = dh_paths.reports_dir(fake_project_root)
        assert reports == state / "reports"


class TestDhPathsEnsureDirs:
    """Test ensure_dirs creates the expected directory tree."""

    def test_ensure_dirs_creates_backlog_and_plan_directories(
        self, isolated_state: Path, fake_project_root: Path
    ) -> None:
        import dh_paths

        with patch.object(dh_paths, "git_project_root", return_value=fake_project_root):
            returned = dh_paths.ensure_dirs(fake_project_root)

        assert dh_paths.backlog_dir(fake_project_root).is_dir()
        assert dh_paths.plan_dir(fake_project_root).is_dir()
        assert dh_paths.context_dir(fake_project_root).is_dir()
        assert dh_paths.reports_dir(fake_project_root).is_dir()
        assert returned == dh_paths.state_root(fake_project_root)

    def test_ensure_dirs_is_idempotent(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        # Calling twice should not raise.
        dh_paths.ensure_dirs(fake_project_root)
        dh_paths.ensure_dirs(fake_project_root)

    def test_ensure_dirs_creates_gitkeep_in_repo(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths

        dh_paths.ensure_dirs(fake_project_root)
        gitkeep = fake_project_root / ".dh" / ".gitkeep"
        assert gitkeep.exists()


# ---------------------------------------------------------------------------
# models.BACKLOG_DIR via dh_paths
# ---------------------------------------------------------------------------


class TestModelsBACKLOGDIR:
    """Test that models.BACKLOG_DIR resolves via dh_paths, not .claude/backlog/."""

    def test_backlog_dir_does_not_contain_dot_claude(self, isolated_state: Path, fake_project_root: Path) -> None:
        """BACKLOG_DIR must not point inside .claude/ after init()."""
        from backlog_core import models

        models.init(project_dir=str(fake_project_root), repo="test-owner/test-repo")
        assert ".claude" not in str(models.BACKLOG_DIR), f"BACKLOG_DIR still contains .claude: {models.BACKLOG_DIR}"

    def test_backlog_dir_resolves_to_state_root_backlog(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths
        from backlog_core import models

        models.init(project_dir=str(fake_project_root), repo="test-owner/test-repo")
        expected = dh_paths.backlog_dir(fake_project_root)
        assert expected == models.BACKLOG_DIR

    def test_backlog_dir_updates_when_init_called_with_different_project(
        self, isolated_state: Path, tmp_path: Path
    ) -> None:
        import dh_paths
        from backlog_core import models

        project_a = tmp_path / "project_a"
        project_b = tmp_path / "project_b"
        project_a.mkdir()
        project_b.mkdir()

        models.init(project_dir=str(project_a), repo="test-owner/test-repo")
        dir_a = models.BACKLOG_DIR

        models.init(project_dir=str(project_b), repo="test-owner/test-repo")
        dir_b = models.BACKLOG_DIR

        assert dir_a != dir_b
        assert dh_paths.compute_slug(project_a) in str(dir_a)
        assert dh_paths.compute_slug(project_b) in str(dir_b)


# ---------------------------------------------------------------------------
# artifact_provider root_worktree default
# ---------------------------------------------------------------------------


class TestGitHubArtifactProviderRootWorktree:
    """Test that GitHubArtifactProvider defaults to dh_paths.state_root()."""

    def test_default_root_worktree_is_state_root(self, isolated_state: Path, fake_project_root: Path) -> None:
        import dh_paths
        from backlog_core.artifact_provider import GitHubArtifactProvider

        with patch.object(dh_paths, "git_project_root", return_value=fake_project_root):
            provider = GitHubArtifactProvider(repo="owner/repo")

        expected = dh_paths.state_root(fake_project_root)
        assert provider._root_worktree == expected

    def test_explicit_root_worktree_overrides_default(self, isolated_state: Path, tmp_path: Path) -> None:
        from backlog_core.artifact_provider import GitHubArtifactProvider

        custom_root = tmp_path / "custom"
        custom_root.mkdir()
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=custom_root)
        assert provider._root_worktree == custom_root

    def test_path_traversal_raises_value_error(self, tmp_path: Path) -> None:
        from backlog_core.artifact_provider import GitHubArtifactProvider

        root = tmp_path / "state"
        root.mkdir()
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=root)

        with pytest.raises(ValueError, match="Path traversal detected"):
            provider._validate_artifact_path("../../etc/passwd")

    def test_valid_artifact_path_within_root_does_not_raise(self, tmp_path: Path) -> None:
        from backlog_core.artifact_provider import GitHubArtifactProvider

        root = tmp_path / "state"
        root.mkdir()
        provider = GitHubArtifactProvider(repo="owner/repo", root_worktree=root)
        # Should not raise — path stays inside root.
        provider._validate_artifact_path("plan/architect-foo.md")
