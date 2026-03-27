"""Tests for P{NNN} addressing scheme -- plan number resolution and backward compatibility.

Tests: Numeric plan resolution, slug resolution, collision detection, backward
compatibility fallback, and property-based plan number validation.
How: Create filesystem fixtures with P{NNN}-{slug} and tasks-{N}-{slug} files,
invoke resolve_plan_address, and verify resolution results.
Why: Addressing is the lookup layer -- incorrect resolution silently accesses
the wrong plan file, causing agents to read/write the wrong tasks.

Note: This test module focuses on the NEW P{NNN} addressing scheme added in T03.
The existing test_addressing.py covers the base addressing functionality.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st
from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Return a temporary plan/ directory.

    Returns:
        Path to an empty ``plan/`` directory inside ``tmp_path``.
    """
    d = tmp_path / "plan"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Property-based tests for plan number resolution
# ---------------------------------------------------------------------------


class TestPlanNumberResolutionPropertyBased:
    """Property-based tests for P{NNN} plan number resolution.

    Tests: Plan number resolution for all valid numeric inputs.
    How: Use hypothesis to generate plan numbers, create matching files,
    verify resolution finds the correct file.
    Why: Plan numbers span a wide range -- exhaustive testing is impractical
    but property-based testing covers the space probabilistically.
    """

    @given(plan_num=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=50, deadline=None)
    def test_resolve_any_valid_plan_number(self, plan_num: int) -> None:
        """Any valid plan number 1-9999 resolves to the correct P{NNN} file.

        Tests: Numeric resolution across the valid plan number range.
        How: Generate random plan number, create file, resolve, check match.
        Why: Zero-padding and integer comparison must work for all values.
        """
        # Arrange -- use tempfile instead of tmp_path (hypothesis compatibility)
        d = Path(tempfile.mkdtemp())
        try:
            filename = f"P{plan_num:03d}-test-feature.yaml"
            (d / filename).touch()

            # Act
            result = resolve_plan_address(str(plan_num), d)

            # Assert
            assert result.name == filename
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @given(plan_num=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=50, deadline=None)
    def test_resolve_zero_padded_input_matches_file(self, plan_num: int) -> None:
        """Zero-padded input '001' matches file P001-*.yaml.

        Tests: Zero-padded string input resolution.
        How: Generate plan number, pad to 3 digits, resolve.
        Why: CLI users may type 'P001' or just '001'.
        """
        # Arrange
        d = Path(tempfile.mkdtemp())
        try:
            filename = f"P{plan_num:03d}-padded.yaml"
            (d / filename).touch()

            # Act
            padded_input = f"{plan_num:03d}"
            result = resolve_plan_address(padded_input, d)

            # Assert
            assert result.name == filename
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @given(plan_num=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=30, deadline=None)
    def test_nonexistent_plan_number_raises_addressing_error(self, plan_num: int) -> None:
        """A plan number with no matching file raises AddressingError.

        Tests: Negative resolution.
        How: Create dir with wrong-numbered file, attempt resolution.
        Why: Missing plan must raise, not return wrong file.
        """
        # Arrange
        d = Path(tempfile.mkdtemp())
        try:
            other_num = plan_num + 1 if plan_num < 9999 else plan_num - 1
            (d / f"P{other_num:03d}-other.yaml").touch()

            # Act / Assert
            with pytest.raises(AddressingError):
                resolve_plan_address(str(plan_num), d)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# P{NNN} numeric resolution edge cases
# ---------------------------------------------------------------------------


class TestPlanNumberEdgeCases:
    """Test edge cases in P{NNN} numeric plan resolution.

    Tests: Variable padding, large numbers, boundary values.
    How: Create files with various padding schemes, resolve by number.
    Why: Zero-padding flexibility is specified in the addressing module.
    """

    def test_resolve_p1_matches_p001(self, plan_dir: Path) -> None:
        """P1 resolves to P001-*.yaml (3-digit padding).

        Tests: Minimal input matching maximum padding.
        How: Create P001-test.yaml, resolve "1".
        Why: Most common use case -- short input, padded file.
        """
        # Arrange
        (plan_dir / "P001-test.yaml").touch()
        # Act
        result = resolve_plan_address("1", plan_dir)
        # Assert
        assert result.name == "P001-test.yaml"

    def test_resolve_p1_matches_p1_no_padding(self, plan_dir: Path) -> None:
        """P1 resolves to P1-*.yaml (no padding).

        Tests: Unpadded file matching.
        How: Create P1-test.yaml, resolve "1".
        Why: Some files may not use zero-padding.
        """
        # Arrange
        (plan_dir / "P1-test.yaml").touch()
        # Act
        result = resolve_plan_address("1", plan_dir)
        # Assert
        assert result.name == "P1-test.yaml"

    def test_resolve_large_plan_number_4_digits(self, plan_dir: Path) -> None:
        """Plan number 9999 resolves correctly.

        Tests: Large plan number boundary.
        How: Create P9999-test.yaml, resolve "9999".
        Why: Upper boundary of the plan number space.
        """
        # Arrange
        (plan_dir / "P9999-test.yaml").touch()
        # Act
        result = resolve_plan_address("9999", plan_dir)
        # Assert
        assert result.name == "P9999-test.yaml"

    def test_resolve_p_prefix_in_input_is_stripped(self, plan_dir: Path) -> None:
        """Input 'P1' (with prefix) is handled -- prefix is stripped.

        Tests: Full-form input handling.
        How: Create P001-test.yaml, resolve "P1".
        Why: Users type 'P1' not just '1' -- both must work.
        """
        # Arrange
        (plan_dir / "P001-test.yaml").touch()
        # Act
        result = resolve_plan_address("P1", plan_dir)
        # Assert
        assert result.name == "P001-test.yaml"

    def test_resolve_directory_plan_by_number(self, plan_dir: Path) -> None:
        """Numeric resolution works for directory-format plans.

        Tests: Directory plan resolution.
        How: Create P003-dir-plan/ directory, resolve "3".
        Why: Plans above LINE_THRESHOLD are directories.
        """
        # Arrange
        (plan_dir / "P003-dir-plan").mkdir()
        # Act
        result = resolve_plan_address("3", plan_dir)
        # Assert
        assert result.name == "P003-dir-plan"
        assert result.is_dir()


# ---------------------------------------------------------------------------
# Slug resolution with P{NNN} files
# ---------------------------------------------------------------------------


class TestSlugResolutionPNNN:
    """Test slug-based resolution against P{NNN}-{slug} files.

    Tests: Slug substring matching in the new naming scheme.
    How: Create P{NNN}-{slug} files, resolve by slug substring.
    Why: Agents use slugs for human-readable plan references.
    """

    def test_slug_matches_p_prefixed_file(self, plan_dir: Path) -> None:
        """Slug 'auth-system' matches P001-auth-system.yaml.

        Tests: Exact slug match.
        How: Create file, resolve by slug.
        Why: Most common slug usage pattern.
        """
        # Arrange
        (plan_dir / "P001-auth-system.yaml").touch()
        # Act
        result = resolve_plan_address("auth-system", plan_dir)
        # Assert
        assert result.name == "P001-auth-system.yaml"

    def test_slug_substring_matches(self, plan_dir: Path) -> None:
        """Partial slug 'auth' matches P001-auth-system.yaml.

        Tests: Substring slug matching.
        How: Resolve partial slug, verify match.
        Why: Users may abbreviate slugs for convenience.
        """
        # Arrange
        (plan_dir / "P001-auth-system.yaml").touch()
        # Act
        result = resolve_plan_address("auth", plan_dir)
        # Assert
        assert result.name == "P001-auth-system.yaml"

    def test_slug_no_match_raises_addressing_error(self, plan_dir: Path) -> None:
        """Non-matching slug raises AddressingError.

        Tests: Slug resolution failure.
        How: Attempt to resolve slug that does not match any file.
        Why: Missing slug must raise, not return arbitrary file.
        """
        # Arrange
        (plan_dir / "P001-auth-system.yaml").touch()
        # Act / Assert
        with pytest.raises(AddressingError):
            resolve_plan_address("nonexistent-slug", plan_dir)

    def test_slug_matches_first_when_multiple(self, plan_dir: Path) -> None:
        """When slug matches multiple P-files, returns first sorted match.

        Tests: Multi-match slug behavior.
        How: Create two files both containing slug, check first returned.
        Why: Deterministic behavior for ambiguous slugs.
        """
        # Arrange
        (plan_dir / "P001-feature-alpha.yaml").touch()
        (plan_dir / "P002-feature-beta.yaml").touch()
        # Act
        result = resolve_plan_address("feature", plan_dir)
        # Assert -- returns first sorted match
        assert result.name == "P001-feature-alpha.yaml"


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------


class TestCollisionDetection:
    """Test collision detection when multiple P{NNN} files share numeric value.

    Tests: Numeric collision produces error with disambiguation hints.
    How: Create two files with same P-number, attempt resolution.
    Why: Collision must be surfaced to prevent wrong-file access.
    """

    def test_collision_raises_addressing_error(self, plan_dir: Path) -> None:
        """Two P004-*.yaml files cause AddressingError on numeric resolve.

        Tests: Collision detection.
        How: Create P004-alpha.yaml and P004-beta.yaml, resolve "4".
        Why: Ambiguous resolution must raise, not pick arbitrarily.
        """
        # Arrange
        (plan_dir / "P004-alpha.yaml").touch()
        (plan_dir / "P004-beta.yaml").touch()
        # Act / Assert
        with pytest.raises(AddressingError):
            resolve_plan_address("4", plan_dir)

    def test_collision_error_lists_matching_paths(self, plan_dir: Path) -> None:
        """Collision error message includes all matching file paths.

        Tests: Error message content.
        How: Check error message contains both filenames.
        Why: User needs to see which files collide to disambiguate.
        """
        # Arrange
        (plan_dir / "P004-alpha.yaml").touch()
        (plan_dir / "P004-beta.yaml").touch()
        # Act
        with pytest.raises(AddressingError) as exc_info:
            resolve_plan_address("4", plan_dir)
        # Assert
        msg = str(exc_info.value)
        assert "P004-alpha.yaml" in msg
        assert "P004-beta.yaml" in msg

    def test_collision_error_suggests_disambiguation(self, plan_dir: Path) -> None:
        """Collision error suggests using full slug to disambiguate.

        Tests: Error message helpfulness.
        How: Check error contains 'Disambiguate' text.
        Why: Actionable error messages reduce user confusion.
        """
        # Arrange
        (plan_dir / "P004-alpha.yaml").touch()
        (plan_dir / "P004-beta.yaml").touch()
        # Act
        with pytest.raises(AddressingError) as exc_info:
            resolve_plan_address("4", plan_dir)
        # Assert
        assert "disambiguate" in str(exc_info.value).lower()

    def test_collision_between_file_and_directory(self, plan_dir: Path) -> None:
        """Collision between P004.yaml file and P004-feature/ directory raises error.

        Tests: Cross-type collision.
        How: Create both a file and directory with P004 prefix.
        Why: File-vs-directory collision is the same ambiguity.
        """
        # Arrange
        (plan_dir / "P004-file.yaml").touch()
        (plan_dir / "P004-dir").mkdir()
        # Act / Assert
        with pytest.raises(AddressingError):
            resolve_plan_address("4", plan_dir)


# ---------------------------------------------------------------------------
# Backward compatibility fallback
# ---------------------------------------------------------------------------


class TestBackwardCompatFallback:
    """Test backward-compatible fallback to tasks-{N}-{slug} naming.

    Tests: Legacy file resolution when no P{NNN} match exists.
    How: Create only tasks-{N}-{slug} files, resolve by number.
    Why: 64 existing plan files use legacy naming -- must work until migrated.
    """

    def test_legacy_numeric_fallback(self, plan_dir: Path) -> None:
        """Number '5' falls back to tasks-5-old-feature.md when no P005 exists.

        Tests: Numeric fallback to legacy naming.
        How: Create only legacy file, resolve "5".
        Why: Unmigrated files must remain accessible.
        """
        # Arrange
        (plan_dir / "tasks-5-old-feature.md").touch()
        # Act
        result = resolve_plan_address("5", plan_dir)
        # Assert
        assert result.name == "tasks-5-old-feature.md"

    def test_legacy_slug_fallback(self, plan_dir: Path) -> None:
        """Slug 'old-feature' falls back to tasks-5-old-feature.md.

        Tests: Slug fallback to legacy naming.
        How: Create only legacy file, resolve by slug.
        Why: Slug resolution must work on legacy files too.
        """
        # Arrange
        (plan_dir / "tasks-5-old-feature.md").touch()
        # Act
        result = resolve_plan_address("old-feature", plan_dir)
        # Assert
        assert result.name == "tasks-5-old-feature.md"

    def test_p_file_takes_precedence_over_legacy(self, plan_dir: Path) -> None:
        """P{NNN} file is preferred over tasks-{N}-{slug} when both exist.

        Tests: Resolution priority.
        How: Create both naming styles, resolve by number.
        Why: P{NNN} is canonical -- legacy is fallback only.
        """
        # Arrange
        (plan_dir / "P005-feature.yaml").touch()
        (plan_dir / "tasks-5-feature.md").touch()
        # Act
        result = resolve_plan_address("5", plan_dir)
        # Assert
        assert result.name == "P005-feature.yaml"

    def test_legacy_directory_fallback(self, plan_dir: Path) -> None:
        """Legacy directory-format plan resolves via numeric fallback.

        Tests: Legacy directory resolution.
        How: Create tasks-3-plan/ directory, resolve "3".
        Why: Directory-format legacy plans must also resolve.
        """
        # Arrange
        (plan_dir / "tasks-3-big-plan").mkdir()
        # Act
        result = resolve_plan_address("3", plan_dir)
        # Assert
        assert result.name == "tasks-3-big-plan"
        assert result.is_dir()

    def test_no_match_at_all_raises_addressing_error(self, plan_dir: Path) -> None:
        """Neither P{NNN} nor legacy match raises AddressingError.

        Tests: Total resolution failure.
        How: Resolve number with no matching files.
        Why: Clear error when plan does not exist at all.
        """
        # Arrange -- empty plan_dir
        # Act / Assert
        with pytest.raises(AddressingError):
            resolve_plan_address("999", plan_dir)


# ---------------------------------------------------------------------------
# parse_address -- P{NNN}/T{M} format
# ---------------------------------------------------------------------------


class TestParseAddressPNNN:
    """Test parse_address with P{NNN}/T{M} format strings.

    Tests: Address parsing for the P-prefix scheme.
    How: Pass various address strings, verify tuple output.
    Why: parse_address is the entry point for all CLI commands.
    """

    @pytest.mark.parametrize(
        ("address", "expected_plan", "expected_task"),
        [
            ("P1/T3", "1", "3"),
            ("P719/T3", "719", "3"),
            ("P001/T01", "001", "01"),
            ("P1", "1", None),
            ("p5/T2", "5", "2"),
            ("P3/t7", "3", "7"),
        ],
        ids=["P1/T3", "P719/T3", "P001/T01-padded", "P1-plan-only", "p5-lowercase", "t7-lowercase"],
    )
    def test_parse_address_variants(self, address: str, expected_plan: str, expected_task: str | None) -> None:
        """Various address formats parse correctly.

        Tests: Address parsing for multiple format variants.
        How: Parametrize over valid addresses, check components.
        Why: CLI accepts multiple input forms -- all must parse correctly.
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address(address)
        # Assert
        assert plan_ref == expected_plan
        assert task_ref == expected_task

    @pytest.mark.parametrize(
        "address", ["", "P1/", "../danger/T1", "/etc/passwd"], ids=["empty", "trailing-slash", "traversal", "absolute"]
    )
    def test_parse_address_rejects_invalid(self, address: str) -> None:
        """Invalid address formats raise ValueError.

        Tests: Input validation.
        How: Pass invalid addresses, expect ValueError.
        Why: Security and correctness -- invalid input must be rejected.
        """
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match=r"Address "):
            parse_address(address)

    def test_parse_address_slug_with_task(self) -> None:
        """Slug address 'my-slug/T3' parses correctly.

        Tests: Slug-based address parsing.
        How: Parse slug address, check components.
        Why: Agents may use slugs instead of plan numbers.
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address("my-slug/T3")
        # Assert
        assert plan_ref == "my-slug"
        assert task_ref == "3"

    def test_parse_address_slug_only(self) -> None:
        """Slug-only address 'my-slug' returns None task_ref.

        Tests: Plan-only slug address.
        How: Parse slug without task component.
        Why: Plan-only reads use slug addresses.
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address("my-slug")
        # Assert
        assert plan_ref == "my-slug"
        assert task_ref is None
