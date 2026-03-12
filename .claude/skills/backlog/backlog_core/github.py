"""GitHub API operations for the backlog MCP package.

Handles GitHub connection, issue CRUD, status/label management, and view enrichment.
All functions that previously used typer.echo() accept an optional Output parameter.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from github import Auth, Github, GithubException

from .models import (
    DEFAULT_REPO,
    TYPE_TO_LABEL,
    BacklogItem,
    GitHubUnavailableError,
    IssueLocalFields,
    IssueStatus,
    Output,
    PullRequestRef,
    SamTask,
    ViewItemResult,
)
from .parsing import (
    append_or_replace_section,
    build_issue_body,
    build_sam_task_body,
    build_sam_task_issue_title,
    infer_type,
    normalize_issue_title,
    parse_sam_task_metadata,
    today,
)

if TYPE_CHECKING:
    from github.Issue import Issue, SubIssue
    from github.Repository import Repository


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def get_github(repo: str = DEFAULT_REPO, timeout: int = 15) -> Repository:
    """Get a PyGithub Repository object.

    Args:
        repo: Repository name in ``owner/name`` format.
        timeout: HTTP request timeout in seconds. Defaults to 15 to prevent
            blocking the FastMCP async event loop when called via
            ``asyncio.to_thread()``. The MCP transport enforces a 60-second
            tool deadline; without a timeout here, a slow GitHub API response
            blocks the thread for the full 60 seconds before timing out.

    Returns:
        PyGithub Repository object.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise GitHubUnavailableError("GITHUB_TOKEN not set")
    gh = Github(auth=Auth.Token(token), timeout=timeout)
    return gh.get_repo(repo)


def try_get_github(repo: str = DEFAULT_REPO) -> Repository | None:
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


# ---------------------------------------------------------------------------
# Issue CRUD
# ---------------------------------------------------------------------------


def create_issue_for_item(
    repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
) -> int | None:
    """Create GitHub issue for backlog item.

    Returns:
        Issue number if created, None otherwise.
    """
    out = output or Output()
    title = item.title
    if not title:
        return None
    type_label = item.item_type
    type_map = {"feature": "feat", "bug": "fix", "refactor": "refactor", "docs": "docs", "chore": "chore"}
    prefix = type_map.get(type_label.lower(), "feat")
    issue_title = f"{prefix}: {title}"
    body = build_issue_body(item)
    priority = item.priority or "P1"
    type_gh = TYPE_TO_LABEL.get(type_label.lower()) or infer_type(item.description, title)
    priority_gh = f"priority:{priority.lower()}"
    if dry_run:
        out.info(f"  [dry-run] Would create: {issue_title}")
        return None
    labels = ["status:needs-grooming", priority_gh, type_gh]
    label_objs = []
    for name in labels:
        try:
            label_objs.append(repo.get_label(name))
        except GithubException:
            out.warn(f"  WARNING: label '{name}' not found")
    issue = repo.create_issue(title=issue_title, body=body, labels=label_objs)
    out.info(f"  Created #{issue.number}: {issue_title[:60]}...")
    return issue.number


def close_github_issue(
    issue_ref: str,
    reason: str,
    *,
    reference: str = "",
    comment: str = "",
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> None:
    """Close GitHub issue as dismissed (not completed). ADR-9."""
    out = output or Output()
    try:
        repository = get_github(repo)
        num = issue_ref.lstrip("#")
        issue = repository.get_issue(int(num))
        parts = [f"**Closed** ({reason})."]
        if reference:
            parts.append(f"**Reference**: {reference}")
        if comment:
            parts.append(f"\n{comment}")
        issue.create_comment(" ".join(parts))
        issue.edit(state="closed")
        out.info(f"  GitHub issue #{num} closed ({reason}).")
    except GithubException as e:
        out.warn(f"  WARNING: Could not close issue: {e}")


def resolve_github_issue(
    issue_ref: str,
    *,
    summary: str,
    method: str = "",
    notes: str = "",
    follow_ups: str = "",
    findings: str = "",
    repo: str = DEFAULT_REPO,
    output: Output | None = None,
) -> None:
    """Close GitHub issue as completed with structured evidence trail. ADR-9."""
    out = output or Output()
    try:
        repository = get_github(repo)
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
        issue.edit(state="closed")
        out.info(f"  GitHub issue #{num} resolved.")
    except GithubException as e:
        out.warn(f"  WARNING: Could not close issue: {e}")


# ---------------------------------------------------------------------------
# PR check
# ---------------------------------------------------------------------------


def check_open_prs_for_issue(issue_num: int, repo: str = DEFAULT_REPO) -> list[PullRequestRef]:
    """Check for open pull requests that reference a given issue number.

    Searches the repository for open PRs whose title or body contains ``#N``
    (where N is the issue number). This catches PRs with ``Fixes #N``,
    ``Closes #N``, or any other reference to the issue.

    Args:
        issue_num: The GitHub issue number to search for.
        repo: Repository in ``owner/repo`` format.

    Returns:
        List of PullRequestRef models for each matching PR.
        Empty list if no open PRs found or GitHub is unavailable.
    """
    try:
        gh = Github(auth=Auth.Token(os.environ.get("GITHUB_TOKEN", "")), timeout=10)
        query = f"repo:{repo} is:pr is:open #{issue_num}"
        results = gh.search_issues(query)
        # Materialize the lazy PaginatedList inside try — iteration triggers the API call
        prs = [PullRequestRef(number=pr.number, title=pr.title, url=pr.html_url) for pr in results]
    except GithubException:
        return []
    return prs


# ---------------------------------------------------------------------------
# Status / label management
# ---------------------------------------------------------------------------


def batch_fetch_statuses(items: list[BacklogItem], repo: str = DEFAULT_REPO) -> dict[int, IssueStatus]:
    """Batch fetch status and milestone from GH for all items with issue numbers.

    Single API call replaces N+1 per-item get_issue() calls.

    Returns:
        Dict mapping issue_number -> IssueStatus model.
    """
    repo_obj = try_get_github(repo)
    if repo_obj is None:
        return {}
    try:
        all_issues = {issue.number: issue for issue in repo_obj.get_issues(state="open") if issue.pull_request is None}
    except GithubException:
        return {}
    result: dict[int, IssueStatus] = {}
    for item in items:
        num_str = item.issue.lstrip("#")
        if not num_str.isdigit():
            continue
        num = int(num_str)
        if num in all_issues:
            gh_issue = all_issues[num]
            status_labels = [lbl.name for lbl in gh_issue.labels if lbl.name.startswith("status:")]
            result[num] = IssueStatus(
                status=status_labels[0] if status_labels else "",
                milestone=gh_issue.milestone.title if gh_issue.milestone else "",
            )
    return result


def fetch_item_status(item: BacklogItem, repo: str = DEFAULT_REPO, output: Output | None = None) -> str:
    """Fetch status label from GitHub issue for an item (single-item fallback).

    Prefer batch_fetch_statuses() for listing multiple items.

    Returns:
        Status label string or empty string.
    """
    if not item.issue:
        return ""
    try:
        repository = get_github(repo)
        num = item.issue.lstrip("#")
        gh_issue = repository.get_issue(int(num))
        labels = [lb.name for lb in gh_issue.labels if lb.name.startswith("status:")]
        return labels[0] if labels else ""
    except GithubException:
        return ""


def apply_status_in_progress(item: BacklogItem, repo: str = DEFAULT_REPO, output: Output | None = None) -> None:
    """Set GitHub issue label to status:in-progress."""
    out = output or Output()
    try:
        repository = get_github(repo)
        num = item.issue.lstrip("#")
        issue = repository.get_issue(int(num))
        labels = [label.name for label in issue.labels]
        if "status:in-progress" not in labels:
            lbl = repository.get_label("status:in-progress")
            issue.add_to_labels(lbl)
            if "status:needs-grooming" in labels:
                ng = repository.get_label("status:needs-grooming")
                issue.remove_from_labels(ng)
        out.info("  Status: in-progress")
    except GithubException as e:
        out.warn(f"  WARNING: Could not set status: {e}")


# ---------------------------------------------------------------------------
# Issue queries
# ---------------------------------------------------------------------------


def fetch_open_issues_by_title(repo: Repository) -> dict[str, int]:
    """Fetch all open issues and return ``{normalized_title: issue_number}`` map.

    When duplicates exist, keeps the lowest issue number (the original).

    Returns:
        Dict mapping normalized title strings to their GitHub issue number.
    """
    title_to_num: dict[str, int] = {}
    for issue in repo.get_issues(state="open"):
        if issue.pull_request:
            continue
        key = normalize_issue_title(issue.title)
        if key not in title_to_num or issue.number < title_to_num[key]:
            title_to_num[key] = issue.number
    return title_to_num


# ---------------------------------------------------------------------------
# View enrichment
# ---------------------------------------------------------------------------


def view_enrich_from_github(result: ViewItemResult, issue_num: str, repo: str = DEFAULT_REPO) -> bool:
    """Enrich view result with live GitHub issue data.

    Returns:
        True if GitHub data was fetched, False if unavailable or errored.
    """
    gh_repo = try_get_github(repo)
    if gh_repo is None:
        return False
    try:
        gh_issue = gh_repo.get_issue(int(issue_num))
    except GithubException:
        return False
    result.number = gh_issue.number
    result.title = gh_issue.title
    result.state = gh_issue.state
    result.body = gh_issue.body or ""
    result.labels = [lb.name for lb in gh_issue.labels]
    ms = gh_issue.milestone
    result.milestone = ms.title if ms else ""
    for lb in result.labels:
        if lb.startswith("priority:"):
            result.priority = lb.split(":", 1)[1].upper()
        if lb.startswith("status:"):
            result.status = lb.split(":", 1)[1]
    return True


# ---------------------------------------------------------------------------
# Issue data extraction
# ---------------------------------------------------------------------------


def issue_to_local_fields(issue: Issue) -> IssueLocalFields:
    """Extract backlog-relevant fields from a PyGithub Issue object.

    Returns:
        IssueLocalFields model with title, body, priority, type, status, etc.
    """
    labels = [lbl.name for lbl in issue.labels]
    priority = "P1"
    for lbl in labels:
        if lbl.startswith("priority:"):
            priority = lbl.split(":")[1].upper()
            break
    item_type = "Feature"
    for lbl in labels:
        if lbl.startswith("type:"):
            item_type = lbl.split(":")[1].capitalize()
            break
    status = "open"
    if issue.state == "closed":
        status = "done"
    else:
        for lbl in labels:
            if lbl.startswith("status:"):
                status = lbl.split(":")[1]
                break
    return IssueLocalFields(
        title=issue.title,
        body=issue.body or "",
        priority=priority,
        item_type=item_type,
        status=status,
        updated_at=issue.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if issue.updated_at else "",
        milestone=issue.milestone.title if issue.milestone else "",
    )


# ---------------------------------------------------------------------------
# Groomed content sync
# ---------------------------------------------------------------------------


def sync_groomed_to_github_issue(
    repo_obj: Repository,
    issue_num: int,
    groomed_content: str,
    section_name: str | None = None,
    output: Output | None = None,
) -> bool:
    """Append or merge groomed content into GitHub issue body. GitHub is canonical.

    Returns:
        True if the issue body was actually updated, False otherwise.
    """
    out = output or Output()
    try:
        issue = repo_obj.get_issue(issue_num)
        body = issue.body or ""
        content = groomed_content.strip()
        if not content:
            return False
        today_str = today()
        if section_name and section_name.lower() not in {"groomed", ""}:
            new_body = append_or_replace_section(body, section_name, content)
        else:
            groomed_re = re.compile(r"\n## Groomed\s*\([^)]*\)\s*\n[\s\S]*?(?=\n## |\Z)", re.MULTILINE)
            block = f"\n## Groomed ({today_str})\n\n{content}\n"
            new_body = groomed_re.sub(block, body) if groomed_re.search(body) else body.rstrip() + "\n\n" + block
        if new_body == body:
            return False
        issue.edit(body=new_body)
    except GithubException as e:
        out.warn(f"  WARNING: Could not sync to GitHub issue: {e}")
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# Issue body fetch
# ---------------------------------------------------------------------------


def fetch_github_issue_body(repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
    """Fetch GitHub issue body text.

    Args:
        repo_obj: PyGithub Repository object.
        issue_num: Issue number (without '#').
        output: Optional Output collector for status/warning messages.

    Returns:
        Issue body string, or None on error.
    """
    out = output or Output()
    try:
        return repo_obj.get_issue(issue_num).body or ""
    except GithubException as e:
        out.warn(f"  WARNING: Could not fetch issue #{issue_num}: {e}")
        return None


# ---------------------------------------------------------------------------
# SAM task sub-issue operations
# ---------------------------------------------------------------------------


def create_task_issue(
    repo: Repository,
    parent_issue_number: int,
    task: SamTask,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
    labels: list[str] | None = None,
    output: Output | None = None,
) -> Issue | None:
    """Create a GitHub issue for a SAM task and link it as a sub-issue of the parent story.

    The issue body uses ``build_sam_task_body()``: human-readable sections are
    visible in the GitHub UI, machine-readable metadata is stored in an invisible
    ``<!-- sam:task ... -->`` block for ``parse_sam_task_metadata()`` to read back.

    Title format: ``[{feature}/{task_id}] {task_type}: {description}``

    Args:
        repo: PyGithub Repository object.
        parent_issue_number: Issue number of the parent story (without ``#``).
        task: ``SamTask`` with ``task_id``, ``feature``, ``task_type``, and other fields.
        description: Short human-readable description of the task.
        acceptance_criteria: Optional list of acceptance criteria strings.
        labels: Optional list of label names to apply (e.g. ``["sam-task"]``).
        output: Optional Output collector.

    Returns:
        The created PyGithub Issue object, or None on failure.

    Note:
        ``add_sub_issue()`` requires the Issue *object*, not ``.number`` or ``.id``.
        This function always passes the object to avoid the ``.id``/``.number``
        confusion documented in PyGithub's Issue.py docstring (line 588).
    """
    out = output or Output()
    title = build_sam_task_issue_title(task, description)
    body = build_sam_task_body(task, description, acceptance_criteria)
    label_objs = []
    for name in labels or []:
        try:
            label_objs.append(repo.get_label(name))
        except GithubException:
            out.warn(f"  WARNING: label '{name}' not found, skipping")
    try:
        task_issue = repo.create_issue(title=title, body=body, labels=label_objs)
        out.info(f"  Created task issue #{task_issue.number}: {title[:70]}")
    except GithubException as e:
        out.warn(f"  WARNING: Could not create task issue: {e}")
        return None
    # Link as sub-issue — pass the Issue object, not .id or .number, to avoid
    # the integer ID confusion documented in PyGithub Issue.py line 588.
    try:
        parent = repo.get_issue(parent_issue_number)
        parent.add_sub_issue(task_issue)
        out.info(f"  Linked #{task_issue.number} as sub-issue of #{parent_issue_number}")
    except GithubException as e:
        out.warn(f"  WARNING: Created issue #{task_issue.number} but could not link as sub-issue: {e}")
    return task_issue


def get_task_issues(repo: Repository, parent_issue_number: int, output: Output | None = None) -> list[SubIssue]:
    """Return all sub-issues for a parent story issue, ordered by ``priority_position``.

    Args:
        repo: PyGithub Repository object.
        parent_issue_number: Issue number of the parent story (without ``#``).
        output: Optional Output collector.

    Returns:
        List of ``SubIssue`` objects (empty on failure or when none exist).
    """
    out = output or Output()
    try:
        parent = repo.get_issue(parent_issue_number)
        return sorted(parent.get_sub_issues(), key=lambda si: si.priority_position)
    except GithubException as e:
        out.warn(f"  WARNING: Could not fetch sub-issues for #{parent_issue_number}: {e}")
        return []


def update_task_status(repo: Repository, issue_number: int, new_status: str, output: Output | None = None) -> bool:
    """Update the ``status`` field inside the ``<!-- sam:task ... -->`` block of a task issue body.

    Reads the current body, patches the YAML block's ``status`` value, and writes
    the updated body back. Returns ``False`` without writing if the body has no
    ``<!-- sam:task ... -->`` block, or if the status is already the target value.

    Args:
        repo: PyGithub Repository object.
        issue_number: Task issue number (without ``#``).
        new_status: Target status string, e.g. ``"in-progress"`` or ``"complete"``.
        output: Optional Output collector.

    Returns:
        ``True`` if the body was updated, ``False`` otherwise.
    """
    out = output or Output()
    try:
        issue = repo.get_issue(issue_number)
        body = issue.body or ""
    except GithubException as e:
        out.warn(f"  WARNING: Could not fetch issue #{issue_number}: {e}")
        return False
    task_meta = parse_sam_task_metadata(body)
    if task_meta is None:
        out.warn(f"  WARNING: Issue #{issue_number} has no sam:task block — cannot update status")
        return False
    if task_meta.status == new_status:
        return False
    # Replace only the status line inside the invisible block.
    updated_body = re.sub(
        r"(<!--\s*sam:task\s*\n(?:.*\n)*?status:\s*)(\S+)",
        lambda m: m.group(1) + new_status,
        body,
        count=1,
        flags=re.DOTALL,
    )
    if updated_body == body:
        out.warn(f"  WARNING: Issue #{issue_number}: sam:task block present but status line not found")
        return False
    try:
        issue.edit(body=updated_body)
    except GithubException as e:
        out.warn(f"  WARNING: Could not update issue #{issue_number} body: {e}")
        return False
    out.info(f"  Updated #{issue_number} status: {task_meta.status} -> {new_status}")
    return True
