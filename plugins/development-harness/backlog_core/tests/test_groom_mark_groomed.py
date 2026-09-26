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

from backlog_core import operations
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogItem, Entry, Section, ValidationError
from backlog_core.operations import _apply_groomed_entries, _resolve_groomed_content, groom_item

from ._view_test_helpers import _configure_memory_view

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


def test_replace_section_without_reason_raises_backlog_error() -> None:
    """replace_section=True with no reason raises a BacklogError subclass.

    The backlog_groom MCP wrapper catches only BacklogError and returns it in
    the ``error`` field. A plain ValueError escaped the wrapper as an unhandled
    tool exception instead.
    """
    section = Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="old")])

    with pytest.raises(ValidationError, match="reason is required"):
        _apply_groomed_entries(
            section, "new", append=False, replace_section=True, reason=None, entry_id=None, added_date="2026-01-01"
        )


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
    fake_item = BacklogItem(title="test-item")
    _configure_memory_view(mocker, item=fake_item)
    mock_update_item = mocker.patch("backlog_core.operations.update_item")

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
    fake_item = BacklogItem(title="test-item")
    _configure_memory_view(mocker, item=fake_item)
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
# Live-first — mark_groomed reuses its command-scoped selection
# ---------------------------------------------------------------------------


def test_groom_item_mark_groomed_reuses_one_selection(mocker: MockerFixture) -> None:
    """mark_groomed uses the item selected once at command start."""
    fake_item = BacklogItem(title="vanishing-item")
    backend = _configure_memory_view(mocker, item=fake_item)
    mock_list = mocker.patch.object(backend, "list_work_items", side_effect=[[fake_item], []])
    mocker.patch("backlog_core.operations.update_item", return_value={"updated": True})
    mock_update_metadata = mocker.patch("backlog_core.operations.update_item_metadata")
    mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

    out = MagicMock()

    # Act
    result = groom_item(
        selector="vanishing-item", section="Description", content="Groomed content.", output=out, mark_groomed=True
    )

    assert result.get("mark_groomed_applied") is True
    mock_update_metadata.assert_called_once()
    mock_apply.assert_not_called()
    assert mock_list.call_count == 1


def test_groom_item_mark_groomed_preserves_content_in_final_storage(mocker: MockerFixture) -> None:
    """The status write accumulates on the item containing the new section."""
    backend = InMemoryBackend()
    original = BacklogItem(title="cumulative groom", reference="cumulative-groom", priority="P1")
    backend.put_work_item(original)
    mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))

    groom_item(
        "cumulative groom",
        section="Acceptance Criteria",
        content="- [ ] Final item keeps this criterion",
        mark_groomed=True,
    )

    stored = backend.get_work_item("cumulative-groom")
    section = stored.sections["acceptance_criteria"]
    assert isinstance(section, Section)
    assert section.entries[-1].content == "- [ ] Final item keeps this criterion"
    assert stored.status == "groomed"
