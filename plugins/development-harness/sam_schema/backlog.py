"""Grouped Typer commands for provider-neutral backlog operations."""

from __future__ import annotations

import shutil
import subprocess
from typing import Annotated, Literal

import typer
from backlog_core import operations
from backlog_core.models import BacklogError, Output

from sam_schema import cli_output

app = typer.Typer(name="backlog", help="Backlog item operations.", no_args_is_help=True)


def _emit(result: object, output: Output) -> None:
    cli_output.output_json(result)
    for message in output.messages:
        typer.echo(message, err=True)
    for warning in output.warnings:
        typer.echo(f"Warning: {warning}", err=True)
    for error in output.errors:
        typer.echo(f"Error: {error}", err=True)


def _filter_pairs(filters: list[str] | None) -> dict[str, str] | None:
    if not filters:
        return None
    result: dict[str, str] = {}
    for item in filters:
        key, separator, value = item.partition("=")
        if not separator or not key:
            cli_output.err(f"--filter expects 'key=value', got: {item!r}")
        result[key] = value
    return result


@app.command("add")
def add(
    title: Annotated[str, typer.Option("--title", help="Backlog item title")],
    description: Annotated[str, typer.Option("--description", help="Item description")] = "",
    priority: Annotated[str, typer.Option("--priority", help="Priority level (P1/P2/P3)")] = "P1",
    source: Annotated[str, typer.Option("--source", help="Source of the item")] = "Not specified",
    type_: Annotated[str, typer.Option("--type", help="Item type (Feature/Bug/etc.)")] = "Feature",
    force: Annotated[bool, typer.Option("--force", help="Force creation even if duplicate suspected")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Add a new item to the backlog."""
    output = Output()
    result = operations.add_item(
        title=title,
        description=description,
        priority=priority,
        source=source,
        type_=type_,
        force=force,
        repo=repo,
        output=output,
    )
    _emit(result, output)


@app.command("list")
def list_items(
    refresh: Annotated[
        bool, typer.Option("--refresh", help="Refresh from the selected backend provider before listing")
    ] = False,
    label: Annotated[str | None, typer.Option("--label", help="Filter by label")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Filter by section")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Filter by status")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Filter by title substring")] = None,
    type_: Annotated[str | None, typer.Option("--type", help="Filter by item type")] = None,
    topic: Annotated[str | None, typer.Option("--topic", help="Filter by topic")] = None,
    include_closed: Annotated[bool, typer.Option("--include-closed", help="Include closed items")] = False,
    filters: Annotated[list[str] | None, typer.Option("--filter", help="Filter by key=value (repeatable)")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """List backlog items, optionally filtered."""
    output = Output()
    result = operations.list_items(
        from_github=refresh,
        label=label,
        section=section,
        status=status,
        title=title,
        type_=type_,
        topic=topic,
        include_closed=include_closed,
        filter_by_key=_filter_pairs(filters),
        repo=repo,
        output=output,
    )
    _emit(result, output)


@app.command("view")
def view(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    offset: Annotated[int, typer.Option("--offset", min=0, help="Pagination offset")] = 0,
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum items to return (0 = all)")] = 0,
    show: Annotated[str | None, typer.Option("--show", help="Show a section or field")] = None,
    since: Annotated[str | None, typer.Option("--since", help="Filter entries since date/commit")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Show only a named section")] = None,
) -> None:
    """View a single backlog item by selector."""
    output = Output()
    result = operations.view_item(
        selector=selector, repo=repo, offset=offset, limit=limit, show=show, since=since, output=output, section=section
    )
    _emit(result, output)


@app.command("update")
def update(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    plan: Annotated[str | None, typer.Option("--plan", help="Set plan reference")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Set status")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Section name for content update")] = None,
    content: Annotated[str | None, typer.Option("--content", help="Content to write into section")] = None,
    title: Annotated[str | None, typer.Option("--title", help="New title")] = None,
    description: Annotated[str | None, typer.Option("--description", help="New description")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Update a backlog item's fields."""
    output = Output()
    result = operations.update_item(
        selector=selector,
        plan=plan,
        status=status,
        section=section,
        content=content,
        title=title,
        description=description,
        repo=repo,
        output=output,
    )
    _emit(result, output)


@app.command("close")
def close(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    reason: Annotated[str, typer.Option("--reason", help="Categorized reason for closing")],
    reference: Annotated[str, typer.Option("--reference", help="Reference URL or issue number")] = "",
    comment: Annotated[str, typer.Option("--comment", help="Closing comment")] = "",
    cleanup: Annotated[bool, typer.Option("--cleanup", help="Clean up local files after closing")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force close even if checks fail")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Dismiss a backlog item without completion."""
    output = Output()
    result = operations.close_item(
        selector=selector,
        reason=reason,
        reference=reference,
        comment=comment,
        cleanup=cleanup,
        force=force,
        repo=repo,
        output=output,
    )
    _emit(result, output)


@app.command("resolve")
def resolve(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    summary: Annotated[str, typer.Option("--summary", help="Completion summary")],
    plan: Annotated[str, typer.Option("--plan", help="Plan reference applied")] = "",
    method: Annotated[str, typer.Option("--method", help="Method used to resolve")] = "",
    notes: Annotated[str, typer.Option("--notes", help="Additional notes")] = "",
    follow_ups: Annotated[str, typer.Option("--follow-ups", help="Follow-up items")] = "",
    findings: Annotated[str, typer.Option("--findings", help="Findings or evidence")] = "",
    cleanup: Annotated[bool, typer.Option("--cleanup", help="Clean up local files after resolving")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force resolve even if checks fail")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Mark a backlog item as done and close the issue with evidence."""
    output = Output()
    result = operations.resolve_item(
        selector=selector,
        summary=summary,
        plan=plan,
        method=method,
        notes=notes,
        follow_ups=follow_ups,
        findings=findings,
        cleanup=cleanup,
        force=force,
        repo=repo,
        output=output,
    )
    _emit(result, output)


@app.command("link-followup")
def link_followup(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    followup_to: Annotated[str, typer.Option("--to", help="Originating plan or task ID")],
) -> None:
    """Link a backlog item to its originating plan or task."""
    output = Output()
    result = operations.link_followup(selector=selector, followup_to=followup_to, output=output)
    _emit(result, output)


@app.command("list-followups")
def list_followups(
    followup_to: Annotated[str, typer.Option("--followup-to", help="Originating plan or task ID")],
) -> None:
    """List backlog items linked to an originating plan or task."""
    output = Output()
    result = operations.list_followups(followup_to=followup_to, output=output)
    _emit(result, output)


@app.command("groom")
def groom(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    section: Annotated[str | None, typer.Option("--section", help="Section name for content")] = None,
    content: Annotated[str | None, typer.Option("--content", help="Content to write into section")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Write groomed content into a backlog item file."""
    output = Output()
    result = operations.groom_item(selector=selector, section=section, content=content, repo=repo, output=output)
    _emit(result, output)


def _sync_fallback(repo: str, dry_run: bool, output: Output, error: Exception) -> None:
    """Preserve the legacy optional-core fallback for backlog sync."""
    typer.echo(f"Warning: backlog_core sync failed; falling back to CLI. ({error})", err=True)
    uv_exe = shutil.which("uv")
    if uv_exe is None:
        cli_output.err("Backlog sync unavailable (uv not found).")
        return
    try:
        proc = subprocess.run(
            [uv_exe, "run", "backlog", "sync"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        cli_output.err(f"Backlog sync unavailable: {exc}")
        return
    if proc.returncode != 0:
        cli_output.err(f"Backlog sync failed (exit {proc.returncode}): {proc.stderr.strip()}")
        return
    _emit({"synced": True, "dry_run": dry_run, "fallback": True}, output)


@app.command("sync")
def sync(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
) -> None:
    """Sync local backlog items using the selected backend provider."""
    output = Output()
    try:
        result = operations.sync_items(repo=repo, dry_run=dry_run, output=output)
    except (BacklogError, OSError, ValueError) as exc:
        _sync_fallback(repo, dry_run, output, exc)
        return
    _emit(result, output)


@app.command("pull")
def pull(
    selector: Annotated[str, typer.Option("--selector", help="Item selector: issue, URL, or title")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    diff: Annotated[bool, typer.Option("--diff", help="Return a diff instead of writing")] = False,
) -> None:
    """Pull a single backlog item using the selected backend provider."""
    output = Output()
    result = operations.pull_by_selector(selector=selector, repo=repo, diff=diff, output=output)
    _emit(result, output)


@app.command("pull-all")
def pull_all(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force pull even if local items are newer")] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Return a diff instead of writing items")] = False,
) -> None:
    """Pull all backlog items using the selected backend provider."""
    output = Output()
    result = operations.pull_items(repo=repo, dry_run=dry_run, force=force, diff=diff, output=output)
    _emit(result, output)


@app.command("normalize")
def normalize(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
) -> None:
    """Normalize backlog item files to canonical structure."""
    output = Output()
    result = operations.normalize_items(dry_run=dry_run, output=output)
    _emit(result, output)


@app.command("strike")
def strike(
    selector: Annotated[str, typer.Option("--selector", help="Item selector")],
    entry_id: Annotated[str, typer.Option("--entry-id", help="Log entry ID to strike")],
    reason: Annotated[str, typer.Option("--reason", help="Reason for striking the entry")],
    section: Annotated[str | None, typer.Option("--section", help="Section containing the entry")] = None,
) -> None:
    """Strike a log entry from a backlog item."""
    output = Output()
    result = operations.strike_entry(
        selector=selector, entry_id=entry_id, reason=reason, section=section, output=output
    )
    _emit(result, output)


@app.command("refresh")
def refresh(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    label: Annotated[str | None, typer.Option("--label", help="Filter issues by label")] = None,
    full_refresh: Annotated[bool, typer.Option("--full-refresh", help="Re-fetch all items, not just deltas")] = False,
) -> None:
    """Refresh the local backlog cache from the selected backend provider."""
    output = Output()
    result = operations.refresh_local_cache_from_github(
        repo=repo, label=label, full_refresh=full_refresh, output=output
    )
    _emit(result, output)


@app.command("labels")
def labels(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum labels to return")] = 100,
) -> None:
    """List labels for a repository."""
    output = Output()
    result = operations.list_labels(repo=repo, limit=limit, output=output)
    _emit(result, output)


@app.command("merged-prs")
def merged_prs(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    search: Annotated[str | None, typer.Option("--search", help="Search query")] = None,
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum pull requests to return")] = 20,
) -> None:
    """List merged pull requests for a repository."""
    output = Output()
    result = operations.list_merged_prs(repo=repo, search=search, limit=limit, output=output)
    _emit(result, output)


@app.command("milestones")
def milestones(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    state: Annotated[Literal["open", "closed", "all"], typer.Option("--state", help="Milestone state")] = "open",
) -> None:
    """List milestones for a repository."""
    output = Output()
    result = operations.list_milestones(repo=repo, state=state, output=output)
    _emit(result, output)


@app.command("soonest-milestone")
def soonest_milestone(repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "") -> None:
    """Get the soonest open milestone for a repository."""
    output = Output()
    result = operations.get_soonest_milestone(repo=repo, output=output)
    _emit(result, output)


@app.command("create-milestone")
def create_milestone(
    title: Annotated[str, typer.Option("--title", help="Milestone title")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    description: Annotated[str, typer.Option("--description", help="Milestone description")] = "",
    due_on: Annotated[str | None, typer.Option("--due-on", help="Due date (ISO 8601)")] = None,
) -> None:
    """Create a new milestone in a repository."""
    output = Output()
    result = operations.create_milestone(repo=repo, title=title, description=description, due_on=due_on, output=output)
    _emit(result, output)


@app.command("issues")
def issues(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    milestone: Annotated[str | None, typer.Option("--milestone", help="Filter by milestone title")] = None,
    labels: Annotated[str | None, typer.Option("--labels", help="Comma-separated labels")] = None,
    state: Annotated[Literal["open", "closed", "all"], typer.Option("--state", help="Issue state")] = "open",
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum issues to return")] = 30,
) -> None:
    """List issues in a repository."""
    output = Output()
    result = operations.list_issues(
        repo=repo, milestone=milestone, labels=labels, state=state, limit=limit, output=output
    )
    _emit(result, output)


@app.command("comment-issue")
def comment_issue(
    issue_number: Annotated[int, typer.Option("--issue-number", min=1, help="Issue number")],
    body: Annotated[str, typer.Option("--body", help="Comment body")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Add a comment to an issue."""
    output = Output()
    result = operations.comment_issue(repo=repo, issue_number=issue_number, body=body, output=output)
    _emit(result, output)


@app.command("comments")
def comments(
    issue_number: Annotated[int, typer.Option("--issue-number", min=1, help="Issue number")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum comments to return")] = 20,
    offset: Annotated[int, typer.Option("--offset", min=0, help="Number of comments to skip")] = 0,
) -> None:
    """List comments on an issue."""
    output = Output()
    result = operations.list_comments(repo=repo, issue_number=issue_number, limit=limit, offset=offset, output=output)
    _emit(result, output)


@app.command("read-comment")
def read_comment(
    issue_number: Annotated[int, typer.Option("--issue-number", min=1, help="Issue number")],
    comment_id: Annotated[int, typer.Option("--comment-id", min=1, help="REST comment ID")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
) -> None:
    """Read a single comment on an issue."""
    output = Output()
    result = operations.read_comment(repo=repo, issue_number=issue_number, comment_id=comment_id, output=output)
    _emit(result, output)


@app.command("projects")
def projects(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    owner: Annotated[str | None, typer.Option("--owner", help="Owner login")] = None,
    limit: Annotated[int, typer.Option("--limit", min=0, help="Maximum projects to return")] = 20,
) -> None:
    """List projects for a repository owner."""
    output = Output()
    result = operations.list_projects(repo=repo, owner=owner, limit=limit, output=output)
    _emit(result, output)


@app.command("create-project")
def create_project(
    title: Annotated[str, typer.Option("--title", help="Project title")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    owner: Annotated[str | None, typer.Option("--owner", help="Owner login")] = None,
) -> None:
    """Create a project."""
    output = Output()
    result = operations.create_project(repo=repo, title=title, owner=owner, output=output)
    _emit(result, output)


__all__ = ["app"]
