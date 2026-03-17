"""Tests for sam_schema.core.addressing module.

Covers P{NNN}-{slug} primary resolution, slug-based resolution, collision
handling, backward-compatible tasks-{N}-{slug} fallback, path traversal
security, and parse_address parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sam_schema.core.addressing import AddressingError, _reject_path_traversal, parse_address, resolve_plan_address

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Return a temporary plan/ directory."""
    d = tmp_path / "plan"
    d.mkdir()
    return d


@pytest.fixture
def plan_dir_with_p_files(plan_dir: Path) -> Path:
    """Populate plan/ with P{NNN}-{slug}.yaml files and a legacy tasks-* file.

    Layout::

        plan/
          P001-backlog-reconciliation.yaml
          P002-other-feature.yaml
          P719-sam-schema-integration.yaml
          tasks-5-old-feature.md
          tasks-5-old-feature/        # directory form of legacy plan
    """
    (plan_dir / "P001-backlog-reconciliation.yaml").touch()
    (plan_dir / "P002-other-feature.yaml").touch()
    (plan_dir / "P719-sam-schema-integration.yaml").touch()
    (plan_dir / "tasks-5-old-feature.md").touch()
    (plan_dir / "tasks-5-old-feature").mkdir()
    return plan_dir


# ---------------------------------------------------------------------------
# resolve_plan_address — P{NNN} numeric resolution
# ---------------------------------------------------------------------------


def test_resolve_plan_address_p1_matches_p001_file(plan_dir_with_p_files: Path) -> None:
    # Arrange — P001-backlog-reconciliation.yaml exists
    # Act
    result = resolve_plan_address("1", plan_dir_with_p_files)

    # Assert
    assert result.name == "P001-backlog-reconciliation.yaml"


def test_resolve_plan_address_p719_matches_p719_file(plan_dir_with_p_files: Path) -> None:
    # Arrange — P719-sam-schema-integration.yaml exists
    # Act
    result = resolve_plan_address("719", plan_dir_with_p_files)

    # Assert
    assert result.name == "P719-sam-schema-integration.yaml"


def test_resolve_plan_address_p2_matches_p002_file(plan_dir_with_p_files: Path) -> None:
    # Arrange — P002-other-feature.yaml exists
    # Act
    result = resolve_plan_address("2", plan_dir_with_p_files)

    # Assert
    assert result.name == "P002-other-feature.yaml"


def test_resolve_plan_address_numeric_matches_directory_plan(plan_dir: Path) -> None:
    # Arrange — plan is a directory (split format)
    (plan_dir / "P003-big-feature").mkdir()

    # Act
    result = resolve_plan_address("3", plan_dir)

    # Assert
    assert result.name == "P003-big-feature"
    assert result.is_dir()


def test_resolve_plan_address_zero_padded_input_matches_file(plan_dir: Path) -> None:
    # Arrange — P001-test.yaml; input "001" (already zero-padded)
    (plan_dir / "P001-test.yaml").touch()

    # Act
    result = resolve_plan_address("001", plan_dir)

    # Assert
    assert result.name == "P001-test.yaml"


def test_resolve_plan_address_numeric_no_match_raises_addressing_error(plan_dir_with_p_files: Path) -> None:
    # Arrange — no P099-* file exists
    # Act / Assert
    with pytest.raises(AddressingError):
        resolve_plan_address("99", plan_dir_with_p_files)


# ---------------------------------------------------------------------------
# resolve_plan_address — collision handling
# ---------------------------------------------------------------------------


def test_resolve_plan_address_collision_raises_addressing_error_with_paths(plan_dir: Path) -> None:
    # Arrange — two files share numeric prefix P004
    (plan_dir / "P004-feature-alpha.yaml").touch()
    (plan_dir / "P004-feature-beta.yaml").touch()

    # Act
    with pytest.raises(AddressingError) as exc_info:
        resolve_plan_address("4", plan_dir)

    # Assert — error message includes both matching paths
    error_msg = str(exc_info.value)
    assert "P004-feature-alpha.yaml" in error_msg
    assert "P004-feature-beta.yaml" in error_msg


def test_resolve_plan_address_collision_error_message_suggests_disambiguation(plan_dir: Path) -> None:
    # Arrange
    (plan_dir / "P004-alpha.yaml").touch()
    (plan_dir / "P004-beta.yaml").touch()

    # Act
    with pytest.raises(AddressingError) as exc_info:
        resolve_plan_address("4", plan_dir)

    # Assert — error hints at slug-based disambiguation
    assert "Disambiguate" in str(exc_info.value) or "disambiguate" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# resolve_plan_address — slug resolution
# ---------------------------------------------------------------------------


def test_resolve_plan_address_slug_matches_p_prefixed_file(plan_dir_with_p_files: Path) -> None:
    # Arrange — P001-backlog-reconciliation.yaml exists; use slug substring
    # Act
    result = resolve_plan_address("backlog-reconciliation", plan_dir_with_p_files)

    # Assert
    assert result.name == "P001-backlog-reconciliation.yaml"


def test_resolve_plan_address_slug_matches_sam_schema_file(plan_dir_with_p_files: Path) -> None:
    # Arrange — P719-sam-schema-integration.yaml
    # Act
    result = resolve_plan_address("sam-schema-integration", plan_dir_with_p_files)

    # Assert
    assert result.name == "P719-sam-schema-integration.yaml"


def test_resolve_plan_address_slug_no_match_raises_addressing_error(plan_dir_with_p_files: Path) -> None:
    # Arrange — no file contains "nonexistent-slug"
    # Act / Assert
    with pytest.raises(AddressingError):
        resolve_plan_address("nonexistent-slug", plan_dir_with_p_files)


def test_resolve_plan_address_slug_does_not_match_legacy_p_prefix(plan_dir: Path) -> None:
    # Arrange — only legacy file exists, not a P{NNN} file
    (plan_dir / "tasks-3-my-feature.md").touch()

    # slug "my-feature" should fall back to legacy (tested separately)
    # This test verifies slug resolution does NOT match tasks-* via P-pattern loop
    # but DOES succeed via the fallback path
    result = resolve_plan_address("my-feature", plan_dir)
    assert result.name == "tasks-3-my-feature.md"


# ---------------------------------------------------------------------------
# resolve_plan_address — backward compatibility fallback
# ---------------------------------------------------------------------------


def test_resolve_plan_address_legacy_numeric_fallback_when_no_p_file(plan_dir: Path) -> None:
    # Arrange — only legacy tasks-5-old-feature.md, no P005-* file
    (plan_dir / "tasks-5-old-feature.md").touch()

    # Act
    result = resolve_plan_address("5", plan_dir)

    # Assert — resolves via legacy fallback
    assert result.name == "tasks-5-old-feature.md"


def test_resolve_plan_address_legacy_slug_fallback_when_no_p_file(plan_dir: Path) -> None:
    # Arrange — only legacy tasks-5-old-feature.md, no P-pattern match
    (plan_dir / "tasks-5-old-feature.md").touch()

    # Act
    result = resolve_plan_address("old-feature", plan_dir)

    # Assert
    assert result.name == "tasks-5-old-feature.md"


def test_resolve_plan_address_p_file_takes_precedence_over_legacy(plan_dir: Path) -> None:
    # Arrange — both P001-old-feature.yaml and tasks-1-old-feature.md exist
    (plan_dir / "P001-old-feature.yaml").touch()
    (plan_dir / "tasks-1-old-feature.md").touch()

    # Act
    result = resolve_plan_address("1", plan_dir)

    # Assert — P-pattern wins
    assert result.name == "P001-old-feature.yaml"


def test_resolve_plan_address_legacy_directory_fallback(plan_dir: Path) -> None:
    # Arrange — legacy directory-form plan
    legacy_dir = plan_dir / "tasks-3-legacy-plan"
    legacy_dir.mkdir()

    # Act
    result = resolve_plan_address("3", plan_dir)

    # Assert
    assert result.name == "tasks-3-legacy-plan"
    assert result.is_dir()


# ---------------------------------------------------------------------------
# resolve_plan_address — path traversal security
# ---------------------------------------------------------------------------


def test_resolve_plan_address_rejects_dotdot_traversal(plan_dir: Path) -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="traversal"):
        resolve_plan_address("../secrets", plan_dir)


def test_resolve_plan_address_rejects_absolute_path(plan_dir: Path) -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="absolute"):
        resolve_plan_address("/etc/passwd", plan_dir)


def test_resolve_plan_address_rejects_dotdot_in_slug(plan_dir: Path) -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="traversal"):
        resolve_plan_address("my-feature/../other", plan_dir)


# ---------------------------------------------------------------------------
# resolve_plan_address — plan_dir does not exist
# ---------------------------------------------------------------------------


def test_resolve_plan_address_raises_file_not_found_when_dir_missing(tmp_path: Path) -> None:
    # Arrange — non-existent directory
    missing_dir = tmp_path / "no-such-dir"

    # Act / Assert
    with pytest.raises(FileNotFoundError):
        resolve_plan_address("1", missing_dir)


# ---------------------------------------------------------------------------
# _reject_path_traversal
# ---------------------------------------------------------------------------


def test_reject_path_traversal_raises_for_dotdot() -> None:
    with pytest.raises(ValueError, match="traversal"):
        _reject_path_traversal("../danger")


def test_reject_path_traversal_raises_for_absolute_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        _reject_path_traversal("/absolute/path")


def test_reject_path_traversal_passes_for_normal_address() -> None:
    # Should not raise
    _reject_path_traversal("P1/T3")
    _reject_path_traversal("my-feature-slug")
    _reject_path_traversal("719")


# ---------------------------------------------------------------------------
# parse_address
# ---------------------------------------------------------------------------


def test_parse_address_p719_t3_returns_719_and_3() -> None:
    # Arrange / Act — T03 acceptance criterion 1
    plan_ref, task_ref = parse_address("P719/T3")

    # Assert
    assert plan_ref == "719"
    assert task_ref == "3"


def test_parse_address_p1_t3_returns_1_and_3() -> None:
    plan_ref, task_ref = parse_address("P1/T3")

    assert plan_ref == "1"
    assert task_ref == "3"


def test_parse_address_plan_only_returns_none_task() -> None:
    plan_ref, task_ref = parse_address("P1")

    assert plan_ref == "1"
    assert task_ref is None


def test_parse_address_slug_with_task_returns_slug_and_task() -> None:
    plan_ref, task_ref = parse_address("my-slug/T3")

    assert plan_ref == "my-slug"
    assert task_ref == "3"


def test_parse_address_slug_only_returns_slug_and_none() -> None:
    plan_ref, task_ref = parse_address("my-slug")

    assert plan_ref == "my-slug"
    assert task_ref is None


def test_parse_address_empty_string_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_address("")


def test_parse_address_empty_task_component_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_address("P1/")


def test_parse_address_rejects_dotdot_traversal() -> None:
    with pytest.raises(ValueError, match="traversal"):
        parse_address("../danger/T1")


def test_parse_address_rejects_absolute_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        parse_address("/etc/passwd")


def test_parse_address_p_lowercase_strips_prefix() -> None:
    # Lowercase 'p' prefix should also be stripped
    plan_ref, task_ref = parse_address("p5/T2")

    assert plan_ref == "5"
    assert task_ref == "2"


def test_parse_address_t_lowercase_strips_prefix() -> None:
    # Lowercase 't' prefix should also be stripped
    plan_ref, task_ref = parse_address("P3/t7")

    assert plan_ref == "3"
    assert task_ref == "7"


def test_parse_address_zero_padded_p_strips_to_digits() -> None:
    # P001 -> plan_ref is "001" (three chars after stripping P)
    plan_ref, task_ref = parse_address("P001/T01")

    assert plan_ref == "001"
    assert task_ref == "01"
