"""Regression tests for the typed degradation-provenance fields (#3546, B5).

``list_items``/``view_item`` compute ``status_source``, ``unavailable_capabilities``,
and (list only) ``filters_evaluated_against_unavailable_data`` directly on their own
result shapes, following the ``ReconcileResult`` precedent already shipped in this
module (``models.py``), per B-critique.md §5/§2.4's ranking of Alt-1 over a universal
``Output.degradations`` side-channel.

Mirrors the fixture patterns already established in
``test_status_filter_fabrication.py`` (list) and ``test_refusal_not_item_missing.py``
(view) rather than inventing new backend stubs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core import operations
from backlog_core.github_client import MissingGitHubTokenError
from backlog_core.models import BackendUnavailableError, BacklogItem, GraphQLUnavailableError, Output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _item(issue: str, title: str = "An item") -> BacklogItem:
    """Build a minimal open backlog item carrying the given issue reference."""
    return BacklogItem(title=title, issue=issue, section="P1", status="status:in-progress")


class _BatchCapableBackend:
    """Backend stub whose batch status fetch may succeed or fail per test."""

    supports_batch_status_fetch = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return list(self._items)


class _StringIdBackend:
    """Backend stub without batch status support (e.g. beads) -- status is backend-owned."""

    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return list(self._items)


class _GitHubLikeBackend:
    """Backend stub that, unlike ``_BatchCapableBackend``, declares
    ``supports_github_extras = True`` -- the flag ``list_items()`` gates its
    (network-free) GitHub-token check on, matching the real ``GitHubBackend``.
    """

    supports_batch_status_fetch = True
    supports_github_extras = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return list(self._items)


class TestListItemsStatusSource:
    """``list_items()`` reports where its status data actually came from."""

    def test_healthy_batch_fetch_reports_live(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_BatchCapableBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        result = operations.list_items(output=Output())

        assert result["status_source"] == "live"
        assert result["unavailable_capabilities"] == []
        assert result["filters_evaluated_against_unavailable_data"] == []

    def test_refused_batch_fetch_reports_unavailable(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_BatchCapableBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        result = operations.list_items(output=Output())

        assert result["status_source"] == "unavailable"
        assert result["unavailable_capabilities"] == ["live_status"]

    def test_backend_without_batch_support_reports_cache_not_unavailable(self, mocker: MockerFixture) -> None:
        """A string-ID backend's own status field is authoritative -- not a degradation."""
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_StringIdBackend([_item("#1")])))

        result = operations.list_items(output=Output())

        assert result["status_source"] == "cache"
        assert result["unavailable_capabilities"] == []

    def test_missing_github_token_reports_cache_not_live(self, mocker: MockerFixture) -> None:
        """A skipped batch fetch (no GITHUB_TOKEN) must not be reported as 'live' (#3546,
        Codex review on PR #3577): gh_client.batch_fetch_statuses() would short-circuit to
        an empty map without ever making a live request, so list_items() must never claim
        the request succeeded. Per StatusSource's docstring, "no live fetch was attempted
        this call" is "cache", not "unavailable" -- the latter is reserved for an attempt
        that was made and failed.
        """
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_GitHubLikeBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "resolve_token", side_effect=MissingGitHubTokenError("no token configured"))
        batch_fetch_spy = mocker.patch.object(operations, "batch_fetch_statuses")

        result = operations.list_items(output=Output())

        batch_fetch_spy.assert_not_called()
        assert result["status_source"] == "cache"
        assert result["unavailable_capabilities"] == []

    def test_missing_github_token_with_status_filter_names_filter_unreliable(self, mocker: MockerFixture) -> None:
        """A skipped-for-credentials fetch is exactly as unevaluable as an
        attempted-and-failed one -- B2's fabrication-prevention guard must apply here too.
        """
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_GitHubLikeBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "resolve_token", side_effect=MissingGitHubTokenError("no token configured"))
        mocker.patch.object(operations, "batch_fetch_statuses")

        result = operations.list_items(status="in-progress", output=Output())

        assert result["filters_evaluated_against_unavailable_data"] == ["status"]

    def test_no_numeric_issue_references_reports_cache_not_live(self, mocker: MockerFixture) -> None:
        """No item on the page carries a numeric issue reference -- nothing for the
        provider to look up, live or otherwise (#3546, Codex review on PR #3577).
        Must report "cache", never "live", and must never call batch_fetch_statuses.
        """
        beads_style_item = BacklogItem(title="Beads item", issue="bd-a3f8", section="P1", status="status:in-progress")
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_GitHubLikeBackend([beads_style_item]))
        )
        batch_fetch_spy = mocker.patch.object(operations, "batch_fetch_statuses")

        result = operations.list_items(output=Output())

        batch_fetch_spy.assert_not_called()
        assert result["status_source"] == "cache"
        assert result["unavailable_capabilities"] == []

    def test_status_filter_active_under_refusal_names_itself_as_unreliable(self, mocker: MockerFixture) -> None:
        """B2's fabrication-prevention fix (silent) is also surfaced structurally here."""
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_BatchCapableBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        result = operations.list_items(status="in-progress", output=Output())

        assert result["filters_evaluated_against_unavailable_data"] == ["status"]

    def test_status_filter_absent_under_refusal_does_not_name_a_filter(self, mocker: MockerFixture) -> None:
        """No status= filter was requested, so nothing was evaluated against unavailable data."""
        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_BatchCapableBackend([_item("#1")]))
        )
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        result = operations.list_items(output=Output())

        assert result["filters_evaluated_against_unavailable_data"] == []


class _ViewBackend:
    """Backend stub exposing only what ``view_item`` reads."""

    issue_id_type = "int"
    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items


def _patch_view_backend(mocker: MockerFixture, items: list[BacklogItem]) -> None:
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_ViewBackend(items)))


class TestViewItemStatusSource:
    """``view_item()`` reports where its enrichment data actually came from."""

    def test_successful_live_enrichment_reports_live(self, mocker: MockerFixture) -> None:
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(operations, "view_enrich_from_github", return_value=True)

        result = operations.view_item("#519", output=Output())

        assert result.status_source == "live"
        assert result.unavailable_capabilities == []

    def test_attempted_and_failed_enrichment_reports_unavailable(self, mocker: MockerFixture) -> None:
        """A genuine attempt that failed -- distinct from never having tried."""
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(operations, "view_enrich_from_github", return_value=False)

        result = operations.view_item("#519", output=Output())

        assert result.status_source == "unavailable"
        assert result.unavailable_capabilities == ["live_enrichment"]

    def test_backend_unavailable_exception_reports_unavailable(self, mocker: MockerFixture) -> None:
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(
            operations, "view_enrich_from_github", side_effect=BackendUnavailableError("simulated outage")
        )

        result = operations.view_item("#519", output=Output())

        assert result.status_source == "unavailable"
        assert result.unavailable_capabilities == ["live_enrichment"]

    def test_no_live_id_to_check_reports_cache_not_unavailable(self, mocker: MockerFixture) -> None:
        """The false-positive #3546 §3.4 bug: nothing was attempted here (no issue ref,
        no refresh requested). status_source must say "cache", never "unavailable" --
        a caller asking specifically for this field must not receive the B-critique.md
        §3.4 false positive that the *prose* warning still carries (tracked separately,
        plan task B6). This is the field this test suite exists to keep honest.
        """
        item_without_issue = BacklogItem(title="No issue ref", section="P1", status="status:in-progress")
        _patch_view_backend(mocker, [item_without_issue])
        mock_enrich = mocker.patch.object(operations, "view_enrich_from_github")

        result = operations.view_item(item_without_issue.title, output=Output())

        mock_enrich.assert_not_called()
        assert result.status_source == "cache"
        assert result.unavailable_capabilities == []

    def test_refresh_requested_but_no_identifier_still_reports_cache(self, mocker: MockerFixture) -> None:
        """The precise #3546 §3.4 reproduction: refresh=True enters the live-check
        sub-block (issue_num or refresh is True), but the item carries no issue
        reference at all, so _live_lookup_id resolves to None and
        view_enrich_from_github is never called -- this is the exact branch where
        the existing "backend unreachable" prose warning is a false positive
        (tracked separately as plan task B6). status_source must still say
        "cache", not "unavailable", even though the sub-block was entered.
        """
        item_without_issue = BacklogItem(title="No issue ref", section="P1", status="status:in-progress")
        _patch_view_backend(mocker, [item_without_issue])
        mock_enrich = mocker.patch.object(operations, "view_enrich_from_github")

        result = operations.view_item(item_without_issue.title, output=Output(), refresh=True)

        mock_enrich.assert_not_called()
        assert result.status_source == "cache"
        assert result.unavailable_capabilities == []
