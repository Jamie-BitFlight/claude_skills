#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "tiktoken>=0.7.0",
#   "rich>=13.0",
#   "python-dotenv>=1.0.0",
# ]
# ///
"""Group a day's dataset files into token-bounded semantic buckets.

Reads the ``dataset/`` directory produced by ``collect_day_dataset.py`` and
groups source files into token-bounded semantic buckets, writing each bucket's
manifest and content into ``<day_dir>/buckets/bucket_NNN/``.

Uses tiktoken with ``cl100k_base`` encoding as a proxy for token counting
(not the exact Claude tokenizer, but a reasonable approximation for budget sizing).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

import os

import tiktoken
import typer
from rich.console import Console

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TOKEN_LIMIT: int = int(os.environ.get("DAILY_RELEASES_TOKEN_LIMIT", "100000"))
_TIKTOKEN_ENCODING: str = "p50k_base"

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="bucket_day_data",
    help="Group a day's dataset files into token-bounded semantic buckets.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# AppExit helper
# ---------------------------------------------------------------------------


class AppExit(typer.Exit):
    """Exit with a user-friendly error message printed to stderr."""

    exit_code: int

    def __init__(self, code: int = 1, message: str | None = None) -> None:
        """Initialise exit with optional message.

        Args:
            code: Process exit code (default 1).
            message: Human-readable error message printed to stderr in red.
        """
        if message is not None:
            err_console.print(f"[red]{message}[/red]")
        self.exit_code = code
        super().__init__(code=code)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FileEntry:
    """Metadata for a single source file from files.json.

    Attributes:
        path: Repository-relative file path.
        is_source: True when the file extension is a source type.
        is_excluded: True when the file is in an excluded directory.
        diff_file: Relative path inside the dataset directory where the diff is stored,
            or empty string when no diff was written.
    """

    path: str
    is_source: bool
    is_excluded: bool
    diff_file: str


@dataclass
class CommitRecord:
    """Metadata for a single commit from commits.json.

    Attributes:
        sha: Full 40-character commit SHA.
        subject: First line of the commit message.
        body: Remainder of the commit message after the subject line.
        author: Author name and e-mail formatted as ``Name <email>``.
        date: ISO 8601 UTC timestamp.
        files_touched: Sorted list of repository-relative paths changed by this commit.
    """

    sha: str
    subject: str
    body: str
    author: str
    date: str
    files_touched: list[str]


@dataclass
class FileGroup:
    """A semantic group of files sharing the same top-2-level directory prefix.

    Attributes:
        prefix: Group key (e.g. ``src/auth`` or ``root`` for top-level files).
        file_paths: Ordered list of repository-relative file paths in this group.
        token_count: Total estimated token count for all files in the group.
        commit_shas: Union of SHAs for all commits touching any file in this group.
    """

    prefix: str
    file_paths: list[str] = field(default_factory=list)
    token_count: int = 0
    commit_shas: set[str] = field(default_factory=set)


@dataclass
class Bucket:
    """A token-bounded collection of file groups for LLM processing.

    Attributes:
        bucket_id: Zero-padded three-digit bucket identifier string (e.g. ``001``).
        file_paths: Ordered list of repository-relative file paths in this bucket.
        token_count: Total estimated token count for this bucket.
        commit_shas: Union of SHAs for commits touching any file in this bucket.
    """

    bucket_id: str
    file_paths: list[str] = field(default_factory=list)
    token_count: int = 0
    commit_shas: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def load_file_entries(dataset_dir: Path) -> list[FileEntry]:
    """Load and filter file records from ``files.json``.

    Only returns entries where ``is_source=true`` and ``is_excluded=false``.

    Args:
        dataset_dir: Path to the ``dataset/`` directory.

    Returns:
        List of FileEntry instances eligible for bucketing.

    Raises:
        AppExit: When ``files.json`` is missing or contains invalid JSON.
    """
    files_json = dataset_dir / "files.json"
    if not files_json.exists():
        raise AppExit(code=1, message=f"files.json not found at {files_json}")

    try:
        raw: list[dict] = json.loads(files_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppExit(code=1, message=f"Invalid JSON in files.json: {exc}") from exc

    entries = [
        FileEntry(
            path=item["path"],
            is_source=item.get("is_source", False),
            is_excluded=item.get("is_excluded", False),
            diff_file=item.get("diff_file", ""),
        )
        for item in raw
        if item.get("is_source") and not item.get("is_excluded")
    ]

    err_console.print(f"[dim]Loaded {len(entries)} eligible source files from files.json[/dim]")
    return entries


def load_commit_records(dataset_dir: Path) -> list[CommitRecord]:
    """Load commit records from ``commits.json``.

    Args:
        dataset_dir: Path to the ``dataset/`` directory.

    Returns:
        List of CommitRecord instances.

    Raises:
        AppExit: When ``commits.json`` is missing or contains invalid JSON.
    """
    commits_json = dataset_dir / "commits.json"
    if not commits_json.exists():
        raise AppExit(code=1, message=f"commits.json not found at {commits_json}")

    try:
        raw: list[dict] = json.loads(commits_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppExit(code=1, message=f"Invalid JSON in commits.json: {exc}") from exc

    records = [
        CommitRecord(
            sha=item["sha"],
            subject=item.get("subject", ""),
            body=item.get("body", ""),
            author=item.get("author", ""),
            date=item.get("date", ""),
            files_touched=item.get("files_touched", []),
        )
        for item in raw
    ]

    err_console.print(f"[dim]Loaded {len(records)} commit records from commits.json[/dim]")
    return records


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    """Count tokens in a text string using the given tiktoken encoding.

    Args:
        text: Input text to tokenize.
        enc: tiktoken Encoding instance.

    Returns:
        Number of tokens in the text.
    """
    return len(enc.encode(text))


def read_diff_text(day_dir: Path, diff_file: str) -> str:
    """Read the contents of a diff file relative to ``day_dir``.

    Returns an empty string if the diff file path is empty or the file does
    not exist, rather than raising an error.

    Args:
        day_dir: Root day directory (parent of ``dataset/``).
        diff_file: Relative path as stored in files.json (e.g. ``dataset/diffs/foo.diff``).

    Returns:
        Decoded diff text, or empty string when not available.
    """
    if not diff_file:
        return ""
    diff_path = day_dir / diff_file
    if not diff_path.exists():
        return ""
    return diff_path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Semantic prefix grouping
# ---------------------------------------------------------------------------


def semantic_prefix(file_path: str) -> str:
    """Compute the semantic group key for a file path.

    Uses the top-2-level directory components as the prefix. Files with no
    directory component (root-level files) are assigned to the ``root`` group.

    Examples:
        ``src/auth/login.py`` -> ``src/auth``
        ``src/module/sub/file.py`` -> ``src/module``
        ``README.md`` -> ``root``

    Args:
        file_path: Repository-relative file path.

    Returns:
        Group key string.
    """
    parts = Path(file_path).parts
    if len(parts) <= 1:
        return "root"
    return "/".join(parts[:2])


# ---------------------------------------------------------------------------
# Bucketing algorithm
# ---------------------------------------------------------------------------


def build_file_groups(
    file_entries: list[FileEntry], commit_records: list[CommitRecord], day_dir: Path, enc: tiktoken.Encoding
) -> list[FileGroup]:
    """Build semantic file groups with token counts and commit SHA mappings.

    Steps:
    1. Build a map from file path to list of commits that touched it.
    2. For each source file, compute its token count from diff text + commit messages.
    3. Group files by semantic prefix (top-2-level directory).
    4. Sort groups alphabetically for determinism.

    Args:
        file_entries: Eligible source file entries (is_source=true, is_excluded=false).
        commit_records: All commit records for the day.
        day_dir: Root day directory for resolving diff file paths.
        enc: tiktoken Encoding instance for token counting.

    Returns:
        List of FileGroup instances sorted alphabetically by prefix.
    """
    # Build file -> commits mapping
    file_to_commits: dict[str, list[CommitRecord]] = {}
    for commit in commit_records:
        for touched_path in commit.files_touched:
            file_to_commits.setdefault(touched_path, []).append(commit)

    # Build groups indexed by prefix
    groups: dict[str, FileGroup] = {}
    for entry in file_entries:
        prefix = semantic_prefix(entry.path)
        if prefix not in groups:
            groups[prefix] = FileGroup(prefix=prefix)

        group = groups[prefix]
        group.file_paths.append(entry.path)

        # Token count: diff text + commit messages for commits touching this file
        diff_text = read_diff_text(day_dir, entry.diff_file)
        file_tokens = count_tokens(diff_text, enc)

        touching_commits = file_to_commits.get(entry.path, [])
        for commit in touching_commits:
            commit_text = f"{commit.subject}\n{commit.body}"
            file_tokens += count_tokens(commit_text, enc)
            group.commit_shas.add(commit.sha)

        group.token_count += file_tokens

    return sorted(groups.values(), key=lambda g: g.prefix)


def assign_buckets(groups: list[FileGroup], token_limit: int) -> list[Bucket]:
    """Assign file groups to token-bounded buckets using greedy filling.

    Iterates sorted groups and adds each group to the current bucket if it
    fits within the token limit. When a group would exceed the limit, a new
    bucket is started. Groups larger than ``token_limit`` on their own are
    placed in a single-group bucket (never split).

    Args:
        groups: File groups sorted alphabetically by prefix.
        token_limit: Maximum tokens allowed per bucket.

    Returns:
        List of Bucket instances in fill order.
    """
    buckets: list[Bucket] = []
    current: Bucket | None = None

    def new_bucket() -> Bucket:
        bucket_id = f"{len(buckets) + 1:03d}"
        return Bucket(bucket_id=bucket_id)

    for group in groups:
        if current is None:
            current = new_bucket()

        fits = current.token_count + group.token_count <= token_limit
        if not fits and current.file_paths:
            # Flush current bucket and start fresh
            buckets.append(current)
            current = new_bucket()

        # Add group to current bucket (even if it exceeds limit on its own)
        current.file_paths.extend(group.file_paths)
        current.token_count += group.token_count
        current.commit_shas.update(group.commit_shas)

    if current is not None and current.file_paths:
        buckets.append(current)

    return buckets


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def build_content_text(
    bucket: Bucket, file_entries_by_path: dict[str, FileEntry], commits_by_sha: dict[str, CommitRecord], day_dir: Path
) -> str:
    """Build the human-readable content.txt string for a bucket.

    Format:
        === File: <path> ===
        <diff content>

        === Commits ===
        commit <sha>
        Author: <author>
        Date: <date>
        Subject: <subject>

        <body>

    Args:
        bucket: The Bucket whose content to render.
        file_entries_by_path: Map from file path to FileEntry.
        commits_by_sha: Map from SHA to CommitRecord for all commits in the day.
        day_dir: Root day directory for resolving diff file paths.

    Returns:
        Rendered content string.
    """
    lines: list[str] = []

    for file_path in bucket.file_paths:
        lines.append(f"=== File: {file_path} ===")
        entry = file_entries_by_path.get(file_path)
        if entry:
            diff_text = read_diff_text(day_dir, entry.diff_file)
            lines.append(diff_text or "(no diff available)")
        else:
            lines.append("(entry not found)")
        lines.append("")

    lines.append("=== Commits ===")
    for sha in sorted(bucket.commit_shas):
        commit = commits_by_sha.get(sha)
        if commit is None:
            continue
        lines.extend((
            f"commit {commit.sha}",
            f"Author: {commit.author}",
            f"Date: {commit.date}",
            f"Subject: {commit.subject}",
            "",
        ))
        if commit.body:
            lines.extend((commit.body, ""))

    return "\n".join(lines)


def write_bucket(
    buckets_dir: Path,
    bucket: Bucket,
    file_entries_by_path: dict[str, FileEntry],
    commits_by_sha: dict[str, CommitRecord],
    day_dir: Path,
) -> None:
    """Write a bucket's ``manifest.json`` and ``content.txt`` to disk.

    Creates ``<buckets_dir>/bucket_<bucket_id>/`` and writes both files.

    Args:
        buckets_dir: Parent directory for all bucket subdirectories.
        bucket: The Bucket to write.
        file_entries_by_path: Map from file path to FileEntry.
        commits_by_sha: Map from SHA to CommitRecord.
        day_dir: Root day directory for resolving diff file paths.
    """
    bucket_dir = buckets_dir / f"bucket_{bucket.bucket_id}"
    bucket_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "bucket_id": bucket.bucket_id,
        "files": bucket.file_paths,
        "token_count": bucket.token_count,
        "commit_shas": sorted(bucket.commit_shas),
    }
    (bucket_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    content = build_content_text(bucket, file_entries_by_path, commits_by_sha, day_dir)
    (bucket_dir / "content.txt").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.command()
def main(
    day_dir: Annotated[
        Path,
        typer.Argument(
            help="Date directory containing dataset/ (e.g. ./daily-releases/2026-02-10/)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ],
    token_limit: Annotated[
        int,
        typer.Option(
            "--token-limit",
            help=f"Max tokens per bucket (default: DAILY_RELEASES_TOKEN_LIMIT env var or {DEFAULT_TOKEN_LIMIT})",
            min=1,
        ),
    ] = DEFAULT_TOKEN_LIMIT,
) -> None:
    """Group dataset files into token-bounded semantic buckets.

    Reads ``<day_dir>/dataset/files.json`` and ``commits.json``, groups
    eligible source files by semantic prefix into token-bounded buckets,
    and writes each bucket under ``<day_dir>/buckets/bucket_NNN/``.

    Token counts use tiktoken ``cl100k_base`` encoding as a proxy — not the
    exact Claude tokenizer, but a reasonable approximation for budget sizing.

    Progress is printed to stderr; the summary table is printed to stdout.
    """
    dataset_dir = day_dir / "dataset"
    if not dataset_dir.exists():
        raise AppExit(code=1, message=f"dataset/ directory not found under {day_dir}")

    err_console.print(f"[bold]bucket_day_data[/bold] {day_dir} (token_limit={token_limit:,})")

    err_console.print("[dim]Step 1/4: Loading file entries[/dim]")
    file_entries = load_file_entries(dataset_dir)

    err_console.print("[dim]Step 2/4: Loading commit records[/dim]")
    commit_records = load_commit_records(dataset_dir)

    err_console.print("[dim]Step 3/4: Building file groups and counting tokens[/dim]")
    enc = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
    groups = build_file_groups(file_entries, commit_records, day_dir, enc)

    err_console.print("[dim]Step 4/4: Assigning buckets[/dim]")
    buckets = assign_buckets(groups, token_limit)

    # Index structures for writing
    file_entries_by_path: dict[str, FileEntry] = {e.path: e for e in file_entries}
    commits_by_sha: dict[str, CommitRecord] = {c.sha: c for c in commit_records}

    buckets_dir = day_dir / "buckets"
    for bucket in buckets:
        write_bucket(buckets_dir, bucket, file_entries_by_path, commits_by_sha, day_dir)

    # Summary output to stdout
    total_files = len(file_entries)
    num_buckets = len(buckets)
    console.print(f"Bucketed {total_files} files into {num_buckets} buckets (token_limit={token_limit:,})")
    for bucket in buckets:
        console.print(f"  bucket_{bucket.bucket_id}: {len(bucket.file_paths)} files, {bucket.token_count:,} tokens")

    err_console.print(":white_check_mark: [green]Bucketing complete[/green]")


if __name__ == "__main__":
    try:
        app()
    except AppExit as exc:
        sys.exit(exc.exit_code)
