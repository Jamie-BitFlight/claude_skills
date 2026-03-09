"""Tests for the render_rage_receipt tool and _render_card helper.

Verifies that:
- SVG output returns TextContent blocks (metadata + SVG string)
- PNG output returns TextContent metadata + Image object
- Files are written to disk in both cases
- JSON metadata always contains output_path and format
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the MCP server directory to the path so we can import the module
_SERVER_DIR = Path(__file__).resolve().parent.parent / "mcp"
sys.path.insert(0, str(_SERVER_DIR))

from fastmcp.utilities.types import Image
from mcp.types import TextContent
from server import _render_card  # ty: ignore[unresolved-import]

_TASK = "Implement login page"
_ASSISTANT = "I have written the login page using React."
_USER = "I said use Vue, not React! Read the prompt!"


class TestRenderCardSVG:
    """Tests for SVG output format."""

    def test_returns_two_text_content_blocks(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert len(result) == 2
        assert isinstance(result[0], TextContent)
        assert isinstance(result[1], TextContent)

    def test_metadata_block_contains_output_path_and_format(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        meta = json.loads(result[0].text)
        assert meta["format"] == "svg"
        assert meta["output_path"] == str(out)

    def test_svg_content_block_contains_svg_xml(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        svg_text = result[1].text
        assert "<svg" in svg_text
        assert "</svg>" in svg_text

    def test_svg_file_written_to_disk(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<svg" in content

    def test_svg_file_content_matches_returned_content(self, tmp_path: Path) -> None:
        out = tmp_path / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        file_content = out.read_text(encoding="utf-8")
        returned_svg = result[1].text
        assert file_content == returned_svg


class TestRenderCardPNG:
    """Tests for PNG output format."""

    def test_returns_text_content_and_image(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert len(result) == 2
        assert isinstance(result[0], TextContent)
        assert isinstance(result[1], Image)

    def test_metadata_block_contains_output_path_and_format(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        meta = json.loads(result[0].text)
        assert meta["format"] == "png"
        assert meta["output_path"] == str(out)

    def test_image_object_has_png_data(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        image = result[1]
        assert isinstance(image, Image)
        assert image.data is not None
        assert len(image.data) > 0
        # PNG magic bytes
        assert image.data[:4] == b"\x89PNG"

    def test_png_file_written_to_disk(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert out.exists()
        file_bytes = out.read_bytes()
        assert file_bytes[:4] == b"\x89PNG"

    def test_png_file_matches_returned_image_data(self, tmp_path: Path) -> None:
        out = tmp_path / "card.png"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        file_bytes = out.read_bytes()
        image = result[1]
        assert isinstance(image, Image)
        assert file_bytes == image.data


class TestRenderCardEdgeCases:
    """Edge case tests."""

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "deep" / "card.svg"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert out.exists()
        assert len(result) == 2

    def test_uppercase_extension_treated_as_png(self, tmp_path: Path) -> None:
        out = tmp_path / "card.PNG"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        assert isinstance(result[1], Image)

    def test_non_svg_non_png_defaults_to_svg(self, tmp_path: Path) -> None:
        out = tmp_path / "card.html"
        result = _render_card(_TASK, _ASSISTANT, _USER, str(out))

        # Non-png extension falls through to SVG path
        assert isinstance(result[1], TextContent)
        meta = json.loads(result[0].text)
        assert meta["format"] == "svg"
