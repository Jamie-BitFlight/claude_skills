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

    def test_joins_metadata_case_insensitively(self) -> None:
        """An explicit seed's casing may differ from GraphQL's canonical nameWithOwner.

        fetch_metadata() stores results keyed by GitHub's canonical casing; a hit whose
        repository casing came from whatever the caller typed (e.g. --seed-repository
        Octo/Repo) must still join against metadata keyed "octo/repo" -- an exact-key
        lookup would silently exclude a real, valid candidate.
        """
        hits = [{"repository": "Octo/Repo", "path": ".codex-plugin/plugin.json", "query": "explicit_seed"}]
        metadata = {"octo/repo": self._metadata("octo/repo", stars=4000, forks=0)}

        candidates = discovery.rank_candidates(hits, metadata, minimum_stars=0)

        assert [c.repository for c in candidates] == ["Octo/Repo"]


class TestReconcileSeedHits:
    """Coverage of ``reconcile_seed_hits`` -- checkpoint seed-list reconciliation.

    A checkpoint created with --seed-repository A/B can be reused after that option is
    removed or changed; without reconciliation the stale explicit_seed hit stays ranked
    forever while the payload claims to reflect only the current seed list.
    """

    def test_drops_a_checkpointed_seed_no_longer_in_the_current_invocation(self) -> None:
        hits = [{"repository": "octo/stale-seed", "path": "", "query": "explicit_seed"}]

        reconciled = discovery.reconcile_seed_hits(hits, explicit_seed_repositories=[])

        assert reconciled == []

    def test_keeps_a_checkpointed_seed_still_in_the_current_invocation(self) -> None:
        hits = [{"repository": "octo/kept-seed", "path": "", "query": "explicit_seed"}]

        reconciled = discovery.reconcile_seed_hits(hits, explicit_seed_repositories=["octo/kept-seed"])

        assert reconciled == hits

    def test_matches_current_seeds_case_insensitively_so_it_is_not_dropped_then_readded(self) -> None:
        hits = [{"repository": "Octo/Cased-Seed", "path": "", "query": "explicit_seed"}]

        reconciled = discovery.reconcile_seed_hits(hits, explicit_seed_repositories=["octo/cased-seed"])

        # Preserves the original hit's casing rather than dropping and re-adding
        # a second entry under the --seed-repository argument's casing.
        assert reconciled == hits

    def test_never_drops_a_non_seed_code_search_hit(self) -> None:
        hits = [{"repository": "octo/from-search", "path": "x.json", "query": "some code search query"}]

        reconciled = discovery.reconcile_seed_hits(hits, explicit_seed_repositories=[])

        assert reconciled == hits

    def test_adds_a_newly_requested_seed_not_yet_in_hits(self) -> None:
        reconciled = discovery.reconcile_seed_hits([], explicit_seed_repositories=["octo/new-seed"])

        assert reconciled == [{"repository": "octo/new-seed", "path": "", "query": "explicit_seed"}]


class TestComputeQueryGaps:
    """Coverage of ``compute_query_gaps`` -- the four independent completeness signals."""

    @staticmethod
    def _summary(**overrides: object) -> dict[str, object]:
        base = {
            "complete": True,
            "result_count_mismatch": False,
            "incomplete_results": False,
            "truncated_by_github_limit": False,
        }
        base.update(overrides)
        return base

    def test_all_clean_produces_no_gaps(self) -> None:
        gaps = discovery.compute_query_gaps({"q1": self._summary()})

        assert gaps == discovery.QueryGaps([], [], [], [])

    def test_github_incomplete_results_flagged_even_when_our_pagination_is_complete(self) -> None:
        """Our own "complete" flag can be True while GitHub's own search was itself incomplete."""
        gaps = discovery.compute_query_gaps({"q1": self._summary(complete=True, incomplete_results=True)})

        assert gaps.incomplete_queries == []
        assert gaps.github_incomplete_queries == ["q1"]

    def test_result_cap_truncation_flagged_even_when_our_pagination_is_complete(self) -> None:
        gaps = discovery.compute_query_gaps({"q1": self._summary(complete=True, truncated_by_github_limit=True)})

        assert gaps.incomplete_queries == []
        assert gaps.truncated_queries == ["q1"]

    def test_each_gap_category_maps_to_its_own_field(self) -> None:
        summaries = {
            "incomplete": self._summary(complete=False),
            "mismatched": self._summary(result_count_mismatch=True),
            "github-incomplete": self._summary(incomplete_results=True),
            "truncated": self._summary(truncated_by_github_limit=True),
        }

        gaps = discovery.compute_query_gaps(summaries)

        assert gaps.incomplete_queries == ["incomplete"]
        assert gaps.mismatched_queries == ["mismatched"]
        assert gaps.github_incomplete_queries == ["github-incomplete"]
        assert gaps.truncated_queries == ["truncated"]


def _gaps(
    incomplete: list[str] | None = None,
    mismatched: list[str] | None = None,
    github_incomplete: list[str] | None = None,
    truncated: list[str] | None = None,
) -> Any:
    return discovery.QueryGaps(
        incomplete_queries=incomplete or [],
        mismatched_queries=mismatched or [],
        github_incomplete_queries=github_incomplete or [],
        truncated_queries=truncated or [],
    )


class TestBuildCollectionWarnings:
    """Coverage of ``build_collection_warnings``, including missing-GraphQL-metadata tracking.

    A repository whose GraphQL alias returns null (renamed, made private, or deleted since the
    code-search hit was recorded) is silently dropped by rank_candidates -- correctly, since it
    can't be ranked. Without this warning it was indistinguishable in the report from a candidate
    correctly excluded for being below --minimum-stars.
    """

    def test_no_gaps_produces_no_warnings(self) -> None:
        assert discovery.build_collection_warnings(_gaps(), []) == []

    def test_incomplete_queries_produce_a_warning(self) -> None:
        warnings = discovery.build_collection_warnings(_gaps(incomplete=["q1"]), [])

        assert warnings == ["one or more Code Search queries have uncollected pages"]

    def test_mismatched_queries_produce_a_warning(self) -> None:
        warnings = discovery.build_collection_warnings(_gaps(mismatched=["q1"]), [])

        assert warnings == ["GitHub advertised more Code Search results than its pages returned"]

    def test_missing_metadata_repositories_produce_a_counted_warning(self) -> None:
        warnings = discovery.build_collection_warnings(_gaps(), ["octo/renamed", "octo/deleted"])

        assert len(warnings) == 1
        assert "2 candidate repositories returned no GraphQL metadata" in warnings[0]
        assert "missing_metadata_repositories" in warnings[0]

    def test_github_incomplete_results_produce_a_warning_independent_of_our_pagination(self) -> None:
        """GitHub's own per-page incompleteness flag must be surfaced even when our pagination is clean."""
        warnings = discovery.build_collection_warnings(_gaps(github_incomplete=["q1"]), [])

        assert len(warnings) == 1
        assert "incomplete" in warnings[0].lower()
        assert "incomplete_results" in warnings[0]

    def test_github_result_cap_truncation_produces_a_warning(self) -> None:
        """A query hitting GitHub's 1,000-result cap must be surfaced -- more --max-pages can't fix it."""
        warnings = discovery.build_collection_warnings(_gaps(truncated=["q1"]), [])

        assert len(warnings) == 1
        assert "1,000-result" in warnings[0]
        assert "truncated_by_github_limit" in warnings[0]

    def test_all_five_gap_categories_each_produce_their_own_warning(self) -> None:
        gaps = _gaps(incomplete=["q1"], mismatched=["q2"], github_incomplete=["q1"], truncated=["q2"])

        warnings = discovery.build_collection_warnings(gaps, ["octo/gone"])

        assert len(warnings) == 5


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
