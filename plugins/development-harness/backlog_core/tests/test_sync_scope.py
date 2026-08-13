"""Regression tests for finalization sync scope after GitHub issue #2452.

The MCP schema still excludes the never-implemented ``flush_only`` input. Explicit sync
reconciles linked provider references, while selector pull reconciles one targeted reference.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, ReconcileRequest, ReconcileResult, ReconcileScope
from backlog_core.operations import pull_by_selector, sync_items
from backlog_core.server import backlog_sync

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# Path to the finalization workflow file that was corrected by #2452.
# Resolves relative to this test file: ../../.. → plugins/development-harness/
_FINALLY_MD = Path(__file__).parent.parent.parent / "skills/work-backlog-item/references/workflows/groom/finally.md"


class _SyncBackend:
    def __init__(self, items: list[BacklogItem], result: ReconcileResult) -> None:
        self.items = items
        self.result = result
        self.requests: list[ReconcileRequest] = []

    def list_work_items(self) -> list[BacklogItem]:
        return self.items

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
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
        assert backend.requests == [ReconcileRequest(scope=ReconcileScope.LINKED, references=["12"], dry_run=True)]
        assert result["created"] == 1
        assert result["pushed"] == 2

    def test_finally_md_does_not_reference_flush_only(self) -> None:
        """finally.md must not contain any reference to the phantom flush_only parameter.

        The flush_only=true documentation was removed in #2452 (Path B doc-only fix).
        This test reads the actual file from disk and fails if flush_only is found
        anywhere in the content — preventing accidental re-introduction.
        """
        # Arrange
        assert _FINALLY_MD.exists(), (
            f"finally.md not found at expected path: {_FINALLY_MD}. "
            "Check that the skills directory structure is intact."
        )

        # Act
        content = _FINALLY_MD.read_text(encoding="utf-8")

        # Assert
        assert "flush_only" not in content, (
            "finally.md must not reference 'flush_only' — this parameter was removed "
            "in #2452 because it was never implemented in the MCP schema. "
            "Any re-introduction must be accompanied by an actual implementation, "
            "which requires a separate architectural decision (not Path B)."
        )

    def test_backlog_pull_selector_refreshes_single_item(self, mocker: MockerFixture) -> None:
        backend = _SyncBackend([], ReconcileResult(file_paths={"#2452": "cache://2452"}))
        mocker.patch("backlog_core.operations.get_config", return_value=SimpleNamespace(backend=backend))

        result = pull_by_selector("#2452")

        assert backend.requests == [
            ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#2452"], include_diff=False)
        ]
        assert result["file_path"] == "cache://2452"
