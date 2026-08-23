"""UTC timestamp helper shared by parsing.py and entry_blocks.py.

Extracted to break a module-scope import cycle: entry_blocks.py needs
``now_iso`` for wrapping entry timestamps, and parsing.py needs
``find_entry_spans``/``_entry_from_span``/``_deduplicate_timestamps`` from
entry_blocks.py to parse entry blocks. Two modules importing each other at
module scope is a cycle regardless of direction, so the shared symbol lives
here instead — a module with no imports from other backlog_core modules.
"""

from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["now_iso"]


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string with microsecond precision.

    Microsecond precision ensures uniqueness across rapid successive calls,
    preventing entry id collisions in batch groom operations.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
