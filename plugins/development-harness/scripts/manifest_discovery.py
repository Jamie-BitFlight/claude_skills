"""Manifest discovery across priority levels.

Discovers language manifests from 5 priority levels (highest to lowest):
1. Enterprise (managed settings -- future, not implemented)
2. Personal (~/.claude/manifests/)
3. Project (.claude/manifests/)
4. Plugin (plugins/*/manifests/)
5. Skill (plugins/*/skills/*/assets/ -- most specific)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import tomlkit
import tomlkit.exceptions
from ruamel.yaml import YAMLError

from manifest_schema import LanguageManifest, ManifestValidationError, load_manifest

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "language-manifest.yaml"


class PriorityLevel(IntEnum):
    """Priority levels for manifest discovery.

    Lower numeric value = higher priority. Ordering contract:
    ENTERPRISE (1) > PERSONAL (2) > PROJECT (3) > PLUGIN (4) > SKILL (5).
    Values are compared numerically; do not reorder without updating
    all call sites that rely on ``value < other.value`` comparisons.
    """

    ENTERPRISE = 1  # Phase 2+ -- managed settings, not yet implemented
    PERSONAL = 2
    PROJECT = 3
    PLUGIN = 4
    SKILL = 5


@dataclass(slots=True)
class DiscoveredManifest:
    """A manifest discovered at a specific priority level."""

    manifest: LanguageManifest
    path: Path
    priority: PriorityLevel


def _discover_from_directory(
    base_dir: Path, priority: PriorityLevel, project_markers: set[str]
) -> list[DiscoveredManifest]:
    """Discover manifests from a directory containing manifest-name/ subdirs.

    Returns:
        List of DiscoveredManifest entries found in base_dir.
    """
    results: list[DiscoveredManifest] = []
    if not base_dir.is_dir():
        return results

    for manifest_dir in sorted(base_dir.iterdir()):
        manifest_file = manifest_dir / MANIFEST_FILENAME
        if not manifest_file.is_file():
            continue
        try:
            manifest = load_manifest(manifest_file)
        except (ManifestValidationError, FileNotFoundError, ValueError, YAMLError) as exc:
            logger.warning("Skipping %s: %s", manifest_file, exc)
            continue

        # Filter: at least one marker must match the project
        if project_markers and not (set(manifest.project_detection.markers) & project_markers):
            continue

        results.append(DiscoveredManifest(manifest=manifest, path=manifest_file, priority=priority))
    return results


def discover_manifests(
    project_root: Path, plugin_dirs: list[Path], project_markers: set[str], personal_dir: Path | None = None
) -> list[DiscoveredManifest]:
    """Discover all matching manifests across priority levels.

    Args:
        project_root: Root of the project being analyzed.
        plugin_dirs: List of plugin directories (each is plugins/plugin-name/).
        project_markers: Set of marker filenames found in the project root.
        personal_dir: Override for personal manifests dir (default: ~/.claude/manifests/).

    Returns:
        List of DiscoveredManifest, unordered.
    """
    results: list[DiscoveredManifest] = []

    # Level 2: Personal
    if personal_dir is None:
        personal_dir = Path.home() / ".claude" / "manifests"
    results.extend(_discover_from_directory(personal_dir, PriorityLevel.PERSONAL, project_markers))

    # Level 3: Project
    project_manifests_dir = project_root / ".claude" / "manifests"
    results.extend(_discover_from_directory(project_manifests_dir, PriorityLevel.PROJECT, project_markers))

    # Level 4: Plugin
    for plugin_dir in plugin_dirs:
        manifests_dir = plugin_dir / "manifests"
        results.extend(_discover_from_directory(manifests_dir, PriorityLevel.PLUGIN, project_markers))

    # Level 5: Skill
    for plugin_dir in plugin_dirs:
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            assets_dir = skill_dir / "assets"
            manifest_file = assets_dir / MANIFEST_FILENAME
            if manifest_file.is_file():
                try:
                    manifest = load_manifest(manifest_file)
                except (ManifestValidationError, FileNotFoundError, ValueError, YAMLError) as exc:
                    logger.warning("Skipping %s: %s", manifest_file, exc)
                    continue
                if project_markers and not (set(manifest.project_detection.markers) & project_markers):
                    continue
                results.append(DiscoveredManifest(manifest=manifest, path=manifest_file, priority=PriorityLevel.SKILL))

    return results


def detect_project_dependencies(project_root: Path) -> set[str]:
    """Detect project dependencies from pyproject.toml.

    Extracts package names (without version specifiers) from
    [project].dependencies in pyproject.toml.

    Returns:
        Set of lowercased package names found in dependencies.
    """
    pyproject = project_root / "pyproject.toml"
    try:
        data = tomlkit.loads(pyproject.read_text())
    except FileNotFoundError:
        return set()
    except tomlkit.exceptions.TOMLKitError as exc:
        logger.warning("Cannot read dependencies from %s: %s", pyproject, exc)
        return set()

    deps_list = data.get("project", {}).get("dependencies", [])
    result: set[str] = set()
    for dep in deps_list:
        # Strip version specifiers: "typer>=0.9" -> "typer"
        name = re.split(r"[>=<!~\[;]", str(dep))[0].strip().lower()
        if name:
            result.add(name)
    return result


def select_best_manifest(candidates: list[DiscoveredManifest], actual_deps: set[str]) -> DiscoveredManifest | None:
    """Select the best manifest by specificity scoring.

    Scoring: count of required_dependencies matching actual_deps.
    Tie-break: higher priority level (lower PriorityLevel value) wins.

    Returns:
        The highest-scoring DiscoveredManifest, or None if candidates is empty.
    """
    if not candidates:
        return None

    def score_key(dm: DiscoveredManifest) -> tuple[int, int]:
        """Higher dep match score first, then higher priority (lower int).

        Returns:
            Tuple of (dependency_match_count, negated_priority_value) for sorting.
        """
        dep_score = dm.manifest.project_detection.specificity_score(actual_deps)
        # Negate priority so lower PriorityLevel value sorts first
        return (dep_score, -dm.priority.value)

    return max(candidates, key=score_key)
