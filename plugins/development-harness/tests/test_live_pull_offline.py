"""Offline proof for the live e2e "pull observes an independent provider edit" phase.

test_live_validation.py::test_live_crud_persists_changes_and_preserves_other_sections cannot run
without live GitHub credentials. This exercises the same mechanism -- pull persisting a provider
edit into the configured backend's own cache, then a provider-unavailable, allow_cached view
reading that same cache back -- with a real GitHubBackend and FileCache. Only the provider
seams are monkeypatched: fetch_snapshot for the pull, and get_github for the title lookup,
which resolves through GitHub search before any snapshot read.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from backlog_core import operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import BackendUnavailableError, ProviderItem, ProviderSnapshot, ReconcileRequest


def test_pull_then_offline_allow_cached_view_reads_writer_cache(tmp_path: Path) -> None:
    reference = "#48"
    changed_title = "Provider edit changed remotely"
    changed_body = "Provider edit not present in the writer cache."
    backend = GitHubBackend(repo="acct/repo", cache=FileCache(tmp_path / "writer"))
    set_config(BacklogConfig(backend=backend))
    try:
        changed_snapshot = ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="MDU6SXNzdWU0OA==",
                    reference=reference,
                    title=changed_title,
                    body=changed_body,
                    state="open",
                    labels=[],
                    revision="rev-1",
                )
            ],
            sync_started_at="2026-01-01T00:00:00Z",
        )

        def provider_edit(request: ReconcileRequest) -> ProviderSnapshot:
            return changed_snapshot

        with pytest.MonkeyPatch.context() as m:
            m.setattr(backend, "fetch_snapshot", provider_edit)
            operations.pull_by_selector(reference)

        def unavailable(*args: object, **kwargs: object) -> ProviderSnapshot:
            raise BackendUnavailableError("offline read-back after pull")

        with pytest.MonkeyPatch.context() as m:
            m.setattr(backend, "fetch_snapshot", unavailable)
            m.setattr(backend, "get_github", unavailable)
            pulled = operations.view_item(changed_title, allow_cached=True)

        assert pulled.status_source == "cache", pulled
        assert pulled.title == changed_title, pulled
        assert changed_body in pulled.body, pulled
    finally:
        reset_config()
