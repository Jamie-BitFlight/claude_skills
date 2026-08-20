"""Unit tests for dh_paths module.

Tests cover:
- compute_slug(): slug format for various path inputs
- git_project_root(): real Git repositories and linked worktrees
- infer_project_root(): env/workspace hints, including Codex's PWD forwarding
- All *_dir() functions: correct absolute paths given a known project_root
- ensure_dirs(): idempotent directory creation
- DH_STATE_HOME override: env var changes base directory
- Cache behaviour: repeated calls with same cwd return cached results
- LEGACY_PATH_MAP: expected keys present
- _get_dh_user_root(): module-level alias re-reads env on each call
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import dh_paths
import git
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


def _init_repo(path: Path) -> git.Repo:
    """Create a commit-bearing repository suitable for linked-worktree tests."""
    repo = git.Repo.init(path)
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    repo.index.add(["tracked.txt"])
    repo.index.commit("initial commit")
    return repo


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

        Tests: compute_slug with a multi-component path
        How: Pass /home/developer/repos/myproject and verify result
        Why: Ensures all separators are converted, not just the first
        """
        # Arrange
        path = Path("/home/developer/repos/myproject")

        # Act
        slug = compute_slug(path)

        # Assert
        assert slug == "-home-developer-repos-myproject"

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
    """Tests for GitPython root discovery using real repositories."""

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    def test_git_project_root_main_repo_returns_parent_of_git_dir(self, tmp_path: Path) -> None:
        """Verify main worktree root is the parent of the .git directory.

        Tests: git_project_root resolves the project root for a main worktree
        How: Create a repository and resolve from its root; assert parent
        Why: Main repo .git parent is always the project root
        """
        # Arrange
        repo = tmp_path / "repo"
        _init_repo(repo)

        # Act
        result = git_project_root(cwd=repo)

        # Assert
        assert result == repo

    def test_git_project_root_worktree_returns_common_dir_parent(self, tmp_path: Path) -> None:
        """Verify linked worktree resolves to the main repo root, not the worktree path.

        Tests: git_project_root handles worktrees via --git-common-dir
        How: Create a linked worktree and resolve from it
        Why: All worktrees sharing a repo must produce the same state slug
        """
        # Arrange
        main_repo = tmp_path / "main-repo"
        main = _init_repo(main_repo)
        worktree_dir = tmp_path / "worktree"
        main.git.worktree("add", str(worktree_dir))

        # Act
        result = git_project_root(cwd=worktree_dir)

        # Assert — resolves to main repo root, not worktree root
        assert result == main_repo

    def test_git_project_root_not_a_git_repo_raises_invalid_git_repository_error(self, tmp_path: Path) -> None:
        """Verify GitPython propagates an invalid repository error outside Git.

        Tests: git_project_root fails fast outside a Git repository
        How: Resolve an ordinary directory
        Why: Fail-fast principle; callers must know when git is unavailable
        """
        # Arrange
        # Act / Assert
        with pytest.raises(git.exc.InvalidGitRepositoryError):
            git_project_root(cwd=tmp_path)

    def test_git_project_root_caches_result_for_same_cwd(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify repeated calls with the same cwd construct GitPython Repo once.

        Tests: git_project_root caches result per cwd
        How: Spy on GitPython Repo; call git_project_root twice from the same repo
        Why: Per-process caching avoids repeated repository discovery
        """
        # Arrange
        repo = tmp_path / "repo"
        _init_repo(repo)
        repo_constructor = mocker.spy(dh_paths.git, "Repo")

        # Act
        git_project_root(cwd=repo)
        git_project_root(cwd=repo)

        assert repo_constructor.call_count == 1

    def test_git_project_root_different_cwds_each_resolved_independently(self, tmp_path: Path) -> None:
        """Verify different cwd values each trigger an independent resolution.

        Tests: git_project_root resolves two distinct cwds to distinct roots
        How: Create two repositories and resolve each root
        Why: Cache is keyed by cwd so different dirs must not share cached results
        """
        # Arrange
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        _init_repo(dir_a)
        _init_repo(dir_b)

        # Act
        result_a = git_project_root(cwd=dir_a)
        result_b = git_project_root(cwd=dir_b)

        # Assert — two distinct roots resolved
        assert result_a != result_b


# ---------------------------------------------------------------------------
# _git_common_root — resource cleanup and hang protection
# ---------------------------------------------------------------------------


class TestGitCommonRootResourceCleanup:
    """Tests that the GitPython Repo object constructed internally is closed."""

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    def test_git_common_root_closes_repo_object(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """_git_common_root closes the GitPython Repo it constructs.

        Tests: resource cleanup for the Repo object built inside _git_common_root
        How: Spy on git.Repo.close; resolve a real repo; assert close was called
             exactly once for *this* repo instance
        Why: An unclosed Repo leaks file handles/locks across repeated resolutions.
             The spy patches git.Repo.close at the class level, so it also
             observes close() calls on unrelated Repo instances constructed
             elsewhere in the same test process (e.g. finalized by GC during a
             full-suite run) -- filter to calls on this repo_path specifically
             instead of asserting a bare global call_count, which is flaky
             under full-suite/xdist execution.
        """
        # Arrange
        repo_path = tmp_path / "repo"
        _init_repo(repo_path)
        close_spy = mocker.spy(git.Repo, "close")

        # Act
        dh_paths._git_common_root(repo_path)

        # Assert -- working_dir survives close(), so it reliably identifies
        # which Repo instance a given close() call targeted.
        calls_for_this_repo = [call for call in close_spy.call_args_list if call.args[0].working_dir == str(repo_path)]
        assert len(calls_for_this_repo) == 1


class TestGitCommonRootHangProtection:
    """Tests that a hung GitPython Repo() construction times out with an actionable error.

    Strategy: monkeypatch git.Repo with a stub that sleeps past a shortened
    timeout, proving the wrapper itself enforces the bound rather than relying
    on the real (long) production timeout in a test.
    """

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    @staticmethod
    def _install_hanging_repo_stub(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dh_paths, "_GIT_RESOLUTION_TIMEOUT_SECONDS", 0.05)

        def _hang(*args: object, **kwargs: object) -> git.Repo:
            del args, kwargs
            time.sleep(2)
            raise AssertionError("hanging stub should never return")

        monkeypatch.setattr(dh_paths.git, "Repo", _hang)

    def test_git_common_root_raises_timeout_error_on_hang(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_git_common_root bounds a hung Repo() construction and raises an actionable error.

        Tests: GitResolutionTimeoutError is raised (not an indefinite hang)
        How: Stub git.Repo to sleep past a shortened timeout; call _git_common_root
        Why: A bad NFS mount must fail fast with a diagnosable message, not hang forever
        """
        # Arrange
        self._install_hanging_repo_stub(monkeypatch)

        # Act / Assert — bounded by the shortened timeout, not the 2-second stub sleep
        with pytest.raises(dh_paths.GitResolutionTimeoutError, match="unreachable network filesystem"):
            dh_paths._git_common_root(tmp_path)

    def test_git_root_if_directory_treats_hang_as_failed_candidate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_git_root_if_directory treats a hang as a failed candidate, not a fatal error.

        Tests: hang handling inside the per-hint candidate resolver
        How: Stub git.Repo to hang; call _git_root_if_directory; expect None
        Why: A hang on one candidate directory must not abort the whole hint chain
        """
        # Arrange
        self._install_hanging_repo_stub(monkeypatch)

        # Act
        result = dh_paths._git_root_if_directory(tmp_path)

        # Assert
        assert result is None

    def test_infer_project_root_raises_actionable_runtime_error_on_hang(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """infer_project_root turns a final-fallback git hang into the documented RuntimeError.

        Tests: end-to-end hang handling through the public resolution entrypoint
        How: Disable all env hints; stub git.Repo to hang; call infer_project_root
        Why: Callers (MCP servers, CLI) need the same actionable message a timed-out
             subprocess git call used to produce, not a silent indefinite hang
        """
        # Arrange
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
        self._install_hanging_repo_stub(monkeypatch)

        # Act / Assert
        with pytest.raises(RuntimeError, match="unreachable network filesystem"):
            dh_paths.infer_project_root(tmp_path)

    def test_hung_worker_is_left_as_a_daemon_thread_not_an_executor_thread(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A timed-out worker must be exempt from being joined at interpreter shutdown.

        Tests: the abandoned worker thread's daemon flag
        How: Stub git.Repo to hang; trigger a timeout; inspect the still-running thread
        Why: A concurrent.futures.ThreadPoolExecutor worker is joined by an atexit hook
             regardless of shutdown(wait=False), so a genuinely wedged filesystem call
             would hang the whole process at exit, not just this function -- reproduced
             directly (see PR #2787 review) by observing a subprocess exit code 124 despite
             the timeout firing correctly inside it. A daemon threading.Thread is exempt
             from that join.
        """
        # Arrange
        threads_before = set(threading.enumerate())
        self._install_hanging_repo_stub(monkeypatch)

        # Act
        with pytest.raises(dh_paths.GitResolutionTimeoutError):
            dh_paths._git_common_root(tmp_path)

        # Assert -- the abandoned worker is a daemon thread, exempt from interpreter-exit join
        new_threads = set(threading.enumerate()) - threads_before
        assert new_threads, "expected the timed-out worker thread to still be running"
        assert all(thread.daemon for thread in new_threads)

    def test_real_git_error_propagates_unchanged_across_the_worker_thread(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A genuine GitPython error raised inside the worker reaches the caller's thread unchanged.

        Tests: cross-thread exception forwarding for the non-hang, non-timeout path
        How: Stub git.Repo to raise InvalidGitRepositoryError immediately; call _git_common_root
        Why: Exceptions do not cross thread boundaries automatically -- the worker must
             forward the original exception via the result queue, not just a timeout
        """

        def _raise(*args: object, **kwargs: object) -> git.Repo:
            del args, kwargs
            raise git.exc.InvalidGitRepositoryError(str(tmp_path))

        monkeypatch.setattr(dh_paths.git, "Repo", _raise)

        with pytest.raises(git.exc.InvalidGitRepositoryError):
            dh_paths._git_common_root(tmp_path)


# ---------------------------------------------------------------------------
# infer_project_root — MCP / env hints
# ---------------------------------------------------------------------------


class TestInferProjectRoot:
    """Tests for infer_project_root(): env and workspace hints before cwd."""

    def setup_method(self) -> None:
        """Clear module-level root cache before each test."""
        dh_paths._root_cache.clear()

    def test_infer_respects_dh_project_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """DH_PROJECT_ROOT pointing at a repo resolves via git common dir."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        monkeypatch.setenv("DH_PROJECT_ROOT", str(repo))

        assert infer_project_root() == repo

    def test_git_project_root_without_cwd_uses_infer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """git_project_root(None) applies DH_PROJECT_ROOT like infer_project_root."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        monkeypatch.setenv("DH_PROJECT_ROOT", str(repo))

        assert git_project_root() == repo

    def test_infer_uses_codex_pwd_when_plugin_cwd_is_not_a_repository(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Codex MCP uses its forwarded agent PWD instead of the plugin cache cwd."""
        project = tmp_path / "project"
        plugin_cache = tmp_path / "plugin-cache"
        _init_repo(project)
        plugin_cache.mkdir()
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("CODEX_THREAD_ID", "codex-test-thread")
        monkeypatch.setenv("PWD", str(project))
        monkeypatch.chdir(plugin_cache)

        assert infer_project_root() == project

    def test_infer_ignores_codex_pwd_when_cwd_is_explicit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Codex PWD hint only applies to the no-arg (MCP) resolution path."""
        pwd_repo = tmp_path / "pwd-repo"
        explicit_repo = tmp_path / "explicit-repo"
        _init_repo(pwd_repo)
        _init_repo(explicit_repo)
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("CODEX_THREAD_ID", "codex-test-thread")
        monkeypatch.setenv("PWD", str(pwd_repo))

        assert infer_project_root(cwd=explicit_repo) == explicit_repo

    def test_infer_workspace_folder_paths_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """WORKSPACE_FOLDER_PATHS JSON array first folder is used."""
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        repo = tmp_path / "ws"
        _init_repo(repo)
        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", json.dumps([str(repo)]))

        assert infer_project_root() == repo

    def test_infer_workspace_folder_paths_precedes_claude_project_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """VS Code/Cursor WORKSPACE_FOLDER_PATHS is used before CLAUDE_PROJECT_DIR."""
        claude_side = tmp_path / "claude-path"
        ws_side = tmp_path / "workspace-path"
        _init_repo(claude_side)
        _init_repo(ws_side)
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_side))
        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", json.dumps([str(ws_side)]))

        assert infer_project_root() == ws_side

    def test_infer_fails_with_runtime_error_when_no_project_root_is_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When all strategies fail, raise an actionable error."""
        monkeypatch.delenv("DH_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CURSOR_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)
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

    Strategy: Pass an explicit project root and use DH_STATE_HOME to run
    ensure_dirs in a fully isolated tmp_path environment.
    """

    def test_ensure_dirs_creates_all_expected_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify ensure_dirs creates all Tier 2 and Tier 3 subdirectories.

        Tests: ensure_dirs creates backlog, plan, plan/codebase, milestones,
               research, context, and reports directories
        How: Mock git; call ensure_dirs; assert each expected dir exists
        Why: All consumers depend on these directories existing before writing
        """
        # Arrange
        dh_paths._root_cache.clear()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))

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
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify ensure_dirs creates the in-repo .dh/ dir with .gitkeep file.

        Tests: Tier 1 directory and .gitkeep creation
        How: Call ensure_dirs; assert .dh/ and .dh/.gitkeep exist
        Why: .dh/ must exist in-repo so git tracks it across clones
        """
        # Arrange
        dh_paths._root_cache.clear()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))

        # Act
        ensure_dirs(project_root=tmp_path)

        # Assert
        assert (tmp_path / ".dh").is_dir()
        assert (tmp_path / ".dh" / ".gitkeep").exists()

    def test_ensure_dirs_is_idempotent_called_twice_no_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify ensure_dirs can be called twice without raising an error.

        Tests: ensure_dirs idempotency via mkdir(exist_ok=True)
        How: Call ensure_dirs twice in sequence; assert no exception and dirs remain
        Why: Producers call ensure_dirs defensively; it must not fail on repeat
        """
        # Arrange
        dh_paths._root_cache.clear()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))

        # Act — calling twice must not raise
        ensure_dirs(project_root=tmp_path)
        ensure_dirs(project_root=tmp_path)

        # Assert — directories still exist after second call
        assert (tmp_path / ".dh").is_dir()

    def test_ensure_dirs_returns_state_root_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify ensure_dirs returns the state_root path.

        Tests: ensure_dirs return value is the per-project state root
        How: Call ensure_dirs; compare returned path to state_root(project_root)
        Why: Return value allows callers to chain directory creation and use
        """
        # Arrange
        dh_paths._root_cache.clear()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))

        # Act
        result = ensure_dirs(project_root=tmp_path)

        # Assert
        expected = state_root(project_root=tmp_path)
        assert result == expected

    def test_ensure_dirs_does_not_delete_existing_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify ensure_dirs preserves existing files when called again.

        Tests: ensure_dirs does not wipe existing state on second invocation
        How: Create sentinel file in backlog; call ensure_dirs again; assert file remains
        Why: ensure_dirs must be safe to call even when state already exists
        """
        # Arrange
        dh_paths._root_cache.clear()
        monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh"))

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
