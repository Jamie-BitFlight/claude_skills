"""Consume published job events."""

from __future__ import annotations


def consume(event: dict[str, str | int]) -> str:
    """Format an event value.

    Returns:
        Formatted value.
    """
    return f"{event['jobId']}:{event['attempt']}"
