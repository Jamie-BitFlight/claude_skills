#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyGithub>=2.1.1",
#   "pydantic>=2.0.0",
#   "typer>=0.21.0",
#   "python-frontmatter>=1.1.0",
#   "ruamel.yaml>=0.18.0",
#   "python-dotenv>=1.0.0",
# ]
# ///
"""Backlog CLI — single interface for .claude/backlog/ per-item files and GitHub Issues.

All backlog and issue operations go through this script. Skills invoke it;
no direct edits to backlog files or GitHub.

GitHub Issues are the source of truth. Local .claude/backlog/*.md files are
a cache for agent consumption (avoiding GH API saturation during sessions).

Usage:
    backlog add --title X --priority P1 --description D [--source S] [--type T] [--create-issue]
    backlog list [--format text|json]
    backlog view <selector> [--format json]  # URL, #N, bare number, or title substring
    backlog sync [--dry-run]
    backlog close <selector> --plan PATH --checklist-pass [--cleanup]
    backlog resolve <selector> --reason "reason" [--cleanup]
    backlog update <selector> [--plan PATH] [--status in-progress] [--create-issue]
    backlog groom <selector> [--groomed-content "..." | --groomed-file PATH | --section X --content "..." | stdin]
    backlog normalize  # one-off: rewrite per-item files to research-style metadata, remove body duplication
    backlog migrate-status [--dry-run]  # migrate items with 'open' status to valid state-machine states
    backlog pull [--dry-run] [--force]  # pull issue bodies from GitHub into local files

Environment:
    GITHUB_TOKEN  Required for issue operations.
"""

from __future__ import annotations

import json
import os
import re
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from dotenv import load_dotenv

load_dotenv()

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from github import Auth, Github, GithubException, GithubObject
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "plugins" / "plugin-creator" / "scripts"))
sys.path.insert(0, str(_SCRIPT_DIR))  # expose sibling modules (state_handler, frontmatter_utils)
sys.path.insert(0, str(_SCRIPT_DIR.parent))  # expose backlog_core package

import frontmatter
from backlog_core import operations as _backlog_operations
from backlog_core.entry_blocks import rewrite_section as _rewrite_section
from backlog_core.github import (
    create_issue_for_item as _create_issue_for_item,
    fetch_open_issues_by_title as _fetch_open_issues_by_title_core,
    issue_to_local_fields as _issue_to_local_fields_core,
)
from backlog_core.models import (
    BACKLOG_DIR,
    COMMIT_PREFIX_RE as _COMMIT_PREFIX_RE,
    DEFAULT_REPO,
    FIELD_TO_INDEX,
    FUZZY_DUPLICATE_THRESHOLD,
    MIN_FRONTMATTER_PARTS,
    BacklogError as _BacklogError,
    BacklogItem,
    ItemNotFoundError as _ItemNotFoundError,
    Output as _Output,
)
from backlog_core.operations import update_item_metadata as _update_item_metadata
from backlog_core.parsing import (
    build_issue_body as _build_issue_body,
    build_issue_body_from_file as _build_issue_body_from_file_core,
    find_fuzzy_duplicates as _find_fuzzy_duplicates_core,
    find_item as _find_item,
    items_needing_issues as _items_needing_issues_core,
    items_with_issues as _items_with_issues_core,
    normalize_issue_title as _normalize_issue_title,
    now_iso as _now_iso,
    parse_issue_selector,
    parse_item_file as _parse_item_file_core,
    title_to_slug as _title_to_slug,
    today as _today,
)

from frontmatter_utils import dump_frontmatter, loads_frontmatter
from state_handler import BacklogState, StateTransitionError, apply_github_transition

if TYPE_CHECKING:
    from github.Issue import Issue
    from github.Repository import Repository

app = typer.Typer(help="Backlog and GitHub Issue CRUD — single interface")
_console = Console()


def _get_table_width(table: Table) -> int:
    """Get natural width of a Rich table for correct display.

    Returns:
        Natural width in characters as integer.
    """
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


def _get_github(repo: str) -> Repository:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        typer.echo("ERROR: GITHUB_TOKEN not set", err=True)
        raise typer.Exit(1)
    gh = Github(auth=Auth.Token(token))
    return gh.get_repo(repo)


def _try_get_github(repo: str) -> Repository | None:
    """Try to get GitHub repo, return None if unavailable (no token, network error, etc.).

    Use this for operations where local-only fallback is acceptable.

    Returns:
        Repository object or None if GitHub is unavailable.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    try:
        gh = Github(auth=Auth.Token(token), timeout=10)
        return gh.get_repo(repo)
    except GithubException:
        return None


def _dict_to_backlog_item_fields(d: dict) -> dict:
    """Convert a CLI display dict back to BacklogItem field kwargs for model_validate.

    This is the inverse of backlog_item_to_display_dict. Used when the CLI has a
    list[dict] and needs to pass items to a core function that expects list[BacklogItem].

    Args:
        d: CLI item dict with ``_title``, ``_section``, ``**Key**`` fields.

    Returns:
        Dict of BacklogItem field names and values suitable for BacklogItem.model_validate().
    """
    return {
        "title": d.get("_title", ""),
        "section": d.get("_section", ""),
        "file_path": d.get("_file_path", ""),
        "skip": bool(d.get("_skip")),
        "issue": d.get("_issue", ""),
        "raw_body": d.get("_raw_body", ""),
        "description": d.get("**Description**", ""),
        "source": d.get("**Source**", "Not specified"),
        "added": d.get("**Added**", ""),
        "priority": d.get("**Priority**", ""),
        "plan": d.get("**Plan**", ""),
        "item_type": d.get("**Type**", "Feature"),
        "research_first": d.get("**Research first**", ""),
        "files": d.get("**Files**", ""),
        "suggested_location": d.get("**Suggested location**", ""),
        "groomed": d.get("_groomed", ""),
        "last_synced": d.get("_last_synced", ""),
        "status": d.get("_status", ""),
    }


def backlog_item_to_display_dict(item: BacklogItem) -> dict:
    """Convert a BacklogItem to the dict format the CLI's display and mutation code expects.

    This is a LOCAL adapter helper in backlog.py (not in backlog_core/). It is explicitly
    temporary per architecture spec Section 5.6 — exists to bridge the BacklogItem type
    returned by backlog_core parsing functions and the dict-based CLI call sites.

    Maps typed fields to underscore-prefixed keys and bold-star metadata keys used
    throughout the CLI commands.

    Args:
        item: Parsed BacklogItem from backlog_core parsing functions.

    Returns:
        Dict with ``_title``, ``_section``, ``_file_path``, ``_skip``, ``_issue``,
        ``_raw_body``, ``_groomed``, ``_last_synced``, ``_status`` (conditional —
        only present when ``item.status`` is non-empty) and ``**Key**`` metadata keys.
    """
    d: dict = {
        "_title": item.title,
        "_section": item.section,
        "_file_path": item.file_path,
        "_skip": item.skip,
        "_issue": item.issue,
        "_raw_body": item.raw_body,
        "**Description**": item.description,
        "**Source**": item.source,
        "**Added**": item.added,
        "**Priority**": item.priority,
        "**Plan**": item.plan,
        "**Type**": item.item_type,
        "**Research first**": item.research_first,
        "**Files**": item.files,
        "**Suggested location**": item.suggested_location,
    }
    if item.groomed:
        d["_groomed"] = item.groomed
    if item.last_synced:
        d["_last_synced"] = item.last_synced
    if item.status:
        d["_status"] = item.status
    return d


def _parse_backlog_from_directory() -> list[dict]:
    """Parse backlog items directly from .claude/backlog/ per-item files.

    Uses the module-level BACKLOG_DIR so tests can redirect it via monkeypatch.
    Mirrors the logic in backlog_core.parsing.parse_backlog_from_directory but
    reads from the local BACKLOG_DIR name instead of the core's private binding.

    Returns:
        List of item dicts with _section, _title, and field keys.
    """
    # Use module-level BACKLOG_DIR so tests can patch it via monkeypatch.setattr(_mod, "BACKLOG_DIR", ...)
    # Do NOT call _parse_backlog_from_directory_core() — it reads backlog_core.models.BACKLOG_DIR
    # which ignores the patched value.
    if not BACKLOG_DIR.exists():
        return []
    prefix_to_section = {
        "p0-": "P0",
        "p1-": "P1",
        "p2-": "P2",
        "idea-": "Ideas",
        "ideas-": "Ideas",
        "completed-": "Completed",
        "medium-": "P1",
    }
    items: list[dict] = []
    for filepath in sorted(BACKLOG_DIR.glob("*.md")):
        name = filepath.stem
        section = ""
        for prefix, sec in prefix_to_section.items():
            if name.startswith(prefix):
                section = sec
                break
        try:
            item_text = filepath.read_text(encoding="utf-8")
        except OSError:
            continue
        item = _parse_item_file_core(item_text, filepath)
        meta_priority = item.priority
        if meta_priority and meta_priority.upper() in {"P0", "P1", "P2"}:
            section = meta_priority.upper()
        item.section = section
        if not item.title:
            item.title = name
        item.file_path = str(filepath)
        if section == "Completed":
            item.skip = True
        items.append(backlog_item_to_display_dict(item))
    return items


def parse_backlog() -> list[dict]:
    """Parse backlog items from .claude/backlog/ per-item files.

    Uses the module-level BACKLOG_DIR so tests can redirect it via monkeypatch.
    Delegates directory iteration to _parse_backlog_from_directory() which
    uses the patchable local BACKLOG_DIR name.

    Returns:
        List of item dicts with _section, _title, and field keys.
    """
    # Use _parse_backlog_from_directory() — NOT _parse_backlog_core() — so that
    # tests patching _mod.BACKLOG_DIR via monkeypatch.setattr take effect.
    # _parse_backlog_core() reads backlog_core.models.BACKLOG_DIR directly and
    # ignores any patches applied to the backlog.py module namespace.
    return _parse_backlog_from_directory()


def _parse_item_file(text: str, path: Path) -> dict:
    """Parse a single per-item backlog file (frontmatter + body).

    Delegates to backlog_core.parsing.parse_item_file and converts the BacklogItem
    to the dict format the CLI expects via backlog_item_to_display_dict.

    Returns:
        Item dict with _title, _raw_body, and field keys.
    """
    return backlog_item_to_display_dict(_parse_item_file_core(text, path))


def _parse_issue_selector(selector: str) -> str | None:
    """Extract issue number from selector (URL, #N, or bare number).

    Delegates to backlog_core.parsing.parse_issue_selector.

    Returns:
        Issue number as string (e.g. ``"123"``) or None if not an issue ref.
    """
    return parse_issue_selector(selector)


def find_item(items: list[dict], selector: str) -> dict | None:
    """Find item by title substring, #N, bare number, or GitHub issue URL.

    Converts dicts back to BacklogItem objects for the core find_item call, then
    returns the original dict (preserving all CLI-only fields like _file_path).

    Supports:
      - ``https://github.com/owner/repo/issues/123`` — extract issue number
      - ``#123`` — match by issue number
      - ``123`` — match by issue number (bare number)
      - ``title substring`` — case-insensitive title match

    Returns:
        Matching item dict or None.
    """
    core_items = [BacklogItem.model_validate(_dict_to_backlog_item_fields(d)) for d in items]
    result = _find_item(core_items, selector)
    if result is None:
        return None
    # _find_item returns one of the core_items objects; find its index to return the original dict
    for idx, core in enumerate(core_items):
        if core is result:
            return items[idx]
    # Fallback: should not be reached but converts result if identity match failed
    return backlog_item_to_display_dict(result)


def _find_fuzzy_duplicates(
    title: str, items: list[dict], threshold: float = FUZZY_DUPLICATE_THRESHOLD
) -> list[tuple[str, float, str]]:
    """Find existing backlog items with titles similar to the given title.

    Delegates to backlog_core.parsing.find_fuzzy_duplicates. Converts each
    dict to BacklogItem for the core call, returns the same
    ``list[tuple[str, float, str]]`` interface.

    Args:
        title: The new item title to check.
        items: Existing backlog items from ``parse_backlog()``.
        threshold: Similarity ratio (0.0-1.0) above which a match is reported.

    Returns:
        List of ``(existing_title, similarity_ratio, file_path)`` tuples sorted
        by similarity descending. Empty list if no matches above threshold.
    """
    core_items = [BacklogItem.model_validate(_dict_to_backlog_item_fields(d)) for d in items]
    return _find_fuzzy_duplicates_core(title, core_items, threshold)


def _fetch_open_issues_by_title(repo: Repository) -> dict[str, int]:
    """Fetch all open issues and return ``{normalized_title: issue_number}`` map.

    Delegates to backlog_core.github.fetch_open_issues_by_title.

    Returns:
        Dict mapping normalized title strings to their GitHub issue number.
    """
    return _fetch_open_issues_by_title_core(repo)


def items_needing_issues(items: list[dict]) -> list[dict]:
    """Return all backlog items that lack GitHub issues and are not skipped.

    Delegates to backlog_core.parsing.items_needing_issues. Converts dicts to
    BacklogItems for the core call, then maps results back to original dicts by
    title to preserve all dict fields including ``_file_path``.
    """
    core_items = [BacklogItem.model_validate(_dict_to_backlog_item_fields(d)) for d in items]
    core_result = _items_needing_issues_core(core_items)
    result_titles = {item.title for item in core_result}
    return [d for d in items if d.get("_title") in result_titles]


def items_with_issues(items: list[dict]) -> list[dict]:
    """Return backlog items that already have a GitHub issue and are not skipped.

    Delegates to backlog_core.parsing.items_with_issues. Converts dicts to
    BacklogItems for the core call, then maps results back to original dicts by
    title to preserve all dict fields including ``_file_path``.

    Returns:
        List of item dicts that have an issue reference.
    """
    core_items = [BacklogItem.model_validate(_dict_to_backlog_item_fields(d)) for d in items]
    core_result = _items_with_issues_core(core_items)
    result_titles = {item.title for item in core_result}
    return [d for d in items if d.get("_title") in result_titles]


def _build_issue_body_from_file(item: dict) -> str | None:
    """Build GitHub issue body from local per-item file content.

    Delegates to backlog_core.parsing.build_issue_body_from_file. Converts
    the dict to BacklogItem for the core call.

    Returns None if the body has no groomed content (i.e. no '## Groomed'
    section), since ungroomed items don't need their body synced to GitHub.

    Args:
        item: Parsed backlog item dict with _raw_body and frontmatter fields.

    Returns:
        Issue body markdown string, or None if no groomed section present.
    """
    return _build_issue_body_from_file_core(BacklogItem.model_validate(_dict_to_backlog_item_fields(item)))


def build_issue_body(item: dict) -> str:
    """Build GitHub issue body from backlog item fields.

    Converts the CLI item dict to BacklogItem and delegates to backlog_core.parsing.build_issue_body.

    Returns:
        Markdown-formatted issue body string.
    """
    return _build_issue_body(BacklogItem.model_validate(_dict_to_backlog_item_fields(item)))


def create_issue_for_item(repo: Repository, item: dict, dry_run: bool = False) -> int | None:
    """Create GitHub issue for backlog item.

    Converts the CLI item dict to BacklogItem and delegates to backlog_core.github.create_issue_for_item.
    Captures output messages and warnings via an Output collector and prints them with typer.echo.

    Returns:
        Issue number if created, None otherwise.
    """
    out = _Output()
    result = _create_issue_for_item(
        repo, BacklogItem.model_validate(_dict_to_backlog_item_fields(item)), dry_run=dry_run, output=out
    )
    for msg in out.messages:
        typer.echo(msg)
    for warn in out.warnings:
        typer.echo(warn, err=True)
    return result


def _create_issue_and_update_item(item: dict, repo: str) -> int | None:
    """Create GitHub issue for item and update per-item file metadata.

    Returns:
        Issue number if created, None otherwise.
    """
    try:
        repository = _get_github(repo)
        issue_num = create_issue_for_item(repository, item, dry_run=False)
    except GithubException as e:
        typer.echo(f"  WARNING: Issue creation failed: {e}", err=True)
        return None
    else:
        if not issue_num:
            return None
        filepath_str = item.get("_file_path")
        if filepath_str:
            _update_item_metadata(Path(filepath_str), {"metadata": {"issue": f"#{issue_num}"}})
        return issue_num


def _issue_to_local_fields(issue: Issue) -> dict[str, str]:
    """Extract backlog-relevant fields from a PyGithub Issue object.

    Delegates to backlog_core.github.issue_to_local_fields and converts the
    returned IssueLocalFields model to the dict[str, str] interface callers expect.

    Returns:
        Dict with title, body, priority, type, status, updated_at, milestone.
    """
    result = _issue_to_local_fields_core(issue)
    return {
        "title": result.title,
        "body": result.body,
        "priority": result.priority,
        "type": result.item_type,
        "status": result.status,
        "updated_at": result.updated_at,
        "milestone": result.milestone,
    }


def _pull_single_issue(repo_obj: Repository, issue_num: int, filepath: Path | None = None) -> Path | None:
    """Fetch a GitHub issue and write/update the local cache file.

    If filepath is None, derives it from the issue title and priority.

    Returns:
        Path to the local file, or None on failure.
    """
    try:
        issue = repo_obj.get_issue(issue_num)
    except GithubException as e:
        typer.echo(f"  WARNING: Could not fetch issue #{issue_num}: {e}", err=True)
        return None

    fields = _issue_to_local_fields(issue)
    # Strip conventional-commit prefix from title (e.g., "feat: Title" → "Title")
    raw_title = fields["title"]
    clean_title = _COMMIT_PREFIX_RE.sub("", raw_title).strip()

    if filepath is None:
        slug = _title_to_slug(clean_title)
        filename = f"{fields['priority'].lower()}-{slug}.md"
        filepath = BACKLOG_DIR / filename

    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)

    if filepath.exists():
        # Update existing file: overwrite description, body, metadata
        _update_item_metadata(
            filepath,
            {
                "name": clean_title,
                "description": _extract_description_from_issue_body(fields["body"]),
                "metadata": {
                    "issue": f"#{issue_num}",
                    "priority": fields["priority"],
                    "type": fields["type"],
                    "status": fields["status"],
                    "last_synced": _now_iso(),
                },
            },
        )
        # Overwrite body sections from GitHub issue body
        _overwrite_body_from_github(filepath, fields["body"])
    else:
        # Create new cache file from GitHub issue
        fm_str = _build_backlog_frontmatter(
            name=clean_title,
            description=_extract_description_from_issue_body(fields["body"]),
            source=f"GitHub Issue #{issue_num}",
            added=_today(),
            priority=fields["priority"],
            type_val=fields["type"],
            status=fields["status"],
            issue=f"#{issue_num}",
        )
        filepath.write_text(fm_str.rstrip() + "\n\n" + fields["body"] + "\n", encoding="utf-8")
        _update_item_metadata(filepath, {"metadata": {"last_synced": _now_iso()}})

    return filepath


def _extract_description_from_issue_body(body: str) -> str:
    """Extract the Description section from a GitHub issue body.

    Falls back to first non-empty paragraph if no ## Description section found.

    Returns:
        Description text.
    """
    desc_match = re.search(r"## Description\s*\n\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if desc_match:
        return desc_match.group(1).strip()
    # Fallback: first non-empty paragraph
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            return stripped
    return body.strip()


def _overwrite_body_from_github(filepath: Path, issue_body: str) -> None:
    """Replace the body of a local cache file with content from GitHub issue body.

    Preserves frontmatter, replaces everything after it.
    """
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    parts = text.split("---", 2)
    if len(parts) < MIN_FRONTMATTER_PARTS:
        return
    # Keep frontmatter, replace body
    new_content = "---" + parts[1] + "---\n\n" + issue_body.strip() + "\n"
    filepath.write_text(new_content, encoding="utf-8")


def _check_item_staleness(item: dict, repo: str) -> bool:
    """Check if a local cache file is stale relative to its GitHub issue.

    Returns:
        True if the GitHub issue was updated after last_synced, False otherwise.
    """
    issue_ref = item.get("_issue", "")
    if not issue_ref:
        return False
    last_synced = item.get("_last_synced", "")
    if not last_synced:
        # No sync timestamp = always stale if there's an issue
        return True
    try:
        repo_obj = _get_github(repo)
        num = int(issue_ref.lstrip("#"))
        issue = repo_obj.get_issue(num)
        gh_updated = issue.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if issue.updated_at else ""
    except (GithubException, typer.Exit):
        return False
    else:
        return gh_updated > last_synced


# --- Subcommands ---


def _add_item_index_format(
    title: str,
    description: str,
    source: str,
    today: str,
    priority: str,
    type_: str,
    research_first: str,
    files: str,
    suggested_location: str,
    section_heading: str,
    create_issue: bool,
    repo: str,
) -> None:
    """Add item: create GitHub Issue first (GH-first), then write local cache file.

    GH-first flow: try to create the GitHub Issue before writing the local file.
    If GH succeeds, the local file includes the issue number from the start (single write).
    If GH is unavailable (no token, network error), fall back to local-only with a warning.
    """
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    slug = _title_to_slug(title)
    filename = f"{priority.lower()}-{slug}.md"
    filepath = BACKLOG_DIR / filename
    idx = 0
    while filepath.exists():
        idx += 1
        filename = f"{priority.lower()}-{slug}-{idx}.md"
        filepath = BACKLOG_DIR / filename

    # GH-first: try to create GitHub Issue BEFORE writing local file
    issue_num: int | None = None
    if create_issue:
        item = {
            "_title": title,
            "**Description**": description,
            "**Source**": source,
            "**Added**": today,
            "**Priority**": priority,
            "**Type**": type_,
            "**Research first**": research_first,
            "**Files**": files,
            "**Suggested location**": suggested_location,
        }
        repository = _try_get_github(repo)
        if repository is not None:
            try:
                issue_num = create_issue_for_item(repository, item, dry_run=False)
            except GithubException as e:
                typer.echo(f"  WARNING: Issue creation failed: {e}", err=True)
        else:
            typer.echo("  WARNING: GitHub unavailable — creating local-only item", err=True)

    # Build frontmatter with issue number already included (single write)
    issue_ref = f"#{issue_num}" if issue_num else ""
    fm_str = _build_backlog_frontmatter(title, description, source, today, priority, type_, "open", issue_ref, "", "")

    body_parts: list[str] = []
    if research_first:
        body_parts.append(f"**Research first**: {research_first}")
    if files:
        body_parts.append(f"**Files**: {files}")
    if suggested_location:
        body_parts.append(f"**Suggested location**: {suggested_location}")
    body = "\n".join(body_parts) + "\n" if body_parts else ""

    # Write local cache file (single write — no update needed)
    filepath.write_text(fm_str.rstrip() + "\n\n" + body, encoding="utf-8")
    if issue_num:
        _update_item_metadata(filepath, {}, set_synced=True)

    typer.echo(f"Backlog item created.\n  Title: {title}\n  Priority: {priority}\n  File: {filepath.name}")
    if issue_num:
        typer.echo(f"  Issue: #{issue_num}")
    typer.echo(f"Next steps: /groom-backlog-item {title}  /work-backlog-item {title}")


@app.command()
def add(
    title: Annotated[str, typer.Option("--title", "-t")],
    priority: Annotated[str, typer.Option("--priority", "-p")],
    description: Annotated[str, typer.Option("--description", "-d")],
    source: Annotated[str, typer.Option("--source")] = "Not specified",
    type_: Annotated[str, typer.Option("--type")] = "Feature",
    research_first: Annotated[str, typer.Option("--research-first")] = "",
    files: Annotated[str, typer.Option("--files")] = "",
    suggested_location: Annotated[str, typer.Option("--suggested-location")] = "",
    create_issue: Annotated[bool, typer.Option("--create-issue/--no-create-issue")] = True,
    force: Annotated[bool, typer.Option("--force", help="Skip fuzzy duplicate check")] = False,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Add item to backlog. Creates per-item file and optionally a GitHub issue."""
    if not force:
        existing_items = parse_backlog()
        duplicates = _find_fuzzy_duplicates(title, existing_items)
        if duplicates:
            typer.echo("WARNING: Similar backlog items found:", err=True)
            for dup_title, ratio, dup_path in duplicates:
                pct = int(ratio * 100)
                file_label = Path(dup_path).name if dup_path else "unknown"
                typer.echo(f'  - "{dup_title}" ({pct}% similar)  [{file_label}]', err=True)
            typer.echo("\nUse --force to add anyway.", err=True)
            raise typer.Exit(1)
    today = _today()
    section_heading = {
        "P0": "## P0 - Must Have",
        "P1": "## P1 - Should Have",
        "P2": "## P2 - Could Have",
        "Idea": "## Ideas",
        "Ideas": "## Ideas",
    }.get(priority, "## P1 - Should Have")
    _add_item_index_format(
        title,
        description,
        source,
        today,
        priority,
        type_,
        research_first,
        files,
        suggested_location,
        section_heading,
        create_issue,
        repo,
    )


def _batch_fetch_statuses(items: list[dict], repo: str) -> dict[int, dict[str, str]]:
    """Batch fetch status and milestone from GH for all items with issue numbers.

    Single API call replaces N+1 per-item get_issue() calls.

    Returns:
        Dict mapping issue_number -> {"status": str, "milestone": str}
    """
    repo_obj = _try_get_github(repo)
    if repo_obj is None:
        return {}
    try:
        all_issues = {issue.number: issue for issue in repo_obj.get_issues(state="open") if issue.pull_request is None}
    except GithubException:
        return {}
    result: dict[int, dict[str, str]] = {}
    for item in items:
        num_str = item.get("_issue", "").lstrip("#")
        if not num_str.isdigit():
            continue
        num = int(num_str)
        if num in all_issues:
            gh_issue = all_issues[num]
            status_labels = [lbl.name for lbl in gh_issue.labels if lbl.name.startswith("status:")]
            result[num] = {
                "status": status_labels[0] if status_labels else "",
                "milestone": gh_issue.milestone.title if gh_issue.milestone else "",
            }
    return result


def _fetch_item_status(item: dict, repo: str) -> str:
    """Fetch status label from GitHub issue for an item (single-item fallback).

    Prefer _batch_fetch_statuses() for listing multiple items.

    Returns:
        Status label string or empty string.
    """
    if not item.get("_issue"):
        return ""
    try:
        repository = _get_github(repo)
        num = item.get("_issue", "").lstrip("#")
        gh_issue = repository.get_issue(int(num))
        labels = [lb.name for lb in gh_issue.labels if lb.name.startswith("status:")]
        return labels[0] if labels else ""
    except GithubException:
        return ""


def _list_items_json(open_items: list[dict], with_status: bool, repo: str) -> None:
    """Output backlog items as JSON."""
    status_map: dict[int, dict[str, str]] = {}
    if with_status:
        status_map = _batch_fetch_statuses(open_items, repo)
    out = []
    for it in open_items:
        entry: dict[str, Any] = {
            "section": it.get("_section"),
            "title": it.get("_title"),
            "issue": it.get("_issue"),
            "plan": it.get("**Plan**"),
        }
        if it.get("_file_path"):
            entry["file_path"] = it.get("_file_path")
        if it.get("_groomed"):
            entry["groomed"] = True
        if with_status and it.get("_issue"):
            num_str = it.get("_issue", "").lstrip("#")
            num = int(num_str) if num_str.isdigit() else 0
            info = status_map.get(num, {"status": "", "milestone": ""})
            entry["status"] = info["status"]
            entry["milestone"] = info["milestone"]
        out.append(entry)
    typer.echo(json.dumps(out, indent=2))


def _list_items_table(open_items: list[dict], with_status: bool, repo: str) -> None:
    """Output backlog items as Rich table."""
    status_map: dict[int, dict[str, str]] = {}
    if with_status:
        status_map = _batch_fetch_statuses(open_items, repo)
    table = Table(title=":clipboard: Backlog Items", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold blue")
    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Plan", justify="center", no_wrap=True)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Issue", style="dim", no_wrap=True)
    if with_status:
        table.add_column("Status", style="magenta", no_wrap=True)
    for it in open_items:
        issue = it.get("_issue", "no issue")
        plan = ":white_check_mark:" if it.get("**Plan**") else ":clipboard:"
        title = (it.get("_title", "") or "")[:50]
        row: list[str] = [it.get("_section", ""), plan, title, issue]
        if with_status:
            num_str = it.get("_issue", "").lstrip("#")
            num = int(num_str) if num_str.isdigit() else 0
            info = status_map.get(num, {"status": "", "milestone": ""})
            row.append(info["status"])
        table.add_row(*row)
    table.width = _get_table_width(table)
    _console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


def _refresh_local_cache_from_github(repo: str, label: str | None = None) -> None:
    """Fetch open GitHub Issues and update local cache files.

    This is the GH-first list path: queries GitHub for the current state,
    writes/updates local cache files, then the caller reads from local cache.
    """
    repo_obj = _try_get_github(repo)
    if repo_obj is None:
        typer.echo("  WARNING: GitHub unavailable — listing from local cache only", err=True)
        return

    label_objs = []
    if label:
        try:
            label_objs.append(repo_obj.get_label(label))
        except GithubException:
            typer.echo(f"  WARNING: label '{label}' not found — listing all issues", err=True)

    issues = repo_obj.get_issues(state="open", labels=label_objs or GithubObject.NotSet)
    count = 0
    for issue in issues:
        if issue.pull_request is not None:
            continue
        _pull_single_issue(repo_obj, issue.number)
        count += 1
    typer.echo(f"  Refreshed {count} issue(s) from GitHub into local cache.")


@app.command("list")
def list_items(
    output_format: Annotated[str, typer.Option("--format", "-f")] = "text",
    with_status: Annotated[bool, typer.Option("--with-status")] = False,
    from_github: Annotated[
        bool, typer.Option("--from-github", help="Query GitHub Issues and refresh local cache before listing")
    ] = False,
    label: Annotated[str | None, typer.Option("--label", help="Filter by GitHub label (e.g. 'priority:p1')")] = None,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """List backlog items. Default reads local cache only. Use --from-github to refresh from GH first."""
    if from_github:
        _refresh_local_cache_from_github(repo, label)
    items = parse_backlog()
    open_items = [it for it in items if not it.get("_skip") and it.get("_section")]
    if output_format == "json":
        _list_items_json(open_items, with_status, repo)
    else:
        _list_items_table(open_items, with_status, repo)


def _find_or_create_issue(
    item: dict, existing_issues: dict[str, int], repository: Repository, dry_run: bool
) -> int | None:
    """Check for existing issue by title; create only if no match found.

    Returns:
        Issue number (existing or newly created), or None for dry-run creates.
    """
    title = item.get("_title", "")
    normalized = _normalize_issue_title(title)
    if normalized in existing_issues:
        existing_num = existing_issues[normalized]
        typer.echo(f"  Linked #{existing_num}: {title[:60]} (existing issue found)")
        return existing_num
    if dry_run:
        typer.echo(f"  [dry-run] Would create: {title[:60]}")
        return None
    return create_issue_for_item(repository, item, dry_run=False)


def _sync_create_missing_issues(items: list[dict], repo: str, dry_run: bool) -> None:
    """Pass 1 of sync: create GitHub issues for all items that lack them.

    Before creating any issues, fetches all open issues from GitHub and checks
    for title matches. If an existing open issue matches (after stripping
    conventional-commit prefixes), links to it instead of creating a duplicate.

    Args:
        items: Parsed backlog items.
        repo: GitHub repo slug.
        dry_run: If True, print what would happen without executing.
    """
    needed = items_needing_issues(items)
    if not needed:
        typer.echo("No items need GitHub issues created.")
        return
    typer.echo(f"Found {len(needed)} item(s) without GitHub issues:")
    for it in needed:
        typer.echo(f"  - {it.get('_title', '')[:60]}")
    repository = _get_github(repo)

    # Dedup: fetch existing open issues to prevent duplicate creation.
    typer.echo("Fetching open issues for deduplication check...")
    existing_issues = _fetch_open_issues_by_title(repository)
    typer.echo(f"  Found {len(existing_issues)} existing open issues.")

    for item in needed:
        issue_num = _find_or_create_issue(item, existing_issues, repository, dry_run)
        if not issue_num or dry_run:
            continue
        # Track newly created/linked issues to prevent intra-batch duplicates.
        new_normalized = _normalize_issue_title(item.get("_title", ""))
        if new_normalized not in existing_issues:
            existing_issues[new_normalized] = issue_num
        # Update per-item file metadata with issue number
        filepath_str = item.get("_file_path")
        if filepath_str:
            _update_item_metadata(Path(filepath_str), {"metadata": {"issue": f"#{issue_num}"}})


def _sync_push_groomed_content(items: list[dict], repo: str, dry_run: bool) -> None:
    """Pass 2 of sync: push groomed content to existing GitHub issues.

    Skips items with no '## Groomed' section in their body.

    Args:
        items: Parsed backlog items.
        repo: GitHub repo slug.
        dry_run: If True, print what would happen without executing.
    """
    groomed_items = [it for it in items_with_issues(items) if "## Groomed" in (it.get("_raw_body") or "")]
    if not groomed_items:
        typer.echo("No items with groomed content to push.")
        return
    typer.echo(f"Found {len(groomed_items)} item(s) with groomed content to push to GitHub:")
    if dry_run:
        for it in groomed_items:
            issue_ref = it.get("_issue", "")
            typer.echo(f"  [dry-run] Would update issue {issue_ref}: {it.get('_title', '')[:60]}")
        return
    repository = _get_github(repo)
    for item in groomed_items:
        issue_ref = item.get("_issue", "")
        num_str = issue_ref.lstrip("#")
        if not num_str.isdigit():
            typer.echo(f"  WARNING: Skipping item with invalid issue ref '{issue_ref}'", err=True)
            continue
        body = _build_issue_body_from_file(item)
        if body is None:
            continue
        try:
            gh_issue = repository.get_issue(int(num_str))
            gh_issue.edit(body=body)
            typer.echo(f"  Updated issue #{num_str}: {item.get('_title', '')[:60]}")
        except GithubException as e:
            typer.echo(f"  WARNING: Could not update issue #{num_str}: {e}", err=True)


@app.command()
def sync(
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Create GitHub issues for all items missing them, and push groomed content to existing issues."""
    items = parse_backlog()
    _sync_create_missing_issues(items, repo, dry_run)
    _sync_push_groomed_content(items, repo, dry_run)


def _check_open_prs_for_issue(issue_num: int, repo: str) -> list[dict[str, Any]]:
    """Check for open pull requests that reference a given issue number.

    Searches the repository for open PRs whose title or body contains ``#N``
    (where N is the issue number). This catches PRs with ``Fixes #N``,
    ``Closes #N``, or any other reference to the issue.

    Args:
        issue_num: The GitHub issue number to search for.
        repo: Repository in ``owner/repo`` format.

    Returns:
        List of dicts with ``number``, ``title``, ``url`` for each matching PR.
        Empty list if no open PRs found or GitHub is unavailable.
    """
    try:
        gh = Github(auth=Auth.Token(os.environ.get("GITHUB_TOKEN", "")), timeout=10)
        query = f"repo:{repo} is:pr is:open #{issue_num}"
        results = gh.search_issues(query)
        # Materialize the lazy PaginatedList inside try — iteration triggers the API call
        prs = [{"number": pr.number, "title": pr.title, "url": pr.html_url} for pr in results]
    except GithubException:
        return []
    return prs


def _close_item_index(item: dict, reason: str, today: str) -> bool:
    """Apply close (dismissal) to item by updating per-item file metadata. ADR-9.

    Returns:
        True if closed, False if already closed.
    """
    filepath_str = item.get("_file_path")
    if not filepath_str:
        typer.echo("ERROR: Item has no file path", err=True)
        raise typer.Exit(1)
    raw = item.get("_raw_body", "")
    if any(marker in raw for marker in ("**Status**: CLOSED", "**Status**: DONE", "**Completed**:")):
        typer.echo("Item already closed.")
        return False
    _update_item_metadata(Path(filepath_str), {"metadata": {"status": "closed", "close_reason": reason}})
    return True


def _close_github_issue(issue_ref: str, reason: str, reference: str, comment: str, repo: str) -> None:
    """Close GitHub issue as dismissed (not completed). ADR-9."""
    try:
        repository = _get_github(repo)
        num = issue_ref.lstrip("#")
        issue = repository.get_issue(int(num))
        parts = [f"**Closed** ({reason})."]
        if reference:
            parts.append(f"**Reference**: {reference}")
        if comment:
            parts.append(f"\n{comment}")
        issue.create_comment(" ".join(parts))
        current_status = next(
            (lbl.name.removeprefix("status:") for lbl in issue.labels if lbl.name.startswith("status:")), None
        )
        apply_github_transition(repository, issue, current_status, BacklogState.CLOSED.value)
        issue.edit(state="closed")
        typer.echo(f"  GitHub issue #{num} closed ({reason}).")
    except (GithubException, StateTransitionError) as e:
        typer.echo(f"  WARNING: Could not close issue: {e}", err=True)


def _close_cleanup(item: dict, issue_ref: str, repo: str) -> None:
    """Remove local per-item file after close (canonical state lives in GitHub)."""
    filepath_str = item.get("_file_path")
    if not filepath_str:
        return
    filepath = Path(filepath_str)
    if filepath.exists():
        filepath.unlink()
        typer.echo(f"  Removed local file {filepath.name} (canonical: GH #{issue_ref.lstrip('#')})")


@app.command()
def close(
    selector: Annotated[str, typer.Argument(help="Title substring, #N, bare number, or GitHub issue URL")],
    reason: Annotated[
        str, typer.Option("--reason", "-r", help="One of: duplicate, out_of_scope, superseded, wontfix, blocked")
    ],
    reference: Annotated[str, typer.Option("--reference", help="Related item: #N, URL, or title")] = "",
    comment: Annotated[str, typer.Option("--comment", help="Additional context")] = "",
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup",
            help="Remove local file after close; index link becomes GH issue URL (like git delete merged branch)",
        ),
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Close even if open PRs reference the issue")] = False,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Dismiss item without completing it and close GitHub issue. ADR-9."""
    valid_reasons = ("duplicate", "out_of_scope", "superseded", "wontfix", "blocked")
    reason = reason.strip().lower()
    if reason not in valid_reasons:
        typer.echo(f"ERROR: Invalid reason: {reason!r}. Valid: {', '.join(valid_reasons)}", err=True)
        raise typer.Exit(1)
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        typer.echo(f"ERROR: No item found for: {selector}", err=True)
        raise typer.Exit(1)
    issue_ref = item.get("_issue")
    if issue_ref and not force:
        issue_num = int(issue_ref.lstrip("#"))
        open_prs = _check_open_prs_for_issue(issue_num, repo)
        if open_prs:
            typer.echo(f"WARNING: Open PRs reference issue {issue_ref}:", err=True)
            for pr in open_prs:
                typer.echo(f"  - PR #{pr['number']}: {pr['title']}", err=True)
                typer.echo(f"    {pr['url']}", err=True)
            typer.echo(f"\nIssue {issue_ref} will auto-close when a PR merges with 'Fixes {issue_ref}'.", err=True)
            typer.echo("Use --force to close anyway.", err=True)
            raise typer.Exit(1)
    today = _today()
    if not _close_item_index(item, reason, today):
        return
    typer.echo(f'Backlog item "{item.get("_title")}" closed ({reason}).')
    if issue_ref:
        _close_github_issue(issue_ref, reason, reference, comment, repo)
    if cleanup and issue_ref:
        _close_cleanup(item, issue_ref, repo)


def _resolve_item_index(item: dict, summary: str, plan: str, today: str) -> bool:
    """Apply resolve (completion) to item by updating per-item file metadata. ADR-9.

    Returns:
        True if resolved, False if already resolved.
    """
    filepath_str = item.get("_file_path")
    if not filepath_str:
        typer.echo("ERROR: Item has no file path", err=True)
        raise typer.Exit(1)
    raw = item.get("_raw_body", "")
    if any(marker in raw for marker in ("**Status**: DONE", "**Completed**:", "**Resolved**:")):
        typer.echo("Item already resolved.")
        return False
    metadata: dict[str, str] = {"status": "done", "priority": "completed"}
    if plan:
        metadata["plan"] = plan
    _update_item_metadata(Path(filepath_str), {"metadata": metadata})
    return True


def _resolve_github_issue(
    issue_ref: str, summary: str, method: str, notes: str, follow_ups: str, findings: str, repo: str
) -> None:
    """Close GitHub issue as completed with structured evidence trail. ADR-9."""
    try:
        repository = _get_github(repo)
        num = issue_ref.lstrip("#")
        issue = repository.get_issue(int(num))
        body_parts = [f"## Resolved\n\n**Summary**: {summary}"]
        if method:
            body_parts.append(f"**Method**: {method}")
        if notes:
            body_parts.append(f"\n### Notes\n\n{notes}")
        if follow_ups:
            body_parts.append(f"\n### Follow-ups\n\n{follow_ups}")
        if findings:
            body_parts.append(f"\n### Findings\n\n{findings}")
        issue.create_comment("\n".join(body_parts))
        current_status = next(
            (lbl.name.removeprefix("status:") for lbl in issue.labels if lbl.name.startswith("status:")), None
        )
        apply_github_transition(repository, issue, current_status, BacklogState.DONE.value)
        issue.edit(state="closed")
        typer.echo(f"  GitHub issue #{num} resolved.")
    except (GithubException, StateTransitionError) as e:
        typer.echo(f"  WARNING: Could not close issue: {e}", err=True)


@app.command()
def resolve(
    selector: Annotated[str, typer.Argument(help="Title substring, #N, bare number, or GitHub issue URL")],
    summary: Annotated[str, typer.Option("--summary", "-s", help="What was done (required)")],
    plan: Annotated[str, typer.Option("--plan", "-p", help="Plan path or completion reference")] = "",
    method: Annotated[str, typer.Option("--method", help="How the work was done")] = "",
    notes: Annotated[str, typer.Option("--notes", help="Problems found, surprises, comments")] = "",
    follow_ups: Annotated[str, typer.Option("--follow-ups", help="Created follow-up tickets (comma-separated)")] = "",
    findings: Annotated[str, typer.Option("--findings", help="Retrospective learnings")] = "",
    cleanup: Annotated[
        bool, typer.Option("--cleanup", help="Remove local file after resolve; index link becomes GH issue URL")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Resolve even if open PRs reference the issue")] = False,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Mark item DONE (completed) and close GitHub issue with evidence trail. ADR-9."""
    if not summary.strip():
        typer.echo("ERROR: --summary required (what was done)", err=True)
        raise typer.Exit(1)
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        typer.echo(f"ERROR: No item found for: {selector}", err=True)
        raise typer.Exit(1)
    issue_ref = item.get("_issue")
    if issue_ref and not force:
        issue_num = int(issue_ref.lstrip("#"))
        open_prs = _check_open_prs_for_issue(issue_num, repo)
        if open_prs:
            typer.echo(f"WARNING: Open PRs reference issue {issue_ref}:", err=True)
            for pr in open_prs:
                typer.echo(f"  - PR #{pr['number']}: {pr['title']}", err=True)
                typer.echo(f"    {pr['url']}", err=True)
            typer.echo("\nResolving will close the issue and orphan these PRs.", err=True)
            typer.echo("Use --force to resolve anyway.", err=True)
            raise typer.Exit(1)
    today = _today()
    if not _resolve_item_index(item, summary, plan, today):
        return
    typer.echo(f'Backlog item "{item.get("_title")}" resolved.')
    if issue_ref:
        _resolve_github_issue(issue_ref, summary, method, notes, follow_ups, findings, repo)
    if cleanup and issue_ref:
        _close_cleanup(item, issue_ref, repo)


def _build_backlog_frontmatter(
    name: str,
    description: str,
    source: str,
    added: str,
    priority: str,
    type_val: str,
    status: str,
    issue: str = "",
    plan: str = "",
    groomed: str = "",
) -> str:
    """Build research-style frontmatter with metadata block.

    Returns:
        YAML frontmatter string.
    """
    meta: dict[str, str] = {
        "topic": _title_to_slug(name),
        "source": source or "Not specified",
        "added": added or _today(),
        "priority": priority,
        "type": type_val,
        "status": status,
    }
    if issue:
        meta["issue"] = issue
    if plan:
        meta["plan"] = plan
    if groomed:
        meta["groomed"] = groomed
    post = frontmatter.Post(
        "", name=name.replace('"', "'"), description=(description or "").replace('"', "'"), metadata=meta
    )
    return dump_frontmatter(post)


def _apply_field_to_result(key_lower: str, val: str) -> tuple[str, str, str, str, str, str]:
    """Return (desc, suggested, research, decision, files_val, required_work) with val applied to the matching key.

    Returns:
        Tuple of (desc, suggested, research, decision, files_val, required_work).
    """
    result: list[str] = ["", "", "", "", "", ""]
    if key_lower in FIELD_TO_INDEX:
        result[FIELD_TO_INDEX[key_lower]] = val
    return (result[0], result[1], result[2], result[3], result[4], result[5])


def _extract_body_field_pairs(body: str) -> list[tuple[str, str]]:
    """Extract (key, value) pairs from body until first ## heading. Stops at ## Groomed or ## .

    Returns:
        List of (key, value) tuples.
    """
    field_re = re.compile(r"^\*\*([^*]+)\*\*:\s*(.*)$", re.DOTALL)
    pairs: list[tuple[str, str]] = []
    current_key = ""
    current_val: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_key:
                pairs.append((current_key, "\n".join(current_val).strip()))
            return pairs
        m = field_re.match(line)
        if m:
            if current_key:
                pairs.append((current_key, "\n".join(current_val).strip()))
            current_key = m.group(1).strip()
            current_val = [m.group(2).strip()] if m.group(2).strip() else []
        elif current_key:
            current_val.append(line)
    if current_key:
        pairs.append((current_key, "\n".join(current_val).strip()))
    return pairs


def _merge_field_into_result(
    key: str, val: str, desc: str, suggested: str, research: str, decision: str, files_val: str, required_work: str
) -> tuple[str, str, str, str, str, str]:
    """Merge one field (key, val) into result tuple.

    Returns:
        Updated (desc, suggested, research, decision, files_val, required_work).
    """
    d, s, r, dec, f, req = _apply_field_to_result(key.lower(), val)
    return (d or desc, s or suggested, r or research, dec or decision, f or files_val, req or required_work)


def _parse_body_extra_fields(body: str) -> tuple[str, str, str, str, str, str]:
    """Extract Description, Suggested location, Research first, Decision needed, Files, Required work from body.

    Returns:
        Tuple of (desc, suggested, research, decision, files_val, required_work).
    """
    desc, suggested, research, decision, files_val, required_work = "", "", "", "", "", ""
    for key, val in _extract_body_field_pairs(body):
        desc, suggested, research, decision, files_val, required_work = _merge_field_into_result(
            key, val, desc, suggested, research, decision, files_val, required_work
        )
    return desc, suggested, research, decision, files_val, required_work


def _extract_groomed_section(body: str) -> str:
    """Extract full ## Groomed (date) ... section from body.

    Returns:
        Groomed section text or empty string.
    """
    m = re.search(r"(## Groomed\s*\([^)]*\)\s*\n[\s\S]*?)(?=\n## |\Z)", body)
    return m.group(1).rstrip() if m else ""


def _build_body_extra_only(
    suggested: str, research: str, decision: str, files_val: str, required_work: str, groomed_section: str
) -> str:
    """Build body with only extra fields (no duplication) and ## Groomed if present.

    Returns:
        Body string with extra fields and groomed section.
    """
    parts: list[str] = []
    if suggested:
        parts.append(f"**Suggested location**: {suggested}")
    if research:
        parts.append(f"**Research first**: {research}")
    if decision:
        parts.append(f"**Decision needed**: {decision}")
    if files_val:
        parts.append(f"**Files**: {files_val}")
    if required_work:
        parts.append(f"**Required work**:\n{required_work}")
    if groomed_section:
        parts.append(groomed_section)
    return "\n\n".join(parts) + "\n" if parts else ""


def _append_or_replace_section(body: str, section_name: str, content: str) -> str:
    """Append or replace a section in body. section_name: Fact-Check, RT-ICA, or groomed subsection (Reproducibility, Priority, etc.).

    Returns:
        Updated body string.
    """
    content = content.strip()
    if not content:
        return body
    today = _today()
    section_lower = section_name.strip().lower()
    if section_lower in {"fact-check", "rt-ica"}:
        header = f"## {section_name.strip()}\n\n"
        # [^\n]* absorbs trailing text like ": BLOCKED" on the heading line.
        # Using \s* instead would silently fail on headings with suffixes.
        section_re = re.compile(
            rf"\n## {re.escape(section_name.strip())}[^\n]*\n[\s\S]*?(?=\n## |\Z)", re.IGNORECASE | re.MULTILINE
        )
        new_block = header + content + "\n"
        if section_re.search(body):
            return section_re.sub(f"\n{new_block}", body)
        return body.rstrip() + "\n\n" + new_block
    # Treat known groomed subsections AND any unrecognized section name as a
    # ### subsection under ## Groomed.  Previous code silently dropped unknown
    # section names (returned body unchanged), violating "no silent data loss".
    groomed_header = f"## Groomed ({today})"
    sub_header = f"### {section_name.strip()}\n\n"
    # [^\n]* absorbs trailing text like ": BLOCKED" on the heading line.
    # Using \s* instead would silently fail on headings with suffixes.
    # This regex only searches within groomed_body (scoped by groomed_re below).
    sub_re = re.compile(
        rf"\n### {re.escape(section_name.strip())}[^\n]*\n[\s\S]*?(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
    )
    new_block = sub_header + content + "\n"
    groomed_re = re.compile(r"(## Groomed\s*\([^)]*\)\s*\n)([\s\S]*?)(?=\n## |\Z)", re.MULTILINE)
    match = groomed_re.search(body)
    if match:
        groomed_body = match.group(2)
        if sub_re.search(groomed_body):
            new_groomed_body = sub_re.sub(f"\n{new_block}", groomed_body)
        else:
            new_groomed_body = groomed_body.rstrip() + "\n\n" + new_block
        return groomed_re.sub(match.group(1) + new_groomed_body + "\n", body, count=1)
    return body.rstrip() + "\n\n" + groomed_header + "\n\n" + new_block


def _write_groomed_to_item_file(
    filepath: Path,
    groomed_content: str,
    section_name: str | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
) -> None:
    """Merge groomed content into per-item file.

    Updates frontmatter groomed date and body.
    If section_name is set, append/replace that section only (incremental).
    When entry_id or replace_section is set, uses entry_blocks.rewrite_section().
    Else replace full ## Groomed.
    """
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        typer.echo("ERROR: Item file has no frontmatter", err=True)
        raise typer.Exit(1)
    parts = text.split("---", 2)
    if len(parts) < MIN_FRONTMATTER_PARTS:
        typer.echo("ERROR: Malformed item file", err=True)
        raise typer.Exit(1)
    fm_text, body = parts[1].strip(), parts[2].strip()
    today = _today()
    if section_name and (entry_id or replace_section):
        new_body = _rewrite_section(body, groomed_content, entry_id=entry_id, replace=replace_section)
    elif section_name:
        new_body = _append_or_replace_section(body, section_name, groomed_content)
    else:
        groomed_section = f"## Groomed ({today})\n\n{groomed_content.strip()}"
        groomed_re = re.compile(r"\n## Groomed\s*\([^)]*\)\s*\n[\s\S]*?(?=\n## |\Z)", re.MULTILINE)
        if groomed_re.search(body):
            new_body = groomed_re.sub(f"\n{groomed_section}\n", body)
        else:
            new_body = body.rstrip() + "\n\n" + groomed_section + "\n"
    try:
        post = loads_frontmatter(text)
        meta_block = post.metadata.get("metadata")
        if isinstance(meta_block, dict):
            updated = dict(meta_block)
            updated["groomed"] = today
            updated["status"] = BacklogState.GROOMED.value
            post.metadata["metadata"] = updated
        else:
            post.metadata["groomed"] = today
        post.content = new_body
        new_content = dump_frontmatter(post)
    except (ValueError, KeyError, TypeError):
        new_content = "---\n" + fm_text + "\n---\n\n" + new_body
        if "groomed:" not in fm_text:
            new_content = new_content.replace("---\n", f'---\ngroomed: "{today}"\n', 1)
    filepath.write_text(new_content, encoding="utf-8")


def _sync_groomed_to_github_issue(
    repo_obj: Repository, issue_num: int, groomed_content: str, section_name: str | None = None
) -> bool:
    """Append or merge groomed content into GitHub issue body. GitHub is canonical.

    Returns:
        True if the issue body was actually updated, False otherwise.
    """
    try:
        issue = repo_obj.get_issue(issue_num)
        body = issue.body or ""
        content = groomed_content.strip()
        if not content:
            return False
        today = _today()
        if section_name and section_name.lower() not in {"groomed", ""}:
            new_body = _append_or_replace_section(body, section_name, content)
        else:
            groomed_re = re.compile(r"\n## Groomed\s*\([^)]*\)\s*\n[\s\S]*?(?=\n## |\Z)", re.MULTILINE)
            block = f"\n## Groomed ({today})\n\n{content}\n"
            new_body = groomed_re.sub(block, body) if groomed_re.search(body) else body.rstrip() + "\n\n" + block
        if new_body == body:
            return False
        issue.edit(body=new_body)
    except GithubException as e:
        typer.echo(f"  WARNING: Could not sync to GitHub issue: {e}", err=True)
        return False
    else:
        return True


def _resolve_groomed_content(
    section: str | None, content: str | None, groomed_content: str | None, groomed_file: str | None
) -> tuple[str, str | None]:
    """Resolve groomed content from section/content, groomed_content, groomed_file, or stdin.

    Returns:
        Tuple of (content_string, section_name_or_None).
    """
    if section is not None and content is not None:
        return content, section
    if groomed_content is not None:
        return groomed_content, None
    if groomed_file:
        return Path(groomed_file).read_text(encoding="utf-8"), None
    return sys.stdin.read(), None


def _handle_update_groomed(
    item: dict,
    groomed_content_val: str,
    section_name: str | None,
    repo: str,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
) -> None:
    """Handle groomed content update: GitHub-first, then cache locally.

    Write order: (1) GitHub issue (canonical), (2) local file (cache).
    If item has no issue, creates one for P0/P1 first.
    Sets last_synced after successful GitHub write.
    """
    filepath = Path(item["_file_path"])
    issue_ref = item.get("_issue")

    # Step 1: Ensure GitHub issue exists for P0/P1 items
    if not issue_ref and not item.get("_skip") and item.get("_section") in {"P0", "P1", "P2", "Ideas"}:
        issue_ref = _ensure_github_issue(item, filepath, repo)

    # Step 2: Write to GitHub FIRST (canonical source of truth)
    github_synced = False
    if issue_ref:
        github_synced = _write_groomed_to_github(issue_ref, groomed_content_val, section_name, repo)

    # Step 3: Write to local file (cache)
    _write_groomed_to_item_file(
        filepath, groomed_content_val, section_name, entry_id=entry_id, replace_section=replace_section
    )
    typer.echo(f"Updated {filepath.name} with groomed content")

    # Step 4: Set last_synced if GitHub write succeeded
    if github_synced:
        _update_item_metadata(filepath, {"metadata": {"last_synced": _now_iso()}})


def _ensure_github_issue(item: dict, filepath: Path, repo: str) -> str | None:
    """Create GitHub issue if item doesn't have one.

    Uses _try_get_github for graceful fallback when GitHub is unavailable.

    Returns:
        Issue ref like '#42', or None if no issue was created.
    """
    repository = _try_get_github(repo)
    if not repository:
        typer.echo("  INFO: GitHub unavailable — working locally only")
        return None
    try:
        issue_num = create_issue_for_item(repository, item, dry_run=False)
    except typer.Exit:
        raise
    except GithubException as e:
        typer.echo(f"  WARNING: Could not create issue: {e}", err=True)
        return None
    else:
        if not issue_num:
            return None
        _update_item_metadata(filepath, {"metadata": {"issue": f"#{issue_num}"}}, set_synced=True)
        typer.echo(f"  Created GitHub issue #{issue_num}")
        return f"#{issue_num}"


def _write_groomed_to_github(issue_ref: str, content: str, section_name: str | None, repo: str) -> bool:
    """Write groomed content to GitHub issue.

    Gracefully falls back to local-only when GitHub is unavailable.

    Returns:
        True if content was synced to GitHub, False otherwise.
    """
    repository = _try_get_github(repo)
    if not repository:
        typer.echo(f"  INFO: GitHub unavailable — {issue_ref} will sync on next `backlog pull` or `backlog sync`")
        return False
    try:
        num = int(issue_ref.lstrip("#"))
        updated = _sync_groomed_to_github_issue(repository, num, content, section_name)
    except GithubException as e:
        typer.echo(f"  WARNING: Could not sync to GitHub: {e}", err=True)
        return False
    else:
        if updated:
            typer.echo(f"  Synced to GitHub issue {issue_ref}")
            try:
                issue = repository.get_issue(num)
                apply_github_transition(repository, issue, "needs-grooming", "groomed")
            except (GithubException, StateTransitionError) as e:
                typer.echo(f"  WARNING: Could not update grooming label: {e}", err=True)
        else:
            typer.echo(f"  No changes to sync to GitHub issue {issue_ref}")
        return updated


def _apply_status_in_progress(item: dict, repo: str) -> None:
    """Set GitHub issue label to status:in-progress via state handler."""
    try:
        repository = _get_github(repo)
        num = item.get("_issue", "").lstrip("#")
        issue = repository.get_issue(int(num))
        current_status = next(
            (lbl.name.removeprefix("status:") for lbl in issue.labels if lbl.name.startswith("status:")), None
        )
        apply_github_transition(repository, issue, current_status, BacklogState.IN_PROGRESS.value)
        typer.echo("  Status: in-progress")
    except (GithubException, StateTransitionError) as e:
        typer.echo(f"  WARNING: Could not set status: {e}", err=True)


def _apply_plan_to_item(item: dict, plan: str, repo: str = DEFAULT_REPO) -> bool:
    """Apply plan update: write to GitHub Issue first (comment), then update local cache.

    GH-first: posts a plan comment on the linked GitHub Issue before updating local.
    If GH is unavailable, local update still succeeds.

    Returns:
        True if updated, False otherwise.
    """
    filepath_str = item.get("_file_path")
    if not filepath_str:
        return False
    _update_item_metadata(Path(filepath_str), {"metadata": {"plan": plan}})

    # GH-first: post plan reference as a comment on the linked issue
    issue_ref = item.get("_issue", "")
    if issue_ref:
        repository = _try_get_github(repo)
        if repository is not None:
            try:
                num = int(issue_ref.lstrip("#"))
                gh_issue = repository.get_issue(num)
                gh_issue.create_comment(f"**Plan**: {plan}")
                typer.echo(f"  Plan comment posted to issue {issue_ref}")
            except GithubException as e:
                typer.echo(f"  WARNING: Could not post plan to issue {issue_ref}: {e}", err=True)

    return True


@app.command()
def update(
    selector: Annotated[str, typer.Argument(help="Title substring, #N, bare number, or GitHub issue URL")],
    plan: Annotated[str | None, typer.Option("--plan", "-p")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    create_issue: Annotated[bool, typer.Option("--create-issue")] = False,
    groomed_file: Annotated[str | None, typer.Option("--groomed-file")] = None,
    section: Annotated[str | None, typer.Option("--section")] = None,
    content: Annotated[str | None, typer.Option("--content")] = None,
    entry_id: Annotated[str | None, typer.Option("--entry-id", help="Replace a specific entry by ID")] = None,
    replace_section: Annotated[
        bool, typer.Option("--replace-section", help="Replace entire section instead of appending")
    ] = False,
    reason: Annotated[str | None, typer.Option("--reason", help="Reason for striking/replacing an entry")] = None,
    groomed: Annotated[bool, typer.Option("--groomed")] = False,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Update item: add Plan, set status:in-progress, create issue, or write groomed content."""
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        typer.echo(f"ERROR: No item found for: {selector}", err=True)
        raise typer.Exit(1)

    has_groomed = groomed or groomed_file or (section and content)
    if has_groomed:
        if not item.get("_file_path"):
            typer.echo("ERROR: Item has no file path", err=True)
            raise typer.Exit(1)
        groomed_content_val, section_name = _resolve_groomed_content(section, content, None, groomed_file)
        if not groomed_content_val.strip():
            typer.echo("ERROR: No groomed content provided", err=True)
            raise typer.Exit(1)
        _handle_update_groomed(
            item,
            groomed_content_val,
            section_name,
            repo,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
        )
        return

    if plan:
        _apply_plan_to_item(item, plan, repo)
        typer.echo(f"  Plan: {plan}")

    if create_issue and not item.get("_issue") and item.get("_section") in {"P0", "P1"}:
        issue_num = _create_issue_and_update_item(item, repo)
        if issue_num:
            typer.echo(f"  Issue: #{issue_num}")

    if status == "in-progress" and item.get("_issue"):
        _apply_status_in_progress(item, repo)


def _view_result_from_local_item(item: dict) -> dict[str, Any]:
    """Build view result dict from a local backlog item.

    Returns:
        Dict with title, priority, issue, plan, file_path, groomed, and
        optionally description/source/added/status from the per-item file.
    """
    result: dict[str, Any] = {
        "title": item.get("_title", ""),
        "priority": item.get("_section", ""),
        "issue": item.get("_issue", ""),
        "plan": item.get("**Plan**", ""),
        "file_path": item.get("_file_path", ""),
        "groomed": bool(item.get("_groomed")),
        "status": item.get("_status", ""),
    }
    fp = item.get("_file_path")
    if fp and Path(fp).exists():
        raw = Path(fp).read_text(encoding="utf-8")
        post = loads_frontmatter(raw)
        fm_raw = post.metadata if hasattr(post, "metadata") else (post[0] if isinstance(post, tuple) else {})
        fm: dict = dict(fm_raw) if isinstance(fm_raw, dict) else {}
        meta_raw = fm.get("metadata", {})
        meta: dict = dict(meta_raw) if isinstance(meta_raw, dict) else {}
        result["description"] = str(fm.get("description", ""))
        result["source"] = str(meta.get("source", fm.get("source", "")))
        result["added"] = str(meta.get("added", fm.get("added", "")))
    return result


def _view_enrich_from_github(result: dict[str, Any], issue_num: str, repo: str) -> bool:
    """Enrich view result with live GitHub issue data.

    Returns:
        True if GitHub data was fetched, False if unavailable or errored.
    """
    gh_repo = _try_get_github(repo)
    if gh_repo is None:
        return False
    try:
        gh_issue = gh_repo.get_issue(int(issue_num))
    except GithubException:
        return False
    result["number"] = gh_issue.number
    result["title"] = gh_issue.title
    result["state"] = gh_issue.state
    result["body"] = gh_issue.body or ""
    result["labels"] = [lb.name for lb in gh_issue.labels]
    ms = gh_issue.milestone
    result["milestone"] = ms.title if ms else ""
    for lb in result["labels"]:
        if lb.startswith("priority:"):
            result["priority"] = lb.split(":", 1)[1].upper()
        if lb.startswith("status:"):
            result["status"] = lb.split(":", 1)[1]
    return True


def _view_print_text(result: dict[str, Any], *, offset: int = 0, limit: int = 0) -> None:
    """Print view result in human-readable text format."""
    typer.echo(f"Title:       {result.get('title', '')}")
    # Issue line: prefer number over issue ref
    issue_display = f"#{result['number']}" if result.get("number") else result.get("issue", "")
    if issue_display:
        typer.echo(f"Issue:       {issue_display}")
    # Single-line fields
    VIEW_FIELDS = [
        ("state", "State:      "),
        ("priority", "Priority:   "),
        ("status", "Status:     "),
        ("milestone", "Milestone:  "),
        ("plan", "Plan:       "),
        ("file_path", "Local file: "),
    ]
    for key, label in VIEW_FIELDS:
        val = result.get(key)
        if val:
            typer.echo(f"{label} {val}")
    if result.get("labels"):
        typer.echo(f"Labels:      {', '.join(result['labels'])}")
    if result.get("groomed"):
        typer.echo("Groomed:     yes")
    # Multi-line fields
    _view_print_body_fields(result, offset=offset, limit=limit)


def _view_print_body_fields(result: dict[str, Any], *, offset: int = 0, limit: int = 0) -> None:
    """Print description and body fields for view output.

    Args:
        result: View result dict.
        offset: Number of lines to skip from the start of the body.
        limit: Maximum number of lines to show (0 = unlimited).
    """
    if result.get("description"):
        typer.echo(f"\nDescription:\n  {result['description']}")
    if result.get("body"):
        body = result["body"]
        lines = body.splitlines()
        total = len(lines)
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]
        body = "\n".join(lines)
        typer.echo(f"\nIssue Body ({total} lines total):\n  {body}")
        remaining = total - offset - len(lines)
        if remaining > 0:
            typer.echo(f"\n  ... {remaining} more lines (use --offset / --limit to paginate)")


@app.command()
def view(
    selector: Annotated[str, typer.Argument(help="Issue URL, #N, bare number, or title substring")],
    output_format: Annotated[str, typer.Option("--format", "-f")] = "text",
    offset: Annotated[int, typer.Option("--offset", help="Skip N lines from body start")] = 0,
    limit: Annotated[int, typer.Option("--limit", help="Show at most N body lines (0=all)")] = 0,
    show: Annotated[str | None, typer.Option("--show", help="Filter to a specific section name")] = None,
    since: Annotated[str | None, typer.Option("--since", help="Show entries since ISO timestamp")] = None,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """View a backlog item or GitHub issue by URL, #N, bare number, or title.

    Accepts:
      - https://github.com/owner/repo/issues/123
      - #123
      - 123
      - title substring

    When the selector is an issue reference (URL, #N, bare number), fetches
    the issue directly from GitHub via PyGithub if no local item matches.
    Use --offset and --limit to paginate long issue bodies.
    """
    items = parse_backlog()
    item = find_item(items, selector)
    issue_num = _parse_issue_selector(selector)

    result: dict[str, Any] = _view_result_from_local_item(item) if item else {}

    if issue_num:
        if not _view_enrich_from_github(result, issue_num, repo) and not item:
            typer.echo(f"ERROR: Issue #{issue_num} not found or GitHub unavailable", err=True)
            raise typer.Exit(1)
    elif not item:
        typer.echo(f"ERROR: No item found matching: {selector}", err=True)
        raise typer.Exit(1)

    if output_format == "json":
        typer.echo(json.dumps(result, indent=2, default=str))
    else:
        _view_print_text(result, offset=offset, limit=limit)


@app.command()
def groom(
    selector: Annotated[str, typer.Argument(help="Title substring, #N, bare number, or GitHub issue URL")],
    groomed_file: Annotated[str | None, typer.Option("--groomed-file")] = None,
    section: Annotated[str | None, typer.Option("--section")] = None,
    content: Annotated[str | None, typer.Option("--content")] = None,
    entry_id: Annotated[str | None, typer.Option("--entry-id", help="Replace a specific entry by ID")] = None,
    replace_section: Annotated[
        bool, typer.Option("--replace-section", help="Replace entire section instead of appending")
    ] = False,
    reason: Annotated[str | None, typer.Option("--reason", help="Reason for striking/replacing an entry")] = None,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Write groomed content into per-item file. Use --groomed-file, --section/--content (incremental), or stdin. Syncs to GitHub issue when item has one."""
    has_input = groomed_file or (section and content)
    update(
        selector=selector,
        plan=None,
        status=None,
        create_issue=False,
        groomed_file=groomed_file,
        section=section,
        content=content,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
        groomed=not has_input,
        repo=repo,
    )


def _extract_normalize_metadata(fm: dict, meta: dict) -> dict[str, str]:
    """Extract normalized metadata from frontmatter and metadata dicts.

    Returns:
        Normalized metadata dict.
    """
    plan = str(meta.get("plan") or fm.get("plan") or "")
    return {
        "name": str(fm.get("name") or fm.get("title") or "").strip(),
        "description": str(fm.get("description") or "").strip(),
        "source": str(meta.get("source") or fm.get("source") or "Not specified"),
        "added": str(meta.get("added") or fm.get("added") or _today()),
        "priority": str(meta.get("priority") or fm.get("priority") or "P2"),
        "type_val": str(meta.get("type") or fm.get("type") or "Feature"),
        "status": str(meta.get("status") or fm.get("status") or "open"),
        "issue": str(meta.get("issue") or fm.get("issue") or ""),
        "plan": "" if plan.upper() == "N/A" else plan,
        "groomed": str(meta.get("groomed") or fm.get("groomed") or ""),
    }


def _build_normalized_content(filepath: Path) -> str | None:
    """Build normalized content for one file.

    Returns:
        Normalized content string or None if skip.
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as e:
        typer.echo(f"  Skip {filepath.name}: {e}", err=True)
        return None
    if not text.startswith("---"):
        return None
    try:
        post = loads_frontmatter(text)
        fm = post.metadata or {}
        body = post.content or ""
    except (ValueError, KeyError, TypeError):
        return None
    meta_raw = fm.get("metadata")
    meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}
    md = _extract_normalize_metadata(fm, meta)
    if not md["name"]:
        return None
    parsed = _parse_body_extra_fields(body)
    if parsed[0] and not md["description"]:
        md["description"] = parsed[0]
    groomed = _extract_groomed_section(body)
    new_body = _build_body_extra_only(parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], groomed)
    fm_str = _build_backlog_frontmatter(
        md["name"],
        md["description"],
        md["source"],
        md["added"],
        md["priority"],
        md["type_val"],
        md["status"],
        md["issue"],
        md["plan"],
        md["groomed"],
    )
    out = fm_str.rstrip()
    return out + ("\n" if not out.endswith("\n\n") else "") + new_body


def _normalize_item_file(filepath: Path, dry_run: bool) -> bool:
    """Normalize one backlog item file.

    Returns:
        True if updated, False if skipped.
    """
    content = _build_normalized_content(filepath)
    if content is None:
        return False
    if not dry_run:
        filepath.write_text(content, encoding="utf-8")
    return True


def _infer_correct_status(filepath: Path) -> str:
    """Infer the correct state-machine status for a backlog item whose local status is 'open'.

    Decision rules (applied in priority order):
    1. If metadata.status is already a valid state-machine value — return it unchanged.
    2. If metadata.groomed is set (non-empty) — item has been groomed → 'groomed'.
    3. Otherwise — item not yet groomed → 'needs-grooming'.

    Returns:
        A valid BacklogState value string.
    """
    valid_states = {s.value for s in BacklogState}
    try:
        text = filepath.read_text(encoding="utf-8")
        post = loads_frontmatter(text)
        fm = post.metadata or {}
        meta_raw = fm.get("metadata", {})
        meta: dict = dict(meta_raw) if isinstance(meta_raw, dict) else {}
        status = str(meta.get("status") or fm.get("status") or "open").strip()
        if status in valid_states:
            return status
        # 'open' or any other legacy value — derive from groomed field
        groomed = str(meta.get("groomed") or fm.get("groomed") or "").strip()
        if groomed:
            return BacklogState.GROOMED.value
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return BacklogState.NEEDS_GROOMING.value


@app.command(name="migrate-status")
def migrate_status(
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Migrate local per-item files with status 'open' to valid state-machine states.

    Rule: items with a groomed date → 'groomed'; items without → 'needs-grooming'.

    Does not touch GitHub labels (run 'backlog sync' afterwards to sync labels).
    Use --dry-run to preview changes without writing files.
    """
    if not BACKLOG_DIR.exists():
        typer.echo(f"ERROR: {BACKLOG_DIR} not found", err=True)
        raise typer.Exit(1)

    valid_states = {s.value for s in BacklogState}
    pattern = re.compile(r"^(p0|p1|p2|idea|ideas|completed)-[a-z0-9-]+\.md$", re.IGNORECASE)
    files = sorted(f for f in BACKLOG_DIR.glob("*.md") if pattern.match(f.name))

    migrated = skipped = already_valid = 0
    for filepath in files:
        try:
            text = filepath.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            post = loads_frontmatter(text)
            fm = post.metadata or {}
            meta_raw = fm.get("metadata", {})
            meta: dict = dict(meta_raw) if isinstance(meta_raw, dict) else {}
            current = str(meta.get("status") or fm.get("status") or "open").strip()
            if current in valid_states:
                already_valid += 1
                if verbose:
                    typer.echo(f"  {filepath.name}: already {current!r}")
                continue
            # 'open' or other unknown value — needs migration
            new_status = _infer_correct_status(filepath)
            if dry_run:
                typer.echo(f"  [dry-run] {filepath.name}: {current!r} → {new_status!r}")
            else:
                _update_item_metadata(filepath, {"metadata": {"status": new_status}})
                typer.echo(f"  {filepath.name}: {current!r} → {new_status!r}")
            migrated += 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            typer.echo(f"  Skip {filepath.name}: {e}", err=True)
            skipped += 1

    action = "Would migrate" if dry_run else "Migrated"
    typer.echo(f"\n{action} {migrated} item(s) to valid states. Already valid: {already_valid}. Skipped: {skipped}.")
    if dry_run and migrated:
        typer.echo("Re-run without --dry-run to apply changes.")
    if migrated and not dry_run:
        typer.echo("Run 'backlog sync' to push updated labels to GitHub.")


@app.command()
def normalize(dry_run: Annotated[bool, typer.Option("--dry-run")] = False) -> None:
    """One-off: rewrite per-item files to research-style metadata, remove body duplication."""
    if not BACKLOG_DIR.exists():
        typer.echo(f"ERROR: {BACKLOG_DIR} not found", err=True)
        raise typer.Exit(1)
    pattern = re.compile(r"^(p0|p1|p2|idea|ideas|completed)-[a-z0-9-]+\.md$", re.IGNORECASE)
    files = sorted(f for f in BACKLOG_DIR.glob("*.md") if pattern.match(f.name))
    if not files:
        typer.echo("No backlog item files found")
        return
    updated = sum(1 for f in files if _normalize_item_file(f, dry_run))
    typer.echo(f"Normalized {updated} item file(s)" + (" [dry-run]" if dry_run else ""))


def _fetch_github_issue_body(repo_obj: Repository, issue_num: int) -> str | None:
    """Fetch GitHub issue body text.

    Args:
        repo_obj: PyGithub Repository object.
        issue_num: Issue number (without '#').

    Returns:
        Issue body string, or None on error.
    """
    try:
        return repo_obj.get_issue(issue_num).body or ""
    except GithubException as e:
        typer.echo(f"  WARNING: Could not fetch issue #{issue_num}: {e}", err=True)
        return None


def _extract_sections(text: str) -> dict[str, str]:
    """Extract '## Section' content blocks from markdown text.

    Args:
        text: Markdown body text.

    Returns:
        Dict mapping section heading (e.g. '## Story') to its content (not including heading).
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line.strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections


def _reconstruct_body_from_sections(
    local_sections: dict[str, str], github_sections: dict[str, str], result_sections: dict[str, str]
) -> str:
    """Reconstruct body from merged sections, preserving local order then appending GitHub-only sections.

    Args:
        local_sections: Original local section map (preserves order).
        github_sections: GitHub section map (source of new sections).
        result_sections: Merged result to render from.

    Returns:
        Reconstructed body string ending with newline.
    """
    seen: set[str] = set()
    parts: list[str] = []
    for heading in local_sections:
        content = result_sections[heading]
        parts.append(f"{heading}\n\n{content}" if content else heading)
        seen.add(heading)
    for heading in github_sections:
        if heading not in seen:
            content = result_sections[heading]
            parts.append(f"{heading}\n\n{content}" if content else heading)
    return "\n\n".join(parts) + "\n"


def _merge_sections(local_body: str, github_body: str) -> tuple[str, bool]:
    """Merge GitHub issue body into local body by section.

    For each section in GitHub body:
    - If the section exists locally, keep the longer version.
    - If the section is only in GitHub, append it to the local body.

    Args:
        local_body: Current local file body content.
        github_body: GitHub issue body content.

    Returns:
        Tuple of (merged_body, was_modified).
    """
    local_sections = _extract_sections(local_body)
    github_sections = _extract_sections(github_body)

    if not github_sections:
        return local_body, False

    modified = False
    result_sections: dict[str, str] = dict(local_sections)

    for heading, gh_content in github_sections.items():
        if heading in local_sections:
            if len(gh_content) > len(local_sections[heading]):
                result_sections[heading] = gh_content
                modified = True
        else:
            result_sections[heading] = gh_content
            modified = True

    if not modified:
        return local_body, False

    return _reconstruct_body_from_sections(local_sections, github_sections, result_sections), True


def _pull_item_create_new(
    item: dict, issue_num: int, issue_ref: str, title: str, github_body: str, dry_run: bool
) -> bool:
    """Create a new local file from a GitHub issue body.

    Args:
        item: Parsed backlog item dict.
        issue_num: GitHub issue number.
        issue_ref: Issue reference string (e.g. "#42").
        title: Issue title.
        github_body: Body text fetched from GitHub.
        dry_run: If True, print what would happen without writing.

    Returns:
        True if created (or would create in dry-run).
    """
    slug = _title_to_slug(title)
    priority = item.get("**Priority**", "P2")
    filename = f"{priority.lower()}-{slug}.md"
    filepath = BACKLOG_DIR / filename
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    if dry_run:
        typer.echo(f"  [dry-run] Would create {filename} from #{issue_num}: {title}")
        return True
    fm_str = _build_backlog_frontmatter(
        title,
        item.get("**Description**", ""),
        item.get("**Source**", "Not specified"),
        item.get("**Added**", _today()),
        priority,
        item.get("**Type**", "Feature"),
        "open",
        issue_ref,
        item.get("**Plan**", ""),
        "",
    )
    filepath.write_text(fm_str.rstrip() + "\n\n" + github_body, encoding="utf-8")
    typer.echo(f"  Created #{issue_num} -> {filename}: {title}")
    return True


def _pull_item_update_existing(
    item: dict, issue_num: int, title: str, filepath: Path, github_body: str, dry_run: bool, force: bool
) -> bool:
    """Update an existing local file with content from a GitHub issue body.

    Args:
        item: Parsed backlog item dict.
        issue_num: GitHub issue number.
        title: Issue title.
        filepath: Path to the existing local file.
        github_body: Body text fetched from GitHub.
        dry_run: If True, print what would happen without writing.
        force: If True, overwrite local content even if local is longer.

    Returns:
        True if updated (or would update in dry-run), False if no change needed.
    """
    local_body = item.get("_raw_body", "")

    if force:
        if dry_run:
            typer.echo(f"  [dry-run] Would overwrite {filepath.name} from #{issue_num}: {title}")
            return True
        post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
        post.content = github_body
        filepath.write_text(dump_frontmatter(post), encoding="utf-8")
        typer.echo(f"  Pulled #{issue_num} -> {filepath.name}: {title}")
        return True

    merged_body, modified = _merge_sections(local_body, github_body)
    if not modified:
        return False

    if dry_run:
        typer.echo(f"  [dry-run] Would merge #{issue_num} -> {filepath.name}: {title}")
        return True

    post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
    post.content = merged_body
    filepath.write_text(dump_frontmatter(post), encoding="utf-8")
    typer.echo(f"  Pulled #{issue_num} -> {filepath.name}: {title}")
    return True


def _pull_item(item: dict, repo_obj: Repository, dry_run: bool, force: bool) -> bool:
    """Pull GitHub issue body into local per-item file.

    Args:
        item: Parsed backlog item dict.
        repo_obj: PyGithub Repository object.
        dry_run: If True, print what would happen without writing.
        force: If True, overwrite local content even if local is longer.

    Returns:
        True if pulled (or would pull in dry-run), False if skipped.
    """
    issue_ref = item.get("_issue", "")
    num_str = issue_ref.lstrip("#")
    if not num_str.isdigit():
        return False

    issue_num = int(num_str)
    title = item.get("_title", "")
    filepath_str = item.get("_file_path")

    github_body = _fetch_github_issue_body(repo_obj, issue_num)
    if github_body is None:
        return False

    if not filepath_str or not Path(filepath_str).exists():
        return _pull_item_create_new(item, issue_num, issue_ref, title, github_body, dry_run)

    return _pull_item_update_existing(item, issue_num, title, Path(filepath_str), github_body, dry_run, force)


def _pull_single_by_selector(selector: str, repo: str) -> None:
    """Resolve selector to a single GitHub issue and pull it into the local cache."""
    try:
        result = _backlog_operations.pull_by_selector(selector, repo)
    except _ItemNotFoundError:
        typer.echo(f"No backlog item found matching: {selector!r}", err=True)
        raise typer.Exit(code=1) from None
    except _BacklogError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from None

    for msg in result.get("messages") or []:
        typer.echo(msg)
    for warn in result.get("warnings") or []:
        typer.echo(f"Warning: {warn}", err=True)
    file_path = result.get("file_path")
    if file_path:
        typer.echo(f"Pulled issue into {file_path}.")
    else:
        typer.echo(f"Failed to pull issue for {selector!r}.", err=True)


@app.command()
def pull(
    selector: Annotated[
        str | None,
        typer.Argument(
            help="Optional selector to pull a single issue: #N, bare number, GitHub URL, or title substring. When omitted, pulls all issues."
        ),
    ] = None,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite local content even if local is newer/longer")
    ] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Show entry-level diff instead of merging")] = False,
) -> None:
    """Pull issue body content from GitHub into local per-item files.

    When SELECTOR is provided, pulls a single issue by #N, bare number,
    GitHub URL, or title substring. When omitted, pulls all issues.

    Also auto-migrates P0/P1 items that lack GitHub Issues by creating them.
    Merges by section — keeps longer version of each section.
    Skips items with no issue number (after migration).
    Use --diff to show an entry-level diff without merging.
    """
    if selector is not None:
        _pull_single_by_selector(selector, repo)
        return

    items = parse_backlog()

    # Auto-migration: create missing GitHub Issues for P0/P1 items
    items_without_issues = [
        it for it in items if it.get("_section") in {"P0", "P1"} and not it.get("_skip") and not it.get("_issue")
    ]
    if items_without_issues:
        typer.echo(f"Auto-migrating {len(items_without_issues)} P0/P1 item(s) to GitHub Issues...")
        _sync_create_missing_issues(items, repo, dry_run)
        # Re-parse after migration to pick up updated issue numbers
        items = parse_backlog()

    candidates = [it for it in items if it.get("_issue") and not it.get("_skip")]

    if not candidates:
        typer.echo("No items with GitHub issue numbers found.")
        return

    typer.echo(f"Checking {len(candidates)} item(s) with GitHub issues...")
    repository = _get_github(repo)
    pulled = 0
    for item in candidates:
        if _pull_item(item, repository, dry_run, force):
            pulled += 1

    if pulled == 0:
        typer.echo("Nothing to pull — local files are up to date.")
    else:
        suffix = " [dry-run]" if dry_run else ""
        typer.echo(f"Pulled {pulled} item(s){suffix}.")


@app.command(name="strike-entry")
def strike_entry(
    selector: Annotated[str, typer.Argument(help="Title substring, #N, bare number, or GitHub issue URL")],
    section_name: Annotated[str, typer.Option("--section", help="Section containing the entry")],
    entry_id: Annotated[str, typer.Option("--entry-id", help="ID of the entry to strike")],
    reason: Annotated[str | None, typer.Option("--reason", help="Reason for striking")] = None,
    repo: Annotated[str, typer.Option("--repo", "-R")] = DEFAULT_REPO,
) -> None:
    """Strike (soft-delete) an entry in a section by wrapping it in a collapsed details block."""
    result = _backlog_operations.strike_entry(
        selector=selector, section=section_name, entry_id=entry_id, reason=reason or ""
    )
    if "error" in result:
        typer.echo(f"ERROR: {result['error']}", err=True)
        raise typer.Exit(1)
    messages = result.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            typer.echo(msg)


if __name__ == "__main__":
    app()
