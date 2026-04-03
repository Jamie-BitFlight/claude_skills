#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.0.0",
# ]
# ///
"""Rich containers (Panel, Table) behavior with long content in non-TTY environments."""

from __future__ import annotations

from rich.console import Console, RenderableType
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table


def get_rendered_width(renderable: RenderableType) -> int:
    """Get actual rendered width of any Rich renderable.

    Handles color codes, Unicode, styling, padding, and borders.
    Works with Panel, Table, or any Rich container.

    Returns:
        The maximum rendered width in characters.
    """
    temp_console = Console(width=999999)
    measurement = Measurement.get(temp_console, temp_console.options, renderable)
    return int(measurement.maximum)


long_url = (
    "https://raw.githubusercontent.com/python/cpython/main/Lib/asyncio/base_events.py"
    "#L1000-L1100?ref=docs-example&utm_source=rich-demo&utm_medium=terminal"
    "&utm_campaign=long-url-wrapping-behavior-test"
)
long_command = "[bold cyan]:sparkles: v3.13.0 Release Highlights :sparkles:[/bold cyan] New JIT optimizations, faster startup, improved error messages, richer tracebacks, better asyncio diagnostics, enhanced typing features, smoother virtualenv workflows, and a refined standard library experience for developers everywhere.\n[green]:rocket: Performance & Reliability :rocket:[/green] Lower latency event loops, smarter garbage collection heuristics, adaptive I/O backpressure, fine-tuned file system operations, reduced memory fragmentation, and sturdier cross-platform behavior in cloud-native deployments.\n[magenta]:hammer_and_wrench: Developer Experience :hammer_and_wrench:[/magenta] More precise type hints, clearer deprecation warnings, friendlier REPL niceties, first-class debugging hooks, expanded `typing` utilities, and streamlined packaging stories for modern Python projects of all sizes.\n[yellow]:shield: Security & Ecosystem :shield:[/yellow] Hardened TLS defaults, safer subprocess handling, improved sandboxing hooks, more robust hashing algorithms, curated secure defaults across modules, and deeper ecosystem integration for auditing, scanning, and compliance workflows."

console = Console()

# BROKEN EXAMPLES AND ANTI-PATTERNS

print("=" * 80)
print("Panel with default settings")
print("=" * 80)
panel = Panel(f"URL: {long_url}\nCommand: {long_command}")
console.print(panel)

print("\n" + "=" * 80)
print("Panel with crop=False, overflow='ignore' on print")
print("=" * 80)
console.print(panel, crop=False, overflow="ignore")

print("\n" + "=" * 80)
print("Panel with expand=False and measured width")
print("=" * 80)
# Avoid doing this, where you set the console width for all output to a wide width,
# It will cause output that is 'extended' to fit to the console width,
# which is not what you want.
panel_content = f"URL: {long_url}\nCommand: {long_command}"
panel_measured = Panel(panel_content, expand=False)
temp_console = Console(width=99999)
measurement = Measurement.get(temp_console, temp_console.options, panel_measured)
panel_measured.width = int(measurement.maximum)
console.print(panel_measured, crop=False, overflow="ignore")

print("\n" + "=" * 80)
print("Table with default settings")
print("=" * 80)
table = Table()
table.add_column("Type", style="cyan")
table.add_column("Value", style="green")
table.add_row("URL", long_url)
table.add_row("Command", long_command)
console.print(table)

print("\n" + "=" * 80)
print("Table with no_wrap=True on columns")
print("=" * 80)
table_nowrap = Table()
table_nowrap.add_column("Type", style="cyan", no_wrap=True)
table_nowrap.add_column("Value", style="green", no_wrap=True)
table_nowrap.add_row("URL", long_url)
table_nowrap.add_row("Command", long_command)
console.print(table_nowrap, crop=False, overflow="ignore")

# WORKING EXAMPLES THAT DO WHAT IS EXPECTED

print("\n" + "=" * 80)
print("Panel that works: Use get_rendered_width() helper")
print("=" * 80)
# Panels fill the space up to the size of the Console,
# to to make a Panel that doesn't wrap,
# we need to set the width of the Console to the rendered panel width
content_lines = f"URL: {long_url}\n{long_command}"
panel_measured = Panel(content_lines)
panel_width = get_rendered_width(panel_measured)

console.width = panel_width
console.print(panel_measured, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)

print("\n" + "=" * 80)
print("Table that works: Use get_rendered_width() helper")
print("=" * 80)
# Tables are bossy and will display at their own width if set,
# regardless of the console width. So we need to measure the table width
# and set the width of the table to the measured width.
table_measured = Table()
table_measured.add_column("Type", style="cyan", no_wrap=True)
table_measured.add_column("Value", style="green", no_wrap=True)
table_measured.add_row("URL", long_url)
table_measured.add_row("Command", long_command)
# set table width to the measured width
table_measured.width = get_rendered_width(table_measured)
console.print(table_measured, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)

print("\n" + "=" * 80)
print("Plain text with crop=False, overflow='ignore'")
print("=" * 80)
# Plain text doesn't have a width, so we can just print it directly,
# as long as we set crop=False and overflow="ignore"
console.print(f"URL: {long_url}", crop=False, overflow="ignore")
console.print(f"Command: {long_command}", crop=False, overflow="ignore")

print("\n" + "=" * 80)
print("Table with matching Panel summary: Same width for both")
print("=" * 80)
# Create table with data
result_table = Table()
result_table.add_column("Type", style="cyan", no_wrap=True)
result_table.add_column("Value", style="green", no_wrap=True)
result_table.add_row("URL", long_url)
result_table.add_row("Command", long_command)

# Measure table width and set it
table_width = get_rendered_width(result_table)
result_table.width = table_width

# Create panel summary with same width
summary_text = "[bold]Summary:[/bold] Processed 2 items with no errors"
summary_panel = Panel(summary_text, title="Results", border_style="green")
# Panel needs Console width set to match table
console.width = table_width

# Print both - they'll have matching widths
console.print(result_table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
console.print(summary_panel, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
