"""Asserts every backlog_core MCP tool advertises a real output schema, not
an unconstrained object. See plugins/development-harness/backlog_core/tool_responses.py.

TOOLS_NOT_YET_TYPED tracks tools whose return-type annotation hasn't been
migrated to a Pydantic model yet -- shrinks across the rollout's commits.
Once empty, delete this set and the skip branch below.
"""

from __future__ import annotations

import json

import tiktoken
from backlog_core.server import mcp

EXCLUDED_TOOLS = {"profile_list", "profile_load"}  # different ownership, out of scope

# Guards against the failure mode seen in the sibling SAM server, where a
# consolidated tool's outputSchema alone costs 8,758 tokens (sam_plan) --
# 60% of that server's entire 45-tool listing. A real schema is the point of
# this rollout; an unbounded one defeats it just as badly as no schema at all.
#
# Recalibrated against a real measurement, not a guess: with 29/43 tools
# fully typed (real nested models, no budget-driven dict[str, object]
# flattening), the total was 7,211 tokens -- an earlier 6,000 total /
# 400-per-tool cap was set before that measurement existed and forced two
# rounds of stripping real type information (docstrings, nested models,
# even an entire shared Milestone model going unused) just to satisfy an
# untested number. These values leave headroom for the remaining 14 tools
# (13 ordinary tools plus backlog_view, the one deliberately complex
# exception) while staying two orders of magnitude below sam_plan's
# single-tool disaster.
_MAX_TOTAL_SCHEMA_TOKENS = 13000
_MAX_SINGLE_TOOL_SCHEMA_TOKENS = 600
_ENCODING = tiktoken.get_encoding("cl100k_base")


def _schema_tokens(schema: dict[str, object]) -> int:
    return len(_ENCODING.encode(json.dumps(schema)))


TOOLS_NOT_YET_TYPED = {
    "backlog_strike_entry",
    "backlog_sync",
    "backlog_update",
    "backlog_update_sam_task_status",
    "backlog_view",
    "dispatch_conflicts",
    "dispatch_create_plan",
    "dispatch_item_status",
    "dispatch_read",
    "dispatch_stale_check",
    "dispatch_validate",
    "dispatch_wave_start",
    "sync_now",
    "sync_status",
}


async def _tool_schemas() -> dict[str, dict[str, object]]:
    tools = await mcp.list_tools()
    return {t.name: (t.output_schema or {}) for t in tools if t.name not in EXCLUDED_TOOLS}


async def test_all_typed_tools_advertise_a_real_output_schema() -> None:
    schemas = await _tool_schemas()
    for name, schema in schemas.items():
        if name in TOOLS_NOT_YET_TYPED:
            continue
        assert schema.get("properties"), f"{name}: no properties in output schema"
        assert schema.get("additionalProperties") is not True, f"{name}: still unconstrained object"
        assert "x-fastmcp-wrap-result" not in schema, f"{name}: Union return type wrapped the result -- wire regression"


async def test_every_registered_tool_is_accounted_for() -> None:
    # Catches a renamed/added/removed tool falling through the cracks of TOOLS_NOT_YET_TYPED.
    schemas = await _tool_schemas()
    assert set(schemas) >= TOOLS_NOT_YET_TYPED, "TOOLS_NOT_YET_TYPED references a tool that no longer exists"


async def test_output_schemas_stay_within_token_budget() -> None:
    schemas = await _tool_schemas()
    per_tool = {name: _schema_tokens(schema) for name, schema in schemas.items()}
    total = sum(per_tool.values())
    over_budget = {name: n for name, n in per_tool.items() if n > _MAX_SINGLE_TOOL_SCHEMA_TOKENS}
    assert not over_budget, f"Tool(s) exceed {_MAX_SINGLE_TOOL_SCHEMA_TOKENS}-token schema budget: {over_budget}"
    assert total <= _MAX_TOTAL_SCHEMA_TOKENS, (
        f"Total outputSchema tokens across all tools ({total}) exceeds budget of {_MAX_TOTAL_SCHEMA_TOKENS}"
    )
