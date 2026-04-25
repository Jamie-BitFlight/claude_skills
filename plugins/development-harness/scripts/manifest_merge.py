"""Manifest merge and extends resolution logic.

GitLab CI-style extends semantics:
- Scalars: child replaces parent
- Lists: child appends to parent (deduped)
- Dicts: deep merge
"""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING, Any

from manifest_schema import LanguageManifest, ProjectDetection, QualityGates, load_manifest

if TYPE_CHECKING:
    from pathlib import Path


class CircularExtendsError(Exception):
    """Raised when a circular extends chain is detected."""


def deep_merge_dicts(base: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dicts. Lists append (deduped), dicts recurse, scalars replace.

    Returns:
        New dict with merged contents.
    """
    result = dict(base)
    for key, child_val in child.items():
        if key in result:
            base_val = result[key]
            if isinstance(base_val, dict) and isinstance(child_val, dict):
                result[key] = deep_merge_dicts(base_val, child_val)
            elif isinstance(base_val, list) and isinstance(child_val, list):
                result[key] = list(dict.fromkeys(base_val + child_val))
            else:
                result[key] = child_val
        else:
            result[key] = child_val
    return result


def _merge_quality_gates(parent: QualityGates | None, child: QualityGates | None) -> QualityGates | None:
    if parent is None:
        return child
    if child is None:
        return parent
    merged = {}
    for f in fields(QualityGates):
        child_val = getattr(child, f.name)
        merged[f.name] = child_val if child_val is not None else getattr(parent, f.name)
    return QualityGates(**merged)


def _merge_project_detection(parent: ProjectDetection, child: ProjectDetection) -> ProjectDetection:
    return ProjectDetection(
        markers=child.markers or parent.markers,
        required_dependencies=list(dict.fromkeys(parent.required_dependencies + child.required_dependencies)),
        source_patterns=parent.source_patterns + child.source_patterns,
        test_patterns=parent.test_patterns + child.test_patterns,
    )


def merge_manifests(parent: LanguageManifest, child: LanguageManifest) -> LanguageManifest:
    """Merge parent and child manifests following extends semantics.

    Returns:
        New LanguageManifest with child values taking precedence.
    """
    merged_skills = deep_merge_dicts(parent.stage_skills, child.stage_skills)
    merged_gates = _merge_quality_gates(parent.quality_gates, child.quality_gates)
    merged_detection = _merge_project_detection(parent.project_detection, child.project_detection)
    return LanguageManifest(
        name=child.name,
        extends=None,
        language=child.language or parent.language,
        stack=child.stack if child.stack is not None else parent.stack,
        version=child.version or parent.version,
        project_detection=merged_detection,
        stage_skills=merged_skills,
        quality_gates=merged_gates,
    )


def _resolve_extends_ref(ref: str, child_path: Path, search_paths: list[tuple[str, Path]]) -> Path:
    if ref.startswith(("./", "../")):
        resolved = (child_path.parent / ref).resolve()
        if not resolved.exists():
            msg = f"Extends path not found: {ref} (resolved to {resolved})"
            raise FileNotFoundError(msg)
        return resolved
    if ":" in ref:
        plugin_name, manifest_name = ref.split(":", 1)
        filtered_paths = [(n, p) for n, p in search_paths if n == plugin_name]
        if not filtered_paths:
            filtered_paths = search_paths
    else:
        manifest_name = ref
        filtered_paths = search_paths
    for _name, search_path in filtered_paths:
        candidate = search_path / manifest_name / "language-manifest.yaml"
        if candidate.exists():
            return candidate
    path_strs = [f"{name}:{p}" for name, p in search_paths]
    msg = f"Cannot resolve extends reference '{ref}' in search paths: {path_strs}"
    raise FileNotFoundError(msg)


def resolve_extends_chain(
    manifest_path: Path, search_paths: list[tuple[str, Path]], _seen: set[str] | None = None
) -> LanguageManifest:
    """Recursively resolve the extends chain for a manifest.

    Returns:
        Fully resolved LanguageManifest with all parent fields merged.
    """
    if _seen is None:
        _seen = set()
    manifest = load_manifest(manifest_path)
    if manifest.name in _seen:
        msg = f"Circular extends chain detected: {manifest.name} already in chain {_seen}"
        raise CircularExtendsError(msg)
    _seen.add(manifest.name)
    if manifest.extends is None:
        return manifest
    extends_list: list[str] = manifest.extends if isinstance(manifest.extends, list) else [manifest.extends]
    resolved_base: LanguageManifest | None = None
    for ref in extends_list:
        parent_path = _resolve_extends_ref(ref, manifest_path, search_paths)
        parent_resolved = resolve_extends_chain(parent_path, search_paths, _seen)
        resolved_base = parent_resolved if resolved_base is None else merge_manifests(resolved_base, parent_resolved)
    if resolved_base is not None:
        return merge_manifests(resolved_base, manifest)
    return manifest
