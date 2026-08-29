"""Parity between the CLI and MCP backend-resolution seams.

``sam_plan._backend()`` (CLI) and ``server._get_backend()`` (MCP) must resolve
to the same underlying provider — a divergence here would mean the CLI and MCP
server silently operate on different backlog state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.bd_runner import BdRunner
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.memory_backend import InMemoryBackend

import sam_schema.sam_plan as sam_plan
import sam_schema.server as server
from sam_schema.core.backends.content import ContentTaskProvider

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_backend_config() -> Generator[None, None, None]:
    # Reset before too: the beads test relies on get_config() being uninitialised
    # so BACKLOG_BACKEND is actually consulted. Under the full suite, an earlier
    # test elsewhere can leave the module-level _active_config singleton cached
    # (e.g. to a real GitHubBackend), which would otherwise short-circuit env
    # resolution here and trigger a real (sandbox-blocked) network call.
    reset_config()
    yield
    reset_config()


def test_cli_and_mcp_backend_resolution_match_default() -> None:
    backend = InMemoryBackend()
    set_config(BacklogConfig(backend=backend))

    cli_provider = sam_plan._backend()
    mcp_provider = server._get_backend("")

    assert isinstance(cli_provider, ContentTaskProvider)
    assert isinstance(mcp_provider, ContentTaskProvider)
    assert cli_provider._provider is backend
    assert mcp_provider._provider is backend


def test_cli_and_mcp_backend_resolution_match_beads(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_runner = MagicMock(spec=BdRunner)
    mock_runner.run_json.return_value = {}
    monkeypatch.setattr("backlog_core.backends.beads_backend.BdRunner", lambda: mock_runner)
    monkeypatch.setenv("BACKLOG_BACKEND", "beads")

    cli_provider = sam_plan._backend()
    mcp_provider = server._get_backend("")

    assert isinstance(cli_provider, ContentTaskProvider)
    assert isinstance(mcp_provider, ContentTaskProvider)
    assert isinstance(cli_provider._provider, BeadsBackend)
    # Same cached BacklogConfig singleton backs both seams.
    assert cli_provider._provider is mcp_provider._provider
