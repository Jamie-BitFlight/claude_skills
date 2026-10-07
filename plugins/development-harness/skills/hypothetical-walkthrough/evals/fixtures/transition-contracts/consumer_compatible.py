"""Consume published job events with the producer's key contract."""

from __future__ import annotations


def consume(event: dict[str, str | int]) -> str:
    """Format an event value.

    Returns:
        Formatted value.
    """
    return f"{event['job_id']}:{event['attempt']}"
