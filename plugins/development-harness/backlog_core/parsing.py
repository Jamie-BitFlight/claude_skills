"""Backlog parsing, item search, slug generation, body section utilities.

Extracted from ``backlog.py`` — pure functions with no GitHub or typer dependencies.
"""

from __future__ import annotations

import difflib
import io
import logging
import operator
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

from ruamel.yaml import YAML, YAMLError

# ---------------------------------------------------------------------------
# Imports from sibling models module
# ---------------------------------------------------------------------------
from . import models as _models
from .models import (
    BENEFIT_MAP,
    COMMIT_PREFIX_RE as _COMMIT_PREFIX_RE,
    FUZZY_DUPLICATE_THRESHOLD,
    GITHUB_ISSUE_URL_RE,
    MIN_FRONTMATTER_PARTS,
    ROLE_MAP,
    SECTION_HEADING_ALIAS,
    SKIP_STATUS,
    BacklogItem,
    Entry,
    GroomedData,
    SamTask,
    Section,
    ViewItemResult,
    parse_issue_number,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "build_body_extra_only",
    "build_issue_body",
    "build_issue_body_from_file",
    "build_sam_task_body",
    "build_sam_task_issue_title",
    "dump_frontmatter",
    "extract_description_from_issue_body",
    "extract_groomed_section",
    "extract_normalize_metadata",
    "extract_sections",
    "find_fuzzy_duplicates",
    "find_item",
    "infer_type",
    "items_needing_issues",
    "items_with_issues",
    "loads_frontmatter",
    "merge_sections",
    "normalize_issue_title",
    "now_iso",
    "parse_backlog",
    "parse_backlog_from_directory",
    "parse_issue_selector",
    "parse_item_file",
    "parse_md_body_sections",
    "parse_sam_task_metadata",
    "title_to_slug",
    "today",
    "view_result_from_local_item",
]


# ---------------------------------------------------------------------------
# Ruamel-based frontmatter helpers (replaces python-frontmatter dependency)
# ---------------------------------------------------------------------------


class _MdPost:
    """Lightweight container for legacy .md frontmatter + body.

    Replaces ``frontmatter.Post`` for the legacy .md code paths.
    Both attributes are mutable so callers can patch them before serialising.
    """

    def __init__(self, metadata: dict[str, str | dict[str, str]], content: str) -> None:
        """Initialize post with parsed metadata dict and body content."""
        self.metadata: dict[str, str | dict[str, str]] = metadata
        self.content: str = content


def _make_yaml() -> YAML:
    """Return a configured ruamel.yaml round-trip instance.

    Returns:
        YAML instance with wide width to prevent unwanted line-wrapping.
    """
    y = YAML(typ="rt")
    y.width = sys.maxsize
    y.preserve_quotes = False
    return y


def _validate_metadata(raw: dict[str, Any]) -> dict[str, str | dict[str, str]]:
    """Coerce raw YAML metadata values to ``str`` or ``dict[str, str]`` at the parse boundary.

    YAML can produce integers, booleans, lists, or ``None`` for any scalar field.
    This function ensures every value is either a plain string or a shallow mapping
    of strings to strings before the metadata dict reaches any consumer.

    - Scalar values (int, float, bool, None, list, …) are coerced to ``str``.
    - Mapping values have their own values coerced to ``str`` (one level deep).

    Args:
        raw: The raw metadata dict produced by the YAML parser.

    Returns:
        A new dict with all values typed as ``str | dict[str, str]``.
    """
    result: dict[str, str | dict[str, str]] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[str(k)] = {str(dk): str(dv) for dk, dv in v.items()}
        else:
            result[str(k)] = str(v) if v is not None else ""
    return result


def loads_frontmatter(text: str) -> _MdPost:
    """Parse frontmatter + body from a markdown string using ruamel.yaml.

    Raises ``YAMLError`` when the frontmatter block contains invalid YAML so
    callers can distinguish corrupt input from absent frontmatter.

    Args:
        text: Markdown string with optional ``---``-delimited YAML frontmatter.

    Returns:
        ``_MdPost`` with *metadata* dict and *content* body string.

    Raises:
        YAMLError: When the frontmatter block is present but contains invalid YAML.
    """
    parts = text.split("---", 2)
    if len(parts) < MIN_FRONTMATTER_PARTS:
        return _MdPost({}, text)
    y = _make_yaml()
    raw = y.load(parts[1]) or {}
    metadata = _validate_metadata(dict(raw) if raw else {})
    return _MdPost(metadata, parts[2].strip())


def dump_frontmatter(post: _MdPost) -> str:
    """Serialise a ``_MdPost`` back to a markdown string with ``---`` delimiters.

    Args:
        post: Post object with *metadata* dict and *content* body string.

    Returns:
        Markdown string with YAML frontmatter block followed by the body.
    """
    y = _make_yaml()
    buf = io.StringIO()
    y.dump(dict(post.metadata), buf)
    fm_text = buf.getvalue()
    body = post.content.strip()
    return f"---\n{fm_text}---\n\n{body}\n"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def today() -> str:
    """Return current UTC date as YYYY-MM-DD string."""
    return datetime.now(UTC).strftime("%Y-%m-%d")


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string for last_synced tracking."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Slug / title helpers
# ---------------------------------------------------------------------------


def title_to_slug(title: str, max_len: int = 60) -> str:
    """Convert item title to filename slug.

    Returns:
        Slug string suitable for filenames.
    """
    # Strip strikethrough and status suffixes
    t = re.sub(r"^~~(.+)~~\s*(RESOLVED|COMPLETED)?\s*$", r"\1", title.strip())
    t = t.lower()
    t = re.sub(r"[:\[\]\(\)]", " ", t)
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t[:max_len] if len(t) > max_len else t


def normalize_issue_title(title: str) -> str:
    """Strip conventional-commit prefix and normalize for dedup comparison.

    Returns:
        Lowercased title with any ``feat:``/``fix:``/etc. prefix removed.

    Examples:
        >>> normalize_issue_title("feat: SAM: Error Recovery")
        'sam: error recovery'
        >>> normalize_issue_title("SAM: Error Recovery")
        'sam: error recovery'
    """
    return _COMMIT_PREFIX_RE.sub("", title).strip().lower()


def infer_type(description: str, title: str) -> str:
    """Infer issue type label from description and title keywords.

    Returns:
        Type label string (e.g. ``"type:bug"``, ``"type:feature"``).
    """
    text = f"{title} {description}".lower()
    if any(w in text for w in ("fix", "bug", "broken", "vulnerability")):
        return "type:bug"
    if any(w in text for w in ("add", "create", "implement", "build")):
        return "type:feature"
    if any(w in text for w in ("refactor", "remove dead", "consolidate")):
        return "type:refactor"
    if any(w in text for w in ("document", "update readme", "docs")):
        return "type:docs"
    return "type:feature"


# ---------------------------------------------------------------------------
# Selector parsing
# ---------------------------------------------------------------------------


def parse_issue_selector(selector: str) -> str | None:
    """Extract issue number from selector (URL, #N, or bare number).

    Supports:
      - ``https://github.com/owner/repo/issues/123``
      - ``#123``
      - ``123`` (bare number)

    Returns:
        Issue number as string (e.g. ``"123"``) or None if not an issue ref.
    """
    selector = selector.strip()
    # URL form: https://github.com/owner/repo/issues/123
    url_match = GITHUB_ISSUE_URL_RE.search(selector)
    if url_match:
        return url_match.group(2)
    # #N form
    if selector.startswith("#"):
        n = parse_issue_number(selector)
        if n is not None:
            return str(n)
    # Bare number form
    if selector.isdigit():
        return selector
    return None


# ---------------------------------------------------------------------------
# Item file parsing
# ---------------------------------------------------------------------------


def _fm_str(fm: dict[str, str | dict[str, str]], meta: dict[str, str], key: str, fm_key: str = "") -> str:
    """Resolve a string field from metadata dict with frontmatter fallback.

    Returns:
        Resolved string value, or empty string if not found.
    """
    return str(meta.get(key) or fm.get(fm_key or key) or "")


def _parse_frontmatter(text: str) -> tuple[dict[str, str | dict[str, str]], dict[str, str], str]:
    """Parse frontmatter and metadata from item text.

    ``loads_frontmatter`` guarantees all metadata values are ``str`` or
    ``dict[str, str]`` via ``_validate_metadata``, so no further coercion is
    needed here.

    Returns:
        Tuple of (frontmatter_dict, metadata_dict, body_text).
    """
    try:
        post = loads_frontmatter(text)
        fm: dict[str, str | dict[str, str]] = post.metadata or {}
        body: str = post.content or ""
    except YAMLError:
        # Structural YAML corruption (e.g. duplicate keys, bad anchors) cannot be
        # recovered via text-split; propagate so callers can log and skip the file.
        raise
    except (ValueError, KeyError, TypeError):
        parts = text.split("---", 2)
        fm, body = {}, parts[2].strip() if len(parts) >= MIN_FRONTMATTER_PARTS else text
    meta_raw = fm.get("metadata")
    meta: dict[str, str] = {str(k): str(v) for k, v in meta_raw.items()} if isinstance(meta_raw, dict) else {}
    return fm, meta, body


def parse_item_file(text: str, path: Path) -> BacklogItem:
    """Parse a single per-item backlog file (frontmatter + body). Handles both flat and research-style metadata block.

    Returns:
        BacklogItem with parsed fields from frontmatter and body.
    """
    if not text.startswith("---"):
        return BacklogItem()
    fm, meta, body = _parse_frontmatter(text)
    # Research-style: name, description, metadata.*
    # Flat (legacy): title, source, added, ...
    plan_raw = _fm_str(fm, meta, "plan")
    status_raw = _fm_str(fm, meta, "status")
    groomed = _fm_str(fm, meta, "groomed")
    if not groomed and "## Groomed" in body:
        groomed = "true"
    added_date = _fm_str(fm, meta, "added") or "0000-00-00"
    item = BacklogItem(
        title=str(fm.get("name") or fm.get("title") or ""),
        description=str(fm.get("description") or ""),
        source=_fm_str(fm, meta, "source"),
        added=_fm_str(fm, meta, "added"),
        priority=_fm_str(fm, meta, "priority"),
        issue=_fm_str(fm, meta, "issue"),
        plan="" if plan_raw.upper() == "N/A" else plan_raw,
        type_=meta.get("type", ""),
        topic=meta.get("topic", ""),
        skip=status_raw.upper() in SKIP_STATUS,
        status=status_raw,
        groomed=groomed,
        last_synced=_fm_str(fm, meta, "last_synced"),
    )
    if body:
        item.sections.update(parse_md_body_sections(body, added_date=added_date))
    return item


def _parse_yaml_item_file(path: Path) -> BacklogItem:
    """Load a per-item ``.yaml`` file into a BacklogItem using ruamel.yaml.

    Intentionally does not import from ``yaml_io`` to avoid the circular
    dependency ``yaml_io → parsing → yaml_io``.  The implementation mirrors
    the read path in :func:`yaml_io.load_item`.

    Args:
        path: Path to a ``.yaml`` backlog item file.

    Returns:
        Parsed ``BacklogItem`` with ``file_path`` set.

    Raises:
        YAMLError: On malformed YAML content.
    """
    yaml = YAML(typ="safe")
    with path.open(encoding="utf-8") as fh:
        data = yaml.load(fh)
    item = _models.BacklogItem.model_validate(data)
    item.file_path = str(path.resolve())
    return item


def parse_backlog_from_directory() -> list[BacklogItem]:
    """Parse backlog items directly from ~/.dh/projects/{slug}/backlog/ per-item files.

    Scans the directory, reads frontmatter from each file, and derives the
    priority section from the filename prefix. This is the primary parsing
    path — BACKLOG.md is not required.

    Returns:
        List of BacklogItem instances with section, title, and parsed fields.
    """
    if not _models.get_backlog_dir().exists():
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
    # Collect .yaml files first (new format), then .md files (legacy).
    # When a stem has both .yaml and .md, .yaml takes precedence.
    yaml_files = list(_models.get_backlog_dir().glob("*.yaml"))
    md_files = list(_models.get_backlog_dir().glob("*.md"))
    yaml_stems = {f.stem for f in yaml_files}
    all_files = sorted(yaml_files + [f for f in md_files if f.stem not in yaml_stems])

    items: list[BacklogItem] = []
    for filepath in all_files:
        name = filepath.stem
        section = ""
        for prefix, sec in prefix_to_section.items():
            if name.startswith(prefix):
                section = sec
                break
        try:
            if filepath.suffix == ".yaml":
                item = _parse_yaml_item_file(filepath)
            else:
                item_text = filepath.read_text(encoding="utf-8")
                item = parse_item_file(item_text, filepath)
        except (YAMLError, OSError, ValueError, KeyError) as exc:
            log.warning("Skipping corrupt backlog file %s: %s", filepath, exc)
            continue
        # Filename-derived section; override with metadata if available
        meta_priority = item.priority
        if meta_priority and meta_priority.upper() in {"P0", "P1", "P2"}:
            section = meta_priority.upper()
        item.section = section
        if not item.title:
            item.title = name
        item.file_path = str(filepath)
        if section == "Completed":
            item.skip = True
        items.append(item)
    return items


def parse_backlog() -> list[BacklogItem]:
    """Parse backlog items from ~/.dh/projects/{slug}/backlog/ per-item files.

    Returns:
        List of BacklogItem instances with section, title, and parsed fields.
    """
    return parse_backlog_from_directory()


# ---------------------------------------------------------------------------
# Item search
# ---------------------------------------------------------------------------


def find_item(items: list[BacklogItem], selector: str) -> BacklogItem | None:
    """Find item by title substring, #N, bare number, or GitHub issue URL.

    Supports:
      - ``https://github.com/owner/repo/issues/123`` — extract issue number
      - ``#123`` — match by issue number
      - ``123`` — match by issue number (bare number)
      - ``title substring`` — case-insensitive title match

    Returns:
        Matching BacklogItem or None.
    """
    selector = selector.strip()
    issue_num = parse_issue_selector(selector)
    if issue_num is not None:
        for it in items:
            issue_ref = it.issue or ""
            if str(parse_issue_number(issue_ref)) == issue_num:
                return it
        return None
    # Title substring match (case-insensitive)
    selector_lower = selector.lower()
    matches = [it for it in items if selector_lower in it.title.lower()]
    return matches[0] if len(matches) == 1 else (matches[0] if matches else None)


def find_fuzzy_duplicates(
    title: str, items: list[BacklogItem], threshold: float = FUZZY_DUPLICATE_THRESHOLD
) -> list[tuple[str, float, str]]:
    """Find existing backlog items with titles similar to the given title.

    Uses ``difflib.SequenceMatcher`` on normalized titles (conventional-commit
    prefixes stripped, lowercased) to detect near-duplicates.

    Args:
        title: The new item title to check.
        items: Existing backlog items from ``parse_backlog()``.
        threshold: Similarity ratio (0.0-1.0) above which a match is reported.

    Returns:
        List of ``(existing_title, similarity_ratio, file_path)`` tuples sorted
        by similarity descending. Empty list if no matches above threshold.
    """
    normalized_new = normalize_issue_title(title)
    if not normalized_new:
        return []
    matches: list[tuple[str, float, str]] = []
    for item in items:
        existing_title = item.title
        if not existing_title:
            continue
        # Skip done/resolved items
        if item.skip:
            continue
        normalized_existing = normalize_issue_title(existing_title)
        if not normalized_existing:
            continue
        ratio = difflib.SequenceMatcher(None, normalized_new, normalized_existing).ratio()
        if ratio >= threshold:
            matches.append((existing_title, ratio, item.file_path))
    matches.sort(key=operator.itemgetter(1), reverse=True)
    return matches


# ---------------------------------------------------------------------------
# Item filtering
# ---------------------------------------------------------------------------


def items_needing_issues(items: list[BacklogItem]) -> list[BacklogItem]:
    """Return all backlog items that lack GitHub issues and are not skipped."""
    return [it for it in items if it.section in {"P0", "P1", "P2", "Ideas"} and not it.skip and not it.issue]


def items_with_issues(items: list[BacklogItem]) -> list[BacklogItem]:
    """Return backlog items that already have a GitHub issue and are not skipped.

    Returns:
        List of BacklogItem instances that have an issue reference.
    """
    return [it for it in items if it.section in {"P0", "P1", "P2", "Ideas"} and not it.skip and it.issue]


# ---------------------------------------------------------------------------
# Issue body building
# ---------------------------------------------------------------------------


def build_issue_body_from_file(item: BacklogItem) -> str | None:
    """Build GitHub issue body from local per-item file content.

    For ``.yaml`` items, returns None when no groomed section exists in
    ``item.sections``.  For legacy ``.md`` items, reads the body from the
    file referenced by ``item.file_path``.

    Returns None if the body has no groomed content (i.e. no ``## Groomed``
    section), since ungroomed items don't need their body synced to GitHub.

    Args:
        item: Parsed BacklogItem with file_path and sections populated.

    Returns:
        Issue body markdown string, or None if no groomed section present.
    """
    file_path_str = item.file_path
    has_groomed_section = "groomed" in item.sections

    # For non-YAML items, require a .md file path
    if not has_groomed_section and (not file_path_str or Path(file_path_str).suffix != ".md"):
        return None
    if not file_path_str:
        return None

    path = Path(file_path_str)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    body = parts[2].strip() if len(parts) >= MIN_FRONTMATTER_PARTS else text
    if "## Groomed" not in body:
        return None
    return body.strip() + "\n"


def build_issue_body(item: BacklogItem) -> str:
    """Build GitHub issue body from backlog item fields.

    Returns:
        Markdown-formatted issue body string.
    """
    title = item.title
    desc = item.description
    source = item.source or "Not specified"
    added = item.added
    priority = item.priority
    item_type = item.item_type
    research = item.research_first
    files = item.files
    suggested_location = item.suggested_location
    role = ROLE_MAP.get(item_type, "developer using Claude Code skills")
    benefit = BENEFIT_MAP.get(item_type, "the product improves")
    goal = title.rstrip(".")

    sections = [
        f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**.",
        f"## Description\n\n{desc}",
        "## Acceptance Criteria\n\n- [ ] Work matches description\n- [ ] Plan or implementation complete",
    ]

    if files:
        sections.append(f"## Files\n\n{files}")

    if suggested_location:
        sections.append(f"## Suggested Location\n\n{suggested_location}")

    context_lines = [
        f"- **Source**: {source}",
        f"- **Priority**: {priority}",
        f"- **Added**: {added}",
        f"- **Research questions**: {research or 'None'}",
    ]
    sections.append("## Context\n\n" + "\n".join(context_lines))

    return "\n\n".join(sections) + "\n"


def extract_groomed_section(body: str) -> str:
    """Extract full ## Groomed (date) ... section from body.

    Returns:
        Groomed section text or empty string.
    """
    m = re.search(r"(## Groomed\s*\([^)]*\)\s*\n[\s\S]*?)(?=\n## |\Z)", body)
    return m.group(1).rstrip() if m else ""


def build_body_extra_only(
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


# ---------------------------------------------------------------------------
# Description extraction from issue body
# ---------------------------------------------------------------------------


def extract_description_from_issue_body(body: str) -> str:
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


# ---------------------------------------------------------------------------
# Section extraction / reconstruction / merging
# ---------------------------------------------------------------------------


def extract_sections(text: str) -> dict[str, str]:
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


def merge_sections(local_body: str, github_body: str) -> tuple[str, bool]:
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
    local_sections = extract_sections(local_body)
    github_sections = extract_sections(github_body)

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
    return "\n\n".join(parts) + "\n", True


# ---------------------------------------------------------------------------
# Legacy .md body section parsing — converts markdown body into typed sections
# ---------------------------------------------------------------------------

import marko
from marko.block import Heading as _MarkoHeading

# Heading levels used for body section splitting.
_H2_LEVEL = 2
_H3_LEVEL = 3

# Groomed heading: "## Groomed" with optional " (YYYY-MM-DD)" suffix.
_GROOMED_DATE_RE = re.compile(r"^Groomed(?:\s*\((\d{4}-\d{2}-\d{2})\))?$", re.IGNORECASE)

# ATX heading detector used when mapping AST positions back to source lines.
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


def _extract_heading_text(node: _MarkoHeading) -> str:
    """Reconstruct heading text from all inline children of a marko Heading node.

    Args:
        node: Parsed marko Heading node.

    Returns:
        Heading text as a plain string with inline formatting stripped.
    """
    parts: list[str] = []
    for inline in node.children:
        raw = getattr(inline, "children", "")
        parts.append(raw if isinstance(raw, str) else str(raw))
    return "".join(parts).strip()


def _ast_h2_headings(text: str) -> list[str]:
    """Return level-2 heading texts from the marko AST in document order.

    marko correctly ignores ``##`` lines inside fenced code blocks.

    Args:
        text: Raw markdown body text.

    Returns:
        Ordered list of heading text strings (after ``## ``).
    """
    doc = marko.parse(text)
    return [
        _extract_heading_text(child)
        for child in doc.children
        if isinstance(child, _MarkoHeading) and child.level == _H2_LEVEL
    ]


def _ast_h3_headings(text: str) -> list[str]:
    """Return level-3 heading texts from the marko AST in document order.

    Args:
        text: Raw markdown text for a single section body.

    Returns:
        Ordered list of heading text strings (after ``### ``).
    """
    doc = marko.parse(text)
    return [
        _extract_heading_text(child)
        for child in doc.children
        if isinstance(child, _MarkoHeading) and child.level == _H3_LEVEL
    ]


def _map_headings_to_lines(ast_headings: list[str], raw_lines: list[str], target_level: int) -> list[tuple[int, str]]:
    """Map AST heading texts to their 0-indexed source line numbers.

    Uses a code-fence state tracker to skip ``#`` lines inside fenced code
    blocks, then matches AST heading entries in document order by level.  Line
    numbers are 0-indexed (offsets into ``raw_lines``).

    Args:
        ast_headings: Heading texts extracted from the marko AST, in order.
        raw_lines: Source lines of the text (``text.splitlines()``).
        target_level: Heading depth to match (2 for ``##``, 3 for ``###``).

    Returns:
        List of ``(line_index, heading_text_from_source)`` tuples.
    """
    "#" * target_level + " "
    result: list[tuple[int, str]] = []
    ast_idx = 0
    in_fence = False

    for idx, line in enumerate(raw_lines):
        if ast_idx >= len(ast_headings):
            break
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _ATX_HEADING_RE.match(line)
        if m and len(m.group(1)) == target_level:
            result.append((idx, m.group(2).strip()))
            ast_idx += 1

    return result


def _split_body_h2(body: str) -> list[tuple[str, str]]:
    """Split markdown body on ``## `` headings using the marko AST.

    marko correctly identifies ATX headings while ignoring ``##`` lines inside
    fenced code blocks.  Heading positions are then mapped back to source lines
    so that raw content (including HTML entry blocks) is extracted verbatim.

    Args:
        body: Raw markdown body text (everything after frontmatter).

    Returns:
        List of ``(heading_name, content)`` tuples in document order.
        The heading_name is the text after ``## `` with whitespace stripped.
        Content does not include the heading line itself.
    """
    ast_headings = _ast_h2_headings(body)
    if not ast_headings:
        return []

    raw_lines = body.splitlines()
    positioned = _map_headings_to_lines(ast_headings, raw_lines, target_level=2)

    segments: list[tuple[str, str]] = []
    for i, (line_idx, heading_name) in enumerate(positioned):
        content_start = line_idx + 1
        content_end = positioned[i + 1][0] if i + 1 < len(positioned) else len(raw_lines)
        content = "\n".join(raw_lines[content_start:content_end]).strip()
        segments.append((heading_name, content))

    return segments


def _split_h3_subsections(content: str) -> dict[str, str]:
    """Split a block of text on ``### `` headings using the marko AST.

    Subsection content is extracted from the raw source lines so that entry
    block HTML is stored verbatim.

    Args:
        content: Block of text under a ``## `` section.

    Returns:
        Dict mapping subsection name to raw content (verbatim).
        Keys are the heading text after ``### ``, whitespace stripped.
    """
    ast_headings = _ast_h3_headings(content)
    if not ast_headings:
        return {}

    raw_lines = content.splitlines()
    positioned = _map_headings_to_lines(ast_headings, raw_lines, target_level=3)

    subsections: dict[str, str] = {}
    for i, (line_idx, sub_name) in enumerate(positioned):
        content_start = line_idx + 1
        content_end = positioned[i + 1][0] if i + 1 < len(positioned) else len(raw_lines)
        sub_content = "\n".join(raw_lines[content_start:content_end]).strip()
        subsections[sub_name] = sub_content

    return subsections


def _parse_section_entries(content: str, added_date: str) -> Section:
    """Parse content into a Section, handling both entry-block and plain text.

    If ``<div><sub>`` entry blocks are present the content is parsed into
    ``Entry`` objects via the entry_blocks module.  Plain text (no entry
    blocks) is wrapped in a single synthetic ``Entry`` so the data model
    stays uniform.

    Edge case: text appearing after the last ``</div>`` closing tag is captured
    as an additional synthetic ``Entry`` so no content is dropped.

    Args:
        content: Raw text content of a section body.
        added_date: YYYY-MM-DD date used to construct a synthetic entry id
            when the content has no entry block wrappers.

    Returns:
        ``Section`` with one or more ``Entry`` objects.
    """
    # Import here to avoid circular dependency: entry_blocks → parsing (now_iso).
    from .entry_blocks import ENTRY_RE  # noqa: PLC0415

    if not content:
        return Section(entries=[])

    matches = list(ENTRY_RE.finditer(content))
    if matches:
        from .entry_blocks import _deduplicate_timestamps, _parse_match_to_entry  # noqa: PLC0415

        entries = [_parse_match_to_entry(m) for m in matches]
        _deduplicate_timestamps(entries)

        # Edge case 3: capture any text that appears after the last </div>.
        last_match_end = matches[-1].end()
        trailing = content[last_match_end:].strip()
        if trailing:
            entries.append(Entry(id="", content=trailing))

        return Section(entries=entries)

    # No entry blocks — wrap raw content in a synthetic entry.
    synthetic_id = f"{added_date}T00:00:00Z"
    return Section(entries=[Entry(id=synthetic_id, content=content)])


def _parse_groomed_section(heading_name: str, content: str, added_date: str) -> GroomedData:
    """Parse a ``## Groomed`` section into a ``GroomedData`` object.

    The date is extracted from the heading suffix ``(YYYY-MM-DD)``.
    ``### `` subsections become keys in ``GroomedData.subsections``; their
    values are stored verbatim so existing ``entry_blocks`` operations work
    without re-parsing.

    Edge case 2: when a ``## Groomed`` section has body content but no
    ``### `` subsections, the entire body is stored under the key
    ``"Content"`` so no text is silently dropped.

    Args:
        heading_name: Full heading text after ``## ``, e.g. ``"Groomed (2026-02-28)"``.
        content: Raw text content under the heading (after the heading line).
        added_date: Fallback date when no date is in the heading.

    Returns:
        ``GroomedData`` with ``date`` and ``subsections`` populated.
    """
    date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", heading_name)
    date = date_match.group(1) if date_match else added_date
    subsections = _split_h3_subsections(content)
    # Edge case 2: body present but no ### subsection markers — preserve body verbatim.
    if not subsections and content.strip():
        subsections = {"Content": content.strip()}
    return GroomedData(date=date, subsections=subsections)


def parse_md_body_sections(body_text: str, added_date: str = "0000-00-00") -> dict[str, Section | GroomedData]:
    """Parse markdown body sections from a legacy ``.md`` backlog file body.

    Splits the body on ``## `` top-level headings (respecting fenced code
    blocks), then converts each section to a typed model:

    - ``## Groomed`` (with optional date suffix) → ``GroomedData``
      ``### `` subsections become ``GroomedData.subsections`` keys; values
      are stored verbatim so ``entry_blocks`` operations work unchanged.
    - All other sections → ``Section`` with a list of ``Entry`` objects.
      Sections with ``<div><sub>`` entry blocks are parsed into individual
      ``Entry`` instances.  Sections with plain text get a single synthetic
      ``Entry`` (id = ``{added_date}T00:00:00Z``).

    Duplicate ``## `` headings are merged: entries from the second (and any
    subsequent) occurrence are appended to the first, preserving all content.
    ``GroomedData`` from duplicate ``## Groomed`` headings are merged by
    updating ``subsections`` (later keys overwrite earlier ones with the same
    name).

    Args:
        body_text: Raw markdown body string — everything after the ``---``
            frontmatter delimiter block.
        added_date: YYYY-MM-DD date used as the synthetic entry id timestamp
            for plain-text sections that have no ``<div><sub>`` wrappers.
            Defaults to ``"0000-00-00"``.

    Returns:
        Dict mapping section name (as it appears in the heading after ``## ``,
        with any date suffix stripped for ``Groomed``) to a ``Section`` or
        ``GroomedData`` instance.  The key for ``## Groomed (2026-02-28)``
        is ``"groomed"``; all other section names are lowercased.
    """
    segments = _split_body_h2(body_text)
    result: dict[str, Section | GroomedData] = {}

    # Edge case 1: capture body text that precedes the first ## heading as "preamble".
    if segments:
        raw_lines = body_text.splitlines()
        ast_headings = _ast_h2_headings(body_text)
        positioned = _map_headings_to_lines(ast_headings, raw_lines, target_level=2)
        if positioned:
            first_heading_line = positioned[0][0]
            pre_heading_text = "\n".join(raw_lines[:first_heading_line]).strip()
            if pre_heading_text:
                synthetic_id = f"{added_date}T00:00:00Z"
                result["preamble"] = Section(entries=[Entry(id=synthetic_id, content=pre_heading_text)])
    elif body_text.strip():
        # No ## headings at all — entire body is preamble.
        synthetic_id = f"{added_date}T00:00:00Z"
        result["preamble"] = Section(entries=[Entry(id=synthetic_id, content=body_text.strip())])

    for heading_name, content in segments:
        groomed_match = _GROOMED_DATE_RE.match(heading_name.strip())
        if groomed_match:
            key = "groomed"
            parsed: Section | GroomedData = _parse_groomed_section(heading_name, content, added_date)
            existing_groomed = result.get(key)
            if isinstance(existing_groomed, GroomedData) and isinstance(parsed, GroomedData):
                # Merge duplicate ## Groomed sections: later subsections overwrite.
                existing_groomed.subsections.update(parsed.subsections)
                if parsed.date and not existing_groomed.date:
                    existing_groomed.date = parsed.date
            else:
                result[key] = parsed
        else:
            raw_key = heading_name.lower()
            # Normalize legacy hyphenated keys (e.g. "fact-check") to canonical
            # underscore form (e.g. "fact_check") so they are visible to render_issue_body.
            key = SECTION_HEADING_ALIAS.get(raw_key, raw_key)
            parsed_section = _parse_section_entries(content, added_date)
            existing_section = result.get(key)
            if isinstance(existing_section, Section):
                # Merge duplicate headings: append entries from subsequent occurrences.
                existing_section.entries.extend(parsed_section.entries)
            else:
                result[key] = parsed_section

    return result


# ---------------------------------------------------------------------------
# View helper
# ---------------------------------------------------------------------------


def view_result_from_local_item(item: BacklogItem) -> ViewItemResult:
    """Build view result from a local backlog item.

    Returns:
        ViewItemResult with title, priority, issue, plan, file_path, groomed, and
        optionally description/source/added/status from the per-item file.
    """
    result = ViewItemResult(
        title=item.title,
        priority=item.section,
        issue=item.issue,
        plan=item.plan,
        file_path=item.file_path,
        groomed=item.metadata.groomed,
    )
    # Use fields already parsed on BacklogItem instead of re-reading the file
    result.description = item.description or ""
    result.source = item.source or ""
    result.added = item.added or ""
    if item.file_path:
        fp = Path(item.file_path)
        if fp.suffix == ".md" and fp.exists():
            text = fp.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            result.body = parts[2].strip() if len(parts) >= MIN_FRONTMATTER_PARTS else text
    result.status = item.status
    return result


# ---------------------------------------------------------------------------
# Normalize helper
# ---------------------------------------------------------------------------


def extract_normalize_metadata(fm: dict[str, str | dict[str, str]], meta: dict[str, str]) -> dict[str, str]:
    """Extract normalized metadata from frontmatter and metadata dicts.

    Returns:
        Normalized metadata dict.
    """
    plan = str(meta.get("plan") or fm.get("plan") or "")
    return {
        "name": str(fm.get("name") or fm.get("title") or "").strip(),
        "description": str(fm.get("description") or "").strip(),
        "source": str(meta.get("source") or fm.get("source") or "Not specified"),
        "added": str(meta.get("added") or fm.get("added") or today()),
        "priority": str(meta.get("priority") or fm.get("priority") or "P2"),
        "type_val": str(meta.get("type") or fm.get("type") or "Feature"),
        "status": str(meta.get("status") or fm.get("status") or "open"),
        "issue": str(meta.get("issue") or fm.get("issue") or ""),
        "plan": "" if plan.upper() == "N/A" else plan,
        "groomed": str(meta.get("groomed") or fm.get("groomed") or ""),
    }


# ---------------------------------------------------------------------------
# SAM task body format
# ---------------------------------------------------------------------------

# Matches the invisible HTML comment block that stores SAM task metadata.
# Format: <!-- sam:task\n<YAML content>\n-->
_SAM_TASK_RE = re.compile(r"<!--\s*sam:task\s*\n(.*?)\n-->", re.DOTALL)

_YAML = YAML()
_YAML.default_flow_style = False
_YAML.preserve_quotes = True


def parse_sam_task_metadata(body: str) -> SamTask | None:
    """Extract SAM task metadata from the ``<!-- sam:task ... -->`` block in an issue body.

    The block is invisible in GitHub's rendered Markdown. Returns ``None`` if
    no block is found or the YAML is malformed.

    Args:
        body: GitHub issue body text.

    Returns:
        ``SamTask`` populated from the block, or ``None``.
    """
    m = _SAM_TASK_RE.search(body or "")
    if not m:
        return None
    try:
        data = _YAML.load(io.StringIO(m.group(1)))
    except (ValueError, TypeError, KeyError, YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    skills_raw = data.get("skills", [])
    deps_raw = data.get("dependencies", [])
    return SamTask(
        task_id=str(data.get("task_id", "")),
        feature=str(data.get("feature", "")),
        task_type=str(data.get("type", data.get("task_type", ""))),
        status=str(data.get("status", "not-started")),
        agent=str(data.get("agent", "")),
        priority=int(data.get("priority", 2)),
        skills=[str(s) for s in skills_raw] if isinstance(skills_raw, list) else [],
        dependencies=[str(d) for d in deps_raw] if isinstance(deps_raw, list) else [],
    )


def build_sam_task_issue_title(task: SamTask, description: str) -> str:
    """Build the GitHub issue title for a SAM task.

    Format: ``[{feature}/{task_id}] {task_type}: {description}``

    Args:
        task: ``SamTask`` with ``feature``, ``task_id``, and ``task_type`` set.
        description: Short human-readable description (the "what").

    Returns:
        Formatted issue title string.
    """
    return f"[{task.feature}/{task.task_id}] {task.task_type}: {description}"


def build_sam_task_body(task: SamTask, description: str = "", acceptance_criteria: list[str] | None = None) -> str:
    """Build a GitHub issue body for a SAM task.

    The human-readable sections (What, Acceptance Criteria) are visible in
    GitHub's UI. The ``<!-- sam:task ... -->`` block at the end is invisible
    and stores machine-readable metadata for the backlog MCP to parse.

    Args:
        task: ``SamTask`` with all metadata fields populated.
        description: Human-readable description of what the task does.
        acceptance_criteria: Optional list of acceptance criteria strings.

    Returns:
        Markdown-formatted issue body string.
    """
    criteria = acceptance_criteria or ["Work matches description"]
    criteria_lines = "\n".join(f"- [ ] {c}" for c in criteria)

    buf = io.StringIO()
    _YAML.dump(
        {
            "task_id": task.task_id,
            "feature": task.feature,
            "type": task.task_type,
            "status": task.status,
            "agent": task.agent,
            "priority": task.priority,
            "skills": list(task.skills),
            "dependencies": list(task.dependencies),
        },
        buf,
    )
    yaml_block = buf.getvalue().rstrip("\n")

    return (
        f"## What\n\n{description or '(no description)'}\n\n"
        f"## Acceptance Criteria\n\n{criteria_lines}\n\n"
        f"<!-- sam:task\n{yaml_block}\n-->\n"
    )
