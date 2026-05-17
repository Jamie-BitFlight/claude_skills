"""Tests for backlog Projects V2 MCP tools and operations.

Covers two tools and operations:
- list_projects / backlog_list_projects
- create_project / backlog_create_project

GraphQL calls are mocked at the _graphql_request boundary in backlog_core.github
(imported and called from operations.py). No real GitHub API calls are made.

Tests are structured in two layers:
- Operation layer: list_projects() and create_project() in operations.py.
- Server layer: MCP tool wrappers via in-memory FastMCP Client.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from backlog_core.models import BacklogError, ValidationError
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fake_project_node(
    project_id: str = "PVT_abc123",
    title: str = "My Project",
    number: int = 1,
    url: str = "https://github.com/orgs/owner/projects/1",
    closed: bool = False,
    short_description: str = "",
) -> dict[str, object]:
    """Return a dict matching a GraphQL projectsV2 node."""
    return {
        "id": project_id,
        "title": title,
        "number": number,
        "url": url,
        "closed": closed,
        "shortDescription": short_description,
    }


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Operation layer: list_projects()
# ---------------------------------------------------------------------------


def test_list_projects_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects returns dicts with all required fields for each project.

    Tests: list_projects field mapping
    How: Patch _graphql_request to return one project node; verify field names.
    Why: Field names are the contract between server and MCP consumers.
    """
    # Arrange
    node = _fake_project_node(
        project_id="PVT_1",
        title="Roadmap",
        number=3,
        url="https://github.com/orgs/acme/projects/3",
        closed=False,
        short_description="Q2 roadmap",
    )
    graphql_response = {"repositoryOwner": {"projectsV2": {"nodes": [node]}}}

    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr("backlog_core.operations._graphql_request", lambda *a, **kw: graphql_response)

    from backlog_core.operations import list_projects

    # Act
    result = list_projects()

    # Assert
    assert result["count"] == 1
    projects = result["projects"]
    assert isinstance(projects, list)
    entry = projects[0]
    assert isinstance(entry, dict)
    assert entry["id"] == "PVT_1"
    assert entry["title"] == "Roadmap"
    assert entry["number"] == 3
    assert entry["url"] == "https://github.com/orgs/acme/projects/3"
    assert entry["closed"] is False
    assert entry["short_description"] == "Q2 roadmap"


def test_list_projects_passes_limit_in_graphql_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects forwards the limit to the GraphQL query variables.

    Tests: list_projects limit forwarding
    How: Capture variables passed to _graphql_request; verify limit appears.
    Why: The limit is enforced by the GraphQL API via the first: variable, not
    by slicing the returned nodes locally. The test verifies the contract at
    the API boundary, not the post-fetch slice.
    """
    # Arrange
    captured: dict[str, object] = {}
    graphql_response = {"repositoryOwner": {"projectsV2": {"nodes": []}}}

    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    def capture_graphql(repo: object, query: str, variables: dict) -> dict:
        captured["variables"] = variables
        return graphql_response

    monkeypatch.setattr("backlog_core.operations._graphql_request", capture_graphql)

    from backlog_core.operations import list_projects

    # Act
    list_projects(limit=5)

    # Assert — limit is forwarded in the GraphQL variables (key is "limit" per _projects_v2_list_query)
    assert "variables" in captured
    variables = cast("dict[str, object]", captured["variables"])
    assert variables["limit"] == 5


def test_list_projects_empty_when_no_projects(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects returns count=0 and empty list when owner has no projects.

    Tests: list_projects empty case
    How: Return empty nodes list from GraphQL response.
    Why: Empty result must be handled without errors.
    """
    # Arrange
    graphql_response = {"repositoryOwner": {"projectsV2": {"nodes": []}}}

    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr("backlog_core.operations._graphql_request", lambda *a, **kw: graphql_response)

    from backlog_core.operations import list_projects

    # Act
    result = list_projects()

    # Assert
    assert result["count"] == 0
    assert result["projects"] == []


def test_list_projects_handles_none_nodes_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects handles null nodes in the GraphQL response without crashing.

    Tests: list_projects null node filtering
    How: Include a None entry in the nodes list; verify it is skipped.
    Why: The GraphQL API can return null nodes for deleted/inaccessible projects.
    """
    # Arrange
    node = _fake_project_node(project_id="PVT_1", title="Active")
    graphql_response = {"repositoryOwner": {"projectsV2": {"nodes": [None, node]}}}

    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr("backlog_core.operations._graphql_request", lambda *a, **kw: graphql_response)

    from backlog_core.operations import list_projects

    # Act
    result = list_projects()

    # Assert — None node skipped, active node included
    assert result["count"] == 1
    projects = result["projects"]
    assert isinstance(projects, list)
    first_project = projects[0]
    assert isinstance(first_project, dict)
    assert first_project["title"] == "Active"


def test_list_projects_graphql_error_raises_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects propagates BacklogError raised by _graphql_request.

    Tests: list_projects error propagation
    How: Raise BacklogError from mocked _graphql_request; verify it propagates.
    Why: GraphQL errors must surface as BacklogError for consistent error handling.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr(
        "backlog_core.operations._graphql_request",
        lambda *a, **kw: (_ for _ in ()).throw(BacklogError("GraphQL error: field not found")),
    )

    from backlog_core.operations import list_projects

    # Act / Assert
    with pytest.raises(BacklogError, match="GraphQL error"):
        list_projects()


def test_list_projects_uses_owner_from_repo_when_not_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_projects resolves owner from repo.owner.login when owner param is None.

    Tests: list_projects owner resolution
    How: Capture owner passed to _projects_v2_list_query; verify it matches repo owner.
    Why: Without correct owner resolution, GraphQL query targets the wrong org.
    """
    # Arrange
    captured: dict[str, object] = {}
    graphql_response = {"repositoryOwner": {"projectsV2": {"nodes": []}}}

    mock_repo = MagicMock()
    mock_repo.owner.login = "myorg"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    def capture_graphql(repo: object, query: str, variables: dict) -> dict:
        captured["variables"] = variables
        return graphql_response

    monkeypatch.setattr("backlog_core.operations._graphql_request", capture_graphql)

    from backlog_core.operations import list_projects

    # Act
    list_projects()

    # Assert — owner resolved from repo, used in GraphQL variables
    assert "variables" in captured
    variables = cast("dict[str, object]", captured["variables"])
    assert variables["owner"] == "myorg"


# ---------------------------------------------------------------------------
# Operation layer: create_project()
# ---------------------------------------------------------------------------


def test_create_project_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_project returns project_id, title, url, and number.

    Tests: create_project return shape
    How: Mock _graphql_request to return owner ID then project creation data.
    Why: Callers need the project_id immediately after creation for further API calls.
    """
    # Arrange
    id_response = {"repositoryOwner": {"id": "U_abc123"}}
    create_response = {
        "createProjectV2": {
            "projectV2": {
                "id": "PVT_new",
                "title": "Sprint Board",
                "url": "https://github.com/orgs/acme/projects/5",
                "number": 5,
            }
        }
    }
    call_count = 0

    def two_phase_graphql(repo: object, query: str, variables: dict) -> dict:
        nonlocal call_count
        call_count += 1
        return id_response if call_count == 1 else create_response

    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr("backlog_core.operations._graphql_request", two_phase_graphql)

    from backlog_core.operations import create_project

    # Act
    result = create_project(title="Sprint Board")

    # Assert
    assert result["project_id"] == "PVT_new"
    assert result["title"] == "Sprint Board"
    assert result["url"] == "https://github.com/orgs/acme/projects/5"
    assert result["number"] == 5
    assert "messages" in result
    assert "warnings" in result


def test_create_project_empty_title_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_project raises ValidationError when title is empty or whitespace.

    Tests: create_project title validation
    How: Pass empty title; expect ValidationError before any API call.
    Why: Empty project title is invalid and caught before network round-trips.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import create_project

    # Act / Assert
    with pytest.raises(ValidationError, match="title must not be empty"):
        create_project(title="")


def test_create_project_owner_not_found_raises_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_project raises BacklogError when repositoryOwner GraphQL node is missing.

    Tests: create_project owner resolution failure
    How: Return None repositoryOwner from first _graphql_request call.
    Why: Owner resolution failure must surface explicitly, not cause a KeyError.
    """
    # Arrange
    id_response: dict[str, object] = {"repositoryOwner": None}

    mock_repo = MagicMock()
    mock_repo.owner.login = "ghost"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr("backlog_core.operations._graphql_request", lambda *a, **kw: id_response)

    from backlog_core.operations import create_project

    # Act / Assert
    with pytest.raises(BacklogError, match="not found via GraphQL"):
        create_project(title="My Board")


def test_create_project_graphql_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_project propagates BacklogError raised by _graphql_request.

    Tests: create_project error propagation
    How: Raise BacklogError on first _graphql_request call; verify it propagates.
    Why: GraphQL errors must surface as BacklogError for consistent handling.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.owner.login = "acme"
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)
    monkeypatch.setattr(
        "backlog_core.operations._graphql_request",
        lambda *a, **kw: (_ for _ in ()).throw(BacklogError("GraphQL: token lacks scopes")),
    )

    from backlog_core.operations import create_project

    # Act / Assert
    with pytest.raises(BacklogError, match="token lacks scopes"):
        create_project(title="My Board")


def test_create_project_whitespace_title_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_project raises ValidationError for whitespace-only titles.

    Tests: create_project whitespace title validation
    How: Pass title consisting only of spaces; expect ValidationError.
    Why: strip() check must catch whitespace-only strings, not just empty strings.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import create_project

    # Act / Assert
    with pytest.raises(ValidationError, match="title must not be empty"):
        create_project(title="   ")


# ---------------------------------------------------------------------------
# Server layer: backlog_list_projects tool
# ---------------------------------------------------------------------------


async def test_backlog_list_projects_success_returns_projects_list() -> None:
    """backlog_list_projects tool returns projects list with count and output keys.

    Tests: backlog_list_projects server tool success path
    How: Patch list_projects with fake result; verify response shape.
    Why: Verifies the tool is registered and wired to the operation.
    """
    # Arrange
    fake_result = {
        "projects": [
            {
                "id": "PVT_1",
                "title": "Roadmap",
                "number": 1,
                "url": "https://github.com/orgs/acme/projects/1",
                "closed": False,
                "short_description": "",
            }
        ],
        "count": 1,
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.list_projects", return_value=fake_result):
        # Act
        result = await _call("backlog_list_projects", {})

    # Assert
    assert result["count"] == 1
    assert len(result["projects"]) == 1
    assert result["projects"][0]["id"] == "PVT_1"
    assert "messages" in result
    assert "warnings" in result


async def test_backlog_list_projects_passes_owner_and_limit() -> None:
    """backlog_list_projects forwards owner and limit to list_projects.

    Tests: backlog_list_projects parameter forwarding
    How: Capture kwargs via side_effect; verify forwarding.
    Why: Without forwarding, filtering and pagination silently break.
    """
    # Arrange
    captured: dict[str, object] = {}

    def fake_list(repo: str = "", owner: str | None = None, limit: int = 20, output: object = None) -> dict:
        captured["owner"] = owner
        captured["limit"] = limit
        return {"projects": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_projects", side_effect=fake_list):
        # Act
        await _call("backlog_list_projects", {"owner": "myorg", "limit": 5})

    # Assert
    assert captured["owner"] == "myorg"
    assert captured["limit"] == 5


async def test_backlog_list_projects_backlog_error_returns_error_key() -> None:
    """backlog_list_projects returns dict with error key on BacklogError.

    Tests: backlog_list_projects error handling
    How: Raise BacklogError from patched list_projects; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.list_projects", side_effect=BacklogError("Token missing")):
        # Act
        result = await _call("backlog_list_projects", {})

    # Assert
    assert "error" in result
    assert "Token missing" in result["error"]


async def test_backlog_list_projects_empty_result() -> None:
    """backlog_list_projects returns count=0 and empty list when no projects exist.

    Tests: backlog_list_projects empty response
    How: Patch list_projects to return empty; verify structure.
    Why: Consumers must handle empty results without KeyError.
    """
    # Arrange
    fake_result = {"projects": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_projects", return_value=fake_result):
        # Act
        result = await _call("backlog_list_projects", {})

    # Assert
    assert result["count"] == 0
    assert result["projects"] == []


# ---------------------------------------------------------------------------
# Server layer: backlog_create_project tool
# ---------------------------------------------------------------------------


async def test_backlog_create_project_success_returns_project_fields() -> None:
    """backlog_create_project tool returns project_id, title, url, and number.

    Tests: backlog_create_project server tool success path
    How: Patch create_project with fake result; verify response keys.
    Why: Callers need project_id immediately after creation.
    """
    # Arrange
    fake_result = {
        "project_id": "PVT_new",
        "title": "Sprint Board",
        "url": "https://github.com/orgs/acme/projects/5",
        "number": 5,
        "messages": ["  Created project 'Sprint Board' (#5)"],
        "warnings": [],
    }

    with patch("backlog_core.operations.create_project", return_value=fake_result):
        # Act
        result = await _call("backlog_create_project", {"title": "Sprint Board"})

    # Assert
    assert result["project_id"] == "PVT_new"
    assert result["title"] == "Sprint Board"
    assert result["number"] == 5
    assert "messages" in result


async def test_backlog_create_project_forwards_title_and_owner() -> None:
    """backlog_create_project forwards title and owner to create_project.

    Tests: backlog_create_project parameter forwarding
    How: Capture kwargs via side_effect; verify title and owner forwarded.
    Why: Owner determines which org/user the project is created under.
    """
    # Arrange
    captured: dict[str, object] = {}

    def fake_create(repo: str = "", title: str = "", owner: str | None = None, output: object = None) -> dict:
        captured["title"] = title
        captured["owner"] = owner
        return {"project_id": "PVT_x", "title": title, "url": "", "number": 1, "messages": [], "warnings": []}

    with patch("backlog_core.operations.create_project", side_effect=fake_create):
        # Act
        await _call("backlog_create_project", {"title": "My Board", "owner": "myorg"})

    # Assert
    assert captured["title"] == "My Board"
    assert captured["owner"] == "myorg"


async def test_backlog_create_project_backlog_error_returns_error_key() -> None:
    """backlog_create_project returns dict with error key on BacklogError.

    Tests: backlog_create_project error handling
    How: Raise BacklogError from patched create_project; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.create_project", side_effect=BacklogError("GraphQL mutation failed")):
        # Act
        result = await _call("backlog_create_project", {"title": "New Board"})

    # Assert
    assert "error" in result
    assert "GraphQL mutation failed" in result["error"]
