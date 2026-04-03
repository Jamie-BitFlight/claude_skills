# Rich Table Best Practices

Apply these settings when printing Rich tables to non-TTY outputs (piped, CI, Claude Code Bash tool) to prevent silent data loss.

## Required Imports

```python
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table
```

## Table Width Measurement

Use when the table will be printed in a non-TTY context. Without this, `Measurement.get()` caps measured width to `console.width` (default 80 in non-TTY), hiding content.

```python
def _get_table_width(self, table: Table) -> int:
    """Measure natural table width without the 80-column cap."""
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)
```

## Table Creation and Print

```python
table = Table(
    title=":electric_plug: Device Status",
    box=box.MINIMAL_DOUBLE_HEAD,
    title_style="bold blue"
)
table.add_column("Device", style="cyan", no_wrap=True)
table.add_column("Status", justify="center")

table_width = self._get_table_width(table)
table.width = table_width

console.print(
    table,
    crop=False,
    overflow="ignore",
    no_wrap=True,
    soft_wrap=True,
)
```

## When to Use Each Setting

- `box.MINIMAL_DOUBLE_HEAD` — use when output will be consumed by LLMs or piped. No left/right borders avoids whitespace padding that inflates token count.
- `no_wrap=True` on columns — use on columns containing identifiers, paths, or data that loses meaning when split across lines.
- `soft_wrap=True` — use on all non-TTY `console.print()` calls. Compound flag that sets `no_wrap=True`, `overflow="ignore"`, and `crop=False` together.
- `crop=False` — use when table may exceed 80 columns. Default `crop=True` hard-cuts all characters past `console.width` (80 in non-TTY).
- `overflow="ignore"` — use when any cell content must appear in full. Default behavior truncates or adds ellipsis.
- `soft_wrap=True` makes `crop=False` and `overflow="ignore"` redundant, but keeping them explicit documents intent for readers who don't know `soft_wrap` internals.
