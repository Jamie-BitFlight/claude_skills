"""Unit tests for dh_paths module.

Tests cover:
- compute_slug(): slug format for various path inputs
- git_project_root(): subprocess mock for main repo and worktree scenarios
- All *_dir() functions: correct absolute paths given a known project_root
- ensure_dirs(): idempotent directory creation
- DH_STATE_HOME override: env var changes base directory
- Cache behaviour: repeated calls with same cwd return cached results
- LEGACY_PATH_MAP: expected keys present
- _get_dh_user_root(): module-level alias re-reads env on each call
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import dh_paths
import pytest
from dh_paths import (
    LEGACY_PATH_MAP,
    _get_dh_user_root,
    backlog_dir,
    compute_slug,
    context_dir,
    ensure_dirs,
    git_project_root,
    infer_project_root,
    milestones_dir,
    plan_dir,
    project_dh_dir,
    reports_dir,
    research_dir,
    state_root,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_git_run_mock(common_dir: Path):
    """Return a side-effect callable that simulates git rev-parse output.

    Args:
        common_dir: The fake .git common directory path to return in stdout.

    Returns:
        A callable suitable for use as mocker.patch side_effect.
    """

    def _side_effect(args, **kwargs):
        return type("CompletedProcess", (), {"stdout": str(common_dir) + "\n", "returncode": 0})()

    return _side_effect


# ---------------------------------------------------------------------------
# compute_slug
# ---------------------------------------------------------------------------


class TestComputeSlug:
    """Tests for compute_slug(): slug format for various path inputs.

    Strategy: Pass explicit Path objects and verify the replacement algorithm
    produces dash-prefixed, slash-free slug strings matching the documented
    contract: str(path).replace('/', '-').
    """

    def test_compute_slug_simple_path_returns_dash_prefixed_slug(self) -> None:
        """Verify simple nested path produces the correct slug.

        Tests: compute_slug with a straightforward unix path
        How: Pass /home/user/repos/project and assert exact slug value
        Why: Documents the core slug format contract for consumers
        """
        # Arrange
        path = Path("/home/user/repos/project")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug == "-home-user-repos-project"

    def test_compute_slug_nested_path_replaces_all_slashes(self) -> None:
        """Verify every slash in the path is replaced with a dash.

        Tests: compute_slug with a real-world project path
        How: Pass /home/ubuntulinuxqa2/repos/claude_skills and verify result
        Why: Ensures all separators are converted, not just the first
        """
        # Arrange
        path = Path("/home/ubuntulinuxqa2/repos/claude_skills")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug == "-home-ubuntulinuxqa2-repos-claude_skills"

    def test_compute_slug_path_with_underscores_preserves_underscores(self) -> None:
        """Verify underscores in path components are preserved unchanged.

        Tests: compute_slug with path containing underscores
        How: Pass path with underscore directory name and verify it survives
        Why: Slug must not mangle valid path characters other than forward slash
        """
        # Arrange
        path = Path("/home/user/my_project")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug == "-home-user-my_project"

    def test_compute_slug_short_path_produces_minimal_slug(self) -> None:
        """Verify a single-segment path produces a minimal slug.

        Tests: compute_slug with /project (one level deep)
        How: Pass /project and assert slug is -project
        Why: Confirms minimal path edge case works correctly
        """
        # Arrange
        path = Path("/project")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug == "-project"

    def test_compute_slug_leading_dash_is_always_present(self) -> None:
        """Verify every slug starts with a dash due to leading slash replacement.

        Tests: compute_slug always produces dash-prefixed output
        How: Pass any absolute path and check startswith('-')
        Why: Leading dash is documented as intentional for namespace distinctness
        """
        # Arrange
        path = Path("/anything")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug.startswith("-")

    def test_compute_slug_no_forward_slashes_in_result(self) -> None:
        """Verify no forward slashes remain in the slug output.

        Tests: compute_slug eliminates all forward slashes
        How: Pass deeply nested path and assert '/' not in result
        Why: Slug must be filesystem-safe as a directory name component
        """
        # Arrange
        path = Path("/home/user/deep/nested/directory/structure")

        # Act
        slug = compute_slug(path)

        # Assert
        assert "/" not in slug


# ---------------------------------------------------------------------------
# git_project_root
# ---------------------------------------------------------------------------


class TestGitProjectRoot:
    """Tests for git_project_root(): subprocess-mocked git rev-parse behaviour.

    Strategy: Use mocker.patch to intercept subprocess.run and simulate git
    output for main repo, worktree, error, and caching scenarios. Each test
    clears the module-level cache to avoid inter-test interference.
    """

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    def test_git_project_root_main_repo_returns_parent_of_git_dir(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify main worktree root is the parent of the .git directory.

        Tests: git_project_root resolves the project root for a main worktree
        How: Mock subprocess.run to return fake .git dir path; assert parent
        Why: Main repo .git parent is always the project root
        """
        # Arrange
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act
        result = git_project_root(cwd=tmp_path)

        # Assert
        assert result == tmp_path

    def test_git_project_root_worktree_returns_common_dir_parent(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify linked worktree resolves to the main repo root, not the worktree path.

        Tests: git_project_root handles worktrees via --git-common-dir
        How: Simulate common dir pointing to main repo; call from worktree cwd
        Why: All worktrees sharing a repo must produce the same state slug
        """
        # Arrange
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        common_git_dir = main_repo / ".git"
        common_git_dir.mkdir()
        worktree_dir = tmp_path / "worktree"
        worktree_dir.mkdir()
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(common_git_dir))

        # Act
        result = git_project_root(cwd=worktree_dir)

        # Assert — resolves to main repo root, not worktree root
        assert result == main_repo

    def test_git_project_root_not_a_git_repo_raises_called_process_error(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Verify CalledProcessError propagates when git reports non-zero exit.

        Tests: git_project_root fails fast outside a git repo
        How: Mock subprocess.run to raise CalledProcessError
        Why: Fail-fast principle; callers must know when git is unavailable
        """
        # Arrange
        mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git"))

        # Act / Assert
        with pytest.raises(subprocess.CalledProcessError):
            git_project_root(cwd=tmp_path)

    def test_git_project_root_uses_list_args_not_shell(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify subprocess.run is called with a list (not shell=True).

        Tests: git_project_root subprocess call uses safe list args
        How: Capture the args passed to subprocess.run and inspect them
        Why: ADR-002 and security requirement: no shell injection via shell=True
        """
        # Arrange
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        captured: list[list[str]] = []

        def _capture(args, **kwargs):  # type: ignore[no-untyped-def]
            captured.append(args)
            return type("CP", (), {"stdout": str(fake_git_dir) + "\n", "returncode": 0})()

        mocker.patch("subprocess.run", side_effect=_capture)

        # Act
        git_project_root(cwd=tmp_path)

        # Assert — args is a list; first element is "git"; --git-common-dir present
        assert isinstance(captured[0], list)
        assert captured[0][0] == "git"
        assert "--git-common-dir" in captured[0]

    def test_git_project_root_caches_result_for_same_cwd(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify repeated calls with the same cwd invoke subprocess only once.

        Tests: git_project_root caches result per cwd
        How: Count subprocess.run calls; call git_project_root twice from same dir
        Why: Per-process caching avoids repeated git subprocess overhead
        """
        # Arrange
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        mock_run = mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act
        git_project_root(cwd=tmp_path)
        git_project_root(cwd=tmp_path)

        # Assert — subprocess called only once; second call served from cache
        assert mock_run.call_count == 1

    def test_git_project_root_different_cwds_each_resolved_independently(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Verify different cwd values each trigger an independent resolution.

        Tests: git_project_root resolves two distinct cwds to distinct roots
        How: Call from dir_a then dir_b; verify results differ and call count is 2
        Why: Cache is keyed by cwd so different dirs must not share cached results
        """
        # Arrange
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        git_a = dir_a / ".git"
        git_b = dir_b / ".git"
        git_a.mkdir()
        git_b.mkdir()
        call_count: dict[str, int] = {"n": 0}

        def _tracking(args, **kwargs):  # type: ignore[no-untyped-def]
            call_count["n"] += 1
            cwd_used = str(kwargs.get("cwd", ""))
            git_dir = git_a if str(dir_a) in cwd_used else git_b
            return type("CP", (), {"stdout": str(git_dir) + "\n", "returncode": 0})()

        mocker.patch("subprocess.run", side_effect=_tracking)

        # Act
        result_a = git_project_root(cwd=dir_a)
        result_b = git_project_root(cwd=dir_b)

        # Assert — two distinct roots resolved
        assert result_a != result_b
        assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# infer_project_root — MCP / env hints
# ---------------------------------------------------------------------------


class TestInferProjectRoot:
    """Tests for infer_project_root(): env and workspace hints before cwd."""

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    def test_infer_respects_dh_project_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """DH_PROJECT_ROOT pointing at a repo resolves via git common dir."""
        repo = tmp_path / "repo"
        repo.mkdir()
        fake_git = repo / ".git"
        fake_git.mkdir()
        monkeypatch.setenv("DH_PROJECT_ROOT", str(repo))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git))

        assert infer_project_root() == repo

    def test_git_project_root_without_cwd_uses_infer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """git_project_root(None) applies DH_PROJECT_ROOT like infer_project_root."""
        repo = tmp_path / "repo"
        repo.mkdir()
        fake_git = repo / ".git"
        fake_git.mkdir()
        monkeypatch.setenv("DH_PROJECT_ROOT", str(repo))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git))

        assert git_project_root() == repo

    def test_infer_workspace_folder_paths_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """WORKSPACE_FOLDER_PATHS JSON array first folder is used."""
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        repo = tmp_path / "ws"
        repo.mkdir()
        fake_git = repo / ".git"
        fake_git.mkdir()
        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", json.dumps([str(repo)]))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git))

        assert infer_project_root() == repo

    def test_infer_workspace_folder_paths_precedes_claude_project_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """VS Code/Cursor WORKSPACE_FOLDER_PATHS is used before CLAUDE_PROJECT_DIR."""
        claude_side = tmp_path / "claude-path"
        ws_side = tmp_path / "workspace-path"
        claude_side.mkdir()
        ws_side.mkdir()
        (claude_side / ".git").mkdir()
        (ws_side / ".git").mkdir()
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_side))
        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", json.dumps([str(ws_side)]))

        def _side_effect(args: list[str], **kwargs: object) -> object:
            cwd = str(kwargs.get("cwd", ""))
            git_dir = ws_side / ".git" if str(ws_side) in cwd else claude_side / ".git"
            return type("CP", (), {"stdout": str(git_dir) + "\n", "returncode": 0})()

        mocker.patch("subprocess.run", side_effect=_side_effect)

        assert infer_project_root() == ws_side

    def test_infer_fails_with_runtime_error_wrapping_git_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """When all strategies fail, raise RuntimeError with chained CalledProcessError."""
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
        mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git"))

        with pytest.raises(RuntimeError, match="Could not resolve the git project root"):
            infer_project_root(tmp_path)


# ---------------------------------------------------------------------------
# Path functions — given an explicit project_root
# ---------------------------------------------------------------------------


class TestPathFunctions:
    """Verify each *_dir() function returns the correct subpath.

    Strategy: All tests pass an explicit project_root to avoid subprocess calls.
    DH_STATE_HOME is set via monkeypatch so state paths stay in tmp_path.
    """

    def test_project_dh_dir_returns_dh_under_project_root(self, tmp_path: Path) -> None:
        """Verify project_dh_dir returns {project_root}/.dh.

        Tests: Tier 1 in-repo config directory path
        How: Call with explicit tmp_path; assert result is tmp_path/.dh
        Why: .dh/ is the committed project config namespace (Tier 1)
        """
        # Arrange / Act
        result = project_dh_dir(project_root=tmp_path)

        # Assert
        assert result == tmp_path / ".dh"

    def test_state_root_returns_path_under_dh_user_root_with_slug(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify state_root constructs the correct per-project state path.

        Tests: state_root produces DH_STATE_HOME/projects/{slug}/
        How: Set DH_STATE_HOME; compute expected slug; compare paths
        Why: state_root is the base for all Tier 2 and Tier 3 directories
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = state_root(project_root=project)

        # Assert
        expected_slug = compute_slug(project)
        assert result == tmp_path / "dh" / "projects" / expected_slug

    def test_backlog_dir_returns_backlog_under_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify backlog_dir is state_root/backlog.

        Tests: backlog_dir path composition
        How: Compare result to state_root(...)/backlog
        Why: Backlog markdown files live under this directory
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = backlog_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "backlog"

    def test_plan_dir_returns_plan_under_state_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify plan_dir is state_root/plan.

        Tests: plan_dir path composition
        How: Compare result to state_root(...)/plan
        Why: SAM plan YAML files live under this directory
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = plan_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "plan"

    def test_milestones_dir_returns_milestones_under_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify milestones_dir is state_root/milestones.

        Tests: milestones_dir path composition
        How: Compare result to state_root(...)/milestones
        Why: Milestone artifacts live under this directory
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = milestones_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "milestones"

    def test_research_dir_returns_research_under_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify research_dir is state_root/research.

        Tests: research_dir path composition
        How: Compare result to state_root(...)/research
        Why: Research artifacts live under this directory
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = research_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "research"

    def test_context_dir_returns_context_under_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify context_dir is state_root/context.

        Tests: context_dir path composition
        How: Compare result to state_root(...)/context
        Why: Active-task JSON session context files live here
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = context_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "context"

    def test_reports_dir_returns_reports_under_state_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify reports_dir is state_root/reports.

        Tests: reports_dir path composition
        How: Compare result to state_root(...)/reports
        Why: Investigation and analysis reports live here
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act
        result = reports_dir(project_root=project)

        # Assert
        assert result == state_root(project_root=project) / "reports"

    def test_all_dir_functions_return_absolute_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify every *_dir() function returns an absolute Path.

        Tests: all path functions produce absolute paths
        How: Iterate all six state-dir functions; assert is_absolute()
        Why: Relative paths would break consumers that use them as base dirs
        """
        # Arrange
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        project = Path("/home/user/repo")

        # Act / Assert
        for fn in (backlog_dir, plan_dir, milestones_dir, research_dir, context_dir, reports_dir):
            result = fn(project_root=project)
            assert result.is_absolute(), f"{fn.__name__} returned non-absolute path: {result}"


# ---------------------------------------------------------------------------
# DH_STATE_HOME environment variable override
# ---------------------------------------------------------------------------


class TestDHStateHomeOverride:
    """Tests for DH_STATE_HOME env var override behaviour.

    Strategy: Use monkeypatch to set/clear DH_STATE_HOME and verify that
    _dh_user_root() (and by extension all *_dir() functions) respond correctly.
    """

    def test_state_root_uses_dh_state_home_when_set(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify DH_STATE_HOME redirects the base state directory.

        Tests: DH_STATE_HOME env var is respected by state_root
        How: Set DH_STATE_HOME to custom_home; verify result starts with it
        Why: Test isolation and CI require redirectable state root
        """
        # Arrange
        custom_home = tmp_path / "custom-dh"
        monkeypatch.setenv("DH_STATE_HOME", str(custom_home))
        project = Path("/home/user/project")

        # Act
        result = state_root(project_root=project)

        # Assert
        assert str(result).startswith(str(custom_home))

    def test_state_root_uses_home_dh_when_dh_state_home_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify default state root is ~/.dh when DH_STATE_HOME is unset.

        Tests: Default state root falls back to ~/.dh
        How: Delete DH_STATE_HOME; check result starts with Path.home()/'.dh'
        Why: ~/.dh is the documented default for user installations
        """
        # Arrange
        monkeypatch.delenv("DH_STATE_HOME", raising=False)
        project = Path("/home/user/project")

        # Act
        result = state_root(project_root=project)

        # Assert
        assert str(result).startswith(str(Path.home() / ".dh"))

    def test_backlog_dir_respects_dh_state_home_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify backlog_dir base directory changes when DH_STATE_HOME is set.

        Tests: backlog_dir inherits DH_STATE_HOME override
        How: Set env var; check result path prefix and final segment name
        Why: All state dirs must honour the same override consistently
        """
        # Arrange
        custom_home = tmp_path / "env-override"
        monkeypatch.setenv("DH_STATE_HOME", str(custom_home))
        project = Path("/home/user/project")

        # Act
        result = backlog_dir(project_root=project)

        # Assert
        assert str(result).startswith(str(custom_home))
        assert result.name == "backlog"

    def test_plan_dir_respects_dh_state_home_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify plan_dir base directory changes when DH_STATE_HOME is set.

        Tests: plan_dir inherits DH_STATE_HOME override
        How: Set env var; check result path prefix and final segment name
        Why: SAM plan files must move to the overridden state home
        """
        # Arrange
        custom_home = tmp_path / "env-override"
        monkeypatch.setenv("DH_STATE_HOME", str(custom_home))
        project = Path("/home/user/project")

        # Act
        result = plan_dir(project_root=project)

        # Assert
        assert str(result).startswith(str(custom_home))
        assert result.name == "plan"

    def test_context_dir_respects_dh_state_home_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify context_dir base directory changes when DH_STATE_HOME is set.

        Tests: context_dir inherits DH_STATE_HOME override
        How: Set env var; check result path prefix and final segment name
        Why: Session context files must move to the overridden state home
        """
        # Arrange
        custom_home = tmp_path / "env-override"
        monkeypatch.setenv("DH_STATE_HOME", str(custom_home))
        project = Path("/home/user/project")

        # Act
        result = context_dir(project_root=project)

        # Assert
        assert str(result).startswith(str(custom_home))
        assert result.name == "context"

    def test_two_different_env_values_produce_different_roots(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify changing DH_STATE_HOME between calls produces distinct state roots.

        Tests: DH_STATE_HOME is re-evaluated on each call (not cached)
        How: Set env to home-a; get root; set env to home-b; get root; compare
        Why: monkeypatch-driven test isolation requires per-call re-evaluation
        """
        # Arrange
        project = Path("/home/user/project")

        # Act
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "home-a"))
        root_a = state_root(project_root=project)

        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "home-b"))
        root_b = state_root(project_root=project)

        # Assert
        assert root_a != root_b

    def test_get_dh_user_root_reads_env_on_each_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify _get_dh_user_root() re-reads DH_STATE_HOME every invocation.

        Tests: _get_dh_user_root module-level alias is not cached
        How: Set DH_STATE_HOME to path-a; call; change to path-b; call again
        Why: Tests using monkeypatch rely on the function re-reading the env
             var rather than using a stale cached value from import time
        """
        # Arrange
        path_a = tmp_path / "dh-a"
        path_b = tmp_path / "dh-b"

        # Act
        monkeypatch.setenv("DH_STATE_HOME", str(path_a))
        result_a = _get_dh_user_root()

        monkeypatch.setenv("DH_STATE_HOME", str(path_b))
        result_b = _get_dh_user_root()

        # Assert — each call reflects the current env var value
        assert result_a == path_a
        assert result_b == path_b
        assert result_a != result_b


# ---------------------------------------------------------------------------
# ensure_dirs
# ---------------------------------------------------------------------------


class TestEnsureDirs:
    """Tests for ensure_dirs(): idempotent directory creation.

    Strategy: Use mocker.patch on subprocess.run and DH_STATE_HOME monkeypatch
    to run ensure_dirs in a fully isolated tmp_path environment.
    """

    def test_ensure_dirs_creates_all_expected_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify ensure_dirs creates all Tier 2 and Tier 3 subdirectories.

        Tests: ensure_dirs creates backlog, plan, plan/codebase, milestones,
               research, context, and reports directories
        How: Mock git; call ensure_dirs; assert each expected dir exists
        Why: All consumers depend on these directories existing before writing
        """
        # Arrange
        dh_paths._root_cache.clear()
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act
        returned = ensure_dirs(project_root=tmp_path)

        # Assert — all tier-2 and tier-3 dirs exist
        expected_dirs = [
            returned / "backlog",
            returned / "plan",
            returned / "plan" / "codebase",
            returned / "milestones",
            returned / "research",
            returned / "context",
            returned / "reports",
        ]
        for d in expected_dirs:
            assert d.is_dir(), f"Expected directory not created: {d}"

    def test_ensure_dirs_creates_tier1_dh_dir_with_gitkeep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify ensure_dirs creates the in-repo .dh/ dir with .gitkeep file.

        Tests: Tier 1 directory and .gitkeep creation
        How: Call ensure_dirs; assert .dh/ and .dh/.gitkeep exist
        Why: .dh/ must exist in-repo so git tracks it across clones
        """
        # Arrange
        dh_paths._root_cache.clear()
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act
        ensure_dirs(project_root=tmp_path)

        # Assert
        assert (tmp_path / ".dh").is_dir()
        assert (tmp_path / ".dh" / ".gitkeep").exists()

    def test_ensure_dirs_is_idempotent_called_twice_no_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify ensure_dirs can be called twice without raising an error.

        Tests: ensure_dirs idempotency via mkdir(exist_ok=True)
        How: Call ensure_dirs twice in sequence; assert no exception and dirs remain
        Why: Producers call ensure_dirs defensively; it must not fail on repeat
        """
        # Arrange
        dh_paths._root_cache.clear()
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act — calling twice must not raise
        ensure_dirs(project_root=tmp_path)
        ensure_dirs(project_root=tmp_path)

        # Assert — directories still exist after second call
        assert (tmp_path / ".dh").is_dir()

    def test_ensure_dirs_returns_state_root_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify ensure_dirs returns the state_root path.

        Tests: ensure_dirs return value is the per-project state root
        How: Call ensure_dirs; compare returned path to state_root(project_root)
        Why: Return value allows callers to chain directory creation and use
        """
        # Arrange
        dh_paths._root_cache.clear()
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        # Act
        result = ensure_dirs(project_root=tmp_path)

        # Assert
        expected = state_root(project_root=tmp_path)
        assert result == expected

    def test_ensure_dirs_does_not_delete_existing_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Verify ensure_dirs preserves existing files when called again.

        Tests: ensure_dirs does not wipe existing state on second invocation
        How: Create sentinel file in backlog; call ensure_dirs again; assert file remains
        Why: ensure_dirs must be safe to call even when state already exists
        """
        # Arrange
        dh_paths._root_cache.clear()
        fake_git_dir = tmp_path / ".git"
        fake_git_dir.mkdir()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))
        mocker.patch("subprocess.run", side_effect=_make_git_run_mock(fake_git_dir))

        state = ensure_dirs(project_root=tmp_path)
        sentinel = state / "backlog" / "sentinel.txt"
        sentinel.write_text("keep me")

        # Act
        ensure_dirs(project_root=tmp_path)

        # Assert — sentinel file untouched
        assert sentinel.exists()
        assert sentinel.read_text() == "keep me"


# ---------------------------------------------------------------------------
# LEGACY_PATH_MAP
# ---------------------------------------------------------------------------


class TestLegacyPathMap:
    """Tests for LEGACY_PATH_MAP constant: presence, mapping correctness, callability.

    Strategy: Assert dictionary contents directly — no subprocess or filesystem
    operations needed. All assertions are pure dict/attribute checks.
    """

    def test_legacy_path_map_contains_backlog_key(self) -> None:
        """Verify .claude/backlog key is present in LEGACY_PATH_MAP.

        Tests: LEGACY_PATH_MAP key presence for backlog directory
        How: Assert key in dict
        Why: Migration tool uses this map to discover all old-path consumers
        """
        assert ".claude/backlog" in LEGACY_PATH_MAP

    def test_legacy_path_map_contains_plan_key(self) -> None:
        """Verify plan key is present in LEGACY_PATH_MAP.

        Tests: LEGACY_PATH_MAP key presence for plan directory
        How: Assert key in dict
        Why: Migration tool must recognise the plan/ prefix
        """
        assert "plan" in LEGACY_PATH_MAP

    def test_legacy_path_map_contains_context_key(self) -> None:
        """Verify .claude/context key is present in LEGACY_PATH_MAP.

        Tests: LEGACY_PATH_MAP key presence for context directory
        How: Assert key in dict
        Why: Migration tool must recognise the .claude/context/ prefix
        """
        assert ".claude/context" in LEGACY_PATH_MAP

    def test_legacy_path_map_contains_reports_key(self) -> None:
        """Verify .claude/reports key is present in LEGACY_PATH_MAP.

        Tests: LEGACY_PATH_MAP key presence for reports directory
        How: Assert key in dict
        Why: Migration tool must recognise the .claude/reports/ prefix
        """
        assert ".claude/reports" in LEGACY_PATH_MAP

    def test_legacy_path_map_backlog_maps_to_backlog_dir(self) -> None:
        """Verify .claude/backlog maps to the string 'backlog_dir'.

        Tests: LEGACY_PATH_MAP maps backlog prefix to correct function name
        How: Assert dict value equals expected string
        Why: Automated reference updates use this value to generate import calls
        """
        assert LEGACY_PATH_MAP[".claude/backlog"] == "backlog_dir"

    def test_legacy_path_map_plan_maps_to_plan_dir(self) -> None:
        """Verify plan maps to the string 'plan_dir'.

        Tests: LEGACY_PATH_MAP maps plan prefix to correct function name
        How: Assert dict value equals expected string
        Why: Automated reference updates must produce the correct function name
        """
        assert LEGACY_PATH_MAP["plan"] == "plan_dir"

    def test_legacy_path_map_context_maps_to_context_dir(self) -> None:
        """Verify .claude/context maps to the string 'context_dir'.

        Tests: LEGACY_PATH_MAP maps context prefix to correct function name
        How: Assert dict value equals expected string
        Why: Hook scripts need to find and update their context path references
        """
        assert LEGACY_PATH_MAP[".claude/context"] == "context_dir"

    def test_legacy_path_map_reports_maps_to_reports_dir(self) -> None:
        """Verify .claude/reports maps to the string 'reports_dir'.

        Tests: LEGACY_PATH_MAP maps reports prefix to correct function name
        How: Assert dict value equals expected string
        Why: Reports dir consumers need correct function reference in migration
        """
        assert LEGACY_PATH_MAP[".claude/reports"] == "reports_dir"

    def test_legacy_path_map_all_values_are_callable_function_names(self) -> None:
        """Verify every value in LEGACY_PATH_MAP names a callable on dh_paths.

        Tests: LEGACY_PATH_MAP values are resolvable and callable attributes
        How: Use hasattr + callable check on dh_paths module for each value
        Why: Map is only useful if every value resolves to an actual function
        """
        for value in LEGACY_PATH_MAP.values():
            assert hasattr(dh_paths, value), f"dh_paths has no attribute '{value}'"
            assert callable(getattr(dh_paths, value)), f"dh_paths.{value} is not callable"
