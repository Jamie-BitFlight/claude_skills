"""Regression tests for finalization sync scope after GitHub issue #2452.

The MCP schema still excludes the never-implemented ``flush_only`` input. Explicit sync
reconciles linked provider references, while selector pull reconciles one targeted reference.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, ProviderSnapshot, ReconcileRequest, ReconcileResult, ReconcileScope
from backlog_core.operations import pull_by_selector, sync_items
from backlog_core.server import backlog_sync

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class _SyncBackend:
    def __init__(self, items: list[BacklogItem], result: ReconcileResult) -> None:
        self.items = items
        self.result = result
        self.requests: list[ReconcileRequest] = []

    def list_work_items(self) -> list[BacklogItem]:
        return self.items

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
        del snapshot
        self.requests.append(request)
        return self.result


class TestFinallyWorkflowFinalization:
    """Regression suite for Failure 2: phantom flush_only parameter (Path B doc-only fix).

    All four tests guard against re-introduction of the flush_only capability
    that was documented in finally.md but never implemented.
    """

    def test_backlog_sync_has_no_flush_only_parameter(self) -> None:
        """backlog_sync must not expose a flush_only parameter in its MCP schema.

        FastMCP builds the tool's inputSchema directly from the function's signature.
        Inspecting the signature is equivalent to inspecting the MCP schema — any
        parameter in the signature becomes a parameter in the schema, and vice versa.

        The flush_only parameter was described in finally.md as triggering a JSONL
        export, but this export was never implemented. Path B removes the documentation
        without adding an implementation. This test ensures no flush_only parameter
        is accidentally added to the function signature.
        """
        # Arrange
        sig = inspect.signature(backlog_sync)

        # Act: FastMCP injects `ctx: Context` at runtime — exclude it from the
        # user-visible parameter set, as it does not appear in the MCP schema.
        user_params = {name for name in sig.parameters if name != "ctx"}

        # Assert
        assert "flush_only" not in user_params, (
            f"backlog_sync must NOT expose a flush_only parameter. "
            f"User-facing parameters found: {sorted(user_params)}. "
            f"The flush_only capability was never implemented — do not add it."
        )

    def test_sync_items_reconciles_linked_backend_references(self, mocker: MockerFixture) -> None:
        items = [BacklogItem(reference="local-1", title="One", section="P1", issue="12")]
        backend = _SyncBackend(items, ReconcileResult(provider_patches=2))
        mocker.patch("backlog_core.operations.get_config", return_value=SimpleNamespace(backend=backend))
        mock_create = mocker.patch("backlog_core.operations.sync_create_missing_issues", return_value={"created": 1})

        result = sync_items(dry_run=True)

        mock_create.assert_called_once_with(items, "", True, output=mocker.ANY)
        assert backend.requests == [ReconcileRequest(scope=ReconcileScope.INCREMENTAL, dry_run=True)]
        assert result["created"] == 1
        assert result["pushed"] == 2

    def test_backlog_pull_selector_refreshes_single_item(self, mocker: MockerFixture) -> None:
        backend = _SyncBackend([], ReconcileResult(file_paths={"#2452": "cache://2452"}))
        mocker.patch("backlog_core.operations.get_config", return_value=SimpleNamespace(backend=backend))

        result = pull_by_selector("#2452")

        assert backend.requests == [
            ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#2452"], include_diff=False)
        ]
        assert result["file_path"] == "cache://2452"
