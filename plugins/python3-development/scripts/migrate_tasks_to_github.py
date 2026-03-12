#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "ruamel.yaml>=0.18.0",
#     "PyGithub>=2.1.0",
# ]
# ///
r"""Migrate SAM task files to GitHub sub-issues.

Creates a GitHub sub-issue for each task in a local plan/tasks-*.md file,
writing the assigned issue number back to the task's YAML frontmatter as
``github_issue: N``.

This is a one-time operator script for features that pre-date automatic
task issue creation. It is idempotent: tasks that already have a
``github_issue`` field are skipped.

Usage:
    # Dry-run (no API calls, no writes)
    uv run migrate_tasks_to_github.py --task-file plan/tasks-001-my-feature.md \\
        --parent-issue 480 --dry-run

    # Live migration
    uv run migrate_tasks_to_github.py --task-file plan/tasks-001-my-feature/ \\
        --parent-issue 480 --label sam-task
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from ruamel.yaml import YAML

from task_format import resolve_task_id

if TYPE_CHECKING:
    from github.Issue import Issue
    from github.Repository import Repository

# ---------------------------------------------------------------------------
# backlog_core path setup — conditional import guard
# ---------------------------------------------------------------------------

# _SCRIPT_DIR = scripts/  parents[0] = python3-development/
# parents[1] = plugins/   parents[2] = project root (claude_skills/)
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[2]
_BACKLOG_CORE = _PROJECT_ROOT / ".claude" / "skills" / "backlog" / "backlog_core"

_TASK_FORMAT_DIR = _SCRIPT_DIR.parent / "skills" / "implementation-manager" / "scripts"
if _TASK_FORMAT_DIR.exists():
    sys.path.insert(0, str(_TASK_FORMAT_DIR))

if _BACKLOG_CORE.exists():
    sys.path.insert(0, str(_BACKLOG_CORE.parent))

# ---------------------------------------------------------------------------
# Conditional module-level imports from backlog_core.
# Imported at module level so unit tests can patch them via:
#   patch("migrate_tasks_to_github.create_task_issue")
# The guards keep the script runnable without backlog_core present.
# ---------------------------------------------------------------------------

create_task_issue = None
get_github = None
SamTask = None

if _BACKLOG_CORE.exists():
    try:
        from backlog_core.github import create_task_issue, get_github
        from backlog_core.models import SamTask
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# CLI app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="migrate_tasks_to_github", help="Migrate SAM task files to GitHub sub-issues.", no_args_is_help=True
)
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """A parsed task with its source file path.

    Stores both the task metadata and the file path so writes can be
    directed to the correct location.

    Args:
        task_id: Feature-scoped task ID, e.g. "T1".
        title: Human-readable task title.
        status: Task status string, e.g. "not-started".
        agent: Agent name, or empty string if absent.
        priority: Integer priority (1=highest).
        skills: List of skill names.
        dependencies: List of dependency task IDs.
        github_issue: Existing GitHub issue number, or None.
        file_path: Path to the file containing this task.
        raw_content: Full raw content of the file (for round-trip writes).
    """

    task_id: str
    title: str
    status: str
    agent: str
    priority: int
    skills: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    github_issue: int | None = None
    file_path: Path = field(default_factory=Path)
    raw_content: str = ""


# ---------------------------------------------------------------------------
# YAML parsing helpers — standalone, does not import implementation_manager
# ---------------------------------------------------------------------------

_YAML_SAFE = YAML(typ="safe")


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter dict from a ``---``-delimited block.

    Args:
        content: File content starting with ``---``.

    Returns:
        Parsed frontmatter dict, or empty dict on failure.
    """
    parts = content.split("---\n", 2)
    if len(parts) < 3:  # noqa: PLR2004
        return {}
    try:
        parsed = _YAML_SAFE.load(parts[1])
        return parsed if isinstance(parsed, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _parse_task_from_block(segment: str, file_path: Path, raw_content: str) -> TaskRecord | None:
    """Parse a single YAML frontmatter segment into a TaskRecord.

    Args:
        segment: Raw YAML text between ``---`` delimiters (without delimiters).
        file_path: Path to the containing file.
        raw_content: Full raw file content for round-trip writes.

    Returns:
        TaskRecord or None when required fields are missing.
    """
    block = f"---\n{segment}\n---\n"
    fm = _parse_frontmatter(block)
    if not fm:
        return None

    task_id = str(resolve_task_id(fm) or "")
    title = str(fm.get("title") or "")
    status = str(fm.get("status") or "not-started")
    if not task_id or not title:
        return None

    agent = str(fm.get("agent") or "")
    raw_priority = fm.get("priority")
    priority = int(str(raw_priority)) if raw_priority is not None else 2

    raw_skills = fm.get("skills")
    if isinstance(raw_skills, list):
        skills = [str(s) for s in raw_skills if s]
    elif isinstance(raw_skills, str) and raw_skills:
        skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    else:
        skills = []

    raw_deps = fm.get("dependencies")
    if isinstance(raw_deps, list):
        deps = [str(d) for d in raw_deps if d]
    elif isinstance(raw_deps, str) and raw_deps:
        deps = [d.strip() for d in raw_deps.split(",") if d.strip()]
    else:
        deps = []

    github_issue: int | None = None
    raw_gi = fm.get("github_issue")
    if raw_gi is not None:
        try:
            github_issue = int(str(raw_gi))
        except (ValueError, TypeError):
            github_issue = None

    return TaskRecord(
        task_id=task_id,
        title=title,
        status=status,
        agent=agent,
        priority=priority,
        skills=skills,
        dependencies=deps,
        github_issue=github_issue,
        file_path=file_path,
        raw_content=raw_content,
    )


def _parse_directory(path: Path) -> list[TaskRecord]:
    """Parse each .md file in a task directory as a single-task file.

    Args:
        path: Directory containing one .md file per task.

    Returns:
        List of TaskRecord objects.
    """
    tasks: list[TaskRecord] = []
    for md_file in sorted(path.glob("*.md")):
        content = md_file.read_text()
        # Strip leading/trailing --- delimiters for single-task files.
        stripped = content.strip()
        if stripped.startswith("---"):
            stripped = stripped[3:].lstrip("\n")
        if stripped.endswith("---"):
            stripped = stripped[:-3].rstrip("\n")
        task = _parse_task_from_block(stripped, md_file, content)
        if task is not None:
            tasks.append(task)
    return tasks


def parse_task_file(path: Path) -> list[TaskRecord]:
    """Parse a task file or directory into a list of TaskRecords.

    Handles two file structures:
    - **Directory**: one ``.md`` file per task.
    - **Single file**: multiple ``---``-delimited blocks; first block is the
      global manifest (has ``feature:`` but no ``task:``/``task_id:``).

    Args:
        path: Path to a task ``.md`` file or a task directory.

    Returns:
        List of TaskRecord objects, one per task.
    """
    if path.is_dir():
        return _parse_directory(path)

    content = path.read_text(encoding="utf-8")
    first_fm = _parse_frontmatter(content)

    # Multi-task: global manifest has 'feature' but no task identifier.
    if "feature" in first_fm and "task" not in first_fm and "task_id" not in first_fm:
        parts = content.split("---\n", 2)
        body = parts[2] if len(parts) >= 3 else ""  # noqa: PLR2004
        tasks: list[TaskRecord] = []
        for segment in re.split(r"\n---\n", body):
            has_task_field = "task:" in segment or "task_id:" in segment
            if not has_task_field or "status:" not in segment:
                continue
            task = _parse_task_from_block(segment, path, content)
            if task is not None:
                tasks.append(task)
        return tasks

    # Single-task file: strip surrounding --- delimiters before parsing.
    stripped = content.strip()
    if stripped.startswith("---"):
        stripped = stripped[3:].lstrip("\n")
    if stripped.endswith("---"):
        stripped = stripped[:-3].rstrip("\n")
    task = _parse_task_from_block(stripped, path, content)
    return [task] if task is not None else []


def derive_slug(task_file: Path) -> str:
    """Derive the feature slug from the task file path.

    Strips the ``tasks-N-`` prefix from the filename or directory name.

    Args:
        task_file: Path to task file or directory.

    Returns:
        Feature slug string.
    """
    name = task_file.stem if task_file.is_file() else task_file.name
    slug = re.sub(r"^tasks-\d+-", "", name)
    return slug or name


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


def topological_sort(tasks: list[TaskRecord]) -> list[TaskRecord]:
    """Sort tasks in dependency-first order using Kahn's algorithm.

    Falls back to file order with a warning when a cycle is detected.

    Args:
        tasks: List of TaskRecord objects to sort.

    Returns:
        Sorted list of TaskRecord objects.
    """
    id_to_task = {t.task_id: t for t in tasks}
    known_ids = set(id_to_task)

    in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
    dependents: dict[str, list[str]] = {t.task_id: [] for t in tasks}

    for task in tasks:
        for dep in task.dependencies:
            if dep in known_ids:
                in_degree[task.task_id] += 1
                dependents[dep].append(task.task_id)

    queue = sorted(tid for tid, deg in in_degree.items() if deg == 0)
    sorted_ids: list[str] = []

    while queue:
        tid = queue.pop(0)
        sorted_ids.append(tid)
        newly_ready = []
        for dependent in dependents[tid]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                newly_ready.append(dependent)
        queue.extend(sorted(newly_ready))

    if len(sorted_ids) != len(tasks):
        err_console.print(":warning:  Cycle detected in task dependencies — processing in file order.", style="yellow")
        return tasks

    return [id_to_task[tid] for tid in sorted_ids]


# ---------------------------------------------------------------------------
# Task type inference
# ---------------------------------------------------------------------------

_TASK_TYPE_HEURISTICS: list[tuple[list[str], str]] = [
    (["research", "investigate", "explore"], "research"),
    # "review" before "implement" so "Review the implementation" -> "review".
    (["review", "audit", "check"], "review"),
    (["implement", "add", "build", "create"], "implement"),
    (["fix", "repair", "correct"], "fix"),
    (["doc", "update skill"], "docs"),
]


def infer_task_type(title: str) -> str:
    """Infer the SAM task type from the task title.

    Checks title (case-insensitive) against keyword heuristics. Returns
    ``"implement"`` when no keyword matches.

    Args:
        title: Human-readable task title.

    Returns:
        One of: ``"research"``, ``"implement"``, ``"review"``, ``"fix"``, ``"docs"``.
    """
    lower = title.lower()
    for keywords, task_type in _TASK_TYPE_HEURISTICS:
        if any(kw in lower for kw in keywords):
            return task_type
    return "implement"


# ---------------------------------------------------------------------------
# YAML field write helpers
# ---------------------------------------------------------------------------


def _patch_frontmatter_field(content: str, field_name: str, value: int) -> str:
    """Insert or replace a field in the first YAML frontmatter block.

    Args:
        content: Full file content.
        field_name: YAML field name to set.
        value: Integer value for the field.

    Returns:
        Updated content string.
    """
    lines = content.split("\n")
    open_idx: int | None = None
    close_idx: int | None = None

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if open_idx is None:
                open_idx = i
            else:
                close_idx = i
                break

    if open_idx is None or close_idx is None:
        return content

    pattern = re.compile(rf"^{re.escape(field_name)}\s*:")
    field_idx: int | None = None
    for i in range(open_idx + 1, close_idx):
        if pattern.match(lines[i]):
            field_idx = i
            break

    new_line = f"{field_name}: {value}"
    if field_idx is not None:
        lines[field_idx] = new_line
    else:
        lines.insert(close_idx, new_line)

    return "\n".join(lines)


def _patch_segment_in_multi_task(content: str, task_id: str, issue_number: int) -> str:
    r"""Patch ``github_issue`` in the YAML segment for a specific task.

    Splits on ``\n---\n`` boundaries, locates the segment containing the
    given task_id, patches it, then reassembles the file.

    Args:
        content: Full multi-task file content.
        task_id: Task ID to match.
        issue_number: Issue number to write.

    Returns:
        Updated full content string.
    """
    header_split = content.split("---\n", 2)
    if len(header_split) < 3:  # noqa: PLR2004
        return content

    prefix = header_split[0]
    global_block = header_split[1]
    body = header_split[2]

    id_pattern = re.compile(rf'(?:^|\n)task(?:_id)?:\s*["\']?{re.escape(task_id)}["\']?\s*(?:\n|$)')
    patched_segments: list[str] = []
    for seg in re.split(r"\n---\n", body):
        if id_pattern.search(seg):
            seg_content = f"---\n{seg}\n---\n"
            seg_content = _patch_frontmatter_field(seg_content, "github_issue", issue_number)
            seg = seg_content.removeprefix("---\n").removesuffix("\n---\n")  # noqa: PLW2901
        patched_segments.append(seg)

    body_patched = "\n---\n".join(patched_segments)
    return f"{prefix}---\n{global_block}---\n{body_patched}"


def _write_github_issue_field(task: TaskRecord, issue_number: int) -> None:
    """Write ``github_issue: N`` into the task's YAML frontmatter.

    For multi-task single files, patches only the relevant segment.
    For individual task files, patches the leading frontmatter block.

    Args:
        task: TaskRecord whose file should be updated.
        issue_number: GitHub issue number to write.
    """
    if task.file_path.is_dir():
        return

    content = task.file_path.read_text()
    first_fm = _parse_frontmatter(content)
    is_multi = "feature" in first_fm and "task" not in first_fm and "task_id" not in first_fm

    updated = (
        _patch_segment_in_multi_task(content, task.task_id, issue_number)
        if is_multi
        else _patch_frontmatter_field(content, "github_issue", issue_number)
    )
    task.file_path.write_text(updated)


# ---------------------------------------------------------------------------
# Cache write
# ---------------------------------------------------------------------------


def _write_cache(slug: str, parent_issue: int, created: list[tuple[TaskRecord, int]]) -> Path:
    """Write the sam-tasks cache file after migration.

    Args:
        slug: Feature slug.
        parent_issue: Parent GitHub issue number.
        created: List of (TaskRecord, issue_number) pairs.

    Returns:
        Path to the written cache file.
    """
    cache_dir = Path(".claude") / "context"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"sam-tasks-{slug}.json"

    tasks_data = [
        {
            "issue_number": issue_num,
            "task_id": task.task_id,
            "status": task.status,
            "agent": task.agent,
            "priority": task.priority,
            "skills": task.skills,
            "dependencies": task.dependencies,
        }
        for task, issue_num in created
    ]

    cache = {
        "feature_slug": slug,
        "parent_issue_number": parent_issue,
        "synced_at": datetime.now(UTC).isoformat(),
        "tasks": tasks_data,
    }

    cache_path.write_text(json.dumps(cache, indent=2))
    return cache_path


# ---------------------------------------------------------------------------
# Live migration helpers — separated to reduce migrate() complexity
# ---------------------------------------------------------------------------


def _connect_github() -> Repository | None:
    """Connect to GitHub and return a Repository object.

    Returns:
        Repository object, or None if backlog_core is unavailable.

    Raises:
        SystemExit: On connection failure.
    """
    if create_task_issue is None or get_github is None or SamTask is None:
        err_console.print(
            f":cross_mark: backlog_core not found or could not be imported from {_BACKLOG_CORE}", style="red"
        )
        raise typer.Exit(code=1)

    try:
        return get_github()
    except Exception as exc:
        err_console.print(f":cross_mark: GitHub connection failed: {exc}", style="red")
        raise typer.Exit(code=1) from exc


def _migrate_task(task: TaskRecord, slug: str, repo: Repository, parent_issue: int, labels: list[str]) -> Issue | None:
    """Create a GitHub sub-issue for a single task.

    Args:
        task: TaskRecord to migrate.
        slug: Feature slug.
        repo: GitHub Repository object.
        parent_issue: Parent story issue number.
        labels: Label names to apply.

    Returns:
        Created Issue object, or None on failure.
    """
    task_type = infer_task_type(task.title)
    sam = SamTask(  # type: ignore[misc]
        task_id=task.task_id,
        feature=slug,
        task_type=task_type,
        status=task.status,
        agent=task.agent,
        priority=task.priority,
        skills=task.skills,
        dependencies=task.dependencies,
    )
    try:
        return create_task_issue(  # type: ignore[misc]
            repo, parent_issue, sam, description=task.title, acceptance_criteria=[], labels=labels
        )
    except Exception as exc:  # noqa: BLE001
        err_console.print(f":warning:  Failed to create issue for {task.task_id}: {exc}", style="yellow")
        return None


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@app.command()
def migrate(
    task_file: Annotated[
        Path, typer.Option("--task-file", help="Path to task file or task directory.", show_default=False)
    ],
    parent_issue: Annotated[
        int, typer.Option("--parent-issue", help="Parent story GitHub issue number (without #).", show_default=False)
    ],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print actions without making API calls or writing files.")
    ] = False,
    label: Annotated[
        list[str] | None, typer.Option("--label", help="GitHub label name to apply to created issues (repeatable).")
    ] = None,
) -> None:
    """Create GitHub sub-issues for tasks in a SAM task file.

    Reads each task, infers its type, and creates a GitHub sub-issue under
    the parent story issue. Writes ``github_issue: N`` back to the task YAML
    on success. Skips tasks that already have a ``github_issue`` field.
    """
    if not task_file.exists():
        console.print(f":cross_mark: Task file not found: {task_file}", style="red")
        raise typer.Exit(code=1)

    tasks = parse_task_file(task_file)
    if not tasks:
        console.print(":cross_mark: No tasks found in task file.", style="red")
        raise typer.Exit(code=1)

    slug = derive_slug(task_file)
    labels: list[str] = label or []
    ordered = topological_sort(tasks)

    repo = None if dry_run else _connect_github()

    n_created = 0
    n_skipped = 0
    n_failed = 0
    created_pairs: list[tuple[TaskRecord, int]] = []

    for task in ordered:
        task_type = infer_task_type(task.title)

        if task.github_issue is not None:
            console.print(f"Skipping {task.task_id} — already has github_issue: {task.github_issue}")
            n_skipped += 1
            continue

        if dry_run:
            # Escape brackets so Rich does not interpret them as markup tags.
            console.print(f"Would create: \\[{slug}/{task.task_id}] {task_type}: {task.title}")
            n_created += 1
            continue

        if repo is None:
            err_console.print(":cross_mark: Repository unavailable for live migration.", style="red")
            raise typer.Exit(code=1)
        issue = _migrate_task(task, slug, repo, parent_issue, labels)
        if issue is None:
            n_failed += 1
            continue

        try:
            _write_github_issue_field(task, issue.number)
            console.print(f":white_check_mark: Created #{issue.number} for {task.task_id}: {task.title}")
            n_created += 1
            created_pairs.append((task, issue.number))
        except Exception as exc:  # noqa: BLE001
            err_console.print(
                f":warning:  Created #{issue.number} but could not write github_issue field: {exc}", style="yellow"
            )
            n_failed += 1

    if not dry_run and created_pairs:
        cache_path = _write_cache(slug, parent_issue, created_pairs)
        console.print(f"Cache written: {cache_path}")

    console.print(f"{n_created} created, {n_skipped} skipped, {n_failed} failed")


if __name__ == "__main__":
    app()
