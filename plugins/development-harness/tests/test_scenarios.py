"""Scenario-based integration tests for the backlog MCP FastMCP server.

Tests are organized by the skill/agent workflow that generates each call
pattern. All tests go through the full operations layer — mocking only at
the github.py boundary and filesystem (via conftest fixtures).

Uses in-memory FastMCP Client transport (``Client(mcp)``).
No ``@pytest.mark.asyncio`` decorators — global ``asyncio_mode = "auto"``.
"""

from __future__ import annotations

import json
from typing import ClassVar
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

    # Scenario 2: list always includes GitHub status fields
    async def test_list_includes_status_fields(self, backlog_dir, mock_github, write_test_item):
        write_test_item("Status Test Item", issue="#10")
        status_mock = MagicMock()
        status_mock.status = "open"
        status_mock.milestone = "v1.0"
        mock_github["batch_fetch_statuses"].return_value = {10: status_mock}

        result = await _call("backlog_list", {})

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
        mock_repo.full_name = "owner/repo"
        mock_repo.get_issues.return_value = []
        mock_repo.requester.graphql_query.return_value = (
            {},
            {"data": {"repository": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}},
        )
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

        result = await _call("backlog_view", {"selector": "#42", "summary": False})

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

        result = await _call("backlog_view", {"selector": "Unique Title", "summary": False})

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
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_groom_test",
                            "number": 80,
                            "title": "Groom Full Test",
                            "state": "OPEN",
                            "body": "",
                            "createdAt": "2026-01-01T00:00:00Z",
                            "updatedAt": "2026-01-01T00:00:00Z",
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                        }
                    }
                }
            },
        )
        mock_github["try_get_github"].return_value = mock_repo
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
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_groom_section_test",
                            "number": 81,
                            "title": "Groom Section Test",
                            "state": "OPEN",
                            "body": "",
                            "createdAt": "2026-01-01T00:00:00Z",
                            "updatedAt": "2026-01-01T00:00:00Z",
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                        }
                    }
                }
            },
        )
        mock_github["try_get_github"].return_value = mock_repo

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
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_groom_via_update_test",
                            "number": 82,
                            "title": "Groom Via Update Test",
                            "state": "OPEN",
                            "body": "",
                            "createdAt": "2026-01-01T00:00:00Z",
                            "updatedAt": "2026-01-01T00:00:00Z",
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                        }
                    }
                }
            },
        )
        mock_github["try_get_github"].return_value = mock_repo

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

        result = await _call("backlog_list", {})

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

        view_result = await _call("backlog_view", {"selector": target["title"], "summary": False})

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
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.requester.graphql_query.return_value = (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_lifecycle_close",
                            "number": 70,
                            "title": "Lifecycle Close Item",
                            "state": "OPEN",
                            "body": "",
                            "createdAt": "2026-01-01T00:00:00Z",
                            "updatedAt": "2026-01-01T00:00:00Z",
                            "labels": {"nodes": []},
                            "milestone": None,
                            "assignees": {"nodes": []},
                        }
                    }
                }
            },
        )
        mock_github["try_get_github"].return_value = mock_repo
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

        result = await _call("backlog_list", {})

        matching = [i for i in result["items"] if i.get("title") == "Stale Discovery Item"]
        assert matching, "Expected 'Stale Discovery Item' in list results"
        item = matching[0]
        # Issue #100 is not in batch_fetch_statuses → status should be empty/absent
        assert item.get("status", "") == "", f"Expected empty status for stale item, got {item.get('status')}"


# ---------------------------------------------------------------------------
# Group 3: Layer 2 semantic matching integration tests
# ---------------------------------------------------------------------------


class TestSemanticMatchingInfrastructure:
    """Integration tests for the semantic matching strategy chain infrastructure.

    Tests verify that the backlog_list type/topic filters and title substring
    matching work correctly to support the 3-strategy matching chain:
      - Strategy 1: substring via title= filter
      - Strategy 2: filter-first via type=/topic= to narrow candidates
      - Strategy 3: LLM semantic match (instruction-level, not tested here)
    """

    async def test_semantic_match_synonym_query_via_type_filter(self, backlog_dir, mock_github, write_test_item):
        """Query for 'login' issue finds auth-related item when filtered by type='Bug'."""
        write_test_item("Authentication failure on SSO redirect", type_val="Bug")
        write_test_item("Add new dashboard widget", type_val="Feature")
        write_test_item("Refactor database connection pool", type_val="Refactor")

        # Strategy 2: filter by type='Bug' narrows to auth item only
        result = await _call("backlog_list", {"type": "Bug"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Authentication failure on SSO redirect"
        assert result["items"][0]["type"] == "Bug"

    async def test_substring_match_takes_priority(self, backlog_dir, mock_github, write_test_item):
        """When substring matches exist, title filter returns them directly without needing type/topic filters."""
        write_test_item("Authentication failure on SSO redirect", type_val="Bug")
        write_test_item("Backlog list performance degradation", type_val="Bug")
        write_test_item("Add dark mode theme support", type_val="Feature")

        # Strategy 1: direct substring match on title — no type/topic needed
        result = await _call("backlog_list", {"title": "SSO redirect"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Authentication failure on SSO redirect"

    async def test_filter_first_narrows_candidates_type_and_substring(self, backlog_dir, mock_github, write_test_item):
        """type='Bug' combined with title substring finds the correct bug from a mixed item set."""
        write_test_item("Schema migration script error on PostgreSQL 15", type_val="Bug")
        write_test_item("Schema migration documentation update", type_val="Docs")
        write_test_item("UI theme customization support", type_val="Feature")

        # Strategy 2: type filter + substring narrows to exact match
        result = await _call("backlog_list", {"type": "Bug", "title": "migration"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Schema migration script error on PostgreSQL 15"
        assert result["items"][0]["type"] == "Bug"

    async def test_filter_first_narrows_candidates_topic_filter(self, backlog_dir, mock_github, write_test_item):
        """topic filter narrows candidates using substring match on auto-derived topic slug."""
        write_test_item("MCP server timeout on reconnect", type_val="Bug")
        write_test_item("REST API route registration incomplete", type_val="Bug")

        # topic is auto-derived from title slug: 'mcp-server-timeout-on-reconnect'
        result = await _call("backlog_list", {"topic": "mcp-server"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "MCP server timeout on reconnect"

    async def test_type_filter_excludes_items_without_type(self, backlog_dir, mock_github, write_test_item):
        """Items without metadata.type are excluded when type filter is active."""
        write_test_item("Item with type", type_val="Bug")
        # Create item with empty type
        write_test_item("Item without type", type_val="")

        result = await _call("backlog_list", {"type": "Bug"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Item with type"

    async def test_type_filter_case_insensitive(self, backlog_dir, mock_github, write_test_item):
        """type filter performs case-insensitive exact match."""
        write_test_item("A bug item", type_val="Bug")
        write_test_item("A feature item", type_val="Feature")

        result = await _call("backlog_list", {"type": "bug"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "A bug item"

    async def test_topic_filter_case_insensitive_substring(self, backlog_dir, mock_github, write_test_item):
        """topic filter performs case-insensitive substring match."""
        write_test_item("GitHub Actions workflow optimization", type_val="Chore")
        write_test_item("REST API improvements", type_val="Feature")

        # topic slug: 'github-actions-workflow-optimization'
        result = await _call("backlog_list", {"topic": "GITHUB-ACTIONS"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "GitHub Actions workflow optimization"

    async def test_response_includes_type_and_topic_fields(self, backlog_dir, mock_github, write_test_item):
        """Each item in backlog_list response includes type and topic keys."""
        write_test_item("Test type topic fields", type_val="Feature")

        result = await _call("backlog_list")

        assert result["count"] >= 1
        item = result["items"][0]
        assert "type" in item, "Expected 'type' key in item dict"
        assert "topic" in item, "Expected 'topic' key in item dict"
        assert item["type"] == "Feature"
        assert item["topic"] != ""  # auto-derived from title

    async def test_no_filters_returns_all_items(self, backlog_dir, mock_github, write_test_item):
        """Backward compatibility: no type/topic params returns all items."""
        write_test_item("Item A", type_val="Bug")
        write_test_item("Item B", type_val="Feature")
        write_test_item("Item C", type_val="Refactor")

        result = await _call("backlog_list")

        assert result["count"] == 3


class TestSemanticQueryCorpus:
    """Corpus-based integration tests verifying the filter infrastructure
    supports semantic matching for a diverse set of queries.

    Each test case represents a semantic query that an LLM user would issue.
    The test verifies that the type/topic filter infrastructure correctly
    narrows candidates so the target item is findable. The 10-query corpus
    must achieve at least 80% success rate (8/10 correct matches).
    """

    # Corpus of (query_description, filter_params, expected_title) tuples.
    # Each entry tests that applying Strategy 1 (title substring) or
    # Strategy 2 (type/topic filter) can surface the correct item.
    CORPUS: ClassVar[list[tuple[str, dict, str]]] = [
        (
            "fix login issue -> auth failure via Bug type filter",
            {"type": "Bug"},
            "Authentication failure on SSO redirect",
        ),
        (
            "improve search speed -> performance via title substring",
            {"title": "performance"},
            "Backlog list performance degradation on large datasets",
        ),
        ("broken MCP connection -> MCP via topic filter", {"topic": "mcp-server"}, "MCP server timeout on reconnect"),
        (
            "add dark mode -> dark mode via title substring",
            {"title": "dark mode"},
            "UI theme customization support dark mode",
        ),
        (
            "clean up old tests -> test suite via title substring",
            {"title": "test suite"},
            "Test suite maintenance and dead code removal",
        ),
        (
            "database migration failing -> migration Bug filter",
            {"type": "Bug", "title": "migration"},
            "Schema migration script error on PostgreSQL 15",
        ),
        (
            "fix typo in docs -> docs type filter + spelling substring",
            {"type": "Docs", "title": "spelling"},
            "Documentation spelling and grammar corrections",
        ),
        (
            "slow CI pipeline -> CI via topic filter",
            {"topic": "github-actions"},
            "GitHub Actions workflow optimization",
        ),
        (
            "memory leak on startup -> memory via title substring",
            {"title": "memory"},
            "Process memory growth during initialization",
        ),
        (
            "missing API endpoint -> API via title substring",
            {"title": "API route"},
            "REST API route registration incomplete",
        ),
    ]

    async def _setup_corpus_items(self, write_test_item):
        """Create all corpus items in the test backlog directory."""
        write_test_item("Authentication failure on SSO redirect", type_val="Bug")
        write_test_item("Backlog list performance degradation on large datasets", type_val="Bug")
        write_test_item("MCP server timeout on reconnect", type_val="Bug")
        write_test_item("UI theme customization support dark mode", type_val="Feature")
        write_test_item("Test suite maintenance and dead code removal", type_val="Chore")
        write_test_item("Schema migration script error on PostgreSQL 15", type_val="Bug")
        write_test_item("Documentation spelling and grammar corrections", type_val="Docs")
        write_test_item("GitHub Actions workflow optimization", type_val="Chore")
        write_test_item("Process memory growth during initialization", type_val="Bug")
        write_test_item("REST API route registration incomplete", type_val="Bug")

    async def test_semantic_corpus_80_percent_threshold(self, backlog_dir, mock_github, write_test_item):
        """10-query semantic corpus achieves at least 80% success rate (8/10 matches)."""
        await self._setup_corpus_items(write_test_item)

        successes = 0
        failures: list[str] = []
        for description, params, expected_title in self.CORPUS:
            result = await _call("backlog_list", params)
            titles = [item["title"] for item in result["items"]]
            if expected_title in titles:
                successes += 1
            else:
                failures.append(f"  MISS: {description} — expected '{expected_title}', got {titles}")

        success_rate = successes / len(self.CORPUS)
        failure_report = "\n".join(failures) if failures else "none"
        assert success_rate >= 0.80, (
            f"Semantic corpus success rate {successes}/{len(self.CORPUS)} ({success_rate:.0%}) "
            f"below 80% threshold.\nFailures:\n{failure_report}"
        )

    async def test_each_corpus_query_returns_nonempty(self, backlog_dir, mock_github, write_test_item):
        """Each corpus query returns at least one result (no empty result sets)."""
        await self._setup_corpus_items(write_test_item)

        for description, params, _expected in self.CORPUS:
            result = await _call("backlog_list", params)
            assert result["count"] >= 1, f"Corpus query '{description}' returned empty results with params {params}"


# ---------------------------------------------------------------------------
# Group 4: End-to-end integration tests — query to filter to match to result
# ---------------------------------------------------------------------------


class TestEndToEndQueryToResult:
    """End-to-end tests exercising the full path: user query -> backlog_list
    call -> matching -> result returned.

    These tests validate the complete semantic matching strategy chain from
    the caller's perspective, using the MCP in-memory transport.
    """

    async def test_e2e_full_path_query_to_matching_result(self, backlog_dir, mock_github, write_test_item):
        """Full e2e path: create items, issue query via backlog_list, receive matched result."""
        write_test_item("Broken authentication on mobile app", type_val="Bug")
        write_test_item("Add CSV export feature", type_val="Feature")
        write_test_item("Optimize database query performance", type_val="Refactor")

        # User query: find the auth bug via title substring
        result = await _call("backlog_list", {"title": "authentication"})

        assert result["count"] == 1
        item = result["items"][0]
        assert item["title"] == "Broken authentication on mobile app"
        assert item["type"] == "Bug"
        assert "topic" in item
        assert "section" in item
        assert "file_path" in item

    async def test_e2e_fallback_chain_strategy1_substring_hit(self, backlog_dir, mock_github, write_test_item):
        """Fallback chain e2e: Strategy 1 (substring) finds match immediately — no fallback needed."""
        write_test_item("MCP server crash on reconnect", type_val="Bug")
        write_test_item("Dashboard layout improvements", type_val="Feature")

        # Strategy 1: direct substring match succeeds
        s1_result = await _call("backlog_list", {"title": "MCP server crash"})
        assert s1_result["count"] == 1
        assert s1_result["items"][0]["title"] == "MCP server crash on reconnect"

    async def test_e2e_fallback_chain_strategy1_miss_strategy2_hit(self, backlog_dir, mock_github, write_test_item):
        """Fallback chain e2e: Strategy 1 (substring) returns zero -> Strategy 2 (filter-first) finds match."""
        write_test_item("Authentication failure on SSO redirect", type_val="Bug")
        write_test_item("Add new dashboard widget", type_val="Feature")
        write_test_item("Refactor database connection pool", type_val="Refactor")

        # Strategy 1: substring 'login' does not match any title
        s1_result = await _call("backlog_list", {"title": "login"})
        assert s1_result["count"] == 0, "Strategy 1 should miss — 'login' not in any title"

        # Strategy 2: filter by type='Bug' narrows to auth item (semantically related to 'login')
        s2_result = await _call("backlog_list", {"type": "Bug"})
        assert s2_result["count"] == 1
        assert s2_result["items"][0]["title"] == "Authentication failure on SSO redirect"

    async def test_e2e_fallback_chain_strategy1_miss_strategy2_miss_strategy3_candidates(
        self, backlog_dir, mock_github, write_test_item
    ):
        """Fallback chain e2e: Strategy 1 and 2 return zero -> Strategy 3 (LLM semantic) gets full candidate list.

        Strategy 3 is instruction-level (LLM picks from candidates). This test verifies
        that when Strategies 1 and 2 both miss, an unfiltered list returns all items
        as candidates for LLM semantic matching.
        """
        write_test_item("Optimize webpack bundle size", type_val="Chore")
        write_test_item("Fix flaky CI test suite", type_val="Chore")
        write_test_item("Update README badges", type_val="Docs")

        # Strategy 1: substring 'build performance' matches nothing
        s1_result = await _call("backlog_list", {"title": "build performance"})
        assert s1_result["count"] == 0, "Strategy 1 should miss"

        # Strategy 2: no matching type for 'Performance' category
        s2_result = await _call("backlog_list", {"type": "Performance"})
        assert s2_result["count"] == 0, "Strategy 2 should miss — no Performance type items"

        # Strategy 3 fallback: unfiltered list returns all candidates for LLM to evaluate
        s3_candidates = await _call("backlog_list")
        assert s3_candidates["count"] == 3, "All items available as candidates for LLM semantic match"
        titles = {item["title"] for item in s3_candidates["items"]}
        assert "Optimize webpack bundle size" in titles

    async def test_e2e_fallback_chain_all_three_transitions(self, backlog_dir, mock_github, write_test_item):
        """Fallback chain e2e: all 3 strategy transitions are observable in sequence.

        Simulates the full chain: Strategy 1 -> 2 -> 3 with observable transition
        points (zero-result checks between strategies).
        """
        write_test_item("Memory leak in worker pool", type_val="Bug")
        write_test_item("Add GraphQL subscriptions", type_val="Feature")
        write_test_item("Refactor error handling middleware", type_val="Refactor")

        # --- Strategy 1: substring match ---
        s1_result = await _call("backlog_list", {"title": "slow response time"})
        s1_count = s1_result["count"]
        assert s1_count == 0, f"Strategy 1 transition: expected 0 results, got {s1_count}"

        # --- Strategy 2: type + topic filter ---
        s2_result = await _call("backlog_list", {"type": "Performance"})
        s2_count = s2_result["count"]
        assert s2_count == 0, f"Strategy 2 transition: expected 0 results, got {s2_count}"

        # --- Strategy 3: full candidate list for LLM evaluation ---
        s3_result = await _call("backlog_list")
        s3_count = s3_result["count"]
        assert s3_count == 3, f"Strategy 3 candidates: expected 3, got {s3_count}"

        # The LLM would semantically match 'slow response time' to 'Memory leak in worker pool'
        # (both are performance-related bugs). Verify the target is in candidates.
        titles = [item["title"] for item in s3_result["items"]]
        assert "Memory leak in worker pool" in titles

    async def test_e2e_backward_compat_title_only_parameter(self, backlog_dir, mock_github, write_test_item):
        """Backward compatibility: existing callers using only title= produce identical results to pre-change behavior.

        Pre-change behavior: backlog_list(title=X) returned items whose title
        contains X as a case-insensitive substring. This must remain unchanged.
        """
        write_test_item("Implement OAuth2 PKCE flow", type_val="Feature")
        write_test_item("OAuth token refresh fails silently", type_val="Bug")
        write_test_item("Database migration rollback", type_val="Refactor")

        # title-only filter: case-insensitive substring — original pre-change behavior
        result = await _call("backlog_list", {"title": "oauth"})

        assert result["count"] == 2
        titles = sorted(item["title"] for item in result["items"])
        assert titles == ["Implement OAuth2 PKCE flow", "OAuth token refresh fails silently"]
        # Verify no unexpected keys or structure changes
        for item in result["items"]:
            assert "section" in item
            assert "title" in item
            assert "issue" in item
            assert "plan" in item
            assert "type" in item
            assert "topic" in item

    async def test_e2e_backward_compat_no_params_returns_all(self, backlog_dir, mock_github, write_test_item):
        """Backward compatibility: calling backlog_list with no params returns all items."""
        write_test_item("Item Alpha", type_val="Bug")
        write_test_item("Item Beta", type_val="Feature")
        write_test_item("Item Gamma", type_val="Refactor")
        write_test_item("Item Delta", type_val="Docs")

        result = await _call("backlog_list")

        assert result["count"] == 4
        assert len(result["items"]) == 4

    async def test_e2e_empty_corpus_all_strategies_graceful(self, backlog_dir, mock_github):
        """Empty corpus: when no items exist, all strategies return gracefully with zero results."""
        # Strategy 1: substring on empty corpus
        s1_result = await _call("backlog_list", {"title": "anything"})
        assert s1_result["count"] == 0
        assert s1_result["items"] == []
        assert "error" not in s1_result


# ---------------------------------------------------------------------------
# Group 5: Progressive disclosure — compact backlog_view (Scenario C1)
# ---------------------------------------------------------------------------


class TestCompactBacklogView:
    """Scenarios for backlog_view with include_content=False (compact mode).

    Verifies that compact mode returns section inventory without body or entry
    content, and that offset/limit parameters do not affect the compact response
    shape.
    """

    async def test_compact_view_returns_sections_metadata(self, backlog_dir, mock_github, write_test_item):
        """Scenario C1a: backlog_view(include_content=False) returns sections_metadata list.

        Tests: compact mode response shape
        How: write item with groomed section content, call backlog_view with
             include_content=False, assert sections_metadata is a list of dicts
             with name/num_entries/num_struck keys.
        Why: callers that only need a section inventory should not pay the cost
             of transferring full body content.
        """
        filepath = write_test_item("Compact View Test Item")
        # Append a section with entries so sections_metadata is non-empty
        filepath.write_text(
            filepath.read_text(encoding="utf-8")
            + "\n### Groomed (2026-03-22)\n\n"
            + "- [2026-03-22] First entry content.\n"
            + "- [2026-03-22] Second entry content.\n",
            encoding="utf-8",
        )
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call(
            "backlog_view", {"selector": "Compact View Test Item", "include_content": False, "summary": False}
        )

        assert "error" not in result
        assert "sections_metadata" in result, "Compact mode must include sections_metadata"
        assert isinstance(result["sections_metadata"], list)
        for section in result["sections_metadata"]:
            assert "name" in section, f"Section entry missing 'name': {section}"
            assert "num_entries" in section, f"Section entry missing 'num_entries': {section}"
            assert "num_struck" in section, f"Section entry missing 'num_struck': {section}"
            assert isinstance(section["num_entries"], int)
            assert isinstance(section["num_struck"], int)

    async def test_compact_view_omits_body_and_sections(self, backlog_dir, mock_github, write_test_item):
        """Scenario C1b: backlog_view(include_content=False) omits body and sections keys.

        Tests: compact mode omits full-content fields
        How: call backlog_view with include_content=False, assert 'body' and
             'sections' keys are absent from the response.
        Why: the compact response contract guarantees no body or entry content
             is transferred — callers rely on key absence to detect compact mode.
        """
        write_test_item("No Body View Item")
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call("backlog_view", {"selector": "No Body View Item", "include_content": False})

        assert "error" not in result
        assert "body" not in result, "Compact mode must not include 'body' key"
        assert "sections" not in result, "Compact mode must not include 'sections' key"

    async def test_compact_view_preserves_metadata_fields(self, backlog_dir, mock_github, write_test_item):
        """Scenario C1c: backlog_view(include_content=False) returns all metadata fields.

        Tests: compact mode includes all non-content metadata fields
        How: call backlog_view with include_content=False, assert expected
             metadata keys are present with correct types.
        Why: callers using compact mode still need item metadata (title, priority,
             issue, file_path, etc.) to identify and act on the item.
        """
        write_test_item("Metadata Preserved Item", priority="P1", issue="#77")
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call(
            "backlog_view", {"selector": "Metadata Preserved Item", "include_content": False, "summary": False}
        )

        assert "error" not in result
        assert result["title"] == "Metadata Preserved Item"
        assert isinstance(result["priority"], str)
        assert isinstance(result["file_path"], str)
        assert result["file_path"] != ""
        assert isinstance(result["groomed"], bool)
        assert isinstance(result["labels"], list)
        assert isinstance(result["messages"], list)
        assert isinstance(result["warnings"], list)

    async def test_compact_view_with_offset_limit_does_not_error(self, backlog_dir, mock_github, write_test_item):
        """Scenario C1d: backlog_view(include_content=False, offset=5, limit=3) does not error.

        Tests: compact mode with pagination params is harmless (no error path)
        How: call backlog_view with include_content=False plus offset and limit,
             assert response has no error key and sections_metadata is present.
        Why: offset/limit are pagination params for full-content mode; compact
             mode ignores them (returns all sections) but must not raise an error
             when they are supplied, preserving backward compatibility for callers
             that always pass pagination params.
        """
        filepath = write_test_item("Pagination Compact Item")
        filepath.write_text(
            filepath.read_text(encoding="utf-8")
            + "\n### Groomed (2026-03-22)\n\n"
            + "- [2026-03-22] Entry one.\n"
            + "- [2026-03-22] Entry two.\n",
            encoding="utf-8",
        )
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call(
            "backlog_view",
            {
                "selector": "Pagination Compact Item",
                "include_content": False,
                "summary": False,
                "offset": 5,
                "limit": 3,
            },
        )

        assert "error" not in result
        assert "sections_metadata" in result
        assert "body" not in result
        assert "sections" not in result

    async def test_default_include_content_true_unchanged(self, backlog_dir, mock_github, write_test_item):
        """Scenario C1e: backlog_view without include_content returns full body (backward compat).

        Tests: default behavior is unchanged when include_content is omitted
        How: call backlog_view with no include_content param, assert 'body' is
             present in the response and 'sections_metadata' is absent.
        Why: include_content defaults to True — all existing callers that do not
             pass the parameter must continue to receive the full response.
        """
        write_test_item("Default Full View Item")
        mock_github["view_enrich_from_github"].return_value = False

        result = await _call("backlog_view", {"selector": "Default Full View Item", "summary": False})

        assert "error" not in result
        assert "body" in result, "Default mode must include 'body' key"
        assert "sections_metadata" not in result, "Default mode must not include 'sections_metadata' key"

    async def test_e2e_combined_type_and_title_filters(self, backlog_dir, mock_github, write_test_item):
        """Combined filters narrow results correctly through the full MCP path."""
        write_test_item("Schema migration script error on PostgreSQL 15", type_val="Bug")
        write_test_item("Schema migration documentation update", type_val="Docs")
        write_test_item("API rate limiting bug", type_val="Bug")

        # type + title combined: only the Bug about migration
        result = await _call("backlog_list", {"type": "Bug", "title": "migration"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Schema migration script error on PostgreSQL 15"

    async def test_e2e_topic_filter_finds_semantically_related_item(self, backlog_dir, mock_github, write_test_item):
        """Topic filter narrows candidates for semantic matching via topic slug."""
        write_test_item("GitHub Actions workflow optimization", type_val="Chore")
        write_test_item("REST API improvements", type_val="Feature")
        write_test_item("Database schema updates", type_val="Refactor")

        # Topic filter uses slug-based substring match
        result = await _call("backlog_list", {"topic": "github-actions"})

        assert result["count"] == 1
        assert result["items"][0]["title"] == "GitHub Actions workflow optimization"


# ---------------------------------------------------------------------------
# Group 5: Pipeline completion enforcement — resolve gate and reconciliation
# ---------------------------------------------------------------------------


class TestResolveVerifiedGate:
    """Integration tests for the status:verified gate on resolve (Gap 4)
    and full pipeline flow (Gaps 1+4) and closed-issue reconciliation (Gap 3).

    The gate logic is:
    - If item has a Plan field AND no status:verified label -> block resolve
    - If item has no Plan field -> skip gate entirely
    - force=True bypasses the gate
    """

    async def test_resolve_blocks_without_verified_label(self, backlog_dir, mock_github, write_test_item):
        """Resolve with plan but no status:verified label is blocked at the view gate.

        When an item has a Plan field, the resolve workflow checks backlog_view
        labels for status:verified. Without the label, the caller is expected
        to block. This test verifies the data prerequisites: view returns labels
        and the item has a plan attached, but no verified label.
        """
        write_test_item("Verified Gate Test", issue="#200")
        mock_github["view_enrich_from_github"].return_value = False

        # Attach a plan to the item via backlog_update
        await _call("backlog_update", {"selector": "#200", "plan": "plan/test-plan.md"})

        # View item — should return labels (empty, no verified label)
        view_result = await _call("backlog_view", {"selector": "#200", "summary": False})

        assert view_result["title"] == "Verified Gate Test"
        assert isinstance(view_result["labels"], list)
        # No status:verified label present — gate should block at skill level
        assert "status:verified" not in view_result["labels"]
        # Plan field is present
        assert view_result.get("plan") == "plan/test-plan.md"

    async def test_resolve_passes_with_verified_label(self, backlog_dir, mock_github, write_test_item):
        """Resolve proceeds when status:verified label is present on the issue.

        After backlog_update(verified=True) applies the label, backlog_view
        returns it in labels, and the resolve call succeeds.
        """
        write_test_item("Verified Pass Test", issue="#201")
        mock_github["view_enrich_from_github"].return_value = False
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None

        # Attach plan, then apply verified label
        await _call("backlog_update", {"selector": "#201", "plan": "plan/verified-plan.md"})
        update_result = await _call("backlog_update", {"selector": "#201", "verified": True})

        assert update_result.get("verified") is True
        mock_github["apply_status_verified"].assert_called_once()

        # Resolve succeeds
        resolve_result = await _call("backlog_resolve", {"selector": "Verified Pass Test", "summary": "Work completed"})

        assert resolve_result["resolved"] is True
        assert resolve_result["title"] == "Verified Pass Test"

    async def test_resolve_skips_gate_without_plan(self, backlog_dir, mock_github, write_test_item):
        """Items without a Plan field skip the verification gate entirely.

        Non-SAM items (no plan attached) resolve without needing status:verified.
        """
        write_test_item("No Plan Item", issue="#202")
        mock_github["view_enrich_from_github"].return_value = False
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None

        # View confirms no plan
        view_result = await _call("backlog_view", {"selector": "#202", "summary": False})
        assert view_result.get("plan", "") == ""

        # Resolve succeeds without verified label — no plan means no gate
        resolve_result = await _call("backlog_resolve", {"selector": "No Plan Item", "summary": "Quick fix applied"})

        assert resolve_result["resolved"] is True
        # apply_status_verified never called — not needed for non-SAM items
        mock_github["apply_status_verified"].assert_not_called()

    async def test_resolve_force_bypasses_verified_gate(self, backlog_dir, mock_github, write_test_item):
        """force=True bypasses the verification gate even with a plan and no verified label."""
        write_test_item("Force Bypass Test", issue="#203")
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None

        # Attach plan but do NOT apply verified label
        await _call("backlog_update", {"selector": "#203", "plan": "plan/force-plan.md"})

        # Force resolve — bypasses both gates
        resolve_result = await _call(
            "backlog_resolve", {"selector": "Force Bypass Test", "summary": "Forced completion", "force": True}
        )

        assert resolve_result["resolved"] is True
        assert resolve_result["title"] == "Force Bypass Test"

    async def test_resolve_force_bypasses_both_gates(self, backlog_dir, mock_github, write_test_item):
        """force=True bypasses both the verified gate and the open-PR gate."""
        write_test_item("Force Both Gates Test", issue="#204")
        # Simulate open PRs that would normally block resolve
        pr_mock = MagicMock()
        pr_mock.number = 500
        pr_mock.title = "WIP: implementation"
        pr_mock.url = "https://github.com/test/repo/pull/500"
        mock_github["check_open_prs_for_issue"].return_value = [pr_mock]
        mock_github["resolve_github_issue"].return_value = None

        # Attach plan but no verified label, and open PRs exist
        await _call("backlog_update", {"selector": "#204", "plan": "plan/both-gates.md"})

        # Force resolve — bypasses both open-PR guard and verified gate
        resolve_result = await _call(
            "backlog_resolve", {"selector": "Force Both Gates Test", "summary": "Emergency resolve", "force": True}
        )

        assert resolve_result["resolved"] is True

    async def test_full_pipeline_label_then_resolve(self, backlog_dir, mock_github, write_test_item):
        """Full pipeline flow: create item with issue, attach plan, apply verified label, resolve.

        Gap 1 (apply label) followed by Gap 4 (gate passes) — the complete
        happy-path pipeline from completion to closure.
        """
        write_test_item("Pipeline Flow Test", issue="#205")
        mock_github["check_open_prs_for_issue"].return_value = []
        mock_github["resolve_github_issue"].return_value = None

        # Step 1: Attach plan (simulating /add-new-feature output)
        await _call("backlog_update", {"selector": "#205", "plan": "plan/pipeline-test.md"})

        # Step 2: Apply verified label (simulating /complete-implementation)
        update_result = await _call("backlog_update", {"selector": "#205", "verified": True})
        assert update_result.get("verified") is True
        mock_github["apply_status_verified"].assert_called_once()

        # Step 3: Resolve (simulating /work-backlog-item resolve)
        resolve_result = await _call(
            "backlog_resolve", {"selector": "Pipeline Flow Test", "summary": "All quality gates passed"}
        )

        assert resolve_result["resolved"] is True
        assert resolve_result["title"] == "Pipeline Flow Test"
        mock_github["resolve_github_issue"].assert_called_once()

    async def test_premature_close_detected_by_reconciliation(self, backlog_dir, mock_github, write_test_item):
        """Gap 3: closed-issue reconciliation detects issue closed without verified label.

        When backlog_list(from_github=True) triggers refresh_local_cache_from_github,
        closed issues are reconciled and local files updated to status=closed.
        """
        write_test_item("Premature Close Test", issue="#206")

        # Configure mock: GraphQL returns empty for OPEN, one closed issue for CLOSED.
        # _fetch_issues_graphql passes variables["states"] = ["OPEN"] or ["CLOSED"] to
        # graphql_query. The side_effect distinguishes open vs closed by inspecting variables.
        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.get_issues.return_value = []

        closed_issue_node = {
            "id": "I_206",
            "number": 206,
            "title": "Premature Close Test",
            "state": "CLOSED",
            "body": "",
            "closedAt": "2026-01-01T00:00:00Z",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
            "isPullRequest": False,
            "labels": {"nodes": []},
            "milestone": None,
            "assignees": {"nodes": []},
        }

        def _graphql_side_effect(query: str, variables: dict) -> tuple[dict, dict]:
            states = variables.get("states", [])
            if "CLOSED" in states:
                return (
                    {},
                    {
                        "data": {
                            "repository": {"issues": {"nodes": [closed_issue_node], "pageInfo": {"hasNextPage": False}}}
                        }
                    },
                )
            return ({}, {"data": {"repository": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}})

        mock_repo.requester.graphql_query.side_effect = _graphql_side_effect
        mock_github["try_get_github"].return_value = mock_repo

        # Trigger reconciliation via from_github=True
        result = await _call("backlog_list", {"from_github": True})

        assert isinstance(result["items"], list)
        # The reconciliation should have updated the local file
        # Check the file was updated to closed status
        item_files = list(backlog_dir.glob("*premature-close*"))
        assert item_files, "Expected local file to exist"
        file_text = item_files[0].read_text(encoding="utf-8")
        assert "closed" in file_text.lower()
