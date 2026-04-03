# Typer and Rich CLI Examples

This directory contains executable examples demonstrating solutions to common problems when building Python CLI applications with Typer and Rich.

## Available Examples

| Script                                                           | Problem Solved                                       | Key Technique                                         |
| ---------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| [console_no_wrap_example.py](./console_no_wrap_example.py)       | Rich Console wraps text at 80 chars in CI/non-TTY    | Use `crop=False, overflow="ignore"` on print calls    |
| [console_containers_no_wrap.py](./console_containers_no_wrap.py) | Panels/Tables wrap long content even with crop=False | Use `get_rendered_width()` helper + dedicated Console |

## Quick Start

All scripts use PEP 723 inline script metadata and can be run directly:

```bash
# Run directly (uv handles dependencies automatically)
./console_no_wrap_example.py

# Or explicitly with uv
uv run console_no_wrap_example.py
```

## Problem 1: Rich Console Text Wrapping in CI

### The Problem

Rich Console wraps text at default width (80 chars in non-TTY environments like CI), breaking:

-   URLs in log output
-   Long command strings
-   Stack traces
-   Structured log parsing

### Why This Matters

**In non-interactive environments (CI, logs, automation), output is consumed by machines, not humans:**

-   **Log parsing**: Tools like grep/awk/sed expect data on single lines - wrapping breaks patterns
-   **URLs**: Wrapped URLs become invalid - can't click, copy-paste, or process with tools
-   **Structured data**: JSON/CSV output splits across lines - breaks parsers and data processing
-   **Commands**: Wrapped command strings can't be copy-pasted to execute
-   **Error investigation**: Stack traces and file paths fragment across lines - harder to trace issues

**In interactive TTY (terminal), wrapping is good** - optimizes for human reading at terminal width.

**The solution must detect context and apply different behavior:**

-   **TTY (interactive)**: Use terminal width, wrap for human readability
-   **Non-TTY (CI/logs)**: Never wrap, optimize for machine parsing

### The Solution

Use `crop=False` + `overflow="ignore"` on `console.print()` calls:

```python
from rich.console import Console

console = Console()

# For text that should never wrap (URLs, commands, paths)
console.print(long_url, crop=False, overflow="ignore")

# For normal text that can wrap
console.print(normal_text)
```

### Example Script

[console_no_wrap_example.py](./console_no_wrap_example.py) demonstrates:

-   The problem (default wrapping behavior)
-   The solution (using crop=False + overflow="ignore")
-   Usage patterns for different text types

## Problem 2: Rich Containers (Panel/Table) Wrapping Content

### The Problem

Rich containers like `Panel` and `Table` wrap content internally even when using `crop=False, overflow="ignore"` on the print call. This is because:

-   Containers calculate their own internal layout
-   Console width (default 80 in non-TTY) constrains container rendering
-   Content wraps inside the container before `crop=False` can prevent it

### The Solution

Use a helper function to measure the actual rendered width, then apply width differently for Panel vs Table:

```python
from rich.console import Console, RenderableType
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table

def get_rendered_width(renderable: RenderableType) -> int:
    """Get actual rendered width of any Rich renderable.

    Handles color codes, Unicode, styling, padding, and borders.
    Works with Panel, Table, or any Rich container.
    """
    temp_console = Console(width=99999)
    measurement = Measurement.get(temp_console, temp_console.options, renderable)
    return int(measurement.maximum)

console = Console()

# Panel: Set Console width (Panel fills Console width)
panel = Panel(long_content)
panel_width = get_rendered_width(panel)
console.width = panel_width  # Set Console width, NOT panel.width
console.print(panel, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)

# Table: Set Table width (Table controls its own width)
table = Table()
table.add_column("Type", style="cyan", no_wrap=True)
table.add_column("Value", style="green", no_wrap=True)
table.add_row("Data", long_content)
table.width = get_rendered_width(table)  # Set Table width
console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
```

### Example Script

[console_containers_no_wrap.py](./console_containers_no_wrap.py) demonstrates:

-   Default Panel/Table wrapping behavior
-   Why `crop=False` alone doesn't work for containers
-   The `get_rendered_width()` helper function
-   Complete working examples for both Panel and Table
-   Comparison of different approaches

## When to Use Each Technique

**Use `crop=False, overflow="ignore"` for:**

-   Plain text output
-   URLs, file paths, commands that must stay on single lines
-   Text that doesn't use Rich containers

**Use `get_rendered_width()` + set width on container for:**

-   Panel with long content
-   Table with long cell values
-   Any Rich container that wraps content
-   Structured output that must preserve exact formatting

## Related Documentation

-   [Rich Console Documentation](https://rich.readthedocs.io/en/stable/console.html)
-   [Rich Panel Documentation](https://rich.readthedocs.io/en/stable/panel.html)
-   [Rich Table Documentation](https://rich.readthedocs.io/en/stable/tables.html)
-   [Typer Documentation](https://typer.tiangolo.com/)
