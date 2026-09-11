#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "pydantic>=2.0",
#     "rich>=13.0",
#     "cairosvg>=2.7.0",
#     "tiktoken>=0.7.0",
# ]
# ///
"""Mine Claude and Codex sessions for instruction-following failures.

Provides session discovery, user-message batching, conversational context,
receipt rendering, and provider-tagged social post copy.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET  # ruff: ignore[suspicious-xml-etree-import]
from collections.abc import Iterator
from datetime import UTC, datetime
from io import StringIO, TextIOWrapper
from typing import TYPE_CHECKING, Any, Literal

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element as _Element

import tiktoken
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from mcp.types import TextContent
from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_WINDOW: int = 5
_MAX_SESSION_LIMIT: int = 1000
_SUMMARY_RECORD_LIMIT: int = 200

_READONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_WRITE_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_DEFAULT_BATCH_TOKENS: int = 100_000
_TIKTOKEN_ENCODING: str = "p50k_base"


class _EncoderCache:
    """Lazily-initialised tiktoken encoder singleton."""

    _enc: tiktoken.Encoding | None = None

    @classmethod
    def get(cls) -> tiktoken.Encoding:
        """Return the shared p50k_base encoder, creating it on first call."""
        if cls._enc is None:
            cls._enc = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
        return cls._enc


def _count_tokens(text: str) -> int:
    """Return the token count from the configured batch encoding."""
    return len(_EncoderCache.get().encode(text))


def _split_into_batches(messages: list[dict[str, Any]], batch_tokens: int) -> list[list[dict[str, Any]]]:
    """Return messages split into token-bounded batches."""
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_tokens = 0
    for msg in messages:
        tokens = msg["token_count"]
        if current_tokens + tokens > batch_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(msg)
        current_tokens += tokens
    if current_batch:
        batches.append(current_batch)
    return batches


def _write_batches(messages: list[dict[str, Any]], output_path: str, batch_tokens: int) -> list[str]:
    """Return paths written as one JSONL file or numbered batch files."""
    total_tokens = sum(m["token_count"] for m in messages)

    if total_tokens <= batch_tokens:
        out_path = pathlib.Path(output_path).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for msg in messages:
                fh.write(json.dumps(msg) + "\n")
        return [str(out_path)]

    base = pathlib.Path(output_path).expanduser()
    batch_dir = base.parent / f"rtfp-batches-{base.stem}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    batches = _split_into_batches(messages, batch_tokens)
    written_paths: list[str] = []
    for i, batch in enumerate(batches):
        batch_path = batch_dir / f"batch_{i + 1:03d}.jsonl"
        with batch_path.open("w", encoding="utf-8") as fh:
            for msg in batch:
                fh.write(json.dumps(msg) + "\n")
        written_paths.append(str(batch_path))
    return written_paths


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("frustration-analyzer", mask_error_details=False)

# ---------------------------------------------------------------------------
# Session reader
# ---------------------------------------------------------------------------


class SessionMessage(BaseModel):
    """One user-visible conversational message from a session transcript."""

    model_config = ConfigDict(frozen=True, strict=True)

    source_line: int
    role: Literal["user", "assistant"]
    text: str
    timestamp: str = ""
    uuid: str = ""


class SessionTranscript(BaseModel):
    """Provider-neutral transcript metadata and messages."""

    model_config = ConfigDict(frozen=True, strict=True)

    provider: Literal["claude", "codex"]
    session_id: str
    project: str
    messages: list[SessionMessage]


class SessionSummary(BaseModel):
    """Metadata returned by session discovery."""

    model_config = ConfigDict(frozen=True, strict=True)

    file: str
    project: str
    modified: str
    size_bytes: int
    title: str
    provider: Literal["claude", "codex"]
    session_id: str


SessionMessage.model_rebuild(_types_namespace={"Literal": Literal})
SessionTranscript.model_rebuild(_types_namespace={"Literal": Literal, "SessionMessage": SessionMessage})
SessionSummary.model_rebuild(_types_namespace={"Literal": Literal})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_glob(glob_path: str) -> list[str]:
    """Return sorted paths resolved from a glob pattern."""
    expanded = str(pathlib.Path(glob_path).expanduser()) if "~" in glob_path else glob_path
    glob_chars = {"*", "?", "["}

    if not any(c in expanded for c in glob_chars):
        p = pathlib.Path(expanded)
        return [str(p)] if p.is_file() else []

    parts = pathlib.PurePosixPath(expanded).parts
    base_parts: list[str] = []
    for part in parts:
        if any(c in part for c in glob_chars):
            break
        base_parts.append(part)

    if base_parts:
        base = pathlib.Path(*base_parts)
        relative = str(pathlib.PurePosixPath(*parts[len(base_parts) :]))
    else:
        base = pathlib.Path()
        relative = expanded

    return sorted(str(p) for p in base.glob(relative))


def _resolve_path(file: str) -> str:
    """Return a path with its home directory expanded."""
    return str(pathlib.Path(file).expanduser()) if "~" in file else file


def _extract_user_text_from_value(
    content: str | list[str | dict[str, str]] | dict[str, str | list[str | dict[str, str]]] | None,
) -> str:
    """Return text from supported user-message content shapes."""
    unwrapped = content.get("content", content) if isinstance(content, dict) else content

    if isinstance(unwrapped, str):
        return unwrapped
    if isinstance(unwrapped, list):
        parts: list[str] = []
        for block in unwrapped:
            if isinstance(block, dict) and str(block.get("type", "")).lower() == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


def _is_human_plaintext(text: str) -> bool:
    """Return whether text is genuine human input."""
    stripped = text.strip()
    # Remove exactly one wrapping pair of double-quotes if present
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 1:
        stripped = stripped[1:-1].strip()
    if not stripped:
        return False
    # Skill/command injection payloads, system-injected XML tags, and
    # stop-hook feedback lines are not genuine human input.
    if stripped.startswith((
        "<command-message",
        "<command-name",
        "<command-args",
        "<task-notification",
        "<system-reminder",
        '<parameter name="orchestrator-read-warning',
        "[~/.claude/",
    )):
        return False
    # Tool result blocks are JSON arrays of dicts
    return not stripped.startswith("[{")


def _extract_assistant_text(message: str | dict[str, Any] | None) -> str:
    """Return text blocks from a Claude assistant message."""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            t = block.get("text", "")
            if isinstance(t, str):
                parts.append(t)
    return " ".join(parts)


def _iter_jsonl(file_path: str) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with pathlib.Path(file_path).open(encoding="utf-8") as handle:
            for line_index, line in enumerate(handle):
                if not line.strip():
                    continue
                value = json.loads(line)
                if isinstance(value, dict):
                    yield line_index, value
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"Could not read session file {file_path}: {exc}") from exc


def _read_jsonl(file_path: str) -> list[tuple[int, dict[str, Any]]]:
    return list(_iter_jsonl(file_path))


def _codex_text(value: str | list[dict[str, str]] | None) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    parts = [
        block.get("text", "")
        for block in value
        if isinstance(block, dict) and str(block.get("type", "")).lower() == "text"
    ]
    return " ".join(text for text in parts if isinstance(text, str))


def _claude_message(line_index: int, record: dict[str, Any]) -> SessionMessage | None:
    role = record.get("type")
    if role not in {"user", "assistant"}:
        return None
    if role == "user":
        if record.get("toolUseResult") is not None:
            return None
        text = _extract_user_text_from_value(record.get("message"))
        if not _is_human_plaintext(text):
            return None
    else:
        text = _extract_assistant_text(record.get("message"))
        if not text:
            return None
    return SessionMessage(
        source_line=line_index,
        role=role,
        text=text,
        timestamp=str(record.get("timestamp") or ""),
        uuid=str(record.get("uuid") or ""),
    )


def _codex_message(line_index: int, record: dict[str, Any]) -> SessionMessage | None:
    if record.get("type") != "event_msg" or not isinstance(record.get("payload"), dict):
        return None
    payload = record["payload"]
    event_type = payload.get("type")
    role: Literal["user", "assistant"] | None = None
    text = ""
    uuid = ""
    if event_type in {"user_message", "agent_message"}:
        role = "user" if event_type == "user_message" else "assistant"
        text = _codex_text(payload.get("message"))
        uuid = str(payload.get("client_id") or "")
    elif event_type == "item_completed" and isinstance(payload.get("item"), dict):
        item = payload["item"]
        item_type = str(item.get("type", "")).lower()
        if item_type in {"usermessage", "agentmessage"}:
            role = "user" if item_type == "usermessage" else "assistant"
            text = _codex_text(item.get("content"))
            uuid = str(item.get("id") or payload.get("client_id") or "")
    if role is None or not text.strip():
        return None
    return SessionMessage(
        source_line=line_index, role=role, text=text, timestamp=str(record.get("timestamp") or ""), uuid=uuid
    )


def read_session(file_path: str) -> SessionTranscript:
    """Read a Claude or Codex JSONL session into one message model.

    Args:
        file_path: Session JSONL path.

    Returns:
        Provider-neutral transcript.

    Raises:
        ToolError: If the file is missing, malformed, or unsupported.
    """
    resolved = _resolve_path(file_path)
    if not pathlib.Path(resolved).is_file():
        raise ToolError(f"Session file not found: {resolved}")
    records = _read_jsonl(resolved)
    codex_meta = next(
        (
            record["payload"]
            for _line_index, record in records
            if record.get("type") == "session_meta" and isinstance(record.get("payload"), dict)
        ),
        None,
    )
    is_codex = codex_meta is not None or any(record.get("type") == "event_msg" for _index, record in records)
    is_claude = any(record.get("type") in {"user", "assistant"} for _index, record in records)
    if not is_codex and not is_claude:
        raise ToolError(f"Unsupported session format: {resolved}")

    if is_codex:
        messages = [message for index, record in records if (message := _codex_message(index, record)) is not None]
        metadata = codex_meta or {}
        cwd = str(metadata.get("cwd") or "")
        return SessionTranscript(
            provider="codex",
            session_id=str(metadata.get("id") or pathlib.Path(resolved).stem),
            project=pathlib.Path(cwd).name if cwd else pathlib.Path(resolved).parent.name,
            messages=messages,
        )

    messages = [message for index, record in records if (message := _claude_message(index, record)) is not None]
    session_id = next(
        (str(record.get("sessionId")) for _index, record in records if record.get("sessionId")),
        pathlib.Path(resolved).stem,
    )
    return SessionTranscript(
        provider="claude", session_id=session_id, project=pathlib.Path(resolved).parent.name, messages=messages
    )


def _message_entry(message: SessionMessage) -> dict[str, Any]:
    return {
        "role": message.role,
        "line_index": message.source_line,
        "text": message.text,
        "timestamp": message.timestamp,
    }


def _query_user_messages(
    glob_path: str, context_window: int, offset: int = 0, limit: int = 100
) -> tuple[list[dict[str, Any]], int, int]:
    files = _resolve_glob(glob_path)
    if not files:
        raise ToolError(f"No files matched glob pattern: {glob_path}")

    messages: list[dict[str, Any]] = []
    for file_path in files:
        transcript = read_session(file_path)
        for message in transcript.messages:
            if message.role != "user":
                continue
            messages.append({
                "file": file_path,
                "line_index": message.source_line,
                "uuid": message.uuid,
                "timestamp": message.timestamp,
                "session_id": transcript.session_id,
                "text": message.text,
                "context": _context_messages(transcript, message.source_line, context_window),
            })
    return messages[offset : offset + limit], len(messages), len(files)


def _context_messages(transcript: SessionTranscript, line_index: int, context_window: int) -> list[dict[str, Any]]:
    if context_window <= 0:
        return []
    preceding = [message for message in transcript.messages if message.source_line < line_index]
    return [
        {"role": message.role, "timestamp": message.timestamp, "uuid": message.uuid, "text": message.text}
        for message in preceding[-context_window:]
    ]


def _session_summary(path: pathlib.Path, stat: os.stat_result) -> SessionSummary:
    provider: Literal["claude", "codex"] | None = None
    session_id = ""
    project = path.parent.name
    title = ""
    codex_metadata_seen = False

    for record_number, (line_index, record) in enumerate(_iter_jsonl(str(path)), start=1):
        record_type = record.get("type")
        if record_type == "session_meta" and isinstance(record.get("payload"), dict):
            provider = "codex"
            codex_metadata_seen = True
            metadata = record["payload"]
            session_id = str(metadata.get("id") or "")
            cwd = str(metadata.get("cwd") or "")
            project = pathlib.Path(cwd).name or project
        elif record_type == "event_msg":
            provider = "codex"
            message = _codex_message(line_index, record)
            if message is not None and message.role == "user" and not title:
                title = message.text[:80].replace("\n", " ").strip()
        elif record_type in {"user", "assistant"} and provider is None:
            provider = "claude"
            session_id = session_id or str(record.get("sessionId") or "")
            message = _claude_message(line_index, record)
            if message is not None and message.role == "user" and not title:
                title = message.text[:80].replace("\n", " ").strip()

        if provider == "claude" and title and session_id:
            break
        if provider == "codex" and title and codex_metadata_seen:
            break
        if record_number >= _SUMMARY_RECORD_LIMIT:
            break

    if provider is None:
        raise ToolError(f"Unsupported session format: {path}")
    return SessionSummary(
        file=str(path),
        project=project,
        modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        size_bytes=stat.st_size,
        title=title or path.stem,
        provider=provider,
        session_id=session_id or path.stem,
    )


def _parse_time_bound(value: str | None, name: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ToolError(f"{name} must be a valid timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ToolError(f"{name} must include a timezone offset")
    return parsed.astimezone(UTC)


def _message_at_line(transcript: SessionTranscript, line_index: int, file_path: str) -> SessionMessage:
    message = next((item for item in transcript.messages if item.source_line == line_index), None)
    if message is None:
        raise ToolError(f"line_index {line_index} not found in {file_path}")
    return message


def _session_files(project_path: str | None) -> list[pathlib.Path]:
    if project_path is not None:
        root = pathlib.Path(project_path).expanduser()
        if not root.exists():
            raise ToolError(f"Project path does not exist: {root}")
        return list(root.rglob("*.jsonl"))

    claude_root = pathlib.Path("~/.claude/projects").expanduser()
    codex_root = pathlib.Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    files = list(claude_root.rglob("*.jsonl")) if claude_root.exists() else []
    sessions_root = codex_root / "sessions"
    archived_root = codex_root / "archived_sessions"
    if sessions_root.exists():
        files.extend(sessions_root.rglob("rollout-*.jsonl"))
    if archived_root.exists():
        files.extend(archived_root.glob("rollout-*.jsonl"))
    return files


# ---------------------------------------------------------------------------
# Card rendering (Rich-based SVG/PNG)
# ---------------------------------------------------------------------------


def _build_card_content(task_summary: str, assistant_excerpt: str, user_reply: str) -> Text:
    """Return styled task, assistant, and user sections."""
    content = Text()

    sections: list[tuple[str, str, str]] = [
        ("task:", task_summary, "#4ec9b0"),
        ("assistant:", assistant_excerpt, "#dcdcaa"),
        ("user:", user_reply, "#f44747"),
    ]

    for i, (label, body, color) in enumerate(sections):
        if i > 0:
            content.append("\n")
        content.append(label, style=f"bold {color}")
        content.append(f" {body}\n", style="dim white")

    return content


_SVG_NS = "http://www.w3.org/2000/svg"
_SVG_NS_MAP = {"svg": _SVG_NS}
_BORDER_COLOR = "#1984e9"
_BOX_DRAWING_CHARS = frozenset("╭╮╰╯│─┐┘┌└├┤┬┴┼")
_G_TAG = f"{{{_SVG_NS}}}g"
_TEXT_TAG = f"{{{_SVG_NS}}}text"
_CLIP_LINE_MARKER = "-line-"
_CLIP_FIRST_LINE_MARKER = "-line-0"
_CONSOLE_WIDTH = 100

_RE_TRANSLATE = re.compile(r"translate\(")
_RE_TRANSLATE_COORDS = re.compile(r"translate\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")


def _find_content_group(root: _Element) -> _Element | None:
    """Return the translated SVG group containing text."""
    for g in root.iter(_G_TAG):
        if _RE_TRANSLATE.search(g.get("transform", "")) and any(True for _ in g.iter(_TEXT_TAG)):
            return g
    return None


def _parse_translate(g: _Element) -> tuple[float, float]:
    """Return translation coordinates with renderer defaults."""
    m = _RE_TRANSLATE_COORDS.search(g.get("transform", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (9.0, 41.0)


def _extract_line_height(root: _Element) -> float:
    """Return the SVG line height with its renderer default."""
    style_el = root.find(f"{{{_SVG_NS}}}style")
    if style_el is not None and style_el.text and (m := re.search(r"line-height:\s*([\d.]+)px", style_el.text)):
        return float(m.group(1))
    return 24.4


def _count_line_clips(root: _Element) -> tuple[int, float, float | None]:
    clips = root.findall(".//svg:defs/svg:clipPath", _SVG_NS_MAP)
    num_lines = 0
    first_line_y = 1.5
    cell_width: float | None = None
    for cp in clips:
        cp_id = cp.get("id") or ""
        if _CLIP_LINE_MARKER not in cp_id:
            continue
        num_lines += 1
        if _CLIP_FIRST_LINE_MARKER in cp_id:
            rect_el = cp.find(f"{{{_SVG_NS}}}rect")
            if rect_el is not None:
                first_line_y = float(rect_el.get("y", "1.5"))
                clip_width = float(rect_el.get("width", "0"))
                if clip_width > 0:
                    cell_width = clip_width / _CONSOLE_WIDTH
    return num_lines, first_line_y, cell_width


def _find_matrix_group(outer_g: _Element) -> _Element:
    """Return the matrix group, falling back to its parent."""
    for g in outer_g.iter(_G_TAG):
        if "matrix" in g.get("class", ""):
            return g
    return outer_g


def _is_box_drawing_only(text: str) -> bool:
    """Return whether visible text consists only of box-drawing glyphs."""
    non_ws = text.replace(" ", "").replace("\n", "").replace("\r", "")
    return bool(non_ws) and all(c in _BOX_DRAWING_CHARS for c in non_ws)


def _hide_box_drawing_glyphs(matrix_g: _Element) -> None:
    """Hide box-drawing glyphs while preserving the RTFP title."""
    # Single pass: hide box-drawing elements and find the title candidate
    title_candidate: _Element | None = None
    longest_non_box = 0
    for text_el in matrix_g.iter(_TEXT_TAG):
        raw = "".join(text_el.itertext()).strip().replace("\xa0", " ")
        if _is_box_drawing_only(raw):
            text_el.set("fill-opacity", "0")
            # Check if this hidden element contains the RTFP title
            cleaned = "".join(c for c in raw if c not in _BOX_DRAWING_CHARS).strip()
            if cleaned == "RTFP" and len(cleaned) > longest_non_box:
                longest_non_box = len(cleaned)
                title_candidate = text_el

    # Re-show the RTFP title element (it shares a row with ─ chars)
    if title_candidate is not None:
        title_candidate.attrib.pop("fill-opacity", None)


def _inject_border_rect(svg_text: str) -> str:
    """Return SVG with one gapless rectangle replacing glyph borders."""
    ET.register_namespace("", _SVG_NS)
    root = ET.fromstring(svg_text)  # ruff: ignore[suspicious-xml-element-tree-usage]

    outer_g = _find_content_group(root)
    if outer_g is None:
        return svg_text

    tx, ty = _parse_translate(outer_g)
    line_height = _extract_line_height(root)
    num_lines, first_line_y, char_width = _count_line_clips(root)
    if char_width is None:
        return svg_text

    _hide_box_drawing_glyphs(_find_matrix_group(outer_g))

    # Rect aligns with where box-drawing chars were: left/right edges
    # centered on first/last character cells, top/bottom at clip boundaries.
    rect_attrs: dict[str, str] = {
        "x": f"{tx + char_width * 0.5:.1f}",
        "y": f"{ty + first_line_y:.1f}",
        "width": f"{char_width * (_CONSOLE_WIDTH - 1):.1f}",
        "height": f"{num_lines * line_height:.1f}",
        "rx": "4",
        "ry": "4",
        "fill": "none",
        "stroke": _BORDER_COLOR,
        "stroke-width": "2",
    }
    rect = ET.SubElement(root, f"{{{_SVG_NS}}}rect")
    for attr, val in rect_attrs.items():
        rect.set(attr, val)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


_DEFAULT_WIDTH: int = 900
_DEFAULT_FONT_SIZE: int = 15


def _apply_svg_dimensions(svg_text: str, *, width: int, font_size: int) -> str:
    """Return resized SVG with its aspect ratio preserved."""
    ET.register_namespace("", _SVG_NS)
    root = ET.fromstring(svg_text)  # ruff: ignore[suspicious-xml-element-tree-usage]

    # Scale width/height proportionally
    old_width_str = root.get("width", "")
    old_width = float(re.sub(r"[^0-9.]", "", old_width_str)) if old_width_str else float(width)
    scale = width / old_width if old_width else 1.0

    root.set("width", str(width))

    old_height_str = root.get("height", "")
    if old_height_str:
        old_height = float(re.sub(r"[^0-9.]", "", old_height_str))
        root.set("height", str(int(old_height * scale)))

    # Update font-size in embedded <style>
    style_el = root.find(f"{{{_SVG_NS}}}style")
    if style_el is not None and style_el.text:
        style_el.text = re.sub(r"font-size:\s*[\d.]+px", f"font-size: {font_size}px", style_el.text)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _render_card(
    task_summary: str,
    assistant_excerpt: str,
    user_reply: str,
    output_path: str,
    width: int = _DEFAULT_WIDTH,
    font_size: int = _DEFAULT_FONT_SIZE,
) -> list[TextContent | Image]:
    """Return the saved SVG or PNG receipt card."""
    content = _build_card_content(task_summary, assistant_excerpt, user_reply)
    panel = Panel(content, title="RTFP", title_align="left", border_style="bright_blue", padding=(1, 2))

    console = Console(file=StringIO(), record=True, width=_CONSOLE_WIDTH, force_terminal=True, color_system="truecolor")
    panel.width = console.width
    console.print(panel)

    svg_text = console.export_svg(title="RTFP")

    # Replace box-drawing character border with a continuous SVG <rect>
    svg_text = _inject_border_rect(svg_text)

    # Apply configurable dimensions: scale SVG viewBox and font-size
    svg_text = _apply_svg_dimensions(svg_text, width=width, font_size=font_size)

    out = pathlib.Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    is_png = out.suffix.lower() == ".png"
    if is_png:
        import cairosvg  # ruff: ignore[import-outside-top-level]

        png_bytes: bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=width)
        out.write_bytes(png_bytes)
        inline_content: TextContent | Image = Image(data=png_bytes, format="png")
    else:
        out.write_text(svg_text, encoding="utf-8")
        inline_content = TextContent(type="text", text=svg_text)

    metadata = json.dumps({"output_path": str(out), "format": "png" if is_png else "svg"})
    return [TextContent(type="text", text=metadata), inline_content]


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def list_sessions(
    project_path: str | None = None,
    modified_after: str | None = None,
    modified_before: str | None = None,
    provider: Literal["all", "claude", "codex"] = "all",
    limit: int = 100,
) -> dict[str, Any]:
    """List recent Claude and Codex sessions for selection.

    Without ``project_path``, searches the default session locations for both
    providers. An explicit path searches all JSONL files beneath that directory,
    such as ``~/.claude/projects/my-project`` or ``~/.codex/sessions/2026/09``.
    Results are newest first, with paths breaking
    modification-time ties. ``modified_after`` is inclusive and
    ``modified_before`` is exclusive; both require a timezone. The response
    distinguishes returned ``count`` from pre-limit ``matched_count``, includes
    provider counts and the applied limit, and reports truncation. Each summary
    exposes its UTC ``modified`` time. Unsupported files are omitted.

    Args:
        project_path: Optional directory to search recursively.
        modified_after: Inclusive lower bound for file modification time as a
            timezone-aware ISO timestamp.
        modified_before: Exclusive upper bound for file modification time as a
            timezone-aware ISO timestamp.
        provider: Return ``all``, ``claude``, or ``codex`` sessions.
        limit: Maximum number of sessions to return; valid range is 1 to 1000.

    Returns:
        ``sessions`` contains ``file``, ``project``, ``modified`` (UTC ISO),
        ``size_bytes``, ``title``, ``provider``, and ``session_id``. ``count``
        is the returned size; ``matched_count`` and ``provider_counts`` describe
        all matches before ``limit``. ``limit`` echoes the applied cap and
        ``truncated`` reports omitted matches. A title uses early user text or
        falls back to the filename stem.

    Raises:
        ToolError: If a filter is invalid.
    """
    after = _parse_time_bound(modified_after, "modified_after")
    before = _parse_time_bound(modified_before, "modified_before")
    if after is not None and before is not None and after > before:
        raise ToolError("modified_after must not be later than modified_before")
    if provider not in {"all", "claude", "codex"}:
        raise ToolError("provider must be one of: all, claude, codex")
    if not 1 <= limit <= _MAX_SESSION_LIMIT:
        raise ToolError("limit must be between 1 and 1000")

    def _scan() -> dict[str, Any]:
        file_stats: list[tuple[pathlib.Path, os.stat_result]] = []
        for path in _session_files(project_path):
            try:
                stat = path.stat()
            except OSError as exc:
                logger.debug("Skipping unreadable session file %s: %s", path, exc)
                continue
            modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            if after is not None and modified < after:
                continue
            if before is not None and modified >= before:
                continue
            file_stats.append((path, stat))
        file_stats.sort(key=lambda pair: (-pair[1].st_mtime, str(pair[0])))

        matches: list[SessionSummary] = []
        provider_counts = {"claude": 0, "codex": 0}
        for path, stat in file_stats:
            try:
                summary = _session_summary(path, stat)
            except ToolError as exc:
                logger.debug("Skipping unsupported session file %s: %s", path, exc)
                continue
            if provider not in {"all", summary.provider}:
                continue
            matches.append(summary)
            provider_counts[summary.provider] += 1

        sessions = [summary.model_dump() for summary in matches[:limit]]
        matched_count = len(matches)
        return {
            "sessions": sessions,
            "count": len(sessions),
            "matched_count": matched_count,
            "provider_counts": provider_counts,
            "limit": limit,
            "truncated": matched_count > limit,
        }

    return await asyncio.to_thread(_scan)


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def extract_user_messages(
    file: str, output_path: str, batch_tokens: int = _DEFAULT_BATCH_TOKENS
) -> dict[str, Any]:
    """Write genuine user messages from one session to JSONL batch files.

    Each compact JSONL entry contains ``file``, ``line_index``, ``text``, and
    ``token_count``. ``line_index`` is the raw zero-based source-file line used
    by context tools. Assistant messages, tool traffic, and injected content
    are excluded. A session within budget writes exactly ``output_path``;
    larger sessions write numbered files under
    ``rtfp-batches-{output_stem}/``. One oversized message occupies one batch.

    Args:
        file: Claude or Codex session JSONL file.
        output_path: Destination for a single batch and naming base for split
            batches. Home-relative paths are accepted.
        batch_tokens: Maximum encoded tokens per batch where possible.

    Returns:
        Written ``output_paths``, ``batch_count``, ``message_count``,
        ``total_tokens``, and resolved ``source_file``.

    Raises:
        ToolError: If the session is missing, unreadable, malformed, or unsupported.
    """

    def _extract() -> dict[str, Any]:
        resolved = _resolve_path(file)
        transcript = read_session(resolved)
        user_messages: list[dict[str, Any]] = [
            {
                "file": resolved,
                "line_index": message.source_line,
                "text": message.text,
                "token_count": _count_tokens(message.text),
            }
            for message in transcript.messages
            if message.role == "user"
        ]

        total_tokens = sum(m["token_count"] for m in user_messages)
        written_paths = _write_batches(user_messages, output_path, batch_tokens)

        return {
            "output_paths": written_paths,
            "batch_count": len(written_paths),
            "message_count": len(user_messages),
            "total_tokens": total_tokens,
            "source_file": resolved,
        }

    return await asyncio.to_thread(_extract)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_context_window(file: str, line_index: int, before: int = 10, after: int = 3) -> dict[str, Any]:
    """Return a conversational message with adjacent context.

    ``line_index`` addresses the raw zero-based JSONL line, while ``before``
    and ``after`` count visible user or assistant messages. Tool traffic,
    reasoning, and injected records do not occupy context slots. Every returned
    entry contains ``role``, ``line_index``, ``text``, and ``timestamp``; the
    response separates ``target``, ``before``, and ``after``.

    Args:
        file: Claude or Codex session JSONL file.
        line_index: Raw zero-based line containing the target message.
        before: Maximum visible messages before the target.
        after: Maximum visible messages after the target.

    Returns:
        ``target`` plus ordered ``before`` and ``after`` message lists.

    Raises:
        ToolError: If the session cannot be read or the line is not a visible message.
    """

    def _query() -> dict[str, Any]:
        resolved = _resolve_path(file)
        transcript = read_session(resolved)
        if not transcript.messages:
            raise ToolError(f"No messages found in {resolved}")
        target = _message_at_line(transcript, line_index, resolved)
        before_messages = (
            [message for message in transcript.messages if message.source_line < line_index][-before:]
            if before > 0
            else []
        )
        after_messages = (
            [message for message in transcript.messages if message.source_line > line_index][:after]
            if after > 0
            else []
        )

        return {
            "target": _message_entry(target),
            "before": [_message_entry(message) for message in before_messages],
            "after": [_message_entry(message) for message in after_messages],
        }

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def render_rage_receipt(
    task_summary: str,
    assistant_excerpt: str,
    user_reply: str,
    output_path: str,
    width: int = _DEFAULT_WIDTH,
    font_size: int = _DEFAULT_FONT_SIZE,
) -> list[TextContent | Image]:
    """Save and return a receipt containing task, assistant, and user text.

    A ``.png`` output path selects PNG; every other suffix produces SVG. The
    asset is written to disk and returned inline. The first content block is
    compact JSON metadata with ``output_path`` and ``format``; the second is
    SVG text or PNG image content.

    Args:
        task_summary: Task text shown on the receipt.
        assistant_excerpt: Assistant text shown on the receipt.
        user_reply: User text shown on the receipt.
        output_path: Destination path; ``.png`` selects PNG, otherwise SVG.
        width: Output width in pixels.
        font_size: Text size in pixels.

    Returns:
        Metadata text followed by the inline SVG or PNG content.

    Raises:
        ToolError: If the file cannot be written.
    """

    def _render() -> list[TextContent | Image]:
        try:
            return _render_card(
                task_summary, assistant_excerpt, user_reply, output_path, width=width, font_size=font_size
            )
        except OSError as exc:
            raise ToolError(f"Failed to write card to {output_path}: {exc}") from exc

    return await asyncio.to_thread(_render)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def scan_transcripts(
    glob_path: str, context_window: int = _DEFAULT_CONTEXT_WINDOW, offset: int = 0, limit: int = 100
) -> dict[str, Any]:
    """Return paginated user messages with preceding conversation context.

    Matches Claude or Codex JSONL files, then returns genuine user messages for
    caller-side classification. Each message contains ``file``, raw zero-based
    ``line_index``, ``uuid``, ``timestamp``, ``session_id``, ``text``, and
    preceding visible ``context``. ``total`` is computed before pagination.

    Args:
        glob_path: Session file or glob, such as
            ``~/.claude/projects/-my-project/*.jsonl`` or
            ``~/.codex/sessions/2026/09/**/rollout-*.jsonl``.
        context_window: Maximum preceding visible messages per result.
        offset: Number of matched user messages to skip.
        limit: Maximum matched user messages to return.

    Returns:
        ``messages``, pre-pagination ``total``, ``offset``, ``limit``, and
        ``files_scanned``.

    Raises:
        ToolError: If no files match or a matched session cannot be read.
    """

    def _scan() -> dict[str, Any]:
        messages, total, files_scanned = _query_user_messages(glob_path, context_window, offset, limit)

        return {"messages": messages, "total": total, "offset": offset, "limit": limit, "files_scanned": files_scanned}

    return await asyncio.to_thread(_scan)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_scenario(file: str, line_index: int, context_window: int = _DEFAULT_CONTEXT_WINDOW) -> dict[str, Any]:
    """Return one message and its preceding conversation for reconstruction.

    ``line_index`` is the raw zero-based JSONL line retained by extraction and
    scan results. Context contains visible user and assistant messages only.
    The response identifies the session and target role, text, UUID, timestamp,
    and ordered preceding context.

    Args:
        file: Claude or Codex session JSONL file.
        line_index: Raw zero-based line containing the target message.
        context_window: Maximum preceding visible messages to return.

    Returns:
        ``file``, ``line_index``, ``type``, ``text``, ``uuid``, ``timestamp``,
        ``session_id``, and ordered preceding ``context``.

    Raises:
        ToolError: If the session cannot be read or the line is not a visible message.
    """

    def _query() -> dict[str, Any]:
        resolved = _resolve_path(file)
        transcript = read_session(resolved)
        message = _message_at_line(transcript, line_index, resolved)
        context = _context_messages(transcript, line_index, context_window)

        return {
            "file": resolved,
            "line_index": line_index,
            "type": message.role,
            "text": message.text,
            "uuid": message.uuid,
            "timestamp": message.timestamp,
            "session_id": transcript.session_id,
            "context": context,
        }

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def generate_social_post(
    file: str, line_index: int, context_window: int = _DEFAULT_CONTEXT_WINDOW
) -> dict[str, Any]:
    """Create provider-tagged social post copy from one user message.

    The target text is inserted verbatim and is not posted anywhere. The result
    includes a privacy reminder so the caller can review identifying details
    with the user before sharing. Claude sessions receive ``#ClaudeCode``;
    Codex sessions receive ``#Codex``. The response contains ``post``,
    ``hashtags``, and ``privacy_reminder``.

    Args:
        file: Claude or Codex session JSONL file.
        line_index: Raw zero-based line containing a user message.
        context_window: Accepted for interface consistency; the post currently
            uses only the target message.

    Returns:
        ``post``, provider-aware ``hashtags``, and ``privacy_reminder``.

    Raises:
        ToolError: If the session cannot be read or the line is not a user message.
    """

    def _generate() -> dict[str, Any]:
        resolved = _resolve_path(file)
        transcript = read_session(resolved)
        message = _message_at_line(transcript, line_index, resolved)
        if message.role != "user":
            raise ToolError(f"line_index {line_index} is not a user message in {resolved}")
        text = message.text

        provider_hashtag = "#Codex" if transcript.provider == "codex" else "#ClaudeCode"
        hashtags = ["#AIFrustration", "#RTFP", provider_hashtag]
        post_text = f'\U0001f525 RTFP — Read The Fucking Prompt\n\nWhat the user said: "{text}"\n\n{" ".join(hashtags)}'

        return {
            "post": post_text,
            "hashtags": hashtags,
            "privacy_reminder": (
                "Review before sharing: this content may contain personal, business, or identifying details. "
                "Ask the user to confirm, or offer to replace specific details with mock placeholders like "
                "[Company], [Project], [Colleague], [Tool]."
            ),
        }

    return await asyncio.to_thread(_generate)


if __name__ == "__main__":
    mcp.run()
