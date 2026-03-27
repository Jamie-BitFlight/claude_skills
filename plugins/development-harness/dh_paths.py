"""DH path constants and resolution.

All path functions return absolute Path objects. Call ensure_dirs() to
create the directory tree before writing files.

Three-tier layout
-----------------
Tier 1 — in-repo project config:
    {project_root}/.dh/              (committed, shared across developers)

Tier 2 — persistent per-project state:
    ~/.dh/projects/{slug}/backlog/
    ~/.dh/projects/{slug}/plan/
    ~/.dh/projects/{slug}/milestones/
    ~/.dh/projects/{slug}/research/

Tier 3 — ephemeral per-session state:
    ~/.dh/projects/{slug}/context/
    ~/.dh/projects/{slug}/reports/

Environment override
--------------------
Set DH_STATE_HOME to relocate all DH state (useful for tests and CI):
    DH_STATE_HOME=/tmp/test-dh uv run ...

Set a project path when the process cwd is not inside the repo (MCP servers,
plugin cache cwd, IDEs). Checked in order by :func:`infer_project_root` when
:func:`git_project_root` is called with no *cwd* argument:

    DH_PROJECT_ROOT=/path/to/repo          # explicit override (any host)
    WORKSPACE_FOLDER_PATHS=["/path"]       # VS Code / Cursor (JSON array)
    CURSOR_PROJECT_ROOT=/path/to/repo      # when the Cursor host sets it
    CLAUDE_PROJECT_DIR=/path/to/repo       # when the Claude Code host sets it

MCP layout: **Claude Code** uses ``.claude-plugin/plugin.json`` (and may merge
``.mcp.json``) with ``${CLAUDE_PLUGIN_ROOT}`` in script paths. **Cursor** uses
``.cursor-plugin/plugin.json`` with the **same** script path variable:
``${CLAUDE_PLUGIN_ROOT}/scripts/...`` — Cursor resolves ``./scripts/...`` against
``${workspaceFolder}``, not the plugin install dir. **Cursor** sets
``DH_PROJECT_ROOT`` to ``${workspaceFolder}`` for the open repo. Shared
``infer_project_root()`` consumes whichever env the active host sets.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Module-level cache: maps cwd (as str) -> resolved project root Path.
# _git_rev_parse_root() populates this on first call per cwd.
_root_cache: dict[str, Path] = {}

# IDE-specific env vars (after WORKSPACE_FOLDER_PATHS). Cursor before Claude so
# competing hosts do not prefer the other's convention when both are present.
_IDE_DISCOVERY_ENV_VARS: tuple[str, ...] = ("CURSOR_PROJECT_ROOT", "CLAUDE_PROJECT_DIR")


def _git_rev_parse_root(resolved_cwd: Path) -> Path:
    """Resolve the main worktree root via ``git rev-parse --git-common-dir``.

    Uses ``git rev-parse --path-format=absolute --git-common-dir`` which
    returns the common git dir (identical to .git/ for main worktrees; the
    shared ``../.git/`` parent for linked worktrees).  The project root is
    the parent of that directory.

    Args:
        resolved_cwd: Directory from which to run git (absolute or relative).

    Returns:
        Absolute path to the project root (main worktree root).

    Raises:
        FileNotFoundError: If the ``git`` binary is not found.
        subprocess.CalledProcessError: If the directory is not inside a
            git repository.
    """
    cwd_key = str(resolved_cwd.resolve())
    if cwd_key in _root_cache:
        return _root_cache[cwd_key]

    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd_key,
    )
    # Strip trailing whitespace / newline from git output.
    git_common_dir = Path(result.stdout.strip())
    # .git/ (or bare common dir) → parent is the project root.
    project_root = git_common_dir.parent
    _root_cache[cwd_key] = project_root
    return project_root


def _first_git_ancestor(start: Path) -> Path | None:
    """Return the nearest ancestor of *start* that contains a ``.git`` entry.

    Args:
        start: Directory to walk upward from (typically ``Path.cwd()``).

    Returns:
        That ancestor directory, or ``None`` if no ``.git`` exists on the path.
    """
    cur = start.resolve()
    for d in (cur, *cur.parents):
        if (d / ".git").exists():
            return d
    return None


def _git_root_if_directory(path: Path) -> Path | None:
    """Run git common-dir resolution for *path* if it is a directory.

    Returns:
        The resolved project root, or ``None`` if *path* is not a directory or
        git rev-parse fails.
    """
    if not path.is_dir():
        return None
    try:
        return _git_rev_parse_root(path)
    except subprocess.CalledProcessError:
        return None


def _infer_dh_project_root_env() -> Path | None:
    """Try ``DH_PROJECT_ROOT`` only (explicit host/user override).

    Returns:
        Resolved git root, or ``None`` if unset or not a valid repo.
    """
    raw = os.environ.get("DH_PROJECT_ROOT", "").strip()
    if not raw:
        return None
    return _git_root_if_directory(Path(raw).expanduser().resolve())


def _infer_from_ide_env_vars() -> Path | None:
    """Try ``CURSOR_PROJECT_ROOT`` then ``CLAUDE_PROJECT_DIR``.

    Returns:
        Resolved git root, or ``None`` if neither yields a valid repo.
    """
    for var in _IDE_DISCOVERY_ENV_VARS:
        raw = os.environ.get(var, "").strip()
        if not raw:
            continue
        resolved = _git_root_if_directory(Path(raw).expanduser().resolve())
        if resolved is not None:
            return resolved
    return None


def _infer_from_workspace_folder_paths() -> Path | None:
    """Try ``WORKSPACE_FOLDER_PATHS`` JSON array (VS Code / Cursor).

    Returns:
        Resolved git root, or ``None`` if the variable is missing or invalid.
    """
    wfp = os.environ.get("WORKSPACE_FOLDER_PATHS", "").strip()
    if not wfp.startswith("["):
        return None
    try:
        folders = json.loads(wfp)
    except json.JSONDecodeError:
        return None
    if not isinstance(folders, list):
        return None
    for item in folders:
        if not isinstance(item, str) or not item.strip():
            continue
        resolved = _git_root_if_directory(Path(item.strip()).expanduser().resolve())
        if resolved is not None:
            return resolved
    return None


def infer_project_root(cwd: Path | None = None) -> Path:
    """Resolve the git project root when the process cwd may be wrong (MCP, plugins).

    MCP servers and IDE-hosted stdio processes often start with a cwd outside
    the user's repository (for example the plugin cache).  This function tries,
    in order:

    #. ``DH_PROJECT_ROOT`` — explicit override.
    #. ``WORKSPACE_FOLDER_PATHS`` — JSON array (VS Code / Cursor); first folder
       that resolves as a git worktree.
    #. ``CURSOR_PROJECT_ROOT``, then ``CLAUDE_PROJECT_DIR`` — only if the host
       sets them (Cursor before Claude when both are present).
    #. Walk upward from *cwd* (default ``Path.cwd()``) for a ``.git`` entry,
       then git-resolve from that directory (preserves worktree semantics).
    #. Run git from *cwd* itself.

    Args:
        cwd: Directory to use for walk-up and final git attempt.  Defaults to
            ``Path.cwd()``.

    Returns:
        Absolute path to the main worktree root.

    Raises:
        FileNotFoundError: If the ``git`` binary is not found.
        RuntimeError: If resolution fails; chained from
            :exc:`subprocess.CalledProcessError` with an actionable message.
    """
    start = (cwd or Path.cwd()).resolve()

    for resolved in (_infer_dh_project_root_env(), _infer_from_workspace_folder_paths(), _infer_from_ide_env_vars()):
        if resolved is not None:
            return resolved

    ancestor = _first_git_ancestor(start)
    if ancestor is not None:
        resolved = _git_root_if_directory(ancestor)
        if resolved is not None:
            return resolved

    try:
        return _git_rev_parse_root(start)
    except subprocess.CalledProcessError as exc:
        msg = (
            "Could not resolve the git project root: process cwd is not inside a repository "
            "and no project path was found. If you use Cursor, ensure the backlog MCP entry "
            "is merged from config that expands ${workspaceFolder} (see .cursor/mcp.json or "
            "plugin .mcp.json env). Otherwise set DH_PROJECT_ROOT, WORKSPACE_FOLDER_PATHS, "
            "CURSOR_PROJECT_ROOT, or CLAUDE_PROJECT_DIR, or pass --project-dir."
        )
        raise RuntimeError(msg) from exc


def git_project_root(cwd: Path | None = None) -> Path:
    """Resolve the main worktree root via git.

    When *cwd* is ``None`` (the typical MCP / CLI default), uses
    :func:`infer_project_root` so environment and workspace hints are applied
    before ``Path.cwd()``.  When *cwd* is explicit, runs git only from that
    directory (stable for tests and callers that pin the working directory).

    Args:
        cwd: Directory from which to run git.  ``None`` enables
            :func:`infer_project_root`; a path uses git from that directory only.

    Returns:
        Absolute path to the project root (main worktree root).

    Raises:
        FileNotFoundError: If the ``git`` binary is not found.
        subprocess.CalledProcessError: If *cwd* was explicit and is not inside a
            git repository.
        RuntimeError: If *cwd* was ``None`` and all resolution strategies failed.
    """
    if cwd is not None:
        return _git_rev_parse_root(Path(cwd))
    return infer_project_root()


def compute_slug(project_root: Path) -> str:
    """Compute project slug from absolute path.

    Algorithm: replace every ``/`` in ``str(project_root)`` with ``-``.
    The leading ``-`` is intentional — it makes slugs visually distinct
    from ordinary directory names and prevents collision with numeric ids.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Slug string, e.g. ``-home-user-repos-claude_skills``.

    Examples:
        >>> from pathlib import Path
        >>> compute_slug(Path("/home/user/repos/claude_skills"))
        '-home-user-repos-claude_skills'
    """
    return str(project_root).replace("/", "-")


# ---------------------------------------------------------------------------
# Tier 1 — in-repo project config
# ---------------------------------------------------------------------------


def project_dh_dir(project_root: Path | None = None) -> Path:
    """Return ``{project_root}/.dh/`` — committed project config directory.

    Args:
        project_root: Explicit project root.  If ``None``, auto-detected
            via :func:`git_project_root`.

    Returns:
        Absolute path to the in-repo ``.dh/`` directory.
    """
    root = project_root if project_root is not None else git_project_root()
    return root / ".dh"


# ---------------------------------------------------------------------------
# State home — overridable via DH_STATE_HOME
# ---------------------------------------------------------------------------


def _dh_user_root() -> Path:
    """Return the base DH state directory.

    Reads ``DH_STATE_HOME`` environment variable.  If set, returns that
    path; otherwise returns ``~/.dh/``.

    Returns:
        Absolute Path to the DH state home.
    """
    env_override = os.environ.get("DH_STATE_HOME", "")
    if env_override:
        return Path(env_override)
    return Path.home() / ".dh"


# Module-level alias kept for consumers that import the constant directly.
# Re-computed on each access through the function so DH_STATE_HOME overrides
# set after import take effect (important for tests using monkeypatch).
def _get_dh_user_root() -> Path:
    return _dh_user_root()


# ---------------------------------------------------------------------------
# Tier 2 + Tier 3 — per-project state
# ---------------------------------------------------------------------------


def state_root(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/`` — per-project state directory.

    Args:
        project_root: Explicit project root.  If ``None``, auto-detected
            via :func:`git_project_root`.

    Returns:
        Absolute path to the per-project state root.
    """
    root = project_root if project_root is not None else git_project_root()
    slug = compute_slug(root)
    return _dh_user_root() / "projects" / slug


def backlog_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/backlog/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the backlog directory.
    """
    return state_root(project_root) / "backlog"


def plan_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/plan/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the plan directory.
    """
    return state_root(project_root) / "plan"


def milestones_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/milestones/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the milestones directory.
    """
    return state_root(project_root) / "milestones"


def research_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/research/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the research directory.
    """
    return state_root(project_root) / "research"


def context_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/context/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the context (ephemeral session files) directory.
    """
    return state_root(project_root) / "context"


def reports_dir(project_root: Path | None = None) -> Path:
    """Return ``~/.dh/projects/{slug}/reports/``.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        Absolute path to the reports directory.
    """
    return state_root(project_root) / "reports"


# ---------------------------------------------------------------------------
# Directory initialisation
# ---------------------------------------------------------------------------


def ensure_dirs(project_root: Path | None = None) -> Path:
    """Create all Tier 2 and Tier 3 directories if they do not exist.

    Also creates the Tier 1 ``.dh/`` directory and ``.dh/.gitkeep``
    inside the repo.  Idempotent — safe to call multiple times.

    Args:
        project_root: Explicit project root.  Defaults to git auto-detect.

    Returns:
        The resolved :func:`state_root` path.
    """
    root = project_root if project_root is not None else git_project_root()

    # Tier 1 — in-repo config dir
    dh_dir = project_dh_dir(root)
    dh_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = dh_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    # Tier 2 — persistent state
    for make_dir in (backlog_dir, plan_dir, milestones_dir, research_dir):
        make_dir(root).mkdir(parents=True, exist_ok=True)

    # plan/codebase sub-directory
    (plan_dir(root) / "codebase").mkdir(parents=True, exist_ok=True)

    # Tier 3 — ephemeral state
    for make_dir in (context_dir, reports_dir):
        make_dir(root).mkdir(parents=True, exist_ok=True)

    return state_root(root)


# ---------------------------------------------------------------------------
# Legacy path mapping (migration support)
# ---------------------------------------------------------------------------

LEGACY_PATH_MAP: dict[str, str] = {
    ".claude/backlog": "backlog_dir",
    "plan": "plan_dir",
    ".claude/context": "context_dir",
    ".claude/reports": "reports_dir",
    ".claude/reports/": "reports_dir",
    "plan/": "plan_dir",
    ".claude/backlog/": "backlog_dir",
    ".claude/context/": "context_dir",
}
"""Maps old repo-relative path prefixes to new dh_paths function names.

Used by the migration tool and automated reference-update scripts to
translate legacy path strings to their ``dh_paths`` equivalents.

Example entries::

    ".claude/backlog"  -> "backlog_dir"
    "plan"             -> "plan_dir"
    ".claude/context"  -> "context_dir"
    ".claude/reports"  -> "reports_dir"
"""
