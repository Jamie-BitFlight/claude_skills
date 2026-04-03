#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
# ]
# ///
"""Fetch ty release notes from GitHub and update skill documentation.

Queries the GitHub Releases API for astral-sh/ty, identifies releases
newer than the last recorded version, categorizes changes (features,
breaking, deprecations, new commands/flags), and updates the Version
Information section in SKILL.md with version-annotated entries.

The AI using this skill compares these version annotations against the
user's installed ty version at runtime to determine feature availability.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")

# Constants
GITHUB_API_BASE = "https://api.github.com/repos/astral-sh/ty/releases"
LOCK_FILE_NAME = ".sync-ty-releases.lock"
COOLDOWN_DAYS = 1
MAX_RELEASES_PER_PAGE = 50
MAX_API_PAGES = 10
VERSION_PARTS_EXPECTED = 3

# Patterns for parsing release notes
BREAKING_PATTERN = re.compile(r"#+\s*breaking\s*changes?", re.IGNORECASE)
FEATURE_PATTERN = re.compile(r"#+\s*(enhancements?|new\s*features?|features?)", re.IGNORECASE)
PREVIEW_PATTERN = re.compile(r"#+\s*preview\s*features?", re.IGNORECASE)
DEPRECATION_PATTERN = re.compile(r"#+\s*deprecations?", re.IGNORECASE)
BUGFIX_PATTERN = re.compile(r"#+\s*(bug\s*fix|fix)", re.IGNORECASE)
SECURITY_PATTERN = re.compile(r"#+\s*security", re.IGNORECASE)
CLI_FLAG_PATTERN = re.compile(r"`--([\w-]+)`")
TY_CMD_PATTERN = re.compile(r"`(ty\s+[\w\s-]+)`")
ENV_VAR_PATTERN = re.compile(r"`(TY_[\w]+)`")

# SKILL.md section pattern
VERSION_SECTION_PATTERN = re.compile(r"(^## Version Information\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)


class SyncError(Exception):
    """Base exception for sync errors."""


class FetchError(SyncError):
    """Failed to fetch release data from GitHub."""


def parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple.

    Args:
        tag: Version string like "0.0.1"

    Returns:
        Tuple of integers for comparison
    """
    tag = tag.lstrip("v")
    parts = []
    for part in tag.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_cooldown(working_dir: Path, force: bool) -> bool:
    """Check if script should run based on cooldown period.

    Args:
        working_dir: Working directory containing lock file
        force: If True, bypass cooldown check

    Returns:
        True if script should proceed
    """
    if force:
        return True

    lock_file = working_dir / LOCK_FILE_NAME
    if not lock_file.exists():
        return True

    try:
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True

    if lock_data.get("last_status") != "success":
        return True

    try:
        last_run = datetime.fromisoformat(lock_data["last_run"])
    except (KeyError, ValueError):
        return True

    now = datetime.now(UTC)
    time_since = now - last_run
    cooldown = timedelta(days=COOLDOWN_DAYS)

    if time_since < cooldown:
        remaining = cooldown - time_since
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        last_version = lock_data.get("last_version", "unknown")
        console.print(
            Panel(
                f"Last successful sync: {last_run.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"Last synced version: {last_version}\n"
                f"Cooldown remaining: {hours}h {minutes}m\n"
                f"Bypass with: --force",
                title="Sync Cooldown Active",
                border_style="yellow",
            )
        )

    return time_since >= cooldown


def update_lock_file(working_dir: Path, status: str, last_version: str = "", releases_processed: int = 0) -> None:
    """Update lock file with sync metadata.

    Args:
        working_dir: Working directory containing lock file
        status: "success" or "failure"
        last_version: Latest version synced
        releases_processed: Number of releases processed
    """
    lock_file = working_dir / LOCK_FILE_NAME
    temp_file = working_dir / f"{LOCK_FILE_NAME}.tmp"

    lock_data = {
        "last_run": datetime.now(UTC).isoformat(),
        "last_status": status,
        "last_version": last_version,
        "releases_processed": releases_processed,
    }

    try:
        temp_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
        temp_file.rename(lock_file)
    except OSError as e:
        error_console.print(f"Warning: Failed to write lock file: {e}")


def fetch_releases(since_version: str | None = None) -> list[dict[str, str]]:
    """Fetch ty releases from GitHub API.

    Args:
        since_version: Only return releases newer than this version

    Returns:
        List of release dicts sorted newest-first

    Raises:
        FetchError: If API request fails
    """
    all_releases: list[dict[str, str]] = []
    page = 1

    try:
        with httpx.Client(timeout=30.0) as client:
            while True:
                url = f"{GITHUB_API_BASE}?per_page={MAX_RELEASES_PER_PAGE}&page={page}"
                response = client.get(url, headers={"Accept": "application/vnd.github+json"})
                response.raise_for_status()
                releases = response.json()

                if not releases:
                    break

                for r in releases:
                    tag = r["tag_name"].lstrip("v")
                    if r.get("prerelease"):
                        continue
                    release_info = {
                        "version": tag,
                        "date": r["published_at"][:10],
                        "body": r.get("body", ""),
                        "url": r.get("html_url", ""),
                    }

                    if since_version and parse_version(tag) <= parse_version(since_version):
                        all_releases.append(release_info)
                        return all_releases

                    all_releases.append(release_info)

                page += 1
                if page > MAX_API_PAGES:
                    break

    except httpx.HTTPStatusError as e:
        msg = f"GitHub API returned HTTP {e.response.status_code}"
        raise FetchError(msg) from e
    except httpx.RequestError as e:
        msg = f"Network error fetching releases: {e}"
        raise FetchError(msg) from e

    return all_releases


SECTION_HEADERS: list[tuple[re.Pattern[str], str]] = [
    (BREAKING_PATTERN, "breaking"),
    (FEATURE_PATTERN, "features"),
    (PREVIEW_PATTERN, "preview"),
    (DEPRECATION_PATTERN, "deprecations"),
    (SECURITY_PATTERN, "security"),
    (BUGFIX_PATTERN, "bugfixes"),
]


def _detect_section(stripped: str) -> str | None:
    """Match a line against known section header patterns.

    Returns:
        Section name if a pattern matches, None otherwise.
    """
    for pattern, section_name in SECTION_HEADERS:
        if pattern.match(stripped):
            return section_name
    return None


def _extract_cli_patterns(stripped: str, categories: dict[str, list[str]]) -> None:
    """Extract CLI commands, flags, and env vars from a line."""
    for match in TY_CMD_PATTERN.finditer(stripped):
        cmd = match.group(1).strip()
        if cmd not in categories["new_commands"]:
            categories["new_commands"].append(cmd)

    for match in CLI_FLAG_PATTERN.finditer(stripped):
        flag = f"--{match.group(1)}"
        if flag not in categories["new_flags"]:
            categories["new_flags"].append(flag)

    for match in ENV_VAR_PATTERN.finditer(stripped):
        var = match.group(1)
        if var not in categories["new_env_vars"]:
            categories["new_env_vars"].append(var)


def categorize_release(body: str) -> dict[str, list[str]]:
    """Parse release notes body into categorized changes.

    Args:
        body: Markdown body of the release

    Returns:
        Dict with keys: breaking, features, preview, deprecations,
        security, bugfixes, new_commands, new_flags, new_env_vars
    """
    categories: dict[str, list[str]] = {
        "breaking": [],
        "features": [],
        "preview": [],
        "deprecations": [],
        "security": [],
        "bugfixes": [],
        "new_commands": [],
        "new_flags": [],
        "new_env_vars": [],
    }

    if not body:
        return categories

    lines = body.split("\n")
    current_section = "features"

    for line in lines:
        stripped = line.strip()

        detected = _detect_section(stripped)
        if detected:
            current_section = detected
            continue

        if stripped.startswith(("- ", "* ")):
            content = stripped[2:].strip()
            if content and current_section in categories:
                categories[current_section].append(content)

        _extract_cli_patterns(stripped, categories)

    return categories


def get_current_skill_version(skill_file: Path) -> str | None:
    """Extract the current documented version from SKILL.md.

    Looks for patterns like "Current latest version: **0.0.1**"

    Args:
        skill_file: Path to SKILL.md

    Returns:
        Version string or None
    """
    if not skill_file.exists():
        return None

    content = skill_file.read_text(encoding="utf-8")
    match = re.search(r"Current latest version:\s*\*\*([\d.]+)\*\*", content)
    return match.group(1) if match else None


def _collect_release_data(
    releases: list[dict[str, str]],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Collect categorized data across all releases.

    Returns:
        Tuple of (breaking_versions, feature_highlights, stabilized, deprecations)
    """
    breaking_versions: list[tuple[str, str]] = []
    feature_highlights: list[tuple[str, str]] = []
    stabilized: list[tuple[str, str]] = []
    deprecations: list[tuple[str, str]] = []

    for release in releases:
        cats = categorize_release(release["body"])
        ver = release["version"]

        breaking_versions.extend((ver, item) for item in cats["breaking"])
        feature_highlights.extend((ver, item) for item in cats["features"][:3])

        stabilized.extend(
            (ver, item) for item in cats["preview"] if "stable" in item.lower() or "stabilize" in item.lower()
        )

        deprecations.extend((ver, item) for item in cats["deprecations"])

    return breaking_versions, feature_highlights, stabilized, deprecations


def _format_breaking_changes(releases: list[dict[str, str]], lines: list[str]) -> None:
    """Append breaking changes section from the latest major release."""
    major_releases = [
        r for r in releases if r["version"].endswith(".0") and len(r["version"].split(".")) == VERSION_PARTS_EXPECTED
    ]

    if not major_releases:
        return

    latest_major = major_releases[0]
    major_cats = categorize_release(latest_major["body"])

    if major_cats["breaking"]:
        lines.append(f"### {latest_major['version']} Breaking Changes ({latest_major['date']})\n")
        lines.extend(f"- {item}" for item in major_cats["breaking"])
        lines.append("")


def build_version_section(releases: list[dict[str, str]], current_doc_version: str | None) -> str:
    """Build the Version Information section content.

    Produces version-annotated entries so the AI using this skill can
    compare feature availability against the user's installed ty version.

    Args:
        releases: List of release dicts (newest first)
        current_doc_version: Version currently documented in SKILL.md

    Returns:
        Markdown string for the Version Information section
    """
    if not releases:
        return "No release data available.\n"

    latest = releases[0]
    lines = [f"Current latest version: **{latest['version']}** ({latest['date']})\n"]

    _, feature_highlights, stabilized, deprecations = _collect_release_data(releases)

    _format_breaking_changes(releases, lines)

    if stabilized:
        lines.append("### Features Stabilized\n")
        lines.extend(f"- {item} ({ver})" for ver, item in stabilized)
        lines.append("")

    baseline = current_doc_version or "0.0.0"
    new_features = [(ver, item) for ver, item in feature_highlights if parse_version(ver) > parse_version(baseline)]

    if new_features:
        lines.append(f"### Key Features Added Since {baseline}\n")
        seen: set[str] = set()
        for ver, item in new_features:
            key = item[:50].lower()
            if key not in seen:
                seen.add(key)
                lines.append(f"- {item} ({ver})")
        lines.append("")

    if deprecations:
        lines.append("### Deprecations\n")
        lines.extend(f"- {item} ({ver})" for ver, item in deprecations)
        lines.append("")

    return "\n".join(lines) + "\n"


def update_skill_file(skill_file: Path, version_content: str) -> None:
    """Update the Version Information section in SKILL.md.

    Args:
        skill_file: Path to SKILL.md
        version_content: New content for the Version Information section

    Raises:
        SyncError: If SKILL.md update fails
    """
    if not skill_file.exists():
        msg = f"SKILL.md not found at {skill_file}"
        raise SyncError(msg)

    content = skill_file.read_text(encoding="utf-8")

    if VERSION_SECTION_PATTERN.search(content):
        new_content = VERSION_SECTION_PATTERN.sub(f"## Version Information\n\n{version_content}", content)
    else:
        new_content = content.rstrip() + f"\n\n## Version Information\n\n{version_content}\n"

    skill_file.write_text(new_content, encoding="utf-8")


def display_release_summary(releases: list[dict[str, str]]) -> None:
    """Print a summary table of releases to the console.

    Args:
        releases: List of release dicts
    """
    table = Table(title="ty Releases Summary")
    table.add_column("Version", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Breaking", style="red")
    table.add_column("Features", style="blue")

    for r in releases[:15]:
        cats = categorize_release(r["body"])
        breaking_count = len(cats["breaking"])
        feature_count = len(cats["features"])

        table.add_row(
            r["version"],
            r["date"],
            str(breaking_count) if breaking_count else "-",
            str(feature_count) if feature_count else "-",
        )

    console.print(table)


def main(
    working_dir: Annotated[
        Path | None,
        typer.Option(
            "--working-dir",
            "-w",
            help="Working directory for the ty skill (default: current directory)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Bypass cooldown period")] = False,
    since: Annotated[
        str | None,
        typer.Option(
            "--since", help="Only fetch releases newer than this version (default: auto-detect from SKILL.md)"
        ),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change without modifying files")] = False,
) -> None:
    """Sync ty release information from GitHub into the skill documentation.

    Fetches release notes from astral-sh/ty GitHub releases, categorizes
    changes (breaking, features, deprecations, new commands), and updates
    the Version Information section in SKILL.md with version-annotated entries.
    """
    resolved_dir = working_dir if working_dir is not None else Path.cwd()

    if not check_cooldown(resolved_dir, force):
        raise typer.Exit(code=0)

    skill_file = resolved_dir / "SKILL.md"

    current_doc_version = get_current_skill_version(skill_file)
    baseline = since or current_doc_version
    if baseline:
        console.print(f"Fetching releases since: [cyan]{baseline}[/cyan]")
    else:
        console.print("No baseline version found, fetching all releases")

    try:
        console.print(Panel(f"Querying GitHub API: {GITHUB_API_BASE}", title="Fetch Releases", border_style="blue"))
        releases = fetch_releases(since_version=baseline)

        if not releases:
            console.print("[yellow]No new releases found[/yellow]")
            update_lock_file(resolved_dir, status="success", last_version=baseline or "", releases_processed=0)
            raise typer.Exit(code=0)

        if baseline:
            new_releases = [r for r in releases if parse_version(r["version"]) > parse_version(baseline)]
        else:
            new_releases = releases

        console.print(
            f"Found [cyan]{len(releases)}[/cyan] total releases, [green]{len(new_releases)}[/green] newer than baseline"
        )

        display_release_summary(releases)

        if dry_run:
            console.print(Panel("Dry run mode - no files modified", title="Dry Run", border_style="yellow"))
            version_content = build_version_section(new_releases, baseline)
            console.print("\n[bold]Would write to Version Information section:[/bold]\n")
            console.print(version_content)
            raise typer.Exit(code=0)

        version_content = build_version_section(new_releases, baseline)
        update_skill_file(skill_file, version_content)

        latest_version = releases[0]["version"]

        console.print(
            Panel(
                f"Updated SKILL.md Version Information section\n"
                f"Latest version: {latest_version}\n"
                f"Releases processed: {len(new_releases)}",
                title="Success",
                border_style="green",
            )
        )

        update_lock_file(
            resolved_dir, status="success", last_version=latest_version, releases_processed=len(new_releases)
        )

    except SyncError as e:
        update_lock_file(resolved_dir, status="failure")
        error_console.print(Panel(f"{e}", title="Sync Failed", border_style="red"))
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        update_lock_file(resolved_dir, status="failure")
        console.print("\nSync cancelled by user")
        raise typer.Exit(code=130) from None


if __name__ == "__main__":
    typer.run(main)
