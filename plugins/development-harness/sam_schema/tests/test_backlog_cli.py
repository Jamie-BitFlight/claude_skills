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
from typing import TYPE_CHECKING

from backlog_core.models import BacklogError
from typer.testing import CliRunner

from sam_schema.cli import app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()

_CLI_ENV = {"NO_COLOR": "1"}


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
