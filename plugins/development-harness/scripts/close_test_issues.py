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
#
# [tool.ty.environment]
# extra-paths = ["..", "."]
# ///
"""Validate a designated sandbox or close only the current run's test issues.

Requires DH_E2E_REPOSITORY, DH_E2E_RUN_ID, DH_ALLOW_TEST_NETWORK=1 and the
sandbox GITHUB_TOKEN. The target must contain the .dh-e2e-sandbox marker.
Use --check-only for a read-only preflight. A legacy --repo argument must
agree with DH_E2E_REPOSITORY; there is no production or broad-sweep fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backlog_core.gh_client import GitHubUnavailableError, get_github
from github import GithubException

from live_test_scope import SANDBOX_MARKER, SANDBOX_MARKER_PATH, LiveTestScope, cleanup_run

if TYPE_CHECKING:
    from github.Repository import Repository


def open_sandbox(scope: LiveTestScope) -> Repository:
    """Read and validate sandbox identity before any resource mutation.

    Returns:
        A repository whose canonical identity and explicit marker were checked.
    """
    scope.check_repository(scope.repository)
    repository = get_github(scope.repository)
    scope.check_repository(repository.full_name)
    marker = repository.get_contents(SANDBOX_MARKER_PATH, ref=repository.default_branch)
    if isinstance(marker, list) or marker.decoded_content != SANDBOX_MARKER:
        raise ValueError(f"Sandbox must contain {SANDBOX_MARKER_PATH} with the documented exact contents")
    return repository


def main() -> int:
    """Run read-only preflight or ownership-checked cleanup with a truthful exit code.

    Returns:
        Zero after successful validation/cleanup, one on any failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Optional legacy target; must match DH_E2E_REPOSITORY")
    parser.add_argument("--check-only", action="store_true", help="Validate the sandbox without modifying it")
    args = parser.parse_args()
    environment = dict(os.environ)
    if args.repo:
        environment["REPO"] = args.repo
    try:
        scope = LiveTestScope.from_environment(environment)
        repository = open_sandbox(scope)
        closed = [] if args.check_only else cleanup_run(scope, repository)
    except (GithubException, GitHubUnavailableError, OSError, RuntimeError, ValueError) as exc:
        print(f"Live-test preflight/cleanup failed: {exc}", file=sys.stderr, flush=True)
        return 1
    print(
        json.dumps({
            "repository": scope.repository,
            "run_id": scope.run_id,
            "check_only": args.check_only,
            "closed": closed,
        })
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
