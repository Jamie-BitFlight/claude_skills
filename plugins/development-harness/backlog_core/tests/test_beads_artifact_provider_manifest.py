"""Regression tests for BeadsArtifactProvider.get_manifest_bd issue_number field.

Background: ``_fetch_issue_and_manifest`` used ``ArtifactManifest(issue_number=0)``
as a sentinel when a beads issue had no stored manifest data.  ``0`` is not a valid
beads ID and caused cross-issue manifest confusion when multiple beads-backed issues
were active simultaneously.

Fix (issue #2442): Both empty-manifest return paths now pass ``issue_id`` to
``ArtifactManifest(issue_number=issue_id)`` so the actual beads nanoid is always
preserved in the returned manifest.
"""

from __future__ import annotations

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


def _provider_with_mock_runner(raw_json: object) -> BeadsArtifactProvider:
    """Return a BeadsArtifactProvider whose runner returns *raw_json* from run_json."""
    provider = BeadsArtifactProvider.__new__(BeadsArtifactProvider)
    provider._root_worktree = None  # type: ignore[attr-defined]
    runner_mock = MagicMock()
    runner_mock.run_json.return_value = raw_json
    provider._runner_instance = runner_mock  # type: ignore[attr-defined]
    return provider


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
