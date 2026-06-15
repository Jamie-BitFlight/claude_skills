"""Unit tests for the _require_int_item_id guard function.

Covers the post-fix contract: any string input raises TypeError immediately;
integer inputs pass through unchanged.  The isdigit() coercion branch was
removed in #2438 — numeric strings are no longer silently coerced.
"""

from __future__ import annotations

import pytest
from backlog_core.artifact_provider import _require_int_item_id


class TestRequireIntItemIdIntInputs:
    def test_positive_int_passes_through(self) -> None:
        assert _require_int_item_id("GitHubGistArtifactProvider", 2438) == 2438

    def test_one_passes_through(self) -> None:
        assert _require_int_item_id("GitHubGistArtifactProvider", 1) == 1

    def test_large_int_passes_through(self) -> None:
        assert _require_int_item_id("GitHubGistArtifactProvider", 999999) == 999999

    def test_zero_passes_through(self) -> None:
        # Zero is technically valid at this layer; callers validate business rules
        assert _require_int_item_id("GitHubGistArtifactProvider", 0) == 0

    def test_negative_int_passes_through(self) -> None:
        # Sign validation is not this function's responsibility
        assert _require_int_item_id("GitHubGistArtifactProvider", -1) == -1


class TestRequireIntItemIdStringInputs:
    def test_beads_nanoid_raises(self) -> None:
        with pytest.raises(TypeError, match="bd-a3f8"):
            _require_int_item_id("GitHubGistArtifactProvider", "bd-a3f8")

    def test_numeric_string_raises(self) -> None:
        """Numeric strings are no longer coerced — isdigit() branch was removed."""
        with pytest.raises(TypeError, match="2438"):
            _require_int_item_id("GitHubGistArtifactProvider", "2438")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(TypeError, match="''"):
            _require_int_item_id("GitHubGistArtifactProvider", "")

    def test_zero_string_raises(self) -> None:
        with pytest.raises(TypeError, match="'0'"):
            _require_int_item_id("GitHubGistArtifactProvider", "0")

    def test_error_message_includes_cls_name(self) -> None:
        with pytest.raises(TypeError, match="GitLabArtifactProvider"):
            _require_int_item_id("GitLabArtifactProvider", "bd-a3f8")

    def test_error_message_mentions_beads_provider(self) -> None:
        with pytest.raises(TypeError, match="BeadsArtifactProvider"):
            _require_int_item_id("GitHubGistArtifactProvider", "bd-a3f8")
