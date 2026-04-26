"""Shared JSONL parsing utilities for Claude Code session transcript handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_jsonl_events(jsonl_path: Path | str, event_type: str | None = None) -> list[dict[str, Any]]:
    """Parse a JSONL file and optionally filter by event type.

    Handles missing files and malformed JSON gracefully.

    Args:
        jsonl_path: Path to the .jsonl file.
        event_type: If provided, only events matching type=event_type are returned.

    Returns:
        List of parsed event dicts. Empty list if file doesn't exist or is unreadable.
    """
    jsonl_path = Path(jsonl_path)
    events: list[dict[str, Any]] = []

    if not jsonl_path.exists():
        return events

    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue

                try:
                    event = json.loads(text)
                except json.JSONDecodeError:
                    continue

                if event_type is None or event.get("type") == event_type:
                    events.append(event)

    except OSError:
        pass

    return events


def find_first_event(jsonl_path: Path | str, event_type: str, subtype: str | None = None) -> dict[str, Any] | None:
    """Find the first event matching type (and optionally subtype) in a JSONL file.

    Args:
        jsonl_path: Path to the .jsonl file.
        event_type: Required event type to match.
        subtype: Optional event subtype to match.

    Returns:
        The first matching event dict, or None if not found or file is unreadable.
    """
    jsonl_path = Path(jsonl_path)

    if not jsonl_path.exists():
        return None

    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                text = line.strip()
                if not text:
                    continue

                try:
                    event = json.loads(text)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == event_type and (subtype is None or event.get("subtype") == subtype):
                    return event

    except OSError:
        pass

    return None
