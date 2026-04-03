#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer",
#   "rich",
# ]
# ///
"""MCP tool context contribution report.

Reads hook-written JSONL logs and answers: which MCP tool calls
are the biggest context contributors?

Use ccusage (https://github.com/ryoppippi/ccusage) for session/daily/monthly
cost reporting from Claude Code's native logs — that is out of scope here.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from io import TextIOWrapper
from pathlib import Path

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Report MCP tool context contribution from token-tracking logs.")
console = Console()

LOG_DIR = Path(__file__).parent.parent / ".claude" / "token-tracking"


def _fmt_num(n: float) -> str:
    return f"{n:,.0f}"


def _load_records(jsonl_files: list[Path], since: str, tool_prefix: str) -> tuple[list[dict], int]:
    """Parse JSONL files and apply filters.

    Returns:
        Tuple of (matching records list, count of skipped malformed lines).
    """
    records: list[dict] = []
    skipped = 0
    for path in sorted(jsonl_files):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                skipped += 1
                console.print(f"[dim]Warning: skipping malformed line {path.name}:{lineno}[/dim]")
                continue
            if since and rec.get("ts", "") < since:
                continue
            if tool_prefix and not rec.get("tool", "").startswith(tool_prefix):
                continue
            records.append(rec)
    return records, skipped


def _summary_line(records: list[dict]) -> None:
    total_calls = len(records)
    total_tokens = sum(r.get("response_tokens_est", 0) for r in records)
    dates = {r.get("ts", "")[:10] for r in records if r.get("ts")}
    day_count = len(dates)
    console.print(
        f"[bold]{_fmt_num(total_calls)} tool calls[/bold] logged across "
        f"[bold]{day_count}[/bold] day(s), "
        f"total est. [bold yellow]{_fmt_num(total_tokens)}[/bold yellow] tokens from MCP responses"
    )


def _render_tool_contribution(records: list[dict]) -> None:
    stats: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens": 0, "max": 0})
    for rec in records:
        t = rec.get("tool", "<unknown>")
        tokens = rec.get("response_tokens_est", 0)
        stats[t]["calls"] += 1
        stats[t]["tokens"] += tokens
        stats[t]["max"] = max(stats[t]["max"], tokens)

    sorted_tools = sorted(stats.items(), key=lambda x: x[1]["tokens"], reverse=True)

    tbl = Table(title="MCP Tool Context Contribution", show_lines=False)
    tbl.add_column("Tool", style="cyan", no_wrap=False)
    tbl.add_column("Calls", justify="right")
    tbl.add_column("Total Est. Tokens", justify="right", style="bold yellow")
    tbl.add_column("Avg Tokens/Call", justify="right")
    tbl.add_column("Max Single Call", justify="right", style="red")

    for tool_name, s in sorted_tools:
        calls = s["calls"]
        tbl.add_row(
            tool_name, _fmt_num(calls), _fmt_num(s["tokens"]), _fmt_num(s["tokens"] / calls), _fmt_num(s["max"])
        )
    console.print(tbl)


def _render_top_calls(records: list[dict], top: int) -> None:
    sorted_records = sorted(records, key=lambda r: r.get("response_tokens_est", 0), reverse=True)

    tbl = Table(title=f"Top {top} Largest Single Calls", show_lines=False)
    tbl.add_column("Timestamp", style="dim")
    tbl.add_column("Tool", style="cyan", no_wrap=False)
    tbl.add_column("Session", style="dim")
    tbl.add_column("Est. Tokens", justify="right", style="bold yellow")

    for rec in sorted_records[:top]:
        tbl.add_row(
            rec.get("ts", ""),
            rec.get("tool", "<unknown>"),
            rec.get("session_id", ""),
            _fmt_num(rec.get("response_tokens_est", 0)),
        )
    console.print(tbl)


@app.command()
def report(
    since: str = typer.Option("", help="Filter to calls on or after this date (YYYY-MM-DD). Default: all dates."),
    top: int = typer.Option(10, help="Number of largest single calls to show."),
    tool: str = typer.Option("", help="Filter to a specific tool prefix (e.g., mcp__plugin_dh_sam)."),
) -> None:
    """Report which MCP tool calls are the biggest context contributors."""
    if not LOG_DIR.exists():
        console.print(f"[yellow]Log directory does not exist yet: {LOG_DIR}[/yellow]")
        raise typer.Exit(0)

    jsonl_files = list(LOG_DIR.glob("*.jsonl"))
    if not jsonl_files:
        console.print("[yellow]No JSONL log files found in log directory.[/yellow]")
        raise typer.Exit(0)

    records, skipped = _load_records(jsonl_files, since, tool)

    if skipped:
        console.print(f"[yellow]Skipped {skipped} malformed line(s).[/yellow]")

    if not records:
        console.print("[bold]No data matched the given filters.[/bold]")
        raise typer.Exit(0)

    _summary_line(records)
    _render_tool_contribution(records)
    _render_top_calls(records, top)


if __name__ == "__main__":
    app()
