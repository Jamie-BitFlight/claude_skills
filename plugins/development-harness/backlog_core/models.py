"""Constants, regex patterns, type maps, Pydantic models, and exceptions for the backlog MCP package.

This module is standalone — it has no imports from other mcp submodules.
All models use Pydantic BaseModel for natural integration with FastMCP 3.x.
"""

from __future__ import annotations

import functools
import os
import re
import sys
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict

import git
from pydantic import AliasChoices, BaseModel, Field
from typing_extensions import TypedDict as ExtTypedDict

# ---------------------------------------------------------------------------
# Path constants — via dh_paths
# ---------------------------------------------------------------------------

# Add plugin root to sys.path so dh_paths can be imported from sibling module.
_plugin_root = Path(__file__).parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import dh_paths as _dh_paths


def _resolve_repo_root(project_dir: str | None = None) -> Path:
    """Return the repository root path.

    Args:
        project_dir: Explicit project directory path, typically passed via
            ``--project-dir`` CLI argument when the server is installed as a
            plugin (where ``__file__`` points to the plugin cache, not the
            user's project).  When ``None``, uses :func:`dh_paths.git_project_root`.

    Returns:
        Resolved Path to the repository root.
    """
    if project_dir:
        return Path(project_dir).resolve()
    return _dh_paths.git_project_root()


_REPO_ROOT = _resolve_repo_root()
BACKLOG_DIR: Path = _dh_paths.backlog_dir(_REPO_ROOT)


def get_repo_root() -> Path:
    """Return the current project (git) root.

    Returns:
        Absolute path to the repository root.  Updated when :func:`init` is
        called with a ``project_dir`` argument.
    """
    return _REPO_ROOT


def init(project_dir: str | None = None, repo: str | None = None) -> None:
    """Re-initialise module-level path and repository constants.

    Call this once at server startup (before any tool runs) when the server is
    launched with ``--project-dir`` or a known ``repo`` slug.  Mutates module
    globals ``_REPO_ROOT``, ``BACKLOG_DIR``, and ``DEFAULT_REPO`` in-place.

    Path resolution now delegates to :mod:`dh_paths` so that ``BACKLOG_DIR``
    points to ``~/.dh/projects/{slug}/backlog/``.

    Args:
        project_dir: Absolute path to the user's project root, forwarded from
            the ``--project-dir`` CLI argument in ``server.py``.
        repo: Explicit ``owner/repo`` slug override.  When ``None``, calls
            :func:`discover_repo` to resolve the slug dynamically.
    """
    global _REPO_ROOT, BACKLOG_DIR, DEFAULT_REPO  # noqa: PLW0603
    _REPO_ROOT = _resolve_repo_root(project_dir)
    BACKLOG_DIR = _dh_paths.backlog_dir(_REPO_ROOT)
    if repo is not None:
        DEFAULT_REPO = _validate_repo_slug(repo)
    else:
        discover_repo.cache_clear()
        DEFAULT_REPO = discover_repo()


# ---------------------------------------------------------------------------
# Repository discovery
# ---------------------------------------------------------------------------

#: Matches the canonical ``owner/repo`` slug format.
_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

#: SSH SCP remote pattern: ``git@github.com:owner/repo.git``
_SSH_REMOTE_RE = re.compile(r"git@[^:]+:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$")

#: HTTPS / proxy remote pattern: ``https://…/owner/repo[.git]``
_HTTPS_REMOTE_RE = re.compile(r"https?://[^/]+/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$")

#: SSH protocol remote pattern: ``ssh://git@github.com/owner/repo.git``
_SSH_PROTO_REMOTE_RE = re.compile(r"ssh://[^/]+/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$")

#: Proxy remote pattern: ``http://local_proxy@127.0.0.1:{port}/git/{owner}/{repo}``
#: Matches any host/port proxy URL with a ``/git/`` path prefix.
_PROXY_REMOTE_RE = re.compile(r".*/git/([^/]+/[^/]+?)(?:\.git)?/?$")


class RepoDiscoveryError(Exception):
    """Raised when all repository discovery methods fail.

    Attributes:
        methods_tried: Names of the discovery methods attempted in order.
        message: User-facing actionable error message.
    """

    def __init__(self, methods_tried: list[str], details: list[str]) -> None:
        """Initialise with discovery context.

        Args:
            methods_tried: Method names tried in order.
            details: Per-method failure descriptions.
        """
        self.methods_tried = methods_tried
        detail_lines = "\n".join(f"  {i + 1}. {d}" for i, d in enumerate(details))
        message = (
            "Could not determine the GitHub repository.\n\n"
            f"Tried:\n{detail_lines}\n\n"
            "To fix, either:\n"
            "  - Set GITHUB_REPO=owner/repo in your environment\n"
            "  - Ensure you are in a git repository with a GitHub remote"
        )
        self.message = message
        super().__init__(message)


def _validate_repo_slug(slug: str) -> str:
    """Validate that *slug* matches ``owner/repo`` format.

    Args:
        slug: Candidate repository slug to validate.

    Returns:
        The validated slug, unchanged.

    Raises:
        RepoDiscoveryError: When the slug does not match the expected format.
    """
    if not _REPO_SLUG_RE.match(slug):
        raise RepoDiscoveryError(
            methods_tried=["validate"], details=[f"Slug '{slug}' does not match owner/repo format"]
        )
    return slug


def _discover_via_env() -> str | None:
    """Return the ``GITHUB_REPO`` environment variable value if set and valid.

    Returns:
        Validated ``owner/repo`` slug, or ``None`` when the variable is absent
        or empty.
    """
    value = os.environ.get("GITHUB_REPO", "").strip()
    if not value:
        return None
    return _validate_repo_slug(value)


def _discover_via_git() -> str | None:
    """Parse the ``origin`` remote URL via GitPython to extract ``owner/repo``.

    Opens :class:`git.Repo` at :data:`_REPO_ROOT` (resolved project root from
    :func:`dh_paths.infer_project_root`, ``DH_PROJECT_ROOT``, etc.), with
    ``search_parent_directories=True`` so a subdirectory of a worktree still
    resolves.  Does **not** use the process cwd — MCP stdio servers often
    start with cwd outside the user's repository (plugin cache, ``/``, IDE).

    Returns:
        Validated ``owner/repo`` slug, or ``None`` when no git repository is
        found, there is no ``origin`` remote, or the URL cannot be parsed.
    """
    try:
        repo = git.Repo(_REPO_ROOT, search_parent_directories=True)
        url = repo.remote().url
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
        return None
    for pattern in (_SSH_REMOTE_RE, _HTTPS_REMOTE_RE, _SSH_PROTO_REMOTE_RE, _PROXY_REMOTE_RE):
        match = pattern.match(url)
        if match:
            slug = match.group(1)
            if _REPO_SLUG_RE.match(slug):
                return slug
    return None


@functools.lru_cache(maxsize=1)
def discover_repo() -> str:
    """Discover the current repository's ``owner/repo`` slug.

    Resolution priority chain (first success wins):

    1. ``GITHUB_REPO`` environment variable — explicit override, highest priority.
    2. GitPython remote URL parsing — reads the ``origin`` remote URL from the
       git repository and parses owner/repo using regex patterns for SSH SCP,
       SSH protocol, and HTTPS URL formats.
    3. :class:`RepoDiscoveryError` — all methods exhausted, no fallback.

    The result is cached with :func:`functools.lru_cache` so discovery runs at
    most once per process.  Call ``discover_repo.cache_clear()`` in tests to
    reset between runs.

    Returns:
        Repository slug in ``owner/repo`` format.

    Raises:
        RepoDiscoveryError: When no discovery method succeeds.
    """
    methods_tried: list[str] = []
    details: list[str] = []

    # 1. Environment variable
    methods_tried.append("GITHUB_REPO environment variable")
    slug = _discover_via_env()
    if slug is not None:
        return slug
    details.append("GITHUB_REPO environment variable: not set or empty")

    # 2. GitPython remote URL parsing
    methods_tried.append("Git remote (origin) via GitPython")
    slug = _discover_via_git()
    if slug is not None:
        return slug
    details.append("Git remote (origin): no git repository found or URL could not be parsed")

    raise RepoDiscoveryError(methods_tried=methods_tried, details=details)


#: Populated at server startup by :func:`init`. Not set at import time to avoid
#: triggering git I/O during module import. Call :func:`discover_repo` directly
#: when a default is needed before ``init()`` has run.
DEFAULT_REPO: str = ""

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"^##\s+(P0|P1|P2|Ideas)")
GITHUB_ISSUE_URL_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)")
COMMIT_PREFIX_RE = re.compile(r"^(feat|fix|refactor|docs|chore|perf|test|ci):\s*", re.IGNORECASE)
_COMMIT_PREFIX_RE = COMMIT_PREFIX_RE  # backwards-compat alias; import COMMIT_PREFIX_RE in new code

# ---------------------------------------------------------------------------
# Scalar constants
# ---------------------------------------------------------------------------

SKIP_STATUS = ("DONE", "RESOLVED", "COMPLETED", "CLOSED")

VALID_CLOSE_REASONS = ("duplicate", "out_of_scope", "superseded", "wontfix", "blocked")
GITHUB_ISSUE_TITLE_TRUNCATE = 80
MIN_FRONTMATTER_PARTS = 3
FUZZY_DUPLICATE_THRESHOLD = 0.80

# ---------------------------------------------------------------------------
# Dict mappings
# ---------------------------------------------------------------------------

TYPE_TO_LABEL: dict[str, str] = {
    "feature": "type:feature",
    "bug": "type:bug",
    "refactor": "type:refactor",
    "docs": "type:docs",
    "chore": "type:chore",
}

ROLE_MAP: dict[str, str] = {
    "Feature": "developer using Claude Code skills",
    "Bug": "developer relying on this plugin",
    "Refactor": "maintainer of the codebase",
    "Docs": "developer reading the documentation",
    "Chore": "maintainer of the project infrastructure",
}

BENEFIT_MAP: dict[str, str] = {
    "Feature": "the tooling becomes more capable and complete",
    "Bug": "the tool works correctly and reliably",
    "Refactor": "the code is cleaner and more maintainable",
    "Docs": "documentation is accurate and trustworthy",
    "Chore": "the project infrastructure stays healthy",
}

FIELD_TO_INDEX: dict[str, int] = {
    "description": 0,
    "suggested location": 1,
    "research first": 2,
    "decision needed": 3,
    "files": 4,
    "required work": 5,
}

PRIORITY_SECTIONS: dict[str, str] = {
    "P0": "## P0 - Must Have",
    "P1": "## P1 - Should Have",
    "P2": "## P2 - Could Have",
    "Idea": "## Ideas",
    "Ideas": "## Ideas",
}

# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class BacklogError(Exception):
    """General backlog operation error."""


class ItemNotFoundError(BacklogError):
    """Raised when a backlog item cannot be found by the given selector."""

    def __init__(self, selector: str) -> None:
        """Initialize with the selector that failed to match."""
        self.selector = selector
        super().__init__(f"No item found for: {selector}")


class DuplicateItemError(BacklogError):
    """Raised when a fuzzy duplicate is detected during item creation."""

    def __init__(self, duplicates: list[tuple[str, float, str]]) -> None:
        """Initialize with list of (title, similarity_ratio, file_path) tuples."""
        self.duplicates = duplicates
        titles = ", ".join(f'"{t}" ({int(r * 100)}%)' for t, r, _ in duplicates)
        super().__init__(f"Similar backlog items found: {titles}")


class GitHubUnavailableError(BacklogError):
    """Raised when GITHUB_TOKEN is missing or the GitHub API is unreachable."""


class ValidationError(BacklogError):
    """Raised on input validation failure."""


class BranchConflictError(BacklogError):
    """Raised when a merge fails due to conflicts.

    Attributes:
        head_branch: Source branch that was being merged.
        base_branch: Target branch that was being merged into.
        conflict_files: List of file paths with conflicts (when available from API).
    """

    head_branch: str
    base_branch: str
    conflict_files: list[str]

    def __init__(self, head_branch: str, base_branch: str, conflict_files: list[str] | None = None) -> None:
        """Initialize with merge conflict details.

        Args:
            head_branch: Source branch being merged.
            base_branch: Target branch being merged into.
            conflict_files: File paths with conflicts. Defaults to empty list.
        """
        self.head_branch = head_branch
        self.base_branch = base_branch
        self.conflict_files = conflict_files or []
        files_str = ", ".join(self.conflict_files[:5]) if self.conflict_files else "unknown"
        super().__init__(f"Merge conflict: {head_branch} -> {base_branch} (files: {files_str})")


# ---------------------------------------------------------------------------
# Branch TypedDicts
# ---------------------------------------------------------------------------


class BranchInfo(TypedDict):
    """Information about a Git branch."""

    name: str
    """Full branch name (e.g. ``milestone/3-v1.1-milestone-workflow``)."""

    sha: str
    """HEAD commit SHA."""

    last_commit_date: str
    """ISO 8601 timestamp of the last commit (e.g. ``2026-03-20T14:30:00Z``)."""

    age_days: int
    """Number of days since the last commit. Computed at query time."""


class MergeResult(TypedDict):
    """Result of a successful merge operation."""

    sha: str
    """New HEAD SHA of the base branch after merge."""

    message: str
    """Commit message used for the merge."""


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Entry(BaseModel):
    """A single timestamped content block within a backlog item section."""

    id: str = ""
    content: str = ""
    struck: bool = False
    struck_reason: str = ""
    struck_at: str = ""
    raw: str = ""


class BacklogItem(BaseModel):
    """Parsed backlog item from a per-item file.

    Replaces the untyped ``dict`` that was previously passed between functions.
    All fields default to empty/falsy values so items can be constructed
    incrementally during parsing.
    """

    title: str = ""
    description: str = ""
    source: str = "Not specified"
    added: str = ""
    priority: str = ""
    item_type: str = "Feature"
    issue: str = ""
    plan: str = ""
    research_first: str = ""
    files: str = ""
    suggested_location: str = ""

    type_: str = ""
    topic: str = ""

    section: str = ""
    file_path: str = ""
    skip: bool = False
    status: str = ""
    groomed: str = ""
    last_synced: str = ""
    raw_body: str = ""


class Output(BaseModel):
    """Structured output collector replacing direct typer.echo() calls.

    Functions that need to communicate status messages take an optional
    ``output: Output | None = None`` parameter. The CLI wrapper prints
    messages; the MCP server returns them in the response dict.
    """

    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def info(self, msg: str) -> None:
        """Record an informational message."""
        self.messages.append(msg)

    def warn(self, msg: str) -> None:
        """Record a warning message."""
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        """Record an error message."""
        self.errors.append(msg)

    def to_dict(self) -> dict[str, list[str]]:
        """Return all collected messages as a dict (alias for model_dump)."""
        return self.model_dump()


class SamTasksResult(TypedDict):
    """Return type for ``get_sam_tasks``."""

    tasks: list[dict[str, object]]
    count: int
    parent_issue_number: int
    messages: list[str]
    warnings: list[str]
    errors: list[str]


class IssueStatus(BaseModel):
    """GitHub issue status and milestone from batch fetch."""

    status: str = ""
    milestone: str = ""


class PullRequestRef(BaseModel):
    """Reference to an open pull request."""

    number: int
    title: str
    url: str


class ViewItemResult(BaseModel):
    """Result of viewing a single backlog item, optionally enriched with GitHub data."""

    title: str = ""
    priority: str = ""
    description: str = ""
    source: str = ""
    added: str = ""
    plan: str = ""
    issue: str = ""
    file_path: str = ""
    groomed: bool = False
    status: str = ""
    number: int | None = None
    state: str = ""
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    milestone: str = ""
    sections: dict[str, dict[str, object]] = Field(default_factory=dict)


class SectionMeta(ExtTypedDict):
    """Compact section inventory entry — section name plus entry counts, no body content."""

    name: str
    """Section heading text, e.g. ``Groomed (2026-03-22)``."""

    num_entries: int
    """Count of active (non-struck) entries in this section."""

    num_struck: int
    """Count of struck (completed/removed) entries in this section."""


class ViewItemResultCompact(BaseModel):
    """Compact result of viewing a single backlog item.

    Returned when ``include_content=False`` is passed to ``backlog_view``.
    Contains all metadata fields from :class:`ViewItemResult` but omits the
    full ``body`` text and per-entry ``sections`` dict.  Callers receive a
    section inventory (names and entry counts) instead.

    Fields are duplicated from :class:`ViewItemResult` rather than inherited
    (ADR-1) so that the two response shapes remain independently evolvable.
    """

    title: str = ""
    priority: str = ""
    description: str = ""
    source: str = ""
    added: str = ""
    plan: str = ""
    issue: str = ""
    file_path: str = ""
    groomed: bool = False
    status: str = ""
    number: int | None = None
    state: str = ""
    labels: list[str] = Field(default_factory=list)
    milestone: str = ""
    sections_metadata: list[SectionMeta] = Field(
        default_factory=list,
        description="Compact section inventory: section names with entry counts, no body or entry content.",
    )
    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IssueLocalFields(BaseModel):
    """Backlog-relevant fields extracted from a PyGithub Issue object."""

    title: str = ""
    body: str = ""
    priority: str = "P1"
    item_type: str = "Feature"
    status: str = "open"
    updated_at: str = ""
    milestone: str = ""


class SamTask(BaseModel):
    """SAM task metadata stored in the ``<!-- sam:task ... -->`` block of a GitHub issue body.

    Title format: ``[{feature}/{task_id}] {task_type}: {description}``
    Body block:   invisible HTML comment containing YAML fields below.
    """

    task_id: str = ""
    """Feature-scoped sequential ID, e.g. "T1", "T2"."""

    feature: str = ""
    """Feature slug, e.g. "uv-skill-update"."""

    task_type: str = ""
    """Execution category: "research" | "implement" | "review" | "fix" | "docs"."""

    status: str = "not-started"
    """Execution state: "not-started" | "in-progress" | "complete" | "blocked"."""

    agent: str = ""
    """Agent name to execute the task, e.g. "context-gathering"."""

    priority: int = 2
    """Execution priority 1-5 (1 = highest)."""

    skills: list[str] = Field(default_factory=list)
    """Skill names the executing agent should load."""

    dependencies: list[str] = Field(default_factory=list)
    """Feature-scoped task IDs this task depends on, e.g. ["T1", "T2"].
    Cross-feature deps use GitHub issue numbers: ["#479"]."""


# ---------------------------------------------------------------------------
# Artifact manifest models
# ---------------------------------------------------------------------------


class ArtifactType(StrEnum):
    """Categories of plan artifacts produced by the SAM workflow.

    Each value corresponds to a distinct artifact class produced by a specific
    agent phase.  The string values use kebab-case to match the naming
    conventions used in plan file names (e.g. ``plan/feature-context-{slug}.md``).
    """

    FEATURE_CONTEXT = "feature-context"
    ARCHITECT = "architect"
    TASK_PLAN = "task-plan"
    T0_BASELINE = "T0-baseline"
    TN_VERIFICATION = "TN-verification"
    CODEBASE_ANALYSIS = "codebase-analysis"
    RESEARCH = "research"
    DISPATCH_PLAN = "dispatch-plan"


class ArtifactStatus(StrEnum):
    """Lifecycle state of a plan artifact.

    Artifacts progress forward through states; they do not regress.
    ``superseded`` is set when a newer artifact of the same type replaces this
    one; ``archived`` marks artifacts that are no longer relevant.
    """

    DRAFT = "draft"
    CURRENT = "current"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class BackendAvailability(StrEnum):
    """Availability state of the GitHub backend.

    Describes whether the GitHub API is reachable and authenticated, or why it
    is not.  Used by :class:`BackendStatus` to summarise the probe result
    returned on every ``backlog_list`` call.
    """

    REACHABLE = "reachable"
    NOT_CHECKED = "not_checked"
    NEEDS_AUTHENTICATION = "needs_authentication"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class BackendStatus(BaseModel):
    """GitHub backend availability status included in every ``backlog_list`` response.

    Populated by ``probe_backend_status()`` in ``backlog_core.github``.  Fields
    default to their "unknown" states so the model is always safe to construct
    without arguments.

    Fields ``open_count`` and ``total_count`` are ``None`` when the backend was
    not reachable.  ``cache_open_count`` and ``cache_total_count`` are derived
    from the local list result in ``server.py``, not from the probe.
    """

    name: str = "GitHub"
    availability: BackendAvailability = BackendAvailability.NOT_CHECKED
    open_count: int | None = None
    total_count: int | None = None
    cache_open_count: int = 0
    cache_total_count: int = 0
    last_sync: str = ""
    error: str = ""


class ArtifactEntry(BaseModel):
    """A single artifact reference stored in the manifest.

    Accepts both kebab-case (``artifact-type``, ``created-at``) and snake_case
    (``artifact_type``, ``created_at``) field names as well as the short alias
    ``type`` for backward compatibility with markdown table rows produced by
    earlier tooling.

    The ``model_config`` enables population by field name and by alias so that
    either form works with ``model_validate``.
    """

    model_config = {"populate_by_name": True}

    artifact_type: ArtifactType = Field(
        ...,
        validation_alias=AliasChoices("artifact_type", "artifact-type", "type"),
        serialization_alias="artifact-type",
    )
    """Artifact category.  Serialised as ``artifact-type`` in markdown tables."""

    path: str = Field(..., description="Repo-relative path to the artifact file, e.g. plan/architect-foo.md.")
    """Repo-relative path to the artifact file, e.g. ``plan/architect-foo.md``."""

    status: ArtifactStatus = Field(default=ArtifactStatus.CURRENT)
    """Lifecycle state.  Defaults to ``current`` on initial registration."""

    created_at: str = Field(
        default="", validation_alias=AliasChoices("created_at", "created-at"), serialization_alias="created-at"
    )
    """ISO 8601 timestamp of when the artifact was registered.  Empty string when unknown."""

    agent: str = Field(default="")
    """Name of the agent that produced the artifact, e.g. ``feature-researcher``."""


class ArtifactManifest(BaseModel):
    """Complete artifact inventory for a single GitHub Issue.

    This model is the canonical in-memory representation of the
    ``<!-- artifact-manifest:begin/end -->`` section stored in the GitHub Issue
    body.  Serialisation and deserialisation are handled by
    ``backlog_core.artifact_registry``.
    """

    issue_number: int = Field(..., description="GitHub Issue number this manifest belongs to.")
    """GitHub Issue number this manifest belongs to."""

    artifacts: list[ArtifactEntry] = Field(default_factory=list)
    """Ordered list of registered artifact entries."""

    last_updated: str = Field(
        default="", validation_alias=AliasChoices("last_updated", "last-updated"), serialization_alias="last-updated"
    )
    """ISO 8601 timestamp of the most recent registry mutation.  Empty string when unknown."""

    model_config = {"populate_by_name": True}


class RegisterResult(BaseModel):
    """Response shape returned by the ``artifact_register`` MCP tool.

    Indicates whether the operation added a new entry or updated an existing
    one, and how many artifacts are now registered for the issue.
    """

    registered: bool = Field(..., description="True when the operation succeeded.")
    """True when the operation succeeded."""

    artifact_count: int = Field(..., description="Total number of artifacts in the manifest after the operation.")
    """Total number of artifacts in the manifest after the operation."""

    action: Literal["added", "updated"] = Field(
        ..., description="'added' for a new entry, 'updated' when an existing entry was modified."
    )
    """``'added'`` for a new entry; ``'updated'`` when an existing entry was modified."""

    content_stored: bool = Field(
        default=False, description="True when artifact content was stored as a GitHub issue comment."
    )
    """True when artifact content was stored as a GitHub issue comment."""


class ArtifactContent(BaseModel):
    """Response shape returned by the ``artifact_read`` MCP tool.

    Carries the raw file content alongside identifying metadata so callers do
    not need a separate lookup to know which artifact was returned.
    """

    artifact_type: ArtifactType = Field(..., description="Category of the returned artifact.")
    """Category of the returned artifact."""

    path: str = Field(..., description="Repo-relative path that was read.")
    """Repo-relative path that was read."""

    content: str = Field(..., description="Raw file content.")
    """Raw file content."""

    status: ArtifactStatus = Field(..., description="Current lifecycle state of the artifact.")
    """Current lifecycle state of the artifact."""


# ---------------------------------------------------------------------------
# Dispatch orchestration models
# ---------------------------------------------------------------------------


class DispatchItemRecord(BaseModel):
    """State of a single dispatch item, maps to the items SQLite table."""

    milestone: int
    wave_num: int
    issue: int
    title: str = ""
    status: str = "pending"
    """pending | in-progress | complete | failed | skipped"""
    pid: int | None = None
    started_at: str = ""
    """ISO 8601 timestamp when item entered in-progress state."""
    completed_at: str = ""
    """ISO 8601 timestamp when item reached a terminal state."""
    result: str = ""
    """JSON string or summary from result file."""
    error: str = ""
    cost: float | None = None
    result_file: str = ""
    error_file: str = ""


class DispatchWaveRecord(BaseModel):
    """State of a dispatch wave, maps to the waves SQLite table."""

    milestone: int
    wave_num: int
    status: str = "pending"
    """pending | in-progress | complete | failed"""
    started_at: str = ""
    completed_at: str = ""
    items: list[DispatchItemRecord] = Field(default_factory=list)


class DispatchSpawnResult(BaseModel):
    """JSON output from spawn.py parsed into a typed model."""

    pid: int
    name: str = ""
    worktree: str | None = None
    result_file: str
    error_file: str
    model: str = "sonnet"
    lock_file: str | None = None


class DispatchWaveSummary(BaseModel):
    """Aggregated wave status returned by the dispatch_wave_status tool."""

    milestone: int
    wave_num: int
    status: str
    total_items: int
    pending: int
    in_progress: int
    complete: int
    failed: int
    skipped: int
    started_at: str = ""
    completed_at: str = ""
    elapsed_seconds: float | None = None
    items: list[DispatchItemRecord] = Field(default_factory=list)


class DispatchSpawnSummary(BaseModel):
    """Final summary returned when the dispatch_spawn background task completes."""

    milestone: int
    waves_executed: int
    total_items: int
    completed: int
    failed: int
    skipped: int
    elapsed_seconds: float
    per_wave: list[DispatchWaveSummary] = Field(default_factory=list)
    total_cost: float | None = None
