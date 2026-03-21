"""Compatibility shim for scripts/backlog.py.

The original dict-based reconciliation functions and _build_issue_body_from_file
that previously lived in this file are provided here for backward compatibility
with test_reconciliation.py and test_backlog_core_parsing.py.

These implementations use plain dicts (not BacklogItem Pydantic models) to
match the original scripts/backlog.py interface.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module-level state (monkeypatched in tests)
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# ReconcileResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReconcileResult:
    """Result of reconciling one backlog item against GitHub state."""

    issue_number: int
    action: str  # no_change | auto_corrected | closed | wip_protected | flagged_divergence
    old_status: str
    new_status: str
    warning: str = ""


# ---------------------------------------------------------------------------
# Terminal statuses
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "resolved", "closed"})


def _get_item_status(item: dict[str, Any]) -> str:
    """Extract status from a dict item using either key variant.

    Returns:
        Status string, or empty string if no status key is present.
    """
    return str(item.get("**Status**", item.get("_status", "")))


# ---------------------------------------------------------------------------
# _filter_closed_items
# ---------------------------------------------------------------------------


def _filter_closed_items(items: list[dict[str, Any]], include_closed: bool) -> list[dict[str, Any]]:
    """Filter out items with terminal status when include_closed is False.

    Args:
        items: List of backlog item dicts.
        include_closed: When True, all items are returned unfiltered.

    Returns:
        Filtered list of items.
    """
    if include_closed:
        return list(items)
    return [it for it in items if _get_item_status(it) not in _TERMINAL_STATUSES]


# ---------------------------------------------------------------------------
# _has_active_work
# ---------------------------------------------------------------------------

_IN_PROGRESS_LEGACY = re.compile(r"\*\*Status\*\*:\s*IN PROGRESS", re.IGNORECASE)
_IN_PROGRESS_YAML = re.compile(r"status:\s*in-progress", re.IGNORECASE)


def _has_active_work(item: dict[str, Any]) -> tuple[bool, str]:
    """Detect whether a backlog item has active in-progress work.

    Checks:
    1. Plan files matching the item topic contain an IN PROGRESS task.
    2. An active-task context file references the item's issue number.

    Args:
        item: Backlog item dict with optional _topic and _issue fields.

    Returns:
        (has_work: bool, reason: str) — reason is empty string when False.
    """
    topic: str | None = item.get("_topic")
    issue_str: str = str(item.get("_issue", ""))

    # Parse issue number for context file check
    issue_num: int | None = None
    m = re.match(r"#(\d+)$", issue_str)
    if m:
        issue_num = int(m.group(1))

    # Check plan files for in-progress tasks
    if topic:
        plan_dir = _REPO_ROOT / "plan"
        if plan_dir.is_dir():
            for plan_file in plan_dir.glob(f"tasks-*-{topic}.md"):
                try:
                    content = plan_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                if _IN_PROGRESS_LEGACY.search(content) or _IN_PROGRESS_YAML.search(content):
                    return True, f"Plan file {plan_file.name} has IN PROGRESS task"

    # Check active-task context files for this issue
    if issue_num is not None:
        context_dir = _REPO_ROOT / ".claude" / "context"
        if context_dir.is_dir():
            for ctx_file in context_dir.glob("active-task-*.json"):
                try:
                    data = json.loads(ctx_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if data.get("issue_number") == issue_num:
                    return True, f"active task context references {issue_str}"

    return False, ""


# ---------------------------------------------------------------------------
# DAG helpers (stubbed — monkeypatched in tests)
# ---------------------------------------------------------------------------


def find_valid_path(from_status: str, to_status: str) -> list[str] | None:  # pragma: no cover
    """Return a valid DAG transition path or None if no path exists.

    This stub always returns None (no auto-correction). Tests monkeypatch
    this to control DAG-valid vs invalid scenarios.
    """
    return None


def _update_item_metadata(file_path_str: str, updates: dict[str, Any]) -> None:  # pragma: no cover
    """Persist metadata updates to a backlog item file.

    This stub is a no-op. Tests monkeypatch this to capture calls.
    """


def _try_get_github(repo: str) -> object | None:  # pragma: no cover
    """Attempt to get a GitHub repo object. Returns None if unavailable.

    This stub always returns None. Tests monkeypatch this.

    Returns:
        GitHub repo object, or None if unavailable.
    """
    return None


# ---------------------------------------------------------------------------
# _reconcile_open_item
# ---------------------------------------------------------------------------


def _reconcile_open_item(
    issue_num: int, local_status: str, github_status: str, file_path_str: str | None
) -> ReconcileResult:
    """Reconcile a local item against an open GitHub issue.

    Args:
        issue_num: GitHub issue number.
        local_status: Local backlog status label.
        github_status: GitHub status label (from status: label) or empty string.
        file_path_str: Path to the backlog item file, or None.

    Returns:
        ReconcileResult describing the action taken.
    """
    # No status label on GitHub: flag as stateless void divergence
    if not github_status:
        return ReconcileResult(
            issue_number=issue_num,
            action="flagged_divergence",
            old_status=local_status,
            new_status=local_status,
            warning=f"#{issue_num} stateless void: local='{local_status}', GitHub has no status label",
        )

    # Statuses match: no action needed
    if local_status == github_status:
        return ReconcileResult(
            issue_number=issue_num, action="no_change", old_status=local_status, new_status=local_status
        )

    # Attempt DAG-valid auto-correction
    path = find_valid_path(local_status, github_status)
    if path is not None:
        if file_path_str is not None:
            _update_item_metadata(file_path_str, {"metadata": {"status": github_status}})
        return ReconcileResult(
            issue_number=issue_num, action="auto_corrected", old_status=local_status, new_status=github_status
        )

    # No valid DAG path: flag as invalid transition divergence
    return ReconcileResult(
        issue_number=issue_num,
        action="flagged_divergence",
        old_status=local_status,
        new_status=local_status,
        warning=f"#{issue_num} invalid transition: local='{local_status}', GitHub='{github_status}'",
    )


# ---------------------------------------------------------------------------
# _reconcile_closed_item
# ---------------------------------------------------------------------------


def _reconcile_closed_item(
    issue_num: int, local_status: str, github_status: str, file_path_str: str | None, item: dict[str, Any]
) -> ReconcileResult:
    """Reconcile a local item against a closed GitHub issue.

    Args:
        issue_num: GitHub issue number.
        local_status: Local backlog status label.
        github_status: GitHub status label (e.g. 'done', 'closed').
        file_path_str: Path to the backlog item file, or None.
        item: Full backlog item dict (used for active-work detection).

    Returns:
        ReconcileResult describing the action taken.
    """
    has_work, reason = _has_active_work(item)
    if has_work:
        return ReconcileResult(
            issue_number=issue_num,
            action="wip_protected",
            old_status=local_status,
            new_status=local_status,
            warning=f"#{issue_num} active work in progress — {reason}",
        )

    terminal = github_status if github_status in _TERMINAL_STATUSES else "closed"
    if file_path_str is not None:
        _update_item_metadata(file_path_str, {"metadata": {"status": terminal}})
    return ReconcileResult(issue_number=issue_num, action="closed", old_status=local_status, new_status=terminal)


# ---------------------------------------------------------------------------
# _reconcile_item
# ---------------------------------------------------------------------------


def _extract_github_status(issue: object) -> str:
    """Extract the status label value from a GitHub issue's labels.

    Returns:
        Status string (e.g. 'groomed'), or empty string if no status label.
    """
    for label in getattr(issue, "labels", []):
        name = getattr(label, "name", "")
        if name.startswith("status:"):
            return name[len("status:") :]
    return ""


def _reconcile_item(item: dict[str, Any], github_map: dict[int, Any], repo: str) -> ReconcileResult:
    """Reconcile one backlog item against GitHub state.

    Args:
        item: Backlog item dict with _issue, **Status**, _topic, _file_path fields.
        github_map: Mapping of issue number -> GitHub issue object.
        repo: GitHub repo string (owner/repo).

    Returns:
        ReconcileResult describing the action taken.
    """
    issue_str: str = str(item.get("_issue", ""))
    if not issue_str:
        return ReconcileResult(issue_number=0, action="no_change", old_status="", new_status="")

    m = re.match(r"#(\d+)$", issue_str)
    if not m:
        return ReconcileResult(issue_number=0, action="no_change", old_status="", new_status="")

    issue_num = int(m.group(1))
    local_status = str(item.get("**Status**", item.get("_status", "")))
    file_path_str: str | None = item.get("_file_path")

    if issue_num not in github_map:
        return ReconcileResult(
            issue_number=issue_num,
            action="no_change",
            old_status=local_status,
            new_status=local_status,
            warning=f"#{issue_num} not found in GitHub issue map",
        )

    gh_issue = github_map[issue_num]
    github_status = _extract_github_status(gh_issue)

    if gh_issue.state == "open":
        return _reconcile_open_item(issue_num, local_status, github_status, file_path_str)
    return _reconcile_closed_item(issue_num, local_status, github_status, file_path_str, item)


# ---------------------------------------------------------------------------
# _reconcile_batch
# ---------------------------------------------------------------------------


def _reconcile_batch(items: list[dict[str, Any]], repo: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Reconcile a batch of backlog items against GitHub.

    Args:
        items: List of backlog item dicts.
        repo: GitHub repo string (owner/repo).

    Returns:
        (updated_items, warnings) tuple. Items may be mutated in place.
    """
    warnings: list[str] = []

    gh_repo = _try_get_github(repo)
    if gh_repo is None:
        warnings.append("GitHub unavailable — skipping reconciliation")
        return items, warnings

    try:
        all_issues = list(gh_repo.get_issues(state="all"))  # type: ignore[unresolved-attribute]
        github_map: dict[int, Any] = {
            issue.number: issue for issue in all_issues if getattr(issue, "pull_request", None) is None
        }
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"GitHub API error: {exc}")
        return items, warnings

    for item in items:
        result = _reconcile_item(item, github_map, repo)
        if result.action == "auto_corrected":
            item["**Status**"] = result.new_status
        if result.warning:
            warnings.append(result.warning)

    return items, warnings


# ---------------------------------------------------------------------------
# _build_issue_body_from_file (dict-based)
# ---------------------------------------------------------------------------


def _build_issue_body_from_file(item: dict[str, Any]) -> str | None:
    """Build GitHub issue body from a dict backlog item.

    Uses the '_raw_body' key instead of BacklogItem.raw_body.
    Returns None if no '## Groomed' section is present.

    Args:
        item: Dict with '_raw_body' key containing the file's markdown body.

    Returns:
        Issue body markdown string, or None if no groomed section present.
    """
    raw_body: str = str(item.get("_raw_body", ""))
    if "## Groomed" not in raw_body:
        return None
    return raw_body.strip() + "\n"
