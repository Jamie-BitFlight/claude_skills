"""Tests for backlog.py GH-first Phase 1 changes.

Tests use pytest-mock (mocker fixture) to mock PyGithub — no live API calls.
Import uses importlib because backlog.py lives under .claude/ (not a Python package).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Load backlog.py as a module via importlib (dot in .claude/ breaks normal import)
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).parent.parent / "scripts" / "backlog.py"
_spec = importlib.util.spec_from_file_location("backlog", _SCRIPT)
assert _spec is not None, f"Cannot find spec for {_SCRIPT}"
assert _spec.loader is not None, f"Cannot find loader for {_SCRIPT}"
_mod = importlib.util.module_from_spec(_spec)
sys.modules["backlog"] = _mod
_spec.loader.exec_module(_mod)

app = _mod.app
runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BACKLOG_DIR to a temp directory for every test.

    Tests: Test isolation for backlog directory.
    How: Patches BACKLOG_DIR to a fresh tmp_path per test.
    Why: Prevents tests from reading/writing real backlog files.
    """
    monkeypatch.setattr(_mod, "BACKLOG_DIR", tmp_path / ".claude" / "backlog")
    (tmp_path / ".claude" / "backlog").mkdir(parents=True, exist_ok=True)


def _make_mock_issue(mocker: MockerFixture, number: int = 999, title: str = "feat: Test item") -> object:
    """Create a mock GitHub Issue with standard attributes.

    Args:
        mocker: pytest-mock fixture for creating mocks.
        number: Issue number.
        title: Issue title.

    Returns:
        Mock object mimicking a PyGithub Issue.
    """
    issue = mocker.Mock()
    issue.number = number
    issue.title = title
    issue.body = "## Story\n\nTest\n\n## Description\n\nTest description"
    issue.state = "open"
    issue.pull_request = None
    label_mock = mocker.Mock()
    label_mock.name = "status:in-progress"
    issue.labels = [label_mock]
    issue.milestone = None
    return issue


# ─── T1: add GH-first ───


class TestAddGhFirst:
    """T1: Verify add creates GitHub Issue before writing local file.

    Tests the GH-first flow for the `add` command: issue creation happens
    before the local cache file is written. Covers online, offline, and
    --no-create-issue scenarios.
    """

    def test_add_creates_gh_issue_first(self, mocker: MockerFixture) -> None:
        """Verify add creates GH Issue first, then writes local cache with issue number.

        Tests: GH-first add command.
        How: Mock _try_get_github to return a repo, mock create_issue_for_item to return 42.
        Why: Core GH-first guarantee — issue must exist before local file.
        """
        # Arrange
        mock_create = mocker.patch.object(_mod, "create_issue_for_item", return_value=42)
        mock_try_gh = mocker.patch.object(_mod, "_try_get_github", return_value=mocker.Mock())

        # Act
        result = runner.invoke(
            app, ["add", "--title", "Test GH-first", "--priority", "P1", "--description", "Testing GH-first add"]
        )

        # Assert
        assert result.exit_code == 0
        mock_try_gh.assert_called_once()
        mock_create.assert_called_once()
        assert "Issue: #42" in result.output

    def test_add_offline_fallback(self, mocker: MockerFixture) -> None:
        """Verify add creates local-only file when GitHub is unavailable.

        Tests: Graceful degradation for add command.
        How: Mock _try_get_github returning None (offline/no token).
        Why: Agents must work offline — local file created without issue number.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(
            app, ["add", "--title", "Offline test", "--priority", "P2", "--description", "Should work offline"]
        )

        # Assert
        assert result.exit_code == 0
        assert "WARNING: GitHub unavailable" in result.output
        assert "Backlog item created" in result.output
        assert "Issue: #" not in result.output

    def test_add_no_create_issue_flag(self, mocker: MockerFixture) -> None:
        """Verify --no-create-issue skips GitHub entirely.

        Tests: Local-only mode via CLI flag.
        How: Pass --no-create-issue and verify _try_get_github is never called.
        Why: Needed for testing/offline use — explicit opt-out of GH integration.
        """
        # Arrange
        mock_try_gh = mocker.patch.object(_mod, "_try_get_github")

        # Act
        result = runner.invoke(
            app, ["add", "--title", "Local only", "--priority", "P2", "--description", "No GH", "--no-create-issue"]
        )

        # Assert
        assert result.exit_code == 0
        mock_try_gh.assert_not_called()


# ─── T2: list --from-github ───


class TestListFromGithub:
    """T2: Verify list --from-github refreshes cache from GH.

    Tests the --from-github flag on the list command: queries GitHub Issues
    and rebuilds local cache before displaying results. Default list (no flag)
    must remain local-only with zero API calls.
    """

    def test_list_default_no_api_calls(self, mocker: MockerFixture) -> None:
        """Verify default list reads only local files — zero API calls.

        Tests: Cache-first read design.
        How: Invoke list without --from-github, verify _try_get_github never called.
        Why: Agents calling list frequently must not trigger API calls.
        """
        # Arrange
        mock_try_gh = mocker.patch.object(_mod, "_try_get_github")

        # Act
        result = runner.invoke(app, ["list", "--format", "json"])

        # Assert
        assert result.exit_code == 0
        mock_try_gh.assert_not_called()

    def test_list_from_github_refreshes_cache(self, mocker: MockerFixture) -> None:
        """Verify --from-github queries GH, calls _pull_single_issue per issue.

        Tests: GH-first list with cache refresh.
        How: Mock repo.get_issues to return one mock issue, verify _pull_single_issue called.
        Why: --from-github must fetch fresh data from GH and update local cache.
        """
        # Arrange
        mock_repo = mocker.Mock()
        mocker.patch.object(_mod, "_try_get_github", return_value=mock_repo)
        mock_pull = mocker.patch.object(_mod, "_pull_single_issue", return_value=Path("/tmp/test.md"))
        mock_issue = _make_mock_issue(mocker)
        mock_repo.get_issues.return_value = [mock_issue]
        mock_repo.get_label.return_value = mocker.Mock()

        # Act
        result = runner.invoke(app, ["list", "--from-github", "--format", "json"])

        # Assert
        assert result.exit_code == 0
        # _refresh_local_cache_from_github calls get_issues once (state="all"),
        # then _reconcile_batch calls it again — assert at least one call occurred.
        mock_repo.get_issues.assert_called()
        mock_pull.assert_called_once_with(mock_repo, 999)

    def test_list_from_github_offline_fallback(self, mocker: MockerFixture) -> None:
        """Verify --from-github falls back to local cache when GH unavailable.

        Tests: Graceful degradation for list --from-github.
        How: Mock _try_get_github returning None.
        Why: Offline agents must see local cache, not crash.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(app, ["list", "--from-github", "--format", "json"])

        # Assert
        assert result.exit_code == 0
        assert "WARNING: GitHub unavailable" in result.output


# ─── T3: update --plan GH-first ───


class TestUpdatePlanGhFirst:
    """T3: Verify update --plan writes to GH Issue then local.

    Tests the GH-first flow for plan updates: plan reference is posted as a
    comment on the linked GitHub Issue, then the local cache file is updated.
    """

    def test_update_plan_posts_gh_comment(self, mocker: MockerFixture) -> None:
        """Verify update --plan posts plan comment on GH Issue and updates local.

        Tests: GH-first plan update.
        How: Create local item with issue #99, mock GH, verify create_comment called.
        Why: Plan references must be visible on GH Issue for team visibility.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        item_file = backlog_dir / "p1-test-plan-item.md"
        item_file.write_text(
            "---\nname: Test plan item\ndescription: Test\nmetadata:\n  issue: '#99'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-plan-item\n---\n",
            encoding="utf-8",
        )
        mock_repo = mocker.Mock()
        mocker.patch.object(_mod, "_try_get_github", return_value=mock_repo)
        mock_issue = _make_mock_issue(mocker, 99)
        mock_repo.get_issue.return_value = mock_issue

        # Act
        result = runner.invoke(app, ["update", "Test plan", "--plan", "plan/tasks-1-test.md", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 0
        mock_issue.create_comment.assert_called_once_with("**Plan**: plan/tasks-1-test.md")

    def test_update_plan_offline_still_updates_local(self, mocker: MockerFixture) -> None:
        """Verify update --plan writes local file even when GH is unavailable.

        Tests: Offline fallback for plan update.
        How: Mock _try_get_github returning None, verify local file contains plan path.
        Why: Local cache must always be updated regardless of GH availability.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        item_file = backlog_dir / "p1-offline-plan.md"
        item_file.write_text(
            "---\nname: Offline plan test\ndescription: Test\nmetadata:\n  priority: P1\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: offline-plan-test\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(app, ["update", "Offline plan", "--plan", "plan/test.md", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 0
        assert "plan/test.md" in item_file.read_text()


# ─── T4: pull auto-migration ───


class TestPullAutoMigration:
    """T4: Verify pull creates missing GH Issues for P0/P1 items.

    Tests the auto-migration behavior in the pull command: P0/P1 items without
    GitHub Issues get them created automatically. P2/Ideas are skipped.
    """

    def test_pull_auto_migrates_p0_p1(self, mocker: MockerFixture) -> None:
        """Verify pull creates GH Issues for P0/P1 items missing them.

        Tests: Auto-migration in pull command.
        How: Create P1 item without issue, mock GH, verify _sync_create_missing_issues called.
        Why: P0/P1 items must be on GitHub for team visibility and tracking.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-unmigrated.md").write_text(
            "---\nname: Unmigrated P1\ndescription: Needs migration\nmetadata:\n  priority: P1\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: unmigrated-p1\n---\n",
            encoding="utf-8",
        )
        mock_sync = mocker.patch.object(_mod, "_sync_create_missing_issues")
        mocker.patch.object(_mod, "_get_github", return_value=mocker.Mock())
        mocker.patch.object(_mod, "_pull_item", return_value=False)

        # Act
        runner.invoke(app, ["pull", "-R", "test/repo"])

        # Assert
        mock_sync.assert_called_once()

    def test_pull_skips_p2_ideas(self, mocker: MockerFixture) -> None:
        """Verify pull does NOT auto-migrate P2/Ideas items.

        Tests: Auto-migration scope restriction.
        How: Create P2 item without issue, verify _sync_create_missing_issues NOT called.
        Why: P2/Ideas stay local-only unless explicitly synced.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p2-no-migrate.md").write_text(
            "---\nname: P2 no migrate\ndescription: Stay local\nmetadata:\n  priority: P2\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: p2-no-migrate\n---\n",
            encoding="utf-8",
        )
        mock_sync = mocker.patch.object(_mod, "_sync_create_missing_issues")
        mocker.patch.object(_mod, "_get_github", return_value=mocker.Mock())

        # Act
        runner.invoke(app, ["pull", "-R", "test/repo"])

        # Assert
        mock_sync.assert_not_called()


# ─── T5: batch status fetch ───


class TestBatchStatusFetch:
    """T5: Verify --with-status uses batch fetch instead of N+1 queries.

    Tests the _batch_fetch_statuses function that replaces per-item
    get_issue() calls with a single get_issues(state="open") call.
    """

    def test_list_with_status_uses_batch(self, mocker: MockerFixture) -> None:
        """Verify list --with-status calls _batch_fetch_statuses once.

        Tests: Batch status fetch integration.
        How: Create item with issue #100, mock batch fetch, verify single call and output.
        Why: N+1 queries are slow and risk rate limiting — batch is mandatory.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-batch-test.md").write_text(
            "---\nname: Batch test\ndescription: Test\nmetadata:\n  issue: '#100'\n  priority: P1\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: batch-test\n---\n",
            encoding="utf-8",
        )
        mock_batch = mocker.patch.object(
            _mod, "_batch_fetch_statuses", return_value={100: {"status": "status:in-progress", "milestone": "v1.0"}}
        )

        # Act
        result = runner.invoke(app, ["list", "--with-status", "--format", "json", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 0
        mock_batch.assert_called_once()
        data = json.loads(result.output)
        items_100 = [it for it in data if it.get("issue") == "#100"]
        assert len(items_100) == 1
        assert items_100[0]["status"] == "status:in-progress"

    def test_batch_fetch_offline_returns_empty(self, mocker: MockerFixture) -> None:
        """Verify _batch_fetch_statuses returns empty dict when GH unavailable.

        Tests: Batch fetch graceful degradation.
        How: Mock _try_get_github returning None, call _batch_fetch_statuses directly.
        Why: Offline agents must get empty status, not crash.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = _mod._batch_fetch_statuses([{"_issue": "#100"}], "test/repo")

        # Assert
        assert result == {}


# ─── Graceful degradation ───


class TestGracefulDegradation:
    """Cross-cutting: all commands degrade gracefully when GH is unavailable.

    Verifies that every GH-first command completes successfully with exit
    code 0 when _try_get_github returns None (no token, network error).
    """

    def test_add_degrades(self, mocker: MockerFixture) -> None:
        """Verify add completes successfully when GH unavailable.

        Tests: Add command graceful degradation.
        How: Mock _try_get_github returning None, invoke add.
        Why: Agents must always be able to create backlog items.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(app, ["add", "--title", "Degrade test", "--priority", "P1", "--description", "test"])

        # Assert
        assert result.exit_code == 0

    def test_list_from_github_degrades(self, mocker: MockerFixture) -> None:
        """Verify list --from-github completes successfully when GH unavailable.

        Tests: List --from-github graceful degradation.
        How: Mock _try_get_github returning None, invoke list --from-github.
        Why: Agents must fall back to local cache, not crash.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(app, ["list", "--from-github", "--format", "json"])

        # Assert
        assert result.exit_code == 0

    def test_list_with_status_degrades(self, mocker: MockerFixture) -> None:
        """Verify list --with-status completes successfully when batch fetch empty.

        Tests: List --with-status graceful degradation.
        How: Mock _batch_fetch_statuses returning empty dict.
        Why: Status display must work even without GH data.
        """
        # Arrange
        mocker.patch.object(_mod, "_batch_fetch_statuses", return_value={})

        # Act
        result = runner.invoke(app, ["list", "--with-status", "--format", "json"])

        # Assert
        assert result.exit_code == 0


# ─── T6: fuzzy duplicate detection ───


class TestFuzzyDuplicateDetection:
    """T6: Verify add command detects fuzzy duplicate titles.

    Tests the _find_fuzzy_duplicates function and its integration into the
    add command. Near-duplicate items are blocked unless --force is used.
    """

    def test_find_fuzzy_duplicates_exact_match(self) -> None:
        """Verify exact title match returns 100% similarity.

        Tests: _find_fuzzy_duplicates with identical titles.
        How: Pass same title as existing item.
        Why: Exact duplicates must always be caught.
        """
        items = [{"_title": "SAM: Error Recovery", "_file_path": "/tmp/p1-sam-error-recovery.md"}]
        matches = _mod._find_fuzzy_duplicates("SAM: Error Recovery", items)
        assert len(matches) == 1
        assert matches[0][1] >= 1.0

    def test_find_fuzzy_duplicates_similar_title(self) -> None:
        """Verify similar titles are detected above threshold.

        Tests: _find_fuzzy_duplicates with near-duplicate titles.
        How: Use titles that differ by a few words but describe the same thing.
        Why: Fuzzy matching must catch near-duplicates, not just exact matches.
        """
        items = [{"_title": "backlog.py add: implement duplicate detection", "_file_path": "/tmp/p1-test.md"}]
        matches = _mod._find_fuzzy_duplicates("backlog.py add: implement fuzzy duplicate detection", items)
        assert len(matches) == 1
        assert matches[0][1] >= 0.80

    def test_find_fuzzy_duplicates_different_title(self) -> None:
        """Verify dissimilar titles are not flagged.

        Tests: _find_fuzzy_duplicates with unrelated titles.
        How: Use completely different titles.
        Why: False positives would block legitimate new items.
        """
        items = [{"_title": "Validate carbonyl Terminal Browser", "_file_path": "/tmp/p2-test.md"}]
        matches = _mod._find_fuzzy_duplicates("SAM: Error Recovery", items)
        assert len(matches) == 0

    def test_find_fuzzy_duplicates_skips_done_items(self) -> None:
        """Verify done/resolved items are excluded from duplicate check.

        Tests: _find_fuzzy_duplicates skip logic.
        How: Mark existing item with _skip=True (done/resolved).
        Why: Completed items should not block creating a new item with the same name.
        """
        items = [{"_title": "SAM: Error Recovery", "_file_path": "/tmp/test.md", "_skip": True}]
        matches = _mod._find_fuzzy_duplicates("SAM: Error Recovery", items)
        assert len(matches) == 0

    def test_find_fuzzy_duplicates_strips_commit_prefix(self) -> None:
        """Verify conventional-commit prefixes are stripped before comparison.

        Tests: _find_fuzzy_duplicates normalization.
        How: One title has 'feat:' prefix, other does not.
        Why: Prefixes should not prevent duplicate detection.
        """
        items = [{"_title": "feat: SAM: Error Recovery", "_file_path": "/tmp/test.md"}]
        matches = _mod._find_fuzzy_duplicates("SAM: Error Recovery", items)
        assert len(matches) == 1
        assert matches[0][1] >= 1.0

    def test_add_blocks_on_duplicate(self, mocker: MockerFixture) -> None:
        """Verify add command exits with error when fuzzy duplicate found.

        Tests: add command duplicate detection integration.
        How: Create existing item, then try to add one with a near-identical title.
        Why: Duplicate items waste effort and cause confusion.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-backlog-duplicate-detection.md").write_text(
            "---\nname: backlog.py add implement duplicate detection\ndescription: Test\n"
            "metadata:\n  priority: P1\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: backlog-duplicate\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act — title differs by one word but is >80% similar
        result = runner.invoke(
            app,
            [
                "add",
                "--title",
                "backlog.py add implement fuzzy duplicate detection",
                "--priority",
                "P1",
                "--description",
                "Similar item",
            ],
        )

        # Assert
        assert result.exit_code == 1
        assert "Similar backlog items found" in result.output

    def test_add_force_bypasses_duplicate_check(self, mocker: MockerFixture) -> None:
        """Verify --force flag allows adding despite fuzzy duplicate.

        Tests: add command --force flag.
        How: Create existing item, add similar one with --force.
        Why: Users must be able to override when they know items are distinct.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-backlog-duplicate-force.md").write_text(
            "---\nname: backlog.py add implement duplicate detection\ndescription: Test\n"
            "metadata:\n  priority: P1\n  status: open\n"
            "  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: backlog-duplicate-force\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(
            app,
            [
                "add",
                "--title",
                "backlog.py add implement fuzzy duplicate detection",
                "--priority",
                "P1",
                "--description",
                "Intentional similar item",
                "--force",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Backlog item created" in result.output

    def test_add_no_duplicate_succeeds(self, mocker: MockerFixture) -> None:
        """Verify add succeeds when no fuzzy duplicates exist.

        Tests: add command happy path with duplicate check enabled.
        How: Add item with no similar existing items.
        Why: Duplicate check must not block unrelated items.
        """
        # Arrange
        mocker.patch.object(_mod, "_try_get_github", return_value=None)

        # Act
        result = runner.invoke(
            app, ["add", "--title", "Brand New Unique Item", "--priority", "P2", "--description", "Totally unique"]
        )

        # Assert
        assert result.exit_code == 0
        assert "Backlog item created" in result.output


# ─── T7: open PR check before close/resolve ───


class TestOpenPrCheckBeforeClose:
    """T7: Verify close/resolve check for open PRs before closing issues.

    Tests the _check_open_prs_for_issue function and its integration into
    close and resolve commands. Open PRs block closing unless --force is used.
    """

    def test_close_blocked_by_open_pr(self, mocker: MockerFixture) -> None:
        """Verify close exits with error when open PRs reference the issue.

        Tests: close command PR check integration.
        How: Mock _check_open_prs_for_issue to return a PR, attempt close.
        Why: Premature close orphans in-flight PRs.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-close-pr.md").write_text(
            "---\nname: Test close PR check\ndescription: Test\nmetadata:\n  issue: '#50'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-close-pr\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(
            _mod,
            "_check_open_prs_for_issue",
            return_value=[{"number": 55, "title": "Fix: implement feature", "url": "https://github.com/test/55"}],
        )

        # Act
        result = runner.invoke(app, ["close", "Test close PR check", "--reason", "duplicate", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 1
        assert "Open PRs reference issue #50" in result.output
        assert "PR #55" in result.output
        assert "--force to close anyway" in result.output

    def test_close_force_bypasses_pr_check(self, mocker: MockerFixture) -> None:
        """Verify --force allows close despite open PRs.

        Tests: close command --force flag with PR check.
        How: Mock open PR, close with --force.
        Why: Users must be able to override when they know PRs are stale.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-close-force.md").write_text(
            "---\nname: Test close force\ndescription: Test\nmetadata:\n  issue: '#60'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-close-force\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(
            _mod,
            "_check_open_prs_for_issue",
            return_value=[{"number": 65, "title": "WIP: feature", "url": "https://github.com/test/65"}],
        )
        mocker.patch.object(_mod, "_close_github_issue")

        # Act
        result = runner.invoke(
            app, ["close", "Test close force", "--reason", "duplicate", "--force", "-R", "test/repo"]
        )

        # Assert
        assert result.exit_code == 0
        assert "closed" in result.output.lower()

    def test_close_no_open_prs_succeeds(self, mocker: MockerFixture) -> None:
        """Verify close succeeds when no open PRs reference the issue.

        Tests: close command happy path with PR check.
        How: Mock _check_open_prs_for_issue returning empty list.
        Why: PR check must not block close when no PRs exist.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-close-ok.md").write_text(
            "---\nname: Test close ok\ndescription: Test\nmetadata:\n  issue: '#70'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-close-ok\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(_mod, "_check_open_prs_for_issue", return_value=[])
        mocker.patch.object(_mod, "_close_github_issue")

        # Act
        result = runner.invoke(app, ["close", "Test close ok", "--reason", "duplicate", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 0
        assert "closed" in result.output.lower()

    def test_close_no_issue_skips_pr_check(self, mocker: MockerFixture) -> None:
        """Verify close skips PR check when item has no GitHub issue.

        Tests: close command PR check skip for local-only items.
        How: Create item without issue number, attempt close.
        Why: Local-only items have no PRs to check.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-close-no-issue.md").write_text(
            "---\nname: Test close no issue\ndescription: Test\nmetadata:\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-close-no-issue\n---\n",
            encoding="utf-8",
        )
        mock_pr_check = mocker.patch.object(_mod, "_check_open_prs_for_issue")

        # Act
        result = runner.invoke(app, ["close", "Test close no issue", "--reason", "duplicate", "-R", "test/repo"])

        # Assert
        assert result.exit_code == 0
        mock_pr_check.assert_not_called()

    def test_resolve_blocked_by_open_pr(self, mocker: MockerFixture) -> None:
        """Verify resolve exits with error when open PRs reference the issue.

        Tests: resolve command PR check integration.
        How: Mock _check_open_prs_for_issue to return a PR, attempt resolve.
        Why: Resolving orphans in-flight PRs.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-resolve-pr.md").write_text(
            "---\nname: Test resolve PR check\ndescription: Test\nmetadata:\n  issue: '#80'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-resolve-pr\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(
            _mod,
            "_check_open_prs_for_issue",
            return_value=[{"number": 85, "title": "Fix: resolve feature", "url": "https://github.com/test/85"}],
        )

        # Act
        result = runner.invoke(
            app, ["resolve", "Test resolve PR check", "--summary", "No longer needed", "-R", "test/repo"]
        )

        # Assert
        assert result.exit_code == 1
        assert "Open PRs reference issue #80" in result.output
        assert "PR #85" in result.output
        assert "--force to resolve anyway" in result.output

    def test_resolve_force_bypasses_pr_check(self, mocker: MockerFixture) -> None:
        """Verify --force allows resolve despite open PRs.

        Tests: resolve command --force flag with PR check.
        How: Mock open PR, resolve with --force.
        Why: Users must be able to override.
        """
        # Arrange
        backlog_dir = _mod.BACKLOG_DIR
        (backlog_dir / "p1-test-resolve-force.md").write_text(
            "---\nname: Test resolve force\ndescription: Test\nmetadata:\n  issue: '#90'\n  priority: P1\n"
            "  status: open\n  source: test\n  added: '2026-01-01'\n  type: Feature\n  topic: test-resolve-force\n---\n",
            encoding="utf-8",
        )
        mocker.patch.object(
            _mod,
            "_check_open_prs_for_issue",
            return_value=[{"number": 95, "title": "WIP", "url": "https://github.com/test/95"}],
        )
        mocker.patch.object(_mod, "_resolve_github_issue")

        # Act
        result = runner.invoke(
            app, ["resolve", "Test resolve force", "--summary", "Stale", "--force", "-R", "test/repo"]
        )

        # Assert
        assert result.exit_code == 0
        assert "resolved" in result.output.lower()

    def test_check_open_prs_offline_returns_empty(self) -> None:
        """Verify _check_open_prs_for_issue returns empty list when offline.

        Tests: PR check graceful degradation.
        How: Call with no GITHUB_TOKEN set (empty string auth).
        Why: Offline agents must not be blocked by PR check failures.
        """
        # The function catches all exceptions and returns []
        result = _mod._check_open_prs_for_issue(999, "nonexistent/repo")
        assert result == []


# ─── T_pull_selector: pull with selector argument ───


class TestPullWithSelector:
    """Verify pull command accepts an optional selector argument.

    Tests the new selector parameter that routes to _pull_single_issue
    for a single issue instead of bulk pull.
    """

    def test_pull_with_issue_number_selector(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """pull #321 routes to pull_by_selector with the selector string.

        Tests: Issue number selector routing.
        How: Mock _backlog_operations.pull_by_selector, invoke pull with #321.
        Why: Users should be able to refresh a single issue without full bulk pull.
        """
        expected_path = tmp_path / "p2-test.md"
        mock_pull = mocker.patch.object(
            _mod._backlog_operations,
            "pull_by_selector",
            return_value={"file_path": str(expected_path), "messages": [], "warnings": []},
        )

        result = runner.invoke(app, ["pull", "#321", "-R", "test/repo"])

        assert result.exit_code == 0
        mock_pull.assert_called_once_with("#321", "test/repo")
        assert "Pulled" in result.output

    def test_pull_with_bare_number_selector(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """pull 42 (bare number) routes to pull_by_selector.

        Tests: Bare number selector routing.
        How: Mock _backlog_operations.pull_by_selector, invoke pull with bare number.
        Why: Bare numbers are a valid selector form for convenience.
        """
        expected_path = tmp_path / "p1-test.md"
        mock_pull = mocker.patch.object(
            _mod._backlog_operations,
            "pull_by_selector",
            return_value={"file_path": str(expected_path), "messages": [], "warnings": []},
        )

        result = runner.invoke(app, ["pull", "42", "-R", "test/repo"])

        assert result.exit_code == 0
        mock_pull.assert_called_once_with("42", "test/repo")

    def test_pull_with_title_selector_finds_item(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """pull 'some title' routes to pull_by_selector with the title string.

        Tests: Title substring selector routing.
        How: Mock _backlog_operations.pull_by_selector, invoke pull with title substring.
        Why: Users may not know the issue number and prefer title-based selection.
        """
        expected_path = tmp_path / "p2-some-title.md"
        mock_pull = mocker.patch.object(
            _mod._backlog_operations,
            "pull_by_selector",
            return_value={"file_path": str(expected_path), "messages": [], "warnings": []},
        )

        result = runner.invoke(app, ["pull", "some title", "-R", "test/repo"])

        assert result.exit_code == 0
        mock_pull.assert_called_once_with("some title", "test/repo")

    def test_pull_title_selector_no_match_exits_nonzero(self, mocker: MockerFixture) -> None:
        """pull with unmatched title selector exits with code 1 and prints error.

        Tests: Not-found error handling.
        How: Empty backlog dir, invoke pull with a title that matches nothing.
        Why: Unmatched selectors must not silently succeed.
        """
        mocker.patch.object(_mod, "_get_github", return_value=mocker.Mock())

        result = runner.invoke(app, ["pull", "nonexistent title", "-R", "test/repo"])

        assert result.exit_code == 1
        assert "No backlog item found" in result.output

    def test_pull_title_selector_item_without_issue_exits_nonzero(self, mocker: MockerFixture) -> None:
        """pull with title selector on item with no GitHub issue exits with code 1.

        Tests: Missing issue number error handling.
        How: Mock pull_by_selector to raise BacklogError for item without issue number.
        Why: Cannot pull from GitHub without a linked issue number.
        """
        mocker.patch.object(
            _mod._backlog_operations,
            "pull_by_selector",
            side_effect=_mod._BacklogError(
                "Item 'No issue item' has no linked GitHub issue. Use backlog_pull() for bulk pull."
            ),
        )

        result = runner.invoke(app, ["pull", "no issue", "-R", "test/repo"])

        assert result.exit_code == 1
        assert "has no linked GitHub issue" in result.output

    def test_pull_no_selector_uses_bulk_path(self, mocker: MockerFixture) -> None:
        """pull with no selector uses the existing bulk pull path (no _pull_single_issue call).

        Tests: Backward-compatible bulk pull.
        How: Mock _get_github and _pull_item, invoke pull without selector.
        Why: No-arg pull must remain unchanged.
        """
        mocker.patch.object(_mod, "_get_github", return_value=mocker.Mock())
        mocker.patch.object(_mod, "_pull_item", return_value=False)
        mocker.patch.object(_mod, "_sync_create_missing_issues")
        mock_single = mocker.patch.object(_mod, "_pull_single_issue")

        runner.invoke(app, ["pull", "-R", "test/repo"])

        mock_single.assert_not_called()
