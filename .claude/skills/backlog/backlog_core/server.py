"""FastMCP 3.x server exposing all backlog operations as MCP tools."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field

from . import operations
from .models import BacklogError, Output

mcp = FastMCP(
    "backlog",
    instructions=(
        "Backlog management server. Manages per-item markdown files in .claude/backlog/, "
        "syncs with GitHub Issues (source of truth), and provides CRUD operations for "
        "backlog items including add, list, view, update, groom, close, resolve, and sync."
    ),
    version="0.1.0",
)


@mcp.tool()
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


@mcp.tool()
async def backlog_list(
    with_status: Annotated[bool, Field(description="Include GitHub issue status for each item")] = False,
    from_github: Annotated[bool, Field(description="Refresh local cache from GitHub Issues before listing")] = False,
    label: Annotated[str | None, Field(description="Filter by GitHub label (e.g. 'priority:p1', 'type:bug')")] = None,
    section: Annotated[
        str | None, Field(description="Filter by priority section: P0, P1, P2, or Ideas (case-insensitive)")
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by status value e.g. 'needs-grooming', 'status:in-progress'")
    ] = None,
    title: Annotated[
        str | None, Field(description="Filter items whose title contains this substring (case-insensitive)")
    ] = None,
) -> dict:
    """List all open backlog items.

    Use from_github=true to refresh the local cache from GitHub before listing.
    Use label to filter items by a specific GitHub label.
    Use section to filter by priority section (P0, P1, P2, Ideas).
    Use status to filter by status value (e.g. needs-grooming, status:in-progress).
    Use title to filter by title substring (case-insensitive).

    Returns:
        Dict with items list (each containing title, priority, issue, plan)
        and output messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_items,
            with_status=with_status,
            from_github=from_github,
            label=label,
            section=section,
            status=status,
            title=title,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool()
async def backlog_view(
    selector: Annotated[str, Field(description="Item selector: GitHub issue URL, #N, bare number, or title substring")],
    offset: Annotated[int, Field(ge=0, description="Skip N lines from body start (for pagination)")] = 0,
    limit: Annotated[int, Field(ge=0, description="Show at most N body lines (0 = all, no truncation)")] = 0,
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
) -> dict:
    """Update a backlog item: attach a plan, set status, create a GitHub issue, or write groomed content.

    For groomed content, provide section + content for section updates.
    Use entry_id to replace a specific entry, or replace_section=True to
    strike all entries and append new content. Groomed content is synced
    to the GitHub issue when the item has one.

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
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
            result = await asyncio.to_thread(operations.pull_by_selector, selector, output=out)
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


if __name__ == "__main__":
    mcp.run()
