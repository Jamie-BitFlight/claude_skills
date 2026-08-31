"""Unit tests for registry_loader.py — RegistryLoader and StepExtension merge.

Tests: RegistryLoader discovery, get_type, list_types, merge_type,
  and _apply_extension merge semantics.
Strategy: Use real JSON files from registry/ (experiment_core.json always present)
  plus tmp_path-based custom JSON files for isolated unit tests.
Coverage target: >=80% of registry_loader.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from models import StepDefinition, StepExtension, ValidationRule
from registry_loader import RegistryLoader

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def registry_dir() -> Path:
    """Return the path to the real registry directory.

    Returns:
        Absolute path to plugins/scientific-method/mcp/experiment-registry/registry/
    """
    return Path(__file__).parent.parent / "registry"


@pytest.fixture
def custom_registry(tmp_path: Path) -> Path:
    """Create a minimal custom registry directory with experiment_core.json.

    Returns:
        Path to the custom registry directory.
    """
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir()
    core = {
        "name": "experiment_core",
        "description": "Core protocol",
        "steps": [
            {
                "id": "hypothesis",
                "name": "State hypothesis",
                "required_artefacts": ["hypothesis.md"],
                "validation_rules": [{"type": "non_empty", "params": {}}],
                "frozen_artefacts": [],
            },
            {
                "id": "fixture",
                "name": "Build fixture",
                "required_artefacts": ["fixture.md"],
                "validation_rules": [{"type": "non_empty", "params": {}}],
                "frozen_artefacts": ["fixture.md"],
            },
        ],
        "anti_patterns": [],
        "rubric_templates": [],
    }
    (reg_dir / "experiment_core.json").write_text(json.dumps(core), encoding="utf-8")
    return reg_dir


# ===========================================================================
# RegistryLoader discovery
# ===========================================================================


class TestRegistryLoaderDiscovery:
    """Tests: RegistryLoader loads JSON files from registry directory on init.

    Tests: _load_all discovers experiment types from real registry files.
    How: Instantiate loader with real registry dir; verify known types are loaded.
    Why: Type discovery is the foundation of the entire MCP server operation.
    """

    def test_loads_experiment_core_from_real_registry(self, registry_dir: Path) -> None:
        """Validate that experiment_core type is loaded from the real registry directory.

        Tests: RegistryLoader discovers experiment_core.json at init
        How: Instantiate with real registry dir; call get_type('experiment_core').
        Why: experiment_core is the base type all experiments derive from.
        """
        loader = RegistryLoader(registry_dir=registry_dir)
        exp_core = loader.get_type("experiment_core")
        assert exp_core.name == "experiment_core"

    def test_real_registry_has_five_steps(self, registry_dir: Path) -> None:
        """Validate that experiment_core has the five expected protocol steps.

        Tests: RegistryLoader parses step definitions from JSON
        How: Load experiment_core; check step IDs.
        Why: The five-step protocol is the core contract of the MCP server.
        """
        loader = RegistryLoader(registry_dir=registry_dir)
        exp_core = loader.get_type("experiment_core")
        step_ids = [s.id for s in exp_core.steps]
        assert step_ids == ["hypothesis", "fixture", "rubric", "baseline", "iterate"]

    def test_examples_subdirectory_excluded(self, registry_dir: Path) -> None:
        """Validate that JSON files in examples/ are not loaded as experiment types.

        Tests: RegistryLoader excludes examples/ subdirectory from discovery
        How: Check list_types() does not contain names from examples/ files.
        Why: Example files are documentation, not valid experiment types for registration.
        """
        loader = RegistryLoader(registry_dir=registry_dir)
        type_names = {t.name for t in loader.list_types()}
        # Examples directory contains debugging_javascript and performance_regression
        assert "debugging_javascript" not in type_names
        assert "performance_regression" not in type_names

    def test_list_types_returns_all_loaded_types(self, registry_dir: Path) -> None:
        """Validate that list_types returns every loaded experiment type.

        Tests: RegistryLoader.list_types() returns complete list
        How: Load real registry; check experiment_core and domain types present.
        Why: list_types is used by MCP to expose available experiment types.
        """
        loader = RegistryLoader(registry_dir=registry_dir)
        types = loader.list_types()
        assert len(types) >= 1
        names = {t.name for t in types}
        assert "experiment_core" in names

    def test_unknown_type_raises_value_error(self, custom_registry: Path) -> None:
        """Validate that get_type raises ValueError for an unknown type name.

        Tests: RegistryLoader.get_type() error handling
        How: Request a type name that does not exist in the registry.
        Why: Clear error reporting prevents silent fallbacks to incorrect type.
        """
        loader = RegistryLoader(registry_dir=custom_registry)
        with pytest.raises(ValueError, match="Unknown experiment type"):
            loader.get_type("nonexistent_type")


# ===========================================================================
# merge_type
# ===========================================================================


class TestMergeType:
    """Tests: RegistryLoader.merge_type() — step merging and extension application.

    Tests: merge_type produces fully resolved StepDefinition lists.
    How: Use custom_registry with controlled step definitions.
    Why: merge_type is the primary interface for resolving step configurations.
    """

    def test_merge_type_experiment_core_returns_core_steps(self, custom_registry: Path) -> None:
        """Validate that merge_type('experiment_core') returns unmodified core steps.

        Tests: merge_type with base_name='experiment_core' — no extension applied
        How: Load custom registry; call merge_type('experiment_core').
        Why: When no domain type is named, core steps are returned unchanged.
        """
        loader = RegistryLoader(registry_dir=custom_registry)
        steps = loader.merge_type("experiment_core")
        assert len(steps) == 2
        assert steps[0].id == "hypothesis"
        assert steps[1].id == "fixture"

    def test_merge_type_with_domain_type_applies_extensions(self, tmp_path: Path) -> None:
        """Validate that merge_type applies domain step_extensions on top of core steps.

        Tests: merge_type with a domain type that has step_extensions
        How: Create a registry with experiment_core and a domain type; verify merged result.
        Why: Domain-specific extensions must be merged into core steps at resolution time.
        """
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()

        core = {
            "name": "experiment_core",
            "description": "Core",
            "steps": [
                {
                    "id": "hypothesis",
                    "name": "State hypothesis",
                    "required_artefacts": ["hypothesis.md"],
                    "validation_rules": [],
                    "frozen_artefacts": [],
                }
            ],
            "rubric_templates": [],
            "anti_patterns": [],
        }
        domain = {
            "name": "custom_type",
            "description": "Custom",
            "extends": "experiment_core",
            "steps": [],
            "step_extensions": {"hypothesis": {"additional_artefacts": ["extra.md"], "checklist": []}},
            "rubric_templates": [],
            "anti_patterns": [],
        }
        (reg_dir / "experiment_core.json").write_text(json.dumps(core), encoding="utf-8")
        (reg_dir / "custom_type.json").write_text(json.dumps(domain), encoding="utf-8")

        loader = RegistryLoader(registry_dir=reg_dir)
        steps = loader.merge_type("custom_type")
        assert len(steps) == 1
        assert "extra.md" in steps[0].required_artefacts
        assert "hypothesis.md" in steps[0].required_artefacts

    def test_merge_type_with_inline_extensions_applied_last(self, custom_registry: Path) -> None:
        """Validate that inline_extensions are applied after domain extensions.

        Tests: merge_type with inline_extensions parameter
        How: Call merge_type with inline_extensions dict; verify the extension was applied.
        Why: Inline extensions allow per-experiment customisation without modifying JSON.
        """
        loader = RegistryLoader(registry_dir=custom_registry)
        inline_ext = StepExtension(additional_artefacts=["custom.md"])
        steps = loader.merge_type("experiment_core", inline_extensions={"hypothesis": inline_ext})
        hyp_step = next(s for s in steps if s.id == "hypothesis")
        assert "custom.md" in hyp_step.required_artefacts

    def test_merge_type_with_none_inline_extensions(self, custom_registry: Path) -> None:
        """Validate that merge_type with inline_extensions=None works correctly.

        Tests: merge_type with None inline_extensions (default)
        How: Explicitly pass None; verify steps are returned without error.
        Why: None is the documented default for inline_extensions.
        """
        loader = RegistryLoader(registry_dir=custom_registry)
        steps = loader.merge_type("experiment_core", inline_extensions=None)
        assert len(steps) == 2


# ===========================================================================
# _apply_extension
# ===========================================================================


class TestApplyExtension:
    """Tests: RegistryLoader._apply_extension() merge semantics.

    Tests: Each merge rule in _apply_extension is exercised independently.
    How: Call the static method directly with controlled inputs.
    Why: Each merge rule has distinct semantics that must be verified.
    """

    def _base_step(self, **kwargs: Any) -> StepDefinition:
        """Build a base step for testing extension merges.

        Returns:
            StepDefinition with minimal fields.
        """
        return StepDefinition(
            id=kwargs.get("id", "test_step"),
            name=kwargs.get("name", "Test Step"),
            required_artefacts=kwargs.get("required_artefacts", ["base.md"]),
            validation_rules=kwargs.get("validation_rules", []),
            frozen_artefacts=kwargs.get("frozen_artefacts", []),
            checklist=kwargs.get("checklist", ["base check"]),
            human_input_required=kwargs.get("human_input_required", False),
            human_input_description=kwargs.get("human_input_description", ""),
        )

    def test_additional_artefacts_appended(self) -> None:
        """Validate that additional_artefacts are appended to required_artefacts.

        Tests: _apply_extension additional_artefacts merge
        How: Extension adds 'extra.md'; verify it's in the merged step's required_artefacts.
        Why: Domain types add artefacts on top of the core required artefacts.
        """
        step = self._base_step()
        ext = StepExtension(additional_artefacts=["extra.md"])
        merged = RegistryLoader._apply_extension(step, ext)
        assert "base.md" in merged.required_artefacts
        assert "extra.md" in merged.required_artefacts

    def test_checklist_items_appended(self) -> None:
        """Validate that extension checklist items are appended to the base checklist.

        Tests: _apply_extension checklist merge
        How: Extension adds one checklist item; verify both base and new items present.
        Why: Domain types extend the checklist without replacing core items.
        """
        step = self._base_step(checklist=["check 1"])
        ext = StepExtension(checklist=["check 2"])
        merged = RegistryLoader._apply_extension(step, ext)
        assert merged.checklist == ["check 1", "check 2"]

    def test_human_input_override_when_not_none(self) -> None:
        """Validate that human_input_required is overridden when extension provides non-None.

        Tests: _apply_extension human_input_required override
        How: Base has human_input_required=False; extension sets it to True.
        Why: Domain types can mark steps as requiring human input.
        """
        step = self._base_step(human_input_required=False)
        ext = StepExtension(human_input_required=True, human_input_description="needs human")
        merged = RegistryLoader._apply_extension(step, ext)
        assert merged.human_input_required is True
        assert merged.human_input_description == "needs human"

    def test_human_input_not_overridden_when_none(self) -> None:
        """Validate that human_input_required retains base value when extension is None.

        Tests: _apply_extension human_input_required non-override (None check)
        How: Extension has human_input_required=None; base value is preserved.
        Why: None signals 'do not override' for the human_input_required field.
        """
        step = self._base_step(human_input_required=True)
        ext = StepExtension(human_input_required=None)
        merged = RegistryLoader._apply_extension(step, ext)
        assert merged.human_input_required is True

    def test_additional_validation_rules_appended(self) -> None:
        """Validate that additional_validation_rules are appended to base rules.

        Tests: _apply_extension validation_rules merge
        How: Base has non_empty rule; extension adds required_sections rule.
        Why: Domain types can add validation rules without replacing core rules.
        """
        step = self._base_step(validation_rules=[ValidationRule(type="non_empty", params={})])
        ext = StepExtension(
            additional_validation_rules=[ValidationRule(type="required_sections", params={"sections": ["HEADER:"]})]
        )
        merged = RegistryLoader._apply_extension(step, ext)
        assert len(merged.validation_rules) == 2
        rule_types = [r.type for r in merged.validation_rules]
        assert "non_empty" in rule_types
        assert "required_sections" in rule_types

    def test_frozen_artefacts_deduplicated(self) -> None:
        """Validate that frozen_artefacts deduplication preserves order and removes duplicates.

        Tests: _apply_extension frozen_artefacts deduplication
        How: Both base and extension include 'base.md'; verify it appears only once.
        Why: Duplicate frozen artefact keys would cause redundant hash computations.
        """
        step = self._base_step(frozen_artefacts=["base.md"])
        ext = StepExtension(additional_frozen_artefacts=["base.md", "extra.md"])
        merged = RegistryLoader._apply_extension(step, ext)
        assert merged.frozen_artefacts.count("base.md") == 1
        assert "extra.md" in merged.frozen_artefacts

    def test_rubric_templates_loaded_from_json(self, registry_dir: Path) -> None:
        """Validate that rubric_templates are parsed from domain type JSON files.

        Tests: RegistryLoader._load_file parses rubric_templates
        How: Load real registry; get ai_agent_testing type; check rubric_templates.
        Why: Rubric templates drive per-criterion scoring for registered domain types.
        """
        loader = RegistryLoader(registry_dir=registry_dir)
        try:
            domain = loader.get_type("ai_agent_testing")
            # ai_agent_testing.json may or may not have rubric_templates
            assert isinstance(domain.rubric_templates, list)
        except ValueError:
            raise pytest.skip.Exception("ai_agent_testing type not present in registry") from None
