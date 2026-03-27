"""Proof-of-concept: end-to-end manifest resolution + dispatch prompt assembly.

Validates that a generic harness agent can be dispatched with the correct
5 inputs for a Python/Typer project at the implementation stage.

Note: _setup_mock_project and _setup_manifests duplicate logic from
test_manifest_resolver.py. Extract to shared fixtures in conftest.py
when adding more integration tests (see L7 in code review).
"""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from dispatch_helper import build_dispatch_prompt
from manifest_resolver import resolve_for_project

if TYPE_CHECKING:
    from pathlib import Path


class TestProofOfConcept:
    """End-to-end: resolve manifest -> build dispatch prompt."""

    def _setup_mock_project(self, tmp_path: Path) -> Path:
        """Create a minimal Typer project."""
        project = tmp_path / "my-cli"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            dedent("""\
            [project]
            name = "my-cli"
            version = "0.1.0"
            dependencies = ["typer>=0.9", "rich"]
        """)
        )
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("import typer\napp = typer.Typer()\n")
        return project

    def _setup_manifests(self, tmp_path: Path) -> Path:
        """Create base and CLI manifests."""
        plugin_dir = tmp_path / "plugins" / "python3-development"
        base = plugin_dir / "manifests" / "python3"
        base.mkdir(parents=True)
        (base / "language-manifest.yaml").write_text(
            dedent("""\
            name: python3
            language: python
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
            stage_skills:
              discovery: [python3-discovery]
              implementation: [python3-implementation]
            quality_gates:
              format: "uv run ruff format {files}"
              lint: "uv run ruff check {files}"
              typecheck: "uv run ty check {files}"
              test: "uv run pytest tests/ --tb=short"
              standards: "/python3-development:modernpython"
        """)
        )

        cli = plugin_dir / "manifests" / "python3-cli"
        cli.mkdir(parents=True)
        (cli / "language-manifest.yaml").write_text(
            dedent("""\
            name: python3-cli
            extends: python3-development:python3
            language: python
            stack: typer-cli
            version: "1.0"
            project_detection:
              markers: [pyproject.toml]
              required_dependencies: [typer]
            stage_skills:
              implementation: [python3-implementation-cli]
              design: [python3-design-cli]
        """)
        )
        return plugin_dir

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Resolve manifest for Typer project, then build dispatch prompt."""
        project = self._setup_mock_project(tmp_path)
        plugin_dir = self._setup_manifests(tmp_path)

        # Step 1: Resolve manifest
        manifest = resolve_for_project(project_root=project, plugin_dirs=[plugin_dir])
        assert manifest is not None
        assert manifest.name == "python3-cli"
        assert manifest.stack == "typer-cli"

        # Verify extends resolution worked
        assert "python3-implementation" in manifest.stage_skills["implementation"]
        assert "python3-implementation-cli" in manifest.stage_skills["implementation"]
        assert manifest.quality_gates is not None
        assert manifest.quality_gates.lint == "uv run ruff check {files}"

        # Step 2: Build dispatch prompt for implementation stage
        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            task_file="plan/tasks-1-my-cli/T1-add-cli-entrypoint.md",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill="development-harness:implementation",
        )

        # Verify all 5 inputs present in prompt
        # Input 1: Stage workflow skill
        assert "development-harness:execution" in prompt

        # Input 2: Cross-cutting skill
        assert "development-harness:implementation" in prompt

        # Input 3: Domain skills from resolved manifest
        assert "python3-implementation" in prompt
        assert "python3-implementation-cli" in prompt

        # Input 4: Task file
        assert "plan/tasks-1-my-cli/T1-add-cli-entrypoint.md" in prompt

        # Input 5: Quality gates
        assert "uv run ruff format" in prompt
        assert "uv run ruff check" in prompt
        assert "uv run ty check" in prompt
        assert "uv run pytest" in prompt

        # Verify metadata
        assert "python" in prompt.lower()
        assert "typer-cli" in prompt

    def test_base_manifest_dispatch(self, tmp_path: Path) -> None:
        """Vanilla Python project resolves to base manifest."""
        project = tmp_path / "vanilla"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            dedent("""\
            [project]
            name = "my-lib"
            dependencies = ["requests"]
        """)
        )
        plugin_dir = self._setup_manifests(tmp_path)

        manifest = resolve_for_project(project_root=project, plugin_dirs=[plugin_dir])
        assert manifest is not None
        assert manifest.name == "python3"

        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            task_file="plan/task.md",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill=None,
        )
        # Only base skill, no CLI skill
        assert "python3-implementation" in prompt
        assert "python3-implementation-cli" not in prompt
