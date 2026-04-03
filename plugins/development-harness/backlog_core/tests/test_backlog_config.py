"""Tests for BacklogConfig and init_paths() in backlog_core.models."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import backlog_core.models as _models
from backlog_core.models import BacklogConfig, get_backlog_dir, get_config, get_default_repo, get_repo_root, init_paths


@pytest.fixture(autouse=True)
def _reset_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore _config to None after each test to isolate state."""
    monkeypatch.setattr(_models, "_config", None)


class TestGetConfigAutoInit:
    """get_config() lazily auto-initialises when _config is None and project root is discoverable."""

    def test_get_config_auto_inits_when_project_root_discoverable(self, tmp_path: Path) -> None:
        """get_config() succeeds when _resolve_repo_root succeeds."""
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            cfg = get_config()
        assert cfg.repo_root == tmp_path

    def test_get_config_raises_when_project_root_not_discoverable(self) -> None:
        """get_config() raises RuntimeError when _resolve_repo_root raises RuntimeError."""
        with (
            patch.object(_models, "_resolve_repo_root", side_effect=RuntimeError("no git root")),
            pytest.raises(RuntimeError, match="not initialised"),
        ):
            get_config()

    def test_get_repo_root_auto_inits(self, tmp_path: Path) -> None:
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            root = get_repo_root()
        assert root == tmp_path

    def test_get_backlog_dir_auto_inits(self, tmp_path: Path) -> None:
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            backlog_dir = get_backlog_dir()
        assert isinstance(backlog_dir, Path)

    def test_get_default_repo_auto_inits(self, tmp_path: Path) -> None:
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            repo = get_default_repo()
        assert isinstance(repo, str)

    def test_module_backlog_dir_attr_auto_inits(self, tmp_path: Path) -> None:
        """_models.BACKLOG_DIR access via __getattr__ auto-initialises when needed."""
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            val = _models.BACKLOG_DIR  # type: ignore[attr-defined]
        assert isinstance(val, Path)

    def test_module_repo_root_attr_auto_inits(self, tmp_path: Path) -> None:
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            val = _models._REPO_ROOT  # type: ignore[attr-defined]
        assert isinstance(val, Path)

    def test_module_default_repo_attr_auto_inits(self, tmp_path: Path) -> None:
        with patch.object(_models, "_resolve_repo_root", return_value=tmp_path):
            val = _models.DEFAULT_REPO  # type: ignore[attr-defined]
        assert isinstance(val, str)

    def test_auto_init_error_message_mentions_env_vars(self) -> None:
        """Error message guides the user to set environment variables."""
        with (
            patch.object(_models, "_resolve_repo_root", side_effect=RuntimeError("no git root")),
            pytest.raises(RuntimeError, match="DH_PROJECT_ROOT"),
        ):
            get_config()

    def test_auto_init_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """A warning is logged when auto-initialisation succeeds."""
        import logging

        with (
            patch.object(_models, "_resolve_repo_root", return_value=tmp_path),
            caplog.at_level(logging.WARNING, logger=_models.__name__),
        ):
            get_config()
        assert any("auto-initialised" in r.message for r in caplog.records)


class TestInitPaths:
    def test_config_fields_match_after_init_paths(self, tmp_path: Path) -> None:
        """After init_paths(project_dir=..., repo=...), config fields are set."""
        init_paths(project_dir=str(tmp_path), repo="owner/myrepo")

        cfg = get_config()
        assert cfg.repo_root == tmp_path.resolve()
        assert cfg.default_repo == "owner/myrepo"

    def test_get_repo_root_returns_correct_path(self, tmp_path: Path) -> None:
        init_paths(project_dir=str(tmp_path), repo="owner/repo")
        assert get_repo_root() == tmp_path.resolve()

    def test_get_default_repo_returns_slug(self, tmp_path: Path) -> None:
        init_paths(project_dir=str(tmp_path), repo="alice/wonderland")
        assert get_default_repo() == "alice/wonderland"

    def test_get_backlog_dir_is_path(self, tmp_path: Path) -> None:
        init_paths(project_dir=str(tmp_path), repo="owner/repo")
        assert isinstance(get_backlog_dir(), Path)

    def test_module_backlog_dir_attr_matches_accessor(self, tmp_path: Path) -> None:
        """_models.BACKLOG_DIR via __getattr__ must equal get_backlog_dir()."""
        init_paths(project_dir=str(tmp_path), repo="owner/repo")
        assert get_backlog_dir() == _models.BACKLOG_DIR  # type: ignore[attr-defined]

    def test_module_repo_root_attr_matches_accessor(self, tmp_path: Path) -> None:
        init_paths(project_dir=str(tmp_path), repo="owner/repo")
        assert get_repo_root() == _models._REPO_ROOT  # type: ignore[attr-defined]

    def test_module_default_repo_attr_matches_accessor(self, tmp_path: Path) -> None:
        init_paths(project_dir=str(tmp_path), repo="owner/repo")
        assert get_default_repo() == _models.DEFAULT_REPO  # type: ignore[attr-defined]

    def test_explicit_init_takes_precedence_over_auto_init(self, tmp_path: Path) -> None:
        """Calling init_paths() explicitly sets config regardless of auto-init path."""
        explicit_dir = tmp_path / "explicit"
        explicit_dir.mkdir()
        init_paths(project_dir=str(explicit_dir), repo="owner/explicit")
        cfg = get_config()
        assert cfg.repo_root == explicit_dir.resolve()
        assert cfg.default_repo == "owner/explicit"


class TestReinitUpdatesConfig:
    def test_reinit_with_different_args_updates_config(self, tmp_path: Path) -> None:
        """Calling init_paths() a second time replaces the config instance."""
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        dir_b = tmp_path / "b"
        dir_b.mkdir()

        init_paths(project_dir=str(dir_a), repo="owner/repo-a")
        cfg_first = get_config()
        assert cfg_first.repo_root == dir_a.resolve()
        assert cfg_first.default_repo == "owner/repo-a"

        init_paths(project_dir=str(dir_b), repo="owner/repo-b")
        cfg_second = get_config()
        assert cfg_second.repo_root == dir_b.resolve()
        assert cfg_second.default_repo == "owner/repo-b"

        # Accessor values reflect the second call.
        assert get_repo_root() == dir_b.resolve()
        assert get_default_repo() == "owner/repo-b"

    def test_reinit_replaces_config_object(self, tmp_path: Path) -> None:
        """Each call to init_paths() creates a fresh BacklogConfig instance."""
        init_paths(project_dir=str(tmp_path), repo="owner/first")
        cfg_before = get_config()

        init_paths(project_dir=str(tmp_path), repo="owner/second")
        cfg_after = get_config()

        assert cfg_before is not cfg_after


class TestBacklogConfigDataclass:
    def test_backlog_config_is_dataclass(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(BacklogConfig)

    def test_backlog_config_fields(self, tmp_path: Path) -> None:
        cfg = BacklogConfig(repo_root=tmp_path, backlog_dir=tmp_path / "backlog", default_repo="owner/repo")
        assert cfg.repo_root == tmp_path
        assert cfg.backlog_dir == tmp_path / "backlog"
        assert cfg.default_repo == "owner/repo"


class TestInitAlias:
    def test_init_is_alias_for_init_paths(self) -> None:
        """``init`` must be the same callable as ``init_paths`` for compat."""
        from backlog_core.models import init

        assert init is init_paths


class TestUnknownAttributeRaises:
    def test_unknown_attr_raises_attribute_error(self) -> None:
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = _models.DOES_NOT_EXIST  # type: ignore[attr-defined]
