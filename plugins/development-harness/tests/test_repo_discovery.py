"""Tests for repository discovery in backlog_core.models.

Covers: discover_repo() priority chain, RepoDiscoveryError, _validate_repo_slug(),
_discover_via_env(), _discover_via_git(), and lru_cache behaviour.

Test strategy:
- Each test is isolated: lru_cache is cleared in an autouse fixture
- External calls (git.Repo) are mocked at the module boundary
- monkeypatch controls environment variables
- pytest-mock (mocker.patch) is used exclusively — no unittest.mock imports
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.models as _bc_models
import pytest
from backlog_core.models import (
    BacklogConfig,
    RepoDiscoveryError,
    _discover_via_env,
    _discover_via_git,
    _validate_repo_slug,
    discover_repo,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Autouse fixture: always reset lru_cache between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_discover_repo_cache() -> Generator[None, None, None]:
    """Clear discover_repo lru_cache before every test.

    Tests: Cache isolation — each test starts with a fresh discovery state.
    How: Call discover_repo.cache_clear() before the test body runs.
    Why: lru_cache persists for the process lifetime; without clearing it
         the first test result poisons all subsequent tests.
    """
    discover_repo.cache_clear()
    yield
    discover_repo.cache_clear()


# ---------------------------------------------------------------------------
# RepoDiscoveryError
# ---------------------------------------------------------------------------


class TestRepoDiscoveryError:
    """RepoDiscoveryError stores context and formats actionable messages.

    Tests the exception's data model and message template to ensure
    operators receive enough context to self-diagnose discovery failures.
    """

    def test_repo_discovery_error_stores_methods_tried(self) -> None:
        """methods_tried attribute preserves the list of attempted methods.

        Tests: RepoDiscoveryError.methods_tried storage
        How: Construct with known list; assert attribute equality.
        Why: Callers may inspect methods_tried programmatically.
        """
        err = RepoDiscoveryError(
            methods_tried=["env", "gh", "git"], details=["env not set", "gh not found", "no remote"]
        )
        assert err.methods_tried == ["env", "gh", "git"]

    def test_repo_discovery_error_message_contains_tried_header(self) -> None:
        """Error message includes 'Tried:' section header.

        Tests: RepoDiscoveryError message template
        How: Construct error; assert 'Tried:' in str(err).
        Why: Users reading the exception must be able to see what was attempted.
        """
        err = RepoDiscoveryError(methods_tried=["env"], details=["GITHUB_REPO environment variable: not set or empty"])
        assert "Tried:" in str(err)

    def test_repo_discovery_error_message_contains_detail_lines(self) -> None:
        """Each detail string appears in the formatted error message.

        Tests: RepoDiscoveryError detail enumeration
        How: Provide two detail strings; assert both appear in str(err).
        Why: Operators need per-method failure reason, not just method names.
        """
        err = RepoDiscoveryError(methods_tried=["env", "gh"], details=["env not set", "gh not found in PATH"])
        msg = str(err)
        assert "env not set" in msg
        assert "gh not found in PATH" in msg

    def test_repo_discovery_error_message_contains_fix_instructions(self) -> None:
        """Error message includes actionable fix instructions.

        Tests: RepoDiscoveryError fix template
        How: Construct error; assert GITHUB_REPO fix instruction is present.
        Why: Users should not need to read source code to know how to fix the error.
        """
        err = RepoDiscoveryError(methods_tried=[], details=[])
        assert "GITHUB_REPO=owner/repo" in str(err)

    def test_repo_discovery_error_message_attribute_matches_str(self) -> None:
        """error.message attribute equals str(error).

        Tests: RepoDiscoveryError.message attribute consistency
        How: Construct; compare .message with str().
        Why: Callers may access .message directly or catch via str(); both must agree.
        """
        err = RepoDiscoveryError(methods_tried=["env"], details=["not set"])
        assert err.message == str(err)

    def test_repo_discovery_error_is_exception_subclass(self) -> None:
        """RepoDiscoveryError is catchable as a plain Exception.

        Tests: Exception hierarchy
        How: assert issubclass check.
        Why: Callers using broad except Exception must still catch it.
        """
        assert issubclass(RepoDiscoveryError, Exception)

    def test_repo_discovery_error_is_raised_and_caught(self) -> None:
        """RepoDiscoveryError can be raised and caught by its own type.

        Tests: raise / except RepoDiscoveryError round-trip
        How: raise inside pytest.raises context.
        Why: Smoke-test for basic exception plumbing.
        """
        with pytest.raises(RepoDiscoveryError):
            raise RepoDiscoveryError(methods_tried=[], details=[])


# ---------------------------------------------------------------------------
# _validate_repo_slug
# ---------------------------------------------------------------------------


class TestValidateRepoSlug:
    """_validate_repo_slug rejects invalid formats and accepts valid ones.

    All public entry points that accept user-supplied repo slugs call this
    function. Thorough validation here prevents injection via env vars.
    """

    @pytest.mark.parametrize(
        "slug", ["owner/repo", "my-org/my-repo", "Owner123/Repo.Name", "A/B", "org.name/repo_name", "o-r-g/r-e-p-o"]
    )
    def test_validate_repo_slug_returns_valid_slug_unchanged(self, slug: str) -> None:
        """Valid owner/repo slugs are returned as-is.

        Tests: _validate_repo_slug happy path
        How: Pass well-formed slugs; assert return value equals input.
        Why: Function must not transform valid input — callers rely on idempotency.
        """
        result = _validate_repo_slug(slug)
        assert result == slug

    @pytest.mark.parametrize(
        "slug", ["", "no-slash", "/no-owner", "no-repo/", "owner/repo/extra", "owner repo", "owner\t/repo"]
    )
    def test_validate_repo_slug_raises_for_invalid_format(self, slug: str) -> None:
        """Invalid slugs raise RepoDiscoveryError.

        Tests: _validate_repo_slug rejection
        How: Pass each invalid slug; assert RepoDiscoveryError is raised.
        Why: All invalid slugs must be rejected before reaching subprocess calls.
        """
        with pytest.raises(RepoDiscoveryError):
            _validate_repo_slug(slug)

    def test_validate_repo_slug_error_message_contains_slug(self) -> None:
        """Error message includes the rejected slug for debuggability.

        Tests: _validate_repo_slug error context
        How: Catch RepoDiscoveryError for invalid slug; check slug in message.
        Why: Operators debugging an invalid GITHUB_REPO value need to see what was rejected.
        """
        bad_slug = "no-slash-at-all"
        with pytest.raises(RepoDiscoveryError) as exc_info:
            _validate_repo_slug(bad_slug)
        assert bad_slug in str(exc_info.value)


# ---------------------------------------------------------------------------
# _discover_via_env
# ---------------------------------------------------------------------------


class TestDiscoverViaEnv:
    """_discover_via_env reads GITHUB_REPO from the environment.

    Priority 1 in the chain — must be tested in complete isolation from
    the filesystem and subprocess layer.
    """

    def test_discover_via_env_returns_slug_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns validated slug when GITHUB_REPO is set to a valid value.

        Tests: _discover_via_env happy path
        How: monkeypatch GITHUB_REPO; call function; assert return value.
        Why: Env var override must take precedence without calling subprocess.
        """
        monkeypatch.setenv("GITHUB_REPO", "my-org/my-repo")
        result = _discover_via_env()
        assert result == "my-org/my-repo"

    def test_discover_via_env_returns_none_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when GITHUB_REPO is absent from the environment.

        Tests: _discover_via_env when env var is missing
        How: Remove GITHUB_REPO from env; assert None is returned.
        Why: Absent env var must not block discovery fallback to gh CLI.
        """
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        result = _discover_via_env()
        assert result is None

    def test_discover_via_env_returns_none_for_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when GITHUB_REPO is set to an empty string.

        Tests: _discover_via_env empty string edge case
        How: Set GITHUB_REPO=""; assert None returned.
        Why: An empty env var is semantically equivalent to not set.
        """
        monkeypatch.setenv("GITHUB_REPO", "")
        result = _discover_via_env()
        assert result is None

    def test_discover_via_env_returns_none_for_whitespace_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when GITHUB_REPO contains only whitespace.

        Tests: _discover_via_env whitespace stripping
        How: Set GITHUB_REPO="   "; assert None returned.
        Why: Whitespace-only values must be treated as absent.
        """
        monkeypatch.setenv("GITHUB_REPO", "   ")
        result = _discover_via_env()
        assert result is None

    def test_discover_via_env_raises_for_invalid_slug_in_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises RepoDiscoveryError when GITHUB_REPO contains an invalid slug.

        Tests: _discover_via_env validation of env var content
        How: Set GITHUB_REPO to malformed value; assert RepoDiscoveryError raised.
        Why: Invalid env var values should fail fast with a clear error rather than
             silently falling through to other discovery methods.
        """
        monkeypatch.setenv("GITHUB_REPO", "not-a-valid-slug")
        with pytest.raises(RepoDiscoveryError):
            _discover_via_env()

    def test_discover_via_env_strips_surrounding_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace around a valid slug is stripped before validation.

        Tests: _discover_via_env .strip() behaviour
        How: Set GITHUB_REPO with leading/trailing spaces; assert slug returned.
        Why: Users may inadvertently add spaces in shell config.
        """
        monkeypatch.setenv("GITHUB_REPO", "  owner/repo  ")
        result = _discover_via_env()
        assert result == "owner/repo"


# ---------------------------------------------------------------------------
# _discover_via_git
# ---------------------------------------------------------------------------


def _make_mock_repo(mocker: MockerFixture, url: str) -> object:
    """Return a mock git.Repo whose origin remote URL is set to *url*."""
    mock_remote = mocker.Mock()
    mock_remote.url = url
    mock_repo = mocker.Mock()
    mock_repo.remote.return_value = mock_remote
    return mock_repo


class TestDiscoverViaGit:
    """_discover_via_git parses the git remote origin URL via GitPython.

    Priority 2 in the chain. All git.Repo calls are mocked — tests must
    not depend on the actual git repository state.
    """

    def test_discover_via_git_returns_none_when_not_a_git_repo(self, mocker: MockerFixture) -> None:
        """Returns None when git.Repo raises InvalidGitRepositoryError.

        Tests: _discover_via_git absent git repository
        How: Mock git.Repo to raise InvalidGitRepositoryError; assert None returned.
        Why: Environments not inside a git repository must not error.
        """
        import git as gitlib

        mocker.patch("backlog_core.models.git.Repo", side_effect=gitlib.InvalidGitRepositoryError("not a repo"))

        result = _discover_via_git()

        assert result is None

    def test_discover_via_git_returns_none_when_no_origin_remote(self, mocker: MockerFixture) -> None:
        """Returns None when the repo has no origin remote (ValueError from GitPython).

        Tests: _discover_via_git no origin remote
        How: Mock git.Repo.remote() to raise ValueError; assert None returned.
        Why: Repos without an origin remote must fall through to error.
        """
        mock_repo = mocker.Mock()
        mock_repo.remote.side_effect = ValueError("Remote named 'origin' didn't exist")
        mocker.patch("backlog_core.models.git.Repo", return_value=mock_repo)

        result = _discover_via_git()

        assert result is None

    def test_discover_via_git_uses_repo_root_not_process_cwd(
        self, tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """git.Repo is opened at ``_REPO_ROOT`` so MCP cwd outside the project still works.

        Tests: _discover_via_git passes resolved project root into GitPython
        How: Point ``_REPO_ROOT`` at tmp_path; mock ``git.Repo``; assert call args.
        Why: stdio MCP servers often have cwd in plugin cache or ``/``, not the repo.
        """
        project_root = tmp_path / "my-app"
        project_root.mkdir()
        existing = _bc_models._config
        monkeypatch.setattr(
            _bc_models,
            "_config",
            BacklogConfig(
                repo_root=project_root,
                backlog_dir=existing.backlog_dir if existing is not None else project_root / "backlog",
                default_repo=existing.default_repo if existing is not None else "",
            ),
        )
        mock_repo_ctor = mocker.patch(
            "backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, "git@github.com:acme/widget.git")
        )

        result = _discover_via_git()

        assert result == "acme/widget"
        mock_repo_ctor.assert_called_once_with(project_root, search_parent_directories=True)

    @pytest.mark.parametrize(
        ("url", "expected_slug"),
        [
            ("git@github.com:owner/repo.git", "owner/repo"),
            ("git@github.com:my-org/my-repo.git", "my-org/my-repo"),
            ("git@github.com:Owner123/Repo.Name.git", "Owner123/Repo.Name"),
        ],
    )
    def test_discover_via_git_parses_ssh_scp_urls(self, url: str, expected_slug: str, mocker: MockerFixture) -> None:
        """SSH SCP remote URLs are parsed to extract owner/repo.

        Tests: _discover_via_git SSH SCP URL parsing
        How: Mock git.Repo to return repo with SSH SCP URL; assert expected slug.
        Why: SSH SCP remotes (git@host:owner/repo.git) are the most common developer format.
        """
        mocker.patch("backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, url))

        result = _discover_via_git()

        assert result == expected_slug

    @pytest.mark.parametrize(
        ("url", "expected_slug"),
        [
            ("https://github.com/owner/repo.git", "owner/repo"),
            ("https://github.com/my-org/my-repo.git", "my-org/my-repo"),
            ("https://github.com/owner/repo", "owner/repo"),
            ("http://127.0.0.1:9876/owner/repo.git", "owner/repo"),
        ],
    )
    def test_discover_via_git_parses_https_and_proxy_urls(
        self, url: str, expected_slug: str, mocker: MockerFixture
    ) -> None:
        """HTTPS and proxy remote URLs are parsed to extract owner/repo.

        Tests: _discover_via_git HTTPS/proxy URL parsing
        How: Mock git.Repo to return repo with HTTPS/proxy URL; assert expected slug.
        Why: Claude Code sessions use proxy URLs (127.0.0.1) — these must parse.
        """
        mocker.patch("backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, url))

        result = _discover_via_git()

        assert result == expected_slug

    @pytest.mark.parametrize(
        ("url", "expected_slug"),
        [
            ("ssh://git@github.com/owner/repo.git", "owner/repo"),
            ("ssh://git@github.com/my-org/my-repo.git", "my-org/my-repo"),
        ],
    )
    def test_discover_via_git_parses_ssh_protocol_urls(
        self, url: str, expected_slug: str, mocker: MockerFixture
    ) -> None:
        """SSH protocol remote URLs (ssh://) are parsed to extract owner/repo.

        Tests: _discover_via_git SSH protocol URL parsing
        How: Mock git.Repo to return repo with ssh:// URL; assert expected slug.
        Why: Some CI environments configure remotes using the ssh:// scheme.
        """
        mocker.patch("backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, url))

        result = _discover_via_git()

        assert result == expected_slug

    @pytest.mark.parametrize(
        ("url", "expected_slug"),
        [
            ("http://local_proxy@127.0.0.1:46723/git/Jamie-BitFlight/claude_skills", "Jamie-BitFlight/claude_skills"),
            ("http://local_proxy@127.0.0.1:12345/git/owner/repo.git", "owner/repo"),
            ("http://local_proxy@127.0.0.1:9999/git/my-org/my-repo", "my-org/my-repo"),
            ("http://local_proxy@127.0.0.1:1/git/Owner123/Repo.Name.git", "Owner123/Repo.Name"),
        ],
    )
    def test_discover_via_git_parses_proxy_urls(self, url: str, expected_slug: str, mocker: MockerFixture) -> None:
        """Claude Code sandbox proxy remote URLs are parsed to extract owner/repo.

        Tests: _discover_via_git proxy URL parsing
        How: Mock git.Repo to return repo with proxy URL; assert expected slug.
        Why: Claude Code sessions use http://local_proxy@127.0.0.1:{port}/git/{owner}/{repo}
             format — these must parse so discover_repo() works in sandbox environments.
        """
        mocker.patch("backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, url))

        result = _discover_via_git()

        assert result == expected_slug

    def test_discover_via_git_returns_none_for_unparseable_url(self, mocker: MockerFixture) -> None:
        """Returns None when the remote URL does not match any known pattern.

        Tests: _discover_via_git unrecognised URL format
        How: Mock git.Repo to return repo with an unrecognisable URL.
        Why: Must not propagate garbage values when URL format is unknown.
        """
        mocker.patch(
            "backlog_core.models.git.Repo", return_value=_make_mock_repo(mocker, "svn+ssh://svn.example.com/project")
        )

        result = _discover_via_git()

        assert result is None


# ---------------------------------------------------------------------------
# discover_repo — priority chain integration
# ---------------------------------------------------------------------------


class TestDiscoverRepoPriorityChain:
    """discover_repo() respects the documented priority chain.

    Tests: GITHUB_REPO env var → GitPython remote URL → RepoDiscoveryError
    Each test asserts one step of the chain by mocking the lower-priority methods.
    """

    def test_env_var_takes_precedence_over_git(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """GITHUB_REPO env var returns immediately without calling GitPython.

        Tests: discover_repo priority 1 (env var)
        How: Set GITHUB_REPO; mock _discover_via_git to assert it is never called.
        Why: Env var is the explicit override — it must short-circuit the chain.
        """
        monkeypatch.setenv("GITHUB_REPO", "env-owner/env-repo")
        mock_git = mocker.patch("backlog_core.models._discover_via_git")

        result = discover_repo()

        assert result == "env-owner/env-repo"
        mock_git.assert_not_called()

    def test_git_remote_used_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """GitPython remote parsing is called when GITHUB_REPO is absent.

        Tests: discover_repo priority 2 (GitPython remote)
        How: Remove GITHUB_REPO; mock _discover_via_git to return a valid slug.
        Why: GitPython is the sole automated method after the env var.
        """
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        mocker.patch("backlog_core.models._discover_via_git", return_value="git-owner/git-repo")

        result = discover_repo()

        assert result == "git-owner/git-repo"

    def test_raises_repo_discovery_error_when_all_methods_fail(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """RepoDiscoveryError is raised when both methods fail.

        Tests: discover_repo exhaustion path
        How: Remove GITHUB_REPO; mock _discover_via_git to return None;
             assert RepoDiscoveryError raised.
        Why: No fallback should exist when all discovery methods are exhausted.
        """
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        mocker.patch("backlog_core.models._discover_via_git", return_value=None)

        with pytest.raises(RepoDiscoveryError):
            discover_repo()

    def test_discovery_error_lists_both_methods_tried(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """RepoDiscoveryError.methods_tried contains both method names.

        Tests: discover_repo error context completeness
        How: Force all methods to fail; assert methods_tried length is 2.
        Why: Operators need the full list to diagnose which step to fix.
        """
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        mocker.patch("backlog_core.models._discover_via_git", return_value=None)

        with pytest.raises(RepoDiscoveryError) as exc_info:
            discover_repo()

        assert len(exc_info.value.methods_tried) == 2

    def test_git_not_called_when_env_var_is_valid(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """When env var succeeds, GitPython is never invoked.

        Tests: discover_repo short-circuit on env var success
        How: Set valid GITHUB_REPO; spy on git.Repo; assert not called.
        Why: Env var should avoid all git I/O overhead.
        """
        monkeypatch.setenv("GITHUB_REPO", "some-org/some-repo")
        mock_git_repo = mocker.patch("backlog_core.models.git.Repo")

        discover_repo()

        mock_git_repo.assert_not_called()


# ---------------------------------------------------------------------------
# discover_repo — lru_cache behaviour
# ---------------------------------------------------------------------------


class TestDiscoverRepoCache:
    """discover_repo() caches its result and supports cache_clear().

    lru_cache correctness is critical: a stale cache in tests or in the MCP
    server's init() path would cause all subsequent operations to use the
    wrong repo slug.
    """

    def test_discover_repo_called_twice_returns_same_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Two calls to discover_repo() return identical values.

        Tests: lru_cache result reuse
        How: Set GITHUB_REPO; call twice; assert both return equal values.
        Why: The cache must not produce different results between calls.
        """
        monkeypatch.setenv("GITHUB_REPO", "cached-owner/cached-repo")
        first = discover_repo()
        second = discover_repo()
        assert first == second

    def test_discover_repo_git_called_once_for_multiple_calls(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """GitPython is called at most once regardless of how many times
        discover_repo() is invoked.

        Tests: lru_cache git I/O deduplication
        How: Remove GITHUB_REPO; mock _discover_via_git to return a slug;
             call discover_repo() twice; assert _discover_via_git called once.
        Why: The performance contract of lru_cache(maxsize=1) — one git call
             per process lifetime.
        """
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        mock_git = mocker.patch("backlog_core.models._discover_via_git", return_value="once/called")

        discover_repo()
        discover_repo()

        mock_git.assert_called_once()

    def test_cache_clear_allows_re_discovery_with_new_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After cache_clear(), a new GITHUB_REPO value is picked up.

        Tests: discover_repo.cache_clear() contract
        How: Set GITHUB_REPO to "first/repo"; call discover_repo(); clear cache;
             change GITHUB_REPO to "second/repo"; call again; assert new value.
        Why: init() calls cache_clear() when re-initialising — this must work.
        """
        monkeypatch.setenv("GITHUB_REPO", "first/repo")
        first = discover_repo()
        assert first == "first/repo"

        discover_repo.cache_clear()
        monkeypatch.setenv("GITHUB_REPO", "second/repo")
        second = discover_repo()
        assert second == "second/repo"

    def test_cache_clear_method_exists_on_discover_repo(self) -> None:
        """discover_repo.cache_clear is callable.

        Tests: lru_cache API presence
        How: Assert callable(discover_repo.cache_clear).
        Why: Tests and init() depend on this attribute — must not be removed.
        """
        assert callable(discover_repo.cache_clear)

    def test_cache_info_reports_maxsize_one(self) -> None:
        """discover_repo.cache_info() reports maxsize=1.

        Tests: lru_cache maxsize configuration
        How: Inspect cache_info().maxsize.
        Why: maxsize=1 is the documented contract (one result cached per process).
        """
        info = discover_repo.cache_info()
        assert info.maxsize == 1
