"""Tests for auto-registration of plan artifacts in backlog_update (T8).

Covers:
- _auto_register_plan_artifact registers task-plan artifact when item has issue
- _auto_register_plan_artifact is skipped when item has no issue number
- Registration failure does not block the call (best-effort, warns)
- Item with issue="#123" format is parsed correctly
- Item with malformed issue string logs warning and skips
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import (
    ArtifactManifest,
    ArtifactType,
    BacklogItem,
    ContentKind,
    ContentRef,
    ContentUnavailableError,
    Output,
)
from backlog_core.operations import _auto_register_plan_artifact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(issue: str = "", file_path: str = "") -> BacklogItem:
    """Return a minimal BacklogItem for testing."""
    return BacklogItem(title="Test Feature", issue=issue, file_path=file_path)


# ---------------------------------------------------------------------------
# Tests: _auto_register_plan_artifact
# ---------------------------------------------------------------------------


class TestAutoRegisterPlanArtifact:
    """Tests for the _auto_register_plan_artifact helper."""

    def test_auto_register_plan_artifact_with_issue_registers_task_plan(self) -> None:
        """When item has a linked issue, the plan is registered as task-plan artifact."""
        item = _make_item(issue="#42")
        out = Output()
        provider = InMemoryBackend()

        with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
            _auto_register_plan_artifact(item, "plan/tasks-1-foo.yaml", repo="owner/repo", output=out)

        record = provider.get_content(ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="#42", name="manifest"))
        manifest = ArtifactManifest.model_validate_json(record.content)
        entry = manifest.artifacts[0]
        assert entry.artifact_type == ArtifactType.TASK_PLAN
        assert entry.artifact_id == "plan/tasks-1-foo.yaml"
        assert any("Artifact registered" in m for m in out.messages)
        assert out.warnings == []

    def test_auto_register_plan_artifact_does_not_replace_unavailable_manifest(self) -> None:
        item = _make_item(issue="#42")
        provider = InMemoryBackend()
        provider.get_content = MagicMock(side_effect=ContentUnavailableError("offline cache miss"))
        provider.put_content = MagicMock()

        with (
            patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)),
            pytest.raises(ContentUnavailableError, match="offline cache miss"),
        ):
            _auto_register_plan_artifact(item, "plan/tasks-1-foo.yaml")

        provider.put_content.assert_not_called()

    def test_auto_register_plan_artifact_without_issue_skips_silently(self) -> None:
        """When item has no issue number, registration is skipped entirely."""
        item = _make_item(issue="")
        out = Output()

        with patch("backlog_core.operations.get_config") as get_config:
            _auto_register_plan_artifact(item, "plan/tasks-1-foo.yaml", repo="owner/repo", output=out)
            get_config.assert_not_called()

        assert out.warnings == []
        assert out.messages == []

    def test_auto_register_plan_artifact_registration_failure_does_not_raise(self) -> None:
        """Registration failure logs a warning but does not propagate the exception."""
        item = _make_item(issue="#99")
        out = Output()
        provider = InMemoryBackend()
        provider.get_content = MagicMock(side_effect=RuntimeError("provider unavailable"))
        provider.put_content = MagicMock()

        with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
            _auto_register_plan_artifact(item, "plan/tasks-1-bar.yaml", repo="owner/repo", output=out)

        assert any("WARNING" in w and "Artifact registration failed" in w for w in out.warnings)
        provider.put_content.assert_not_called()

    def test_auto_register_plan_artifact_malformed_issue_string_warns_and_skips(self) -> None:
        """Item with unparseable issue string logs a warning and does not call the provider."""
        item = _make_item(issue="not-a-number")
        out = Output()
        provider = InMemoryBackend()
        provider.get_content = MagicMock()
        provider.put_content = MagicMock()

        with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
            _auto_register_plan_artifact(item, "plan/tasks-1-foo.yaml", repo="owner/repo", output=out)

        provider.get_content.assert_not_called()
        provider.put_content.assert_not_called()
        assert any("WARNING" in w and "Could not parse issue number" in w for w in out.warnings)

    def test_auto_register_plan_artifact_issue_without_hash_prefix(self) -> None:
        """Issue string without '#' prefix (bare number) is still parsed correctly."""
        item = _make_item(issue="123")
        out = Output()
        provider = InMemoryBackend()

        with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
            _auto_register_plan_artifact(item, "plan/tasks-1-baz.yaml", repo="owner/repo", output=out)

        manifest = ArtifactManifest.model_validate_json(
            provider.get_content(
                ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="#123", name="manifest")
            ).content
        )
        assert manifest.artifacts[0].artifact_id == "plan/tasks-1-baz.yaml"
        assert out.warnings == []

    def test_auto_register_plan_artifact_provider_write_failure_warns(self) -> None:
        """Provider write failure logs a warning but does not propagate."""
        item = _make_item(issue="#7")
        out = Output()
        provider = InMemoryBackend()
        provider.put_content = MagicMock(side_effect=OSError("network timeout"))

        with patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=provider)):
            _auto_register_plan_artifact(item, "plan/tasks-1-qux.yaml", repo="owner/repo", output=out)

        assert any("WARNING" in w for w in out.warnings)
