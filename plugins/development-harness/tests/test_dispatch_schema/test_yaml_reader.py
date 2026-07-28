"""Tests for dispatch_schema.readers.yaml_reader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dispatch_schema.core.models import DispatchPlan, ItemStatus
from dispatch_schema.readers.yaml_reader import read_dispatch_plan

if TYPE_CHECKING:
    from pathlib import Path


class TestReadDispatchPlanValidInput:
    """read_dispatch_plan with well-formed YAML files."""

    def test_read_dispatch_plan_valid_file_returns_dispatch_plan(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert isinstance(plan, DispatchPlan)

    def test_read_dispatch_plan_valid_file_parses_milestone_number(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert plan.milestone.number == 3

    def test_read_dispatch_plan_valid_file_parses_milestone_title(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert plan.milestone.title == "Q1 Infrastructure Sprint"

    def test_read_dispatch_plan_valid_file_parses_kebab_case_integration_branch(self, fixtures_dir: Path) -> None:
        # Arrange — YAML uses kebab-case ``integration-branch``
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert plan.milestone.integration_branch == "milestone/3-infra"

    def test_read_dispatch_plan_valid_file_parses_waves(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert len(plan.waves) == 2

    def test_read_dispatch_plan_valid_file_parses_conflict_groups(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        assert len(plan.conflict_groups) == 1
        assert plan.conflict_groups[0].group_id == 1

    def test_read_dispatch_plan_valid_file_parses_wave_items(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert
        first_item = plan.waves[0].items[0]
        assert first_item.issue == 101
        assert first_item.title == "Add conflict analysis"

    def test_read_dispatch_plan_valid_file_defaults_status_to_pending(self, fixtures_dir: Path) -> None:
        # Arrange
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert — status field exists in YAML as "pending"; must match enum
        assert plan.waves[0].items[0].status == ItemStatus.PENDING

    def test_read_dispatch_plan_valid_file_parses_kebab_case_depends_on(self, fixtures_dir: Path) -> None:
        # Arrange — YAML uses kebab-case ``depends-on``
        path = fixtures_dir / "valid-plan.yaml"

        # Act
        plan = read_dispatch_plan(path)

        # Assert — wave 2, item 0 depends on issue 101
        assert plan.waves[1].items[0].depends_on == [101]

    def test_read_dispatch_plan_inline_yaml_minimal_plan_returns_dispatch_plan(self, tmp_path: Path) -> None:
        # Arrange
        yaml_file = tmp_path / "milestone-1-dispatch.yaml"
        yaml_file.write_text(
            "milestone:\n"
            "  number: 1\n"
            "  title: Test\n"
            "  integration-branch: milestone/1\n"
            "waves:\n"
            "  - wave: 1\n"
            "    items:\n"
            "      - title: Fix thing\n"
            "        issue: 7\n"
            "        priority: P2\n",
            encoding="utf-8",
        )

        # Act
        plan = read_dispatch_plan(yaml_file)

        # Assert
        assert plan.milestone.number == 1
        assert len(plan.waves) == 1


class TestReadDispatchPlanFileNotFound:
    """read_dispatch_plan raises FileNotFoundError for missing paths."""

    def test_read_dispatch_plan_nonexistent_file_raises_file_not_found_error(self, tmp_path: Path) -> None:
        # Arrange
        path = tmp_path / "does-not-exist.yaml"

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            read_dispatch_plan(path)

    def test_read_dispatch_plan_nonexistent_file_message_contains_path(self, tmp_path: Path) -> None:
        # Arrange
        path = tmp_path / "missing.yaml"

        # Act / Assert
        with pytest.raises(FileNotFoundError, match=str(path)):
            read_dispatch_plan(path)


class TestReadDispatchPlanInvalidYAML:
    """read_dispatch_plan raises ValueError for unparseable or invalid content."""

    def test_read_dispatch_plan_malformed_yaml_raises_value_error(self, tmp_path: Path) -> None:
        # Arrange
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(": invalid: yaml: {", encoding="utf-8")

        # Act / Assert
        with pytest.raises(ValueError):  # ruff: ignore[pytest-raises-too-broad]
            read_dispatch_plan(bad_yaml)

    def test_read_dispatch_plan_non_mapping_yaml_raises_value_error(self, tmp_path: Path) -> None:
        # Arrange — top-level is a list, not a mapping
        bad_yaml = tmp_path / "list.yaml"
        bad_yaml.write_text("- item1\n- item2\n", encoding="utf-8")

        # Act / Assert
        with pytest.raises(ValueError):  # ruff: ignore[pytest-raises-too-broad]
            read_dispatch_plan(bad_yaml)

    def test_read_dispatch_plan_missing_required_field_raises_value_error(self, tmp_path: Path) -> None:
        # Arrange — ``waves`` field is required but absent
        incomplete_yaml = tmp_path / "incomplete.yaml"
        incomplete_yaml.write_text(
            "milestone:\n  number: 1\n  title: Test\n  integration-branch: milestone/1\n", encoding="utf-8"
        )

        # Act / Assert
        with pytest.raises(ValueError):  # ruff: ignore[pytest-raises-too-broad]
            read_dispatch_plan(incomplete_yaml)

    def test_read_dispatch_plan_validation_error_message_contains_path(self, tmp_path: Path) -> None:
        # Arrange — invalid milestone number (must be >= 1)
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text(
            "milestone:\n"
            "  number: 0\n"
            "  title: Test\n"
            "  integration-branch: milestone/0\n"
            "waves:\n"
            "  - wave: 1\n"
            "    items:\n"
            "      - title: Fix\n"
            "        issue: 1\n"
            "        priority: P1\n",
            encoding="utf-8",
        )

        # Act / Assert
        with pytest.raises(ValueError, match=str(invalid_yaml)):
            read_dispatch_plan(invalid_yaml)
