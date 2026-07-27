"""Tests for the generic ``filter_by_key`` query filter on ``list_items``.

Covers T-P4-QUERY: the ``filter_by_key`` parameter added to
``backlog_core.operations.list_items`` (and surfaced on the ``backlog_list``
MCP tool and the ``backlog-list`` / ``sam list`` CLI commands).

The filter is applied AFTER the existing type/topic/status filters, on the
result item dicts. Each ``key=value`` pair matches items where
``str(item.get(k)) == v``; all pairs compose with AND logic, and a key the
item does not carry returns no match (a no-op, not an error).

These tests mock ``parse_backlog`` to inject controlled ``BacklogItem``
instances, isolating the filter logic from parsing and GitHub. The conftest
``backlog_dir`` fixture redirects backlog state to a temp directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from backlog_core.models import BacklogItem, IssueStatus
from backlog_core.operations import list_items

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _items(*items: BacklogItem) -> list[BacklogItem]:
    """Build a list of BacklogItems for parse_backlog mocking."""
    return list(items)


def _titles(result: dict) -> list[str]:
    """Extract the title list from a list_items result dict."""
    items = cast("list[dict[str, str | bool]]", result["items"])
    return [str(it["title"]) for it in items]


class TestFilterByKey:
    """Core ``filter_by_key`` behaviour on ``list_items``."""

    def test_filter_by_existing_key_returns_matches(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """Items whose value for the key equals the requested value are returned."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug")
        b = BacklogItem(title="Beta", section="P1", skip=False, type_="Feature")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a, b))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(filter_by_key={"type": "Bug"})

        assert _titles(result) == ["Alpha"]

    def test_filter_by_nonexistent_key_returns_empty(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """A key absent from all items yields an empty result, not an error."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(filter_by_key={"nonexistent": "whatever"})

        assert result["items"] == []
        assert result["count"] == 0

    def test_filter_by_multiple_keys_and_logic(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """Multiple key=value pairs compose with AND logic."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug", topic="auth")
        b = BacklogItem(title="Beta", section="P1", skip=False, type_="Bug", topic="deploy")
        c = BacklogItem(title="Gamma", section="P2", skip=False, type_="Feature", topic="auth")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a, b, c))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(filter_by_key={"type": "Bug", "topic": "auth"})

        assert _titles(result) == ["Alpha"]

    def test_filter_by_key_absent_on_some_items_excludes_those(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """An item missing the requested key is excluded, not errored."""
        with_key = BacklogItem(title="WithSection", section="P1", skip=False)
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(with_key))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        # "milestone" is only present on built entries when the item has an
        # integer issue ref, so filtering on it excludes items lacking one.
        result = list_items(filter_by_key={"milestone": "v2"})

        assert result["items"] == []


class TestFilterByKeyNoRegression:
    """Existing type/topic/status filters must keep working alongside filter_by_key."""

    def test_type_filter_still_works_without_filter_by_key(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """The pre-existing type_ filter is unaffected by the new parameter."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug")
        b = BacklogItem(title="Beta", section="P1", skip=False, type_="Feature")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a, b))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="Bug")

        assert _titles(result) == ["Alpha"]

    def test_status_filter_still_works_with_filter_by_key(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """type/topic/status filters compose with filter_by_key correctly."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug", issue="#1")
        b = BacklogItem(title="Beta", section="P1", skip=False, type_="Feature", issue="#2")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a, b))
        mocker.patch(
            "backlog_core.operations.batch_fetch_statuses",
            return_value={
                1: IssueStatus(status="status:in-progress", milestone=""),
                2: IssueStatus(status="status:open", milestone=""),
            },
        )

        # status filter narrows to Alpha, then filter_by_key further narrows by type.
        result = list_items(status="status:in-progress", filter_by_key={"type": "Bug"})

        assert _titles(result) == ["Alpha"]

    def test_no_filter_by_key_returns_all_items(self, backlog_dir: Path, mocker: MockerFixture) -> None:
        """Omitting filter_by_key (None default) returns all non-skipped items."""
        a = BacklogItem(title="Alpha", section="P1", skip=False, type_="Bug")
        b = BacklogItem(title="Beta", section="P1", skip=False, type_="Feature")
        mocker.patch("backlog_core.operations.parse_backlog", return_value=_items(a, b))
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        assert sorted(_titles(result)) == ["Alpha", "Beta"]
