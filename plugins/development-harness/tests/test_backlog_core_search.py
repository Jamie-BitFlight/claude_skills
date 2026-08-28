"""Tests for backlog_core/search.py content-based duplicate detection.

Replaces the retired title-character (``difflib.SequenceMatcher``) duplicate
suite in ``test_backlog_core_parsing.py`` — see #3169.

The false-positive corpus in ``test_no_false_positive_on_must_not_match_pairs``
is drawn from real, resolved, unrelated GitHub issues in this repository's own
tracker (all same subsystem: ``backlog_core`` / ``backlog-mcp``), so a
passing corpus measures actual behaviour on real records, not invented
fixtures. Provenance (issue number pairs, both closed at the time this suite
was written):

    2978 / 2907, 3157 / 2273, 2900 / 2518, 2903 / 1076, 1664 / 2510,
    2529 / 2904, 2905 / 2899, 2459 / 2420, 1610 / 2904, 916 / 2899,
    2585 / 612, 2656 / 2518

The AC1 regression pair in ``test_incident_pair_from_3169_report_is_detected``
is the real pair from the #3169 incident report: issue #3138 ("CI check for
drift between MCP server tool lists and agent frontmatter tools: entries")
and the independently-filed duplicate that prompted this fix. Under the old
``SequenceMatcher``-based algorithm this pair scored 0.4683 against a 0.80
threshold and was never detected.
"""

from __future__ import annotations

import pytest
from backlog_core.search import ContentDuplicateMatch, build_concept_query, find_content_duplicates


def _candidate(
    title: str, body: str, *, status: str = "open", issue: str = "", file_path: str = ""
) -> dict[str, str | bool]:
    entry: dict[str, str | bool] = {"title": title, "body": body, "status": status}
    if issue:
        entry["issue"] = issue
    if file_path:
        entry["file_path"] = file_path
    return entry


# ---------------------------------------------------------------------------
# find_content_duplicates
# ---------------------------------------------------------------------------


class TestFindContentDuplicates:
    """Tests for find_content_duplicates(title, description, candidates, max_results)."""

    def test_exact_content_match_is_detected(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors as non-retryable, "
                "causing sync to abort instead of retrying.",
                issue="3200",
            )
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors",
            "Sync engine misclassifies transient network errors as non-retryable, "
            "causing sync to abort instead of retrying.",
            candidates,
        )

        assert len(matches) == 1
        assert matches[0].item_ref == "3200"

    def test_clearly_dissimilar_content_returns_no_matches(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors as non-retryable.",
                issue="3200",
            )
        ]

        matches = find_content_duplicates(
            "Add dark mode toggle to settings page",
            "Users want a dark mode toggle available in the settings UI panel.",
            candidates,
        )

        assert matches == []

    def test_candidates_with_excluded_status_are_not_matched(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors as non-retryable.",
                status="done",
                issue="3200",
            )
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors",
            "Sync engine misclassifies transient network errors as non-retryable.",
            candidates,
        )

        assert matches == []

    def test_candidates_with_empty_title_are_skipped(self) -> None:
        candidates = [
            _candidate("", "Sync engine misclassifies transient network errors as non-retryable.", issue="3200")
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors",
            "Sync engine misclassifies transient network errors as non-retryable.",
            candidates,
        )

        assert matches == []

    def test_empty_title_and_description_input_returns_no_matches(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors as non-retryable.",
                issue="3200",
            )
        ]

        matches = find_content_duplicates("", "", candidates)

        assert matches == []

    def test_max_results_caps_the_number_of_matches_returned(self) -> None:
        candidates = [
            _candidate("Something about alpha only", "alpha", issue="1"),
            _candidate("Alpha and beta topic", "alpha beta", issue="2"),
            _candidate("Alpha beta gamma all match", "alpha beta gamma delta", issue="3"),
        ]

        matches = find_content_duplicates("Alpha Beta Gamma Delta", "", candidates, max_results=2)

        assert len(matches) == 2

    def test_results_are_ordered_by_match_count_descending(self) -> None:
        candidates = [
            _candidate("Something about alpha only", "alpha", issue="1"),
            _candidate("Alpha and beta topic", "alpha beta", issue="2"),
            _candidate("Alpha beta gamma all match", "alpha beta gamma delta", issue="3"),
        ]

        matches = find_content_duplicates("Alpha Beta Gamma Delta", "", candidates, max_results=3)

        match_counts = [m.match_count for m in matches]
        assert match_counts == sorted(match_counts, reverse=True)

    def test_item_ref_uses_issue_number_when_present(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors.",
                issue="3200",
                file_path="p1-sync-retry",
            )
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors", "Sync engine misclassifies transient network errors.", candidates
        )

        assert matches[0].item_ref == "3200"

    def test_item_ref_falls_back_to_logical_reference_never_a_bare_file_path(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors.",
                file_path="p1-sync-retry",
            )
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors", "Sync engine misclassifies transient network errors.", candidates
        )

        assert matches[0].item_ref
        assert not matches[0].item_ref.startswith("/")
        assert not matches[0].item_ref.endswith(".md")

    def test_incident_pair_from_3169_report_is_detected(self) -> None:
        """The real #3169 failure case: reworded duplicate the old SequenceMatcher

        algorithm scored 0.4683 (below its 0.80 threshold) and never caught.
        """
        candidates = [
            _candidate(
                "CI check for drift between MCP server tool lists and agent frontmatter `tools:` entries",
                "Every agent definition that uses MCP tools enumerates them by exact name in its "
                "tools: frontmatter. This couples the MCP server's tool code to agent frontmatter "
                "bidirectionally, with no enforcement and silent failure in both directions. "
                "Removing or renaming a tool on the server leaves dead entries in every agent that "
                "listed it.",
                issue="3138",
            )
        ]

        matches = find_content_duplicates(
            "Agent `tools:` frontmatter drifts from MCP server tool lists with no enforcement "
            "and silent failure in both directions",
            "Agent frontmatter tools: entries drift from the MCP server's actual tool list with "
            "no enforcement mechanism and silent failure in both directions when tools are added "
            "or removed.",
            candidates,
        )

        assert len(matches) == 1
        assert matches[0].item_ref == "3138"

    @pytest.mark.parametrize(
        ("existing_title", "existing_body", "new_title", "new_body"),
        [
            pytest.param(
                "fix: backlog_core parse_md_body_sections derives section keys with a different "
                "rule than the write/GitHub-parse paths",
                "parse_md_body_sections derives section keys with a different normalization rule "
                "than the write path and the GitHub-parse path use, so a section written locally "
                "is not recognized as the same section when read back.",
                "artifact/plan content writes never land — GitHub ruleset blocks direct Contents API commits to main",
                "GitHubBackend.put_content used for artifact manifests, artifact content, plans, "
                "and dispatch plans attempts a direct commit to main, which a branch-protection "
                "ruleset silently rejects, so the write never lands.",
                id="2978_vs_2907",
            ),
            pytest.param(
                "backlog_view invents sections from headings inside entry content, because "
                "operations.py keeps a second unguarded section scanner",
                "backlog_groom reports success while discarding the content it was given, and a "
                "section with unbalanced entry tags absorbs the next section, because "
                "operations.py runs a second heading scanner that is not guarded against entry "
                "content.",
                "Add local filesystem artifact fallback to backlog_core ArtifactBackend",
                "When no remote backend is configured, or the configured backend is unreachable, "
                "all MCP artifact tools fail outright instead of falling back to a local "
                "filesystem store for artifact content.",
                id="3157_vs_2273",
            ),
            pytest.param(
                "backlog groom fails with BacklogError 'Item has no backend reference' for valid open GitHub items",
                "Observed during work-backlog-item auto grooming: backlog_groom raises "
                "BacklogError 'Item has no backend reference' even though the item has a valid "
                "open GitHub issue backing it.",
                "result.sections not populated for non-exact section filters in backlog_view",
                "When backlog_view is called with a non-exact section filter such as a substring, "
                "regex pattern, or numeric index, the sections metadata builder still performs "
                "exact case-insensitive header matching, so result.sections comes back empty.",
                id="2900_vs_2518",
            ),
            pytest.param(
                "GitHub-backend reconcile reports '1 failure(s)' on every run",
                "Every GitHub-backend reconcile in this repo's live cache reports '1 failure(s)' "
                "in the reconcile summary even when nothing actually failed, discovered while "
                "fixing an unrelated grooming bug.",
                "Batch section writes for backlog_groom MCP tool",
                "backlog_groom only accepts one section update per call, forcing callers who need "
                "to update several sections at once to make multiple round trips and multiple "
                "GitHub syncs instead of one atomic batch write.",
                id="2903_vs_1076",
            ),
            pytest.param(
                "backlog_view dumps entire item body, causing ~14k token MCP responses that fill agent context",
                "backlog_view called with summary=False returns the full ViewItemResult dict "
                "unconditionally. For groomed items with large bodies this produces ~14.8k token "
                "MCP responses that fill agent context.",
                "add-new-feature skill delegates backlog_update(plan=) to subagent instead of "
                "calling it from orchestrator",
                "After task decomposition completes in add-new-feature, the skill instructs the "
                "orchestrator to delegate the plan-link update to a subagent instead of calling "
                "backlog_update directly, so the plan link silently fails to persist.",
                id="1664_vs_2510",
            ),
            pytest.param(
                "recursive sub-section and code-fence navigation for backlog_view progressive disclosure",
                "The current backlog_view progressive disclosure contract operates only at two "
                "levels: GitHub issue section and entry within section. Deeper sub-sections and "
                "embedded code fences are not navigable.",
                "BacklogItem.reference not kept in sync with metadata.issue by model validator",
                "Unlike priority/issue and other backward-compatible flat fields, "
                "BacklogItem.reference is not kept in sync with metadata.issue by the model "
                "validator, discovered while fixing an unrelated grooming bug.",
                id="2529_vs_2904",
            ),
            pytest.param(
                "backlog update --status done silently no-ops instead of erroring or transitioning",
                "backlog update --selector ... --status done silently no-ops instead of erroring "
                "or transitioning the item to a done state, discovered during grooming and "
                "re-confirmed while fixing an unrelated backend issue.",
                "artifact register reports content_stored:true but artifact list/get return zero "
                "results for same item-id",
                "Observed during work-backlog-item auto on an item: artifact register --item-id "
                "--artifact-type feature-context reports content_stored true, but a subsequent "
                "artifact list or artifact get for the same item id returns zero results.",
                id="2905_vs_2899",
            ),
            pytest.param(
                "backlog_update selector returns ambiguous match when local cache title differs "
                "from GitHub issue title",
                "backlog_update selector lookup returned an Ambiguous selector error even though "
                "only one item matched, because the local cache title differs from the live "
                "GitHub issue title.",
                "complete-implementation final step must close issue via backlog MCP, not GitHub-specific Closes",
                "complete-implementation applies status:verified to the backlog item but never "
                "closes the GitHub issue, so after the PR merges and the session ends the issue "
                "stays open indefinitely.",
                id="2459_vs_2420",
            ),
            pytest.param(
                "backlog_core tests create real GitHub issues due to incomplete test isolation",
                "test_backlog_core_operations.py and test_batch_section_writes.py create real "
                "GitHub issues during test runs when the GitHub mock is absent or incomplete, "
                "polluting the real issue tracker with test artifacts.",
                "BacklogItem.reference not kept in sync with metadata.issue by model validator",
                "Unlike priority/issue and other backward-compatible flat fields, "
                "BacklogItem.reference is not kept in sync with metadata.issue by the model "
                "validator, discovered while fixing an unrelated grooming bug.",
                id="1610_vs_2904",
            ),
            pytest.param(
                "Complete GraphQL migration for backlog MCP server",
                "The backlog MCP server uses the PyGitHub REST API for milestones, issues, PRs, "
                "and most operations. Only label lookups and Projects V2 operations use GraphQL; "
                "the rest of the server was never migrated.",
                "artifact register reports content_stored:true but artifact list/get return zero "
                "results for same item-id",
                "Observed during work-backlog-item auto on an item: artifact register --item-id "
                "--artifact-type feature-context reports content_stored true, but a subsequent "
                "artifact list or artifact get for the same item id returns zero results.",
                id="916_vs_2899",
            ),
            pytest.param(
                "sync_groomed_to_github_issue must write entry-block wrappers so GitHub-only items preserve entry IDs",
                "sync_groomed_to_github_issue writes groomed section content without entry-block "
                "wrappers, so GitHub-only items (with no local YAML file) lose their entry IDs on "
                "the next sync round-trip.",
                "backlog: add status field to BacklogItem model",
                "Every call to view_result_from_local_item re-opens and re-parses the per-item "
                "file solely to extract the status field, a redundant disk read that a cached "
                "status field on the BacklogItem model would eliminate.",
                id="2585_vs_612",
            ),
            pytest.param(
                "backlog MCP tool compatibility gaps with beads backend",
                "The backlog MCP server has confirmed compatibility gaps when the backend is "
                "beads instead of GitHub: backlog_view rejects beads nanoid selectors among other "
                "mismatches.",
                "result.sections not populated for non-exact section filters in backlog_view",
                "When backlog_view is called with a non-exact section filter such as a substring, "
                "regex pattern, or numeric index, the sections metadata builder still performs "
                "exact case-insensitive header matching, so result.sections comes back empty.",
                id="2656_vs_2518",
            ),
        ],
    )
    def test_no_false_positive_on_must_not_match_pairs(
        self, existing_title: str, existing_body: str, new_title: str, new_body: str
    ) -> None:
        """Real, resolved, unrelated backlog_core/backlog-mcp issues must never match.

        See the module docstring for the source issue numbers behind each pair.
        """
        candidates = [_candidate(existing_title, existing_body, issue="1")]

        matches = find_content_duplicates(new_title, new_body, candidates)

        assert matches == []


# ---------------------------------------------------------------------------
# build_concept_query
# ---------------------------------------------------------------------------


class TestBuildConceptQuery:
    """Tests for build_concept_query(title, description, max_concepts)."""

    def test_empty_title_and_description_returns_empty_string(self) -> None:
        assert build_concept_query("", "") == ""

    def test_max_concepts_limits_the_number_of_terms(self) -> None:
        query = build_concept_query("Alpha Beta Gamma Delta Epsilon", "", max_concepts=2)

        assert query == "alpha OR beta"

    def test_stopwords_are_dropped_from_the_concept_query(self) -> None:
        query = build_concept_query("The quick brown fox and the lazy dog", "")

        assert "the" not in query.split(" OR ")
        assert "and" not in query.split(" OR ")


# ---------------------------------------------------------------------------
# ContentDuplicateMatch
# ---------------------------------------------------------------------------


class TestContentDuplicateMatchInvariant:
    """Tests for the ContentDuplicateMatch.item_ref invariant (spec §6.2)."""

    def test_item_ref_is_never_empty(self) -> None:
        candidates = [
            _candidate(
                "Sync retryable network errors",
                "Sync engine misclassifies transient network errors.",
                file_path="p1-sync-retry",
            )
        ]

        matches = find_content_duplicates(
            "Sync retryable network errors", "Sync engine misclassifies transient network errors.", candidates
        )

        assert isinstance(matches[0], ContentDuplicateMatch)
        assert matches[0].item_ref != ""
