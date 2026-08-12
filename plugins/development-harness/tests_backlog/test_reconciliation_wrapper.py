from __future__ import annotations

from pathlib import Path

import backlog_core.models as _models
import pytest
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.models import ReconcileResult
from backlog_core.operations import refresh_local_cache_from_github


class _SyncProviderStub:
    def fetch_snapshot(self, request: object) -> object:
        raise AssertionError(f"unexpected snapshot request: {request!r}")

    def apply_patches(self, patches: list[object]) -> list[object]:
        raise AssertionError(f"unexpected patches: {patches!r}")


@pytest.fixture
def sync_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _SyncProviderStub:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    monkeypatch.setattr(
        _models,
        "_config",
        _models.BacklogConfig(repo_root=tmp_path, backlog_dir=backlog_dir, default_repo=""),
    )
    provider = _SyncProviderStub()
    set_config(BacklogConfig(backend=provider))
    return provider


def test_refresh_wrapper_maps_reconciliation_results(sync_provider, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a SyncProvider and completed reconciliation outcomes
    captured: list[object] = []

    def reconcile(provider: object, request: object) -> ReconcileResult:
        captured.append(request)
        return ReconcileResult(local_updates=2, deleted_provider_items=1)

    monkeypatch.setattr("backlog_core.operations.reconcile_backlog", reconcile)

    # When: the startup-compatible refresh wrapper runs
    result = refresh_local_cache_from_github()

    # Then: it maps the new result into its stable public keys
    assert captured
    assert result["refreshed"] == 2
    assert result["reconciled"] == 1
