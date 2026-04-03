#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml>=0.18.0",
#   "pydantic>=2.12.3",
#   "typer>=0.21.2",
#   "gitpython>=3.1.0",
#   "pygithub>=2.8.1",
#   "fastmcp>=3.0.2",
#   "tiktoken>=0.12.0",
#   "typing-extensions>=4.0.0",
#   "marko>=2.0.0",
# ]
# ///
"""verify_migration_fidelity — compare .md.bak originals against migrated .yaml files.

For each .md.bak file found in the backlog directory:
1. Extract the raw body text (everything after the frontmatter block).
2. Load the corresponding .yaml via load_item().
3. Render the YAML item's sections back to markdown via render_sections_as_body().
4. Diff the original body vs rendered body and classify the result.

Classification:
    MATCH        — identical (or whitespace-only differences)
    MINOR_DIFF   — content present in both but formatting differs
    CONTENT_LOSS — text present in original but absent from rendered
    CONTENT_GAIN — text present in rendered but absent from original

Usage
-----
    uv run plugins/development-harness/scripts/verify_migration_fidelity.py
    uv run plugins/development-harness/scripts/verify_migration_fidelity.py --limit 10
    uv run plugins/development-harness/scripts/verify_migration_fidelity.py --verbose
"""

from __future__ import annotations

import difflib
import re
import sys
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Bootstrap: make backlog_core importable.  Script is at
#   plugins/development-harness/scripts/verify_migration_fidelity.py
# so parents[1] is plugins/development-harness/.
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

import typer
from backlog_core.models import get_backlog_dir
from backlog_core.operations import render_sections_as_body
from backlog_core.yaml_io import load_item
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from ruamel.yaml import YAMLError

if TYPE_CHECKING:
    from backlog_core.models import BacklogItem

_DEFAULT_BACKLOG_DIR: Path = get_backlog_dir()
_REPORT_DIR = Path(__file__).resolve().parents[3] / ".tmp/scratch/reports"
_TODAY = datetime.now(tz=UTC).date().strftime("%Y%m%d")
_REPORT_PATH = _REPORT_DIR / f"migration-fidelity-verification-{_TODAY}.md"

app = typer.Typer(
    name="verify_migration_fidelity",
    help="Compare .md.bak originals against migrated .yaml files for content-level fidelity.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

MATCH = "MATCH"
MINOR_DIFF = "MINOR_DIFF"
CONTENT_LOSS = "CONTENT_LOSS"
CONTENT_GAIN = "CONTENT_GAIN"

ClassificationT = str  # one of the four constants above


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class FileResult:
    """Fidelity verification result for a single .md.bak / .yaml pair.

    Attributes:
        bak_path: Path to the source .md.bak file.
        classification: One of MATCH, MINOR_DIFF, CONTENT_LOSS, CONTENT_GAIN.
        original_body: Raw body extracted from .md.bak.
        rendered_body: Body rendered from the .yaml item.
        diff_lines: Unified diff lines between original and rendered bodies.
        error: Non-empty string when verification itself failed.
    """

    bak_path: Path
    classification: ClassificationT = MATCH
    original_body: str = ""
    rendered_body: str = ""
    diff_lines: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def yaml_path(self) -> Path:
        """Corresponding .yaml file path."""
        return self.bak_path.with_suffix("").with_suffix(".yaml")

    @property
    def lost_lines(self) -> list[str]:
        """Lines present in original but absent from rendered (the '-' lines in the diff)."""
        return [ln[1:] for ln in self.diff_lines if ln.startswith("-") and not ln.startswith("---")]

    @property
    def gained_lines(self) -> list[str]:
        """Lines present in rendered but absent from original (the '+' lines in the diff)."""
        return [ln[1:] for ln in self.diff_lines if ln.startswith("+") and not ln.startswith("+++")]


@dataclass
class VerificationReport:
    """Aggregate results across all processed files.

    Attributes:
        results: Individual FileResult for each processed file.
        total_bak: Total .md.bak files discovered.
        skipped_no_yaml: Files with no corresponding .yaml counterpart.
        errors: Files that raised an exception during processing.
    """

    results: list[FileResult] = field(default_factory=list)
    total_bak: int = 0
    skipped_no_yaml: int = 0
    errors: int = 0

    def count(self, classification: ClassificationT) -> int:
        """Count results with the given classification.

        Args:
            classification: One of MATCH, MINOR_DIFF, CONTENT_LOSS, CONTENT_GAIN.

        Returns:
            Number of results matching that classification.
        """
        return sum(1 for r in self.results if r.classification == classification and not r.error)

    @property
    def processed(self) -> int:
        """Total files processed (excluding skipped)."""
        return len(self.results)

    @property
    def loss_results(self) -> list[FileResult]:
        """Results classified as CONTENT_LOSS."""
        return [r for r in self.results if r.classification == CONTENT_LOSS and not r.error]

    @property
    def gain_results(self) -> list[FileResult]:
        """Results classified as CONTENT_GAIN."""
        return [r for r in self.results if r.classification == CONTENT_GAIN and not r.error]


# ---------------------------------------------------------------------------
# Body extraction
# ---------------------------------------------------------------------------


def _extract_bak_body(text: str) -> str:
    """Extract the body text from a .md.bak file (everything after frontmatter).

    The frontmatter block is delimited by ``---`` lines.  The body is
    everything after the closing ``---``.

    Args:
        text: Full content of the .md.bak file.

    Returns:
        Body string (may be empty if the item has no body), stripped of
        leading/trailing blank lines but with internal whitespace preserved.

    Raises:
        ValueError: When no closing frontmatter delimiter is found.
    """
    if not text.startswith("---"):
        return text.strip()

    # Find the closing --- (skip first line)
    rest = text[3:]
    close = rest.find("\n---")
    if close == -1:
        raise ValueError("No closing frontmatter delimiter found in .md.bak file")

    body = rest[close + 4 :]  # skip past '\n---'
    # Strip the leading newline that follows the closing ---
    body = body.lstrip("\n")
    return body.rstrip()


# ---------------------------------------------------------------------------
# Diff and classification
# ---------------------------------------------------------------------------


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of blank lines and strip trailing whitespace per line.

    Args:
        text: Input text.

    Returns:
        Normalised text.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    # Collapse runs of 2+ blank lines to a single blank line
    result: list[str] = []
    prev_blank = False
    for ln in lines:
        if not ln:
            if not prev_blank:
                result.append(ln)
            prev_blank = True
        else:
            result.append(ln)
            prev_blank = False
    return "\n".join(result).strip()


def _compute_diff(original: str, rendered: str) -> list[str]:
    """Produce a unified diff between original and rendered bodies.

    Args:
        original: Body text from the .md.bak file.
        rendered: Body text produced by rendering the .yaml item.

    Returns:
        List of diff lines (without trailing newlines).
    """
    orig_lines = (original + "\n").splitlines(keepends=True)
    rend_lines = (rendered + "\n").splitlines(keepends=True)
    return list(
        difflib.unified_diff(orig_lines, rend_lines, fromfile="original (.md.bak)", tofile="rendered (.yaml)", n=2)
    )


def _extract_content_tokens(text: str) -> set[str]:
    """Extract non-trivial content tokens from text for loss/gain detection.

    Strips markdown heading markers, list markers, checkboxes, and excess
    whitespace, then splits on word boundaries.

    Args:
        text: Text to tokenise.

    Returns:
        Set of lower-cased word tokens.
    """
    # Remove heading markers
    cleaned = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove list/checkbox markers
    cleaned = re.sub(r"^\s*[-*+]\s+(\[[ xX]\]\s+)?", "", cleaned, flags=re.MULTILINE)
    # Extract words
    return set(re.findall(r"\b\w{3,}\b", cleaned.lower()))


def _classify(original: str, rendered: str, diff_lines: list[str]) -> ClassificationT:
    """Classify the diff between original and rendered bodies.

    Args:
        original: Raw body from .md.bak.
        rendered: Rendered body from .yaml item.
        diff_lines: Unified diff lines.

    Returns:
        Classification constant: MATCH, MINOR_DIFF, CONTENT_LOSS, or CONTENT_GAIN.
    """
    # No change lines means identical (before and after markers are not changes)
    change_lines = [ln for ln in diff_lines if ln.startswith(("+", "-")) and not ln.startswith(("---", "+++"))]
    if not change_lines:
        return MATCH

    norm_orig = _normalise_whitespace(original)
    norm_rend = _normalise_whitespace(rendered)

    if norm_orig == norm_rend:
        return MATCH

    orig_only = _extract_content_tokens(norm_orig) - _extract_content_tokens(norm_rend)
    rend_only = _extract_content_tokens(norm_rend) - _extract_content_tokens(norm_orig)

    return _classify_by_token_sets(orig_only, rend_only)


def _classify_by_token_sets(orig_only: set[str], rend_only: set[str]) -> ClassificationT:
    """Return classification based on token-level differences.

    Args:
        orig_only: Tokens present in original but absent from rendered.
        rend_only: Tokens present in rendered but absent from original.

    Returns:
        Classification constant: MATCH, MINOR_DIFF, CONTENT_LOSS, or CONTENT_GAIN.
    """
    if not orig_only and not rend_only:
        return MINOR_DIFF

    if orig_only and not rend_only:
        return CONTENT_LOSS

    if rend_only and not orig_only:
        return CONTENT_GAIN

    # Both sides have unique tokens; dominant direction determines classification
    if len(orig_only) >= len(rend_only):
        return CONTENT_LOSS
    return CONTENT_GAIN


# ---------------------------------------------------------------------------
# Per-file verification
# ---------------------------------------------------------------------------


def verify_file(bak_path: Path) -> FileResult:
    """Verify fidelity for a single .md.bak / .yaml pair.

    Args:
        bak_path: Path to the .md.bak file.

    Returns:
        FileResult with classification and diff information.
    """
    result = FileResult(bak_path=bak_path)
    yaml_path = bak_path.with_suffix("").with_suffix(".yaml")

    # Read original body from .md.bak
    bak_text = bak_path.read_text(encoding="utf-8")
    try:
        original_body = _extract_bak_body(bak_text)
    except ValueError as exc:
        result.error = f"Body extraction failed: {exc}"
        return result

    result.original_body = original_body

    # Load YAML item
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            item: BacklogItem = load_item(yaml_path)
    except (OSError, ValueError, YAMLError, ValidationError) as exc:
        result.error = f"load_item failed: {exc}"
        return result

    # Render sections to body using the same function backlog_view uses
    rendered_body = render_sections_as_body(item)
    # render_sections_as_body appends trailing '\n\n'; normalise to strip
    rendered_body = rendered_body.rstrip()
    result.rendered_body = rendered_body

    diff_lines = _compute_diff(original_body, rendered_body)
    result.diff_lines = diff_lines
    result.classification = _classify(original_body, rendered_body, diff_lines)

    return result


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _write_report(report: VerificationReport, report_path: Path, verbose: bool) -> None:
    """Write the full verification report to a markdown file.

    Args:
        report: VerificationReport with all results.
        report_path: Destination file path.
        verbose: When True, include diffs for all file types, not just losses.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        f"# Migration Fidelity Verification — {_TODAY}",
        "",
        "## Summary",
        "",
        f"- Total `.md.bak` files found: {report.total_bak}",
        f"- Processed: {report.processed}",
        f"- Skipped (no `.yaml` counterpart): {report.skipped_no_yaml}",
        f"- Errors during verification: {report.errors}",
        "",
        "## Classification Counts",
        "",
        "| Classification | Count |",
        "|---|---|",
        f"| MATCH | {report.count(MATCH)} |",
        f"| MINOR_DIFF | {report.count(MINOR_DIFF)} |",
        f"| CONTENT_LOSS | {report.count(CONTENT_LOSS)} |",
        f"| CONTENT_GAIN | {report.count(CONTENT_GAIN)} |",
        "",
    ]

    if report.loss_results:
        lines += [
            "## CONTENT_LOSS Items",
            "",
            "Text present in original `.md.bak` but absent from rendered `.yaml` output.",
            "",
        ]
        for res in report.loss_results:
            lost_preview = " ".join(res.lost_lines)[:200]
            lines += [
                f"### `{res.bak_path.name}`",
                "",
                f"**Missing text (first 200 chars):** `{lost_preview}`",
                "",
                "```diff",
                *[ln.rstrip() for ln in res.diff_lines[:60]],
                "```",
                "",
            ]

    if report.gain_results:
        lines += [
            "## CONTENT_GAIN Items",
            "",
            "Text present in rendered output but absent from `.md.bak` original.",
            "",
        ]
        for res in report.gain_results:
            gained_preview = " ".join(res.gained_lines)[:200]
            lines += [
                f"### `{res.bak_path.name}`",
                "",
                f"**Added text (first 200 chars):** `{gained_preview}`",
                "",
                "```diff",
                *[ln.rstrip() for ln in res.diff_lines[:60]],
                "```",
                "",
            ]

    if verbose:
        minor_results = [r for r in report.results if r.classification == MINOR_DIFF and not r.error]
        if minor_results:
            lines += ["## MINOR_DIFF Items (verbose)", ""]
            for res in minor_results:
                lines += [
                    f"### `{res.bak_path.name}`",
                    "",
                    "```diff",
                    *[ln.rstrip() for ln in res.diff_lines[:40]],
                    "```",
                    "",
                ]

    error_results = [r for r in report.results if r.error]
    if error_results:
        lines += ["## Verification Errors", ""]
        for res in error_results:
            lines += [f"- `{res.bak_path.name}`: {res.error}"]
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command()
def main(
    backlog_dir: Annotated[
        Path,
        typer.Option("--backlog-dir", help="Directory containing .md.bak and .yaml backlog files.", show_default=True),
    ] = _DEFAULT_BACKLOG_DIR,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Process only the first N .md.bak files (for testing).", show_default=False),
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Show diffs for all files, not just CONTENT_LOSS items.", is_flag=True)
    ] = False,
) -> None:
    """Compare .md.bak originals against migrated .yaml files for content-level fidelity.

    For each .md.bak file, loads the corresponding .yaml, renders sections via the same
    code path as backlog_view, and diffs the result against the original body text.
    """
    if not backlog_dir.exists():
        err_console.print(f"[red]Error:[/red] Directory not found: {backlog_dir}")
        raise typer.Exit(code=1)

    bak_files = sorted(backlog_dir.glob("*.md.bak"))
    report = VerificationReport(total_bak=len(bak_files))

    if limit is not None:
        bak_files = bak_files[:limit]

    console.print(
        f"\n[bold]:magnifying_glass_tilted_left: Verifying migration fidelity[/bold] — {backlog_dir}\n"
        f"Files to check: {len(bak_files)} of {report.total_bak} total .md.bak\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Verifying...", total=len(bak_files))

        for bak_path in bak_files:
            progress.update(task, description=f"[cyan]{bak_path.name}[/cyan]")

            yaml_path = bak_path.with_suffix("").with_suffix(".yaml")
            if not yaml_path.exists():
                report.skipped_no_yaml += 1
                progress.advance(task)
                continue

            result = verify_file(bak_path)
            report.results.append(result)

            if result.error:
                report.errors += 1

            progress.advance(task)

    _print_summary(report, verbose=verbose)

    _write_report(report, _REPORT_PATH, verbose=verbose)
    console.print(f"\n[dim]Full report written to:[/dim] {_REPORT_PATH}\n")

    if report.count(CONTENT_LOSS) > 0 or report.errors > 0:
        raise typer.Exit(code=1)


def _print_summary(report: VerificationReport, *, verbose: bool) -> None:
    """Print the Rich summary to the console.

    Args:
        report: VerificationReport to display.
        verbose: When True, show diffs for MINOR_DIFF items too.
    """
    table = Table(title="Migration Fidelity Report", show_header=True, header_style="bold cyan")
    table.add_column("Classification", style="bold")
    table.add_column("Count", justify="right")

    match_count = report.count(MATCH)
    minor_count = report.count(MINOR_DIFF)
    loss_count = report.count(CONTENT_LOSS)
    gain_count = report.count(CONTENT_GAIN)

    table.add_row("MATCH", str(match_count), style="green" if match_count else "")
    table.add_row("MINOR_DIFF", str(minor_count), style="yellow" if minor_count else "")
    table.add_row("CONTENT_LOSS", str(loss_count), style="red bold" if loss_count else "")
    table.add_row("CONTENT_GAIN", str(gain_count), style="yellow" if gain_count else "")
    table.add_row("[dim]Skipped (no .yaml)[/dim]", str(report.skipped_no_yaml))
    table.add_row("[dim]Errors[/dim]", str(report.errors), style="red" if report.errors else "")

    console.print()
    console.print(table)

    if report.loss_results:
        console.print("\n[red bold]:cross_mark: CONTENT_LOSS items:[/red bold]")
        for res in report.loss_results:
            lost_preview = " ".join(res.lost_lines)[:200]
            console.print(f"  [red]:cross_mark:[/red] [cyan]{res.bak_path.name}[/cyan]")
            console.print(f"     Missing: [dim]{lost_preview}[/dim]")

    if verbose:
        for res in report.results:
            if res.classification in {MINOR_DIFF, CONTENT_GAIN, CONTENT_LOSS} and not res.error and res.diff_lines:
                console.print(
                    Panel(
                        "".join(res.diff_lines[:30]),
                        title=f"[cyan]{res.bak_path.name}[/cyan] — {res.classification}",
                        expand=False,
                    )
                )

    error_results = [r for r in report.results if r.error]
    if error_results:
        console.print("\n[red bold]:cross_mark: Verification errors:[/red bold]")
        for res in error_results:
            console.print(f"  [red]:cross_mark:[/red] [cyan]{res.bak_path.name}[/cyan]")
            console.print(f"     {res.error}")


if __name__ == "__main__":
    app()
