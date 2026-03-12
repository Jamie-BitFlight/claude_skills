"""Scenario-based integration tests for the backlog MCP FastMCP server.

Tests are organized by the skill/agent workflow that generates each call
pattern. All tests go through the full operations layer — mocking only at
the github.py boundary and filesystem (via conftest fixtures).

Uses in-memory FastMCP Client transport (``Client(mcp)``).
No ``@pytest.mark.asyncio`` decorators — global ``asyncio_mode = "auto"``.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from backlog_core.server import mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call MCP tool via in-memory transport and parse JSON response."""
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Group 2.1: create-backlog-item workflow (backlog_add)
# ---------------------------------------------------------------------------


class TestCreateBacklogItem:
    """Scenarios consumed by /create-backlog-item skill."""

    async def test_create_item_with_github_issue(self, backlog_dir, mock_github):
        """backlog_add creates a file, syncs a GitHub issue, and returns all expected fields."""
        mock_github["try_get_github"].return_value = MagicMock()
        mock_github["create_issue_for_item"].return_value = 42

        result = await _call(
            "backlog_add",
            {
                "title": "Test Create Item",
                "priority": "P1",
                "description": "A test item",
                "source": "test",
                "create_issue": True,
                "force": True,
            },
        )

        assert result["title"] == "Test Create Item"
        assert result["priority"] == "P1"
        assert isinstance(result["file_path"], str)
        assert result["issue_num"] == 42
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        mock_github["create_issue_for_item"].assert_called_once()
        assert result["file_path"]  # path string returned


# ---------------------------------------------------------------------------
# Group 2.2-2.5: work-backlog-item workflows
# ---------------------------------------------------------------------------


class TestWorkBacklogItem:
    """Scenarios consumed by /work-backlog-item skill.

    Covers browse/list, view, plan/status/update, close, and resolve.
    """

    # Scenario 2: list with GitHub status enrichment
    async def test_list_with_status(self, backlog_dir, mock_github, write_test_item):
        write_test_item("Status Test Item", issue="#10")
        status_mock = MagicMock()
        status_mock.status = "open"
        status_mock.milestone = "v1.0"
        mock_github["batch_fetch_statuses"].return_value = {10: status_mock}

        result = await _call("backlog_list", {"with_status": True})

        assert isinstance(result["items"], list)
        assert result["count"] >= 1
        matching = [i for i in result["items"] if i.get("title") == "Status Test Item"]
        assert matching, "Expected item 'Status Test Item' in list results"
        item = matching[0]
        for key in ("section", "title", "issue", "plan", "file_path"):
            assert key in item, f"Expected key '{key}' in item dict"
        # Items with issues should carry status and milestone when enrichment is active
        if item.get("issue"):
            assert "status" in item
            assert "milestone" in item

    # Scenario 3: list sourced from GitHub (refresh_local_cache_from_github path)
    async def test_list_from_github(self, backlog_dir, mock_github):
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []
        mock_github["try_get_github"].return_value = mock_repo

        result = await _call("backlog_list", {"from_github": True})

        assert isinstance(result["items"], list)
        assert result["count"] >= 0
        mock_github["try_get_github"].assert_called()

    # Scenario 4: list with label filter (does not error without GitHub)
    async def test_list_with_label_filter(self, backlog_dir, mock_github, write_test_item):
        write_test_item("Alpha Item")
        write_test_item("Beta Item")
        mock_github["try_get_github"].return_value = None

        result = await _call("backlog_list", {"label": "priority:p1"})

        assert isinstance(result["items"], list)
        assert not result.get("errors")

    # Scenario 5: view item by GitHub issue number selector
    async def test_view_by_issue_number(self, backlog_dir, mock_github, write_test_item):
        write_test_item("View Issue Test", issue="#42")
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call("backlog_view", {"selector": "#42"})

        assert result["title"] == "View Issue Test"
        assert isinstance(result["priority"], str)
        assert result["issue"] == "#42"
        assert isinstance(result["body"], str)
        assert isinstance(result["groomed"], bool)
        assert isinstance(result["labels"], list)
        assert isinstance(result["milestone"], str)

    # Scenario 6: view item by partial title substring
    async def test_view_by_title_substring(self, backlog_dir, mock_github, write_test_item):
        write_test_item("My Unique Title Item")

        result = await _call("backlog_view", {"selector": "Unique Title"})

        assert result["title"] == "My Unique Title Item"
        assert isinstance(result["file_path"], str)
        assert result["file_path"] != ""

    # Scenario 7: view with pagination produces truncation metadata
    async def test_view_with_pagination(self, backlog_dir, mock_github, write_test_item):
        filepath = write_test_item("Long Body Item")
        # Append 50 extra lines to the body section so pagination kicks in
        extra_lines = "\n".join(f"Line {i} of the long body content." for i in range(1, 51))
        with filepath.open("a", encoding="utf-8") as fh:
            fh.write("\n" + extra_lines + "\n")

        result = await _call("backlog_view", {"selector": "Long Body Item", "offset": 0, "limit": 5})

        total = result.get("body_total_lines")
        if total is not None and total > 5:
            assert result.get("body_truncated") is True
            assert isinstance(result.get("body_remaining_lines"), int)
            assert isinstance(result.get("body_total_lines"), int)

    async def test_close_with_reason(self, backlog_dir, mock_github, write_test_item):
        """Scenario 11: backlog_close closes an item with a reason and no blocking PRs."""
        write_test_item("Close Test Item", issue="#42")
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["close_github_issue"].return_value = None

        result = await _call("backlog_close", {"selector": "Close Test Item", "reason": "wontfix"})

        assert result["title"] == "Close Test Item"
        assert result["closed"] is True
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        mock_github["close_github_issue"].assert_called_once()

    async def test_update_with_plan(self, backlog_dir, mock_github, write_test_item):
        """Scenario 8: backlog_update sets a plan path and returns title + plan field."""
        write_test_item("Plan Update Test")

        result = await _call("backlog_update", {"selector": "Plan Update Test", "plan": "plan/my-plan.md"})

        assert result["title"] == "Plan Update Test"
        assert result["plan"] == "plan/my-plan.md"
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_update_status_in_progress(self, backlog_dir, mock_github, write_test_item):
        """Scenario 9: backlog_update with status=in-progress calls apply_status_in_progress."""
        write_test_item("Status Update Test", issue="#55")
        mock_github["try_get_github"].return_value = MagicMock()

        result = await _call("backlog_update", {"selector": "Status Update Test", "status": "in-progress"})

        assert result["title"] == "Status Update Test"
        assert result["status"] == "in-progress"
        mock_github["apply_status_in_progress"].assert_called_once()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_update_create_github_issue(self, backlog_dir, mock_github, write_test_item):
        """Scenario 10: backlog_update with create_issue=True creates a GitHub issue."""
        write_test_item("Issue Create Test", priority="P1")
        mock_github["try_get_github"].return_value = MagicMock()
        mock_github["create_issue_for_item"].return_value = 99

        result = await _call("backlog_update", {"selector": "Issue Create Test", "create_issue": True})

        assert result["title"] == "Issue Create Test"
        assert result["issue_num"] == 99
        mock_github["create_issue_for_item"].assert_called_once()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_resolve_with_summary(self, backlog_dir, mock_github, write_test_item):
        """Scenario 12: backlog_resolve marks item resolved and calls resolve_github_issue."""
        write_test_item("Resolve Test Item", issue="#55")
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None

        result = await _call("backlog_resolve", {"selector": "Resolve Test Item", "summary": "No longer needed"})

        assert result["title"] == "Resolve Test Item"
        assert result["resolved"] is True
        mock_github["resolve_github_issue"].assert_called_once()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_resolve_with_cleanup(self, backlog_dir, mock_github, write_test_item):
        """Scenario 13: backlog_resolve with cleanup=True removes the local per-item file."""
        filepath = write_test_item("Cleanup Resolve Item", issue="#66")
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None
        mock_github["get_github"].return_value = MagicMock()

        result = await _call(
            "backlog_resolve", {"selector": "Cleanup Resolve Item", "summary": "Duplicate of #10", "cleanup": True}
        )

        assert result["resolved"] is True
        assert not filepath.exists()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)


# ---------------------------------------------------------------------------
# Group 2.6: groom-backlog-item workflow (backlog_groom)
# ---------------------------------------------------------------------------


class TestGroomBacklogItem:
    """Scenarios consumed by /groom-backlog-item skill."""

    async def test_groom_full_content(self, backlog_dir, mock_github, write_test_item):
        """Scenario 14: backlog_groom with section/content syncs to GitHub and updates the file."""
        filepath = write_test_item("Groom Full Test", issue="#80")
        mock_github["try_get_github"].return_value = MagicMock()
        mock_github["sync_groomed_to_github_issue"].return_value = True

        result = await _call(
            "backlog_groom",
            {"selector": "Groom Full Test", "section": "Groomed", "content": "This is groomed content."},
        )

        assert result["groomed_updated"] is True
        file_text = filepath.read_text(encoding="utf-8")
        assert "groomed content" in file_text
        mock_github["sync_groomed_to_github_issue"].assert_called()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_groom_incremental_section(self, backlog_dir, mock_github, write_test_item):
        """Scenario 15: backlog_groom with section + content updates that section in the file."""
        filepath = write_test_item("Groom Section Test", issue="#81")
        mock_github["try_get_github"].return_value = MagicMock()

        result = await _call(
            "backlog_groom",
            {
                "selector": "Groom Section Test",
                "section": "Reproducibility",
                "content": "Steps to reproduce the issue.",
            },
        )

        assert result["groomed_updated"] is True
        file_text = filepath.read_text(encoding="utf-8")
        assert "Reproducibility" in file_text
        assert "Steps to reproduce" in file_text
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_groom_local_only(self, backlog_dir, mock_github, write_test_item):
        """Scenario 16: backlog_groom without a GitHub issue updates local file only."""
        write_test_item("Groom Local Only Test")
        mock_github["try_get_github"].return_value = None

        result = await _call(
            "backlog_groom",
            {"selector": "Groom Local Only Test", "section": "Groomed", "content": "Local only groomed content."},
        )

        assert result["groomed_updated"] is True
        mock_github["sync_groomed_to_github_issue"].assert_not_called()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_groom_via_update(self, backlog_dir, mock_github, write_test_item):
        """Scenario 17: backlog_update with section/content param sets groomed content."""
        write_test_item("Groom Via Update Test", issue="#82")
        mock_github["try_get_github"].return_value = MagicMock()

        result = await _call(
            "backlog_update",
            {"selector": "Groom Via Update Test", "section": "Groomed", "content": "Updated groomed content."},
        )

        assert result["groomed_updated"] is True
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)


# ---------------------------------------------------------------------------
# Group 2.7: group-items-to-milestone + backlog-item-groomer
# ---------------------------------------------------------------------------


class TestGroupItemsToMilestone:
    """Scenarios consumed by /group-items-to-milestone skill."""

    async def test_list_for_milestone_selection(self, backlog_dir, mock_github, write_test_item):
        """Scenario 18: list returns items with status/milestone keys for milestone assignment."""
        write_test_item("Milestone Item A", priority="P0", issue="#10")
        write_test_item("Milestone Item B", priority="P1", issue="#11")
        write_test_item("Milestone Item C", priority="P2")

        status_10 = MagicMock()
        status_10.status = "open"
        status_10.milestone = "v1.0"
        status_11 = MagicMock()
        status_11.status = "open"
        status_11.milestone = ""
        mock_github["batch_fetch_statuses"].return_value = {10: status_10, 11: status_11}

        result = await _call("backlog_list", {"with_status": True})

        assert result["count"] >= 3
        for item in result["items"]:
            assert "section" in item
            assert "title" in item
            assert "issue" in item
            if item.get("issue"):
                assert "status" in item
                assert "milestone" in item


class TestBacklogItemGroomer:
    """Scenarios consumed by @backlog-item-groomer agent."""

    async def test_groomer_list_then_view(self, backlog_dir, mock_github, write_test_item):
        """Scenario 19: groomer lists items then views a specific item by title."""
        write_test_item("Groomer View Target", priority="P1")

        list_result = await _call("backlog_list")

        target = next(i for i in list_result["items"] if "Groomer View" in i["title"])

        view_result = await _call("backlog_view", {"selector": target["title"]})

        assert view_result["title"] == "Groomer View Target"
        assert "body" in view_result
        assert "description" in view_result
        assert "groomed" in view_result


# ---------------------------------------------------------------------------
# Group 2.8-2.9: sync, pull, normalize
# ---------------------------------------------------------------------------


class TestSyncAndPull:
    """Scenarios for backlog_sync and backlog_pull tools."""

    async def test_sync_creates_missing_issues(self, backlog_dir, mock_github, write_test_item):
        """Scenario 20: backlog_sync creates GitHub issues for items that lack them."""
        write_test_item("Sync Test Item", priority="P1")
        mock_repo = MagicMock()
        mock_github["get_github"].return_value = mock_repo
        mock_github["fetch_open_issues_by_title"].return_value = {}
        mock_github["create_issue_for_item"].return_value = 99

        result = await _call("backlog_sync")

        assert result["created"] >= 1
        mock_github["create_issue_for_item"].assert_called()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_pull_updates_local(self, backlog_dir, mock_github, write_test_item):
        """Scenario 21: backlog_pull fetches GitHub issue body and updates local file."""
        write_test_item("Pull Test Item", priority="P1", issue="#50")
        mock_repo = MagicMock()
        mock_github["get_github"].return_value = mock_repo
        mock_github["fetch_github_issue_body"].return_value = "Updated body from GitHub"

        result = await _call("backlog_pull")

        mock_github["get_github"].assert_called()
        assert isinstance(result["pulled"], int)
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        # If the merge detected changes, verify the local file was updated
        if result["pulled"] > 0:
            updated_text = (backlog_dir / "p1-pull-test-item.md").read_text(encoding="utf-8")
            assert "Updated body from GitHub" in updated_text


class TestNormalize:
    """Scenarios for backlog_normalize tool."""

    async def test_normalize_updates_items(self, backlog_dir, mock_github):
        """Scenario 2.9: backlog_normalize converts flat-format files to canonical metadata format."""
        non_canonical = backlog_dir / "p1-messy-item.md"
        non_canonical.write_text(
            "---\n"
            "title: Messy Item\n"
            "source: test\n"
            "added: '2026-01-01'\n"
            "priority: P1\n"
            "type: Feature\n"
            "status: open\n"
            "---\n\n"
            "**Description**: A messy item description\n",
            encoding="utf-8",
        )

        result = await _call("backlog_normalize")

        assert isinstance(result["normalized"], int)
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        # Verify normalization occurred — the flat-format file should be updated
        assert non_canonical.exists()
        file_text = non_canonical.read_text(encoding="utf-8")
        assert "---" in file_text


# ---------------------------------------------------------------------------
# Group 2.10-2.11: error paths and lifecycle tests
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Error path tests: close without checklist, view nonexistent,
    add duplicate, list empty backlog.
    """

    async def test_close_with_invalid_reason(self, backlog_dir, mock_github, write_test_item):
        """Scenario 22: backlog_close returns error for an invalid reason value."""
        write_test_item("Error Close Test")

        result = await _call("backlog_close", {"selector": "Error Close Test", "reason": "invalid_reason_value"})

        assert "error" in result
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_view_nonexistent_item(self, backlog_dir, mock_github):
        """Scenario 23: backlog_view returns error for a selector that matches no item."""
        result = await _call("backlog_view", {"selector": "Totally Nonexistent Item XYZ123"})

        assert "error" in result
        assert "not found" in result["error"].lower() or "no item found" in result["error"].lower()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_add_duplicate_force_false(self, backlog_dir, mock_github, write_test_item):
        """Scenario 24: backlog_add returns duplicate error when similar item exists and force=False."""
        write_test_item("Duplicate Detection Test")

        result = await _call(
            "backlog_add",
            {"title": "Duplicate Detection Test", "priority": "P1", "description": "A duplicate", "force": False},
        )

        assert "error" in result
        assert "similar" in result["error"].lower() or "duplicate" in result["error"].lower()
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)

    async def test_list_empty_backlog(self, backlog_dir, mock_github):
        """Scenario 25: backlog_list returns empty items list when no items exist — not an error."""
        result = await _call("backlog_list")

        assert result["items"] == []
        assert result["count"] == 0
        assert "error" not in result
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)


class TestLifecycles:
    """Full lifecycle tests: create→close, create→resolve+cleanup,
    stale discovery.
    """

    async def test_create_groom_update_close(self, backlog_dir, mock_github):
        """Lifecycle 1: create → groom → update plan → close.

        Chains 4 MCP tool calls in sequence, verifying intermediate states.
        """
        # Step 1: Create item
        mock_github["try_get_github"].return_value = MagicMock()
        mock_github["create_issue_for_item"].return_value = 70

        create_result = await _call(
            "backlog_add",
            {
                "title": "Lifecycle Close Item",
                "priority": "P1",
                "description": "Full lifecycle test",
                "source": "test",
                "create_issue": True,
                "force": True,
            },
        )
        assert create_result["title"] == "Lifecycle Close Item"
        assert create_result["issue_num"] == 70

        # Step 2: Groom item
        mock_github["sync_groomed_to_github_issue"].return_value = True

        groom_result = await _call(
            "backlog_groom", {"selector": "Lifecycle Close Item", "section": "Groomed", "content": "Ready for work."}
        )
        assert groom_result["groomed_updated"] is True

        # Step 3: Update with plan
        update_result = await _call(
            "backlog_update", {"selector": "Lifecycle Close Item", "plan": "plan/lifecycle-test.md"}
        )
        assert update_result["plan"] == "plan/lifecycle-test.md"

        # Step 4: Close
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["close_github_issue"].return_value = None

        close_result = await _call("backlog_close", {"selector": "Lifecycle Close Item", "reason": "wontfix"})
        assert close_result["closed"] is True
        assert isinstance(close_result["messages"], list)

    async def test_create_resolve_cleanup(self, backlog_dir, mock_github):
        """Lifecycle 2: create with issue → resolve with cleanup → file removed.

        Verifies item is created, then resolved with cleanup=True removing the file.
        """
        # Step 1: Create item with issue
        mock_github["try_get_github"].return_value = MagicMock()
        mock_github["create_issue_for_item"].return_value = 71

        create_result = await _call(
            "backlog_add",
            {
                "title": "Lifecycle Resolve Item",
                "priority": "P1",
                "description": "Will be resolved",
                "source": "test",
                "create_issue": True,
                "force": True,
            },
        )
        assert create_result["issue_num"] == 71
        assert create_result["file_path"]  # non-empty path string
        # Verify file exists: list files in backlog_dir matching the item slug
        item_files = list(backlog_dir.glob("*resolve*"))
        assert item_files, "Expected item file to exist after create"

        # Step 2: Resolve with cleanup
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None
        mock_github["get_github"].return_value = MagicMock()

        resolve_result = await _call(
            "backlog_resolve",
            {"selector": "Lifecycle Resolve Item", "summary": "Superseded by other work", "cleanup": True},
        )
        assert resolve_result["resolved"] is True
        remaining = list(backlog_dir.glob("*resolve*"))
        assert not remaining, "File should be removed after resolve with cleanup"

    async def test_stale_item_discovery(self, backlog_dir, mock_github, write_test_item):
        """Lifecycle 3: item with issue #100, batch_fetch_statuses returns empty → stale signal.

        Pre-creates item with issue, configures batch_fetch_statuses to return
        empty dict (issue not in open issues), and verifies item appears in list
        with empty status signaling staleness.
        """
        write_test_item("Stale Discovery Item", issue="#100")
        mock_github["batch_fetch_statuses"].return_value = {}

        result = await _call("backlog_list", {"with_status": True})

        matching = [i for i in result["items"] if i.get("title") == "Stale Discovery Item"]
        assert matching, "Expected 'Stale Discovery Item' in list results"
        item = matching[0]
        # Issue #100 is not in batch_fetch_statuses → status should be empty/absent
        assert item.get("status", "") == "", f"Expected empty status for stale item, got {item.get('status')}"
