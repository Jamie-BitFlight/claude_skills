#!/usr/bin/env python3
"""Implementation Manager CLI - Query and manage feature implementation task status.

This CLI tool provides commands to query task files for feature implementations,
returning JSON output for orchestrator consumption.

Supports YAML frontmatter task format: individual ``.md`` files with ``---``
delimited metadata. Two organizational structures are supported:

- **Single file**: All tasks in one ``tasks-*.md`` file (file-level frontmatter)
- **Directory**: One task per ``.md`` file in a ``tasks-*/`` directory

Usage:
    ./implementation_manager.py list-features /path/to/project
    ./implementation_manager.py status /path/to/project prepare-host
    ./implementation_manager.py ready-tasks /path/to/project prepare-host
    ./implementation_manager.py validate /path/to/project prepare-host
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypedDict

import typer
from rich.console import Console

# task_format.py is a sibling module in the same scripts/ directory.
# Ensure the script directory is on sys.path for direct execution.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# backlog_core is at <repo_root>/.claude/skills/backlog/backlog_core.
# parents[5] from this script is the repo root (verified against actual filesystem).
_BACKLOG_CORE = Path(__file__).resolve().parents[5] / ".claude" / "skills" / "backlog" / "backlog_core"
if _BACKLOG_CORE.exists():
    sys.path.insert(0, str(_BACKLOG_CORE.parent))

# sam_schema is the canonical task/plan schema package.
# Installed as a workspace dependency in the project venv.
# Fallback: add packages/ to sys.path for direct-script execution outside the venv.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SAM_PACKAGES_DIR = str(_REPO_ROOT / "packages")
if _SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _SAM_PACKAGES_DIR)

# Import directly from submodules so static type checkers resolve concrete types
# instead of the lazy ``object`` returned by sam_schema.__getattr__.
from sam_schema.core.models import STATUS_MAP
from sam_schema.core.query import claim_task as sam_claim_task, load_plan as sam_load_plan

if TYPE_CHECKING:
    from sam_schema.core.models import Task as SamTask

app = typer.Typer(
    name="implementation-manager", help="Query and manage feature implementation task status.", no_args_is_help=True
)
console = Console()


# =============================================================================
# Enums and Data Models
# =============================================================================


class TaskStatus(StrEnum):
    """Status of a task in the task file."""

    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "IN PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    SKIPPED = "SKIPPED"


# Mapping from YAML frontmatter status values to TaskStatus enum members.
# Source: TASK_FILE_FORMAT.md line 283 defines valid statuses as
# not-started, in-progress, complete, blocked.
_YAML_STATUS_TO_ENUM: dict[str, TaskStatus] = {
    "not-started": TaskStatus.NOT_STARTED,
    "in-progress": TaskStatus.IN_PROGRESS,
    "complete": TaskStatus.COMPLETE,
    "blocked": TaskStatus.BLOCKED,
    "deferred": TaskStatus.DEFERRED,
    "skipped": TaskStatus.SKIPPED,
    "wont-fix": TaskStatus.SKIPPED,
}

# Reverse mapping: TaskStatus -> canonical YAML frontmatter string.
# Used when serialising Task objects back to JSON cache.
_YAML_STATUS_TO_ENUM_REVERSE: dict[TaskStatus, str] = {
    TaskStatus.NOT_STARTED: "not-started",
    TaskStatus.IN_PROGRESS: "in-progress",
    TaskStatus.COMPLETE: "complete",
    TaskStatus.BLOCKED: "blocked",
    TaskStatus.DEFERRED: "deferred",
    TaskStatus.SKIPPED: "skipped",
}

# Statuses that count as terminal/done for completion gating and dependency satisfaction.
_TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset({TaskStatus.COMPLETE, TaskStatus.DEFERRED, TaskStatus.SKIPPED})


class TaskPriority(IntEnum):
    """Priority levels for tasks (1=highest, 5=lowest).

    Used to order task execution and validate priority values.
    Raises ValueError when instantiated with an invalid value.
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


@dataclass
class Task:
    """Represents a single task parsed from a task file.

    Args:
        id: Task identifier (e.g., "1.1", "T1", "T15")
        name: Task name/title
        status: Current task status
        dependencies: List of dependency task IDs
        agent: Agent name to execute this task
        priority: Task priority (1-5)
        complexity: Task complexity (Low/Medium/High)
        started: ISO timestamp when task started
        completed: ISO timestamp when task completed
        skills: Skills the sub-agent should load before executing this task
    """

    id: str
    name: str
    status: TaskStatus
    dependencies: list[str] = field(default_factory=list)
    agent: str | None = None
    priority: TaskPriority = TaskPriority.CRITICAL
    complexity: str = "Medium"
    started: str | None = None
    completed: str | None = None
    skills: list[str] = field(default_factory=list)

    def to_dict(self) -> TaskDict:
        """Convert task to dictionary for JSON serialization.

        Returns:
            TaskDict with enum fields converted to primitive values.
        """
        return TaskDict(
            id=self.id,
            name=self.name,
            status=self.status.value,
            dependencies=self.dependencies,
            agent=self.agent,
            priority=self.priority.value,
            complexity=self.complexity,
            started=self.started,
            completed=self.completed,
            skills=self.skills,
        )


@dataclass
class Feature:
    """Represents a feature with its task file or task directory.

    Args:
        slug: Feature slug derived from filename or directory name
        task_file: Filename of the task file or directory name
        path: Full path to the task file or directory
    """

    slug: str
    task_file: str
    path: Path

    def to_dict(self) -> dict[str, str]:
        """Convert feature to dictionary for JSON serialization.

        Returns:
            Dictionary with slug, task_file, and path as strings.
        """
        return {"slug": self.slug, "task_file": self.task_file, "path": str(self.path)}


class TaskData(TypedDict):
    """Type-safe dictionary for task parsing intermediate state.

    Used during parsing before converting to Task dataclass.
    All fields use enum types for type safety.
    """

    id: str
    name: str
    status: TaskStatus
    dependencies: list[str]
    agent: str | None
    priority: TaskPriority
    complexity: str
    started: str | None
    completed: str | None
    skills: list[str]


class TaskDict(TypedDict):
    """Type-safe dictionary for JSON serialization of Task.

    All enum fields are converted to their primitive values.
    Used as the return type for Task.to_dict().
    """

    id: str
    name: str
    status: str  # TaskStatus.value
    dependencies: list[str]
    agent: str | None
    priority: int  # TaskPriority.value
    complexity: str
    started: str | None
    completed: str | None
    skills: list[str]


# =============================================================================
# Task File Parsing
# =============================================================================


def _normalize_status(raw: str) -> str:
    """Normalize a raw status string to its canonical hyphenated form.

    Checks STATUS_MAP from sam_schema.core.models for known variants
    (uppercase space-separated, emoji tokens, title markers), then falls
    back to lowercasing and replacing spaces with hyphens.

    Args:
        raw: Raw status string (e.g., "NOT STARTED", "in progress", "complete").

    Returns:
        Canonical hyphenated status string (e.g., "not-started", "in-progress").
    """
    stripped = raw.strip()
    # Direct lookup in sam_schema STATUS_MAP (handles uppercase, emoji, bracket variants)
    mapped = STATUS_MAP.get(stripped.upper()) or STATUS_MAP.get(stripped)
    if mapped:
        return mapped
    # Fallback: lowercase and replace spaces/underscores with hyphens
    return stripped.lower().replace(" ", "-").replace("_", "-")


def parse_status(status_text: str) -> TaskStatus:
    """Parse task status from various formats.

    Handles emoji formats like :white_check_mark:, :x:, etc.
    Also handles YAML frontmatter hyphenated values (not-started, in-progress).

    Args:
        status_text: Raw status text from task file.

    Returns:
        Normalized TaskStatus enum value.
    """
    status_stripped = status_text.strip()

    # Check YAML frontmatter format first (e.g., "not-started", "in-progress")
    normalized = _normalize_status(status_stripped)
    if normalized in _YAML_STATUS_TO_ENUM:
        return _YAML_STATUS_TO_ENUM[normalized]

    status_lower = status_stripped.lower()

    # Pattern table: (patterns, TaskStatus) — checked in priority order.
    STATUS_PATTERNS: list[tuple[tuple[str, ...], TaskStatus]] = [
        (("complete", ":white_check_mark:", ":heavy_check_mark:", "\\u2705", "\\u2714"), TaskStatus.COMPLETE),
        (
            ("in progress", "in_progress", ":arrows_counterclockwise:", ":repeat:", "\\ud83d\\udd04"),
            TaskStatus.IN_PROGRESS,
        ),
        (("blocked", "blocking"), TaskStatus.BLOCKED),
        (("deferred", "[deferred]"), TaskStatus.DEFERRED),
        (("skipped", "[skipped]", "wontfix", "wont fix", "wont-fix"), TaskStatus.SKIPPED),
        (("not started", "not_started", ":x:", ":cross_mark:", "\\u274c"), TaskStatus.NOT_STARTED),
    ]

    for patterns, result_status in STATUS_PATTERNS:
        if any(p in status_lower for p in patterns):
            return result_status

    # Default to NOT_STARTED if unclear
    return TaskStatus.NOT_STARTED


def parse_dependencies(dep_text: str) -> list[str]:
    """Parse dependency references from task file.

    Handles formats like:
    - "Task 1, Task 2" (legacy numeric)
    - "Task 1.1, Task 1.2" (legacy dotted)
    - "Task T1, Task T2" (alphanumeric with prefix)
    - "T1, T2" (bare alphanumeric IDs)
    - "None" (no dependencies)

    Args:
        dep_text: Raw dependencies text from task file.

    Returns:
        List of dependency task IDs.
    """
    if not dep_text or dep_text.lower().strip() == "none":
        return []

    # Try "Task X" pattern first (handles both "Task 1.1" and "Task T1")
    task_pattern = r"Task\s+([A-Za-z0-9]+(?:\.\d+)?)"
    matches = re.findall(task_pattern, dep_text, re.IGNORECASE)
    if matches:
        return matches

    # Fall back to bare alphanumeric IDs (e.g., "T1, T2" or "1.1, 2.3")
    bare_pattern = r"\b([A-Z]?\d+(?:\.\d+)?)\b"
    return re.findall(bare_pattern, dep_text)


def _parse_yaml_status(raw_status: str) -> TaskStatus:
    """Convert a YAML frontmatter status string to TaskStatus enum.

    Args:
        raw_status: Status value from YAML frontmatter (e.g., "not-started").

    Returns:
        Corresponding TaskStatus enum member.
    """
    normalized = _normalize_status(raw_status)
    if normalized in _YAML_STATUS_TO_ENUM:
        return _YAML_STATUS_TO_ENUM[normalized]
    return TaskStatus.NOT_STARTED


def _coerce_timestamp(value: str | datetime | None) -> str | None:
    """Coerce a YAML timestamp value to an ISO 8601 string or None.

    PyYAML automatically parses ISO 8601 timestamps into datetime objects.
    This function converts them back to strings for consistent Task storage.

    Args:
        value: Raw value from YAML frontmatter (may be str, datetime, or None).

    Returns:
        ISO 8601 string representation, or None if value is falsy.
    """
    if value is None:
        return None
    return str(value)


def _parse_yaml_dependencies(raw_deps: list[str] | str | None) -> list[str]:
    """Parse dependencies from YAML frontmatter value.

    Handles both list format (``[T1, T2]``) and string format (``"T1, T2"``).

    Args:
        raw_deps: Dependencies value from YAML frontmatter.

    Returns:
        List of dependency task ID strings.
    """
    if raw_deps is None:
        return []
    if isinstance(raw_deps, list):
        return [str(dep) for dep in raw_deps]
    if isinstance(raw_deps, str):
        return parse_dependencies(raw_deps)
    return []


def _parse_yaml_skills(raw_skills: list[str] | str | None) -> list[str]:
    """Parse skills from YAML frontmatter value.

    Handles list format (``[skill1, skill2]``) and comma-separated string format
    (``"skill1, skill2"``). Missing or ``None`` values return an empty list.

    Args:
        raw_skills: Skills value from YAML frontmatter (may be list, str, or None).

    Returns:
        List of skill name strings, or empty list when field is absent.
    """
    if isinstance(raw_skills, list):
        return [str(s) for s in raw_skills if s]
    if isinstance(raw_skills, str) and raw_skills:
        return [s.strip() for s in raw_skills.split(",") if s.strip()]
    return []


def _status_from_title(title: str, current_status: TaskStatus) -> TaskStatus:
    """Override status based on [DEFERRED] or [SKIPPED] markers in the task title.

    When the YAML status is still ``not-started`` but the title carries an
    explicit deferral/skip marker, infer the intended terminal status so that
    completion gating treats the task as done.

    Args:
        title: Task title string from YAML frontmatter.
        current_status: Status parsed from YAML ``status`` field.

    Returns:
        Overridden TaskStatus if a marker is found, otherwise ``current_status``.
    """
    if current_status != TaskStatus.NOT_STARTED:
        return current_status
    title_upper = title.upper()
    if "[DEFERRED]" in title_upper:
        return TaskStatus.DEFERRED
    if "[SKIPPED]" in title_upper or "[WONTFIX]" in title_upper:
        return TaskStatus.SKIPPED
    return current_status


def _task_sort_key(task: Task) -> tuple[str, int, int]:
    """Generate a sort key for natural ordering of task IDs.

    Handles IDs like "T1", "T10", "1.1", "15" by extracting the
    alphabetic prefix and numeric components.

    Args:
        task: Task to generate sort key for.

    Returns:
        Tuple of (alpha_prefix, major_number, minor_number) for sorting.
    """
    match = re.match(r"^([A-Za-z]*)(\d+)(?:\.(\d+))?$", task.id)
    if match:
        prefix = match.group(1).upper()
        major = int(match.group(2))
        minor = int(match.group(3)) if match.group(3) else 0
        return (prefix, major, minor)
    # Fallback: sort alphabetically
    return (task.id, 0, 0)


def _create_task_from_dict(task_data: TaskData) -> Task:
    """Create a Task dataclass from a TaskData dictionary.

    Args:
        task_data: Type-safe dictionary with all task fields.

    Returns:
        Task dataclass instance with validated fields.
    """
    return Task(
        id=task_data["id"],
        name=task_data["name"],
        status=task_data["status"],
        dependencies=task_data["dependencies"],
        agent=task_data["agent"],
        priority=task_data["priority"],
        complexity=task_data["complexity"],
        started=task_data["started"],
        completed=task_data["completed"],
        skills=task_data["skills"],
    )


def _has_task_content(directory: Path) -> bool:
    """Check if a directory contains task files or task subdirectories.

    A directory qualifies if it contains either:
    - ``tasks-*.md`` files (monolithic task files)
    - ``tasks-*/`` subdirectories (directory-based task organization)

    Args:
        directory: Path to check for task content.

    Returns:
        True if the directory contains task files or task subdirectories.
    """
    if list(directory.glob("tasks-*.md")):
        return True
    for child in directory.iterdir():
        if child.is_dir() and child.name.startswith("tasks-") and list(child.glob("*.md")):
            return True
    return False


def discover_plan_directory(project_path: Path) -> Path | None:
    """Discover the plan directory in a project.

    Searches common locations for plan directories containing task files
    (either ``tasks-*.md`` files or ``tasks-*/`` subdirectories).
    The search prioritizes explicit common locations before falling back
    to a recursive search with depth limits for performance.

    Search order (first match wins):
    1. Explicit common locations: plan/, .claude/plan/, plans/, docs/plan/
    2. Package-level plan directories: */plan/, packages/*/plan/
    3. Recursive search (limited depth) for any plan/ or plans/ directory

    Args:
        project_path: Root path of the project.

    Returns:
        Path to plan directory if found with task files, None otherwise.
    """
    # Priority 1: Check explicit common locations (fast path)
    common_locations = [
        project_path / "plan",
        project_path / ".claude" / "plan",
        project_path / "plans",
        project_path / "docs" / "plan",
        project_path / "docs" / "plans",
    ]

    for location in common_locations:
        if location.exists() and location.is_dir() and _has_task_content(location):
            return location

    # Priority 2: Check package-level plan directories (monorepo support)
    package_patterns = [
        project_path / "*" / "plan",
        project_path / "packages" / "*" / "plan",
        project_path / "src" / "*" / "plan",
    ]

    for pattern in package_patterns:
        for plan_dir in sorted(pattern.parent.glob(pattern.name)):
            if plan_dir.is_dir() and _has_task_content(plan_dir):
                return plan_dir

    # Priority 3: Recursive search with depth limit (slower, but comprehensive)
    # Limit to 3 levels deep to avoid scanning entire filesystems
    max_depth = 3
    for depth in range(1, max_depth + 1):
        glob_pattern = "/".join(["*"] * depth) + "/plan"
        for plan_dir in sorted(project_path.glob(glob_pattern)):
            if plan_dir.is_dir() and _has_task_content(plan_dir):
                return plan_dir

        glob_pattern = "/".join(["*"] * depth) + "/plans"
        for plan_dir in sorted(project_path.glob(glob_pattern)):
            if plan_dir.is_dir() and _has_task_content(plan_dir):
                return plan_dir

    return None


def find_task_files(project_path: Path) -> list[Feature]:
    """Find all task files and task directories in the plan directory.

    Uses discover_plan_directory to locate the plan directory dynamically,
    supporting various project structures including:
    - Standard: project/plan/
    - Claude-specific: project/.claude/plan/
    - Documentation: project/docs/plan/
    - Monorepo: project/packages/*/plan/

    Discovers both:
    - ``tasks-*.md`` monolithic task files
    - ``tasks-*/`` directories containing individual task files

    Args:
        project_path: Root path of the project.

    Returns:
        List of Feature objects representing task files or directories.
    """
    plan_dir = discover_plan_directory(project_path)

    if plan_dir is None:
        return []

    features: list[Feature] = []

    # Pattern for monolithic task files: tasks-001-feature-name.md
    file_pattern = re.compile(r"tasks-(\d+)-(.+)\.md$")
    for file_path in sorted(plan_dir.glob("tasks-*.md")):
        match = file_pattern.match(file_path.name)
        if match:
            slug = match.group(2)
            features.append(Feature(slug=slug, task_file=file_path.name, path=file_path))

    # Pattern for task directories: tasks-feature-name/
    dir_pattern = re.compile(r"tasks-(.+)$")
    for child in sorted(plan_dir.iterdir()):
        if child.is_dir() and child.name.startswith("tasks-"):
            dir_match = dir_pattern.match(child.name)
            if dir_match and list(child.glob("*.md")):
                slug = dir_match.group(1)
                features.append(Feature(slug=slug, task_file=child.name, path=child))

    return features


def find_task_file_by_slug(project_path: Path, slug: str) -> Path | None:
    """Find task file or directory by feature slug.

    Args:
        project_path: Root path of the project.
        slug: Feature slug (e.g., "prepare-host").

    Returns:
        Path to task file or directory if found, None otherwise.
    """
    features = find_task_files(project_path)

    for feature in features:
        if feature.slug == slug:
            return feature.path

    # Try partial match
    for feature in features:
        if slug in feature.slug:
            return feature.path

    return None


def get_ready_tasks(tasks: list[Task]) -> list[Task]:
    """Get tasks that are ready for execution.

    Returns tasks whose status is NOT_STARTED at the time of the snapshot.
    This list is advisory: status may change between this query and task dispatch.
    Callers MUST invoke claim-task before beginning task execution to atomically
    mark the task in-progress. If claim-task returns claimed=false, discard the
    task from the dispatch queue without error.

    A task is ready when:
    1. Status is NOT_STARTED
    2. All dependencies are terminal (COMPLETE, DEFERRED, or SKIPPED)

    Args:
        tasks: List of all tasks.

    Returns:
        List of tasks ready for execution.
    """
    # Build a lookup for task status by ID
    status_by_id: dict[str, TaskStatus] = {task.id: task.status for task in tasks}

    ready: list[Task] = []

    for task in tasks:
        # Skip if not NOT_STARTED
        if task.status != TaskStatus.NOT_STARTED:
            continue

        # Check if all dependencies are terminal (complete, deferred, or skipped)
        deps_satisfied = all(status_by_id.get(dep_id) in _TERMINAL_STATUSES for dep_id in task.dependencies)

        if deps_satisfied:
            ready.append(task)

    return ready


# =============================================================================
# GitHub Task Fetching
# =============================================================================


def _load_tasks_from_cache(cache_path: Path) -> list[Task] | None:
    """Read cached GitHub task data and return as Task objects.

    Returns ``None`` when the cache file is absent or malformed (JSON decode
    error or missing required keys). Per-entry errors are logged and skipped.

    Args:
        cache_path: Path to the JSON cache file written by ``fetch_tasks_from_github``.

    Returns:
        List of Task objects from cache, or ``None`` on read/parse failure.
    """
    if not cache_path.exists():
        return None
    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
        raw_tasks = cache_data.get("tasks", [])
        cached: list[Task] = []
        for raw in raw_tasks:
            try:
                task_status = _parse_yaml_status(str(raw.get("status", "not-started")))
                raw_priority = raw.get("priority", 2)
                task_priority = TaskPriority(int(raw_priority)) if raw_priority is not None else TaskPriority.MEDIUM
                cached.append(
                    Task(
                        id=str(raw["task_id"]),
                        name=str(raw.get("task_id", "")),
                        status=task_status,
                        dependencies=[str(d) for d in raw.get("dependencies", [])],
                        agent=raw.get("agent") or None,
                        priority=task_priority,
                        complexity="Medium",
                        started=None,
                        completed=None,
                        skills=[str(s) for s in raw.get("skills", [])],
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                sys.stderr.write(f"WARNING: Skipping malformed cache task entry: {exc}\n")
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        sys.stderr.write(f"WARNING: Cache file malformed or unreadable ({exc}). Cannot use cache.\n")
        return None
    else:
        return cached


def fetch_tasks_from_github(parent_issue_number: int, feature_slug: str, cache_path: Path) -> list[Task] | None:
    """Fetch sub-issues from GitHub and return as Task objects for get_ready_tasks().

    Imports backlog_core conditionally — only called when ``--github`` flag is set
    and ``_BACKLOG_CORE`` exists. Falls back to reading ``cache_path`` when GitHub
    is unavailable. Returns ``None`` when both GitHub and cache are unavailable.

    Args:
        parent_issue_number: GitHub issue number for the parent story.
        feature_slug: Feature slug used as cache key.
        cache_path: Path to the JSON cache file for offline fallback.

    Returns:
        List of Task objects built from GitHub sub-issues, or ``None`` when
        GitHub is unavailable and no valid cache exists.
    """
    if not _BACKLOG_CORE.exists():
        sys.stderr.write("WARNING: backlog_core not found — cannot fetch from GitHub. Falling back to local files.\n")
        return None

    import backlog_core.github as _gh  # noqa: PLC0415
    import backlog_core.parsing as _parsing  # noqa: PLC0415

    repo = _gh.try_get_github()
    if repo is None:
        # GitHub unavailable — try cache
        cached = _load_tasks_from_cache(cache_path)
        if cached is None:
            sys.stderr.write("WARNING: GitHub unavailable and no cache found. Cannot fetch tasks.\n")
        return cached

    sub_issues = _gh.get_task_issues(repo, parent_issue_number)
    tasks = []
    for si in sub_issues:
        try:
            # si.body is reliable: SubIssue extends Issue directly in PyGitHub
            # (class SubIssue(Issue) in github/Issue.py). Issue.body calls
            # _completeIfNotSet(self._body), which lazy-fetches the full issue
            # body via the GitHub REST API on first access if not already
            # populated. No roundtrip via repo.get_issue(si.number).body is
            # needed — that would double the API calls unnecessarily.
            # SOURCE: .venv/lib/python3.11/site-packages/github/Issue.py
            # lines 822-861 and 196-198, verified 2026-03-07.
            body = si.body or ""
            sam = _parsing.parse_sam_task_metadata(body)
            if sam is None:
                continue
            try:
                task_priority = TaskPriority(int(sam.priority))
            except (ValueError, TypeError):
                task_priority = TaskPriority.MEDIUM
            task_status = _parse_yaml_status(sam.status)
            tasks.append(
                Task(
                    id=sam.task_id,
                    name=sam.task_id,
                    status=task_status,
                    dependencies=list(sam.dependencies),
                    agent=sam.agent or None,
                    priority=task_priority,
                    complexity="Medium",
                    started=None,
                    completed=None,
                    skills=list(sam.skills),
                )
            )
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"WARNING: Skipping sub-issue due to error: {exc}\n")

    # Write cache for offline fallback
    now_iso = datetime.now(tz=UTC).isoformat()
    cache_payload = {
        "feature_slug": feature_slug,
        "parent_issue_number": parent_issue_number,
        "synced_at": now_iso,
        "tasks": [
            {
                "task_id": t.id,
                "status": _YAML_STATUS_TO_ENUM_REVERSE.get(t.status, "not-started"),
                "agent": t.agent,
                "priority": t.priority.value,
                "skills": t.skills,
                "dependencies": t.dependencies,
            }
            for t in tasks
        ],
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"WARNING: Could not write cache file: {exc}\n")

    return tasks


# =============================================================================
# sam_schema Adapters
# =============================================================================
# These adapter functions convert sam_schema.Task objects to the TaskDict
# shape expected by CLI JSON output. The key mapping is:
#   sam_schema.Task.title  ->  TaskDict["name"]   (backward compat)
#   sam_schema.Task.status ->  TaskDict["status"] (already str via use_enum_values)


def _sam_task_to_dict(task: SamTask) -> TaskDict:
    """Convert a sam_schema Task to a TaskDict for JSON output.

    Preserves the ``name`` key in the output dict for backward compatibility
    with existing orchestration scripts that parse ``ready_tasks[].name``.

    Args:
        task: A sam_schema.Task model instance.

    Returns:
        TaskDict with fields matching the legacy implementation_manager format.
    """
    try:
        priority_val = int(task.priority)
    except (TypeError, ValueError):
        priority_val = 3  # TaskPriority.MEDIUM default

    return TaskDict(
        id=task.id,
        name=task.title,
        status=str(task.status),
        dependencies=list(task.dependencies),
        agent=task.agent,
        priority=priority_val,
        complexity=str(task.complexity).capitalize(),
        started=task.started.isoformat() if task.started else None,
        completed=task.completed.isoformat() if task.completed else None,
        skills=list(task.skills),
    )


def _load_tasks_via_sam(task_file: Path) -> list[Task]:
    """Load tasks from a plan file via sam_schema and convert to internal Task objects.

    Uses sam_load_plan for parsing, then converts each sam_schema.Task
    to the internal Task dataclass for use by existing CLI commands.

    Args:
        task_file: Path to the task file or directory.

    Returns:
        List of internal Task dataclass objects.
    """
    result = sam_load_plan(task_file)
    tasks: list[Task] = []
    for st in result.plan.tasks:
        try:
            priority = TaskPriority(int(st.priority))
        except (TypeError, ValueError):
            priority = TaskPriority.MEDIUM
        tasks.append(
            Task(
                id=st.id,
                name=st.title,
                status=_parse_yaml_status(str(st.status)),
                dependencies=list(st.dependencies),
                agent=st.agent,
                priority=priority,
                complexity=str(st.complexity).capitalize(),
                started=st.started.isoformat() if st.started else None,
                completed=st.completed.isoformat() if st.completed else None,
                skills=list(st.skills),
            )
        )
    return tasks


# =============================================================================
# CLI Commands
# =============================================================================


ProjectPath = Annotated[
    Path,
    typer.Argument(
        help="Path to the project root directory.", exists=True, file_okay=False, dir_okay=True, resolve_path=True
    ),
]

FeatureSlug = Annotated[str, typer.Argument(help="Feature slug (e.g., 'prepare-host') or partial match.")]


@app.command(name="list-features")
def list_features(project_path: ProjectPath) -> None:
    """List all features with task files.

    Args:
        project_path: Path to the project root directory.
    """
    features = find_task_files(project_path)

    output = {"features": [f.to_dict() for f in features], "count": len(features)}

    console.print(json.dumps(output, indent=2))


@app.command(name="status")
def status(
    project_path: ProjectPath,
    feature_slug: FeatureSlug,
    github: Annotated[bool, typer.Option("--github", help="Include GitHub sub-issue state in status output.")] = False,
    parent_issue: Annotated[
        int | None, typer.Option("--parent-issue", help="Parent story issue number (required with --github).")
    ] = None,
) -> None:
    """Get detailed status for a specific feature.

    Args:
        project_path: Path to the project root directory.
        feature_slug: Feature slug or partial match.
        github: When True, query GitHub sub-issues instead of local task files.
        parent_issue: Parent story GitHub issue number (required when ``--github`` is set).
    """
    tasks: list[Task] | None = None
    task_file: Path | None = None

    if github and parent_issue is not None:
        cache_path = project_path / ".claude" / "context" / f"sam-tasks-{feature_slug}.json"
        tasks = fetch_tasks_from_github(parent_issue, feature_slug, cache_path)
        if tasks is None:
            sys.stderr.write(
                f"WARNING: GitHub fetch failed for feature '{feature_slug}'. Falling back to local files.\n"
            )

    if tasks is None:
        task_file = find_task_file_by_slug(project_path, feature_slug)
        if not task_file:
            error_output = {
                "error": f"No task file found for feature: {feature_slug}",
                "available_features": [f.slug for f in find_task_files(project_path)],
            }
            console.print(json.dumps(error_output, indent=2))
            raise typer.Exit(1)
        tasks = _load_tasks_via_sam(task_file)

    ready = get_ready_tasks(tasks)

    # Calculate statistics
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETE)
    in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    not_started = sum(1 for t in tasks if t.status == TaskStatus.NOT_STARTED)
    blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
    deferred = sum(1 for t in tasks if t.status == TaskStatus.DEFERRED)
    skipped = sum(1 for t in tasks if t.status == TaskStatus.SKIPPED)

    output = {
        "feature": feature_slug,
        "task_file": task_file.name if task_file is not None else f"github:{parent_issue}",
        "total_tasks": len(tasks),
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "blocked": blocked,
        "deferred": deferred,
        "skipped": skipped,
        "ready_tasks": [{"id": t.id, "name": t.name, "agent": t.agent} for t in ready],
        "tasks": [t.to_dict() for t in tasks],
    }

    console.print(json.dumps(output, indent=2))


@app.command(name="ready-tasks")
def ready_tasks(
    project_path: ProjectPath,
    feature_slug: FeatureSlug,
    github: Annotated[bool, typer.Option("--github", help="Query GitHub sub-issues instead of local files.")] = False,
    parent_issue: Annotated[
        int | None, typer.Option("--parent-issue", help="Parent story issue number (required with --github).")
    ] = None,
) -> None:
    """List tasks ready for execution (dependencies satisfied).

    Args:
        project_path: Path to the project root directory.
        feature_slug: Feature slug or partial match.
        github: When True, query GitHub sub-issues instead of local task files.
        parent_issue: Parent story GitHub issue number (required when ``--github`` is set).
    """
    tasks: list[Task] | None = None

    if github and parent_issue is not None:
        cache_path = project_path / ".claude" / "context" / f"sam-tasks-{feature_slug}.json"
        tasks = fetch_tasks_from_github(parent_issue, feature_slug, cache_path)
        if tasks is None:
            sys.stderr.write(
                f"WARNING: GitHub fetch failed for feature '{feature_slug}'. Falling back to local files.\n"
            )

    if tasks is None:
        task_file = find_task_file_by_slug(project_path, feature_slug)
        if not task_file:
            if github and parent_issue is not None:
                # Both GitHub and local files are unavailable
                error_output = {"error": "No task data available — GitHub unreachable and no cache found"}
                console.print(json.dumps(error_output, indent=2))
                raise typer.Exit(1)
            error_output = {
                "error": f"No task file found for feature: {feature_slug}",
                "available_features": [f.slug for f in find_task_files(project_path)],
            }
            console.print(json.dumps(error_output, indent=2))
            raise typer.Exit(1)
        tasks = _load_tasks_via_sam(task_file)

    ready = get_ready_tasks(tasks)

    output = {
        "feature": feature_slug,
        "ready_tasks": [{"id": t.id, "name": t.name, "agent": t.agent, "skills": t.skills} for t in ready],
        "count": len(ready),
    }

    console.print(json.dumps(output, indent=2))


@app.command(name="validate")
def validate(project_path: ProjectPath, feature_slug: FeatureSlug) -> None:
    """Validate task file structure via sam_schema.

    Delegates to sam_load_plan for parsing. A file that loads without error
    passes structural validation. Reports dependency and duplicate-ID errors.

    Args:
        project_path: Path to the project root directory.
        feature_slug: Feature slug or partial match.
    """
    task_file = find_task_file_by_slug(project_path, feature_slug)

    if not task_file:
        error_output = {
            "error": f"No task file found for feature: {feature_slug}",
            "available_features": [f.slug for f in find_task_files(project_path)],
        }
        console.print(json.dumps(error_output, indent=2))
        raise typer.Exit(1)

    try:
        tasks = _load_tasks_via_sam(task_file)
    except Exception as exc:
        output = {"valid": False, "errors": [str(exc)], "warnings": [], "task_count": 0}
        console.print(json.dumps(output, indent=2))
        raise typer.Exit(1) from exc

    errors: list[str] = []
    warnings: list[str] = []

    # Validate each task
    task_ids = {t.id for t in tasks}
    for task in tasks:
        # Check for missing agent field
        if not task.agent:
            warnings.append(f"Task {task.id} missing Agent field")

        # Validate dependencies exist
        errors.extend(
            f"Task {task.id} has unknown dependency: Task {dep_id}"
            for dep_id in task.dependencies
            if dep_id not in task_ids
        )

    # Check for duplicate task IDs
    seen: set[str] = set()
    for task_id in (t.id for t in tasks):
        if task_id in seen:
            errors.append(f"Duplicate task ID: {task_id}")
        seen.add(task_id)

    output = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "task_count": len(tasks)}

    console.print(json.dumps(output, indent=2))

    if errors:
        raise typer.Exit(1)


def _claim_fail(payload: dict[str, object], exc: BaseException | None = None) -> None:
    """Emit JSON error to stdout and stderr then exit 1.

    Args:
        payload: Dict to serialize as JSON.
        exc: Optional chained exception for ``raise ... from``.
    """
    msg = json.dumps(payload)
    print(msg)
    sys.stderr.write(msg + "\n")
    raise typer.Exit(1) from exc


@app.command(name="claim-task")
def claim_task(
    task_file_path: Annotated[
        Path, typer.Argument(help="Path to the task file or directory.", exists=True, resolve_path=True)
    ],
    task_id: Annotated[str, typer.Argument(help="Task ID to claim (e.g., T1, 1.1).")],
) -> None:
    """Claim a task by atomically transitioning it from not-started to in-progress.

    Delegates to sam_schema.core.query.claim_task for the atomic read-check-write.
    Exits 0 with JSON output on success. Exits 1 with ``claimed: false`` JSON
    when the task is not found, already claimed, or the file cannot be written.

    Args:
        task_file_path: Path to the task file (``.md`` or ``.yaml``) or task directory.
        task_id: Task identifier to claim (e.g., ``T1``, ``1.1``).
    """
    task_file_str = str(task_file_path)

    try:
        claimed_task = sam_claim_task(task_file_path, task_id)
    except KeyError:
        _claim_fail({"claimed": False, "task_id": task_id, "reason": "task-not-found", "task_file": task_file_str})
        return  # unreachable; satisfies type checker
    except ValueError as exc:
        # sam_claim_task raises ValueError when task is not in not-started status.
        # Extract the current status from the error message if possible.
        current_status_str = _normalize_status(str(exc).split("'")[-2]) if "'" in str(exc) else "in-progress"
        _claim_fail(
            {
                "claimed": False,
                "task_id": task_id,
                "reason": f"already-{current_status_str}",
                "current_status": current_status_str,
                "task_file": task_file_str,
            },
            exc,
        )
        return  # unreachable; satisfies type checker
    except OSError as exc:
        _claim_fail({"claimed": False, "reason": "write-error", "error": str(exc), "task_file": task_file_str}, exc)
        return  # unreachable; satisfies type checker

    started_str = (
        claimed_task.started.isoformat()
        if claimed_task.started
        else datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    print(json.dumps({"claimed": True, "task_id": task_id, "started": started_str, "task_file": task_file_str}))
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
