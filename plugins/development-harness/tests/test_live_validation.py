"""Live GitHub contracts in an explicitly authorized, non-production sandbox.

Run with the configuration in docs/live-e2e-validation.md and pytest -m e2e -n 0.
Missing configuration fails before mutation; the default test lane deselects E2E.
Each scenario owns its setup, observations and cleanup, with no test-order coupling.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import backlog_core.models as bc_models
import backlog_core.server as backlog_server
import pytest
from backlog_core.backend_protocol import get_config, reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import ReconcileRequest, ReconcileScope
from fastmcp.client import Client

from close_test_issues import open_sandbox
from live_test_scope import LiveTestScope, cleanup_run
from tests.live_test_support import Journal, LiveCalls, collect_items, issue_number

if TYPE_CHECKING:
    from github.Issue import Issue
    from github.Repository import Repository

pytestmark = pytest.mark.e2e


@dataclass
class LiveEnvironment:
    scope: LiveTestScope
    repository: Repository
    backend: GitHubBackend
    root: Path
    journal: Journal

    @contextmanager
    def fresh_reader(self) -> Iterator[GitHubBackend]:
        """Replace the writer cache with an empty, real provider cache for readback."""
        previous = get_config()
        backend = GitHubBackend(repo=self.scope.repository, cache=FileCache(self.root / f"reader-{uuid.uuid4().hex}"))
        set_config(BacklogConfig(backend=backend))
        try:
            yield backend
        finally:
            set_config(previous)


@pytest.fixture
def live_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    if request.config.getoption("numprocesses", default=0) not in (None, 0):
        pytest.fail("Live scenarios share one configured MCP backend; run this lane with -n 0")
    scope = LiveTestScope.from_environment(os.environ)
    repository = open_sandbox(scope)
    report_dir = Path(os.environ.get("DH_E2E_REPORT_DIR", str(tmp_path / "reports")))
    journal = Journal(report_dir / f"{request.node.name}.jsonl")
    journal.record("scope", repository=scope.repository, run_id=scope.run_id, scenario=request.node.name)
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("GITHUB_REPO", scope.repository)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(
        bc_models,
        "_config",
        bc_models.BacklogConfig(repo_root=project, backlog_dir=tmp_path / "backlog", default_repo=scope.repository),
    )
    # Controlled CRUD and cold-read scenarios, not a claim about background startup.
    monkeypatch.setattr(backlog_server, "_startup_sync_enabled", lambda: False)
    backend = GitHubBackend(repo=scope.repository, cache=FileCache(tmp_path / "writer"))
    set_config(BacklogConfig(backend=backend))
    try:
        yield LiveEnvironment(scope, repository, backend, tmp_path, journal)
    finally:
        reset_config()
        with journal.phase("cleanup"):
            # Revalidate the remote marker and canonical target, not a cached identity.
            closed = cleanup_run(scope, open_sandbox(scope))
            journal.record("cleanup", closed=closed)


async def create_item(calls: LiveCalls, env: LiveEnvironment, suffix: str) -> tuple[int, str]:
    title = f"{env.scope.title_prefix} {suffix} {uuid.uuid4().hex}"
    with env.journal.phase(f"create {suffix}"):
        result = await calls.call(
            "backlog_add",
            {
                "title": title,
                "priority": "P1",
                "description": f"{env.scope.body_marker}\n\nLive validation fixture: {suffix}",
                "source": "test",
                "force": True,
            },
        )
        number = issue_number(result)
        env.journal.record("created", issue=number)
        stored_title = result.get("title")
        assert isinstance(stored_title, str), result
        assert title in stored_title, result
        remote = await asyncio.to_thread(env.repository.get_issue, number)
        assert remote.title == stored_title
        assert env.scope.owns(remote.title, remote.body, remote.pull_request)
        assert f"Live validation fixture: {suffix}" in (remote.body or "")
        return number, stored_title


async def native_issue(env: LiveEnvironment, number: int) -> Issue:
    return await asyncio.to_thread(env.repository.get_issue, number)


def listed_references(items: list[dict[str, object]]) -> set[str]:
    return {str(item.get("issue", "")) for item in items}


async def test_live_crud_persists_changes_and_preserves_other_sections(live_environment: LiveEnvironment) -> None:
    env = live_environment
    # Warm CRUD has an explicit, real open-issue snapshot. Historical cold-cache
    # recovery belongs to the independent scenario below, not an accidental list side effect.
    with env.journal.phase("warm snapshot setup"):
        reconciled = await asyncio.to_thread(
            env.backend.reconcile, ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=False)
        )
        assert reconciled.failures == 0, reconciled
        assert env.backend.has_synced_snapshot()
    async with Client(backlog_server.mcp, timeout=30, init_timeout=30) as client:
        calls = LiveCalls(client, env.journal)
        with env.journal.phase("warm lifecycle"):
            primary, title = await create_item(calls, env, "primary")
            companion, companion_title = await create_item(calls, env, "companion")

            with env.journal.phase("list membership across pages"):
                items = await collect_items(calls.call, {"limit": 1})
                assert {f"#{primary}", f"#{companion}"}.issubset(listed_references(items)), items

            with env.journal.phase("numeric view"):
                view = await calls.call("backlog_view", {"selector": f"#{primary}", "summary": False})
                assert view["title"] == title, view
                assert isinstance(view["body"], str), view
                assert view["status_source"] == "live", view

            with env.journal.phase("plan association and status"):
                plan = "plan/live-test-plan.md"
                updated = await calls.call("backlog_update", {"selector": title, "plan": plan})
                assert updated["plan"] == plan, updated
                associated = await calls.call("backlog_view", {"selector": title, "summary": False})
                assert associated["plan"] == plan, associated
                updated = await calls.call("backlog_update", {"selector": title, "status": "in-progress"})
                assert updated["status"] == "in-progress", updated
                remote = await native_issue(env, primary)
                assert "status:in-progress" in {label.name for label in remote.labels}

            groomed = "Live test groomed content.\n\n### Reproducibility\n\nSteps here."
            dependencies = "No external dependencies."
            with env.journal.phase("groom and incremental section preservation"):
                groom = await calls.call(
                    "backlog_groom", {"selector": title, "section": "Groomed", "content": groomed}
                )
                assert groom["groomed_updated"] is True, groom
                incremental = await calls.call(
                    "backlog_groom", {"selector": title, "section": "Dependencies", "content": dependencies}
                )
                assert incremental["groomed_updated"] is True, incremental
                synced = await calls.call("backlog_sync", {})
                assert isinstance(synced["created"], int), synced
                assert isinstance(synced["pushed"], int), synced
                # Native comments and an empty-cache MCP reader are distinct observations.
                # The issue body is human-owned; grooming must not be tested as a body rewrite.
                remote = await native_issue(env, primary)
                comments = await asyncio.to_thread(lambda: [comment.body for comment in remote.get_comments()])
                assert any("Live test groomed content." in body for body in comments), comments
                assert any(dependencies in body for body in comments), comments
                with env.fresh_reader():
                    persisted = await calls.call("backlog_view", {"selector": f"#{primary}", "summary": False})
                    assert persisted["status_source"] == "live", persisted
                    assert "Live test groomed content." in str(persisted["body"]), persisted
                    assert dependencies in str(persisted["body"]), persisted

            with env.journal.phase("pull observes an independent provider edit"):
                remote = await native_issue(env, companion)
                changed_title = companion_title + " changed remotely"
                changed_body = f"{env.scope.body_marker}\n\nProvider edit not present in the writer cache."
                await asyncio.to_thread(remote.edit, title=changed_title, body=changed_body)
                await calls.call("backlog_pull", {"selector": f"#{companion}"})
                # A title lookup without refresh reads the cache populated by pull. A
                # numeric lookup here would mask a no-op pull by fetching GitHub again.
                pulled = await calls.call("backlog_view", {"selector": changed_title, "summary": False})
                assert pulled["title"] == changed_title, pulled
                assert "Provider edit not present in the writer cache." in str(pulled["body"]), pulled

            with env.journal.phase("close and resolve are native terminal transitions"):
                closed = await calls.call("backlog_close", {"selector": title, "reason": "wontfix"})
                assert closed["closed"] is True, closed
                assert (await native_issue(env, primary)).state == "closed"
                resolved = await calls.call(
                    "backlog_resolve", {"selector": f"#{companion}", "summary": "Live validation completed"}
                )
                assert resolved["resolved"] is True, resolved
                assert (await native_issue(env, companion)).state == "closed"


async def test_live_cold_cache_recovers_open_and_closed_items(live_environment: LiveEnvironment) -> None:
    env = live_environment
    async with Client(backlog_server.mcp, timeout=30, init_timeout=30) as client:
        calls = LiveCalls(client, env.journal)
        with env.journal.phase("cold-cache recovery"):
            opened, _ = await create_item(calls, env, "cold-open")
            closed, _ = await create_item(calls, env, "cold-closed")
            remote = await native_issue(env, closed)
            await asyncio.to_thread(remote.edit, state="closed")
            assert (await native_issue(env, closed)).state == "closed"
            with env.fresh_reader() as backend:
                assert not backend.has_synced_snapshot()
                items = await collect_items(calls.call, {"limit": 1})
                assert f"#{opened}" in listed_references(items), items
                # Recovery completeness is a provider-cache contract, independent of
                # the MCP listing's open-item presentation/filtering policy.
                records = backend.list_work_items()
                recovered = [item for item in records if item.issue == f"#{closed}"]
                assert len(recovered) == 1, records
                assert recovered[0].status == "closed", recovered
                assert backend.has_synced_snapshot()
