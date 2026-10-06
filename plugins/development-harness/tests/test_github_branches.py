"""Tests for backlog_core/github_branches.py.

Covers: create_integration_branch, get_integration_branch_status,
merge_integration_branch, delete_integration_branch, list_integration_branches,
and the private helper _branch_name.

All PyGithub boundary objects are mocked — no live API calls.
Mock boundary: ``backlog_core.github_branches.get_github``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.github_branches import (
    BRANCH_PREFIX,
    _branch_name,
    _validate_milestone_number,
    _validate_slug,
    create_integration_branch,
    delete_integration_branch,
    get_integration_branch_status,
    list_integration_branches,
    merge_integration_branch,
)
from backlog_core.models import BacklogError, BranchConflictError, BranchInfo, MergeResult, Output
from github import GithubException

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Constants used across tests
# ---------------------------------------------------------------------------

_MILESTONE = 3
_SLUG = "v1-1-workflow"
_BRANCH = "milestone/3-v1-1-workflow"
_BASE_SHA = "abc123def456abc123def456abc123def456abc1"
_MERGE_SHA = "deadbeef1234deadbeef1234deadbeef12345678"
_COMMIT_DATE = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
_COMMIT_DATE_STR = "2026-03-15T12:00:00Z"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_branch(
    mocker: MockerFixture, *, name: str = _BRANCH, sha: str = _BASE_SHA, date: datetime = _COMMIT_DATE
) -> Any:
    """Return a mock PyGithub Branch with commit and author date configured.

    Args:
        mocker: pytest-mock fixture.
        name: Branch name string.
        sha: Commit SHA string.
        date: Author date datetime (tz-aware).

    Returns:
        Mock mimicking a PyGithub Branch object.
    """
    branch = mocker.Mock()
    branch.name = name
    branch.commit.sha = sha
    branch.commit.commit.author.date = date
    return branch


def _make_github_exception(status: int, data: str = "error") -> GithubException:
    """Return a GithubException with the given HTTP status code.

    Args:
        status: HTTP status integer (e.g. 404, 409, 422, 500).
        data: Optional error message string.

    Returns:
        GithubException instance.
    """
    return GithubException(status, data, None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> Any:
    """Patch get_github() and return a MagicMock Repository.

    Tests:  All 5 public functions in github_branches.py
    How:    Patches ``backlog_core.github_branches.get_github`` so that
            ``_get_repo()`` returns a controlled MagicMock Repository without
            making real network calls.
    Why:    Isolates unit tests from the GitHub API; ensures tests are
            deterministic and require no credentials.

    Returns:
        MagicMock configured as a PyGithub Repository.
    """
    repo_mock = mocker.MagicMock()
    mocker.patch("backlog_core.github_branches.get_github", return_value=repo_mock)
    return repo_mock


# ---------------------------------------------------------------------------
# _branch_name helper
# ---------------------------------------------------------------------------


class TestBranchName:
    """_branch_name builds canonical milestone branch names."""

    def test_branch_name_format(self) -> None:
        """Test canonical branch name format milestone/{N}-{slug}.

        Tests:  _branch_name helper
        How:    Call with known inputs; assert exact output string.
        Why:    Branch naming is a contract; tests lock it against drift.
        """
        # Arrange / Act
        result = _branch_name(3, "v1.1-milestone-workflow")
        # Assert
        assert result == "milestone/3-v1.1-milestone-workflow"


# ---------------------------------------------------------------------------
# create_integration_branch
# ---------------------------------------------------------------------------


class TestCreateIntegrationBranch:
    """create_integration_branch creates a branch from a base SHA."""

    def test_create_branch_happy_path(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test successful branch creation returns correct BranchInfo.

        Tests:  create_integration_branch — happy path
        How:    Mock get_branch (base) and create_git_ref; assert returned
                BranchInfo fields name, sha, age_days=0.
        Why:    AC4 requires happy-path coverage for every public function.
        """
        # Arrange
        base_branch_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        new_branch_mock = _make_mock_branch(mocker, name=_BRANCH, sha=_BASE_SHA)
        mock_repo.get_branch.side_effect = [base_branch_mock, new_branch_mock]
        mock_repo.create_git_ref.return_value = mocker.MagicMock()

        # Act
        result: BranchInfo = create_integration_branch(_MILESTONE, _SLUG)

        # Assert
        assert result["name"] == _BRANCH
        assert result["sha"] == _BASE_SHA
        assert result["age_days"] == pytest.approx((datetime.now(tz=UTC) - _COMMIT_DATE).days, abs=1)

    def test_create_branch_calls_create_git_ref_with_correct_args(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test create_git_ref is called with the correct ref path and SHA.

        Tests:  create_integration_branch — PyGithub API call
        How:    Capture create_git_ref call_args after creation.
        Why:    Verifies the function constructs refs/heads/{name} correctly.
        """
        # Arrange
        base_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        new_mock = _make_mock_branch(mocker, name=_BRANCH, sha=_BASE_SHA)
        mock_repo.get_branch.side_effect = [base_mock, new_mock]
        mock_repo.create_git_ref.return_value = mocker.MagicMock()

        # Act
        create_integration_branch(_MILESTONE, _SLUG)

        # Assert
        mock_repo.create_git_ref.assert_called_once_with(ref=f"refs/heads/{_BRANCH}", sha=_BASE_SHA)

    def test_create_branch_already_exists_raises_backlog_error(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test 422 from create_git_ref raises BacklogError.

        Tests:  create_integration_branch — 422 error path
        How:    Mock create_git_ref to raise GithubException(422).
        Why:    AC6 requires BranchConflictError/BacklogError on conflict scenarios.
        """
        # Arrange
        base_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        mock_repo.get_branch.return_value = base_mock
        mock_repo.create_git_ref.side_effect = _make_github_exception(422)

        # Act / Assert
        with pytest.raises(BacklogError, match="already exists"):
            create_integration_branch(_MILESTONE, _SLUG)

    def test_create_branch_base_not_found_raises_backlog_error(self, mock_repo: Any) -> None:
        """Test 404 on base branch lookup raises BacklogError.

        Tests:  create_integration_branch — 404 base branch error path
        How:    Mock get_branch to raise GithubException(404).
        Why:    Prevents cryptic errors when caller supplies wrong base branch.
        """
        # Arrange
        mock_repo.get_branch.side_effect = _make_github_exception(404)

        # Act / Assert
        with pytest.raises(BacklogError, match="not found"):
            create_integration_branch(_MILESTONE, _SLUG)

    def test_create_branch_unexpected_exception_propagates(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test non-422/non-404 GithubException propagates uncaught.

        Tests:  create_integration_branch — 500 error path
        How:    Mock create_git_ref to raise GithubException(500).
        Why:    Unexpected API errors must surface to callers.
        """
        # Arrange
        base_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        mock_repo.get_branch.return_value = base_mock
        mock_repo.create_git_ref.side_effect = _make_github_exception(500)

        # Act / Assert
        with pytest.raises(GithubException) as exc_info:
            create_integration_branch(_MILESTONE, _SLUG)
        assert exc_info.value.status == 500

    def test_create_branch_records_output_info(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test create_integration_branch records info message when output provided.

        Tests:  create_integration_branch — output parameter
        How:    Pass Output instance; assert messages populated.
        Why:    Output integration ensures CLI wrapper can display status.
        """
        # Arrange
        base_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        new_mock = _make_mock_branch(mocker, name=_BRANCH, sha=_BASE_SHA)
        mock_repo.get_branch.side_effect = [base_mock, new_mock]
        mock_repo.create_git_ref.return_value = mocker.MagicMock()
        output = Output()

        # Act
        create_integration_branch(_MILESTONE, _SLUG, output=output)

        # Assert
        assert len(output.messages) > 0


# ---------------------------------------------------------------------------
# get_integration_branch_status
# ---------------------------------------------------------------------------


class TestGetIntegrationBranchStatus:
    """get_integration_branch_status returns BranchInfo or None."""

    def test_get_status_branch_exists(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test branch exists returns populated BranchInfo.

        Tests:  get_integration_branch_status — happy path
        How:    Mock get_branch to return branch mock; assert all fields present.
        Why:    AC4 happy-path coverage for every public function.
        """
        # Arrange
        branch_mock = _make_mock_branch(mocker)
        mock_repo.get_branch.return_value = branch_mock

        # Act
        result = get_integration_branch_status(_BRANCH)

        # Assert
        assert result is not None
        assert result["name"] == _BRANCH
        assert result["sha"] == _BASE_SHA
        assert result["last_commit_date"] == _COMMIT_DATE_STR
        assert isinstance(result["age_days"], int)

    def test_get_status_branch_not_found_returns_none(self, mock_repo: Any) -> None:
        """Test 404 returns None without raising.

        Tests:  get_integration_branch_status — 404 not-found path
        How:    Mock get_branch to raise GithubException(404).
        Why:    Function contract: non-raising on not-found, returns None.
        """
        # Arrange
        mock_repo.get_branch.side_effect = _make_github_exception(404)

        # Act
        result = get_integration_branch_status(_BRANCH)

        # Assert
        assert result is None

    def test_get_status_unexpected_error_propagates(self, mock_repo: Any) -> None:
        """Test non-404 GithubException propagates uncaught.

        Tests:  get_integration_branch_status — 500 error path
        How:    Mock get_branch to raise GithubException(500).
        Why:    Non-404 errors indicate real API failure and must surface.
        """
        # Arrange
        mock_repo.get_branch.side_effect = _make_github_exception(500)

        # Act / Assert
        with pytest.raises(GithubException) as exc_info:
            get_integration_branch_status(_BRANCH)
        assert exc_info.value.status == 500

    def test_get_status_records_info_when_output_provided(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test output.info called when branch found and output provided.

        Tests:  get_integration_branch_status — output integration
        How:    Pass Output; assert messages populated after successful call.
        Why:    Output integration must work for CLI and MCP consumers.
        """
        # Arrange
        branch_mock = _make_mock_branch(mocker)
        mock_repo.get_branch.return_value = branch_mock
        output = Output()

        # Act
        get_integration_branch_status(_BRANCH, output=output)

        # Assert
        assert len(output.messages) > 0

    def test_get_status_404_records_info_when_output_provided(self, mock_repo: Any) -> None:
        """Test output.info called when branch not found and output provided.

        Tests:  get_integration_branch_status — 404 output integration
        How:    Mock 404; pass Output; assert messages not empty.
        Why:    Callers rely on output messages to communicate not-found status.
        """
        # Arrange
        mock_repo.get_branch.side_effect = _make_github_exception(404)
        output = Output()

        # Act
        get_integration_branch_status(_BRANCH, output=output)

        # Assert
        assert len(output.messages) > 0


# ---------------------------------------------------------------------------
# merge_integration_branch
# ---------------------------------------------------------------------------


class TestMergeIntegrationBranch:
    """merge_integration_branch merges head into base and handles conflicts."""

    def test_merge_happy_path_returns_merge_result(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test successful merge returns MergeResult with sha and message.

        Tests:  merge_integration_branch — happy path
        How:    Mock repo.merge to return a commit-like object with .sha.
        Why:    AC4 happy-path coverage; verifies MergeResult fields.
        """
        # Arrange
        merge_commit = mocker.MagicMock()
        merge_commit.sha = _MERGE_SHA
        mock_repo.merge.return_value = merge_commit
        msg = "Merge milestone/3 into main"

        # Act
        result: MergeResult = merge_integration_branch(_BRANCH, "main", msg)

        # Assert
        assert result["sha"] == _MERGE_SHA
        assert result["message"] == msg

    def test_merge_calls_repo_merge_with_correct_args(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test repo.merge() is called with base, head, and commit_message.

        Tests:  merge_integration_branch — PyGithub API call
        How:    Assert call_args on mock_repo.merge after invocation.
        Why:    PyGithub merge() parameter order matters (base first, then head).
        """
        # Arrange
        merge_commit = mocker.MagicMock()
        merge_commit.sha = _MERGE_SHA
        mock_repo.merge.return_value = merge_commit
        msg = "chore: merge integration branch"

        # Act
        merge_integration_branch(_BRANCH, "main", msg)

        # Assert
        mock_repo.merge.assert_called_once_with(base="main", head=_BRANCH, commit_message=msg)

    def test_merge_conflict_raises_branch_conflict_error(self, mock_repo: Any) -> None:
        """Test 409 conflict raises BranchConflictError with branch attributes.

        Tests:  merge_integration_branch — 409 conflict path
        How:    Mock repo.merge to raise GithubException(409); check raised exception.
        Why:    AC6 requires BranchConflictError with head_branch, base_branch attributes.
        """
        # Arrange
        mock_repo.merge.side_effect = _make_github_exception(409)

        # Act / Assert
        with pytest.raises(BranchConflictError) as exc_info:
            merge_integration_branch(_BRANCH, "main", "msg")

        err = exc_info.value
        assert err.head_branch == _BRANCH
        assert err.base_branch == "main"
        assert isinstance(err.conflict_files, list)

    def test_merge_conflict_error_is_backlog_error_subclass(self, mock_repo: Any) -> None:
        """Test BranchConflictError is catchable as BacklogError.

        Tests:  merge_integration_branch — exception hierarchy
        How:    Verify BranchConflictError is also caught by BacklogError handler.
        Why:    Callers using broad BacklogError catch must also capture conflicts.
        """
        # Arrange
        mock_repo.merge.side_effect = _make_github_exception(409)

        # Act / Assert
        with pytest.raises(BacklogError):
            merge_integration_branch(_BRANCH, "main", "msg")

    def test_merge_already_up_to_date_returns_base_sha(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test None merge result (HTTP 204, already up-to-date) returns base HEAD SHA.

        Tests:  merge_integration_branch — no-op merge (204) path
        How:    Mock repo.merge to return None; mock get_branch for base HEAD.
        Why:    PyGithub returns None for already-merged branches; function must handle.
        """
        # Arrange
        mock_repo.merge.return_value = None
        base_mock = _make_mock_branch(mocker, name="main", sha=_BASE_SHA)
        mock_repo.get_branch.return_value = base_mock
        msg = "already merged"

        # Act
        result = merge_integration_branch(_BRANCH, "main", msg)

        # Assert
        assert result["sha"] == _BASE_SHA
        assert result["message"] == msg

    def test_merge_unexpected_error_propagates(self, mock_repo: Any) -> None:
        """Test non-409 GithubException propagates uncaught.

        Tests:  merge_integration_branch — 500 error path
        How:    Mock repo.merge to raise GithubException(500).
        Why:    Unexpected API errors must surface to callers.
        """
        # Arrange
        mock_repo.merge.side_effect = _make_github_exception(500)

        # Act / Assert
        with pytest.raises(GithubException) as exc_info:
            merge_integration_branch(_BRANCH, "main", "msg")
        assert exc_info.value.status == 500

    def test_merge_records_output_on_conflict(self, mock_repo: Any) -> None:
        """Test output.warn called when merge conflict occurs.

        Tests:  merge_integration_branch — output on conflict
        How:    Mock 409; pass Output; assert warnings populated before exception.
        Why:    CLI wrapper needs warning messages even when exception raised.
        """
        # Arrange
        mock_repo.merge.side_effect = _make_github_exception(409)
        output = Output()

        # Act / Assert
        with pytest.raises(BranchConflictError):
            merge_integration_branch(_BRANCH, "main", "msg", output=output)

        assert len(output.warnings) > 0


# ---------------------------------------------------------------------------
# delete_integration_branch
# ---------------------------------------------------------------------------


class TestDeleteIntegrationBranch:
    """delete_integration_branch is idempotent and returns bool."""

    def test_delete_branch_success_returns_true(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test successful delete returns True.

        Tests:  delete_integration_branch — happy path
        How:    Mock get_git_ref and ref.delete() to succeed.
        Why:    AC4 happy-path coverage; return value contract.
        """
        # Arrange
        ref_mock = mocker.MagicMock()
        mock_repo.get_git_ref.return_value = ref_mock

        # Act
        result = delete_integration_branch(_BRANCH)

        # Assert
        assert result is True
        ref_mock.delete.assert_called_once()

    def test_delete_branch_404_returns_true_idempotent(self, mock_repo: Any) -> None:
        """Test 404 on get_git_ref returns True (idempotent delete).

        Tests:  delete_integration_branch — 404 already-deleted path
        How:    Mock get_git_ref to raise GithubException(404).
        Why:    Idempotency is a documented contract; callers must not see error.
        """
        # Arrange
        mock_repo.get_git_ref.side_effect = _make_github_exception(404)

        # Act
        result = delete_integration_branch(_BRANCH)

        # Assert
        assert result is True

    def test_delete_branch_unexpected_error_returns_false(self, mock_repo: Any) -> None:
        """Test unexpected GithubException returns False without re-raising.

        Tests:  delete_integration_branch — unexpected error path
        How:    Mock get_git_ref to raise GithubException(500).
        Why:    Delete is best-effort; callers must not crash on unexpected failure.
        """
        # Arrange
        mock_repo.get_git_ref.side_effect = _make_github_exception(500)

        # Act
        result = delete_integration_branch(_BRANCH)

        # Assert
        assert result is False

    def test_delete_branch_unexpected_error_calls_output_warn(self, mock_repo: Any) -> None:
        """Test output.warn called when unexpected error occurs.

        Tests:  delete_integration_branch — output.warn on unexpected error
        How:    Mock 500; pass Output; assert warnings populated.
        Why:    Best-effort delete must communicate failure via output, not exception.
        """
        # Arrange
        mock_repo.get_git_ref.side_effect = _make_github_exception(500)
        output = Output()

        # Act
        result = delete_integration_branch(_BRANCH, output=output)

        # Assert
        assert result is False
        assert len(output.warnings) > 0

    def test_delete_calls_get_git_ref_with_heads_prefix(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test get_git_ref called with 'heads/{branch_name}' (no 'refs/' prefix).

        Tests:  delete_integration_branch — PyGithub ref path construction
        How:    Assert get_git_ref call arg after deletion.
        Why:    PyGithub get_git_ref for deletion uses 'heads/' not 'refs/heads/'.
        """
        # Arrange
        ref_mock = mocker.MagicMock()
        mock_repo.get_git_ref.return_value = ref_mock

        # Act
        delete_integration_branch(_BRANCH)

        # Assert
        mock_repo.get_git_ref.assert_called_once_with(f"heads/{_BRANCH}")


# ---------------------------------------------------------------------------
# list_integration_branches
# ---------------------------------------------------------------------------


class TestListIntegrationBranches:
    """list_integration_branches filters, sorts, and returns BranchInfo list."""

    def test_list_returns_matching_branches(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test branches matching milestone/ prefix are returned.

        Tests:  list_integration_branches — happy path with matches
        How:    Mock get_branches with two milestone/ branches; assert both returned.
        Why:    AC4 happy-path coverage; filter logic must include prefix matches.
        """
        # Arrange
        older = _make_mock_branch(mocker, name="milestone/2-old", sha="sha2", date=datetime(2026, 1, 1, tzinfo=UTC))
        newer = _make_mock_branch(mocker, name="milestone/3-new", sha="sha3", date=datetime(2026, 3, 1, tzinfo=UTC))
        mock_repo.get_branches.return_value = [older, newer]

        # Act
        results = list_integration_branches()

        # Assert
        assert len(results) == 2
        assert all(r["name"].startswith(BRANCH_PREFIX) for r in results)

    def test_list_sorted_most_recent_first(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test branches sorted by last_commit_date descending (most recent first).

        Tests:  list_integration_branches — sort order
        How:    Mock two branches with known dates; assert order in returned list.
        Why:    Architecture spec requires most-recent-first ordering.
        """
        # Arrange
        older = _make_mock_branch(mocker, name="milestone/1-alpha", sha="sha1", date=datetime(2026, 1, 1, tzinfo=UTC))
        newer = _make_mock_branch(mocker, name="milestone/2-beta", sha="sha2", date=datetime(2026, 3, 1, tzinfo=UTC))
        mock_repo.get_branches.return_value = [older, newer]

        # Act
        results = list_integration_branches()

        # Assert
        assert results[0]["name"] == "milestone/2-beta"
        assert results[1]["name"] == "milestone/1-alpha"

    def test_list_excludes_non_matching_branches(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test branches not matching milestone/ prefix are excluded.

        Tests:  list_integration_branches — filter excludes non-prefix branches
        How:    Mix milestone/ and feature/ branches; assert only milestone/ returned.
        Why:    Filter must not include unrelated branches.
        """
        # Arrange
        milestone_branch = _make_mock_branch(mocker, name="milestone/3-work", sha="sha3")
        feature_branch = _make_mock_branch(mocker, name="feature/something", sha="sha4")
        main_branch = _make_mock_branch(mocker, name="main", sha="sha5")
        mock_repo.get_branches.return_value = [milestone_branch, feature_branch, main_branch]

        # Act
        results = list_integration_branches()

        # Assert
        assert len(results) == 1
        assert results[0]["name"] == "milestone/3-work"

    def test_list_no_matching_branches_returns_empty_list(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test no milestone/ branches returns empty list.

        Tests:  list_integration_branches — empty result path
        How:    Mock get_branches with non-matching branches only.
        Why:    Empty result is a valid state; caller must handle gracefully.
        """
        # Arrange
        feature_branch = _make_mock_branch(mocker, name="feature/something", sha="sha1")
        mock_repo.get_branches.return_value = [feature_branch]

        # Act
        results = list_integration_branches()

        # Assert
        assert results == []

    def test_list_github_error_returns_empty_list(self, mock_repo: Any) -> None:
        """Test GithubException from get_branches returns empty list without raising.

        Tests:  list_integration_branches — GitHub API error path
        How:    Mock get_branches to raise GithubException(500).
        Why:    list is soft-fail by design; callers must receive empty list.
        """
        # Arrange
        mock_repo.get_branches.side_effect = _make_github_exception(500)

        # Act
        results = list_integration_branches()

        # Assert
        assert results == []

    def test_list_github_error_calls_output_warn(self, mock_repo: Any) -> None:
        """Test output.warn called when GithubException occurs during listing.

        Tests:  list_integration_branches — output.warn on error
        How:    Mock 500; pass Output; assert warnings populated.
        Why:    Soft-fail must communicate error via output for observability.
        """
        # Arrange
        mock_repo.get_branches.side_effect = _make_github_exception(500)
        output = Output()

        # Act
        results = list_integration_branches(output=output)

        # Assert
        assert results == []
        assert len(output.warnings) > 0


# ---------------------------------------------------------------------------
# BranchConflictError attributes
# ---------------------------------------------------------------------------


class TestBranchConflictError:
    """BranchConflictError stores branch names and conflict_files."""

    def test_branch_conflict_error_head_branch_attribute(self) -> None:
        """Test head_branch attribute is stored on BranchConflictError.

        Tests:  BranchConflictError — head_branch attribute
        How:    Construct directly; assert attribute value.
        Why:    AC6 requires head_branch, base_branch, conflict_files assertions.
        """
        err = BranchConflictError(head_branch="feature/x", base_branch="main")
        assert err.head_branch == "feature/x"

    def test_branch_conflict_error_base_branch_attribute(self) -> None:
        """Test base_branch attribute is stored on BranchConflictError.

        Tests:  BranchConflictError — base_branch attribute
        How:    Construct directly; assert attribute value.
        Why:    AC6 requires both branch attributes accessible.
        """
        err = BranchConflictError(head_branch="feature/x", base_branch="main")
        assert err.base_branch == "main"

    def test_branch_conflict_error_conflict_files_defaults_to_empty_list(self) -> None:
        """Test conflict_files defaults to empty list when not provided.

        Tests:  BranchConflictError — conflict_files default
        How:    Construct without conflict_files; assert [] not None.
        Why:    AC6 requires conflict_files attribute; None would break isinstance checks.
        """
        err = BranchConflictError(head_branch="a", base_branch="b")
        assert err.conflict_files == []

    def test_branch_conflict_error_stores_conflict_files(self) -> None:
        """Test conflict_files list is stored when provided.

        Tests:  BranchConflictError — conflict_files with values
        How:    Construct with file list; assert stored.
        Why:    API callers may provide file lists from GitHub response data.
        """
        files = ["src/foo.py", "README.md"]
        err = BranchConflictError(head_branch="a", base_branch="b", conflict_files=files)
        assert err.conflict_files == files

    def test_branch_conflict_error_message_contains_branch_names(self) -> None:
        """Test string representation includes both branch names.

        Tests:  BranchConflictError — __str__ message
        How:    Check str(err) contains head and base branch names.
        Why:    Error messages must be human-readable for CLI and log output.
        """
        err = BranchConflictError(head_branch="milestone/3-x", base_branch="main")
        msg = str(err)
        assert "milestone/3-x" in msg
        assert "main" in msg

    def test_branch_conflict_error_is_backlog_error_subclass(self) -> None:
        """Test BranchConflictError is a subclass of BacklogError.

        Tests:  BranchConflictError — class hierarchy
        How:    issubclass check.
        Why:    Callers using broad BacklogError catch must capture conflict errors.
        """
        assert issubclass(BranchConflictError, BacklogError)


# ---------------------------------------------------------------------------
# Input validation — _validate_slug
# ---------------------------------------------------------------------------


class TestValidateSlug:
    """_validate_slug enforces ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ pattern."""

    def test_validate_slug_valid_simple(self) -> None:
        """Test valid simple slug passes without raising.

        Tests:  _validate_slug — valid alphanumeric slug
        How:    Call with 'v1-workflow'; expect no exception.
        Why:    Valid slugs must not be rejected.
        """
        # Arrange / Act / Assert
        _validate_slug("v1-workflow")  # must not raise

    def test_validate_slug_valid_with_dots_and_underscores(self) -> None:
        """Test valid slug with dots and underscores passes.

        Tests:  _validate_slug — valid slug with all allowed characters
        How:    Call with 'v1.1_milestone-workflow'; expect no exception.
        Why:    Pattern allows dots and underscores after the first character.
        """
        _validate_slug("v1.1_milestone-workflow")  # must not raise

    def test_validate_slug_empty_string_raises_backlog_error(self) -> None:
        """Test empty string raises BacklogError.

        Tests:  _validate_slug — empty string
        How:    Call with ''; assert BacklogError raised.
        Why:    Empty slug would produce a malformed branch name.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="Invalid slug"):
            _validate_slug("")

    def test_validate_slug_starts_with_hyphen_raises_backlog_error(self) -> None:
        """Test slug starting with hyphen raises BacklogError.

        Tests:  _validate_slug — first character is hyphen
        How:    Call with '-bad-slug'; assert BacklogError raised.
        Why:    Pattern requires alphanumeric first character.
        """
        with pytest.raises(BacklogError, match="Invalid slug"):
            _validate_slug("-bad-slug")

    def test_validate_slug_starts_with_dot_raises_backlog_error(self) -> None:
        """Test slug starting with dot raises BacklogError.

        Tests:  _validate_slug — first character is dot
        How:    Call with '.hidden'; assert BacklogError raised.
        Why:    Pattern requires alphanumeric first character.
        """
        with pytest.raises(BacklogError, match="Invalid slug"):
            _validate_slug(".hidden")

    def test_validate_slug_with_spaces_raises_backlog_error(self) -> None:
        """Test slug with spaces raises BacklogError.

        Tests:  _validate_slug — slug contains space
        How:    Call with 'my slug'; assert BacklogError raised.
        Why:    Spaces are not allowed; would break branch names.
        """
        with pytest.raises(BacklogError, match="Invalid slug"):
            _validate_slug("my slug")

    def test_validate_slug_with_slash_raises_backlog_error(self) -> None:
        """Test slug containing slash raises BacklogError.

        Tests:  _validate_slug — slug contains forward slash
        How:    Call with 'my/slug'; assert BacklogError raised.
        Why:    Slashes would inject path separators into branch names.
        """
        with pytest.raises(BacklogError, match="Invalid slug"):
            _validate_slug("my/slug")

    def test_validate_slug_error_message_contains_slug(self) -> None:
        """Test error message includes the invalid slug value.

        Tests:  _validate_slug — error message content
        How:    Catch BacklogError; check slug appears in message.
        Why:    Descriptive error messages help callers diagnose problems.
        """
        with pytest.raises(BacklogError, match="bad slug!"):
            _validate_slug("bad slug!")


# ---------------------------------------------------------------------------
# Input validation — _validate_milestone_number
# ---------------------------------------------------------------------------


class TestValidateMilestoneNumber:
    """_validate_milestone_number enforces milestone_number > 0."""

    def test_validate_milestone_number_positive_passes(self) -> None:
        """Test positive milestone number passes without raising.

        Tests:  _validate_milestone_number — valid positive integer
        How:    Call with 1; expect no exception.
        Why:    Valid milestone numbers must not be rejected.
        """
        _validate_milestone_number(1)  # must not raise

    def test_validate_milestone_number_zero_raises_backlog_error(self) -> None:
        """Test milestone_number=0 raises BacklogError.

        Tests:  _validate_milestone_number — zero value
        How:    Call with 0; assert BacklogError raised.
        Why:    Milestone numbers must be positive; 0 is not a valid GitHub milestone number.
        """
        with pytest.raises(BacklogError, match="greater than zero"):
            _validate_milestone_number(0)

    def test_validate_milestone_number_negative_raises_backlog_error(self) -> None:
        """Test negative milestone_number raises BacklogError.

        Tests:  _validate_milestone_number — negative value
        How:    Call with -5; assert BacklogError raised.
        Why:    Negative numbers are never valid milestone identifiers.
        """
        with pytest.raises(BacklogError, match="greater than zero"):
            _validate_milestone_number(-5)

    def test_validate_milestone_number_error_includes_value(self) -> None:
        """Test error message includes the invalid milestone_number value.

        Tests:  _validate_milestone_number — error message content
        How:    Catch BacklogError from 0; check '0' appears in message.
        Why:    Descriptive error messages help callers diagnose problems.
        """
        with pytest.raises(BacklogError, match="0"):
            _validate_milestone_number(0)


# ---------------------------------------------------------------------------
# Input validation — create_integration_branch (integration)
# ---------------------------------------------------------------------------


class TestCreateIntegrationBranchValidation:
    """create_integration_branch validates slug and milestone_number before API calls."""

    def test_create_branch_invalid_slug_raises_before_api_call(self, mock_repo: Any) -> None:
        """Test invalid slug raises BacklogError without calling GitHub API.

        Tests:  create_integration_branch — slug validation guard
        How:    Pass slug with spaces; assert BacklogError raised and get_branch not called.
        Why:    Validation must short-circuit before any network I/O.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="Invalid slug"):
            create_integration_branch(_MILESTONE, "bad slug!")

        mock_repo.get_branch.assert_not_called()

    def test_create_branch_zero_milestone_raises_before_api_call(self, mock_repo: Any) -> None:
        """Test milestone_number=0 raises BacklogError without calling GitHub API.

        Tests:  create_integration_branch — milestone_number validation guard
        How:    Pass 0; assert BacklogError raised and get_branch not called.
        Why:    Validation must short-circuit before any network I/O.
        """
        with pytest.raises(BacklogError, match="greater than zero"):
            create_integration_branch(0, _SLUG)

        mock_repo.get_branch.assert_not_called()

    def test_create_branch_negative_milestone_raises_backlog_error(self, mock_repo: Any) -> None:
        """Test negative milestone_number raises BacklogError.

        Tests:  create_integration_branch — negative milestone_number
        How:    Pass -1; assert BacklogError raised.
        Why:    Negative milestone numbers are never valid.
        """
        with pytest.raises(BacklogError, match="greater than zero"):
            create_integration_branch(-1, _SLUG)


# ---------------------------------------------------------------------------
# Input validation — merge_integration_branch (integration)
# ---------------------------------------------------------------------------


class TestMergeIntegrationBranchValidation:
    """merge_integration_branch rejects head_branch == base_branch before API calls."""

    def test_merge_same_branch_raises_backlog_error(self, mock_repo: Any) -> None:
        """Test head_branch == base_branch raises BacklogError without API call.

        Tests:  merge_integration_branch — same-branch guard
        How:    Pass identical head and base; assert BacklogError raised and merge not called.
        Why:    Merging a branch into itself is always a caller mistake.
        """
        # Arrange / Act / Assert
        with pytest.raises(BacklogError, match="must differ"):
            merge_integration_branch("main", "main", "msg")

        mock_repo.merge.assert_not_called()

    def test_merge_different_branches_proceeds_to_api(self, mock_repo: Any, mocker: MockerFixture) -> None:
        """Test distinct head and base branches are accepted and reach the API.

        Tests:  merge_integration_branch — different branches pass validation
        How:    Pass distinct branches; assert merge called.
        Why:    Validation must not block valid inputs.
        """
        # Arrange
        merge_commit = mocker.MagicMock()
        merge_commit.sha = _MERGE_SHA
        mock_repo.merge.return_value = merge_commit

        # Act
        merge_integration_branch(_BRANCH, "main", "msg")

        # Assert
        mock_repo.merge.assert_called_once()
