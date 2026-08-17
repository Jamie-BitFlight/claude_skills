"""Tests for experiment-registry project-root resolution.

Covers the bug where an omitted ``project_root`` argument resolved to
``Path.cwd()`` even when the process cwd is not the consuming project (e.g. an
installed plugin cache directory under a launcher like Codex).
"""

from __future__ import annotations

from pathlib import Path

from project_root import resolve_project_root


def test_resolve_project_root_uses_explicit_argument(tmp_path: Path, monkeypatch) -> None:
    """An explicit project_root argument wins over env var and cwd."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "env-root"))
    explicit = tmp_path / "explicit-root"

    resolved = resolve_project_root(str(explicit))

    assert resolved == explicit


def test_resolve_project_root_falls_back_to_env_var_when_cwd_differs(tmp_path: Path, monkeypatch) -> None:
    """Omitted project_root resolves to CLAUDE_PROJECT_DIR, not the launcher cwd.

    Reproduces the bot-reported bug: a launcher (e.g. Codex) starts the server
    with cwd inside the installed plugin cache while the real project lives
    elsewhere. Before the fix, this resolved to the cache directory (cwd, via
    ``Path.cwd()``) and experiment state was written to the wrong location.
    """
    project_root = tmp_path / "consuming-project"
    plugin_cache_cwd = tmp_path / "plugin-cache"
    project_root.mkdir()
    plugin_cache_cwd.mkdir()

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_root))
    monkeypatch.chdir(plugin_cache_cwd)

    resolved = resolve_project_root(None)

    assert resolved == project_root
    assert resolved != Path.cwd()


def test_resolve_project_root_falls_back_to_cwd_when_env_var_unset(tmp_path: Path, monkeypatch) -> None:
    """Preserves existing behavior: no env var, no argument -> cwd."""
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved = resolve_project_root(None)

    assert resolved == tmp_path
