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
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactType, ContentKind, ContentRecord, ContentRef
from backlog_core.server import mcp
from fastmcp.exceptions import ToolError

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


@pytest.mark.parametrize("tool_name", ["artifact_get", "artifact_list", "artifact_read"])
async def test_unknown_artifact_type_is_reported_as_an_error_response(tool_name: str) -> None:
    """Every string artifact-type input fails the MCP call as ``ToolError``."""
    with (
        patch("backlog_core.server._get_artifact_provider", return_value=MagicMock(spec=ContentProvider)),
        pytest.raises(ToolError, match="Unknown artifact type"),
    ):
        await call_mcp_tool(mcp, tool_name, {"item_id": 42, "artifact_type": "not-a-type"})


async def test_empty_artifact_id_in_the_manifest_is_reported_as_an_error_response() -> None:
    """The content reference is the same boundary one model deeper, and refuses the same way.

    ``artifact_content_reference`` builds a second ``ContentRef`` from a manifest entry, whose
    ``artifact_id`` becomes the content name. An entry stored with an empty one reaches
    ``artifact_read`` only here -- past the manifest reference ``item_id`` is checked against.
    """
    manifest = ArtifactManifest(
        issue_number=42, artifacts=[ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="")]
    )
    provider = MagicMock(spec=ContentProvider)
    provider.get_content.return_value = ContentRecord(
        reference=ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="42", name="manifest"),
        content=manifest.model_dump_json(),
        revision="r1",
    )

    with patch("backlog_core.server._get_artifact_provider", return_value=provider):
        result = await call_mcp_tool(mcp, "artifact_read", {"item_id": 42, "artifact_type": "research"})

    assert "content name must not be empty" in result["error"], result
