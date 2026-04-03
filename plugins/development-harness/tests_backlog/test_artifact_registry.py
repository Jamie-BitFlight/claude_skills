"""Tests for backlog_core.artifact_registry — stateless business logic layer.

Tests: ArtifactRegistry operations, parse/render helpers, and replace_manifest_in_body.
Strategy:
    - All tests are pure unit tests with no I/O. The registry is stateless so
      every test operates on freshly constructed ArtifactManifest objects.
    - The parse → render → parse roundtrip is a key correctness invariant tested
      exhaustively (all artifact types and statuses).
    - Edge cases cover empty bodies, existing sections, multiple same-type artifacts,
      and invalid/malformed table rows.
"""

from __future__ import annotations

import pytest
from backlog_core.artifact_registry import (
    ArtifactRegistry,
    parse_manifest_section,
    render_manifest_section,
    replace_manifest_in_body,
)
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> ArtifactRegistry:
    """Return a fresh ArtifactRegistry instance.

    Tests: ArtifactRegistry instantiation
    How: Construct instance with no arguments.
    Why: Each test gets an isolated registry; stateless by design but explicit
         fixture avoids implicit shared state across future changes.
    """
    return ArtifactRegistry()


@pytest.fixture
def empty_manifest() -> ArtifactManifest:
    """Return an ArtifactManifest with no artifacts.

    Tests: Baseline empty manifest state
    How: Construct with issue_number only.
    Why: Provides a clean slate for registry operation tests.
    """
    return ArtifactManifest(issue_number=965)


@pytest.fixture
def feature_context_entry() -> ArtifactEntry:
    """Return a feature-context ArtifactEntry with fixed metadata.

    Tests: A typical producer artifact entry
    How: Construct with explicit type, path, status, agent, and timestamp.
    Why: Reused across multiple tests to avoid repetition; fixed values
         make assertions deterministic.
    """
    return ArtifactEntry(
        artifact_type=ArtifactType.FEATURE_CONTEXT,
        path="plan/feature-context-foo.md",
        status=ArtifactStatus.CURRENT,
        agent="feature-researcher",
        created_at="2026-03-21T10:00:00Z",
    )


@pytest.fixture
def architect_entry() -> ArtifactEntry:
    """Return an architect ArtifactEntry with fixed metadata.

    Tests: A second distinct artifact type
    How: Construct with architect type, different path and agent.
    Why: Enables tests with multiple distinct artifact types in one manifest.
    """
    return ArtifactEntry(
        artifact_type=ArtifactType.ARCHITECT,
        path="plan/architect-foo.md",
        status=ArtifactStatus.CURRENT,
        agent="python-cli-design-spec",
        created_at="2026-03-21T11:00:00Z",
    )


@pytest.fixture
def manifest_with_feature_context(
    empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry, registry: ArtifactRegistry
) -> ArtifactManifest:
    """Return a manifest containing one feature-context entry.

    Tests: Pre-populated manifest for downstream tests
    How: Register feature_context_entry into empty_manifest.
    Why: Provides a populated starting state without duplicating fixture code.
    """
    return registry.register(empty_manifest, feature_context_entry)


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------


class TestArtifactEntryModelValidation:
    """Unit tests for ArtifactEntry Pydantic model and AliasChoices field interop.

    Tests: ArtifactEntry construction and field alias resolution.
    Strategy: Verify that both kebab-case and snake_case field names produce
              identical model instances (AliasChoices interop requirement).
    """

    def test_snake_case_construction_succeeds(self) -> None:
        """ArtifactEntry accepts snake_case field names at construction.

        Tests: ArtifactEntry(artifact_type=..., created_at=...)
        How: Construct with snake_case names and assert field values.
        Why: MCP tools and internal code use snake_case; model must accept it.
        """
        # Arrange / Act
        entry = ArtifactEntry(
            artifact_type=ArtifactType.ARCHITECT,
            path="plan/architect-test.md",
            status=ArtifactStatus.DRAFT,
            created_at="2026-01-01T00:00:00Z",
            agent="test-agent",
        )

        # Assert
        assert entry.artifact_type == ArtifactType.ARCHITECT
        assert entry.path == "plan/architect-test.md"
        assert entry.status == ArtifactStatus.DRAFT
        assert entry.created_at == "2026-01-01T00:00:00Z"
        assert entry.agent == "test-agent"

    def test_kebab_case_alias_validation(self) -> None:
        """ArtifactEntry accepts kebab-case field name via model_validate.

        Tests: AliasChoices("artifact_type", "artifact-type", "type")
        How: Pass dict with "artifact-type" key to model_validate.
        Why: Markdown table rows use kebab-case; parse_manifest_section produces
             kebab-case dicts that must be validated correctly.
        """
        # Arrange
        raw = {
            "artifact-type": "feature-context",
            "path": "plan/feature-context-bar.md",
            "status": "current",
            "created-at": "2026-03-01T00:00:00Z",
            "agent": "feature-researcher",
        }

        # Act
        entry = ArtifactEntry.model_validate(raw)

        # Assert
        assert entry.artifact_type == ArtifactType.FEATURE_CONTEXT
        assert entry.created_at == "2026-03-01T00:00:00Z"

    def test_short_type_alias_validation(self) -> None:
        """ArtifactEntry accepts short 'type' alias via model_validate.

        Tests: AliasChoices "type" short form
        How: Pass dict with "type" key to model_validate.
        Why: Backward compatibility with older tooling that used "type" in tables.
        """
        # Arrange
        raw = {"type": "architect", "path": "plan/architect-short.md"}

        # Act
        entry = ArtifactEntry.model_validate(raw)

        # Assert
        assert entry.artifact_type == ArtifactType.ARCHITECT

    def test_default_status_is_current(self) -> None:
        """ArtifactEntry defaults status to CURRENT when not provided.

        Tests: ArtifactEntry.status default value
        How: Construct without status argument.
        Why: Ensures newly registered artifacts are current by default.
        """
        # Arrange / Act
        entry = ArtifactEntry(artifact_type=ArtifactType.TASK_PLAN, path="plan/tasks-1-foo.yaml")

        # Assert
        assert entry.status == ArtifactStatus.CURRENT

    def test_all_artifact_types_are_valid(self) -> None:
        """All ArtifactType enum members can be used in ArtifactEntry.

        Tests: ArtifactType enum completeness
        How: Construct one entry per ArtifactType member.
        Why: Guards against ArtifactType members being accidentally invalid.
        """
        for art_type in ArtifactType:
            entry = ArtifactEntry(artifact_type=art_type, path=f"plan/{art_type}-test.md")
            assert entry.artifact_type == art_type

    def test_all_artifact_statuses_are_valid(self) -> None:
        """All ArtifactStatus enum members can be used in ArtifactEntry.

        Tests: ArtifactStatus enum completeness
        How: Construct one entry per ArtifactStatus member.
        Why: Guards against ArtifactStatus members being accidentally invalid.
        """
        for status in ArtifactStatus:
            entry = ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, path="plan/architect-test.md", status=status)
            assert entry.status == status


class TestArtifactManifestModelValidation:
    """Unit tests for ArtifactManifest Pydantic model.

    Tests: ArtifactManifest construction, defaults, and field population.
    Strategy: Verify required and optional fields behave as specified.
    """

    def test_issue_number_is_required(self) -> None:
        """ArtifactManifest requires issue_number at construction.

        Tests: ArtifactManifest.issue_number required field
        How: Attempt construction without issue_number and catch validation error.
        Why: Manifests without an issue number cannot be stored or retrieved.
        """
        import pydantic

        # Arrange / Act / Assert
        with pytest.raises(pydantic.ValidationError):
            ArtifactManifest.model_validate({})

    def test_artifacts_defaults_to_empty_list(self) -> None:
        """ArtifactManifest.artifacts defaults to an empty list.

        Tests: ArtifactManifest default factory for artifacts
        How: Construct with issue_number only; check artifacts.
        Why: Ensures new manifests start empty without requiring explicit []
        """
        # Arrange / Act
        manifest = ArtifactManifest(issue_number=42)

        # Assert
        assert manifest.artifacts == []
        assert manifest.last_updated == ""

    def test_last_updated_alias_interop(self) -> None:
        """ArtifactManifest accepts 'last-updated' and 'last_updated' aliases.

        Tests: AliasChoices for last_updated field
        How: Validate via dict with kebab-case key.
        Why: GitHub Issue body storage uses kebab-case keys.
        """
        # Arrange
        raw = {"issue_number": 99, "last-updated": "2026-03-21T12:00:00Z", "artifacts": []}

        # Act
        manifest = ArtifactManifest.model_validate(raw)

        # Assert
        assert manifest.last_updated == "2026-03-21T12:00:00Z"


# ---------------------------------------------------------------------------
# ArtifactRegistry.register tests
# ---------------------------------------------------------------------------


class TestArtifactRegistryRegister:
    """Unit tests for ArtifactRegistry.register — idempotent upsert logic.

    Tests: register() with new entries, exact-match updates, same-type/different-path.
    Strategy: All tests are pure; no I/O. Each verifies a specific upsert branch.
    """

    def test_register_new_entry_appends_to_manifest(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """Registering into an empty manifest produces a manifest with one entry.

        Tests: First registration into empty manifest
        How: Call register() with empty_manifest and one entry; check artifacts list.
        Why: Verifies the happy-path append branch of the upsert logic.
        """
        # Arrange — empty_manifest has no artifacts

        # Act
        result = registry.register(empty_manifest, feature_context_entry)

        # Assert
        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.FEATURE_CONTEXT
        assert result.artifacts[0].path == "plan/feature-context-foo.md"

    def test_register_same_type_and_path_updates_in_place(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """Registering the same type+path is idempotent — updates, does not duplicate.

        Tests: Exact-match upsert (type AND path both match)
        How: Register same type+path with a new agent; assert count unchanged and
             agent field updated.
        Why: Core idempotency requirement — re-registration must not create duplicates.
        """
        # Arrange
        updated_entry = ArtifactEntry(
            artifact_type=ArtifactType.FEATURE_CONTEXT,
            path="plan/feature-context-foo.md",
            status=ArtifactStatus.SUPERSEDED,
            agent="updated-agent",
            created_at="2026-03-22T00:00:00Z",
        )

        # Act
        result = registry.register(manifest_with_feature_context, updated_entry)

        # Assert — still exactly one entry
        assert len(result.artifacts) == 1
        assert result.artifacts[0].agent == "updated-agent"
        assert result.artifacts[0].status == ArtifactStatus.SUPERSEDED

    def test_register_same_type_different_path_adds_new_row(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """Registering same type but different path adds a new row.

        Tests: Same-type different-path upsert branch
        How: Register a second feature-context with a different path; assert
             the manifest now contains two entries both of type feature-context.
        Why: Multiple codebase-analysis or T0-baseline artifacts must coexist.
        """
        # Arrange
        second_entry = ArtifactEntry(
            artifact_type=ArtifactType.FEATURE_CONTEXT,
            path="plan/feature-context-bar.md",  # Different path
            status=ArtifactStatus.CURRENT,
            agent="feature-researcher",
            created_at="2026-03-22T00:00:00Z",
        )

        # Act
        result = registry.register(manifest_with_feature_context, second_entry)

        # Assert
        assert len(result.artifacts) == 2
        paths = {e.path for e in result.artifacts}
        assert paths == {"plan/feature-context-foo.md", "plan/feature-context-bar.md"}

    def test_register_two_codebase_analysis_artifacts_both_appear(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest
    ) -> None:
        """Two codebase-analysis artifacts with different paths both appear in manifest.

        Tests: Multiple same-type artifacts (architect spec section 7.3 scenario 3)
        How: Register two codebase-analysis entries; assert both are present.
        Why: The test plan explicitly names this scenario as critical.
        """
        # Arrange
        entry_a = ArtifactEntry(
            artifact_type=ArtifactType.CODEBASE_ANALYSIS,
            path="plan/codebase/auth-patterns.md",
            agent="codebase-analyzer",
        )
        entry_b = ArtifactEntry(
            artifact_type=ArtifactType.CODEBASE_ANALYSIS,
            path="plan/codebase/api-patterns.md",
            agent="codebase-analyzer",
        )

        # Act
        manifest_after_first = registry.register(empty_manifest, entry_a)
        manifest_after_second = registry.register(manifest_after_first, entry_b)

        # Assert
        assert len(manifest_after_second.artifacts) == 2
        ca_entries = registry.get_by_type(manifest_after_second, ArtifactType.CODEBASE_ANALYSIS)
        assert len(ca_entries) == 2

    def test_register_auto_stamps_created_at_when_empty(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest
    ) -> None:
        """register() auto-stamps created_at when the entry has an empty value.

        Tests: Auto-timestamp generation for created_at
        How: Register an entry with created_at=""; check result has non-empty timestamp.
        Why: Producer agents should not need to compute timestamps manually.
        """
        # Arrange
        entry = ArtifactEntry(
            artifact_type=ArtifactType.TASK_PLAN,
            path="plan/tasks-1-foo.yaml",
            created_at="",  # Explicitly empty — should be auto-stamped
        )

        # Act
        result = registry.register(empty_manifest, entry)

        # Assert
        assert result.artifacts[0].created_at != ""
        # Basic ISO format check: should contain "T" separator
        assert "T" in result.artifacts[0].created_at

    def test_register_does_not_mutate_original_manifest(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """register() returns a new manifest; the original is unchanged.

        Tests: Immutability / value-object semantics of registry operations
        How: Register into empty_manifest; assert empty_manifest.artifacts is still [].
        Why: Stateless design requires no mutation of input objects.
        """
        # Arrange — empty_manifest has no artifacts

        # Act
        registry.register(empty_manifest, feature_context_entry)

        # Assert original is unchanged
        assert empty_manifest.artifacts == []


# ---------------------------------------------------------------------------
# ArtifactRegistry.remove tests
# ---------------------------------------------------------------------------


class TestArtifactRegistryRemove:
    """Unit tests for ArtifactRegistry.remove.

    Tests: Entry removal by type+path, no-op when missing.
    """

    def test_remove_existing_entry(
        self,
        registry: ArtifactRegistry,
        manifest_with_feature_context: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
    ) -> None:
        """Removing an existing entry produces a manifest with one fewer artifact.

        Tests: ArtifactRegistry.remove on existing entry
        How: Remove the feature-context entry; assert empty artifacts list.
        Why: Verifies correct filtering logic in remove().
        """
        # Arrange — manifest has one entry

        # Act
        result = registry.remove(
            manifest_with_feature_context, ArtifactType.FEATURE_CONTEXT, "plan/feature-context-foo.md"
        )

        # Assert
        assert result.artifacts == []

    def test_remove_nonexistent_entry_returns_unchanged_manifest(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """Removing an entry that does not exist returns the manifest unchanged.

        Tests: ArtifactRegistry.remove on missing entry
        How: Attempt to remove a path that was never registered.
        Why: Ensures remove() is idempotent and safe to call speculatively.
        """
        # Arrange
        original_count = len(manifest_with_feature_context.artifacts)

        # Act
        result = registry.remove(manifest_with_feature_context, ArtifactType.FEATURE_CONTEXT, "plan/does-not-exist.md")

        # Assert — unchanged
        assert len(result.artifacts) == original_count

    def test_remove_only_removes_exact_type_path_match(
        self,
        registry: ArtifactRegistry,
        empty_manifest: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
        architect_entry: ArtifactEntry,
    ) -> None:
        """Remove leaves entries that do not match type+path combination.

        Tests: Precision of remove — does not over-delete
        How: Register two different-type entries; remove one; assert the other remains.
        Why: Prevents accidental deletion of other artifact types.
        """
        # Arrange
        populated = registry.register(empty_manifest, feature_context_entry)
        populated = registry.register(populated, architect_entry)

        # Act
        result = registry.remove(populated, ArtifactType.FEATURE_CONTEXT, "plan/feature-context-foo.md")

        # Assert — architect entry remains
        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.ARCHITECT


# ---------------------------------------------------------------------------
# ArtifactRegistry.get_by_type tests
# ---------------------------------------------------------------------------


class TestArtifactRegistryGetByType:
    """Unit tests for ArtifactRegistry.get_by_type.

    Tests: Filtering by artifact type, empty results, multiple results.
    """

    def test_get_by_type_returns_matching_entries(
        self,
        registry: ArtifactRegistry,
        empty_manifest: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
        architect_entry: ArtifactEntry,
    ) -> None:
        """get_by_type returns only entries matching the requested type.

        Tests: ArtifactRegistry.get_by_type with multiple types in manifest
        How: Register two different types; get_by_type for one; assert count 1.
        Why: Verifies the type filter is applied correctly.
        """
        # Arrange
        manifest = registry.register(empty_manifest, feature_context_entry)
        manifest = registry.register(manifest, architect_entry)

        # Act
        results = registry.get_by_type(manifest, ArtifactType.FEATURE_CONTEXT)

        # Assert
        assert len(results) == 1
        assert results[0].artifact_type == ArtifactType.FEATURE_CONTEXT

    def test_get_by_type_returns_empty_list_when_type_absent(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """get_by_type returns an empty list when no entry of that type exists.

        Tests: ArtifactRegistry.get_by_type on absent type
        How: Query for TASK_PLAN when only feature-context is registered.
        Why: Consumers must receive [] not None or an exception on cache miss.
        """
        # Arrange / Act
        results = registry.get_by_type(manifest_with_feature_context, ArtifactType.TASK_PLAN)

        # Assert
        assert results == []

    def test_get_by_type_returns_all_entries_of_same_type(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest
    ) -> None:
        """get_by_type returns all entries when multiple exist for the same type.

        Tests: Multiple same-type entry retrieval
        How: Register two codebase-analysis entries; get_by_type; assert count 2.
        Why: codebase-analysis commonly has multiple scoped entries.
        """
        # Arrange
        entry_a = ArtifactEntry(artifact_type=ArtifactType.CODEBASE_ANALYSIS, path="plan/codebase/scope-a.md")
        entry_b = ArtifactEntry(artifact_type=ArtifactType.CODEBASE_ANALYSIS, path="plan/codebase/scope-b.md")
        manifest = registry.register(empty_manifest, entry_a)
        manifest = registry.register(manifest, entry_b)

        # Act
        results = registry.get_by_type(manifest, ArtifactType.CODEBASE_ANALYSIS)

        # Assert
        assert len(results) == 2


# ---------------------------------------------------------------------------
# ArtifactRegistry.update_status tests
# ---------------------------------------------------------------------------


class TestArtifactRegistryUpdateStatus:
    """Unit tests for ArtifactRegistry.update_status.

    Tests: Status transition by type+path, no-op on missing entry.
    """

    def test_update_status_changes_matching_entry(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """update_status changes the status of the matching entry.

        Tests: Status transition from current to superseded (architect spec 7.3 scenario 9)
        How: Call update_status with SUPERSEDED; assert the entry's status changed.
        Why: Status lifecycle progression is a core manifest invariant.
        """
        # Arrange — entry is currently CURRENT

        # Act
        result = registry.update_status(
            manifest_with_feature_context,
            ArtifactType.FEATURE_CONTEXT,
            "plan/feature-context-foo.md",
            ArtifactStatus.SUPERSEDED,
        )

        # Assert
        assert result.artifacts[0].status == ArtifactStatus.SUPERSEDED

    def test_update_status_no_op_when_entry_not_found(
        self, registry: ArtifactRegistry, manifest_with_feature_context: ArtifactManifest
    ) -> None:
        """update_status is a no-op when the type+path combination is not found.

        Tests: update_status on absent entry
        How: Update a path that was never registered; assert manifest unchanged.
        Why: Callers should not need to pre-check existence.
        """
        # Arrange
        original_status = manifest_with_feature_context.artifacts[0].status

        # Act
        result = registry.update_status(
            manifest_with_feature_context,
            ArtifactType.FEATURE_CONTEXT,
            "plan/does-not-exist.md",  # Different path
            ArtifactStatus.ARCHIVED,
        )

        # Assert — original entry status unchanged
        assert result.artifacts[0].status == original_status

    def test_update_status_only_affects_matching_entry(
        self,
        registry: ArtifactRegistry,
        empty_manifest: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
        architect_entry: ArtifactEntry,
    ) -> None:
        """update_status only changes the targeted entry, leaving others intact.

        Tests: Surgical status update — no collateral changes
        How: Register two entries; update status on one; assert other is unchanged.
        Why: Prevents accidental status transitions on non-targeted entries.
        """
        # Arrange
        manifest = registry.register(empty_manifest, feature_context_entry)
        manifest = registry.register(manifest, architect_entry)

        # Act — update only the architect entry
        result = registry.update_status(
            manifest, ArtifactType.ARCHITECT, "plan/architect-foo.md", ArtifactStatus.ARCHIVED
        )

        # Assert — feature-context unchanged, architect archived
        fc_entry = next(e for e in result.artifacts if e.artifact_type == ArtifactType.FEATURE_CONTEXT)
        arch_entry = next(e for e in result.artifacts if e.artifact_type == ArtifactType.ARCHITECT)
        assert fc_entry.status == ArtifactStatus.CURRENT
        assert arch_entry.status == ArtifactStatus.ARCHIVED


# ---------------------------------------------------------------------------
# parse_manifest_section tests
# ---------------------------------------------------------------------------


class TestParseManifestSection:
    """Unit tests for parse_manifest_section.

    Tests: Parsing from valid issue bodies, empty bodies, malformed rows.
    Strategy: Focus on all code paths: present section, absent section,
              header/separator skip, invalid artifact type.
    """

    def test_parses_single_entry_from_issue_body(self) -> None:
        """parse_manifest_section extracts a valid entry from a real issue body.

        Tests: Happy-path parsing of a manifest section
        How: Build a body with a delimited section containing one valid row.
        Why: Core parsing function must extract entries faithfully.
        """
        # Arrange
        body = (
            "## Issue Description\n\nSome content here.\n\n"
            "## Artifact Manifest\n\n"
            "<!-- artifact-manifest:begin -->\n"
            "| Type | Path | Status | Agent | Created |\n"
            "|------|------|--------|-------|----------|\n"
            "| feature-context | plan/feature-context-foo.md | current | feature-researcher | 2026-03-21T10:00:00Z |\n"
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 965)

        # Assert
        assert manifest.issue_number == 965
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].artifact_type == ArtifactType.FEATURE_CONTEXT
        assert manifest.artifacts[0].path == "plan/feature-context-foo.md"
        assert manifest.artifacts[0].status == ArtifactStatus.CURRENT
        assert manifest.artifacts[0].agent == "feature-researcher"

    def test_returns_empty_manifest_when_section_absent(self) -> None:
        """parse_manifest_section returns empty manifest when no section found.

        Tests: Issue body with no artifact manifest section (architect spec 7.3 scenario 4)
        How: Pass a body without the delimiter markers.
        Why: Empty manifest is the valid initial state; must not raise.
        """
        # Arrange
        body = "## Some Issue\n\nDescription without a manifest."

        # Act
        manifest = parse_manifest_section(body, 42)

        # Assert
        assert manifest.issue_number == 42
        assert manifest.artifacts == []

    def test_returns_empty_manifest_for_empty_body(self) -> None:
        """parse_manifest_section handles completely empty issue body.

        Tests: Edge case — empty string input (architect spec 7.3 scenario 4)
        How: Pass empty string as body.
        Why: GitHub issues can have null/empty bodies.
        """
        # Arrange / Act
        manifest = parse_manifest_section("", 1)

        # Assert
        assert manifest.artifacts == []

    def test_skips_header_and_separator_rows(self) -> None:
        """parse_manifest_section skips the table header and separator rows.

        Tests: Header/separator row filtering
        How: Include a body with header and separator rows; assert only one entry.
        Why: Header and separator are structural — they are not artifact entries.
        """
        # Arrange
        body = (
            "<!-- artifact-manifest:begin -->\n"
            "| Type | Path | Status | Agent | Created |\n"
            "|------|------|--------|-------|----------|\n"
            "| architect | plan/architect-test.md | draft | agent | 2026-03-21T00:00:00Z |\n"
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 10)

        # Assert
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].artifact_type == ArtifactType.ARCHITECT

    def test_skips_rows_with_invalid_artifact_type(self) -> None:
        """parse_manifest_section silently skips rows with unknown artifact types.

        Tests: Graceful degradation for unknown type values
        How: Include one valid and one invalid type row; assert only valid is parsed.
        Why: Forward compatibility — future artifact types must not break existing parsers.
        """
        # Arrange
        body = (
            "<!-- artifact-manifest:begin -->\n"
            "| unknown-future-type | plan/something.md | current | agent | 2026-03-21T00:00:00Z |\n"
            "| architect | plan/architect-test.md | current | agent | 2026-03-21T00:00:00Z |\n"
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 5)

        # Assert
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].artifact_type == ArtifactType.ARCHITECT

    def test_parses_multiple_entries(self) -> None:
        """parse_manifest_section parses all valid rows in a multi-entry section.

        Tests: Multi-entry manifest parsing
        How: Body contains three valid rows; assert all three are extracted.
        Why: Real manifests commonly have 3-6 entries.
        """
        # Arrange
        body = (
            "<!-- artifact-manifest:begin -->\n"
            "| Type | Path | Status | Agent | Created |\n"
            "|------|------|--------|-------|----------|\n"
            "| feature-context | plan/feature-context-foo.md | current | feature-researcher | 2026-03-21T10:00:00Z |\n"
            "| architect | plan/architect-foo.md | current | architect-agent | 2026-03-21T11:00:00Z |\n"
            "| task-plan | plan/tasks-1-foo.yaml | current | planner | 2026-03-21T12:00:00Z |\n"
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 100)

        # Assert
        assert len(manifest.artifacts) == 3
        types = {e.artifact_type for e in manifest.artifacts}
        assert types == {ArtifactType.FEATURE_CONTEXT, ArtifactType.ARCHITECT, ArtifactType.TASK_PLAN}


# ---------------------------------------------------------------------------
# render_manifest_section tests
# ---------------------------------------------------------------------------


class TestRenderManifestSection:
    """Unit tests for render_manifest_section.

    Tests: Rendering produces correct delimiters, heading, and table rows.
    Strategy: Check structural invariants; roundtrip tests cover full fidelity.
    """

    def test_render_includes_begin_and_end_delimiters(self, manifest_with_feature_context: ArtifactManifest) -> None:
        """render_manifest_section includes both HTML comment delimiters.

        Tests: Rendered section structure
        How: Render and assert delimiter presence.
        Why: Delimiters are required for parse_manifest_section to find the section.
        """
        # Arrange / Act
        rendered = render_manifest_section(manifest_with_feature_context)

        # Assert
        assert "<!-- artifact-manifest:begin -->" in rendered
        assert "<!-- artifact-manifest:end -->" in rendered

    def test_render_includes_manifest_heading(self, manifest_with_feature_context: ArtifactManifest) -> None:
        """render_manifest_section includes the '## Artifact Manifest' heading.

        Tests: Section heading in rendered output
        How: Render and check for heading text.
        Why: replace_manifest_in_body uses the heading to locate the section for replacement.
        """
        # Arrange / Act
        rendered = render_manifest_section(manifest_with_feature_context)

        # Assert
        assert "## Artifact Manifest" in rendered

    def test_render_includes_entry_data(self, manifest_with_feature_context: ArtifactManifest) -> None:
        """render_manifest_section includes artifact entry data in the table.

        Tests: Table row content in rendered output
        How: Render and check for artifact type and path in output.
        Why: Data must survive the render step to be re-parseable.
        """
        # Arrange / Act
        rendered = render_manifest_section(manifest_with_feature_context)

        # Assert
        assert "feature-context" in rendered
        assert "plan/feature-context-foo.md" in rendered
        assert "feature-researcher" in rendered

    def test_render_empty_manifest_still_has_table_structure(self, empty_manifest: ArtifactManifest) -> None:
        """render_manifest_section produces valid table structure even for empty manifest.

        Tests: Empty manifest rendering
        How: Render empty manifest; assert header and separator are present.
        Why: Empty manifests must be parseable after a write-then-read cycle.
        """
        # Arrange / Act
        rendered = render_manifest_section(empty_manifest)

        # Assert
        assert "| Type | Path | Status | Agent | Created |" in rendered
        assert "|------|" in rendered


# ---------------------------------------------------------------------------
# Roundtrip fidelity tests
# ---------------------------------------------------------------------------


class TestParseRenderRoundtrip:
    """Tests for parse → render → parse roundtrip fidelity.

    Tests: Data integrity through full parse/render/parse cycle.
    Strategy: Critical invariant from architect spec section 7.3 scenario 1.
              Test with single entry, multiple entries, all artifact types.
    """

    def test_single_entry_roundtrip_preserves_all_fields(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """Parse → render → parse roundtrip preserves a single entry identically.

        Tests: Roundtrip fidelity for a single-entry manifest (architect spec 7.3 scenario 1)
        How: Register one entry, render the manifest, embed in body, parse back, compare fields.
        Why: The manifest must survive write-to-GitHub then read-from-GitHub with no data loss.
        """
        # Arrange
        manifest = registry.register(empty_manifest, feature_context_entry)

        # Act — render then parse back
        rendered = render_manifest_section(manifest)
        reparsed = parse_manifest_section(rendered, 965)

        # Assert — fields preserved
        assert len(reparsed.artifacts) == 1
        original = manifest.artifacts[0]
        recovered = reparsed.artifacts[0]
        assert recovered.artifact_type == original.artifact_type
        assert recovered.path == original.path
        assert recovered.status == original.status
        assert recovered.agent == original.agent
        assert recovered.created_at == original.created_at

    def test_multi_entry_roundtrip_preserves_all_entries(
        self,
        registry: ArtifactRegistry,
        empty_manifest: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
        architect_entry: ArtifactEntry,
    ) -> None:
        """Parse → render → parse roundtrip preserves multiple entries identically.

        Tests: Multi-entry roundtrip fidelity
        How: Register two entries, render, parse back, compare both entries.
        Why: Ensures the table serialisation/deserialisation is lossless.
        """
        # Arrange
        manifest = registry.register(empty_manifest, feature_context_entry)
        manifest = registry.register(manifest, architect_entry)

        # Act
        rendered = render_manifest_section(manifest)
        reparsed = parse_manifest_section(rendered, 965)

        # Assert
        assert len(reparsed.artifacts) == len(manifest.artifacts)
        for original, recovered in zip(manifest.artifacts, reparsed.artifacts, strict=False):
            assert recovered.artifact_type == original.artifact_type
            assert recovered.path == original.path
            assert recovered.status == original.status

    @pytest.mark.parametrize("artifact_type", list(ArtifactType), ids=[t.value for t in ArtifactType])
    def test_all_artifact_types_survive_roundtrip(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, artifact_type: ArtifactType
    ) -> None:
        """All ArtifactType enum values survive a full parse/render/parse roundtrip.

        Tests: ArtifactType enum value serialisation for every member
        How: For each ArtifactType, register, render, parse back, assert type preserved.
        Why: Guards against any enum value that cannot survive table serialisation.
        """
        # Arrange
        entry = ArtifactEntry(
            artifact_type=artifact_type,
            path=f"plan/{artifact_type}-test.md",
            status=ArtifactStatus.CURRENT,
            agent="test-agent",
            created_at="2026-03-21T00:00:00Z",
        )
        manifest = registry.register(empty_manifest, entry)

        # Act
        rendered = render_manifest_section(manifest)
        reparsed = parse_manifest_section(rendered, 1)

        # Assert
        assert len(reparsed.artifacts) == 1
        assert reparsed.artifacts[0].artifact_type == artifact_type

    @pytest.mark.parametrize("status", list(ArtifactStatus), ids=[s.value for s in ArtifactStatus])
    def test_all_artifact_statuses_survive_roundtrip(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, status: ArtifactStatus
    ) -> None:
        """All ArtifactStatus enum values survive a full parse/render/parse roundtrip.

        Tests: ArtifactStatus enum value serialisation for every member
        How: For each ArtifactStatus, register, render, parse back, assert status preserved.
        Why: Status transitions must not be lossy through the storage layer.
        """
        # Arrange
        entry = ArtifactEntry(
            artifact_type=ArtifactType.ARCHITECT,
            path="plan/architect-status-test.md",
            status=status,
            agent="agent",
            created_at="2026-03-21T00:00:00Z",
        )
        manifest = registry.register(empty_manifest, entry)

        # Act
        rendered = render_manifest_section(manifest)
        reparsed = parse_manifest_section(rendered, 1)

        # Assert
        assert reparsed.artifacts[0].status == status


# ---------------------------------------------------------------------------
# replace_manifest_in_body tests
# ---------------------------------------------------------------------------


class TestReplaceManifestInBody:
    """Unit tests for replace_manifest_in_body.

    Tests: Section replacement, append when absent, surrounding content preservation.
    Strategy: Covers all three code paths: exact heading+section match, delimiter-only
              match (fallback), and no section present (append).
    """

    def test_appends_section_when_body_has_no_manifest(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """replace_manifest_in_body appends section when body has no existing manifest.

        Tests: Append path — architect spec 7.3 scenario 5
        How: Call with a body that has no manifest section; assert section now present.
        Why: First registration on any issue must create the manifest section.
        """
        # Arrange
        original_body = "## Overview\n\nThis is the issue body."
        manifest = registry.register(empty_manifest, feature_context_entry)
        rendered = render_manifest_section(manifest)

        # Act
        result = replace_manifest_in_body(original_body, rendered)

        # Assert
        assert "<!-- artifact-manifest:begin -->" in result
        assert "<!-- artifact-manifest:end -->" in result
        assert "## Overview" in result  # Original content preserved

    def test_replaces_existing_section_in_place(
        self,
        registry: ArtifactRegistry,
        empty_manifest: ArtifactManifest,
        feature_context_entry: ArtifactEntry,
        architect_entry: ArtifactEntry,
    ) -> None:
        """replace_manifest_in_body replaces the existing manifest section in-place.

        Tests: Replacement path — existing section updated without duplication
        How: Build a body with a manifest section; replace with an updated manifest;
             assert the body contains only one manifest section.
        Why: Each update must produce exactly one manifest section.
        """
        # Arrange — create a body that already has a single-entry manifest
        first_manifest = registry.register(empty_manifest, feature_context_entry)
        first_rendered = render_manifest_section(first_manifest)
        existing_body = "## Overview\n\nContent.\n\n" + first_rendered + "\n"

        # Add a second entry and produce a new render
        second_manifest = registry.register(first_manifest, architect_entry)
        second_rendered = render_manifest_section(second_manifest)

        # Act
        result = replace_manifest_in_body(existing_body, second_rendered)

        # Assert — exactly one begin delimiter
        assert result.count("<!-- artifact-manifest:begin -->") == 1
        assert "architect" in result  # New entry present

    def test_preserves_content_before_manifest_section(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """replace_manifest_in_body preserves content before the manifest section.

        Tests: Surrounding content preservation (architect spec 7.3 scenario 5)
        How: Include content before and after the manifest; replace; assert both preserved.
        Why: Issue body contains acceptance criteria, descriptions — none should be lost.
        """
        # Arrange
        manifest = registry.register(empty_manifest, feature_context_entry)
        rendered = render_manifest_section(manifest)
        body_with_section = (
            "## Issue Description\n\nImportant pre-content.\n\n" + rendered + "\n\n## Footer\n\nPost-content."
        )

        # New manifest for the replace
        updated_rendered = render_manifest_section(manifest)

        # Act
        result = replace_manifest_in_body(body_with_section, updated_rendered)

        # Assert — surrounding content intact
        assert "Important pre-content." in result
        assert "Post-content." in result

    def test_append_to_empty_body(self) -> None:
        """replace_manifest_in_body handles completely empty issue body.

        Tests: Edge case — append to empty body (architect spec 7.3 scenario 4)
        How: Pass empty string as body; assert manifest section is created.
        Why: New GitHub issues have empty bodies.
        """
        # Arrange
        manifest = ArtifactManifest(issue_number=1)
        rendered = render_manifest_section(manifest)

        # Act
        result = replace_manifest_in_body("", rendered)

        # Assert
        assert "<!-- artifact-manifest:begin -->" in result
        assert "<!-- artifact-manifest:end -->" in result

    def test_replaces_delimiter_only_section_when_heading_absent(
        self, registry: ArtifactRegistry, empty_manifest: ArtifactManifest, feature_context_entry: ArtifactEntry
    ) -> None:
        """replace_manifest_in_body uses delimiter-only fallback when heading is absent.

        Tests: Fallback replacement branch — delimited block without heading
        How: Build a body with delimiters but no '## Artifact Manifest' heading;
             call replace_manifest_in_body with an updated render; assert one section.
        Why: Some older issue bodies may contain the delimited block without the heading
             immediately preceding it. The fallback regex handles this case.
        """
        # Arrange — body has delimiter block but heading is elsewhere / absent
        orphan_section = (
            "## Something Else\n\n"
            "<!-- artifact-manifest:begin -->\n"
            "| Type | Path | Status | Agent | Created |\n"
            "|------|------|--------|-------|----------|\n"
            "<!-- artifact-manifest:end -->\n"
        )
        manifest = registry.register(empty_manifest, feature_context_entry)
        new_rendered = render_manifest_section(manifest)

        # Act
        result = replace_manifest_in_body(orphan_section, new_rendered)

        # Assert — exactly one begin delimiter; entry data present
        assert result.count("<!-- artifact-manifest:begin -->") == 1
        assert "feature-context" in result


# ---------------------------------------------------------------------------
# Additional coverage for _parse_table_row edge cases
# ---------------------------------------------------------------------------


class TestParseTableRowEdgeCases:
    """Additional tests targeting _parse_table_row branches not covered by other suites.

    Tests: Short-column rows and invalid status values in table rows.
    Strategy: These exercise branches in the private _parse_table_row helper
              indirectly via parse_manifest_section.
    """

    def test_parse_skips_rows_with_fewer_than_five_columns(self) -> None:
        """parse_manifest_section skips table rows with fewer than five columns.

        Tests: Short-column guard in _parse_table_row
        How: Include a row with only three pipe-separated columns inside the
             manifest section; assert zero artifacts parsed.
        Why: Malformed rows (e.g. truncated edits) must not crash the parser.
        """
        # Arrange — row has only 3 columns
        body = (
            "<!-- artifact-manifest:begin -->\n"
            "| feature-context | plan/fc.md |\n"  # Only 2 cells — fewer than 5
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 7)

        # Assert
        assert manifest.artifacts == []

    def test_parse_uses_current_status_for_unknown_status_value(self) -> None:
        """parse_manifest_section defaults status to CURRENT for unknown status values.

        Tests: Invalid status fallback in _parse_table_row
        How: Include a row with an unrecognised status string; assert entry parsed
             with CURRENT status.
        Why: Forward compatibility — future status values default to CURRENT rather
             than dropping the row entirely.
        """
        # Arrange — valid type and path, unknown status
        body = (
            "<!-- artifact-manifest:begin -->\n"
            "| architect | plan/architect-test.md | future-status | agent | 2026-03-21T00:00:00Z |\n"
            "<!-- artifact-manifest:end -->\n"
        )

        # Act
        manifest = parse_manifest_section(body, 8)

        # Assert — row was parsed (not skipped), status defaulted to CURRENT
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].status == ArtifactStatus.CURRENT
