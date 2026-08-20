from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "discover_cross_harness_mcp_candidates.py"
_SPEC = importlib.util.spec_from_file_location("discover_cross_harness_mcp_candidates", _SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load module from {_SCRIPT_PATH}")
discovery = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = discovery
_SPEC.loader.exec_module(discovery)


def test_checkpoint_rejects_changed_page_size(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    discovery.write_checkpoint(checkpoint, [], {}, {}, 100)

    with pytest.raises(RuntimeError, match="page size"):
        discovery.load_checkpoint(checkpoint, 50)


def test_checkpoint_persists_page_size(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    discovery.write_checkpoint(checkpoint, [], {}, {}, 100)

    hits, summaries, metadata = discovery.load_checkpoint(checkpoint, 100)

    assert (hits, summaries, metadata) == ([], {}, {})


class TestRankCandidates:
    """Coverage of ``rank_candidates`` joining code-search hits with GraphQL metadata."""

    def _metadata(self, repository: str, *, stars: int, forks: int, branch: str | None = "main") -> dict[str, Any]:
        owner, name = repository.split("/", maxsplit=1)
        return {
            "nameWithOwner": repository,
            "stargazerCount": stars,
            "forkCount": forks,
            "isArchived": False,
            "url": f"https://github.com/{owner}/{name}",
            "defaultBranchRef": {"name": branch} if branch else None,
        }

    def test_excludes_candidates_below_minimum_stars(self) -> None:
        hits = [{"repository": "octo/low-stars", "path": ".codex-plugin/plugin.json", "query": "q"}]
        metadata = {"octo/low-stars": self._metadata("octo/low-stars", stars=10, forks=1)}

        candidates = discovery.rank_candidates(hits, metadata, minimum_stars=4000)

        assert candidates == []

    def test_excludes_hits_missing_metadata(self) -> None:
        hits = [{"repository": "octo/no-metadata", "path": ".codex-plugin/plugin.json", "query": "q"}]

        candidates = discovery.rank_candidates(hits, metadata={}, minimum_stars=0)

        assert candidates == []

    def test_sorts_by_stars_then_forks_then_repository_name(self) -> None:
        hits = [
            {"repository": "octo/beta", "path": ".codex-plugin/plugin.json", "query": "q"},
            {"repository": "octo/alpha", "path": ".codex-plugin/plugin.json", "query": "q"},
            {"repository": "octo/gamma", "path": ".codex-plugin/plugin.json", "query": "q"},
        ]
        metadata = {
            "octo/beta": self._metadata("octo/beta", stars=5000, forks=100),
            "octo/alpha": self._metadata("octo/alpha", stars=5000, forks=200),
            "octo/gamma": self._metadata("octo/gamma", stars=9000, forks=1),
        }

        candidates = discovery.rank_candidates(hits, metadata, minimum_stars=0)

        assert [candidate.repository for candidate in candidates] == ["octo/gamma", "octo/alpha", "octo/beta"]

    def test_deduplicates_and_sorts_discovery_hits_per_repository(self) -> None:
        hits = [
            {"repository": "octo/multi", "path": "z/.codex-plugin/plugin.json", "query": "query-b"},
            {"repository": "octo/multi", "path": "a/.codex-plugin/plugin.json", "query": "query-a"},
        ]
        metadata = {"octo/multi": self._metadata("octo/multi", stars=4000, forks=0)}

        (candidate,) = discovery.rank_candidates(hits, metadata, minimum_stars=0)

        assert candidate.discovery_hits == (
            {"path": "a/.codex-plugin/plugin.json", "query": "query-a"},
            {"path": "z/.codex-plugin/plugin.json", "query": "query-b"},
        )

    def test_default_branch_none_when_repository_has_no_default_branch_ref(self) -> None:
        hits = [{"repository": "octo/empty", "path": ".codex-plugin/plugin.json", "query": "q"}]
        metadata = {"octo/empty": self._metadata("octo/empty", stars=4000, forks=0, branch=None)}

        (candidate,) = discovery.rank_candidates(hits, metadata, minimum_stars=0)

        assert candidate.default_branch is None


class TestBuildMetadataQuery:
    """Coverage of the GraphQL query builder used by ``fetch_metadata``."""

    def test_builds_one_aliased_field_per_repository_in_order(self) -> None:
        query = discovery.build_metadata_query(["octo/first", "octo/second"])

        assert query.startswith("query CandidateMetadata {")
        assert query.index("r0: repository(") < query.index("r1: repository(")
        assert 'owner: "octo", name: "first"' in query
        assert 'owner: "octo", name: "second"' in query

    def test_escapes_repository_name_via_json_dumps(self) -> None:
        query = discovery.build_metadata_query(['octo/weird"name'])

        assert '\\"' in query

    def test_requests_the_expected_uptake_fields(self) -> None:
        query = discovery.build_metadata_query(["octo/repo"])

        for field in ("nameWithOwner", "stargazerCount", "forkCount", "isArchived", "url", "defaultBranchRef"):
            assert field in query


class TestSearchCode:
    """Coverage of the ``search_code`` pagination state machine."""

    def _page(
        self, *, total_count: int, items: list[dict[str, Any]], incomplete_results: bool = False
    ) -> dict[str, Any]:
        return {"total_count": total_count, "incomplete_results": incomplete_results, "items": items}

    def _item(self, repository: str, path: str) -> dict[str, Any]:
        return {"repository": {"full_name": repository}, "path": path}

    def test_single_page_marks_complete_and_records_hits(self, mocker: MockerFixture) -> None:
        response = self._page(
            total_count=2,
            items=[
                self._item("octo/a", ".codex-plugin/plugin.json"),
                self._item("octo/b", ".codex-plugin/plugin.json"),
            ],
        )
        run_gh_json = mocker.patch.object(discovery, "run_gh_json", return_value=response)
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")
        persist_calls = 0

        def persist() -> None:
            nonlocal persist_calls
            persist_calls += 1

        discovery.search_code(
            "q", page_size=100, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=persist
        )

        assert summary["complete"] is True
        assert summary["pages_fetched"] == 1
        assert summary["result_count"] == 2
        assert summary["truncated_by_github_limit"] is False
        assert hits == [
            {"repository": "octo/a", "path": ".codex-plugin/plugin.json", "query": "q"},
            {"repository": "octo/b", "path": ".codex-plugin/plugin.json", "query": "q"},
        ]
        assert persist_calls == 1
        assert run_gh_json.call_count == 1

    def test_multi_page_accumulates_across_pages_until_total_reached(self, mocker: MockerFixture) -> None:
        page_one = self._page(total_count=3, items=[self._item("octo/a", "p") for _ in range(2)])
        page_two = self._page(total_count=3, items=[self._item("octo/b", "p")])
        mocker.patch.object(discovery, "run_gh_json", side_effect=[page_one, page_two])
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")

        discovery.search_code(
            "q", page_size=2, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        assert summary["complete"] is True
        assert summary["pages_fetched"] == 2
        assert summary["result_count"] == 3

    def test_truncated_by_max_pages_when_total_not_reached(self, mocker: MockerFixture) -> None:
        page = self._page(total_count=100, items=[self._item("octo/a", "p")])
        mocker.patch.object(discovery, "run_gh_json", return_value=page)
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")

        discovery.search_code(
            "q", page_size=1, max_pages=2, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        assert summary["complete"] is False
        assert summary["truncated_by_max_pages"] is True
        assert summary["pages_fetched"] == 2

    def test_truncated_by_github_limit_flag_set_from_first_page_total(self, mocker: MockerFixture) -> None:
        page = self._page(total_count=5000, items=[])
        mocker.patch.object(discovery, "run_gh_json", return_value=page)
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")

        discovery.search_code(
            "q", page_size=100, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        assert summary["truncated_by_github_limit"] is True

    def test_result_count_mismatch_when_items_run_out_early(self, mocker: MockerFixture) -> None:
        page_one = self._page(total_count=5, items=[self._item("octo/a", "p")])
        page_two = self._page(total_count=5, items=[])
        mocker.patch.object(discovery, "run_gh_json", side_effect=[page_one, page_two])
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")

        discovery.search_code(
            "q", page_size=1, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        assert summary["complete"] is True
        assert summary["result_count_mismatch"] is True

    def test_already_complete_summary_is_a_no_op(self, mocker: MockerFixture) -> None:
        run_gh_json = mocker.patch.object(discovery, "run_gh_json")
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")
        summary["complete"] = True

        discovery.search_code(
            "q", page_size=100, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        run_gh_json.assert_not_called()
        assert hits == []

    def test_items_missing_repository_or_path_are_skipped(self, mocker: MockerFixture) -> None:
        page = self._page(total_count=1, items=[{"repository": {}, "path": ".codex-plugin/plugin.json"}])
        mocker.patch.object(discovery, "run_gh_json", return_value=page)
        hits: list[dict[str, str]] = []
        summary = discovery.default_query_summary("q")

        discovery.search_code(
            "q", page_size=100, max_pages=10, delay_seconds=0, hits=hits, summary=summary, persist=lambda: None
        )

        assert hits == []
