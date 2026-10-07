"""Durable domain invariants not exercised by the YAML reader/writer contracts."""

from __future__ import annotations

import pytest
from backlog_core.models import Entry
from pydantic import ValidationError as PydanticValidationError


@pytest.mark.parametrize(
    ("struck", "struck_at"), [(False, ""), (False, "2026-01-01T00:00:00Z"), (True, "2026-01-01T00:00:00Z")]
)
def test_entry_accepts_persistable_strike_states(struck: bool, struck_at: str) -> None:
    """A persisted entry may be ordinary, timestamped, or struck and timestamped."""
    assert Entry(struck=struck, struck_at=struck_at).struck is struck


def test_entry_refuses_a_struck_state_without_a_timestamp() -> None:
    """A struck entry without a timestamp is not a durable state."""
    with pytest.raises(PydanticValidationError, match="struck_at"):
        Entry(struck=True, struck_at="")
