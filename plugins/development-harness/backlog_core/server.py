"""FastMCP 3.x server exposing all backlog operations as MCP tools."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import json as _json
import logging as _logging
import os as _os
import re as _re
import shutil
import sqlite3
import subprocess
import sys
import time as _time
from datetime import UTC, datetime as _datetime
from io import StringIO as _StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import dh_paths as _dh_paths
import dispatch_schema as _ds
import tiktoken
from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan
from pydantic import Field, ValidationError as _ValidationError
from ruamel.yaml import YAML as _YAML, YAMLError as _YAMLError

from . import models as _models, operations
from .artifact_provider import GitHubArtifactProvider
from .artifact_registry import ArtifactRegistry
from .dispatch_state import DispatchStateManager as _DispatchStateManager
from .github import (
    IssueNode as _IssueNode,
    get_github as _get_github,
    probe_backend_status as _probe_backend_status,
    sync_issues_graphql as _sync_issues_graphql,
)
from .models import (
    ArtifactContent,
    ArtifactEntry,
    ArtifactStatus,
    ArtifactType,
    BackendAvailability as _BackendAvailability,
    BackendStatus as _BackendStatus,
    BacklogError,
    DispatchItemRecord as _DispatchItemRecord,
    DispatchSpawnSummary as _DispatchSpawnSummary,
    DispatchWaveRecord as _DispatchWaveRecord,
    DispatchWaveSummary as _DispatchWaveSummary,
    GitHubUnavailableError,
    Output,
    RegisterResult,
    init as _init_models,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .operations import ImpactRadiusItem as _ImpactRadiusItem

# Token budget for auto-pagination in backlog_list: 4400 tokens (cl100k_base encoding).
_LIST_TOKEN_BUDGET = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")

# Fields searched by default when no field-specific prefix is given.
_SEARCH_FIELDS: tuple[str, ...] = ("title", "section", "topic", "type")

# Minimum length for a valid /pattern/ regex term (e.g. "/x/" has length 3).
_REGEX_SLASH_MIN_LEN = 2

# Sentinel: prevents _bootstrap_beads from running more than once per process.
# Tests reset via monkeypatch.setattr("backlog_core.server._beads_bootstrapped", False).
_beads_bootstrapped: bool = False


def _bootstrap_beads(project_dir: Path) -> None:
    """Auto-bootstrap beads toolchain (bd binary, .beads/ database, Claude hooks).

    Runs at server startup via the FastMCP lifespan hook. Blocked by module-level
    sentinel so it executes at most once per process, even when multiple
    ``Client(mcp)`` connections are opened in tests.

    All subprocess calls use ``check=False`` and ``capture_output=True`` to avoid
    raising exceptions or polluting the MCP transport with subprocess output.
    Full binary paths (from ``shutil.which``) are used in subprocess calls to
    satisfy S607 (no partial executable paths).

    Args:
        project_dir: Resolved project root path (from ``models.get_repo_root()``).
    """
    global _beads_bootstrapped  # noqa: PLW0603
    if _beads_bootstrapped:
        return

    log = _logging.getLogger(__name__)

    bd_path = shutil.which("bd")
    if bd_path:
        # Happy path: bd is already on PATH.
        if not (project_dir / ".beads").exists():
            subprocess.run([bd_path, "init", "--stealth", "--quiet"], cwd=project_dir, check=False, capture_output=True)
        subprocess.run(
            [bd_path, "setup", "claude", "--project", "--stealth"], cwd=project_dir, check=False, capture_output=True
        )
        _beads_bootstrapped = True
        return

    # bd not on PATH — try installing via npm.
    npm_path = shutil.which("npm")
    if not npm_path:
        log.warning("beads bootstrap skipped: npm not available")
        _beads_bootstrapped = True
        return

    subprocess.run([npm_path, "install", "-g", "@beads/bd"], check=False, capture_output=True)

    bd_path = shutil.which("bd")
    if not bd_path:
        log.warning("beads bootstrap skipped: npm install failed silently")
        _beads_bootstrapped = True
        return

    # Install succeeded; initialise and set up.
    subprocess.run([bd_path, "init", "--stealth", "--quiet"], cwd=project_dir, check=False, capture_output=True)
    subprocess.run(
        [bd_path, "setup", "claude", "--project", "--stealth"], cwd=project_dir, check=False, capture_output=True
    )
    _beads_bootstrapped = True


@lifespan
async def _beads_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """FastMCP lifespan hook: bootstrap beads before server accepts tool calls.

    Runs ``_bootstrap_beads`` in a thread executor to avoid blocking the event
    loop during startup (subprocess calls may take several seconds).

    Args:
        server: FastMCP server instance (provided by FastMCP at startup).

    Yields:
        None after bootstrap completes.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _bootstrap_beads, _models.get_repo_root())
    yield


def _item_field_text(item: dict[str, str | bool], field: str) -> str:
    """Return the casefolded text for a single field of an item dict."""
    return str(item.get(field, "") or "").casefold()


def _item_matches_term(item: dict[str, str | bool], term: str) -> bool:
    """Return True if a single search term matches the item.

    Supported term forms (evaluated in order):
    - ``/pattern/`` or ``regex:pattern`` — compiled regex matched against all
      default search fields joined with a space.
    - ``field:value`` — substring match restricted to a named field
      (``title``, ``section``, ``topic``, ``type``).  Unknown field names fall
      back to full-text substring match.
    - plain text — case-insensitive substring match across all default fields
      (existing behaviour, fully preserved).
    """
    term = term.strip()
    if not term:
        return True

    # Regex form: /pattern/ or regex:pattern
    if (term.startswith("/") and term.endswith("/") and len(term) > _REGEX_SLASH_MIN_LEN) or term.startswith("regex:"):
        pattern_str = term[1:-1] if term.startswith("/") else term[len("regex:") :]
        try:
            pattern = _re.compile(pattern_str, _re.IGNORECASE)
        except _re.error:
            # Invalid regex — fall through to plain substring match on the raw term.
            pass
        else:
            haystack = " ".join(_item_field_text(item, f) for f in _SEARCH_FIELDS)
            return bool(pattern.search(haystack))

    # Field-specific form: field:value
    if ":" in term:
        field, _, value = term.partition(":")
        field = field.strip().lower()
        value = value.strip().casefold()
        if field in _SEARCH_FIELDS:
            return value in _item_field_text(item, field)
        # Unknown field prefix — treat as plain text (fall through).

    # Plain text — existing case-insensitive substring match across all fields.
    needle = term.casefold()
    return needle in " ".join(_item_field_text(item, f) for f in _SEARCH_FIELDS)


def _apply_search_filter(items: list[dict[str, str | bool]], search: str) -> list[dict[str, str | bool]]:
    """Filter items using the full-text search query syntax.

    Query syntax (case-insensitive keywords):
    - ``term1 OR term2``  — item matches if either term matches.
    - ``term1 AND term2`` — item matches only if both terms match.
    - Bare text without AND/OR — original substring behaviour (single term).

    OR and AND keywords are whitespace-delimited and case-insensitive.  Mixed
    AND/OR in a single query is not supported; AND takes precedence when both
    appear.

    Each individual term supports:
    - ``/regex/`` or ``regex:pattern`` — regex match
    - ``field:value`` — field-specific substring match
    - plain text — substring match across all default fields

    Returns:
        Filtered list of items that match the search query.
    """
    search = search.strip()
    if not search:
        return items

    # Tokenise on whitespace-delimited AND / OR operators (case-insensitive).
    upper = search.upper()
    if " AND " in upper:
        # Split on first-level AND; each part is a term (may itself contain spaces
        # for field:value terms like "title:auth deploy").
        and_parts = _re.split(r"(?i)\s+AND\s+", search)
        return [item for item in items if all(_item_matches_term(item, part) for part in and_parts)]

    if " OR " in upper:
        or_parts = _re.split(r"(?i)\s+OR\s+", search)
        return [item for item in items if any(_item_matches_term(item, part) for part in or_parts)]

    # No operator — treat entire query as a single term (existing behaviour).
    return [item for item in items if _item_matches_term(item, search)]


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
        "Backlog management server. Manages per-item markdown files in ~/.dh/projects/{slug}/backlog/, "
        "syncs with GitHub Issues (source of truth), and provides CRUD operations for "
        "backlog items including add, list, view, update, groom, close, resolve, and sync."
    ),
    version="0.1.0",
    lifespan=_beads_lifespan,
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


def _format_backend_status_message(status: _BackendStatus) -> str:
    """Format a single-line human-readable backend status string for the messages list.

    When reachable, the format is:
        ``Backend: GitHub, Backend availability: reachable, Backend items (N open / M total)``

    When unavailable (any non-reachable state), the format is:
        ``Backend: GitHub, Backend availability: <state>, Backend items (--- open / --- total)[cache: N open / M total]``

    Args:
        status: Populated BackendStatus from probe_backend_status().

    Returns:
        Formatted status string.
    """
    availability_label = (
        status.availability.value if isinstance(status.availability, _BackendAvailability) else str(status.availability)
    )
    if (
        status.availability == _BackendAvailability.REACHABLE
        and status.open_count is not None
        and status.total_count is not None
    ):
        return (
            f"Backend: {status.name}, Backend availability: {availability_label}, "
            f"Backend items ({status.open_count} open / {status.total_count} total)"
        )
    cache_open = status.cache_open_count
    cache_total = status.cache_total_count
    return (
        f"Backend: {status.name}, Backend availability: {availability_label}, "
        f"Backend items (--- open / --- total)"
        f"[cache: {cache_open} open / {cache_total} total]"
    )


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
                "Full-text search across title, section, topic, and type simultaneously. "
                "Supports OR/AND operators (e.g. 'auth OR deploy'), "
                "regex patterns (/pattern/ or regex:pattern), "
                "field-specific search (title:auth, type:bug, topic:devops, section:P1), "
                "and plain case-insensitive substring matching (existing behaviour). "
                "OR/AND are whitespace-delimited and case-insensitive. "
                "Mixed AND/OR in a single query is not supported; AND takes precedence. "
                "Combine with other filters (section=, type=, topic=) to narrow results further."
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
    Use search for full-text search across title, section, topic, and type.
    Search supports OR/AND operators (e.g. 'auth OR deploy'), regex (/pattern/ or regex:pattern),
    field-specific syntax (title:auth, type:bug, topic:devops), and plain substring matching.
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
        result, backend_status = await asyncio.gather(
            asyncio.to_thread(
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
            ),
            asyncio.to_thread(_probe_backend_status),
        )
    except BacklogError as e:
        backend_status = await asyncio.to_thread(_probe_backend_status)
        return {"error": str(e), "backend": backend_status.model_dump(), **out.to_dict()}

    # "items" holds list[dict[str, str | bool]] per operations.list_items return type.
    # Filter to dict elements only to narrow the heterogeneous value union.
    raw_items = result.get("items", [])
    all_items: list[dict[str, str | bool]] = (
        [x for x in raw_items if isinstance(x, dict)] if isinstance(raw_items, list) else []
    )

    # Apply cross-field search filter when requested.
    if search is not None:
        all_items = _apply_search_filter(all_items, search)

    total = len(all_items)

    # ADR-5: cache_open_count reflects the same filter as the items list.
    backend_status.cache_open_count = total

    # Append the human-readable backend status line to the messages list.
    out.info(_format_backend_status_message(backend_status))

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

    pagination: dict = {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more}
    response: dict = {
        **result,
        "items": page_items,
        "count": len(page_items),
        "pagination": pagination,
        "backend": backend_status.model_dump(),
        **out.to_dict(),
    }
    if has_more:
        response["next_call"] = f"backlog_list(offset={offset + effective_limit}, limit={effective_limit})"
    return response


@mcp.tool
async def backlog_view(
    selector: Annotated[str, Field(description="Item selector: GitHub issue URL, #N, bare number, or title substring")],
    summary: Annotated[
        bool,
        Field(
            description="When True (default), returns a compact 5-field routing manifest (issue_number, title, labels, status, plan_path) plus _full_chars and _hint. When False, returns the full response unchanged."
        ),
    ] = True,
    include_content: Annotated[
        bool,
        Field(
            description="When True (default), returns full body and section entries. When False, returns metadata and section inventory only (section names with entry counts, no body or entry content)."
        ),
    ] = True,
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
    Use include_content=False to get a compact response with section names and
    entry counts only, omitting the full body and entry content.
    Use summary=False to receive the full response; summary=True (default) returns
    a 5-field routing manifest with _full_chars so the caller knows what was skipped.

    Returns:
        When summary=True (default): compact dict with issue_number, title, labels,
        status, plan_path, _summary, _full_chars, and _hint.
        When summary=False: dict with title, priority, issue, plan, file_path, body,
        sections metadata, and output messages/warnings.
        On error, dict contains an error key.
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
            include_content=include_content,
            offset=offset,
            limit=limit,
            show=parsed_show,
            since=since,
            output=out,
        )
        full_response = {**result, **out.to_dict()}
        if not summary:
            return full_response
        # Build compact routing manifest.
        full_chars = len(_json.dumps(full_response))
        body_text = str(result.get("body") or "")
        plan_match = _re.search(r"^[Pp]lan:\s*(\S+)", body_text, _re.MULTILINE)
        plan_path: str | None = plan_match.group(1) if plan_match else None
        issue_field = str(result.get("issue") or "")
        issue_number: int | None = None
        num_match = _re.search(r"(\d+)", issue_field)
        if num_match:
            issue_number = int(num_match.group(1))
        labels_raw = result.get("labels", [])
        labels: list[str] = labels_raw if isinstance(labels_raw, list) else []
        state = str(result.get("state") or "")
        status: str = "closed" if state == "closed" else "open"
        return {
            "issue_number": issue_number,
            "title": result.get("title", ""),
            "labels": labels,
            "status": status,
            "plan_path": plan_path,
            "_summary": True,
            "_full_chars": full_chars,
            "_hint": f"Call backlog_view(selector='{selector}', summary=False) for full body, comments, and timeline",
        }
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
    append: Annotated[
        bool,
        Field(
            description=(
                "When True and section is provided, append new content after existing section content "
                "(newline-separated) instead of replacing it. No entry-block wrapping is applied. "
                "Use this to incrementally add lines to a section such as ## Concerns."
            )
        ),
    ] = False,
    sections: Annotated[
        dict[str, str] | None,
        Field(
            description=(
                "Batch section writes: mapping of section name to raw content. "
                "Mutually exclusive with section, content, entry_id, replace_section, reason, and append. "
                "Each section is written with entry-block wrapping applied automatically. "
                "GitHub sync is performed after all local writes complete."
            )
        ),
    ] = None,
    mark_groomed: Annotated[
        bool,
        Field(
            description=(
                "When True, advance item status to groomed after content is written: set local frontmatter "
                "status to 'groomed', remove status:needs-grooming label (idempotent), and add status:groomed "
                "label (created if absent). Default False preserves existing behavior."
            )
        ),
    ] = False,
) -> dict:
    """Write groomed content into a backlog item's per-item file and sync to its GitHub issue.

    Provide section + content for section updates. Use entry_id to replace
    a specific entry, or replace_section=True to strike all entries and
    append new content. Set append=True to add content after existing section
    text without entry-block wrapping. Use sections for atomic multi-section
    writes in a single call — mutually exclusive with section/content/etc.
    When the item has a GitHub issue, the groomed content is synced there
    automatically.

    Returns:
        Dict with groomed item title, synced status, and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    if sections is not None and any((section, content, entry_id, replace_section, reason, append)):
        return {
            "error": "sections is mutually exclusive with section, content, entry_id, replace_section, reason, and append"
        }
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
            append=append,
            sections=sections,
            mark_groomed=mark_groomed,
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


# ---------------------------------------------------------------------------
# Artifact manifest tools
# ---------------------------------------------------------------------------

_artifact_registry = ArtifactRegistry()
_artifact_provider: GitHubArtifactProvider | None = None


def _require_artifact_entries(entries: list, label: str) -> None:
    """Raise BacklogError when no artifact entries are found.

    Args:
        entries: List of artifact entries (may be empty).
        label: Error message to include in the exception.

    Raises:
        BacklogError: When ``entries`` is empty.
    """
    if not entries:
        raise BacklogError(label)


def _get_artifact_provider() -> GitHubArtifactProvider:
    """Return (or lazily create) the GitHubArtifactProvider singleton.

    Deferred so the provider is created after ``_init_models()`` has resolved
    the repo slug and project root from the ``--project-dir`` argument.

    Returns:
        Initialised ``GitHubArtifactProvider`` instance.

    Raises:
        GitHubUnavailableError: When GitHub credentials or repo slug are missing.
    """
    global _artifact_provider  # noqa: PLW0603
    if _artifact_provider is None:
        repo = _models.DEFAULT_REPO
        if not repo:
            raise GitHubUnavailableError("DEFAULT_REPO not set — GitHub credentials or repo slug missing")
        _artifact_provider = GitHubArtifactProvider(
            repo=repo,
            root_worktree=_models._REPO_ROOT,  # noqa: SLF001
        )
    return _artifact_provider


@mcp.tool
async def artifact_register(
    issue_number: Annotated[int, Field(description="GitHub issue number")],
    artifact_type: Annotated[
        str,
        Field(
            description=(
                "Artifact type: feature-context, architect, task-plan, T0-baseline, TN-verification, "
                "codebase-analysis, research"
            )
        ),
    ],
    path: Annotated[str, Field(description="Relative path from repo root, e.g. plan/architect-foo.md")],
    status: Annotated[str, Field(description="Lifecycle status: draft, current, superseded, archived")] = "current",
    agent: Annotated[str, Field(description="Name of the producing agent")] = "",
    content: Annotated[
        str | None,
        Field(
            description=(
                "Optional artifact content to store as a GitHub issue comment. "
                "When provided the content is stored in a collapsible comment identified by type+path. "
                "When omitted only the manifest entry is registered (backward-compatible)."
            )
        ),
    ] = None,
) -> dict:
    """Upsert an artifact entry in the manifest for a GitHub issue.

    Idempotent by (artifact_type, path). If an entry with the same type and
    path already exists it is updated in-place (status, agent, timestamp).
    If only the type matches but the path differs, a new row is added.

    Content upload follows three-tier resolution:

    1. **Explicit content** — when *content* is provided, it is uploaded
       directly to a structured GitHub issue comment so it can be retrieved
       via ``artifact_read`` even from worktree-isolated agents.
    2. **Auto-read from local file** — when *content* is ``None`` but a local
       file exists at *path* (resolved against the root worktree), the file is
       read automatically and uploaded as in tier 1.
    3. **Manifest-only** — when *content* is ``None`` and no local file exists,
       the manifest entry is registered without content storage.  A warning is
       emitted so callers can detect the gap.

    Returns:
        Dict with registered (bool), artifact_count (int), action (str),
        content_stored (bool), and output messages/warnings. On error, dict
        contains an error key.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        artifact_type_enum = ArtifactType(artifact_type)
        status_enum = ArtifactStatus(status)
        entry = ArtifactEntry(
            artifact_type=artifact_type_enum,
            path=path,
            status=status_enum,
            created_at=_datetime.now(UTC).isoformat(),
            agent=agent,
        )

        def _run() -> RegisterResult:
            manifest = provider.get_manifest(issue_number)
            updated_manifest = _artifact_registry.register(manifest, entry)
            provider.set_manifest(issue_number, updated_manifest)
            # Determine action: "updated" if entry pre-existed, "added" otherwise.
            existed = any(e.artifact_type == artifact_type_enum and e.path == path for e in manifest.artifacts)
            action = "updated" if existed else "added"

            # Content upload — three-way resolution:
            # 1. Explicit content provided → use it directly.
            # 2. No explicit content but local file exists → read and upload.
            # 3. Neither → register manifest entry only; emit a warning.
            upload_content: str | None = content
            if upload_content is None:
                upload_content = provider.read_local_artifact_content(path)
                if upload_content is None:
                    out.warn(
                        f"No content provided and no local file found at {path!r}. "
                        "Manifest entry registered without content storage."
                    )

            content_stored = False
            if upload_content is not None:
                provider.store_artifact_content(issue_number, artifact_type, path, upload_content)
                content_stored = True

            return RegisterResult(
                registered=True,
                artifact_count=len(updated_manifest.artifacts),
                action=action,
                content_stored=content_stored,
            )

        result = await asyncio.to_thread(_run)
        return {**result.model_dump(), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def artifact_list(
    issue_number: Annotated[int, Field(description="GitHub issue number")],
    artifact_type: Annotated[str | None, Field(description="Filter by artifact type (optional)")] = None,
) -> dict:
    """Return all artifacts registered for a GitHub issue.

    Optionally filter by artifact type. Returns an empty list when no
    manifest section exists yet — this is not an error.

    Returns:
        Dict with artifacts (list of dicts), count (int), and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_filter: ArtifactType | None = ArtifactType(artifact_type) if artifact_type else None

        def _run() -> list[dict]:
            manifest = provider.get_manifest(issue_number)
            if type_filter is not None:
                entries = _artifact_registry.get_by_type(manifest, type_filter)
            else:
                entries = manifest.artifacts
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def artifact_get(
    issue_number: Annotated[int, Field(description="GitHub issue number")],
    artifact_type: Annotated[str, Field(description="Artifact type to retrieve")],
) -> dict:
    """Return metadata for a specific artifact type registered on a GitHub issue.

    If multiple artifacts of the same type exist (e.g. multiple
    codebase-analysis files), all are returned.

    Returns:
        Dict with artifacts (list of dicts), count (int), and output
        messages/warnings. Returns error key when type is not found.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_enum = ArtifactType(artifact_type)

        def _run() -> list[dict]:
            manifest = provider.get_manifest(issue_number)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        if not artifacts:
            return {"error": f"No artifacts of type '{artifact_type}' found for issue #{issue_number}", **out.to_dict()}
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def artifact_read(
    issue_number: Annotated[int, Field(description="GitHub issue number")],
    artifact_type: Annotated[str, Field(description="Artifact type whose content to read")],
) -> dict:
    """Read the file content for an artifact registered on a GitHub issue.

    Content retrieval order:

    1. GitHub issue comments — searches for a stored artifact content comment
       matching the artifact type and path.  This succeeds even when the local
       filesystem file does not exist (e.g. from a worktree-isolated agent).
    2. Local filesystem fallback — when no GitHub comment is found, resolves
       the artifact path against the root worktree.

    Path safety (filesystem path): the provider validates that the resolved
    path is under the repository root (path traversal prevention).

    Returns:
        Dict with type (str), path (str), content (str), status (str), and
        output messages/warnings. Returns error key on type-not-found, path
        safety violation, or when content is not found via either source.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_enum = ArtifactType(artifact_type)

        def _run() -> ArtifactContent:
            manifest = provider.get_manifest(issue_number)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            _require_artifact_entries(
                entries, f"No artifacts of type '{artifact_type}' found for issue #{issue_number}"
            )
            # Use the first (most recent) entry.
            entry = entries[0]

            # 1. Try GitHub comment storage first.
            github_content = provider.read_artifact_content_from_github(issue_number, artifact_type, entry.path)
            if github_content is not None:
                return ArtifactContent(
                    artifact_type=entry.artifact_type, path=entry.path, content=github_content, status=entry.status
                )

            # 2. Fall back to local filesystem.
            content = provider.read_artifact_content(entry.path)
            return ArtifactContent(
                artifact_type=entry.artifact_type, path=entry.path, content=content, status=entry.status
            )

        result = await asyncio.to_thread(_run)
        return {**result.model_dump(mode="json"), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
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
async def backlog_list_comments(
    issue_number: Annotated[int, Field(description="GitHub issue number (without #)")],
    limit: Annotated[int, Field(description="Maximum comments to return")] = 20,
    offset: Annotated[int, Field(description="Number of comments to skip")] = 0,
) -> dict:
    """List comments on a GitHub issue.

    Returns:
        Dict with comments (list of {id, author, created_at, updated_at, preview}),
        count, has_more, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_comments, issue_number=issue_number, limit=limit, offset=offset, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool
async def backlog_read_comment(
    issue_number: Annotated[int, Field(description="GitHub issue number (without #)")],
    comment_id: Annotated[
        int,
        Field(
            description="REST comment database ID (integer). Use the GitHub REST API or issue comment list to obtain this ID."
        ),
    ],
) -> dict:
    """Read the full body of a single comment on a GitHub issue.

    Returns:
        Dict with id (GraphQL node ID), author, created_at, updated_at,
        body (full Markdown — no truncation), and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.read_comment, issue_number=issue_number, comment_id=comment_id, output=out
        )
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
    # Use the git project root for dispatch plan path resolution.
    # BACKLOG_DIR now points to ~/.dh/projects/{slug}/backlog/ and cannot be
    # used to derive the project root by walking up with .parent.parent.
    return _ds.dispatch_plan_path(milestone_number, _models.get_repo_root())


def _try_register_dispatch_plan_artifact(issue_number: int, plan_path: Path) -> None:
    """Register the newly written dispatch plan file as a dispatch-plan artifact.

    Best-effort: logs a warning on any failure but never raises.  Called after
    ``dispatch_create_plan`` writes the plan file when the caller provides an
    associated GitHub issue number.

    Args:
        issue_number: GitHub issue number to register the artifact against.
        plan_path: Absolute or repo-relative path to the created plan file.
    """
    log = _logging.getLogger(__name__)
    try:
        repo = _models.DEFAULT_REPO
        if not repo:
            log.warning("dispatch_create_plan: skipping artifact registration — DEFAULT_REPO not set")
            return
        provider = GitHubArtifactProvider(
            repo=repo,
            root_worktree=_models._REPO_ROOT,  # noqa: SLF001
        )
        entry = ArtifactEntry(
            artifact_type=ArtifactType.DISPATCH_PLAN,
            path=str(plan_path),
            status=ArtifactStatus.CURRENT,
            agent="dispatch_create_plan",
        )
        manifest = provider.get_manifest(issue_number)
        updated_manifest = _artifact_registry.register(manifest, entry)
        provider.set_manifest(issue_number, updated_manifest)
        log.info("dispatch_create_plan: registered dispatch-plan artifact %s for issue #%d", plan_path, issue_number)
    except Exception:
        log.warning(
            "dispatch_create_plan: artifact registration failed for issue #%d (path=%s)",
            issue_number,
            plan_path,
            exc_info=True,
        )


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
        owner, repo_name = gh_repo.full_name.split("/", 1)
        open_issues = _sync_issues_graphql(gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number)
        closed_issues = _sync_issues_graphql(
            gh_repo, owner, repo_name, state="CLOSED", milestone_number=milestone_number
        )
        return [issue["number"] for issue in open_issues + closed_issues]

    try:
        current_numbers = await asyncio.to_thread(_fetch_milestone_issue_numbers)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    result = await asyncio.to_thread(_ds.detect_stale_plan, plan, current_numbers)
    return {"milestone_number": milestone_number, "plan_path": str(plan_path), **dataclasses.asdict(result)}


@mcp.tool
async def dispatch_create_plan(  # noqa: PLR0911
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    plan_yaml: Annotated[
        str,
        Field(
            description=(
                "YAML string containing the full dispatch plan. Must include top-level keys: "
                "'milestone' (with number, title, integration-branch), 'waves' (list of wave dicts "
                "with items), and optionally 'conflict-groups' and 'quality-gates'. "
                "Both kebab-case and snake_case keys are accepted."
            )
        ),
    ],
    overwrite: Annotated[
        bool,
        Field(
            description=(
                "Allow overwriting an existing plan file. When False (default), returns an error "
                "if plan/milestone-{N}-dispatch.yaml already exists."
            )
        ),
    ] = False,
    validate: Annotated[
        bool,
        Field(
            description=(
                "Run structural integrity validation after writing. When True (default), the response "
                "includes is_valid, errors, and warnings from validate_plan_integrity()."
            )
        ),
    ] = True,
    issue: Annotated[
        int | None,
        Field(
            description=(
                "Optional GitHub issue number to associate. When provided, auto-registers the plan "
                "file as a 'dispatch-plan' artifact on the issue."
            )
        ),
    ] = None,
) -> dict:
    """Create or overwrite a dispatch plan YAML file for a milestone.

    Accepts a YAML string, validates it against the ``DispatchPlan`` Pydantic
    model, writes it atomically to ``plan/milestone-{N}-dispatch.yaml``, and
    optionally validates structural integrity after writing.

    Args:
        milestone_number: GitHub milestone number.
        plan_yaml: Full dispatch plan as a YAML string.
        overwrite: When ``False`` (default) returns an error if the plan file
            already exists.
        validate: When ``True`` (default) runs ``validate_plan_integrity`` after
            writing and includes the result in the response.
        issue: Optional GitHub issue number.  When provided, auto-registers the
            plan file as a ``dispatch-plan`` artifact (best-effort).

    Returns:
        Success dict with ``milestone_number``, ``plan_path``, ``wave_count``,
        ``item_count``, ``is_valid``, ``errors``, ``warnings``, and ``messages``.
        Error dict contains an ``error`` key.
    """
    out = Output()
    plan_path = _dispatch_plan_path(milestone_number)

    # 1. Parse YAML
    try:
        yaml_parser = _YAML()
        parsed = yaml_parser.load(_StringIO(plan_yaml))
    except _YAMLError as exc:
        return {
            "error": f"Invalid YAML: {exc}",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }

    # 2. Verify parsed result is a mapping
    if not isinstance(parsed, dict):
        return {
            "error": "plan_yaml must be a YAML mapping (dict), not a list or scalar",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }

    # 3. Check milestone.number consistency; inject if absent
    milestone_section = parsed.get("milestone")
    if isinstance(milestone_section, dict):
        yaml_number = milestone_section.get("number")
        if yaml_number is not None and int(yaml_number) != milestone_number:
            return {
                "error": (
                    f"Milestone number mismatch: parameter is {milestone_number} "
                    f"but YAML milestone.number is {yaml_number}"
                ),
                "milestone_number": milestone_number,
                "plan_path": str(plan_path),
                **out.to_dict(),
            }
        if yaml_number is None:
            milestone_section["number"] = milestone_number
    else:
        # No milestone key — inject a minimal one so model_validate can proceed
        parsed["milestone"] = {"number": milestone_number}

    # 4. Validate against DispatchPlan
    try:
        plan = _ds.DispatchPlan.model_validate(parsed)
    except _ValidationError as exc:
        violations = "; ".join(f"{e['loc']}: {e['msg']}" for e in exc.errors())
        return {
            "error": f"Plan validation failed: {violations}",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }

    # 5. Check for existing file when overwrite is False
    if not overwrite and plan_path.exists():
        return {
            "error": (f"Plan file already exists: {plan_path}. Pass overwrite=True to replace it."),
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }

    # 6. Write atomically
    try:
        await asyncio.to_thread(_ds.write_dispatch_plan, plan, plan_path)
    except ValueError as exc:
        return {
            "error": f"Cannot write plan (symlink target rejected): {exc}",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }
    except OSError as exc:
        return {
            "error": f"Failed to write plan file: {exc}",
            "milestone_number": milestone_number,
            "plan_path": str(plan_path),
            **out.to_dict(),
        }

    out.info(f"Wrote dispatch plan to {plan_path}")

    # 7. Post-write validation
    is_valid: bool | None = None
    val_errors: list[str] = []
    val_warnings: list[str] = []
    if validate:
        val_result = await asyncio.to_thread(_ds.validate_plan_integrity, plan)
        is_valid = val_result.is_valid
        val_errors = list(val_result.errors)
        val_warnings = list(val_result.warnings)

    # 8. Artifact registration (best-effort)
    if issue is not None:
        _try_register_dispatch_plan_artifact(issue, plan_path)

    wave_count = len(plan.waves)
    item_count = sum(len(wave.items) for wave in plan.waves)

    return {
        "milestone_number": milestone_number,
        "plan_path": str(plan_path),
        "wave_count": wave_count,
        "item_count": item_count,
        "is_valid": is_valid,
        "errors": val_errors,
        "warnings": val_warnings,
        **out.to_dict(),
    }


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
        owner, repo_name = gh_repo.full_name.split("/", 1)
        issue_nodes: list[_IssueNode] = _sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number
        )
        items: list[_ImpactRadiusItem] = []
        ir_re = _re.compile(r"##\s+Impact\s+Radius\b(.*?)(?=\n##|\Z)", _re.IGNORECASE | _re.DOTALL)
        for issue in issue_nodes:
            body = issue["body"] or ""
            match = ir_re.search(body)
            impact_radius = match.group(1).strip() if match else ""
            items.append({"title": issue["title"], "issue": issue["number"], "impact_radius": impact_radius})
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


# ---------------------------------------------------------------------------
# artifact_migrate helpers
# ---------------------------------------------------------------------------

#: Lazily created YAML parser for migration helpers (preserve_quotes prevents
#: round-trip mutations when loading frontmatter).
_migrate_yaml: _YAML | None = None


def _get_migrate_yaml() -> _YAML:
    """Return (or lazily create) the shared YAML instance for migration.

    Returns:
        Configured ``YAML`` instance with ``preserve_quotes=True``.
    """
    global _migrate_yaml  # noqa: PLW0603
    if _migrate_yaml is None:
        _migrate_yaml = _YAML()
        _migrate_yaml.preserve_quotes = True
    return _migrate_yaml


#: Filename pattern → ArtifactType mapping (ordered — first match wins).
_MIGRATE_FILENAME_PATTERNS: list[tuple[_re.Pattern[str], ArtifactType]] = [
    (_re.compile(r"^feature-context-(.+)\.md$"), ArtifactType.FEATURE_CONTEXT),
    (_re.compile(r"^architect-(.+)\.md$"), ArtifactType.ARCHITECT),
    (_re.compile(r"^P\d+-(.+)\.yaml$"), ArtifactType.TASK_PLAN),
    (_re.compile(r"^T0-baseline-(.+)\.yaml$"), ArtifactType.T0_BASELINE),
    (_re.compile(r"^TN-verification-(.+)\.yaml$"), ArtifactType.TN_VERIFICATION),
]

#: Pattern matching markdown files in plan/codebase/ → codebase-analysis.
_MIGRATE_CODEBASE_PATTERN = _re.compile(r"^.+\.md$")


def _migrate_extract_issue(file_path: Path) -> int | None:
    """Read the ``issue`` field from YAML frontmatter or a bare YAML file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Integer issue number when found and parseable, ``None`` otherwise.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    yaml = _get_migrate_yaml()
    raw_data: object = None
    if file_path.suffix in {".yaml", ".yml"}:
        try:
            raw_data = yaml.load(text)
        except Exception:  # noqa: BLE001
            return None
    else:
        fm_match = _re.match(r"^---\r?\n(.*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)", text, _re.DOTALL)
        if not fm_match:
            return None
        try:
            raw_data = yaml.load(fm_match.group(1))
        except Exception:  # noqa: BLE001
            return None

    if isinstance(raw_data, dict):
        return _migrate_coerce_issue(raw_data.get("issue"))
    return None


def _migrate_coerce_issue(value: object) -> int | None:
    """Coerce a YAML value to a positive integer issue number.

    Args:
        value: Raw value from YAML (may be int, str, or None).

    Returns:
        Positive integer, or ``None``.
    """
    if value is None:
        return None
    try:
        n = int(str(value))
    except (ValueError, TypeError):
        return None
    return n if n > 0 else None


def _migrate_slug_from_path(file_path: Path) -> str:
    r"""Extract the slug from a plan filename.

    Strips known prefixes and the file extension.

    Args:
        file_path: Path object for the plan file.

    Returns:
        Slug string (e.g. ``"my-feature"``).
    """
    name = file_path.stem
    for prefix in ("feature-context-", "architect-", "T0-baseline-", "TN-verification-"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    p_match = _re.match(r"^P\d+-(.+)$", name)
    if p_match:
        return p_match.group(1)
    return name


def _migrate_find_issue_via_backlog(slug: str, backlog_items: list[dict]) -> int | None:
    """Match a slug against cached backlog items to find an issue number.

    Args:
        slug: Slug string extracted from the artifact filename.
        backlog_items: List of backlog item dicts (each has ``title``,
            ``number``, and optionally ``plan`` fields).

    Returns:
        Matched GitHub issue number, or ``None``.
    """
    slug_words = set(slug.replace("-", " ").replace("_", " ").lower().split())
    for item in backlog_items:
        title: str = item.get("title", "") or ""
        plan_path: str = item.get("plan", "") or ""
        issue_number = _migrate_coerce_issue(item.get("number"))
        if issue_number is None:
            continue
        if slug in plan_path:
            return issue_number
        title_words = set(title.replace("-", " ").replace("_", " ").lower().split())
        overlap = slug_words & title_words
        if len(overlap) >= max(1, len(slug_words) // 2):
            return issue_number
    return None


def _migrate_resolve_issue(file_path: Path, backlog_items: list[dict]) -> int | None:
    """Resolve the issue number for a file via frontmatter or slug fallback.

    Args:
        file_path: Absolute path to the artifact file.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Resolved issue number, or ``None``.
    """
    issue = _migrate_extract_issue(file_path)
    if issue is None:
        slug = _migrate_slug_from_path(file_path)
        issue = _migrate_find_issue_via_backlog(slug, backlog_items)
    return issue


def _migrate_classify_plan_file(file_path: Path) -> ArtifactType | None:
    """Classify a plan file by its filename pattern.

    Args:
        file_path: Path to the file.

    Returns:
        Matching ``ArtifactType``, or ``None``.
    """
    name = file_path.name
    for pattern, artifact_type in _MIGRATE_FILENAME_PATTERNS:
        if pattern.match(name):
            return artifact_type
    return None


_MigrateCandidate = tuple[str, ArtifactType, int | None, str | None]

#: Return type for candidate discovery — (actionable candidates, filtered-out count).
_MigrateDiscoveryResult = tuple[list[_MigrateCandidate], int]


def _migrate_make_candidate(
    rel: str, atype: ArtifactType, issue: int | None, issue_filter: int | None
) -> _MigrateCandidate | None:
    """Build a candidate tuple, returning ``None`` when the file is filtered out.

    When ``issue_filter`` is set, candidates whose resolved issue does not
    match are excluded entirely (counted as filtered by the caller) rather
    than included as skipped entries.  This avoids building a 500-entry
    skipped list when a specific issue is requested.

    Args:
        rel: Repo-relative path string.
        atype: Resolved artifact type.
        issue: Resolved issue number or ``None``.
        issue_filter: When set, candidates not matching this issue are
            excluded (returns ``None``).

    Returns:
        ``(rel, atype, issue, skip_reason)`` tuple, or ``None`` when filtered.
    """
    if issue_filter is not None and (issue is None or issue != issue_filter):
        return None
    if issue is None:
        return (rel, atype, issue, "no issue number found")
    return (rel, atype, issue, None)


def _migrate_scan_codebase_dir(
    codebase_dir: Path, repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/codebase/`` for markdown codebase-analysis files.

    Args:
        codebase_dir: Absolute path to the ``plan/codebase/`` directory.
        repo_root: Absolute path to the repository root.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for child in codebase_dir.iterdir():
        if not (child.is_file() and _MIGRATE_CODEBASE_PATTERN.match(child.name)):
            continue
        rel = child.relative_to(repo_root).as_posix()
        issue = _migrate_resolve_issue(child, backlog_items)
        candidate = _migrate_make_candidate(rel, ArtifactType.CODEBASE_ANALYSIS, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_scan_plan_dir(
    plan_dir: Path, repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/`` (excluding subdirectories other than ``codebase/``).

    Args:
        plan_dir: Absolute path to the ``plan/`` directory.
        repo_root: Absolute path to the repository root.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for file_path in plan_dir.iterdir():
        if file_path.is_dir():
            if file_path.name == "codebase":
                sub_results, sub_filtered = _migrate_scan_codebase_dir(
                    file_path, repo_root, issue_filter, backlog_items
                )
                results.extend(sub_results)
                filtered += sub_filtered
            continue
        if not file_path.is_file():
            continue
        atype = _migrate_classify_plan_file(file_path)
        if atype is None:
            continue
        rel = file_path.relative_to(repo_root).as_posix()
        issue = _migrate_resolve_issue(file_path, backlog_items)
        candidate = _migrate_make_candidate(rel, atype, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_discover_candidates(
    repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan plan/ and research/ for artifact files.

    When ``issue_filter`` is set, only candidates linked to that issue are
    returned — non-matching files are counted in ``filtered_count`` instead
    of being included as skipped entries.  This prevents the caller from
    building a 500+ entry skipped list when a specific issue is requested.

    Args:
        repo_root: Absolute path to the repository root.
        issue_filter: When set, only candidates linked to this issue number
            are included in the returned list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)`` where ``candidates`` is a
        list of ``(rel_path, artifact_type, issue_number, skip_reason)``
        tuples and ``filtered_count`` is the number of files excluded by the
        issue filter.
    """
    candidates: list[_MigrateCandidate] = []
    filtered = 0

    plan_dir = _dh_paths.plan_dir(repo_root)
    if plan_dir.is_dir():
        plan_candidates, plan_filtered = _migrate_scan_plan_dir(plan_dir, repo_root, issue_filter, backlog_items)
        candidates.extend(plan_candidates)
        filtered += plan_filtered

    research_dir = repo_root / "research"
    if research_dir.is_dir():
        for file_path in research_dir.rglob("*.md"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(repo_root).as_posix()
            issue = _migrate_resolve_issue(file_path, backlog_items)
            candidate = _migrate_make_candidate(rel, ArtifactType.RESEARCH, issue, issue_filter)
            if candidate is None:
                filtered += 1
            else:
                candidates.append(candidate)

    return candidates, filtered


def _migrate_register_one(
    provider: GitHubArtifactProvider, rel_path: str, artifact_type: ArtifactType, issue_number: int
) -> tuple[bool, str]:
    """Register a single artifact, uploading content when available.

    Idempotent — the registry upserts on (artifact_type, path).

    Args:
        provider: Initialised ``GitHubArtifactProvider`` instance.
        rel_path: Repo-relative path string.
        artifact_type: Resolved artifact type.
        issue_number: GitHub issue number (must be positive).

    Returns:
        Tuple of ``(success: bool, message: str)``.
    """
    entry = ArtifactEntry(
        artifact_type=artifact_type,
        path=rel_path,
        status=ArtifactStatus.CURRENT,
        created_at=_datetime.now(UTC).isoformat(),
        agent="artifact-migrate",
    )
    manifest = provider.get_manifest(issue_number)
    existed = any(e.artifact_type == artifact_type and e.path == rel_path for e in manifest.artifacts)
    updated_manifest = _artifact_registry.register(manifest, entry)
    provider.set_manifest(issue_number, updated_manifest)

    local_content = provider.read_local_artifact_content(rel_path)
    if local_content is not None:
        provider.store_artifact_content(issue_number, str(artifact_type), rel_path, local_content)
        content_note = " (content uploaded)"
    else:
        content_note = " (no local file — manifest-only)"

    action = "updated" if existed else "added"
    return True, f"{action}{content_note}"


# ---------------------------------------------------------------------------
# artifact_migrate helpers (dry-run / live-run)
# ---------------------------------------------------------------------------


def _migrate_dry_run(issue_number: int | None) -> dict:
    """Discover candidates and return a preview without making any API calls.

    Args:
        issue_number: Optional issue filter passed to candidate discovery.

    Returns:
        Dict with ``dry_run``, ``would_register``, ``would_skip``,
        ``details``, and ``verify`` keys.  ``details`` contains only entries
        that would be registered or cannot be registered due to a missing
        issue number — filtered entries are counted in ``would_skip`` but not
        included individually.
    """
    repo_root = _models._REPO_ROOT  # noqa: SLF001
    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, [])

    details: list[dict] = []
    would_register = 0
    would_skip = filtered_count  # filtered-out files count as skipped
    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Include no-issue entries in details so the caller knows which
            # files could not be resolved — but do NOT include filter skips.
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"skip — {skip_reason}"})
            would_skip += 1
        else:
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": "would register"})
            would_register += 1

    verify = (
        f"Use artifact_list(issue_number={issue_number}) to verify registered entries"
        if issue_number is not None
        else "Use artifact_list(issue_number=<N>) per issue to verify registered entries"
    )
    return {
        "dry_run": True,
        "would_register": would_register,
        "would_skip": would_skip,
        "details": details,
        "verify": verify,
    }


def _migrate_queue_manifest_only(
    provider: GitHubArtifactProvider, issue_number: int, candidates: list[_MigrateCandidate], out: Output
) -> list[_MigrateCandidate]:
    """Append manifest-only entries (content_stored=False) to the candidate list.

    Called when ``issue_number`` is provided so already-registered entries
    without uploaded content are re-processed to trigger the auto-upload path.

    Args:
        provider: Initialised provider used to read the manifest.
        issue_number: Issue whose manifest to inspect.
        candidates: Existing candidate list (may be mutated by extension).
        out: Output accumulator for warnings.

    Returns:
        Extended candidate list.
    """
    try:
        manifest = provider.get_manifest(issue_number)
    except Exception:  # noqa: BLE001
        out.warn(f"Could not read existing manifest for issue #{issue_number}. Skipping manifest check.")
        return candidates

    result = list(candidates)
    for entry in manifest.artifacts:
        # Re-queue every registered entry so the auto-upload path can attempt
        # content upload for entries where no content was stored yet.
        # _migrate_register_one is idempotent (upserts on type+path).
        already_queued = any(
            rel == entry.path and atype == entry.artifact_type
            for rel, atype, _, skip_reason in candidates
            if skip_reason is None
        )
        if not already_queued:
            result.append((entry.path, entry.artifact_type, issue_number, None))
            out.warn(f"Queued manifest-only entry for re-registration: {entry.path!r}")
    return result


def _migrate_live_run(issue_number: int | None, out: Output) -> dict:
    """Execute the live migration against GitHub.

    Args:
        issue_number: Optional issue filter.
        out: Output accumulator (warnings written here).

    Returns:
        Dict with ``migrated``, ``skipped``, ``failed``, ``details``, and
        ``verify``.  ``details`` contains only migrated and failed entries —
        skipped entries are counted in ``skipped`` but not listed individually
        to keep the response compact.
    """
    repo_root = _models._REPO_ROOT  # noqa: SLF001
    provider = _get_artifact_provider()

    backlog_items: list[dict] = []
    try:
        raw = operations.list_items()
        if isinstance(raw, list):
            backlog_items = raw
        elif isinstance(raw, dict):
            raw_backlog = raw.get("items", [])
            backlog_items = [x for x in raw_backlog if isinstance(x, dict)] if isinstance(raw_backlog, list) else []
    except Exception:  # noqa: BLE001
        out.warn("Could not fetch backlog items for slug matching. Continuing without fallback.")

    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, backlog_items)

    if issue_number is not None:
        candidates = _migrate_queue_manifest_only(provider, issue_number, candidates, out)

    migrated = 0
    skipped = filtered_count  # files excluded by issue filter count as skipped
    failed = 0
    run_details: list[dict] = []

    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Count no-issue files as skipped; do NOT add to run_details to
            # avoid a 500-entry skipped list in the response.
            skipped += 1
            continue

        assert issue is not None  # skip_reason is None only when issue resolved  # noqa: S101
        try:
            _ok, action_msg = _migrate_register_one(provider, rel_path, atype, issue)
            migrated += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": action_msg})
        except Exception as exc:  # noqa: BLE001
            failed += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"FAILED: {exc}"})

    verify = (
        f"Use artifact_read(issue_number={issue_number}, artifact_type='<type>') "
        f"or artifact_list(issue_number={issue_number}) to verify"
        if issue_number is not None
        else "Use artifact_list(issue_number=<N>) per issue to verify registered entries"
    )
    return {"migrated": migrated, "skipped": skipped, "failed": failed, "details": run_details, "verify": verify}


# ---------------------------------------------------------------------------
# artifact_migrate MCP tool
# ---------------------------------------------------------------------------


@mcp.tool
async def artifact_migrate(
    issue_number: Annotated[
        int | None, Field(description="Migrate artifacts for a specific issue number only. Omit to scan all issues.")
    ] = None,
    dry_run: Annotated[
        bool, Field(description="When true, report what would be migrated without making any API calls.")
    ] = False,
) -> dict:
    """Migrate existing plan/research artifacts into the artifact manifest system.

    Scans ``plan/`` and ``research/`` directories for artifact files,
    determines the artifact type from the filename pattern, extracts the
    linked GitHub issue number from YAML frontmatter (falling back to slug
    matching against backlog items), and calls the artifact_register logic
    for each discovered file.

    When ``issue_number`` is provided the tool also checks the existing
    manifest for that issue: any already-registered entry that has
    ``content_stored=False`` is re-registered so the auto-upload path can
    run and upload the local file content.

    Safe to re-run — the registry upserts on ``(artifact_type, path)``
    so existing entries are updated in-place rather than duplicated.

    Returns:
        Dict with ``migrated`` (int), ``skipped`` (int), ``failed`` (int),
        and ``details`` (list of per-artifact outcome dicts).  Each detail
        dict contains ``path``, ``type``, ``issue``, and ``outcome``.
        On error, dict contains an ``error`` key.
    """
    out = Output()

    if dry_run:
        try:
            result = await asyncio.to_thread(_migrate_dry_run, issue_number)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Discovery failed: {exc}", **out.to_dict()}
        return {**result, **out.to_dict()}

    try:
        result = await asyncio.to_thread(_migrate_live_run, issue_number, out)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), **out.to_dict()}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Migration failed: {exc}", **out.to_dict()}

    return {**result, **out.to_dict()}


# ---------------------------------------------------------------------------
# Dispatch execution tools — state management + process spawning
# ---------------------------------------------------------------------------

#: Lazily created singleton DispatchStateManager.
_dispatch_state_mgr: _DispatchStateManager | None = None

#: Path to the spawn.py script resolved once at module level.
_SPAWN_SCRIPT: Path = Path(__file__).parent.parent / "skills" / "kage-bunshin" / "scripts" / "spawn.py"


def _project_stub() -> str:
    """Derive a stable project slug from the repository root path.

    Converts the absolute path of the project root (e.g.
    ``/home/user/repos/my_project``) to a hyphen-separated slug by replacing
    all ``/`` separators with ``-`` and stripping the leading ``-``.

    Returns:
        Slug string, e.g. ``home-user-repos-my_project``.
    """
    project_root = _models.get_repo_root()
    return str(project_root).lstrip("/").replace("/", "-")


def _dispatch_state_manager() -> _DispatchStateManager:
    """Return the lazily created DispatchStateManager singleton.

    Creates the state database under ``~/.dh/projects/{project-stub}/`` on
    first call. The parent directory is created if necessary.

    Returns:
        Shared ``DispatchStateManager`` instance for this server process.
    """
    global _dispatch_state_mgr  # noqa: PLW0603
    if _dispatch_state_mgr is None:
        db_path = Path.home() / ".dh" / "projects" / _project_stub() / "dispatch-state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _dispatch_state_mgr = _DispatchStateManager(db_path)
    return _dispatch_state_mgr


@mcp.tool
async def dispatch_wave_start(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number from dispatch plan (1-based)")],
    items: Annotated[
        list[dict[str, object]], Field(description="List of items, each with 'issue' (int) and 'title' (str) keys")
    ],
) -> dict:
    """Record the start of a dispatch wave.

    Creates wave and item entries in the state database. Items are
    initialised with status ``pending``. Call this before spawning
    processes for a wave.

    Returns:
        Dict with ``milestone``, ``wave_num``, ``items_count``, ``status``,
        and ``messages``/``warnings``. Returns ``error`` if the wave already
        exists or if an item entry is malformed.
    """
    item_records = [
        _DispatchItemRecord(
            milestone=milestone, wave_num=wave_num, issue=int(str(item["issue"])), title=str(item.get("title", ""))
        )
        for item in items
    ]
    try:
        wave: _DispatchWaveRecord = await asyncio.to_thread(
            _dispatch_state_manager().create_wave, milestone, wave_num, item_records
        )
    except sqlite3.IntegrityError:
        return {
            "error": f"Wave {wave_num} already exists for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }
    return {
        "milestone": wave.milestone,
        "wave_num": wave.wave_num,
        "items_count": len(wave.items),
        "status": wave.status,
        "messages": [f"Wave {wave_num} created with {len(wave.items)} items"],
        "warnings": [],
        "errors": [],
    }


@mcp.tool
async def dispatch_item_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    issue: Annotated[int, Field(description="Issue number of the item")],
    status: Annotated[str, Field(description="New status: 'complete', 'failed', or 'skipped'")],
    result: Annotated[str, Field(description="Result summary or JSON from result file")] = "",
    error: Annotated[str, Field(description="Error details on failure")] = "",
    cost: Annotated[float | None, Field(description="USD cost if available from claude output")] = None,
) -> dict:
    """Record completion or failure of a dispatch item.

    Looks up the item by milestone + issue across all waves. Updates
    status, result/error data, and completion timestamp.

    Returns:
        Dict with ``milestone``, ``issue``, ``wave_num``, ``status``,
        ``messages``/``warnings``. Returns ``error`` key if item not found.
    """
    mgr = _dispatch_state_manager()

    def _find_and_update() -> dict:
        waves = mgr.get_all_waves(milestone)
        for wave in waves:
            for item in wave.items:
                if item.issue == issue:
                    if status == "complete":
                        mgr.set_item_complete(
                            milestone=milestone, wave_num=wave.wave_num, issue=issue, result=result, cost=cost
                        )
                    elif status == "failed":
                        mgr.set_item_failed(milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error)
                    elif status == "skipped":
                        # Treat skipped the same as failed with a standard message.
                        mgr.set_item_failed(
                            milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error or "skipped"
                        )
                    else:
                        return {
                            "error": f"Invalid status '{status}': must be 'complete', 'failed', or 'skipped'",
                            "milestone": milestone,
                            "issue": issue,
                        }
                    return {
                        "milestone": milestone,
                        "issue": issue,
                        "wave_num": wave.wave_num,
                        "status": status,
                        "messages": [f"Item #{issue} marked {status} in wave {wave.wave_num}"],
                        "warnings": [],
                        "errors": [],
                    }
        return {
            "error": f"Item #{issue} not found in any wave for milestone {milestone}",
            "milestone": milestone,
            "issue": issue,
        }

    return await asyncio.to_thread(_find_and_update)


@mcp.tool
async def dispatch_wave_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number to query (1-based)")],
) -> dict:
    """Query the current status of a dispatch wave.

    Returns item-level detail grouped by status, with elapsed time and
    progress counts. Checks PIDs for in-progress items and marks dead
    ones as failed before returning.

    Returns:
        Dict with :class:`~backlog_core.models.DispatchWaveSummary` fields,
        or ``error`` if wave not found.
    """
    mgr = _dispatch_state_manager()
    warnings: list[str] = []

    def _check_and_query() -> _DispatchWaveRecord | None:
        stale = mgr.check_stale_pids()
        warnings.extend(
            f"PID {stale_item.pid} for issue #{stale_item.issue} is dead — marked failed"
            for stale_item in stale
            if stale_item.milestone == milestone and stale_item.wave_num == wave_num
        )
        return mgr.get_wave(milestone, wave_num)

    wave = await asyncio.to_thread(_check_and_query)

    if wave is None:
        return {
            "error": f"Wave {wave_num} not found for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }

    items = wave.items
    pending = sum(1 for i in items if i.status == "pending")
    in_progress = sum(1 for i in items if i.status == "in-progress")
    complete = sum(1 for i in items if i.status == "complete")
    failed = sum(1 for i in items if i.status == "failed")
    skipped = sum(1 for i in items if i.status == "skipped")

    elapsed: float | None = None
    if wave.started_at:
        try:
            started = _datetime.fromisoformat(wave.started_at)
            ended = _datetime.fromisoformat(wave.completed_at) if wave.completed_at else _datetime.now(UTC)
            elapsed = (ended - started).total_seconds()
        except ValueError:
            pass

    summary = _DispatchWaveSummary(
        milestone=milestone,
        wave_num=wave_num,
        status=wave.status,
        total_items=len(items),
        pending=pending,
        in_progress=in_progress,
        complete=complete,
        failed=failed,
        skipped=skipped,
        started_at=wave.started_at,
        completed_at=wave.completed_at,
        elapsed_seconds=elapsed,
        items=items,
    )
    return {**summary.model_dump(), "messages": [], "warnings": warnings, "errors": []}


@dataclasses.dataclass
class _WaveCounters:
    """Mutable counters shared across concurrent item coroutines in one wave.

    Using a dataclass avoids ``nonlocal`` declarations in nested async
    functions, which are not thread/coroutine-safe without extra locking and
    cause PLR0914 (too many local variables) in the outer function.
    """

    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_done: int = 0  # cumulative across all waves so far


def _build_spawn_cmd(
    milestone: int, issue_num: int, item_title: str, model: str, phase: str, integration_branch: str
) -> list[str]:
    """Construct the spawn.py subprocess command for one dispatch item.

    Args:
        milestone: GitHub milestone number.
        issue_num: GitHub issue number for the item.
        item_title: Human-readable title used as the prompt suffix.
        model: Model identifier string passed to spawn.py.
        phase: ``'work'`` adds ``--worktree``; any other value omits it.
        integration_branch: If non-empty, appended as ``--branch <value>``.

    Returns:
        List of strings suitable for ``asyncio.create_subprocess_exec``.
    """
    cmd: list[str] = ["uv", "run", str(_SPAWN_SCRIPT), "--model", model, "--name", f"dispatch-{milestone}-{issue_num}"]
    if phase == "work":
        cmd.append("--worktree")
    if integration_branch:
        cmd += ["--branch", integration_branch]
    cmd.append(f"Work on issue #{issue_num}: {item_title}")
    return cmd


async def _poll_until_done(
    mgr: _DispatchStateManager, milestone: int, wave_num: int, issue_num: int, pid: int, result_file: str
) -> tuple[bool, float | None]:
    """Poll until a spawned item completes or its PID dies.

    Args:
        mgr: State manager used to write terminal status.
        milestone: GitHub milestone number.
        wave_num: Wave number (1-based).
        issue_num: GitHub issue number for the item.
        pid: OS process ID of the spawned session (``-1`` when unknown).
        result_file: Filesystem path where spawn.py writes its result JSON.

    Returns:
        ``(succeeded, cost)`` — ``succeeded`` is ``True`` when the result
        file was found; ``cost`` is the USD amount extracted from the result
        JSON or ``None``.
    """
    rf_path = Path(result_file) if result_file else None

    while True:
        await asyncio.sleep(2)

        if rf_path is not None:
            result_ready = await asyncio.to_thread(lambda: rf_path.exists() and rf_path.stat().st_size > 0)
            if result_ready:
                try:
                    content = await asyncio.to_thread(lambda: rf_path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    content = ""
                item_cost: float | None = None
                try:
                    rj = _json.loads(content)
                    item_cost = float(rj.get("cost", 0)) or None
                except (ValueError, KeyError, TypeError):
                    pass
                await asyncio.to_thread(
                    mgr.set_item_complete, milestone, wave_num, issue_num, content[:4096], item_cost
                )
                return True, item_cost

        pid_alive = True
        if pid > 0:
            try:
                _os.kill(pid, 0)
            except ProcessLookupError:
                pid_alive = False
            except PermissionError:
                pass

        if not pid_alive:
            error_msg = f"Process died unexpectedly (PID {pid})"
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
            return False, None


async def _run_spawn_item(
    mgr: _DispatchStateManager,
    semaphore: asyncio.Semaphore,
    counters: _WaveCounters,
    warnings: list[str],
    ctx: Context,
    milestone: int,
    wave_num: int,
    issue_num: int,
    item_title: str,
    total_items: int,
    model: str,
    phase: str,
    integration_branch: str,
) -> None:
    """Spawn one dispatch item, monitor it, and update shared counters.

    Args:
        mgr: Dispatch state manager.
        semaphore: Concurrency throttle — held for the item's full lifetime.
        counters: Shared mutable counters updated on completion.
        warnings: List to append failure messages to.
        ctx: FastMCP context for progress and log reporting.
        milestone: GitHub milestone number.
        wave_num: Wave number (1-based).
        issue_num: GitHub issue number.
        item_title: Human-readable title for the prompt.
        total_items: Total items across all waves (for progress reporting).
        model: Model identifier string.
        phase: ``'work'`` or ``'groom'``.
        integration_branch: Branch name for ``--branch`` flag; empty to omit.
    """
    async with semaphore:
        cmd = _build_spawn_cmd(milestone, issue_num, item_title, model, phase, integration_branch)
        pid = -1
        result_file = ""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_text = stdout_bytes.decode(errors="replace").strip()

            try:
                spawn_data = _json.loads(stdout_text)
                pid = int(spawn_data.get("pid", -1))
                result_file = str(spawn_data.get("result_file", ""))
            except (ValueError, KeyError):
                error_msg = f"spawn.py non-JSON output: {stdout_text[:200]}"
                await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
                counters.failed += 1
                counters.total_done += 1
                warnings.append(f"Item #{issue_num} failed: {error_msg}")
                await ctx.report_progress(counters.total_done, total_items)
                return

            if pid > 0:
                await asyncio.to_thread(mgr.set_item_in_progress, milestone, wave_num, issue_num, pid)

            succeeded, _ = await _poll_until_done(mgr, milestone, wave_num, issue_num, pid, result_file)
            if succeeded:
                counters.completed += 1
            else:
                counters.failed += 1
                warnings.append(f"Item #{issue_num} failed: process exited with no result")

        except Exception as exc:  # noqa: BLE001
            error_msg = f"Spawn error: {exc}"
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
            counters.failed += 1
            warnings.append(f"Item #{issue_num} failed: {error_msg}")

        counters.total_done += 1
        await ctx.report_progress(counters.total_done, total_items)
        await ctx.info(
            f"Wave {wave_num}: {counters.total_done}/{total_items} items — "
            f"{counters.completed} done, {counters.failed} failed"
        )


@mcp.tool(task=True)
async def dispatch_spawn(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[
        int, Field(description="Starting wave number (1-based). Runs this wave and all subsequent waves")
    ],
    ctx: Context,
    max_concurrent: Annotated[int, Field(description="Maximum concurrent spawned sessions")] = 3,
    model: Annotated[str, Field(description="Model identifier for spawned sessions")] = "sonnet",
    phase: Annotated[
        str, Field(description="Dispatch phase: 'groom' (no worktree) or 'work' (with worktree)")
    ] = "work",
) -> dict:
    """Spawn and monitor kage-bunshin sessions for a dispatch wave.

    Runs as a background task (``task=True``). Returns a task ID immediately.
    The background task:

    1. Detects and marks stale PIDs from prior runs.
    2. Reads the dispatch plan to get wave items.
    3. Iterates waves from ``wave_num`` through the last wave in the plan.
    4. For each wave: spawns items throttled to ``max_concurrent``, monitors
       PIDs, reads result files, and reports progress via
       ``ctx.report_progress()``.
    5. On item failure: marks failed, continues with remaining items.
    6. Returns a :class:`~backlog_core.models.DispatchSpawnSummary` when all
       waves complete.

    Returns:
        Dict with :class:`~backlog_core.models.DispatchSpawnSummary` fields
        on completion, or ``error`` on failure.
    """
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, _dispatch_plan_path(milestone))
    except FileNotFoundError:
        return {"error": f"Dispatch plan not found for milestone {milestone}", "milestone": milestone}
    except ValueError as exc:
        return {"error": f"Invalid dispatch plan: {exc}", "milestone": milestone}

    mgr = _dispatch_state_manager()
    await asyncio.to_thread(mgr.check_stale_pids)

    start_time = _time.monotonic()
    integration_branch: str = plan.milestone.integration_branch
    all_waves = [w for w in plan.waves if w.wave >= wave_num]
    total_items = sum(len(w.items) for w in all_waves)
    per_wave_summaries: list[_DispatchWaveSummary] = []
    warnings: list[str] = []
    semaphore = asyncio.Semaphore(max_concurrent)
    overall = _WaveCounters()

    for wave in all_waves:
        with contextlib.suppress(sqlite3.IntegrityError):
            await asyncio.to_thread(
                mgr.create_wave,
                milestone,
                wave.wave,
                [
                    _DispatchItemRecord(milestone=milestone, wave_num=wave.wave, issue=i.issue, title=i.title)
                    for i in wave.items
                ],
            )

        wave_counters = _WaveCounters(total_done=overall.total_done)
        await asyncio.gather(*[
            _run_spawn_item(
                mgr=mgr,
                semaphore=semaphore,
                counters=wave_counters,
                warnings=warnings,
                ctx=ctx,
                milestone=milestone,
                wave_num=wave.wave,
                issue_num=item.issue,
                item_title=item.title,
                total_items=total_items,
                model=model,
                phase=phase,
                integration_branch=integration_branch,
            )
            for item in wave.items
        ])

        overall.completed += wave_counters.completed
        overall.failed += wave_counters.failed
        overall.total_done = wave_counters.total_done

        fetched = await asyncio.to_thread(mgr.get_wave, milestone, wave.wave)
        per_wave_summaries.append(
            _DispatchWaveSummary(
                milestone=milestone,
                wave_num=wave.wave,
                status=fetched.status if fetched else "complete",
                total_items=len(wave.items),
                pending=0,
                in_progress=0,
                complete=wave_counters.completed,
                failed=wave_counters.failed,
                skipped=wave_counters.skipped,
            )
        )

    elapsed_seconds = _time.monotonic() - start_time

    def _sum_costs() -> float | None:
        all_w = mgr.get_all_waves(milestone)
        costs = [i.cost for w in all_w if w.wave_num >= wave_num for i in w.items if i.cost is not None]
        return sum(costs) if costs else None

    total_cost = await asyncio.to_thread(_sum_costs)
    summary = _DispatchSpawnSummary(
        milestone=milestone,
        waves_executed=len(all_waves),
        total_items=total_items,
        completed=overall.completed,
        failed=overall.failed,
        skipped=overall.skipped,
        elapsed_seconds=elapsed_seconds,
        per_wave=per_wave_summaries,
        total_cost=total_cost,
    )
    return {
        **summary.model_dump(),
        "messages": [f"Dispatch complete: {overall.completed}/{total_items} items succeeded"],
        "warnings": warnings,
        "errors": [],
    }


from agent_profile import mcp as _agent_profile_mcp

mcp.mount(_agent_profile_mcp, namespace="profile")

if __name__ == "__main__":
    mcp.run()
