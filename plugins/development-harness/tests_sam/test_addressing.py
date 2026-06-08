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


def test_resolve_plan_address_sha256_sidecar_not_a_collision(plan_dir: Path) -> None:
    # Regression test: a .sha256 hash sidecar written by GistTaskLayer._write_through
    # next to the .yaml plan file must NOT be treated as a second matching plan,
    # which would cause AddressingError for all-decimal UUID hex plan IDs (e.g. P17643163).
    # Arrange — plan file and its hash sidecar coexist
    (plan_dir / "P17643163-finalize-plan.yaml").touch()
    (plan_dir / "P17643163-finalize-plan.sha256").write_text("abc123hash")

    # Act — must resolve without raising AddressingError
    path = resolve_plan_address("P17643163", plan_dir)

    # Assert — resolves to the .yaml file, not the sidecar
    assert path.name == "P17643163-finalize-plan.yaml"
    assert path.suffix == ".yaml"


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


# ---------------------------------------------------------------------------
# Fix A: Collision warning when canonical P-file shadows a legacy tasks-* file
# ---------------------------------------------------------------------------


def test_resolve_plan_address_collision_warning_emits_to_stderr_when_legacy_shadow_exists(
    plan_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange — both P698-research-curator.yaml (canonical) and tasks-698-gates.md (legacy) exist
    (plan_dir / "P698-research-curator.yaml").touch()
    (plan_dir / "tasks-698-gates.md").touch()

    # Act — resolves to canonical; warning should be emitted
    result = resolve_plan_address("698", plan_dir)

    # Assert — canonical wins
    assert result.name == "P698-research-curator.yaml"
    # Assert — warning goes to stderr
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "tasks-698-gates.md" in captured.err
    assert "sam migrate" in captured.err


def test_resolve_plan_address_no_warning_when_no_legacy_shadow_exists(
    plan_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange — only canonical file, no legacy shadow
    (plan_dir / "P001-clean-feature.yaml").touch()

    # Act
    result = resolve_plan_address("1", plan_dir)

    # Assert — resolves correctly, no warning
    assert result.name == "P001-clean-feature.yaml"
    captured = capsys.readouterr()
    assert captured.err == ""


def test_resolve_plan_address_warning_names_all_legacy_shadows(
    plan_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange — two legacy files with the same number as the canonical file
    (plan_dir / "P010-main.yaml").touch()
    (plan_dir / "tasks-10-alpha.md").touch()
    (plan_dir / "tasks-10-beta.md").touch()

    # Act
    resolve_plan_address("10", plan_dir)

    # Assert — both legacy names appear in the warning
    captured = capsys.readouterr()
    assert "tasks-10-alpha.md" in captured.err
    assert "tasks-10-beta.md" in captured.err


# ---------------------------------------------------------------------------
# Fix B: parse_address rejects file-path-like addresses (contain extensions)
# ---------------------------------------------------------------------------


def test_parse_address_rejects_md_extension_raises_value_error() -> None:
    # Arrange — user passed a file path instead of an address
    with pytest.raises(ValueError, match="file path"):
        parse_address("plan/tasks-698-gates-subprocess-timeout.md")


def test_parse_address_rejects_yaml_extension_raises_value_error() -> None:
    with pytest.raises(ValueError, match="file path"):
        parse_address("P698-research-curator-code-analysis.yaml")


def test_parse_address_rejects_yml_extension_raises_value_error() -> None:
    with pytest.raises(ValueError, match="file path"):
        parse_address("plan/something.yml")


def test_parse_address_extension_error_message_suggests_correct_form() -> None:
    # Assert — error message tells the user what to use instead
    with pytest.raises(ValueError, match=r"P698|plan address"):
        parse_address("plan/tasks-698-gates.md")


def test_parse_address_valid_address_without_extension_still_works() -> None:
    # Regression: a slug that contains "md" as a substring (not as extension) must not be rejected
    plan_ref, task_ref = parse_address("P698")
    assert plan_ref == "698"
    assert task_ref is None


# ---------------------------------------------------------------------------
# QG prefix — parse_address
# ---------------------------------------------------------------------------


def test_parse_address_qg003_returns_qg003_and_none() -> None:
    # Arrange / Act — acceptance criterion: parse_address("QG003") returns correct prefix and number
    plan_ref, task_ref = parse_address("QG003")

    # Assert — multi-char prefix is preserved so resolve_plan_address can detect it
    assert plan_ref == "QG003"
    assert task_ref is None


def test_parse_address_qg003_t1_returns_qg003_and_1() -> None:
    # Arrange / Act — acceptance criterion: parse_address("QG003/T1") returns plan+task components
    plan_ref, task_ref = parse_address("QG003/T1")

    # Assert
    assert plan_ref == "QG003"
    assert task_ref == "1"


def test_parse_address_qg_lowercase_is_normalised() -> None:
    # Arrange / Act — lowercase "qg" prefix should be handled by _KNOWN_PREFIX_RE (IGNORECASE)
    plan_ref, task_ref = parse_address("qg003/T2")

    # Assert — plan_ref retains the original casing from input (not forced to upper)
    assert plan_ref == "qg003"
    assert task_ref == "2"


def test_parse_address_qg_with_t_lowercase_strips_t() -> None:
    # Arrange / Act
    plan_ref, task_ref = parse_address("QG001/t5")

    # Assert
    assert plan_ref == "QG001"
    assert task_ref == "5"


# ---------------------------------------------------------------------------
# QG prefix — resolve_plan_address (filesystem resolution)
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir_with_qg_files(plan_dir: Path) -> Path:
    """Populate plan/ with a QG{NNN}-{slug}.yaml file alongside P-prefix files.

    Layout::

        plan/
          P001-baseline.yaml
          QG003-qg-enforce-gates.yaml
    """
    (plan_dir / "P001-baseline.yaml").touch()
    (plan_dir / "QG003-qg-enforce-gates.yaml").touch()
    return plan_dir


def test_resolve_plan_address_qg003_matches_qg003_file(plan_dir_with_qg_files: Path) -> None:
    # Arrange — QG003-qg-enforce-gates.yaml exists
    # Act
    result = resolve_plan_address("QG003", plan_dir_with_qg_files)

    # Assert
    assert result.name == "QG003-qg-enforce-gates.yaml"


def test_resolve_plan_address_qg003_via_parse_address_round_trip(plan_dir_with_qg_files: Path) -> None:
    # Arrange — simulate the call chain: parse_address → resolve_plan_address
    plan_ref, _ = parse_address("QG003")

    # Act
    result = resolve_plan_address(plan_ref, plan_dir_with_qg_files)

    # Assert
    assert result.name == "QG003-qg-enforce-gates.yaml"


def test_resolve_plan_address_qg_directory_form(plan_dir: Path) -> None:
    # Arrange — QG plan stored as a directory (split format)
    (plan_dir / "QG001-qg-gates").mkdir()

    # Act
    result = resolve_plan_address("QG001", plan_dir)

    # Assert
    assert result.name == "QG001-qg-gates"
    assert result.is_dir()


def test_resolve_plan_address_qg_no_match_raises_addressing_error(plan_dir: Path) -> None:
    # Arrange — no QG099-* file exists
    (plan_dir / "P001-something.yaml").touch()

    # Act / Assert — QG plans have no legacy fallback, so AddressingError is raised immediately
    with pytest.raises(AddressingError):
        resolve_plan_address("QG099", plan_dir)


def test_resolve_plan_address_p001_unchanged_when_qg_file_also_present(plan_dir_with_qg_files: Path) -> None:
    # Arrange — both P001-baseline.yaml and QG003-qg-enforce-gates.yaml exist
    # Act — P001 should still resolve to the P-prefix file (no regression)
    result = resolve_plan_address("1", plan_dir_with_qg_files)

    # Assert
    assert result.name == "P001-baseline.yaml"


def test_resolve_plan_address_qg_collision_raises_addressing_error(plan_dir: Path) -> None:
    # Arrange — two QG files share numeric prefix QG003
    (plan_dir / "QG003-alpha.yaml").touch()
    (plan_dir / "QG003-beta.yaml").touch()

    # Act / Assert
    with pytest.raises(AddressingError) as exc_info:
        resolve_plan_address("QG003", plan_dir)

    # Assert — error message includes both matching paths
    error_msg = str(exc_info.value)
    assert "QG003-alpha.yaml" in error_msg
    assert "QG003-beta.yaml" in error_msg


def test_resolve_plan_address_qg_rejects_dotdot_traversal(plan_dir: Path) -> None:
    # Security: path traversal still rejected even with QG-like prefix
    with pytest.raises(ValueError, match="traversal"):
        resolve_plan_address("QG../etc/passwd", plan_dir)


def test_resolve_plan_address_qg_zero_padded_input_matches_file(plan_dir: Path) -> None:
    # Arrange — QG003-test.yaml; input "QG003" (already zero-padded)
    (plan_dir / "QG003-test.yaml").touch()

    # Act
    result = resolve_plan_address("QG003", plan_dir)

    # Assert
    assert result.name == "QG003-test.yaml"
