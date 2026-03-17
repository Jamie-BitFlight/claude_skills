"""High-level CRUD operations for backlog items.

Combines parsing, GitHub, and file I/O into public functions that return
dicts. Each public function accepts an optional ``output: Output | None``
parameter and returns ``{...result, **out.to_dict()}``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from github import GithubException, GithubObject

from .entry_blocks import (
    ENTRY_RE,
    generate_diff,
    parse_entries,
    rewrite_section as rewrite_section_entries,
    strike_entry as strike_entry_block,
)
from .github import (
    apply_status_in_progress,
    batch_fetch_statuses,
    check_open_prs_for_issue,
    close_github_issue,
    create_issue_for_item,
    create_task_issue,
    fetch_github_issue_body,
    fetch_open_issues_by_title,
    get_github,
    get_task_issues,
    issue_to_local_fields,
    resolve_github_issue,
    sync_groomed_to_github_issue,
    try_get_github,
    update_task_status,
    view_enrich_from_github,
)
from .models import (
    BACKLOG_DIR,
    COMMIT_PREFIX_RE as _COMMIT_PREFIX_RE,
    DEFAULT_REPO,
    MIN_FRONTMATTER_PARTS,
    VALID_CLOSE_REASONS,
    BacklogError,
    BacklogItem,
    DuplicateItemError,
    Entry,
    GitHubUnavailableError,  # noqa: F401 — re-exported; raised by get_github() callers
    IssueStatus,
    ItemNotFoundError,
    Output,
    SamTask,
    SamTasksResult,
    ValidationError,
    ViewItemResult,
)
from .parsing import (
    append_or_replace_section,
    build_backlog_frontmatter,
    build_body_extra_only,
    build_issue_body_from_file,
    dump_frontmatter,
    extract_description_from_issue_body,
    extract_groomed_section,
    extract_normalize_metadata,
    extract_sections,
    find_fuzzy_duplicates,
    find_item,
    items_needing_issues,
    items_with_issues,
    loads_frontmatter,
    merge_sections,
    normalize_issue_title,
    now_iso,
    parse_backlog,
    parse_body_extra_fields,
    parse_issue_selector,
    parse_sam_task_metadata,
    reconstruct_body_from_sections,
    title_to_slug,
    today,
    view_result_from_local_item,
)

if TYPE_CHECKING:
    from github.Issue import SubIssue
    from github.Repository import Repository


# ---------------------------------------------------------------------------
# File metadata
# ---------------------------------------------------------------------------


def update_item_metadata(
    filepath: Path, updates: dict[str, str | dict[str, str]], set_synced: bool = False, output: Output | None = None
) -> dict[str, str | bool | list[str]]:
    """Update per-item file frontmatter. Supports nested metadata.plan, metadata.issue, etc.

    When set_synced=True, also sets metadata.last_synced to current UTC time.

    Returns:
        Dict with filepath and updated flag plus output messages.
    """
    out = output or Output()
    post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
    meta = post.metadata or {}
    for key, value in updates.items():
        if key == "metadata" and isinstance(value, dict):
            raw_nested = meta.get("metadata")
            nested_dict: dict[str, str] = (
                {str(k): str(v) for k, v in raw_nested.items()} if isinstance(raw_nested, dict) else {}
            )
            nested_dict.update(value)
            if set_synced:
                nested_dict["last_synced"] = now_iso()
            meta["metadata"] = nested_dict
        else:
            meta[key] = value
    if set_synced and "metadata" not in updates:
        raw_nested = meta.get("metadata")
        nested_dict2: dict[str, str] = (
            {str(k): str(v) for k, v in raw_nested.items()} if isinstance(raw_nested, dict) else {}
        )
        nested_dict2["last_synced"] = now_iso()
        meta["metadata"] = nested_dict2
    post.metadata = meta
    filepath.write_text(dump_frontmatter(post), encoding="utf-8")
    return {"filepath": str(filepath), "updated": True, **out.to_dict()}


# ---------------------------------------------------------------------------
# Internal helpers (not exported)
# ---------------------------------------------------------------------------


_CHANGES_KEY_MAP: dict[str, str] = {
    "renamed_to": "title",
    "description_updated": "description",
    "plan": "plan",
    "status": "status",
    "issue_num": "issue_num",
}


def _extract_changes(result: dict[str, object]) -> dict[str, str | int | bool]:
    """Build a changes summary from update_item result keys.

    Returns:
        Dict mapping changed field names to their new values.
    """
    changes: dict[str, str | int | bool] = {}
    for key, target in _CHANGES_KEY_MAP.items():
        if key not in result:
            continue
        val = result[key]
        if target == "issue_num":
            changes[target] = int(str(val))
        elif target == "description":
            changes[target] = True
        else:
            changes[target] = str(val)
    return changes


def _create_issue_and_update_item(item: BacklogItem, repo: str, output: Output | None = None) -> int | None:
    """Create GitHub issue for item and update per-item file metadata.

    Returns:
        Issue number if created, None otherwise.
    """
    out = output or Output()
    try:
        repository = get_github(repo)
        issue_num = create_issue_for_item(repository, item, dry_run=False, output=out)
    except (GithubException, BacklogError) as e:
        out.warn(f"  WARNING: Issue creation failed: {e}")
        return None
    else:
        if not issue_num:
            return None
        filepath_str = item.file_path
        if filepath_str:
            update_item_metadata(Path(filepath_str), {"metadata": {"issue": f"#{issue_num}"}}, output=out)
        return issue_num


def _rename_item_title(item: BacklogItem, title: str, repo: str = DEFAULT_REPO, output: Output | None = None) -> bool:
    """Update the name field in the per-item file. Syncs to GitHub issue title if linked.

    Returns:
        True if updated, False if no file path on item.
    """
    out = output or Output()
    filepath_str = item.file_path
    if not filepath_str:
        return False
    update_item_metadata(Path(filepath_str), {"name": title}, output=out)

    issue_ref = item.issue
    if issue_ref:
        repository = try_get_github(repo)
        if repository is not None:
            try:
                num = int(issue_ref.lstrip("#"))
                gh_issue = repository.get_issue(num)
                gh_issue.edit(title=title)
                out.info(f"  GitHub issue {issue_ref} title updated to: {title}")
            except GithubException as e:
                out.warn(f"  WARNING: Could not update issue {issue_ref} title: {e}")

    return True


def _update_item_description(item: BacklogItem, description: str, output: Output | None = None) -> bool:
    """Update the description field in the per-item file. Local-only, no GitHub sync.

    Returns:
        True if updated, False if no file path on item.
    """
    out = output or Output()
    filepath_str = item.file_path
    if not filepath_str:
        return False
    update_item_metadata(Path(filepath_str), {"description": description}, output=out)
    return True


def _apply_plan_to_item(item: BacklogItem, plan: str, repo: str = DEFAULT_REPO, output: Output | None = None) -> bool:
    """Apply plan update: write to GitHub Issue first (comment), then update local cache.

    GH-first: posts a plan comment on the linked GitHub Issue before updating local.
    If GH is unavailable, local update still succeeds.

    Returns:
        True if updated, False otherwise.
    """
    out = output or Output()
    filepath_str = item.file_path
    if not filepath_str:
        return False
    update_item_metadata(Path(filepath_str), {"metadata": {"plan": plan}}, output=out)

    # GH-first: post plan reference as a comment on the linked issue
    issue_ref = item.issue
    if issue_ref:
        repository = try_get_github(repo)
        if repository is not None:
            try:
                num = int(issue_ref.lstrip("#"))
                gh_issue = repository.get_issue(num)
                gh_issue.create_comment(f"**Plan**: {plan}")
                out.info(f"  Plan comment posted to issue {issue_ref}")
            except GithubException as e:
                out.warn(f"  WARNING: Could not post plan to issue {issue_ref}: {e}")

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


def _extract_subsection_body(body: str, section_name: str) -> str:
    """Extract the content of a ### subsection under ## Groomed.

    Returns:
        Subsection body text, or empty string if not found.
    """
    groomed_re = re.compile(r"## Groomed\s*\([^)]*\)\s*\n([\s\S]*?)(?=\n## |\Z)", re.MULTILINE)
    groomed_match = groomed_re.search(body)
    if not groomed_match:
        return ""
    groomed_body = groomed_match.group(1)
    sub_re = re.compile(
        rf"### {re.escape(section_name.strip())}[^\n]*\n([\s\S]*?)(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
    )
    sub_match = sub_re.search(groomed_body)
    if not sub_match:
        return ""
    return sub_match.group(1).strip()


def _write_groomed_to_item_file(
    filepath: Path,
    groomed_content: str,
    section_name: str | None = None,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    added_date: str = "0000-00-00",
) -> None:
    """Merge groomed content into per-item file.

    Updates frontmatter groomed date and body.
    If section_name is set, wrap content in an entry block via rewrite_section
    and append/replace that section only (incremental).
    Else replace full ## Groomed.
    """
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValidationError("Item file has no frontmatter")
    parts = text.split("---", 2)
    if len(parts) < MIN_FRONTMATTER_PARTS:
        raise ValidationError("Malformed item file")
    fm_text, body = parts[1].strip(), parts[2].strip()
    today_str = today()
    if section_name:
        existing_section_body = _extract_subsection_body(body, section_name)
        rewritten = rewrite_section_entries(
            existing_body=existing_section_body,
            new_content=groomed_content,
            entry_id=entry_id,
            replace=replace_section,
            reason=reason,
            added_date=added_date,
        )
        new_body = append_or_replace_section(body, section_name, rewritten)
    else:
        groomed_section = f"## Groomed ({today_str})\n\n{groomed_content.strip()}"
        groomed_re = re.compile(r"\n## Groomed\s*\([^)]*\)\s*\n[\s\S]*?(?=\n## |\Z)", re.MULTILINE)
        if groomed_re.search(body):
            new_body = groomed_re.sub(lambda _: f"\n{groomed_section}\n", body)
        else:
            new_body = body.rstrip() + "\n\n" + groomed_section + "\n"
    try:
        post = loads_frontmatter(text)
        meta_block = post.metadata.get("metadata")
        if isinstance(meta_block, dict):
            updated = dict(meta_block)
            updated["groomed"] = today_str
            post.metadata["metadata"] = updated
        else:
            post.metadata["groomed"] = today_str
        post.content = new_body
        new_content = dump_frontmatter(post)
    except (ValueError, KeyError, TypeError):
        new_content = "---\n" + fm_text + "\n---\n\n" + new_body
        if "groomed:" not in fm_text:
            new_content = new_content.replace("---\n", f'---\ngroomed: "{today_str}"\n', 1)
    filepath.write_text(new_content, encoding="utf-8")


def _ensure_github_issue(item: BacklogItem, filepath: Path, repo: str, output: Output | None = None) -> str | None:
    """Create GitHub issue if item doesn't have one.

    Uses try_get_github for graceful fallback when GitHub is unavailable.

    Returns:
        Issue ref like '#42', or None if no issue was created.
    """
    out = output or Output()
    repository = try_get_github(repo)
    if not repository:
        out.info("  INFO: GitHub unavailable — working locally only")
        return None
    try:
        issue_num = create_issue_for_item(repository, item, dry_run=False, output=out)
    except GithubException as e:
        out.warn(f"  WARNING: Could not create issue: {e}")
        return None
    else:
        if not issue_num:
            return None
        update_item_metadata(filepath, {"metadata": {"issue": f"#{issue_num}"}}, set_synced=True, output=out)
        out.info(f"  Created GitHub issue #{issue_num}")
        return f"#{issue_num}"


def _write_groomed_to_github(
    issue_ref: str, content: str, section_name: str | None, repo: str, output: Output | None = None
) -> bool:
    """Write groomed content to GitHub issue.

    Gracefully falls back to local-only when GitHub is unavailable.

    Returns:
        True if content was synced to GitHub, False otherwise.
    """
    out = output or Output()
    repository = try_get_github(repo)
    if not repository:
        out.info(f"  INFO: GitHub unavailable — {issue_ref} will sync on next `backlog pull` or `backlog sync`")
        return False
    try:
        num = int(issue_ref.lstrip("#"))
        updated = sync_groomed_to_github_issue(repository, num, content, section_name, output=out)
    except GithubException as e:
        out.warn(f"  WARNING: Could not sync to GitHub: {e}")
        return False
    else:
        if updated:
            out.info(f"  Synced to GitHub issue {issue_ref}")
            try:
                issue = repository.get_issue(num)
                if any(label.name == "status:needs-grooming" for label in issue.labels):
                    issue.remove_from_labels("status:needs-grooming")
            except GithubException as e:
                out.warn(f"  WARNING: Could not update grooming label: {e}")
        else:
            out.info(f"  No changes to sync to GitHub issue {issue_ref}")
        return updated


def _handle_update_groomed(
    item: BacklogItem,
    groomed_content_val: str,
    section_name: str | None,
    repo: str,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
) -> None:
    """Handle groomed content update: GitHub-first, then cache locally.

    Write order: (1) GitHub issue (canonical), (2) local file (cache).
    If item has no existing issue, skips GitHub sync and writes locally only.
    Sets last_synced after successful GitHub write.
    """
    out = output or Output()
    filepath = Path(item.file_path)
    issue_ref = item.issue

    added_date = item.added if hasattr(item, "added") and item.added else "0000-00-00"

    # Step 1: Write to GitHub FIRST (canonical source of truth), but only if
    # the item already has an issue. Groom must not create a new issue as a
    # side-effect — callers that want issue creation use backlog_add or
    # backlog_sync with create_issue=True.
    github_synced = False
    if issue_ref:
        github_synced = _write_groomed_to_github(issue_ref, groomed_content_val, section_name, repo, output=out)

    # Step 2: Write to local file (cache) with entry block wrapping
    _write_groomed_to_item_file(
        filepath,
        groomed_content_val,
        section_name,
        output=out,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
        added_date=added_date,
    )
    out.info(f"Updated {filepath.name} with groomed content")

    # Step 3: Set last_synced if GitHub write succeeded
    if github_synced:
        update_item_metadata(filepath, {"metadata": {"last_synced": now_iso()}}, output=out)


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


def _close_cleanup(item: BacklogItem, issue_ref: str, repo: str, output: Output | None = None) -> None:
    """Remove local per-item file after close (canonical state lives in GitHub)."""
    out = output or Output()
    filepath_str = item.file_path
    if not filepath_str:
        return
    filepath = Path(filepath_str)
    try:
        filepath.unlink()
        out.info(f"  Removed local file {filepath.name} (canonical: GH #{issue_ref.lstrip('#')})")
    except FileNotFoundError:
        pass


def _pull_if_issue_selector(selector: str, repo: str, output: Output | None = None) -> None:
    """Fetch a GitHub issue into the local cache when selector resolves to an issue number.

    Calls pull_single_issue when parse_issue_selector returns a number. No-op otherwise.

    Args:
        selector: Backlog selector string (title, #N, bare number, or URL).
        repo: GitHub repo in owner/repo format.
        output: Optional Output collector.
    """
    issue_num = parse_issue_selector(selector)
    if issue_num:
        pull_single_issue(get_github(repo), int(issue_num), output=output)


def _build_normalized_content(filepath: Path, output: Output | None = None) -> str | None:
    """Build normalized content for one file.

    Returns:
        Normalized content string or None if skip.
    """
    out = output or Output()
    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as e:
        out.warn(f"  Skip {filepath.name}: {e}")
        return None
    if not text.startswith("---"):
        return None
    try:
        post = loads_frontmatter(text)
        fm: dict[str, object] = (
            {k: (v if isinstance(v, dict) else str(v)) for k, v in post.metadata.items()} if post.metadata else {}
        )
        body: str = post.content or ""
    except (ValueError, KeyError, TypeError):
        return None
    meta_raw = fm.get("metadata")
    meta: dict[str, str] = {str(k): str(v) for k, v in meta_raw.items()} if isinstance(meta_raw, dict) else {}
    md = extract_normalize_metadata(fm, meta)
    if not md["name"]:
        return None
    parsed = parse_body_extra_fields(body)
    if parsed[0] and not md["description"]:
        md["description"] = parsed[0]
    groomed = extract_groomed_section(body)
    new_body = build_body_extra_only(parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], groomed)
    fm_str = build_backlog_frontmatter(
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
    result = fm_str.rstrip()
    return result + ("\n" if not result.endswith("\n\n") else "") + new_body


def _normalize_item_file(filepath: Path, dry_run: bool, output: Output | None = None) -> bool:
    """Normalize one backlog item file.

    Returns:
        True if updated, False if skipped.
    """
    content = _build_normalized_content(filepath, output=output)
    if content is None:
        return False
    if not dry_run:
        filepath.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Pull helpers
# ---------------------------------------------------------------------------


def _pull_item_create_new(
    item: BacklogItem,
    issue_num: int,
    issue_ref: str,
    title: str,
    github_body: str,
    dry_run: bool,
    output: Output | None = None,
) -> bool:
    """Create a new local file from a GitHub issue body.

    Returns:
        True if created (or would create in dry-run).
    """
    out = output or Output()
    slug = title_to_slug(title)
    priority = item.priority or "P2"
    filename = f"{priority.lower()}-{slug}.md"
    filepath = BACKLOG_DIR / filename
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    if dry_run:
        out.info(f"  [dry-run] Would create {filename} from #{issue_num}: {title}")
        return True
    fm_str = build_backlog_frontmatter(
        title,
        item.description,
        item.source,
        item.added or today(),
        priority,
        item.item_type,
        "open",
        issue_ref,
        item.plan,
        "",
    )
    filepath.write_text(fm_str.rstrip() + "\n\n" + github_body, encoding="utf-8")
    out.info(f"  Created #{issue_num} -> {filename}: {title}")
    return True


def _pick_entry(local_e: Entry, remote_e: Entry) -> tuple[str, bool]:
    """Pick the winning entry when both sides have the same ID.

    Returns:
        Tuple of (raw_entry_text, was_modified).
    """
    if local_e.raw == remote_e.raw:
        return local_e.raw, False
    if local_e.struck and not remote_e.struck:
        return local_e.raw, True
    if remote_e.struck and not local_e.struck:
        return remote_e.raw, True
    if local_e.struck and remote_e.struck:
        local_ts = local_e.struck_at or ""
        remote_ts = remote_e.struck_at or ""
        winner = remote_e if remote_ts > local_ts else local_e
        return winner.raw, remote_ts != local_ts
    # Both active: keep longer content
    winner = remote_e if len(remote_e.content) > len(local_e.content) else local_e
    return winner.raw, remote_e.content != local_e.content


def _merge_entry_bodies(local_content: str, remote_content: str) -> tuple[str, bool]:
    """Merge two section bodies using entry-aware rules.

    Merge rules:
    - Entry only on one side: keep it.
    - Both sides, one struck: keep struck version.
    - Both sides, both active: keep longer content.
    - Both sides, both struck: keep later struck timestamp.

    Returns:
        Tuple of (merged_content, was_modified).
    """
    local_entries = {e.id: e for e in parse_entries(local_content, show="all")}
    remote_entries = {e.id: e for e in parse_entries(remote_content, show="all")}

    all_ids = sorted(set(local_entries) | set(remote_entries))
    result_parts: list[str] = []
    modified = False

    for eid in all_ids:
        local_e = local_entries.get(eid)
        remote_e = remote_entries.get(eid)

        if local_e and remote_e:
            raw, changed = _pick_entry(local_e, remote_e)
            result_parts.append(raw)
            modified = modified or changed
        elif local_e:
            result_parts.append(local_e.raw)
        elif remote_e:
            result_parts.append(remote_e.raw)
            modified = True

    return "\n\n".join(result_parts), modified


def _pull_item_update_existing(
    item: BacklogItem,
    issue_num: int,
    title: str,
    filepath: Path,
    github_body: str,
    dry_run: bool,
    force: bool,
    diff_mode: bool = False,
    output: Output | None = None,
) -> tuple[bool, str]:
    """Update an existing local file with content from a GitHub issue body.

    Returns:
        Tuple of (was_updated, diff_string). diff_string is non-empty only when
        diff_mode is True and dry_run is True.
    """
    out = output or Output()
    local_body = item.raw_body

    if force:
        if dry_run:
            out.info(f"  [dry-run] Would overwrite {filepath.name} from #{issue_num}: {title}")
            diff_str = generate_diff(local_body, github_body) if diff_mode else ""
            return True, diff_str
        post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
        post.content = github_body
        filepath.write_text(dump_frontmatter(post), encoding="utf-8")
        out.info(f"  Pulled #{issue_num} -> {filepath.name}: {title}")
        return True, ""

    _merged_body, modified = merge_sections(local_body, github_body)
    if not modified:
        return False, ""

    diff_str = ""
    if dry_run:
        out.info(f"  [dry-run] Would merge #{issue_num} -> {filepath.name}: {title}")
        if diff_mode:
            diff_str = generate_diff(local_body, github_body)
        return True, diff_str

    # Apply entry-aware merge per section
    local_sections = extract_sections(local_body)
    github_sections = extract_sections(github_body)
    result_sections: dict[str, str] = dict(local_sections)
    entry_modified = False

    for heading, gh_content in github_sections.items():
        if heading in local_sections:
            merged_content, section_changed = _merge_entry_bodies(local_sections[heading], gh_content)
            if section_changed:
                result_sections[heading] = merged_content
                entry_modified = True
        else:
            result_sections[heading] = gh_content
            entry_modified = True

    if not entry_modified:
        return False, ""

    final_body = reconstruct_body_from_sections(local_sections, github_sections, result_sections)
    post = loads_frontmatter(filepath.read_text(encoding="utf-8"))
    post.content = final_body
    filepath.write_text(dump_frontmatter(post), encoding="utf-8")
    out.info(f"  Pulled #{issue_num} -> {filepath.name}: {title}")
    return True, ""


def _pull_item(
    item: BacklogItem,
    repo_obj: Repository,
    dry_run: bool,
    force: bool,
    diff_mode: bool = False,
    output: Output | None = None,
) -> tuple[bool, str]:
    """Pull GitHub issue body into local per-item file.

    Returns:
        Tuple of (was_pulled, diff_string). diff_string is non-empty only when
        diff_mode is True and dry_run is True.
    """
    out = output or Output()
    issue_ref = item.issue
    num_str = issue_ref.lstrip("#")
    if not num_str.isdigit():
        return False, ""

    issue_num = int(num_str)
    title = item.title
    filepath_str = item.file_path

    github_body = fetch_github_issue_body(repo_obj, issue_num, output=out)
    if github_body is None:
        return False, ""

    if not filepath_str or not Path(filepath_str).exists():
        created = _pull_item_create_new(item, issue_num, issue_ref, title, github_body, dry_run, output=out)
        return created, ""

    return _pull_item_update_existing(
        item, issue_num, title, Path(filepath_str), github_body, dry_run, force, diff_mode=diff_mode, output=out
    )


# ---------------------------------------------------------------------------
# Public API: ADD  (private helpers)
# ---------------------------------------------------------------------------


def _check_for_duplicates(title: str, force: bool) -> None:
    """Raise DuplicateItemError if a fuzzy duplicate exists and force is False.

    Args:
        title: Title of the new item.
        force: When True, skip the check entirely.

    Raises:
        DuplicateItemError: If one or more similar titles are found.
    """
    if force:
        return
    existing_items = parse_backlog()
    duplicates = find_fuzzy_duplicates(title, existing_items)
    if not duplicates:
        return
    raise DuplicateItemError(duplicates)


def _resolve_filepath(priority: str, slug: str) -> Path:
    """Return a collision-free Path inside BACKLOG_DIR for (priority, slug).

    Appends a numeric suffix when the base filename already exists.

    Args:
        priority: Item priority string (e.g. "high").
        slug: URL-safe slug derived from the item title.

    Returns:
        A Path that does not yet exist on disk.
    """
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{priority.lower()}-{slug}"
    filepath = BACKLOG_DIR / f"{base}.md"
    idx = 0
    while filepath.exists():
        idx += 1
        filepath = BACKLOG_DIR / f"{base}-{idx}.md"
    return filepath


def _try_create_github_issue(item_data: BacklogItem, repo: str, out: Output) -> int | None:
    """Attempt to create a GitHub issue for item_data; return issue number or None.

    Args:
        item_data: Populated BacklogItem (file_path may be empty at this stage).
        repo: Repository slug (owner/name).
        out: Output collector for warnings.

    Returns:
        Issue number on success, None when GitHub is unavailable or creation fails.
    """
    repository = try_get_github(repo)
    if repository is None:
        out.warn("  WARNING: GitHub unavailable — creating local-only item")
        return None
    try:
        return create_issue_for_item(repository, item_data, dry_run=False, output=out)
    except GithubException as e:
        out.warn(f"  WARNING: Issue creation failed: {e}")
        return None


def _build_item_body(research_first: str, files: str, suggested_location: str) -> str:
    """Build the markdown body appended below the frontmatter.

    Args:
        research_first: Optional research-first note.
        files: Optional file references.
        suggested_location: Optional suggested location note.

    Returns:
        Markdown string (empty when all inputs are empty).
    """
    parts: list[str] = []
    if research_first:
        parts.append(f"**Research first**: {research_first}")
    if files:
        parts.append(f"**Files**: {files}")
    if suggested_location:
        parts.append(f"**Suggested location**: {suggested_location}")
    return "\n".join(parts) + "\n" if parts else ""


def _write_local_item(filepath: Path, fm_str: str, body: str, issue_num: int | None, out: Output) -> None:
    """Write the frontmatter + body to disk and mark synced when an issue exists.

    Args:
        filepath: Destination path (must not already exist).
        fm_str: Rendered frontmatter block.
        body: Markdown body section.
        issue_num: GitHub issue number, or None for local-only items.
        out: Output collector forwarded to update_item_metadata.
    """
    filepath.write_text(fm_str.rstrip() + "\n\n" + body, encoding="utf-8")
    if issue_num:
        update_item_metadata(filepath, {}, set_synced=True, output=out)


# ---------------------------------------------------------------------------
# Public API: ADD
# ---------------------------------------------------------------------------


def add_item(
    title: str,
    description: str,
    priority: str,
    source: str = "Not specified",
    type_: str = "Feature",
    research_first: str = "",
    files: str = "",
    suggested_location: str = "",
    create_issue: bool = True,
    force: bool = False,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str]]:
    """Add item to backlog. Creates per-item file and optionally a GitHub issue.

    Returns:
        Dict with title, priority, filepath, and optionally issue_num.
    """
    out = output or Output()

    _check_for_duplicates(title, force)

    today_str = today()
    slug = title_to_slug(title)
    filepath = _resolve_filepath(priority, slug)

    # GH-first: try to create GitHub Issue BEFORE writing local file
    issue_num: int | None = None
    if create_issue:
        item_data = BacklogItem(
            title=title,
            description=description,
            source=source,
            added=today_str,
            priority=priority,
            item_type=type_,
            research_first=research_first,
            files=files,
            suggested_location=suggested_location,
        )
        issue_num = _try_create_github_issue(item_data, repo, out)

    # Build frontmatter with issue number already included (single write)
    issue_ref = f"#{issue_num}" if issue_num else ""
    fm_str = build_backlog_frontmatter(
        title, description, source, today_str, priority, type_, "open", issue_ref, "", ""
    )
    body = _build_item_body(research_first, files, suggested_location)
    _write_local_item(filepath, fm_str, body, issue_num, out)

    out.info(f"Backlog item created.\n  Title: {title}\n  Priority: {priority}\n  File: {filepath.name}")
    if issue_num:
        out.info(f"  Issue: #{issue_num}")
    out.info(f"Next steps: /groom-backlog-item {title}  /work-backlog-item {title}")

    result: dict[str, str | int | bool | list[str]] = {"title": title, "priority": priority, "file_path": str(filepath)}
    if issue_num:
        result["issue_num"] = issue_num
    return {**result, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: LIST
# ---------------------------------------------------------------------------


def refresh_local_cache_from_github(
    repo: str = DEFAULT_REPO, label: str | None = None, output: Output | None = None
) -> dict[str, int | list[str]]:
    """Fetch open GitHub Issues and update local cache files.

    Returns:
        Dict with count of refreshed issues.
    """
    out = output or Output()
    repo_obj = try_get_github(repo)
    if repo_obj is None:
        out.warn("  WARNING: GitHub unavailable — listing from local cache only")
        return {"refreshed": 0, **out.to_dict()}

    label_objs = []
    if label:
        try:
            label_objs.append(repo_obj.get_label(label))
        except GithubException:
            out.warn(f"  WARNING: label '{label}' not found — listing all issues")

    issues = repo_obj.get_issues(state="open", labels=label_objs or GithubObject.NotSet)
    count = 0
    for issue in issues:
        if issue.pull_request is not None:
            continue
        pull_single_issue(repo_obj, issue.number, output=out)
        count += 1
    out.info(f"  Refreshed {count} issue(s) from GitHub into local cache.")
    return {"refreshed": count, **out.to_dict()}


def _item_derived_status(item: BacklogItem, status_map: dict[int, IssueStatus]) -> str:
    """Return the GitHub status string for an item, defaulting to 'needs-grooming'."""
    num_str = item.issue.lstrip("#") if item.issue else ""
    if num_str.isdigit():
        info = status_map.get(int(num_str))
        return info.status if info is not None else "needs-grooming"
    return "needs-grooming"


def _filter_open_items(
    open_items: list[BacklogItem],
    section: str | None,
    title: str | None,
    status: str | None,
    status_map: dict[int, IssueStatus],
    type_: str | None = None,
    topic: str | None = None,
) -> list[BacklogItem]:
    """Apply section, title, status, type, and topic filters to open_items.

    type_ performs a case-insensitive exact match against metadata.type.
    Items missing metadata.type are excluded when type_ filter is active.

    topic performs a case-insensitive substring match against metadata.topic.
    Items missing metadata.topic are excluded when topic filter is active.

    Filters compose with AND logic.

    Returns:
        Filtered list of BacklogItem objects matching all supplied criteria.
    """
    if section:
        section_upper = section.upper()
        open_items = [it for it in open_items if it.section and it.section.upper() == section_upper]
    if title:
        title_lower = title.lower()
        open_items = [it for it in open_items if title_lower in it.title.lower()]
    if status:
        open_items = [it for it in open_items if _item_derived_status(it, status_map) == status]
    if type_:
        type_lower = type_.lower()
        open_items = [it for it in open_items if it.type_ and it.type_.lower() == type_lower]
    if topic:
        topic_lower = topic.lower()
        open_items = [it for it in open_items if it.topic and topic_lower in it.topic.lower()]
    return open_items


_TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "resolved", "closed"})


def _filter_closed_items(items: list[BacklogItem], include_closed: bool) -> list[BacklogItem]:
    """Filter out items whose local status is a terminal state.

    Terminal states are ``done``, ``resolved``, and ``closed``.

    Args:
        items: Parsed BacklogItem objects.
        include_closed: When ``True``, return all items unfiltered.

    Returns:
        Filtered list excluding terminal-status items, or the original list
        when ``include_closed`` is ``True``.
    """
    if include_closed:
        return items
    return [it for it in items if it.status not in _TERMINAL_STATUSES]


def _build_list_entry(
    item: BacklogItem, with_status: bool, status_map: dict[int, IssueStatus]
) -> dict[str, str | bool]:
    """Build the result dict for a single backlog item.

    Returns:
        Dict with section, title, issue, plan, type, topic, and optional
        file_path, groomed, status, and milestone fields.
    """
    entry: dict[str, str | bool] = {
        "section": item.section,
        "title": item.title,
        "issue": item.issue,
        "plan": item.plan,
        "type": item.type_,
        "topic": item.topic,
    }
    if item.file_path:
        entry["file_path"] = item.file_path
    if item.groomed:
        entry["groomed"] = True
    if with_status and item.issue:
        num_str = item.issue.lstrip("#")
        num = int(num_str) if num_str.isdigit() else 0
        info = status_map.get(num)
        entry["status"] = info.status if info is not None else ""
        entry["milestone"] = info.milestone if info is not None else ""
    return entry


def list_items(
    with_status: bool = False,
    from_github: bool = False,
    label: str | None = None,
    section: str | None = None,
    status: str | None = None,
    title: str | None = None,
    type_: str | None = None,
    topic: str | None = None,
    include_closed: bool = False,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, int | list[str] | list[dict[str, str | bool]]]:
    """List backlog items. Default reads local cache only. Use from_github=True to refresh first.

    Args:
        with_status: Include GitHub issue status for each item.
        from_github: Refresh local cache from GitHub Issues before listing.
        label: Filter by GitHub label (applied during refresh).
        section: Filter by priority section — P0, P1, P2, or Ideas (case-insensitive).
        status: Filter by status value e.g. 'needs-grooming', 'status:in-progress'.
        title: Filter items whose title contains this substring (case-insensitive).
        type_: Filter by metadata.type — case-insensitive exact match (e.g. 'Bug', 'Feature').
            Items missing metadata.type are excluded when this filter is active.
        topic: Filter by metadata.topic — case-insensitive substring match.
            Items missing metadata.topic are excluded when this filter is active.
        include_closed: When True, include items with terminal status (done, resolved, closed).
        repo: GitHub repo in owner/repo format.
        output: Optional Output collector.

    Returns:
        Dict with items list (each item a dict with section, title, issue, plan, type, topic,
        file_path, groomed, and optionally status/milestone).
    """
    out = output or Output()
    if from_github:
        refresh_local_cache_from_github(repo, label, output=out)
    items = parse_backlog()
    open_items = [it for it in items if not it.skip and it.section]
    open_items = _filter_closed_items(open_items, include_closed)
    status_map = batch_fetch_statuses(open_items, repo) if (with_status or status) else {}
    open_items = _filter_open_items(open_items, section, title, status, status_map, type_=type_, topic=topic)
    result_items = [_build_list_entry(it, with_status, status_map) for it in open_items]
    return {"items": result_items, "count": len(result_items), **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: VIEW — helpers
# ---------------------------------------------------------------------------


_ENTRY_FILTER_KEYWORDS: frozenset[str] = frozenset({"all", "struck", "last", "first"})


def _merge_section_entries(existing: dict[str, object], new_entries: list[dict[str, str | bool]]) -> dict[str, object]:
    """Merge *new_entries* into *existing* section metadata dict.

    Returns:
        Updated section metadata dict.
    """
    all_entries: list[dict[str, str | bool]] = list(existing["entries"]) + new_entries  # type: ignore[assignment]
    active_count = sum(1 for e in all_entries if not e.get("struck"))
    struck_count = sum(1 for e in all_entries if e.get("struck"))
    return {"num_entries": active_count, "num_struck": struck_count, "entries": all_entries}


def _build_sections_metadata(body: str, show: str | int | None, since: str | None) -> dict[str, dict]:
    """Extract ``### ``-delimited sections from *body* into a metadata dict.

    Args:
        body: Full issue/item body text.
        show: Controls both section and entry filtering.
              A string not in ``{"all", "struck", "last", "first"}`` filters to
              the named section (case-insensitive).  An int or one of those
              keywords is forwarded to ``parse_entries`` for entry-level filtering.
              ``None`` includes all sections with all entries.
        since: If set, filter entries to those on or after this date.

    Returns:
        Mapping of section name to entry metadata.
    """
    section_re = re.compile(r"^### (.+?)$", re.MULTILINE)
    section_headers = list(section_re.finditer(body))

    # Determine whether show is a section-name filter or an entry-level filter.
    section_name_filter: str | None = None
    entry_show: str | int | None = "all"
    if isinstance(show, str) and show not in _ENTRY_FILTER_KEYWORDS:
        section_name_filter = show
    elif show is not None:
        entry_show = show

    sections: dict[str, dict] = {}
    for i, hdr in enumerate(section_headers):
        sec_name = hdr.group(1).strip()
        start = hdr.end()
        end = section_headers[i + 1].start() if i + 1 < len(section_headers) else len(body)
        sec_body = body[start:end]
        if section_name_filter is not None and sec_name.lower() != section_name_filter.lower():
            continue
        entries = parse_entries(sec_body, show=entry_show, since=since)
        entry_dicts = [{"id": e.id, "struck": e.struck, "content": e.content} for e in entries]
        if sec_name in sections:
            sections[sec_name] = _merge_section_entries(sections[sec_name], entry_dicts)
        else:
            active_count = sum(1 for e in entries if not e.struck)
            struck_count = sum(1 for e in entries if e.struck)
            sections[sec_name] = {"num_entries": active_count, "num_struck": struck_count, "entries": entry_dicts}
    return sections


def _paginate_body(data: dict, body: str, offset: int, limit: int) -> None:
    """Apply offset/limit pagination to the ``body`` field of *data* in-place.

    Paginates by entry blocks when the body contains timestamped entry blocks
    (``<div><sub>…</sub>…</div>``). Falls back to line-based pagination for
    plain-text bodies that contain no entry blocks.

    Args:
        data: Mutable result dict whose ``body`` key will be replaced.
        body: Original (unpaginated) body text.
        offset: Number of leading entry blocks (or lines) to skip.
        limit: Maximum entry blocks (or lines) to keep (0 = unlimited).
    """
    has_entry_blocks = bool(ENTRY_RE.search(body))
    if has_entry_blocks:
        # Entry-block aware pagination
        entries = parse_entries(body, show="all")
        total = len(entries)
        sliced = entries[offset:] if offset > 0 else entries
        if limit > 0:
            sliced = sliced[:limit]
        data["body"] = "\n\n".join(e.raw for e in sliced)
        remaining = total - offset - len(sliced)
        if remaining > 0:
            data["body_truncated"] = True
            data["body_remaining_entries"] = remaining
            data["body_total_entries"] = total
    else:
        # Fallback: line-based pagination for plain-text bodies with no entry blocks
        lines = body.splitlines()
        total = len(lines)
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]
        data["body"] = "\n".join(lines)
        remaining = total - offset - len(lines)
        if remaining > 0:
            data["body_truncated"] = True
            data["body_remaining_lines"] = remaining
            data["body_total_lines"] = total


# ---------------------------------------------------------------------------
# Public API: VIEW
# ---------------------------------------------------------------------------


def view_item(
    selector: str,
    repo: str = DEFAULT_REPO,
    offset: int = 0,
    limit: int = 0,
    show: str | int | None = None,
    since: str | None = None,
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str] | dict | None]:
    """View a backlog item or GitHub issue by URL, #N, bare number, or title.

    Args:
        selector: Issue URL, #N, bare number, or title substring.
        repo: GitHub repo in owner/repo format.
        offset: Skip N entry blocks from the start of the body (falls back to
            line-based skipping for plain-text bodies with no entry blocks).
        limit: Show at most N entry blocks (0 = all, no truncation); falls back
            to line-based limit for plain-text bodies with no entry blocks.
        show: Entry filter forwarded to parse_entries — "all", "last", "first",
              "struck", positive int (first N active), negative int (last N active),
              or a section name string (case-insensitive section filter).
              MCP clients may send numeric values as strings; those are converted
              to int automatically.
        since: If set, filter entries to those on or after this date.
        output: Optional Output collector.

    Returns:
        Dict with item/issue details, including a ``sections`` key when the
        item body contains ``### ``-delimited section blocks.
    """
    out = output or Output()
    item = find_item(parse_backlog(), selector)
    issue_num = parse_issue_selector(selector)

    result: ViewItemResult = view_result_from_local_item(item) if item else ViewItemResult()

    if issue_num:
        if not view_enrich_from_github(result, issue_num, repo) and not item:
            raise ItemNotFoundError(selector)
    elif not item:
        raise ItemNotFoundError(selector)

    # MCP clients send numeric show values as strings; convert before forwarding.
    parsed_show: str | int | None = show
    if isinstance(show, str):
        try:
            parsed_show = int(show)
        except ValueError:
            parsed_show = show

    data = result.model_dump()

    body = data.get("body", "")
    if body:
        data["sections"] = _build_sections_metadata(body, parsed_show, since)

    if body and (offset > 0 or limit > 0):
        _paginate_body(data, body, offset, limit)

    return {**data, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: SYNC
# ---------------------------------------------------------------------------


def find_or_create_issue(
    item: BacklogItem,
    existing_issues: dict[str, int],
    repository: Repository,
    dry_run: bool,
    output: Output | None = None,
) -> int | None:
    """Check for existing issue by title; create only if no match found.

    Returns:
        Issue number (existing or newly created), or None for dry-run creates.
    """
    out = output or Output()
    title = item.title
    normalized = normalize_issue_title(title)
    if normalized in existing_issues:
        existing_num = existing_issues[normalized]
        out.info(f"  Linked #{existing_num}: {title[:60]} (existing issue found)")
        return existing_num
    if dry_run:
        out.info(f"  [dry-run] Would create: {title[:60]}")
        return None
    return create_issue_for_item(repository, item, dry_run=False, output=out)


def sync_create_missing_issues(
    items: list[BacklogItem], repo: str, dry_run: bool, output: Output | None = None
) -> dict[str, int | bool | list[str]]:
    """Pass 1 of sync: create GitHub issues for all items that lack them.

    Before creating any issues, fetches all open issues from GitHub and checks
    for title matches. If an existing open issue matches (after stripping
    conventional-commit prefixes), links to it instead of creating a duplicate.

    Returns:
        Dict with count of created/linked issues.
    """
    out = output or Output()
    needed = items_needing_issues(items)
    if not needed:
        out.info("No items need GitHub issues created.")
        return {"created": 0, **out.to_dict()}
    out.info(f"Found {len(needed)} item(s) without GitHub issues:")
    for it in needed:
        out.info(f"  - {it.title[:60]}")
    repository = get_github(repo)

    # Dedup: fetch existing open issues to prevent duplicate creation.
    out.info("Fetching open issues for deduplication check...")
    existing_issues = fetch_open_issues_by_title(repository)
    out.info(f"  Found {len(existing_issues)} existing open issues.")

    created = 0
    for item in needed:
        issue_num = find_or_create_issue(item, existing_issues, repository, dry_run, output=out)
        if not issue_num or dry_run:
            continue
        created += 1
        # Track newly created/linked issues to prevent intra-batch duplicates.
        new_normalized = normalize_issue_title(item.title)
        if new_normalized not in existing_issues:
            existing_issues[new_normalized] = issue_num
        # Update per-item file metadata with issue number
        filepath_str = item.file_path
        if filepath_str:
            update_item_metadata(Path(filepath_str), {"metadata": {"issue": f"#{issue_num}"}}, output=out)

    return {"created": created, **out.to_dict()}


def sync_push_groomed_content(
    items: list[BacklogItem], repo: str, dry_run: bool, output: Output | None = None
) -> dict[str, int | bool | list[str]]:
    """Pass 2 of sync: push groomed content to existing GitHub issues.

    Skips items with no '## Groomed' section in their body.

    Returns:
        Dict with count of pushed items.
    """
    out = output or Output()
    groomed_items = [it for it in items_with_issues(items) if "## Groomed" in (it.raw_body or "")]
    if not groomed_items:
        out.info("No items with groomed content to push.")
        return {"pushed": 0, **out.to_dict()}
    out.info(f"Found {len(groomed_items)} item(s) with groomed content to push to GitHub:")
    if dry_run:
        for it in groomed_items:
            issue_ref = it.issue
            out.info(f"  [dry-run] Would update issue {issue_ref}: {it.title[:60]}")
        return {"pushed": 0, "dry_run": True, **out.to_dict()}
    repository = get_github(repo)

    pushed = 0
    for item in groomed_items:
        issue_ref = item.issue
        num_str = issue_ref.lstrip("#")
        if not num_str.isdigit():
            out.warn(f"  WARNING: Skipping item with invalid issue ref '{issue_ref}'")
            continue
        body = build_issue_body_from_file(item)
        if body is None:
            continue
        try:
            gh_issue = repository.get_issue(int(num_str))
            gh_issue.edit(body=body)
            out.info(f"  Updated issue #{num_str}: {item.title[:60]}")
            pushed += 1
        except GithubException as e:
            out.warn(f"  WARNING: Could not update issue #{num_str}: {e}")

    return {"pushed": pushed, **out.to_dict()}


def sync_items(
    repo: str = DEFAULT_REPO, dry_run: bool = False, output: Output | None = None
) -> dict[str, int | bool | list[str]]:
    """Create GitHub issues for all items missing them, and push groomed content to existing issues.

    Returns:
        Dict with sync results.
    """
    out = output or Output()
    items = parse_backlog()
    create_result = sync_create_missing_issues(items, repo, dry_run, output=out)
    push_result = sync_push_groomed_content(items, repo, dry_run, output=out)
    return {
        "created": create_result.get("created", 0),
        "pushed": push_result.get("pushed", 0),
        "dry_run": dry_run,
        **out.to_dict(),
    }


# ---------------------------------------------------------------------------
# Public API: CLOSE
# ---------------------------------------------------------------------------


def close_item(
    selector: str,
    reason: str,
    reference: str = "",
    comment: str = "",
    cleanup: bool = False,
    force: bool = False,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | bool | list[str]]:
    """Dismiss an item without completion. Requires a categorized reason.

    Use for duplicates, out-of-scope items, superseded items, wontfix, or
    permanently blocked items. For completed work, use resolve_item() instead.

    Returns:
        Dict with closed item title and reason.
    """
    out = output or Output()
    reason = reason.strip().lower()
    if reason not in VALID_CLOSE_REASONS:
        raise ValidationError(f"Invalid close reason: {reason!r}. Valid reasons: {', '.join(VALID_CLOSE_REASONS)}")
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = parse_backlog()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    issue_ref = item.issue
    if issue_ref and not force:
        issue_num_val = int(issue_ref.lstrip("#"))
        open_prs = check_open_prs_for_issue(issue_num_val, repo)
        if open_prs:
            out.warn(f"WARNING: Open PRs reference issue {issue_ref}:")
            for pr in open_prs:
                out.warn(f"  - PR #{pr.number}: {pr.title}")
                out.warn(f"    {pr.url}")
            out.warn(f"\nIssue {issue_ref} will auto-close when a PR merges with 'Fixes {issue_ref}'.")
            out.warn("Use force=True to close anyway.")
            raise BacklogError(f"Open PRs reference issue {issue_ref}. Use force=True to close anyway.")

    today()

    filepath_str = item.file_path
    if not filepath_str:
        raise BacklogError("Item has no file path")
    raw = item.raw_body
    already_closed = any(marker in raw for marker in ("**Status**: CLOSED", "**Status**: DONE", "**Completed**:"))
    if already_closed:
        out.info("Item already closed.")
        return {"title": item.title, "already_closed": True, **out.to_dict()}

    update_item_metadata(Path(filepath_str), {"metadata": {"status": "closed", "close_reason": reason}}, output=out)

    out.info(f'Backlog item "{item.title}" closed ({reason}).')
    if issue_ref:
        close_github_issue(issue_ref, reason, reference=reference, comment=comment, repo=repo, output=out)
    if cleanup and issue_ref:
        _close_cleanup(item, issue_ref, repo, output=out)

    return {"title": item.title, "closed": True, "reason": reason, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: RESOLVE
# ---------------------------------------------------------------------------


def resolve_item(
    selector: str,
    summary: str,
    plan: str = "",
    method: str = "",
    notes: str = "",
    follow_ups: str = "",
    findings: str = "",
    cleanup: bool = False,
    force: bool = False,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> dict[str, str | bool | list[str]]:
    """Mark item DONE (completed) and close GitHub issue with evidence trail.

    Use when the work IS done. Creates a structured completion record
    (summary, method, notes, follow-ups, findings) as an audit trail.
    For dismissals (duplicate, out of scope, etc.), use close_item() instead.

    Returns:
        Dict with resolved item title and summary.
    """
    out = output or Output()
    if not summary.strip():
        raise ValidationError("summary is required (what was done)")
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = parse_backlog()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    issue_ref = item.issue
    if issue_ref and not force:
        issue_num_val = int(issue_ref.lstrip("#"))
        open_prs = check_open_prs_for_issue(issue_num_val, repo)
        if open_prs:
            out.warn(f"WARNING: Open PRs reference issue {issue_ref}:")
            for pr in open_prs:
                out.warn(f"  - PR #{pr.number}: {pr.title}")
                out.warn(f"    {pr.url}")
            out.warn("\nResolving will close the issue and orphan these PRs.")
            out.warn("Use force=True to resolve anyway.")
            raise BacklogError(f"Open PRs reference issue {issue_ref}. Use force=True to resolve anyway.")

    today()

    filepath_str = item.file_path
    if not filepath_str:
        raise BacklogError("Item has no file path")
    raw = item.raw_body
    already_done = any(marker in raw for marker in ("**Status**: DONE", "**Completed**:", "**Resolved**:"))
    if already_done:
        out.info("Item already resolved.")
        return {"title": item.title, "already_resolved": True, **out.to_dict()}

    metadata: dict[str, str] = {"status": "done", "priority": "completed"}
    if plan:
        metadata["plan"] = plan
    update_item_metadata(Path(filepath_str), {"metadata": metadata}, output=out)

    out.info(f'Backlog item "{item.title}" resolved.')
    if issue_ref:
        resolve_github_issue(
            issue_ref,
            summary=summary,
            method=method,
            notes=notes,
            follow_ups=follow_ups,
            findings=findings,
            repo=repo,
            output=out,
        )
    if cleanup and issue_ref:
        _close_cleanup(item, issue_ref, repo, output=out)

    return {"title": item.title, "resolved": True, "summary": summary, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: UPDATE
# ---------------------------------------------------------------------------


def update_item(
    selector: str,
    plan: str | None = None,
    status: str | None = None,
    create_issue: bool = False,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    groomed: bool = False,
    title: str | None = None,
    description: str | None = None,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
) -> dict[str, str | int | bool | list[str]]:
    """Update item: add Plan, set status:in-progress, create issue, or write groomed content.

    Returns:
        Dict with update results.
    """
    out = output or Output()
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = parse_backlog()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)

    result: dict[str, str | int | bool | list[str]] = {"title": item.title}

    if title:
        _rename_item_title(item, title, repo, output=out)
        result["renamed_to"] = title

    if description is not None:
        _update_item_description(item, description, output=out)
        result["description_updated"] = True

    has_groomed = groomed or groomed_file or groomed_content or (section and content)
    if has_groomed:
        if not item.file_path:
            raise BacklogError("Item has no file path")
        groomed_content_val, section_name = _resolve_groomed_content(section, content, groomed_content, groomed_file)
        if not groomed_content_val.strip():
            raise ValidationError("No groomed content provided")
        _handle_update_groomed(
            item,
            groomed_content_val,
            section_name,
            repo,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
        )
        return {**result, "groomed_updated": True, **out.to_dict()}

    if plan:
        _apply_plan_to_item(item, plan, repo, output=out)
        out.info(f"  Plan: {plan}")
        result["plan"] = plan

    if create_issue and not item.issue and item.section in {"P0", "P1"}:
        issue_num = _create_issue_and_update_item(item, repo, output=out)
        if issue_num:
            out.info(f"  Issue: #{issue_num}")
            result["issue_num"] = issue_num

    if status == "in-progress" and item.issue:
        apply_status_in_progress(item, repo, output=out)
        result["status"] = "in-progress"

    result["changes"] = _extract_changes(result)  # type: ignore[assignment]

    return {**result, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: GROOM
# ---------------------------------------------------------------------------


def groom_item(
    selector: str,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
) -> dict[str, str | int | bool | list[str]]:
    """Write groomed content into per-item file. Delegates to update_item.

    Returns:
        Dict with groom results.
    """
    out = output or Output()
    has_input = groomed_file or groomed_content or (section and content)
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
    return update_item(
        selector=selector,
        plan=None,
        status=None,
        create_issue=False,
        groomed_file=groomed_file,
        groomed_content=groomed_content,
        section=section,
        content=content,
        groomed=not has_input,
        repo=repo,
        output=out,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Public API: STRIKE ENTRY
# ---------------------------------------------------------------------------


def _match_in_section(text: str, section: str, match: re.Match[str]) -> bool:
    """Return True if *match* falls within the ``### {section}`` subsection."""
    section_re = re.compile(
        rf"### {re.escape(section.strip())}[^\n]*\n([\s\S]*?)(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
    )
    section_match = section_re.search(text)
    if not section_match:
        return False
    return section_match.start(1) <= match.start() <= section_match.end(1)


def _apply_strike(text: str, entry_id: str, reason: str, section: str | None) -> str:
    """Find entry by *entry_id* in *text*, strike it, and return updated text.

    Returns:
        The updated text with the struck entry.

    Raises:
        ValueError: If entry_id is not found.
    """
    for match in ENTRY_RE.finditer(text):
        if match.group(1) != entry_id:
            continue
        if section and not _match_in_section(text, section, match):
            continue
        struck = strike_entry_block(match.group(0), reason)
        return text[: match.start()] + struck + text[match.end() :]
    raise ValueError(f"Entry '{entry_id}' not found")


def strike_entry(
    selector: str, entry_id: str, reason: str, section: str | None = None, output: Output | None = None
) -> dict[str, str | int | bool | list[str]]:
    """Strike (retract) an entry block within a backlog item.

    Finds the entry by ``entry_id`` across all sections (or within a specific
    section if provided), wraps it in a collapsed ``<details>`` with the
    reason, writes the file back, and syncs to GitHub if an issue exists.

    Args:
        selector: Item title, slug, or issue reference.
        entry_id: Timestamp ID of the entry to strike.
        reason: Human-readable reason for striking.
        section: Optional section name to scope the search.
        output: Optional Output collector.

    Returns:
        Dict with strike results.

    Raises:
        ItemNotFoundError: If item cannot be found.
        ValueError: If entry_id not found in the item body.
    """
    out = output or Output()
    items = parse_backlog()
    item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    if not item.file_path:
        raise BacklogError("Item has no file path")

    filepath = Path(item.file_path)
    text = filepath.read_text(encoding="utf-8")

    try:
        text = _apply_strike(text, entry_id, reason, section)
    except ValueError:
        msg = f"Entry '{entry_id}' not found in item '{item.title}'"
        if section:
            msg += f" section '{section}'"
        raise ValueError(msg) from None

    filepath.write_text(text, encoding="utf-8")
    out.info(f"Struck entry {entry_id} in {filepath.name}")

    # Sync to GitHub if item has an issue
    if item.issue:
        repository = try_get_github(DEFAULT_REPO)
        if repository:
            try:
                num = int(item.issue.lstrip("#"))
                body = build_issue_body_from_file(item)
                issue = repository.get_issue(num)
                if body is not None:
                    issue.edit(body=body)
                out.info(f"  Synced strike to GitHub issue {item.issue}")
            except GithubException as e:
                out.warn(f"  WARNING: Could not sync to GitHub: {e}")

    return {"title": item.title, "entry_id": entry_id, "struck": True, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: NORMALIZE
# ---------------------------------------------------------------------------


def normalize_items(dry_run: bool = False, output: Output | None = None) -> dict[str, int | bool | list[str]]:
    """Rewrite per-item files to research-style metadata, remove body duplication.

    Returns:
        Dict with count of normalized items.
    """
    out = output or Output()
    if not BACKLOG_DIR.exists():
        raise BacklogError(f"{BACKLOG_DIR} not found")
    pattern = re.compile(r"^(p0|p1|p2|ideas|completed)-[a-z0-9-]+\.md$", re.IGNORECASE)
    files = sorted(f for f in BACKLOG_DIR.glob("*.md") if pattern.match(f.name))
    if not files:
        out.info("No backlog item files found")
        return {"normalized": 0, **out.to_dict()}
    updated = sum(1 for f in files if _normalize_item_file(f, dry_run, output=out))
    out.info(f"Normalized {updated} item file(s)" + (" [dry-run]" if dry_run else ""))
    return {"normalized": updated, "dry_run": dry_run, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: PULL
# ---------------------------------------------------------------------------


def pull_single_issue(
    repo_obj: Repository,
    issue_num: int,
    filepath: Path | None = None,
    output: Output | None = None,
    diff_mode: bool = False,
) -> dict[str, Path | str | list[str] | None]:
    """Fetch a GitHub issue and write/update the local cache file.

    If filepath is None, derives it from the issue title and priority.

    Args:
        repo_obj: PyGitHub Repository object.
        issue_num: GitHub issue number to fetch.
        filepath: Local path to write. If None, derived from issue title and priority.
        output: Optional Output collector for messages and warnings.
        diff_mode: When True, computes a unified diff of old vs new body content and
            includes it in the return dict under the ``"diff"`` key.

    Returns:
        Dict with ``"file_path"`` (Path or None on failure) and, when diff_mode is True
        and the file already existed, ``"diff"`` (unified diff string, may be empty if
        content was unchanged).
    """
    out = output or Output()

    try:
        issue = repo_obj.get_issue(issue_num)
    except GithubException as e:
        out.warn(f"  WARNING: Could not fetch issue #{issue_num}: {e}")
        return {"file_path": None, **out.to_dict()}

    fields = issue_to_local_fields(issue)
    # Strip conventional-commit prefix from title (e.g., "feat: Title" -> "Title")
    raw_title = fields.title
    clean_title = _COMMIT_PREFIX_RE.sub("", raw_title).strip()

    if filepath is None:
        slug = title_to_slug(clean_title)
        filename = f"{fields.priority.lower()}-{slug}.md"
        filepath = BACKLOG_DIR / filename

    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)

    diff_str = ""
    if filepath.exists():
        # Capture old body before update when diff is requested
        if diff_mode:
            old_text = filepath.read_text(encoding="utf-8")
            parts = old_text.split("---", 2)
            old_body = parts[2].strip() if len(parts) >= MIN_FRONTMATTER_PARTS else old_text
        # Update existing file: overwrite description, body, metadata
        update_item_metadata(
            filepath,
            {
                "name": clean_title,
                "description": extract_description_from_issue_body(fields.body),
                "metadata": {
                    "issue": f"#{issue_num}",
                    "priority": fields.priority,
                    "type": fields.item_type,
                    "status": fields.status,
                    "last_synced": now_iso(),
                },
            },
            output=out,
        )
        # Overwrite body sections from GitHub issue body
        _overwrite_body_from_github(filepath, fields.body)
        if diff_mode:
            diff_str = generate_diff(old_body, fields.body)
    else:
        # Create new cache file from GitHub issue
        fm_str = build_backlog_frontmatter(
            name=clean_title,
            description=extract_description_from_issue_body(fields.body),
            source=f"GitHub Issue #{issue_num}",
            added=today(),
            priority=fields.priority,
            type_val=fields.item_type,
            status=fields.status,
            issue=f"#{issue_num}",
        )
        filepath.write_text(fm_str.rstrip() + "\n\n" + fields.body + "\n", encoding="utf-8")
        update_item_metadata(filepath, {"metadata": {"last_synced": now_iso()}}, output=out)

    result: dict[str, Path | str | list[str] | None] = {"file_path": filepath, **out.to_dict()}
    if diff_mode:
        result["diff"] = diff_str
    return result


def pull_by_selector(
    selector: str, repo: str = DEFAULT_REPO, output: Output | None = None, diff: bool = False
) -> dict[str, str | list[str] | None]:
    """Pull a single GitHub issue into the local cache by selector.

    Supports issue number selectors (#N, bare number, URL) and title substrings.
    For issue number selectors, fetches directly from GitHub.
    For title substrings, finds the local item, reads its issue number,
    then fetches from GitHub.

    Args:
        selector: Issue number, URL, or title substring.
        repo: GitHub repository slug (owner/name).
        output: Optional Output collector for messages and warnings.
        diff: When True, computes a unified diff of old vs new body content and
            includes it in the return dict under the ``"diff"`` key.

    Returns:
        Dict with 'file_path' (local path written), output messages/warnings, and
        optionally 'diff' (unified diff string) when diff=True.

    Raises:
        ItemNotFoundError: If selector matches no item in the local cache.
        BacklogError: If matched item has no linked GitHub issue.
    """
    out = output or Output()
    issue_num_str = parse_issue_selector(selector)
    if issue_num_str:
        result = pull_single_issue(get_github(repo), int(issue_num_str), output=out, diff_mode=diff)
        filepath = result.get("file_path")
        ret: dict[str, str | list[str] | None] = {"file_path": str(filepath) if filepath else None, **out.to_dict()}
        if diff and "diff" in result:
            ret["diff"] = str(result["diff"])
        return ret

    # Title substring: find item in local cache then pull by its issue number
    items = parse_backlog()
    item = find_item(items, selector)
    if item is None:
        raise ItemNotFoundError(selector)

    issue_ref = item.issue
    if not issue_ref:
        raise BacklogError(f"Item '{item.title}' has no linked GitHub issue. Use backlog_pull() for bulk pull.")

    issue_num_str = parse_issue_selector(issue_ref)
    if not issue_num_str:
        raise BacklogError(f"Could not parse issue number from '{issue_ref}'")

    result = pull_single_issue(get_github(repo), int(issue_num_str), output=out, diff_mode=diff)
    filepath = result.get("file_path")
    ret = {"file_path": str(filepath) if filepath else None, **out.to_dict()}
    if diff and "diff" in result:
        ret["diff"] = str(result["diff"])
    return ret


def pull_items(
    repo: str = DEFAULT_REPO,
    dry_run: bool = False,
    force: bool = False,
    diff: bool = False,
    output: Output | None = None,
) -> dict[str, int | bool | str | list[str]]:
    """Pull issue body content from GitHub into local per-item files.

    Also auto-migrates P0/P1 items that lack GitHub Issues by creating them.
    Merges by section — keeps longer version of each section.
    Skips items with no issue number (after migration).

    Returns:
        Dict with count of pulled items.
    """
    out = output or Output()
    items = parse_backlog()

    # Auto-migration: create missing GitHub Issues for P0/P1 items
    items_without_issues = [it for it in items if it.section in {"P0", "P1"} and not it.skip and not it.issue]
    if items_without_issues:
        out.info(f"Auto-migrating {len(items_without_issues)} P0/P1 item(s) to GitHub Issues...")
        sync_create_missing_issues(items, repo, dry_run, output=out)
        # Re-parse after migration to pick up updated issue numbers
        items = parse_backlog()

    candidates = [it for it in items if it.issue and not it.skip]

    if not candidates:
        out.info("No items with GitHub issue numbers found.")
        return {"pulled": 0, **out.to_dict()}

    out.info(f"Checking {len(candidates)} item(s) with GitHub issues...")
    repository = get_github(repo)
    pulled = 0
    diff_parts: list[str] = []
    for item in candidates:
        was_pulled, diff_str = _pull_item(item, repository, dry_run, force, diff_mode=diff, output=out)
        if was_pulled:
            pulled += 1
        if diff_str:
            diff_parts.append(diff_str)

    if pulled == 0:
        out.info("Nothing to pull — local files are up to date.")
    else:
        suffix = " [dry-run]" if dry_run else ""
        out.info(f"Pulled {pulled} item(s){suffix}.")

    result: dict[str, int | bool | str | list[str]] = {"pulled": pulled, "dry_run": dry_run, **out.to_dict()}
    if diff and diff_parts:
        result["diff"] = "\n".join(diff_parts)
    return result


# ---------------------------------------------------------------------------
# Public API: SAM TASK OPERATIONS
# ---------------------------------------------------------------------------


def _write_sam_task_cache(tasks: list[dict[str, object]], parent_issue_number: int) -> bool:
    """Write SAM task list to ``~/.claude/context/sam-tasks-{feature_slug}.json``.

    Returns:
        True when the cache file was written, False when no feature slug
        could be derived from the task list and the write was skipped.
    """
    feature_slug = _extract_feature_slug(tasks)
    if not feature_slug:
        return False
    cache_dir = Path.home() / ".claude" / "context"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"sam-tasks-{feature_slug}.json"
    payload = {
        "feature_slug": feature_slug,
        "parent_issue_number": parent_issue_number,
        "synced_at": now_iso(),
        "count": len(tasks),
        "tasks": tasks,
    }
    cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True


def _sub_issues_to_task_dicts(sub_issues: list[SubIssue]) -> list[dict[str, object]]:
    """Convert a list of PyGithub SubIssue objects to task dicts.

    Each dict contains ``issue_number``, ``issue_url``, ``title`` plus all
    ``SamTask`` fields parsed from the issue body's ``<!-- sam:task ... -->`` block.

    Returns:
        List of task dicts with GitHub issue fields and SAM metadata merged.

    Note:
        ``SubIssue`` extends ``Issue`` directly (``class SubIssue(Issue)`` in
        ``github/Issue.py``). The ``body`` property is inherited from ``Issue``
        and calls ``_completeIfNotSet(self._body)``, which lazy-fetches the full
        issue via the GitHub REST API if the attribute was not populated in the
        initial paginated response. Accessing ``si.body`` is therefore always
        reliable — the PyGitHub lazy-completion mechanism ensures the value is
        fetched on first access. A roundtrip via ``repo.get_issue(si.number).body``
        is unnecessary and would double the number of API calls.

        SOURCE: Verified against installed PyGitHub source at
        ``.venv/lib/python3.11/site-packages/github/Issue.py`` (lines 822-861,
        196-198) on 2026-03-07.
    """
    tasks: list[dict[str, object]] = []
    for si in sub_issues:
        body = si.body or ""
        task_meta = parse_sam_task_metadata(body)
        task_dict: dict[str, object] = {"issue_number": si.number, "issue_url": si.html_url, "title": si.title}
        if task_meta is not None:
            task_dict.update(task_meta.model_dump())
        tasks.append(task_dict)
    return tasks


def create_sam_task(
    parent_issue_number: int,
    task_id: str,
    feature: str,
    task_type: str,
    agent: str,
    priority: int,
    skills: list[str],
    dependencies: list[str],
    description: str,
    acceptance_criteria: list[str] | None = None,
    labels: list[str] | None = None,
    output: Output | None = None,
) -> dict[str, str | int | list[str]]:
    """Create a GitHub issue for a SAM task and link it as a sub-issue of a parent story.

    Constructs a ``SamTask`` from scalar parameters, creates the GitHub issue, and
    links it as a sub-issue of the parent. Wraps ``github.create_task_issue()``.

    Args:
        parent_issue_number: Issue number of the parent story (without ``#``).
        task_id: Feature-scoped sequential ID, e.g. ``"T1"``, ``"T2"``.
        feature: Feature slug, e.g. ``"uv-skill-update"``.
        task_type: Execution category: ``"research"`` | ``"implement"`` | ``"review"`` | ``"fix"`` | ``"docs"``.
        agent: Agent name to execute the task.
        priority: Execution priority 1-5 (1 = highest).
        skills: Skill names the executing agent should load.
        dependencies: Feature-scoped task IDs this task depends on (e.g. ``["T1", "T2"]``).
        description: Short human-readable description of the task.
        acceptance_criteria: Optional list of acceptance criteria strings.
        labels: Optional list of label names to apply.
        output: Optional Output collector.

    Returns:
        Dict with ``issue_number``, ``title``, ``url``, and output messages.
        Includes ``warnings`` from sub-issue linking when applicable.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    out = output or Output()
    task = SamTask(
        task_id=task_id,
        feature=feature,
        task_type=task_type,
        agent=agent,
        priority=priority,
        skills=skills,
        dependencies=dependencies,
    )
    repo = get_github()
    issue = create_task_issue(repo, parent_issue_number, task, description, acceptance_criteria, labels, output=out)
    if issue is None:
        return {"issue_number": 0, "title": "", "url": "", **out.to_dict()}
    return {"issue_number": issue.number, "title": issue.title, "url": issue.html_url, **out.to_dict()}


def get_sam_tasks(parent_issue_number: int, refresh_cache: bool = True, output: Output | None = None) -> SamTasksResult:
    """Fetch all SAM task sub-issues for a parent story issue.

    When GitHub is unavailable, falls back to the local cache file
    ``~/.claude/context/sam-tasks-{feature_slug}.json``.

    Args:
        parent_issue_number: Issue number of the parent story (without ``#``).
        refresh_cache: Write cache file after a successful GitHub fetch when ``True``.
        output: Optional Output collector.

    Returns:
        Dict with ``tasks`` (list of task dicts), ``count``, ``parent_issue_number``,
        and output messages.
    """
    out = output or Output()

    repo = try_get_github()
    if repo is None:
        # Offline fallback: scan cache directory for any matching cache file
        cache_dir = Path.home() / ".claude" / "context"
        cache_files = list(cache_dir.glob("sam-tasks-*.json")) if cache_dir.exists() else []
        # Try all cache files; find one that has the right parent_issue_number
        for cache_file in cache_files:
            try:
                cached: dict[str, object] = json.loads(cache_file.read_text(encoding="utf-8"))
                if cached.get("parent_issue_number") == parent_issue_number:
                    out.warn(f"  WARNING: GitHub unavailable — returning cached tasks from {cache_file.name}")
                    cached_tasks_raw = cached.get("tasks", [])
                    cached_tasks: list[dict[str, object]] = (
                        cached_tasks_raw if isinstance(cached_tasks_raw, list) else []
                    )  # type: ignore[assignment]
                    count_raw = cached.get("count", len(cached_tasks))
                    return {
                        "tasks": cached_tasks,
                        "count": int(count_raw) if isinstance(count_raw, int) else len(cached_tasks),
                        "parent_issue_number": parent_issue_number,
                        "messages": out.messages,
                        "warnings": out.warnings,
                        "errors": out.errors,
                    }
            except (json.JSONDecodeError, OSError):
                continue
        out.warn(f"  WARNING: GitHub unavailable and no cache found for parent #{parent_issue_number}")
        return {
            "tasks": [],
            "count": 0,
            "parent_issue_number": parent_issue_number,
            "messages": out.messages,
            "warnings": out.warnings,
            "errors": out.errors,
        }

    sub_issues = get_task_issues(repo, parent_issue_number, output=out)
    tasks = _sub_issues_to_task_dicts(sub_issues)
    if refresh_cache and tasks and not _write_sam_task_cache(tasks, parent_issue_number):
        out.warn("  WARNING: Could not write SAM task cache — no feature slug found in tasks")
    return {
        "tasks": tasks,
        "count": len(tasks),
        "parent_issue_number": parent_issue_number,
        "messages": out.messages,
        "warnings": out.warnings,
        "errors": out.errors,
    }


def update_sam_task_status(
    issue_number: int, new_status: str, output: Output | None = None
) -> dict[str, bool | int | str | list[str]]:
    """Update the status field in the ``<!-- sam:task ... -->`` block of a task issue body.

    Wraps ``github.update_task_status()``. Returns without error when the status
    is already the target value or no ``sam:task`` block is found.

    Args:
        issue_number: Task issue number (without ``#``).
        new_status: Target status string, e.g. ``"in-progress"`` or ``"complete"``.
        output: Optional Output collector.

    Returns:
        Dict with ``updated`` (bool), ``issue_number``, ``new_status``, and output messages.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    out = output or Output()
    repo = get_github()
    updated = update_task_status(repo, issue_number, new_status, output=out)
    return {"updated": updated, "issue_number": issue_number, "new_status": new_status, **out.to_dict()}


_SAM_TERMINAL_STATUSES: frozenset[str] = frozenset({"complete", "closed", "done"})


def _extract_feature_slug(tasks: list[dict[str, object]]) -> str:
    """Return the first non-empty feature slug found in a list of task dicts."""
    for t in tasks:
        slug = t.get("feature", "")
        if isinstance(slug, str) and slug:
            return slug
    return ""


def _build_task_status_map(tasks: list[dict[str, object]]) -> dict[str, str]:
    """Return a ``{task_id: status}`` mapping for feature-scoped task IDs."""
    return {
        str(tid): str(t.get("status", "not-started"))
        for t in tasks
        if isinstance((tid := t.get("task_id", "")), str) and tid
    }


def _is_sam_task_ready(task: dict[str, object], status_by_id: dict[str, str]) -> bool:
    """Return True when a task is not-started and all feature-scoped deps are terminal."""
    if str(task.get("status", "not-started")) != "not-started":
        return False
    deps_raw = task.get("dependencies", [])
    for dep in list(deps_raw) if isinstance(deps_raw, list) else []:
        dep_str = str(dep).strip()
        if dep_str.startswith("#"):  # cross-feature ref — always satisfied
            continue
        if status_by_id.get(dep_str, "not-started") not in _SAM_TERMINAL_STATUSES:
            return False
    return True


def get_ready_sam_tasks(
    parent_issue_number: int, output: Output | None = None
) -> dict[str, str | list[dict[str, object]] | int | list[str]]:
    """Return SAM tasks that are ready to execute (not-started with all deps satisfied).

    A task is ready when its status is ``"not-started"`` and all dependencies
    have a terminal status (``"complete"``). Cross-feature ``#N`` dependencies
    (GitHub issue references) are treated as always-satisfied.

    Args:
        parent_issue_number: Issue number of the parent story (without ``#``).
        output: Optional Output collector.

    Returns:
        Dict with ``feature`` (slug), ``ready_tasks`` (list), ``count``, and output messages.
        Each ready task dict contains: ``id``, ``name``, ``agent``, ``skills``, ``issue_number``.
    """
    out = output or Output()
    tasks_result = get_sam_tasks(parent_issue_number, refresh_cache=True, output=out)
    tasks_raw = tasks_result.get("tasks", [])
    tasks: list[dict[str, object]] = tasks_raw if isinstance(tasks_raw, list) else []  # type: ignore[assignment]
    feature_slug = _extract_feature_slug(tasks)
    status_by_id = _build_task_status_map(tasks)
    ready: list[dict[str, object]] = [
        {
            "id": t.get("task_id", ""),
            "name": t.get("title", ""),
            "agent": t.get("agent", ""),
            "skills": t.get("skills", []),
            "issue_number": t.get("issue_number", 0),
        }
        for t in tasks
        if _is_sam_task_ready(t, status_by_id)
    ]
    return {"feature": feature_slug, "ready_tasks": ready, "count": len(ready), **out.to_dict()}
