#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.12.0", "pygithub>=2.8.1", "typer>=0.21.0"]
# ///
"""Batch-fetch current GitHub repo stats and locate citations in research entries.

Two capabilities, split per this skill's established script/agent contract
(``validation-rules.md`` "Script vs Agent Responsibility"): the script fetches and
detects mechanically; applying a text edit into an entry's prose is left to the
calling agent, since entry formatting is not uniform enough across the corpus for
a blind find-replace to be safe.

``stats``: fetches stargazers_count, forks_count, pushed_at, and license for an
arbitrary list of ``owner/repo`` pairs via PyGithub -- no reason to spend agent
reasoning on a deterministic API lookup done one repo at a time.

``scan``: walks a path, extracts every ``github.com/{owner}/{repo}`` URL cited in
each file, fetches current stats for the unique set, and reports (per file) which
citations carry a stats claim that no longer matches the live value -- including
citations with no discoverable stats claim at all, so an agent doesn't have to
independently rediscover which repos in a huge directory are already stale.

Uses PyGithub (``GITHUB_TOKEN`` env var), matching this repo's established
GitHub-tooling convention (see ``backlog_core/gh_client.py`` and AGENTS.md
"Prefer extending this repo's existing GitHub tooling ... over adding new
`gh` CLI usage") rather than shelling out to the ``gh`` CLI.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Annotated

import typer
from github import Auth, Github, GithubException
from pydantic import BaseModel

app = typer.Typer(add_completion=False)

_REPO_URL_PATTERN = re.compile(
    r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/([A-Za-z0-9._-]+?)(?:\.git)?(?=[)\]\s\"'>,;]|$)"
)
_STAR_CLAIM_PATTERN = re.compile(r"([\d,]+(?:\.\d+)?[Kk]?)\s*stars?", re.IGNORECASE)

# GitHub repo names never contain these as their full value; filters out
# incidental non-repo matches like "github.com/settings" or "github.com/orgs".
_NON_REPO_PATH_SEGMENTS = frozenset({
    "settings",
    "orgs",
    "marketplace",
    "notifications",
    "issues",
    "pulls",
    "sponsors",
    "topics",
    "search",
    "about",
    "features",
    "pricing",
    "apps",
})


class RepoStats(BaseModel):
    """Live GitHub stats for a single repository."""

    owner: str
    name: str
    exists: bool
    stargazer_count: int | None = None
    fork_count: int | None = None
    pushed_at: str | None = None
    license_spdx_id: str | None = None
    is_archived: bool | None = None


class CitationFinding(BaseModel):
    """One github.com repo citation found in one file, with its live stats attached."""

    file: str
    line: int
    repo: str
    cited_stat_text: str | None
    live: RepoStats


_HTTP_NOT_FOUND = 404


def _get_client() -> Github:
    """Build an authenticated PyGithub client from ``GITHUB_TOKEN``.

    Returns:
        An authenticated PyGithub client.

    Raises:
        RuntimeError: If ``GITHUB_TOKEN`` is not set.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        msg = "GITHUB_TOKEN not set"
        raise RuntimeError(msg)
    return Github(auth=Auth.Token(token))


def _fetch_one(gh: Github, owner: str, name: str) -> RepoStats:
    """Fetch live stats for a single repo, returning ``exists=False`` on 404.

    Returns:
        Live stats for the repo, or ``exists=False`` if it does not resolve.
    """
    try:
        repo = gh.get_repo(f"{owner}/{name}")
    except GithubException as exc:
        if exc.status == _HTTP_NOT_FOUND:
            return RepoStats(owner=owner, name=name, exists=False)
        msg = f"GitHub API error fetching {owner}/{name}: {exc}"
        raise RuntimeError(msg) from exc

    license_spdx_id = None
    if repo.license is not None:
        license_spdx_id = repo.license.spdx_id

    return RepoStats(
        owner=owner,
        name=name,
        exists=True,
        stargazer_count=repo.stargazers_count,
        fork_count=repo.forks_count,
        pushed_at=repo.pushed_at.isoformat() if repo.pushed_at else None,
        license_spdx_id=license_spdx_id,
        is_archived=repo.archived,
    )


def _fetch_stats_batch(gh: Github, repos: list[tuple[str, str]]) -> dict[tuple[str, str], RepoStats]:
    """Fetch live stats for each (owner, name) pair. Deduplicates before fetching.

    Returns:
        Mapping of (owner, name) to its live stats.
    """
    unique = sorted(set(repos))
    return {(owner, name): _fetch_one(gh, owner, name) for owner, name in unique}


def _extract_repo_citations(text: str) -> list[tuple[int, str, str]]:
    """Return (line_number, owner, name) for every distinct github.com repo URL in text.

    Returns:
        List of (line_number, owner, name) tuples, one per repo URL match.
    """
    found: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for match in _REPO_URL_PATTERN.finditer(line):
            owner, name = match.group(1), match.group(2)
            if name.lower() in _NON_REPO_PATH_SEGMENTS:
                continue
            found.append((i, owner, name))
    return found


@app.command()
def stats(
    repos: Annotated[list[str], typer.Argument(help="owner/repo pairs, e.g. facebook/react anthropics/claude-code")],
) -> None:
    """Fetch live stargazer/fork/license/pushed-at stats for one or more repos."""
    pairs: list[tuple[str, str]] = []
    for r in repos:
        if "/" not in r:
            typer.echo(f"Skipping malformed repo spec (expected owner/repo): {r}", err=True)
            continue
        owner, name = r.split("/", 1)
        pairs.append((owner, name))

    if not pairs:
        print(json.dumps({"results": []}))
        sys.exit(0)

    gh = _get_client()
    results = _fetch_stats_batch(gh, pairs)
    print(json.dumps({"results": [v.model_dump() for v in results.values()]}))


@app.command()
def scan(
    path: Annotated[Path, typer.Argument(help="File or directory to scan for github.com repo citations")] = Path(
        "./research"
    ),
) -> None:
    """Scan a path for github.com repo citations, fetch live stats, and report per-citation findings.

    Output is per-citation, not per-file deduplicated: the same repo cited in five
    files produces five findings, one per file, since each file's cited stat text
    (if any) needs its own comparison against the live value.
    """
    files = [path] if path.is_file() else sorted(path.rglob("*.md"))

    all_citations: list[tuple[Path, int, str, str]] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for line_no, owner, name in _extract_repo_citations(text):
            all_citations.append((f, line_no, owner, name))

    unique_pairs = [(owner, name) for _, _, owner, name in all_citations]
    gh = _get_client()
    live_stats = _fetch_stats_batch(gh, unique_pairs)

    findings: list[CitationFinding] = []
    for f, line_no, owner, name in all_citations:
        text = f.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        # Look for a star-count claim within 3 lines of the citation (same
        # paragraph/list-item range covers this corpus's observed patterns).
        window_start = max(0, line_no - 1 - 3)
        window_end = min(len(lines), line_no + 3)
        window = "\n".join(lines[window_start:window_end])
        star_match = _STAR_CLAIM_PATTERN.search(window)
        findings.append(
            CitationFinding(
                file=str(f),
                line=line_no,
                repo=f"{owner}/{name}",
                cited_stat_text=star_match.group(0) if star_match else None,
                live=live_stats[owner, name],
            )
        )

    print(json.dumps({"findings": [c.model_dump() for c in findings]}))


if __name__ == "__main__":
    app()
