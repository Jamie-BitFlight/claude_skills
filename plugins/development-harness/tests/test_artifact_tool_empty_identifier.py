"""An empty ``item_id`` must be reported by the artifact tools, not escape them.

``item_id`` reaches a pydantic ``model_validator`` on ``ContentRef`` (the manifest
reference every ``artifact_*`` tool builds from it). A ``raise ValueError`` inside a
validator is re-raised by pydantic as ``pydantic.ValidationError``, which subclasses
``ValueError`` and is not a ``BacklogError`` -- so each tool's ``except BacklogError``
missed it and the refusal failed the tool call with an unhandled exception instead of
returning the documented ``error`` response.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from backlog_core.backend_types import ContentProvider
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

_TOOL_PARAMS: dict[str, dict[str, object]] = {
    "artifact_list": {"item_id": ""},
    "artifact_get": {"item_id": "", "artifact_type": "research"},
    "artifact_read": {"item_id": "", "artifact_type": "research"},
    "artifact_register": {"item_id": "", "artifact_type": "research", "artifact_id": "plan/r.md", "content": "# R"},
}


@pytest.mark.parametrize("tool_name", sorted(_TOOL_PARAMS))
async def test_empty_item_id_is_reported_as_an_error_response(tool_name: str) -> None:
    """An empty ``item_id`` names the refusal in ``error`` instead of failing the call."""
    with patch("backlog_core.server._get_artifact_provider", return_value=MagicMock(spec=ContentProvider)):
        result = await call_mcp_tool(mcp, tool_name, _TOOL_PARAMS[tool_name])

    assert "namespace" in result["error"], result
