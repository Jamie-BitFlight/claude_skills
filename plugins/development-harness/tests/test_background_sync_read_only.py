"""Server startup and implicit reconciles never write to GitHub.

On 2026-09-27 the MCP server's startup sync ran a cold-cache reconcile that
posted an audit comment and a head record to every issue whose re-rendered
body differed, and repeated it on every start. These tests drive a real
``GitHubBackend`` over the fake GraphQL transport from
``tests/test_request_shaped_reads.py`` and count the requests it serves.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from backlog_core import operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.models import ContentRecord, ContentWrite
from backlog_core.sync_state import SyncStatus, get_sync_state, reset_sync_state
from fastmcp.client import Client

from tests.test_request_shaped_reads import FakeGitHubFixture

_MUTATIONS = {"AddComment"}


class _RecordingFixture(FakeGitHubFixture):
    """Also records every content-store write (the work-item head records)."""

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.content_writes: list[ContentWrite] = []
        put = self.contents.put

        def recording_put(request: ContentWrite) -> ContentRecord:
            self.content_writes.append(request)
            return put(request)

        self.contents.put = recording_put  # ty: ignore[invalid-assignment]

    def mutations(self) -> list[object]:
        return [*(op for op in self.requester.log.operation_names() if op in _MUTATIONS), *self.content_writes]


@pytest.fixture
def cold_cache(tmp_path: Path) -> Iterator[_RecordingFixture]:
    """Yield a fake repository whose local cache holds rows but no snapshot checkpoint.

    A request-shaped list writes through the rows it read without advancing
    the checkpoint, which is the state that made the next full reconcile
    patch every cached issue.

    Yields:
        The fixture, installed as the active backend, with its request log and
        content-store writes cleared.
    """
    fixture = _RecordingFixture(tmp_path)
    for number, body in enumerate(["## Description\n\nold\n", "freeform intro\n\n## Notes\nx", ""], start=1):
        fixture.add_tracked_issue(number, f"issue {number}", tracked_body=body)
    fixture.add_tracked_issue(9, "closed issue", state="CLOSED", tracked_body="## Description\nclosed")
    set_config(BacklogConfig(backend=fixture.backend))
    try:
        operations.list_items(limit=10, include_closed=True)
        assert fixture.backend.has_synced_snapshot() is False
        fixture.requester.log.clear()
        fixture.content_writes.clear()
        yield fixture
    finally:
        reset_config()


async def _settle_sync() -> None:
    for _ in range(200):
        await asyncio.sleep(0.01)
        if get_sync_state().status != SyncStatus.RUNNING:
            return
    pytest.fail("background sync did not settle")


async def test_server_startup_sends_no_github_requests(cold_cache: _RecordingFixture) -> None:
    from backlog_core.server import mcp

    reset_sync_state()
    async with Client(mcp) as client:
        await client.call_tool("sync_status", {})
        await _settle_sync()

    assert cold_cache.requester.log.operation_names() == []
    assert cold_cache.content_writes == []


def test_implicit_refresh_on_cold_cache_sends_no_mutations(cold_cache: _RecordingFixture) -> None:
    result = operations.refresh_local_cache_from_github()

    assert "ListIssues" in cold_cache.requester.log.operation_names()
    assert cold_cache.mutations() == []
    assert result["failures"] == 0, result


async def test_explicit_sync_now_still_pushes(cold_cache: _RecordingFixture) -> None:
    from backlog_core.server import mcp

    reset_sync_state()
    async with Client(mcp) as client:
        await _settle_sync()
        cold_cache.requester.log.clear()
        cold_cache.content_writes.clear()
        response = await client.call_tool("sync_now", {})
        await _settle_sync()

    assert response.structured_content["triggered"] is True
    assert "AddComment" in cold_cache.requester.log.operation_names()
