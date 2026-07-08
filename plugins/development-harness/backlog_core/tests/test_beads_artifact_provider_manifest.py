"""Regression tests for BeadsArtifactProvider.get_manifest_bd issue_number field.

Background: ``_fetch_issue_and_manifest`` used ``ArtifactManifest(issue_number=0)``
as a sentinel when a beads issue had no stored manifest data.  ``0`` is not a valid
beads ID and caused cross-issue manifest confusion when multiple beads-backed issues
were active simultaneously.

Fix (issue #2442): Both empty-manifest return paths now pass ``issue_id`` to
``ArtifactManifest(issue_number=issue_id)`` so the actual beads nanoid is always
preserved in the returned manifest.

Follow-up fix (Codex review on #2645): the two empty-manifest paths were the only
paths corrected. An issue with a manifest already persisted by pre-fix code — with
``issue_number: 0`` baked into the stored JSON — was returned unchanged by
``_extract_manifest_from_metadata``, and ``ArtifactRegistry.register()`` preserves
whatever ``issue_number`` the input manifest carries via ``model_copy``. So a stale
``0`` written before the fix would survive indefinitely across read/register/persist
cycles. ``_fetch_issue_and_manifest`` now normalizes ``manifest.issue_number`` to
*issue_id* whenever a stored manifest is successfully parsed and its value differs.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from backlog_core.backends.beads_artifact_provider import BeadsArtifactProvider

# Minimal valid bd-show JSON (single-element list as returned by ``bd show``)
_ISSUE_ID = "bd-a3f8"

_BD_SHOW_NO_METADATA: list[dict] = [
    {"id": _ISSUE_ID, "title": "Test issue", "status": "open", "issue_type": "task", "priority": 2}
]

_BD_SHOW_METADATA_NO_DH_ARTIFACTS: list[dict] = [
    {
        "id": _ISSUE_ID,
        "title": "Test issue",
        "status": "open",
        "issue_type": "task",
        "priority": 2,
        "metadata": {"other_key": "some_value"},
    }
]

# A manifest persisted by pre-fix code: issue_number is the stale sentinel 0,
# but one real artifact entry is present — normalization must preserve it.
_STALE_MANIFEST_JSON: str = json.dumps({
    "issue_number": 0,
    "artifacts": [
        {
            "artifact-type": "architect",
            "artifact_id": "plan/architect-foo.md",
            "status": "current",
            "created-at": "2026-01-01T00:00:00Z",
            "agent": "swarm-task-planner",
            "storage-tier": "remote",
        }
    ],
    "last-updated": "2026-01-01T00:00:00Z",
})

_BD_SHOW_STALE_ISSUE_NUMBER: list[dict] = [
    {
        "id": _ISSUE_ID,
        "title": "Test issue",
        "status": "open",
        "issue_type": "task",
        "priority": 2,
        "metadata": {"dh.artifacts": _STALE_MANIFEST_JSON},
    }
]


def _provider_with_mock_runner(raw_json: object) -> BeadsArtifactProvider:
    """Return a BeadsArtifactProvider whose runner returns *raw_json* from run_json."""
    runner_mock = MagicMock()
    runner_mock.run_json.return_value = raw_json
    return BeadsArtifactProvider(runner=runner_mock)


class TestGetManifestBdIssueNumberPreservation:
    """get_manifest_bd always returns manifest.issue_number == issue_id."""

    def test_no_metadata_returns_issue_id_not_zero(self) -> None:
        """When bd show returns no metadata, issue_number must be the beads ID string.

        Regression for #2442: previously returned ArtifactManifest(issue_number=0).
        """
        provider = _provider_with_mock_runner(_BD_SHOW_NO_METADATA)

        manifest = provider.get_manifest_bd(_ISSUE_ID)

        assert manifest.issue_number == _ISSUE_ID

    def test_metadata_without_dh_artifacts_returns_issue_id_not_zero(self) -> None:
        """When metadata has no dh.artifacts key, issue_number must be the beads ID string.

        Regression for #2442: previously returned ArtifactManifest(issue_number=0).
        """
        provider = _provider_with_mock_runner(_BD_SHOW_METADATA_NO_DH_ARTIFACTS)

        manifest = provider.get_manifest_bd(_ISSUE_ID)

        assert manifest.issue_number == _ISSUE_ID

    def test_zero_is_never_returned_as_issue_number(self) -> None:
        """Confirm the sentinel 0 value is gone from both empty-manifest paths."""
        for raw in (_BD_SHOW_NO_METADATA, _BD_SHOW_METADATA_NO_DH_ARTIFACTS):
            provider = _provider_with_mock_runner(raw)
            manifest = provider.get_manifest_bd(_ISSUE_ID)
            assert manifest.issue_number != 0, f"issue_number must not be sentinel 0; got {manifest.issue_number!r}"

    def test_stale_stored_manifest_issue_number_normalized(self) -> None:
        """A manifest persisted by pre-fix code with issue_number=0 is normalized on read.

        Regression for the Codex review finding on #2645: _extract_manifest_from_metadata
        returns a successfully-parsed manifest unchanged, and ArtifactRegistry.register()
        preserves whatever issue_number the input manifest carries via model_copy — so a
        stale 0 written before the #2442 fix would survive indefinitely across
        read/register/persist cycles without this normalization.
        """
        provider = _provider_with_mock_runner(_BD_SHOW_STALE_ISSUE_NUMBER)

        manifest = provider.get_manifest_bd(_ISSUE_ID)

        assert manifest.issue_number == _ISSUE_ID

    def test_stale_manifest_normalization_preserves_artifacts(self) -> None:
        """Normalizing issue_number must not drop or alter the existing artifacts list."""
        provider = _provider_with_mock_runner(_BD_SHOW_STALE_ISSUE_NUMBER)

        manifest = provider.get_manifest_bd(_ISSUE_ID)

        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].artifact_id == "plan/architect-foo.md"
