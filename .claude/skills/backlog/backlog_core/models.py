"""Constants, regex patterns, type maps, Pydantic models, and exceptions for the backlog MCP package.

This module is standalone — it has no imports from other mcp submodules.
All models use Pydantic BaseModel for natural integration with FastMCP 3.x.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

# mcp/ -> backlog/ -> skills/ -> .claude/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

BACKLOG_DIR = _REPO_ROOT / ".claude" / "backlog"
DEFAULT_REPO = "Jamie-BitFlight/claude_skills"

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"^##\s+(P0|P1|P2|Ideas)")
GITHUB_ISSUE_URL_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)")
_COMMIT_PREFIX_RE = re.compile(r"^(feat|fix|refactor|docs|chore|perf|test|ci):\s*", re.IGNORECASE)

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

_FIELD_TO_INDEX: dict[str, int] = {
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
