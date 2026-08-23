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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .backend_types import IssueNode

log = logging.getLogger(__name__)

from pydantic import BaseModel
from ruamel.yaml import YAML, YAMLError

# ---------------------------------------------------------------------------
# Imports from sibling models module
# ---------------------------------------------------------------------------
from . import models as _models
from .models import (
    COMMIT_PREFIX_RE as _COMMIT_PREFIX_RE,
    FUZZY_DUPLICATE_THRESHOLD,
    GITHUB_ISSUE_URL_RE,
    MIN_FRONTMATTER_PARTS,
    SKIP_STATUS,
    AmbiguousSelectorError,
    BacklogItem,
    Entry,
    GroomedData,
    SamTask,
    Section,
    ViewItemResult,
    parse_issue_number,
)
from .rendering import heading_to_unknown_key
from .section_registry import resolve_section_name, resolve_subsection_name

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = [
    "SectionSpan",
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
    "issues_to_title_map",
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
    "split_body_sections",
    "title_to_slug",
    "today",
    "view_result_from_local_item",
]


# ---------------------------------------------------------------------------
# Issue title map helper
# ---------------------------------------------------------------------------


def issues_to_title_map(issues: list[IssueNode]) -> dict[str, int]:
    """Build a ``{normalized_title: issue_number}`` map from a list of issue nodes.

    When duplicates exist, keeps the lowest issue number (the original).
    Pure function — performs no network I/O.

    Args:
        issues: List of IssueNode dicts, e.g. from ``sync_issues_graphql``.

    Returns:
        Dict mapping normalized title strings to their GitHub issue number.
    """
    title_to_num: dict[str, int] = {}
    for issue in issues:
        key = normalize_issue_title(issue["title"])
        num = issue["number"]
        if key not in title_to_num or num < title_to_num[key]:
            title_to_num[key] = num
    return title_to_num


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
    """Return current UTC time as ISO 8601 string with microsecond precision.

    Microsecond precision ensures uniqueness across rapid successive calls,
    preventing entry id collisions in batch groom operations.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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
    """Find item by issue ref, title substring, #N, bare number, or GitHub issue URL.

    Supports:
      - ``https://github.com/owner/repo/issues/123`` — extract issue number
      - ``#123`` — match by issue number
      - ``123`` — match by issue number (bare number)
      - ``<string-id>`` — exact match against ``item.issue`` (e.g. beads nanoid ``"bd-a3f8"``)
      - ``title substring`` — case-insensitive title match

    The string-ID path fires when the selector is not a URL, ``#N``, or bare
    integer.  It compares the selector directly against ``item.issue``, allowing
    string-ID backends (beads, Linear) to resolve items by their native ID.

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
    # String-ID exact match — covers beads nanoids and other non-integer issue refs.
    for it in items:
        if it.issue and it.issue == selector:
            return it
    # Title substring match (case-insensitive)
    selector_lower = selector.lower()
    matches = [it for it in items if selector_lower in it.title.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        numbered = [it for it in matches if parse_issue_number(it.issue) is not None]
        unnumbered = [it for it in matches if parse_issue_number(it.issue) is None]
        if unnumbered:
            raise AmbiguousSelectorError(selector, matches)
        issue_numbers = [parse_issue_number(it.issue) for it in numbered]
        distinct: set[int] = {n for n in issue_numbers if n is not None}
        if len(distinct) == 1:
            log.warning(
                "find_item: selector %r matched %d cache rows sharing issue number; returning first match %r",
                selector,
                len(matches),
                matches[0].title,
            )
            return matches[0]
        raise AmbiguousSelectorError(selector, matches)
    return None


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

    Emits only sections whose content the caller actually supplied. A Story and
    an Acceptance Criteria section are deliberately not generated here: both are
    grooming outputs, established during refinement from information that does
    not exist at intake. ``groom/finalize.md`` requires a non-empty Acceptance
    Criteria section before an item is marked groomed, and a template-filled
    section emitted at creation satisfies that check without anyone having
    written a criterion.

    Returns:
        Markdown-formatted issue body string.
    """
    desc = item.description
    source = item.source or "Not specified"
    added = item.added
    priority = item.priority
    research = item.research_first
    files = item.files
    suggested_location = item.suggested_location
    sections = [f"## Description\n\n{desc}"]

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

    Delegates the actual boundary detection to :func:`_split_body_h2`, the
    marko-AST-based splitter already used by the legacy ``.md`` body-parsing
    path (see the "Legacy .md body section parsing" section of this module).
    Both callers now share one structural section boundary decision instead
    of independently maintaining their own hand-rolled line scanners that can
    silently disagree — see :class:`_EntryDivBlock` for why a naive line-based
    ``## `` scan (this function's previous implementation) misidentifies a
    heading-shaped line inside entry-block content as a real section boundary.

    Args:
        text: Markdown body text.

    Returns:
        Dict mapping section heading (e.g. '## Story') to its content (not including heading).
        When the same heading text appears more than once, the last occurrence wins —
        matching this function's pre-existing (dict-based) contract.
    """
    return {f"## {name}": content for name, content in _split_body_h2(text)}


class SectionSpan(BaseModel):
    """One entry-block-aware ``## ``/``### `` section boundary in a markdown body.

    Produced by :func:`split_body_sections`, the single structural boundary
    detector shared by every ``operations.py`` consumer that used to
    re-implement section-boundary detection with its own naive line regex
    (see :class:`_EntryDivBlock` for why that was wrong).

    Attributes:
        name: Heading text with the ``#`` marker stripped and whitespace trimmed.
        start: Char offset of the start of the heading's own source line in
            the original ``body`` string.
        end: Char offset of the next section's ``start`` (or ``len(body)`` for
            the final section) — the exclusive end of the full section slice
            (heading line plus content).
        content: Section content with the heading line stripped and
            leading/trailing whitespace trimmed.
    """

    name: str
    start: int
    end: int
    content: str


def split_body_sections(body: str) -> list[SectionSpan]:
    """Split *body* into ``## ``/``### ``-delimited sections, entry-block aware.

    The shared structural boundary detector for callers that need the same
    flat, mixed-level ``## ``/``### `` contract the deleted
    ``operations._SECTION_BOUNDARY_RE`` (``^#{2,3} (.+?)$``) used to provide —
    but routed through the marko-AST heading positions shared with
    :func:`_split_body_h2`, so a heading-shaped line inside a
    ``<div><sub>...</sub>...</div>`` entry block (see :class:`_EntryDivBlock`)
    is never misidentified as a section boundary. This is the same guard
    :func:`extract_sections` already applies for ``## ``-only splitting,
    generalized to also match ``### `` and to carry char offsets so callers
    that slice the raw body (rather than only reading section content) have
    a single shared boundary source too.

    Args:
        body: Full issue/item body text.

    Returns:
        List of :class:`SectionSpan` in document order.
    """
    return _section_spans(body, frozenset({_H2_LEVEL, _H3_LEVEL}))


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
from marko.block import BlockElement as _MarkoBlockElement, Heading as _MarkoHeading
from marko.helpers import MarkoExtension as _MarkoExtension

if TYPE_CHECKING:
    from marko.source import Source as _MarkoSource

# Heading levels used for body section splitting.
_H2_LEVEL = 2
_H3_LEVEL = 3

# Groomed heading: "## Groomed" with optional " (YYYY-MM-DD)" suffix.
_GROOMED_DATE_RE = re.compile(r"^Groomed(?:\s*\((\d{4}-\d{2}-\d{2})\))?$", re.IGNORECASE)

# Entry-block wrapper markers. Must match entry_blocks.wrap_entry()'s
# "<div><sub>{ts}</sub>\n\n{content}\n</div>" format (see ENTRY_RE in
# entry_blocks.py for the canonical parse-side pattern this mirrors).
_ENTRY_DIV_OPEN = "<div><sub>"
_ENTRY_DIV_OPEN_RE = re.compile(r" {0,3}" + re.escape(_ENTRY_DIV_OPEN))

# Tag-boundary matchers for div-nesting depth tracking. A literal-substring count
# (``line.count("<div>")``) misses an attributed opening tag like
# ``<div class="note">`` while ``line.count("</div>")`` still matches its close
# unconditionally — that asymmetry drives depth negative and ends entry-block
# opacity early, letting a heading-lookalike line further down escape as a
# spurious section (#2964 follow-up). Matching tag boundaries via regex keeps
# opens and closes counted symmetrically regardless of attributes.
_DIV_OPEN_TAG_RE = re.compile(r"<div\b")
_DIV_CLOSE_TAG_RE = re.compile(r"</div\s*>")


def _div_depth_delta(line: str) -> int:
    """Return the net change in ``<div>``/``</div>`` nesting depth for one line.

    Args:
        line: Source line to scan.

    Returns:
        Count of opening ``<div`` tags minus closing ``</div>`` tags on this line.
    """
    return len(_DIV_OPEN_TAG_RE.findall(line)) - len(_DIV_CLOSE_TAG_RE.findall(line))


# A fence opener or closer: three or more backticks or tildes, at the up-to-three-spaces
# indent CommonMark permits. The delimiter run is captured because a fence closes only on a
# run of the same character at least as long as the one that opened it — the assumption a
# boolean toggle got wrong, which is why a nested ``` inside a ```` block used to end it.
_FENCE_RE = re.compile(r" {0,3}(`{3,}|~{3,})")


# How a scan treats <div>/</div> tags that sit inside a fenced code block.
# STRICT ignores them entirely — correct for a valid entry quoting an HTML example.
# LENIENT ignores opening tags but still counts closing ones, which recovers the real
# wrapper close when the entry holds a fence that is itself never closed, without giving
# up fence opacity for the heading-shaped lines inside it.
_SCAN_STRICT = 0
_SCAN_LENIENT = 1


def _wrapper_depth_delta(line: str, *, in_fence: bool, mode: int) -> int:
    """Return one line's contribution to ``<div>``/``</div>`` nesting depth.

    Args:
        line: Source line to scan.
        in_fence: Whether the line is a fence delimiter or fenced content.
        mode: ``_SCAN_STRICT`` or ``_SCAN_LENIENT``.

    Returns:
        The net depth change this line contributes under *mode*.
    """
    if not in_fence:
        return _div_depth_delta(line)
    if mode == _SCAN_LENIENT:
        return -len(_DIV_CLOSE_TAG_RE.findall(line))
    return 0


class _FenceState:
    """Tracks whether a line-by-line scan is currently inside a fenced code block.

    ``_EntryDivBlock`` is handed raw lines by marko and has to scan them itself, so it
    cannot ask the parser what is inside a fence. Without this, a fenced HTML example
    containing an unmatched ``<div>`` counts as wrapper structure: a properly closed
    wrapper is judged unterminated, and the recovery path then exposes heading-shaped
    lines from inside the entry as sections.
    """

    def __init__(self) -> None:
        """Start outside any fence."""
        self._delimiter = ""

    def opaque(self, line: str) -> bool:
        """Consume one line and report whether it is fence delimiter or fenced content.

        Args:
            line: The source line to classify.

        Returns:
            ``True`` when the line is a fence delimiter or sits inside a fence, and so
            must not contribute tags or headings to the surrounding scan.
        """
        match = _FENCE_RE.match(line)
        if self._delimiter:
            if match is not None:
                run = match.group(1)
                closes = run[0] == self._delimiter[0] and len(run) >= len(self._delimiter)
                if closes and not line.strip()[len(run) :].strip():
                    self._delimiter = ""
            return True
        if match is not None:
            self._delimiter = match.group(1)
            return True
        return False


# Any ATX heading line, at the up-to-three-spaces indent CommonMark permits. Used only to
# bound an unterminated entry wrapper; real heading detection is the parser's job.
_ATX_ANY_RE = re.compile(r" {0,3}#{1,6}\s")
# Captures the text of an ATX heading line, so a section name keeps the exact inline
# spelling callers filter and index against.
_ATX_SOURCE_RE = re.compile(r" {0,3}#{1,6}\s+(.*)$")


def _original_offsets(body: str) -> list[int] | None:
    r"""Map each offset of marko's normalized buffer back to an offset in *body*.

    ``marko.source.Source`` stores ``text.replace("\r\n", "\n")`` and reports every
    position against that buffer, so a ``Source.pos`` taken from a CRLF document is short
    by one character for each ``\r\n`` preceding it. Callers slice the original body with
    these offsets, so the positions have to be translated back rather than used raw.

    Args:
        body: The original, untransformed body text.

    Returns:
        A list indexed by normalized offset holding the matching original offset, or
        ``None`` when the body contains no ``\r\n`` and the two spaces are identical.
    """
    if "\r\n" not in body:
        return None
    mapping: list[int] = []
    i = 0
    n = len(body)
    while i < n:
        if body[i] == "\r" and i + 1 < n and body[i + 1] == "\n":
            i += 1
        mapping.append(i)
        i += 1
    mapping.append(n)
    return mapping


class _EntryDivBlock(_MarkoBlockElement):
    """Marko block element matching this codebase's ``<div><sub>...</sub>...</div>`` entry wrapper.

    CommonMark's HTML-block rules end a generic ``<div>`` block at the first
    blank line. ``entry_blocks.wrap_entry()`` always emits a blank line right
    after the opening ``<div><sub>{ts}</sub>`` tag (to separate the timestamp
    from multi-paragraph content), so marko's built-in ``HTMLBlock`` element
    would otherwise stop treating the entry as opaque at that first blank line
    and reparse everything after it as ordinary markdown — including any
    ``## ``/``### ``-looking line inside the entry's own content (e.g. a
    fact-checker verdict quoting one claim per heading) as a real section
    boundary (#2956).

    This element is registered with higher priority than ``Heading``,
    ``HTMLBlock``, and ``Paragraph`` (see :data:`_ENTRY_AWARE_MARKDOWN`), so
    once a line opens an entry block the parser hands the *entire* block —
    every line up to the point ``<div>``/``</div>`` nesting returns to zero,
    regardless of blank lines, code fences, or heading-shaped text inside — to
    this element instead of descending into it looking for block-level
    structure. Depth is tracked (not "stop at the first ``</div>``") because
    entry content may itself contain further, unrelated ``<div>``/``</div>``
    text; a first-match stop would end the opaque region early and let a
    heading-lookalike line *after* that inner close fragment the section
    again. That makes "a heading-lookalike line inside entry content is
    mistaken for a section boundary" structurally impossible rather than
    special-cased: no line inside an entry block is ever offered to the
    block-level parser as a heading candidate in the first place, at any
    nesting depth.
    """

    priority = 9  # Above ThematicBreak(8)/FencedCode(7)/Heading(6)/HTMLBlock(5)/Paragraph(1).

    def __init__(self, lines: str) -> None:
        self.body = lines

    @classmethod
    def match(cls, source: _MarkoSource) -> bool:
        """Return whether the current line opens an entry block.

        Returns:
            ``True`` when the line matches the entry-block open marker.
        """
        return bool(source.expect_re(_ENTRY_DIV_OPEN_RE))

    @classmethod
    def _scan_close(cls, source: _MarkoSource, mode: int) -> bool:
        """Scan ahead for the wrapper's close under *mode*, then rewind to the start.

        Uses ``Source.anchor``/``Source.reset`` so the scan leaves no trace for the real
        parse.

        Args:
            source: The parser source, positioned at the wrapper's opening line.
            mode: ``_SCAN_STRICT`` or ``_SCAN_LENIENT``.

        Returns:
            ``True`` when nesting returns to zero before the end of the document.
        """
        source.anchor()
        fence = _FenceState()
        depth = 0
        closed = False
        try:
            while not source.exhausted:
                line = source.next_line()
                if line is None:
                    break
                source.consume()
                depth += _wrapper_depth_delta(line, in_fence=fence.opaque(line), mode=mode)
                if depth <= 0:
                    closed = True
                    break
        finally:
            source.reset()
        return closed

    @classmethod
    def _close_mode(cls, source: _MarkoSource) -> int | None:
        """Return the scan mode under which the wrapper closes, or ``None`` if it never does.

        ``_SCAN_STRICT`` is tried first: the common real case is a valid entry quoting an
        HTML example, whose tags must not count as wrapper structure at all.
        ``_SCAN_LENIENT`` then recovers an entry holding a fence that is itself never
        closed — without it, every later line looks fenced, the entry's own ``</div>``
        included, and a closed wrapper is judged unterminated. The mode is returned rather
        than discarded so the parse counts depth exactly as this decision did.

        Args:
            source: The parser source, positioned at the wrapper's opening line.

        Returns:
            The mode that found the close, or ``None`` when neither does.
        """
        for mode in (_SCAN_STRICT, _SCAN_LENIENT):
            if cls._scan_close(source, mode):
                return mode
        return None

    @classmethod
    def parse(cls, source: _MarkoSource) -> str:
        """Consume the entry block, bounding it at the next heading when it never closes.

        A wrapper whose ``</div>`` never arrives is malformed input, and consuming to EOF
        erases every heading after it from the AST and from every consumer built on it.
        Handing the text back to marko instead does not help: a CommonMark type-6 HTML
        block runs to the next blank line, and a malformed body need not contain one, so
        the later headings are lost either way. Treating the next heading as the wrapper's
        end keeps its own text opaque and keeps every following section addressable.

        Returns:
            The raw, verbatim source text of the entry block.
        """
        mode = cls._close_mode(source)
        closes = mode is not None
        scan = mode if mode is not None else _SCAN_LENIENT
        fence = _FenceState()
        lines: list[str] = []
        depth = 0
        while not source.exhausted:
            line = source.next_line()
            if line is None:
                break
            in_fence = fence.opaque(line)
            if not closes and lines and _ATX_ANY_RE.match(line):
                # Nothing closes this wrapper, so bound it at the next heading without
                # regard to fence state. A fence the entry never closed would otherwise
                # hide that heading too, and the recovery that exists to preserve later
                # sections would consume them instead.
                break
            lines.append(line)
            source.consume()
            depth += _wrapper_depth_delta(line, in_fence=in_fence, mode=scan)
            if closes and depth <= 0:
                break
        return "".join(lines)


class _PositionedHeading(_MarkoHeading):
    """A ``Heading`` that records where its own source line begins.

    marko 2.2.2 exposes no source position on ``Heading``, which is why this module
    previously re-scanned the source line by line and joined the Nth heading-shaped line
    to the Nth AST heading. That join never compared heading text to line text, so any
    ``#``-prefixed line the scanner and the parser disagreed about — inside an HTML
    comment, inside a fence whose delimiter run the scanner mis-measured — silently bound
    a heading to the wrong line and dropped every heading after it. Recording the parser's
    own position removes the join, and with it that whole class of defect.

    ``Source.pos`` at the time ``parse`` is entered can still sit on the blank lines or
    the line ending preceding the heading, and it counts against marko's CRLF-normalized
    buffer rather than the original text. :func:`_ast_heading_spans` corrects both; this
    element only records what the parser knew.
    """

    override = True
    _pending_start = 0

    @classmethod
    def parse(cls, source: _MarkoSource) -> re.Match[str] | None:
        """Record the source position, then parse the heading normally.

        Returns:
            The match ``marko.block.Heading.parse`` produced for this source.
        """
        _PositionedHeading._pending_start = source.pos
        return super().parse(source)

    def __init__(self, match: re.Match[str]) -> None:
        """Attach the recorded source position to the parsed heading."""
        super().__init__(match)
        self.raw_start: int = _PositionedHeading._pending_start


# Single shared marko instance used by every AST-based split in this module so
# entry-block opacity is enforced identically everywhere, rather than each
# caller independently re-deciding what counts as a section boundary.
_ENTRY_AWARE_MARKDOWN = marko.Markdown(extensions=[_MarkoExtension(elements=[_EntryDivBlock, _PositionedHeading])])


def _heading_line_start(normalized: str, pos: int) -> int:
    """Advance *pos* to the first character of the heading's own line.

    Args:
        normalized: marko's CRLF-normalized view of the body.
        pos: The ``Source.pos`` recorded when the heading was parsed.

    Returns:
        Offset, in *normalized*, of the first character of the heading line.
    """
    n = len(normalized)
    while pos < n and normalized[pos] == "\n":
        pos += 1
    return pos


def _ast_heading_spans(body: str, levels: frozenset[int]) -> list[tuple[int, str]]:
    """Return ``(start_offset, heading_text)`` for every heading at *levels*.

    Offsets index *body* itself, so a caller may slice the original text with them.

    Args:
        body: Raw markdown body text (everything after frontmatter).
        levels: Heading depths to treat as boundaries.

    Returns:
        Ordered list of ``(start_offset, heading_text)`` tuples.
    """
    doc = _ENTRY_AWARE_MARKDOWN.parse(body)
    normalized = body.replace("\r\n", "\n")
    mapping = _original_offsets(body)

    spans: list[tuple[int, str]] = []
    for child in doc.children:
        if not isinstance(child, _MarkoHeading) or child.level not in levels:
            continue
        norm_start = _heading_line_start(normalized, getattr(child, "raw_start", 0))
        start = mapping[norm_start] if mapping is not None else norm_start
        spans.append((start, _heading_name_from_source(body, start) or _extract_heading_text(child)))
    return spans


def _section_spans(body: str, levels: frozenset[int]) -> list[SectionSpan]:
    """Build the ordered section spans for *body* at the given heading *levels*.

    The single boundary computation behind :func:`split_body_sections` and
    :func:`_split_body_h2`, so the two cannot disagree about where a section starts.

    Args:
        body: Raw markdown body text.
        levels: Heading depths to treat as boundaries.

    Returns:
        Ordered list of :class:`SectionSpan`.
    """
    heads = _ast_heading_spans(body, levels)
    spans: list[SectionSpan] = []
    for i, (start, name) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        newline = body.find("\n", start)
        content_start = len(body) if newline == -1 else newline + 1
        content = _slice_content(body, min(content_start, end), end)
        spans.append(SectionSpan(name=name, start=start, end=end, content=content))
    return spans


def _extract_heading_text(node: _MarkoHeading) -> str:
    """Reconstruct heading text from all inline descendants of a marko Heading node.

    Recurses. A heading containing emphasis, strong text, code or a link nests its
    ``RawText`` one or more levels down, and stringifying the intermediate node instead
    yields marko's ``repr`` — ``## **Impact Radius**`` became the literal section name
    ``"[<RawText children='Impact Radius'>]"``.

    Args:
        node: Parsed marko Heading node.

    Returns:
        Heading text as a plain string with inline formatting stripped.
    """
    parts: list[str] = []

    def collect(inline: object) -> None:
        children = getattr(inline, "children", None)
        if isinstance(children, str):
            parts.append(children)
        elif isinstance(children, list):
            for child in children:
                collect(child)

    collect(node)
    return "".join(parts).strip()


def _heading_name_from_source(body: str, start: int) -> str:
    """Return the heading's name exactly as the source line spells it.

    The name is taken from the source rather than from the AST so that inline markup
    round-trips: the section registry, compact indexes and ``section=`` filters all match
    against the spelling a caller sees in the body, so ``## **Impact Radius**`` must stay
    ``**Impact Radius**`` and not collapse to ``Impact Radius``. This is what the deleted
    line scanner produced, and callers depend on it.

    Args:
        body: Full body text.
        start: Char offset of the first character of the heading's own line.

    Returns:
        The heading text with the ``#`` marker and surrounding whitespace removed, or an
        empty string when the line is not an ATX heading (a setext heading, say).
    """
    line = body[start:].split("\n", 1)[0].rstrip("\r")
    match = _ATX_SOURCE_RE.match(line)
    return match.group(1).strip() if match else ""


def _slice_content(body: str, content_start: int, content_end: int) -> str:
    r"""Slice and trim one section's content out of *body*.

    Line endings are normalized to ``\n``, matching the ``splitlines()``-and-rejoin
    behaviour every consumer of this contract already expects.

    Args:
        body: Full body text.
        content_start: Char offset of the first character after the heading line.
        content_end: Char offset one past the section content's last character.

    Returns:
        The sliced, whitespace-trimmed content string.
    """
    return "\n".join(body[content_start:content_end].splitlines()).strip()


def _split_body_h2(body: str, levels: frozenset[int] = frozenset({_H2_LEVEL})) -> list[tuple[str, str]]:
    """Split markdown body on heading boundaries using the marko AST.

    marko correctly identifies ATX headings while ignoring ``#``-prefixed
    lines inside fenced code blocks or entry-block content (see
    :class:`_EntryDivBlock`).  Heading positions are then mapped back to
    source lines so that raw content (including HTML entry blocks) is
    extracted verbatim.

    Defaults to ``## `` (level 2) only, matching this function's original
    contract used by :func:`extract_sections` and :func:`parse_md_body_sections`.
    Pass ``levels=frozenset({2, 3})`` to treat ``## `` and ``### `` as a single
    flat, mixed-level sequence of boundaries — the same contract
    :func:`split_body_sections` uses, but entry-block aware so a
    heading-shaped line inside a ``<div><sub>...</sub>...</div>`` entry is
    never misidentified as a section boundary (see :func:`extract_sections`'s
    docstring for why the naive regex scan this replaces was wrong).

    Args:
        body: Raw markdown body text (everything after frontmatter).
        levels: Heading depths to treat as boundaries. Defaults to ``{2}``.

    Returns:
        List of ``(heading_name, content)`` tuples in document order.
        The heading_name is the heading text with whitespace stripped.
        Content does not include the heading line itself.
    """
    return [(span.name, span.content) for span in _section_spans(body, levels)]


def _split_h3_subsections(content: str) -> dict[str, str]:
    """Split a block of text on ``### `` headings using the marko AST.

    Subsection content is extracted from the raw source lines so that entry
    block HTML is stored verbatim.

    Subsection names are resolved through
    :func:`~.section_registry.resolve_subsection_name` — the same registry
    lookup :func:`github_sync._parse_groomed_section` applies to
    GitHub-authored ``### `` headings — so a legacy ``.md`` heading like
    ``### priority`` lands under the canonical ``"Priority"`` key instead of
    round-tripping as its own uncanonicalized spelling. An unregistered name
    is preserved verbatim (legitimate free text, not an error).

    Args:
        content: Block of text under a ``## `` section.

    Returns:
        Dict mapping canonical subsection name to raw content (verbatim).
        Keys are the heading text after ``### ``, whitespace stripped, then
        resolved through the subsection registry.
    """
    subsections: dict[str, str] = {}
    for span in _section_spans(content, frozenset({_H3_LEVEL})):
        sub_content = span.content
        sub_name = resolve_subsection_name(span.name) or span.name
        # When two headings collide onto one canonical key (e.g. "Priority"
        # and "priority" in the same body), the longer content wins — the
        # same rule github_sync._parse_groomed_section and _merge_groomed
        # apply, not whichever heading happens to appear last.
        existing = subsections.get(sub_name, "")
        subsections[sub_name] = sub_content if len(sub_content) > len(existing) else existing

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
    from .entry_blocks import ENTRY_RE  # ruff: ignore[import-outside-top-level]

    if not content:
        return Section(entries=[])

    matches = list(ENTRY_RE.finditer(content))
    if matches:
        from .entry_blocks import (  # ruff: ignore[import-outside-top-level]
            _deduplicate_timestamps,
            _parse_match_to_entry,
        )

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
        heads = _ast_heading_spans(body_text, frozenset({_H2_LEVEL}))
        if heads:
            pre_heading_text = _slice_content(body_text, 0, heads[0][0])
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
            # Route through the canonical registry resolver — the same
            # write-boundary lookup operations._normalize_section_key uses —
            # so a display heading like "Impact Radius" resolves to its
            # registered snake_case key ("impact_radius"), not the raw
            # lowercased heading text. A name the registry does not recognise
            # (e.g. "Description", an ad hoc heading a caller invented) falls
            # through to heading_to_unknown_key(), matching operations.py and
            # github_sync.py so the same unregistered heading round-trips to
            # the same storage key regardless of which of the three parse
            # paths handled it (see #2978).
            key = resolve_section_name(heading_name) or heading_to_unknown_key(heading_name)
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
