"""Tests for BacklogConfig and init_paths() in backlog_core.models."""

from __future__ import annotations

from pathlib import Path

import pytest

import backlog_core.models as _models
from backlog_core.models import BacklogConfig, get_backlog_dir, get_config, get_default_repo, get_repo_root, init_paths


@pytest.fixture(autouse=True)
def _reset_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore _config to None after each test to isolate state."""
    monkeypatch.setattr(_models, "_config", None)


class TestGetConfigBeforeInit:
    def test_get_config_raises_before_init_paths(self) -> None:
        """get_config() must raise RuntimeError when _config is None."""
        with pytest.raises(RuntimeError, match="not initialised"):
            get_config()

    def test_get_repo_root_raises_before_init_paths(self) -> None:
        with pytest.raises(RuntimeError, match="not initialised"):
            get_repo_root()

    def test_get_backlog_dir_raises_before_init_paths(self) -> None:
        with pytest.raises(RuntimeError, match="not initialised"):
            get_backlog_dir()

    def test_get_default_repo_raises_before_init_paths(self) -> None:
        with pytest.raises(RuntimeError, match="not initialised"):
            get_default_repo()

    def test_module_backlog_dir_attr_raises_before_init_paths(self) -> None:
        """_models.BACKLOG_DIR access via __getattr__ must also raise."""
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = _models.BACKLOG_DIR  # type: ignore[attr-defined]

    def test_module_repo_root_attr_raises_before_init_paths(self) -> None:
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = _models._REPO_ROOT  # type: ignore[attr-defined]

    def test_module_default_repo_attr_raises_before_init_paths(self) -> None:
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = _models.DEFAULT_REPO  # type: ignore[attr-defined]


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
