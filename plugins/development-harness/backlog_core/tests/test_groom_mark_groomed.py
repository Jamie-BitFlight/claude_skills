"""Regression tests for the groom/mark_groomed hang bug fixed in operations.py.

Bug summary: `backlog_groom(mark_groomed=True)` with no content arguments previously
hung indefinitely because `groom_item()` unconditionally called `update_item(groomed=True)`,
which invoked `_resolve_groomed_content`, which fell through to `sys.stdin.read()` — blocking
forever in a headless MCP context.

Fix 1: `_resolve_groomed_content` now raises `ValidationError` instead of reading stdin.
Fix 2: `groom_item` only calls `update_item` when `has_input=True`; when `has_input=False`
       it assigns `result = {}` directly and proceeds to the `mark_groomed` block.

These tests are the regression guard for both fixes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from backlog_core.models import BacklogItem, ValidationError
from backlog_core.operations import _resolve_groomed_content, groom_item

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fix 1 — _resolve_groomed_content raises instead of blocking on stdin
# ---------------------------------------------------------------------------


def test_resolve_groomed_content_raises_without_input() -> None:
    """_resolve_groomed_content raises ValidationError when all inputs are None.

    Before Fix 1 this function fell through to `sys.stdin.read()`, which blocks
    indefinitely in headless MCP contexts.  The fix raises ValidationError instead.
    The call must return (by raising) without blocking — no timeout guard is needed
    because a hang would cause the test process to stall and eventually time out the
    CI runner.
    """
    # Arrange — all four content parameters are None (no content source supplied)
    # Act + Assert
    with pytest.raises(ValidationError, match="No groomed content provided"):
        _resolve_groomed_content(None, None, None, None)


# ---------------------------------------------------------------------------
# Fix 2 — groom_item does NOT call update_item when has_input=False
# ---------------------------------------------------------------------------


def test_groom_item_mark_groomed_no_content_does_not_call_update_item(mocker: MockerFixture) -> None:
    """groom_item with mark_groomed=True and no content args must NOT call update_item.

    Before Fix 2, groom_item called update_item unconditionally, which triggered the
    stdin-blocking path in _resolve_groomed_content.  The regression guard is that
    update_item is never called when has_input evaluates to False.
    """
    # Arrange
    fake_item = MagicMock(spec=BacklogItem)
    fake_item.file_path = None
    fake_item.issue = None

    mocker.patch("backlog_core.operations.parse_backlog", return_value=[fake_item])
    mocker.patch("backlog_core.operations.find_item", return_value=fake_item)
    mock_update_item = mocker.patch("backlog_core.operations.update_item")
    # mark_groomed path tries a second parse_backlog + find_item; item.file_path=None
    # and item.issue=None means neither the metadata nor GitHub label branch executes,
    # so no further mocking is required.

    # Act
    result = groom_item(selector="test-item", mark_groomed=True)

    # Assert — update_item must never be reached
    mock_update_item.assert_not_called()
    assert isinstance(result, dict)


def test_groom_item_mark_groomed_with_content_calls_update_item(mocker: MockerFixture) -> None:
    """groom_item with mark_groomed=True AND groomed_content calls update_item with groomed=True.

    When content IS supplied, has_input=True so update_item must be called.  This
    test confirms that Fix 2 did not accidentally suppress the normal write path.
    """
    # Arrange
    fake_item = MagicMock(spec=BacklogItem)
    fake_item.file_path = None
    fake_item.issue = None

    mocker.patch("backlog_core.operations.parse_backlog", return_value=[fake_item])
    mocker.patch("backlog_core.operations.find_item", return_value=fake_item)
    mock_update_item = mocker.patch("backlog_core.operations.update_item", return_value={"groomed_updated": True})

    # Act
    result = groom_item(selector="test-item", groomed_content="## Groomed\n\nSome content", mark_groomed=True)

    # Assert — update_item was called and groomed=True was passed
    mock_update_item.assert_called_once()
    call_kwargs = mock_update_item.call_args.kwargs
    assert call_kwargs.get("groomed") is True
    assert call_kwargs.get("groomed_content") == "## Groomed\n\nSome content"
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Fix 3 — mark_groomed emits warning and sets skip signal when re-lookup returns None
# ---------------------------------------------------------------------------


def test_groom_item_mark_groomed_skipped_when_item_not_found_after_reparse(mocker: MockerFixture) -> None:
    """mark_groomed=True emits warning and sets mark_groomed_skipped when re-lookup returns None.

    Before this fix, groom_item silently dropped the mark_groomed operation when
    find_item returned None after the post-write re-parse. No warning was emitted
    and no result key indicated the skip — a violation of the silent-failure-prevention rule.

    Fix 3: when fresh_item is None, emit out.warn() and set result["mark_groomed_skipped"]=True.
    """
    # Arrange — first find_item call (initial lookup) returns item, second (re-lookup) returns None
    fake_item = MagicMock(spec=BacklogItem)
    fake_item.file_path = None
    fake_item.issue = None

    find_item_call_count = {"n": 0}

    def find_item_side_effect(items: object, selector: object) -> BacklogItem | None:
        find_item_call_count["n"] += 1
        return fake_item if find_item_call_count["n"] == 1 else None

    mocker.patch("backlog_core.operations.parse_backlog", return_value=[fake_item])
    mocker.patch("backlog_core.operations.find_item", side_effect=find_item_side_effect)
    mocker.patch("backlog_core.operations.update_item", return_value={"updated": True})
    mock_update_metadata = mocker.patch("backlog_core.operations.update_item_metadata")
    mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

    out = MagicMock()

    # Act
    result = groom_item(
        selector="vanishing-item", section="Description", content="Groomed content.", output=out, mark_groomed=True
    )

    # Assert — skip is explicit, not silent
    assert result.get("mark_groomed_skipped") is True
    skip_reason = result.get("mark_groomed_skip_reason")
    assert isinstance(skip_reason, str)
    assert "vanishing-item" in skip_reason
    assert result.get("mark_groomed_applied") is not True
    # Warning must be emitted — not silent
    out.warn.assert_called()
    warn_msg = out.warn.call_args_list[0][0][0]
    assert "mark_groomed" in warn_msg
    assert "not found" in warn_msg
    # Metadata and GitHub label paths must NOT be reached
    mock_update_metadata.assert_not_called()
    mock_apply.assert_not_called()
