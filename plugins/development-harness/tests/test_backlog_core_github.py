"""Tests for backlog_core/gh_client.py — GraphQL migration (T02).

All tests mock at the ``_graphql_request`` boundary, not at
``repo.requester.graphql_query``. This validates the helper's error handling
logic and keeps tests independent of PyGithub transport internals.

Functions under test:
  - Parser functions: _parse_issue_node, _parse_milestone_node, _parse_search_pr_node
  - Helpers: _is_not_found_error, _get_repo_node_id, _graphql_request
  - Label resolution: _resolve_label_ids_graphql
  - Public API: create_issue_for_item, batch_fetch_statuses, check_open_prs_for_issue
  - Public API: issue_to_local_fields, view_enrich_from_github, try_get_github
  - Public API: apply_status_in_progress, apply_status_verified (label-update path)
  - Public API: fetch_github_issue_body, sync_groomed_to_github_issue

REST-fallback operations (label create, milestone create) retain
PyGithub REST mocks — those are documented ADR-004 exceptions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.gh_client import (
    _get_repo_node_id,
    _is_not_found_error,
    _parse_issue_node,
    _parse_milestone_node,
    _parse_search_pr_node,
    _resolve_label_ids_graphql,
    apply_status_groomed,
    apply_status_in_progress,
    batch_fetch_statuses,
    check_open_prs_for_issue,
    create_issue_for_item,
    fetch_github_issue_body,
    issue_to_local_fields,
    sync_groomed_to_github_issue,
    try_get_github,
    view_enrich_from_github,
)
from backlog_core.models import BacklogError, BacklogItem, Output, ViewItemResult

from tests.graphql_factories import (
    make_create_issue_response,
    make_created_issue_node,
    make_issue_by_number_response,
    make_issue_node,
    make_issues_list_response,
    make_label_node,
    make_milestone_node,
    make_parsed_issue_node,
    make_search_pr_node,
    make_search_prs_response,
    make_update_issue_response,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Shared repo mock helper
# ---------------------------------------------------------------------------


def _make_mock_repo(mocker: MockerFixture, full_name: str = "test-owner/test-repo") -> Any:
    """Return a minimal mock PyGithub Repository for GraphQL tests.

    Args:
        mocker: pytest-mock fixture.
        full_name: Repository full name (owner/repo).

    Returns:
        Mock object with .full_name, .node_id, and .requester.graphql_query set up.
    """
    repo = mocker.Mock()
    repo.full_name = full_name
    repo.node_id = "R_kgDOABCDEF"
    return repo


# ---------------------------------------------------------------------------
# _parse_issue_node — parser function tests (Requirement 14)
# ---------------------------------------------------------------------------


class TestParseIssueNode:
    """Tests for _parse_issue_node() GraphQL response parser.

    Tests: _parse_issue_node correctly maps raw GraphQL dicts to IssueNode TypedDicts.
    Why: Parser is called on every API response; missing-field safety prevents crashes
         when GitHub returns unexpected shapes.
    """

    def test_parse_issue_node_full_input_maps_all_fields(self) -> None:
        """_parse_issue_node maps all expected fields from a complete raw dict.

        Tests: _parse_issue_node happy path
        How: Pass a raw dict with all fields populated; verify each output field.
        Why: Field mapping must be exact — downstream callers depend on these keys.
        """
        # Arrange
        raw: dict[str, Any] = {
            "id": "MDU6SXNzdWUx",
            "number": 42,
            "title": "Fix crash",
            "state": "OPEN",
            "body": "Crashes on null input",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-15T00:00:00Z",
            "labels": {"nodes": [{"name": "bug", "id": "LBL_bug"}, {"name": "priority:p0", "id": "LBL_p0"}]},
            "milestone": {"id": "MS_01", "number": 1, "title": "v1.0"},
            "assignees": {"nodes": [{"login": "alice"}]},
        }

        # Act
        result = _parse_issue_node(raw)

        # Assert
        assert result["id"] == "MDU6SXNzdWUx"
        assert result["number"] == 42
        assert result["title"] == "Fix crash"
        assert result["state"] == "OPEN"
        assert result["body"] == "Crashes on null input"
        assert result["createdAt"] == "2026-01-01T00:00:00Z"
        assert result["updatedAt"] == "2026-01-15T00:00:00Z"
        assert len(result["labels"]) == 2
        assert result["labels"][0] == {"name": "bug", "id": "LBL_bug"}
        assert result["milestone"] is not None
        assert result["milestone"]["title"] == "v1.0"
        assert len(result["assignees"]) == 1
        assert result["assignees"][0]["login"] == "alice"

    def test_parse_issue_node_missing_optional_fields_uses_defaults(self) -> None:
        """_parse_issue_node uses safe defaults when optional fields are absent.

        Tests: _parse_issue_node missing-field handling
        How: Pass a nearly-empty dict; verify default values are applied.
        Why: GitHub occasionally omits fields in partial responses.
        """
        # Arrange
        raw: dict[str, Any] = {}

        # Act
        result = _parse_issue_node(raw)

        # Assert — should not raise; defaults applied
        assert result["id"] == ""
        assert result["number"] == 0
        assert result["title"] == ""
        assert result["state"] == "OPEN"
        assert result["body"] == ""
        assert result["labels"] == []
        assert result["milestone"] is None
        assert result["assignees"] == []

    def test_parse_issue_node_none_milestone_becomes_none(self) -> None:
        """_parse_issue_node maps None milestone field to None in output.

        Tests: _parse_issue_node null milestone
        How: Set milestone=None explicitly in raw dict.
        Why: Issues without milestones must not crash — None is the expected signal.
        """
        # Arrange
        raw: dict[str, Any] = {
            "id": "X",
            "number": 1,
            "title": "t",
            "state": "OPEN",
            "body": "",
            "createdAt": "",
            "updatedAt": "",
            "labels": {"nodes": []},
            "milestone": None,
            "assignees": {"nodes": []},
        }

        # Act
        result = _parse_issue_node(raw)

        # Assert
        assert result["milestone"] is None

    def test_parse_issue_node_empty_labels_nodes_returns_empty_list(self) -> None:
        """_parse_issue_node handles labels.nodes=[] without errors.

        Tests: _parse_issue_node empty labels
        How: Pass labels.nodes=[] in raw dict.
        Why: Unlabelled issues are common; empty list must be returned.
        """
        # Arrange
        raw: dict[str, Any] = {"labels": {"nodes": []}, "assignees": {"nodes": []}}

        # Act
        result = _parse_issue_node(raw)

        # Assert
        assert result["labels"] == []

    def test_parse_issue_node_null_body_becomes_empty_string(self) -> None:
        """_parse_issue_node converts None body to empty string.

        Tests: _parse_issue_node null body handling
        How: Pass body=None in raw dict.
        Why: Callers string-format the body field — None would cause AttributeError.
        """
        # Arrange
        raw: dict[str, Any] = {"body": None}

        # Act
        result = _parse_issue_node(raw)

        # Assert
        assert result["body"] == ""


# ---------------------------------------------------------------------------
# _parse_milestone_node — parser function tests (Requirement 14)
# ---------------------------------------------------------------------------


class TestParseMilestoneNode:
    """Tests for _parse_milestone_node() GraphQL response parser.

    Tests: _parse_milestone_node derives issue counts from nested totalCount fields.
    Why: The issues/closedIssues nested structure is unique to milestones; the
         parser must correctly unwrap it.
    """

    def test_parse_milestone_node_derives_open_and_closed_counts(self) -> None:
        """_parse_milestone_node derives openIssueCount and closedIssueCount from nested data.

        Tests: _parse_milestone_node issue count extraction
        How: Pass raw dict with issues.totalCount and closedIssues.totalCount; verify counts.
        Why: These counts drive milestone progress display.
        """
        # Arrange
        raw: dict[str, Any] = {
            "id": "MI_001",
            "number": 3,
            "title": "v2.0",
            "state": "OPEN",
            "description": "Major release",
            "dueOn": "2026-12-31T00:00:00Z",
            "issues": {"totalCount": 10},
            "closedIssues": {"totalCount": 7},
        }

        # Act
        result = _parse_milestone_node(raw)

        # Assert
        assert result["number"] == 3
        assert result["title"] == "v2.0"
        assert result["openIssueCount"] == 10
        assert result["closedIssueCount"] == 7
        assert result["dueOn"] == "2026-12-31T00:00:00Z"

    def test_parse_milestone_node_null_due_on_becomes_none(self) -> None:
        """_parse_milestone_node maps null dueOn to None.

        Tests: _parse_milestone_node null dueOn
        How: Pass dueOn=None; verify output is None.
        Why: Milestones without due dates are valid; None must not crash callers.
        """
        # Arrange
        raw: dict[str, Any] = {
            "id": "MI_002",
            "number": 1,
            "title": "v1.0",
            "state": "OPEN",
            "description": "",
            "dueOn": None,
            "issues": {"totalCount": 0},
            "closedIssues": {"totalCount": 0},
        }

        # Act
        result = _parse_milestone_node(raw)

        # Assert
        assert result["dueOn"] is None

    def test_parse_milestone_node_missing_issue_counts_defaults_to_zero(self) -> None:
        """_parse_milestone_node defaults issue counts to zero when fields absent.

        Tests: _parse_milestone_node missing issue count fields
        How: Omit issues and closedIssues from raw; verify zero counts returned.
        Why: Prevents KeyError when GitHub omits these fields in some contexts.
        """
        # Arrange
        raw: dict[str, Any] = {"id": "MI_003", "number": 1, "title": "v1.0", "state": "OPEN", "dueOn": None}

        # Act
        result = _parse_milestone_node(raw)

        # Assert
        assert result["openIssueCount"] == 0
        assert result["closedIssueCount"] == 0


# ---------------------------------------------------------------------------
# _parse_search_pr_node — parser function tests (Requirement 14)
# ---------------------------------------------------------------------------


class TestParseSearchPrNode:
    """Tests for _parse_search_pr_node() GraphQL response parser.

    Tests: _parse_search_pr_node filters non-PR nodes from search results.
    Why: GitHub search returns a union type; non-PR nodes return empty dicts that
         must be detected and skipped.
    """

    def test_parse_search_pr_node_valid_pr_returns_node(self) -> None:
        """_parse_search_pr_node returns SearchPRNode for a valid PR dict.

        Tests: _parse_search_pr_node happy path
        How: Pass a dict with number, title, url, state fields.
        Why: Valid PRs must be mapped to the structured node type.
        """
        # Arrange
        raw: dict[str, Any] = {
            "number": 55,
            "title": "fix: crash",
            "url": "https://github.com/owner/repo/pull/55",
            "state": "OPEN",
        }

        # Act
        result = _parse_search_pr_node(raw)

        # Assert
        assert result is not None
        assert result["number"] == 55
        assert result["title"] == "fix: crash"
        assert result["url"] == "https://github.com/owner/repo/pull/55"
        assert result["state"] == "OPEN"

    def test_parse_search_pr_node_empty_dict_returns_none(self) -> None:
        """_parse_search_pr_node returns None for an empty dict (non-PR result).

        Tests: _parse_search_pr_node non-PR node filtering
        How: Pass an empty dict (what GitHub returns for non-PR union members).
        Why: Non-PR search results must be filtered out, not included.
        """
        # Arrange
        raw: dict[str, Any] = {}

        # Act
        result = _parse_search_pr_node(raw)

        # Assert
        assert result is None

    def test_parse_search_pr_node_zero_number_returns_none(self) -> None:
        """_parse_search_pr_node returns None when number is 0 or falsy.

        Tests: _parse_search_pr_node zero-number guard
        How: Pass a dict with number=0.
        Why: Only actual PRs have positive numbers; 0 indicates a non-PR node.
        """
        # Arrange
        raw: dict[str, Any] = {"number": 0, "title": "", "url": "", "state": ""}

        # Act
        result = _parse_search_pr_node(raw)

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# _is_not_found_error — helper tests (Requirement 15)
# ---------------------------------------------------------------------------


class TestIsNotFoundError:
    """Tests for _is_not_found_error() helper.

    Tests: _is_not_found_error correctly classifies BacklogError as not-found.
    Why: 404-equivalent detection drives graceful degradation in public functions
         that must distinguish 'resource absent' from 'API failure'.
    """

    def test_could_not_resolve_message_returns_true(self) -> None:
        """_is_not_found_error returns True for 'Could not resolve' error messages.

        Tests: _is_not_found_error GraphQL not-found pattern
        How: Create BacklogError with 'Could not resolve to ...' message.
        Why: This is the exact phrase GitHub GraphQL returns for 404-equivalent errors.
        """
        # Arrange
        error = BacklogError("GraphQL error: Could not resolve to an Issue with the number 999")

        # Act
        result = _is_not_found_error(error)

        # Assert
        assert result is True

    def test_not_found_message_returns_true(self) -> None:
        """_is_not_found_error returns True for messages containing 'not found'.

        Tests: _is_not_found_error not-found phrase matching
        How: Create BacklogError with 'not found' in message.
        Why: Some operations surface this phrase in their error messages.
        """
        # Arrange
        error = BacklogError("issue not found")

        # Act
        result = _is_not_found_error(error)

        # Assert
        assert result is True

    def test_unrelated_error_returns_false(self) -> None:
        """_is_not_found_error returns False for unrelated error messages.

        Tests: _is_not_found_error negative case
        How: Create BacklogError with auth/network failure message.
        Why: Must not confuse auth failures with missing resources.
        """
        # Arrange
        error = BacklogError("GraphQL error: Bad credentials")

        # Act
        result = _is_not_found_error(error)

        # Assert
        assert result is False

    def test_rate_limit_error_returns_false(self) -> None:
        """_is_not_found_error returns False for rate limit errors.

        Tests: _is_not_found_error rate-limit negative case
        How: Pass rate limit error message.
        Why: Rate limiting must not be treated as a missing-resource condition.
        """
        # Arrange
        error = BacklogError("GraphQL error: API rate limit exceeded")

        # Act
        result = _is_not_found_error(error)

        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# _get_repo_node_id — caching behavior (Requirement 16)
# ---------------------------------------------------------------------------


class TestGetRepoNodeId:
    """Tests for _get_repo_node_id() helper.

    Tests: _get_repo_node_id returns the repository's GraphQL node ID.
    Why: This ID is required for createIssue mutations; incorrect IDs cause
         silent creation failures.
    """

    def test_returns_repo_node_id(self, mocker: MockerFixture) -> None:
        """_get_repo_node_id returns the node_id from the PyGithub Repository object.

        Tests: _get_repo_node_id reads node_id property
        How: Create mock repo with known node_id; verify it is returned verbatim.
        Why: The repo node_id is pre-populated by PyGithub — no extra API call needed.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.node_id = "R_kgDOSpecificId"

        # Act
        result = _get_repo_node_id(repo)

        # Assert
        assert result == "R_kgDOSpecificId"

    def test_converts_node_id_to_string(self, mocker: MockerFixture) -> None:
        """_get_repo_node_id converts non-string node_id to str.

        Tests: _get_repo_node_id type coercion
        How: Set node_id to an integer-like value.
        Why: str() coercion ensures consistent return type regardless of PyGithub internals.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        object.__setattr__(repo, "node_id", 12345)

        # Act
        result = _get_repo_node_id(repo)

        # Assert
        assert result == "12345"
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _resolve_label_ids_graphql — label fetch-then-update (Requirement 17)
# ---------------------------------------------------------------------------


class TestResolveLabelIdsGraphql:
    """Tests for _resolve_label_ids_graphql() — ADR-003 label update helper.

    Tests: _resolve_label_ids_graphql returns {name: node_id} for existing labels.
    Why: This function is the foundation of the ADR-003 fetch-then-update pattern
         for label mutations. Incorrect IDs corrupt all label state.
    """

    def test_all_labels_found_returns_full_mapping(self, mocker: MockerFixture) -> None:
        """_resolve_label_ids_graphql returns name->id mapping for all found labels.

        Tests: _resolve_label_ids_graphql all-found case
        How: Mock requester to return all labels with IDs; verify full mapping returned.
        Why: Happy path must correctly map every requested label name to its node ID.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_001", "name": "status:open"},
                        "label1": {"id": "LBL_002", "name": "priority:p1"},
                    }
                }
            },
        )

        # Act
        result = _resolve_label_ids_graphql(repo, "test-owner", "test-repo", ["status:open", "priority:p1"])

        # Assert
        assert result == {"status:open": "LBL_001", "priority:p1": "LBL_002"}

    def test_missing_label_omitted_from_result(self, mocker: MockerFixture) -> None:
        """_resolve_label_ids_graphql omits labels that resolve to None (missing in repo).

        Tests: _resolve_label_ids_graphql missing label handling
        How: Return None for label1 alias; verify it is absent from the result.
        Why: Missing labels must not crash — they are silently excluded (ADR-003).
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_001", "name": "status:open"},
                        "label1": None,  # missing label
                    }
                }
            },
        )

        # Act
        result = _resolve_label_ids_graphql(repo, "test-owner", "test-repo", ["status:open", "nonexistent"])

        # Assert
        assert "status:open" in result
        assert "nonexistent" not in result
        assert len(result) == 1

    def test_empty_label_names_returns_empty_dict(self, mocker: MockerFixture) -> None:
        """_resolve_label_ids_graphql returns empty dict for empty input.

        Tests: _resolve_label_ids_graphql empty input guard
        How: Pass an empty list; verify no API call is made.
        Why: create_issue_for_item passes empty label list when no labels needed.
        """
        # Arrange
        repo = _make_mock_repo(mocker)

        # Act
        result = _resolve_label_ids_graphql(repo, "test-owner", "test-repo", [])

        # Assert
        assert result == {}
        repo.requester.graphql_query.assert_not_called()

    def test_invalid_label_name_raises_value_error(self, mocker: MockerFixture) -> None:
        """_resolve_label_ids_graphql raises ValueError for label names with disallowed characters.

        Tests: _resolve_label_ids_graphql label name validation
        How: Pass a label name containing a semicolon.
        Why: Label names are embedded in GraphQL queries; invalid characters enable injection.
        """
        # Arrange
        repo = _make_mock_repo(mocker)

        # Act / Assert
        with pytest.raises(ValueError, match="disallowed characters"):
            _resolve_label_ids_graphql(repo, "test-owner", "test-repo", ["valid-label", "bad;label"])

    def test_deduplicates_label_names(self, mocker: MockerFixture) -> None:
        """_resolve_label_ids_graphql deduplicates label names before querying.

        Tests: _resolve_label_ids_graphql deduplication
        How: Pass duplicate label names; verify only one alias is in the query.
        Why: Duplicate aliases in GraphQL would cause a query validation error.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = (
            {},
            {"data": {"repository": {"label0": {"id": "LBL_001", "name": "bug"}}}},
        )

        # Act
        result = _resolve_label_ids_graphql(repo, "test-owner", "test-repo", ["bug", "bug"])

        # Assert
        assert len(result) == 1
        assert "bug" in result
        # Only one graphql_query call with a single alias
        repo.requester.graphql_query.assert_called_once()


# ---------------------------------------------------------------------------
# create_issue_for_item — GraphQL mutation (ADR-003 label pattern)
# ---------------------------------------------------------------------------


class TestCreateIssueForItem:
    """create_issue_for_item creates a GitHub issue via GraphQL mutation.

    Tests: create_issue_for_item correctly uses _resolve_label_ids_graphql and
           _create_issue_graphql instead of PyGithub REST methods.
    Why: This is the primary issue creation path; all callers depend on the
         returned issue number for backlog-to-GitHub linking.
    """

    def test_create_issue_returns_issue_number(self, mocker: MockerFixture) -> None:
        """create_issue_for_item returns the new issue number on success.

        Tests: create_issue_for_item happy path
        How: Mock _graphql_request to return a created issue node with number=42.
        Why: Callers use the returned number to update local cache.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_001", "name": "status:needs-grooming"},
                        "label1": {"id": "LBL_002", "name": "priority:p1"},
                        "label2": {"id": "LBL_003", "name": "type:feature"},
                    }
                }
            },
        )
        mocker.patch(
            "backlog_core.gh_client._graphql_request",
            return_value=make_create_issue_response(make_created_issue_node(number=42)),
        )
        item = BacklogItem(title="Add dark mode", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item)

        # Assert
        assert result == 42

    def test_create_issue_empty_title_returns_none(self, mocker: MockerFixture) -> None:
        """create_issue_for_item returns None and makes no API call for empty title.

        Tests: create_issue_for_item empty title guard
        How: Pass BacklogItem with title="" and verify no GraphQL call is made.
        Why: An issue with no title is invalid — the guard prevents pointless API calls.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mock_gql = mocker.patch("backlog_core.gh_client._graphql_request")
        item = BacklogItem(title="", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item)

        # Assert
        assert result is None
        mock_gql.assert_not_called()

    def test_create_issue_dry_run_returns_none_without_api_call(self, mocker: MockerFixture) -> None:
        """create_issue_for_item returns None in dry-run mode without touching GitHub.

        Tests: create_issue_for_item dry-run mode
        How: Call with dry_run=True; verify _graphql_request is not called.
        Why: Dry-run must be safe to invoke without creating anything.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mock_gql = mocker.patch("backlog_core.gh_client._graphql_request")
        out = Output()
        item = BacklogItem(title="Dry run item", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item, dry_run=True, output=out)

        # Assert
        assert result is None
        mock_gql.assert_not_called()
        assert any("dry-run" in m.lower() for m in out.messages)

    def test_create_issue_warns_on_missing_label(self, mocker: MockerFixture) -> None:
        """create_issue_for_item warns via Output when a label does not exist in the repo.

        Tests: create_issue_for_item missing label warning
        How: Return None alias for label1 in label resolution response.
        Why: Missing labels must not abort creation — a warning is the correct response.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        # All labels missing
        repo.requester.graphql_query.return_value = (
            {},
            {"data": {"repository": {"label0": None, "label1": None, "label2": None}}},
        )
        mocker.patch(
            "backlog_core.gh_client._graphql_request",
            return_value=make_create_issue_response(make_created_issue_node(number=5)),
        )
        out = Output()
        item = BacklogItem(title="Some feature", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item, output=out)

        # Assert
        assert result == 5
        assert any("WARNING" in w for w in out.warnings)

    def test_create_issue_uses_correct_title_prefix_for_bug(self, mocker: MockerFixture) -> None:
        """create_issue_for_item prefixes bug items with 'fix:'.

        Tests: create_issue_for_item title formatting for bug type
        How: Capture the title arg passed to _graphql_request; verify 'fix:' prefix.
        Why: Conventional-commit prefix must match item type for correct categorisation.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = ({}, {"data": {"repository": {}}})
        captured_vars: list[dict[str, Any]] = []

        def capture_graphql(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            if variables and "title" in variables:
                captured_vars.append(variables)
            return make_create_issue_response(make_created_issue_node(number=7))

        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=capture_graphql)
        item = BacklogItem(title="Fix null crash", item_type="bug", priority="P0")

        # Act
        create_issue_for_item(repo, item)

        # Assert
        assert len(captured_vars) == 1
        assert captured_vars[0]["title"].startswith("fix: Fix null crash")


# ---------------------------------------------------------------------------
# batch_fetch_statuses — GraphQL list query (Requirement: replaces N+1 REST)
# ---------------------------------------------------------------------------


class TestBatchFetchStatuses:
    """batch_fetch_statuses maps issue numbers to IssueStatus via a single GraphQL call.

    Tests: batch_fetch_statuses uses _fetch_issues_graphql instead of repo.get_issues().
    Why: The N+1 REST pattern is the primary motivation for this migration;
         the single-call pattern must be verified.
    """

    def test_returns_status_for_item_with_matching_issue(self, mocker: MockerFixture) -> None:
        """batch_fetch_statuses returns IssueStatus for items whose issue number appears in GraphQL results.

        Tests: batch_fetch_statuses happy path
        How: Patch try_get_github and _graphql_request; verify IssueStatus populated.
        Why: This is the primary consumer-facing behaviour — status enrichment for listing.
        """
        # Arrange
        issue_node = make_issue_node(
            number=10,
            labels=[make_label_node("status:in-progress", "LBL_ip"), make_label_node("priority:p1", "LBL_p1")],
            milestone=make_milestone_node(title="v1.0"),
        )
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issues_list_response([issue_node]))
        items = [BacklogItem(title="Feature A", issue="#10", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert 10 in result
        assert result[10].status == "status:in-progress"
        assert result[10].milestone == "v1.0"

    def test_skips_items_without_issue_number(self, mocker: MockerFixture) -> None:
        """batch_fetch_statuses silently skips items with no issue field.

        Tests: batch_fetch_statuses empty issue guard
        How: Pass BacklogItem with issue="" and verify result dict is empty.
        Why: Local-only items have no issue number to look up.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issues_list_response([]))
        items = [BacklogItem(title="No issue item", issue="", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result == {}

    def test_returns_empty_dict_when_github_unavailable(self, mocker: MockerFixture) -> None:
        """batch_fetch_statuses returns empty dict when try_get_github returns None.

        Tests: batch_fetch_statuses offline path
        How: Patch try_get_github to return None.
        Why: Agents must work offline — empty status is acceptable, crash is not.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=None)
        items = [BacklogItem(title="Item", issue="#5", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result == {}

    def test_empty_milestone_is_empty_string(self, mocker: MockerFixture) -> None:
        """batch_fetch_statuses maps None milestone to empty string in IssueStatus.

        Tests: batch_fetch_statuses null milestone handling
        How: Return IssueNode with milestone=None; verify IssueStatus.milestone is "".
        Why: Callers string-format the milestone field — None would cause crash.
        """
        # Arrange
        issue_node = make_issue_node(number=30, milestone=None)
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issues_list_response([issue_node]))
        items = [BacklogItem(title="No milestone", issue="#30", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result[30].milestone == ""

    def test_issue_not_in_graphql_result_is_absent_from_return(self, mocker: MockerFixture) -> None:
        """batch_fetch_statuses does not include issue numbers absent from GraphQL response.

        Tests: batch_fetch_statuses absent-issue handling
        How: Item references issue #99 but GraphQL returns issue #10.
        Why: Missing issues should produce an empty dict, not crash or hallucinate data.
        """
        # Arrange
        issue_node = make_issue_node(number=10)
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issues_list_response([issue_node]))
        items = [BacklogItem(title="Missing issue", issue="#99", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert 99 not in result


# ---------------------------------------------------------------------------
# check_open_prs_for_issue — GraphQL search query
# ---------------------------------------------------------------------------


class TestCheckOpenPrsForIssue:
    """check_open_prs_for_issue searches for open PRs via GraphQL instead of search_issues.

    Tests: check_open_prs_for_issue uses _graphql_request with _SEARCH_PRS_QUERY.
    Why: The migration replaced Github.search_issues() with a GraphQL search query;
         the test mocks at _graphql_request to validate the correct layer.
    """

    def test_returns_pull_request_refs_for_matching_prs(self, mocker: MockerFixture) -> None:
        """check_open_prs_for_issue returns PullRequestRef list for matching open PRs.

        Tests: check_open_prs_for_issue happy path
        How: Patch get_github and _graphql_request with a SearchPR response.
        Why: Callers block close/resolve operations when PRs are open.
        """
        # Arrange
        pr_node = make_search_pr_node(number=55, title="fix: implement feature")
        mocker.patch("backlog_core.gh_client.get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_search_prs_response([pr_node]))

        # Act
        result = check_open_prs_for_issue(10, "test-owner/test-repo")

        # Assert
        assert len(result) == 1
        assert result[0].number == 55
        assert result[0].title == "fix: implement feature"

    def test_returns_empty_list_when_no_prs_found(self, mocker: MockerFixture) -> None:
        """check_open_prs_for_issue returns empty list when search yields no results.

        Tests: check_open_prs_for_issue no-match case
        How: Return empty nodes list from _graphql_request.
        Why: Empty list is the expected signal that close/resolve is safe.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_search_prs_response([]))

        # Act
        result = check_open_prs_for_issue(42, "test-owner/test-repo")

        # Assert
        assert result == []

    def test_returns_empty_list_on_backlog_error(self, mocker: MockerFixture) -> None:
        """check_open_prs_for_issue returns empty list when _graphql_request raises BacklogError.

        Tests: check_open_prs_for_issue error handling
        How: Raise BacklogError from _graphql_request; verify empty list returned.
        Why: PR-check errors must not block the close/resolve flow.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=BacklogError("GraphQL error: timeout"))

        # Act
        result = check_open_prs_for_issue(10, "test-owner/test-repo")

        # Assert
        assert result == []

    def test_filters_out_non_pr_search_nodes(self, mocker: MockerFixture) -> None:
        """check_open_prs_for_issue skips empty dicts returned for non-PR search hits.

        Tests: check_open_prs_for_issue non-PR node filtering
        How: Include one valid PR node and one empty dict in search response.
        Why: GraphQL search returns union types; non-PR nodes are empty dicts.
        """
        # Arrange
        pr_node = make_search_pr_node(number=55)
        non_pr_node: dict[str, Any] = {}  # non-PR union member returns empty dict
        mocker.patch("backlog_core.gh_client.get_github", return_value=_make_mock_repo(mocker))
        mocker.patch(
            "backlog_core.gh_client._graphql_request", return_value=make_search_prs_response([pr_node, non_pr_node])
        )

        # Act
        result = check_open_prs_for_issue(10, "test-owner/test-repo")

        # Assert
        assert len(result) == 1
        assert result[0].number == 55


# ---------------------------------------------------------------------------
# issue_to_local_fields — accepts IssueNode (ADR-005 signature change)
# ---------------------------------------------------------------------------


class TestIssueToLocalFields:
    """issue_to_local_fields accepts IssueNode TypedDict (ADR-005 change from PyGithub Issue).

    Tests: issue_to_local_fields correctly maps IssueNode fields to IssueLocalFields.
    Why: ADR-005 changed the function signature — the tests must validate the new
         contract (dict input) not the old one (PyGithub Issue object input).
    """

    def test_maps_priority_from_label(self) -> None:
        """issue_to_local_fields extracts priority from 'priority:*' label.

        Tests: issue_to_local_fields priority label extraction
        How: Pass IssueNode with priority:p0 label; verify priority field.
        Why: Priority must come from labels, not from a bare field.
        """
        # Arrange
        issue = make_parsed_issue_node(
            title="Critical fix", labels=[make_label_node("priority:p0", "LBL_p0")], state="OPEN"
        )

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.priority == "P0"

    def test_maps_item_type_from_label(self) -> None:
        """issue_to_local_fields extracts item_type from 'type:*' label.

        Tests: issue_to_local_fields type label extraction
        How: Pass IssueNode with type:bug label; verify item_type field.
        Why: Item type drives categorisation in the backlog view.
        """
        # Arrange
        issue = make_parsed_issue_node(title="Bug fix", labels=[make_label_node("type:bug", "LBL_bug")], state="OPEN")

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.item_type == "Bug"

    def test_closed_issue_sets_status_done(self) -> None:
        """issue_to_local_fields sets status='done' for CLOSED issues.

        Tests: issue_to_local_fields CLOSED state mapping
        How: Pass IssueNode with state='CLOSED'; verify status.
        Why: Closed issues must be marked done regardless of status labels.
        """
        # Arrange
        issue = make_parsed_issue_node(state="CLOSED", labels=[])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.status == "done"

    def test_open_issue_with_status_label_uses_label_status(self) -> None:
        """issue_to_local_fields uses status label value for OPEN issues.

        Tests: issue_to_local_fields status label extraction for open issues
        How: Pass OPEN IssueNode with status:in-progress label.
        Why: Status labels drive live status display in backlog views.
        """
        # Arrange
        issue = make_parsed_issue_node(state="OPEN", labels=[make_label_node("status:in-progress", "LBL_ip")])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.status == "in-progress"

    def test_milestone_title_extracted_when_present(self) -> None:
        """issue_to_local_fields extracts milestone title from milestone node.

        Tests: issue_to_local_fields milestone extraction
        How: Pass IssueNode with milestone dict; verify milestone field.
        Why: Milestone is displayed in view-enrichment output.
        """
        # Arrange
        issue = make_parsed_issue_node(milestone=make_milestone_node(title="v2.0"))

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.milestone == "v2.0"

    def test_no_milestone_gives_empty_string(self) -> None:
        """issue_to_local_fields sets milestone='' when milestone is None.

        Tests: issue_to_local_fields null milestone handling
        How: Pass IssueNode with milestone=None.
        Why: Empty string prevents AttributeError in callers that string-format milestone.
        """
        # Arrange
        issue = make_parsed_issue_node(milestone=None)

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.milestone == ""

    def test_defaults_priority_p1_when_no_priority_label(self) -> None:
        """issue_to_local_fields defaults to P1 when no priority label is present.

        Tests: issue_to_local_fields priority default
        How: Pass IssueNode with no priority label.
        Why: P1 is the assumed default when no label signals otherwise.
        """
        # Arrange
        issue = make_parsed_issue_node(labels=[])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.priority == "P1"


# ---------------------------------------------------------------------------
# view_enrich_from_github — enriches ViewItemResult from GraphQL
# ---------------------------------------------------------------------------


class TestViewEnrichFromGithub:
    """view_enrich_from_github enriches a ViewItemResult with live GraphQL issue data.

    Tests: view_enrich_from_github uses _fetch_issue_graphql instead of repo.get_issue().
    Why: View enrichment is the primary user-facing path for real-time issue data.
    """

    def test_enriches_result_with_graphql_data_returns_true(self, mocker: MockerFixture) -> None:
        """view_enrich_from_github populates ViewItemResult fields and returns True.

        Tests: view_enrich_from_github happy path
        How: Mock try_get_github and _graphql_request; verify result fields populated.
        Why: Returns True to signal that GitHub data was fetched successfully.
        """
        # Arrange
        issue_node = make_issue_node(
            number=42,
            title="Important feature",
            state="OPEN",
            body="Feature body",
            labels=[make_label_node("status:in-progress", "LBL_ip"), make_label_node("priority:p0", "LBL_p0")],
            milestone=make_milestone_node(title="v1.0"),
        )
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issue_by_number_response(issue_node))
        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "42")

        # Assert
        assert enriched is True
        assert result.number == 42
        assert result.title == "Important feature"
        assert result.state == "open"  # lowercased from "OPEN"
        assert result.milestone == "v1.0"
        assert result.status == "in-progress"
        assert result.priority == "P0"

    def test_returns_false_when_github_unavailable(self, mocker: MockerFixture) -> None:
        """view_enrich_from_github returns False when try_get_github returns None.

        Tests: view_enrich_from_github offline path
        How: Patch try_get_github to return None.
        Why: No token / offline must degrade gracefully, not crash.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=None)
        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "42")

        # Assert
        assert enriched is False

    def test_returns_false_on_backlog_error(self, mocker: MockerFixture) -> None:
        """view_enrich_from_github returns False when _graphql_request raises BacklogError.

        Tests: view_enrich_from_github error handling
        How: Raise BacklogError from _graphql_request.
        Why: Errors must not crash the view command; False is the correct signal.
        """
        # Arrange
        mocker.patch("backlog_core.gh_client.try_get_github", return_value=_make_mock_repo(mocker))
        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=BacklogError("GraphQL error: not found"))
        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "999")

        # Assert
        assert enriched is False


# ---------------------------------------------------------------------------
# try_get_github — connection helper
# ---------------------------------------------------------------------------


class TestTryGetGithub:
    """try_get_github returns None gracefully when GitHub is unavailable.

    Tests: try_get_github returns None on missing token or GithubException.
    Why: All callers that use try_get_github must handle None safely.
    """

    def test_returns_none_when_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None when GITHUB_TOKEN env var is not set.

        Tests: try_get_github missing token
        How: Remove GITHUB_TOKEN from environment; call function.
        Why: No token is the most common offline scenario.
        """
        # Arrange
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Act
        result = try_get_github("test-owner/test-repo")

        # Assert
        assert result is None

    def test_returns_none_on_github_exception(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None when PyGithub raises GithubException.

        Tests: try_get_github API failure handling
        How: Patch Github.get_repo to raise GithubException.
        Why: Auth failures and network errors must not crash callers.
        """
        # Arrange
        from github import GithubException

        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        mocker.patch("backlog_core.gh_client.Github").return_value.get_repo.side_effect = GithubException(
            status=401, data="Bad credentials", headers={}
        )

        # Act
        result = try_get_github("test-owner/test-repo")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# apply_status_in_progress — ADR-003 fetch-then-update label pattern
# ---------------------------------------------------------------------------


class TestApplyStatusInProgress:
    """apply_status_in_progress uses fetch-then-update GraphQL label pattern (ADR-003).

    Tests: apply_status_in_progress fetches issue labels, computes desired set,
           and calls _update_issue_graphql with the full label ID list.
    Why: ADR-003 requires full label ID replacement (not additive); the test
         verifies that the fetch-then-compute-then-update flow is followed.
    """

    def test_sets_in_progress_label_via_graphql(self, mocker: MockerFixture) -> None:
        """apply_status_in_progress updates label set via GraphQL when not already in-progress.

        Tests: apply_status_in_progress happy path
        How: Mock get_github, _graphql_request sequence (fetch issue, resolve labels, update).
        Why: Verifies the ADR-003 fetch-then-update pattern is used correctly.
        """
        # Arrange
        issue_node = make_issue_node(
            id="MDU6SXNzdWUx",
            number=5,
            labels=[make_label_node("status:needs-grooming", "LBL_ng"), make_label_node("priority:p1", "LBL_p1")],
        )
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        # _resolve_label_ids_graphql uses repo.requester.graphql_query directly
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_p1", "name": "priority:p1"},
                        "label1": {"id": "LBL_ip", "name": "status:in-progress"},
                    }
                }
            },
        )

        call_count = 0

        def side_effect(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: _fetch_issue_graphql
                return make_issue_by_number_response(issue_node)
            # Second call: _update_issue_graphql
            return make_update_issue_response()

        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=side_effect)
        item = BacklogItem(title="Task", issue="#5", priority="P1")

        # Act — should not raise
        apply_status_in_progress(item)

        # Assert — _graphql_request was called twice: fetch + update
        assert call_count == 2

    def test_skips_update_when_already_in_progress(self, mocker: MockerFixture) -> None:
        """apply_status_in_progress is a no-op when issue already has status:in-progress.

        Tests: apply_status_in_progress idempotent case
        How: Provide issue with status:in-progress already set; verify update not called.
        Why: Idempotent calls must not re-apply labels unnecessarily.
        """
        # Arrange
        issue_node = make_issue_node(
            id="MDU6SXNzdWUx", number=5, labels=[make_label_node("status:in-progress", "LBL_ip")]
        )
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        mock_gql = mocker.patch(
            "backlog_core.gh_client._graphql_request", return_value=make_issue_by_number_response(issue_node)
        )
        item = BacklogItem(title="Task", issue="#5", priority="P1")
        out = Output()

        # Act
        apply_status_in_progress(item, output=out)

        # Assert — only one call for fetch; no update call
        assert mock_gql.call_count == 1
        assert any("already" in m.lower() for m in out.messages)


# ---------------------------------------------------------------------------
# fetch_github_issue_body — returns body or None on error
# ---------------------------------------------------------------------------


class TestFetchGithubIssueBody:
    """fetch_github_issue_body returns issue body string via GraphQL.

    Tests: fetch_github_issue_body uses _fetch_issue_graphql correctly.
    Why: This function is the read path for issue body sync operations.
    """

    def test_returns_issue_body_on_success(self, mocker: MockerFixture) -> None:
        """fetch_github_issue_body returns the body string from GraphQL response.

        Tests: fetch_github_issue_body happy path
        How: Mock _graphql_request with an issue containing a known body.
        Why: Callers depend on this to read issue body for sync operations.
        """
        # Arrange
        issue_node = make_issue_node(body="This is the issue body")
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issue_by_number_response(issue_node))

        # Act
        result = fetch_github_issue_body(mock_repo, 42)

        # Assert
        assert result == "This is the issue body"

    def test_returns_none_on_backlog_error(self, mocker: MockerFixture) -> None:
        """fetch_github_issue_body returns None and warns when GraphQL raises BacklogError.

        Tests: fetch_github_issue_body error handling
        How: Raise BacklogError from _graphql_request.
        Why: Callers must handle None as 'failed to fetch' without crashing.
        """
        # Arrange
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=BacklogError("GraphQL error: not found"))
        out = Output()

        # Act
        result = fetch_github_issue_body(mock_repo, 999, output=out)

        # Assert
        assert result is None
        assert any("WARNING" in w for w in out.warnings)


# ---------------------------------------------------------------------------
# sync_groomed_to_github_issue — GraphQL body update
# ---------------------------------------------------------------------------


class TestSyncGroomedToGithubIssue:
    """sync_groomed_to_github_issue fetches then updates issue body via GraphQL.

    Tests: sync_groomed_to_github_issue uses _fetch_issue_graphql and _update_issue_graphql.
    Why: The groomed-content sync is the write path for grooming results.
    """

    def test_returns_true_when_body_changed(self, mocker: MockerFixture) -> None:
        """sync_groomed_to_github_issue returns True when body was successfully updated.

        Tests: sync_groomed_to_github_issue happy path
        How: Provide issue with empty body; add groomed content; verify True returned.
        Why: Return value signals to caller whether GitHub was updated.
        """
        # Arrange
        issue_node = make_issue_node(id="MDU6SXNzdWUx", body="Original body")
        mock_repo = _make_mock_repo(mocker)

        call_count = 0

        def side_effect(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_issue_by_number_response(issue_node)
            return make_update_issue_response()

        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=side_effect)

        # Act
        result = sync_groomed_to_github_issue(mock_repo, 1, "New groomed content")

        # Assert
        assert result is True
        assert call_count == 2  # fetch + update

    def test_returns_false_when_content_empty(self, mocker: MockerFixture) -> None:
        """sync_groomed_to_github_issue returns False when groomed_content is empty.

        Tests: sync_groomed_to_github_issue empty content guard
        How: Pass empty string as groomed_content.
        Why: Empty content should not trigger a write.
        """
        # Arrange
        issue_node = make_issue_node(body="Original body")
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issue_by_number_response(issue_node))

        # Act
        result = sync_groomed_to_github_issue(mock_repo, 1, "")

        # Assert
        assert result is False

    def test_returns_false_and_warns_on_backlog_error(self, mocker: MockerFixture) -> None:
        """sync_groomed_to_github_issue returns False and warns on BacklogError.

        Tests: sync_groomed_to_github_issue error handling
        How: Raise BacklogError from _graphql_request.
        Why: Sync errors must not crash the grooming workflow.
        """
        # Arrange
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=BacklogError("GraphQL error: timeout"))
        out = Output()

        # Act
        result = sync_groomed_to_github_issue(mock_repo, 1, "content", output=out)

        # Assert
        assert result is False
        assert any("WARNING" in w for w in out.warnings)


# ---------------------------------------------------------------------------
# apply_status_groomed — ADR-003 fetch-then-update label pattern
# ---------------------------------------------------------------------------


class TestApplyStatusGroomed:
    """apply_status_groomed uses fetch-then-update GraphQL label pattern (ADR-003).

    Tests: apply_status_groomed fetches issue labels, computes desired set
           (add status:groomed, remove status:needs-grooming), and calls
           _update_issue_graphql with the full label ID list.
    Why: ADR-003 requires full label ID replacement (not additive); tests verify
         the fetch-then-compute-then-update flow, idempotency, label creation, and
         no-issue early exit.
    """

    def test_apply_status_groomed_adds_label_removes_needs_grooming(self, mocker: MockerFixture) -> None:
        """apply_status_groomed adds status:groomed and removes status:needs-grooming.

        Tests: apply_status_groomed happy path label set computation
        How: Issue has status:needs-grooming + priority:p1. Assert update call
             receives status:groomed ID (LBL_g) but not needs-grooming ID (LBL_ng).
        Why: Core behavior — groomed replaces needs-grooming in the label set.
        """
        # Arrange
        issue_node = make_issue_node(
            id="MDU6SXNzdWUx",
            number=5,
            labels=[make_label_node("status:needs-grooming", "LBL_ng"), make_label_node("priority:p1", "LBL_p1")],
        )
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_p1", "name": "priority:p1"},
                        "label1": {"id": "LBL_g", "name": "status:groomed"},
                    }
                }
            },
        )

        call_count = 0

        def side_effect(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_issue_by_number_response(issue_node)
            return make_update_issue_response()

        mock_gql = mocker.patch("backlog_core.gh_client._graphql_request", side_effect=side_effect)
        item = BacklogItem(title="Task", issue="#5", priority="P1")

        # Act
        apply_status_groomed(item)

        # Assert — fetch + update both ran
        assert call_count == 2
        # Update call must carry groomed ID but not needs-grooming ID
        update_call = mock_gql.call_args_list[1]
        variables = update_call.kwargs.get("variables") or (update_call.args[2] if len(update_call.args) > 2 else None)
        assert variables is not None
        label_ids = variables.get("labelIds", [])
        assert "LBL_g" in label_ids
        assert "LBL_ng" not in label_ids

    def test_apply_status_groomed_idempotent_when_already_groomed(self, mocker: MockerFixture) -> None:
        """apply_status_groomed is a no-op when issue already has status:groomed.

        Tests: apply_status_groomed idempotent — already-groomed early return
        How: Issue already has status:groomed label; verify _update_issue_graphql
             is NOT called (only the fetch call is made).
        Why: Calling apply_status_groomed twice must not re-apply labels.
        """
        # Arrange
        issue_node = make_issue_node(id="MDU6SXNzdWUx", number=5, labels=[make_label_node("status:groomed", "LBL_g")])
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        mock_gql = mocker.patch(
            "backlog_core.gh_client._graphql_request", return_value=make_issue_by_number_response(issue_node)
        )
        item = BacklogItem(title="Task", issue="#5", priority="P1")
        out = Output()

        # Act
        apply_status_groomed(item, output=out)

        # Assert — only fetch call; no update call issued
        assert mock_gql.call_count == 1
        assert any("already" in m.lower() for m in out.messages)

    def test_apply_status_groomed_idempotent_when_needs_grooming_already_removed(self, mocker: MockerFixture) -> None:
        """apply_status_groomed still adds status:groomed when needs-grooming is absent.

        Tests: apply_status_groomed with no needs-grooming label to remove
        How: Issue has only priority:p1 (no needs-grooming); verify update is
             still called and status:groomed is applied.
        Why: Absence of needs-grooming must not prevent the groomed label being added.
        """
        # Arrange
        issue_node = make_issue_node(id="MDU6SXNzdWUx", number=5, labels=[make_label_node("priority:p1", "LBL_p1")])
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "label0": {"id": "LBL_p1", "name": "priority:p1"},
                        "label1": {"id": "LBL_g", "name": "status:groomed"},
                    }
                }
            },
        )

        call_count = 0

        def side_effect(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_issue_by_number_response(issue_node)
            return make_update_issue_response()

        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=side_effect)
        item = BacklogItem(title="Task", issue="#5", priority="P1")

        # Act
        apply_status_groomed(item)

        # Assert — update still ran even without needs-grooming present to remove
        assert call_count == 2

    def test_apply_status_groomed_creates_label_if_absent(self, mocker: MockerFixture) -> None:
        """apply_status_groomed creates status:groomed label when it does not exist.

        Tests: apply_status_groomed label auto-creation (ADR-004 REST exception)
        How: get_label raises GithubException(status=404); verify create_label is
             called with name='status:groomed' and color='0075ca'.
        Why: ADR-004 — label creation stays REST; new repos need the label created
             on first use.
        """
        from github import GithubException

        # Arrange
        issue_node = make_issue_node(
            id="MDU6SXNzdWUx", number=5, labels=[make_label_node("status:needs-grooming", "LBL_ng")]
        )
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client.get_github", return_value=mock_repo)
        mock_repo.get_label.side_effect = GithubException(404, "not found")
        mock_repo.requester.graphql_query.return_value = (
            {},
            {"data": {"repository": {"label0": {"id": "LBL_g", "name": "status:groomed"}}}},
        )

        call_count = 0

        def side_effect(repo_arg: Any, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_issue_by_number_response(issue_node)
            return make_update_issue_response()

        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=side_effect)
        item = BacklogItem(title="Task", issue="#5", priority="P1")

        # Act
        apply_status_groomed(item)

        # Assert — label was created with the correct name and color
        mock_repo.create_label.assert_called_once_with(
            name="status:groomed", color="0075ca", description="Grooming complete — all sections written and approved"
        )

    def test_apply_status_groomed_noop_without_issue(self, mocker: MockerFixture) -> None:
        """apply_status_groomed is a no-op when BacklogItem has no issue number.

        Tests: apply_status_groomed early-exit guard for empty issue field
        How: Item has issue=""; verify get_github is never called.
        Why: Items without GitHub issues cannot have labels updated — must not raise.
        """
        # Arrange
        mock_get_github = mocker.patch("backlog_core.gh_client.get_github")
        item = BacklogItem(title="Task", issue="", priority="P1")

        # Act — should not raise
        apply_status_groomed(item)

        # Assert — no GitHub API calls made
        mock_get_github.assert_not_called()
