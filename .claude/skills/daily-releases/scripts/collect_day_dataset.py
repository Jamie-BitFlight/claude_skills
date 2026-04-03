#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "daily-releases-lib",
#   "typer>=0.21.0",
#   "PyGithub>=2.1.1",
#   "python-dotenv>=1.0.0",
# ]
#
# [tool.uv.sources]
# daily-releases-lib = { path = "daily_releases_lib", editable = true }
# ///
"""Collect per-day dataset for the daily-releases chunked pipeline.

Extracts per-file diffs, commit metadata, and GitHub issues referenced in
commits for a given base_ref..head_ref range, writing structured JSON and
diff files into ``<output_dir>/dataset/``.

Uses PyGithub and the GitHub REST API — no local git repository required.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

import os

import typer
from daily_releases_lib.github_utils import AppExit, get_github_repo, make_github_client
from github import GithubException
from rich.console import Console

if TYPE_CHECKING:
    from github.GitCommit import GitCommit
    from github.Repository import Repository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REPO: str = os.environ.get("DEFAULT_REPO") or "Jamie-BitFlight/claude_skills"
EMPTY_TREE_SHA: str = os.environ.get("EMPTY_TREE_SHA") or "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

#: Source file extensions to include in the dataset.
SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    ".py",
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".tsx",
    ".sh",
    ".md",
    ".json",
    ".yaml",
    ".yml",
})

#: Path prefixes whose files are excluded from diff output (is_excluded=true).
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "dist/",
    "build/",
    ".cache/",
    "node_modules/",
    "vendor/",
    "third_party/",
    ".venv/",
    "__pycache__/",
)

#: Regex matching "closes/fixes/resolves #N" in commit messages (case-insensitive).
_ISSUE_REF_RE: re.Pattern[str] = re.compile(r"(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="collect_day_dataset",
    help="Collect per-file diffs, commit metadata, and GitHub issues into dataset/.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FileRecord:
    """Metadata for a single changed source file.

    Attributes:
        path: Repository-relative file path.
        status: Single-letter git status: A (added), M (modified), D (deleted), R (renamed).
        lines_added: Number of lines added in this file's diff.
        lines_deleted: Number of lines removed in this file's diff.
        is_source: True when the file extension is in SOURCE_EXTENSIONS.
        is_excluded: True when the file path starts with an excluded prefix.
        diff_file: Relative path inside the dataset directory where the diff is stored,
            or empty string when no diff was written.
    """

    path: str
    status: str
    lines_added: int
    lines_deleted: int
    is_source: bool
    is_excluded: bool
    diff_file: str


@dataclass
class CommitRecord:
    """Metadata for a single commit.

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
class IssueRecord:
    """Minimal GitHub issue/PR record.

    Attributes:
        number: GitHub issue number.
        title: Issue title.
        state: ``open`` or ``closed``.
        url: HTML URL of the issue.
    """

    number: int
    title: str
    state: str
    url: str


# ---------------------------------------------------------------------------
# File record helpers
# ---------------------------------------------------------------------------


def _sanitize_path(file_path: str) -> str:
    """Sanitize a repository file path for use as a diff filename.

    Replaces ``/`` with ``_`` and keeps other characters unchanged.
    Example: ``src/module/file.py`` becomes ``src_module_file.py``.

    Args:
        file_path: Repository-relative path to the file.

    Returns:
        Sanitized filename suitable for use inside the ``diffs/`` directory.
    """
    return file_path.replace("/", "_")


def _status_letter(github_status: str) -> str:
    """Convert a GitHub file status string to a single-letter status code.

    Args:
        github_status: Status string from the GitHub API
            (e.g. ``added``, ``modified``, ``deleted``, ``renamed``, ``copied``).

    Returns:
        Single letter: ``A`` (added/copied), ``D`` (deleted), ``R`` (renamed),
        or ``M`` (modified/anything else).
    """
    return {"added": "A", "deleted": "D", "renamed": "R", "copied": "A"}.get(github_status, "M")


def _count_patch_lines(patch: str | None) -> tuple[int, int]:
    """Count added and deleted lines in a unified diff patch string.

    Args:
        patch: Unified diff text as returned by the GitHub API, or None.

    Returns:
        Tuple of ``(lines_added, lines_deleted)``.
    """
    if not patch:
        return 0, 0
    added = deleted = 0
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    return added, deleted


def _write_patch_file(diffs_dir: Path, file_path: str, patch: str | None) -> str:
    """Write a patch string to the diffs directory and return the relative path.

    Args:
        diffs_dir: Directory where individual diff files are stored.
        file_path: Repository-relative file path (used to derive the filename).
        patch: Unified diff text to write, or None when no diff is available.

    Returns:
        Relative path string of the form ``dataset/diffs/<name>.diff``,
        or empty string when ``patch`` is None.
    """
    if patch is None:
        return ""
    diff_filename = f"{_sanitize_path(file_path)}.diff"
    (diffs_dir / diff_filename).write_text(patch, encoding="utf-8")
    return f"dataset/diffs/{diff_filename}"


# ---------------------------------------------------------------------------
# File record collection
# ---------------------------------------------------------------------------


def _collect_initial_file_records(gh_repo: Repository, head_ref: str) -> list[FileRecord]:
    """List all source files at head_ref via the recursive tree API.

    Used when ``base_ref`` is the empty-tree SHA, meaning there are no prior
    commits. All files are treated as added (status ``A``) with no diff content.

    Args:
        gh_repo: Authenticated PyGithub Repository object.
        head_ref: Commit SHA whose tree to examine.

    Returns:
        List of FileRecord instances with status ``A`` and empty ``diff_file``.
    """
    tree = gh_repo.get_git_tree(head_ref, recursive=True)
    records: list[FileRecord] = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        path: str = item.path
        if Path(path).suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        is_excluded = any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
        records.append(
            FileRecord(
                path=path,
                status="A",
                lines_added=0,
                lines_deleted=0,
                is_source=True,
                is_excluded=is_excluded,
                diff_file="",
            )
        )
    err_console.print(f"[dim]  {len(records)} source files found in initial tree[/dim]")
    return records


def collect_file_records(gh_repo: Repository, base_ref: str, head_ref: str, diffs_dir: Path) -> list[FileRecord]:
    """Extract per-file diff records for the commit range via GitHub API.

    For the empty-tree base (first day of the repository), uses the recursive
    tree API to list all files at ``head_ref`` and treats them as added. For
    all other ranges, uses the GitHub compare REST API to get per-file diffs
    with patch text.

    The GitHub compare API supports ranges of up to 300 files. Files beyond
    that limit are omitted from the comparison response.

    Args:
        gh_repo: Authenticated PyGithub Repository object.
        base_ref: Git commit SHA before the range (exclusive), or EMPTY_TREE_SHA.
        head_ref: Git commit SHA at the end of the range (inclusive).
        diffs_dir: Directory path where individual diff files are written.

    Returns:
        List of FileRecord instances, one per changed file that matches
        SOURCE_EXTENSIONS.
    """
    err_console.print(f"[dim]Extracting file diffs {base_ref[:8]}..{head_ref[:8]} via GitHub API[/dim]")
    diffs_dir.mkdir(parents=True, exist_ok=True)

    if base_ref == EMPTY_TREE_SHA:
        return _collect_initial_file_records(gh_repo, head_ref)

    comparison = gh_repo.compare(base_ref, head_ref)
    records: list[FileRecord] = []
    for f in comparison.files:
        path: str = f.filename
        if Path(path).suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        is_excluded = any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
        patch: str | None = getattr(f, "patch", None)
        diff_file = "" if is_excluded else _write_patch_file(diffs_dir, path, patch)
        lines_added, lines_deleted = _count_patch_lines(patch)
        records.append(
            FileRecord(
                path=path,
                status=_status_letter(f.status),
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                is_source=True,
                is_excluded=is_excluded,
                diff_file=diff_file,
            )
        )

    err_console.print(f"[dim]  {len(records)} source files processed[/dim]")
    return records


# ---------------------------------------------------------------------------
# Commit record collection
# ---------------------------------------------------------------------------


def _commit_record_from_gh(gh_repo: Repository, sha: str, commit_obj: GitCommit) -> CommitRecord:
    """Build a CommitRecord from a PyGithub Commit object.

    Fetches the full commit to retrieve ``files_touched``.  This is one extra
    API call per commit; for a typical daily range of 10-50 commits the
    overhead is acceptable.

    Args:
        gh_repo: Authenticated PyGithub Repository object.
        sha: Full commit SHA.
        commit_obj: PyGithub ``GitCommit`` object (the ``.commit`` sub-object).

    Returns:
        Populated CommitRecord.
    """
    message: str = commit_obj.message or ""
    lines = message.splitlines()
    subject = lines[0] if lines else ""
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    author = commit_obj.author
    author_name = (author.name or "") if author else ""
    author_email = (author.email or "") if author else ""
    author_str = f"{author_name} <{author_email}>"

    committer = commit_obj.committer
    if committer and committer.date:
        date_str = committer.date.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif author and author.date:
        date_str = author.date.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        date_str = ""

    # Fetch per-commit file list for files_touched attribution.
    try:
        full_commit = gh_repo.get_commit(sha)
        files_touched: list[str] = sorted(f.filename for f in full_commit.files)
    except GithubException:
        files_touched = []

    return CommitRecord(
        sha=sha, subject=subject, body=body, author=author_str, date=date_str, files_touched=files_touched
    )


def collect_commit_records(gh_repo: Repository, base_ref: str, head_ref: str) -> list[CommitRecord]:
    """Collect commit metadata for the range base_ref..head_ref via GitHub API.

    For the empty-tree base (first day), fetches all commits reachable from
    ``head_ref`` via ``get_commits()``. For all other ranges, uses the GitHub
    compare REST API (up to 250 commits per comparison).

    Each commit requires one additional API call to retrieve ``files_touched``.

    Args:
        gh_repo: Authenticated PyGithub Repository object.
        base_ref: Git commit SHA before the range (exclusive), or EMPTY_TREE_SHA.
        head_ref: Git commit SHA at the end of the range (inclusive).

    Returns:
        List of CommitRecord instances ordered oldest-first.
    """
    err_console.print(f"[dim]Collecting commits {base_ref[:8]}..{head_ref[:8]} via GitHub API[/dim]")

    if base_ref == EMPTY_TREE_SHA:
        # First day: get all commits reachable from head_ref (newest-first from API)
        raw_commits = list(gh_repo.get_commits(sha=head_ref))
        raw_commits.reverse()  # oldest-first
    else:
        # compare() returns commits oldest-first
        comparison = gh_repo.compare(base_ref, head_ref)
        raw_commits = list(comparison.commits)

    records: list[CommitRecord] = [
        _commit_record_from_gh(gh_repo, gh_commit.sha, gh_commit.commit) for gh_commit in raw_commits
    ]

    err_console.print(f"[dim]  {len(records)} commits collected[/dim]")
    return records


# ---------------------------------------------------------------------------
# GitHub issue helpers
# ---------------------------------------------------------------------------


def _extract_issue_numbers(commit_records: list[CommitRecord]) -> list[int]:
    """Extract unique GitHub issue numbers referenced in commit messages.

    Scans subject and body of each commit for patterns matching
    ``closes/fixes/resolves #N`` (case-insensitive) and returns a deduplicated
    sorted list of issue numbers.

    Args:
        commit_records: List of CommitRecord instances to scan.

    Returns:
        Sorted list of unique referenced issue numbers.
    """
    seen: set[int] = set()
    for record in commit_records:
        text = f"{record.subject}\n{record.body}"
        seen.update(int(match.group(1)) for match in _ISSUE_REF_RE.finditer(text))
    return sorted(seen)


def collect_issue_records(commit_records: list[CommitRecord], gh_repo: Repository) -> list[IssueRecord]:
    """Fetch GitHub issues/PRs referenced in commit messages.

    Args:
        commit_records: Commits to scan for issue references.
        gh_repo: Authenticated PyGithub Repository object.

    Returns:
        List of IssueRecord instances for each referenced issue number.
    """
    issue_numbers = _extract_issue_numbers(commit_records)
    if not issue_numbers:
        err_console.print("[dim]No issue references found in commits[/dim]")
        return []

    err_console.print(f"[dim]Fetching {len(issue_numbers)} referenced GitHub issues[/dim]")

    records: list[IssueRecord] = []
    for number in issue_numbers:
        try:
            issue = gh_repo.get_issue(number)
            records.append(IssueRecord(number=issue.number, title=issue.title, state=issue.state, url=issue.html_url))
        except GithubException as exc:
            err_console.print(f"[yellow]Warning: could not fetch issue #{number}: {exc}[/yellow]")

    err_console.print(f"[dim]  {len(records)} issues fetched[/dim]")
    return records


# ---------------------------------------------------------------------------
# Dataset writer
# ---------------------------------------------------------------------------


def write_dataset(
    output_dir: Path,
    file_records: list[FileRecord],
    commit_records: list[CommitRecord],
    issue_records: list[IssueRecord],
) -> None:
    """Write the dataset JSON files to ``<output_dir>/dataset/``.

    Creates the directory if it does not exist, then writes:
    - ``files.json``
    - ``commits.json``
    - ``issues.json``

    The ``diffs/`` subdirectory is created earlier by ``collect_file_records``.

    Args:
        output_dir: Root output directory (e.g. ``./daily-releases/2026-02-10/``).
        file_records: Per-file metadata records.
        commit_records: Commit metadata records.
        issue_records: GitHub issue records (may be empty).
    """
    dataset_dir = output_dir / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    files_payload = [
        {
            "path": r.path,
            "status": r.status,
            "lines_added": r.lines_added,
            "lines_deleted": r.lines_deleted,
            "is_source": r.is_source,
            "is_excluded": r.is_excluded,
            "diff_file": r.diff_file,
        }
        for r in file_records
    ]

    commits_payload = [
        {
            "sha": r.sha,
            "subject": r.subject,
            "body": r.body,
            "author": r.author,
            "date": r.date,
            "files_touched": r.files_touched,
        }
        for r in commit_records
    ]

    issues_payload = [{"number": r.number, "title": r.title, "state": r.state, "url": r.url} for r in issue_records]

    (dataset_dir / "files.json").write_text(json.dumps(files_payload, indent=2), encoding="utf-8")
    (dataset_dir / "commits.json").write_text(json.dumps(commits_payload, indent=2), encoding="utf-8")
    (dataset_dir / "issues.json").write_text(json.dumps(issues_payload, indent=2), encoding="utf-8")

    err_console.print(
        f"[dim]Dataset written to {dataset_dir}: "
        f"{len(file_records)} files, {len(commit_records)} commits, "
        f"{len(issue_records)} issues[/dim]"
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.command()
def main(
    base_ref: Annotated[str, typer.Argument(help="Git commit SHA before the day's first commit")],
    head_ref: Annotated[str, typer.Argument(help="Git commit SHA of the day's last commit")],
    output_dir: Annotated[
        Path, typer.Argument(help="Directory under which dataset/ subdirectory will be created", writable=True)
    ],
    repo_slug: Annotated[
        str, typer.Option("--repo", "-R", help="GitHub OWNER/REPO slug (default from DEFAULT_REPO env var)")
    ] = DEFAULT_REPO,
) -> None:
    """Collect per-file diffs, commit metadata, and GitHub issues into dataset/.

    Writes three JSON files and per-file diffs under ``<output_dir>/dataset/``:

    - ``files.json``: changed source files with diff stats and diff_file path
    - ``commits.json``: commit metadata for the base_ref..head_ref range
    - ``issues.json``: GitHub issues referenced via closes/fixes/resolves #N

    Progress summaries are printed to stderr; no output is written to stdout.

    Uses the GitHub REST API — no local git repository is required.
    GITHUB_TOKEN must be set in the environment.
    """
    err_console.print(f"[bold]collect_day_dataset[/bold] {base_ref[:8]}..{head_ref[:8]} -> {output_dir}")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise AppExit(code=1, message="GITHUB_TOKEN environment variable not set")

    gh = make_github_client(token)
    gh_repo = get_github_repo(gh, repo_slug)

    diffs_dir = output_dir / "dataset" / "diffs"

    err_console.print("[dim]Step 1/3: file diffs[/dim]")
    file_records = collect_file_records(gh_repo, base_ref, head_ref, diffs_dir)

    err_console.print("[dim]Step 2/3: commit metadata[/dim]")
    commit_records = collect_commit_records(gh_repo, base_ref, head_ref)

    err_console.print("[dim]Step 3/3: GitHub issues[/dim]")
    issue_records = collect_issue_records(commit_records, gh_repo)

    write_dataset(output_dir, file_records, commit_records, issue_records)

    err_console.print(":white_check_mark: [green]Dataset collection complete[/green]")


if __name__ == "__main__":
    try:
        app()
    except AppExit as exc:
        sys.exit(exc.exit_code)
