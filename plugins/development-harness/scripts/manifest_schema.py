"""Language manifest YAML schema dataclasses."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ruamel.yaml import YAML, YAMLError

if TYPE_CHECKING:
    from pathlib import Path

_YAML = YAML()

# Canonical SDLC stage identifiers
VALID_STAGES: frozenset[str] = frozenset({
    "discovery",
    "design",
    "planning-context-integration",
    "planning-task-decomposition",
    "implementation",
    "testing-forensic-review",
    "testing-verification",
})


@dataclass(slots=True)
class ProjectDetection:
    """Project detection rules for a language manifest."""

    markers: list[str]
    required_dependencies: list[str] = field(default_factory=list)
    source_patterns: list[str] = field(default_factory=list)
    test_patterns: list[str] = field(default_factory=list)

    def specificity_score(self, actual_deps: set[str]) -> int:
        """Score this manifest against actual project dependencies.

        Returns:
            Count of required_dependencies that appear in actual_deps.
        """
        if not self.required_dependencies:
            return 0
        return len(set(self.required_dependencies) & actual_deps)


@dataclass(slots=True)
class QualityGates:
    """Quality gate commands for a language manifest."""

    format: str | None = None
    lint: str | None = None
    typecheck: str | None = None
    test: str | None = None
    standards: str | None = None


@dataclass(slots=True)
class LanguageManifest:
    """A language manifest declaring stack-specific configuration."""

    name: str
    language: str
    version: str
    project_detection: ProjectDetection
    extends: str | list[str] | None = None
    stack: str | None = None
    stage_skills: dict[str, list[str]] = field(default_factory=dict)
    quality_gates: QualityGates | None = None


class ManifestValidationError(Exception):
    """Raised when a manifest fails validation."""


@dataclass(slots=True)
class ValidationResult:
    """Structured validation result."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_manifest(manifest: LanguageManifest) -> ValidationResult:
    """Validate a loaded manifest.

    Returns:
        ValidationResult with errors and warnings populated.
    """
    result = ValidationResult()
    if not manifest.project_detection.markers:
        result.errors.append("project_detection.markers must not be empty")
    for stage in manifest.stage_skills:
        if stage not in VALID_STAGES:
            result.warnings.append(
                f"Unrecognized stage name '{stage}' in stage_skills. Valid stages: {', '.join(sorted(VALID_STAGES))}"
            )
    return result


def _parse_yaml_data(path: Path) -> dict:
    """Read and validate raw YAML data from a manifest file.

    Returns:
        Parsed YAML data as a dict.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ManifestValidationError: If the YAML is invalid or not a mapping.
    """
    try:
        data = _YAML.load(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Manifest not found: {path}") from None
    except YAMLError as exc:
        msg = f"Invalid YAML in manifest {path}: {exc}"
        raise ManifestValidationError(msg) from exc
    if not isinstance(data, dict):
        msg = f"Manifest must be a YAML mapping, got {type(data).__name__}"
        raise ManifestValidationError(msg)

    for required_field in ("name", "language", "version"):
        if required_field not in data:
            msg = f"Missing required field: {required_field}"
            raise ManifestValidationError(msg)

    pd_data = data.get("project_detection", {})
    if not isinstance(pd_data, dict) or "markers" not in pd_data:
        msg = "project_detection.markers is required"
        raise ManifestValidationError(msg)

    return data


def load_manifest(path: Path) -> LanguageManifest:
    """Load a language manifest from a YAML file.

    Returns:
        Fully validated LanguageManifest instance.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ManifestValidationError: If the manifest fails structural or semantic validation.
    """
    data = _parse_yaml_data(path)

    pd_data = data.get("project_detection", {})
    project_detection = ProjectDetection(
        markers=list(pd_data.get("markers", [])),
        required_dependencies=list(pd_data.get("required_dependencies", [])),
        source_patterns=list(pd_data.get("source_patterns", [])),
        test_patterns=list(pd_data.get("test_patterns", [])),
    )

    qg_data = data.get("quality_gates")
    quality_gates = None
    if isinstance(qg_data, dict):
        quality_gates = QualityGates(
            format=qg_data.get("format"),
            lint=qg_data.get("lint"),
            typecheck=qg_data.get("typecheck"),
            test=qg_data.get("test"),
            standards=qg_data.get("standards"),
        )

    stage_skills_data = data.get("stage_skills", {})
    stage_skills: dict[str, list[str]] = {}
    if isinstance(stage_skills_data, dict):
        for stage, skill_val in stage_skills_data.items():
            skill_list = skill_val if isinstance(skill_val, list) else [skill_val]
            stage_skills[str(stage)] = [str(s) for s in skill_list]

    manifest = LanguageManifest(
        name=data["name"],
        extends=data.get("extends"),
        language=data["language"],
        stack=data.get("stack"),
        version=str(data["version"]),
        project_detection=project_detection,
        stage_skills=stage_skills,
        quality_gates=quality_gates,
    )

    validation = validate_manifest(manifest)
    if validation.errors:
        msg = f"Manifest validation failed for {path}: {'; '.join(validation.errors)}"
        raise ManifestValidationError(msg)
    for warning in validation.warnings:
        logging.getLogger(__name__).warning("Manifest %s: %s", path, warning)

    return manifest
