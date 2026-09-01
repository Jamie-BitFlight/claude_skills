"""Shared test configuration for development-harness tests.

Adds the plugin root to sys.path so ``from backlog_core.parsing import ...``
resolves correctly regardless of pytest invocation directory.

Shared fixtures for scenario integration tests:
- ``backlog_dir``: Redirects legacy path-specific tests to an isolated directory
- ``mock_github``: Patches GitHub delegates at the operations boundary
- ``write_test_item``: Creates work items through the configured backend
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

# Standalone script modules that live under docs/ (assemble_graph.py) are
# also imported by tests as bare module names.
_docs_dir = _plugin_dir / "docs"
if str(_docs_dir) not in sys.path:
    sys.path.insert(0, str(_docs_dir))

import backlog_core.models as _bc_models
import pytest
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ReconcileRequest, ReconcileResult

if TYPE_CHECKING:
    from backlog_core.models import GroomedData, Section


class ProviderMemoryBackend(InMemoryBackend):
    """Default per-test backend: an InMemoryBackend that also simulates GitHub.

    Dozens of operation-layer tests across ``tests/test_github_tools_*.py``
    patch only ``operations.get_github`` and then exercise the real
    ``GitHubExtras`` delegate methods (``sync_issues_graphql``,
    ``_fetch_milestones_graphql``, ``_projects_v2_list_query``, ...) that
    ``InMemoryBackend`` implements as local simulations. Those tests are
    deliberately simulating a GitHub-shaped backend, so ``supports_github_extras``
    is ``True`` here even though the base ``InMemoryBackend`` declares it
    ``False`` (see ``backends/memory_backend.py`` — a plain in-memory backend
    cannot return a real ``Repository``). Setting it centrally here, rather
    than in every individual test fixture, is the honest fix for the whole
    class of tests that use this double via the autouse ``_isolated_backend``
    fixture below.
    """

    supports_github_extras: bool = True

    def __init__(self) -> None:
        super().__init__()
        self.reconcile_requests: list[ReconcileRequest] = []
        self.reconcile_result = ReconcileResult()

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        self.reconcile_requests.append(request)
        return self.reconcile_result


# ---------------------------------------------------------------------------
# Shared fixtures for backlog scenario integration tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_backend(monkeypatch: pytest.MonkeyPatch) -> object:
    backend = ProviderMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    yield backend
    reset_config()


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
def write_test_item() -> object:
    def _write(
        title: str,
        priority: str = "P1",
        issue: str = "",
        description: str = "Test item",
        status: str = "open",
        type_val: str = "Feature",
        sections: dict[str, Section | GroomedData] | None = None,
    ) -> str:
        from backlog_core.models import BacklogItem, BacklogItemMetadata
        from backlog_core.parsing import title_to_slug

        slug = title_to_slug(title)
        reference = issue or f"{priority.lower()}-{slug}"
        item = BacklogItem(
            title=title,
            description=description,
            reference=reference,
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
        from backlog_core.backend_protocol import get_config

        get_config().backend.put_work_item(item)
        return reference

    return _write


# ---------------------------------------------------------------------------
# State isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Redirect DH_STATE_HOME to a temp directory for all non-e2e tests.

    Without this, dh_paths.state_root() falls back to the real ~/.dh/projects/{slug}/
    directory, letting any test that reaches it (dispatch state, SAM context, etc.)
    read or write real user state. Skips for tests marked @pytest.mark.e2e, which
    set up their own DH_STATE_HOME to exercise the real runtime path.
    """
    if request.node.get_closest_marker("e2e"):
        return
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))


# ---------------------------------------------------------------------------
# Quality gate fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def built_plan() -> str:
    """Standard quality gate plan used by TestBuildQualityGatePlan tests."""
    from sam_schema.core.quality_gates import build_quality_gate_plan

    return build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001")
