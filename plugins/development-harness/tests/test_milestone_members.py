"""Regression coverage for authoritative configured-backend milestone membership."""

from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from backlog_core import gh_client, operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem, BacklogItemMetadata
from backlog_core.server import mcp
from sam_schema.cli import app
from typer.testing import CliRunner

from tests.helpers import call_mcp_tool


async def test_milestone_members_include_unmanaged_provider_rows_across_public_transports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A milestone audit reads every native member, not only DH-parsed work items."""
    database_path = tmp_path / "isolated-backlog.sqlite3"
    backend = SQLiteBackend(str(database_path))
    set_config(BacklogConfig(backend=backend))

    def deny_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden in this local-backend regression")

    def deny_subprocess(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("subprocess escape is forbidden in this local-backend regression")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(subprocess, "Popen", deny_subprocess)

    try:
        target = operations.create_milestone(title="Release")
        alternate = operations.create_milestone(title="Release")
        target_milestone = cast("dict[str, object]", target["milestone"])
        alternate_milestone = cast("dict[str, object]", alternate["milestone"])
        target_number = target_milestone["number"]
        alternate_number = alternate_milestone["number"]
        assert isinstance(target_number, int)
        assert isinstance(alternate_number, int)

        managed_number = backend.create_issue_for_item(
            None,
            BacklogItem(
                title="Managed member",
                metadata=BacklogItemMetadata(source="test", added="2026-10-17", priority="P1", status="open"),
            ),
        )
        assert managed_number is not None
        operations.assign_item_to_milestone(managed_number, target_number)

        backend._conn.execute(
            "INSERT INTO items (issue_number, title, status, body, created_at, updated_at, closed_at, milestone_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                700,
                "Ordinary member",
                "closed",
                "No DH priority section.",
                "2026-10-17T00:00:00Z",
                "2026-10-17T00:00:00Z",
                None,
                target_number,
            ),
        )
        backend._conn.execute(
            "INSERT INTO items (issue_number, title, status, body, created_at, updated_at, closed_at, milestone_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                701,
                "Ordinary member",
                "open",
                "No DH priority section.",
                "2026-10-17T00:00:00Z",
                "2026-10-17T00:00:00Z",
                None,
                alternate_number,
            ),
        )
        backend._conn.commit()

        native_counts = operations.list_milestones(state="all")
        milestones = cast("list[dict[str, object]]", native_counts["milestones"])
        target_counts = next(item for item in milestones if item["number"] == target_number)
        assert target_counts["open_issues"] == 1
        assert target_counts["closed_issues"] == 1

        direct = operations.list_milestone_members(target_number)
        assert direct["count"] == 2
        assert direct["members"] == [
            {
                "issue_number": managed_number,
                "title": "Managed member",
                "state": "OPEN",
                "milestone_number": target_number,
            },
            {"issue_number": 700, "title": "Ordinary member", "state": "CLOSED", "milestone_number": target_number},
        ]

        mcp_result = await call_mcp_tool(mcp, "backlog_list_milestone_members", {"milestone_number": target_number})
        assert mcp_result["count"] == 2
        assert mcp_result["members"] == direct["members"]

        monkeypatch.chdir(tmp_path)
        assert Path.cwd() == tmp_path
        cli_result = CliRunner().invoke(
            app,
            ["backlog", "list-milestone-members", "--milestone-number", str(target_number)],
            env={"NO_COLOR": "1", "GITHUB_TOKEN": ""},
        )
        assert cli_result.exit_code == 0, cli_result.stderr
        assert json.loads(cli_result.stdout)["members"] == direct["members"]
    finally:
        reset_config()
        backend._conn.close()


def test_github_membership_read_exhausts_the_milestone_issues_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """The authoritative GitHub read includes every page and preserves native state."""
    responses = {
        None: {
            "repository": {
                "milestone": {
                    "issues": {
                        "nodes": [{"number": 10, "title": "Managed", "state": "OPEN"}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
                    }
                }
            }
        },
        "page-2": {
            "repository": {
                "milestone": {
                    "issues": {
                        "nodes": [{"number": 11, "title": "Ordinary", "state": "CLOSED"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        },
    }
    cursors: list[str | None] = []

    def graphql_page(_repo: object, _query: str, variables: dict[str, object]) -> dict[str, object]:
        cursor = variables["after"]
        assert cursor is None or isinstance(cursor, str)
        cursors.append(cursor)
        return cast("dict[str, object]", responses[cursor])

    monkeypatch.setattr(gh_client, "_graphql_request", graphql_page)

    members = gh_client.fetch_milestone_members_graphql(MagicMock(), "owner", "repo", 7)

    assert cursors == [None, "page-2"]
    assert members == [
        {"issue_number": 10, "title": "Managed", "state": "OPEN", "milestone_number": 7},
        {"issue_number": 11, "title": "Ordinary", "state": "CLOSED", "milestone_number": 7},
    ]
