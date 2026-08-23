"""The artifact tools must advertise their value domain and reject anything outside it (#3162).

``artifact_register`` declared ``artifact_type`` and ``status`` as bare strings, so the
published schema named no allowed values and a calling agent had nothing to check its
literal against. The invalid literal then raised inside the handler, where a broad
``except (ValueError, KeyError)`` turned it into a success envelope carrying an ``error``
key — an agent that does not inspect the payload continues as though its artifact was
stored. These tests pin both halves: the schema advertises the enums, and an invalid
literal produces a genuine error response rather than a successful one.

The contract matches the one already documented for ``sam_schema/server.py``: handlers let
exceptions propagate and FastMCP converts them into ``isError=true``.
"""

from __future__ import annotations

from typing import Any, Final

import pytest
from backlog_core.models import ArtifactStatus, ArtifactType
from backlog_core.server import mcp
from fastmcp.exceptions import ToolError

from tests.helpers import call_mcp_tool

_VALID_REGISTER_ARGS: Final = {
    "item_id": 42,
    "artifact_type": "T0-baseline",
    "artifact_id": "T0-baseline-x",
    "content": "# baseline",
}


async def _register_schema() -> dict[str, Any]:
    """Return the published input schema of ``artifact_register``.

    Returns:
        The JSON Schema an MCP client receives for the tool's parameters.
    """
    tools = await mcp.list_tools()
    return next(tool.parameters for tool in tools if tool.name == "artifact_register")


def _advertised_enum(schema: dict[str, Any], property_name: str) -> set[str]:
    """Return the enum values a schema publishes for one property.

    Pydantic emits an enum-typed field either inline or as a ``$ref`` into ``$defs``,
    optionally wrapped in ``allOf`` when the field also carries a default. All three shapes
    are equivalent to a client, so all three are resolved here.

    Args:
        schema: The tool's full input schema.
        property_name: Name of the parameter to inspect.

    Returns:
        The advertised values, or an empty set when the property advertises none.
    """
    fragment: dict[str, Any] = schema["properties"][property_name]
    candidates: list[dict[str, Any]] = [fragment, *fragment.get("allOf", []), *fragment.get("anyOf", [])]
    for candidate in candidates:
        if "enum" in candidate:
            return set(candidate["enum"])
        ref = candidate.get("$ref")
        if ref:
            definition = schema.get("$defs", {}).get(ref.rsplit("/", 1)[-1], {})
            if "enum" in definition:
                return set(definition["enum"])
    return set()


async def test_artifact_register_schema_advertises_the_artifact_type_enum() -> None:
    """The schema must name every valid artifact type, not just describe them in prose."""
    schema = await _register_schema()

    assert _advertised_enum(schema, "artifact_type") == {member.value for member in ArtifactType}, (
        "artifact_type advertises no enum, so a calling agent has no machine-readable list "
        f"of allowed values to check its literal against: {schema['properties']['artifact_type']!r}"
    )


async def test_artifact_register_schema_advertises_the_artifact_status_enum() -> None:
    """The schema must name every valid lifecycle status."""
    schema = await _register_schema()

    assert _advertised_enum(schema, "status") == {member.value for member in ArtifactStatus}, (
        f"status advertises no enum, so 'complete' reads as acceptable to an author: {schema['properties']['status']!r}"
    )


@pytest.mark.parametrize("invalid_status", ["complete", "done", "COMPLETE"])
async def test_artifact_register_rejects_a_status_outside_the_enum(invalid_status: str) -> None:
    """An invalid status must produce an error response, not a success envelope.

    ``status="complete"`` was instructed across eight shipped agent files. Each of those
    registrations reported success and stored nothing.
    """
    with pytest.raises(ToolError):
        await call_mcp_tool(mcp, "artifact_register", {**_VALID_REGISTER_ARGS, "status": invalid_status})


async def test_artifact_register_rejects_an_artifact_type_outside_the_enum() -> None:
    """An invalid artifact type must produce an error response, not a success envelope."""
    with pytest.raises(ToolError):
        await call_mcp_tool(mcp, "artifact_register", {**_VALID_REGISTER_ARGS, "artifact_type": "not-a-real-type"})


async def test_artifact_read_raises_rather_than_returning_an_error_envelope() -> None:
    """An unknown artifact type on a read must surface as a failed call.

    A read that returns ``{"error": ...}`` inside a successful response is indistinguishable
    from a legitimately absent artifact to an agent that only checks whether the call
    succeeded.
    """
    with pytest.raises(ToolError):
        await call_mcp_tool(mcp, "artifact_read", {"item_id": 42, "artifact_type": "not-a-real-type"})
