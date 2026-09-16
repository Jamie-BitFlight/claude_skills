"""Wire-level regression tests for #3546 B5's typed degradation-provenance fields.

Proves ``status_source``/``unavailable_capabilities``/
``filters_evaluated_against_unavailable_data`` actually reach the MCP wire on
both ``backlog_list`` and ``backlog_view`` -- not silently dropped by
``_respond``'s ``model_validate(...).model_dump(...)`` chain, whose default
``extra='ignore'`` is exactly the failure mode B-critique.md §2.1/§2.2 proved
for the rejected ``Output.degradations`` side-channel design (nine response
models, including ``BacklogViewResponse``, do not inherit ``Output`` and would
silently drop an undeclared key). ``BacklogViewResponse`` is covered
explicitly here since it is the model the critique proved was missed.

Two layers:
  1. Direct model round-trip proofs -- ``cls.model_validate(payload).model_dump(...)``,
     the exact chain ``_respond`` (server.py) performs -- the sharpest test of the
     defect class, independent of any operations-layer wiring.
  2. Full MCP-transport round trips via ``Client(mcp)``, covering both of
     ``backlog_view``'s response-building paths (the default ``summary=True``
     compact manifest via ``_build_compact_manifest``, and the
     ``summary=False`` full response via ``result.model_dump()``) -- the
     compact-manifest path builds its payload dict from scratch and would
     silently drop any field not explicitly listed there, the same failure
     mode at a different call site.
"""

from __future__ import annotations

from unittest.mock import patch

from backlog_core.models import ViewItemResult
from backlog_core.server import mcp
from backlog_core.tool_responses import BacklogListResponse, BacklogViewResponse

from tests.helpers import call_mcp_tool


async def _call(tool_name: str, params: dict | None = None) -> dict:
    return await call_mcp_tool(mcp, tool_name, params)


class TestRespondDoesNotDropStatusSourceFields:
    """Direct proof that ``_respond`` preserves the new fields (B-critique.md §2.2)."""

    def test_backlog_list_response_keeps_status_source_fields(self) -> None:
        payload = {
            "items": [],
            "count": 0,
            "status_source": "unavailable",
            "unavailable_capabilities": ["live_status"],
            "filters_evaluated_against_unavailable_data": ["status"],
        }

        wire = BacklogListResponse.model_validate(payload).model_dump()

        assert wire["status_source"] == "unavailable"
        assert wire["unavailable_capabilities"] == ["live_status"]
        assert wire["filters_evaluated_against_unavailable_data"] == ["status"]

    def test_backlog_view_response_keeps_status_source_fields(self) -> None:
        """The model the B-critique.md §2.1 proof found missed by the rejected design."""
        payload = {"title": "An item", "status_source": "unavailable", "unavailable_capabilities": ["live_enrichment"]}

        wire = BacklogViewResponse.model_validate(payload).model_dump(exclude_none=False, exclude_unset=True)

        assert wire["status_source"] == "unavailable"
        assert wire["unavailable_capabilities"] == ["live_enrichment"]


class TestBacklogListMcpWireCarriesStatusSource:
    """``backlog_list`` over the in-memory FastMCP transport."""

    async def test_healthy_call_reports_live_status_source(self) -> None:
        op_result = {
            "items": [{"issue": "#1", "title": "Live", "status": "open"}],
            "count": 1,
            "status_source": "live",
            "unavailable_capabilities": [],
            "filters_evaluated_against_unavailable_data": [],
        }
        with patch("dh_core.operations.list_items", return_value=op_result):
            response = await _call("backlog_list", {})

        assert response["status_source"] == "live"
        assert response["unavailable_capabilities"] == []

    async def test_degraded_call_reports_unavailable_status_source_on_the_wire(self) -> None:
        op_result = {
            "items": [{"issue": "#1", "title": "Unavailable", "status": ""}],
            "count": 1,
            "status_source": "unavailable",
            "unavailable_capabilities": ["live_status"],
            "filters_evaluated_against_unavailable_data": ["status"],
        }
        with patch("dh_core.operations.list_items", return_value=op_result):
            response = await _call("backlog_list", {"status": "in-progress"})

        assert response["status_source"] == "unavailable"
        assert response["unavailable_capabilities"] == ["live_status"]
        assert response["filters_evaluated_against_unavailable_data"] == ["status"]


class TestBacklogViewMcpWireCarriesStatusSource:
    """``backlog_view`` over the in-memory FastMCP transport, both response shapes."""

    async def test_summary_true_compact_manifest_carries_status_source(self) -> None:
        """The default call path -- _build_compact_manifest must not drop the field."""
        op_result = ViewItemResult.model_validate({
            "title": "An item",
            "issue": "#42",
            "state": "open",
            "status_source": "unavailable",
            "unavailable_capabilities": ["live_enrichment"],
        })
        with patch("dh_core.operations.view_item", return_value=op_result):
            response = await _call("backlog_view", {"selector": "#42"})

        assert response["status_source"] == "unavailable"
        assert response["unavailable_capabilities"] == ["live_enrichment"]

    async def test_summary_false_full_response_carries_status_source(self) -> None:
        op_result = ViewItemResult.model_validate({
            "title": "An item",
            "issue": "#42",
            "state": "open",
            "body": "content",
            "status_source": "unavailable",
            "unavailable_capabilities": ["live_enrichment"],
        })
        with patch("dh_core.operations.view_item", return_value=op_result):
            response = await _call("backlog_view", {"selector": "#42", "summary": False})

        assert response["status_source"] == "unavailable"
        assert response["unavailable_capabilities"] == ["live_enrichment"]

    async def test_healthy_call_reports_live_status_source_on_both_shapes(self) -> None:
        op_result = ViewItemResult.model_validate({
            "title": "An item",
            "issue": "#42",
            "state": "open",
            "status_source": "live",
            "unavailable_capabilities": [],
        })
        with patch("dh_core.operations.view_item", return_value=op_result):
            compact = await _call("backlog_view", {"selector": "#42"})
            full = await _call("backlog_view", {"selector": "#42", "summary": False})

        assert compact["status_source"] == "live"
        assert full["status_source"] == "live"
