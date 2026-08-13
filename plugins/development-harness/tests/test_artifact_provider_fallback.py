from __future__ import annotations

from types import SimpleNamespace

import backlog_core.server as _server
import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentUnavailableError


def test_get_artifact_provider_returns_configured_content_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = InMemoryBackend()
    monkeypatch.setattr(_server, "_get_config", lambda: SimpleNamespace(backend=backend))

    assert _server._get_artifact_provider() is backend


def test_get_artifact_provider_rejects_backend_without_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_server, "_get_config", lambda: SimpleNamespace(backend=object()))

    with pytest.raises(ContentUnavailableError, match="does not support artifact content"):
        _server._get_artifact_provider()
