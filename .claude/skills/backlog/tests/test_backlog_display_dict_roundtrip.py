"""Tests for backlog_item_to_display_dict and _dict_to_backlog_item_fields round-trip.

Covers: _status field presence and full status round-trip for all relevant status values.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from backlog_core.models import BacklogItem

# Load backlog.py via importlib — the .claude/ path prefix breaks normal import resolution.
_SCRIPT = Path(__file__).parent.parent / "scripts" / "backlog.py"
_spec = importlib.util.spec_from_file_location("backlog", _SCRIPT)
assert _spec is not None, f"Cannot find spec for {_SCRIPT}"
assert _spec.loader is not None, f"Cannot find loader for {_SCRIPT}"
if "backlog" not in sys.modules:
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["backlog"] = _mod
    _spec.loader.exec_module(_mod)

from backlog import _dict_to_backlog_item_fields, backlog_item_to_display_dict  # ty: ignore[unresolved-import]

# ---------------------------------------------------------------------------
# backlog_item_to_display_dict — _status key presence
# ---------------------------------------------------------------------------


class TestBacklogItemToDisplayDictStatusKey:
    """backlog_item_to_display_dict includes _status for non-empty status values."""

    @pytest.mark.parametrize("status_value", ["open", "in-progress", "needs-grooming"])
    def test_backlog_item_to_display_dict_with_non_empty_status_includes_status_key(self, status_value: str) -> None:
        # Arrange
        item = BacklogItem(status=status_value)

        # Act
        result = backlog_item_to_display_dict(item)

        # Assert
        assert "_status" in result
        assert result["_status"] == status_value

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
