"""Shared utilities for SAM backend implementations."""

from __future__ import annotations

from datetime import UTC, datetime


def _now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(tz=UTC).isoformat()
