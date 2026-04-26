"""Session transcript reader for token usage accumulation.

Reads JSONL session files and extracts cumulative usage data from all type=result events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .jsonl_utils import parse_jsonl_events

if TYPE_CHECKING:
    from pathlib import Path


def read_session_transcript_usage(jsonl_path: Path | str) -> dict[str, Any]:
    """Read a session JSONL file and accumulate all token usage.

    Extracts all type=result events from the JSONL file and sums their usage fields:
    - input_tokens
    - output_tokens
    - cache_read_tokens
    - cache_creation_tokens
    - estimated_cost_usd

    Args:
        jsonl_path: Path to the session JSONL file.

    Returns:
        A dict with cumulative usage snapshot:
        {
            "input_tokens": <int>,
            "output_tokens": <int>,
            "cache_read_tokens": <int>,
            "cache_creation_tokens": <int>,
            "estimated_cost_usd": <float>,
            "event_count": <int>,  # Number of type=result events processed
        }

        If the file does not exist or contains no result events, returns
        a dict with all counters at 0 and event_count 0.

    Example:
        >>> path = Path("~/.claude/projects/my-project/abc123.jsonl")
        >>> usage = read_session_transcript_usage(path)
        >>> print(f"Total cost: ${usage['estimated_cost_usd']:.4f}")
    """
    snapshot = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "estimated_cost_usd": 0.0,
        "event_count": 0,
    }

    result_events = parse_jsonl_events(jsonl_path, event_type="result")
    if not result_events:
        return snapshot

    for event in result_events:
        usage = event.get("usage", {})
        snapshot["input_tokens"] += usage.get("input_tokens", 0)
        snapshot["output_tokens"] += usage.get("output_tokens", 0)
        snapshot["cache_read_tokens"] += usage.get("cache_read_tokens", 0)
        snapshot["cache_creation_tokens"] += usage.get("cache_creation_tokens", 0)
        snapshot["estimated_cost_usd"] += usage.get("estimated_cost_usd", 0.0)
        snapshot["event_count"] += 1

    return snapshot
