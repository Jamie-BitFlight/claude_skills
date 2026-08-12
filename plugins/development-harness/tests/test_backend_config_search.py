"""Tests — .dh/config.yaml backend resolution through the backend factories.

The factories (``create_backend`` / ``create_task_backend``) delegate resolution
in full to ``DHConfig.get_backend``. These tests assert against the factories
rather than any private helper, so they exercise the contract callers actually
depend on: which backend object you get for a given .dh/config.yaml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

import backlog_core.backend_protocol as _bp
import dh_config as _dh_config
import pytest
import sam_schema.core.task_config as _tc
from backlog_core.backend_protocol import BEADS_DIR, BEADS_OPT_IN_MARKER
from ruamel.yaml import YAML

from tests.helpers import make_dh_paths_mock

if TYPE_CHECKING:
    from pathlib import Path

_yaml = YAML(typ="safe")


class _BackendSearchModule(Protocol):
    """Protocol matching both backlog_core.backend_protocol and sam_schema.core.task_config."""

    def create_backend(self) -> object: ...


def _write_yaml_config(path: Path, backend_name: str) -> None:
    """Write a .dh/config.yaml with global backend.name set."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _yaml.dump({"backend": {"name": backend_name}}, path.open("w", encoding="utf-8"))


def _write_yaml_config_subsystem(path: Path, subsystem: str, backend_name: str) -> None:
    """Write a .dh/config.yaml with a subsystem-specific backend override."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _yaml.dump({subsystem: {"backend": backend_name}}, path.open("w", encoding="utf-8"))


_make_dh_paths_mock = make_dh_paths_mock


def _patch_dh_paths(
    monkeypatch: pytest.MonkeyPatch, module: _BackendSearchModule, project_root: Path, tmp_path: Path
) -> None:
    """Patch _dh_paths in the shim module (when present) and in dh_config.

    task_config and context_config no longer hold _dh_paths; they delegate entirely to DHConfig.
    Only backend_protocol retains _dh_paths for its _auto_detect_beads() function.
    """
    dh_mock = _make_dh_paths_mock(project_root, user_dh_root=tmp_path / "fakehome" / ".dh")
    if hasattr(module, "_dh_paths"):
        monkeypatch.setattr(module, "_dh_paths", dh_mock)
    monkeypatch.setattr(_dh_config, "_dh_paths", dh_mock)


def _resolve(module: object, subsystem: str) -> str:
    """Return the concrete backend class name the module's factory produces."""
    if subsystem == "backlog":
        return type(_bp.create_backend()).__name__
    return type(_tc.create_task_backend()).__name__


_BOTH_SIDES = pytest.mark.parametrize(
    ("module", "subsystem", "configured_name", "expected_cls"),
    [
        pytest.param(_bp, "backlog", "memory", "InMemoryBackend", id="backlog_core"),
        pytest.param(_tc, "task", "memory", "InMemoryTaskProvider", id="sam_schema"),
    ],
)

_BOTH_SIDES_ONLY_MODULE = pytest.mark.parametrize(
    ("module", "subsystem", "default_cls"),
    [
        pytest.param(_bp, "backlog", "GitHubBackend", id="backlog_core"),
        pytest.param(_tc, "task", "LocalYamlTaskProvider", id="sam_schema"),
    ],
)


@_BOTH_SIDES
def test_dh_subdir_config_yaml_discovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: _BackendSearchModule,
    subsystem: str,
    configured_name: str,
    expected_cls: str,
) -> None:
    """Backend from {project_root}/.dh/config.yaml is the one the factory builds."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_yaml_config(project_root / ".dh" / "config.yaml", configured_name)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.delenv("TASKBACKEND", raising=False)
    _patch_dh_paths(monkeypatch, module, project_root, tmp_path)
    assert _resolve(module, subsystem) == expected_cls


@_BOTH_SIDES
def test_only_dh_config_present_is_picked_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: _BackendSearchModule,
    subsystem: str,
    configured_name: str,
    expected_cls: str,
) -> None:
    """Only .dh/config.yaml exists — config.yaml is the sole source."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_yaml_config(project_root / ".dh" / "config.yaml", configured_name)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.delenv("TASKBACKEND", raising=False)
    _patch_dh_paths(monkeypatch, module, project_root, tmp_path)
    assert _resolve(module, subsystem) == expected_cls


@_BOTH_SIDES_ONLY_MODULE
def test_returns_none_when_no_config_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: _BackendSearchModule, subsystem: str, default_cls: str
) -> None:
    """Falls back to the subsystem default when no config.yaml exists."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.delenv("TASKBACKEND", raising=False)
    # Ensure no .beads/ dir so auto-detect returns None too; patch both module
    # and dh_config._dh_paths so DHConfig sees the isolated tmp project root
    _patch_dh_paths(monkeypatch, module, project_root, tmp_path)
    assert _resolve(module, subsystem) == default_cls


@_BOTH_SIDES
def test_subsystem_section_overrides_global_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: _BackendSearchModule,
    subsystem: str,
    configured_name: str,
    expected_cls: str,
) -> None:
    """Subsystem-specific backend in config.yaml overrides global backend.name."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    config_path = project_root / ".dh" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Global says sqlite, subsystem-specific says configured_name — subsystem wins
    with config_path.open("w", encoding="utf-8") as fh:
        _yaml.dump({"backend": {"name": "sqlite"}, subsystem: {"backend": configured_name}}, fh)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.delenv("TASKBACKEND", raising=False)
    _patch_dh_paths(monkeypatch, module, project_root, tmp_path)
    assert _resolve(module, subsystem) == expected_cls


# ---------------------------------------------------------------------------
# Beads backend — YAML resolution
# ---------------------------------------------------------------------------


def test_backend_config_yaml_beads_name_honored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """create_backend() builds BeadsBackend when config.yaml specifies it.

    Why: If 'beads' is not treated as a valid string name by the YAML parser,
         create_backend() never receives it and silently falls through to the
         default 'github' backend.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_yaml_config(project_root / ".dh" / "config.yaml", "beads")
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    _patch_dh_paths(monkeypatch, cast("_BackendSearchModule", _bp), project_root, tmp_path)

    assert type(_bp.create_backend()).__name__ == "BeadsBackend"


def test_backend_config_yaml_dh_subdir_beads_honored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """create_backend() builds BeadsBackend from {project_root}/.dh/config.yaml.

    Why: The .dh/ subdir search path is how project-level config is detected;
         if that path is broken for 'beads', users with .dh/config.yaml config
         would fall through to the default github backend silently.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_yaml_config(project_root / ".dh" / "config.yaml", "beads")
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    _patch_dh_paths(monkeypatch, cast("_BackendSearchModule", _bp), project_root, tmp_path)

    assert type(_bp.create_backend()).__name__ == "BeadsBackend"


def test_sqlite_factory_uses_persistent_project_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured SQLite uses the project's durable state database."""
    from backlog_core.backends.sqlite_backend import SQLiteBackend

    project_root = tmp_path / "project"
    project_root.mkdir()
    state_root = tmp_path / "state"
    dh_paths_mock = _make_dh_paths_mock(project_root)
    dh_paths_mock.state_root.return_value = state_root
    monkeypatch.setattr(_bp, "_dh_paths", dh_paths_mock)

    backend = _bp.create_backend("sqlite")

    assert isinstance(backend, SQLiteBackend)
    assert (state_root / "backlog.sqlite3").is_file()


# ---------------------------------------------------------------------------
# Auto-detect _auto_detect_beads
# ---------------------------------------------------------------------------


def test_auto_detect_beads_found_when_opt_in_marker_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns 'beads' when .beads/dh-backend marker file exists.

    Why: Auto-detect requires an explicit opt-in marker file. A project that has
         .beads/ for other purposes must not be silently routed to the beads backend.
    """
    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")
    dh_mock = _make_dh_paths_mock(project_root)
    monkeypatch.setattr(_bp, "_dh_paths", dh_mock)

    assert _bp._auto_detect_beads() == "beads"


def test_auto_detect_beads_returns_none_when_only_dot_beads_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_auto_detect_beads() returns None when .beads/ exists but the opt-in marker is absent.

    Why: T33 requirement — BEADS_DIR alone must not trigger auto-detection.
         Projects using .beads/ for other purposes would be silently mis-routed
         to the beads backend without the explicit opt-in marker file.
    """
    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    # No BEADS_OPT_IN_MARKER file — directory alone must not trigger detection
    dh_mock = _make_dh_paths_mock(project_root)
    monkeypatch.setattr(_bp, "_dh_paths", dh_mock)

    assert _bp._auto_detect_beads() is None


def test_auto_detect_beads_not_found_when_dot_beads_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns None when BEADS_DIR does not exist.

    Why: Returning 'beads' when BEADS_DIR is absent would route all non-beads
         projects to the beads backend, breaking github/sqlite/memory users.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    dh_mock = _make_dh_paths_mock(project_root)
    monkeypatch.setattr(_bp, "_dh_paths", dh_mock)

    assert _bp._auto_detect_beads() is None


def test_auto_detect_beads_returns_none_when_dh_paths_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns None when _dh_paths is None.

    Why: dh_paths is an optional import (absent in test environments without the
         plugin installed).  None must not propagate as a AttributeError crash.
    """
    monkeypatch.setattr(_bp, "_dh_paths", None)

    assert _bp._auto_detect_beads() is None


def test_auto_detect_beads_file_not_dir_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns None when .beads is a plain file, not a directory.

    Why: When BEADS_DIR is a plain file (not a directory), the marker file path
         cannot exist, so auto-detection must return None rather than crashing.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / BEADS_DIR).write_text("not a directory", encoding="utf-8")
    dh_mock = _make_dh_paths_mock(project_root)
    monkeypatch.setattr(_bp, "_dh_paths", dh_mock)

    assert _bp._auto_detect_beads() is None


def test_config_yaml_takes_precedence_over_auto_detect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """config.yaml with name='memory' wins even when the opt-in marker exists.

    Why: YAML config is ranked above auto-detect in the resolution order;
         if auto-detect overrides config.yaml, users cannot opt out of beads by
         setting config.yaml to a different backend.
    """
    from backlog_core.backend_protocol import create_backend
    from backlog_core.backends.memory_backend import InMemoryBackend

    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")
    _write_yaml_config(project_root / ".dh" / "config.yaml", "memory")

    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    _patch_dh_paths(monkeypatch, cast("_BackendSearchModule", _bp), project_root, tmp_path)

    backend = create_backend()

    assert isinstance(backend, InMemoryBackend)


def test_explicit_default_pin_wins_over_auto_detect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """config.yaml pinning backlog to its DEFAULT ('github') beats the beads marker.

    Why: regression guard for the sentinel-collision bug. The old
    ``_load_backend_name_from_config()`` returned ``None`` whenever the resolved
    value equalled the subsystem default, making an explicit pin indistinguishable
    from "unset" — so the outer ``or`` chain fell through to ``_auto_detect_beads()``
    and handed back BeadsBackend. A user on a beads project could not pin backlog
    back to github. The sibling test above uses 'memory' (a non-default), which is
    why it never caught this.
    """
    from backlog_core.backend_protocol import create_backend
    from backlog_core.backends.github_backend import GitHubBackend

    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")
    _write_yaml_config_subsystem(project_root / ".dh" / "config.yaml", "backlog", "github")

    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    _patch_dh_paths(monkeypatch, cast("_BackendSearchModule", _bp), project_root, tmp_path)

    assert isinstance(create_backend(), GitHubBackend)


def test_marker_only_still_auto_detects_beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no config.yaml, the .beads/dh-backend marker still selects BeadsBackend.

    Why: pairs with the test above — fixing the explicit-pin case must not disable
    auto-detect for users who rely on the marker alone.
    """
    from backlog_core.backend_protocol import create_backend
    from backlog_core.backends.beads_backend import BeadsBackend

    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")

    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    _patch_dh_paths(monkeypatch, cast("_BackendSearchModule", _bp), project_root, tmp_path)

    assert isinstance(create_backend(), BeadsBackend)
