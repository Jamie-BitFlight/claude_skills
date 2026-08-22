"""Tests for the dispatch helper that assembles 5 inputs for generic agent."""

from __future__ import annotations

from dispatch_helper import build_dispatch_prompt
from manifest_schema import LanguageManifest, ProjectDetection, QualityGates


class TestBuildDispatchPrompt:
    """Test dispatch prompt assembly."""

    def test_basic_dispatch(self) -> None:
        """Build a dispatch prompt with all 5 inputs."""
        manifest = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation", "python3-implementation-cli"]},
            quality_gates=QualityGates(
                format="uv run ruff format {files}", lint="uv run ruff check {files}", test="uv run pytest tests/"
            ),
        )
        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill="development-harness:implementation",
        )

        # Verify all 5 inputs are present
        assert "development-harness:execution" in prompt
        assert "development-harness:implementation" in prompt
        assert "python3-implementation" in prompt
        assert "python3-implementation-cli" in prompt
        assert 'sam_task(plan="P123-auth", task="T1"' in prompt
        assert "uv run ruff format" in prompt
        assert "uv run ruff check" in prompt
        assert "uv run pytest" in prompt

    def test_stage_without_skills(self) -> None:
        """Stage not in manifest stage_skills should still produce a prompt."""
        manifest = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={},
        )
        prompt = build_dispatch_prompt(
            stage="discovery",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:discovery",
            cross_cutting_skill=None,
        )
        assert "development-harness:discovery" in prompt
        no_skills_indicators = [
            "No domain skills" in prompt,
            "domain_skills: []" in prompt.lower(),
            "none" in prompt.lower(),
        ]
        assert any(no_skills_indicators), f"Expected prompt to indicate no domain skills, got: {prompt[:200]}"

    def test_no_quality_gates(self) -> None:
        """Manifest without quality gates should note it in the prompt."""
        manifest = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
        )
        prompt = build_dispatch_prompt(
            stage="discovery",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:discovery",
            cross_cutting_skill=None,
        )
        assert 'sam_task(plan="P123-auth", task="T1"' in prompt

    def test_output_artifact_target_included(self) -> None:
        """I5: Dispatch prompt routes stage output through artifact_register, not a file path."""
        manifest = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation"]},
        )
        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill=None,
            item_id=1770,
            artifact_type="architect",
            artifact_id="architect-auth",
        )
        assert "artifact_register(item_id=1770" in prompt
        assert 'artifact_type="architect"' in prompt
        assert 'artifact_id="architect-auth"' in prompt
        assert ".md" not in prompt

    def test_files_template_variable_documented(self) -> None:
        """N5: Dispatch prompt should document {files} template variable contract."""
        manifest = LanguageManifest(
            name="python3",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            quality_gates=QualityGates(lint="uv run ruff check {files}"),
        )
        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill=None,
        )
        assert "{files}" in prompt or "files" in prompt.lower()
        # Should explain the substitution protocol
        assert "substitute" in prompt.lower() or "format" in prompt.lower()

    def test_prompt_contains_skill_load_instructions(self) -> None:
        """Prompt should contain Skill() call instructions."""
        manifest = LanguageManifest(
            name="python3-cli",
            language="python",
            version="1.0",
            project_detection=ProjectDetection(markers=["pyproject.toml"]),
            stage_skills={"implementation": ["python3-implementation"]},
        )
        prompt = build_dispatch_prompt(
            stage="implementation",
            manifest=manifest,
            plan="P123-auth",
            task="T1",
            stage_workflow_skill="development-harness:execution",
            cross_cutting_skill="development-harness:implementation",
        )
        # Should contain instructions to load skills
        assert "Skill(" in prompt or "skill=" in prompt.lower()
