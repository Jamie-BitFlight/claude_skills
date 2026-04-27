#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["marko>=2.2.2", "typer>=0.21.0"]
# ///
"""Validate research entries against the research-curator quality standard."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, TypedDict

import typer

if TYPE_CHECKING:
    import types


class Issue(TypedDict):
    """A single validation issue found in a research entry."""

    check: str
    severity: str
    message: str
    line: int | None


app = typer.Typer(add_completion=False)

REQUIRED_SECTIONS = [
    "Overview",
    "Problem Addressed",
    "Key Statistics",
    "Key Features",
    "Technical Architecture",
    "Installation & Usage",
    "Relevance to Claude Code Development",
    "References",
    "Freshness Tracking",
]

# Alternative accepted spellings for section headings
SECTION_ALIASES: dict[str, list[str]] = {"Installation & Usage": ["Installation and Usage"]}

REQUIRED_HEADER_FIELDS = ["Research Date", "Source URL", "Version at Research", "License"]

FRESHNESS_REQUIRED_FIELDS = ["Last Verified", "Version at Verification", "Next Review Recommended"]

# Alternative field names accepted in Freshness Tracking
FRESHNESS_ALIASES: dict[str, list[str]] = {
    "Last Verified": ["Research Date"],
    "Next Review Recommended": ["Next Review"],
}

URL_PATTERN = re.compile(r"https?://[^\s>)\]]+")
ACCESS_DATE_PATTERN = re.compile(r"(?:accessed\s+\d{4}-\d{2}-\d{2}|\(\d{4}-\d{2}-\d{2}\))")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


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


def _check_section_completeness(sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check that all required sections exist.

    Returns:
        List of ``Issue`` dicts, one per missing required section. Empty list
        when all required sections (including accepted aliases) are present.
    """
    issues: list[Issue] = []
    section_names = set(sections.keys())

    for required in REQUIRED_SECTIONS:
        found = required in section_names
        if not found:
            aliases = SECTION_ALIASES.get(required, [])
            found = any(alias in section_names for alias in aliases)
        if not found:
            issues.append({
                "check": "section_completeness",
                "severity": "error",
                "message": f"Missing section: {required}",
                "line": None,
            })
    return issues


def _check_header_fields(header_lines: list[str]) -> list[Issue]:
    """Check that required header fields exist.

    Returns:
        List of ``Issue`` dicts, one per missing required header field. Empty
        list when all required fields are found in the header block.
    """
    issues: list[Issue] = []
    header_text = "\n".join(header_lines)

    for field in REQUIRED_HEADER_FIELDS:
        # Match both **Field** and Field patterns
        patterns = [f"**{field}**", f"{field}:", f"{field}**:"]
        found = any(p in header_text for p in patterns)
        if not found:
            issues.append({
                "check": "header_fields",
                "severity": "error",
                "message": f"Missing header field: {field}",
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


def _check_freshness_tracking(lines: list[str], sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check that Freshness Tracking section has required fields.

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


def _check_statistics_currency(lines: list[str], sections: dict[str, tuple[int, int]], today: date) -> list[Issue]:
    """Check for stale dates in Key Statistics section.

    Returns:
        List of ``Issue`` dicts, one per stale date found.
    """
    issues: list[Issue] = []
    cutoff = today - timedelta(days=180)

    ks_section = sections.get("Key Statistics")
    if ks_section is None:
        return issues

    start, end = ks_section
    for i in range(start - 1, end):
        if i >= len(lines):
            break
        line = lines[i]
        for match in DATE_PATTERN.finditer(line):
            date_str = match.group(1)
            try:
                d = date.fromisoformat(date_str)
            except ValueError:
                continue
            if d < cutoff:
                issues.append({
                    "check": "statistics_currency",
                    "severity": "warning",
                    "message": f"Stale date {date_str} in Key Statistics (older than 6 months)",
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


def validate_file(filepath: Path, research_root: Path, today: date) -> dict[str, Any]:
    """Validate a single research markdown file.

    Returns:
        Dict with keys ``file``, ``status`` (pass/fail), and ``issues``.
    """
    relative = str(filepath.relative_to(research_root))
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    header_lines, _ = _get_header_block(lines)
    sections = _parse_sections(lines)

    all_issues: list[Issue] = []
    all_issues.extend(_check_section_completeness(sections))
    all_issues.extend(_check_header_fields(header_lines))
    all_issues.extend(_check_empty_sections(lines, sections))
    all_issues.extend(_check_access_dates(lines, sections))
    all_issues.extend(_check_freshness_tracking(lines, sections))
    all_issues.extend(_check_statistics_currency(lines, sections, today))
    all_issues.extend(_check_url_format(lines))
    all_issues.extend(_check_formatting_suggestions(lines))

    has_errors = any(i["severity"] == "error" for i in all_issues)
    status = "fail" if has_errors else "pass"

    return {"file": relative, "status": status, "issues": all_issues}


def collect_files(path: Path) -> list[Path]:
    """Collect markdown files to validate, excluding README.md.

    Returns:
        Sorted list of markdown file paths.
    """
    if path.is_file():
        return [path] if path.suffix == ".md" and path.name != "README.md" else []
    files = sorted(path.rglob("*.md"))
    return [f for f in files if f.name != "README.md"]


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
    # os.path.relpath supports walking above the start directory on all Python 3.11+
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


_PATH_ARG = typer.Argument(Path("./research/"), help="File or directory to validate")
_JSON_OPT = typer.Option(False, "--json", help="Output machine-readable JSON")
_VERBOSE_OPT = typer.Option(False, "--verbose", help="Show per-file detail")


@app.command()
def main(path: Path = _PATH_ARG, output_json: bool = _JSON_OPT, verbose: bool = _VERBOSE_OPT) -> None:
    """Validate research entries against quality standards."""
    research_root = path if path.is_dir() else path.parent
    today = datetime.now(tz=UTC).date()

    files = collect_files(path)
    if not files:
        if output_json:
            print(
                json.dumps({"summary": {"total": 0, "passed": 0, "errors": 0, "warnings": 0}, "entries": []}, indent=2)
            )
        else:
            print("No research files found.")
        sys.exit(0)

    entries = [validate_file(f, research_root, today) for f in files]

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
        failed = total - passed
        print(f"Research Validation: {total} entries scanned")
        print(f"  \u2713 {passed} passed")
        if failed > 0:
            print(f"  \u2717 {failed} failed ({total_errors} errors, {total_warnings} warnings)")
        else:
            print(f"  {total_warnings} warnings")

        if verbose:
            print()
            for entry in entries:
                marker = "\u2713" if entry["status"] == "pass" else "\u2717"
                print(f"{marker} {entry['file']}")
                for issue in entry["issues"]:
                    severity_label = issue["severity"].upper()
                    print(f"  {severity_label}: {issue['message']}")

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
                # Log to stderr and continue — do not abort the entire fix pass
                typer.echo(
                    f"warning: could not repair {source.relative_to(vault_path)} -> {target.relative_to(vault_path)}",
                    err=True,
                )

        print(f"backlinks_repaired: {repaired}")
        # After fix, re-check asymmetries to set exit code correctly
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
