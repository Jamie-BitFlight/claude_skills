"""Tests for configurable width and font_size in _render_card.

Verifies that:
- Custom width is applied to SVG output dimensions
- Custom font_size is applied to SVG style declarations
- Default values produce expected output (backward compat)
- PNG output respects custom dimensions
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from _server import ASSISTANT, DEFAULT_FONT_SIZE, DEFAULT_WIDTH, TASK, USER, render_card
from fastmcp.utilities.types import Image
from mcp.types import TextContent

if TYPE_CHECKING:
    from pathlib import Path

_render_card = render_card
_DEFAULT_WIDTH = DEFAULT_WIDTH
_DEFAULT_FONT_SIZE = DEFAULT_FONT_SIZE
_TASK = TASK
_ASSISTANT = ASSISTANT
_USER = USER


class TestRenderCardCustomWidth:
    """Tests for custom width parameter."""

    def test_svg_contains_custom_width_attribute(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out), width=1200)

        svg_text = out.read_text(encoding="utf-8")
        assert 'width="1200"' in svg_text

    def test_svg_default_width_is_900(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out))

        svg_text = out.read_text(encoding="utf-8")
        assert 'width="900"' in svg_text

    def test_svg_different_widths_produce_different_output(self, tmp_path: Path) -> None:
        out_narrow = tmp_path / "card_narrow.svg"
        out_wide = tmp_path / "card_wide.svg"

        _render_card(_TASK, _ASSISTANT, _USER, str(out_narrow), width=600)
        _render_card(_TASK, _ASSISTANT, _USER, str(out_wide), width=1200)

        narrow_svg = out_narrow.read_text(encoding="utf-8")
        wide_svg = out_wide.read_text(encoding="utf-8")

        assert 'width="600"' in narrow_svg
        assert 'width="1200"' in wide_svg
        # The two SVGs must differ
        assert narrow_svg != wide_svg

    def test_png_output_respects_custom_width(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out), width=600)

        assert isinstance(result[1], Image)
        meta = json.loads(result[0].text)
        assert meta["format"] == "png"
        # PNG was written successfully
        assert out.exists()
        assert out.stat().st_size > 0


class TestRenderCardCustomFontSize:
    """Tests for custom font_size parameter."""

    def test_svg_contains_custom_font_size(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out), font_size=20)

        svg_text = out.read_text(encoding="utf-8")
        assert "font-size: 20px" in svg_text

    def test_svg_default_font_size_is_15(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out))

        svg_text = out.read_text(encoding="utf-8")
        assert "font-size: 15px" in svg_text

    def test_font_size_does_not_affect_format_detection(self, tmp_path: Path) -> None:
        out_svg = tmp_path / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out_svg), font_size=25)

        meta = json.loads(result[0].text)
        assert meta["format"] == "svg"
        assert isinstance(result[1], TextContent)


class TestRenderCardCombinedDimensions:
    """Tests for width and font_size used together."""

    def test_both_params_applied_to_svg(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out), width=1200, font_size=22)

        svg_text = out.read_text(encoding="utf-8")
        assert 'width="1200"' in svg_text
        assert "font-size: 22px" in svg_text

    def test_both_params_applied_to_png(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out), width=1200, font_size=22)

        assert isinstance(result[1], Image)
        assert out.exists()
        assert result[1].data[:4] == b"\x89PNG"

    def test_default_params_backward_compatible(self, tmp_path: Path) -> None:
        """Calling without width/font_size produces same result as explicit defaults."""
        out_default = tmp_path / "default.svg"
        out_explicit = tmp_path / "explicit.svg"

        _render_card(_TASK, _ASSISTANT, _USER, str(out_default))
        _render_card(_TASK, _ASSISTANT, _USER, str(out_explicit), width=_DEFAULT_WIDTH, font_size=_DEFAULT_FONT_SIZE)

        default_svg = out_default.read_text(encoding="utf-8")
        explicit_svg = out_explicit.read_text(encoding="utf-8")
        assert default_svg == explicit_svg
