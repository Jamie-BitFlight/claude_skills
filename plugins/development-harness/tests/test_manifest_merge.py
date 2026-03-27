"""Tests for manifest extends resolution and merge logic."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from manifest_merge import CircularExtendsError, deep_merge_dicts, merge_manifests, resolve_extends_chain
from manifest_schema import LanguageManifest, ProjectDetection, QualityGates

if TYPE_CHECKING:
    from pathlib import Path


class TestDeepMergeDicts:
    def test_disjoint_keys(self) -> None:
        assert deep_merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_scalar_replace(self) -> None:
        assert deep_merge_dicts({"a": 1, "b": 2}, {"b": 3}) == {"a": 1, "b": 3}

    def test_nested_merge(self) -> None:
        assert deep_merge_dicts({"a": {"x": 1, "y": 2}}, {"a": {"y": 3, "z": 4}}) == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_list_append(self) -> None:
        assert deep_merge_dicts({"a": [1, 2]}, {"a": [3, 4]}) == {"a": [1, 2, 3, 4]}

    def test_empty_child(self) -> None:
        assert deep_merge_dicts({"a": 1}, {}) == {"a": 1}

    def test_empty_base(self) -> None:
        assert deep_merge_dicts({}, {"a": 1}) == {"a": 1}


class TestMergeManifests:
    def test_child_scalar_replaces_parent(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            stack="base",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            stack="typer-cli",
            project_detection=ProjectDetection(markers=["pyproject.toml"], required_dependencies=["typer"]),
        )
        merged = merge_manifests(parent, child)
        assert merged.name == "python3-cli"
        assert merged.stack == "typer-cli"

    def test_stage_skills_append(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation"]},
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation-cli"], "design": ["python3-design-cli"]},
        )
        merged = merge_manifests(parent, child)
        assert merged.stage_skills["implementation"] == ["python3-implementation", "python3-implementation-cli"]
        assert merged.stage_skills["design"] == ["python3-design-cli"]

    def test_stage_skills_deduped_after_append(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation"]},
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation", "python3-implementation-cli"]},
        )
        merged = merge_manifests(parent, child)
        assert merged.stage_skills["implementation"] == ["python3-implementation", "python3-implementation-cli"]

    def test_quality_gates_merge(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            quality_gates=QualityGates(lint="uv run ruff check {files}", test="uv run pytest tests/"),
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            quality_gates=QualityGates(
                test="uv run pytest tests/ --tb=short", standards="/python3-development:modernpython"
            ),
        )
        merged = merge_manifests(parent, child)
        assert merged.quality_gates is not None
        assert merged.quality_gates.lint == "uv run ruff check {files}"
        assert merged.quality_gates.test == "uv run pytest tests/ --tb=short"
        assert merged.quality_gates.standards == "/python3-development:modernpython"

    def test_child_required_deps_append(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"], required_dependencies=["ruff"]),
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"], required_dependencies=["typer"]),
        )
        merged = merge_manifests(parent, child)
        assert merged.project_detection.required_dependencies == ["ruff", "typer"]

    def test_duplicate_required_deps_deduped(self) -> None:
        parent = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"], required_dependencies=["ruff", "typer"]),
        )
        child = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"], required_dependencies=["ruff", "rich"]),
        )
        merged = merge_manifests(parent, child)
        assert merged.project_detection.required_dependencies == ["ruff", "typer", "rich"]


class TestResolveExtendsChain:
    def test_no_extends(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            name: python3
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        manifest_file = tmp_path / "manifests" / "python3" / "language-manifest.yaml"
        manifest_file.parent.mkdir(parents=True)
        manifest_file.write_text(yaml_content)
        resolved = resolve_extends_chain(manifest_file, search_paths=[("test", tmp_path / "manifests")])
        assert resolved.name == "python3"

    def test_single_extends_by_name(self, tmp_path: Path) -> None:
        parent_dir = tmp_path / "plugin-a" / "manifests" / "base"
        parent_dir.mkdir(parents=True)
        (parent_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: base
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              discovery: [base-discovery]
        """)
        )
        child_dir = tmp_path / "plugin-b" / "manifests" / "child"
        child_dir.mkdir(parents=True)
        child_file = child_dir / "language-manifest.yaml"
        child_file.write_text(
            dedent("""\
            name: child
            extends: plugin-a:base
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              implementation: [child-impl]
        """)
        )
        search_paths = [
            ("plugin-a", tmp_path / "plugin-a" / "manifests"),
            ("plugin-b", tmp_path / "plugin-b" / "manifests"),
        ]
        resolved = resolve_extends_chain(child_file, search_paths=search_paths)
        assert resolved.name == "child"
        assert resolved.stage_skills["discovery"] == ["base-discovery"]
        assert resolved.stage_skills["implementation"] == ["child-impl"]

    def test_extends_by_relative_path(self, tmp_path: Path) -> None:
        parent_file = tmp_path / "base.yaml"
        parent_file.write_text(
            dedent("""\
            name: base
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              discovery: [base-discovery]
        """)
        )
        child_file = tmp_path / "child.yaml"
        child_file.write_text(
            dedent("""\
            name: child
            extends: ./base.yaml
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        )
        resolved = resolve_extends_chain(child_file, search_paths=[])
        assert resolved.name == "child"
        assert resolved.stage_skills["discovery"] == ["base-discovery"]

    def test_circular_extends_raises(self, tmp_path: Path) -> None:
        a_dir = tmp_path / "manifests" / "a"
        b_dir = tmp_path / "manifests" / "b"
        a_dir.mkdir(parents=True)
        b_dir.mkdir(parents=True)
        (a_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: a
            extends: test:b
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        )
        (b_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: b
            extends: test:a
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
        """)
        )
        with pytest.raises(CircularExtendsError):
            resolve_extends_chain(a_dir / "language-manifest.yaml", search_paths=[("test", tmp_path / "manifests")])

    def test_two_level_chain(self, tmp_path: Path) -> None:
        gp_dir = tmp_path / "manifests" / "gp"
        p_dir = tmp_path / "manifests" / "parent"
        c_dir = tmp_path / "manifests" / "child"
        for d in (gp_dir, p_dir, c_dir):
            d.mkdir(parents=True)
        (gp_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: gp
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            quality_gates:
              lint: "ruff check"
        """)
        )
        (p_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: parent
            extends: test:gp
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              implementation: [parent-impl]
        """)
        )
        (c_dir / "language-manifest.yaml").write_text(
            dedent("""\
            name: child
            extends: test:parent
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              implementation: [child-impl]
        """)
        )
        search = [("test", tmp_path / "manifests")]
        resolved = resolve_extends_chain(c_dir / "language-manifest.yaml", search_paths=search)
        assert resolved.name == "child"
        assert resolved.stage_skills["implementation"] == ["parent-impl", "child-impl"]
        assert resolved.quality_gates is not None
        assert resolved.quality_gates.lint == "ruff check"
