#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21"]
# ///
"""Fix common markdown formatting issues in research entries.

Repairs three classes of problems:
  1. MD031 — missing blank lines before/after fenced code blocks (auto-fixed).
  2. Missing language specifiers on code fences (warned, not auto-fixed).
  3. Trailing whitespace on any line (auto-fixed).

Run this script BEFORE validate_research.py, not as a replacement for it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

__all__ = ["app"]

app = typer.Typer(add_completion=False, rich_markup_mode="rich")
_err = Console(stderr=True)
_out = Console()


# ---------------------------------------------------------------------------
# Core transformation logic (pure functions — no I/O)
# ---------------------------------------------------------------------------


def _is_fence_line(line: str) -> bool:
    """Return True when *line* opens or closes a fenced code block.

    A fence line is any line whose stripped form starts with three or more
    backticks at position zero — the CommonMark / GFM definition.

    Args:
        line: A single line of text (may contain a trailing newline).

    Returns:
        True when the stripped line starts with ````` ``` `````.
    """
    return line.strip().startswith("```")


def _fence_has_language(line: str) -> bool:
    """Return True when a fence opening line carries a language identifier.

    Closing fences (bare ` ``` `) always return True so callers need only
    invoke this on opening fences.

    Args:
        line: A line already identified as a fence line.

    Returns:
        True when the fence has a non-empty language specifier.
    """
    stripped = line.strip()
    # Closing fence has no language — but we only call this on openers.
    # An opener looks like ```python or ```text; a bare opener is just ```.
    lang_part = stripped[3:].strip()
    return bool(lang_part)


def _needs_blank_before(lines: list[str], fence_index: int) -> bool:
    """Return True when the line before an opening fence is non-blank.

    Mirrors the condition used by validate_research._check_formatting_suggestions:
    a non-empty preceding line that is not a heading and not a ``---`` separator
    requires a blank line inserted before the fence.

    Args:
        lines: All document lines (without trailing newlines).
        fence_index: Zero-based index of the fence opening line.

    Returns:
        True when a blank line must be inserted before *fence_index*.
    """
    if fence_index == 0:
        return False
    prev = lines[fence_index - 1].strip()
    return bool(prev) and not prev.startswith("#") and prev != "---"


def _needs_blank_after(lines: list[str], fence_index: int) -> bool:
    """Return True when the line after a closing fence is non-blank.

    Mirrors the condition used by validate_research._check_formatting_suggestions:
    a non-empty following line that is not a heading and not a ``---`` separator
    requires a blank line inserted after the fence.

    Args:
        lines: All document lines (without trailing newlines).
        fence_index: Zero-based index of the fence closing line.

    Returns:
        True when a blank line must be inserted after *fence_index*.
    """
    if fence_index >= len(lines) - 1:
        return False
    nxt = lines[fence_index + 1].strip()
    return bool(nxt) and not nxt.startswith("#") and nxt != "---"


class FileIssues:
    """Collects issues found in a single file before applying fixes.

    Attributes:
        md031_before: Line numbers (1-based) where a blank is needed before a fence.
        md031_after: Line numbers (1-based) where a blank is needed after a fence.
        missing_lang: Line numbers (1-based) of fence openers missing a language tag.
        trailing_ws: Line numbers (1-based) with trailing whitespace.
    """

    def __init__(self) -> None:
        self.md031_before: list[int] = []
        self.md031_after: list[int] = []
        self.missing_lang: list[int] = []
        self.trailing_ws: list[int] = []

    @property
    def has_fixable(self) -> bool:
        """True when there is at least one auto-fixable issue."""
        return bool(self.md031_before or self.md031_after or self.trailing_ws)

    @property
    def has_warnings(self) -> bool:
        """True when there is at least one warning-only issue."""
        return bool(self.missing_lang)


def _analyse(lines: list[str]) -> FileIssues:
    """Scan *lines* and return all discovered issues without modifying them.

    A two-pass scan:
      - Pass 1: trailing whitespace (every line).
      - Pass 2: fence tracking (MD031 + missing language).

    Args:
        lines: Document lines stripped of their trailing newline characters.

    Returns:
        Populated FileIssues instance.
    """
    issues = FileIssues()
    in_fence = False

    for i, line in enumerate(lines):
        # Trailing whitespace — checked on every line regardless of fence state.
        if line != line.rstrip():
            issues.trailing_ws.append(i + 1)

        stripped = line.strip()
        if not stripped.startswith("```"):
            continue

        if not in_fence:
            # Opening fence.
            in_fence = True
            if _needs_blank_before(lines, i):
                issues.md031_before.append(i + 1)
            if not _fence_has_language(line):
                issues.missing_lang.append(i + 1)
        else:
            # Closing fence.
            in_fence = False
            if _needs_blank_after(lines, i):
                issues.md031_after.append(i + 1)

    return issues


def _apply_fixes(lines: list[str], issues: FileIssues) -> list[str]:
    """Return a new list of lines with all auto-fixable issues resolved.

    Fixes are applied in a single forward pass to avoid index drift:
      - MD031 blank-before: insert an empty string before each affected fence.
      - MD031 blank-after: insert an empty string after each affected fence.
      - Trailing whitespace: rstrip every line.

    Args:
        lines: Original document lines (no trailing newlines).
        issues: Analysed issues from ``_analyse``.

    Returns:
        New list of lines with fixes applied.
    """
    # Convert 1-based sets for O(1) lookup.
    before_set = set(issues.md031_before)
    after_set = set(issues.md031_after)

    result: list[str] = []
    for i, line in enumerate(lines):
        one_based = i + 1
        if one_based in before_set:
            result.append("")
        result.append(line.rstrip())
        if one_based in after_set:
            result.append("")

    return result


# ---------------------------------------------------------------------------
# File-level orchestration
# ---------------------------------------------------------------------------


from dataclasses import dataclass


@dataclass
class FileResult:
    """Outcome of processing a single file."""

    path: Path
    changed: bool
    issues: FileIssues


def _process_file(path: Path, *, dry_run: bool, check: bool, verbose: bool) -> FileResult:
    """Read *path*, analyse it, optionally write fixes, and return a result.

    Args:
        path: Markdown file to process.
        dry_run: When True, print diffs but do not write.
        check: When True, do not write; caller uses return value to set exit code.
        verbose: When True, print the file path even when no issues are found.

    Returns:
        FileResult describing what was found and whether the file changed.

    Raises:
        OSError: When the file cannot be read or written.
    """
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    issues = _analyse(lines)

    if verbose:
        _out.print(f"  [dim]{path}[/dim]")

    if issues.has_warnings:
        for lineno in issues.missing_lang:
            _err.print(
                f"  [yellow]WARNING[/yellow] {path}:{lineno} — code fence missing language specifier (not auto-fixed)"
            )

    if not issues.has_fixable:
        return FileResult(path=path, changed=False, issues=issues)

    fixed_lines = _apply_fixes(lines, issues)
    fixed = "\n".join(fixed_lines)
    # Preserve a trailing newline that was present in the original file.
    if raw.endswith("\n"):
        fixed += "\n"

    changed = fixed != raw

    if changed and dry_run:
        _out.print(f"  [cyan]would fix[/cyan] {path}")
        _emit_fix_summary(issues)

    if changed and not dry_run and not check:
        path.write_text(fixed, encoding="utf-8")

    return FileResult(path=path, changed=changed, issues=issues)


def _emit_fix_summary(issues: FileIssues) -> None:
    """Print a human-readable summary of what was or would be fixed.

    Args:
        issues: Issues discovered in a file.
    """
    if issues.md031_before:
        _out.print(f"    [dim]MD031 blank-before: lines {issues.md031_before}[/dim]")
    if issues.md031_after:
        _out.print(f"    [dim]MD031 blank-after: lines {issues.md031_after}[/dim]")
    if issues.trailing_ws:
        _out.print(f"    [dim]trailing whitespace: {len(issues.trailing_ws)} line(s)[/dim]")


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _collect_paths(paths: list[Path]) -> list[Path]:
    """Expand directories to ``*.md`` files and return deduplicated sorted list.

    Args:
        paths: Mix of file and directory paths supplied by the caller.

    Returns:
        Sorted, deduplicated list of ``*.md`` ``Path`` objects to process.
    """
    collected: list[Path] = []
    for p in paths:
        if p.is_dir():
            collected.extend(sorted(p.rglob("*.md")))
        elif p.suffix == ".md":
            collected.append(p)
        else:
            _err.print(f"[yellow]skipping[/yellow] {p} (not a .md file)")
    # Deduplicate while preserving order.
    seen: set[Path] = set()
    result: list[Path] = []
    for p in collected:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.command()
def main(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            help=(
                "Files or directories to process. "
                "Directories are traversed recursively for *.md files. "
                "Defaults to ./research/."
            ),
            show_default=False,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what would change without writing any files.", rich_help_panel="Modes"),
    ] = False,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help=("Exit non-zero if any file needs changes. Does not write files. Useful as a CI gate."),
            rich_help_panel="Modes",
        ),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print each file as it is processed.", rich_help_panel="Output")
    ] = False,
) -> None:
    r"""Fix markdown formatting issues in research entries.

    Automatically fixes:

    \b
      - MD031: missing blank lines around fenced code blocks.
      - Trailing whitespace on any line.

    Warns (does not auto-fix):

    \b
      - Code fences with no language specifier (language is semantic).
    """
    resolved: list[Path] = _collect_paths(paths or [Path("research")])

    if not resolved:
        _err.print("[yellow]No markdown files found.[/yellow]")
        raise typer.Exit(0)

    files_changed = 0
    files_with_warnings = 0

    for path in resolved:
        result = _process_file(path, dry_run=dry_run, check=check, verbose=verbose)
        if result.changed:
            files_changed += 1
            if not dry_run and not check:
                _out.print(f"  [green]fixed[/green] {result.path}")
            elif check:
                _out.print(f"  [red]needs fix[/red] {result.path}")
                _emit_fix_summary(result.issues)
        if result.issues.has_warnings:
            files_with_warnings += 1

    _emit_run_summary(
        total=len(resolved), changed=files_changed, warnings=files_with_warnings, dry_run=dry_run, check=check
    )

    if check and files_changed:
        raise typer.Exit(1)


def _emit_run_summary(*, total: int, changed: int, warnings: int, dry_run: bool, check: bool) -> None:
    """Print the final run summary line.

    Args:
        total: Number of files processed.
        changed: Number of files that were (or would be) modified.
        warnings: Number of files that carried warning-only issues.
        dry_run: Whether the run was a dry-run.
        check: Whether the run was a check-only run.
    """
    verb = "would fix" if dry_run else ("need fixing" if check else "fixed")
    warn_part = f", {warnings} with warnings" if warnings else ""
    _out.print(f"\n[bold]{total}[/bold] file(s) scanned, [bold]{changed}[/bold] {verb}{warn_part}.")


if __name__ == "__main__":
    app()
