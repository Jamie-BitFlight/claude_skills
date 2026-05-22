"""Shared test configuration for development-harness tests.

Adds the plugin root to sys.path so ``from backlog_core.parsing import ...``
resolves correctly regardless of pytest invocation directory.

Shared fixtures for scenario integration tests:
- ``backlog_dir``: Redirects backlog state to tmp_path via DH_STATE_HOME for
  test isolation (uses dh_paths.backlog_dir() path conventions)
- ``mock_github``: Patches all gh_client.py functions at operations.py boundary
- ``write_test_item``: Factory for creating per-item files with valid frontmatter
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

# Ensure backlog_core package is importable when running tests from repo root.
# The package lives at plugins/development-harness/ (not installed as editable
# from root), so we add its parent directory to sys.path explicitly.
# Must run before any backlog_core imports below.
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Standalone script modules (dispatch_helper, manifest_schema, etc.) live in
# scripts/ and are imported by tests as bare module names.
_scripts_dir = _plugin_dir / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import backlog_core.models as _bc_models
import pytest

if TYPE_CHECKING:
    from backlog_core.models import GroomedData, Section


# ---------------------------------------------------------------------------
# Shared fixtures for backlog scenario integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect backlog state to a temp directory for test isolation.

    Sets DH_STATE_HOME so dh_paths resolves all state directories under
    tmp_path. Patches backlog_core.models.BACKLOG_DIR with the resolved
    dh_paths backlog directory so that parsing and operations (which access
    it via _models.BACKLOG_DIR) also see the temp path.

    Returns the directory path so tests can inspect created files.
    """
    import dh_paths

    # Override DH_STATE_HOME so dh_paths resolves state under tmp_path.
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))

    # Use a stable fake project root whose slug is deterministic.
    fake_project_root = tmp_path / "project"
    fake_project_root.mkdir(parents=True, exist_ok=True)

    bd = dh_paths.backlog_dir(project_root=fake_project_root)
    bd.mkdir(parents=True, exist_ok=True)

    # Redirect backlog_dir via _config so get_backlog_dir() returns the temp path.
    # parsing.py and operations.py call _models.get_backlog_dir(); patching _config
    # is the correct interception point after the BacklogConfig refactor.
    existing = _bc_models._config
    monkeypatch.setattr(
        _bc_models,
        "_config",
        _bc_models.BacklogConfig(
            repo_root=existing.repo_root if existing is not None else fake_project_root,
            backlog_dir=bd,
            default_repo=existing.default_repo if existing is not None else "",
        ),
    )
    return bd


@pytest.fixture
def mock_github(monkeypatch):
    """Patch all gh_client.py functions imported by operations.py.

    Returns dict of ``{function_name: MagicMock}`` for per-test configuration.
    Override return values in individual tests like::

        mock_github["create_issue_for_item"].return_value = 99
    """
    from backlog_core.models import IssueLocalFields

    mocks: dict[str, MagicMock] = {}
    defaults: dict[str, object] = {
        "try_get_github": None,
        "get_github": MagicMock(),
        "create_issue_for_item": 42,
        "close_github_issue": None,
        "resolve_github_issue": None,
        "check_open_prs_for_issue": [],
        "batch_fetch_statuses": {},
        "apply_status_in_progress": None,
        "apply_status_verified": None,
        "fetch_open_issues_by_title": {},
        "view_enrich_from_github": False,
        "sync_groomed_to_github_issue": True,
        "fetch_github_issue_body": "issue body from github",
        "issue_to_local_fields": IssueLocalFields(
            title="Test", body="body", priority="P1", item_type="Feature", status="open"
        ),
    }
    for name, default in defaults.items():
        mock = MagicMock(return_value=default)
        monkeypatch.setattr(f"backlog_core.operations.{name}", mock)
        mocks[name] = mock
    return mocks


@pytest.fixture
def write_test_item(backlog_dir: Path) -> object:
    """Factory: create per-item ``.yaml`` file loadable by yaml_io in test backlog_dir.

    Creates pure-YAML backlog item files via ``yaml_io.save_item()``, replacing the
    legacy ``build_backlog_frontmatter`` + ``.md`` approach.

    Usage::

        filepath = write_test_item("My Title", priority="P0", issue="#42")

    Returns the Path to the created ``.yaml`` file.
    """

    def _write(
        title: str,
        priority: str = "P1",
        issue: str = "",
        description: str = "Test item",
        status: str = "open",
        type_val: str = "Feature",
        sections: dict[str, Section | GroomedData] | None = None,
    ) -> Path:
        from backlog_core.models import BacklogItem, BacklogItemMetadata
        from backlog_core.parsing import title_to_slug
        from backlog_core.yaml_io import save_item

        slug = title_to_slug(title)
        filepath = backlog_dir / f"{priority.lower()}-{slug}.yaml"
        item = BacklogItem(
            title=title,
            description=description,
            metadata=BacklogItemMetadata(
                source="test",
                added="2026-01-01",
                priority=priority,
                item_type=type_val,
                status=status,
                issue=issue,
                topic=slug,
            ),
            sections=sections or {},
        )
        save_item(item, filepath)
        return filepath

    return _write


# ---------------------------------------------------------------------------
# Gate token fixtures
# ---------------------------------------------------------------------------

_TEST_SESSION_ID = "test-session-id-for-gate-token"
TEST_GATE_TOKEN = f"{_TEST_SESSION_ID}:test-fixed-gate-token-aabbccdd"


@pytest.fixture(autouse=True)
def _patch_gate_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Write the fixed gate token to a temp session file for all non-e2e tests.

    Sets DH_STATE_HOME so that backlog_core.server._read_gate_token() finds the
    token at the path encoded in the token value itself. Skips for tests marked
    with @pytest.mark.e2e so that live validation tests use the real token written
    by the skill at load time.
    """
    if request.node.get_closest_marker("e2e"):
        return
    dh_state = tmp_path / "dh_state"
    token_dir = dh_state / "sessions" / _TEST_SESSION_ID
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / ".gate-token").write_text(TEST_GATE_TOKEN, encoding="utf-8")
    monkeypatch.setenv("DH_STATE_HOME", str(dh_state))


@pytest.fixture
def gate_token() -> str:
    """Return the fixed gate token used by the file-backed server in tests."""
    return TEST_GATE_TOKEN


# ---------------------------------------------------------------------------
# Quality gate fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def built_plan() -> str:
    """Standard quality gate plan used by TestBuildQualityGatePlan tests."""
    from sam_schema.core.quality_gates import build_quality_gate_plan

    return build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001")
