"""Regression coverage for FastMCP response serialization."""

from __future__ import annotations

import warnings
from typing import get_type_hints

from pydantic import TypeAdapter

from backlog_core.server import _respond, backlog_list
from backlog_core.tool_responses import BacklogListResponse


def test_dumped_response_matches_tool_return_annotation_without_warnings() -> None:
    """FastMCP must not serialize a dumped dict as a Pydantic model."""
    payload = _respond(BacklogListResponse, {"items": [], "count": 0})
    return_type = get_type_hints(backlog_list)["return"]

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        serialized = TypeAdapter(return_type).dump_python(payload)

    assert serialized["items"] == []
    assert serialized["count"] == 0
