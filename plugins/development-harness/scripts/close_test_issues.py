#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "gitpython>=3.1.0",
#   "pygithub>=2.8.1",
#   "pydantic>=2.12.3",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "marko>=2.0.0",
#   "typer>=0.21.2",
#   "python-dotenv>=1.0.0",
#   "httpx>=0.28.1",
# ]
# ///
"""Close orphaned [MCP-TEST-*] GitHub issues left by failed e2e test teardown.

Fetches all open issues via backlog_core shared GraphQL client, filters for titles
containing '[MCP-TEST-', and closes each one with an explanatory comment.

Usage:
    uv run plugins/development-harness/scripts/close_test_issues.py --repo <owner/repo>
    uv run plugins/development-harness/scripts/close_test_issues.py  # uses REPO env var

Environment:
    REPO          owner/repo string (required if --repo not supplied)
    GITHUB_TOKEN  GitHub token for authentication (required)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make backlog_core importable when run via `uv run` against the project workspace
# (which does not install development-harness as an editable package).
# Pattern mirrors run_backlog_server.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backlog_core.gh_client import GitHubUnavailableError, close_github_issue, get_github, sync_issues_graphql
from backlog_core.models import Output


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

    try:
        repository = get_github(repo)
    except GitHubUnavailableError as exc:
        print(f"Emergency cleanup: GitHub unavailable — {exc}", file=sys.stderr)
        sys.exit(1)

    owner, repo_name = repository.full_name.split("/", 1)
    issues = sync_issues_graphql(repository, owner, repo_name, state="OPEN")

    orphans = [i for i in issues if "[MCP-TEST-" in i.get("title", "") and "pull_request" not in i]

    swept = 0
    failed = 0
    for issue in orphans:
        number = issue["number"]
        out = Output()
        close_github_issue(
            str(number),
            reason="emergency-sweep",
            comment="Closed by CI emergency sweep: orphaned e2e test issue",
            repo=repo,
            output=out,
        )
        if out.warnings:
            for msg in out.warnings:
                print(f"Emergency cleanup: issue #{number}: {msg}", file=sys.stderr)
            failed += 1
        else:
            swept += 1

    print(f"Swept {swept} orphaned test issues" + (f", failed {failed}" if failed else ""))


if __name__ == "__main__":
    main()
