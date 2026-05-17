"""TDD tests for DHConfig — unified backend-name resolver using .dh/config.yaml.

These tests are written BEFORE the implementation exists. All must fail RED with
ImportError when ``dh_config.py`` is absent. Once implementation exists, all tests
must go GREEN.

Expected module location:  plugins/development-harness/dh_config.py
Expected public API:       DHConfig.get_backend(subsystem: str) -> str

Where ``subsystem`` is one of: "backlog", "task", "context".

Resolution order per subsystem (precedence highest → lowest):
    1. Subsystem-specific env var (BACKLOG_BACKEND / TASKBACKEND / CONTEXTBACKEND)
    2. Subsystem override in .dh/config.yaml  (e.g. task.backend: beads)
    3. Global backend.name in .dh/config.yaml
    4. .beads/dh-backend marker file auto-detect → returns "beads" if marker file present
    5. Default: "github" for backlog, "local" for task and context

Config search paths (priority order):
    1. {project_root}/.dh/config.yaml   via dh_paths.project_dh_dir()
    2. ~/.dh/config.yaml                via dh_paths._dh_user_root() or Path.home() / ".dh"

YAML schema:
    backend:
      name: github           # global default for all subsystems

    # Optional per-subsystem overrides:
    task:
      backend: beads
    context:
      backend: local
    backlog:
      backend: sqlite

Design note on .beads/ and task/context subsystems:
    The resolution order in the spec applies to ALL three subsystems identically.
    Step 4 (.beads/ auto-detect) is therefore exercised for task and context too.
    This extends the existing behaviour (only backlog_core detects .beads/ today)
    and the tests encode that intended new behaviour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.helpers import make_dh_paths_mock

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Parametrize marker — apply to tests that are symmetric across all subsystems
# ---------------------------------------------------------------------------

_ALL_SUBSYSTEMS = pytest.mark.parametrize(
    ("subsystem", "env_var", "default"),
    [
        pytest.param("backlog", "BACKLOG_BACKEND", "github", id="backlog"),
        pytest.param("task", "TASKBACKEND", "local", id="task"),
        pytest.param("context", "CONTEXTBACKEND", "local", id="context"),
    ],
)

_TASK_AND_CONTEXT = pytest.mark.parametrize(
    ("subsystem", "env_var"),
    [pytest.param("task", "TASKBACKEND", id="task"), pytest.param("context", "CONTEXTBACKEND", id="context")],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(path: Path, content: str) -> None:
    """Write a YAML config file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _clear_all_backend_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all three backend selector env vars to prevent env leakage."""
    for var in ("BACKLOG_BACKEND", "TASKBACKEND", "CONTEXTBACKEND"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Test group 1 — env var takes precedence
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_env_var_set_then_returns_env_var_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Env var value is returned regardless of any config file content.

    Why: Env vars are the highest-priority override mechanism; they must
    beat every file-based configuration layer to enable CI/CD overrides.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setenv(env_var, "memory")
    # Write a config file that would return a different value
    config_path = tmp_path / "project" / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: sqlite\n")

    fake_dh_paths = _make_dh_paths_mock(tmp_path / "project")
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "memory"


@_ALL_SUBSYSTEMS
def test_when_env_var_set_then_config_file_is_not_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Config file value is not used when env var is set.

    Why: Confirms the ordering contract — env var is step 1 and must
    short-circuit all lower-priority resolution steps.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setenv(env_var, "beads")
    config_path = tmp_path / "project" / ".dh" / "config.yaml"
    _write_config(config_path, f"{subsystem}:\n  backend: github\n")

    fake_dh_paths = _make_dh_paths_mock(tmp_path / "project")
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "beads"


# ---------------------------------------------------------------------------
# Test group 2 — subsystem-specific section overrides global section
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_subsystem_section_present_then_overrides_global_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Subsystem-specific section overrides the global backend.name key.

    Why: Per-subsystem overrides exist precisely to allow different backends
    for backlog, task, and context. If global always wins, the override keys
    are useless.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    config_content = f"backend:\n  name: github\n{subsystem}:\n  backend: memory\n"
    config_path = tmp_path / "project" / ".dh" / "config.yaml"
    _write_config(config_path, config_content)

    fake_dh_paths = _make_dh_paths_mock(tmp_path / "project")
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "memory"


@_ALL_SUBSYSTEMS
def test_when_other_subsystem_section_present_then_current_subsystem_sees_global(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """A per-subsystem override for a different subsystem does not affect this one.

    Why: Subsystem isolation — setting task.backend must not change what
    backlog or context resolves to.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    # Use a subsystem that is NOT the current one
    other = "context" if subsystem != "context" else "task"
    config_content = f"backend:\n  name: sqlite\n{other}:\n  backend: memory\n"
    config_path = tmp_path / "project" / ".dh" / "config.yaml"
    _write_config(config_path, config_content)

    fake_dh_paths = _make_dh_paths_mock(tmp_path / "project")
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert — current subsystem sees the global section
    assert result == "sqlite"


# ---------------------------------------------------------------------------
# Test group 3 — global backend section applies when no subsystem override
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_only_global_backend_section_then_all_subsystems_use_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Global backend.name is returned for all subsystems when no override exists.

    Why: The global section is a one-line config for teams that want the same
    backend everywhere. If any subsystem ignores it, that team must repeat
    themselves.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    config_path = tmp_path / "project" / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: sqlite\n")

    fake_dh_paths = _make_dh_paths_mock(tmp_path / "project")
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "sqlite"


# ---------------------------------------------------------------------------
# Test group 4 — project-root config file is found and read
# ---------------------------------------------------------------------------


def test_when_project_config_exists_then_it_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Config at {project_root}/.dh/config.yaml is discovered and parsed.

    Why: Project-level config is the primary per-project configuration
    mechanism; if it is not read, all project-specific settings are ignored.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "myproject"
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: sqlite\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert
    assert result == "sqlite"


def test_when_project_config_exists_then_it_takes_priority_over_user_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project-level config takes priority over the user-home config.

    Why: Per-project settings must override user-level defaults; otherwise
    a global user config leaks into every project.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    fake_home = tmp_path / "fakehome"
    monkeypatch.setenv("HOME", str(fake_home))

    project_root = tmp_path / "myproject"
    project_config = project_root / ".dh" / "config.yaml"
    _write_config(project_config, "backend:\n  name: sqlite\n")

    user_config = fake_home / ".dh" / "config.yaml"
    _write_config(user_config, "backend:\n  name: memory\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert — project wins
    assert result == "sqlite"


# ---------------------------------------------------------------------------
# Test group 5 — user-home config is found when no project config exists
# ---------------------------------------------------------------------------


def test_when_only_user_config_exists_then_user_config_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """~/.dh/config.yaml is read when no project-level file exists.

    Why: User-home config provides a personal default for all projects;
    if it is not read when project config is absent, users must repeat
    themselves in every project.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    fake_home = tmp_path / "fakehome"
    monkeypatch.setenv("HOME", str(fake_home))

    user_config = fake_home / ".dh" / "config.yaml"
    _write_config(user_config, "backend:\n  name: memory\n")

    # No project config — project_dh_dir returns a path that has no config.yaml
    project_root = tmp_path / "emptyproject"
    project_root.mkdir(parents=True)
    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert
    assert result == "memory"


# ---------------------------------------------------------------------------
# Test group 6 — .beads/dh-backend marker file triggers auto-detect
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_beads_dir_exists_and_no_env_and_no_config_then_returns_beads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """.beads/dh-backend marker file at project root triggers beads auto-detect.

    Why: Beads auto-detect requires explicit opt-in via the .beads/dh-backend
    marker file (commit 02acb45b). Applies to all three subsystems so any beads
    project routes correctly without any config file.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    (project_root / ".beads").mkdir(parents=True)
    (project_root / ".beads" / "dh-backend").write_text("", encoding="utf-8")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "beads"


@_ALL_SUBSYSTEMS
def test_when_config_file_present_then_beads_auto_detect_is_not_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Config file takes priority over .beads/dh-backend marker file auto-detect.

    Why: A user who set backend.name = 'local' explicitly must be able to
    opt out of beads even if the .beads/dh-backend opt-in marker is present.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    (project_root / ".beads").mkdir(parents=True)
    (project_root / ".beads" / "dh-backend").write_text("", encoding="utf-8")
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: local\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert — config file wins over auto-detect
    assert result == "local"


def test_when_beads_path_is_file_not_directory_then_auto_detect_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """.beads as a plain file (not a directory) does not trigger auto-detect.

    Why: Auto-detect checks .beads/dh-backend as a file. When .beads itself is
    a file rather than a directory, the path .beads/dh-backend cannot exist,
    so is_file() returns False and beads is not selected.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)
    (project_root / ".beads").write_text("not a directory", encoding="utf-8")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act — falls through to default
    result = DHConfig().get_backend("backlog")

    # Assert — default, not beads
    assert result == "github"


# ---------------------------------------------------------------------------
# Test group 7 — defaults when nothing is configured
# ---------------------------------------------------------------------------


def test_when_nothing_configured_then_backlog_returns_github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default for backlog subsystem is 'github' when no config, env, or .beads/ exists.

    Why: The spec mandates 'github' as the default to preserve backwards
    compatibility for existing deployments.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert
    assert result == "github"


@_TASK_AND_CONTEXT
def test_when_nothing_configured_then_task_and_context_return_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str
) -> None:
    """Default for task and context subsystems is 'local' when nothing is configured.

    Why: Local backend requires no credentials and works offline — the
    correct safe default for user-scoped task/context state.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert
    assert result == "local"


# ---------------------------------------------------------------------------
# Test group 8 — missing config file is silently ignored
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_config_file_absent_then_no_exception_is_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Missing .dh/config.yaml does not raise; falls through to lower-priority steps.

    Why: Users without any config file must get defaults, not a crash. The
    config file is optional.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True)
    # Deliberately do NOT create any config.yaml

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act — must not raise
    result = DHConfig().get_backend(subsystem)

    # Assert — falls through to default
    assert result == default


# ---------------------------------------------------------------------------
# Test group 9 — invalid YAML is silently ignored
# ---------------------------------------------------------------------------


@_ALL_SUBSYSTEMS
def test_when_config_file_contains_invalid_yaml_then_no_exception_is_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Malformed YAML in config file is silently skipped; default is returned.

    Why: A corrupted config must not crash the whole tool. The user needs a
    clear path to recovery (fix the file), not a stack trace.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, ":::not valid yaml:::\n  - [unclosed\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act — must not raise
    result = DHConfig().get_backend(subsystem)

    # Assert — falls through to default
    assert result == default


@_ALL_SUBSYSTEMS
def test_when_project_config_invalid_yaml_then_user_config_is_tried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, subsystem: str, env_var: str, default: str
) -> None:
    """Invalid project config falls through to user config, not directly to default.

    Why: Resolution order must be exhausted in sequence. An invalid project
    config at step (1) must try user config at step (2) before defaulting.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    fake_home = tmp_path / "fakehome"
    monkeypatch.setenv("HOME", str(fake_home))

    project_root = tmp_path / "project"
    bad_config = project_root / ".dh" / "config.yaml"
    _write_config(bad_config, ":::invalid:::\n")

    user_config = fake_home / ".dh" / "config.yaml"
    _write_config(user_config, "backend:\n  name: memory\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend(subsystem)

    # Assert — user config is used because project config was invalid
    assert result == "memory"


# ---------------------------------------------------------------------------
# Test group 10 — dh_paths absent: user path fallback, project path skipped
# ---------------------------------------------------------------------------


def test_when_dh_paths_absent_then_user_config_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When dh_paths is None, ~/.dh/config.yaml is read via Path.home() fallback.

    Why: dh_paths is an optional import — tests and environments without the
    plugin must still read user-level config. The fallback to Path.home() / ".dh"
    is the contract for this case.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    fake_home = tmp_path / "fakehome"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr("dh_config._dh_paths", None)

    user_config = fake_home / ".dh" / "config.yaml"
    _write_config(user_config, "backend:\n  name: memory\n")

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert
    assert result == "memory"


def test_when_dh_paths_absent_then_project_path_is_gracefully_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When dh_paths is None, project-root config lookup is skipped without error.

    Why: Project path discovery requires dh_paths.project_dh_dir(). With
    dh_paths absent, the lookup cannot happen and must be silently skipped,
    not raise AttributeError.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setattr("dh_config._dh_paths", None)
    # No user config either — should return default

    # Act — must not raise
    result = DHConfig().get_backend("backlog")

    # Assert — falls through to default
    assert result == "github"


def test_when_dh_paths_absent_then_all_subsystems_return_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With dh_paths None and no user config, all subsystems return their defaults.

    Why: Tests the complete fallback chain for the common test/CI environment
    where dh_paths is not installed.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setattr("dh_config._dh_paths", None)

    config = DHConfig()

    # Act + Assert — each subsystem falls to its own default
    assert config.get_backend("backlog") == "github"
    assert config.get_backend("task") == "local"
    assert config.get_backend("context") == "local"


# ---------------------------------------------------------------------------
# Test group 11 — edge cases and combined scenarios
# ---------------------------------------------------------------------------


def test_when_config_has_empty_backend_name_then_falls_through_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config file with backend.name = '' is ignored; default is returned.

    Why: An empty string is not a valid backend name. It must not be
    treated as a valid configuration value.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: ''\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert
    assert result == "github"


def test_when_config_has_missing_backend_section_then_falls_through_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config file with no backend section is treated as if absent.

    Why: A user might have a config.yaml for other settings. If it lacks
    a backend section, it must not crash or silently override the default.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, "other_setting: true\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("task")

    # Assert
    assert result == "local"


def test_when_subsystem_section_has_empty_backend_then_global_section_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subsystem section with empty backend falls through to global section.

    Why: An empty per-subsystem override must not override global with an
    invalid empty value — it must be treated as absent.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    project_root = tmp_path / "project"
    config_path = project_root / ".dh" / "config.yaml"
    _write_config(config_path, "backend:\n  name: sqlite\ntask:\n  backend: ''\n")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("task")

    # Assert — falls through to global
    assert result == "sqlite"


def test_when_env_var_set_then_beads_auto_detect_is_not_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env var beats .beads/dh-backend auto-detect (env var is step 1, auto-detect is step 4).

    Why: A user who explicitly sets BACKLOG_BACKEND=github in their shell
    must be able to override .beads/dh-backend marker file auto-detect.
    """
    from dh_config import DHConfig  # ImportError until module exists

    # Arrange
    _clear_all_backend_env_vars(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    monkeypatch.setenv("BACKLOG_BACKEND", "github")
    project_root = tmp_path / "project"
    (project_root / ".beads").mkdir(parents=True)
    (project_root / ".beads" / "dh-backend").write_text("", encoding="utf-8")

    fake_dh_paths = _make_dh_paths_mock(project_root)
    monkeypatch.setattr("dh_config._dh_paths", fake_dh_paths)

    # Act
    result = DHConfig().get_backend("backlog")

    # Assert — env var wins
    assert result == "github"


# ---------------------------------------------------------------------------
# Helper: dh_paths mock factory (shared across all test groups above)
# ---------------------------------------------------------------------------


_make_dh_paths_mock = make_dh_paths_mock
