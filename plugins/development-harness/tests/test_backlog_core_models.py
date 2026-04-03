"""Tests for backlog_core.models — Pydantic models, exceptions, and constants.

Covers: BacklogItem, Output, IssueStatus, PullRequestRef, ViewItemResult,
IssueLocalFields, exception hierarchy, and module-level constants.
"""

from __future__ import annotations

from pathlib import Path

import backlog_core.models as _bc_models
import pytest
from backlog_core.models import (
    BACKLOG_DIR,
    COMMIT_PREFIX_RE,
    DEFAULT_REPO,
    TYPE_TO_LABEL,
    BacklogConfig,
    BacklogError,
    BacklogItem,
    DuplicateItemError,
    GitHubUnavailableError,
    IssueLocalFields,
    IssueStatus,
    ItemNotFoundError,
    Output,
    PullRequestRef,
    ValidationError,
    ViewItemResult,
    resolve_repo,
)
from pydantic import ValidationError as PydanticValidationError

# ---------------------------------------------------------------------------
# BacklogItem
# ---------------------------------------------------------------------------


class TestBacklogItemDefaults:
    """BacklogItem field defaults are correct when no arguments provided."""

    def test_backlog_item_default_title_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.title == ""

    def test_backlog_item_default_description_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.description == ""

    def test_backlog_item_default_source_is_not_specified(self) -> None:
        item = BacklogItem()
        assert item.source == "Not specified"

    def test_backlog_item_default_item_type_is_feature(self) -> None:
        item = BacklogItem()
        assert item.item_type == "Feature"

    def test_backlog_item_default_skip_is_false(self) -> None:
        item = BacklogItem()
        assert item.skip is False

    def test_backlog_item_default_priority_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.priority == ""

    def test_backlog_item_default_added_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.added == ""

    def test_backlog_item_default_issue_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.issue == ""

    def test_backlog_item_default_plan_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.plan == ""

    def test_backlog_item_default_file_path_is_empty_string(self) -> None:
        item = BacklogItem()
        assert item.file_path == ""


class TestBacklogItemFieldAssignment:
    """BacklogItem accepts and stores assigned field values."""

    def test_backlog_item_stores_title(self) -> None:
        item = BacklogItem(title="My Feature")
        assert item.title == "My Feature"

    def test_backlog_item_stores_description(self) -> None:
        item = BacklogItem(description="Some description")
        assert item.description == "Some description"

    def test_backlog_item_stores_priority(self) -> None:
        item = BacklogItem(priority="P1")
        assert item.priority == "P1"

    def test_backlog_item_stores_item_type(self) -> None:
        item = BacklogItem(item_type="Bug")
        assert item.item_type == "Bug"

    def test_backlog_item_stores_issue(self) -> None:
        item = BacklogItem(issue="#42")
        assert item.issue == "#42"

    def test_backlog_item_stores_plan(self) -> None:
        item = BacklogItem(plan="plan/tasks-1-test.md")
        assert item.plan == "plan/tasks-1-test.md"

    def test_backlog_item_stores_skip_true(self) -> None:
        item = BacklogItem(skip=True)
        assert item.skip is True

    def test_backlog_item_stores_file_path(self) -> None:
        item = BacklogItem(file_path="/some/path.md")
        assert item.file_path == "/some/path.md"

    def test_backlog_item_stores_section(self) -> None:
        item = BacklogItem(section="P1")
        assert item.section == "P1"

    def test_backlog_item_stores_groomed(self) -> None:
        item = BacklogItem(groomed="2026-01-01")
        assert item.groomed == "2026-01-01"


class TestBacklogItemModelDump:
    """BacklogItem.model_dump() returns expected keys and values."""

    def test_model_dump_contains_title_key(self) -> None:
        item = BacklogItem(title="Dump test")
        result = item.model_dump()
        assert "title" in result

    def test_model_dump_title_value_matches(self) -> None:
        item = BacklogItem(title="Dump test")
        result = item.model_dump()
        assert result["title"] == "Dump test"

    def test_model_dump_contains_all_expected_keys(self) -> None:
        item = BacklogItem()
        result = item.model_dump()
        expected_keys = {"title", "description", "metadata", "sections"}
        assert expected_keys.issubset(result.keys())

    def test_model_dump_excludes_type_(self) -> None:
        item = BacklogItem(type_="bug")
        result = item.model_dump()
        assert "type_" not in result

    def test_model_dump_excludes_section(self) -> None:
        item = BacklogItem(section="P1")
        result = item.model_dump()
        assert "section" not in result

    def test_model_dump_excludes_file_path(self) -> None:
        item = BacklogItem(file_path="/some/path.md")
        result = item.model_dump()
        assert "file_path" not in result

    def test_model_dump_excludes_skip(self) -> None:
        item = BacklogItem(skip=True)
        result = item.model_dump()
        assert "skip" not in result

    def test_model_dump_excludes_raw_body(self) -> None:
        """raw_body is an excluded runtime field and must not appear in model_dump output.

        ``raw_body`` is declared with ``exclude=True`` so that legacy ``.md`` parsing
        results are not serialised to YAML.  This test guards that the exclusion holds.
        """
        item = BacklogItem()
        result = item.model_dump()
        assert "raw_body" not in result

    def test_model_dump_skip_accessible_directly(self) -> None:
        item = BacklogItem()
        assert item.skip is False


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class TestOutputInfo:
    """Output.info() appends to messages list only."""

    def test_info_appends_to_messages(self) -> None:
        out = Output()
        out.info("hello")
        assert out.messages == ["hello"]

    def test_info_does_not_append_to_warnings(self) -> None:
        out = Output()
        out.info("hello")
        assert out.warnings == []

    def test_info_does_not_append_to_errors(self) -> None:
        out = Output()
        out.info("hello")
        assert out.errors == []

    def test_info_multiple_calls_preserves_order(self) -> None:
        out = Output()
        out.info("first")
        out.info("second")
        assert out.messages == ["first", "second"]


class TestOutputWarn:
    """Output.warn() appends to warnings list only."""

    def test_warn_appends_to_warnings(self) -> None:
        out = Output()
        out.warn("attention")
        assert out.warnings == ["attention"]

    def test_warn_does_not_append_to_messages(self) -> None:
        out = Output()
        out.warn("attention")
        assert out.messages == []

    def test_warn_does_not_append_to_errors(self) -> None:
        out = Output()
        out.warn("attention")
        assert out.errors == []


class TestOutputError:
    """Output.error() appends to errors list only."""

    def test_error_appends_to_errors(self) -> None:
        out = Output()
        out.error("boom")
        assert out.errors == ["boom"]

    def test_error_does_not_append_to_messages(self) -> None:
        out = Output()
        out.error("boom")
        assert out.messages == []

    def test_error_does_not_append_to_warnings(self) -> None:
        out = Output()
        out.error("boom")
        assert out.warnings == []


class TestOutputToDict:
    """Output.to_dict() returns the same structure as model_dump()."""

    def test_to_dict_equals_model_dump(self) -> None:
        out = Output()
        out.info("msg")
        out.warn("warn")
        out.error("err")
        assert out.to_dict() == out.model_dump()

    def test_to_dict_contains_messages_key(self) -> None:
        out = Output()
        out.info("x")
        result = out.to_dict()
        assert "messages" in result

    def test_to_dict_contains_warnings_key(self) -> None:
        out = Output()
        result = out.to_dict()
        assert "warnings" in result

    def test_to_dict_contains_errors_key(self) -> None:
        out = Output()
        result = out.to_dict()
        assert "errors" in result

    def test_to_dict_empty_output_has_empty_lists(self) -> None:
        out = Output()
        result = out.to_dict()
        assert result["messages"] == []
        assert result["warnings"] == []
        assert result["errors"] == []


class TestOutputDefaultFactories:
    """Output instances have independent list instances."""

    def test_two_outputs_share_no_state(self) -> None:
        out1 = Output()
        out2 = Output()
        out1.info("only in out1")
        assert out2.messages == []


# ---------------------------------------------------------------------------
# IssueStatus
# ---------------------------------------------------------------------------


class TestIssueStatus:
    """IssueStatus construction and field defaults."""

    def test_issue_status_default_status_is_empty(self) -> None:
        status = IssueStatus()
        assert status.status == ""

    def test_issue_status_default_milestone_is_empty(self) -> None:
        status = IssueStatus()
        assert status.milestone == ""

    def test_issue_status_stores_status(self) -> None:
        status = IssueStatus(status="status:in-progress")
        assert status.status == "status:in-progress"

    def test_issue_status_stores_milestone(self) -> None:
        status = IssueStatus(milestone="v1.0")
        assert status.milestone == "v1.0"


# ---------------------------------------------------------------------------
# PullRequestRef
# ---------------------------------------------------------------------------


class TestPullRequestRef:
    """PullRequestRef requires number, title, url."""

    def test_pull_request_ref_stores_number(self) -> None:
        pr = PullRequestRef(number=42, title="Fix bug", url="https://github.com/org/repo/pull/42")
        assert pr.number == 42

    def test_pull_request_ref_stores_title(self) -> None:
        pr = PullRequestRef(number=1, title="My PR", url="https://github.com/org/repo/pull/1")
        assert pr.title == "My PR"

    def test_pull_request_ref_stores_url(self) -> None:
        url = "https://github.com/org/repo/pull/5"
        pr = PullRequestRef(number=5, title="PR", url=url)
        assert pr.url == url

    def test_pull_request_ref_requires_number(self) -> None:
        with pytest.raises(PydanticValidationError, match="number"):
            PullRequestRef.model_validate({"title": "No number", "url": "https://example.com"})


# ---------------------------------------------------------------------------
# ViewItemResult
# ---------------------------------------------------------------------------


class TestViewItemResult:
    """ViewItemResult field defaults and construction."""

    def test_view_item_result_default_title_empty(self) -> None:
        result = ViewItemResult()
        assert result.title == ""

    def test_view_item_result_default_groomed_empty(self) -> None:
        result = ViewItemResult()
        assert result.groomed == ""

    def test_view_item_result_default_number_none(self) -> None:
        result = ViewItemResult()
        assert result.number is None

    def test_view_item_result_default_labels_empty_list(self) -> None:
        result = ViewItemResult()
        assert result.labels == []

    def test_view_item_result_stores_title(self) -> None:
        result = ViewItemResult(title="My Item")
        assert result.title == "My Item"

    def test_view_item_result_stores_number(self) -> None:
        result = ViewItemResult(number=99)
        assert result.number == 99

    def test_view_item_result_stores_labels(self) -> None:
        result = ViewItemResult(labels=["type:feature", "status:open"])
        assert result.labels == ["type:feature", "status:open"]

    def test_view_item_result_stores_groomed_date(self) -> None:
        result = ViewItemResult(groomed="2026-03-15")
        assert result.groomed == "2026-03-15"


# ---------------------------------------------------------------------------
# IssueLocalFields
# ---------------------------------------------------------------------------


class TestIssueLocalFields:
    """IssueLocalFields construction and field defaults."""

    def test_issue_local_fields_default_title_empty(self) -> None:
        fields = IssueLocalFields()
        assert fields.title == ""

    def test_issue_local_fields_default_priority_is_p1(self) -> None:
        fields = IssueLocalFields()
        assert fields.priority == "P1"

    def test_issue_local_fields_default_item_type_is_feature(self) -> None:
        fields = IssueLocalFields()
        assert fields.item_type == "Feature"

    def test_issue_local_fields_default_status_is_open(self) -> None:
        fields = IssueLocalFields()
        assert fields.status == "open"

    def test_issue_local_fields_stores_title(self) -> None:
        fields = IssueLocalFields(title="Imported issue")
        assert fields.title == "Imported issue"

    def test_issue_local_fields_stores_priority(self) -> None:
        fields = IssueLocalFields(priority="P0")
        assert fields.priority == "P0"

    def test_issue_local_fields_stores_milestone(self) -> None:
        fields = IssueLocalFields(milestone="v2.0")
        assert fields.milestone == "v2.0"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestBacklogErrorIsBase:
    """BacklogError is the base for all backlog exceptions."""

    def test_backlog_error_is_exception(self) -> None:
        assert issubclass(BacklogError, Exception)

    def test_item_not_found_error_inherits_from_backlog_error(self) -> None:
        assert issubclass(ItemNotFoundError, BacklogError)

    def test_duplicate_item_error_inherits_from_backlog_error(self) -> None:
        assert issubclass(DuplicateItemError, BacklogError)

    def test_github_unavailable_error_inherits_from_backlog_error(self) -> None:
        assert issubclass(GitHubUnavailableError, BacklogError)

    def test_validation_error_inherits_from_backlog_error(self) -> None:
        assert issubclass(ValidationError, BacklogError)


class TestItemNotFoundError:
    """ItemNotFoundError stores selector and formats message."""

    def test_item_not_found_error_stores_selector(self) -> None:
        err = ItemNotFoundError("my-item")
        assert err.selector == "my-item"

    def test_item_not_found_error_message_contains_selector(self) -> None:
        err = ItemNotFoundError("my-item")
        assert "my-item" in str(err)

    def test_item_not_found_error_message_format(self) -> None:
        err = ItemNotFoundError("test-selector")
        assert str(err) == "No item found for: test-selector"

    def test_item_not_found_error_is_raised_as_backlog_error(self) -> None:
        with pytest.raises(BacklogError):
            raise ItemNotFoundError("x")

    @pytest.mark.parametrize("selector", ["", "abc", "123", "my-feature-item", "P1"])
    def test_item_not_found_error_selector_stored_for_various_inputs(self, selector: str) -> None:
        err = ItemNotFoundError(selector)
        assert err.selector == selector


class TestDuplicateItemError:
    """DuplicateItemError formats message with titles and percentages."""

    def test_duplicate_item_error_stores_duplicates(self) -> None:
        dupes = [("My Feature", 0.95, "/path/to/file.md")]
        err = DuplicateItemError(dupes)
        assert err.duplicates == dupes

    def test_duplicate_item_error_message_contains_title(self) -> None:
        dupes = [("My Feature", 0.95, "/path.md")]
        err = DuplicateItemError(dupes)
        assert "My Feature" in str(err)

    def test_duplicate_item_error_message_contains_percentage(self) -> None:
        dupes = [("My Feature", 0.95, "/path.md")]
        err = DuplicateItemError(dupes)
        assert "95%" in str(err)

    def test_duplicate_item_error_message_format_single(self) -> None:
        dupes = [("Alpha", 0.80, "/alpha.md")]
        err = DuplicateItemError(dupes)
        assert str(err) == 'Similar backlog items found: "Alpha" (80%)'

    def test_duplicate_item_error_message_format_multiple(self) -> None:
        dupes = [("Alpha", 0.80, "/a.md"), ("Beta", 1.0, "/b.md")]
        err = DuplicateItemError(dupes)
        msg = str(err)
        assert "Alpha" in msg
        assert "Beta" in msg
        assert "80%" in msg
        assert "100%" in msg

    def test_duplicate_item_error_is_raised_as_backlog_error(self) -> None:
        with pytest.raises(BacklogError):
            raise DuplicateItemError([("X", 1.0, "/x.md")])

    @pytest.mark.parametrize(
        ("title", "ratio", "expected_pct"),
        [("A", 1.0, "100%"), ("B", 0.90, "90%"), ("C", 0.85, "85%"), ("D", 0.80, "80%")],
    )
    def test_duplicate_item_error_percentage_rounding(self, title: str, ratio: float, expected_pct: str) -> None:
        err = DuplicateItemError([(title, ratio, "/path.md")])
        assert expected_pct in str(err)


class TestGitHubUnavailableError:
    """GitHubUnavailableError inherits from BacklogError."""

    def test_github_unavailable_error_can_be_raised(self) -> None:
        with pytest.raises(GitHubUnavailableError):
            raise GitHubUnavailableError("no token")

    def test_github_unavailable_error_caught_as_backlog_error(self) -> None:
        with pytest.raises(BacklogError):
            raise GitHubUnavailableError("no token")

    def test_github_unavailable_error_message_preserved(self) -> None:
        err = GitHubUnavailableError("connection refused")
        assert "connection refused" in str(err)


class TestValidationError:
    """ValidationError inherits from BacklogError."""

    def test_validation_error_can_be_raised(self) -> None:
        with pytest.raises(ValidationError):
            raise ValidationError("bad input")

    def test_validation_error_caught_as_backlog_error(self) -> None:
        with pytest.raises(BacklogError):
            raise ValidationError("bad input")

    def test_validation_error_message_preserved(self) -> None:
        err = ValidationError("field X is required")
        assert "field X is required" in str(err)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Module-level constants have correct types and values."""

    def test_backlog_dir_is_path_instance(self) -> None:
        assert isinstance(BACKLOG_DIR, Path)

    def test_default_repo_is_string(self) -> None:
        assert isinstance(DEFAULT_REPO, str)

    def test_default_repo_contains_slash(self) -> None:
        """DEFAULT_REPO is empty before init(); discover_repo() resolves it."""
        from backlog_core.models import discover_repo

        discover_repo.cache_clear()
        slug = discover_repo()
        assert "/" in slug

    def test_type_to_label_is_dict(self) -> None:
        assert isinstance(TYPE_TO_LABEL, dict)

    @pytest.mark.parametrize(
        ("key", "expected_label"),
        [
            ("feature", "type:feature"),
            ("bug", "type:bug"),
            ("refactor", "type:refactor"),
            ("docs", "type:docs"),
            ("chore", "type:chore"),
        ],
    )
    def test_type_to_label_maps_correctly(self, key: str, expected_label: str) -> None:
        assert TYPE_TO_LABEL[key] == expected_label

    def test_type_to_label_has_five_entries(self) -> None:
        assert len(TYPE_TO_LABEL) == 5


class TestCommitPrefixRegex:
    """COMMIT_PREFIX_RE strips conventional-commit prefixes."""

    @pytest.mark.parametrize("prefix", ["feat", "fix", "refactor", "docs", "chore", "perf", "test", "ci"])
    def test_commit_prefix_re_matches_known_prefix(self, prefix: str) -> None:
        text = f"{prefix}: My Title"
        assert COMMIT_PREFIX_RE.match(text) is not None

    @pytest.mark.parametrize("prefix", ["feat", "fix", "refactor", "docs", "chore", "perf", "test", "ci"])
    def test_commit_prefix_re_strips_prefix_leaving_title(self, prefix: str) -> None:
        text = f"{prefix}: My Title"
        result = COMMIT_PREFIX_RE.sub("", text)
        assert result == "My Title"

    def test_commit_prefix_re_case_insensitive_upper(self) -> None:
        assert COMMIT_PREFIX_RE.match("FEAT: Something") is not None

    def test_commit_prefix_re_case_insensitive_mixed(self) -> None:
        assert COMMIT_PREFIX_RE.match("Fix: Something") is not None

    def test_commit_prefix_re_no_match_on_plain_title(self) -> None:
        assert COMMIT_PREFIX_RE.match("My plain title") is None

    def test_commit_prefix_re_no_match_on_unknown_prefix(self) -> None:
        assert COMMIT_PREFIX_RE.match("wip: My Title") is None

    def test_commit_prefix_re_strips_trailing_space(self) -> None:
        result = COMMIT_PREFIX_RE.sub("", "feat: Title With Spaces")
        assert result == "Title With Spaces"


# ---------------------------------------------------------------------------
# resolve_repo
# ---------------------------------------------------------------------------


class TestResolveRepo:
    """Behavioural tests for :func:`~backlog_core.models.resolve_repo`."""

    def test_resolve_repo_returns_default_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string falls back to the configured default_repo."""
        existing = _bc_models._config
        monkeypatch.setattr(
            _bc_models,
            "_config",
            BacklogConfig(
                repo_root=existing.repo_root if existing is not None else _bc_models._resolve_repo_root(),
                backlog_dir=existing.backlog_dir
                if existing is not None
                else _bc_models._dh_paths.backlog_dir(_bc_models._resolve_repo_root()),
                default_repo="owner/default",
            ),
        )
        assert resolve_repo("") == "owner/default"

    def test_resolve_repo_returns_input_when_non_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-empty slug is returned unchanged regardless of DEFAULT_REPO."""
        existing = _bc_models._config
        monkeypatch.setattr(
            _bc_models,
            "_config",
            BacklogConfig(
                repo_root=existing.repo_root if existing is not None else _bc_models._resolve_repo_root(),
                backlog_dir=existing.backlog_dir
                if existing is not None
                else _bc_models._dh_paths.backlog_dir(_bc_models._resolve_repo_root()),
                default_repo="owner/default",
            ),
        )
        assert resolve_repo("owner/custom") == "owner/custom"
