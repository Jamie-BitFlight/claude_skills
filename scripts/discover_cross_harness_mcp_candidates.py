#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Collect and rank GitHub candidates before any plugin-source inspection.

The script intentionally separates cheap discovery from expensive analysis:

1. GitHub Code Search finds repositories whose Codex plugin manifests declare
   an MCP surface.
2. GitHub GraphQL enriches those repository names in batches with public
   uptake metadata.
3. The emitted JSON is sorted by stars, then forks. A later stage may inspect
   only the highest-ranked candidates for Claude packaging and MCP semantics.

No repository tree or source file is fetched by this script.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_utils import run_gh_json

if TYPE_CHECKING:
    from collections.abc import Callable

DISCOVERY_QUERIES = (
    "mcpServers path:.codex-plugin filename:plugin.json",
    "mcp_servers path:.codex-plugin filename:plugin.json",
)
METADATA_BATCH_SIZE = 50
GITHUB_CODE_SEARCH_RESULT_LIMIT = 1000
CHECKPOINT_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class QueryGaps:
    """Collection-completeness signals extracted from a run's query summaries."""

    incomplete_queries: list[str]
    mismatched_queries: list[str]
    github_incomplete_queries: list[str]
    truncated_queries: list[str]


@dataclass(frozen=True)
class Candidate:
    """A code-search candidate enriched only with repository metadata."""

    repository: str
    stars: int
    forks: int
    archived: bool
    default_branch: str | None
    url: str
    discovery_hits: tuple[dict[str, str], ...]


def default_query_summary(query: str) -> dict[str, Any]:
    """Create the persisted state for one GitHub Code Search query.

    Returns:
        A query summary updated after each completed page.
    """
    return {
        "query": query,
        "pages_fetched": 0,
        "total_count": 0,
        "result_count": 0,
        "incomplete_results": False,
        "truncated_by_max_pages": False,
        "truncated_by_github_limit": False,
        "result_count_mismatch": False,
        "complete": False,
    }


def write_checkpoint(
    checkpoint_path: Path,
    hits: list[dict[str, str]],
    summaries: dict[str, dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    page_size: int,
) -> None:
    """Atomically write partial collection data after every remote request."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "page_size": page_size,
        "updated_at": datetime.now(UTC).isoformat(),
        "hits": hits,
        "query_summaries": summaries,
        "metadata": metadata,
    }
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(checkpoint_path)


def load_checkpoint(
    checkpoint_path: Path, page_size: int
) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load a compatible checkpoint, or return an empty collection state.

    Returns:
        Prior code-search hits, query summaries, and GraphQL metadata.
    """
    if not checkpoint_path.exists():
        return [], {}, {}
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported checkpoint schema: {checkpoint_path}")
    if payload.get("page_size") != page_size:
        raise RuntimeError(f"Checkpoint page size does not match requested page size: {checkpoint_path}")
    hits = payload.get("hits")
    summaries = payload.get("query_summaries")
    metadata = payload.get("metadata")
    if not isinstance(hits, list) or not isinstance(summaries, dict) or not isinstance(metadata, dict):
        raise TypeError(f"Malformed checkpoint: {checkpoint_path}")
    return hits, summaries, metadata


def search_code(
    query: str,
    page_size: int,
    max_pages: int,
    delay_seconds: float,
    hits: list[dict[str, str]],
    summary: dict[str, Any],
    persist: Callable[[], None],
) -> None:
    """Extend saved hits for one Code Search query, page by page.

    GitHub Code Search exposes at most 1,000 results per query. The summary
    records whether that boundary was reached so downstream research knows
    when the candidate corpus may be incomplete.
    """
    if summary["complete"]:
        return
    summary["truncated_by_max_pages"] = False
    for page in range(summary["pages_fetched"] + 1, max_pages + 1):
        endpoint = f"search/code?q={quote(query, safe='')}&per_page={page_size}&page={page}"
        response = run_gh_json(["api", "-H", "Accept: application/vnd.github+json", endpoint])
        items = response.get("items", [])
        if page == 1:
            summary["total_count"] = response.get("total_count", 0)
            summary["incomplete_results"] = response.get("incomplete_results", False)
            summary["truncated_by_github_limit"] = summary["total_count"] > GITHUB_CODE_SEARCH_RESULT_LIMIT

        summary["pages_fetched"] = page
        summary["result_count"] += len(items)
        for item in items:
            repository = item.get("repository", {}).get("full_name")
            path = item.get("path")
            if repository and path:
                hits.append({"repository": repository, "path": path, "query": query})

        expected_result_count = min(summary["total_count"], GITHUB_CODE_SEARCH_RESULT_LIMIT)
        if not items:
            summary["complete"] = True
            summary["result_count_mismatch"] = summary["result_count"] != expected_result_count
        elif summary["result_count"] >= expected_result_count:
            summary["complete"] = True
        elif page == max_pages:
            summary["truncated_by_max_pages"] = True
        persist()
        if summary["complete"]:
            break
        if page != max_pages:
            time.sleep(delay_seconds)


def build_metadata_query(repositories: list[str]) -> str:
    """Build a bounded GraphQL query for GitHub repository uptake metadata.

    Returns:
        A GraphQL query containing one aliased repository lookup per candidate.
    """
    fields: list[str] = []
    for index, repository in enumerate(repositories):
        owner, name = repository.split("/", maxsplit=1)
        fields.append(
            f"""r{index}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{
                nameWithOwner
                stargazerCount
                forkCount
                isArchived
                url
                defaultBranchRef {{ name }}
            }}"""
        )
    return "query CandidateMetadata {\n" + "\n".join(fields) + "\n}"


def _metadata_by_casefold(metadata: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index metadata by casefolded repository name for case-insensitive lookup.

    An explicit --seed-repository value's casing (whatever the caller typed) can
    differ from GitHub's canonical nameWithOwner casing that fetch_metadata()
    stores results under; an exact-key lookup would then silently miss a real
    match. Repository identifiers are already compared with casefold() elsewhere
    in this script (deduplicating seeds); this brings metadata lookups in line.

    Returns:
        The same values, keyed by ``repository.casefold()`` instead of ``repository``.
    """
    return {repository.casefold(): value for repository, value in metadata.items()}


def fetch_metadata(
    repositories: list[str], metadata: dict[str, dict[str, Any]], delay_seconds: float, persist: Callable[[], None]
) -> None:
    """Fetch candidate metadata in GraphQL batches instead of one REST call per repo.

    The existing mapping is updated in place after each completed batch, so a
    rate-limit interruption can continue without repeating completed requests.
    """
    known_casefold = _metadata_by_casefold(metadata)
    pending = [repository for repository in repositories if repository.casefold() not in known_casefold]
    for offset in range(0, len(pending), METADATA_BATCH_SIZE):
        batch = pending[offset : offset + METADATA_BATCH_SIZE]
        response = run_gh_json(["api", "graphql", "-f", f"query={build_metadata_query(batch)}"])
        for value in response.get("data", {}).values():
            if value and value.get("nameWithOwner"):
                metadata[value["nameWithOwner"]] = value
        persist()
        if offset + METADATA_BATCH_SIZE < len(pending):
            time.sleep(delay_seconds)


def rank_candidates(
    hits: list[dict[str, str]], metadata: dict[str, dict[str, Any]], minimum_stars: int
) -> list[Candidate]:
    """Join candidate hits with metadata and rank eligible repositories by uptake.

    Returns:
        Candidates at or above the star threshold, sorted by stars then forks.
    """
    hits_by_repository: dict[str, list[dict[str, str]]] = defaultdict(list)
    for hit in hits:
        hits_by_repository[hit["repository"]].append({"path": hit["path"], "query": hit["query"]})

    metadata_by_casefold = _metadata_by_casefold(metadata)
    candidates: list[Candidate] = []
    for repository, repository_hits in hits_by_repository.items():
        value = metadata_by_casefold.get(repository.casefold())
        if value is None or value["stargazerCount"] < minimum_stars:
            continue
        branch = value.get("defaultBranchRef")
        candidates.append(
            Candidate(
                repository=repository,
                stars=value["stargazerCount"],
                forks=value["forkCount"],
                archived=value["isArchived"],
                default_branch=branch["name"] if branch else None,
                url=value["url"],
                discovery_hits=tuple(sorted(repository_hits, key=itemgetter("query", "path"))),
            )
        )
    return sorted(
        candidates, key=lambda candidate: (-candidate.stars, -candidate.forks, candidate.repository.casefold())
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Validated command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="Destination JSON file for the ranked metadata-only candidate set."
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Resumable raw collection state (default: output path with .checkpoint.json suffix).",
    )
    parser.add_argument(
        "--minimum-stars",
        type=int,
        default=4000,
        help="Exclude candidates below this public-uptake threshold (default: 4000).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        choices=range(1, 101),
        metavar="1..100",
        help="GitHub Code Search results per page (default: 100).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        choices=range(1, 11),
        metavar="1..10",
        help="Pages to fetch for each query, capped by GitHub's 1,000-result limit (default: 10).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=2.1,
        help="Delay between Code Search pages to respect its rate limit (default: 2.1).",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write a partial ranked dataset when a query has more pages to collect.",
    )
    parser.add_argument(
        "--allow-inconsistent",
        action="store_true",
        help="Write a potentially incomplete dataset when GitHub's count exceeds its returned pages.",
    )
    parser.add_argument(
        "--metadata-delay-seconds",
        type=float,
        default=0.5,
        help="Delay between GraphQL metadata batches to avoid request bursts (default: 0.5).",
    )
    parser.add_argument(
        "--seed-repository",
        action="append",
        default=[],
        metavar="OWNER/REPOSITORY",
        help="Add a direct repository reference to the ranked candidate corpus; repeat as needed.",
    )
    args = parser.parse_args()
    if args.checkpoint is None:
        args.checkpoint = args.output.with_suffix(".checkpoint.json")
    return args


def compute_query_gaps(summaries_by_query: dict[str, dict[str, Any]]) -> QueryGaps:
    """Extract the four independent collection-completeness signals from query summaries.

    incomplete/mismatched reflect our own pagination bookkeeping; github_incomplete and
    truncated reflect GitHub's own per-page completeness flag and its hard 1,000-result
    cap, which are independent of pagination completing cleanly on our side.

    Returns:
        The four gap categories, each as a list of affected query strings.
    """
    return QueryGaps(
        incomplete_queries=[q for q, summary in summaries_by_query.items() if not summary["complete"]],
        mismatched_queries=[q for q, summary in summaries_by_query.items() if summary["result_count_mismatch"]],
        github_incomplete_queries=[q for q, summary in summaries_by_query.items() if summary["incomplete_results"]],
        truncated_queries=[q for q, summary in summaries_by_query.items() if summary["truncated_by_github_limit"]],
    )


def build_collection_warnings(gaps: QueryGaps, missing_metadata_repositories: list[str]) -> list[str]:
    """Translate collection-completeness gaps into human-readable warnings.

    Returns:
        One warning string per gap category that actually occurred.
    """
    warnings: list[str] = []
    if gaps.incomplete_queries:
        warnings.append("one or more Code Search queries have uncollected pages")
    if gaps.mismatched_queries:
        warnings.append("GitHub advertised more Code Search results than its pages returned")
    if missing_metadata_repositories:
        warnings.append(
            f"{len(missing_metadata_repositories)} candidate repositories returned no GraphQL metadata "
            "(renamed, made private, or deleted) and were dropped -- see missing_metadata_repositories"
        )
    if gaps.github_incomplete_queries:
        warnings.append(
            "GitHub reported its own Code Search index as incomplete for one or more queries "
            "(independent of our pagination completing) -- see queries[].incomplete_results"
        )
    if gaps.truncated_queries:
        warnings.append(
            "one or more queries exceeded GitHub's 1,000-result Code Search cap -- more candidates "
            "exist than this API can ever return for that query -- see queries[].truncated_by_github_limit"
        )
    return warnings


def reconcile_seed_hits(hits: list[dict[str, str]], explicit_seed_repositories: list[str]) -> list[dict[str, str]]:
    """Drop stale checkpointed seed hits and add any not yet present.

    A checkpoint can carry explicit_seed hits from a prior invocation whose
    --seed-repository has since been removed or changed; without reconciling
    against the current set, a stale repository stays ranked forever while the
    payload claims to reflect the current, potentially narrower seed list.

    Returns:
        ``hits`` with stale explicit_seed entries removed and current seeds present.
    """
    current_casefold = {repository.casefold() for repository in explicit_seed_repositories}
    reconciled = [
        hit for hit in hits if hit["query"] != "explicit_seed" or hit["repository"].casefold() in current_casefold
    ]
    for repository in explicit_seed_repositories:
        if not any(hit["repository"].casefold() == repository.casefold() for hit in reconciled):
            reconciled.append({"repository": repository, "path": "", "query": "explicit_seed"})
    return reconciled


def main() -> int:
    """Collect and write the ranked candidate dataset.

    Returns:
        Process exit status.
    """
    args = parse_args()
    all_hits, summaries_by_query, metadata = load_checkpoint(args.checkpoint, args.page_size)
    explicit_seed_repositories = sorted(set(args.seed_repository), key=str.casefold)
    for repository in explicit_seed_repositories:
        if repository.count("/") != 1 or any(not segment for segment in repository.split("/")):
            raise ValueError(f"Invalid --seed-repository value: {repository}")
    all_hits = reconcile_seed_hits(all_hits, explicit_seed_repositories)
    for query in DISCOVERY_QUERIES:
        summary = summaries_by_query.setdefault(query, default_query_summary(query))
        summary.setdefault("result_count", sum(hit["query"] == query for hit in all_hits))
        summary.setdefault("result_count_mismatch", False)
        expected_result_count = min(summary["total_count"], GITHUB_CODE_SEARCH_RESULT_LIMIT)
        if (
            summary["complete"]
            and not summary["result_count_mismatch"]
            and summary["result_count"] < expected_result_count
        ):
            summary["complete"] = False

    def persist() -> None:
        write_checkpoint(args.checkpoint, all_hits, summaries_by_query, metadata, args.page_size)

    for query in DISCOVERY_QUERIES:
        search_code(
            query, args.page_size, args.max_pages, args.delay_seconds, all_hits, summaries_by_query[query], persist
        )

    gaps = compute_query_gaps(summaries_by_query)
    if gaps.mismatched_queries and not args.allow_inconsistent:
        raise RuntimeError(
            "Code Search result count disagrees with GitHub pagination; refusing to rank an inconsistent corpus"
        )
    if gaps.incomplete_queries and not args.allow_partial:
        raise RuntimeError(
            "Code Search collection is incomplete; rerun with a higher --max-pages or pass --allow-partial explicitly"
        )

    repositories = sorted({hit["repository"] for hit in all_hits}, key=str.casefold)
    fetch_metadata(repositories, metadata, args.metadata_delay_seconds, persist)
    known_metadata_casefold = _metadata_by_casefold(metadata)
    missing_metadata_repositories = [
        repository for repository in repositories if repository.casefold() not in known_metadata_casefold
    ]
    candidates = rank_candidates(all_hits, metadata, args.minimum_stars)
    collection_warnings = build_collection_warnings(gaps, missing_metadata_repositories)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "metadata-only candidate discovery; no repository trees or source files were inspected",
        "partial": bool(
            gaps.incomplete_queries
            or gaps.mismatched_queries
            or missing_metadata_repositories
            or gaps.github_incomplete_queries
            or gaps.truncated_queries
        ),
        "collection_warnings": collection_warnings,
        "missing_metadata_repositories": missing_metadata_repositories,
        "ranking": "stars descending, then forks descending, then repository name",
        "minimum_stars": args.minimum_stars,
        "explicit_seed_repositories": explicit_seed_repositories,
        "queries": [summaries_by_query[query] for query in DISCOVERY_QUERIES],
        "candidate_repositories_before_uptake_filter": len(repositories),
        "eligible_candidates": [asdict(candidate) for candidate in candidates],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(candidates)} ranked candidates to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
