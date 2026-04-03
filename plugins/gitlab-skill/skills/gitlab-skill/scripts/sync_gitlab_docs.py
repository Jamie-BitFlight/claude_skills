#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
#     "ruamel.yaml>=0.18.0",
# ]
# ///
"""Download and update GitLab CI documentation from official repository.

This script downloads the latest GitLab CI documentation archive,
extracts it to a temporary directory, validates the extraction,
grooms markdown files (transforms links, removes Hugo shortcodes),
generates a file tree index, and atomically replaces the existing documentation.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import tarfile
from collections import defaultdict
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
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")

# Constants
GITLAB_CI_DOCS_URL = "https://gitlab.com/gitlab-org/gitlab/-/archive/master/gitlab-master.tar.gz?path=doc/ci"
CHUNK_SIZE = 8192  # 8KB chunks for streaming download

# Compiled regex patterns (module level for performance)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
ANGLE_BRACKET_SHORTCODE_PATTERN = re.compile(r"{{\s*<\s*(\w+)\s*>}}.*?{{\s*<\s*/\s*\1\s*>}}", re.DOTALL | re.MULTILINE)
PERCENT_SHORTCODE_PATTERN = re.compile(r"{{\s*%\s*(\w+)\s*%}}.*?{{\s*%\s*/\s*\1\s*%}}", re.DOTALL | re.MULTILINE)
SECTION_PATTERN = re.compile(r"(^## Documentation Index\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)


def extract_frontmatter(file_path: Path) -> dict[str, str]:
    """Extract YAML frontmatter from markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary with 'title' and 'description' keys.
        Returns empty dict if no frontmatter or parsing fails.

    Examples:
        >>> extract_frontmatter(Path("debugging.md"))
        {'title': 'Debugging CI/CD pipelines', 'description': 'Configuration validation...'}
        >>> extract_frontmatter(Path("no-frontmatter.md"))
        {}
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        match = FRONTMATTER_PATTERN.match(content)

        if not match:
            return {}

        frontmatter_text = match.group(1)
        yaml = YAML(typ="safe")
        frontmatter_data = yaml.load(frontmatter_text)

        if not isinstance(frontmatter_data, dict):
            return {}

        # Extract only title and description
        result: dict[str, str] = {}
        if "title" in frontmatter_data:
            result["title"] = str(frontmatter_data["title"])
        if "description" in frontmatter_data:
            result["description"] = str(frontmatter_data["description"])

    except (OSError, ScannerError):
        return {}
    else:
        return result


class UpdateError(Exception):
    """Base exception for documentation update errors."""


class DownloadError(UpdateError):
    """Exception raised when documentation download fails."""


class ExtractionError(UpdateError):
    """Exception raised when archive extraction fails."""


class ValidationError(UpdateError):
    """Exception raised when extracted content validation fails."""


def check_cooldown(working_dir: Path, force: bool) -> bool:
    """Check if script should run based on cooldown period.

    Args:
        working_dir: Working directory containing lock file
        force: If True, bypass cooldown check

    Returns:
        True if script should proceed, False if within cooldown period

    Raises:
        UpdateError: If lock file is corrupted or unreadable
    """
    if force:
        return True

    lock_file = working_dir / ".sync-gitlab-docs.lock"

    if not lock_file.exists():
        return True

    try:
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        msg = f"Failed to read lock file {lock_file}: {e}"
        raise UpdateError(msg) from e

    # Only enforce cooldown if last run was successful
    if lock_data.get("last_status") != "success":
        return True

    try:
        last_run = datetime.fromisoformat(lock_data["last_run"])
    except (KeyError, ValueError) as e:
        msg = f"Invalid timestamp in lock file: {e}"
        raise UpdateError(msg) from e

    # Calculate time since last run
    now = datetime.now(UTC)
    time_since_last_run = now - last_run
    cooldown_period = timedelta(days=3)

    if time_since_last_run < cooldown_period:
        # Calculate time remaining
        time_remaining = cooldown_period - time_since_last_run
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)

        console.print(
            Panel(
                f":clock3: Last successful update: {last_run.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f":hourglass: Time remaining: {hours}h {minutes}m\n"
                f":rocket: To force update now: --force",
                title="Update Cooldown Active",
                border_style="yellow",
            )
        )
        return False

    return True


def update_lock_file(working_dir: Path, status: str, files_processed: int = 0) -> None:
    """Update lock file with run metadata.

    Uses atomic write pattern (write to temp, then rename).

    Args:
        working_dir: Working directory containing lock file
        status: Status of the run ("success" or "failure")
        files_processed: Number of files processed (default: 0)

    Raises:
        UpdateError: If lock file write fails
    """
    lock_file = working_dir / ".sync-gitlab-docs.lock"
    temp_lock_file = working_dir / ".sync-gitlab-docs.lock.tmp"

    lock_data = {"last_run": datetime.now(UTC).isoformat(), "last_status": status, "files_processed": files_processed}

    try:
        # Write to temp file
        temp_lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
        # Atomic rename
        temp_lock_file.rename(lock_file)
    except OSError as e:
        msg = f"Failed to write lock file {lock_file}: {e}"
        raise UpdateError(msg) from e


async def _download_with_progress(client: httpx.AsyncClient, url: str, output_path: Path) -> None:
    """Stream download with progress bar display.

    Args:
        client: Active httpx client
        url: URL to download
        output_path: Destination file path

    Raises:
        httpx.HTTPStatusError: If HTTP error occurs
        OSError: If file write fails
    """
    async with client.stream("GET", url) as response:
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading GitLab CI docs...", total=total_size)

            with output_path.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))


async def download_archive(url: str, output_path: Path) -> None:
    """Download GitLab CI docs archive with progress indication.

    Args:
        url: URL of the archive to download
        output_path: Path where archive should be saved

    Raises:
        DownloadError: If download fails or HTTP error occurs
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            await _download_with_progress(client, url, output_path)
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code} error downloading archive"
        raise DownloadError(msg) from e
    except httpx.RequestError as e:
        msg = f"Network error downloading archive: {e}"
        raise DownloadError(msg) from e
    except OSError as e:
        msg = f"Failed to write archive to {output_path}: {e}"
        raise DownloadError(msg) from e


def extract_archive(archive_path: Path, extract_to: Path) -> None:
    """Extract tar.gz archive to specified directory.

    Args:
        archive_path: Path to the tar.gz archive
        extract_to: Directory where archive should be extracted

    Raises:
        ExtractionError: If extraction fails
    """
    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            progress.add_task("Extracting archive...", total=None)

            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=extract_to, filter="data")

    except tarfile.TarError as e:
        msg = f"Failed to extract archive: {e}"
        raise ExtractionError(msg) from e
    except OSError as e:
        msg = f"Filesystem error during extraction: {e}"
        raise ExtractionError(msg) from e


def validate_extraction(extract_dir: Path) -> Path:
    """Validate extracted content and return path to docs directory.

    Args:
        extract_dir: Directory where archive was extracted

    Returns:
        Path to the actual documentation directory

    Raises:
        ValidationError: If extracted content is invalid
    """
    # The archive extracts to gitlab-master-doc-ci/doc/ci/
    # Find the actual doc/ci directory
    extracted_items = list(extract_dir.iterdir())

    if not extracted_items:
        msg = f"Extraction produced no files in {extract_dir}"
        raise ValidationError(msg)

    # Should have one top-level directory (gitlab-master-doc-ci)
    if len(extracted_items) != 1 or not extracted_items[0].is_dir():
        msg = f"Unexpected extraction structure in {extract_dir}: {[p.name for p in extracted_items]}"
        raise ValidationError(msg)

    top_dir = extracted_items[0]
    docs_path = top_dir / "doc" / "ci"

    if not docs_path.exists() or not docs_path.is_dir():
        msg = f"Expected doc/ci directory not found at {docs_path} (parent: {top_dir})"
        raise ValidationError(msg)

    # Verify we have markdown files
    md_files = list(docs_path.rglob("*.md"))
    if not md_files:
        msg = f"No markdown files found in {docs_path}"
        raise ValidationError(msg)

    return docs_path


class GroomingError(UpdateError):
    """Exception raised when markdown grooming fails."""


def transform_links(content: str, current_file: Path, docs_root: Path) -> str:
    """Transform markdown links to use relative paths or GitLab raw URLs.

    Internal links (within docs_root) are converted to relative paths starting with ./
    External links (outside docs_root) are converted to GitLab raw URLs.

    Args:
        content: Markdown file content
        current_file: Path to the current markdown file being processed
        docs_root: Root directory of the documentation (e.g., .../doc/ci/)

    Returns:
        Transformed content with updated links

    Examples:
        >>> # From doc/ci/yaml/index.md linking to ../pipelines/index.md
        >>> transform_links("[text](../pipelines/index.md)", current_file, docs_root)
        '[text](./pipelines/index.md)'
        >>> # From doc/ci/yaml/index.md linking to ../../api/api_resources.md
        >>> transform_links("[text](../../api/api_resources.md)", current_file, docs_root)
        '[text](https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/api/api_resources.md?ref_type=heads)'
    """

    def replace_link(match: re.Match[str]) -> str:
        link_text = match.group(1)
        link_path = match.group(2)

        # Skip if it's already an absolute URL, anchor link, or mailto
        if link_path.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)

        # Resolve the link target relative to the current file's directory
        # This handles arbitrary nesting depths correctly
        link_target = (current_file.parent / link_path).resolve()

        # Check if the resolved link target is within docs_root
        try:
            # If relative_to succeeds, the link is internal to docs_root
            rel_to_root = link_target.relative_to(docs_root)
        except ValueError:
            # Link target is outside docs_root - convert to GitLab raw URL
            # Need to determine the path relative to the GitLab doc/ directory
            # docs_root is .../doc/ci/, so parent is .../doc/
            doc_dir = docs_root.parent

            try:
                # Get path relative to doc/ directory
                rel_to_doc = link_target.relative_to(doc_dir)
            except ValueError:
                # Link is outside doc/ entirely - keep original
                return match.group(0)
            else:
                gitlab_url = f"https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/{rel_to_doc}?ref_type=heads"
                return f"[{link_text}]({gitlab_url})"
        else:
            # Internal link - convert to relative path from docs_root with ./ prefix
            return f"[{link_text}](./{rel_to_root})"

    return LINK_PATTERN.sub(replace_link, content)


def remove_hugo_shortcodes(content: str) -> str:
    r"""Remove Hugo shortcodes from markdown content.

    Removes {{< details >}}, {{< history >}}, and {{% %}} syntax blocks.

    Args:
        content: Markdown file content

    Returns:
        Content with Hugo shortcodes removed

    Examples:
        >>> remove_hugo_shortcodes("{{< details >}}\\nContent\\n{{< /details >}}")
        ''
        >>> remove_hugo_shortcodes("Text\\n{{< history >}}\\nVersion info\\n{{< /history >}}\\nMore text")
        'Text\\n\\nMore text'
    """
    # Use module-level compiled patterns for performance
    content = ANGLE_BRACKET_SHORTCODE_PATTERN.sub("", content)
    return PERCENT_SHORTCODE_PATTERN.sub("", content)


def groom_markdown_files(docs_dir: Path) -> int:
    """Groom markdown files by transforming links and removing Hugo shortcodes.

    Processes all .md files recursively in the docs directory.

    Args:
        docs_dir: Directory containing markdown files to groom

    Returns:
        Number of files processed

    Raises:
        GroomingError: If file processing fails
    """
    md_files = list(docs_dir.rglob("*.md"))

    if not md_files:
        msg = f"No markdown files found in {docs_dir}"
        raise GroomingError(msg)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Grooming markdown files...", total=len(md_files))

            for md_file in md_files:
                # Read file content
                content = md_file.read_text(encoding="utf-8")

                # Apply transformations with file context for path-aware link resolution
                content = transform_links(content, current_file=md_file, docs_root=docs_dir)
                content = remove_hugo_shortcodes(content)

                # Write back
                md_file.write_text(content, encoding="utf-8")

                progress.update(task, advance=1)

    except OSError as e:
        msg = f"Failed to process markdown files: {e}"
        raise GroomingError(msg) from e

    return len(md_files)


def generate_file_tree(docs_dir: Path) -> str:
    """Generate markdown tree with clickable links and descriptions for all files.

    Extracts title and description from YAML frontmatter in each markdown file.
    Format:
        ├── [Title from frontmatter](./ci/path/file.md)
            Description from frontmatter

    Falls back to filename if no frontmatter exists.

    Args:
        docs_dir: Directory to scan for markdown files

    Returns:
        Formatted markdown string with file tree including titles and descriptions

    Raises:
        GroomingError: If directory scanning fails
    """
    try:
        md_files = sorted(docs_dir.rglob("*.md"))

        if not md_files:
            return "*No markdown files found*\n"

        # Build tree structure
        tree_lines = ["```text"]
        tree_lines.append(f"{docs_dir.name}/")

        # Group files by directory
        dirs: dict[Path, list[Path]] = defaultdict(list)
        for file in md_files:
            parent = file.parent
            dirs[parent].append(file)

        # Sort directories by path
        sorted_dirs = sorted(dirs.keys())

        for dir_path in sorted_dirs:
            # Calculate relative path from docs_dir
            try:
                rel_dir = dir_path.relative_to(docs_dir)
            except ValueError:
                continue

            # Indent based on depth
            depth = len(rel_dir.parts) if str(rel_dir) != "." else 0
            indent = "  " * depth

            # Add directory line if not root
            if str(rel_dir) != ".":
                tree_lines.append(f"{indent}├── {rel_dir.name}/")

            # Add files in this directory
            for file in sorted(dirs[dir_path]):
                file_indent = "  " * (depth + 1)
                rel_path = file.relative_to(docs_dir)

                # Extract frontmatter for title and description
                frontmatter = extract_frontmatter(file)
                title = frontmatter.get("title", file.name)
                description = frontmatter.get("description")

                # Add file link with title
                tree_lines.append(f"{file_indent}├── [{title}](./references/ci/{rel_path})")

                # Add description on next line if present
                if description:
                    desc_indent = file_indent + "    "
                    tree_lines.append(f"{desc_indent}{description}")

        tree_lines.append("```")

        return "\n".join(tree_lines) + "\n"

    except OSError as e:
        msg = f"Failed to generate file tree: {e}"
        raise GroomingError(msg) from e


def update_skill_index(skill_file: Path, file_tree: str) -> None:
    """Update SKILL.md with generated file tree index.

    Finds or creates ## Documentation Index section and replaces its content.

    Args:
        skill_file: Path to SKILL.md file
        file_tree: Generated file tree markdown

    Raises:
        GroomingError: If SKILL.md update fails
    """
    try:
        if not skill_file.exists():
            msg = f"SKILL.md not found at {skill_file}"
            raise GroomingError(msg)

        content = skill_file.read_text(encoding="utf-8")

        # Pattern to match ## Documentation Index section
        section_pattern = re.compile(r"(^## Documentation Index\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)

        # Check if section exists
        if section_pattern.search(content):
            # Replace existing section content
            new_content = section_pattern.sub(f"## Documentation Index\n\n{file_tree}\n", content)
        else:
            # Append new section at the end
            new_content = content.rstrip() + f"\n\n## Documentation Index\n\n{file_tree}\n"

        skill_file.write_text(new_content, encoding="utf-8")

    except OSError as e:
        msg = f"Failed to update SKILL.md: {e}"
        raise GroomingError(msg) from e


def atomic_replace(source: Path, target: Path) -> None:
    """Atomically replace target directory with source.

    Args:
        source: Source directory to move
        target: Target directory to replace

    Raises:
        OSError: If directory operations fail
    """
    # Remove old directory if it exists
    if target.exists():
        shutil.rmtree(target)

    # Move new directory into place
    source.rename(target)


async def update_docs(working_dir: Path, cleanup: bool = True) -> int:
    """Download and update GitLab CI documentation.

    Args:
        working_dir: Working directory (default: current directory)
        cleanup: Whether to clean up temporary files on success

    Returns:
        Number of markdown files processed

    Raises:
        UpdateError: If any step of the update process fails
    """
    # Resolve paths relative to working directory
    references_dir = working_dir / "references"
    ci_dir = references_dir / "ci"
    ci_new_dir = references_dir / "ci-new"
    archive_path = working_dir / "gitlab-ci-docs.tar.gz"
    skill_file = working_dir / "SKILL.md"

    # Create references directory if needed
    references_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download archive
        console.print(
            Panel(f"Downloading from: {GITLAB_CI_DOCS_URL}", title=":inbox_tray: Download", border_style="blue")
        )
        await download_archive(GITLAB_CI_DOCS_URL, archive_path)

        # Extract archive
        console.print(Panel(f"Extracting to: {ci_new_dir}", title=":package: Extract", border_style="blue"))
        ci_new_dir.mkdir(parents=True, exist_ok=True)
        extract_archive(archive_path, ci_new_dir)

        # Validate extraction
        console.print(Panel("Validating extracted content...", title=":mag: Validate", border_style="blue"))
        docs_path = validate_extraction(ci_new_dir)

        # Count markdown files for feedback
        md_files = list(docs_path.rglob("*.md"))
        console.print(f"Found {len(md_files)} markdown files")

        # Groom markdown files
        console.print(
            Panel("Transforming links and removing Hugo shortcodes...", title=":broom: Groom", border_style="blue")
        )
        processed_count = groom_markdown_files(docs_path)
        console.print(f"Processed {processed_count} markdown files")

        # Generate file tree and update SKILL.md
        console.print(Panel("Generating documentation index...", title=":file_folder: Index", border_style="blue"))
        file_tree = generate_file_tree(docs_path)
        update_skill_index(skill_file, file_tree)
        console.print(f"Updated {skill_file.name} with file tree index")

        # Atomic replacement
        console.print(
            Panel(
                f"Replacing {ci_dir} with new documentation",
                title=":arrows_counterclockwise: Replace",
                border_style="blue",
            )
        )
        atomic_replace(docs_path, ci_dir)

        # Success message
        console.print(
            Panel(
                f":white_check_mark: Successfully updated GitLab CI documentation\n"
                f"Location: {ci_dir}\n"
                f"Files: {len(md_files)} markdown files\n"
                f"Processed: {processed_count} files groomed\n"
                f"Index: {skill_file.name} updated",
                title="Success",
                border_style="green",
            )
        )

    except UpdateError:
        # Re-raise our own errors
        raise
    except Exception as e:
        # Wrap unexpected errors
        msg = f"Unexpected error during update: {e}"
        raise UpdateError(msg) from e
    else:
        return processed_count
    finally:
        # Cleanup temporary files
        if cleanup:
            if archive_path.exists():
                archive_path.unlink()
            if ci_new_dir.exists():
                shutil.rmtree(ci_new_dir)


def main(
    working_dir: Annotated[
        Path | None,
        typer.Option(
            "--working-dir",
            "-w",
            help="Working directory (default: current directory)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    no_cleanup: Annotated[
        bool, typer.Option("--no-cleanup", help="Keep temporary files after successful update")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Bypass 3-day cooldown period")] = False,
) -> None:
    """Download and update GitLab CI documentation from official repository.

    This script downloads the latest GitLab CI documentation archive,
    extracts it to a temporary directory, validates the extraction,
    and atomically replaces the existing documentation.

    The documentation will be placed in: WORKING_DIR/references/ci/

    A lock file prevents updates more than once every 3 days (unless --force is used).
    """
    # Resolve working_dir here instead of in function signature
    resolved_dir = working_dir if working_dir is not None else Path.cwd()

    # Check cooldown period
    if not check_cooldown(resolved_dir, force):
        raise typer.Exit(code=0)

    try:
        files_processed = asyncio.run(update_docs(resolved_dir, cleanup=not no_cleanup))
        # Update lock file with success status
        update_lock_file(resolved_dir, status="success", files_processed=files_processed)
    except UpdateError as e:
        # Update lock file with failure status
        update_lock_file(resolved_dir, status="failure", files_processed=0)
        error_console.print(Panel(f":cross_mark: {e}", title="Update Failed", border_style="red"))
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        # Update lock file with failure status
        update_lock_file(resolved_dir, status="failure", files_processed=0)
        console.print("\n:warning: Update cancelled by user")
        raise typer.Exit(code=130) from None


if __name__ == "__main__":
    typer.run(main)
