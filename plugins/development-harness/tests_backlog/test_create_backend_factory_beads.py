"""Tests for the beads branch of create_backend() and auto-detect logic.

Verifies:
- create_backend("beads") returns a BeadsBackend instance.
- create_backend() uses auto-detect when .beads/ exists at project root.
- reset_config() clears the singleton so factory is re-run on next get_config().
- BACKLOG_BACKEND=beads env var is honoured by create_backend().

All tests isolate dh_paths via monkeypatch to avoid filesystem side-effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.backend_protocol as _bp
import pytest
from backlog_core.backend_protocol import BEADS_DIR, BEADS_OPT_IN_MARKER, create_backend, reset_config
from backlog_core.backends.beads_backend import BeadsBackend
from tests.helpers import make_dh_paths_mock

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_make_dh_paths_mock = make_dh_paths_mock


# ---------------------------------------------------------------------------
# create_backend("beads") — explicit name
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_backend_beads_explicit_returns_beads_backend() -> None:
    """create_backend('beads') returns a BeadsBackend instance.

    Why: The factory must dispatch to BeadsBackend on the explicit name — a
         wrong dispatch would cause all beads operations to route to the wrong
         backend class.
    """
    backend = create_backend("beads")

    assert isinstance(backend, BeadsBackend)


@pytest.mark.unit
def test_create_backend_beads_instance_satisfies_protocol() -> None:
    """create_backend('beads') result satisfies the BacklogBackend Protocol.

    Why: Protocol conformance is checked at runtime by operations.py; a backend
         that doesn't satisfy the Protocol would silently drop operations.
    """
    from backlog_core.backend_protocol import BacklogBackend

    backend = create_backend("beads")

    assert isinstance(backend, BacklogBackend)


# ---------------------------------------------------------------------------
# BACKLOG_BACKEND env var
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_env_var_backlog_backend_beads_creates_beads_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """BACKLOG_BACKEND=beads causes create_backend(None) to return BeadsBackend.

    Why: The env var is the primary user-facing configuration mechanism — if it
         is ignored, users cannot select beads without a backend.toml.
    """
    monkeypatch.setenv("BACKLOG_BACKEND", "beads")

    backend = create_backend()

    assert isinstance(backend, BeadsBackend)


@pytest.mark.unit
def test_env_var_overrides_toml_to_select_beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """BACKLOG_BACKEND=beads takes precedence over backend.toml set to 'memory'.

    Why: Resolution order mandates env var first — a TOML file that sets
         'memory' must be ignored when the env var is explicitly set to 'beads'.
    """
    import tomlkit

    project_root = tmp_path / "project"
    project_root.mkdir()
    toml_path = project_root / "backend.toml"
    toml_path.write_text(tomlkit.dumps({"backend": {"name": "memory"}}), encoding="utf-8")

    monkeypatch.setenv("BACKLOG_BACKEND", "beads")
    monkeypatch.setattr(_bp, "_dh_paths", _make_dh_paths_mock(project_root))

    backend = create_backend()

    assert isinstance(backend, BeadsBackend)


# ---------------------------------------------------------------------------
# _auto_detect_beads
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_auto_detect_beads_returns_beads_when_marker_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_auto_detect_beads() returns 'beads' when .beads/dh-backend marker file exists.

    Why: The auto-detect mechanism requires an explicit opt-in marker file.
         Directory presence alone is not sufficient — projects using .beads/ for
         other purposes must not be silently routed to the beads backend.
    """
    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")

    monkeypatch.setattr(_bp, "_dh_paths", _make_dh_paths_mock(project_root))

    result = _bp._auto_detect_beads()

    assert result == "beads"


@pytest.mark.unit
def test_auto_detect_beads_returns_none_when_only_dot_beads_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_auto_detect_beads() returns None when BEADS_DIR exists but the opt-in marker is absent.

    Why: T33 requirement — BEADS_DIR alone must not trigger auto-detection.
         Explicit opt-in via BEADS_OPT_IN_MARKER is required to prevent silent
         mis-routing of projects that use .beads/ for other purposes.
    """
    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    # No BEADS_OPT_IN_MARKER — directory alone must not trigger detection

    monkeypatch.setattr(_bp, "_dh_paths", _make_dh_paths_mock(project_root))

    result = _bp._auto_detect_beads()

    assert result is None


@pytest.mark.unit
def test_auto_detect_beads_returns_none_when_no_dot_beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns None when .beads/ is absent.

    Why: Returning 'beads' when .beads/ does not exist would cause all projects
         to use the beads backend unless they opt out — breaking all existing
         github/sqlite/memory users.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()

    monkeypatch.setattr(_bp, "_dh_paths", _make_dh_paths_mock(project_root))

    result = _bp._auto_detect_beads()

    assert result is None


@pytest.mark.unit
def test_auto_detect_beads_returns_none_when_dh_paths_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """_auto_detect_beads() returns None when _dh_paths is None.

    Why: dh_paths is an optional import (only present inside the plugin).
         When absent, auto-detect must fall through silently — raising an
         AttributeError would crash the factory in test environments.
    """
    monkeypatch.setattr(_bp, "_dh_paths", None)

    result = _bp._auto_detect_beads()

    assert result is None


@pytest.mark.unit
def test_create_backend_none_auto_detects_beads_when_marker_file_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_backend(None) returns BeadsBackend via auto-detect when .beads/dh-backend exists.

    Why: End-to-end test of the auto-detect path through the full factory
         resolution chain — confirms that the marker file wires into create_backend
         and the directory-alone path no longer triggers BeadsBackend selection.
    """
    project_root = tmp_path / "project"
    (project_root / BEADS_DIR).mkdir(parents=True)
    (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).write_text("", encoding="utf-8")

    monkeypatch.delenv("BACKLOG_BACKEND", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setattr(_bp, "_dh_paths", _make_dh_paths_mock(project_root))

    backend = create_backend()

    assert isinstance(backend, BeadsBackend)


# ---------------------------------------------------------------------------
# get_config / reset_config singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reset_config_clears_singleton_so_next_get_config_re_runs_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """reset_config() forces the next get_config() call to re-run backend selection.

    Why: Test isolation requires the singleton to be cleared between tests;
         if reset_config() is a no-op, earlier tests contaminate later ones.
    """
    from backlog_core.backend_protocol import get_config

    # Pre-load with a known backend so we can detect the reset
    monkeypatch.setenv("BACKLOG_BACKEND", "memory")
    original = get_config()
    assert original is not None

    reset_config()

    # After reset, a fresh get_config() with beads env must yield a new BeadsBackend
    monkeypatch.setenv("BACKLOG_BACKEND", "beads")
    new_config = get_config()

    assert isinstance(new_config.backend, BeadsBackend)

    # Teardown — restore to pristine state
    reset_config()


@pytest.mark.unit
def test_get_config_returns_same_instance_without_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_config() returns the cached singleton without re-running the factory.

    Why: Idempotent config access is a correctness requirement — each call
         must return the same object, not create a new backend each time.
    """
    from backlog_core.backend_protocol import get_config

    reset_config()
    monkeypatch.setenv("BACKLOG_BACKEND", "beads")

    first = get_config()
    second = get_config()

    assert first is second

    reset_config()


# ---------------------------------------------------------------------------
# create_backend — invalid name raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_backend_unknown_name_raises_value_error() -> None:
    """create_backend('unknown') raises ValueError with the invalid name.

    Why: An unknown backend name indicates a misconfiguration; ValueError
         surfaces the problem at configuration time rather than silently
         returning a default backend.
    """
    with pytest.raises(ValueError, match="Unknown backend"):
        create_backend("not-a-real-backend")


# ---------------------------------------------------------------------------
# Ordering — env var > TOML > auto-detect > default
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_explicit_name_overrides_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_backend('beads') uses the explicit arg even when env var is set to 'memory'.

    Why: Explicit name is the highest-priority mechanism — callers that pass
         an explicit name must get the named backend, not the env var backend.
    """
    monkeypatch.setenv("BACKLOG_BACKEND", "memory")

    backend = create_backend("beads")

    assert isinstance(backend, BeadsBackend)
