#!/usr/bin/env -S uv run --quiet --script
# noqa: SIZE_OK - Existing standalone validator CLI kept intact; this change adds typed backlink output and cache flags.
# /// script
# requires-python = ">=3.11"
# dependencies = ["marko>=2.2.2", "pydantic>=2.12.5", "ruamel.yaml>=0.18.0", "typer>=0.21.0"]
#
# [tool.ty.environment]
# root = ["."]
# ///
"""Validate research entries against the research-curator quality standard.

Supports two entry formats:
- ``text_header``: bold key-value pairs before the first ``---`` separator
- ``yaml_frontmatter``: standard YAML block between opening and closing ``---``

Both formats are valid. The ``format`` key in each result reports which was detected.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import date
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, TypedDict

import typer
from ruamel.yaml import YAML

import backlink_cache
from backlink_models import BacklinkEdge, CheckBacklinksReport

if TYPE_CHECKING:
    import types


class Issue(TypedDict):
    """A single validation issue found in a research entry."""

    check: str
    severity: str
    message: str
    line: int | None


app = typer.Typer(add_completion=False)

# Sections required in the body for all formats.
# For yaml_frontmatter entries, freshness data lives in the frontmatter, so
# the Freshness Tracking body section is not required.
REQUIRED_BODY_SECTIONS = [
    "Overview",
    "Problem Addressed",
    "Key Features",
    "Technical Architecture",
    "Installation & Usage",
    "Relevance to Claude Code Development",
    "References",
]

# Additional body section required only for text-header format entries.
# YAML frontmatter entries satisfy freshness via frontmatter keys instead.
_REQUIRED_SECTIONS_TEXT_HEADER_ONLY = ["Freshness Tracking"]

# Alternative accepted spellings for section headings
SECTION_ALIASES: dict[str, list[str]] = {"Installation & Usage": ["Installation and Usage"]}

REQUIRED_HEADER_FIELDS = ["Research Date", "Source URL", "Version at Research", "License"]

FRESHNESS_REQUIRED_FIELDS = ["Last Verified", "Version at Verification", "Next Review Recommended"]

# Alternative field names accepted in Freshness Tracking
FRESHNESS_ALIASES: dict[str, list[str]] = {
    "Last Verified": ["Research Date"],
    "Next Review Recommended": ["Next Review"],
}

# YAML frontmatter key aliases mapping canonical requirement name → accepted YAML keys.
# ``resource_url``, ``date_created``, and ``date_last_reviewed`` are the spellings used by
# the second historical schema documented in references/frontmatter-generation.md — accepted
# here so both historical formats validate under one schema instead of two.
_YAML_HEADER_ALIASES: dict[str, list[str]] = {
    "Research Date": ["research_date", "date", "date_created"],
    "Source URL": ["source_url", "url", "resource_url"],
    "Version at Research": ["version_at_research", "version"],
    "License": ["license"],
}

_YAML_FRESHNESS_ALIASES: dict[str, list[str]] = {
    "Last Verified": ["last_verified", "date_last_reviewed"],
    "Version at Verification": ["version_at_verification"],
    "Next Review Recommended": ["next_review", "next_review_recommended"],
}

URL_PATTERN = re.compile(r"https?://[^\s>)\]]+")
ACCESS_DATE_PATTERN = re.compile(r"(?:accessed\s+\d{4}-\d{2}-\d{2}|\(\d{4}-\d{2}-\d{2}\))")

# cross_references_absent (validation-rules.md) exempts entries verified before this date —
# the ## Cross-References convention only applies from this date forward.
CROSS_REFERENCES_EXEMPT_BEFORE = date(2026, 3, 12)

# relevance_unanchored exempts entries dated before this — the Phase 1c Repo Anchor Pass only
# applies from this date forward. validation-rules.md states the check is must-fix only for an
# entry a run just created or refreshed; that is a fact about the caller's mode, which this script
# cannot observe. The date is the observable proxy: an entry a run just wrote or refreshed carries
# a current Research Date or Last Verified, so it lands on or after the cutoff and is gated, while
# the pre-existing corpus stays quiet. Same mechanism as CROSS_REFERENCES_EXEMPT_BEFORE above.
#
# relevance_anchor_path_missing deliberately has NO such cutoff. "This entry predates Phase 1c" is
# a reason not to demand anchors of it; it is not a reason to let it keep citing a path that is not
# in the repository. That claim is false at any age and checkable at any age.
RELEVANCE_ANCHOR_EXEMPT_BEFORE = date(2026, 9, 15)
_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")

_yaml = YAML()
_yaml.preserve_quotes = True


# ---------------------------------------------------------------------------
# Format detection and YAML parsing
# ---------------------------------------------------------------------------


def detect_format(lines: list[str]) -> str:
    """Detect whether a file uses YAML frontmatter or text-header format.

    Args:
        lines: All lines of the file, including line endings stripped.

    Returns:
        ``"yaml_frontmatter"`` when the file starts with ``---``, otherwise
        ``"text_header"``.
    """
    return "yaml_frontmatter" if lines and lines[0].strip() == "---" else "text_header"


def parse_yaml_frontmatter(lines: list[str]) -> dict[str, Any]:
    """Parse the YAML block from a file that starts with ``---``.

    Reads from the opening ``---`` to the next ``---`` and returns the parsed
    mapping. Returns an empty dict on any parse error so callers can still
    produce validation issues rather than crashing.

    Args:
        lines: All lines of the file (first line must be ``---``).

    Returns:
        Parsed YAML mapping, or an empty dict on failure.
    """
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing is None:
        return {}
    yaml_text = "\n".join(lines[1:closing])
    try:
        result = _yaml.load(StringIO(yaml_text))
        return result if isinstance(result, dict) else {}
    except Exception:  # ruff: ignore[blind-except] — ruamel raises internal exc types not in public API
        return {}


def _yaml_body_lines(lines: list[str]) -> list[str]:
    """Return file lines with the YAML frontmatter blanked out, not removed.

    Every check downstream computes 1-indexed line numbers (in both the
    ``line`` field and embedded message text) from list position (``i + 1``).
    Truncating the frontmatter off the front used to make those numbers
    relative to where the frontmatter ends rather than the actual file --
    every yaml_frontmatter entry's reported ``{file}:{line}`` locator was off
    by that entry's frontmatter length. Blanking the frontmatter in place
    instead keeps body content at its real file line number, so every
    downstream number is already file-absolute.

    Args:
        lines: All file lines; first line must be ``---``.

    Returns:
        ``lines`` with the frontmatter block (opening ``---`` through closing
        ``---``, inclusive) replaced by empty strings. Returns ``lines``
        unchanged when no closing ``---`` is found.
    """
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return [""] * (i + 1) + lines[i + 1 :]
    return lines


# ---------------------------------------------------------------------------
# Section parsing (shared by both formats)
# ---------------------------------------------------------------------------


def _parse_sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Return mapping of section heading -> (start_line, end_line) (1-indexed)."""
    sections: dict[str, tuple[int, int]] = {}
    heading_positions: list[tuple[str, int]] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            heading = stripped[3:].strip()
            heading_positions.append((heading, i + 1))

    for idx, (heading, start) in enumerate(heading_positions):
        end = heading_positions[idx + 1][1] - 1 if idx + 1 < len(heading_positions) else len(lines)
        sections[heading] = (start, end)

    return sections


def _get_header_block(lines: list[str]) -> tuple[list[str], int]:
    """Return lines before the first --- separator and the line count."""
    header_lines: list[str] = []
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return header_lines, i
        header_lines.append(line)
    return header_lines, len(lines)


def _section_content(lines: list[str], start: int, end: int) -> str:
    """Extract content between section heading and next heading/separator (0-indexed range).

    Returns:
        Stripped string of content lines joined by newlines, excluding heading
        lines and ``---`` separators. Empty string when no content is present.
    """
    content_lines = []
    for line in lines[start:end]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("## "):
            continue
        content_lines.append(stripped)
    return "\n".join(content_lines).strip()


# ---------------------------------------------------------------------------
# Checks shared by both formats
# ---------------------------------------------------------------------------


def _check_section_completeness(sections: dict[str, tuple[int, int]], required: list[str]) -> list[Issue]:
    """Check that all required sections exist.

    Args:
        sections: Section heading → (start_line, end_line) mapping.
        required: List of section headings that must be present.

    Returns:
        List of ``Issue`` dicts, one per missing required section.
    """
    issues: list[Issue] = []
    section_names = set(sections.keys())

    for section in required:
        found = section in section_names
        if not found:
            aliases = SECTION_ALIASES.get(section, [])
            found = any(alias in section_names for alias in aliases)
        if not found:
            issues.append({
                "check": "section_completeness",
                "severity": "error",
                "message": f"Missing section: {section}",
                "line": None,
            })
    return issues


def _check_empty_sections(lines: list[str], sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check for sections that exist but have no content.

    Returns:
        List of ``Issue`` dicts, one per empty section.
    """
    issues: list[Issue] = []
    for heading, (start, end) in sections.items():
        content = _section_content(lines, start - 1, end)
        if not content:
            issues.append({
                "check": "empty_sections",
                "severity": "error",
                "message": f"Empty section: {heading}",
                "line": start,
            })
    return issues


def _check_access_dates(lines: list[str], sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check that URLs in References section have access dates.

    Returns:
        List of ``Issue`` dicts, one per reference missing access date.
    """
    issues: list[Issue] = []

    ref_section = sections.get("References")
    if ref_section is None:
        return issues

    start, end = ref_section
    for i in range(start - 1, end):
        if i >= len(lines):
            break
        line = lines[i]
        urls = URL_PATTERN.findall(line)
        if urls and not ACCESS_DATE_PATTERN.search(line):
            issues.append({
                "check": "access_dates",
                "severity": "warning",
                "message": f"Reference without access date on line {i + 1}",
                "line": i + 1,
            })
    return issues


def _check_url_format(lines: list[str]) -> list[Issue]:
    """Check for malformed URLs throughout the document.

    Returns:
        List of ``Issue`` dicts, one per malformed URL.
    """
    issues: list[Issue] = []
    bare_url_pattern = re.compile(r"(?<!\()(?<!<)(?<!https://)(?<!http://)(?:www\.)\S+", re.IGNORECASE)

    for i, line in enumerate(lines):
        for match in bare_url_pattern.finditer(line):
            url = match.group()
            if not url.startswith(("http://", "https://")):
                issues.append({
                    "check": "url_format",
                    "severity": "warning",
                    "message": f"URL missing scheme (http/https) on line {i + 1}: {url[:60]}",
                    "line": i + 1,
                })
    return issues


_LAST_VERIFIED_LABEL_PATTERN = re.compile(
    "(?:"
    + "|".join(re.escape(label) for label in ("Last Verified", *FRESHNESS_ALIASES.get("Last Verified", [])))
    + r").{0,10}?(\d{4}-\d{2}-\d{2})"
)


def reference_date_from_freshness_section(lines: list[str], sections: dict[str, tuple[int, int]]) -> str | None:
    """Scan the body Freshness Tracking section for its Last Verified date.

    Shared by both entry formats: a YAML-frontmatter entry can still carry its
    freshness date only in the body, under a frontmatter key spelling this file
    does not enumerate. Matches ``Last Verified`` or any of its accepted
    ``FRESHNESS_ALIASES`` labels (e.g. ``Research Date`` used inside this
    section) -- ``_check_freshness_tracking_text`` already accepts those as
    satisfying the same field, so this must recognize the same labels or a
    refreshed entry using an alias falls back to the older header date.

    Returns:
        The ``YYYY-MM-DD`` Last Verified date, or ``None`` when the section is
        absent or carries no date.
    """
    ft_section = sections.get("Freshness Tracking")
    if ft_section is None:
        return None
    start, end = ft_section
    section_text = "\n".join(lines[start - 1 : end])
    match = _LAST_VERIFIED_LABEL_PATTERN.search(section_text)
    return match.group(1) if match else None


def reference_date_text(header_lines: list[str], lines: list[str], sections: dict[str, tuple[int, int]]) -> str | None:
    """Resolve the date that gates the cross_references_absent exemption (text-header format).

    Prefers Freshness Tracking's Last Verified over the header's Research Date,
    matching the precedence FRESHNESS_ALIASES already applies elsewhere in this file.

    Returns:
        The first ``YYYY-MM-DD`` date found, or ``None`` if neither is present.
    """
    body_date = reference_date_from_freshness_section(lines, sections)
    if body_date:
        return body_date
    match = _ISO_DATE_PATTERN.search("\n".join(header_lines))
    return match.group() if match else None


def reference_date_yaml(
    frontmatter: dict[str, Any], lines: list[str], sections: dict[str, tuple[int, int]]
) -> str | None:
    """Resolve the date that gates the cross_references_absent exemption (YAML frontmatter).

    Prefers the body Freshness Tracking section's Last Verified -- the value a
    rerun actually updates -- over any frontmatter date field, matching the
    precedence ``reference_date_text`` already applies for the text-header
    format. Falls back to frontmatter's ``freshness_tracking.last_verified``
    (and its ``date_last_reviewed`` alias from the second historical schema --
    see ``_YAML_FRESHNESS_ALIASES``), the legacy corpus's bare
    ``metadata.verified`` spelling, then ``research_date``/``date`` (and their
    ``date_created`` alias -- see ``_YAML_HEADER_ALIASES``), for entries with
    no body section at all. Checking frontmatter first would let a stale
    frontmatter value -- one a rerun updated only in the body -- wrongly
    exempt an entry that is actually past the cutoff; the corpus already has
    entries in this exact state (e.g.
    ``research/context-management/claude-mem.md``: frontmatter ``2026-01-31``,
    body ``2026-05-08``).

    Returns:
        The first matching date string found, or ``None`` when neither source has one.
    """
    body_date = reference_date_from_freshness_section(lines, sections)
    if body_date:
        return body_date
    flat = flatten_yaml_items(frontmatter)
    for key in ("last_verified", "date_last_reviewed", "verified", "research_date", "date", "date_created"):
        value = flat.get(key)
        if value:
            return str(value)
    return None


RELEVANCE_SECTION = "Relevance to Claude Code Development"

# Anchor evidence: a backticked repo-relative path under one of the roots the Phase 1c Repo Anchor
# Pass searches, or a ``git grep`` command string. extraction-methodology.md's Phase 1c writes every
# Relevance item from one or the other, so a section carrying neither did not run the pass.
RELEVANCE_ANCHOR_PATTERN = re.compile(r"`(?:plugins/|\.claude/|rules/|docs/|AGENTS\.md)[^`\n]*`|git\s+grep")


# The backticked repo-relative path inside a Relevance anchor. Same roots as
# RELEVANCE_ANCHOR_PATTERN, but capturing the path so it can be resolved against the repo root.
RELEVANCE_ANCHOR_PATH_PATTERN = re.compile(r"`((?:plugins/|\.claude/|rules/|docs/|AGENTS\.md)[^`\n]*)`")

# A backticked span carrying one of these is a shape (a glob, a template placeholder), not a path
# any single file can satisfy, so it is excluded from the existence check rather than failed by it.
_UNRESOLVABLE_PATH_CHARS = "*?[{"


def exempt_by_date(reference_date: str | None, cutoff: date) -> bool:
    """Report whether an entry's date puts it before a check's cutoff.

    Args:
        reference_date: ISO date string from the entry, or ``None`` when the entry has none.
        cutoff: The first date on which the check applies.

    Returns:
        ``True`` when ``reference_date`` parses and falls before ``cutoff``. An entry with no
        date, or an unparseable one, is not exempt -- an exemption has to be earned by a date
        that was actually read.
    """
    if reference_date is None:
        return False
    try:
        return date.fromisoformat(reference_date) < cutoff
    except ValueError:
        return False


def repo_root_for(path: Path) -> Path | None:
    """Find the repository checkout containing ``path``.

    Walks up from ``path`` to the first directory holding a ``.git`` entry. ``.git`` is a
    directory in a primary checkout and a file in a linked worktree, so existence is the test,
    not directory-ness.

    Args:
        path: A file inside the checkout.

    Returns:
        The checkout root, or ``None`` when ``path`` is not inside one.
    """
    for candidate in path.resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    return None


def check_relevance_anchor_paths(
    lines: list[str], sections: dict[str, tuple[int, int]], repo_root: Path | None
) -> list[Issue]:
    """Check that every repo path the Relevance section cites resolves in the repository.

    ``check_relevance_anchored`` below tests only that anchor-shaped evidence is present. Shape
    alone is satisfied by a plausible-looking path that was never opened, which makes naming an
    invented file the cheapest way to clear the gate -- the failure mode the Phase 1c anchor pass
    exists to remove. Every path in a real anchor record came from a ``git grep`` hit, so it
    resolves; one that does not resolve did not come from the pass.

    Args:
        lines: Body lines of the entry.
        sections: Section heading -> (start_line, end_line) mapping from ``_parse_sections``.
        repo_root: Checkout root the paths resolve against, or ``None`` when it was not found.

    Returns:
        One ``relevance_anchor_path_missing`` issue per unresolvable path; or a single
        ``relevance_anchor_paths_unchecked`` issue when paths were cited but no checkout root was
        available to resolve them against, so that a skipped check is never reported as a clean one.
    """
    section = sections.get(RELEVANCE_SECTION)
    if section is None:
        # section_completeness already reports the section as missing; do not double-report.
        return []

    start, end = section
    cited: list[str] = []
    for match in RELEVANCE_ANCHOR_PATH_PATTERN.finditer("\n".join(lines[start - 1 : end])):
        candidate = match.group(1).split()[0].rstrip(".,;:)")
        if any(ch in candidate for ch in _UNRESOLVABLE_PATH_CHARS):
            continue
        if candidate not in cited:
            cited.append(candidate)

    if not cited:
        # Nothing to resolve. An absence anchor cites a search command rather than a path, and
        # check_relevance_anchored already reports a section carrying neither.
        return []

    if repo_root is None:
        return [
            {
                "check": "relevance_anchor_paths_unchecked",
                "severity": "warning",
                "message": (
                    f"{RELEVANCE_SECTION} cites {len(cited)} repo path(s) that were not checked: "
                    "no .git found above this entry -- run the validator inside the checkout"
                ),
                "line": start,
            }
        ]

    return [
        {
            "check": "relevance_anchor_path_missing",
            "severity": "warning",
            "message": (
                f"{RELEVANCE_SECTION} anchors to `{candidate}`, which does not exist in this "
                "repository -- an anchor path comes from a git grep hit, so it resolves"
            ),
            "line": start,
        }
        for candidate in cited
        if not (repo_root / candidate).exists()
    ]


def check_relevance_anchored(
    lines: list[str], sections: dict[str, tuple[int, int]], reference_date: str | None
) -> list[Issue]:
    """Check that the Relevance section cites a repo path or a search command.

    Phase 1c of references/extraction-methodology.md writes every Relevance item from an anchor:
    a repo-relative path with a quoted line read from it, or the search command that returned
    nothing. A section carrying neither is prose no reader can check against this repository, and
    is the signature of a skipped anchor pass.

    This detects the skip only. Whether the anchors are any good -- the quoted line contains the
    search term, the paths are distinct, the quote is not a frontmatter field -- is Gate 4 and
    Gate 5 of references/entry-review-rubric.md, which no regex can judge.

    Args:
        lines: Body lines of the entry.
        sections: Section heading -> (start_line, end_line) mapping from ``_parse_sections``.
        reference_date: Entry date gating ``RELEVANCE_ANCHOR_EXEMPT_BEFORE``.

    Returns:
        A single-item list with the ``relevance_unanchored`` issue, or an empty list.
    """
    section = sections.get(RELEVANCE_SECTION)
    if section is None:
        # section_completeness already reports the section as missing; do not double-report.
        return []
    if exempt_by_date(reference_date, RELEVANCE_ANCHOR_EXEMPT_BEFORE):
        return []
    start, end = section
    if RELEVANCE_ANCHOR_PATTERN.search("\n".join(lines[start - 1 : end])):
        return []
    return [
        {
            "check": "relevance_unanchored",
            "severity": "warning",
            "message": (
                f"{RELEVANCE_SECTION} cites no repo-relative path and no search command "
                "-- run the Phase 1c Repo Anchor Pass (references/extraction-methodology.md)"
            ),
            "line": start,
        }
    ]


def check_cross_references(sections: dict[str, tuple[int, int]], reference_date: str | None) -> list[Issue]:
    """Check for a ``## Cross-References`` section, exempting older entries.

    Per validation-rules.md, entries with a Research Date or Last Verified date
    before ``CROSS_REFERENCES_EXEMPT_BEFORE`` are exempt from this check.

    Returns:
        A single-item list with the ``cross_references_absent`` issue, or an empty list.
    """
    if "Cross-References" in sections:
        return []
    if exempt_by_date(reference_date, CROSS_REFERENCES_EXEMPT_BEFORE):
        return []
    return [
        {
            "check": "cross_references_absent",
            "severity": "warning",
            "message": "Entry has no Cross-References section",
            "line": None,
        }
    ]


# ---------------------------------------------------------------------------
# Format-specific header / freshness checks
# ---------------------------------------------------------------------------


def _check_header_fields_text(header_lines: list[str]) -> list[Issue]:
    """Check that required header fields exist in a text-header block.

    Args:
        header_lines: Lines before the first ``---`` separator.

    Returns:
        List of ``Issue`` dicts, one per missing required header field.
    """
    issues: list[Issue] = []
    header_text = "\n".join(header_lines)

    for field in REQUIRED_HEADER_FIELDS:
        patterns = [f"**{field}**", f"{field}:", f"{field}**:"]
        found = any(p in header_text for p in patterns)
        if not found:
            issues.append({
                "check": "header_fields",
                "severity": "warning",
                "message": f"Missing header field: {field}. "
                "If this is a new research entry, this field needs to be completed.",
                "line": None,
            })
    return issues


def _check_header_fields_yaml(frontmatter: dict[str, Any]) -> list[Issue]:
    """Check that required header fields exist in a YAML frontmatter block.

    Uses ``_YAML_HEADER_ALIASES`` to accept alternative key spellings.

    Args:
        frontmatter: Parsed YAML frontmatter dict.

    Returns:
        List of ``Issue`` dicts, one per missing required field.
    """
    issues: list[Issue] = []
    # Flatten nested keys (e.g. metadata.source_url) into a single lookup set
    flat_keys = _flatten_yaml_keys(frontmatter)

    for field, yaml_keys in _YAML_HEADER_ALIASES.items():
        found = any(k in flat_keys for k in yaml_keys)
        if not found:
            issues.append({
                "check": "header_fields",
                "severity": "warning",
                "message": f"Missing header field: {field} (expected YAML key: {yaml_keys[0]}). "
                "If this is a new research entry, this field needs to be completed.",
                "line": None,
            })
    return issues


def _check_freshness_tracking_text(lines: list[str], sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check Freshness Tracking section in a text-header entry.

    Args:
        lines: All body lines of the file.
        sections: Section name → (start, end) mapping from ``_parse_sections``.

    Returns:
        List of ``Issue`` dicts, one per missing required field.
    """
    issues: list[Issue] = []

    ft_section = sections.get("Freshness Tracking")
    if ft_section is None:
        return issues

    start, end = ft_section
    section_text = "\n".join(lines[start - 1 : end])

    for field in FRESHNESS_REQUIRED_FIELDS:
        found = field in section_text
        if not found:
            aliases = FRESHNESS_ALIASES.get(field, [])
            found = any(alias in section_text for alias in aliases)
        if not found:
            issues.append({
                "check": "freshness_tracking",
                "severity": "warning",
                "message": f"Freshness Tracking missing field: {field}",
                "line": start,
            })
    return issues


def _check_freshness_tracking_yaml(frontmatter: dict[str, Any]) -> list[Issue]:
    """Check freshness fields in a YAML frontmatter block.

    Uses ``_YAML_FRESHNESS_ALIASES`` to accept alternative key spellings.

    Args:
        frontmatter: Parsed YAML frontmatter dict.

    Returns:
        List of ``Issue`` dicts, one per missing required freshness field.
    """
    issues: list[Issue] = []
    flat_keys = _flatten_yaml_keys(frontmatter)

    for field, yaml_keys in _YAML_FRESHNESS_ALIASES.items():
        found = any(k in flat_keys for k in yaml_keys)
        if not found:
            issues.append({
                "check": "freshness_tracking",
                "severity": "warning",
                "message": f"Freshness Tracking missing field: {field} (expected YAML key: {yaml_keys[0]})",
                "line": None,
            })
    return issues


def _flatten_yaml_keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    """Recursively collect all leaf keys from a nested dict, with dotted paths.

    Also includes bare leaf keys (without prefix) to allow matching ``source_url``
    whether it lives at the root or nested under ``metadata.source_url``.

    Args:
        data: Dict to flatten.
        prefix: Dot-separated key prefix accumulated by recursive calls.

    Returns:
        Set of all key strings (bare and dotted).
    """
    keys: set[str] = set()
    for k, v in data.items():
        bare = str(k)
        dotted = f"{prefix}.{bare}" if prefix else bare
        keys.add(bare)
        keys.add(dotted)
        if isinstance(v, dict):
            keys.update(_flatten_yaml_keys(v, dotted))
    return keys


def flatten_yaml_items(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Recursively collect leaf key -> value pairs from a nested dict, with dotted paths.

    Mirrors ``_flatten_yaml_keys`` but keeps the values, so a caller can look up
    e.g. ``last_verified`` whether it lives at the root or under ``freshness_tracking``.

    Args:
        data: Dict to flatten.
        prefix: Dot-separated key prefix accumulated by recursive calls.

    Returns:
        Dict mapping each bare and dotted key to its value.
    """
    items: dict[str, Any] = {}
    for k, v in data.items():
        bare = str(k)
        dotted = f"{prefix}.{bare}" if prefix else bare
        if isinstance(v, dict):
            items.update(flatten_yaml_items(v, dotted))
        else:
            items[bare] = v
            items[dotted] = v
    return items


# ---------------------------------------------------------------------------
# Top-level validation
# ---------------------------------------------------------------------------


def _infer_research_root(resolved: list[Path]) -> Path:
    """Infer the research root as the common ancestor of all input paths.

    When all inputs share a common directory ancestor (e.g. ``research/``),
    that ancestor is returned and used as the base for relative path display.
    A lone directory argument is the root as-is (so scanning an arbitrary
    vault directory reports paths relative to that vault, not to whatever
    repository happens to contain it).

    An all-*files* argument list is the case a plain "common ancestor of the
    inputs" heuristic cannot serve. The pre-commit hook runs with
    ``pass_filenames: true``, so it passes the staged entries themselves --
    one filename for a one-entry commit, N for an N-entry commit. Their common
    ancestor is the entries' own directory whenever they share a category
    (``research/coding-agents/`` for three staged entries from that category),
    which collapses every locator to a bare basename with no path context left
    to resolve it from. For an all-files argument list, walk up from that
    common ancestor to the nearest enclosing git repository root instead, so
    the printed locator stays resolvable from the repo root the files actually
    live under. Falls back to the common ancestor when no repository is found
    (e.g. a throwaway vault built by a test fixture, which is never inside a
    git repo of its own).

    Args:
        resolved: Non-empty list of file or directory paths to validate.

    Returns:
        A ``Path`` that is an ancestor of every path in ``resolved``.
    """
    absolute_paths = [p.resolve() for p in resolved]
    candidate_dirs = [p if p.is_dir() else p.parent for p in absolute_paths]

    if len(candidate_dirs) == 1:
        common = candidate_dirs[0]
    else:
        # os.path.commonpath returns the longest common sub-path string.
        common = Path(os.path.commonpath([str(d) for d in candidate_dirs]))

    if any(p.is_dir() for p in absolute_paths):
        return common

    for candidate in (common, *common.parents):
        # A worktree's .git is a file, not a directory -- exists() covers both.
        if (candidate / ".git").exists():
            return candidate
    return common


def validate_file(filepath: Path, research_root: Path) -> dict[str, Any]:
    """Validate a single research markdown file.

    Detects format automatically and applies the appropriate header/freshness
    checks. Shared checks (sections, empty sections, access dates, URL format,
    formatting) run for both formats.

    Args:
        filepath: Absolute path to the markdown file to validate.
        research_root: Root directory used to produce a relative file path.

    Returns:
        Dict with keys ``file``, ``format``, ``status`` (pass/fail), and ``issues``.
    """
    # Use absolute paths for the relative_to call to guarantee both sides match.
    abs_filepath = filepath.resolve()
    abs_root = research_root.resolve()
    try:
        relative = str(abs_filepath.relative_to(abs_root))
    except ValueError:
        # filepath is outside research_root (e.g. an absolute path to a
        # completely different tree). Fall back to the bare filename so the
        # report is still readable rather than crashing.
        relative = str(abs_filepath)

    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    fmt = detect_format(lines)

    if fmt == "yaml_frontmatter":
        frontmatter = parse_yaml_frontmatter(lines)
        body_lines = _yaml_body_lines(lines)
        sections = _parse_sections(body_lines)
        all_issues: list[Issue] = []
        all_issues.extend(_check_section_completeness(sections, REQUIRED_BODY_SECTIONS))
        all_issues.extend(_check_header_fields_yaml(frontmatter))
        all_issues.extend(_check_empty_sections(body_lines, sections))
        all_issues.extend(_check_access_dates(body_lines, sections))
        all_issues.extend(_check_freshness_tracking_yaml(frontmatter))
        all_issues.extend(_check_url_format(body_lines))
        entry_date = reference_date_yaml(frontmatter, body_lines, sections)
        all_issues.extend(check_cross_references(sections, entry_date))
        all_issues.extend(check_relevance_anchored(body_lines, sections, entry_date))
        all_issues.extend(check_relevance_anchor_paths(body_lines, sections, repo_root_for(filepath)))
    else:
        header_lines, _ = _get_header_block(lines)
        sections = _parse_sections(lines)
        all_issues = []
        all_issues.extend(
            _check_section_completeness(sections, REQUIRED_BODY_SECTIONS + _REQUIRED_SECTIONS_TEXT_HEADER_ONLY)
        )
        all_issues.extend(_check_header_fields_text(header_lines))
        all_issues.extend(_check_empty_sections(lines, sections))
        all_issues.extend(_check_access_dates(lines, sections))
        all_issues.extend(_check_freshness_tracking_text(lines, sections))
        all_issues.extend(_check_url_format(lines))
        entry_date = reference_date_text(header_lines, lines, sections)
        all_issues.extend(check_cross_references(sections, entry_date))
        all_issues.extend(check_relevance_anchored(lines, sections, entry_date))
        all_issues.extend(check_relevance_anchor_paths(lines, sections, repo_root_for(filepath)))

    has_errors = any(i["severity"] == "error" for i in all_issues)
    status = "fail" if has_errors else "pass"

    return {"file": relative, "format": fmt, "status": status, "issues": all_issues}


_NON_ENTRY_DIRS = frozenset({"insights", "utilization", "design-notes"})

# Directory-level AI-facing instruction/navigation files, not comprehensive external-tool
# reference entries -- excluded regardless of which directory under research/ they live in.
_NON_ENTRY_FILENAMES = frozenset({"README.md", "CLAUDE.md", "AGENTS.md"})


def _is_research_entry(file: Path) -> bool:
    """Return whether a markdown file is a research entry subject to the schema.

    Excludes directory-level AI-facing instruction/navigation files (see
    ``_NON_ENTRY_FILENAMES`` -- e.g. ``README.md``, ``CLAUDE.md``, ``AGENTS.md``) and files
    under non-entry artifact directories such as ``research/insights/``
    (improvement/utilization reports written by ``research-insight-extractor`` and
    ``research-utilization-assessor``, which intentionally do not follow the research entry
    template) and ``research/design-notes/`` (internal design/status notes for this project's
    own features -- working investigations that inform an implementation decision, not
    comprehensive external-tool reference entries).
    """
    return file.name not in _NON_ENTRY_FILENAMES and not _NON_ENTRY_DIRS.intersection(file.parts)


def collect_files(path: Path) -> list[Path]:
    """Collect markdown files to validate, excluding non-entry navigation files and artifacts.

    Returns:
        Sorted list of markdown file paths.
    """
    if path.is_file():
        return [path] if path.suffix == ".md" and _is_research_entry(path) else []
    files = sorted(path.rglob("*.md"))
    return [f for f in files if _is_research_entry(f)]


def _load_backlink_lib() -> types.ModuleType:
    """Load backlink_lib from the same directory as this script using importlib.util.

    Both scripts are PEP 723 siblings in the same directory; importlib is needed
    because neither is an installed package.

    Returns:
        The loaded backlink_lib module with all public functions accessible.
    """
    lib_path = Path(__file__).parent / "backlink_lib.py"
    spec = importlib.util.spec_from_file_location("backlink_lib", lib_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load backlink_lib from {lib_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["backlink_lib"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _repair_one_asymmetric_pair(bl: types.ModuleType, source: Path, target: Path, vault_path: Path) -> bool:
    """Attempt to append a missing backlink row to target pointing at source.

    Reads the source and target entry files, locates the forward cross-reference row
    in source that cites target, transforms the relationship description, and appends
    the reciprocal row to target. Writes the modified target file on success.

    Args:
        bl: Loaded backlink_lib module.
        source: Absolute path to the entry that has a forward reference to target.
        target: Absolute path to the entry that is missing the reciprocal backlink.
        vault_path: Absolute path to the vault root (for computing relative paths).

    Returns:
        True if a new backlink row was appended and target was written; False if the
        row already exists (idempotent) or if source has no parseable forward row.
    """
    source_md = source.read_text(encoding="utf-8")
    source_rows: list[object] = bl.parse_cross_references_table(source_md)

    forward_row: object | None = None
    for row in source_rows:
        row_link: str = getattr(row, "link_path", "")
        if bl.resolve_link_path(source, row_link) == target:
            forward_row = row
            break

    target_md = target.read_text(encoding="utf-8")
    source_category: str = bl.category_of(source, vault_path)
    backlink_str = os.path.relpath(source, target.parent).replace("\\", "/")
    if not backlink_str.startswith(".."):
        backlink_str = "./" + backlink_str

    CrossRefRow = bl.CrossRefRow  # type: ignore[attr-defined]

    # forward_row's entry_name is always target's own display name -- a cross-reference
    # row's entry_name names the *other* entry a row points at, never the file the table
    # lives in. source_name must therefore never come from forward_row.
    source_name: str = source.stem
    if forward_row is not None:
        forward_rel: str = getattr(forward_row, "relationship", "")
        backlink_relationship = bl.transform_to_backlink_description(
            forward_rel, source_name, source_category, bl.category_of(target, vault_path)
        )
    else:
        backlink_relationship = bl.bare_reference_description(source_name, source_category)

    backlink_row = CrossRefRow(
        entry_name=source_name, link_path=backlink_str, category=source_category, relationship=backlink_relationship
    )

    new_md, modified = bl.append_backlink_row(target_md, backlink_row)
    if modified:
        target.write_text(new_md, encoding="utf-8")
    return modified


def _collect_deduped_files(paths: list[Path]) -> list[Path]:
    """Collect files from all paths, preserving order and deduplicating.

    Args:
        paths: Files or directories to collect from.

    Returns:
        Ordered, deduplicated list of matching research files.
    """
    seen: set[Path] = set()
    files: list[Path] = []
    for p in paths:
        for f in collect_files(p):
            if f not in seen:
                seen.add(f)
                files.append(f)
    return files


def _print_text_report(entries: list[dict[str, Any]], total_errors: int, total_warnings: int, verbose: bool) -> None:
    """Print a human-readable validation report.

    Args:
        entries: Validated entry results.
        total_errors: Count of error-severity issues across all entries.
        total_warnings: Count of warning-severity issues across all entries.
        verbose: When True, print per-file issue detail.
    """
    total = len(entries)
    passed = sum(1 for e in entries if e["status"] == "pass")
    failed = total - passed
    print(f"Research Validation: {total} entries scanned")
    print(f"  ✓ {passed} passed")
    if failed > 0:
        print(f"  ✗ {failed} failed ({total_errors} errors, {total_warnings} warnings)")
    else:
        print(f"  {total_warnings} warnings")
    if verbose:
        for entry in entries:
            if not entry["issues"]:
                continue
            print()
            marker = "✓" if entry["status"] == "pass" else "✗"
            print(f"{marker} {entry['file']} [{entry['format']}]")
            for issue in entry["issues"]:
                severity_label = issue["severity"].upper()
                line = issue.get("line")
                locator = f"{entry['file']}:{line}" if line else entry["file"]
                print(f"  {severity_label} {locator} [{issue['check']}] {issue['message']}")


@app.command()
def main(
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Files or directories to validate. Defaults to ./research/")
    ] = None,
    output_json: Annotated[bool, typer.Option("--json", help="Output machine-readable JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show per-file detail")] = False,
) -> None:
    """Validate research entries against quality standards."""
    resolved = paths or [Path("./research/")]
    research_root = _infer_research_root(resolved)

    files = _collect_deduped_files(resolved)
    if not files:
        if output_json:
            print(
                json.dumps({"summary": {"total": 0, "passed": 0, "errors": 0, "warnings": 0}, "entries": []}, indent=2)
            )
        else:
            print("No research files found.")
        sys.exit(0)

    entries = [validate_file(f, research_root) for f in files]

    total = len(entries)
    passed = sum(1 for e in entries if e["status"] == "pass")
    total_errors = sum(1 for e in entries for i in e["issues"] if i["severity"] == "error")
    total_warnings = sum(1 for e in entries for i in e["issues"] if i["severity"] == "warning")

    if output_json:
        result = {
            "summary": {"total": total, "passed": passed, "errors": total_errors, "warnings": total_warnings},
            "entries": entries,
        }
        print(json.dumps(result, indent=2))
    else:
        _print_text_report(entries, total_errors, total_warnings, verbose)

    if total_errors > 0:
        sys.exit(1)
    sys.exit(0)


@app.command(name="check-backlinks")
def check_backlinks(
    vault_path: Annotated[Path, typer.Argument(help="Root directory of the research vault")],
    fix: Annotated[bool, typer.Option("--fix", help="Auto-append missing backlink rows")] = False,
    exclude: Annotated[
        list[Path] | None,
        typer.Option(
            "--exclude",
            help=(
                "Path that --fix must not write to. Repeatable. The excluded file is still "
                "scanned and its asymmetric pairs are still reported -- only the write is skipped."
            ),
        ),
    ] = None,
    allow_partial_scan: Annotated[
        bool,
        typer.Option(
            "--allow-partial-scan",
            help=(
                "Exit 0 even when files were skipped during the scan. Without this, a skipped "
                "file fails the run, because exit 0 otherwise claims coverage the scan did not have."
            ),
        ),
    ] = False,
    cache_path: Annotated[
        Path | None,
        typer.Option(
            "--cache-path", help="SQLite extraction-cache path. Defaults to a user cache scoped to this vault."
        ),
    ] = None,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Disable persistent extraction caching for this scan.")
    ] = False,
) -> None:
    """Scan the vault for asymmetric cross-references and optionally repair them."""
    bl = _load_backlink_lib()
    vault_path = vault_path.resolve()
    excluded: set[Path] = {path.resolve() for path in (exclude or [])}
    if no_cache and cache_path is not None:
        raise typer.BadParameter("--cache-path cannot be combined with --no-cache")
    selected_cache_path: Path | None = (
        None if no_cache else cache_path or backlink_cache.default_cross_reference_cache_path(vault_path)
    )

    scan = bl.build_cross_reference_graph(vault_path, cache_path=selected_cache_path)
    asymmetric: list[tuple[Path, Path]] = bl.find_asymmetric_edges(scan.graph)
    count = len(asymmetric)
    report = CheckBacklinksReport(
        schema_version=1,
        asymmetric_cross_references=count,
        edges=[
            BacklinkEdge(
                source=os.path.relpath(source, vault_path).replace("\\", "/"),
                target=os.path.relpath(target, vault_path).replace("\\", "/"),
            )
            for source, target in asymmetric
        ],
        scan_skipped_files=len(scan.skips),
        skips=scan.skips,
        files_parsed=scan.files_parsed,
        cache_hits=scan.cache_hits,
    )

    # A skipped file is a hole in the scan's coverage, so it decides the exit code
    # independently of the edges found. Reported before any repair, because --fix
    # does not touch scan-skip defects.
    scan_incomplete = bool(scan.skips) and not allow_partial_scan

    if fix and count > 0:
        repaired = 0
        excluded_writes = 0
        for source, target in asymmetric:
            # _repair_one_asymmetric_pair writes the reciprocal row into target.
            if target.resolve() in excluded:
                excluded_writes += 1
                typer.echo(f"note: excluded, not writing to {target.relative_to(vault_path)}", err=True)
                continue
            try:
                if _repair_one_asymmetric_pair(bl, source, target, vault_path):
                    repaired += 1
            except OSError as exc:
                typer.echo(
                    f"warning: io-error, could not repair {source.relative_to(vault_path)} -> "
                    f"{target.relative_to(vault_path)}: {exc}",
                    err=True,
                )
            except ValueError as exc:
                typer.echo(
                    f"warning: structural, could not repair {source.relative_to(vault_path)} -> "
                    f"{target.relative_to(vault_path)}: {exc}",
                    err=True,
                )

        # quiet=True: this rebuild only checks for remaining asymmetric edges after
        # repair; the fix step never touches scan-skip defects, so re-scanning here
        # would reprint every skip the first build (above) already reported.
        rescan = bl.build_cross_reference_graph(vault_path, quiet=True, cache_path=selected_cache_path)
        remaining: list[tuple[Path, Path]] = bl.find_asymmetric_edges(rescan.graph)
        report = report.model_copy(
            update={
                "backlinks_repaired": repaired,
                "backlinks_excluded": excluded_writes,
                "verification_files_parsed": rescan.files_parsed,
                "verification_cache_hits": rescan.cache_hits,
                "remaining_asymmetric_cross_references": len(remaining),
            }
        )
        print(json.dumps(report.model_dump(mode="json", exclude_unset=True), separators=(",", ":"), sort_keys=True))
        if remaining or scan_incomplete:
            sys.exit(1)
        sys.exit(0)

    if fix:
        report = report.model_copy(
            update={
                "backlinks_repaired": 0,
                "backlinks_excluded": 0,
                "verification_files_parsed": None,
                "verification_cache_hits": None,
                "remaining_asymmetric_cross_references": count,
            }
        )
    print(json.dumps(report.model_dump(mode="json", exclude_unset=True), separators=(",", ":"), sort_keys=True))
    if count > 0 or scan_incomplete:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    app()
