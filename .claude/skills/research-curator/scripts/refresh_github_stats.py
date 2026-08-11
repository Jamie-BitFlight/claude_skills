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
arbitrary list of ``owner/repo`` pairs in a single aliased GraphQL query (chunked
at 50 repos per request) -- no reason to spend agent reasoning, or a REST call per
repo, on a deterministic lookup that GitHub's API already supports batching.

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
    r"https?://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/([A-Za-z0-9._-]+?)(?:\.git)?(?=[/#?)\]\s\"'>,;]|$)"
)
_STAR_CLAIM_PATTERN = re.compile(r"([\d,]+(?:\.\d+)?[Kk]?)\s*stars?", re.IGNORECASE)

# Same character classes as _REPO_URL_PATTERN's capture groups, anchored for
# whole-string validation of CLI-supplied owner/repo pairs (which, unlike
# scan()'s regex-extracted citations, are not pre-constrained to safe
# characters and could otherwise break the interpolated GraphQL query string).
_VALID_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")
_VALID_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

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
    """Live GitHub stats for a single repository.

    ``exists=False, error=None`` means GitHub confirmed the repo does not
    resolve (a real NOT_FOUND). ``exists=False, error=<reason>`` means the
    lookup itself could not be completed (malformed input, API failure) --
    a distinct case a caller should not treat as "confirmed nonexistent."
    """

    owner: str
    name: str
    exists: bool
    error: str | None = None
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


_GRAPHQL_CHUNK_SIZE = 50


def _run_graphql_batch(gh: Github, chunk: list[tuple[str, str]]) -> dict[str, object]:
    """Run one aliased GraphQL query covering every repo in ``chunk``.

    Mirrors ``backlog_core/gh_client.py``'s ``_graphql_request`` pattern: PyGithub's
    ``requester.graphql_query`` raises ``GithubException`` whenever the response
    carries a GraphQL ``errors`` array -- including the ordinary case where one
    alias in the batch resolves to a nonexistent repo while the others succeed.
    The exception's ``.data`` attribute still carries the full partial response,
    so a raise here is not a total failure; only a response with no ``data`` key
    at all (auth failure, malformed query) is fatal.

    Returns:
        The GraphQL response's ``data`` dict, keyed by alias (``r0``, ``r1``, ...).

    Raises:
        RuntimeError: If the response carries no usable ``data`` at all.
    """
    fields = "\n".join(
        f'r{i}: repository(owner: "{owner}", name: "{name}") {{'
        f" stargazerCount forkCount pushedAt isArchived licenseInfo {{ spdxId }} }}"
        for i, (owner, name) in enumerate(chunk)
    )
    query = f"query {{ {fields} }}"
    try:
        _headers, response = gh.requester.graphql_query(query, {})
    except GithubException as exc:
        data = exc.data.get("data") if isinstance(exc.data, dict) else None
        if not isinstance(data, dict):
            msg = f"GraphQL batch query failed with no usable data: {exc}"
            raise TypeError(msg) from exc
        return data
    return response.get("data", {})


def _parse_chunk_response(chunk: list[tuple[str, str]], data: dict[str, object]) -> dict[tuple[str, str], RepoStats]:
    """Turn one successful chunk response into per-repo results.

    Returns:
        Mapping of (owner, name) to its live stats for this chunk.
    """
    results: dict[tuple[str, str], RepoStats] = {}
    for i, (owner, name) in enumerate(chunk):
        node = data.get(f"r{i}")
        if not isinstance(node, dict):
            results[owner, name] = RepoStats(owner=owner, name=name, exists=False)
            continue
        license_info = node.get("licenseInfo")
        results[owner, name] = RepoStats(
            owner=owner,
            name=name,
            exists=True,
            stargazer_count=node.get("stargazerCount"),
            fork_count=node.get("forkCount"),
            pushed_at=node.get("pushedAt"),
            license_spdx_id=license_info.get("spdxId") if isinstance(license_info, dict) else None,
            is_archived=node.get("isArchived"),
        )
    return results


def _fetch_chunk_with_isolation(gh: Github, chunk: list[tuple[str, str]]) -> dict[tuple[str, str], RepoStats]:
    """Fetch one chunk; on total failure, bisect and retry each half to isolate the bad entry.

    A NOT_FOUND-type failure for one alias does not reach here -- it is already
    handled inside a successful multi-repo response by ``_parse_chunk_response``.
    This only triggers for failures that break the *whole* query (a malformed
    owner/name breaking GraphQL syntax, a transient API error, a rate limit) so
    that one bad or unlucky entry does not silently discard every other result
    in the same chunk. The isolated failure is reported to stderr and recorded
    with ``exists=False, error=<reason>`` rather than crashing the batch.

    Returns:
        Mapping of (owner, name) to its live stats for every repo in ``chunk``.
    """
    try:
        data = _run_graphql_batch(gh, chunk)
    except TypeError as exc:
        if len(chunk) == 1:
            owner, name = chunk[0]
            typer.echo(f"Could not resolve {owner}/{name}: {exc}", err=True)
            return {(owner, name): RepoStats(owner=owner, name=name, exists=False, error=str(exc))}
        mid = len(chunk) // 2
        left = _fetch_chunk_with_isolation(gh, chunk[:mid])
        right = _fetch_chunk_with_isolation(gh, chunk[mid:])
        return {**left, **right}
    return _parse_chunk_response(chunk, data)


def _fetch_stats_batch(gh: Github, repos: list[tuple[str, str]]) -> dict[tuple[str, str], RepoStats]:
    """Fetch live stats for each (owner, name) pair in chunks of 50 aliases per query.

    Deduplicates before fetching so a repo cited many times costs one lookup.
    A chunk-breaking failure isolates and reports the specific bad entry via
    bisection rather than discarding the whole chunk's results.

    Returns:
        Mapping of (owner, name) to its live stats.
    """
    unique = sorted(set(repos))
    results: dict[tuple[str, str], RepoStats] = {}
    for start in range(0, len(unique), _GRAPHQL_CHUNK_SIZE):
        chunk = unique[start : start + _GRAPHQL_CHUNK_SIZE]
        results.update(_fetch_chunk_with_isolation(gh, chunk))
    return results


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
        if not (_VALID_OWNER.match(owner) and _VALID_NAME.match(name)):
            typer.echo(f"Skipping invalid owner/repo (not a valid GitHub identifier): {r}", err=True)
            continue
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
