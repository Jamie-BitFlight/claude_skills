# Rich Table Best Practices

Apply these settings when printing Rich tables to non-TTY outputs (piped, CI, Claude Code Bash tool) to prevent silent data loss.

## The Goal: Zero Data Loss

Rich table output in non-TTY contexts (CI logs, piped stdout, agent transcripts, LLM consumption) **must preserve every character of every cell**. The default behavior does not. Capping table width — whether via Rich's implicit 80-column non-TTY default or an explicit `min(measured, N)` ceiling — causes one of two silent data-loss modes:

1. **Wrapped continuation lines lose their left-hand context.** When a cell wraps, only the first line carries the row label, timestamp, or column header. Tools that parse output line-by-line (`grep`, `awk`, human eyes scrolling a log) see orphaned fragments with no way to associate them back to the row they belong to. Labels, timestamps, severities — all absent from every line after the first.
2. **Truncation with `…` destroys identifiers and descriptions.** When a column is `no_wrap` but too narrow for its content, Rich replaces the tail with an ellipsis. The truncated part — URL query strings, file paths, error messages, config tag names, test IDs — is **gone**. An operator reading the output cannot make decisions from `...asyncio…` or `Ty…`. The data needed for analysis does not exist in the output at all.

**There is no "pathological" width.** A 500-column table is the tool doing its job. The consumer of the output (terminal pager, log viewer, grep pipeline, LLM context window) is responsible for handling width — not the tool producing the diagnostic. Any cap added "for safety" re-introduces exactly the data loss the measurement pattern exists to eliminate. Do not cap measured widths. Do not write `min(measured, N)`.

## Required Imports

```python
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table
```

## Table Width Measurement

Without this helper, `Measurement.get()` caps measured width to `console.width` (default 80 in non-TTY), which silently wraps or truncates content as described above.

```python
def _get_table_width(table: Table) -> int:
    """Measure natural table width without the 80-column non-TTY cap."""
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)
```

## Table Creation and Print

```python
table = Table(title=":electric_plug: Device Status", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold blue")
table.add_column("Device", style="cyan", no_wrap=True)
table.add_column("Status", justify="center", no_wrap=True)

table.width = _get_table_width(table)  # natural width, no cap

console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
```

**Prohibited**: `table.width = min(_get_table_width(table), SOME_CAP)`. A cap defeats the measurement. If you believe a cap is required, re-read "The Goal: Zero Data Loss" above — the answer is that the consumer handles width, not the producer.

## When to Use Each Setting

- `box.MINIMAL_DOUBLE_HEAD` — use when output will be consumed by LLMs or piped. No left/right borders avoids whitespace padding that inflates token count.
- `no_wrap=True` on **every** column — non-TTY tables must not wrap cells under any circumstance. Wrapping loses left-hand row context on continuation lines (see "Zero Data Loss" above). If a cell content is genuinely too large for a table row (multi-KB stderr dump, full log files), truncate it **at the data source with an explicit length and ellipsis sentinel** before it reaches the cell — never via column width. The truncation must be visible in the source data, not hidden by Rich's rendering.
- `soft_wrap=True` on `console.print()` — compound flag that sets `no_wrap=True`, `overflow="ignore"`, and `crop=False` together. Use on every non-TTY print call.
- `crop=False` — prevents Rich from hard-cutting all characters past `console.width`. Without it, `console.print(table)` in a non-TTY environment silently drops everything past column 80 even when the table's own `width` is larger.
- `overflow="ignore"` — tells Rich to extend past container boundaries rather than truncate or ellipsize. Required alongside `crop=False` when cells contain data that must appear in full.
- `soft_wrap=True` makes `crop=False` and `overflow="ignore"` redundant, but keeping them explicit documents intent for readers who don't know `soft_wrap` internals.

## Verify with the Demo Script

Run `assets/typer_examples/console_containers_no_wrap.py` to see both failure modes (wrapping that orphans labels, truncation that destroys data) and the working pattern side-by-side. The broken examples in that script demonstrate exactly what happens when the measurement step is skipped or its result is capped.
