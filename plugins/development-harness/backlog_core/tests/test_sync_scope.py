"""Regression tests for finalization workflow correctness (Failure 2 — doc-only fix).

Failure 2 summary: finally.md documented a ``backlog_sync(flush_only=true)`` call as the
finalization step after grooming. This parameter was never implemented in the MCP tool
schema — the server's Pydantic validation silently dropped the unknown kwarg, resolving
to a full bidirectional sweep of all 321 issues instead of the expected lightweight
JSONL export (which was itself aspirational and never realized).

Path B fix (doc-only): Remove the flush_only documentation and replace with the correct
pattern — use ``backlog_pull(selector=<item_ref>)`` for per-item cache refresh, and
warn explicitly against calling the expensive ``backlog_sync()``.

These tests verify the documented contract post-fix:
- ``backlog_sync`` exposes no ``flush_only`` parameter in its MCP schema
- ``sync_items`` always performs a full sweep — no selective mode exists
- ``finally.md`` no longer references ``flush_only`` anywhere in its content
- ``pull_by_selector`` fetches only the targeted item, not all items

Reference: GitHub issue #2452.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from backlog_core.operations import pull_by_selector, sync_items
from backlog_core.server import backlog_sync

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# Path to the finalization workflow file that was corrected by #2452.
# Resolves relative to this test file: ../../.. → plugins/development-harness/
_FINALLY_MD = Path(__file__).parent.parent.parent / "skills/work-backlog-item/references/workflows/groom/finally.md"


class TestFinallyWorkflowFinalization:
    """Regression suite for Failure 2: phantom flush_only parameter (Path B doc-only fix).

    All four tests guard against re-introduction of the flush_only capability
    that was documented in finally.md but never implemented.
    """

    def test_backlog_sync_has_no_flush_only_parameter(self) -> None:
        """backlog_sync must not expose a flush_only parameter in its MCP schema.

        FastMCP builds the tool's inputSchema directly from the function's signature.
        Inspecting the signature is equivalent to inspecting the MCP schema — any
        parameter in the signature becomes a parameter in the schema, and vice versa.

        The flush_only parameter was described in finally.md as triggering a JSONL
        export, but this export was never implemented. Path B removes the documentation
        without adding an implementation. This test ensures no flush_only parameter
        is accidentally added to the function signature.
        """
        # Arrange
        sig = inspect.signature(backlog_sync)

        # Act: FastMCP injects `ctx: Context` at runtime — exclude it from the
        # user-visible parameter set, as it does not appear in the MCP schema.
        user_params = {name for name in sig.parameters if name != "ctx"}

        # Assert
        assert "flush_only" not in user_params, (
            f"backlog_sync must NOT expose a flush_only parameter. "
            f"User-facing parameters found: {sorted(user_params)}. "
            f"The flush_only capability was never implemented — do not add it."
        )

    def test_sync_items_always_sweeps_all_items(self, mocker: MockerFixture) -> None:
        """sync_items must call both helpers with the full item list on every invocation.

        When invoked with no arguments, sync_items always performs a full sweep —
        calling sync_create_missing_issues and sync_push_groomed_content with every
        item returned by parse_backlog. There is no flush_only or selective mode.

        This guards against a future refactor that might add a conditional path
        skipping the full sweep when some flag is set.
        """
        # Arrange
        fake_items = [MagicMock(), MagicMock(), MagicMock()]
        mocker.patch("backlog_core.operations.parse_backlog", return_value=fake_items)
        mock_create = mocker.patch("backlog_core.operations.sync_create_missing_issues", return_value={"created": 0})
        mock_push = mocker.patch("backlog_core.operations.sync_push_groomed_content", return_value={"pushed": 0})

        # Act
        result = sync_items()

        # Assert: both helpers called exactly once, each receiving the full item list
        mock_create.assert_called_once()
        mock_push.assert_called_once()
        assert mock_create.call_args.args[0] is fake_items, (
            "sync_create_missing_issues must receive the full items list from parse_backlog"
        )
        assert mock_push.call_args.args[0] is fake_items, (
            "sync_push_groomed_content must receive the full items list from parse_backlog"
        )
        assert "created" in result
        assert "pushed" in result

    def test_finally_md_does_not_reference_flush_only(self) -> None:
        """finally.md must not contain any reference to the phantom flush_only parameter.

        The flush_only=true documentation was removed in #2452 (Path B doc-only fix).
        This test reads the actual file from disk and fails if flush_only is found
        anywhere in the content — preventing accidental re-introduction.
        """
        # Arrange
        assert _FINALLY_MD.exists(), (
            f"finally.md not found at expected path: {_FINALLY_MD}. "
            "Check that the skills directory structure is intact."
        )

        # Act
        content = _FINALLY_MD.read_text(encoding="utf-8")

        # Assert
        assert "flush_only" not in content, (
            "finally.md must not reference 'flush_only' — this parameter was removed "
            "in #2452 because it was never implemented in the MCP schema. "
            "Any re-introduction must be accompanied by an actual implementation, "
            "which requires a separate architectural decision (not Path B)."
        )

    def test_backlog_pull_selector_refreshes_single_item(self, mocker: MockerFixture) -> None:
        """pull_by_selector must fetch only the targeted item, not all items.

        This verifies that pull_by_selector(selector="#N") issues exactly one
        pull_single_issue call for the matched issue number. It does NOT trigger
        a full sweep of all items — confirming the per-item refresh pattern
        documented in the corrected finally.md as the safe finalization step.

        The selector "#2452" exercises the issue-number path in pull_by_selector,
        which calls parse_issue_selector then pull_single_issue directly.
        """
        # Arrange
        mock_repo = MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mock_pull = mocker.patch(
            "backlog_core.operations.pull_single_issue", return_value={"file_path": "/tmp/test-2452.md"}
        )

        # Act: issue-number selector bypasses the title-lookup path
        result = pull_by_selector("#2452")

        # Assert: exactly one pull for the targeted item
        mock_pull.assert_called_once()
        call_args = mock_pull.call_args
        assert call_args.args[0] is mock_repo, "pull_single_issue must receive the github repo object from get_github()"
        assert call_args.args[1] == 2452, "pull_single_issue must receive the parsed issue number 2452"
        assert call_args.kwargs.get("diff_mode") is False, (
            "diff_mode must be False when pull_by_selector is called without diff=True"
        )
        assert result.get("file_path") is not None, "pull_by_selector must return a file_path in its result dict"
