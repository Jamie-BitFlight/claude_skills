"""Tests for the ``sam backlog`` command group's error contract and sync fallback.

Tests: (1) ``backlog add`` emits a parseable JSON error instead of letting an
operation-layer exception escape uncaught, and (2) the ``backlog sync``
subprocess fallback invokes a command that actually exists.
How: Invoke the grouped Typer app via ``CliRunner`` with the ``backlog_core``
operations layer mocked, so no real backend (GitHub, sqlite) is touched.
Why: Every ``sam`` CLI invocation is consumed by an agent parsing compact
JSON from stdout (see plugins/development-harness/AGENTS.md "CLI and script
output"). Both defects verified here previously produced either a raw
traceback (add) or a deterministic "command not found" failure (sync
fallback) instead of the documented JSON contract.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from backlog_core import operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogError, BacklogItem, BacklogItemMetadata
from typer.testing import CliRunner

from sam_schema.cli import app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()

_CLI_ENV = {"NO_COLOR": "1"}

_DUPLICATE_DESCRIPTION = (
    "Sync engine misclassifies transient network errors as non-retryable, causing sync to abort instead of retrying."
)


class TestBacklogAddErrorContract:
    """``backlog add`` keeps operation-layer failures JSON-parseable."""

    def test_duplicate_item_rejection_emits_json_error_and_exits_nonzero(self, mocker: MockerFixture) -> None:
        """A ``BacklogError`` raised by ``add_item`` becomes a JSON error, not a traceback.

        Tests: The literal PR review regression -- a duplicate-title rejection
        (or any other operation-layer validation failure) previously escaped
        ``add()`` uncaught, so the caller received a traceback on stderr and
        nothing parseable on stdout.
        How: Mock ``operations.add_item`` to raise ``BacklogError``, as the
        real duplicate-detection path does.
        Why: Agents consuming this CLI must always get parseable JSON, even
        on failure.
        """
        mocker.patch(
            "sam_schema.backlog.operations.add_item",
            side_effect=BacklogError('Similar backlog items found: "dup" (100%)'),
        )

        result = runner.invoke(app, ["backlog", "add", "--title", "dup", "--priority", "P1"], env=_CLI_ENV)

        assert result.exit_code == 1
        assert json.loads(result.stdout) == {"error": 'Similar backlog items found: "dup" (100%)'}
        assert result.stderr == ""

    def test_successful_add_still_emits_the_operation_result(self, mocker: MockerFixture) -> None:
        """A successful ``add_item`` call still reaches stdout unchanged.

        Tests: Regression guard -- the new ``try``/``except`` must not affect
        the pre-existing success path.
        How: Mock ``operations.add_item`` to return a normal result mapping.
        Why: ``add`` is the most-used backlog mutation; a success-path
        regression would break routine item creation, not just error handling.
        """
        mocker.patch(
            "sam_schema.backlog.operations.add_item",
            return_value={"title": "new item", "priority": "P1", "item_ref": "#123"},
        )

        result = runner.invoke(app, ["backlog", "add", "--title", "new item", "--priority", "P1"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        assert json.loads(result.stdout) == {"title": "new item", "priority": "P1", "item_ref": "#123"}


class TestBacklogViewRefreshForwarding:
    """``backlog view`` forwards the ``--refresh`` flag to ``operations.view_item``."""

    def test_refresh_flag_forwards_true(self, mocker: MockerFixture) -> None:
        """``--refresh`` forwards ``refresh=True`` into ``operations.view_item``."""
        mock_view = mocker.patch(
            "sam_schema.backlog.operations.view_item", return_value={"title": "Item", "issue": "#42"}
        )

        result = runner.invoke(app, ["backlog", "view", "--selector", "#42", "--refresh"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        assert mock_view.call_args.kwargs["refresh"] is True

    def test_no_refresh_flag_forwards_false(self, mocker: MockerFixture) -> None:
        """Omitting ``--refresh`` forwards ``refresh=False`` into ``operations.view_item``."""
        mock_view = mocker.patch(
            "sam_schema.backlog.operations.view_item", return_value={"title": "Item", "issue": "#42"}
        )

        result = runner.invoke(app, ["backlog", "view", "--selector", "#42"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        assert mock_view.call_args.kwargs["refresh"] is False


class TestBacklogListRefreshForwarding:
    """``backlog list`` forwards the ``--refresh`` flag to ``operations.list_items``."""

    def test_refresh_flag_forwards_true(self, mocker: MockerFixture) -> None:
        """``--refresh`` forwards ``refresh=True`` into ``operations.list_items``."""
        mock_list = mocker.patch("sam_schema.backlog.operations.list_items", return_value={"items": []})

        result = runner.invoke(app, ["backlog", "list", "--refresh"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        assert mock_list.call_args.kwargs["refresh"] is True


class TestBacklogSyncFallback:
    """The ``backlog sync`` fallback invokes a command that actually exists."""

    def test_fallback_emits_error_json_not_subprocess(self, mocker: MockerFixture) -> None:
        """The fallback emits structured error JSON directly, no subprocess.

        After removing the recursive self-invocation, the fallback emits
        ``{\"error\": ..., \"synced\": False, \"fallback\": False}`` rather than
        spawning a child process.
        """
        mocker.patch("sam_schema.backlog.operations.sync_items", side_effect=BacklogError("GITHUB_TOKEN not set"))

        result = runner.invoke(app, ["backlog", "sync", "--repo", "owner/name"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["synced"] is False
        assert payload["fallback"] is False
        assert "GITHUB_TOKEN not set" in payload["error"]

    def test_fallback_sync_error_written_to_stderr(self, mocker: MockerFixture) -> None:
        """A failing sync prints a warning to stderr and emits error JSON to stdout.

        Tests: End-to-end fallback path after removing recursive subprocess.
        """
        mocker.patch("sam_schema.backlog.operations.sync_items", side_effect=BacklogError("GITHUB_TOKEN not set"))

        result = runner.invoke(app, ["backlog", "sync", "--repo", "owner/name", "--dry-run"], env=_CLI_ENV)

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["synced"] is False
        assert "dry_run" not in payload


class TestBacklogListCliSearch:
    """``backlog list --search`` matches the MCP ``list_items(search=...)`` path (AC4/AC7/DO-7).

    Both paths run against the same real (in-memory) backend and configured
    query -- this is a cross-interface parity test, not two mocks asserting
    against each other.
    """

    def test_cli_search_matches_operations_search_result(self) -> None:
        backend = InMemoryBackend()
        set_config(BacklogConfig(backend=backend))
        try:
            backend.put_work_item(BacklogItem(title="Sync engine retry handling", section="P1", skip=False))
            backend.put_work_item(BacklogItem(title="Unrelated documentation cleanup", section="P2", skip=False))

            cli_result = runner.invoke(app, ["backlog", "list", "--search", "retry"], env=_CLI_ENV)
            unfiltered = operations.list_items(search=None)
            filtered = operations.list_items(search="retry")
        finally:
            reset_config()

        assert cli_result.exit_code == 0, cli_result.stderr
        filtered_items = cast("list[dict[str, str | bool]]", filtered["items"])
        unfiltered_items = cast("list[dict[str, str | bool]]", unfiltered["items"])
        cli_titles = {item["title"] for item in json.loads(cli_result.stdout)["items"]}
        filtered_titles = {item["title"] for item in filtered_items}

        assert cli_titles == filtered_titles == {"Sync engine retry handling"}
        assert 0 < len(cli_titles) < len(unfiltered_items)


class TestBacklogAddCliContentDuplicateEndToEnd:
    """``backlog add`` surfaces a content duplicate end-to-end, not only via ``list --search`` (AC4).

    ``list --search`` parity alone does not prove ``add`` itself reports a
    duplicate result to the caller -- this test exercises the ``add`` command
    directly against a corpus containing a known content duplicate.
    """

    def test_add_reports_duplicate_found_for_content_overlapping_item(self) -> None:
        backend = InMemoryBackend()
        set_config(BacklogConfig(backend=backend))
        try:
            backend.put_work_item(
                BacklogItem(
                    title="Sync engine mishandles retryable network errors",
                    description=_DUPLICATE_DESCRIPTION,
                    metadata=BacklogItemMetadata(
                        source="test", added="2026-01-01", priority="P1", status="open", issue="", topic="sync-retry"
                    ),
                )
            )

            result = runner.invoke(
                app,
                [
                    "backlog",
                    "add",
                    "--title",
                    "Retryable network error handling in sync",
                    "--description",
                    _DUPLICATE_DESCRIPTION,
                    "--priority",
                    "P1",
                ],
                env=_CLI_ENV,
            )
        finally:
            reset_config()

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert "Similar backlog items found" in payload["error"]
        assert "Sync engine mishandles retryable network errors" in payload["error"]
