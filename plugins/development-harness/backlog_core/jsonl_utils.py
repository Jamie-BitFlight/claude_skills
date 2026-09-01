"""Shared JSONL parsing utilities for Claude Code session transcript handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator


def _iter_json_lines(jsonl_path: Path) -> Iterator[dict[str, Any]]:
    """Yield each well-formed JSON object in a JSONL file.

    Skips blank lines and lines that fail to parse as JSON. Handles a
    missing or unreadable file by yielding nothing.

    Args:
        jsonl_path: Path to the .jsonl file.

    Yields:
        Each line's parsed JSON object, in file order.
    """
    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue
                try:
                    yield json.loads(text)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def parse_jsonl_events(jsonl_path: Path | str, event_type: str | None = None) -> list[dict[str, Any]]:
    """Parse a JSONL file and optionally filter by event type.

    Handles missing files and malformed JSON gracefully.

    Args:
        jsonl_path: Path to the .jsonl file.
        event_type: If provided, only events matching type=event_type are returned.

    Returns:
        List of parsed event dicts. Empty list if file doesn't exist or is unreadable.
    """
    return [
        event for event in _iter_json_lines(Path(jsonl_path)) if event_type is None or event.get("type") == event_type
    ]


def find_first_event(jsonl_path: Path | str, event_type: str, subtype: str | None = None) -> dict[str, Any] | None:
    """Find the first event matching type (and optionally subtype) in a JSONL file.

    Args:
        jsonl_path: Path to the .jsonl file.
        event_type: Required event type to match.
        subtype: Optional event subtype to match.

    Returns:
        The first matching event dict, or None if not found or file is unreadable.
    """
    return next(
        (
            event
            for event in _iter_json_lines(Path(jsonl_path))
            if event.get("type") == event_type and (subtype is None or event.get("subtype") == subtype)
        ),
        None,
    )
