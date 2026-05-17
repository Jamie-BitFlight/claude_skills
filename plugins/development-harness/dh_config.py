"""DHConfig — unified backend-name resolver using .dh/config.yaml.

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
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import types

_dh_paths: types.ModuleType | None = None
with contextlib.suppress(ImportError):
    import dh_paths as _dh_paths  # optional — only present inside the plugin

__all__ = ["DHConfig"]

try:
    from ruamel.yaml import YAML as _RuamelYAML
    from ruamel.yaml.error import YAMLError as _YAMLError

    _YAML: _RuamelYAML | None = _RuamelYAML(typ="safe")
    _YAML_PARSE_ERRORS: tuple[type[Exception], ...] = (OSError, _YAMLError)
except ImportError:
    _YAML = None
    _YAML_PARSE_ERRORS = (OSError,)

# ---------------------------------------------------------------------------
# Subsystem configuration constants
# ---------------------------------------------------------------------------

_ENV_VARS: dict[str, str] = {"backlog": "BACKLOG_BACKEND", "task": "TASKBACKEND", "context": "CONTEXTBACKEND"}

_DEFAULTS: dict[str, str] = {"backlog": "github", "task": "local", "context": "local"}

_CONFIG_FILENAME = "config.yaml"


# ---------------------------------------------------------------------------
# YAML config loader
# ---------------------------------------------------------------------------


def _load_yaml_config(path: Path) -> dict[str, object] | None:
    """Read a YAML config file and return parsed content, or None on any error.

    Args:
        path: Path to the YAML config file.

    Returns:
        Parsed dict if successful, None if file absent or any error occurs.
    """
    if not path.is_file():
        return None
    if _YAML is None:
        return None
    try:
        data = _YAML.load(path.read_text(encoding="utf-8"))
    except _YAML_PARSE_ERRORS:
        return None
    else:
        if not isinstance(data, dict):
            return None
        return cast("dict[str, object]", data)


def _dh_user_root_path() -> Path:
    """Return the user-level .dh directory path.

    Uses _dh_paths._dh_user_root() when available, falls back to
    Path.home() / ".dh" otherwise.

    Returns:
        Path to the user-level .dh directory.
    """
    if _dh_paths is not None:
        try:
            return _dh_paths._dh_user_root()  # noqa: SLF001
        except (FileNotFoundError, RuntimeError):
            pass
    return Path.home() / ".dh"


def _get_config_search_paths() -> list[Path]:
    """Return ordered list of config.yaml paths to try.

    Priority: project-root .dh/ dir first, then user home .dh/ dir.

    Returns:
        List of Path objects to try in priority order.
    """
    paths: list[Path] = []

    if _dh_paths is not None:
        with contextlib.suppress(FileNotFoundError, RuntimeError):
            project_root = _dh_paths.git_project_root()
            dh_dir = _dh_paths.project_dh_dir(project_root)
            paths.append(dh_dir / _CONFIG_FILENAME)

    paths.append(_dh_user_root_path() / _CONFIG_FILENAME)
    return paths


def _resolve_from_config(subsystem: str) -> str | None:
    """Resolve backend name from config files for the given subsystem.

    Tries each config file in priority order. Within a file, subsystem-specific
    section takes priority over global backend.name.

    Args:
        subsystem: One of "backlog", "task", or "context".

    Returns:
        Backend name string if found in any config file, otherwise None.
    """
    for config_path in _get_config_search_paths():
        data = _load_yaml_config(config_path)
        if data is None:
            continue

        # Step 2: subsystem-specific override
        subsystem_section = data.get(subsystem)
        if isinstance(subsystem_section, dict):
            sub_backend = cast("dict[str, object]", subsystem_section).get("backend")
            if isinstance(sub_backend, str) and sub_backend:
                return sub_backend

        # Step 3: global backend.name
        backend_section = data.get("backend")
        if isinstance(backend_section, dict):
            global_name = cast("dict[str, object]", backend_section).get("name")
            if isinstance(global_name, str) and global_name:
                return global_name

    return None


def _auto_detect_beads() -> str | None:
    """Return 'beads' when .beads/dh-backend marker file exists at the project root.

    Uses _dh_paths to resolve project root. Returns None if _dh_paths absent,
    project root cannot be determined, or .beads/dh-backend does not exist as a file.

    Returns:
        "beads" when the opt-in marker file is present, otherwise None.
    """
    if _dh_paths is None:
        return None
    try:
        project_root = _dh_paths.git_project_root()
    except (FileNotFoundError, RuntimeError):
        return None
    return "beads" if (project_root / ".beads" / "dh-backend").is_file() else None


# ---------------------------------------------------------------------------
# DHConfig — public API
# ---------------------------------------------------------------------------


class DHConfig:
    """Unified backend-name resolver using .dh/config.yaml.

    Resolution order per subsystem (highest → lowest priority):
        1. Env var (BACKLOG_BACKEND / TASKBACKEND / CONTEXTBACKEND)
        2. Subsystem override in .dh/config.yaml
        3. Global backend.name in .dh/config.yaml
        4. .beads/dh-backend marker file auto-detect
        5. Subsystem default ("github" for backlog, "local" for task/context)
    """

    def get_backend(self, subsystem: str) -> str:
        """Resolve and return the backend name for the given subsystem.

        Args:
            subsystem: One of "backlog", "task", or "context".

        Returns:
            Backend name string.
        """
        # Step 1: env var
        env_var = _ENV_VARS.get(subsystem, "")
        env_val = os.environ.get(env_var, "")
        if env_val:
            return env_val

        # Steps 2 + 3: config file (subsystem section, then global)
        config_result = _resolve_from_config(subsystem)
        if config_result:
            return config_result

        # Step 4: .beads/ auto-detect
        beads = _auto_detect_beads()
        if beads:
            return beads

        # Step 5: default
        return _DEFAULTS.get(subsystem, "github")
