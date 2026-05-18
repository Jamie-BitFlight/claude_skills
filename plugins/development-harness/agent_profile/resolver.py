"""Skill URI resolver for the agent-profile MCP package.

Resolves skill URIs declared in agent frontmatter to their actual filesystem
locations and content, handling three URI formats:

1. **Bare names** (``subagent-contract``): context plugin checked first, then
   global scan across all plugins.
2. **Plugin-qualified names** (``dh:subagent-contract``): splits on the first
   colon, resolves plugin alias, looks in ``plugins/{plugin}/skills/{path}/``.
3. **Domain paths** (``domains/enterprise-foo``): relative to
   ``context_plugin/skills/{path}/``.

Circular dependencies (A → B → A) are detected via a visited set of absolute
path strings and produce warnings rather than errors (ADR-4: partial profile
preferred over total failure).

Path traversal attempts (``..`` in domain paths) are caught and rejected with
warnings (never raise to MCP clients).

Public API
----------
SkillResolver  -- Class providing .resolve() for a list of URIs.
PLUGIN_ALIASES -- Module-level constant mapping short names to full plugin dirs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent_profile.discovery import _resolve_plugin_subdir, get_plugins_root
from agent_profile.models import ResolvedSkill
from agent_profile.parser import parse_skill_frontmatter, read_skill_content

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["PLUGIN_ALIASES", "SkillResolver"]

# ---------------------------------------------------------------------------
# Plugin alias map — add entries here when new short aliases are introduced.
# ---------------------------------------------------------------------------
PLUGIN_ALIASES: dict[str, str] = {"dh": "development-harness"}


class SkillResolver:
    """Resolve a list of skill URIs to :class:`~agent_profile.models.ResolvedSkill` objects.

    Args:
        plugins_root: Path to the ``plugins/`` directory. When ``None``,
            :func:`~agent_profile.discovery.get_plugins_root` resolves it
            automatically from the module file location.
    """

    def __init__(self, plugins_root: Path | None = None) -> None:
        """Initialise the resolver with an optional plugins root override.

        Args:
            plugins_root: Path to the ``plugins/`` directory. When ``None``,
                resolved automatically from the module file location.
        """
        self._plugins_root: Path = plugins_root if plugins_root is not None else get_plugins_root()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def resolve(self, skill_uris: list[str], context_plugin: str) -> tuple[list[ResolvedSkill], list[str]]:
        """Resolve *skill_uris* to filesystem-backed :class:`~agent_profile.models.ResolvedSkill` objects.

        Calls :meth:`_resolve_single` for each URI. Missing or unresolvable
        skills are recorded as warnings; resolution continues with remaining
        URIs so that a partial profile is returned rather than nothing
        (ADR-3: warnings over errors).

        Sub-skills declared in a resolved ``SKILL.md``'s own frontmatter are
        resolved recursively. Circular dependencies are caught via *visited*,
        which is freshly allocated per :meth:`resolve` call.

        Args:
            skill_uris: Ordered list of skill URI strings as declared in the
                agent frontmatter.
            context_plugin: Name of the plugin that owns the agent being
                loaded. Used for bare-name and domain-path resolution
                (context plugin searched first).

        Returns:
            A two-element tuple of:
            - ``list[ResolvedSkill]`` — resolved skills in declaration order,
              including recursively resolved sub-skills.
            - ``list[str]`` — non-fatal warning messages, one per issue
              encountered. Empty when everything resolved cleanly.
        """
        visited: set[str] = set()
        resolved: list[ResolvedSkill] = []
        warnings: list[str] = []

        for uri in skill_uris:
            self._resolve_into(uri, context_plugin, visited, resolved, warnings)

        return resolved, warnings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_into(
        self, uri: str, context_plugin: str, visited: set[str], resolved: list[ResolvedSkill], warnings: list[str]
    ) -> None:
        """Resolve *uri* and append result to *resolved*, warnings to *warnings*.

        Mutates *visited*, *resolved*, and *warnings* in-place.

        Args:
            uri: Skill URI string to resolve.
            context_plugin: Plugin name for context-first bare-name lookup.
            visited: Set of absolute path strings already resolved in this call
                chain, used for circular dependency detection.
            resolved: Accumulator list for successfully resolved skills.
            warnings: Accumulator list for non-fatal warning messages.
        """
        skill = self._resolve_single(uri, context_plugin, visited, warnings)
        if skill is None:
            return

        resolved.append(skill)

        # Recursively resolve sub-skills declared in this skill's frontmatter.
        try:
            sub_uris = parse_skill_frontmatter(skill.resolved_path)
        except FileNotFoundError:
            # The SKILL.md was readable above but now missing — degenerate case.
            warnings.append(f"Skill '{uri}': SKILL.md disappeared during sub-skill scan at {skill.resolved_path}")
            return

        for sub_uri in sub_uris:
            self._resolve_into(sub_uri, skill.plugin, visited, resolved, warnings)

    def _resolve_single(
        self, uri: str, context_plugin: str, visited: set[str], warnings: list[str]
    ) -> ResolvedSkill | None:
        """Resolve one URI string to a :class:`~agent_profile.models.ResolvedSkill`.

        Returns ``None`` and appends to *warnings* on any failure so that
        callers can continue with the remaining URIs.

        Args:
            uri: Skill URI string.
            context_plugin: Plugin name for context-first resolution.
            visited: Visited-path set. If the resolved path is already in
                this set, returns ``None`` with a circular-dependency warning.
            warnings: Warning accumulator.

        Returns:
            :class:`~agent_profile.models.ResolvedSkill` on success,
            ``None`` on any failure.
        """
        fmt, plugin_hint, skill_path = self._classify_uri(uri)

        skill_dir: Path | None = None

        match fmt:
            case "plugin-qualified":
                skill_dir = self._locate_plugin_qualified(uri, plugin_hint, skill_path, warnings)
            case "domain":
                skill_dir = self._locate_domain(uri, context_plugin, skill_path, warnings)
            case _:
                # bare
                skill_dir = self._locate_bare(uri, context_plugin, skill_path, warnings)

        if skill_dir is None:
            return None

        # Path safety: resolved path must remain within plugins_root.
        try:
            resolved_dir = skill_dir.resolve()
        except OSError as exc:
            warnings.append(f"Skill '{uri}': path resolution error — {exc}")
            return None

        if not _is_within(resolved_dir, self._plugins_root.resolve()):
            warnings.append(
                f"Skill '{uri}': resolved path {resolved_dir} escapes plugins_root "
                f"{self._plugins_root} — skipping (possible path traversal attempt)."
            )
            return None

        skill_md = resolved_dir / "SKILL.md"
        abs_key = str(skill_md)

        if abs_key in visited:
            warnings.append(f"Skill '{uri}': circular dependency detected at {skill_md} — skipping.")
            return None

        visited.add(abs_key)

        try:
            content, reference_files = read_skill_content(resolved_dir)
        except FileNotFoundError:
            warnings.append(f"Skill '{uri}': SKILL.md not found at {resolved_dir} — skipping.")
            return None

        # Derive plugin and skill_name from the resolved directory.
        resolved_plugin, resolved_skill_name = _plugin_and_name_from_dir(resolved_dir, self._plugins_root)

        return ResolvedSkill(
            uri=uri,
            resolved_path=skill_md,
            plugin=resolved_plugin,
            skill_name=resolved_skill_name,
            content=content,
            reference_files=reference_files,
        )

    # ------------------------------------------------------------------
    # URI classification
    # ------------------------------------------------------------------

    def _classify_uri(self, uri: str) -> tuple[str, str, str]:
        """Classify *uri* into a format type and decomposed components.

        Returns a three-element tuple of:

        - *format_type*: ``"bare"``, ``"plugin-qualified"``, or ``"domain"``
        - *plugin_or_empty*: Plugin name (after alias expansion) for
          plugin-qualified URIs; empty string otherwise.
        - *skill_path*: The skill path component, slash-separated.

        Args:
            uri: Raw skill URI string.

        Returns:
            ``(format_type, plugin_or_empty, skill_path)``
        """
        if uri.startswith(("domains/", "domains\\")):
            # Domain path: "domains/enterprise-foo" → relative to context plugin.
            return "domain", "", uri

        if ":" in uri:
            plugin_part, _, rest = uri.partition(":")
            # Expand known aliases.
            resolved_plugin = PLUGIN_ALIASES.get(plugin_part, plugin_part)
            return "plugin-qualified", resolved_plugin, rest

        return "bare", "", uri

    # ------------------------------------------------------------------
    # Locators for each URI format
    # ------------------------------------------------------------------

    def _locate_plugin_qualified(self, uri: str, plugin: str, skill_path: str, warnings: list[str]) -> Path | None:
        """Locate the skill directory for a plugin-qualified URI.

        Converts colon-separated *skill_path* (e.g. ``analyze-test-failures``)
        to slash-separated path components under ``plugins/{plugin}/skills/``.

        Args:
            uri: Original URI string (for warnings).
            plugin: Resolved plugin directory name (alias already expanded).
            skill_path: Path portion after the first colon in the URI. May
                contain additional colons for subdirectory skills.
            warnings: Warning accumulator.

        Returns:
            Skill directory :class:`~pathlib.Path` or ``None``.
        """
        # Colon-separated sub-path → slash-separated directory path.
        path_parts = skill_path.replace(":", "/")
        plugin_dir = self._plugins_root / plugin
        skills_dir = _resolve_plugin_subdir(plugin_dir, "skills")

        if skills_dir is None:
            warnings.append(f"Skill '{uri}': directory not found at {plugin_dir / 'skills'} — skipping.")
            return None

        skill_dir = skills_dir / path_parts

        if not skill_dir.is_dir():
            warnings.append(f"Skill '{uri}': directory not found at {skill_dir} — skipping.")
            return None

        return skill_dir

    def _locate_domain(self, uri: str, context_plugin: str, skill_path: str, warnings: list[str]) -> Path | None:
        """Locate the skill directory for a domain-path URI.

        Domain paths are relative to ``plugins/{context_plugin}/skills/``.
        Path traversal attempts (``..`` anywhere in *skill_path*) are caught
        before constructing the path.

        Args:
            uri: Original URI string (for warnings).
            context_plugin: Plugin name providing context for relative resolution.
            skill_path: The full URI value (e.g. ``domains/enterprise-foo``).
            warnings: Warning accumulator.

        Returns:
            Skill directory :class:`~pathlib.Path` or ``None``.
        """
        # Reject traversal attempts before any path construction.
        normalized = skill_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            warnings.append(f"Skill '{uri}': path traversal attempt detected in domain path '{skill_path}' — skipping.")
            return None

        plugin_dir = self._plugins_root / context_plugin
        skills_dir = _resolve_plugin_subdir(plugin_dir, "skills")

        if skills_dir is None:
            warnings.append(f"Skill '{uri}': domain path directory not found at {plugin_dir / 'skills'} — skipping.")
            return None

        skill_dir = skills_dir / skill_path

        if not skill_dir.is_dir():
            warnings.append(f"Skill '{uri}': domain path directory not found at {skill_dir} — skipping.")
            return None

        return skill_dir

    def _locate_bare(self, uri: str, context_plugin: str, skill_name: str, warnings: list[str]) -> Path | None:
        """Locate the skill directory for a bare-name URI.

        Search order:
        1. ``plugins/{context_plugin}/skills/{skill_name}/``
        2. All other plugins (``plugins/*/skills/{skill_name}/``)

        When multiple matches exist outside the context plugin, a warning is
        logged and the first (alphabetically) is used.

        Args:
            uri: Original URI string (for warnings).
            context_plugin: Plugin to check first.
            skill_name: Bare skill name string.
            warnings: Warning accumulator.

        Returns:
            Skill directory :class:`~pathlib.Path` or ``None``.
        """
        # 1. Context plugin first.
        context_plugin_dir = self._plugins_root / context_plugin
        context_skills_dir = _resolve_plugin_subdir(context_plugin_dir, "skills")
        if context_skills_dir is not None:
            context_dir = context_skills_dir / skill_name
            if context_dir.is_dir():
                return context_dir

        # 2. Global scan.
        matches: list[Path] = []
        for plugin_dir in sorted(self._plugins_root.iterdir()):
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name == context_plugin:
                continue  # Already checked.
            skills_dir = _resolve_plugin_subdir(plugin_dir, "skills")
            if skills_dir is None:
                continue
            candidate = skills_dir / skill_name
            if candidate.is_dir():
                matches.append(candidate)

        if not matches:
            warnings.append(
                f"Skill '{uri}': bare name '{skill_name}' not found in any plugin under "
                f"{self._plugins_root} — skipping."
            )
            return None

        if len(matches) > 1:
            locations = ", ".join(str(m) for m in matches)
            warnings.append(
                f"Skill '{uri}': bare name '{skill_name}' found in multiple plugins: {locations}. "
                "Using first match. Use a plugin-qualified URI to suppress this warning."
            )

        return matches[0]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _is_within(path: Path, root: Path) -> bool:
    """Return ``True`` when *path* is equal to or a descendant of *root*.

    Args:
        path: Absolute, resolved path to test.
        root: Absolute, resolved root path.

    Returns:
        ``True`` if *path* starts with *root*, ``False`` otherwise.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    else:
        return True


def _plugin_and_name_from_dir(skill_dir: Path, plugins_root: Path) -> tuple[str, str]:
    """Extract plugin name and skill name from an absolute skill directory path.

    For a path like ``plugins/development-harness/skills/subagent-contract``,
    returns ``("development-harness", "subagent-contract")``.

    For nested skill directories like
    ``plugins/development-harness/skills/analyze-test-failures``,
    returns ``("development-harness", "analyze-test-failures")``.

    Args:
        skill_dir: Absolute path to the skill directory (the directory
            containing ``SKILL.md``).
        plugins_root: Absolute path to the ``plugins/`` root directory.

    Returns:
        ``(plugin_name, skill_name)`` where *skill_name* uses ``/`` separators
        for nested skills.
    """
    # Minimum parts to safely index: plugin / skills / skill-name = 3 components.
    MIN_PARTS_FOR_PARENT = 2
    SKILLS_SUBDIR_INDEX = 2  # parts[0]=plugin, parts[1]="skills", parts[2:]=skill path

    try:
        relative = skill_dir.relative_to(plugins_root)
    except ValueError:
        # Shouldn't happen after path-safety check, but be defensive.
        return skill_dir.parts[-2] if len(skill_dir.parts) >= MIN_PARTS_FOR_PARENT else "", skill_dir.name

    parts = relative.parts  # e.g. ("development-harness", "skills", "subagent-contract")
    plugin_name = parts[0] if parts else ""
    # parts[1] is "skills", parts[2:] is the skill path.
    skill_path_parts = parts[SKILLS_SUBDIR_INDEX:] if len(parts) > SKILLS_SUBDIR_INDEX else (skill_dir.name,)
    skill_name = "/".join(skill_path_parts)

    return plugin_name, skill_name
