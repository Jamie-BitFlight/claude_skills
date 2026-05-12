#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "ruamel.yaml>=0.18.0",
#     "python-frontmatter>=1.1.0",
#     "PyGithub>=2.1.1",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""Knowledge base explorer for research/ directory.

Manages entries in the research/ knowledge base. Reads both inline-header and
YAML frontmatter formats; always writes in frontmatter format. Six subcommands
share a single Typer entry point.
"""

from __future__ import annotations

import contextlib
import json

from dotenv import load_dotenv

load_dotenv()
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from urllib.parse import urlparse

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import frontmatter
import typer
from frontmatter.default_handlers import YAMLHandler
from github import Auth, Github, GithubException
from rich.console import Console
from rich.measure import Measurement
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KB_ROOT: Path = Path(__file__).parent.resolve()
_KNOWLEDGE_EXPLORER_SCRIPT_PATH: Path = Path(__file__).resolve()
_LEVENSHTEIN_MAX_DISTANCE: int = 2
_MAX_SUGGESTIONS: int = 3
_MIN_GITHUB_PATH_PARTS: int = 2
_DEFAULT_REVIEW_DAYS: int = 90
_NAME_MAX_LEN: int = 64
_README_DESC_MAX_LEN: int = 220
_CATEGORY_ACRONYMS: dict[str, str] = {
    "ai": "AI",
    "ui": "UI",
    "ux": "UX",
    "llm": "LLM",
    "mcp": "MCP",
    "api": "API",
    "sdk": "SDK",
    "cli": "CLI",
    "qa": "QA",
    "ci": "CI",
    "cd": "CD",
}

VALID_CATEGORIES: frozenset[str] = frozenset({
    "agent-frameworks",
    "agent-infrastructure",
    "agent-orchestration",
    "ai-design-tools",
    "ai-observability",
    "ai-research-tools",
    "ai-writing-tools",
    "api-frameworks",
    "async-libraries",
    "claude-code-plugins",
    "code-auditing",
    "coding-agents",
    "context-management",
    "customer-support-platforms",
    "data-infrastructure",
    "database-libraries",
    "developer-tooling",
    "developer-tools",
    "documentation-tools",
    "embedded-ui-libraries",
    "evaluation-testing",
    "insights",
    "installer-tools",
    "learning-resources",
    "llm-infrastructure",
    "low-code-platforms",
    "mcp-ecosystem",
    "ml-infrastructure",
    "paas-platforms",
    "prompt-engineering",
    "python-runtimes",
    "research-agent-patterns",
    "rust-python-bindings",
    "serialization-libraries",
    "skill-generation-tools",
    "task-management",
    "utilization",
})

console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class KBError(Exception):
    """Base exception. All knowledge-explorer errors inherit from this."""


@dataclass
class ParseError(KBError):
    """Format unrecognisable or required field missing during parse."""

    path: Path
    detail: str

    def __str__(self) -> str:
        """Return string representation."""
        return f"Parse error in {self.path}: {self.detail}"


@dataclass
class FrontmatterValidationError(KBError):
    """Frontmatter present but fails schema constraints."""

    path: Path
    missing_fields: list[str]
    invalid_fields: list[str]

    def __str__(self) -> str:
        """Return string representation."""
        parts: list[str] = []
        if self.missing_fields:
            parts.append(f"missing: {', '.join(self.missing_fields)}")
        if self.invalid_fields:
            parts.append(f"invalid: {', '.join(self.invalid_fields)}")
        return f"Validation error in {self.path}: {'; '.join(parts)}"


@dataclass
class TopicNotFoundError(KBError):
    """Topic slug not found in any entry. Includes suggestions."""

    topic: str
    suggestions: list[str]

    def __str__(self) -> str:
        """Return string representation."""
        msg = f"Topic '{self.topic}' not found."
        if self.suggestions:
            msg += f" Did you mean: {', '.join(self.suggestions)}?"
        return msg


@dataclass
class TopicConflictError(KBError):
    """Target path exists with a different topic slug."""

    target_path: Path
    existing_topic: str
    new_topic: str

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"Target {self.target_path} already exists with topic "
            f"'{self.existing_topic}', cannot overwrite with '{self.new_topic}'."
        )


@dataclass
class ExternalCommandError(KBError):
    """gh CLI not found or returned non-zero exit code."""

    command: str
    hint: str
    stderr: str = ""

    def __str__(self) -> str:
        """Return string representation."""
        msg = f"External command error: {self.command}\n{self.hint}"
        if self.stderr:
            msg += f"\nstderr: {self.stderr}"
        return msg


@dataclass
class ReadmeUpdateError(KBError):
    """README.md structure not recognised; update could not be applied."""

    detail: str

    def __str__(self) -> str:
        """Return string representation."""
        return f"README update error: {self.detail}"


@dataclass
class ReadmeSyncResult:
    """Result summary from README reconciliation."""

    missing_links: list[str]
    stale_links: list[str]
    added_rows: int
    created_sections: list[str]


# ---------------------------------------------------------------------------
# Layer 6: YAML Handler (embedded _RuamelYAMLHandler)
# ---------------------------------------------------------------------------


class _RuamelYAMLHandler(YAMLHandler):
    """Frontmatter handler using ruamel.yaml in round-trip mode.

    Overrides the default pyyaml-based handler so that:
    - Values without special YAML characters stay unquoted.
    - Values requiring quotes (colon-space) get single-quoted.
    - Unnecessary quotes from the source are stripped on round-trip.
    - Long scalar values do not get wrapped into block scalars.
    """

    def __init__(self) -> None:
        """Initialize handler with ruamel.yaml round-trip instance."""
        super().__init__()
        self._yaml = YAML(typ="rt")
        self._yaml.preserve_quotes = False
        self._yaml.width = 2147483647

    def load(self, fm: str, **kwargs: Any) -> Any:
        """Parse YAML frontmatter string using ruamel.yaml round-trip loader.

        Args:
            fm: Raw YAML frontmatter string (without delimiters).
            **kwargs: Ignored (present for API compatibility).

        Returns:
            Parsed YAML data as a CommentedMap or None for empty input.
        """
        return self._yaml.load(fm)

    def export(self, metadata: dict[str, Any], **kwargs: Any) -> str:
        """Serialize metadata dict to YAML string using ruamel.yaml.

        Args:
            metadata: Frontmatter metadata dictionary.
            **kwargs: Ignored (present for API compatibility).

        Returns:
            YAML-formatted string without trailing newline.
        """
        buf = StringIO()
        self._yaml.dump(metadata, buf)
        return buf.getvalue().strip()


_handler = _RuamelYAMLHandler()

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class KBEntry:
    """Canonical in-memory representation of a knowledge base entry."""

    # Required frontmatter fields
    topic: str
    name: str
    category: str
    source_url: str
    verified: date
    next_review: date

    # Top-level skill spec fields
    description: str = ""

    # Optional frontmatter fields
    github: str | None = None
    version: str | None = None
    license: str | None = None
    tags: list[str] = field(default_factory=list)
    # SDLC layer metadata (see .claude/docs/sdlc-layers/)
    layer: str | None = None
    language: str | None = None
    stack: str | None = None

    # Runtime-only fields — not written to frontmatter
    file_path: Path = field(default_factory=Path)
    body: str = ""
    has_frontmatter: bool = False
    is_overdue: bool = field(init=False)

    def __post_init__(self) -> None:
        """Compute derived fields."""
        self.is_overdue = self.next_review < datetime.now(tz=UTC).date()


@dataclass
class MigrationResult:
    """Result of a migrate operation."""

    migrated: list[Path] = field(default_factory=list)
    already_migrated: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)


@dataclass
class GitHubMetadata:
    """Metadata fetched from GitHub API."""

    slug: str
    name: str
    description: str
    license: str | None
    latest_tag: str | None
    default_branch: str
    has_docs_dir: bool
    docs_files: list[str]
    topics: list[str]


# ---------------------------------------------------------------------------
# Layer 5: External I/O
# ---------------------------------------------------------------------------


def _get_github() -> Github:
    """Return authenticated Github client. Raises ExternalCommandError if GITHUB_TOKEN not set."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ExternalCommandError(command="GITHUB_TOKEN", hint="Set GITHUB_TOKEN or run: gh auth login")
    return Github(auth=Auth.Token(token))


def fetch_github_metadata(repo_slug: str) -> GitHubMetadata:
    """Fetch metadata for a GitHub repository.

    Args:
        repo_slug: Repository in 'owner/repo' format.

    Returns:
        GitHubMetadata populated from GitHub API.

    Raises:
        ExternalCommandError: If GITHUB_TOKEN not set or API call fails.
    """
    gh = _get_github()
    try:
        repo = gh.get_repo(repo_slug)
    except Exception as exc:
        raise ExternalCommandError(
            command=f"get_repo({repo_slug})", hint="Ensure you are authenticated: gh auth login", stderr=str(exc)
        ) from exc

    latest_tag: str | None = None
    try:
        release = repo.get_latest_release()
        latest_tag = release.tag_name
    except GithubException:
        latest_tag = None

    root_contents = repo.get_contents("")
    items = list(root_contents) if isinstance(root_contents, list) else [root_contents]
    has_docs_dir = False
    docs_dirname: str | None = None
    for item in items:
        if item.type == "dir" and item.name in {"docs", "doc"}:
            has_docs_dir = True
            docs_dirname = item.name
            break

    docs_files: list[str] = []
    if has_docs_dir and docs_dirname:
        try:
            docs_contents = repo.get_contents(docs_dirname)
            docs_items = list(docs_contents) if isinstance(docs_contents, list) else [docs_contents]
            docs_files = [item.path for item in docs_items]
        except GithubException:
            docs_files = []

    license_info = repo.raw_data.get("license") or {}
    license_spdx: str | None = license_info.get("spdx_id") if license_info else None
    if license_spdx in {"NOASSERTION", ""}:
        license_spdx = None

    return GitHubMetadata(
        slug=repo_slug,
        name=repo.name or repo_slug.rsplit("/", maxsplit=1)[-1],
        description=repo.description or "",
        license=license_spdx,
        latest_tag=latest_tag,
        default_branch=repo.default_branch or "main",
        has_docs_dir=has_docs_dir,
        docs_files=docs_files,
        topics=repo.get_topics(),
    )


def find_entry_by_topic(topic: str, kb_root: Path) -> Path | None:
    """Search all .md files for an entry matching the topic slug.

    Args:
        topic: Kebab-case topic slug to find.
        kb_root: Root directory of the knowledge base.

    Returns:
        Path to the matching file, or None if not found.
    """
    for md_file in _iter_kb_files(kb_root):
        text = md_file.read_text(encoding="utf-8")
        fmt = _detect_format_safe(text)
        if fmt == "frontmatter":
            with contextlib.suppress(Exception):
                post = frontmatter.loads(text, handler=_handler)
                meta = post.metadata
                # New skill-spec format: topic is inside metadata block
                raw_inner = meta.get("metadata")
                inner: dict[str, Any] = {}
                if isinstance(raw_inner, dict):
                    inner = cast("dict[str, Any]", raw_inner)
                stored_topic = inner.get("topic") if inner else meta.get("topic")
                if stored_topic == topic:
                    return md_file
        elif md_file.stem == topic:
            return md_file
    return None


def _build_readme_row(entry: KBEntry) -> str:
    """Build a README table row string for an entry.

    Args:
        entry: Entry to build the row for.

    Returns:
        Markdown table row string.
    """
    today_iso = datetime.now(tz=UTC).date().isoformat()
    first_paragraph = _extract_first_paragraph(entry.body)
    summary_source = entry.name if first_paragraph is None else first_paragraph
    summary = _normalize_readme_description(summary_source)
    return f"| [{entry.topic}.md](./{entry.category}/{entry.topic}.md) | {summary} | {today_iso} |"


def _normalize_readme_description(value: str, max_len: int = _README_DESC_MAX_LEN) -> str:
    """Normalize README row description text for markdown table safety.

    Args:
        value: Raw description text.
        max_len: Maximum allowed output length.

    Returns:
        Normalized and length-capped markdown-safe description text with ``|``
        escaped for markdown table cells.
    """
    normalized = re.sub(r"\s+", " ", value).strip().replace("|", "\\|")
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def _readme_paths_from_text(text: str) -> set[str]:
    """Extract markdown link targets from README table links.

    Args:
        text: Full README markdown content.

    Returns:
        Set of relative markdown paths referenced by README links.
    """
    return set(re.findall(r"\]\(\./([^)]+\.md)\)", text))


def _discover_research_markdown_paths(kb_root: Path) -> set[str]:
    """Return all research markdown paths relative to kb_root."""
    excluded = {(kb_root / "README.md").resolve(), _KNOWLEDGE_EXPLORER_SCRIPT_PATH}
    return {str(path.relative_to(kb_root)).replace("\\", "/") for path in kb_root.rglob("*.md") if path not in excluded}


def _extract_readme_row_metadata(path: Path) -> tuple[str, str]:
    """Extract description and date for README table row generation.

    Args:
        path: Absolute path to a markdown research file.

    Returns:
        Tuple of ``(description, yyyy-mm-dd)`` suitable for README tables.
    """
    text = path.read_text(encoding="utf-8")
    body = text
    frontmatter_meta: dict[str, Any] = {}

    if text.startswith("---\n"):
        with contextlib.suppress(Exception):
            post = frontmatter.loads(text, handler=_handler)
            frontmatter_meta = cast("dict[str, Any]", post.metadata)
            body = post.content

    nested_meta = frontmatter_meta.get("metadata")
    nested = cast("dict[str, Any]", nested_meta) if isinstance(nested_meta, dict) else {}

    desc = (
        cast("str | None", frontmatter_meta.get("subtitle"))
        or cast("str | None", frontmatter_meta.get("description"))
        or cast("str | None", frontmatter_meta.get("title"))
        or cast("str | None", frontmatter_meta.get("name"))
        or _extract_first_paragraph(body)
        or path.stem.replace("-", " ")
    )
    normalized_desc = _normalize_readme_description(desc)

    date_candidates: list[str] = []
    for key in ("date_last_reviewed", "last_reviewed", "date_created", "verified"):
        value = frontmatter_meta.get(key)
        if isinstance(value, str):
            date_candidates.append(value)
    nested_verified = nested.get("verified")
    if isinstance(nested_verified, str):
        date_candidates.append(nested_verified)

    for value in date_candidates:
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return normalized_desc, match.group(0)

    body_date_match = re.search(r"\*\*(?:Research Date|Last Verified)\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", body)
    if body_date_match:
        return normalized_desc, body_date_match.group(1)

    freshness_match = re.search(r"\|\s*Last Verified\s*\|\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*\|", body)
    if freshness_match:
        return normalized_desc, freshness_match.group(1)

    return normalized_desc, datetime.now(tz=UTC).date().isoformat()


def _find_location_section_index(lines: list[str], category: str) -> int | None:
    """Return index of the Location line for a README category section.

    Args:
        lines: README lines with newlines preserved.
        category: Category directory name or ``"(root)"``.

    Returns:
        Line index for the matching ``**Location**`` line, else ``None``.
    """
    targets = ("(./)",) if category == "(root)" else (f"(./{category}/)",)
    for idx, line in enumerate(lines):
        if line.startswith("**Location**:") and any(target in line for target in targets):
            return idx
    return None


def _find_table_insert_index(lines: list[str], location_idx: int) -> int | None:
    """Find insertion point at end of a category table.

    Args:
        lines: README lines with newlines preserved.
        location_idx: Line index of the category ``**Location**`` marker.

    Returns:
        Line index where new table rows should be inserted, or ``None`` when
        no table header exists for the section.
    """
    table_idx = None
    for idx in range(location_idx + 1, len(lines)):
        if lines[idx].startswith(("### ", "## ")):
            break
        if lines[idx].startswith("| Document |"):
            table_idx = idx
            break
    if table_idx is None:
        return None

    insert_idx = table_idx + 2
    while insert_idx < len(lines) and lines[insert_idx].startswith("| "):
        insert_idx += 1
    return insert_idx


def _build_readme_row_from_relpath(kb_root: Path, rel_path: str) -> str:
    """Build a README table row for a research markdown relative path.

    Args:
        kb_root: Root ``research/`` directory.
        rel_path: Markdown path relative to ``kb_root``.

    Returns:
        Markdown table row with link, description, and date.
    """
    desc, updated = _extract_readme_row_metadata(kb_root / rel_path)
    file_name = Path(rel_path).name
    return f"| [{file_name}](./{rel_path}) | {desc} | {updated} |\n"


def _group_paths_by_category(paths: list[str]) -> dict[str, list[str]]:
    """Group relative markdown paths by category key.

    Args:
        paths: Relative markdown paths from ``research/``.

    Returns:
        Mapping of category name (or ``"(root)"``) to relative paths.
    """
    grouped: dict[str, list[str]] = {}
    for rel_path in paths:
        category = rel_path.split("/", 1)[0] if "/" in rel_path else "(root)"
        grouped.setdefault(category, []).append(rel_path)
    return grouped


def _format_category_title(category: str) -> str:
    """Format category slug into an acronym-aware section title.

    Args:
        category: Category directory name or ``"(root)"``.

    Returns:
        Human-readable README section title.
    """
    if category == "(root)":
        return "Root Research Entries"

    parts = category.split("-")
    return " ".join(_CATEGORY_ACRONYMS.get(part.lower(), part.capitalize()) for part in parts)


def _append_category_section(lines: list[str], category: str, rows: list[str]) -> None:
    """Append a new README section and table block for a category.

    Args:
        lines: README lines with newlines preserved.
        category: Category directory name or ``"(root)"``.
        rows: Prebuilt markdown table rows for the category.
    """
    title = _format_category_title(category)
    location = "./" if category == "(root)" else f"./{category}/"
    block = [
        "\n",
        f"### {title}\n",
        "\n",
        f"**Location**: [{location}]({location})\n",
        "\n",
        "| Document | Description | Last Updated |\n",
        "|---|---|---|\n",
        *rows,
    ]
    planned_idx = next((idx for idx, line in enumerate(lines) if line.startswith("## Planned")), len(lines))
    lines[planned_idx:planned_idx] = block


def _insert_missing_rows(kb_root: Path, lines: list[str], grouped_paths: dict[str, list[str]]) -> tuple[int, list[str]]:
    """Insert missing README rows by category and return mutation summary.

    Args:
        kb_root: Root ``research/`` directory.
        lines: README lines with newlines preserved.
        grouped_paths: Missing file paths grouped by category.

    Returns:
        Tuple of ``(added_row_count, created_sections)``.
    """
    added_rows = 0
    created_sections: list[str] = []
    for category in sorted(grouped_paths):
        rows = [_build_readme_row_from_relpath(kb_root, rel_path) for rel_path in grouped_paths[category]]
        location_idx = _find_location_section_index(lines, category)
        if location_idx is not None:
            insert_idx = _find_table_insert_index(lines, location_idx)
            if insert_idx is None:
                continue
            lines[insert_idx:insert_idx] = rows
            added_rows += len(rows)
            continue

        _append_category_section(lines, category, rows)
        added_rows += len(rows)
        created_sections.append(category)
    return added_rows, created_sections


def reconcile_readme_index(kb_root: Path, write: bool = True) -> ReadmeSyncResult:
    """Reconcile README links against all markdown files in ``research/``.

    Args:
        kb_root: Root ``research/`` directory.
        write: When ``True``, writes missing rows into README. When ``False``,
            performs a read-only drift check.

    Returns:
        Summary containing missing links, stale links, and write mutations.
    """
    readme_path = kb_root / "README.md"
    if not readme_path.exists():
        raise ReadmeUpdateError(detail="README.md not found")

    text = readme_path.read_text(encoding="utf-8")
    linked_paths = _readme_paths_from_text(text)
    discovered_paths = _discover_research_markdown_paths(kb_root)

    missing = sorted(discovered_paths - linked_paths)
    stale = sorted(linked_paths - discovered_paths)
    if not write or not missing:
        return ReadmeSyncResult(missing_links=missing, stale_links=stale, added_rows=0, created_sections=[])

    grouped = _group_paths_by_category(missing)
    lines = text.splitlines(keepends=True)
    added_rows, created_sections = _insert_missing_rows(kb_root, lines, grouped)

    readme_path.write_text("".join(lines), encoding="utf-8")
    return ReadmeSyncResult(
        missing_links=missing, stale_links=stale, added_rows=added_rows, created_sections=created_sections
    )


def _update_existing_section(text: str, new_row: str, entry: KBEntry, section_start: int) -> str:
    """Update a README table row inside an existing category section.

    Args:
        text: Full README text.
        new_row: New table row to insert or replace.
        entry: Entry being added/updated.
        section_start: Character offset of the category section start.

    Returns:
        Updated README text.

    Raises:
        ReadmeUpdateError: If no table is found in the section.
    """
    table_header_pat = re.compile(r"\| Document \|.*\n\|[-| ]+\|", re.IGNORECASE)
    table_match = table_header_pat.search(text, section_start)
    if not table_match:
        raise ReadmeUpdateError(detail=f"No table found in section for '{entry.category}'")

    table_end = table_match.end()
    row_pattern = re.compile(r"\n(\|[^\n]+\|)")
    rows: list[tuple[int, int, str]] = []
    pos = table_end
    while pos < len(text):
        row_match = row_pattern.match(text, pos)
        if not row_match:
            break
        rows.append((row_match.start(), row_match.end(), row_match.group(1)))
        pos = row_match.end()

    topic_marker_a = f"/{entry.topic}.md)"
    topic_marker_b = f"/{entry.topic}.md |"
    existing_idx = next(
        (
            i
            for i, (_, _, row_content) in enumerate(rows)
            if topic_marker_a in row_content or topic_marker_b in row_content
        ),
        None,
    )

    if existing_idx is not None:
        start, end, _ = rows[existing_idx]
        return text[:start] + "\n" + new_row + text[end:]

    # Insert alphabetically
    insert_pos = table_end
    for _, row_end, row_content in rows:
        link_match = re.search(r"\[([^\]]+)\.md\]", row_content)
        if link_match and link_match.group(1) < entry.topic:
            insert_pos = row_end
        else:
            break
    return text[:insert_pos] + "\n" + new_row + text[insert_pos:]


def _append_new_section(text: str, new_row: str, entry: KBEntry) -> str:
    """Append a new category section to README text.

    Args:
        text: Full README text.
        new_row: Table row for the entry.
        entry: Entry being added.

    Returns:
        Updated README text with new section inserted.
    """
    new_section = (
        f"\n\n### {entry.category.replace('-', ' ').title()}\n\n"
        f"**Location**: [./{entry.category}/](./{entry.category}/)\n\n"
        f"| Document | Description | Last Updated |\n"
        f"|---|---|---|\n"
        f"{new_row}\n"
    )
    planned_pat = re.compile(r"^## Planned", re.MULTILINE)
    planned_match = planned_pat.search(text)
    if planned_match:
        return text[: planned_match.start()] + new_section + text[planned_match.start() :]
    return text.rstrip() + new_section


def update_readme(kb_root: Path, entry: KBEntry) -> None:
    """Update README.md with the new or updated entry row.

    Args:
        kb_root: Root directory of the knowledge base.
        entry: Entry to add/update in the README table.

    Raises:
        ReadmeUpdateError: If README structure is not recognised.
    """
    readme_path = kb_root / "README.md"
    if not readme_path.exists():
        raise ReadmeUpdateError(detail="README.md not found")

    text = readme_path.read_text(encoding="utf-8")
    new_row = _build_readme_row(entry)

    location_pattern = re.compile(rf"\*\*Location\*\*:.*\[.*{re.escape(entry.category)}.*\]", re.IGNORECASE)
    section_match = location_pattern.search(text)

    if section_match:
        text = _update_existing_section(text, new_row, entry, section_match.start())
    else:
        text = _append_new_section(text, new_row, entry)

    tmp = readme_path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(readme_path)


# ---------------------------------------------------------------------------
# Layer 3: Parsers
# ---------------------------------------------------------------------------


def detect_format(text: str) -> Literal["frontmatter", "inline-header"]:
    """Detect whether text uses frontmatter or inline-header format.

    Args:
        text: Raw file content.

    Returns:
        'frontmatter' or 'inline-header'.

    Raises:
        ParseError: If format cannot be determined.
    """
    if text.startswith("---\n"):
        return "frontmatter"
    # Check inline-header: first non-blank line is '# Heading' and
    # block before '---' or '##' contains at least one **Field** marker.
    first_nonblank = next((line for line in text.splitlines() if line.strip()), "")
    if first_nonblank.startswith(("# ", "|")):
        # Look for bold field or table row before first ## heading
        pre_body = text
        separator_match = re.search(r"^##\s", text, re.MULTILINE)
        if separator_match:
            pre_body = text[: separator_match.start()]
        bold_field = re.search(r"\*\*[A-Za-z ]+\*\*\s*:", pre_body)
        table_field = re.search(r"^\|\s*Research Date\s*\|", pre_body, re.MULTILINE)
        if bold_field or table_field:
            return "inline-header"
    raise ParseError(
        path=Path("<text>"), detail="Cannot determine format: not frontmatter and no inline-header fields found."
    )


def _detect_format_safe(text: str) -> Literal["frontmatter", "inline-header"] | None:
    """Detect format without raising.

    Args:
        text: Raw file content.

    Returns:
        Format string or None on error.
    """
    try:
        return detect_format(text)
    except ParseError:
        return None


def _parse_research_date(value: str) -> date:
    """Parse a research date in ISO or long format.

    Args:
        value: Date string, e.g. '2026-01-26' or 'January 26, 2026'.

    Returns:
        Parsed date object.

    Raises:
        ParseError: If neither pattern matches.
    """
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%B %d, %Y").replace(tzinfo=UTC).date()
    except ValueError:
        pass
    raise ParseError(
        path=Path("<date>"), detail=f"Cannot parse date: '{value}'. Expected YYYY-MM-DD or 'Month DD, YYYY'."
    )


def _extract_github_slug(url: str) -> str | None:
    """Extract 'owner/repo' from a GitHub URL.

    Args:
        url: Full GitHub URL such as 'https://github.com/owner/repo'.

    Returns:
        'owner/repo' string, or None if pattern does not match.
    """
    url = url.strip().strip("<>")
    parsed = urlparse(url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= _MIN_GITHUB_PATH_PARTS:
        return f"{parts[0]}/{parts[1]}"
    return None


def _merge_freshness_fields(fields: dict[str, str], freshness_block: str, table_pattern: re.Pattern[str]) -> None:
    """Extract freshness table values and merge into fields dict.

    Args:
        fields: Existing fields dict to update in-place.
        freshness_block: Text of the Freshness Tracking section.
        table_pattern: Compiled regex for table row matching.
    """
    for match in table_pattern.finditer(freshness_block):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if re.match(r"^[-:]+$", key):
            continue
        key_lower = key.lower()
        if "last verified" in key_lower:
            fields.setdefault("Last Verified", value)
        elif "version at verif" in key_lower:
            fields["Version at Verification"] = value
        elif "next review" in key_lower:
            cleaned = re.sub(r"\s*\([^)]+\)\s*$", "", value).strip()
            fields.setdefault("Next Review Recommended", cleaned)


def _trim_body_section(body_lines: list[str]) -> str:
    """Trim trailing Change Detection / Review Triggers noise from body lines.

    Args:
        body_lines: Lines of the body section (before Freshness Tracking).

    Returns:
        Stripped body text.
    """
    trimmed: list[str] = []
    for line in body_lines:
        if re.match(r"^\*\*(Change Detection|Review Triggers)", line):
            break
        trimmed.append(line)
    return "".join(trimmed).strip()


def strip_inline_header_and_freshness(text: str) -> tuple[dict[str, str], str]:
    """Extract fields and body from inline-header format.

    Parses **Field**: value pairs from the header region and removes the
    Freshness Tracking section.

    Args:
        text: Full file content in inline-header format.

    Returns:
        Tuple of (fields_dict, body).
    """
    lines = text.splitlines(keepends=True)
    fields: dict[str, str] = {}

    # Detect header end: first line starting with ## after a non-heading section
    header_end_line = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## ") and i > 0:
            header_end_line = i
            break

    header_block = "".join(lines[:header_end_line])

    # Parse **Field**: value patterns
    bold_pattern = re.compile(r"\*\*([^*]+)\*\*\s*:\s*(.+)")
    for match in bold_pattern.finditer(header_block):
        key = match.group(1).strip()
        value = match.group(2).strip()
        fields[key] = value

    # Parse table-style: | Field | Value |
    table_pattern = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
    for match in table_pattern.finditer(header_block):
        key = match.group(1).strip()
        value = match.group(2).strip()
        # Skip separator rows like | --- |
        if re.match(r"^[-:]+$", key) or re.match(r"^[-:]+$", value):
            continue
        if key.lower() in {"field", "document", "description"}:
            continue
        fields[key] = value

    body_lines = lines[header_end_line:]
    freshness_start = next(
        (i for i, line in enumerate(body_lines) if re.match(r"^## Freshness", line, re.IGNORECASE)), None
    )

    if freshness_start is not None:
        _merge_freshness_fields(fields, "".join(body_lines[freshness_start:]), table_pattern)
        body_text = _trim_body_section(body_lines[:freshness_start])
    else:
        body_text = "".join(body_lines).strip()

    body_text = re.sub(r"\n---\s*$", "", body_text).strip()
    return fields, body_text


def _extract_optional_inline_fields(
    fields: dict[str, str], stem: str
) -> tuple[str, str | None, str | None, str | None]:
    """Extract source_url, github, version, license from inline-header fields dict.

    Args:
        fields: Parsed inline-header fields.
        stem: File stem used as fallback for source_url.

    Returns:
        Tuple of (source_url, github, version, license).
    """
    source_url_raw = fields.get("Source URL") or fields.get("Primary URL") or ""
    source_url = source_url_raw.strip().strip("<>") or f"https://github.com/{stem}"

    github_raw = (fields.get("GitHub Repository") or fields.get("GitHub") or "").strip().strip("<>")
    github: str | None = _extract_github_slug(github_raw) if github_raw else None

    version_raw = (
        fields.get("Version at Verification")
        or fields.get("Version at Research")
        or fields.get("Version")
        or fields.get("Version Documented")
    )
    version: str | None = re.sub(r"\s*\(.*\)\s*$", "", version_raw).strip() or None if version_raw else None

    license_raw = fields.get("License")
    lic: str | None = license_raw.strip() if license_raw else None

    return source_url, github, version, lic


def _parse_inline_dates(fields: dict[str, str], path: Path, verified_raw: str) -> tuple[date, date]:
    """Parse verified and next_review dates from inline-header fields dict.

    Args:
        fields: Parsed inline-header field dict.
        path: File path for error context.
        verified_raw: Raw string for the verified date.

    Returns:
        Tuple of (verified, next_review) date objects.

    Raises:
        ParseError: If verified_raw cannot be parsed.
    """
    try:
        verified = _parse_research_date(verified_raw)
    except ParseError as exc:
        raise ParseError(path=path, detail=str(exc)) from exc

    next_review_raw = fields.get("Next Review Recommended") or fields.get("Next Review Date") or ""
    if next_review_raw:
        try:
            next_review = _parse_research_date(next_review_raw)
        except ParseError:
            next_review = verified + timedelta(days=_DEFAULT_REVIEW_DAYS)
    else:
        next_review = verified + timedelta(days=_DEFAULT_REVIEW_DAYS)

    return verified, next_review


def parse_inline_header_entry(text: str, path: Path) -> KBEntry:
    """Parse an entry in inline-header format.

    Args:
        text: Raw file content.
        path: File path for error reporting.

    Returns:
        KBEntry populated from inline-header fields.

    Raises:
        ParseError: If required fields are missing or unparseable.
    """
    fields, body = strip_inline_header_and_freshness(text)

    topic = path.stem
    category = path.parent.name

    heading_match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    name = heading_match.group(1).strip() if heading_match else topic

    verified_raw = fields.get("Research Date") or fields.get("Last Verified") or fields.get("Version Documented") or ""
    if not verified_raw:
        raise ParseError(path=path, detail="Cannot find Research Date or Last Verified field.")

    verified, next_review = _parse_inline_dates(fields, path, verified_raw)
    source_url, github, version, lic = _extract_optional_inline_fields(fields, path.stem)

    first_para = _extract_first_paragraph(body)
    description = first_para or f"Research entry for {name}. Use when working with {name} or related tools."

    return KBEntry(
        topic=topic,
        name=name,
        description=description,
        category=category,
        source_url=source_url,
        verified=verified,
        next_review=next_review,
        github=github,
        version=version,
        license=lic,
        tags=[],
        file_path=path,
        body=body,
        has_frontmatter=False,
    )


def _parse_tags_field(tags_raw: Any) -> list[str]:
    """Parse a tags value from frontmatter into a list of strings.

    Accepts a list, a comma-separated string, or None/empty.

    Args:
        tags_raw: Raw value from frontmatter metadata.

    Returns:
        List of tag strings.
    """
    if isinstance(tags_raw, list):
        return [str(t) for t in tags_raw]
    if tags_raw:
        return [t.strip() for t in str(tags_raw).split(",") if t.strip()]
    return []


def _parse_date_field(raw: Any) -> date:
    """Parse a date field that may already be a date or a string.

    Args:
        raw: Raw value from frontmatter (date object or string).

    Returns:
        Parsed date object.

    Raises:
        ParseError: If the value cannot be parsed.
    """
    if isinstance(raw, date):
        return raw
    return _parse_research_date(str(raw))


def _from_research_curator_meta(top: Any, path: Path) -> KBEntry:
    """Parse a KBEntry from canonical research-curator frontmatter schema.

    Handles entries written by the research-curator skill's frontmatter
    generation procedure: title/subtitle/category/resource_url/github_url/
    date_created/date_last_reviewed/status at the top level.

    Field mapping to KBEntry:
        title           -> name  (topic defaults to file stem)
        subtitle        -> description
        resource_url    -> source_url
        date_created    -> verified
        date_last_reviewed -> next_review
        github_url      -> github

    Args:
        top: Full parsed frontmatter metadata dict.
        path: File path for error reporting.

    Returns:
        KBEntry populated from research-curator format.

    Raises:
        FrontmatterValidationError: If required fields are missing.
        ParseError: If date fields cannot be parsed.
    """
    required = [f for f in ("title", "resource_url", "date_created", "date_last_reviewed") if f not in top]
    if required:
        raise FrontmatterValidationError(path=path, missing_fields=required, invalid_fields=[])

    category = str(top.get("category") or path.parent.name)
    github_raw = top.get("github_url")

    return KBEntry(
        topic=path.stem,
        name=str(top["title"]),
        description=str(top.get("subtitle") or ""),
        category=category,
        source_url=str(top["resource_url"]),
        verified=_parse_date_field(top["date_created"]),
        next_review=_parse_date_field(top["date_last_reviewed"]),
        github=str(github_raw) if github_raw is not None else None,
        file_path=path,
        body="",
        has_frontmatter=True,
    )


def _from_skill_spec_meta(top: Any, path: Path) -> KBEntry:
    """Parse a KBEntry from new skill-spec frontmatter (metadata sub-mapping).

    Args:
        top: Full parsed frontmatter metadata dict.
        path: File path for error reporting.

    Returns:
        KBEntry populated from skill-spec format.

    Raises:
        FrontmatterValidationError: If required fields are missing.
        ParseError: If date fields cannot be parsed.
    """
    inner: dict[str, Any] = top["metadata"]
    required_top = [f for f in ("name",) if f not in top]
    required_inner = [f for f in ("topic", "category", "source_url", "verified", "next_review") if f not in inner]
    missing = required_top + required_inner
    if missing:
        raise FrontmatterValidationError(path=path, missing_fields=missing, invalid_fields=[])

    license_val: str | None = str(top["license"]) if top.get("license") is not None else None
    github_val: str | None = str(inner["github"]) if inner.get("github") is not None else None
    version_val: str | None = str(inner["version"]) if inner.get("version") is not None else None

    layer_val: str | None = str(inner["layer"]) if inner.get("layer") is not None else None
    language_val: str | None = str(inner["language"]) if inner.get("language") is not None else None
    stack_val: str | None = str(inner["stack"]) if inner.get("stack") is not None else None

    return KBEntry(
        topic=str(inner["topic"]),
        name=str(top["name"]),
        description=str(top.get("description") or ""),
        category=str(inner["category"]),
        source_url=str(inner["source_url"]),
        verified=_parse_date_field(inner["verified"]),
        next_review=_parse_date_field(inner["next_review"]),
        github=github_val,
        version=version_val,
        license=license_val,
        tags=_parse_tags_field(inner.get("tags")),
        layer=layer_val,
        language=language_val,
        stack=stack_val,
        file_path=path,
        body="",  # filled by caller
        has_frontmatter=True,
    )


def _from_flat_meta(meta: Any, path: Path) -> KBEntry:
    """Parse a KBEntry from old flat frontmatter format.

    Args:
        meta: Full parsed frontmatter metadata dict (flat, no metadata sub-key).
        path: File path for error reporting.

    Returns:
        KBEntry populated from flat format.

    Raises:
        FrontmatterValidationError: If required fields are missing.
        ParseError: If date fields cannot be parsed.
    """
    missing = [f for f in ("topic", "name", "category", "source_url", "verified", "next_review") if f not in meta]
    if missing:
        raise FrontmatterValidationError(path=path, missing_fields=missing, invalid_fields=[])

    github_val: str | None = str(meta["github"]) if meta.get("github") is not None else None
    version_val: str | None = str(meta["version"]) if meta.get("version") is not None else None
    license_val: str | None = str(meta["license"]) if meta.get("license") is not None else None

    layer_val: str | None = str(meta["layer"]) if meta.get("layer") is not None else None
    language_val: str | None = str(meta["language"]) if meta.get("language") is not None else None
    stack_val: str | None = str(meta["stack"]) if meta.get("stack") is not None else None

    return KBEntry(
        topic=str(meta["topic"]),
        name=str(meta["name"]),
        description=str(meta.get("description") or ""),
        category=str(meta["category"]),
        source_url=str(meta["source_url"]),
        verified=_parse_date_field(meta["verified"]),
        next_review=_parse_date_field(meta["next_review"]),
        github=github_val,
        version=version_val,
        license=license_val,
        tags=_parse_tags_field(meta.get("tags")),
        layer=layer_val,
        language=language_val,
        stack=stack_val,
        file_path=path,
        body="",  # filled by caller
        has_frontmatter=True,
    )


def parse_frontmatter_entry(text: str, path: Path) -> KBEntry:
    """Parse an entry in YAML frontmatter format.

    Handles three formats:
    - Skill-spec format: top-level ``name``, ``description``, ``license``; KB
      fields inside a ``metadata`` mapping.
    - Research-curator format: top-level ``title``, ``resource_url``,
      ``date_created``, ``date_last_reviewed`` (produced by the research-curator
      skill's frontmatter generation procedure).
    - Flat format: all KB fields at top level (topic, name, category, …).

    Args:
        text: Raw file content.
        path: File path for error reporting.

    Returns:
        KBEntry populated from frontmatter fields.

    Raises:
        ParseError: If required fields are missing.
        FrontmatterValidationError: If fields fail schema constraints.
    """
    try:
        post = frontmatter.loads(text, handler=_handler)
    except Exception as exc:
        raise ParseError(path=path, detail=f"YAML parse error: {exc}") from exc

    top = post.metadata
    if isinstance(top.get("metadata"), dict):
        entry = _from_skill_spec_meta(top, path)
    elif "title" in top and "resource_url" in top:
        entry = _from_research_curator_meta(top, path)
    else:
        entry = _from_flat_meta(top, path)
    entry.body = post.content
    return entry


# ---------------------------------------------------------------------------
# Layer 2: Core operations
# ---------------------------------------------------------------------------


def parse_entry(path: Path) -> KBEntry:
    """Read a file and return a KBEntry.

    Args:
        path: Path to a markdown knowledge base file.

    Returns:
        KBEntry parsed from the file.

    Raises:
        ParseError: If file format is unrecognisable.
    """
    text = path.read_text(encoding="utf-8")
    fmt = detect_format(text)
    if fmt == "frontmatter":
        return parse_frontmatter_entry(text, path)
    return parse_inline_header_entry(text, path)


def _iter_kb_files(kb_root: Path) -> list[Path]:
    """Return all .md files in kb_root excluding README.md and the script.

    Args:
        kb_root: Root directory to scan.

    Returns:
        Sorted list of Path objects.
    """
    excluded = {kb_root / "README.md", kb_root / "knowledge-explorer.py"}
    result: list[Path] = []
    for category_dir in sorted(kb_root.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue
        result.extend(md_file for md_file in sorted(category_dir.glob("*.md")) if md_file not in excluded)
    return result


def build_tree(kb_root: Path) -> list[KBEntry]:
    """Scan kb_root and return all successfully parsed entries.

    Args:
        kb_root: Root directory to scan.

    Returns:
        List of KBEntry objects; parse failures are silently skipped.
    """
    entries: list[KBEntry] = []
    for path in _iter_kb_files(kb_root):
        with contextlib.suppress(KBError):
            entries.append(parse_entry(path))
    return entries


def write_entry(entry: KBEntry, path: Path) -> None:
    """Write a KBEntry to disk in frontmatter format atomically.

    Args:
        entry: Entry to serialize.
        path: Destination file path.
    """
    post = entry_to_post(entry)
    content = frontmatter.dumps(post, handler=_handler)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def migrate_entry(entry: KBEntry) -> KBEntry:
    """Return a copy of the entry ready for serialization in skill-spec format.

    Preserves all fields. Sets ``has_frontmatter=True`` so the caller knows the
    entry will be written in frontmatter format.

    Args:
        entry: Entry in any format.

    Returns:
        Entry ready for serialization as skill-compatible frontmatter.
    """
    return KBEntry(
        topic=entry.topic,
        name=entry.name,
        description=entry.description,
        category=entry.category,
        source_url=entry.source_url,
        verified=entry.verified,
        next_review=entry.next_review,
        github=entry.github,
        version=entry.version,
        license=entry.license,
        tags=entry.tags,
        file_path=entry.file_path,
        body=entry.body,
        has_frontmatter=True,
    )


def _infer_category(meta: GitHubMetadata) -> str | None:
    """Infer a VALID_CATEGORIES category from GitHub repo topics.

    Args:
        meta: GitHubMetadata fetched from GitHub API.

    Returns:
        Matching category string, or None if no topic matches.
    """
    for topic in meta.topics:
        if topic in VALID_CATEGORIES:
            return topic
    return None


def build_draft(repo_slug: str, meta: GitHubMetadata, category: str) -> KBEntry:
    """Construct a draft KBEntry from GitHub metadata.

    Args:
        repo_slug: 'owner/repo' slug.
        meta: GitHubMetadata fetched from GitHub API.
        category: Resolved category (must be a member of VALID_CATEGORIES).

    Returns:
        Draft KBEntry with the provided category.
    """
    topic_slug = re.sub(r"[^a-z0-9-]", "-", meta.name.lower()).strip("-")
    today = datetime.now(tz=UTC).date()

    raw_desc = (meta.description or "").strip()
    description = raw_desc or f"Research entry for {meta.name}. Use when working with {meta.name} or related tools."

    return KBEntry(
        topic=topic_slug,
        name=meta.name,
        description=description,
        category=category,
        source_url=f"https://github.com/{repo_slug}",
        verified=today,
        next_review=today + timedelta(days=_DEFAULT_REVIEW_DAYS),
        github=repo_slug,
        version=meta.latest_tag,
        license=meta.license,
        tags=[t for t in meta.topics if t in VALID_CATEGORIES],
        file_path=KB_ROOT / category / f"{topic_slug}.md",
        body=f"> {meta.description}\n\n<!-- DRAFT: Review category and tags, then run: ./knowledge-explorer.py add <this-file> -->",
        has_frontmatter=True,
    )


# ---------------------------------------------------------------------------
# Layer 4: Serializers
# ---------------------------------------------------------------------------


def entry_to_post(entry: KBEntry) -> frontmatter.Post:
    """Serialize a KBEntry to a frontmatter.Post in skill-spec format.

    Top-level keys: ``name``, ``description``, ``license`` (if set).
    All KB tracking fields go into the ``metadata`` sub-mapping with string values.
    Date fields are serialized as ISO date strings. Tags are serialized as a
    comma-separated string, or omitted when empty.

    Args:
        entry: Entry to serialize.

    Returns:
        frontmatter.Post with ordered metadata and body.
    """
    meta: CommentedMap = CommentedMap()

    # Top-level Agent Skills spec fields
    meta["name"] = entry.name
    meta["description"] = entry.description
    if entry.license is not None:
        meta["license"] = entry.license

    # KB fields in metadata sub-mapping (all string values)
    inner: CommentedMap = CommentedMap()
    inner["topic"] = entry.topic
    inner["category"] = entry.category
    inner["source_url"] = entry.source_url
    if entry.github is not None:
        inner["github"] = entry.github
    if entry.version is not None:
        inner["version"] = DoubleQuotedScalarString(entry.version)
    # Dates serialized as ISO strings (not YAML date objects)
    inner["verified"] = DoubleQuotedScalarString(str(entry.verified))
    inner["next_review"] = DoubleQuotedScalarString(str(entry.next_review))
    if entry.tags:
        inner["tags"] = DoubleQuotedScalarString(",".join(entry.tags))
    if entry.layer is not None:
        inner["layer"] = DoubleQuotedScalarString(entry.layer)
    if entry.language is not None:
        inner["language"] = entry.language
    if entry.stack is not None:
        inner["stack"] = entry.stack

    meta["metadata"] = inner

    return frontmatter.Post(entry.body, handler=_handler, **meta)


def format_update_block(content: str, today: date) -> str:
    """Format an update section block.

    Args:
        content: Update content text.
        today: Date to label the section.

    Returns:
        Formatted markdown update block.
    """
    return f"\n\n## Update: {today.isoformat()}\n\n{content.strip()}"


# ---------------------------------------------------------------------------
# Name validation (Agent Skills spec)
# ---------------------------------------------------------------------------


def validate_name(name: str) -> bool:
    """Check whether a name satisfies the Agent Skills spec constraints.

    Rules:
    - 1-64 characters
    - Lowercase alphanumeric characters and hyphens only
    - No leading or trailing hyphen
    - No consecutive hyphens

    Args:
        name: Kebab-case slug to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not name or len(name) > _NAME_MAX_LEN:
        return False
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        return False
    return "--" not in name


# ---------------------------------------------------------------------------
# Levenshtein distance for suggestions
# ---------------------------------------------------------------------------


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Integer edit distance.
    """
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for ch_a in a:
        curr = [prev[0] + 1]
        for j, ch_b in enumerate(b):
            curr.append(min(prev[j] + (ch_a != ch_b), curr[-1] + 1, prev[j + 1] + 1))
        prev = curr
    return prev[-1]


def _find_suggestions(topic: str, all_topics: list[str]) -> list[str]:
    """Find close topic slug suggestions using Levenshtein distance.

    Args:
        topic: The requested topic slug.
        all_topics: All known topic slugs.

    Returns:
        Up to 3 suggestions with distance <= 2.
    """
    candidates = [t for t in all_topics if _levenshtein(topic, t) <= _LEVENSHTEIN_MAX_DISTANCE]
    return sorted(candidates, key=lambda t: _levenshtein(topic, t))[:_MAX_SUGGESTIONS]


# ---------------------------------------------------------------------------
# Helper: first paragraph extraction
# ---------------------------------------------------------------------------


def _extract_first_paragraph(body: str) -> str:
    """Extract the first non-heading, non-blank paragraph from body text.

    Args:
        body: Markdown body text.

    Returns:
        First paragraph text, or empty string.
    """
    in_para = False
    para_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith("#"):
            if in_para:
                break
            continue
        in_para = True
        para_lines.append(stripped)
    return " ".join(para_lines)


# ---------------------------------------------------------------------------
# Rich helper
# ---------------------------------------------------------------------------


def _show_error(message: str, *, verbose: bool = False, exc: BaseException | None = None) -> None:
    """Display an error panel on stderr.

    Args:
        message: Error message to display.
        verbose: If True and exc is provided, print traceback.
        exc: Exception to optionally print traceback for.
    """
    err_console.print(Panel(message, title="Error", border_style="red", expand=False))
    if verbose and exc is not None:
        err_console.print_exception()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _auto_description(entry: KBEntry) -> tuple[str, str | None]:
    """Compute a description for an entry that has none, with a warning message.

    Args:
        entry: Entry whose description is empty or missing.

    Returns:
        Tuple of (description, warning_message). warning_message is None when no
        auto-generation was necessary.
    """
    first_para = _extract_first_paragraph(entry.body)
    if first_para:
        desc = first_para
        warn = "description not set; auto-generated from body first paragraph."
    else:
        desc = f"Research entry for {entry.name}. Use when working with {entry.name} or related tools."
        warn = "description not set; using auto-generated fallback. Consider adding a description."
    return desc, warn


def _validate_add_entry(entry: KBEntry) -> str | None:
    """Run all add-command validations on entry.

    Returns an error string (exit code 2) or None when valid.
    Mutates entry.description if it was empty.

    Args:
        entry: Entry to validate.

    Returns:
        Error message string, or None when the entry is valid.
    """
    if not validate_name(entry.topic):
        return (
            f"Topic '{entry.topic}' is not a valid Agent Skills name.\n"
            "Must be 1-64 chars, lowercase alphanumeric + hyphens, "
            "no leading/trailing/consecutive hyphens."
        )
    if entry.category not in VALID_CATEGORIES:
        return f"Invalid category '{entry.category}'.\nValid categories: {', '.join(sorted(VALID_CATEGORIES))}"
    missing = [
        f for f in ("topic", "name", "category", "source_url", "verified", "next_review") if not getattr(entry, f, None)
    ]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="knowledge-explorer", help="Manage the research/ knowledge base.", no_args_is_help=False, add_completion=False
)

_verbose_state: dict[str, bool] = {"verbose": False}


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show tracebacks on error.")] = False,
) -> None:
    """Knowledge base explorer. Run without a subcommand to list entries.

    Args:
        ctx: Typer context.
        verbose: Enable verbose error output.
    """
    _verbose_state["verbose"] = verbose
    if ctx.invoked_subcommand is None:
        list_kb()


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


@app.command("list")
def list_kb(
    layer: Annotated[str | None, typer.Option("--layer", "-l", help="Filter by SDLC layer (0, 1, or 2)")] = None,
) -> None:
    """Show a tree view of all knowledge base entries.

    Displays category summaries with entry count and overdue count,
    plus per-entry version, verified date, review date, and overdue status.
    Use --layer to filter by SDLC layer (0=process, 1=language, 2=stack).
    """
    entries = build_tree(KB_ROOT)
    if layer is not None:
        entries = [e for e in entries if e.layer == layer]
    if not entries:
        console.print("[yellow]No entries found in knowledge base.[/yellow]")
        return

    # Group by category
    by_category: dict[str, list[KBEntry]] = {}
    for entry in entries:
        by_category.setdefault(entry.category, []).append(entry)

    tree = Tree("[bold blue]research/[/bold blue]")
    for cat in sorted(by_category):
        cat_entries = sorted(by_category[cat], key=lambda e: e.file_path.name)
        overdue_count = sum(1 for e in cat_entries if e.is_overdue)
        cat_label = f"[cyan]{cat}/[/cyan]  [dim]({len(cat_entries)} entries, {overdue_count} overdue)[/dim]"
        cat_branch = tree.add(cat_label)
        for entry in cat_entries:
            version_str = entry.version or "no version"
            overdue_str = " [red][OVERDUE][/red]" if entry.is_overdue else ""
            label = (
                f"[green]{entry.file_path.name}[/green]"
                f"  {version_str}"
                f"  [dim]verified {entry.verified.isoformat()}"
                f"  review {entry.next_review.isoformat()}[/dim]"
                f"{overdue_str}"
            )
            cat_branch.add(label)

    # Measure and print
    temp_con = Console(width=9999)
    measurement = Measurement.get(temp_con, temp_con.options, tree)
    tree_width = int(measurement.maximum)
    console.print(tree, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True, width=max(tree_width, 80))


# ---------------------------------------------------------------------------
# sync-readme command
# ---------------------------------------------------------------------------


@app.command("sync-readme")
def sync_readme(
    read_only: Annotated[
        bool,
        typer.Option(
            "--check", help="Report missing/stale README links without writing. Exits non-zero when drift is found."
        ),
    ] = False,
) -> None:
    """Reconcile README index links with markdown files under research/."""
    result = reconcile_readme_index(KB_ROOT, write=not read_only)
    has_drift = bool(result.missing_links or result.stale_links)

    if result.added_rows:
        console.print(f"[green]Added {result.added_rows} missing README row(s).[/green]")
    if result.created_sections:
        console.print(f"[green]Created sections:[/green] {', '.join(result.created_sections)}")
    if result.stale_links:
        console.print("[yellow]Stale README links (no matching file):[/yellow]")
        for stale in result.stale_links:
            console.print(f"  - {stale}")
    if read_only and has_drift:
        if result.missing_links:
            console.print("[yellow]Missing README links:[/yellow]")
            for missing in result.missing_links:
                console.print(f"  - {missing}")
        raise typer.Exit(code=1)
    if not has_drift:
        console.print("[green]README index is in sync.[/green]")


# ---------------------------------------------------------------------------
# show-template command
# ---------------------------------------------------------------------------


@app.command("show-template")
def show_template() -> None:
    """Print the skill-spec compatible frontmatter template with body structure."""
    today = datetime.now(tz=UTC).date()
    next_review = today + timedelta(days=_DEFAULT_REVIEW_DAYS)
    cats_comment = f"# one of: {', '.join(sorted(VALID_CATEGORIES))}"
    template = (
        "---\n"
        "name: kebab-case-identifier\n"
        "description: >-\n"
        "  Verified reference for <topic>. Use when configuring or working with\n"
        "  <topic> in deployments. Max 1024 chars.\n"
        "license: MIT\n"
        "metadata:\n"
        "  topic: kebab-case-identifier\n"
        f"  category: category-dir-name  {cats_comment}\n"
        "  source_url: https://...\n"
        "  github: owner/repo\n"
        '  version: "1.0.0"\n'
        f'  verified: "{today.isoformat()}"\n'
        f'  next_review: "{next_review.isoformat()}"\n'
        '  tags: "tag1,tag2"\n'
        '  # layer: "0" | "1" | "2"  # SDLC layer (optional)\n'
        "  # language: python | typescript | ...  # optional\n"
        "  # stack: fastapi | tornado | ...  # optional\n"
        "---\n"
        "\n"
        "# Display Name\n"
        "\n"
        "[Body content here — body must not repeat the inline header block or include a Freshness Tracking table]\n"
    )
    syntax = Syntax(template, "yaml", theme="monokai", line_numbers=False)
    console.print(syntax)


# ---------------------------------------------------------------------------
# fetch-github command
# ---------------------------------------------------------------------------


def _resolve_fetch_category(meta: GitHubMetadata, category: str | None) -> str:
    """Resolve category: explicit > inferred from topics > prompt user.

    Returns:
        Resolved category string from VALID_CATEGORIES.
    """
    if category is not None:
        return category
    inferred = _infer_category(meta)
    if inferred is not None:
        console.print(f"[dim]Category inferred from GitHub topics:[/dim] [cyan]{inferred}[/cyan]")
        return inferred
    valid_sorted = sorted(VALID_CATEGORIES)
    console.print(
        f"[yellow]No matching category found in GitHub topics.[/yellow]\nValid categories: {', '.join(valid_sorted)}"
    )
    while True:
        chosen = typer.prompt("Enter category")
        if chosen in VALID_CATEGORIES:
            return chosen
        console.print(f"[red]'{chosen}' is not a valid category.[/red] Choose from: {', '.join(valid_sorted)}")


def _fetch_readme_text(repo_slug: str) -> str:
    """Fetch README content from GitHub. Returns placeholder on failure.

    Returns:
        README content as string, or placeholder if not available.
    """
    try:
        gh = _get_github()
        gh_repo = gh.get_repo(repo_slug)
        readme = gh_repo.get_readme()
        return readme.decoded_content.decode("utf-8")
    except (ExternalCommandError, GithubException):
        return "<!-- README not available -->"


def _assemble_fetch_draft(repo_slug: str, meta: GitHubMetadata, category: str, readme_text: str) -> str:
    """Build draft entry and return serialized frontmatter content.

    Returns:
        Serialized frontmatter string with body and metadata.
    """
    entry = build_draft(repo_slug, meta, category)
    body_parts = [
        f"# {entry.name}",
        "",
        f"> {meta.description}",
        "",
        "<!-- DRAFT: Review category and tags, then run: ./knowledge-explorer.py add <this-file> -->",
        "",
        readme_text,
    ]
    if meta.has_docs_dir and meta.docs_files:
        doc_lines = "\n".join(meta.docs_files)
        body_parts.extend(["", "<!-- docs/ files found (fetch manually if needed):", doc_lines, "-->"])
    entry.body = "\n".join(body_parts)
    post = entry_to_post(entry)
    return frontmatter.dumps(post, handler=_handler)


@app.command("fetch-github")
def fetch_github(
    repo: Annotated[str, typer.Argument(help="owner/repo slug")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write draft to file")] = None,
    category: Annotated[str | None, typer.Option("--category", "-c", help="Override inferred category")] = None,
) -> None:
    """Fetch README and docs/ from GitHub and output a draft entry.

    Args:
        repo: GitHub 'owner/repo' slug.
        output: Optional file path to write draft to.
        category: Override inferred category.
    """
    verbose = _verbose_state["verbose"]
    try:
        if category is not None and category not in VALID_CATEGORIES:
            _show_error(f"Invalid category '{category}'.\nValid categories: {', '.join(sorted(VALID_CATEGORIES))}")
            raise typer.Exit(code=2)

        with console.status(f"Fetching metadata for [cyan]{repo}[/cyan]..."):
            meta = fetch_github_metadata(repo)

        resolved_category = _resolve_fetch_category(meta, category)
        readme_text = _fetch_readme_text(repo)
        draft_content = _assemble_fetch_draft(repo, meta, resolved_category, readme_text)

        if output is not None:
            tmp = output.with_suffix(".tmp")
            tmp.write_text(draft_content, encoding="utf-8")
            tmp.replace(output)
            console.print(f"[green]OK[/green] Draft written to [green]{output}[/green]")
        else:
            console.print(draft_content)

    except KBError as exc:
        _show_error(str(exc), verbose=verbose, exc=exc)
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# update-append command
# ---------------------------------------------------------------------------


@app.command("update-append")
def update_append(topic: Annotated[str, typer.Argument(help="kebab-case topic slug")]) -> None:
    """Find entry by topic, open editor for update content, append section.

    Args:
        topic: Kebab-case topic slug to find and update.
    """
    verbose = _verbose_state["verbose"]
    try:
        path = find_entry_by_topic(topic, KB_ROOT)
        if path is None:
            entries = build_tree(KB_ROOT)
            all_topics = [e.topic for e in entries]
            suggestions = _find_suggestions(topic, all_topics)
            raise TopicNotFoundError(topic=topic, suggestions=suggestions)

        entry = parse_entry(path)

        # Migrate if needed
        if not entry.has_frontmatter:
            entry = migrate_entry(entry)
            write_entry(entry, path)
            entry = parse_entry(path)

        # Open editor
        template = "<!-- Replace this with your update content -->"
        update_content = typer.edit(template) or ""
        if not update_content.strip() or update_content.strip() == template.strip():
            console.print("[yellow]No update content provided. Aborted.[/yellow]")
            raise typer.Exit(code=0)

        today = datetime.now(tz=UTC).date()
        update_block = format_update_block(update_content, today)

        # Update frontmatter dates
        entry.verified = today
        entry.next_review = today + timedelta(days=_DEFAULT_REVIEW_DAYS)
        entry.body = entry.body.rstrip() + update_block

        write_entry(entry, path)
        rel = path.relative_to(KB_ROOT)
        console.print(f"[green]OK[/green] Updated [green]{rel}[/green]")

    except KBError as exc:
        _show_error(str(exc), verbose=verbose, exc=exc)
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# add command
# ---------------------------------------------------------------------------


@app.command("add")
def add(
    file: Annotated[Path | None, typer.Argument(help="Entry file with frontmatter; omit to read stdin")] = None,
) -> None:
    """Read a frontmatter entry and add it to the knowledge base.

    Validates, routes to the correct category directory, and updates README.md.

    Args:
        file: Path to entry file. Reads stdin if omitted.
    """
    verbose = _verbose_state["verbose"]
    try:
        text = file.read_text(encoding="utf-8") if file is not None else sys.stdin.read()

        # Pre-write validation
        if _detect_format_safe(text) != "frontmatter":
            _show_error(
                "Input is not in frontmatter format.\n"
                "Run [bold]./knowledge-explorer.py show-template[/bold] to see the required format."
            )
            raise typer.Exit(code=1)

        entry = parse_frontmatter_entry(text, file or Path("<stdin>"))

        # Warn (don't error) if description is missing — auto-generate from body
        if not entry.description.strip():
            entry.description, warn = _auto_description(entry)
            console.print(f"[yellow]Warning:[/yellow] {warn}")

        # Validate all fields; returns error string or None
        err = _validate_add_entry(entry)
        if err:
            _show_error(err)
            raise typer.Exit(code=2)

        # Determine target path
        target_dir = KB_ROOT / entry.category
        target_path = target_dir / f"{entry.topic}.md"

        # Check for conflicts
        if target_path.exists():
            existing = parse_entry(target_path)
            if existing.topic != entry.topic:
                raise TopicConflictError(target_path=target_path, existing_topic=existing.topic, new_topic=entry.topic)

        # Ensure category directory exists
        if not KB_ROOT.exists():
            _show_error(f"KB_ROOT does not exist: {KB_ROOT}")
            raise typer.Exit(code=1)
        target_dir.mkdir(parents=False, exist_ok=True)

        write_entry(entry, target_path)

        try:
            update_readme(KB_ROOT, entry)
        except ReadmeUpdateError as exc:
            console.print(f"[yellow]Warning: README update failed: {exc}[/yellow]")

        rel = target_path.relative_to(KB_ROOT)
        console.print(f"[green]OK[/green] Added [green]{rel}[/green]")

    except KBError as exc:
        _show_error(str(exc), verbose=verbose, exc=exc)
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# migrate command
# ---------------------------------------------------------------------------


def _migrate_frontmatter_path(path: Path, text: str, dry_run: bool, result: MigrationResult) -> None:
    """Migrate a single frontmatter file from old flat format to skill-spec.

    Skips files already in new format. Appends to result in-place.

    Args:
        path: Path to the file being processed.
        text: Raw file content.
        dry_run: When True, log intent without writing.
        result: MigrationResult to update in-place.
    """
    try:
        post = frontmatter.loads(text, handler=_handler)
    except (ValueError, KeyError, TypeError) as yaml_exc:
        result.failed.append((path, f"YAML parse error: {yaml_exc}"))
        return

    if _is_new_skill_format(post.metadata):
        result.already_migrated.append(path)
        return

    try:
        entry = parse_frontmatter_entry(text, path)
    except KBError as exc:
        result.failed.append((path, str(exc)))
        return

    if entry.category not in VALID_CATEGORIES:
        result.failed.append((path, f"Unknown category '{entry.category}'"))
        return

    migrated = migrate_entry(entry)
    rel = path.relative_to(KB_ROOT)
    if dry_run:
        console.print(f"[yellow]Would upgrade[/yellow] {rel} [dim](flat frontmatter -> skill-spec)[/dim]")
    else:
        write_entry(migrated, path)
        console.print(f"[green]Upgraded[/green] {rel} [dim](flat frontmatter -> skill-spec)[/dim]")
    result.migrated.append(path)


def _migrate_inline_path(path: Path, text: str, dry_run: bool, result: MigrationResult) -> None:
    """Migrate a single inline-header file to skill-spec frontmatter.

    Appends to result in-place.

    Args:
        path: Path to the file being processed.
        text: Raw file content.
        dry_run: When True, log intent without writing.
        result: MigrationResult to update in-place.
    """
    try:
        entry = parse_inline_header_entry(text, path)
    except KBError as exc:
        result.failed.append((path, str(exc)))
        return

    if entry.category not in VALID_CATEGORIES:
        result.failed.append((path, f"Unknown category '{entry.category}'"))
        return

    migrated = migrate_entry(entry)
    rel = path.relative_to(KB_ROOT)
    if dry_run:
        console.print(f"[yellow]Would migrate[/yellow] {rel} [dim](inline-header -> skill-spec)[/dim]")
    else:
        write_entry(migrated, path)
        console.print(f"[green]Migrated[/green] {rel} [dim](inline-header -> skill-spec)[/dim]")
    result.migrated.append(path)


def _is_new_skill_format(meta: dict[str, Any]) -> bool:
    """Return True when frontmatter already uses the new skill-spec layout.

    The new format has a ``metadata`` sub-mapping containing ``topic``.

    Args:
        meta: Parsed frontmatter metadata dict.

    Returns:
        True if already in new skill-spec format.
    """
    inner = meta.get("metadata")
    return isinstance(inner, dict) and "topic" in inner


@app.command("migrate")
def migrate(
    all_entries: Annotated[bool, typer.Option("--all", help="Migrate all entries (default behaviour)")] = True,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change without writing")] = False,
) -> None:
    """Migrate entries to skill-spec compatible frontmatter format in-place.

    Handles two source formats:
    - Inline-header (``# Heading`` + bold/table fields) → skill-spec frontmatter
    - Old flat frontmatter (top-level KB fields) → skill-spec frontmatter (fields
      moved into ``metadata`` sub-mapping)

    Entries already in skill-spec format are skipped.

    Args:
        all_entries: Migrate all entries (default).
        dry_run: Show what would change without writing.
    """
    verbose = _verbose_state["verbose"]
    result = MigrationResult()

    for path in _iter_kb_files(KB_ROOT):
        try:
            text = path.read_text(encoding="utf-8")
            fmt = _detect_format_safe(text)

            if fmt == "frontmatter":
                _migrate_frontmatter_path(path, text, dry_run, result)
            elif fmt == "inline-header":
                _migrate_inline_path(path, text, dry_run, result)
            else:
                result.failed.append((path, "Unrecognised format"))

        except KBError as exc:
            result.failed.append((path, str(exc)))
            if verbose:
                err_console.print(f"[red]Failed[/red] {path}: {exc}")

    console.print(
        f"\nMigrated: [green]{len(result.migrated)}[/green]  "
        f"Already done: [blue]{len(result.already_migrated)}[/blue]  "
        f"Failed: [red]{len(result.failed)}[/red]"
    )
    if result.failed:
        for fail_path, reason in result.failed:
            console.print(f"  [red]FAILED[/red] {fail_path.relative_to(KB_ROOT)}: {reason}")


# ---------------------------------------------------------------------------
# list-candidates command
# ---------------------------------------------------------------------------

_BAD_DESCRIPTION_PREFIX_RE: re.Pattern[str] = re.compile(
    r"^(Research on|Notes on|Information about|Overview of)\s", re.IGNORECASE
)


def _is_bad_description(entry: KBEntry) -> bool:
    """Return True if entry description matches any bad-description heuristic.

    Args:
        entry: Entry to evaluate.

    Returns:
        True if description is considered bad quality.
    """
    desc = entry.description.strip()
    if not desc:
        return True
    if desc.endswith("..."):
        return True
    if _BAD_DESCRIPTION_PREFIX_RE.match(desc):
        return True
    # Check if description equals or is a leading substring of first body paragraph
    first_para = _extract_first_paragraph(entry.body)
    return bool(first_para and first_para.startswith(desc))


@app.command("list-candidates")
def list_candidates(
    all_entries: Annotated[
        bool, typer.Option("--all", help="Include every entry regardless of description quality.")
    ] = False,
) -> None:
    """Scan all KB entries and output JSON array of description candidates.

    Without --all, applies bad-description heuristics to identify entries
    whose descriptions need improvement. With --all, includes every entry.

    Args:
        all_entries: Skip heuristics and include every entry.
    """
    entries = build_tree(KB_ROOT)
    repo_root = KB_ROOT.parent

    candidates: list[dict[str, object]] = []
    for entry in entries:
        if not all_entries and not _is_bad_description(entry):
            continue
        try:
            rel_path = str(entry.file_path.relative_to(repo_root))
        except ValueError:
            rel_path = str(entry.file_path)
        candidates.append({
            "topic": entry.topic,
            "file_path": rel_path,
            "name": entry.name,
            "category": entry.category,
            "tags": entry.tags,
            "current_description": entry.description,
            "body": entry.body,
        })

    sys.stdout.write(json.dumps(candidates, indent=2, ensure_ascii=False))
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# set-description command
# ---------------------------------------------------------------------------


@app.command("set-description")
def set_description(
    topic: Annotated[str, typer.Argument(help="Kebab-case topic slug.")],
    description: Annotated[str, typer.Argument(help="New description text.")],
) -> None:
    """Find entry by topic slug and set its description field.

    Validates the description, then writes the entry atomically.
    Exits with code 1 if topic not found, code 2 on validation failure.

    Args:
        topic: Kebab-case topic slug to locate.
        description: New description to apply.
    """
    verbose = _verbose_state["verbose"]

    # Validate description before doing any I/O
    if not description.strip():
        err_console.print("Error: description must not be empty.")
        raise typer.Exit(code=2)
    if "\n" in description:
        err_console.print("Error: description must not contain newlines.")
        raise typer.Exit(code=2)
    try:
        path = find_entry_by_topic(topic, KB_ROOT)
        if path is None:
            entries = build_tree(KB_ROOT)
            all_topics = [e.topic for e in entries]
            suggestions = _find_suggestions(topic, all_topics)
            raise TopicNotFoundError(topic=topic, suggestions=suggestions)

        entry = parse_entry(path)
        if not entry.has_frontmatter:
            entry = migrate_entry(entry)

        entry.description = description
        write_entry(entry, path)

    except KBError as exc:
        _show_error(str(exc), verbose=verbose, exc=exc)
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt as exc:
        err_console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=130) from exc
