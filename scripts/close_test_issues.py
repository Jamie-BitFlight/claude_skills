#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Close orphaned [MCP-TEST-*] GitHub issues left by failed e2e test teardown.

Fetches all open issues via paginated gh API calls, filters for titles
containing '[MCP-TEST-', and closes each one with an explanatory comment.

Usage:
    uv run scripts/close_test_issues.py --repo <owner/repo>
    uv run scripts/close_test_issues.py  # uses REPO env var

Environment:
    REPO        owner/repo string (required if --repo not supplied)
    GH_TOKEN    GitHub token for gh CLI authentication (required)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any


def fetch_open_issues(repo: str) -> list[dict[str, Any]]:
    """Fetch all open issues via paginated gh API calls.

    Uses --paginate so gh handles traversal of all pages — no invented limit.
    Uses --slurp to collect pages into a JSON array of arrays.

    Returns:
        Flat list of issue dicts. Empty list on any error.
    """
    result = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/issues?state=open&per_page=100"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"Emergency cleanup: gh api call failed (exit {result.returncode}): {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []

    raw = result.stdout
    try:
        pages = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Emergency cleanup: could not parse gh output ({exc}), skipping", file=sys.stderr)
        return []

    if not isinstance(pages, list):
        print(f"Emergency cleanup: unexpected payload type {type(pages).__name__}, skipping", file=sys.stderr)
        return []

    if pages and not isinstance(pages[0], list):
        pages = [pages]

    return [issue for page in pages for issue in page]


def close_issue(repo: str, number: int) -> bool:
    """Close a single issue with an explanatory comment.

    Returns:
        True if the issue was closed successfully, False otherwise.
    """
    result = subprocess.run(
        [
            "gh",
            "issue",
            "close",
            str(number),
            "-R",
            repo,
            "--comment",
            "Closed by CI emergency sweep: orphaned e2e test issue",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"Emergency cleanup: failed to close issue #{number} (exit {result.returncode}): {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def main() -> None:
    """Entry point: resolve repo, fetch issues, close orphans."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", default=os.environ.get("REPO", ""), help="owner/repo string (defaults to REPO env var)"
    )
    args = parser.parse_args()

    repo = args.repo
    if not repo:
        print("Emergency cleanup: REPO not set and --repo not supplied, skipping", file=sys.stderr)
        sys.exit(1)

    issues = fetch_open_issues(repo)
    orphans = [i for i in issues if "[MCP-TEST-" in i.get("title", "") and "pull_request" not in i]

    swept = 0
    failed = 0
    for issue in orphans:
        if close_issue(repo, issue["number"]):
            swept += 1
        else:
            failed += 1

    print(f"Swept {swept} orphaned test issues" + (f", failed {failed}" if failed else ""))


if __name__ == "__main__":
    main()
