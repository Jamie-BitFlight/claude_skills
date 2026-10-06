"""Tests for the live context-backend factory route."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sam_schema.core.backends.beads import BeadsContextBackend
from sam_schema.core.context_config import create_context_backend, reset_context_config
from sam_schema.core.exceptions import SamError

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_configs() -> Generator[None, None, None]:
    """Ensure singleton configs are cleared after each test."""
    yield
    reset_context_config()


# ---------------------------------------------------------------------------
# create_context_backend — env var routing
# ---------------------------------------------------------------------------


class TestCreateContextBackendEnvVar:
    def test_env_var_beads_returns_beads_context_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CONTEXTBACKEND=beads must return a BeadsContextBackend instance."""
        monkeypatch.setenv("CONTEXTBACKEND", "beads")
        backend = create_context_backend()
        assert isinstance(backend, BeadsContextBackend)

    def test_env_var_invalid_raises_sam_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CONTEXTBACKEND=bad must raise SamError."""
        monkeypatch.setenv("CONTEXTBACKEND", "bad")
        with pytest.raises(SamError, match="Unknown backend"):
            create_context_backend()

    def test_explicit_name_beads_returns_beads_context_backend(self) -> None:
        """create_context_backend('beads') must return a BeadsContextBackend."""
        backend = create_context_backend("beads")
        assert isinstance(backend, BeadsContextBackend)

    def test_explicit_name_github_raises_not_implemented(self) -> None:
        """create_context_backend('github') must raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            create_context_backend("github")
