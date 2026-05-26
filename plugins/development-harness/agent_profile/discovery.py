"""Agent file discovery for the agent-profile MCP package.

Provides three public functions:

- :func:`get_plugins_root` — resolve the ``plugins/`` directory from the
  module's own location without requiring an environment variable.
- :func:`scan_all_agents` — enumerate every agent ``.md`` file across all
  installed plugins, returning a sorted :class:`~agent_profile.models.AgentEntry`
  list.
- :func:`find_agent` — locate a single agent by bare name or
  plugin-qualified name (``plugin:agent-name``), raising on ambiguity or
  absence.

Subdirectory agents (``agents/subdir/name.md``) are represented with
colon-separated names (``subdir:name``) so that the same colon-qualified
lookup syntax used by skills also works for agents.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import re
from pathlib import Path

from .models import AgentEntry

logger = logging.getLogger(__name__)

__all__ = ["_resolve_plugin_subdir", "find_agent", "get_plugins_root", "scan_all_agents"]

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")


def _looks_like_semver(name: str) -> bool:
    """Return True if *name* looks like a semver version (e.g., '4.4.25')."""
    return bool(_SEMVER_RE.match(name))


def get_plugins_root() -> Path:
    """Return the absolute path to the directory that contains all plugin directories.

    Uses ``CLAUDE_PLUGIN_ROOT`` env var (set by Claude Code for MCP server
    subprocesses and hooks) when available.  Falls back to walking up from
    ``__file__`` for repo-layout development.

    Layout differences::

        Repo:  plugins/development-harness/agents/
               CLAUDE_PLUGIN_ROOT = plugins/development-harness/
               plugins_root       = plugins/                        (.parent)

        Cache: cache/org/development-harness/4.4.19/agents/
               CLAUDE_PLUGIN_ROOT = cache/org/development-harness/4.4.19/
               plugins_root       = cache/org/                      (.parent.parent)

    Returns:
        Absolute :class:`~pathlib.Path` to the directory whose children are the
        individual plugin directories (e.g. ``python3-development/``,
        ``plugin-creator/``, ``development-harness/``).

    Raises:
        FileNotFoundError: When the plugins root cannot be determined.
    """
    plugin_root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root_env:
        plugin_root = Path(plugin_root_env).resolve()
        # Detect layout: in the cache, plugin_root is a version directory
        # (e.g., 4.4.19/) inside a plugin-name directory.  The parent of
        # plugin_root is the plugin-name dir, which contains only version
        # dirs — not sibling plugins.  Go up one more to reach the org dir.
        #
        # In the repo, plugin_root IS the plugin dir (development-harness/)
        # and its parent (plugins/) directly contains sibling plugins.
        candidate = plugin_root.parent
        # Check if candidate has sibling dirs that are real plugins (not
        # version-number dirs like 4.4.25/ that also contain agents/).
        has_sibling_plugins = any(
            d.is_dir()
            and d.name != plugin_root.name
            and not _looks_like_semver(d.name)
            and ((d / "agents").is_dir() or (d / "skills").is_dir())
            for d in candidate.iterdir()
            if d.is_dir()
        )
        if has_sibling_plugins:
            logger.debug("plugins_root from CLAUDE_PLUGIN_ROOT (repo): %s", candidate)
            return candidate
        # Cache layout: candidate is plugin-name dir with version subdirs.
        # Go up one more level to the org directory.
        plugins_root = candidate.parent
        if plugins_root.exists():
            logger.debug("plugins_root from CLAUDE_PLUGIN_ROOT (cache): %s", plugins_root)
            return plugins_root

    # Fallback: walk up from __file__ to find agents/ directory.
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "agents").is_dir():
            candidate = current.parent
            has_sibling_plugins = any(
                d.is_dir()
                and d.name != current.name
                and not _looks_like_semver(d.name)
                and ((d / "agents").is_dir() or (d / "skills").is_dir())
                for d in candidate.iterdir()
                if d.is_dir()
            )
            if has_sibling_plugins:
                logger.debug("plugins_root from __file__ walk (repo): %s", candidate)
                return candidate
            plugins_root = candidate.parent
            if plugins_root.exists():
                logger.debug("plugins_root from __file__ walk (cache): %s", plugins_root)
                return plugins_root
            return candidate
        current = current.parent

    raise FileNotFoundError(
        f"Could not locate the plugin root. "
        f"Searched ancestors of {Path(__file__).resolve()} for 'agents/' subdirectory "
        "and CLAUDE_PLUGIN_ROOT is not set."
    )


def _resolve_plugin_subdir(plugin_dir: Path, subdir_name: str) -> Path | None:
    """Return the path to *subdir_name* inside *plugin_dir*, handling both layouts.

    Repo layout::

        plugins/plugin-name/agents/         <- direct child
        plugins/plugin-name/skills/         <- direct child

    Cache layout::

        cache/org/plugin-name/7.2.8/agents/ <- versioned subdir
        cache/org/plugin-name/7.2.8/skills/ <- versioned subdir

    When the direct child does not exist, the function inspects immediate
    children for semver-looking directories and returns the *subdir_name*
    directory of the highest version.  Returns ``None`` when *subdir_name*
    cannot be found in either location.

    Args:
        plugin_dir: Directory that is either a plugin directory (repo layout)
            or a plugin-name directory whose children are version dirs (cache
            layout).
        subdir_name: Name of the subdirectory to locate (e.g. ``"agents"`` or
            ``"skills"``).

    Returns:
        Absolute :class:`~pathlib.Path` to the requested subdirectory, or
        ``None`` if it is not found.
    """
    direct = plugin_dir / subdir_name
    if direct.is_dir():
        return direct

    # Cache layout: look for semver-named child directories that contain subdir_name.
    # Guard against plugin_dir not existing (e.g. context plugin with no skills/).
    if not plugin_dir.is_dir():
        return None

    version_dirs = [
        d for d in plugin_dir.iterdir() if d.is_dir() and _looks_like_semver(d.name) and (d / subdir_name).is_dir()
    ]
    if not version_dirs:
        return None

    # Sort by version components numerically to pick the highest version.
    def _version_key(p: Path) -> tuple[int, ...]:
        try:
            return tuple(int(x) for x in p.name.split("."))
        except ValueError:
            return (0,)

    best = max(version_dirs, key=_version_key)
    return best / subdir_name


def _resolve_agents_dir(plugin_dir: Path) -> Path | None:
    """Return the ``agents/`` directory for *plugin_dir*, handling both layouts.

    Delegates to :func:`_resolve_plugin_subdir` with ``subdir_name="agents"``.

    Args:
        plugin_dir: Directory that is either a plugin directory (repo layout)
            or a plugin-name directory whose children are version dirs (cache
            layout).

    Returns:
        Absolute :class:`~pathlib.Path` to the ``agents/`` directory, or
        ``None`` if no ``agents/`` directory is found.
    """
    return _resolve_plugin_subdir(plugin_dir, "agents")


@functools.cache
def _build_manifest_name_index(plugins_root: Path) -> dict[str, Path]:
    """Scan *plugins_root* for ``.claude-plugin/plugin.json`` manifests and return a name→directory mapping.

    Handles both repo layout (manifest directly under plugin dir) and cache layout
    (manifest under a semver-named version subdir — picks the highest version).
    Malformed or unreadable manifests are skipped with a warning so that sibling
    plugins remain resolvable.

    Args:
        plugins_root: Absolute path to the directory whose children are individual
            plugin directories (e.g. ``plugins/``).

    Returns:
        ``dict`` mapping manifest ``"name"`` field value → absolute plugin directory
        ``Path`` (not the versioned subdir).

    Raises:
        ValueError: When two plugin directories declare the same manifest name,
            listing both conflicting paths in the message.
    """
    index: dict[str, Path] = {}
    if not plugins_root.is_dir():
        return index

    for plugin_dir in sorted(plugins_root.iterdir()):
        if not plugin_dir.is_dir() or _looks_like_semver(plugin_dir.name):
            continue

        # Repo layout: <plugin-dir>/.claude-plugin/plugin.json
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            # Cache layout: <plugin-dir>/<semver>/.claude-plugin/plugin.json
            version_dirs = [d for d in plugin_dir.iterdir() if d.is_dir() and _looks_like_semver(d.name)]
            if version_dirs:
                best = max(version_dirs, key=lambda p: tuple(int(x) for x in p.name.split(".")))
                manifest_path = best / ".claude-plugin" / "plugin.json"

        if not manifest_path.is_file():
            continue

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            name: str = data["name"]
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("Skipping malformed manifest %s: %s", manifest_path, exc)
            continue

        if name in index:
            raise ValueError(
                f"Duplicate plugin manifest name '{name}' declared by two plugins: {index[name]} and {plugin_dir}"
            )
        index[name] = plugin_dir

    return index


def _resolve_plugin_dir_by_manifest_name(plugin_name: str, plugins_root: Path) -> Path | None:
    """Return the plugin directory for *plugin_name* by scanning manifests, or ``None``.

    Args:
        plugin_name: The ``"name"`` field value from a ``.claude-plugin/plugin.json``
            manifest (e.g. ``"dh"``).
        plugins_root: Absolute path to the directory whose children are individual
            plugin directories.

    Returns:
        Absolute :class:`~pathlib.Path` to the matching plugin directory, or ``None``
        if no manifest declares *plugin_name*.
    """
    index = _build_manifest_name_index(plugins_root)
    return index.get(plugin_name)


def _get_manifest_name_for_dir(plugin_dir: Path, plugins_root: Path) -> str:
    """Return the manifest name for *plugin_dir*, falling back to directory name.

    Calls :func:`_build_manifest_name_index` (cached) and performs a reverse
    lookup — given a resolved directory, return the manifest ``"name"`` value
    if one exists.

    Args:
        plugin_dir: Absolute path to the resolved plugin directory.
        plugins_root: Absolute path to the plugins root (used for cache key).

    Returns:
        Manifest ``"name"`` field if *plugin_dir* appears in the index; otherwise
        ``plugin_dir.name`` (the directory name as fallback).
    """
    index = _build_manifest_name_index(plugins_root)
    # Reverse lookup: find the manifest name whose value is plugin_dir.
    for manifest_name, dir_path in index.items():
        if dir_path == plugin_dir:
            return manifest_name
    return plugin_dir.name


def _agent_name_from_path(agent_path: Path, agents_dir: Path) -> str:
    """Derive the colon-separated agent name from its path relative to agents_dir.

    Examples::

        agents/code-reviewer.md           -> "code-reviewer"
        agents/testing/unit-tester.md     -> "testing:unit-tester"

    Args:
        agent_path: Absolute path to the agent ``.md`` file.
        agents_dir: Absolute path to the plugin's ``agents/`` directory.

    Returns:
        Colon-separated name string.
    """
    relative = agent_path.relative_to(agents_dir)
    # Remove the .md suffix from the final component.
    parts = list(relative.parts)
    parts[-1] = parts[-1][: -len(".md")]
    return ":".join(parts)


def scan_all_agents(plugins_root: Path | None = None) -> list[AgentEntry]:
    """Scan all plugins for agent definition files and return a sorted list.

    Searches ``plugins/*/agents/**/*.md`` for agent definitions. Agents in
    subdirectories produce colon-separated names
    (e.g. ``agents/testing/unit-tester.md`` → name ``testing:unit-tester``).

    The result is sorted by ``(plugin, name)`` for deterministic ordering.

    Args:
        plugins_root: Path to the ``plugins/`` directory. When ``None``,
            :func:`get_plugins_root` is called to resolve it automatically.

    Returns:
        Sorted list of :class:`~agent_profile.models.AgentEntry` objects,
        one per discovered agent file. Returns an empty list when no
        ``agents/`` directories exist.
    """
    if plugins_root is None:
        plugins_root = get_plugins_root()

    entries: list[AgentEntry] = []

    for plugin_dir in sorted(plugins_root.iterdir()):
        if not plugin_dir.is_dir():
            continue
        # Skip version-numbered directories that appear directly under
        # plugins_root (can happen in unusual layouts).
        if _looks_like_semver(plugin_dir.name):
            continue
        agents_dir = _resolve_agents_dir(plugin_dir)
        if agents_dir is None:
            continue

        # Use manifest name when .claude-plugin/plugin.json declares one; fall back
        # to directory name so that plugins without a manifest continue to work.
        plugin_name = _get_manifest_name_for_dir(plugin_dir, plugins_root)

        for agent_file in sorted(agents_dir.rglob("*.md")):
            if not agent_file.is_file():
                continue
            name = _agent_name_from_path(agent_file, agents_dir)
            entries.append(AgentEntry(name=name, plugin=plugin_name, path=agent_file))

    return entries


def find_agent(agent_name: str, plugins_root: Path | None = None) -> AgentEntry:
    """Locate a single agent by name and return its :class:`~agent_profile.models.AgentEntry`.

    Supports two addressing forms:

    **Plugin-qualified** (``plugin:agent-name`` or ``plugin:subdir:name``):
        Splits on the first colon, resolves the plugin directory, and constructs
        the expected path directly without scanning. The remainder after the first
        colon is used as a slash-delimited path relative to ``agents/``.
        Example: ``python3-development:code-reviewer``
        → ``plugins/python3-development/agents/code-reviewer.md``

    **Bare name** (no colon):
        Scans all plugins. Exactly one match → returns it. Zero matches →
        raises :class:`FileNotFoundError`. Two or more matches across different
        plugins → raises :class:`ValueError` (ambiguous; use a plugin-qualified
        name to disambiguate).

    Subdirectory-qualified bare names use the colon separator, e.g. the agent
    at ``agents/testing/unit-tester.md`` in any plugin has the bare name
    ``testing:unit-tester``. When such a name is passed, the first colon is
    treated as the plugin qualifier, so callers should always use a
    plugin-qualified form for subdirectory agents to avoid ambiguity.

    Args:
        agent_name: Agent name in bare (``code-reviewer``) or plugin-qualified
            (``python3-development:code-reviewer``) form. Subdirectory agents
            should be plugin-qualified (``dh:analyze-test-failures``)
            to avoid false-positive plugin detection.
        plugins_root: Path to ``plugins/``. When ``None``,
            :func:`get_plugins_root` resolves it automatically.

    Returns:
        Matching :class:`~agent_profile.models.AgentEntry`.

    Raises:
        FileNotFoundError: When no agent matching *agent_name* is found.
        ValueError: When *agent_name* is a bare name that matches agents in
            two or more different plugins (ambiguous).
    """
    if plugins_root is None:
        plugins_root = get_plugins_root()

    if ":" in agent_name:
        return _find_plugin_qualified(agent_name, plugins_root)

    return _find_bare(agent_name, plugins_root)


def _find_plugin_qualified(agent_name: str, plugins_root: Path) -> AgentEntry:
    """Resolve a plugin-qualified agent name (``plugin:rest``) directly.

    Args:
        agent_name: Plugin-qualified name with at least one colon.
        plugins_root: Absolute path to ``plugins/``.

    Returns:
        :class:`~agent_profile.models.AgentEntry` for the agent.

    Raises:
        FileNotFoundError: When the expected file does not exist.
    """
    plugin_part, _, rest = agent_name.partition(":")

    # Fast path: try treating plugin_part as a filesystem directory name.
    candidate_dir = plugins_root / plugin_part
    if candidate_dir.is_dir():
        plugin_dir = candidate_dir
    else:
        # Manifest fallback: resolve plugin_part via .claude-plugin/plugin.json name fields.
        resolved = _resolve_plugin_dir_by_manifest_name(plugin_part, plugins_root)
        if resolved is None:
            raise FileNotFoundError(
                f"No plugin named '{plugin_part}' (checked directory names and "
                f".claude-plugin/plugin.json manifests) in {plugins_root}"
            )
        plugin_dir = resolved

    agents_dir = _resolve_agents_dir(plugin_dir)
    if agents_dir is None:
        raise FileNotFoundError(f"Agent '{agent_name}' not found: no agents/ directory under {plugin_dir}")

    # Convert colon-separated remainder to a slash path + .md suffix.
    relative_path = Path(*rest.split(":")).with_suffix(".md")
    agent_file = agents_dir / relative_path

    if not agent_file.is_file():
        raise FileNotFoundError(f"Agent '{agent_name}' not found: expected file at {agent_file}")

    name = _agent_name_from_path(agent_file, agents_dir)
    # Normalise plugin field to manifest name (Option A policy).  When the caller
    # used the directory name as the qualifier, the manifest name takes precedence so
    # that AgentEntry.plugin is consistent across find_agent() and scan_all_agents().
    normalised_plugin = _get_manifest_name_for_dir(plugin_dir, plugins_root)
    return AgentEntry(name=name, plugin=normalised_plugin, path=agent_file)


def _find_bare(agent_name: str, plugins_root: Path) -> AgentEntry:
    """Scan all plugins for a bare agent name and return the unique match.

    Args:
        agent_name: Bare agent name (no colon), e.g. ``code-reviewer``.
        plugins_root: Absolute path to ``plugins/``.

    Returns:
        :class:`~agent_profile.models.AgentEntry` for the unique matching agent.

    Raises:
        FileNotFoundError: When no match is found across all plugins.
        ValueError: When two or more plugins contain an agent with this name.
    """
    all_agents = scan_all_agents(plugins_root)
    matches = [entry for entry in all_agents if entry.name == agent_name]

    if len(matches) == 1:
        return matches[0]

    if len(matches) == 0:
        raise FileNotFoundError(
            f"Agent '{agent_name}' not found in any plugin under {plugins_root}. "
            "Check the agent name or use a plugin-qualified form."
        )

    # Multiple matches — report which plugins contain this agent.
    locations = ", ".join(f"{m.plugin}/{m.name}" for m in matches)
    raise ValueError(
        f"Ambiguous agent name '{agent_name}': found in multiple plugins: {locations}. "
        "Use a plugin-qualified name (e.g. 'plugin-name:agent-name') to disambiguate."
    )
