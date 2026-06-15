"""Regression tests for item_id type contract in artifact_provider.

Background: ``artifact_read`` and ``artifact_list`` raised
``GitHubGistArtifactProvider requires an integer item ID, got '2459'``
when a numeric string was passed instead of an integer.

Fix approach (implemented): The MCP tool schema uses ``item_id: int | str``
(integer-first union) so Pydantic coerces numeric inputs to ``int`` at the
MCP boundary before they reach ``_require_int_item_id``.  The previous
``isdigit()`` coercion branch in ``_require_int_item_id`` was removed — any
string that arrives at the guard is a provider-routing error.

Post-fix contract:
- A plain integer ``2459`` passes through unchanged.
- A numeric string ``'2459'`` raises ``TypeError`` — Pydantic delivers int at
  the MCP boundary, so a string here means the caller bypassed the boundary.
- A beads nanoid string ``'bd-a3f8'`` raises ``TypeError`` — must route via
  ``BeadsArtifactProvider``, not GitHub/GitLab providers.
"""

from __future__ import annotations

import pytest

from backlog_core.artifact_provider import _require_int_item_id


class TestRequireIntItemIdCoercion:
    """_require_int_item_id rejects all strings; ints pass through unchanged."""

    def test_numeric_string_raises_type_error(self) -> None:
        """A numeric string like '2459' must raise TypeError, not coerce.

        The MCP boundary (int | str annotation) coerces numeric inputs to int
        before reaching this guard.  A string here means the caller bypassed
        the MCP boundary — that is a routing error and must raise immediately.
        """
        # Arrange
        item_id_string = "2459"

        # Act / Assert
        with pytest.raises(TypeError, match="requires an integer item ID"):
            _require_int_item_id("GitHubGistArtifactProvider", item_id_string)

    def test_beads_string_still_raises_type_error(self) -> None:
        """A beads nanoid string like 'bd-a3f8' must still raise TypeError.

        The discriminator between GitHub and beads providers depends on this
        rejection — a beads ID cannot be coerced to int and must not silently
        succeed for GitHub providers.
        """
        # Arrange / Act / Assert
        with pytest.raises(TypeError, match="requires an integer item ID"):
            _require_int_item_id("GitHubGistArtifactProvider", "bd-a3f8")

    def test_plain_integer_passes_through_unchanged(self) -> None:
        """A plain int like 2459 must be returned as-is without modification.

        This is the existing happy-path contract; the coercion fix must not
        alter it.
        """
        # Arrange
        item_id_int = 2459

        # Act
        result = _require_int_item_id("GitHubGistArtifactProvider", item_id_int)

        # Assert
        assert result == 2459
        assert isinstance(result, int)

    def test_gitlab_provider_name_in_error_message(self) -> None:
        """The cls_name parameter appears in the TypeError message for GitLab too.

        Verifies that the error message is correctly attributed regardless of
        which provider is calling the helper.
        """
        with pytest.raises(TypeError, match="GitLabArtifactProvider requires an integer item ID"):
            _require_int_item_id("GitLabArtifactProvider", "bd-a3f8")

    def test_zero_string_raises_type_error(self) -> None:
        """item_id='0' must raise TypeError — all strings are rejected.

        With the isdigit() coercion removed, '0' raises the same way as any
        other string.  Business-level zero validation (GitHub IDs start at 1)
        is the caller's responsibility; the guard only enforces the type contract.
        """
        # Arrange / Act / Assert
        with pytest.raises(TypeError, match="requires an integer item ID"):
            _require_int_item_id("GitHubGistArtifactProvider", "0")
