#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["marko>=2.2.2", "ruamel.yaml>=0.18.0", "typer>=0.21.0"]
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
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, TypedDict

import typer
from ruamel.yaml import YAML

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

# YAML frontmatter key aliases mapping canonical requirement name → accepted YAML keys
_YAML_HEADER_ALIASES: dict[str, list[str]] = {
    "Research Date": ["research_date", "date"],
    "Source URL": ["source_url", "url"],
    "Version at Research": ["version_at_research", "version"],
    "License": ["license"],
}

_YAML_FRESHNESS_ALIASES: dict[str, list[str]] = {
    "Last Verified": ["last_verified"],
    "Version at Verification": ["version_at_verification"],
    "Next Review Recommended": ["next_review", "next_review_recommended"],
}

URL_PATTERN = re.compile(r"https?://[^\s>)\]]+")
ACCESS_DATE_PATTERN = re.compile(r"(?:accessed\s+\d{4}-\d{2}-\d{2}|\(\d{4}-\d{2}-\d{2}\))")

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
    """Return the body lines after the closing ``---`` of YAML frontmatter.

    Args:
        lines: All file lines; first line must be ``---``.

    Returns:
        Lines after the closing ``---``, or all lines when no closing found.
    """
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[i + 1 :]
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


def _check_formatting_suggestions(lines: list[str]) -> list[Issue]:
    """Check for minor markdown formatting issues (MD031: blank lines around fences).

    Returns:
        List of Issue dicts with severity 'info' for each formatting issue found.
    """
    issues: list[Issue] = []
    in_fence = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                if i > 0:
                    prev = lines[i - 1].strip()
                    if prev and not prev.startswith("#") and prev != "---":
                        issues.append({
                            "check": "formatting_suggestions",
                            "severity": "info",
                            "message": f"Missing blank line before code fence on line {i + 1}",
                            "line": i + 1,
                        })
            else:
                in_fence = False
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith("#") and next_line != "---":
                        issues.append({
                            "check": "formatting_suggestions",
                            "severity": "info",
                            "message": f"Missing blank line after code fence on line {i + 1}",
                            "line": i + 1,
                        })

    return issues


def _check_url_format(lines: list[str]) -> list[Issue]:
    """Check for malformed URLs throughout the document.

    Returns:
        List of ``Issue`` dicts, one per malformed URL.
    """
    issues: list[Issue] = []
    bare_url_pattern = re.compile(r"(?<!\()(?<!<)(?:www\.)\S+", re.IGNORECASE)

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


# ---------------------------------------------------------------------------
# Top-level validation
# ---------------------------------------------------------------------------


def _infer_research_root(resolved: list[Path]) -> Path:
    """Infer the research root as the common ancestor of all input paths.

    When all inputs share a common directory ancestor (e.g. ``research/``),
    that ancestor is returned and used as the base for relative path display.
    If only a single path is provided and it is a directory, that directory is
    the root. Falls back to the current working directory when the common
    ancestor cannot be determined from the input set alone.

    Args:
        resolved: Non-empty list of file or directory paths to validate.

    Returns:
        A ``Path`` that is an ancestor of every path in ``resolved``.
    """
    # Resolve all paths to absolute so commonpath works across relative inputs.
    absolute_paths = [p.resolve() for p in resolved]

    # Directories contribute themselves; files contribute their parent.
    # This means a lone directory arg returns that directory as the root,
    # and a set of files returns their deepest common directory ancestor.
    candidate_dirs = [p if p.is_dir() else p.parent for p in absolute_paths]

    if len(candidate_dirs) == 1:
        return candidate_dirs[0]

    # os.path.commonpath returns the longest common sub-path string.
    return Path(os.path.commonpath([str(d) for d in candidate_dirs]))


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
        all_issues.extend(_check_formatting_suggestions(body_lines))
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
        all_issues.extend(_check_formatting_suggestions(lines))

    has_errors = any(i["severity"] == "error" for i in all_issues)
    status = "fail" if has_errors else "pass"

    return {"file": relative, "format": fmt, "status": status, "issues": all_issues}


_NON_ENTRY_DIRS = frozenset({"insights", "utilization", "design-notes"})


def _is_research_entry(file: Path) -> bool:
    """Return whether a markdown file is a research entry subject to the schema.

    Excludes README.md and files under non-entry artifact directories such as
    ``research/insights/`` (improvement/utilization reports written by
    ``research-insight-extractor`` and ``research-utilization-assessor``, which
    intentionally do not follow the research entry template) and
    ``research/design-notes/`` (internal design/status notes for this project's
    own features -- working investigations that inform an implementation
    decision, not comprehensive external-tool reference entries).
    """
    return file.name != "README.md" and not _NON_ENTRY_DIRS.intersection(file.parts)


def collect_files(path: Path) -> list[Path]:
    """Collect markdown files to validate, excluding README.md and non-entry artifacts.

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
    because neither is an installed package. Module must be registered in sys.modules
    before exec_module so that @dataclass can resolve its module namespace.

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

    if forward_row is not None:
        source_name: str = getattr(forward_row, "entry_name", source.stem)
        forward_rel: str = getattr(forward_row, "relationship", "")
        backlink_relationship = bl.transform_to_backlink_description(
            forward_rel, source_name, source_category, bl.category_of(target, vault_path)
        )
    else:
        source_name = source.stem
        backlink_relationship = f"referenced by {source_name} ({source_category})"

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
        print()
        for entry in entries:
            marker = "✓" if entry["status"] == "pass" else "✗"
            print(f"{marker} {entry['file']} [{entry['format']}]")
            for issue in entry["issues"]:
                severity_label = issue["severity"].upper()
                print(f"  {severity_label}: {issue['message']}")


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
    total_info = sum(1 for e in entries for i in e["issues"] if i["severity"] == "info")

    if output_json:
        result = {
            "summary": {
                "total": total,
                "passed": passed,
                "errors": total_errors,
                "warnings": total_warnings,
                "info": total_info,
            },
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
) -> None:
    """Scan the vault for asymmetric cross-references and optionally repair them."""
    bl = _load_backlink_lib()
    vault_path = vault_path.resolve()

    graph: dict[Path, list[Path]] = bl.build_cross_reference_graph(vault_path)
    asymmetric: list[tuple[Path, Path]] = bl.find_asymmetric_edges(graph)
    count = len(asymmetric)

    print(f"asymmetric_cross_references: {count}")
    for source, target in asymmetric:
        source_rel = source.relative_to(vault_path)
        target_rel = target.relative_to(vault_path)
        print(f"  {source_rel} -> {target_rel}")

    if fix and count > 0:
        repaired = 0
        for source, target in asymmetric:
            try:
                if _repair_one_asymmetric_pair(bl, source, target, vault_path):
                    repaired += 1
            except (OSError, ValueError):
                typer.echo(
                    f"warning: could not repair {source.relative_to(vault_path)} -> {target.relative_to(vault_path)}",
                    err=True,
                )

        print(f"backlinks_repaired: {repaired}")
        graph_after: dict[Path, list[Path]] = bl.build_cross_reference_graph(vault_path)
        remaining: list[tuple[Path, Path]] = bl.find_asymmetric_edges(graph_after)
        if remaining:
            sys.exit(1)
        sys.exit(0)

    if count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    app()
