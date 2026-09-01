"""Asserts every backlog_core MCP tool advertises a real output schema, not
an unconstrained object. See plugins/development-harness/backlog_core/tool_responses.py.

TOOLS_NOT_YET_TYPED tracks tools whose return-type annotation hasn't been
migrated to a Pydantic model yet -- shrinks across the rollout's commits.
Once empty, delete this set and the skip branch below.
"""

from __future__ import annotations

from backlog_core.server import mcp

EXCLUDED_TOOLS = {"profile_list", "profile_load"}  # different ownership, out of scope

TOOLS_NOT_YET_TYPED = {
    "artifact_get",
    "artifact_list",
    "artifact_read",
    "artifact_register",
    "backlog_add",
    "backlog_close",
    "backlog_comment_issue",
    "backlog_create_milestone",
    "backlog_create_project",
    "backlog_create_sam_task",
    "backlog_get_ready_sam_tasks",
    "backlog_get_sam_tasks",
    "backlog_get_soonest_milestone",
    "backlog_groom",
    "backlog_link_followup",
    "backlog_list",
    "backlog_list_comments",
    "backlog_list_followups",
    "backlog_list_issues",
    "backlog_list_labels",
    "backlog_list_merged_prs",
    "backlog_list_milestones",
    "backlog_list_projects",
    "backlog_normalize",
    "backlog_pull",
    "backlog_read_comment",
    "backlog_resolve",
    "backlog_strike_entry",
    "backlog_sync",
    "backlog_update",
    "backlog_update_sam_task_status",
    "backlog_view",
    "dispatch_conflicts",
    "dispatch_create_plan",
    "dispatch_item_status",
    "dispatch_read",
    "dispatch_spawn",
    "dispatch_stale_check",
    "dispatch_validate",
    "dispatch_wave_start",
    "dispatch_wave_status",
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
