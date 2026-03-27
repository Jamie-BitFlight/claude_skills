"""Tests for manifest YAML schema dataclasses."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from manifest_schema import (
    LanguageManifest,
    ManifestValidationError,
    ProjectDetection,
    QualityGates,
    load_manifest,
    validate_manifest,
)


class TestLanguageManifest:
    """Test LanguageManifest dataclass construction and validation."""

    def test_minimal_manifest(self) -> None:
        """A manifest with only required fields should construct successfully."""
        m = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
        )
        assert m.name == "python3"
        assert m.extends is None
        assert m.stack is None
        assert m.stage_skills == {}
        assert m.quality_gates is None

    def test_full_manifest(self) -> None:
        """A manifest with all fields should construct successfully."""
        m = LanguageManifest(
            name="python3-cli",
            extends="python3-development:python3",
            language="python",
            stack="typer-cli",
            version="1.0",
            project_detection=ProjectDetection(
                markers=["pyproject.toml"],
                required_dependencies=["typer"],
                source_patterns=["src/**/*.py"],
                test_patterns=["tests/**/*.py"],
            ),
            stage_skills={
                "discovery": ["python3-discovery"],
                "implementation": ["python3-implementation", "python3-implementation-cli"],
            },
            quality_gates=QualityGates(
                format="uv run ruff format {files}",
                lint="uv run ruff check {files}",
                typecheck="uv run ty check {files}",
                test="uv run pytest tests/ --tb=short",
                standards="/python3-development:modernpython",
            ),
        )
        assert m.name == "python3-cli"
        assert m.extends == "python3-development:python3"
        assert m.stack == "typer-cli"
        assert m.project_detection.required_dependencies == ["typer"]
        assert len(m.stage_skills["implementation"]) == 2

    def test_extends_as_list(self) -> None:
        """extends field accepts a list of strings."""
        m = LanguageManifest(
            name="combo",
            extends=["python3-development:python3", "python3-development:python3-cli"],
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
        )
        assert isinstance(m.extends, list)
        assert len(m.extends) == 2


class TestProjectDetection:
    """Test ProjectDetection dataclass."""

    def test_defaults(self) -> None:
        pd = ProjectDetection(markers=["pyproject.toml"])
        assert pd.required_dependencies == []
        assert pd.source_patterns == []
        assert pd.test_patterns == []

    def test_specificity_score_no_deps(self) -> None:
        """Manifest with no required_dependencies scores 0."""
        pd = ProjectDetection(markers=["pyproject.toml"])
        assert pd.specificity_score({"typer", "rich"}) == 0

    def test_specificity_score_partial_match(self) -> None:
        """Score counts matched required_dependencies."""
        pd = ProjectDetection(markers=["pyproject.toml"], required_dependencies=["typer", "rich", "httpx"])
        assert pd.specificity_score({"typer", "rich"}) == 2

    def test_specificity_score_full_match(self) -> None:
        pd = ProjectDetection(markers=["pyproject.toml"], required_dependencies=["typer"])
        assert pd.specificity_score({"typer", "rich", "click"}) == 1

    def test_specificity_score_no_match(self) -> None:
        """If no required_dependencies match, score is 0."""
        pd = ProjectDetection(markers=["pyproject.toml"], required_dependencies=["django"])
        assert pd.specificity_score({"typer", "rich"}) == 0


class TestLoadManifest:
    """Test YAML loading into LanguageManifest."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            name: python3
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
              source_patterns: ["src/**/*.py"]
            stage_skills:
              discovery: [python3-discovery]
            quality_gates:
              lint: "uv run ruff check {files}"
              test: "uv run pytest tests/"
        """)
        manifest_file = tmp_path / "language-manifest.yaml"
        manifest_file.write_text(yaml_content)
        m = load_manifest(manifest_file)
        assert m.name == "python3"
        assert m.language == "python"
        assert m.project_detection.markers == ["pyproject.toml"]
        assert m.stage_skills["discovery"] == ["python3-discovery"]
        assert m.quality_gates is not None
        assert m.quality_gates.lint == "uv run ruff check {files}"

    def test_load_with_extends_string(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            name: python3-cli
            extends: python3-development:python3
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
              required_dependencies: [typer]
        """)
        manifest_file = tmp_path / "language-manifest.yaml"
        manifest_file.write_text(yaml_content)
        m = load_manifest(manifest_file)
        assert m.extends == "python3-development:python3"

    def test_load_with_extends_list(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            name: combo
            extends:
              - python3-development:python3
              - python3-development:python3-cli
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        manifest_file = tmp_path / "language-manifest.yaml"
        manifest_file.write_text(yaml_content)
        m = load_manifest(manifest_file)
        assert isinstance(m.extends, list)
        assert len(m.extends) == 2

    def test_load_missing_name_raises(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        manifest_file = tmp_path / "language-manifest.yaml"
        manifest_file.write_text(yaml_content)
        with pytest.raises(ManifestValidationError, match="name"):
            load_manifest(manifest_file)

    def test_load_missing_markers_raises(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            name: python3
            language: python
            version: "1.0"
            project_detection: {}
        """)
        manifest_file = tmp_path / "language-manifest.yaml"
        manifest_file.write_text(yaml_content)
        with pytest.raises(ManifestValidationError, match="markers"):
            load_manifest(manifest_file)

    def test_load_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_manifest(Path("/nonexistent/manifest.yaml"))

    def test_load_malformed_yaml_raises(self, tmp_path: Path) -> None:
        bad_yaml = tmp_path / "language-manifest.yaml"
        bad_yaml.write_text("name: python3\n  bad_indent: [unmatched\n")
        with pytest.raises(ManifestValidationError, match="Invalid YAML"):
            load_manifest(bad_yaml)


class TestValidateManifest:
    """Test manifest validation rules."""

    def test_valid_manifest_passes(self) -> None:
        m = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
        )
        result = validate_manifest(m)
        assert result.errors == []
        assert result.warnings == []

    def test_empty_markers_fails(self) -> None:
        m = LanguageManifest(
            name="python3", language="python", version="1.0", project_detection=ProjectDetection(markers=[])
        )
        result = validate_manifest(m)
        assert any("markers" in e for e in result.errors)

    def test_invalid_stage_name_warns(self) -> None:
        m = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"invalid-stage-name": ["some-skill"]},
        )
        result = validate_manifest(m)
        assert result.errors == [], "Unrecognized stages should be warnings, not errors"
        assert any("stage" in w.lower() for w in result.warnings)
