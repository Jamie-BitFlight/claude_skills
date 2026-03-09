#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow>=10.0.0",
# ]
# ///
"""Render an RTFP artifact as a Claude Code terminal-style PNG.

Produces a dark-themed terminal screenshot with macOS window chrome,
containing exactly three sections: task summary, assistant output,
and user reaction.

Input JSON format::

    {"task_summary": "task: writing a Claude Code plugin", "triggering_assistant_output": "...", "user_reaction": "..."}

Output: PNG file (default ``<tempdir>/rtfp-artifact.png``).

Usage::

    render_artifact.py --input-file input.json --output out.png --width 900
    cat input.json | render_artifact.py --output out.png
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
AnyFont: TypeAlias = ImageFont.FreeTypeFont | ImageFont.ImageFont

# ---------------------------------------------------------------------------
# Color scheme -- dark terminal aesthetic
# ---------------------------------------------------------------------------
BG: tuple[int, int, int] = (26, 26, 26)  # #1a1a1a
CHROME_BG: tuple[int, int, int] = (40, 40, 40)  # #282828 -- title bar
BORDER: tuple[int, int, int] = (68, 68, 68)  # #444444 -- subtle dividers
TEXT_DIM: tuple[int, int, int] = (136, 136, 136)  # #888888 -- labels
TEXT_TASK: tuple[int, int, int] = (180, 180, 200)  # #b4b4c8 -- task line
TEXT_ASST: tuple[int, int, int] = (200, 210, 245)  # #c8d2f5 -- assistant
TEXT_USER: tuple[int, int, int] = (255, 255, 255)  # #ffffff -- user (bright)
DOT_RED: tuple[int, int, int] = (255, 95, 86)  # macOS red
DOT_YEL: tuple[int, int, int] = (255, 189, 46)  # macOS yellow
DOT_GRN: tuple[int, int, int] = (39, 201, 63)  # macOS green
CORNER_RADIUS = 12

PADDING = 32
LINE_SPACING = 6
SECTION_GAP = 20
CHROME_H = 40

# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------
_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    "/usr/share/fonts/truetype/hack/Hack-Regular.ttf",
    "/usr/share/fonts/truetype/fira/FiraMono-Regular.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/Windows/Fonts/consola.ttf",
]

_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
    "/usr/share/fonts/truetype/hack/Hack-Bold.ttf",
]


def _load_font(candidates: list[str], size: int) -> AnyFont:
    """Load the first available font from candidates at the given size.

    Args:
        candidates: File paths to try in order.
        size: Font size in points.

    Returns:
        A loaded font object.
    """
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _resolve_candidates(search: list[str]) -> list[str]:
    """Return a single-element list with the first existing path, or empty.

    Args:
        search: Font file paths to check.

    Returns:
        List with the winning path, or empty list.
    """
    winning = next((p for p in search if Path(p).exists()), None)
    return [winning] if winning else []


def load_fonts(base_size: int = 15) -> dict[str, AnyFont]:
    """Load the font variants used by the renderer.

    Args:
        base_size: Base font size in points.

    Returns:
        Dict mapping variant names to loaded font objects.
    """
    mono = _resolve_candidates(_MONO_CANDIDATES)
    bold = _resolve_candidates(_BOLD_CANDIDATES)
    return {
        "regular": _load_font(mono, base_size),
        "bold": _load_font(bold, base_size),
        "small": _load_font(mono, base_size - 2),
        "label": _load_font(bold, base_size - 1),
    }


# ---------------------------------------------------------------------------
# Text measurement and wrapping
# ---------------------------------------------------------------------------


def _char_width(font: AnyFont) -> float:
    """Get the average character width for a monospace font.

    Args:
        font: The font to measure.

    Returns:
        Width of a single character in pixels.
    """
    try:
        return font.getlength("x")
    except AttributeError:
        return 8.0


def wrap_text(text: str, font: AnyFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels.

    Args:
        text: The text to wrap.
        font: Font used for width estimation.
        max_width: Maximum line width in pixels.

    Returns:
        List of wrapped text lines.
    """
    chars_per_line = max(20, int(max_width / max(_char_width(font), 1)))
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(raw_line, width=chars_per_line, break_long_words=True)
        lines.extend(wrapped or [""])
    return lines


def _line_height(font_size: int) -> int:
    """Calculate the pixel height of a single line.

    Args:
        font_size: Font size in points.

    Returns:
        Line height in pixels.
    """
    return font_size + LINE_SPACING


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _font_size(font: AnyFont) -> int:
    """Extract the numeric size from a font object.

    Args:
        font: A Pillow font object.

    Returns:
        Font size as integer.
    """
    return int(getattr(font, "size", 13))


def draw_rounded_rect(
    img: Image.Image, rect: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int]
) -> None:
    """Draw a filled rectangle with rounded corners onto an image.

    Uses a mask-based approach for clean anti-aliased corners.

    Args:
        img: Target image.
        rect: Bounding box (x0, y0, x1, y1).
        radius: Corner radius in pixels.
        fill: RGB fill color.
    """
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    overlay = Image.new("RGB", (w, h), fill)
    img.paste(overlay, (x0, y0), mask)


def draw_chrome(draw: ImageDraw.ImageDraw, img: Image.Image, width: int, title: str, font: AnyFont) -> None:
    """Draw the terminal window chrome (title bar with traffic-light dots).

    Args:
        draw: ImageDraw instance for the image.
        img: The image (needed for rounded-rect compositing).
        width: Image width.
        title: Title text displayed in the chrome bar.
        font: Font for the title text.
    """
    # Rounded rectangle for top chrome (only top corners rounded)
    draw_rounded_rect(img, (0, 0, width, CHROME_H + CORNER_RADIUS), CORNER_RADIUS, CHROME_BG)
    # Overwrite the bottom portion to make it square at the junction
    draw.rectangle([0, CHROME_H, width, CHROME_H + CORNER_RADIUS], fill=BG)
    # Redraw the actual chrome area cleanly
    draw.rectangle([0, CORNER_RADIUS, width, CHROME_H], fill=CHROME_BG)

    # Traffic-light dots
    cx = PADDING
    cy = CHROME_H // 2
    r = 6
    for color in (DOT_RED, DOT_YEL, DOT_GRN):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        cx += 20

    # Title centered
    try:
        title_w = font.getlength(title)
    except AttributeError:
        title_w = len(title) * 8
    tx = max(PADDING, int((width - title_w) // 2))
    ty = (CHROME_H - _font_size(font)) // 2
    draw.text((tx, ty), title, font=font, fill=TEXT_DIM)


def draw_divider(draw: ImageDraw.ImageDraw, y: int, width: int) -> None:
    """Draw a horizontal divider line.

    Args:
        draw: ImageDraw instance.
        y: Vertical position of the line.
        width: Image width.
    """
    draw.line([(PADDING, y), (width - PADDING, y)], fill=BORDER, width=1)


def draw_label(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, font: AnyFont) -> int:
    """Draw a section label and return its rendered height.

    Args:
        draw: ImageDraw instance.
        x: Horizontal position.
        y: Vertical position.
        label: Label text.
        font: Font for the label.

    Returns:
        Height in pixels consumed by the label.
    """
    draw.text((x, y), label, font=font, fill=TEXT_DIM)
    return _font_size(font) + LINE_SPACING + 4


def draw_lines(
    draw: ImageDraw.ImageDraw, x: int, y: int, lines: list[str], font: AnyFont, color: tuple[int, int, int]
) -> int:
    """Draw wrapped text lines and return total height consumed.

    Args:
        draw: ImageDraw instance.
        x: Horizontal position.
        y: Starting vertical position.
        lines: Text lines to draw.
        font: Font for the text.
        color: RGB text color.

    Returns:
        Total height in pixels consumed by the drawn lines.
    """
    lh = _line_height(_font_size(font))
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += lh
    return len(lines) * lh


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def render(
    task_summary: str,
    assistant_output: str,
    user_reaction: str,
    output_path: Path,
    width: int = 900,
    base_font_size: int = 15,
) -> Path:
    """Render the RTFP artifact image and save it to output_path.

    Args:
        task_summary: Short dry task summary line.
        assistant_output: The assistant output that triggered the reaction.
        user_reaction: The user's emotional reply.
        output_path: Where to write the PNG.
        width: Image width in pixels.
        base_font_size: Base font size in points.

    Returns:
        The path to the written PNG file.
    """
    fonts = load_fonts(base_font_size)
    indent = 16
    text_width = width - 2 * PADDING - indent

    # Pre-wrap all sections
    task_lines = wrap_text(task_summary, fonts["regular"], text_width)
    asst_lines = wrap_text(assistant_output, fonts["regular"], text_width)
    user_lines = wrap_text(user_reaction, fonts["bold"], text_width)

    lh = _line_height(base_font_size)
    label_h = base_font_size + LINE_SPACING + 4

    # Calculate total height
    height = (
        CHROME_H
        + PADDING
        + label_h
        + len(task_lines) * lh
        + SECTION_GAP
        + 1  # divider
        + SECTION_GAP
        + label_h
        + len(asst_lines) * lh
        + SECTION_GAP
        + 1  # divider
        + SECTION_GAP
        + label_h
        + len(user_lines) * lh
        + PADDING
    )

    # Create image with rounded-corner background
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_rounded_rect(
        img,
        (0, 0, width, height),
        CORNER_RADIUS,
        BG,  # type: ignore[arg-type]
    )
    draw = ImageDraw.Draw(img)

    # Chrome
    draw_chrome(draw, img, width, "Claude Code", fonts["small"])

    y = CHROME_H + PADDING
    x = PADDING

    # Task section
    draw_label(draw, x, y, "task:", fonts["label"])
    y += label_h
    draw_lines(draw, x + indent, y, task_lines, fonts["regular"], TEXT_TASK)
    y += len(task_lines) * lh

    y += SECTION_GAP
    draw_divider(draw, y, width)
    y += SECTION_GAP

    # Assistant section
    draw_label(draw, x, y, "assistant:", fonts["label"])
    y += label_h
    draw_lines(draw, x + indent, y, asst_lines, fonts["regular"], TEXT_ASST)
    y += len(asst_lines) * lh

    y += SECTION_GAP
    draw_divider(draw, y, width)
    y += SECTION_GAP

    # User reaction section
    draw_label(draw, x, y, "user:", fonts["label"])
    y += label_h
    draw_lines(draw, x + indent, y, user_lines, fonts["bold"], TEXT_USER)

    # Convert RGBA to RGB for PNG output (paste onto solid background)
    final = Image.new("RGB", (width, height), (0, 0, 0))
    final.paste(img, mask=img.split()[3])

    final.save(str(output_path), "PNG", optimize=True)
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Render RTFP terminal-style artifact as PNG")
    parser.add_argument(
        "--input-file",
        default=None,
        help="JSON file with task_summary/triggering_assistant_output/user_reaction fields (default: stdin)",
    )
    default_output = str(Path(tempfile.gettempdir()) / "rtfp-artifact.png")
    parser.add_argument("--output", "-o", default=default_output, help=f"Output PNG path (default: {default_output})")
    parser.add_argument("--width", type=int, default=900, help="Image width in pixels (default: 900)")
    parser.add_argument("--font-size", type=int, default=15, help="Base font size (default: 15)")
    return parser.parse_args(argv)


def main() -> None:
    """Parse CLI arguments and render an RTFP artifact PNG."""
    args = parse_args()

    if args.input_file is not None:
        with Path(args.input_file).open(encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = json.load(sys.stdin)

    task_summary = data.get("task_summary", "").strip()
    assistant_output = data.get("triggering_assistant_output", "").strip()
    user_reaction = data.get("user_reaction", "").strip()

    if not task_summary or not user_reaction:
        print("Error: 'task_summary' and 'user_reaction' fields are required in the input JSON.", file=sys.stderr)
        sys.exit(1)

    if not assistant_output:
        assistant_output = "(assistant output not available)"

    out_path = Path(args.output)
    result = render(
        task_summary, assistant_output, user_reaction, out_path, width=args.width, base_font_size=args.font_size
    )
    print(f"Artifact written to: {result}")


if __name__ == "__main__":
    main()
