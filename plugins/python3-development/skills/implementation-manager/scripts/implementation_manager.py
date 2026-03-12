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
from typing import Annotated, TypedDict

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

from task_format import (
    VALID_STATUSES,
    has_yaml_frontmatter,
    normalize_status,
    parse_yaml_frontmatter,
    resolve_task_id,
    update_yaml_field,
)

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
    normalized = normalize_status(status_stripped)
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


# =============================================================================
# YAML Frontmatter Parsing
# =============================================================================


def _parse_yaml_status(raw_status: str) -> TaskStatus:
    """Convert a YAML frontmatter status string to TaskStatus enum.

    Args:
        raw_status: Status value from YAML frontmatter (e.g., "not-started").

    Returns:
        Corresponding TaskStatus enum member.
    """
    normalized = normalize_status(raw_status)
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


def parse_task_from_frontmatter(content: str) -> Task:
    """Parse a single task from YAML frontmatter content.

    Extracts metadata from the YAML frontmatter block and maps fields
    to a Task dataclass. Falls back to defaults for missing optional fields.

    Field mapping (YAML field -> Task attribute):
    - task -> id
    - title -> name
    - status -> status (via normalize_status)
    - agent -> agent
    - dependencies -> dependencies
    - priority -> priority
    - complexity -> complexity
    - started -> started
    - completed -> completed
    - skills -> skills (optional; defaults to [])

    Args:
        content: File content with YAML frontmatter delimiters.

    Returns:
        Task object populated from frontmatter metadata.

    Raises:
        ValueError: If frontmatter is missing required fields (task, title, status).
    """
    frontmatter, _body = parse_yaml_frontmatter(content)

    # Normalize task_id -> task for backward compatibility
    if "task_id" in frontmatter and "task" not in frontmatter:
        frontmatter["task"] = frontmatter["task_id"]

    # Validate required fields
    missing = [f for f in ("task", "title", "status") if f not in frontmatter]
    if missing:
        msg = f"Missing required YAML frontmatter fields: {', '.join(missing)}"
        raise ValueError(msg)

    task_id = str(frontmatter["task"])
    title = str(frontmatter["title"])
    status = _status_from_title(title, _parse_yaml_status(str(frontmatter["status"])))
    dependencies = _parse_yaml_dependencies(frontmatter.get("dependencies"))
    agent = frontmatter.get("agent")
    if agent is not None:
        agent = str(agent)
        if agent.lower() in {"none", "n/a", "-", ""}:
            agent = None

    raw_priority = frontmatter.get("priority")
    priority = TaskPriority(int(raw_priority)) if raw_priority is not None else TaskPriority.MEDIUM
    complexity = str(frontmatter.get("complexity", "medium")).capitalize()

    started = _coerce_timestamp(frontmatter.get("started"))
    completed = _coerce_timestamp(frontmatter.get("completed"))
    skills = _parse_yaml_skills(frontmatter.get("skills"))

    return Task(
        id=task_id,
        name=title,
        status=status,
        dependencies=dependencies,
        agent=agent,
        priority=priority,
        complexity=complexity,
        started=started,
        completed=completed,
        skills=skills,
    )


# =============================================================================
# Task Parsing
# =============================================================================


def parse_task_content(content: str) -> list[Task]:
    """Parse task content and extract all tasks.

    Handles two YAML frontmatter formats:
    - **Single-task**: One ``---`` frontmatter block with ``task:`` and ``status:`` fields.
    - **Multi-task**: A global manifest block (has ``feature:``, lacks ``task:``/``status:``)
      followed by embedded per-task frontmatter blocks in the body.

    Returns an empty list if frontmatter is absent or parsing fails.

    Args:
        content: Raw text content of task file.

    Returns:
        List of Task objects parsed from the content.
    """
    if not has_yaml_frontmatter(content):
        return []

    try:
        frontmatter, body = parse_yaml_frontmatter(content)
    except (ValueError, TypeError) as exc:
        sys.stderr.write(f"WARNING: YAML frontmatter parsing failed: {exc}\n")
        return []

    # Detect multi-task file: global manifest block has 'feature:' or 'feature_slug:' but not a task identifier.
    # Support both 'task:' and 'task_id:' as task identifier fields.
    has_feature = "feature" in frontmatter or "feature_slug" in frontmatter
    if has_feature and "task" not in frontmatter and "task_id" not in frontmatter:
        return _parse_multi_task_body(body)

    # Single-task file: the leading frontmatter IS the task
    try:
        task = parse_task_from_frontmatter(content)
    except (ValueError, TypeError) as exc:
        sys.stderr.write(f"WARNING: YAML frontmatter parsing failed: {exc}\n")
        return []
    return [task]


def _parse_multi_task_body(body: str) -> list[Task]:
    r"""Parse embedded task blocks from body content after a global manifest.

    Splits body on ``\\n---\\n`` boundaries to isolate each YAML block.
    Only segments containing both ``task:`` and ``status:`` field markers
    are parsed as tasks; all other segments (markdown prose, HTML comments)
    are silently skipped.

    Args:
        body: Content after the global manifest's closing ``---`` delimiter.

    Returns:
        List of Task objects sorted by natural task ID order.
    """
    tasks: list[Task] = []
    for segment in re.split(r"\n---\n", body):
        has_task_field = "task:" in segment or "task_id:" in segment
        if not has_task_field or "status:" not in segment:
            continue
        try:
            task = parse_task_from_frontmatter(f"---\n{segment}\n---\n")
            tasks.append(task)
        except (ValueError, TypeError):
            continue
    tasks.sort(key=_task_sort_key)
    return tasks


def parse_task_file(file_path: Path) -> list[Task]:
    """Parse a task file or task directory and extract all tasks.

    Handles both single files and directories:
    - **File**: Reads content and delegates to parse_task_content.
    - **Directory**: Discovers all ``.md`` files with YAML frontmatter,
      parses each as a single task.

    Follows DIP by separating file I/O from parsing logic.

    Args:
        file_path: Path to the task file or task directory.

    Returns:
        List of Task objects parsed from the file(s).

    Raises:
        FileNotFoundError: If the task file does not exist.
    """
    if file_path.is_dir():
        return _parse_task_directory(file_path)

    content = file_path.read_text(encoding="utf-8")
    return parse_task_content(content)


def _parse_task_directory(dir_path: Path) -> list[Task]:
    """Parse all task files in a directory.

    Each ``.md`` file in the directory is expected to contain a single task
    with YAML frontmatter. Files without YAML frontmatter are skipped.

    Tasks are sorted by ID using natural sort order (T1, T2, T10, not T1, T10, T2).

    Args:
        dir_path: Path to directory containing individual task files.

    Returns:
        List of Task objects from all parseable files in the directory.
    """
    tasks: list[Task] = []

    for md_file in sorted(dir_path.glob("*.md")):
        if not md_file.is_file():
            continue
        content = md_file.read_text(encoding="utf-8")
        parsed = parse_task_content(content)
        tasks.extend(parsed)

    # Sort tasks by ID using natural sort (numeric part extraction)
    tasks.sort(key=_task_sort_key)
    return tasks


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
        tasks = parse_task_file(task_file)

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
        tasks = parse_task_file(task_file)

    ready = get_ready_tasks(tasks)

    output = {
        "feature": feature_slug,
        "ready_tasks": [{"id": t.id, "name": t.name, "agent": t.agent, "skills": t.skills} for t in ready],
        "count": len(ready),
    }

    console.print(json.dumps(output, indent=2))


@app.command(name="validate")
def validate(project_path: ProjectPath, feature_slug: FeatureSlug) -> None:
    """Validate task file frontmatter and structure.

    Supports both YAML frontmatter and legacy markdown formats.
    Validates required fields, dependency references, and duplicate IDs.

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

    tasks = parse_task_file(task_file)
    errors: list[str] = []
    warnings: list[str] = []

    # Validate each task
    task_ids = {t.id for t in tasks}
    for task in tasks:
        # Check for missing agent field
        if not task.agent:
            warnings.append(f"Task {task.id} missing Agent field")

        # Validate status is a recognized value
        normalized = normalize_status(task.status.value)
        if normalized not in VALID_STATUSES:
            warnings.append(f"Task {task.id} has non-standard status: {task.status.value}")

        # Priority validation happens at parse time via TaskPriority enum constructor

        # Validate dependencies exist
        errors.extend(
            f"Task {task.id} has unknown dependency: Task {dep_id}"
            for dep_id in task.dependencies
            if dep_id not in task_ids
        )

    # Check for duplicate task IDs
    task_ids_list = [t.id for t in tasks]
    seen: set[str] = set()
    for task_id in task_ids_list:
        if task_id in seen:
            errors.append(f"Duplicate task ID: {task_id}")
        seen.add(task_id)

    output = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "task_count": len(tasks)}

    console.print(json.dumps(output, indent=2))

    if errors:
        raise typer.Exit(1)


def _find_task_section_in_file(content: str, task_id: str) -> tuple[int, int] | None:
    r"""Locate the byte offsets of the frontmatter block for a given task_id.

    Splits content on ``\\n---\\n`` boundaries and searches each candidate
    section for a frontmatter block that contains ``task: {task_id}``.

    Args:
        content: Full file content, potentially containing multiple frontmatter blocks.
        task_id: Task ID to find (e.g., "T1", "1.1").

    Returns:
        Tuple of (start, end) character offsets for the entire section
        (including its ``---\\n`` prefix and ``\\n---\\n`` suffix), or None
        if no matching section is found.
    """
    # Split on "\n---\n" to get candidate sections.
    # The file starts with "---\n" so parts[0] is empty.
    separator = "\n---\n"
    parts = content.split(separator)

    # Reconstruct offsets for each part.
    offset = 0
    for part in parts:
        # The part content is everything between separators.
        # Reconstruct what the original slice looks like.
        part_start = offset
        part_end = offset + len(part)

        # Only consider sections that look like standalone YAML blocks
        # (i.e., start with a key: value line, not a comment or blank line).
        stripped = part.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
            # If the part already starts with "---" it is a self-contained
            # frontmatter block (first section of a standard single-frontmatter
            # file).  Wrap only parts that lack their own opening delimiter.
            if part.startswith(("---\n", "---\r\n")):
                candidate_content = part if part.endswith("\n---\n") else f"{part}\n---\n"
            else:
                candidate_content = f"---\n{part}\n---\n"
            if has_yaml_frontmatter(candidate_content):
                try:
                    fm, _ = parse_yaml_frontmatter(candidate_content)
                    if resolve_task_id(fm) == task_id:
                        return (part_start, part_end)
                except (ValueError, TypeError):
                    pass

        # Advance offset past this part + the separator.
        offset = part_end + len(separator)

    return None


def _resolve_write_target(task_file_path: Path, task_id: str) -> tuple[Path, str] | None:
    """Resolve the write target file and its content for a given task_id.

    For directory-based task files, locates the individual ``.md`` file
    containing the task. For single-file task files with multiple frontmatter
    blocks, returns the single file.

    Args:
        task_file_path: Path to the task file or directory.
        task_id: Task ID to locate.

    Returns:
        Tuple of (write_target_path, file_content) if the task is found,
        or None if no file containing the task is found.
    """
    if task_file_path.is_dir():
        # Directory: scan individual .md files for the matching task.
        for md_file in sorted(task_file_path.glob("*.md")):
            if not md_file.is_file():
                continue
            file_content = md_file.read_text(encoding="utf-8")
            parsed = parse_task_content(file_content)
            for task in parsed:
                if task.id == task_id:
                    return (md_file, file_content)
        return None

    # Single file: read once, locate the section containing task_id.
    file_content = task_file_path.read_text(encoding="utf-8")
    return (task_file_path, file_content)


def _try_claim_part(part: str, task_id: str, timestamp: str) -> str | None:
    r"""Try to claim task_id in a single frontmatter part.

    Args:
        part: One section split from the file on ``\\n---\\n``.
        task_id: Task ID to match.
        timestamp: UTC ISO 8601 timestamp for the ``started`` field.

    Returns:
        Updated part string if task_id matched, else None.
    """
    if part.startswith(("---\n", "---\r\n")):
        candidate = part if part.endswith("\n---\n") else f"{part}\n---\n"
        prefix_len = 0
    else:
        candidate = f"---\n{part}\n---\n"
        prefix_len = len("---\n")
    if not has_yaml_frontmatter(candidate):
        return None
    try:
        fm, _ = parse_yaml_frontmatter(candidate)
    except (ValueError, TypeError):
        return None
    if resolve_task_id(fm) != task_id:
        return None
    updated = update_yaml_field(candidate, "status", "in-progress")
    if fm.get("started") is None:
        updated = update_yaml_field(updated, "started", timestamp)
    return updated[prefix_len : -len("\n---\n")]


def _apply_claim_to_content(content: str, task_id: str, timestamp: str) -> str | None:
    """Apply status and started fields to the section matching task_id.

    For a single-task file (one frontmatter block), updates the block in place.
    For a multi-task file (multiple frontmatter blocks), locates and updates
    only the block matching task_id.

    Args:
        content: Full file content.
        task_id: Task ID whose frontmatter should be updated.
        timestamp: UTC ISO 8601 timestamp for the ``started`` field.

    Returns:
        Updated file content string, or None if task_id was not found.
    """
    separator = "\n---\n"
    parts = content.split(separator)
    updated_parts: list[str] = []
    found = False

    for part in parts:
        stripped = part.strip()
        if not found and stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
            claimed = _try_claim_part(part, task_id, timestamp)
            if claimed is not None:
                updated_parts.append(claimed)
                found = True
                continue
        updated_parts.append(part)

    if not found:
        return None

    return separator.join(updated_parts)


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


def _resolve_task_status(file_content: str, task_id: str, task_file_str: str) -> Task:
    """Parse the task matching task_id and return it, or exit 1.

    Args:
        file_content: Full text of the task file.
        task_id: Task ID to locate.
        task_file_str: File path string for error payloads.

    Returns:
        Matching Task object with ``status`` populated.
    """
    try:
        tasks = parse_task_content(file_content)
        if not tasks:
            section_result = _find_task_section_in_file(file_content, task_id)
            if section_result is None:
                _claim_fail({
                    "claimed": False,
                    "task_id": task_id,
                    "reason": "task-not-found",
                    "task_file": task_file_str,
                })
            start_idx, end_idx = section_result  # type: ignore[misc]
            tasks = parse_task_content(f"---\n{file_content[start_idx:end_idx]}\n---\n")
        matching_task = next((t for t in tasks if t.id == task_id), None)
    except (ValueError, TypeError) as exc:
        _claim_fail(
            {
                "claimed": False,
                "task_id": task_id,
                "reason": "parse-error",
                "error": str(exc),
                "task_file": task_file_str,
            },
            exc,
        )
        return None  # type: ignore[return-value]  # unreachable

    if matching_task is None:
        _claim_fail({"claimed": False, "task_id": task_id, "reason": "task-not-found", "task_file": task_file_str})
    return matching_task  # type: ignore[return-value]


@app.command(name="claim-task")
def claim_task(
    task_file_path: Annotated[
        Path, typer.Argument(help="Path to the task file or directory.", exists=True, resolve_path=True)
    ],
    task_id: Annotated[str, typer.Argument(help="Task ID to claim (e.g., T1, 1.1).")],
) -> None:
    """Claim a task by atomically transitioning it from not-started to in-progress.

    Performs a read-check-write sequence: reads the task file, verifies the
    task status is ``not-started``, writes ``status: in-progress`` and
    ``started: <timestamp>``, then exits 0 with JSON output on success.

    Exits 1 with ``claimed: false`` JSON when the task is not found, already
    claimed, or the file cannot be parsed or written.

    Args:
        task_file_path: Path to the task file (``.md``) or task directory.
        task_id: Task identifier to claim (e.g., ``T1``, ``1.1``).
    """
    task_file_str = str(task_file_path)
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    resolved = _resolve_write_target(task_file_path, task_id)
    if resolved is None:
        _claim_fail({"claimed": False, "task_id": task_id, "reason": "task-not-found", "task_file": task_file_str})

    write_target, file_content = resolved  # type: ignore[misc]
    matching_task = _resolve_task_status(file_content, task_id, task_file_str)

    if matching_task.status != TaskStatus.NOT_STARTED:
        current_status_str = normalize_status(matching_task.status.value)
        _claim_fail({
            "claimed": False,
            "task_id": task_id,
            "reason": f"already-{current_status_str}",
            "current_status": current_status_str,
            "task_file": task_file_str,
        })

    updated_content = _apply_claim_to_content(file_content, task_id, timestamp)
    if updated_content is None:
        _claim_fail({"claimed": False, "task_id": task_id, "reason": "task-not-found", "task_file": task_file_str})

    try:
        write_target.write_text(updated_content, encoding="utf-8")  # type: ignore[union-attr]
    except OSError as exc:
        _claim_fail({"claimed": False, "reason": "write-error", "error": str(exc), "task_file": task_file_str}, exc)

    print(json.dumps({"claimed": True, "task_id": task_id, "started": timestamp, "task_file": task_file_str}))
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
