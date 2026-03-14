"""Tests for backlog_item_to_display_dict and _dict_to_backlog_item_fields round-trip.

Covers: _status field presence and full status round-trip for all relevant status values.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from backlog_core.models import BacklogItem

# Ensure scripts/ directory is importable (conftest adds backlog root, but backlog.py
# lives one level deeper in scripts/).
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from backlog import _dict_to_backlog_item_fields, backlog_item_to_display_dict

# ---------------------------------------------------------------------------
# backlog_item_to_display_dict — _status key presence
# ---------------------------------------------------------------------------


class TestBacklogItemToDisplayDictStatusKey:
    """backlog_item_to_display_dict includes _status for non-empty status values."""

    def test_backlog_item_to_display_dict_with_status_open_includes_status_key(self) -> None:
        # Arrange
        item = BacklogItem(status="open")

        # Act
        result = backlog_item_to_display_dict(item)

        # Assert
        assert "_status" in result
        assert result["_status"] == "open"

    def test_backlog_item_to_display_dict_with_status_in_progress_includes_status_key(self) -> None:
        # Arrange
        item = BacklogItem(status="in-progress")

        # Act
        result = backlog_item_to_display_dict(item)

        # Assert
        assert "_status" in result
        assert result["_status"] == "in-progress"

    def test_backlog_item_to_display_dict_with_status_needs_grooming_includes_status_key(self) -> None:
        # Arrange
        item = BacklogItem(status="needs-grooming")

        # Act
        result = backlog_item_to_display_dict(item)

        # Assert
        assert "_status" in result
        assert result["_status"] == "needs-grooming"

    def test_backlog_item_to_display_dict_with_empty_status_omits_status_key(self) -> None:
        # Arrange
        item = BacklogItem(status="")

        # Act
        result = backlog_item_to_display_dict(item)

        # Assert
        assert "_status" not in result


# ---------------------------------------------------------------------------
# Full round-trip: BacklogItem -> display dict -> BacklogItem fields
# ---------------------------------------------------------------------------


class TestDisplayDictRoundTripStatus:
    """Round-trip through display dict preserves status field."""

    @pytest.mark.parametrize(
        "status_value", ["open", "in-progress", "needs-grooming", "closed", "resolved", "custom-label"]
    )
    def test_roundtrip_status_preserved_for_non_empty_values(self, status_value: str) -> None:
        # Arrange
        item = BacklogItem(title="Round-trip item", status=status_value)

        # Act
        display = backlog_item_to_display_dict(item)
        fields = _dict_to_backlog_item_fields(display)
        reconstructed = BacklogItem.model_validate(fields)

        # Assert
        assert reconstructed.status == status_value

    def test_roundtrip_empty_status_preserved(self) -> None:
        # Arrange
        item = BacklogItem(title="No status item", status="")

        # Act
        display = backlog_item_to_display_dict(item)
        fields = _dict_to_backlog_item_fields(display)
        reconstructed = BacklogItem.model_validate(fields)

        # Assert
        assert reconstructed.status == ""

    def test_roundtrip_title_preserved_alongside_status(self) -> None:
        # Arrange
        item = BacklogItem(title="My Backlog Item", status="open")

        # Act
        display = backlog_item_to_display_dict(item)
        fields = _dict_to_backlog_item_fields(display)
        reconstructed = BacklogItem.model_validate(fields)

        # Assert
        assert reconstructed.title == "My Backlog Item"
        assert reconstructed.status == "open"
