# Rich Table Best Practices

Prevents wrapping issues when Rich tables are printed to terminals or non-TTY outputs.

## Required Imports

```python
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table
```

## Table Width Measurement

Without this pattern, Rich wraps tables to terminal width (default 80 when no TTY), hiding data.

```python
def _get_table_width(self, table: Table) -> int:
    """Get the natural width of a table using a temporary wide console.

    Args:
        table: The Rich table to measure

    Returns:
        The width in characters needed to display the table
    """
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
# no_wrap=True on columns that must not wrap (device names, IDs)
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

## Settings Rationale

- `box.MINIMAL_DOUBLE_HEAD` — clean professional look, consistent across tools
- `no_wrap=True` on columns — prevents text wrapping within critical columns
- Table width measurement — ensures table uses exactly the space it needs
- `crop=False` — allows table to exceed terminal width if necessary
- `overflow="ignore"` — prevents Rich from trying to wrap overflowing content
- `soft_wrap=True` — allows graceful handling at terminal boundaries
