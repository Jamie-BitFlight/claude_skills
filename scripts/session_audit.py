#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "rich>=14.0.0",
# ]
# ///
"""Claude Code session JSONL audit tool.

Reads raw session transcripts from ~/.claude/projects/<project-key>/*.jsonl
and reports hook injection noise, MCP tool response sizes, duplicate calls,
and loop patterns. Complementary to token_usage_report.py which reads
hook-written token-tracking logs.

Usage:
    uv run scripts/session_audit.py project <path>
    uv run scripts/session_audit.py session <session-id-or-file>
    uv run scripts/session_audit.py message <session-file> <record-index>
    uv run scripts/session_audit.py top-tools <project-path> [--days 3]
    uv run scripts/session_audit.py duplicates <project-path> [--min-waste 1000]
"""

from __future__ import annotations

import hashlib
import json
import operator
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="session-audit",
    help="Claude Code session JSONL audit tool -- progressive disclosure from project to message level.",
    no_args_is_help=True,
)
console = Console()

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Token cost rates per million tokens (Sonnet 4.6, 2026-03-24)
_COST_INPUT_PER_M = 3.00
_COST_OUTPUT_PER_M = 15.00
_COST_CACHE_CREATE_PER_M = 3.75
_COST_CACHE_READ_PER_M = 0.30

# Size formatting thresholds
_MEGA = 1_000_000
_KILO = 1_000

# Tight-loop detection defaults
_LOOP_WINDOW = 50
_LOOP_MIN_CALLS = 3

# Display truncation lengths
_INPUT_DISPLAY_LEN = 60
_INPUT_DISPLAY_LEN_SHORT = 55
_SESSION_ID_SHORT = 8
_INDICES_DISPLAY_LIMIT = 8

# Duplicate group minimum size
_DUP_MIN_GROUP = 2


# ─────────────────────────── helpers ──────────────────────────────────────────


def _fmt_num(n: float) -> str:
    """Format a number with thousands separator and no decimals.

    Returns:
        Formatted string like "1,234".
    """
    return f"{n:,.0f}"


def _fmt_size(chars: int) -> str:
    """Format a character count with M/K suffix for readability.

    Returns:
        Formatted string like "1.2M", "345.6K", or "789".
    """
    if chars >= _MEGA:
        return f"{chars / _MEGA:.1f}M"
    if chars >= _KILO:
        return f"{chars / _KILO:.1f}K"
    return str(chars)


def _tool_result_size(content: Any) -> int:  # noqa: ANN401
    """Compute character size of a tool_result content value.

    Returns:
        Character count: len(content) for strings, len(json.dumps(content)) otherwise.
    """
    if isinstance(content, str):
        return len(content)
    return len(json.dumps(content))


def _input_hash(tool_name: str, input_val: Any) -> str:  # noqa: ANN401
    """Canonical hash for duplicate detection using (tool_name, sorted input json).

    Returns:
        MD5 hex digest string identifying this tool_name + input combination.
    """
    if isinstance(input_val, dict):
        canonical = json.dumps(dict(sorted(input_val.items())), sort_keys=True)
    else:
        canonical = json.dumps(input_val)
    key = f"{tool_name}:{canonical}"
    return hashlib.md5(key.encode()).hexdigest()  # noqa: S324


def _resolve_project_dir(path_arg: str) -> Path:
    """Resolve a project path argument to an absolute directory.

    Args:
        path_arg: Either a project key (e.g. -home-user-repos-myproject),
                  a full path to ~/.claude/projects/<key>/, or any directory
                  path to a project root (which gets encoded).

    Returns:
        Absolute path to the project directory under ~/.claude/projects/.

    Raises:
        typer.Exit: If the resolved directory does not exist.
    """
    candidate = Path(path_arg).expanduser()
    if candidate.exists() and candidate.is_dir():
        return candidate

    direct = CLAUDE_PROJECTS_DIR / path_arg
    if direct.exists() and direct.is_dir():
        return direct

    encoded = path_arg.replace("/", "-").replace("\\", "-").replace(":", "-")
    encoded_path = CLAUDE_PROJECTS_DIR / encoded
    if encoded_path.exists() and encoded_path.is_dir():
        return encoded_path

    console.print(f"[red]Project directory not found:[/red] {path_arg}")
    console.print(f"Searched: {direct} and {encoded_path}")
    raise typer.Exit(1)


def _session_files(project_dir: Path, *, days: int | None = None) -> list[Path]:
    """Return main session JSONL files (excludes agent- prefixed subagent files).

    Args:
        project_dir: The project directory to search.
        days: If set, only return files modified within this many days.

    Returns:
        List of session JSONL paths sorted by mtime descending (newest first).
    """
    cutoff = datetime.now(UTC) - timedelta(days=days) if days else None
    files: list[Path] = []
    for p in project_dir.glob("*.jsonl"):
        if p.name.startswith("agent-"):
            continue
        if cutoff and datetime.fromtimestamp(p.stat().st_mtime, tz=UTC) < cutoff:
            continue
        files.append(p)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _load_records(session_file: Path) -> list[dict[str, Any]]:
    """Parse all JSONL records from a session file.

    Args:
        session_file: Path to the session .jsonl file.

    Returns:
        List of parsed record dicts (malformed lines are warned and skipped).
    """
    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(session_file.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError:
            console.print(f"[dim yellow]Warning: skipping malformed line {session_file.name}:{lineno}[/dim yellow]")
    return records


def _iter_content_items(records: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """Yield (record_index, content_item) for all content items across records.

    Args:
        records: Parsed JSONL records.

    Returns:
        List of (record_index, content_item_dict) tuples.
    """
    result: list[tuple[int, dict[str, Any]]] = []
    for idx, rec in enumerate(records):
        msg = rec.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        result.extend((idx, item) for item in content if isinstance(item, dict))
    return result


def _extract_tool_pairs(records: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], int, int]]:
    """Extract (tool_name, input, response_chars, result_record_index) for every tool pair.

    Uses the schema-verified pairing algorithm: tool_use.id == tool_result.tool_use_id.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        List of (tool_name, input_dict, response_chars, result_record_index) tuples.
    """
    pending: dict[str, tuple[str, dict[str, Any]]] = {}
    result: list[tuple[str, dict[str, Any], int, int]] = []

    for idx, item in _iter_content_items(records):
        itype = item.get("type")
        if itype == "tool_use":
            tool_id = item.get("id", "")
            tool_name = item.get("name", "<unknown>")
            tool_input = item.get("input") or {}
            if not isinstance(tool_input, dict):
                tool_input = {}
            pending[tool_id] = (tool_name, tool_input)
        elif itype == "tool_result":
            tool_use_id = item.get("tool_use_id", "")
            if tool_use_id in pending:
                name, inp = pending.pop(tool_use_id)
                raw_content = item.get("content", "")
                size = _tool_result_size(raw_content)
                result.append((name, inp, size, idx))
    return result


def _compute_tag_sizes(records: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Compute per-tag character size lists for hook injections.

    Args:
        records: Parsed JSONL records.

    Returns:
        Dict mapping tag_name to list of character counts for each occurrence.
    """
    tag_re = re.compile(r"^<([a-zA-Z][a-zA-Z0-9_-]*)")
    tag_sizes: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        if rec.get("type") != "user":
            continue
        for _idx, item in _iter_content_items([rec]):
            if item.get("type") != "text":
                continue
            text = item.get("text", "")
            if not text.strip().startswith("<"):
                continue
            m = tag_re.match(text.strip())
            if m:
                tag_sizes[m.group(1)].append(len(text))
    return dict(tag_sizes)


def _extract_hook_injections(records: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Extract hook injection tags from user records.

    Hook injections are user records whose text content starts with '<'.

    Args:
        records: Parsed JSONL records.

    Returns:
        Dict of {tag_name: [record_indices]} for all detected hook injections.
    """
    tag_re = re.compile(r"^<([a-zA-Z][a-zA-Z0-9_-]*)")
    injections: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        if rec.get("type") != "user":
            continue
        for _rec_idx, item in _iter_content_items([rec]):
            if item.get("type") == "text":
                text = item.get("text", "")
                if text and text.strip().startswith("<"):
                    m = tag_re.match(text.strip())
                    if m:
                        injections[m.group(1)].append(idx)
    return dict(injections)


def _extract_result_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the result record (last type=result in the session), or None.

    Args:
        records: Parsed JSONL records.

    Returns:
        The result record dict, or None if not present.
    """
    for rec in reversed(records):
        if rec.get("type") == "result":
            return rec
    return None


def _sum_assistant_usage(records: list[dict[str, Any]]) -> dict[str, int]:
    """Sum token usage across all assistant records.

    Args:
        records: Parsed JSONL records.

    Returns:
        Dict with keys input_tokens, output_tokens, cache_creation_input_tokens,
        cache_read_input_tokens — each summed across all assistant turns.
    """
    totals: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        usage = rec.get("message", {}).get("usage") or {}
        if not isinstance(usage, dict):
            continue
        for key in totals:
            totals[key] += int(usage.get(key, 0) or 0)
    return totals


def _estimate_cost_from_usage(usage: dict[str, int]) -> float:
    """Compute estimated cost in USD from a usage dict using per-million-token rates.

    Args:
        usage: Dict with input_tokens, output_tokens, cache_creation_input_tokens,
               cache_read_input_tokens keys.

    Returns:
        Estimated cost in USD.
    """
    return (
        usage.get("input_tokens", 0) / 1_000_000 * _COST_INPUT_PER_M
        + usage.get("output_tokens", 0) / 1_000_000 * _COST_OUTPUT_PER_M
        + usage.get("cache_creation_input_tokens", 0) / 1_000_000 * _COST_CACHE_CREATE_PER_M
        + usage.get("cache_read_input_tokens", 0) / 1_000_000 * _COST_CACHE_READ_PER_M
    )


def _find_duplicates(pairs: list[tuple[str, dict[str, Any], int, int]]) -> list[tuple[str, str, list[int], int]]:
    """Find exact-duplicate tool calls (same tool_name + same input).

    Args:
        pairs: Output of _extract_tool_pairs.

    Returns:
        List of (tool_name, input_repr, record_indices, wasted_chars) for groups
        with 2+ calls, sorted by wasted_chars descending.
    """
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    hash_meta: dict[str, tuple[str, str]] = {}

    for tool_name, inp, size, rec_idx in pairs:
        h = _input_hash(tool_name, inp)
        groups[h].append((rec_idx, size))
        if h not in hash_meta:
            inp_repr = json.dumps(inp, sort_keys=True)
            hash_meta[h] = (tool_name, inp_repr)

    result: list[tuple[str, str, list[int], int]] = []
    for h, calls in groups.items():
        if len(calls) < _DUP_MIN_GROUP:
            continue
        tool_name, inp_repr = hash_meta[h]
        indices = [c[0] for c in calls]
        wasted = sum(c[1] for c in calls[1:])
        result.append((tool_name, inp_repr, indices, wasted))
    return sorted(result, key=operator.itemgetter(3), reverse=True)


def _find_tight_loops(
    pairs: list[tuple[str, dict[str, Any], int, int]], window: int = _LOOP_WINDOW, min_calls: int = _LOOP_MIN_CALLS
) -> list[tuple[str, str, list[int]]]:
    """Detect tool calls that repeat with identical input within a record window.

    Args:
        pairs: Output of _extract_tool_pairs.
        window: Maximum record span between first and last call in group.
        min_calls: Minimum call count to flag as a loop.

    Returns:
        List of (tool_name, input_repr, record_indices) for detected loops.
    """
    groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    hash_meta: dict[str, tuple[str, str]] = {}

    for tool_name, inp, size, rec_idx in pairs:
        h = _input_hash(tool_name, inp)
        groups[h].append((rec_idx, size))
        if h not in hash_meta:
            inp_repr = json.dumps(inp, sort_keys=True)
            hash_meta[h] = (tool_name, inp_repr)

    loops: list[tuple[str, str, list[int]]] = []
    for h, calls in groups.items():
        if len(calls) < min_calls:
            continue
        indices = [c[0] for c in calls]
        span = max(indices) - min(indices)
        if span <= window:
            tool_name, inp_repr = hash_meta[h]
            loops.append((tool_name, inp_repr, indices))
    return loops


def _top_hook_tag(records: list[dict[str, Any]]) -> tuple[str, int]:
    """Return the top hook injection tag by total character count.

    Args:
        records: Parsed JSONL records.

    Returns:
        Tuple of (tag_name, total_chars). Both empty/zero if no injections found.
    """
    tag_sizes = _compute_tag_sizes(records)
    if not tag_sizes:
        return "", 0
    tag_totals = {t: sum(s) for t, s in tag_sizes.items()}
    top_tag = max(tag_totals, key=lambda k: tag_totals[k])
    return top_tag, tag_totals[top_tag]


def _session_summary_row(session_file: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary stats for one session.

    Args:
        session_file: Path to the session JSONL file.
        records: Parsed records from that file.

    Returns:
        Dict with keys: session_id, date, size_bytes, turns, total_cost_usd,
        cost_is_estimated, usage, top_waste_tag, top_waste_chars, tool_pairs, injections.
        cost_is_estimated is True when cost was derived from per-turn usage (no result record).
    """
    result_rec = _extract_result_record(records)
    pairs = _extract_tool_pairs(records)
    injections = _extract_hook_injections(records)
    turns = sum(1 for r in records if r.get("type") == "assistant")
    top_tag, top_chars = _top_hook_tag(records)
    session_id = (records[0].get("sessionId", "") or session_file.stem) if records else session_file.stem
    mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=UTC)

    if result_rec is not None:
        total_cost = float(result_rec.get("total_cost_usd", 0.0) or 0.0)
        usage: dict[str, Any] = result_rec.get("usage", {}) or {}
        cost_is_estimated = False
    else:
        usage = _sum_assistant_usage(records)
        total_cost = _estimate_cost_from_usage(usage)
        cost_is_estimated = True

    return {
        "session_id": session_id,
        "date": mtime.strftime("%Y-%m-%d %H:%M"),
        "size_bytes": session_file.stat().st_size,
        "turns": turns,
        "total_cost_usd": total_cost,
        "cost_is_estimated": cost_is_estimated,
        "usage": usage,
        "top_waste_tag": top_tag,
        "top_waste_chars": top_chars,
        "tool_pairs": pairs,
        "injections": injections,
    }


def _build_tool_stats_table(sorted_tools: list[tuple[str, dict[str, Any]]], title: str, days_label: str = "") -> Table:
    """Build a Rich table for tool response size statistics.

    Args:
        sorted_tools: List of (tool_name, stats_dict) sorted by total descending.
        title: Table title.
        days_label: Optional label suffix appended to title.

    Returns:
        Populated Rich Table ready for console.print().
    """
    tbl = Table(title=f"{title}{days_label}", show_lines=False)
    tbl.add_column("Tool", style="cyan")
    tbl.add_column("Calls", justify="right")
    tbl.add_column("Avg Chars", justify="right")
    tbl.add_column("Max Chars", justify="right")
    tbl.add_column("Total Chars", justify="right", style="bold yellow")
    tbl.add_column("Est. Tokens", justify="right", style="dim")
    for tool_name, stats in sorted_tools:
        calls = stats["calls"]
        total = stats["total"]
        avg = total // calls
        tbl.add_row(
            tool_name,
            str(calls),
            _fmt_size(avg),
            _fmt_size(stats["max"]),
            _fmt_size(total),
            _fmt_size(total // 4) + " (est.)",
        )
    return tbl


def _render_session_hook_section(records: list[dict[str, Any]]) -> None:
    """Render the hook injections section for a session drill-down.

    Args:
        records: Parsed JSONL records.
    """
    tag_sizes = _compute_tag_sizes(records)
    inj_tbl = Table(title="Hook Injections (user records with XML tags)", show_lines=False)
    inj_tbl.add_column("Tag", style="cyan")
    inj_tbl.add_column("Count", justify="right")
    inj_tbl.add_column("Avg Chars", justify="right")
    inj_tbl.add_column("Total Chars", justify="right", style="bold yellow")

    if tag_sizes:
        total_inj_chars = 0
        for tag in sorted(tag_sizes, key=lambda t: sum(tag_sizes[t]), reverse=True):
            sizes = tag_sizes[tag]
            count = len(sizes)
            total = sum(sizes)
            avg = total // count
            total_inj_chars += total
            inj_tbl.add_row(tag, str(count), _fmt_size(avg), _fmt_size(total))
        console.print(inj_tbl)
        console.print(f"  [dim]Total injection chars: {_fmt_size(total_inj_chars)}[/dim]\n")
    else:
        console.print("[dim]No hook injections found.[/dim]\n")


def _render_session_mcp_section(pairs: list[tuple[str, dict[str, Any], int, int]]) -> None:
    """Render the MCP tool response sizes section.

    Args:
        pairs: Output of _extract_tool_pairs.
    """
    tool_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls": 0, "total": 0, "max": 0})
    for tool_name, _inp, size, _idx in pairs:
        tool_stats[tool_name]["calls"] += 1
        tool_stats[tool_name]["total"] += size
        tool_stats[tool_name]["max"] = max(tool_stats[tool_name]["max"], size)

    sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]["total"], reverse=True)
    if sorted_tools:
        tbl = _build_tool_stats_table(sorted_tools, "Tool Response Sizes (sorted by total chars)")
        console.print(tbl)
        console.print()
    else:
        console.print("[dim]No tool calls found.[/dim]\n")


def _render_session_dup_section(pairs: list[tuple[str, dict[str, Any], int, int]]) -> None:
    """Render the duplicate calls section.

    Args:
        pairs: Output of _extract_tool_pairs.
    """
    dups = _find_duplicates(pairs)
    dup_tbl = Table(title="Duplicate Tool Calls (exact input match)", show_lines=False)
    dup_tbl.add_column("Tool", style="cyan")
    dup_tbl.add_column("Input (truncated)", style="dim")
    dup_tbl.add_column("Calls", justify="right")
    dup_tbl.add_column("Record Indices")
    dup_tbl.add_column("Wasted Chars", justify="right", style="bold red")

    if dups:
        for tool_name, inp_repr, indices, wasted in dups:
            inp_display = inp_repr[:_INPUT_DISPLAY_LEN] + "..." if len(inp_repr) > _INPUT_DISPLAY_LEN else inp_repr
            indices_str = str(indices[:_INDICES_DISPLAY_LIMIT]) + (
                "..." if len(indices) > _INDICES_DISPLAY_LIMIT else ""
            )
            dup_tbl.add_row(tool_name, inp_display, str(len(indices)), indices_str, _fmt_size(wasted))
        console.print(dup_tbl)
        console.print()
    else:
        console.print("[dim]No exact-duplicate tool calls found.[/dim]\n")


def _render_session_loop_section(pairs: list[tuple[str, dict[str, Any], int, int]]) -> None:
    """Render the tight-loop detection section.

    Args:
        pairs: Output of _extract_tool_pairs.
    """
    loops = _find_tight_loops(pairs)
    if not loops:
        return
    loop_tbl = Table(title="Tight Loops (3+ identical calls within 50 records)", show_lines=False)
    loop_tbl.add_column("Tool", style="cyan")
    loop_tbl.add_column("Input (truncated)", style="dim")
    loop_tbl.add_column("Calls", justify="right")
    loop_tbl.add_column("Span (records)", justify="right")
    for tool_name, inp_repr, indices in loops:
        inp_display = inp_repr[:_INPUT_DISPLAY_LEN] + "..." if len(inp_repr) > _INPUT_DISPLAY_LEN else inp_repr
        span = max(indices) - min(indices)
        loop_tbl.add_row(tool_name, inp_display, str(len(indices)), str(span))
    console.print(loop_tbl)
    console.print()


def _render_session_cost_section(records: list[dict[str, Any]]) -> None:
    """Render the cost summary panel.

    When the session has a result record, cost is authoritative.
    When the session was interrupted (no result record), cost is estimated from
    per-turn assistant usage at current Sonnet 4.6 rates.

    Args:
        records: Parsed JSONL records (result record is extracted from these).
    """
    result_rec = _extract_result_record(records)

    if result_rec is not None:
        usage: dict[str, Any] = result_rec.get("usage", {}) or {}
        cost = float(result_rec.get("total_cost_usd", 0.0) or 0.0)
        cost_label = f"[bold yellow]${cost:.6f}[/bold yellow] USD"
        cost_source = "authoritative (result record)"
        extra_lines = [
            f"Turns: {result_rec.get('num_turns', '?')}",
            f"Duration: {result_rec.get('duration_ms', 0) / 1000:.1f}s",
        ]
    else:
        usage = _sum_assistant_usage(records)
        cost = _estimate_cost_from_usage(usage)
        cost_label = f"[bold yellow]~${cost:.6f}[/bold yellow] USD [dim](est.)[/dim]"
        cost_source = "estimated from per-turn usage (interrupted/abandoned session)"
        extra_lines = []

    lines = [
        f"Total cost: {cost_label}",
        f"Cost source: [dim]{cost_source}[/dim]",
        *extra_lines,
        f"Input tokens: {_fmt_num(usage.get('input_tokens', 0))}",
        f"Output tokens: {_fmt_num(usage.get('output_tokens', 0))}",
        f"Cache read tokens: {_fmt_num(usage.get('cache_read_input_tokens', 0))}",
        f"Cache write tokens: {_fmt_num(usage.get('cache_creation_input_tokens', 0))}",
    ]
    console.print(Panel("\n".join(lines), title="Cost Summary", expand=False))


def _find_paired_tool_result(
    records: list[dict[str, Any]], start_index: int, tool_use_id: str
) -> dict[str, Any] | None:
    """Search records after start_index for a tool_result matching tool_use_id.

    Args:
        records: All parsed JSONL records.
        start_index: Start searching after this record index.
        tool_use_id: The tool_use.id to match against tool_result.tool_use_id.

    Returns:
        The matching tool_result content item dict, or None if not found.
    """
    for rec in records[start_index + 1 :]:
        msg = rec.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for fi in content:
            if isinstance(fi, dict) and fi.get("type") == "tool_result" and fi.get("tool_use_id") == tool_use_id:
                return fi
    return None


def _resolve_session_file(session_arg: str, project_path: str) -> Path | None:
    """Resolve a session argument to a Path.

    Args:
        session_arg: Either a .jsonl file path or a session ID prefix.
        project_path: Optional project path to restrict search.

    Returns:
        Resolved Path, or None if not found.
    """
    candidate = Path(session_arg).expanduser()
    if candidate.exists() and candidate.suffix == ".jsonl":
        return candidate

    search_dirs: list[Path] = []
    if project_path:
        search_dirs.append(_resolve_project_dir(project_path))
    elif CLAUDE_PROJECTS_DIR.exists():
        search_dirs.extend(d for d in CLAUDE_PROJECTS_DIR.iterdir() if d.is_dir())

    for pdir in search_dirs:
        for sf in pdir.glob("*.jsonl"):
            if sf.name.startswith("agent-"):
                continue
            if sf.stem.startswith(session_arg):
                return sf
    return None


def _render_paired_tool_results(records: list[dict[str, Any]], record_index: int, rec: dict[str, Any]) -> None:
    """Render paired tool_result panels for all tool_use items in an assistant record.

    Args:
        records: All parsed JSONL records.
        record_index: The index of rec in records (used as search start).
        rec: The record to inspect for tool_use items.
    """
    msg = rec.get("message", {})
    if not isinstance(msg, dict):
        return
    content = msg.get("content", [])
    if not isinstance(content, list):
        return
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_use":
            continue
        tool_use_id = item.get("id", "")
        tool_name = item.get("name", "")
        paired = _find_paired_tool_result(records, record_index, tool_use_id)
        if paired:
            console.print(
                Panel(JSON(json.dumps(paired, indent=2)), title=f"Paired tool_result for [cyan]{tool_name}[/cyan]")
            )


# ─────────────────────────── commands ─────────────────────────────────────────


@app.command()
def project(
    path: Annotated[str, typer.Argument(help="Project key (e.g. -home-user-repos-myproject) or directory path.")],
) -> None:
    """Level 1: Project summary -- per-session table with cost, turns, and top waste.

    Shows all sessions in the project with size, turns, cost, and the top hook
    injection tag. Summary row shows top 3 MCP tools by total response volume and
    total duplicate call count.
    """
    project_dir = _resolve_project_dir(path)
    files = _session_files(project_dir)

    if not files:
        console.print(f"[yellow]No session files found in:[/yellow] {project_dir}")
        raise typer.Exit(0)

    console.print(f"\n[bold]Project:[/bold] {project_dir.name}")
    console.print(f"[dim]Sessions found: {len(files)}[/dim]\n")

    tbl = Table(title="Session Summary", show_lines=False, expand=True)
    tbl.add_column("Session ID", style="cyan", no_wrap=True, width=36)
    tbl.add_column("Date", style="dim", width=16)
    tbl.add_column("Size", justify="right", width=8)
    tbl.add_column("Turns", justify="right", width=6)
    tbl.add_column("Cost USD", justify="right", style="bold yellow", width=10)
    tbl.add_column("Top Hook Tag", style="dim", width=24)
    tbl.add_column("Hook Chars", justify="right", width=10)

    total_cost = 0.0
    total_dup_count = 0
    all_tool_totals: dict[str, int] = defaultdict(int)
    summaries: list[dict[str, Any]] = []

    for sf in files:
        records = _load_records(sf)
        row = _session_summary_row(sf, records)
        summaries.append(row)
        total_cost += row["total_cost_usd"]
        for tool_name, _inp, size, _idx in row["tool_pairs"]:
            all_tool_totals[tool_name] += size
        dups = _find_duplicates(row["tool_pairs"])
        total_dup_count += sum(len(d[2]) - 1 for d in dups)

    for row in summaries:
        sid = row["session_id"]
        short_id = sid[:_SESSION_ID_SHORT] + "..." if len(sid) > _SESSION_ID_SHORT else sid
        cost = row["total_cost_usd"]
        cost_str = (f"~${cost:.4f}" if row["cost_is_estimated"] else f"${cost:.4f}") if cost else "--"
        tbl.add_row(
            short_id,
            row["date"],
            _fmt_size(row["size_bytes"]),
            str(row["turns"]),
            cost_str,
            row["top_waste_tag"] or "--",
            _fmt_size(row["top_waste_chars"]) if row["top_waste_chars"] else "--",
        )

    console.print(tbl)
    console.print()

    top3 = sorted(all_tool_totals.items(), key=operator.itemgetter(1), reverse=True)[:3]
    top3_str = ", ".join(f"[cyan]{t}[/cyan] ({_fmt_size(s)} chars)" for t, s in top3)
    console.print(f"[bold]Total cost:[/bold] ${total_cost:.4f} USD")
    console.print(f"[bold]Duplicate tool calls (wasted):[/bold] {_fmt_num(total_dup_count)} extra calls")
    if top3_str:
        console.print(f"[bold]Top 3 tools by response volume:[/bold] {top3_str}")


@app.command()
def session(
    session_arg: Annotated[str, typer.Argument(help="Session ID (prefix or full UUID) or path to a .jsonl file.")],
    project_path: Annotated[
        str, typer.Option("--project", "-p", help="Project key or directory (used when resolving session by ID).")
    ] = "",
) -> None:
    """Level 2: Session drill-down -- hook injections, MCP sizes, duplicates, loops, cost.

    Pass a .jsonl file path directly, or a session ID (with --project if needed).
    Shows four sections: hook injections, MCP tool response sizes, duplicate calls,
    tight-loop detection, and token cost summary.
    """
    session_file = _resolve_session_file(session_arg, project_path)

    if not session_file or not session_file.exists():
        console.print(f"[red]Session not found:[/red] {session_arg}")
        raise typer.Exit(1)

    records = _load_records(session_file)
    if not records:
        console.print("[yellow]No records found in session file.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Session:[/bold] [cyan]{session_file.stem}[/cyan]")
    console.print(f"[dim]{session_file} -- {len(records)} records[/dim]\n")

    pairs = _extract_tool_pairs(records)
    _render_session_hook_section(records)
    _render_session_mcp_section(pairs)
    _render_session_dup_section(pairs)
    _render_session_loop_section(pairs)
    _render_session_cost_section(records)


@app.command()
def message(
    session_file: Annotated[Path, typer.Argument(help="Path to the session .jsonl file.")],
    record_index: Annotated[int, typer.Argument(help="Zero-based record index to inspect.")],
) -> None:
    """Level 3: Message drill-down -- pretty-print a specific record.

    For tool_use records, also shows the paired tool_result.
    """
    if not session_file.exists():
        console.print(f"[red]File not found:[/red] {session_file}")
        raise typer.Exit(1)

    records = _load_records(session_file)
    if record_index < 0 or record_index >= len(records):
        console.print(f"[red]Record index {record_index} out of range (0 to {len(records) - 1}).[/red]")
        raise typer.Exit(1)

    rec = records[record_index]
    console.print(Panel(JSON(json.dumps(rec, indent=2)), title=f"Record [{record_index}] -- type: {rec.get('type')}"))
    _render_paired_tool_results(records, record_index, rec)


@app.command()
def top_tools(
    path: Annotated[str, typer.Argument(help="Project key or directory path.")],
    days: Annotated[int, typer.Option("--days", "-d", help="Limit to sessions modified within N days.")] = 3,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum number of tools to display.")] = 20,
) -> None:
    """Aggregate top tools by total response volume across sessions.

    Reads all sessions in the project (filtered by --days) and ranks tools
    by total character volume of their responses.
    """
    project_dir = _resolve_project_dir(path)
    files = _session_files(project_dir, days=days)

    if not files:
        console.print(f"[yellow]No session files found (within {days} days) in:[/yellow] {project_dir}")
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Project:[/bold] {project_dir.name} -- scanning {len(files)} session(s) (last {days} days)\n"
    )

    all_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls": 0, "total": 0, "max": 0})
    for sf in files:
        records = _load_records(sf)
        for tool_name, _inp, size, _idx in _extract_tool_pairs(records):
            all_stats[tool_name]["calls"] += 1
            all_stats[tool_name]["total"] += size
            all_stats[tool_name]["max"] = max(all_stats[tool_name]["max"], size)

    sorted_tools = sorted(all_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:limit]
    tbl = _build_tool_stats_table(sorted_tools, f"Top {limit} Tools by Response Volume", f" (last {days} days)")
    console.print(tbl)


@app.command()
def duplicates(
    path: Annotated[str, typer.Argument(help="Project key or directory path.")],
    days: Annotated[int, typer.Option("--days", "-d", help="Limit to sessions modified within N days.")] = 3,
    min_waste: Annotated[
        int, typer.Option("--min-waste", "-w", help="Only show groups wasting at least N chars.")
    ] = 1000,
) -> None:
    """Show all duplicate tool call groups across sessions.

    Scans all sessions in the project, finds exact-duplicate calls (same tool,
    same input), and reports groups wasting more than --min-waste characters.
    """
    project_dir = _resolve_project_dir(path)
    files = _session_files(project_dir, days=days)

    if not files:
        console.print(f"[yellow]No session files found (within {days} days) in:[/yellow] {project_dir}")
        raise typer.Exit(0)

    console.print(
        f"\n[bold]Project:[/bold] {project_dir.name} -- scanning {len(files)} session(s) "
        f"(last {days} days, min waste: {_fmt_size(min_waste)} chars)\n"
    )

    tbl = Table(title="Duplicate Tool Calls Across Sessions", show_lines=False)
    tbl.add_column("Session", style="dim", width=10)
    tbl.add_column("Tool", style="cyan")
    tbl.add_column("Input (truncated)", style="dim")
    tbl.add_column("Calls", justify="right")
    tbl.add_column("Wasted Chars", justify="right", style="bold red")

    total_wasted = 0
    found = 0

    for sf in files:
        records = _load_records(sf)
        dups = _find_duplicates(_extract_tool_pairs(records))
        for tool_name, inp_repr, indices, wasted in dups:
            if wasted < min_waste:
                continue
            inp_display = (
                inp_repr[:_INPUT_DISPLAY_LEN_SHORT] + "..." if len(inp_repr) > _INPUT_DISPLAY_LEN_SHORT else inp_repr
            )
            tbl.add_row(sf.stem[:_SESSION_ID_SHORT], tool_name, inp_display, str(len(indices)), _fmt_size(wasted))
            total_wasted += wasted
            found += 1

    if found:
        console.print(tbl)
        console.print(
            f"\n[bold]Total wasted chars:[/bold] {_fmt_size(total_wasted)} (~{_fmt_size(total_wasted // 4)} est. tokens)"
        )
    else:
        console.print(f"[dim]No duplicate groups found wasting >= {_fmt_size(min_waste)} chars.[/dim]")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        console.print(
            Panel(
                "[bold]Claude Code Session Audit Tool[/bold]\n\n"
                "Commands:\n"
                "  [cyan]project[/cyan]    <path>                    Project-level summary\n"
                "  [cyan]session[/cyan]    <id-or-file>              Session drill-down\n"
                "  [cyan]message[/cyan]    <file> <index>            Single record inspection\n"
                "  [cyan]top-tools[/cyan]  <path> [--days 3]         Top tools by response volume\n"
                "  [cyan]duplicates[/cyan] <path> [--min-waste 1000] Duplicate calls across sessions\n\n"
                "Run with [bold]--help[/bold] for full usage.",
                title="session-audit",
                expand=False,
            )
        )
    app()
