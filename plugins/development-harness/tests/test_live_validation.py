"""Live validation tests for the backlog MCP server.

Suite 2: No mocks — calls go through real operations and GitHub API.
Requires ``GITHUB_TOKEN`` environment variable.

Marked with ``pytest.mark.e2e`` — excluded from default test runs.
Run with: ``uv run pytest .claude/skills/backlog/tests/test_live_validation.py -m e2e -v``

No ``@pytest.mark.asyncio`` decorators — global ``asyncio_mode = "auto"``.
"""

from __future__ import annotations

import logging
import os
import uuid

import backlog_core.models as _bc_models
import pytest
from backlog_core.models import BacklogConfig
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

logger = logging.getLogger(__name__)


def _find_latest_gate_token() -> str:
    """Return the contents of the most recently modified .gate-token file.

    Scans ``{DH_STATE_HOME}/sessions/*/.gate-token`` (or ``~/.dh/sessions/``
    when ``DH_STATE_HOME`` is not set).  In e2e live tests there is no skill
    injection, so the test must locate the token file itself rather than
    receiving it through context.

    Returns:
        The raw token string, or an empty string when no file is found.
    """
    from pathlib import Path

    dh_root = Path(os.environ.get("DH_STATE_HOME", Path.home() / ".dh"))
    candidates = list(dh_root.glob("sessions/*/.gate-token"))
    if not candidates:
        return ""
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Module-level skip + mark
# ---------------------------------------------------------------------------

_HAS_TOKEN = bool(os.environ.get("GITHUB_TOKEN"))

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not _HAS_TOKEN, reason="GITHUB_TOKEN not set — skipping live tests")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call MCP tool via in-memory transport and parse JSON response.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Fixture: live_items (class-scoped, creates temp backlog dir + cleanup)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class")
def live_items(tmp_path_factory, monkeypatch_class):
    """Class-scoped fixture for live validation tests.

    - Redirects BACKLOG_DIR to a temp directory
    - Generates a unique test UUID for issue title prefixing
    - Tracks created issue numbers for teardown cleanup
    - Cleans up ALL created GitHub issues via PyGithub on teardown
    """
    import dh_paths

    tmp_root = tmp_path_factory.mktemp("live_backlog")
    monkeypatch_class.setenv("DH_STATE_HOME", str(tmp_root / "dh_state"))

    fake_project_root = tmp_root / "project"
    fake_project_root.mkdir(parents=True, exist_ok=True)

    bd = dh_paths.backlog_dir(project_root=fake_project_root)
    bd.mkdir(parents=True, exist_ok=True)

    existing = _bc_models._config
    # Prefer GITHUB_REPO env var (set in CI) over the already-resolved default_repo.
    # The fixture replaces _config directly, bypassing _discover_via_env(), so without
    # this the env var is never consulted and default_repo stays "" in CI — causing 404s.
    resolved_repo = os.environ.get("GITHUB_REPO", existing.default_repo if existing is not None else "")
    monkeypatch_class.setattr(
        _bc_models, "_config", BacklogConfig(repo_root=fake_project_root, backlog_dir=bd, default_repo=resolved_repo)
    )

    test_id = str(uuid.uuid4())[:8]

    # Write gate token file so backlog_add passes its gate validation.
    # The server reads the token from {DH_STATE_HOME}/sessions/{session_id}/.gate-token
    # at request time. CLAUDE_CODE_SESSION_ID must also be set in the process environment
    # so that both the server's validation path and _read_gate_token() (called inline in
    # test bodies to supply the gate_token parameter) resolve to the same file.
    live_session_id = f"live-test-session-{test_id}"
    # Use a fixed-length 64-char hex-style token that is unique to this test run.
    live_gate_token = str(uuid.uuid4()).replace("-", "") + str(uuid.uuid4()).replace("-", "")
    live_gate_token = live_gate_token[:64]
    token_dir = tmp_root / "dh_state" / "sessions" / live_session_id
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / ".gate-token").write_text(live_gate_token, encoding="utf-8")
    monkeypatch_class.setenv("CLAUDE_CODE_SESSION_ID", live_session_id)

    ctx: dict = {
        "test_id": test_id,
        "backlog_dir": bd,
        "issues": [],  # track created issue numbers for cleanup
        "title_prefix": f"[MCP-TEST-{test_id}]",
        # Populated by test_l1_add_with_real_issue on success.
        # Pre-initialised to None so dependent tests can pytest.skip instead of KeyError.
        "item_title": None,
        "item_issue_num": None,
        "item_filepath": None,
        # Set to True only when L1 fully completes. Downstream guards check this sentinel.
        "l1_ok": False,
    }

    yield ctx

    # Teardown: close all created issues — log failures instead of swallowing silently
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and ctx["issues"]:
        try:
            from github import Auth, Github, GithubException
        except ImportError:
            logger.warning(
                "PyGithub not available — cannot clean up %d test issues: %s", len(ctx["issues"]), ctx["issues"]
            )
        else:
            try:
                from backlog_core.models import RepoDiscoveryError, discover_repo

                try:
                    repo_slug = discover_repo()
                except RepoDiscoveryError:
                    # repo_root is a temp non-git dir and GITHUB_REPO is unset;
                    # fall back to the pre-patched default_repo if available
                    repo_slug = existing.default_repo if existing is not None else ""
                if not repo_slug:
                    logger.warning("Cannot determine repo slug for teardown cleanup of issues: %s", ctx["issues"])
                else:
                    g = Github(auth=Auth.Token(token))
                    repo = g.get_repo(repo_slug)
                    for issue_num in ctx["issues"]:
                        try:
                            issue = repo.get_issue(issue_num)
                            issue.edit(state="closed")
                        except GithubException:
                            logger.warning(
                                "Failed to close test issue #%d — will remain open as orphan", issue_num, exc_info=True
                            )
            except GithubException:
                logger.warning(
                    "Failed to connect to GitHub for teardown cleanup of issues: %s", ctx["issues"], exc_info=True
                )


@pytest.fixture(scope="class")
def monkeypatch_class():
    """Class-scoped monkeypatch for use with class-scoped fixtures."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ---------------------------------------------------------------------------
# Live Lifecycle Tests (L1-L11)
# ---------------------------------------------------------------------------


@pytest.mark.xdist_group("live_lifecycle")
class TestLiveLifecycle:
    """Live validation lifecycle: L1 creates an item, L2-L10 operate on it,
    L11 creates and resolves a second item. Tests execute in declaration order
    on a single xdist worker (grouped via xdist_group marker).
    """

    async def test_l1_add_with_real_issue(self, live_items):
        """L1: backlog_add creates a real GitHub issue."""
        prefix = live_items["title_prefix"]
        result = await _call(
            "backlog_add",
            {
                "title": f"{prefix} Live Test Item",
                "priority": "P1",
                "description": "Live validation test item",
                "source": "test",
                "force": True,
                "gate_token": _find_latest_gate_token(),
            },
        )

        assert result["title"] == f"{prefix} Live Test Item"
        assert isinstance(result["issue_num"], int)
        assert result["issue_num"] > 0
        assert isinstance(result["file_path"], str)
        assert isinstance(result["messages"], list)
        # Track for cleanup and later tests
        live_items["issues"].append(result["issue_num"])
        live_items["item_title"] = result["title"]
        live_items["item_filepath"] = result["file_path"]
        live_items["item_issue_num"] = result["issue_num"]
        live_items["l1_ok"] = True

    async def test_l2_list_includes_created_item(self, live_items):
        """L2: backlog_list returns the item created in L1."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call("backlog_list", {})

        assert isinstance(result["items"], list)
        assert result["count"] >= 1
        matching = [i for i in result["items"] if live_items["title_prefix"] in i.get("title", "")]
        assert matching, f"Expected item with prefix {live_items['title_prefix']} in list"

    async def test_l3_view_by_issue_number(self, live_items):
        """L3: backlog_view by issue number returns full item data."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        issue_num = live_items["item_issue_num"]
        result = await _call("backlog_view", {"selector": f"#{issue_num}", "summary": False})

        # backlog_view may return a GitHub-normalised title (e.g. "feat: ..." prefix)
        # so verify the original title text is present in the returned title.
        assert live_items["item_title"] in result["title"] or result["title"] == live_items["item_title"]
        assert isinstance(result["body"], str)
        assert isinstance(result["priority"], str)
        assert isinstance(result["labels"], list)

    async def test_l4_update_attach_plan(self, live_items):
        """L4: backlog_update attaches a plan path to the item."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call("backlog_update", {"selector": live_items["item_title"], "plan": "plan/live-test-plan.md"})

        assert result["title"] == live_items["item_title"]
        assert result["plan"] == "plan/live-test-plan.md"

    async def test_l5_update_set_status_in_progress(self, live_items):
        """L5: backlog_update sets status to in-progress via GitHub label."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call("backlog_update", {"selector": live_items["item_title"], "status": "in-progress"})

        assert result["title"] == live_items["item_title"]
        assert result["status"] == "in-progress"

    async def test_l6_groom_write_full_content(self, live_items):
        """L6: backlog_groom writes full groomed content to item and syncs to GitHub."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call(
            "backlog_groom",
            {
                "selector": live_items["item_title"],
                "section": "Groomed",
                "content": "Live test groomed content.\n\n### Reproducibility\n\nSteps here.",
            },
        )

        assert result["groomed_updated"] is True
        assert isinstance(result["messages"], list)

    async def test_l7_groom_incremental_section(self, live_items):
        """L7: backlog_groom updates a specific section incrementally."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call(
            "backlog_groom",
            {"selector": live_items["item_title"], "section": "Dependencies", "content": "No external dependencies."},
        )

        assert result["groomed_updated"] is True

    async def test_l8_sync_push_groomed(self, live_items):
        """L8: backlog_sync pushes groomed content to GitHub issues."""
        result = await _call("backlog_sync")

        assert isinstance(result["created"], int)
        assert isinstance(result["pushed"], int)
        assert isinstance(result["messages"], list)

    async def test_l9_pull_refresh_from_github(self, live_items):
        """L9: backlog_pull refreshes local files from GitHub issue bodies."""
        result = await _call("backlog_pull")

        assert isinstance(result["messages"], list)

    async def test_l10_close_full_lifecycle_end(self, live_items):
        """L10: backlog_close with reason closes the item."""
        if not live_items["l1_ok"]:
            pytest.skip("L1 (test_l1_add_with_real_issue) did not complete — skipping dependent test")
        result = await _call("backlog_close", {"selector": live_items["item_title"], "reason": "wontfix"})

        assert result["closed"] is True
        assert isinstance(result["messages"], list)

    async def test_l11_resolve_alternative_end(self, live_items):
        """L11: Create a second item and resolve it (alternative lifecycle end)."""
        prefix = live_items["title_prefix"]

        # Create second item
        create_result = await _call(
            "backlog_add",
            {
                "title": f"{prefix} Live Resolve Item",
                "priority": "P2",
                "description": "Item to be resolved",
                "source": "test",
                "force": True,
                "gate_token": _find_latest_gate_token(),
            },
        )
        assert isinstance(create_result["issue_num"], int)
        live_items["issues"].append(create_result["issue_num"])

        # Resolve it
        resolve_result = await _call(
            "backlog_resolve",
            {"selector": f"{prefix} Live Resolve Item", "summary": "No longer needed — live test cleanup"},
        )

        assert resolve_result["resolved"] is True
        assert isinstance(resolve_result["messages"], list)
