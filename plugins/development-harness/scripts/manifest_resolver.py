#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml", "tomlkit", "typer", "rich"]
# ///
"""Manifest resolver CLI -- discover, score, resolve, return manifest.

Usage:
    uv run manifest_resolver.py resolve /path/to/project [--plugin-dir DIR]...
    uv run manifest_resolver.py show /path/to/manifest.yaml
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Any, cast

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console

from manifest_discovery import DiscoveredManifest, detect_project_dependencies, discover_manifests, select_best_manifest
from manifest_merge import resolve_extends_chain
from manifest_schema import LanguageManifest, ManifestValidationError, load_manifest

app = typer.Typer(help="Language manifest resolver for the development harness.")
console = Console(stderr=True)


def _detect_project_markers(project_root: Path, plugin_dirs: list[Path] | None = None) -> set[str]:
    """Detect which marker files exist in the project root.

    Derives known markers from loaded manifests when plugin_dirs are provided,
    falling back to a minimal default set for bootstrapping.

    Returns:
        Set of marker filenames that exist in the project root.
    """
    # Minimal fallback set for when no manifests are available yet
    known_markers = {"pyproject.toml", "package.json", "Cargo.toml", "go.mod"}

    # Derive additional markers from discovered manifests
    if plugin_dirs:
        for pd in plugin_dirs:
            manifests_dir = pd / "manifests"
            if not manifests_dir.is_dir():
                continue
            for manifest_dir in manifests_dir.iterdir():
                manifest_file = manifest_dir / "language-manifest.yaml"
                if manifest_file.is_file():
                    try:
                        m = load_manifest(manifest_file)
                        known_markers.update(m.project_detection.markers)
                    except (FileNotFoundError, ValueError, ManifestValidationError):
                        continue

    return {m for m in known_markers if (project_root / m).exists()}


def _read_plugin_name(plugin_dir: Path) -> str | None:
    """Read the canonical plugin name from plugin.json.

    Returns:
        The 'name' field from .claude-plugin/plugin.json or
        plugin.json, or None if neither exists or is unreadable.
    """
    for candidate in (plugin_dir / ".claude-plugin" / "plugin.json", plugin_dir / "plugin.json"):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text())
                return data.get("name")
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _collect_search_paths(
    plugin_dirs: list[Path], project_root: Path | None = None, personal_dir: Path | None = None
) -> list[tuple[str, Path]]:
    """Collect all manifest search paths with their canonical plugin names.

    Includes all 5 priority levels (except enterprise, deferred to Phase 2):
    - Personal: ~/.claude/manifests/
    - Project: .claude/manifests/
    - Plugin: plugins/*/manifests/
    - Skill-level paths are not included here (handled by discover_manifests)

    Returns:
        List of (plugin_name, manifests_path) tuples. For project-level and
        personal-level paths, plugin_name is "__project__" or "__personal__"
        respectively (synthetic names that cannot collide with real plugins).
    """
    paths: list[tuple[str, Path]] = []

    # Personal-level manifests
    if personal_dir is None:
        personal_dir = Path.home() / ".claude" / "manifests"
    if personal_dir.is_dir():
        paths.append(("__personal__", personal_dir))

    # Project-level manifests
    if project_root is not None:
        project_manifests = project_root / ".claude" / "manifests"
        if project_manifests.is_dir():
            paths.append(("__project__", project_manifests))

    # Plugin-level manifests -- use canonical name from plugin.json
    for pd in plugin_dirs:
        manifests_dir = pd / "manifests"
        if manifests_dir.is_dir():
            plugin_name = _read_plugin_name(pd) or pd.name
            paths.append((plugin_name, manifests_dir))

    return paths


def _dedup_by_name_priority(candidates: list[DiscoveredManifest]) -> list[DiscoveredManifest]:
    """Deduplicate manifests by name, keeping highest priority (lowest int).

    Architecture spec: "Higher-priority locations win when manifests share
    the same name." This dedup happens BEFORE scoring by specificity.

    Returns:
        List of DiscoveredManifest with at most one entry per manifest name.
    """
    best_by_name: dict[str, DiscoveredManifest] = {}
    for dm in candidates:
        name = dm.manifest.name
        if name not in best_by_name or dm.priority.value < best_by_name[name].priority.value:
            best_by_name[name] = dm
    return list(best_by_name.values())


def resolve_for_project(
    project_root: Path, plugin_dirs: list[Path], personal_dir: Path | None = None
) -> LanguageManifest | None:
    """Full resolution pipeline: discover -> dedup by name -> score -> select -> resolve extends.

    Returns:
        The fully resolved manifest for the project, or None if no
        matching manifest is found.
    """
    markers = _detect_project_markers(project_root, plugin_dirs)
    if not markers:
        return None

    candidates = discover_manifests(
        project_root=project_root, plugin_dirs=plugin_dirs, project_markers=markers, personal_dir=personal_dir
    )
    if not candidates:
        return None

    # Dedup same-name manifests by priority BEFORE scoring (C2)
    candidates = _dedup_by_name_priority(candidates)

    actual_deps = detect_project_dependencies(project_root)
    best = select_best_manifest(candidates, actual_deps)
    if best is None:
        return None

    # Collect search paths from all 5 levels (C3) -- includes personal + project
    search_paths = _collect_search_paths(plugin_dirs, project_root=project_root, personal_dir=personal_dir)
    return resolve_extends_chain(best.path, search_paths=search_paths)


def _normalize_for_json(obj: object) -> object:
    """Recursively normalize types for JSON serialization.

    Returns:
        JSON-compatible object with Path, set, and enum types converted.
    """
    if isinstance(obj, dict):
        return {str(k): _normalize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_json(item) for item in obj]
    if isinstance(obj, set):
        return sorted(str(item) for item in obj)
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _manifest_to_dict(m: LanguageManifest) -> dict[str, Any]:
    """Convert manifest to a JSON-serializable dict.

    Returns:
        Dict representation of the manifest with all types JSON-compatible.
    """
    raw = asdict(m)
    return cast("dict[str, Any]", _normalize_for_json(raw))


def _validate_plugin_dir(path: Path) -> Path:
    """Typer callback to validate --plugin-dir exists and is a directory.

    Returns:
        The validated path if it exists and is a directory.
    """
    if not path.is_dir():
        msg = f"Plugin directory does not exist or is not a directory: {path}"
        raise typer.BadParameter(msg)
    return path


@app.command()
def resolve(
    project_root: Annotated[Path, typer.Argument(help="Path to the project root")],
    plugin_dir: Annotated[
        list[Path] | None,
        typer.Option("--plugin-dir", help="Plugin directories to search for manifests", callback=_validate_plugin_dir),
    ] = None,
) -> None:
    """Resolve the best manifest for a project and print as JSON."""
    if plugin_dir is None:
        plugin_dir = []
    result = resolve_for_project(project_root, plugin_dir)
    if result is None:
        console.print("[yellow]No matching manifest found.[/yellow]")
        raise typer.Exit(1)

    print(json.dumps(_manifest_to_dict(result), indent=2))


@app.command()
def show(manifest_path: Annotated[Path, typer.Argument(help="Path to a manifest YAML file")]) -> None:
    """Load and display a single manifest as JSON (no extends resolution)."""
    m = load_manifest(manifest_path)
    print(json.dumps(_manifest_to_dict(m), indent=2))


if __name__ == "__main__":
    app()
