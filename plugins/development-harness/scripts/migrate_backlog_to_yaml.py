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
"""migrate_backlog_to_yaml — bulk migration of .md backlog files to .yaml format.

Each file is loaded via load_item() (which handles .md parsing and section
extraction), verified for round-trip fidelity, then the .yaml is written and
the .md renamed to .md.bak.

Usage
-----
    # Always dry-run first to verify parsing
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --dry-run

    # Migrate after confirming dry-run is clean
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --confirm

    # Remove .md.bak files after verifying YAML is correct
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --cleanup
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Bootstrap: make the development-harness package importable within the PEP 723
# isolated environment.  The script lives at:
#   plugins/development-harness/scripts/migrate_backlog_to_yaml.py
# so parents[1] is plugins/development-harness/.
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

import typer
from backlog_core.file_cache import FileCache
from dh_paths import compute_slug
from pydantic import ValidationError

from cli_output import err, output_json

if TYPE_CHECKING:
    from backlog_core.models import BacklogItem

_REPO_ROOT = _HARNESS_DIR.parent.parent.resolve()
_DEFAULT_BACKLOG_DIR = Path.home() / ".dh" / "projects" / compute_slug(_REPO_ROOT) / "backlog"

app = typer.Typer(
    name="migrate_backlog_to_yaml",
    help="Bulk migration of .md backlog files to pure YAML format.",
    no_args_is_help=False,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class MigrationReport:
    """Aggregate results from a migration run."""

    total_found: int = 0
    """Total .md files discovered in the backlog directory."""

    migrated: int = 0
    """Files successfully migrated to .yaml."""

    skipped_no_frontmatter: int = 0
    """Files skipped because they lack YAML frontmatter (README, notes, etc.)."""

    skipped_already_converted: int = 0
    """Files skipped because a .yaml counterpart already exists."""

    skipped_bak_exists: int = 0
    """Files skipped because a .md.bak counterpart already exists (already migrated)."""

    errors: list[tuple[str, str]] = field(default_factory=list)
    """(file_path, error_message) pairs for every file that failed."""

    results: list[dict[str, object]] = field(default_factory=list)
    """Per-file outcome records: {"file", "status", ...detail fields}."""

    @property
    def error_count(self) -> int:
        """Number of migration failures."""
        return len(self.errors)

    @property
    def total_skipped(self) -> int:
        """Total files skipped for any reason."""
        return self.skipped_no_frontmatter + self.skipped_already_converted + self.skipped_bak_exists


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _has_frontmatter(text: str) -> bool:
    """Return True when text begins with a YAML frontmatter block (--- ... ---).

    Args:
        text: Raw file content.

    Returns:
        True if a frontmatter block is present.
    """
    if not text.startswith("---"):
        return False
    return "---" in text[3:]


def _dry_run_section_info(item: BacklogItem) -> tuple[int, list[str]]:
    """Return section count and section keys from a BacklogItem.

    Args:
        item: BacklogItem to inspect.

    Returns:
        Tuple of (section_count, sorted_key_list).
    """
    return len(item.sections), sorted(item.sections.keys())


# ---------------------------------------------------------------------------
# Core migration functions
# ---------------------------------------------------------------------------


def migrate_file_dry_run(md_path: Path) -> tuple[BacklogItem, bool, str]:
    """Parse and verify a single .md file without writing anything.

    Args:
        md_path: Path to the source .md file.

    Returns:
        Tuple of (item, round_trip_ok, detail_message).
        detail_message is empty on success, or describes the mismatch on failure.

    Raises:
        ValueError: When the file lacks frontmatter.
        OSError: When file I/O fails.
        ValidationError: When parsing produces an invalid model.
    """
    text = md_path.read_text(encoding="utf-8")

    if not _has_frontmatter(text):
        raise ValueError("No frontmatter — not a backlog item file")

    item, mismatches = FileCache(md_path.parent).verify_legacy_item(md_path)
    if not mismatches:
        return item, True, ""
    detail = f"Mismatched fields: {mismatches}"
    return item, False, detail


def migrate_file_live(md_path: Path) -> Path:
    """Migrate a single .md backlog file to .yaml format.

    Steps:
    1. Load the .md via load_item() — fully populated BacklogItem including sections.
    2. Write .yaml via save_item().
    3. Reload from disk via load_item() and compare model_dump().
    4. Rename .md to .md.bak on success, or remove corrupt .yaml and raise on failure.

    Args:
        md_path: Path to the source .md file.

    Returns:
        Path to the written .yaml file.

    Raises:
        ValueError: When round-trip verification detects data loss, or no frontmatter.
        OSError: When file I/O fails.
        ValidationError: When parsing or reloading produces an invalid model.
    """
    text = md_path.read_text(encoding="utf-8")
    if not _has_frontmatter(text):
        raise ValueError("No frontmatter — not a backlog item file")

    yaml_path = FileCache(md_path.parent).migrate_legacy_item(md_path)
    md_path.rename(md_path.with_suffix(".md.bak"))
    return yaml_path


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


def run_dry_run(backlog_dir: Path) -> MigrationReport:
    """Parse and verify all .md files without writing anything.

    Prints per-file section information and round-trip results.

    Args:
        backlog_dir: Directory containing .md backlog files.

    Returns:
        MigrationReport with outcomes.
    """
    report = MigrationReport()

    if not backlog_dir.exists():
        return report

    md_files = sorted(backlog_dir.glob("*.md"))
    report.total_found = len(md_files)

    for md_path in md_files:
        yaml_path = md_path.with_suffix(".yaml")
        bak_path = md_path.with_suffix(".md.bak")

        if yaml_path.exists():
            report.skipped_already_converted += 1
            report.results.append({"file": md_path.name, "status": "skipped_yaml_exists"})
            continue

        if bak_path.exists():
            report.skipped_bak_exists += 1
            report.results.append({"file": md_path.name, "status": "skipped_bak_exists"})
            continue

        text = md_path.read_text(encoding="utf-8")
        if not _has_frontmatter(text):
            report.skipped_no_frontmatter += 1
            report.results.append({"file": md_path.name, "status": "skipped_no_frontmatter"})
            continue

        try:
            item, ok, detail = migrate_file_dry_run(md_path)
            section_count, section_keys = _dry_run_section_info(item)
            result: dict[str, object] = {
                "file": md_path.name,
                "status": "verified" if ok else "round_trip_mismatch",
                "sections": section_count,
                "section_keys": section_keys,
            }
            if ok:
                report.migrated += 1
            else:
                result["detail"] = detail
                report.errors.append((str(md_path), detail))
            report.results.append(result)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, ValidationError) as exc:
            report.errors.append((str(md_path), str(exc)))
            report.results.append({"file": md_path.name, "status": "error", "error": str(exc)})

    return report


def run_migration(backlog_dir: Path) -> MigrationReport:
    """Migrate all .md files to .yaml in backlog_dir.

    Args:
        backlog_dir: Directory containing .md backlog files.

    Returns:
        MigrationReport with per-file outcomes.
    """
    report = MigrationReport()

    if not backlog_dir.exists():
        return report

    md_files = sorted(backlog_dir.glob("*.md"))
    report.total_found = len(md_files)

    for md_path in md_files:
        yaml_path = md_path.with_suffix(".yaml")
        bak_path = md_path.with_suffix(".md.bak")

        if yaml_path.exists():
            report.skipped_already_converted += 1
            report.results.append({"file": md_path.name, "status": "skipped_yaml_exists"})
            continue

        if bak_path.exists():
            report.skipped_bak_exists += 1
            report.results.append({"file": md_path.name, "status": "skipped_bak_exists"})
            continue

        text = md_path.read_text(encoding="utf-8")
        if not _has_frontmatter(text):
            report.skipped_no_frontmatter += 1
            report.results.append({"file": md_path.name, "status": "skipped_no_frontmatter"})
            continue

        try:
            migrate_file_live(md_path)
            report.migrated += 1
            report.results.append({"file": md_path.name, "status": "migrated"})
        except (OSError, ValueError, KeyError, TypeError, AttributeError, ValidationError) as exc:
            report.errors.append((str(md_path), str(exc)))
            report.results.append({"file": md_path.name, "status": "error", "error": str(exc)})

    return report


def run_cleanup(backlog_dir: Path) -> list[str]:
    """Remove all .md.bak files in backlog_dir.

    Args:
        backlog_dir: Directory to clean up.

    Returns:
        Names of the removed .md.bak files.
    """
    removed: list[str] = []
    for bak_path in sorted(backlog_dir.glob("*.md.bak")):
        bak_path.unlink()
        removed.append(bak_path.name)
    return removed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.command()
def main(
    backlog_dir: Annotated[
        Path,
        typer.Option("--backlog-dir", help="Directory containing .md backlog files to migrate.", show_default=True),
    ] = _DEFAULT_BACKLOG_DIR,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Parse and verify without writing .yaml or renaming .md files.", is_flag=True),
    ] = False,
    confirm: Annotated[
        bool, typer.Option("--confirm", help="Execute the migration (required for live runs).", is_flag=True)
    ] = False,
    cleanup: Annotated[
        bool, typer.Option("--cleanup", help="Remove .md.bak files after verifying YAML is correct.", is_flag=True)
    ] = False,
) -> None:
    """Migrate .md backlog files to pure YAML format.

    Run --dry-run first to verify parsing, then --confirm to migrate.
    Use --cleanup after verifying .yaml files are correct.
    """
    if not dry_run and not confirm and not cleanup:
        output_json({
            "status": "no_action",
            "message": (
                "No action flag provided. Use --dry-run first to verify parsing and round-trip "
                "fidelity, then --confirm to execute the migration. After verifying YAML output, "
                "use --cleanup to remove .md.bak files."
            ),
        })
        raise typer.Exit(code=0)

    if not backlog_dir.exists():
        err(f"Directory not found: {backlog_dir}")

    if cleanup:
        removed = run_cleanup(backlog_dir)
        output_json({
            "backlog_dir": backlog_dir,
            "status": "cleanup",
            "removed": removed,
            "removed_count": len(removed),
        })
        return

    if dry_run:
        report = run_dry_run(backlog_dir)
        output_json(_report_payload(backlog_dir, report, dry_run=True))
        if report.error_count:
            raise typer.Exit(code=1)
        return

    if confirm:
        report = run_migration(backlog_dir)
        output_json(_report_payload(backlog_dir, report, dry_run=False))
        if report.error_count:
            raise typer.Exit(code=1)
        return


def _report_payload(backlog_dir: Path, report: MigrationReport, *, dry_run: bool) -> dict[str, object]:
    """Build the JSON payload summarising a dry-run or live migration report.

    Args:
        backlog_dir: Directory that was scanned.
        report: MigrationReport with per-file outcomes.
        dry_run: When True, this is a verify-only run (no files modified).

    Returns:
        Dict summarising the run for JSON output, including per-file results.
    """
    return {
        "backlog_dir": backlog_dir,
        "dry_run": dry_run,
        "total_found": report.total_found,
        "migrated": report.migrated,
        "skipped_no_frontmatter": report.skipped_no_frontmatter,
        "skipped_already_converted": report.skipped_already_converted,
        "skipped_bak_exists": report.skipped_bak_exists,
        "error_count": report.error_count,
        "results": report.results,
    }


if __name__ == "__main__":
    app()
