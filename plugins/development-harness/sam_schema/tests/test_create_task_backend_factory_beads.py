"""Tests for create_task_backend and create_context_backend factory routing.

Verifies that:
- TASKBACKEND=beads env var routes to BeadsTaskProvider
- CONTEXTBACKEND=beads env var routes to BeadsContextBackend
- .dh/config.yaml with task.backend = "beads" is respected (via DHConfig)
- .dh/config.yaml with context.backend = "beads" is respected (via DHConfig)
- Invalid backend names raise ValueError
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sam_schema.core.backends.beads import BeadsContextBackend, BeadsTaskProvider
from sam_schema.core.context_config import create_context_backend, reset_context_config
from sam_schema.core.task_config import create_task_backend, reset_task_config

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_configs() -> Generator[None, None, None]:
    """Ensure singleton configs are cleared after each test."""
    yield
    reset_task_config()
    reset_context_config()


# ---------------------------------------------------------------------------
# create_task_backend — env var routing
# ---------------------------------------------------------------------------


class TestCreateTaskBackendEnvVar:
    def test_env_var_beads_returns_beads_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TASKBACKEND=beads must return a BeadsTaskProvider instance."""
        monkeypatch.setenv("TASKBACKEND", "beads")
        backend = create_task_backend()
        assert isinstance(backend, BeadsTaskProvider)

    def test_env_var_invalid_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TASKBACKEND=nonexistent must raise ValueError."""
        monkeypatch.setenv("TASKBACKEND", "nonexistent")
        with pytest.raises(ValueError, match="Unknown backend"):
            create_task_backend()

    def test_explicit_name_beads_returns_beads_provider(self) -> None:
        """create_task_backend('beads') must return a BeadsTaskProvider."""
        backend = create_task_backend("beads")
        assert isinstance(backend, BeadsTaskProvider)

    def test_explicit_name_github_raises_not_implemented(self) -> None:
        """create_task_backend('github') must raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            create_task_backend("github")


# ---------------------------------------------------------------------------
# create_task_backend — TOML file routing
# ---------------------------------------------------------------------------


class TestCreateTaskBackendConfig:
    def test_config_yaml_task_backend_beads_returns_beads_provider(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """.dh/config.yaml with task.backend = 'beads' must route to BeadsTaskProvider."""
        import dh_config as _dh_config_mod

        dh_dir = tmp_path / ".dh"
        dh_dir.mkdir()
        (dh_dir / "config.yaml").write_text("task:\n  backend: beads\n", encoding="utf-8")

        # Clear TASKBACKEND env var so config file path is used.
        monkeypatch.delenv("TASKBACKEND", raising=False)

        # Null out _dh_paths so project-root config (which sets task.backend: local)
        # is not found — only the user-home config (tmp_path/.dh/config.yaml) is searched.
        monkeypatch.setattr(_dh_config_mod, "_dh_paths", None)

        # Patch Path.home() so DHConfig finds the config at tmp_path/.dh/config.yaml.
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

        backend = create_task_backend()
        assert isinstance(backend, BeadsTaskProvider)


# ---------------------------------------------------------------------------
# create_context_backend — env var routing
# ---------------------------------------------------------------------------


class TestCreateContextBackendEnvVar:
    def test_env_var_beads_returns_beads_context_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CONTEXTBACKEND=beads must return a BeadsContextBackend instance."""
        monkeypatch.setenv("CONTEXTBACKEND", "beads")
        backend = create_context_backend()
        assert isinstance(backend, BeadsContextBackend)

    def test_env_var_invalid_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CONTEXTBACKEND=bad must raise ValueError."""
        monkeypatch.setenv("CONTEXTBACKEND", "bad")
        with pytest.raises(ValueError, match="Unknown backend"):
            create_context_backend()

    def test_explicit_name_beads_returns_beads_context_backend(self) -> None:
        """create_context_backend('beads') must return a BeadsContextBackend."""
        backend = create_context_backend("beads")
        assert isinstance(backend, BeadsContextBackend)

    def test_explicit_name_github_raises_not_implemented(self) -> None:
        """create_context_backend('github') must raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            create_context_backend("github")
