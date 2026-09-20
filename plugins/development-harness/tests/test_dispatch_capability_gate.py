"""Direct unit tests for dh_core.operations.dispatch_stale_check / dispatch_conflicts.

Both functions previously had no direct test: the only existing coverage
(``test_frontend_parity_ops.py``'s CLI-forwarding test) fully mocks
``dh_core.operations.dispatch_stale_check``/``dispatch_conflicts`` rather than
calling the real implementation, so the ``UnsupportedBackendCapabilityError``
handling branch and its ``to_response()`` shape were unverified by any test.
``backlog_core.server``'s async MCP tools are thin ``asyncio.to_thread``
delegates to these same functions (T-P6-DEDUP), so exercising the real
functions here also covers the MCP boundary's failure path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import dh_core.operations as _dh_ops
import pytest
from backlog_core.backend_protocol import reset_config as _reset_bp_config, set_config as _set_bp_config
from backlog_core.backend_types import BacklogConfig as _BacklogConfig
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import ContentUnavailableError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def sqlite_backend():
    """Wire a real SQLiteBackend (supports_github_extras=False) as the active config.

    ``SQLiteBackend`` leaves its connection open with no lifecycle owner, so
    teardown closes it explicitly — an unclosed connection fails this repo's
    strict warning-as-error validation policy (AGENTS.md #18) with a
    ResourceWarning.
    """
    backend = SQLiteBackend(":memory:")
    _set_bp_config(_BacklogConfig(backend=backend))
    yield
    _reset_bp_config()
    backend._conn.close()


@pytest.mark.unit
def test_dispatch_stale_check_reports_capability_gap_on_non_github_backend(
    sqlite_backend: None, mocker: MockerFixture
) -> None:
    """dispatch_stale_check returns a structured capability-gap dict, not a crash.

    Why: this is the real function server.py now delegates to unchanged; a
         non-GitHub backend must produce UnsupportedBackendCapabilityError's
         to_response() shape, naming this specific operation.
    """
    mocker.patch("dh_core.operations._read_dispatch_plan", return_value=object())

    result = _dh_ops.dispatch_stale_check(milestone_number=42)

    assert result["unsupported_capability"] == "github_extras"
    assert result["backend"] == "SQLiteBackend"
    assert result["milestone_number"] == 42
    assert "dispatch_stale_check" in result["error"]


@pytest.mark.unit
def test_dispatch_conflicts_reports_capability_gap_on_non_github_backend(sqlite_backend: None) -> None:
    """dispatch_conflicts returns a structured capability-gap dict, not a crash.

    Why: same contract as dispatch_stale_check, exercised on the real function.
    """
    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["unsupported_capability"] == "github_extras"
    assert result["backend"] == "SQLiteBackend"
    assert result["milestone_number"] == 42
    assert "dispatch_conflicts" in result["error"]


@pytest.mark.unit
def test_dispatch_conflicts_reads_canonical_systems_inventory(mocker: MockerFixture) -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    authoritative_bodies = [
        "\n".join([
            "## Impact Radius",
            "SCOPE_EXPANSION: None.",
            "IMPACT_RADIUS_COMPLETE: Written to item A.",
            "",
            "### Change Frame",
            "- Delta: first",
            "",
            "### Systems Inventory",
            f"- `{shared}` | Role: producer | Risk: HIGH",
            "",
            "### Excluded Candidates and Unknown Frontier",
            "- Unknown: `plugins/a-unknown.py` - inspect later",
            "",
            "## Fact-Check",
            "Unrelated section.",
        ]),
        "\n".join([
            "## Impact Radius",
            "SCOPE_EXPANSION: None.",
            "IMPACT_RADIUS_COMPLETE: Written to item B.",
            "",
            "### Change Frame",
            "- Delta: second",
            "",
            "### Systems Inventory",
            f"- `{shared}` | Role: consumer | Risk: MEDIUM",
            "",
            "### Excluded Candidates and Unknown Frontier",
            "- Unknown: `plugins/b-unknown.py` - inspect later",
            "",
            "## Fact-Check",
            "Unrelated section.",
        ]),
    ]
    github_backend = mocker.Mock()
    github_backend.get_github.return_value = mocker.Mock(full_name="owner/repo")
    github_backend.sync_issues_graphql.return_value = [
        {"id": f"issue-{number}", "title": title, "number": number, "body": f"Human-owned body for {title}"}
        for number, title in enumerate(("A", "B"), start=1)
    ]
    github_backend.resolve_issue_body.side_effect = authoritative_bodies
    mocker.patch.object(_dh_ops, "get_config", return_value=mocker.Mock(backend=object()))
    mocker.patch.object(_dh_ops, "require_github_extras", return_value=github_backend)

    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["count"] == 1
    assert result["conflict_groups"][0]["items"] == ["A", "B"]
    assert shared in result["conflict_groups"][0]["reason"]
    assert github_backend.resolve_issue_body.call_count == 2


@pytest.mark.unit
@pytest.mark.parametrize("body_shape", ["legacy_nested", "section_wrapped"])
def test_dispatch_conflicts_reads_rendered_impact_radius_shapes(body_shape: str, mocker: MockerFixture) -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    if body_shape == "legacy_nested":
        radius = f"## Groomed (2026-09-20)\n\n### Impact Radius\n\n- {shared}\n\n### Fact-Check\n\nVerified."
    else:
        radius = "\n".join([
            "## Impact Radius",
            "",
            "<div><sub>2026-09-20</sub></div>",
            "",
            "## Impact Radius",
            "",
            "### Systems Inventory",
            f"- `{shared}` | Role: producer",
            "",
            "## Fact-Check",
            "Verified.",
        ])
    github_backend = mocker.Mock()
    github_backend.get_github.return_value = mocker.Mock(full_name="owner/repo")
    github_backend.sync_issues_graphql.return_value = [
        {"id": f"issue-{number}", "title": title, "number": number, "body": "Human-owned body"}
        for number, title in enumerate(("A", "B"), start=1)
    ]
    github_backend.resolve_issue_body.side_effect = [radius, radius]
    mocker.patch.object(_dh_ops, "get_config", return_value=mocker.Mock(backend=object()))
    mocker.patch.object(_dh_ops, "require_github_extras", return_value=github_backend)

    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["count"] == 1
    assert result["conflict_groups"][0]["items"] == ["A", "B"]
    assert result["conflict_groups"][0]["reason"] == f"Shared systems: {shared}"


@pytest.mark.unit
def test_dispatch_conflicts_accepts_atx_closing_hashes(mocker: MockerFixture) -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    body = f"## Impact Radius ##\n- `{shared}`\n## Fact-Check ##\nVerified."
    github_backend = mocker.Mock()
    github_backend.get_github.return_value = mocker.Mock(full_name="owner/repo")
    github_backend.sync_issues_graphql.return_value = [
        {"id": f"issue-{number}", "title": title, "number": number, "body": "Human-owned body"}
        for number, title in enumerate(("A", "B"), start=1)
    ]
    github_backend.resolve_issue_body.side_effect = [body, body]
    mocker.patch.object(_dh_ops, "get_config", return_value=mocker.Mock(backend=object()))
    mocker.patch.object(_dh_ops, "require_github_extras", return_value=github_backend)

    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["count"] == 1
    assert result["conflict_groups"][0]["reason"] == f"Shared systems: {shared}"


@pytest.mark.unit
def test_dispatch_conflicts_ignores_impact_radius_headings_inside_fences(mocker: MockerFixture) -> None:
    shared = "plugins/development-harness/backlog_core/operations.py"
    authoritative_bodies = [
        "\n".join([
            "## Impact Radius",
            "",
            "### Systems Inventory",
            f"- `{shared}` | Role: consumer",
            "",
            "## Fact-Check",
            "```markdown",
            "## Impact Radius",
            "### Systems Inventory",
            f"- `plugins/example-{number}.py` | Role: example",
            "```",
        ])
        for number in (1, 2)
    ]
    github_backend = mocker.Mock()
    github_backend.get_github.return_value = mocker.Mock(full_name="owner/repo")
    github_backend.sync_issues_graphql.return_value = [
        {"id": f"issue-{number}", "title": title, "number": number, "body": "Human-owned body"}
        for number, title in enumerate(("A", "B"), start=1)
    ]
    github_backend.resolve_issue_body.side_effect = authoritative_bodies
    mocker.patch.object(_dh_ops, "get_config", return_value=mocker.Mock(backend=object()))
    mocker.patch.object(_dh_ops, "require_github_extras", return_value=github_backend)

    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["count"] == 1
    assert result["conflict_groups"][0]["reason"] == f"Shared systems: {shared}"


@pytest.mark.unit
def test_extract_impact_radius_prefers_outer_section_over_later_subsection() -> None:
    body = "## Impact Radius\n- shared.py\n## Fact-Check\n### Impact Radius\nNo scope change."

    assert _dh_ops._extract_impact_radius_section(body) == "- shared.py"


@pytest.mark.unit
def test_extract_impact_radius_uses_ast_level_for_indented_heading_boundary() -> None:
    body = "  ## Impact Radius\n- shared.py\n## Systems Inventory\n- unrelated.py"

    assert _dh_ops._extract_impact_radius_section(body) == "- shared.py"


@pytest.mark.unit
def test_dispatch_conflicts_fails_closed_when_authoritative_body_is_unavailable(mocker: MockerFixture) -> None:
    github_backend = mocker.Mock()
    github_backend.get_github.return_value = mocker.Mock(full_name="owner/repo")
    github_backend.sync_issues_graphql.return_value = [
        {"id": "issue-1", "title": "A", "number": 1, "body": "Human-owned body"}
    ]
    github_backend.resolve_issue_body.side_effect = ContentUnavailableError("head record unavailable")
    mocker.patch.object(_dh_ops, "get_config", return_value=mocker.Mock(backend=object()))
    mocker.patch.object(_dh_ops, "require_github_extras", return_value=github_backend)

    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result == {
        "error": "Could not resolve authoritative body for issue #1: head record unavailable",
        "milestone_number": 42,
    }
