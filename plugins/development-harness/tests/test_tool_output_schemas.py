"""Asserts every backlog_core MCP tool advertises a real output schema, not
an unconstrained object. See plugins/development-harness/backlog_core/tool_responses.py.

All 43 tools are typed as of #3368 (backlog_view, the last holdout).
"""

from __future__ import annotations

import inspect
import json

import tiktoken
from backlog_core import tool_responses as _tool_responses
from backlog_core.models import Output
from backlog_core.server import mcp
from pydantic import BaseModel

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
# single-tool disaster. Per-tool cap bumped 600->700 when widening several
# list-response fields to Optional (fixing error-arm default-value leaks,
# e.g. dispatch_wave_status) pushed one tool to 604 -- still nowhere near
# sam_plan's per-tool cost.
_MAX_TOTAL_SCHEMA_TOKENS = 13000
_MAX_SINGLE_TOOL_SCHEMA_TOKENS = 700

# backlog_view (#3368) is the deliberate multi-mode outlier: one tool
# advertising seven response shapes (map/navigate/extract/summary/
# over-budget/full-detail/error) behind a single flat, all-Optional model --
# see BacklogViewResponse in tool_responses.py. Measured at 1,904 tokens.
# Held to its own explicit ceiling so the 700-token cap keeps its teeth for
# the other 42 tools rather than being raised 3x for all of them.
_PER_TOOL_SCHEMA_OVERRIDES = {"backlog_view": 2000}
_ENCODING = tiktoken.get_encoding("cl100k_base")


def _schema_tokens(schema: dict[str, object]) -> int:
    return len(_ENCODING.encode(json.dumps(schema, sort_keys=True)))


async def _tool_schemas() -> dict[str, dict[str, object]]:
    tools = await mcp.list_tools()
    return {t.name: (t.output_schema or {}) for t in tools if t.name not in EXCLUDED_TOOLS}


async def test_all_typed_tools_advertise_a_real_output_schema() -> None:
    schemas = await _tool_schemas()
    for name, schema in schemas.items():
        assert schema.get("properties"), f"{name}: no properties in output schema"
        assert schema.get("additionalProperties") is not True, f"{name}: still unconstrained object"
        assert "x-fastmcp-wrap-result" not in schema, f"{name}: Union return type wrapped the result -- wire regression"


async def test_output_schemas_stay_within_token_budget() -> None:
    schemas = await _tool_schemas()
    per_tool = {name: _schema_tokens(schema) for name, schema in schemas.items()}
    total = sum(per_tool.values())
    over_budget = {
        name: n
        for name, n in per_tool.items()
        if n > _PER_TOOL_SCHEMA_OVERRIDES.get(name, _MAX_SINGLE_TOOL_SCHEMA_TOKENS)
    }
    assert not over_budget, f"Tool(s) exceed their per-tool schema budget: {over_budget}"
    assert total <= _MAX_TOTAL_SCHEMA_TOKENS, (
        f"Total outputSchema tokens across all tools ({total}) exceeds budget of {_MAX_TOTAL_SCHEMA_TOKENS}"
    )


def test_no_response_model_field_shadows_an_output_method() -> None:
    """No tool_responses.py model field name collides with an Output method.

    Regression guard for a real bug hit during this rollout: a field named
    ``error`` on a subclass of ``Output`` silently shadowed the inherited
    ``Output.error()`` method (since renamed to ``record_error()``) --
    pydantic v2 resolved the field's default back to the bound method
    instead of the declared default, breaking JSON serialization with no
    exception at class-definition time. Checked against Output's actual
    method names (not a hardcoded list), so this still catches a future
    mutator method added to Output, not just today's three.
    """
    output_method_names = {
        name for name, _ in inspect.getmembers(Output, predicate=inspect.isfunction) if not name.startswith("_")
    }
    offenders: dict[str, set[str]] = {}
    for name, obj in vars(_tool_responses).items():
        if isinstance(obj, type) and issubclass(obj, BaseModel) and issubclass(obj, Output):
            shadowed = set(obj.model_fields) & output_method_names
            if shadowed:
                offenders[name] = shadowed
    assert not offenders, f"Field name(s) shadow an Output method, breaking serialization: {offenders}"
