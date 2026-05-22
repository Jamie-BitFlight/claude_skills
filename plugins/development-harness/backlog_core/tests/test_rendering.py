"""Tests for the rendering abstraction introduced in backlog_core.rendering.

Verifies:
- All three BacklogBackend implementations return identical output for
  ``render_groomed_section`` — confirming the shared rendering module is used.
- ``operations.py`` no longer imports rendering symbols from ``github_sync``.
- The ``section_heading`` property is accessible on all backends and contains
  the expected keys.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from backlog_core import rendering as _rendering
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import GroomedData

if TYPE_CHECKING:
    from backlog_core.backend_protocol import BacklogBackend

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(params=["github", "sqlite", "memory", "beads"])
def backend_instance(request: pytest.FixtureRequest) -> BacklogBackend:
    """Parametrised fixture yielding each BacklogBackend implementation.

    Covers GitHubBackend, SQLiteBackend (in-memory), InMemoryBackend, and
    BeadsBackend so that rendering tests exercise all four without repeating
    test logic.  All rendering methods on every backend delegate to
    backlog_core.rendering and do not call external services, so no mocking
    is required.  BeadsBackend is lazily-validating — the constructor does not
    touch the filesystem or spawn processes, so it is safe to instantiate here
    even when the ``bd`` CLI is not installed.
    """
    name: str = request.param
    if name == "github":
        return cast("BacklogBackend", GitHubBackend())
    if name == "sqlite":
        return cast("BacklogBackend", SQLiteBackend(db_path=":memory:"))
    if name == "beads":
        return cast("BacklogBackend", BeadsBackend())
    return cast("BacklogBackend", InMemoryBackend())


# ---------------------------------------------------------------------------
# Test 1 — render_groomed_section is identical across all backends
# ---------------------------------------------------------------------------


class TestRenderGroomedSectionConsistency:
    """render_groomed_section on all three backends produces the same markdown."""

    def test_render_groomed_section_returns_same_output_for_all_backends(
        self, backend_instance: BacklogBackend
    ) -> None:
        """Each backend's render_groomed_section matches the canonical rendering module output.

        Regression guard: if any backend re-implemented section rendering locally rather
        than delegating to backlog_core.rendering, this test catches the drift.

        The GroomedData fixture includes subsections both in and out of canonical order
        plus an ``unknown__`` extra key to exercise all rendering code paths.
        """
        # Arrange — canonical-order keys, an out-of-order key, and an unknown__ extra
        groomed = GroomedData(
            date="2026-04-04",
            subsections={
                "Priority": "P1",
                "Impact": "High customer demand — affects 3 teams",
                "Benefits": "Removes duplicated rendering logic across backends",
                "Resources": "2 engineer-days",
                "unknown__custom_section": "Extra section content for unknown-key path",
            },
        )
        expected = _rendering.render_groomed_section(groomed)

        # Act
        result = backend_instance.render_groomed_section(groomed)

        # Assert
        assert result == expected, (
            f"Backend {type(backend_instance).__name__} returned different markdown.\n"
            f"Expected:\n{expected}\n\nGot:\n{result}"
        )


# ---------------------------------------------------------------------------
# Test 2 — operations.py has no github_sync rendering imports
# ---------------------------------------------------------------------------


class TestOperationsDoesNotImportFromGithubSync:
    """operations.py must not import rendering symbols from github_sync at module level."""

    def test_operations_does_not_import_from_github_sync(self) -> None:
        """Verify via AST that operations.py has no github_sync rendering imports.

        After the T3 refactor (commit e48e7973) rendering utilities were moved to
        backlog_core.rendering and the github_sync imports were removed from
        operations.py.  This test confirms the removal is permanent and was not
        silently re-introduced.

        Checks:
        - No ``import github_sync`` or ``from . import github_sync`` statement.
        - No ``from .github_sync import ...`` statement.
        - The legacy symbols ``_SECTION_HEADING_MAP`` and ``_render_groomed_md``
          are not imported at module level (they were the old github_sync rendering
          symbols).
        """
        # Arrange
        ops_path = Path(__file__).parent.parent / "operations.py"
        source = ops_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(ops_path))

        github_sync_imports: list[str] = []
        forbidden_names: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "github_sync" in module:
                    github_sync_imports.append(module)
                forbidden_names.extend(
                    alias.name for alias in node.names if alias.name in {"_SECTION_HEADING_MAP", "_render_groomed_md"}
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name or ""
                    if "github_sync" in name:
                        github_sync_imports.append(name)

        # Assert
        assert github_sync_imports == [], f"operations.py still imports from github_sync: {github_sync_imports}"
        assert forbidden_names == [], (
            f"operations.py still imports forbidden legacy rendering symbols: {forbidden_names}"
        )


# ---------------------------------------------------------------------------
# Test 3 — section_heading property is accessible and well-formed on all backends
# ---------------------------------------------------------------------------


class TestBackendProtocolSectionHeadingProperty:
    """section_heading property is accessible on all backends and contains required keys."""

    def test_backend_protocol_section_heading_property(self, backend_instance: BacklogBackend) -> None:
        """section_heading returns a dict[str, str] with the minimum required section keys.

        Verifies that all three backends correctly expose the section_heading property
        defined on the BacklogBackend Protocol, that the returned value is a plain dict
        mapping str to str, and that the keys used by the grooming workflow are present.
        """
        # Act
        heading_map = backend_instance.section_heading

        # Assert — type is dict[str, str]
        assert isinstance(heading_map, dict), (
            f"{type(backend_instance).__name__}.section_heading must be a dict, got {type(heading_map).__name__}"
        )
        for key, value in heading_map.items():
            assert isinstance(key, str), f"{type(backend_instance).__name__}.section_heading key {key!r} is not a str"
            assert isinstance(value, str), (
                f"{type(backend_instance).__name__}.section_heading value for {key!r} is not a str"
            )

        # Assert — required keys are present
        required_keys = {"fact_check", "rt_ica", "issue_classification"}
        missing = required_keys - heading_map.keys()
        assert not missing, f"{type(backend_instance).__name__}.section_heading is missing required keys: {missing}"


# ---------------------------------------------------------------------------
# Test 4 — unknown_key_to_heading strips prefix and title-cases
# ---------------------------------------------------------------------------


class TestUnknownKeyToHeading:
    """unknown_key_to_heading strips the ``unknown__`` prefix and title-cases the result."""

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("unknown__rt_ica", "Rt Ica"),
            ("unknown__custom_analysis", "Custom Analysis"),
            ("unknown__story", "Story"),
            ("unknown__my_custom_section", "My Custom Section"),
            ("unknown__single", "Single"),
        ],
        ids=["rt_ica", "custom_analysis", "story", "my_custom_section", "single_word"],
    )
    def test_unknown_key_to_heading_strips_prefix_and_title_cases(self, key: str, expected: str) -> None:
        """Strips the ``unknown__`` prefix, replaces underscores with spaces, title-cases.

        Verifies that the canonical rendering module correctly reverses the
        ``unknown__`` prefixing applied during section storage, producing a
        human-readable heading for display.
        """
        result = _rendering.unknown_key_to_heading(key)
        assert result == expected, f"unknown_key_to_heading({key!r}) returned {result!r}, expected {expected!r}"


# ---------------------------------------------------------------------------
# Test 5 — section_display_title is identical across all backends
# ---------------------------------------------------------------------------


class TestSectionDisplayTitleConsistency:
    """section_display_title on all four backends produces identical output.

    Regression guard: verifies that every BacklogBackend delegates
    ``section_display_title`` to ``backlog_core.rendering.section_display_title``
    rather than re-implementing the logic locally.  A backend that diverges
    (e.g. returns a different heading for the same key) would produce
    inconsistent UI rendering that CI would otherwise miss.

    Covers three representative input classes:
    - A known key present in ``SECTION_HEADING`` (canonical lookup path).
    - The special ``"groomed"`` key with a non-empty date (date-suffix path).
    - An ``unknown__`` prefixed key not in ``SECTION_HEADING`` (fallback path).
    """

    @pytest.mark.parametrize(
        ("key", "groomed_date"),
        [("fact_check", ""), ("groomed", "2026-04-04"), ("unknown__custom_section", "")],
        ids=["known_key", "groomed_key_with_date", "unknown_key"],
    )
    def test_section_display_title_returns_same_output_for_all_backends(
        self, backend_instance: BacklogBackend, key: str, groomed_date: str
    ) -> None:
        """Each backend's section_display_title matches the canonical rendering module output.

        Asserts that ``backend.section_display_title(key, groomed_date)`` equals
        ``_rendering.section_display_title(key, groomed_date)`` for every backend
        and every representative input combination.
        """
        expected = _rendering.section_display_title(key, groomed_date)
        result = backend_instance.section_display_title(key, groomed_date)
        assert result == expected, (
            f"{type(backend_instance).__name__}.section_display_title({key!r}, {groomed_date!r}) "
            f"returned {result!r}; expected {expected!r}"
        )
