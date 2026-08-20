"""Workflow-level test proving the discover -> verify pipeline composes correctly.

Runs the real ``discover_cross_harness_mcp_candidates.py`` collection/ranking logic and feeds its
output directly into the real ``verify_cross_harness_mcp_structure.py`` classification logic,
against fixture repository trees built as real files under ``tmp_path``. Only the outbound
``gh`` calls (``run_gh_json`` in each module) are replaced — everything else is the production
code path both scripts actually run.
"""

from __future__ import annotations

import importlib.util
import operator
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"


def _load(module_name: str, file_name: str) -> Any:
    """Load one of the pipeline scripts as an isolated module object.

    Returns:
        The executed module, independent of any other test file's copy of the same script.
    """
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPTS_DIR / file_name)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


discovery = _load("discover_cross_harness_mcp_candidates_pipeline", "discover_cross_harness_mcp_candidates.py")
verify = _load("verify_cross_harness_mcp_structure_pipeline", "verify_cross_harness_mcp_structure.py")

_QUERY_WITH_HITS = discovery.DISCOVERY_QUERIES[0]
_QUERY_WITHOUT_HITS = discovery.DISCOVERY_QUERIES[1]


def _write(root: Path, *relative_paths: str) -> None:
    """Create empty files at each relative path under ``root``, creating parents as needed."""
    for relative_path in relative_paths:
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")


def _blob_paths(root: Path) -> list[dict[str, str]]:
    """Return GitHub-tree-shaped blob entries for every real file under ``root``.

    Returns:
        One ``{"path": ..., "type": "blob"}`` entry per file, sorted by path.
    """
    return sorted(
        (
            {"path": file_path.relative_to(root).as_posix(), "type": "blob"}
            for file_path in root.rglob("*")
            if file_path.is_file()
        ),
        key=operator.itemgetter("path"),
    )


def _code_search_page(items: list[tuple[str, str]]) -> dict[str, Any]:
    """Build a one-page GitHub Code Search response for the given (repository, path) hits."""
    return {
        "total_count": len(items),
        "incomplete_results": False,
        "items": [{"repository": {"full_name": repository}, "path": path} for repository, path in items],
    }


def _metadata_record(repository: str, *, stars: int, forks: int) -> dict[str, Any]:
    owner, name = repository.split("/", maxsplit=1)
    return {
        "nameWithOwner": repository,
        "stargazerCount": stars,
        "forkCount": forks,
        "isArchived": False,
        "url": f"https://github.com/{owner}/{name}",
        "defaultBranchRef": {"name": "main"},
    }


def test_discovery_and_verification_compose_correctly_end_to_end(tmp_path: Path, mocker: MockerFixture) -> None:
    """Discovery ranks three candidates; verification classifies each by real tree structure."""
    accepted_repo = "octo-org/accepted-plugin"
    rejected_repo = "octo-org/rejected-plugin"
    inconclusive_repo = "octo-org/inconclusive-plugin"

    # -- Stage 1: discovery (real search_code + fetch_metadata + rank_candidates) --------------
    code_search_page = _code_search_page([
        (accepted_repo, ".codex-plugin/plugin.json"),
        (rejected_repo, ".codex-plugin/plugin.json"),
        (inconclusive_repo, ".codex-plugin/plugin.json"),
    ])
    empty_page = _code_search_page([])
    metadata_batch = {
        "r0": _metadata_record(accepted_repo, stars=9000, forks=300),
        "r1": _metadata_record(rejected_repo, stars=7000, forks=100),
        "r2": _metadata_record(inconclusive_repo, stars=5000, forks=50),
    }

    def fake_run_gh_json(arguments: list[str]) -> dict[str, Any]:
        if "graphql" in arguments:
            return {"data": metadata_batch}
        endpoint = arguments[-1]
        if endpoint.startswith(f"search/code?q={quote(_QUERY_WITH_HITS, safe='')}"):
            return code_search_page
        if endpoint.startswith(f"search/code?q={quote(_QUERY_WITHOUT_HITS, safe='')}"):
            return empty_page
        raise AssertionError(f"Unexpected discovery gh invocation: {arguments}")

    mocker.patch.object(discovery, "run_gh_json", side_effect=fake_run_gh_json)

    all_hits: list[dict[str, str]] = []
    for query in discovery.DISCOVERY_QUERIES:
        summary = discovery.default_query_summary(query)
        discovery.search_code(
            query, page_size=100, max_pages=10, delay_seconds=0, hits=all_hits, summary=summary, persist=lambda: None
        )

    repositories = sorted({hit["repository"] for hit in all_hits})
    metadata: dict[str, dict[str, Any]] = {}
    discovery.fetch_metadata(repositories, metadata, delay_seconds=0, persist=lambda: None)
    ranked = discovery.rank_candidates(all_hits, metadata, minimum_stars=4000)

    assert [candidate.repository for candidate in ranked] == [accepted_repo, rejected_repo, inconclusive_repo]

    # -- Stage 2: verification (real inspect_tree against fixture trees) -----------------------
    accepted_root = tmp_path / "accepted"
    _write(
        accepted_root,
        "plugins/foo/.claude-plugin/plugin.json",
        "plugins/foo/.codex-plugin/plugin.json",
        "plugins/foo/.mcp.json",
    )
    rejected_root = tmp_path / "rejected"
    _write(
        rejected_root,
        "plugins/foo/.claude-plugin/plugin.json",
        "plugins/foo/.codex-plugin/plugin.json",
        "plugins/foo/README.md",
    )
    inconclusive_root = tmp_path / "inconclusive"
    _write(
        inconclusive_root,
        "plugins/foo/.claude-plugin/plugin.json",
        "plugins/foo/.codex-plugin/plugin.json",
        "plugins/foo/.mcp.json",
    )
    tree_by_repository = {
        accepted_repo: {"tree": _blob_paths(accepted_root), "truncated": False},
        rejected_repo: {"tree": _blob_paths(rejected_root), "truncated": False},
        inconclusive_repo: {"tree": _blob_paths(inconclusive_root), "truncated": True},
    }

    def fake_tree_run_gh_json(arguments: list[str]) -> dict[str, Any]:
        endpoint = arguments[-1]
        for repository, tree in tree_by_repository.items():
            if endpoint == f"repos/{repository}/git/trees/main?recursive=1":
                return tree
        raise AssertionError(f"Unexpected verification gh invocation: {arguments}")

    mocker.patch.object(verify, "run_gh_json", side_effect=fake_tree_run_gh_json)

    records = {}
    for rank, candidate in enumerate(ranked, start=1):
        candidate_dict = {
            "repository": candidate.repository,
            "default_branch": candidate.default_branch,
            "rank": rank,
            "stars": candidate.stars,
            "forks": candidate.forks,
        }
        records[candidate.repository] = verify.inspect_tree(candidate_dict)

    assert records[accepted_repo]["status"] == "accepted_for_semantic_inspection"
    assert records[rejected_repo]["status"] == "rejected_no_aligned_bundled_mcp"
    assert records[inconclusive_repo]["status"] == "inconclusive_tree_truncated"
