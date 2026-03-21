"""FastMCP 3.x server exposing all backlog operations as MCP tools."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json as _json
import re as _re
import sys
from typing import TYPE_CHECKING, Annotated, cast

import dispatch_schema as _ds
import tiktoken
from fastmcp import Context, FastMCP
from pydantic import Field

from . import models as _models, operations
from .github import get_github as _get_github
from .models import BacklogError, GitHubUnavailableError, Output, init as _init_models

if TYPE_CHECKING:
    from pathlib import Path

    from .operations import ImpactRadiusItem as _ImpactRadiusItem

# Token budget for auto-pagination in backlog_list: 4400 tokens (cl100k_base encoding).
_LIST_TOKEN_BUDGET = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")


def _parse_args() -> argparse.Namespace:
    """Parse server startup arguments.

    Returns:
        Parsed namespace; ``project_dir`` is ``None`` when not supplied.
    """
    parser = argparse.ArgumentParser(description="Backlog MCP server")
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help=(
            "Absolute path to the user's project root. "
            "Required when installed as a plugin so BACKLOG_DIR resolves "
            "to the user's project rather than the plugin cache directory."
        ),
    )
    # parse_known_args prevents FastMCP/uvicorn arguments from causing errors
    namespace, _ = parser.parse_known_args(sys.argv[1:])
    return namespace


_args = _parse_args()
_init_models(_args.project_dir)

mcp = FastMCP(
    "backlog",
    instructions=(
        "Backlog management server. Manages per-item markdown files in .claude/backlog/, "
        "syncs with GitHub Issues (source of truth), and provides CRUD operations for "
        "backlog items including add, list, view, update, groom, close, resolve, and sync."
    ),
    version="0.1.0",
)


@mcp.tool
async def backlog_add(
    title: Annotated[str, Field(description="Item title")],
    priority: Annotated[str, Field(description="Priority level: P0, P1, P2, or Ideas")],
    description: Annotated[str, Field(description="Item description")],
    source: Annotated[str, Field(description="Where this item came from")] = "Not specified",
    type_: Annotated[
        str, Field(description="Item type: Feature, Bug, Refactor, Docs, or Chore", alias="type")
    ] = "Feature",
    create_issue: Annotated[bool, Field(description="Create a GitHub issue for this item")] = True,
    force: Annotated[bool, Field(description="Skip fuzzy duplicate check")] = False,
) -> dict:
    """Add a new item to the backlog. Creates a per-item file and optionally a GitHub issue.

    Use priority P0 for must-have, P1 for should-have, P2 for could-have,
    or Ideas for exploratory items.

    Returns:
        Dict with file_path, title, priority, issue number (if created),
        and output messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.add_item,
            title=title,
            priority=priority,
            description=description,
            source=source,
            type_=type_,
            create_issue=create_issue,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list(
    from_github: Annotated[bool, Field(description="Refresh local cache from GitHub Issues before listing")] = False,
    label: Annotated[str | None, Field(description="Filter by GitHub label (e.g. 'priority:p1', 'type:bug')")] = None,
    section: Annotated[
        str | None, Field(description="Filter by priority section: P0, P1, P2, or Ideas (case-insensitive)")
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by status value e.g. 'needs-grooming', 'status:in-progress'")
    ] = None,
    title_filter: Annotated[
        str | None,
        Field(description="Filter items whose title contains this substring (case-insensitive)", alias="title"),
    ] = None,
    type_: Annotated[
        str | None,
        Field(
            description=(
                "Filter by metadata.type — case-insensitive exact match (e.g. 'Bug', 'Feature'). "
                "Items without metadata.type are excluded when this filter is active."
            ),
            alias="type",
        ),
    ] = None,
    topic: Annotated[
        str | None,
        Field(
            description=(
                "Filter by metadata.topic — case-insensitive substring match. "
                "Items without metadata.topic are excluded when this filter is active."
            )
        ),
    ] = None,
    include_closed: Annotated[
        bool, Field(description="Include items with closed/done/resolved status (excluded by default)")
    ] = False,
    search: Annotated[
        str | None,
        Field(
            description=(
                "Case-insensitive substring search across title, section, topic, and type simultaneously. "
                "Unlike title= which only matches the title field, search= matches any of these fields. "
                "Combine with other filters to narrow results further."
            )
        ),
    ] = None,
    offset: Annotated[
        int, Field(ge=0, description="Skip the first N items from the filtered result set (for pagination).")
    ] = 0,
    limit: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Maximum number of items to return. 0 = auto-paginate to stay within 4400 token budget "
                "(cl100k_base encoding). Caller can override with an explicit positive value."
            ),
        ),
    ] = 0,
) -> dict:
    """List all open backlog items.

    Use from_github=true to refresh the local cache from GitHub before listing.
    Use label to filter items by a specific GitHub label.
    Use section to filter by priority section (P0, P1, P2, Ideas).
    Use status to filter by status value (e.g. needs-grooming, status:in-progress).
    Use title to filter by title substring (case-insensitive).
    Use type_ to filter by metadata.type exact match (e.g. Bug, Feature).
    Use topic to filter by metadata.topic substring match.
    Use include_closed=true to include items with terminal status (done, resolved, closed).
    Use search to search across title, section, topic, and type simultaneously.
    Use offset and limit to paginate results. When limit=0, auto-pagination keeps the
    response under 4400 tokens (cl100k_base encoding). When has_more=true, call again
    with the offset shown in next_call.

    Returns:
        Dict with items list, count, pagination object, and output messages/warnings.
        Each item includes state (open/closed) and status (workflow status from status:* labels).
        pagination contains offset, limit, total, and has_more. When has_more=true,
        next_call provides the suggested follow-up call string.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_items,
            from_github=from_github,
            label=label,
            section=section,
            status=status,
            title=title_filter,
            type_=type_,
            topic=topic,
            include_closed=include_closed,
            output=out,
        )
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}

    # "items" holds list[dict[str, str | bool]] per operations.list_items return type.
    # cast() narrows from the heterogeneous value union (int | list[str] | list[dict[...]]).
    all_items = cast("list[dict[str, str | bool]]", result.get("items", []))

    # Apply cross-field search filter when requested.
    if search is not None:
        needle = search.casefold()
        filtered: list[dict] = []
        for item in all_items:
            haystack = " ".join(
                str(item.get(field, "") or "") for field in ("title", "section", "topic", "type")
            ).casefold()
            if needle in haystack:
                filtered.append(item)
        all_items = filtered

    total = len(all_items)

    # Determine effective page limit.
    if limit > 0:
        # Caller requested an explicit limit — honour it exactly.
        effective_limit = limit
    else:
        # Auto-paginate: binary-search for the largest slice that fits the budget.
        # Start with all items and halve until the token count fits.
        candidate = all_items[offset:]
        effective_limit = len(candidate)
        while effective_limit > 1:
            token_count = len(_enc.encode(_json.dumps(candidate[:effective_limit])))
            if token_count <= _LIST_TOKEN_BUDGET:
                break
            effective_limit = max(1, effective_limit // 2)

    page_items = all_items[offset : offset + effective_limit]
    has_more = (offset + effective_limit) < total
    next_offset = offset + effective_limit

    pagination: dict = {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more}
    response: dict = {
        **result,
        "items": page_items,
        "count": len(page_items),
        "pagination": pagination,
        **out.to_dict(),
    }
    if has_more:
        response["next_call"] = f"backlog_list(offset={next_offset}, limit={effective_limit})"
    return response


@mcp.tool
async def backlog_view(
    selector: Annotated[str, Field(description="Item selector: GitHub issue URL, #N, bare number, or title substring")],
    offset: Annotated[int, Field(ge=0, description="Skip N entry blocks from body start (for pagination)")] = 0,
    limit: Annotated[int, Field(ge=0, description="Show at most N entry blocks (0 = all, no truncation)")] = 0,
    show: Annotated[
        str | None,
        Field(description="Entry filter: 'all', 'last', 'first', 'struck', or integer N (first N active entries)"),
    ] = None,
    since: Annotated[
        str | None, Field(description="ISO date/datetime. Only entries at or after this timestamp are included.")
    ] = None,
) -> dict:
    """View a single backlog item or GitHub issue in detail.

    Accepts a GitHub issue URL, #N, bare number, or title substring as selector.
    Use offset and limit to paginate long issue bodies.
    Use show and since to filter entry blocks within sections.

    Returns:
        Dict with title, priority, issue, plan, file_path, body, sections
        metadata, and output messages/warnings. On error, dict contains an
        error key.
    """
    out = Output()
    try:
        # MCP tool parameters are always strings; convert numeric show values to int.
        parsed_show: str | int | None = show
        if show is not None:
            try:
                parsed_show = int(show)
            except ValueError:
                parsed_show = show
        result = await asyncio.to_thread(
            operations.view_item,
            selector=selector,
            offset=offset,
            limit=limit,
            show=parsed_show,
            since=since,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_sync(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview what would be synced without making changes")] = False,
) -> dict:
    """Sync backlog items with GitHub: create missing issues and push groomed content.

    Use dry_run=true to preview changes without modifying anything.

    Returns:
        Dict with created and pushed counts and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        await ctx.info("Starting backlog sync" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.sync_items, dry_run=dry_run, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        created = result.get("created", 0)
        pushed = result.get("pushed", 0)
        await ctx.info(f"Sync complete: {created} issue(s) created, {pushed} item(s) pushed")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_close(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    reason: Annotated[
        str,
        Field(
            description="Why the item is being dismissed. One of: duplicate, out_of_scope, superseded, wontfix, blocked"
        ),
    ],
    reference: Annotated[
        str, Field(description="Related item reference: #N, URL, or title of the item this duplicates/is superseded by")
    ] = "",
    comment: Annotated[str, Field(description="Additional context about why this item is being closed")] = "",
    cleanup: Annotated[
        bool, Field(description="Remove local file after close; index link becomes GitHub issue URL")
    ] = False,
    force: Annotated[bool, Field(description="Close even if open PRs reference the issue")] = False,
) -> dict:
    """Dismiss a backlog item without completing it and close its GitHub issue.

    Use for items that are duplicates, out of scope, superseded, wontfix,
    or permanently blocked. For completed work, use backlog_resolve instead.

    Returns:
        Dict with closed item title, reason, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.close_item,
            selector=selector,
            reason=reason,
            reference=reference,
            comment=comment,
            cleanup=cleanup,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_resolve(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    summary: Annotated[str, Field(description="What was done — 1-2 sentence completion summary (required)")],
    plan: Annotated[str | None, Field(description="Plan path or completion reference")] = None,
    method: Annotated[str | None, Field(description="How the work was done — approach taken")] = None,
    notes: Annotated[str | None, Field(description="Problems found, surprises, or other comments")] = None,
    follow_ups: Annotated[str | None, Field(description="Created follow-up tickets (comma-separated refs)")] = None,
    findings: Annotated[str | None, Field(description="Retrospective learnings from this work")] = None,
    cleanup: Annotated[
        bool, Field(description="Remove local file after resolve; index link becomes GitHub issue URL")
    ] = False,
    force: Annotated[bool, Field(description="Resolve even if open PRs reference the issue")] = False,
) -> dict:
    """Mark a backlog item as DONE (completed) and close its GitHub issue.

    Creates a structured completion record as an audit/retrospective trail.
    Only summary is required — for trivial items a one-liner suffices.
    For dismissals (duplicate, out of scope, etc.), use backlog_close instead.

    Returns:
        Dict with resolved item title, summary, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.resolve_item,
            selector=selector,
            summary=summary,
            plan=plan or "",
            method=method or "",
            notes=notes or "",
            follow_ups=follow_ups or "",
            findings=findings or "",
            cleanup=cleanup,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_update(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    plan: Annotated[str | None, Field(description="Path to a plan file to attach to the item")] = None,
    status: Annotated[
        str | None,
        Field(description="Set item status (e.g. 'in-progress'). Updates GitHub issue labels when applicable."),
    ] = None,
    create_issue: Annotated[
        bool, Field(description="Create a GitHub issue for this item if it lacks one (P0/P1 items only)")
    ] = False,
    section: Annotated[
        str | None, Field(description="Section name for groomed content update (use with content parameter)")
    ] = None,
    content: Annotated[
        str | None, Field(description="Content for the named section (use with section parameter)")
    ] = None,
    title: Annotated[
        str | None,
        Field(
            description="New title for the item. Updates the local file name field and GitHub issue title if the item already has a linked issue."
        ),
    ] = None,
    description: Annotated[
        str | None,
        Field(description="New description text for the item. Updates the local file only — no GitHub sync."),
    ] = None,
    entry_id: Annotated[
        str | None, Field(description="Timestamp ID of an existing entry to replace within the section")
    ] = None,
    replace_section: Annotated[
        bool, Field(description="Strike all existing entries in the section and append new content")
    ] = False,
    reason: Annotated[
        str | None, Field(description="Reason for striking entries (required when replace_section=True)")
    ] = None,
    verified: Annotated[
        bool,
        Field(
            description="Apply status:verified label to the GitHub issue. "
            "Signals that /complete-implementation quality gates have passed. "
            "Auto-creates the label if absent. No-op when item has no issue number."
        ),
    ] = False,
) -> dict:
    """Update a backlog item: attach a plan, set status, create a GitHub issue, or write groomed content.

    For groomed content, provide section + content for section updates.
    Use entry_id to replace a specific entry, or replace_section=True to
    strike all entries and append new content. Groomed content is synced
    to the GitHub issue when the item has one.

    Use verified=True after /complete-implementation quality gates pass to
    apply the status:verified label to the linked GitHub issue.

    Returns:
        Dict with updated item title, applied changes, and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.update_item,
            selector=selector,
            plan=plan,
            status=status,
            create_issue=create_issue,
            section=section,
            content=content,
            title=title,
            description=description,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
            verified=verified,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_groom(
    ctx: Context,
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    section: Annotated[
        str | None, Field(description="Section name for incremental update (use with content parameter)")
    ] = None,
    content: Annotated[
        str | None, Field(description="Content for the named section (use with section parameter)")
    ] = None,
    entry_id: Annotated[
        str | None, Field(description="Timestamp ID of an existing entry to replace within the section")
    ] = None,
    replace_section: Annotated[
        bool, Field(description="Strike all existing entries in the section and append new content")
    ] = False,
    reason: Annotated[
        str | None, Field(description="Reason for striking entries (required when replace_section=True)")
    ] = None,
) -> dict:
    """Write groomed content into a backlog item's per-item file and sync to its GitHub issue.

    Provide section + content for section updates. Use entry_id to replace
    a specific entry, or replace_section=True to strike all entries and
    append new content. When the item has a GitHub issue, the groomed
    content is synced there automatically.

    Returns:
        Dict with groomed item title, synced status, and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        await ctx.info(f"Grooming item: {selector}")
        result = await asyncio.to_thread(
            operations.groom_item,
            selector=selector,
            section=section,
            content=content,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
        )
        for w in out.warnings:
            await ctx.warning(w)
        title = result.get("title", selector)
        await ctx.info(f"Groomed: {title}")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_normalize(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview normalization changes without modifying files")] = False,
) -> dict:
    """Normalize all per-item files to research-style metadata format and remove body duplication.

    This is a one-off maintenance operation. Use dry_run=true to preview
    what would change.

    Returns:
        Dict with count of normalized files and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        await ctx.info("Starting normalize" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.normalize_items, dry_run=dry_run, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        updated = result.get("updated", 0)
        suffix = " (dry-run)" if dry_run else ""
        await ctx.info(f"Normalized {updated} file(s){suffix}")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_pull(
    ctx: Context,
    selector: Annotated[
        str | None,
        Field(
            description="Optional selector to pull a single issue: #N, bare number, GitHub URL, or title substring. When omitted, pulls all issues."
        ),
    ] = None,
    dry_run: Annotated[bool, Field(description="Preview what would be pulled without modifying local files")] = False,
    force: Annotated[
        bool, Field(description="Overwrite local content even if local version is newer or longer")
    ] = False,
    diff: Annotated[bool, Field(description="Include entry-level diff output showing local vs remote changes")] = False,
) -> dict:
    """Pull issue body content from GitHub into local per-item files.

    When selector is provided, pulls a single issue by #N, bare number,
    GitHub URL, or title substring. When omitted, pulls all issues.

    Auto-migrates P0/P1 items lacking GitHub Issues by creating them.
    Merges by section using entry-aware merge (keeps longer entries,
    preserves strikes). Use dry_run=true to preview changes.
    Use diff=true to include entry-level diff output.

    Returns:
        Dict with count of pulled items (bulk) or file_path (single) and
        output messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        if selector is not None:
            await ctx.info(f"Pulling issue: {selector}")
            result = await asyncio.to_thread(operations.pull_by_selector, selector, diff=diff, output=out)
            for w in out.warnings:
                await ctx.warning(w)
            file_path = result.get("file_path")
            await ctx.info(f"Pulled: {file_path}" if file_path else "Nothing pulled")
            return {**result, **out.to_dict()}
        await ctx.info("Starting bulk pull from GitHub" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.pull_items, dry_run=dry_run, force=force, diff=diff, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        pulled = result.get("pulled", 0)
        await ctx.info(f"Pull complete: {pulled} item(s) pulled")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_create_sam_task(
    parent_issue_number: Annotated[int, Field(description="Parent story issue number (without #)")],
    task_id: Annotated[str, Field(description="Feature-scoped task ID, e.g. 'T1'")],
    feature: Annotated[str, Field(description="Feature slug, e.g. 'my-feature'")],
    task_type: Annotated[str, Field(description="Task category: research | implement | review | fix | docs")],
    agent: Annotated[str, Field(description="Agent name to execute this task")],
    priority: Annotated[int, Field(description="Priority 1-5 (1=highest)")] = 2,
    skills: Annotated[list[str], Field(description="Skill names for the executing agent")] = [],  # noqa: B006
    dependencies: Annotated[list[str], Field(description="Task IDs this task depends on")] = [],  # noqa: B006
    description: Annotated[str, Field(description="Human-readable description of the task")] = "",
    acceptance_criteria: Annotated[list[str] | None, Field(description="Acceptance criteria strings")] = None,
    labels: Annotated[list[str] | None, Field(description="GitHub label names to apply")] = None,
) -> dict:
    """Create a GitHub sub-issue for a SAM task under a parent story issue.

    Use to bootstrap GitHub visibility for a task when starting a new feature plan.

    Returns:
        Dict with issue_number, title, url, and output messages. On error, returns error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.create_sam_task,
            parent_issue_number=parent_issue_number,
            task_id=task_id,
            feature=feature,
            task_type=task_type,
            agent=agent,
            priority=priority,
            skills=skills,
            dependencies=dependencies,
            description=description,
            acceptance_criteria=acceptance_criteria,
            labels=labels,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_get_sam_tasks(
    parent_issue_number: Annotated[int, Field(description="Parent story issue number (without #)")],
    refresh_cache: Annotated[bool, Field(description="Write updated cache after fetching")] = True,
) -> dict:
    """Return all SAM task sub-issues for a parent story issue.

    Returns tasks list with SamTask fields plus issue_number and issue_url.
    Falls back to local cache if GitHub is unavailable.
    Use to inspect per-task status from the GitHub source of truth.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.get_sam_tasks, parent_issue_number=parent_issue_number, refresh_cache=refresh_cache, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_update_sam_task_status(
    issue_number: Annotated[int, Field(description="Task sub-issue number (without #)")],
    new_status: Annotated[str, Field(description="Target status: not-started | in-progress | complete | blocked")],
) -> dict:
    """Update the status field in a SAM task sub-issue.

    Patches the sam:task YAML block in the issue body. No-op if status already matches.

    Returns:
        Dict with updated (bool), issue_number, new_status, and output messages.
        On error, returns error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.update_sam_task_status, issue_number=issue_number, new_status=new_status, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_get_ready_sam_tasks(
    parent_issue_number: Annotated[int, Field(description="Parent story issue number (without #)")],
) -> dict:
    """Return SAM tasks ready for execution from GitHub sub-issues.

    Fetches sub-issues, resolves dependency graph locally, returns tasks whose
    status is not-started and all dependencies are terminal.
    Output shape matches implementation_manager.py ready-tasks JSON:
    feature, ready_tasks, count. Each ready_task includes id, name, agent, skills, issue_number.
    Falls back to local cache if GitHub is unavailable.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.get_ready_sam_tasks, parent_issue_number=parent_issue_number, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_strike_entry(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    entry_id: Annotated[str, Field(description="Timestamp ID of the entry to strike")],
    reason: Annotated[str, Field(description="Human-readable reason for striking the entry")],
    section: Annotated[str | None, Field(description="Optional section name to scope the search within")] = None,
) -> dict:
    """Strike (retract) an entry block within a backlog item.

    Wraps the entry in a collapsed details block with the reason,
    preserving the original content for audit. Syncs to GitHub issue
    if the item has one.

    Returns:
        Dict with strike results and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.strike_entry, selector=selector, entry_id=entry_id, reason=reason, section=section, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list_labels(limit: Annotated[int, Field(description="Maximum labels to return")] = 100) -> dict:
    """List repository labels (read-only).

    Returns all labels defined on the repository, up to ``limit``.
    Label mutations are not supported by this tool; they are owned by
    the state transition handler.

    Returns:
        Dict with ``labels`` (list of dicts with ``name``, ``color``, ``description``),
        ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_labels, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list_merged_prs(
    search: Annotated[
        str | None,
        Field(
            description=(
                "Optional substring to filter by (checked against PR title and body, "
                "case-insensitive). Use to find PRs related to a specific issue number "
                "(e.g. '#42') or keyword."
            )
        ),
    ] = None,
    limit: Annotated[int, Field(description="Maximum number of PRs to return")] = 20,
) -> dict:
    """List merged pull requests, optionally filtered by a search query.

    Only PRs that were actually merged (not just closed) are returned.
    Use ``search`` to filter by issue reference (e.g. ``'#42'``) or any
    keyword present in the PR title or body.

    Returns:
        Dict with ``pull_requests`` (list of dicts with ``number``,
        ``title``, ``merged_at``, ``author``, ``url``, ``head_branch``),
        ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_merged_prs, search=search, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list_milestones(
    state: Annotated[str, Field(description="Milestone state filter: open | closed | all")] = "open",
) -> dict:
    """List repository milestones filtered by state.

    Returns milestones with their issue counts and optional due dates.

    Returns:
        Dict with ``milestones`` (list of dicts with ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``), ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_milestones, state=state, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_get_soonest_milestone() -> dict:
    """Return the open milestone with the earliest due date.

    Milestones without a due date are excluded. If all open milestones
    lack a due date, the first one by GitHub's default ordering is returned
    with a warning.

    Returns:
        Dict with ``milestone`` (dict or None) containing ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``, and output messages/warnings.
        ``milestone`` is ``None`` when no open milestones exist.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.get_soonest_milestone, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_create_milestone(
    title: Annotated[str, Field(description="Milestone title (required, must be non-empty)")],
    description: Annotated[str, Field(description="Optional milestone description")] = "",
    due_on: Annotated[
        str | None,
        Field(description="Optional due date as ISO 8601 string, e.g. '2026-06-30' or '2026-06-30T00:00:00Z'"),
    ] = None,
) -> dict:
    """Create a new milestone on the repository.

    Returns:
        Dict with ``milestone`` containing ``number``, ``title``, ``state``,
        ``description``, ``due_on``, ``open_issues``, ``closed_issues``,
        and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.create_milestone, title=title, description=description, due_on=due_on, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list_issues(
    milestone: Annotated[str | None, Field(description="Filter by milestone title")] = None,
    labels: Annotated[str | None, Field(description="Comma-separated label names to filter by")] = None,
    state: Annotated[str, Field(description="Issue state: open, closed, or all")] = "open",
    limit: Annotated[int, Field(description="Maximum issues to return")] = 30,
) -> dict:
    """List GitHub issues with optional milestone, label, and state filters.

    Returns:
        Dict with issues list, count, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_issues, milestone=milestone, labels=labels, state=state, limit=limit, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_comment_issue(
    issue_number: Annotated[int, Field(description="GitHub issue number (without #)")],
    body: Annotated[str, Field(description="Comment body (Markdown)")],
) -> dict:
    """Add a comment to a GitHub issue.

    Returns:
        Dict with issue_number, comment_id, comment_url, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.comment_issue, issue_number=issue_number, body=body, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_list_projects(
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
    limit: Annotated[int, Field(description="Maximum projects to return")] = 20,
) -> dict:
    """List Projects V2 for the repository owner via GraphQL.

    Returns:
        Dict with projects list, count, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_projects, owner=owner, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_create_project(
    title: Annotated[str, Field(description="Project title")],
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
) -> dict:
    """Create a Projects V2 project under the repository owner.

    Resolves the owner node ID then runs the createProjectV2 GraphQL mutation.

    Returns:
        Dict with project_id, title, url, number, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.create_project, title=title, owner=owner, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


def _dispatch_plan_path(milestone_number: int) -> Path:
    """Return the canonical dispatch plan path for a milestone.

    Delegates to :func:`dispatch_schema.dispatch_plan_path`, resolving the
    project root from ``_models.BACKLOG_DIR``.

    Args:
        milestone_number: GitHub milestone number.

    Returns:
        Path to ``plan/milestone-{N}-dispatch.yaml`` under the project root.
    """
    # BACKLOG_DIR is <project_root>/.claude/backlog — walk up to project root
    return _ds.dispatch_plan_path(milestone_number, _models.BACKLOG_DIR.parent.parent)


@mcp.tool
async def dispatch_read(milestone_number: Annotated[int, Field(description="GitHub milestone number")]) -> dict:
    """Read a dispatch plan for the given milestone.

    Loads and returns the full plan as a dict. Returns an error dict if
    the plan file does not exist or fails YAML/schema validation.

    Returns:
        Dict with ``milestone_number``, ``plan_path``, and ``plan`` (full plan
        as a nested dict), or ``error`` on failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except FileNotFoundError:
        return {
            "error": f"Dispatch plan not found: {plan_path}",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
        }
    except ValueError as exc:
        return {"error": str(exc), "milestone_number": milestone_number, "plan_path": str(plan_path)}
    return {"milestone_number": milestone_number, "plan_path": str(plan_path), "plan": plan.model_dump()}


@mcp.tool
async def dispatch_validate(milestone_number: Annotated[int, Field(description="GitHub milestone number")]) -> dict:
    """Validate an existing dispatch plan's structural integrity.

    Reads the plan file then runs five structural checks: duplicate issues,
    conflict group references, depends_on existence, wave ordering, and
    conflict group wave placement.

    Returns:
        Dict with ``is_valid`` (bool), ``errors`` (list[str]), and
        ``warnings`` (list[str]), or ``error`` on file/parse failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number, "plan_path": str(plan_path)}
    result = await asyncio.to_thread(_ds.validate_plan_integrity, plan)
    return {"milestone_number": milestone_number, "plan_path": str(plan_path), **dataclasses.asdict(result)}


@mcp.tool
async def dispatch_stale_check(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> dict:
    """Check whether a dispatch plan is stale relative to the current milestone.

    Fetches open issues assigned to the milestone from GitHub, compares
    their issue numbers against those in the plan, and returns a stale/fresh
    indicator with added/removed issue lists.

    Returns:
        Dict with ``is_stale`` (bool), ``added_issues`` (list[int]),
        ``removed_issues`` (list[int]), and ``message`` (str).
        Returns ``error`` on file/parse or GitHub failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number, "plan_path": str(plan_path)}

    def _fetch_milestone_issue_numbers() -> list[int]:
        gh_repo = _get_github(repo)
        ms_obj = gh_repo.get_milestone(milestone_number)
        return [
            issue.number for issue in gh_repo.get_issues(milestone=ms_obj, state="all") if issue.pull_request is None
        ]

    try:
        current_numbers = await asyncio.to_thread(_fetch_milestone_issue_numbers)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    result = await asyncio.to_thread(_ds.detect_stale_plan, plan, current_numbers)
    return {"milestone_number": milestone_number, "plan_path": str(plan_path), **dataclasses.asdict(result)}


@mcp.tool
async def dispatch_conflicts(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> dict:
    """Analyze Impact Radius conflicts for items in a milestone.

    Fetches open issues for the milestone from GitHub, extracts the
    Impact Radius section from each issue body, then runs conflict analysis
    to find items that share file paths.

    Returns:
        Dict with ``conflict_groups`` (list of group dicts with group_id,
        reason, and items), ``count`` (int), and ``milestone_number``.
        Returns ``error`` on GitHub failure.
    """

    def _fetch_items_with_impact_radius() -> list[_ImpactRadiusItem]:
        gh_repo = _get_github(repo)
        ms_obj = gh_repo.get_milestone(milestone_number)
        items: list[_ImpactRadiusItem] = []
        ir_re = _re.compile(r"##\s+Impact\s+Radius\b(.*?)(?=\n##|\Z)", _re.IGNORECASE | _re.DOTALL)
        for issue in gh_repo.get_issues(milestone=ms_obj, state="open"):
            if issue.pull_request is not None:
                continue
            body = issue.body or ""
            match = ir_re.search(body)
            impact_radius = match.group(1).strip() if match else ""
            items.append({"title": issue.title, "issue": issue.number, "impact_radius": impact_radius})
        return items

    try:
        items = await asyncio.to_thread(_fetch_items_with_impact_radius)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    conflict_groups = await asyncio.to_thread(operations.analyze_impact_radius_conflicts, items)
    return {
        "milestone_number": milestone_number,
        "conflict_groups": [dataclasses.asdict(cg) for cg in conflict_groups],
        "count": len(conflict_groups),
    }


if __name__ == "__main__":
    mcp.run()
