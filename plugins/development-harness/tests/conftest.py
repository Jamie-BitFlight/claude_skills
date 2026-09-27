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
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

# Ensure backlog_core package is importable when running tests from repo root.
# The package lives at plugins/development-harness/ (not installed as editable
# from root), so we add its parent directory to sys.path explicitly.
# Must run before any backlog_core imports below.
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Standalone script modules (cli_output, merge_layer, etc.) live in
# scripts/ and are imported by tests as bare module names.
_scripts_dir = _plugin_dir / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Standalone script modules that live under docs/ (assemble_graph.py) are
# also imported by tests as bare module names.
_docs_dir = _plugin_dir / "docs"
if str(_docs_dir) not in sys.path:
    sys.path.insert(0, str(_docs_dir))

import backlog_core.models as bc_models
import pytest
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig, ListPageResult
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BacklogItem,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    parse_issue_number,
)
from backlog_core.reconciliation import provider_item_to_backlog_item as _provider_item_to_backlog_item

if TYPE_CHECKING:
    from collections.abc import Callable

    from backlog_core.backend_types import ListPageRequest
    from backlog_core.models import GroomedData, Section
    from github.Repository import Repository


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
        self.provider_items: list[BacklogItem] = []
        self.reconcile_requests: list[ReconcileRequest] = []
        self.snapshot_requests: list[ReconcileRequest] = []
        self.page_requests: list[object] = []
        self.reconcile_result = ReconcileResult()

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Return explicitly seeded provider rows without consulting local intent."""
        self.snapshot_requests.append(request)
        items = [
            ProviderItem(
                provider_id=item.issue or item.reference,
                # Canonicalize to "#N" -- a real provider reference is always
                # this shape, regardless of how a fixture's own BacklogItem.issue
                # string happened to be spelled ("99" vs "#99"). A caller that
                # resolves a reference independently (e.g. a title search
                # returning a raw issue number) must find the same row a
                # differently-spelled fixture would otherwise hide from it.
                reference=(
                    f"#{number}"
                    if (number := parse_issue_number(item.issue or item.reference)) is not None
                    else (item.issue or item.reference)
                ),
                title=item.title,
                body=render_issue_body(item),
                state=("CLOSED" if item.status.casefold() in {"closed", "completed", "done", "resolved"} else "OPEN"),
                labels=list(item.metadata.labels),
                revision=item.metadata.updated_at or f"test-{item.issue}",
                milestone=item.metadata.milestone,
            )
            for item in self.provider_items
        ]
        if request.scope in {ReconcileScope.LINKED, ReconcileScope.TARGETED}:
            # Canonicalize both sides to "#N" -- a real provider always resolves
            # a targeted fetch by number, regardless of how a fixture's own
            # BacklogItem.issue string happened to be spelled ("99" vs "#99").
            by_reference = {item.reference: item for item in items}
            items = [
                by_reference.get(
                    reference,
                    ProviderItem(
                        provider_id="",
                        reference=reference,
                        title="",
                        body="",
                        state="",
                        labels=[],
                        revision="",
                        exists=False,
                    ),
                )
                for reference in request.references
            ]
        return ProviderSnapshot(items=items, sync_started_at="2026-09-24T00:00:00+00:00", pages_fetched=1)

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Return a structural repository stand-in carrying only ``full_name``."""
        del timeout
        return cast("Repository", SimpleNamespace(full_name=repo or "owner/repository"))

    def fetch_page(
        self, request: ListPageRequest, *, match: Callable[[BacklogItem, ProviderItem], bool], force_hydration: bool
    ) -> ListPageResult:
        """Apply *match* directly over ``provider_items`` (see ``RequestShapedListing``)."""
        del force_hydration
        self.page_requests.append(request)
        provider_items = [
            ProviderItem(
                provider_id=item.issue or item.reference,
                reference=item.issue or item.reference,
                title=item.title,
                body=render_issue_body(item),
                state=("CLOSED" if item.status.casefold() in {"closed", "completed", "done", "resolved"} else "OPEN"),
                labels=list(item.metadata.labels),
                revision=item.metadata.updated_at or f"test-{item.issue}",
                milestone=item.metadata.milestone,
            )
            for item in self.provider_items
        ]
        matched = [pi for pi in provider_items if match(_provider_item_to_backlog_item(pi), pi)]
        after_offset = matched[request.offset :]
        if request.limit > 0:
            has_more = len(after_offset) > request.limit
            page_items = after_offset[: request.limit]
        else:
            has_more = False
            page_items = after_offset
        return ListPageResult(
            items=page_items, has_more=has_more, total=len(matched), sync_started_at="2026-09-24T00:00:00+00:00"
        )

    def _fetch_issues_page_graphql(self, repo: object, owner: str, repo_name: str, **kwargs: object) -> object:
        """Unused by this double's own ``fetch_page`` -- present only to satisfy ``RequestShapedListing``."""
        raise NotImplementedError

    def search_issues_by_title(self, repo: str, selector: str) -> list[tuple[int, str]]:
        """Return ``(number, title)`` for every provider item whose title contains *selector*."""
        del repo
        return [
            (int(item.issue.lstrip("#")), item.title)
            for item in self.provider_items
            if item.issue and selector.lower() in item.title.lower()
        ]

    def confirm_issues_reachable(self, repo: str) -> None:
        """Answer every reachability check; this double has no transport to fail."""
        del repo

    def fetch_issue_titles(self, repo: str, *, open_only: bool = False) -> list[tuple[int, str]]:
        """Return every provider item's ``(number, title)``, open only when *open_only*."""
        del repo
        return [
            (int(item.issue.lstrip("#")), item.title)
            for item in self.provider_items
            if item.issue and not (open_only and item.status.casefold() in {"closed", "completed", "done", "resolved"})
        ]

    def pending_work_items(self, repo: str = "") -> list[BacklogItem]:
        """Return unlinked local intent separately from live provider rows."""
        del repo
        return [item.model_copy(deep=True) for item in self.list_work_items() if not item.issue]

    def put_work_item(self, item: BacklogItem, repo: str = "") -> None:
        """Accept the repository parameter required by GitHub-shaped tests."""
        del repo
        super().put_work_item(item)

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
        del snapshot
        self.reconcile_requests.append(request)
        return self.reconcile_result


# ---------------------------------------------------------------------------
# Shared fixtures for backlog scenario integration tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_backend(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> object:
    """Install an in-memory backend for every non-e2e test.

    Skips tests marked ``@pytest.mark.e2e``, which install their own live
    backend from a higher-scoped fixture. This fixture is function-scoped, so
    without the exemption it runs after that class-scoped setup and replaces
    the live backend with the in-memory double for every e2e test body —
    ``try_get_github()`` then returns ``None`` and ``add_item`` falls back to a
    local-only item with ``item_ref == ""`` instead of creating a real issue
    (#3546). The teardown ``reset_config()`` compounds it by discarding the
    class-scoped config after the first test in the class.
    """
    if request.node.get_closest_marker("e2e"):
        yield None
        return
    backend = ProviderMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    yield backend
    reset_config()


@pytest.fixture
def plain_memory_backend() -> InMemoryBackend:
    """Install the native backend for tests that exercise provider-neutral behavior."""
    backend = InMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    return backend


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
    existing = bc_models._config
    monkeypatch.setattr(
        bc_models,
        "_config",
        bc_models.BacklogConfig(
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
